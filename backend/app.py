"""Servidor da RiosFootball. Para ligar: dois cliques em rodar.bat e abra http://localhost:5000"""
import html
import json
import re
import secrets
import sqlite3
from datetime import datetime, timedelta
from functools import wraps
from pathlib import Path

from flask import Flask, g, jsonify, redirect, request, send_from_directory, session
from werkzeug.security import check_password_hash, generate_password_hash

from banco import conectar, iniciar_banco

PASTA_BACKEND = Path(__file__).resolve().parent
PASTA_SITE = PASTA_BACKEND.parent / "frontend"
PASTA_PAGINAS = PASTA_BACKEND / "paginas"  # paginas privadas: so o dono recebe

STATUS = ["Aguardando pagamento", "Pago", "Em separação", "Enviado", "Entregue", "Finalizado"]
TAMANHOS = {
    "Torcedor": ["P", "M", "G", "GG", "2XL", "3XL", "4XL"],
    "Jogador": ["P", "M", "G", "GG", "2XL", "3XL", "4XL"],
    "Feminina": ["P", "M", "G", "GG", "2XL"],
    "Kit infantil": ["16", "18", "20", "22", "24", "26", "28"],
    "Conjunto": ["P", "M", "G", "GG", "2XL", "3XL", "4XL"],
}
EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
SECOES = ["Camisas de Time", "Seleções", "NBA"]
COR = re.compile(r"^#[0-9a-fA-F]{6}$")
UPLOADS = PASTA_BACKEND / "uploads"   # fotos e escudos enviados pelo painel
FOTO_MAX = 8 * 1024 * 1024            # 8 MB por foto

app = Flask(__name__, static_folder=str(PASTA_SITE), static_url_path="")


def chave_secreta():
    """Chave que protege o login (cookie). Criada uma vez e guardada em backend/segredo.key. Nao compartilhe."""
    arquivo = PASTA_BACKEND / "segredo.key"
    if not arquivo.exists():
        arquivo.write_text(secrets.token_hex(32))
    return arquivo.read_text().strip()


app.config.update(SECRET_KEY=chave_secreta(), SESSION_COOKIE_HTTPONLY=True, SESSION_COOKIE_SAMESITE="Lax",
                  MAX_CONTENT_LENGTH=100 * 1024 * 1024)


# ---------- utilidades ----------
def banco():
    if "db" not in g:
        g.db = conectar()
    return g.db


@app.teardown_appcontext
def fechar_banco(_erro):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def erro(mensagem, codigo=400):
    return jsonify({"erro": mensagem}), codigo


def agora():
    return datetime.now().isoformat(timespec="seconds")


def usuario_atual():
    uid = session.get("uid")
    if not uid:
        return None
    return banco().execute("SELECT id, nome, telefone, email, papel FROM usuarios WHERE id = ?", (uid,)).fetchone()


def exige_login(funcao):
    @wraps(funcao)
    def protegida(*args, **kwargs):
        if not usuario_atual():
            return erro("Faça login para continuar.", 401)
        return funcao(*args, **kwargs)
    return protegida


def exige_admin(funcao):
    @wraps(funcao)
    def protegida(*args, **kwargs):
        usuario = usuario_atual()
        if not usuario or usuario["papel"] != "admin":
            return erro("Acesso restrito ao dono da loja.", 403)
        return funcao(*args, **kwargs)
    return protegida


@app.before_request
def exige_json():
    """Protecao extra: pedidos que alteram dados precisam vir como JSON (feitos pelo nosso JavaScript)."""
    if request.method in ("POST", "PATCH") and request.path.startswith("/api/"):
        # JSON ou envio de formulario feito pelo nosso JavaScript (que manda este cabecalho)
        if not request.is_json and request.headers.get("X-Requested-With") != "fetch":
            return erro("Requisição inválida.", 415)


@app.after_request
def cabecalhos_de_seguranca(resposta):
    resposta.headers["X-Content-Type-Options"] = "nosniff"  # o navegador nao "adivinha" o tipo dos arquivos
    return resposta


@app.errorhandler(413)
def arquivo_grande(_e):
    return erro("Os arquivos enviados são grandes demais (limite de 100 MB no total).", 413)


def corpo():
    return request.get_json(silent=True) or {}


# ---------- paginas ----------
@app.route("/")
def inicio():
    arquivo = PASTA_SITE / "index.html"
    if not arquivo.exists():
        return (
            "<h1>Não achei o site</h1><p>Procurei o arquivo index.html em:</p>"
            f"<p><code>{html.escape(str(arquivo))}</code></p>"
            "<p>A pasta <b>frontend</b> precisa ficar ao lado da pasta <b>backend</b>.</p>"
        ), 404
    return app.send_static_file("index.html")


@app.route("/admin")
def painel():
    usuario = usuario_atual()
    if not usuario or usuario["papel"] != "admin":
        return redirect("/conta.html")  # atalho: quem nao e o dono cai na tela de login
    return send_from_directory(PASTA_PAGINAS, "admin.html")


