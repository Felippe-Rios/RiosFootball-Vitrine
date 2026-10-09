// Vitrine (página inicial): banner, filtros e cartões. O código comum fica em comum.js
// ===== 2. Banner =====
let slideAtual = 0, girar;

function mostrarSlide(i) {
  slideAtual = (i + banners.length) % banners.length;
  document.querySelectorAll(".slide").forEach((s, n) => s.classList.toggle("ativo", n === slideAtual));
  document.querySelectorAll(".pontos button").forEach((b, n) => b.setAttribute("aria-current", n === slideAtual));
}

function iniciarBanner() {
  const slides = banners.map((b) => {
    const fundo = b.fundo ? `style="background-image:linear-gradient(90deg,#000c,#0003),url('${b.fundo}')"` : "";
    return `<div class="slide" ${fundo}><p class="slide__titulo">${b.titulo}</p><p>${b.texto}</p></div>`;
  }).join("");
  const pontos = banners.map((_, i) => `<button type="button" data-i="${i}" aria-label="Ver destaque ${i + 1}"></button>`).join("");
  $("banner").innerHTML = slides + (banners.length > 1 ? `<div class="pontos">${pontos}</div>` : "");
  mostrarSlide(0);

  $("banner").addEventListener("click", (e) => {
    const b = e.target.closest("[data-i]");
    if (b) mostrarSlide(Number(b.dataset.i));
  });

  const semMovimento = matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (banners.length > 1 && !semMovimento) {
    const iniciar = () => { girar = setInterval(() => mostrarSlide(slideAtual + 1), 6000); };
    iniciar();
    $("banner").addEventListener("mouseenter", () => clearInterval(girar));
    $("banner").addEventListener("mouseleave", iniciar);
  }
}

// ===== Catálogo e filtros =====
function preencherFiltros() {
  const times = [...new Set(produtos.map((p) => p.time))].sort();
  const tamanhos = [...new Set(produtos.flatMap((p) => TAMANHOS[p.modelo]))];
  times.forEach((t) => $("filtro-time").add(new Option(t, t)));
  tamanhos.forEach((t) => $("filtro-tamanho").add(new Option(t, t)));
}

function desenhar(lista) {
  $("lista").innerHTML = lista.map(cartaoHTML).join("");
  $("vazio").hidden = lista.length > 0;
  $("contador").textContent = `${lista.length} camisa(s)`;
}

function filtrar() {
  const time = $("filtro-time").value;
  const tamanho = $("filtro-tamanho").value;
  desenhar(produtos.filter((p) =>
    (time === "" || p.time === time) && (tamanho === "" || TAMANHOS[p.modelo].includes(tamanho))));
}

$("filtro-time").addEventListener("change", filtrar);
$("filtro-tamanho").addEventListener("change", filtrar);
$("limpar").addEventListener("click", () => {
  $("filtro-time").value = "";
  $("filtro-tamanho").value = "";
  filtrar();
});

async function carregar() {
  try {
    await carregarProdutos();
  } catch (erro) {
    $("vazio").textContent = "Não foi possível carregar as camisas. O servidor Python está ligado?";
    $("vazio").hidden = false;
    return;
  }
  preencherFiltros();
  desenhar(produtos);
}

iniciarBanner();
carregar();
