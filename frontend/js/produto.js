// Página do produto: galeria, abas, avaliações e recomendações. O código comum fica em comum.js
const raiz = $("produto");
const idDaCamisa = Number(new URLSearchParams(location.search).get("id"));
let produtoAtual = null;
let notaEscolhida = 0;

// Guia de tamanhos adulto (tabela da loja). Os tamanhos 2GG, 3GG e 4GG aparecem como 2XL, 3XL e 4XL.
const MEDIDAS = [
  ["P", "160 - 165", "49 - 51", "68 - 70", "50 - 62"],
  ["M", "165 - 170", "51 - 53", "70 - 72", "62 - 70"],
  ["G", "170 - 175", "53 - 55", "72 - 74", "71 - 75"],
  ["GG", "177 - 180", "55 - 57", "74 - 77", "76 - 80"],
  ["2XL (2GG)", "180 - 185", "57 - 59", "77 - 79", "81 - 89"],
  ["3XL (3GG)", "185 - 190", "59 - 61", "79 - 82", "90 - 96"],
  ["4XL (4GG)", "190 - 195", "61 - 64", "82 - 85", "97 - 103"],
];

async function iniciar() {
  try {
    await carregarProdutos();
  } catch (e) {
    raiz.innerHTML = '<p class="vazio">Não foi possível carregar a camisa. O servidor Python está ligado?</p>';
    return;
  }
  produtoAtual = produtos.find((p) => p.id === idDaCamisa);
  if (!produtoAtual) {
    raiz.innerHTML = '<p class="vazio">Esta camisa não está disponível. <a href="index.html">Voltar à vitrine</a></p>';
    return;
  }
  document.title = `${nomeDaCamisa(produtoAtual)} | RiosFootball`;
  desenharProduto(produtoAtual);
  carregarAvaliacoes(produtoAtual);
  desenharRecomendacoes(produtoAtual);
}

function desenharProduto(p) {
  const guia = ["Torcedor", "Jogador"].includes(p.modelo)
    ? `<div class="tabela-wrap"><table class="medidas">
         <thead><tr><th>Tamanho</th><th>Altura (cm)</th><th>Busto (cm)</th><th>Comprimento (cm)</th><th>Peso (kg)</th></tr></thead>
         <tbody>${MEDIDAS.map((l) => `<tr>${l.map((c) => `<td>${c}</td>`).join("")}</tr>`).join("")}</tbody>
       </table></div><p class="dica">Medidas aproximadas. Em dúvida entre dois tamanhos, chame a gente no WhatsApp.</p>`
    : `<p>A tabela de medidas deste modelo estará disponível em breve. Chame a gente no WhatsApp que ajudamos a escolher o tamanho.</p>`;

  raiz.innerHTML = `
    <nav class="trilha" aria-label="Você está em"><a href="index.html">Início</a> / ${esc(p.time)} / ${esc(nomeDaCamisa(p))}</nav>

    <div class="produto__topo">
      <div class="galeria">
        <div id="foto-grande">${foto(p, p.fotos[0])}</div>
        <div class="miniaturas">${p.fotos.length > 1 ? p.fotos.map((f, i) =>
          `<button type="button" data-foto="${esc(f)}" aria-label="Ver foto ${i + 1}">${foto(p, f)}</button>`).join("") : ""}</div>
      </div>

      <div class="produto__info">
        <span class="cartao__modelo">${esc(p.modelo)}${p.lancamento ? ' <b class="selo">Lançamento</b>' : ""}</span>
        <h1>${esc(nomeDaCamisa(p))}</h1>
        <a class="nota" href="#" id="nota-topo" data-abrir="avaliacoes">Sem avaliações ainda</a>
        <p class="preco-grande">${real(p.preco)}</p>
        <p class="parcela">Parcele em até 12x no cartão de crédito. Aceitamos também Pix e cartão de débito.</p>
        <fieldset class="tamanhos">
          <legend>Tamanho <button type="button" class="link" data-abrir="guia">Guia de tamanhos</button></legend>
          ${TAMANHOS[p.modelo].map((t) => `<label><input type="radio" name="tam" value="${t}"><span>${t}</span></label>`).join("")}
        </fieldset>
        <p class="erro" hidden>Escolha um tamanho para continuar.</p>
        <button class="botao" type="button" id="adicionar">Adicionar ao carrinho</button>
        <ul class="vantagens">
          <li>Entrega em BH, Contagem e região</li>
          <li>Envio para todo o Brasil pelos Correios</li>
          <li>Atendimento no WhatsApp de segunda a sexta</li>
        </ul>
      </div>
    </div>

    <div class="abas abas--produto" role="tablist">
      <button type="button" role="tab" data-aba="descricao" aria-selected="true">Descrição</button>
      <button type="button" role="tab" data-aba="avaliacoes" aria-selected="false">Avaliações <span id="qtd-aval">(0)</span></button>
      <button type="button" role="tab" data-aba="guia" aria-selected="false">Guia de tamanhos</button>
      <button type="button" role="tab" data-aba="entrega" aria-selected="false">Entrega e suporte</button>
    </div>

    <section class="aba-conteudo" id="aba-descricao">
      <h2>Sobre esta camisa</h2>
      ${p.detalhes ? `<p class="destaque-texto">${esc(p.detalhes)}</p>` : ""}
      <p>Camisa 100% poliéster, em tecido leve e respirável que ajuda a manter o suor longe da pele e se ajusta bem ao corpo. É um material que não encolhe nem deforma com facilidade, ótimo para usar nos jogos, nos treinos ou no dia a dia.</p>
      <p>Mais do que uma peça de roupa, a camisa do seu time é uma forma de mostrar a sua paixão e fazer parte da torcida onde você for.</p>
      <p>Quer personalizar com nome e número? Combine com a gente pelo WhatsApp.</p>
    </section>

    <section class="aba-conteudo" id="aba-avaliacoes" hidden><div id="avaliacoes">Carregando avaliações...</div></section>

    <section class="aba-conteudo" id="aba-guia" hidden><h2>Guia de tamanhos</h2>${guia}</section>

    <section class="aba-conteudo" id="aba-entrega" hidden>
      <h2>Entrega e suporte</h2>
      <p><strong>Belo Horizonte, Contagem e região:</strong> entregamos na hora ou levamos até você, inclusive por Uber.</p>
      <p><strong>Todo o Brasil:</strong> enviamos pelos Correios (Sedex, PAC ou mini envios).</p>
      <p><strong>Pagamento:</strong> Pix, cartão de débito e cartão de crédito, parcelado em até 12x.</p>
      <p><strong>Trocas:</strong> fazemos a troca. É só chamar a gente no WhatsApp.</p>
      <p><strong>Atendimento:</strong> suporte pelo WhatsApp, de segunda a sexta, antes e depois da compra.</p>
      <p><a class="botao botao--auto" href="https://wa.me/${WHATSAPP}" target="_blank" rel="noopener">Falar no WhatsApp</a></p>
    </section>

    <section id="recomendacoes" class="recomendacoes"></section>`;
}