# ---------- catalogo ----------
@app.route("/api/produtos")
def listar_produtos():
    db = banco()
    linhas = db.execute(
        "SELECT p.id, p.time_id, t.nome AS time, t.categoria, t.secao, p.versao, p.temporada, p.modelo, "
        "       p.preco, p.lancamento, p.detalhes, "
        "       (SELECT ROUND(AVG(nota), 1) FROM avaliacoes a WHERE a.produto_id = p.id AND a.visivel = 1) AS nota, "
        "       (SELECT COUNT(*) FROM avaliacoes a WHERE a.produto_id = p.id AND a.visivel = 1) AS avaliacoes "
        "FROM produtos p JOIN times t ON t.id = p.time_id "
        "WHERE p.ativo = 1 ORDER BY p.id DESC"
    ).fetchall()
    fotos = db.execute("SELECT produto_id, arquivo FROM fotos ORDER BY produto_id, ordem").fetchall()
    produtos = []
    for linha in linhas:
        produto = dict(linha)
        produto["fotos"] = [f["arquivo"] for f in fotos if f["produto_id"] == produto["id"]]
        produtos.append(produto)
    return jsonify(produtos)


# ---------- conta: cadastro, login, sair ----------
@app.route("/api/cadastro", methods=["POST"])
def cadastrar():
    d = corpo()
    nome = str(d.get("nome", "")).strip()
    email = str(d.get("email", "")).strip().lower()
    telefone = re.sub(r"\D", "", str(d.get("telefone", "")))
    senha = str(d.get("senha", ""))
    if not 2 <= len(nome) <= 80:
        return erro("Informe seu nome.")
    if not 10 <= len(telefone) <= 13:
        return erro("Informe um telefone válido, com DDD.")
    if not EMAIL.match(email):
        return erro("Informe um e-mail válido.")
    if len(senha) < 6:
        return erro("A senha precisa ter pelo menos 6 caracteres.")
    db = banco()
    try:
        cursor = db.execute(
            "INSERT INTO usuarios (login, nome, telefone, email, senha_hash) VALUES (?, ?, ?, ?, ?)",
            (email, nome, telefone, email, generate_password_hash(senha)),
        )
        db.commit()
    except sqlite3.IntegrityError:
        return erro("Já existe uma conta com esse e-mail.", 409)
    session.clear()
    session["uid"] = cursor.lastrowid
    return jsonify({"nome": nome, "papel": "cliente"})


@app.route("/api/login", methods=["POST"])
def entrar():
    d = corpo()
    login = str(d.get("login", "")).strip().lower()
    senha = str(d.get("senha", ""))
    db = banco()
    u = db.execute("SELECT * FROM usuarios WHERE login = ?", (login,)).fetchone()

    if u and u["bloqueado_ate"] and datetime.now() < datetime.fromisoformat(u["bloqueado_ate"]):
        return erro("Muitas tentativas erradas. Tente de novo em alguns minutos.", 429)

    if not u or not check_password_hash(u["senha_hash"], senha):
        if u:  # conta as tentativas erradas; na 5a, bloqueia por 10 minutos
            tentativas = u["tentativas"] + 1
            bloqueio = (datetime.now() + timedelta(minutes=10)).isoformat() if tentativas >= 5 else None
            db.execute("UPDATE usuarios SET tentativas = ?, bloqueado_ate = ? WHERE id = ?",
                       (0 if bloqueio else tentativas, bloqueio, u["id"]))
            db.commit()
        return erro("Usuário ou senha incorretos.", 401)

    db.execute("UPDATE usuarios SET tentativas = 0, bloqueado_ate = NULL WHERE id = ?", (u["id"],))
    db.commit()
    session.clear()
    session["uid"] = u["id"]
    return jsonify({"nome": u["nome"], "papel": u["papel"], "telefone_pendente": telefone_pendente(u)})


@app.route("/api/logout", methods=["POST"])
def sair():
    session.clear()
    return jsonify({"ok": True})


@app.route("/api/eu")
def quem_sou_eu():
    u = usuario_atual()
    if not u:
        return jsonify({"logado": False})
    return jsonify({"logado": True, "nome": u["nome"], "papel": u["papel"], "telefone_pendente": telefone_pendente(u)})


# ---------- login com Google ----------
GOOGLE_ARQUIVO = PASTA_BACKEND / "config_google.txt"


def google_client_id():
    """Le o ID do cliente do Google em backend/config_google.txt (o arquivo e criado vazio na 1a vez)."""
    if not GOOGLE_ARQUIVO.exists():
        GOOGLE_ARQUIVO.write_text(
            "# Cole abaixo, em uma linha, o ID do cliente do Google (termina com .apps.googleusercontent.com)\n",
            encoding="utf-8")
    for linha in GOOGLE_ARQUIVO.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if linha and not linha.startswith("#"):
            return linha
    return ""


