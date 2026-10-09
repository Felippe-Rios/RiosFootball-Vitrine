// Página de um time: banner nas cores do time e só as camisas dele. Código comum em comum.js
const raiz = $("time");
const idDoTime = Number(new URLSearchParams(location.search).get("id"));

(async () => {
  let times;
  try {
    await carregarProdutos();
    times = await (await fetch("/api/times")).json();
  } catch (e) {
    raiz.innerHTML = '<p class="vazio">Não foi possível carregar o time. O servidor Python está ligado?</p>';
    return;
  }
  const t = times.find((x) => x.id === idDoTime);
  if (!t) {
    raiz.innerHTML = '<p class="vazio">Time não encontrado. <a href="index.html">Voltar à vitrine</a></p>';
    return;
  }
  document.title = `${t.nome} | RiosFootball`;
  const camisas = produtos.filter((p) => p.time_id === t.id);

  raiz.innerHTML = `
    <section class="time-banner" style="--cor1:${esc(t.cor1 || "#d4a843")};--cor2:${esc(t.cor2 || "#0a0a0a")}">
      ${escudoHTML(t)}
      <div>
        <p class="cartao__modelo">${esc(t.categoria)}</p>
        <h1>${esc(t.nome)}</h1>
        <p>${camisas.length ? `${camisas.length} ${camisas.length === 1 ? "produto" : "produtos"} no site` : "Em breve por aqui"}</p>
      </div>
    </section>
    <section class="catalogo">
      ${camisas.length
        ? `<div class="grade">${camisas.map(cartaoHTML).join("")}</div>`
        : `<p class="vazio">Ainda não temos produtos do ${esc(t.nome)} no site. Chame a gente no WhatsApp para saber das novidades.</p>
           <p class="centro"><a class="botao botao--auto" href="https://wa.me/${WHATSAPP}" target="_blank" rel="noopener">Falar no WhatsApp</a></p>`}
    </section>`;
})();
