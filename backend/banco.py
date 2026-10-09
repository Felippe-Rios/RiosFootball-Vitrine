"""Banco de dados da RiosFootball (SQLite): cria as tabelas e, na 1a vez, coloca dados de exemplo."""
import sqlite3
from pathlib import Path

from werkzeug.security import generate_password_hash

ARQUIVO = Path(__file__).resolve().parent / "loja.db"  # o banco inteiro e este arquivo unico

# Tres tabelas ligadas entre si: um time tem varios produtos; um produto tem varias fotos
TABELAS = """
CREATE TABLE IF NOT EXISTS times (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    nome      TEXT NOT NULL UNIQUE,
    categoria TEXT NOT NULL,          -- a liga ou campeonato (vira uma coluna no menu de times)
    secao     TEXT NOT NULL DEFAULT 'Camisas de Time',   -- Camisas de Time, Seleções ou NBA
    escudo    TEXT,                   -- caminho da imagem do escudo (usaremos nas proximas etapas)
    cor1      TEXT,
    cor2      TEXT
);
CREATE TABLE IF NOT EXISTS produtos (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    time_id    INTEGER NOT NULL REFERENCES times(id),
    versao     TEXT NOT NULL,         -- Titular, Reserva, Terceira...
    temporada  TEXT NOT NULL,         -- ex: 25/26
    modelo     TEXT NOT NULL,         -- Torcedor, Jogador, Kit infantil, Feminina
    preco      REAL NOT NULL,
    lancamento INTEGER NOT NULL DEFAULT 0,
    detalhes   TEXT,
    ativo      INTEGER NOT NULL DEFAULT 1
);
CREATE TABLE IF NOT EXISTS fotos (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id INTEGER NOT NULL REFERENCES produtos(id),
    arquivo    TEXT NOT NULL,         -- endereco da foto, ex: /uploads/produtos/7/1.jpg
    ordem      INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS usuarios (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    login         TEXT NOT NULL UNIQUE,   -- e-mail do cliente (minusculo) ou "admin"
    nome          TEXT NOT NULL,
    telefone      TEXT,
    email         TEXT,
    senha_hash    TEXT NOT NULL,          -- a senha nunca e guardada, so este "embaralhado"
    papel         TEXT NOT NULL DEFAULT 'cliente',   -- cliente ou admin
    tentativas    INTEGER NOT NULL DEFAULT 0,
    bloqueado_ate TEXT
);
CREATE TABLE IF NOT EXISTS pedidos (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,   -- este e o numero do pedido (cresce em ordem cronologica)
    cliente_id INTEGER NOT NULL REFERENCES usuarios(id),
    status     TEXT NOT NULL,
    total      REAL NOT NULL,
    criado_em  TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS pedido_itens (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    pedido_id  INTEGER NOT NULL REFERENCES pedidos(id),
    produto_id INTEGER,
    nome       TEXT NOT NULL,             -- guardamos o nome e o preco da hora da compra
    tamanho    TEXT NOT NULL,
    qtd        INTEGER NOT NULL,
    preco      REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS avaliacoes (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    produto_id INTEGER NOT NULL REFERENCES produtos(id),
    cliente_id INTEGER NOT NULL REFERENCES usuarios(id),
    nota       INTEGER NOT NULL,          -- 1 a 5 estrelas
    texto      TEXT,
    criado_em  TEXT NOT NULL,
    visivel    INTEGER NOT NULL DEFAULT 1,
    UNIQUE (produto_id, cliente_id)       -- cada cliente avalia cada camisa uma vez
);
CREATE TABLE IF NOT EXISTS avaliacao_midias (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    avaliacao_id INTEGER NOT NULL REFERENCES avaliacoes(id),
    arquivo      TEXT NOT NULL,
    tipo         TEXT NOT NULL            -- foto ou video
);
"""

# Dados de exemplo (precos inventados). Depois voce cadastra os reais pelo painel.
TIMES = [
    ("Flamengo", "Brasileirão"), ("Corinthians", "Brasileirão"), ("Cruzeiro", "Brasileirão"),
    ("Real Madrid", "Europa"), ("Barcelona", "Europa"), ("Brasil", "Seleções"),
]
PRODUTOS = [  # time, versao, temporada, modelo, preco, lancamento, detalhes
    ("Flamengo", "Titular", "25/26", "Torcedor", 149.90, 0, "Escudo bordado e gola com acabamento dourado."),
    ("Flamengo", "Reserva", "25/26", "Jogador", 199.90, 0, None),
    ("Corinthians", "Titular", "25/26", "Torcedor", 149.90, 0, None),
    ("Cruzeiro", "Titular", "25/26", "Torcedor", 149.90, 1, None),
    ("Real Madrid", "Titular", "25/26", "Feminina", 159.90, 0, None),
    ("Barcelona", "Reserva", "25/26", "Kit infantil", 139.90, 0, "Kit com camisa e short."),
    ("Brasil", "Titular", "24/25", "Jogador", 219.90, 0, None),
]


def conectar():
    conexao = sqlite3.connect(ARQUIVO)
    conexao.row_factory = sqlite3.Row            # permite ler as colunas pelo nome
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def iniciar_banco():
    db = conectar()
    db.executescript(TABELAS)
    if "secao" not in [c["name"] for c in db.execute("PRAGMA table_info(times)")]:  # banco criado antes do menu novo
        db.execute("ALTER TABLE times ADD COLUMN secao TEXT NOT NULL DEFAULT 'Camisas de Time'")
        db.execute("UPDATE times SET secao = 'Seleções' WHERE categoria = 'Seleções'")
    if db.execute("SELECT COUNT(*) FROM times").fetchone()[0] == 0:
        db.executemany("INSERT INTO times (nome, categoria) VALUES (?, ?)", TIMES)
        db.execute("UPDATE times SET secao = 'Seleções' WHERE categoria = 'Seleções'")
        for nome_time, *resto in PRODUTOS:
            db.execute(
                "INSERT INTO produtos (time_id, versao, temporada, modelo, preco, lancamento, detalhes) "
                "VALUES ((SELECT id FROM times WHERE nome = ?), ?, ?, ?, ?, ?, ?)",
                (nome_time, *resto),
            )
    if db.execute("SELECT COUNT(*) FROM usuarios WHERE papel = 'admin'").fetchone()[0] == 0:
        # SENHA INICIAL, so para testar no seu computador. Troque no painel (Trocar senha) antes de publicar o site.
        db.execute(
            "INSERT INTO usuarios (login, nome, senha_hash, papel) VALUES ('admin', 'Administrador', ?, 'admin')",
            (generate_password_hash("1510"),),
        )
    db.commit()
    db.close()