def telefone_pendente(usuario):
    return usuario["papel"] != "admin" and not usuario["telefone"]


@app.route("/api/google-config")
def google_config():
    return jsonify({"client_id": google_client_id()})  # o ID do cliente e publico por natureza


@app.route("/api/login-google", methods=["POST"])
def entrar_com_google():
    client_id = google_client_id()
    if not client_id:
        return erro("O login com Google ainda não foi configurado.", 503)
    try:
        from google.auth.transport import requests as requisicoes
        from google.oauth2 import id_token
    except ImportError:
        return erro("Falta instalar a biblioteca do Google. Feche e abra o rodar.bat de novo.", 500)
    try:
        # O Google assina o "credential"; aqui conferimos a assinatura, o destinatario (nosso ID) e a validade
        dados = id_token.verify_oauth2_token(
            str(corpo().get("credential", "")), requisicoes.Request(), client_id, clock_skew_in_seconds=10)
    except ValueError:
        return erro("Não foi possível confirmar sua conta Google. Tente de novo.", 401)
    except Exception:
        return erro("Não foi possível falar com o Google. Confira sua internet e tente de novo.", 502)

    email = str(dados.get("email", "")).lower()
    if not dados.get("email_verified") or not EMAIL.match(email):
        return erro("O e-mail desta conta Google não está verificado.", 401)

    db = banco()
    u = db.execute("SELECT * FROM usuarios WHERE login = ?", (email,)).fetchone()
    if u and u["papel"] == "admin":
        return erro("Esta conta não pode entrar com o Google.", 403)
    if u:
        uid, nome, telefone = u["id"], u["nome"], u["telefone"]
    else:  # primeiro acesso: cria a conta com o nome do Google (a senha fica trancada, o acesso e sempre pelo Google)
        nome = str(dados.get("name") or email.split("@")[0]).strip()[:80]
        telefone = None
        uid = db.execute("INSERT INTO usuarios (login, nome, email, senha_hash) VALUES (?, ?, ?, ?)",
                         (email, nome, email, generate_password_hash(secrets.token_urlsafe(32)))).lastrowid
        db.commit()
    session.clear()
    session["uid"] = uid
    return jsonify({"nome": nome, "papel": "cliente", "telefone_pendente": not telefone})


@app.route("/api/completar-cadastro", methods=["POST"])
@exige_login
def completar_cadastro():
    telefone = re.sub(r"\D", "", str(corpo().get("telefone", "")))
    if not 10 <= len(telefone) <= 13:
        return erro("Informe um telefone válido, com DDD.")
    db = banco()
    db.execute("UPDATE usuarios SET telefone = ? WHERE id = ?", (telefone, usuario_atual()["id"]))
    db.commit()
    return jsonify({"ok": True})


# ---------- pedidos ----------
def com_itens(linhas):
    db = banco()
    pedidos = []
    for linha in linhas:
        p = dict(linha)
        p["itens"] = [dict(i) for i in db.execute(
            "SELECT nome, tamanho, qtd, preco FROM pedido_itens WHERE pedido_id = ?", (p["id"],))]
        pedidos.append(p)
    return pedidos


@app.route("/api/pedidos", methods=["POST"])
@exige_login
def criar_pedido():
    if telefone_pendente(usuario_atual()):  # conta criada pelo Google ainda sem telefone
        return jsonify({"erro": "Complete seu cadastro com o telefone para fazer o pedido.", "telefone_pendente": True}), 403
    itens = corpo().get("itens")
    if not isinstance(itens, list) or not 0 < len(itens) <= 30:
        return erro("Seu carrinho está vazio.")
    db = banco()
    linhas, total = [], 0.0
    for item in itens:
        try:
            pid, qtd, tamanho = int(item["id"]), int(item["qtd"]), str(item["tamanho"])
        except (KeyError, TypeError, ValueError):
            return erro("Item inválido no carrinho.")
        p = db.execute(
            "SELECT p.id, p.preco, p.modelo, p.versao, p.temporada, t.nome AS time "
            "FROM produtos p JOIN times t ON t.id = p.time_id WHERE p.id = ? AND p.ativo = 1", (pid,)).fetchone()
        if not p or not 1 <= qtd <= 20 or tamanho not in TAMANHOS.get(p["modelo"], []):
            return erro("Um item do carrinho não está mais disponível. Atualize a página.")
        tipo = "Conjunto" if p["modelo"] == "Conjunto" else "Camisa"
        nome = f"{tipo} {p['time']} {p['versao']} {p['temporada']} ({p['modelo']})"
        linhas.append((pid, nome, tamanho, qtd, p["preco"]))  # o preco vem do banco, nunca do navegador
        total += p["preco"] * qtd
    total = round(total, 2)

    cursor = db.execute("INSERT INTO pedidos (cliente_id, status, total, criado_em) VALUES (?, ?, ?, ?)",
                        (usuario_atual()["id"], STATUS[0], total, agora()))
    numero = cursor.lastrowid
    db.executemany("INSERT INTO pedido_itens (pedido_id, produto_id, nome, tamanho, qtd, preco) VALUES (?, ?, ?, ?, ?, ?)",
                   [(numero, *linha) for linha in linhas])
    db.commit()
    return jsonify({"numero": numero, "total": total,
                    "itens": [{"nome": l[1], "tamanho": l[2], "qtd": l[3]} for l in linhas]})


