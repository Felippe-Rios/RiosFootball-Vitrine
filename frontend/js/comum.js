// Código compartilhado pela vitrine (index.html) e pela página do produto (produto.html)
// ===== 1. Funções auxiliares =====
const $ = (id) => document.getElementById(id);
const real = (v) => v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
const nomeDaCamisa = (p) => `${p.modelo === "Conjunto" ? "Conjunto" : "Camisa"} ${p.time} ${p.versao} ${p.temporada}`;
const sigla = (p) => p.time.slice(0, 3).toUpperCase();

// As camisas chegam do servidor Python (banco de dados) pela função carregar()
let produtos = [];

// Mostra a foto; se o arquivo não existir, aparece a sigla do time no lugar
function foto(p, arquivo) {
  const img = arquivo
    ? `<img src="${arquivo}" alt="${esc(nomeDaCamisa(p))}" loading="lazy" onerror="this.hidden=true">`
    : "";
  return `<span class="foto" data-sigla="${sigla(p)}">${img}</span>`;
}

// ===== Peças usadas na vitrine e na página do produto =====
const esc = (t) => String(t ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const estrelas = (n) => "★".repeat(Math.round(n)) + "☆".repeat(5 - Math.round(n));

// O cartão da camisa é um link para a página do produto
const cartaoHTML = (p) => `
  <a class="cartao" href="produto.html?id=${p.id}">
    ${foto(p, p.fotos[0])}
    <span class="cartao__corpo">
      <span class="cartao__modelo">${esc(p.modelo)}${p.lancamento ? ' <b class="selo">Lançamento</b>' : ""}</span>
      <span class="cartao__nome">${esc(nomeDaCamisa(p))}</span>
      ${p.avaliacoes ? `<span class="nota"><span class="estrelas">${estrelas(p.nota)}</span> <small>(${p.avaliacoes})</small></span>` : ""}
      <span class="cartao__preco">${real(p.preco)}</span>
      <span class="cartao__tamanhos">Tamanhos: ${TAMANHOS[p.modelo].join(", ")}</span>
    </span>
  </a>`;

// Busca as camisas no servidor Python (rota /api/produtos)
async function carregarProdutos() {
  const resposta = await fetch("/api/produtos");
  if (!resposta.ok) throw new Error(resposta.status);
  produtos = await resposta.json();
  carrinho = carrinho.filter((i) => produtos.some((p) => p.id === i.id));
  salvar();
}

// ===== Cabeçalho com busca e menu de times (montado aqui para ser igual em todas as páginas) =====
const NOMES_MENU = { "Camisas de Time": "Camisas de Time", "Seleções": "Camisas de Seleção", "NBA": "NBA" };

function escudoHTML(t) {
  return t.escudo
    ? `<img class="escudo" src="${esc(t.escudo)}" alt="" loading="lazy">`
    : `<span class="escudo escudo--sigla">${esc(t.nome.slice(0, 3).toUpperCase())}</span>`;
}

function montarCabecalho() {
  const alvo = document.getElementById("cabecalho");
  if (!alvo) return;
  const q = new URLSearchParams(location.search).get("q") || "";
  const painel = (secao) => `
    <li class="menu__item">
      <button type="button" class="menu__botao" data-secao="${secao}" aria-expanded="false">${NOMES_MENU[secao]} <span aria-hidden="true">▾</span></button>
      <div class="mega" hidden></div>
    </li>`;
  alvo.innerHTML = `
    <div class="topo__linha">
      <a href="index.html" class="topo__marca"><img src="imagens/logo.png" alt="RiosFootball" width="56" height="56"><span>Rios<b>Football</b></span></a>
      <form class="busca" role="search" action="lista.html">
        <input type="search" name="q" value="${esc(q)}" placeholder="O que você está buscando?" aria-label="Buscar camisas">
        <button type="submit" aria-label="Buscar"><svg width="26" height="26" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="10.5" cy="10.5" r="7"/><path d="M16 16l5 5"/></svg></button>
      </form>
      <div class="topo__acoes">
        <a id="link-conta" class="icone" href="conta.html" title="Minha conta" aria-label="Minha conta">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><circle cx="12" cy="8" r="4"/><path d="M4 21c0-4.4 3.6-7 8-7s8 2.6 8 7"/></svg>
        </a>
        <button id="abrir-carrinho" type="button" class="icone" title="Meu carrinho" aria-label="Meu carrinho">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M2 3h3l2.6 12.2a1.5 1.5 0 0 0 1.5 1.2h8.8a1.5 1.5 0 0 0 1.5-1.1L21 7H6"/><circle cx="9.5" cy="20" r="1.4"/><circle cx="17.5" cy="20" r="1.4"/></svg>
          <span id="qtd-carrinho" class="icone__selo">0</span>
        </button>
      </div>
    </div>
    <nav class="menu" aria-label="Principal">
      <button type="button" class="menu__toggle" aria-expanded="false" aria-controls="menu-lista">Menu ☰</button>
      <ul id="menu-lista">
        <li><a href="index.html">Início</a></li>
        ${painel("Camisas de Time")}
        ${painel("Seleções")}
        <li><a href="lista.html?modelo=Kit%20infantil">Kits Infantis</a></li>
        ${painel("NBA")}
        <li><a href="lista.html?modelo=Conjunto">Conjuntos</a></li>
      </ul>
    </nav>`;
  ligarMenu();
  carregarMenu();
}

// Preenche cada painel com os times da seção, em colunas por liga
async function carregarMenu() {
  let times;
  try { times = await (await fetch("/api/times")).json(); } catch (e) { return; }
  document.querySelectorAll(".menu__botao").forEach((botao) => {
    const secao = botao.dataset.secao;
    const ligas = {};
    times.filter((t) => t.secao === secao).forEach((t) => (ligas[t.categoria] ||= []).push(t));
    const ordem = Object.keys(ligas).sort((a, b) =>
      a === "Brasileirão" ? -1 : b === "Brasileirão" ? 1 : a.localeCompare(b, "pt-BR"));
    const colunas = ordem.map((liga) => `
      <div class="mega__col"><h3>${esc(liga)}</h3>
        ${ligas[liga].map((t) => `<a href="time.html?id=${t.id}">${escudoHTML(t)}<span>${esc(t.nome)}</span></a>`).join("")}
      </div>`).join("");
    botao.nextElementSibling.innerHTML = (colunas || '<p class="dica">Em breve.</p>') +
      `<a class="mega__todas" href="lista.html?secao=${encodeURIComponent(secao)}">Ver todas as camisas</a>`;
  });
}

function ligarMenu() {
  const fechar = () => document.querySelectorAll(".menu__botao").forEach((b) => {
    b.setAttribute("aria-expanded", "false");
    b.nextElementSibling.hidden = true;
  });
  const abrir = (botao) => { botao.setAttribute("aria-expanded", "true"); botao.nextElementSibling.hidden = false; };
  const comMouse = () => matchMedia("(hover: hover) and (min-width: 801px)").matches;

  document.querySelectorAll(".menu__item").forEach((item) => {
    item.addEventListener("mouseenter", () => { if (comMouse()) { fechar(); abrir(item.firstElementChild); } });
    item.addEventListener("mouseleave", () => { if (comMouse()) fechar(); });
  });
  document.addEventListener("click", (e) => {
    const toggle = e.target.closest(".menu__toggle");
    if (toggle) {
      const aberto = toggle.parentElement.classList.toggle("aberto");
      toggle.setAttribute("aria-expanded", aberto);
      return;
    }
    const botao = e.target.closest(".menu__botao");
    const jaAberto = botao && botao.getAttribute("aria-expanded") === "true";
    if (!e.target.closest(".mega")) fechar();
    if (botao && !jaAberto) abrir(botao);
  });
  document.addEventListener("keydown", (e) => { if (e.key === "Escape") fechar(); });
}

montarCabecalho();

// ===== 5. Carrinho (fica salvo no navegador com localStorage) =====
let carrinho = [];
try { carrinho = JSON.parse(localStorage.getItem("carrinho-rios")) || []; } catch { carrinho = []; }

function salvar() {
  try { localStorage.setItem("carrinho-rios", JSON.stringify(carrinho)); } catch {}
  $("qtd-carrinho").textContent = carrinho.reduce((soma, i) => soma + i.qtd, 0);
}

let tempoAviso;
function avisar(texto) {
  $("aviso").textContent = texto;
  $("aviso").classList.add("visivel");
  clearTimeout(tempoAviso);
  tempoAviso = setTimeout(() => $("aviso").classList.remove("visivel"), 2500);
}

function adicionar(id, tamanho) {
  const item = carrinho.find((i) => i.id === id && i.tamanho === tamanho);
  if (item) item.qtd++; else carrinho.push({ id, tamanho, qtd: 1 });
  salvar();
  avisar("Adicionado ao carrinho");
}

function desenharCarrinho() {
  const itens = carrinho.map((i, n) => ({ ...i, n, p: produtos.find((x) => x.id === i.id) }));
  const total = itens.reduce((soma, i) => soma + i.p.preco * i.qtd, 0);

  const linhas = itens.map((i) => `
    <li class="linha">
      <div><strong>${nomeDaCamisa(i.p)}</strong><span>${i.p.modelo}, tamanho ${i.tamanho}</span></div>
      <strong>${real(i.p.preco * i.qtd)}</strong>
      <div class="qtd">
        <button type="button" data-acao="menos" data-n="${i.n}" aria-label="Diminuir">-</button>
        <span>${i.qtd}</span>
        <button type="button" data-acao="mais" data-n="${i.n}" aria-label="Aumentar">+</button>
      </div>
    </li>`).join("");

  $("modal-carrinho").innerHTML = `
    <div class="carrinho">
      <button class="fechar" type="button" data-fechar aria-label="Fechar">&times;</button>
      <h2>Seu carrinho</h2>
      ${itens.length
        ? `<ul>${linhas}</ul>
           <p class="total"><span>Total</span><strong>${real(total)}</strong></p>
           <button class="botao" type="button" data-pedir>Pedir pelo WhatsApp</button>
           <p class="erro" hidden></p>`
        : `<p class="vazio">Seu carrinho está vazio. Escolha uma camisa para começar.</p>`}
    </div>`;
}

$("abrir-carrinho").addEventListener("click", () => { desenharCarrinho(); $("modal-carrinho").showModal(); });

$("modal-carrinho").addEventListener("click", (e) => {
  const m = e.currentTarget;
  if (e.target === m || e.target.closest("[data-fechar]")) return m.close();
  if (e.target.closest("[data-pedir]")) return fazerPedido(m);
  const b = e.target.closest("[data-acao]");
  if (!b) return;
  const n = Number(b.dataset.n);
  if (b.dataset.acao === "mais") carrinho[n].qtd++;
  else if (--carrinho[n].qtd <= 0) carrinho.splice(n, 1);
  salvar();
  desenharCarrinho();
});

// Cria o pedido no servidor (exige login) e so entao abre o WhatsApp com o numero do pedido
async function fazerPedido(m) {
  const erro = m.querySelector(".erro");
  const botao = m.querySelector("[data-pedir]");
  erro.hidden = true;
  const aba = window.open("", "_blank"); // abre ja, para o navegador nao bloquear o WhatsApp
  botao.disabled = true;
  try {
    const resposta = await fetch("/api/pedidos", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ itens: carrinho.map(({ id, tamanho, qtd }) => ({ id, tamanho, qtd })) }),
    });
    if (resposta.status === 401) { if (aba) aba.close(); location.href = "conta.html?voltar=1"; return; }
    const pedido = await resposta.json();
    if (resposta.status === 403 && pedido.telefone_pendente) {  // conta do Google sem telefone ainda
      if (aba) aba.close();
      location.href = "conta.html?voltar=1";
      return;
    }
    if (!resposta.ok) throw new Error(pedido.erro);

    const texto = `Olá! Acabei de fazer o pedido nº ${pedido.numero} no site:\n` +
      pedido.itens.map((i) => `- ${i.qtd}x ${i.nome}, tam. ${i.tamanho}`).join("\n") +
      `\nTotal: ${real(pedido.total)}`;
    const link = `https://wa.me/${WHATSAPP}?text=${encodeURIComponent(texto)}`;
    if (aba) aba.location = link; else location.href = link;

    carrinho = [];
    salvar();
    m.close();
    avisar(`Pedido nº ${pedido.numero} criado. Acompanhe em Minha conta.`);
  } catch (e) {
    if (aba) aba.close();
    erro.textContent = e.message || "Não foi possível enviar o pedido.";
    erro.hidden = false;
  } finally {
    botao.disabled = false;
  }
}

// Troca "Minha conta" por "Painel" quando quem entrou e o dono
async function verificarSessao() {
  try {
    const eu = await (await fetch("/api/eu")).json();
    if (!eu.logado) return;
    const link = $("link-conta");
    const nome = eu.papel === "admin" ? "Painel do dono" : `Minha conta (${eu.nome.split(" ")[0]})`;
    link.title = nome;                        // o ícone não tem texto: o nome fica no balãozinho
    link.setAttribute("aria-label", nome);
    link.href = eu.papel === "admin" ? "/admin" : "conta.html";
    link.classList.add("logado");             // aparece uma bolinha dourada no ícone
  } catch {}
}

verificarSessao();