function abrirAba(nome, rolar) {
  raiz.querySelectorAll("[data-aba]").forEach((b) => b.setAttribute("aria-selected", b.dataset.aba === nome));
  raiz.querySelectorAll(".aba-conteudo").forEach((s) => { s.hidden = s.id !== "aba-" + nome; });
  if (rolar) raiz.querySelector(".abas--produto").scrollIntoView({ behavior: "smooth", block: "start" });
}

raiz.addEventListener("click", (e) => {
  const abrir = e.target.closest("[data-abrir]");
  if (abrir) { e.preventDefault(); return abrirAba(abrir.dataset.abrir, true); }
  const aba = e.target.closest("[data-aba]");
  if (aba) return abrirAba(aba.dataset.aba, false);

  const mini = e.target.closest("[data-foto]");
  if (mini) $("foto-grande").innerHTML = foto(produtoAtual, mini.dataset.foto);

  const estrela = e.target.closest("[data-n]");
  if (estrela) {
    notaEscolhida = Number(estrela.dataset.n);
    raiz.querySelectorAll("[data-n]").forEach((b) => b.classList.toggle("ativa", Number(b.dataset.n) <= notaEscolhida));
  }

  if (e.target.closest("#adicionar")) {
    const tamanho = raiz.querySelector("input[name=tam]:checked");
    const aviso = raiz.querySelector(".produto__info .erro");
    aviso.hidden = !!tamanho;
    if (tamanho) adicionar(produtoAtual.id, tamanho.value);
  }
});

// ----- avaliações -----
const itemAvaliacao = (a) => `
  <article class="avaliacao">
    <header><span class="estrelas">${estrelas(a.nota)}</span> <strong>${esc(a.autor)}</strong>
      <small>${new Date(a.criado_em).toLocaleDateString("pt-BR")}</small></header>
    ${a.texto ? `<p>${esc(a.texto)}</p>` : ""}
    <div class="midias">${a.midias.map((m) => m.tipo === "video"
      ? `<video controls preload="metadata" src="${esc(m.arquivo)}"></video>`
      : `<a href="${esc(m.arquivo)}" target="_blank" rel="noopener"><img src="${esc(m.arquivo)}" alt="Foto da avaliação" loading="lazy"></a>`).join("")}</div>
  </article>`;