@app.route("/api/meus-pedidos")
@exige_login
def meus_pedidos():
    linhas = banco().execute(
        "SELECT id, status, total, criado_em FROM pedidos WHERE cliente_id = ? ORDER BY id DESC",
        (usuario_atual()["id"],)).fetchall()
    return jsonify(com_itens(linhas))


# ---------- painel do dono ----------
@app.route("/api/admin/pedidos")
@exige_admin
def admin_pedidos():
    linhas = banco().execute(
        "SELECT p.id, p.status, p.total, p.criado_em, u.nome, u.telefone, u.email "
        "FROM pedidos p JOIN usuarios u ON u.id = p.cliente_id ORDER BY p.id DESC LIMIT 300").fetchall()
    return jsonify({"status": STATUS, "pedidos": com_itens(linhas)})


@app.route("/api/admin/pedidos/<int:numero>/status", methods=["PATCH"])
@exige_admin
def admin_mudar_status(numero):
    novo = corpo().get("status")
    if novo not in STATUS:
        return erro("Status inválido.")
    db = banco()
    db.execute("UPDATE pedidos SET status = ? WHERE id = ?", (novo, numero))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/admin/trocar-senha", methods=["POST"])
@exige_admin
def admin_trocar_senha():
    d = corpo()
    db = banco()
    u = db.execute("SELECT * FROM usuarios WHERE id = ?", (usuario_atual()["id"],)).fetchone()
    if not check_password_hash(u["senha_hash"], str(d.get("atual", ""))):
        return erro("A senha atual está incorreta.", 401)
    nova = str(d.get("nova", ""))
    if len(nova) < 8:
        return erro("A nova senha precisa ter pelo menos 8 caracteres.")
    db.execute("UPDATE usuarios SET senha_hash = ? WHERE id = ?", (generate_password_hash(nova), u["id"]))
    db.commit()
    return jsonify({"ok": True})


# ---------- times e produtos (painel do dono) ----------
def tipo_imagem(dados):
    """Confere o conteudo do arquivo (nao so a extensao). Devolve a extensao ou None."""
    if dados[:3] == b"\xff\xd8\xff":
        return ".jpg"
    if dados[:8] == b"\x89PNG\r\n\x1a\n":
        return ".png"
    if dados[:4] == b"RIFF" and dados[8:12] == b"WEBP":
        return ".webp"
    return None


def ler_imagens(arquivos, maximo):
    imagens = []
    for arquivo in arquivos:
        if not arquivo.filename:  # campo de arquivo vazio
            continue
        dados = arquivo.read(FOTO_MAX + 1)
        if len(dados) > FOTO_MAX:
            raise ValueError("Cada foto pode ter no máximo 8 MB.")
        extensao = tipo_imagem(dados)
        if not extensao:
            raise ValueError("Envie apenas fotos JPG, PNG ou WEBP.")
        imagens.append((dados, extensao))
    if len(imagens) > maximo:
        raise ValueError(f"Envie no máximo {maximo} foto(s).")
    return imagens


def salvar_imagem(pasta, dados, extensao):
    """Grava a imagem com nome aleatorio (nunca usamos o nome que veio do navegador)."""
    destino = UPLOADS / pasta
    destino.mkdir(parents=True, exist_ok=True)
    nome = secrets.token_hex(8) + extensao
    (destino / nome).write_bytes(dados)
    return f"/uploads/{pasta}/{nome}"


@app.route("/uploads/<path:caminho>")
def entregar_upload(caminho):
    return send_from_directory(UPLOADS, caminho)


@app.route("/api/times")
def listar_times():
    linhas = banco().execute(
        "SELECT id, nome, categoria, secao, escudo, cor1, cor2 FROM times ORDER BY secao, categoria, nome").fetchall()
    return jsonify([dict(l) for l in linhas])


