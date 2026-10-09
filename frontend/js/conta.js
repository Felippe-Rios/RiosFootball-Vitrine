const $ = (id) => document.getElementById(id);
const real = (v) => v.toLocaleString("pt-BR", { style: "currency", currency: "BRL" });
// Protege a pagina: transforma < e > em texto comum, para ninguem injetar codigo pelo nome, por exemplo
const esc = (t) => String(t).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

async function api(url, corpo) {
  const opcoes = corpo === undefined ? {} : {
    method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpo),
  };
  const resposta = await fetch(url, opcoes);
  const dados = await resposta.json().catch(() => ({}));
  if (!resposta.ok) throw new Error(dados.erro || "Algo deu errado. Tente de novo.");
  return dados;
}

// ----- abas Entrar / Criar conta -----
document.querySelectorAll("[data-aba]").forEach((b) => b.addEventListener("click", () => {
  document.querySelectorAll("[data-aba]").forEach((x) => x.setAttribute("aria-selected", x === b));
  $("form-entrar").hidden = b.dataset.aba !== "entrar";
  $("form-criar").hidden = b.dataset.aba !== "criar";
}));

// Vindo do carrinho (?voltar), ja abre o login para a pessoa nao precisar clicar
if (new URLSearchParams(location.search).has("voltar")) document.querySelector('[data-aba="entrar"]').click();

// ----- envio dos formularios -----
function ligarFormulario(form, url) {
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    const msg = form.querySelector(".erro");
    msg.hidden = true;
    try {
      entrou(await api(url, Object.fromEntries(new FormData(form))));
    } catch (erro) {
      msg.textContent = erro.message;
      msg.hidden = false;
    }
  });
}
ligarFormulario($("form-entrar"), "/api/login");
ligarFormulario($("form-criar"), "/api/cadastro");

function entrou(usuario) {
  if (usuario.papel === "admin") { location.href = "/admin"; return; }
  if (usuario.telefone_pendente) {  // veio pelo Google e ainda nao informou o telefone
    $("visitante").hidden = true;
    $("completar").hidden = false;
    return;
  }
  if (new URLSearchParams(location.search).has("voltar")) { location.href = "index.html"; return; }
  $("visitante").hidden = true;
  $("logado").hidden = false;
  $("ola").textContent = `Olá, ${usuario.nome.split(" ")[0]}!`;
  carregarPedidos();
}

async function carregarPedidos() {
  const pedidos = await api("/api/meus-pedidos");
  $("pedidos").innerHTML = pedidos.length ? pedidos.map((p) => `
    <article class="pedido">
      <header><strong>Pedido nº ${p.id}</strong><span class="status">${esc(p.status)}</span></header>
      <ul>${p.itens.map((i) => `<li>${i.qtd}x ${esc(i.nome)}, tam. ${esc(i.tamanho)}</li>`).join("")}</ul>
      <p>Total: <strong>${real(p.total)}</strong> <small>${new Date(p.criado_em).toLocaleString("pt-BR")}</small></p>
    </article>`).join("") : '<p class="vazio">Você ainda não fez nenhum pedido.</p>';
}

$("sair").addEventListener("click", async () => { await api("/api/logout", {}); location.href = "index.html"; });

// Se ja estiver logado, vai direto para a area certa
(async () => {
  try {
    const eu = await api("/api/eu");
    if (eu.logado) entrou(eu);
  } catch {}
})();

// ----- completar o cadastro (telefone) -----
$("form-completar").addEventListener("submit", async (e) => {
  e.preventDefault();
  const msg = e.target.querySelector(".erro");
  msg.hidden = true;
  try {
    await api("/api/completar-cadastro", Object.fromEntries(new FormData(e.target)));
    $("completar").hidden = true;
    entrou(await api("/api/eu"));
  } catch (erro) {
    msg.textContent = erro.message;
    msg.hidden = false;
  }
});

// ----- entrar com Google -----
const carregarScript = (src) => new Promise((ok, falha) => {
  const s = document.createElement("script");
  s.src = src; s.async = true; s.onload = ok; s.onerror = falha;
  document.head.appendChild(s);
});

async function aoReceberGoogle(resposta) {
  const aviso = $("erro-google");
  aviso.hidden = true;
  try {
    entrou(await api("/api/login-google", { credential: resposta.credential }));
  } catch (erro) {
    aviso.textContent = erro.message;
    aviso.hidden = false;
  }
}

async function iniciarGoogle() {
  try {
    const { client_id } = await api("/api/google-config");
    if (!client_id) return;  // ainda nao configurado: o botao nem aparece
    await carregarScript("https://accounts.google.com/gsi/client");
    google.accounts.id.initialize({ client_id, callback: aoReceberGoogle });
    google.accounts.id.renderButton($("botao-google"), {
      theme: "filled_black", size: "large", shape: "pill", text: "continue_with", locale: "pt-BR", width: 320,
    });
    $("google").hidden = false;
  } catch (e) { /* sem internet ou bloqueado: o login normal continua funcionando */ }
}
iniciarGoogle();
