
// Simple i18n
const I18N = {
  fr: {
    title: "EconoDeal – Les meilleures liquidations au Canada",
    subtitle: "Explorez les rabais de Walmart, Toys“R”Us, RONA – avec liens Amazon, eBay et Keepa.",
    search: "Rechercher un produit…",
    store: "Magasin",
    category: "Catégorie",
    minDiscount: "% rabais min",
    investorsTitle: "Espace Investisseur",
    investorsCopy: "EconoDeal construit la première plateforme canadienne de suivi des liquidations et de l'inventaire (style BrickSeek/Keepa), bilingue et multi‑magasins. Contactez‑nous pour le deck et le plan financier.",
    contact: "Nous joindre",
    viewAllRona: "Voir la galerie RONA",
    seeMore: "Voir plus"
  },
  en: {
    title: "EconoDeal – The best clearance deals in Canada",
    subtitle: "Browse deals from Walmart, Toys“R”Us, RONA — with Amazon, eBay and Keepa links.",
    search: "Search products…",
    store: "Store",
    category: "Category",
    minDiscount: "Min % off",
    investorsTitle: "Investor Space",
    investorsCopy: "EconoDeal is building the first Canadian clearance & inventory tracking platform (BrickSeek/Keepa-style), bilingual and multi‑retailer. Contact us for the deck and financials.",
    contact: "Contact",
    viewAllRona: "View RONA gallery",
    seeMore: "See more"
  }
};

let LANG = localStorage.getItem("lang") || "fr";
function t(key){ return I18N[LANG][key] || key }

// Data sources
const DS = {
  walmart: fetch("./data/walmart_clean.json").then(r => r.json()).catch(_ => []),
  toys: fetch("./data/toysrus_clean.json").then(r => r.json()).catch(_ => [])
};

function encode(q){ return encodeURIComponent(q || "") }
function linkAmazon(q){ return `https://www.amazon.ca/s?k=${encode(q)}` }
function linkEbay(q){ return `https://www.ebay.ca/sch/i.html?_nkw=${encode(q)}` }
function linkKeepa(q){ return `https://keepa.com/#!search/${encode(q)}` } // search fallback

function asNumber(s){
  if(!s) return null;
  const m = (s+"").replace(/[^\d.,]/g,"").replace(",",".").match(/[\d.]+/g);
  if(!m) return null;
  const n = parseFloat(m.join(""));
  return isNaN(n) ? null : n;
}
function discountPct(sale, reg){
  const a = asNumber(sale), b = asNumber(reg);
  if(a && b && b>0 && a<=b) return Math.round((1 - a/b) * 100);
  return null;
}

function renderUI(deals){
  // Elements
  const title = document.querySelector("[data-i18n=title]");
  const subtitle = document.querySelector("[data-i18n=subtitle]");
  const search = document.getElementById("search");
  const storeSel = document.getElementById("store");
  const catSel = document.getElementById("category");
  const minSel = document.getElementById("minpct");
  title.textContent = t("title");
  subtitle.textContent = t("subtitle");
  search.placeholder = t("search");
  document.querySelector("[for=store]").textContent = t("store");
  document.querySelector("[for=category]").textContent = t("category");
  document.querySelector("[for=minpct]").textContent = t("minDiscount");
  document.querySelector("[data-i18n=viewAllRona]").textContent = t("viewAllRona");
  document.querySelector("[data-i18n=investorsTitle]").textContent = t("investorsTitle");
  document.querySelector("[data-i18n=investorsCopy]").textContent = t("investorsCopy");

  // Populate store & category filters
  const stores = Array.from(new Set(deals.map(d=>d.store).filter(Boolean))).sort();
  storeSel.innerHTML = `<option value="">All</option>` + stores.map(s=>`<option>${s}</option>`).join("");

  const cats = Array.from(new Set(deals.map(d=>d.category || "Misc"))).sort();
  catSel.innerHTML = `<option value="">All</option>` + cats.map(c=>`<option>${c}</option>`).join("");

  function applyFilters(){
    const q = search.value.trim().toLowerCase();
    const store = storeSel.value;
    const cat = catSel.value;
    const min = parseInt(minSel.value||"0",10);
    const filtered = deals.filter(d=>{
      if (store && d.store!==store) return false;
      if (cat && (d.category||"")!==cat) return false;
      if (q && !(d.name||"").toLowerCase().includes(q)) return false;
      const pct = discountPct(d.price, d.regular_price) || 0;
      if (min && pct < min) return false;
      return true;
    });
    drawCards(filtered.slice(0, 500)); // render up to 500 for performance; they can refine filters
    document.getElementById("count").textContent = `${filtered.length} items`;
  }

  function drawCards(list){
    const grid = document.getElementById("grid");
    grid.innerHTML = "";
    for(const d of list){
      const pct = discountPct(d.price, d.regular_price);
      grid.insertAdjacentHTML("beforeend", `
        <article class="card">
          <a class="pic" href="${d.product_url||"#"}" target="_blank" rel="noopener">
            <img src="${d.image_url||""}" alt="${(d.name||"").replace(/"/g,'&quot;')}" loading="lazy">
            ${pct ? `<span class="tag">-${pct}%</span>` : ``}
          </a>
          <div class="info">
            <h4 class="title">${d.name||""}</h4>
            <div class="price"><span class="sale">${d.price||""}</span> <span class="reg">${d.regular_price||""}</span></div>
            <div class="meta">
              ${d.store?`<span class="badge">${d.store}</span>`:""}
              ${d.category?`<span class="badge">${d.category}</span>`:""}
              ${d.sku?`<span class="badge">SKU: ${d.sku}</span>`:""}
              ${d.availability?`<span class="badge">${d.availability}</span>`:""}
            </div>
            <div class="actions">
              <a href="${linkAmazon(d.sku||d.name)}" target="_blank" rel="noopener">Amazon</a>
              <a href="${linkEbay(d.sku||d.name)}" target="_blank" rel="noopener">eBay</a>
              <a href="${linkKeepa(d.sku||d.name)}" target="_blank" rel="noopener">Keepa</a>
            </div>
          </div>
        </article>
      `);
    }
  }

  // Wire filters
  ["input","change"].forEach(evt=>{
    search.addEventListener(evt, applyFilters);
    storeSel.addEventListener(evt, applyFilters);
    catSel.addEventListener(evt, applyFilters);
    minSel.addEventListener(evt, applyFilters);
  });

  applyFilters();
}

async function boot(){
  const deals = [...await DS.walmart, ...await DS.toys];
  renderUI(deals);
}
boot();

// Language switch
function setLang(l){
  LANG = l; localStorage.setItem("lang", l);
  document.querySelectorAll(".lang button").forEach(b=>b.classList.toggle("active", b.dataset.lang===l));
  // Update static strings
  document.querySelector("[data-i18n=title]").textContent = t("title");
  document.querySelector("[data-i18n=subtitle]").textContent = t("subtitle");
  document.querySelector("[data-i18n=viewAllRona]").textContent = t("viewAllRona");
  document.querySelector("[data-i18n=investorsTitle]").textContent = t("investorsTitle");
  document.querySelector("[data-i18n=investorsCopy]").textContent = t("investorsCopy");
}
document.addEventListener("DOMContentLoaded", ()=>{
  setLang(LANG);
  document.querySelectorAll(".lang button").forEach(b=>b.addEventListener("click", ()=>setLang(b.dataset.lang)));
});