@app.route("/api/admin/times", methods=["POST"])
@exige_admin
def admin_salvar_time():
    f = request.form
    nome = f.get("nome", "").strip()
    secao, categoria = f.get("secao", ""), f.get("liga", "").strip()
    cor1, cor2 = f.get("cor1", ""), f.get("cor2", "")
    if not 2 <= len(nome) <= 60:
        return erro("Informe o nome do time.")
    if secao not in SECOES:
        return erro("Escolha a seção do menu.")
    if not 2 <= len(categoria) <= 40:
        return erro("Informe a liga ou o campeonato.")
    if not (COR.match(cor1) and COR.match(cor2)):
        return erro("Escolha as duas cores.")
    try:
        imagens = ler_imagens(request.files.getlist("escudo"), 1)
    except ValueError as e:
        return erro(str(e))

    db = banco()
    existente = db.execute("SELECT id FROM times WHERE nome = ? COLLATE NOCASE", (nome,)).fetchone()
    if existente:  # time ja cadastrado: atualiza (util para colocar o escudo nos times de exemplo)
        time_id = existente["id"]
        db.execute("UPDATE times SET categoria = ?, secao = ?, cor1 = ?, cor2 = ? WHERE id = ?",
                   (categoria, secao, cor1, cor2, time_id))
    else:
        time_id = db.execute("INSERT INTO times (nome, categoria, secao, cor1, cor2) VALUES (?, ?, ?, ?, ?)",
                             (nome, categoria, secao, cor1, cor2)).lastrowid
    if imagens:
        db.execute("UPDATE times SET escudo = ? WHERE id = ?", (salvar_imagem("escudos", *imagens[0]), time_id))
    db.commit()
    return jsonify({"id": time_id, "atualizado": bool(existente)})


@app.route("/api/admin/times")
@exige_admin
def admin_listar_times():
    linhas = banco().execute(
        "SELECT t.id, t.nome, t.categoria, t.secao, t.escudo, t.cor1, t.cor2, "
        "       (SELECT COUNT(*) FROM produtos p WHERE p.time_id = t.id) AS produtos "
        "FROM times t ORDER BY t.secao, t.categoria, t.nome").fetchall()
    return jsonify([dict(l) for l in linhas])


def ler_time(f):
    """Confere os campos do formulario de time. Levanta ValueError com a mensagem para o dono."""
    nome = f.get("nome", "").strip()
    secao, liga = f.get("secao", ""), f.get("liga", "").strip()
    cor1, cor2 = f.get("cor1", ""), f.get("cor2", "")
    if not 2 <= len(nome) <= 60:
        raise ValueError("Informe o nome do time.")
    if secao not in SECOES:
        raise ValueError("Escolha a seção do menu.")
    if not 2 <= len(liga) <= 40:
        raise ValueError("Informe a liga ou o campeonato.")
    if not (COR.match(cor1) and COR.match(cor2)):
        raise ValueError("Escolha as duas cores.")
    return {"nome": nome, "secao": secao, "categoria": liga, "cor1": cor1, "cor2": cor2}


@app.route("/api/admin/times/<int:time_id>", methods=["POST"])
@exige_admin
def admin_editar_time(time_id):
    db = banco()
    atual = db.execute("SELECT * FROM times WHERE id = ?", (time_id,)).fetchone()
    if not atual:
        return erro("Time não encontrado.", 404)
    try:
        dados = ler_time(request.form)
        imagens = ler_imagens(request.files.getlist("escudo"), 1)
    except ValueError as e:
        return erro(str(e))
    if db.execute("SELECT 1 FROM times WHERE nome = ? COLLATE NOCASE AND id != ?", (dados["nome"], time_id)).fetchone():
        return erro("Já existe outro time com esse nome.", 409)

    escudo, antigo = atual["escudo"], None
    if imagens:                                          # escudo novo: troca o arquivo
        antigo, escudo = escudo, salvar_imagem("escudos", *imagens[0])
    elif request.form.get("remover_escudo") == "1":      # ou so tira o escudo
        antigo, escudo = escudo, None
    db.execute("UPDATE times SET nome = :nome, categoria = :categoria, secao = :secao, cor1 = :cor1, cor2 = :cor2, "
               "escudo = :escudo WHERE id = :id", {**dados, "escudo": escudo, "id": time_id})
    db.commit()
    apagar_arquivo(antigo)
    return jsonify({"ok": True})


@app.route("/api/admin/times/<int:time_id>/excluir", methods=["POST"])
@exige_admin
def admin_excluir_time(time_id):
    db = banco()
    atual = db.execute("SELECT * FROM times WHERE id = ?", (time_id,)).fetchone()
    if not atual:
        return erro("Time não encontrado.", 404)
    quantos = db.execute("SELECT COUNT(*) FROM produtos WHERE time_id = ?", (time_id,)).fetchone()[0]
    if quantos:  # protege contra apagar sem querer um time que ainda tem camisas
        return erro(f"Este time tem {quantos} produto(s) cadastrado(s). Exclua esses produtos primeiro.", 409)
    db.execute("DELETE FROM times WHERE id = ?", (time_id,))
    db.commit()
    apagar_arquivo(atual["escudo"])
    return jsonify({"ok": True})


