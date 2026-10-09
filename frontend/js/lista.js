// Lista de camisas: resultado de busca, kits infantis, conjuntos ou uma seção do menu (NBA, seleções...)
const raiz = $("lista-pagina");
const params = new URLSearchParams(location.search);
const busca = (params.get("q") || "").trim();
const modelo = params.get("modelo");
const secao = params.get("secao");

// Tira acentos e maiúsculas, para "Grêmio" e "gremio" serem a mesma busca
const norm = (s) => String(s).normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
const TITULOS = { "Kit infantil": "Kits infantis", "Conjunto": "Conjuntos", "Camisas de Time": "Camisas de time", "Seleções": "Camisas de seleção", "NBA": "NBA" };

(async () => {
  try {
    await carregarProdutos();
  } catch (e) {
    raiz.innerHTML = '<p class="vazio">Não foi possível carregar as camisas. O servidor Python está ligado?</p>';
    return;
  }
  let lista = produtos;
  let titulo = "Todas as camisas";
  if (modelo) { lista = lista.filter((p) => p.modelo === modelo); titulo = TITULOS[modelo] || modelo; }
  if (secao) { lista = lista.filter((p) => p.secao === secao); titulo = TITULOS[secao] || secao; }
  if (busca) {
    const palavras = norm(busca).split(/\s+/).filter(Boolean);
    lista = lista.filter((p) => {
      const texto = norm(`${nomeDaCamisa(p)} ${p.categoria} ${p.modelo}`);
      return palavras.every((w) => texto.includes(w));
    });
    titulo = `Resultados para "${busca}"`;
  }
  document.title = `${titulo} | RiosFootball`;
  raiz.innerHTML = `
    <section class="catalogo">
      <h1 class="titulo-pagina">${esc(titulo)}</h1>
      <p class="contador">${lista.length} ${lista.length === 1 ? "produto" : "produtos"}</p>
      ${lista.length
        ? `<div class="grade">${lista.map(cartaoHTML).join("")}</div>`
        : `<p class="vazio">Nada encontrado por aqui. Tente outra busca ou chame a gente no WhatsApp.</p>
           <p class="centro"><a class="botao botao--auto" href="https://wa.me/${WHATSAPP}" target="_blank" rel="noopener">Falar no WhatsApp</a></p>`}
    </section>`;
})();