const formularioAvaliacao = `
  <form id="form-avaliacao" class="form">
    <h3>Avalie esta camisa</h3>
    <div class="estrelas-input" role="group" aria-label="Nota">
      ${[1, 2, 3, 4, 5].map((n) => `<button type="button" data-n="${n}" aria-label="${n} estrela(s)">★</button>`).join("")}
    </div>
    <label>Conte como foi <textarea name="texto" rows="4" maxlength="1000"></textarea></label>
    <label>Fotos (até 5) <input type="file" name="fotos" accept="image/png,image/jpeg,image/webp" multiple></label>
    <label>Vídeo (1 vídeo, até 50 MB) <input type="file" name="video" accept="video/mp4,video/quicktime,video/webm"></label>
    <p class="erro" hidden></p>
    <button class="botao" type="submit">Enviar avaliação</button>
  </form>`;

async function carregarAvaliacoes(p) {
  const caixa = $("avaliacoes");
  let d;
  try {
    d = await (await fetch(`/api/produtos/${p.id}/avaliacoes`)).json();
  } catch (e) {
    caixa.textContent = "Não foi possível carregar as avaliações.";
    return;
  }
  $("qtd-aval").textContent = `(${d.total})`;
  $("nota-topo").innerHTML = d.total
    ? `<span class="estrelas">${estrelas(d.media)}</span> ${String(d.media).replace(".", ",")} <small>(${d.total} avaliações)</small>`
    : "Sem avaliações ainda";

  caixa.innerHTML = `
    <h2>Avaliações dos clientes</h2>
    ${d.total ? `<p class="resumo"><span class="estrelas">${estrelas(d.media)}</span> ${String(d.media).replace(".", ",")} de 5 <small>(${d.total})</small></p>` : ""}
    ${d.pode_avaliar ? formularioAvaliacao
      : `<p class="dica">${esc(d.motivo)} ${d.motivo.startsWith("Entre") ? '<a href="conta.html">Entrar agora</a>' : ""}</p>`}
    ${d.avaliacoes.map(itemAvaliacao).join("") || '<p class="vazio">Ainda não há avaliações desta camisa.</p>'}`;

  const form = $("form-avaliacao");
  if (form) form.addEventListener("submit", (e) => enviarAvaliacao(e, p));
}

async function enviarAvaliacao(e, p) {
  e.preventDefault();
  const form = e.target;
  const aviso = form.querySelector(".erro");
  const mostrarErro = (t) => { aviso.textContent = t; aviso.hidden = false; };
  aviso.hidden = true;
  if (!notaEscolhida) return mostrarErro("Escolha de 1 a 5 estrelas.");
  if (form.fotos.files.length > 5) return mostrarErro("Envie no máximo 5 fotos.");
  if (form.video.files[0] && form.video.files[0].size > 50 * 1024 * 1024) return mostrarErro("O vídeo pode ter no máximo 50 MB.");

  const dados = new FormData(form);
  dados.set("nota", notaEscolhida);
  const botao = form.querySelector("button[type=submit]");
  botao.disabled = true;
  botao.textContent = "Enviando...";
  try {
    const resposta = await fetch(`/api/produtos/${p.id}/avaliacoes`, {
      method: "POST", headers: { "X-Requested-With": "fetch" }, body: dados,
    });
    const r = await resposta.json().catch(() => ({}));
    if (!resposta.ok) throw new Error(r.erro || "Não foi possível enviar.");
    notaEscolhida = 0;
    await carregarAvaliacoes(p);
    avisar("Avaliação enviada. Obrigado!");
  } catch (erro) {
    mostrarErro(erro.message);
    botao.disabled = false;
    botao.textContent = "Enviar avaliação";
  }
}

// ----- recomendações -----
function desenharRecomendacoes(p) {
  const mesmoTime = produtos.filter((x) => x.id !== p.id && x.time === p.time).slice(0, 4);
  const usados = new Set([p.id, ...mesmoTime.map((x) => x.id)]);
  const outras = produtos.filter((x) => !usados.has(x.id) && (x.modelo === p.modelo || x.lancamento)).slice(0, 4);
  const bloco = (titulo, lista) => lista.length
    ? `<h2>${titulo}</h2><div class="grade">${lista.map(cartaoHTML).join("")}</div>` : "";
  $("recomendacoes").innerHTML = bloco(`Mais camisas do ${esc(p.time)}`, mesmoTime) + bloco("Você também pode gostar", outras);
}

iniciar();