def ler_produto(f, db, ignorar_id=0):
    """Confere os campos do formulario de produto. Levanta ValueError com a mensagem para o dono."""
    try:
        time_id = int(f.get("time_id", ""))
    except ValueError:
        raise ValueError("Escolha o time.")
    if not db.execute("SELECT 1 FROM times WHERE id = ?", (time_id,)).fetchone():
        raise ValueError("Escolha o time.")
    versao = f.get("versao", "").strip()
    if versao == "Outra":
        versao = f.get("versao_outra", "").strip()
    if not 2 <= len(versao) <= 40:
        raise ValueError("Informe a versão da camisa (titular, reserva, terceira ou outra).")
    temporada = f.get("temporada", "").strip()
    if not re.fullmatch(r"\d{2}/\d{2}", temporada):
        raise ValueError("Escreva a temporada assim: 25/26.")
    modelo = f.get("modelo", "")
    if modelo not in TAMANHOS:
        raise ValueError("Escolha o modelo.")
    texto = f.get("preco", "").replace("R$", "").strip()
    if "," in texto:  # aceita 1.299,90 e 149,90
        texto = texto.replace(".", "").replace(",", ".")
    try:
        preco = round(float(texto), 2)
    except ValueError:
        raise ValueError("Informe o preço, por exemplo 149,90.")
    if not 0 < preco < 10000:
        raise ValueError("Preço fora do esperado.")
    if db.execute("SELECT 1 FROM produtos WHERE time_id = ? AND versao = ? COLLATE NOCASE "
                  "AND temporada = ? AND modelo = ? AND id != ?",
                  (time_id, versao, temporada, modelo, ignorar_id)).fetchone():
        raise ValueError("Essa camisa já está cadastrada.")
    return {"time_id": time_id, "versao": versao, "temporada": temporada, "modelo": modelo, "preco": preco,
            "lancamento": 1 if f.get("lancamento") == "1" else 0,
            "detalhes": f.get("detalhes", "").strip()[:300] or None}


def gravar_foto(db, produto_id, dados, extensao, ordem):
    url = salvar_imagem(f"produtos/{produto_id}", dados, extensao)
    db.execute("INSERT INTO fotos (produto_id, arquivo, ordem) VALUES (?, ?, ?)", (produto_id, url, ordem))


def apagar_arquivo(url):
    """Apaga uma foto do disco, so se ela estiver mesmo dentro da pasta uploads."""
    if not url or not url.startswith("/uploads/"):
        return
    alvo = (UPLOADS / url[len("/uploads/"):]).resolve()
    if alvo.is_relative_to(UPLOADS.resolve()) and alvo.is_file():
        alvo.unlink()


@app.route("/api/admin/produtos")
@exige_admin
def admin_listar_produtos():
    db = banco()
    linhas = db.execute(
        "SELECT p.id, p.time_id, t.nome AS time, p.versao, p.temporada, p.modelo, p.preco, "
        "       p.lancamento, p.detalhes, p.ativo "
        "FROM produtos p JOIN times t ON t.id = p.time_id ORDER BY p.id DESC").fetchall()
    fotos = db.execute("SELECT id, produto_id, arquivo FROM fotos ORDER BY produto_id, ordem").fetchall()
    produtos = []
    for linha in linhas:
        p = dict(linha)
        p["fotos"] = [{"id": f["id"], "arquivo": f["arquivo"]} for f in fotos if f["produto_id"] == p["id"]]
        produtos.append(p)
    return jsonify(produtos)


@app.route("/api/admin/produtos", methods=["POST"])
@exige_admin
def admin_criar_produto():
    db = banco()
    try:
        dados = ler_produto(request.form, db)
        fotos = ler_imagens(request.files.getlist("fotos"), 12)
    except ValueError as e:
        return erro(str(e))
    if not fotos:
        return erro("Envie ao menos uma foto.")
    produto_id = db.execute(
        "INSERT INTO produtos (time_id, versao, temporada, modelo, preco, lancamento, detalhes) "
        "VALUES (:time_id, :versao, :temporada, :modelo, :preco, :lancamento, :detalhes)", dados).lastrowid
    for ordem, (conteudo, extensao) in enumerate(fotos):  # a 1a foto enviada e a principal
        gravar_foto(db, produto_id, conteudo, extensao, ordem)
    db.commit()
    return jsonify({"id": produto_id})


@app.route("/api/admin/produtos/<int:produto_id>", methods=["POST"])
@exige_admin
def admin_editar_produto(produto_id):
    db = banco()
    if not db.execute("SELECT 1 FROM produtos WHERE id = ?", (produto_id,)).fetchone():
        return erro("Produto não encontrado.", 404)
    try:
        dados = ler_produto(request.form, db, produto_id)
        novas = ler_imagens(request.files.getlist("fotos"), 12)
    except ValueError as e:
        return erro(str(e))

    # "ordem" diz como ficam as fotos: "e12" = foto ja salva de id 12, "n0" = 1a foto nova enviada
    try:
        ordem = json.loads(request.form.get("ordem", "[]"))
    except ValueError:
        ordem = None
    if not isinstance(ordem, list) or not all(isinstance(t, str) and re.fullmatch(r"[en]\d+", t) for t in ordem):
        return erro("Fotos inválidas.")
    atuais = {f["id"]: f["arquivo"] for f in db.execute("SELECT id, arquivo FROM fotos WHERE produto_id = ?", (produto_id,))}
    mantidas = [int(t[1:]) for t in ordem if t[0] == "e"]
    usadas_novas = sorted(int(t[1:]) for t in ordem if t[0] == "n")
    if len(set(mantidas)) != len(mantidas) or any(i not in atuais for i in mantidas) \
            or usadas_novas != list(range(len(novas))):
        return erro("Fotos inválidas.")
    if not ordem:
        return erro("O produto precisa ter ao menos uma foto.")
    if len(ordem) > 12:
        return erro("Máximo de 12 fotos.")

    db.execute("UPDATE produtos SET time_id = :time_id, versao = :versao, temporada = :temporada, modelo = :modelo, "
               "preco = :preco, lancamento = :lancamento, detalhes = :detalhes WHERE id = :id", {**dados, "id": produto_id})
    removidas = []
    for foto_id, arquivo in atuais.items():
        if foto_id not in mantidas:
            db.execute("DELETE FROM fotos WHERE id = ?", (foto_id,))
            removidas.append(arquivo)
    for posicao, token in enumerate(ordem):
        if token[0] == "e":
            db.execute("UPDATE fotos SET ordem = ? WHERE id = ?", (posicao, int(token[1:])))
        else:
            conteudo, extensao = novas[int(token[1:])]
            gravar_foto(db, produto_id, conteudo, extensao, posicao)
    db.commit()
    for arquivo in removidas:
        apagar_arquivo(arquivo)
    return jsonify({"ok": True})


@app.route("/api/admin/produtos/<int:produto_id>/ativo", methods=["POST"])
@exige_admin
def admin_ocultar_produto(produto_id):
    db = banco()
    db.execute("UPDATE produtos SET ativo = ? WHERE id = ?", (1 if corpo().get("ativo") else 0, produto_id))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/admin/produtos/<int:produto_id>/excluir", methods=["POST"])
@exige_admin
def admin_excluir_produto(produto_id):
    db = banco()
    arquivos = [f["arquivo"] for f in db.execute("SELECT arquivo FROM fotos WHERE produto_id = ?", (produto_id,))]
    arquivos += [m["arquivo"] for m in db.execute(
        "SELECT m.arquivo FROM avaliacao_midias m JOIN avaliacoes a ON a.id = m.avaliacao_id WHERE a.produto_id = ?",
        (produto_id,))]
    db.execute("DELETE FROM avaliacao_midias WHERE avaliacao_id IN (SELECT id FROM avaliacoes WHERE produto_id = ?)", (produto_id,))
    db.execute("DELETE FROM avaliacoes WHERE produto_id = ?", (produto_id,))
    db.execute("DELETE FROM fotos WHERE produto_id = ?", (produto_id,))
    db.execute("DELETE FROM produtos WHERE id = ?", (produto_id,))  # pedidos antigos guardam nome e preco, nada se perde
    db.commit()
    for arquivo in arquivos:
        apagar_arquivo(arquivo)
    return jsonify({"ok": True})


# ---------- avaliacoes ----------
VIDEO_MAX = 50 * 1024 * 1024  # 50 MB


def tipo_video(dados):
    """Confere o conteudo do video (nao so a extensao)."""
    if dados[4:8] == b"ftyp":
        return ".mov" if dados[8:12] == b"qt  " else ".mp4"
    if dados[:4] == b"\x1a\x45\xdf\xa3":
        return ".webm"
    return None


def nome_publico(nome):
    """Mostra so o primeiro nome e a inicial do ultimo: 'Maria S.'"""
    partes = nome.split()
    return partes[0] if len(partes) < 2 else f"{partes[0]} {partes[-1][0]}."


def situacao_avaliacao(db, produto_id, usuario):
    """Diz se o cliente logado pode avaliar a camisa e, se nao puder, o motivo."""
    if not usuario:
        return False, "Entre na sua conta para avaliar."
    if db.execute("SELECT 1 FROM avaliacoes WHERE produto_id = ? AND cliente_id = ?", (produto_id, usuario["id"])).fetchone():
        return False, "Você já avaliou esta camisa. Obrigado!"
    comprou = db.execute(
        "SELECT 1 FROM pedido_itens i JOIN pedidos p ON p.id = i.pedido_id "
        "WHERE i.produto_id = ? AND p.cliente_id = ? AND p.status IN ('Entregue', 'Finalizado')",
        (produto_id, usuario["id"])).fetchone()
    if not comprou:
        return False, "Só quem comprou esta camisa pode avaliar, depois que o pedido for entregue."
    return True, ""


@app.route("/api/produtos/<int:produto_id>/avaliacoes")
def listar_avaliacoes(produto_id):
    db = banco()
    linhas = db.execute(
        "SELECT a.id, a.nota, a.texto, a.criado_em, u.nome FROM avaliacoes a JOIN usuarios u ON u.id = a.cliente_id "
        "WHERE a.produto_id = ? AND a.visivel = 1 ORDER BY a.id DESC LIMIT 100", (produto_id,)).fetchall()
    resumo = db.execute("SELECT ROUND(AVG(nota), 1) AS media, COUNT(*) AS total FROM avaliacoes "
                        "WHERE produto_id = ? AND visivel = 1", (produto_id,)).fetchone()
    lista = []
    for l in linhas:
        midias = [dict(m) for m in db.execute(
            "SELECT arquivo, tipo FROM avaliacao_midias WHERE avaliacao_id = ?", (l["id"],))]
        lista.append({"id": l["id"], "nota": l["nota"], "texto": l["texto"], "criado_em": l["criado_em"],
                      "autor": nome_publico(l["nome"]), "midias": midias})
    pode, motivo = situacao_avaliacao(db, produto_id, usuario_atual())
    return jsonify({"media": resumo["media"] or 0, "total": resumo["total"], "avaliacoes": lista,
                    "pode_avaliar": pode, "motivo": motivo})


@app.route("/api/produtos/<int:produto_id>/avaliacoes", methods=["POST"])
@exige_login
def criar_avaliacao(produto_id):
    db = banco()
    if not db.execute("SELECT 1 FROM produtos WHERE id = ?", (produto_id,)).fetchone():
        return erro("Produto não encontrado.", 404)
    pode, motivo = situacao_avaliacao(db, produto_id, usuario_atual())
    if not pode:
        return erro(motivo, 403)
    try:
        nota = int(request.form.get("nota", ""))
    except ValueError:
        nota = 0
    if not 1 <= nota <= 5:
        return erro("Escolha de 1 a 5 estrelas.")
    texto = request.form.get("texto", "").strip()[:1000] or None

    try:
        fotos = ler_imagens(request.files.getlist("fotos"), 5)
        videos = [v for v in request.files.getlist("video") if v.filename]
        if len(videos) > 1:
            raise ValueError("Envie apenas 1 vídeo.")
        video = None
        if videos:
            dados = videos[0].read(VIDEO_MAX + 1)
            if len(dados) > VIDEO_MAX:
                raise ValueError("O vídeo pode ter no máximo 50 MB.")
            extensao = tipo_video(dados)
            if not extensao:
                raise ValueError("Envie o vídeo em MP4, MOV ou WEBM.")
            video = (dados, extensao)
    except ValueError as e:
        return erro(str(e))

    avaliacao_id = db.execute(
        "INSERT INTO avaliacoes (produto_id, cliente_id, nota, texto, criado_em) VALUES (?, ?, ?, ?, ?)",
        (produto_id, usuario_atual()["id"], nota, texto, agora())).lastrowid
    pasta = f"avaliacoes/{avaliacao_id}"
    for dados, extensao in fotos:
        db.execute("INSERT INTO avaliacao_midias (avaliacao_id, arquivo, tipo) VALUES (?, ?, 'foto')",
                   (avaliacao_id, salvar_imagem(pasta, dados, extensao)))
    if video:
        db.execute("INSERT INTO avaliacao_midias (avaliacao_id, arquivo, tipo) VALUES (?, ?, 'video')",
                   (avaliacao_id, salvar_imagem(pasta, *video)))
    db.commit()
    return jsonify({"ok": True})


@app.route("/api/admin/avaliacoes")
@exige_admin
def admin_avaliacoes():
    db = banco()
    linhas = db.execute(
        "SELECT a.id, a.nota, a.texto, a.criado_em, a.visivel, u.nome, t.nome AS time, p.versao, p.temporada, p.modelo "
        "FROM avaliacoes a JOIN usuarios u ON u.id = a.cliente_id JOIN produtos p ON p.id = a.produto_id "
        "JOIN times t ON t.id = p.time_id ORDER BY a.id DESC LIMIT 200").fetchall()
    lista = []
    for l in linhas:
        a = dict(l)
        a["midias"] = [dict(m) for m in db.execute(
            "SELECT arquivo, tipo FROM avaliacao_midias WHERE avaliacao_id = ?", (a["id"],))]
        lista.append(a)
    return jsonify(lista)


@app.route("/api/admin/avaliacoes/<int:avaliacao_id>/visivel", methods=["POST"])
@exige_admin
def admin_visibilidade_avaliacao(avaliacao_id):
    db = banco()
    db.execute("UPDATE avaliacoes SET visivel = ? WHERE id = ?", (1 if corpo().get("visivel") else 0, avaliacao_id))
    db.commit()
    return jsonify({"ok": True})


if __name__ == "__main__":
    UPLOADS.mkdir(exist_ok=True)
    iniciar_banco()
    print(f"Procurando o site em: {PASTA_SITE}  (index.html existe? {(PASTA_SITE / 'index.html').exists()})")
    app.run(debug=True)
