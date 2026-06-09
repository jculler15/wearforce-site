/* ============================================================
   THE WEARFORCE — storefront logic
   Loads products from data/products.json (Phase 2: auto-generated
   from eBay) and renders the grid + product detail pages.
   ============================================================ */

/* ---- Placeholder artwork (until real eBay photos in Phase 2) ---- */
function sneakerIcon(color) {
  return `<svg viewBox="0 0 64 40" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <path d="M3 27c0-2 1-3 3-3 6 0 9-2 13-6 3-3 5-6 8-6 2 0 3 1 4 3l2 4c1 2 3 3 6 4l11 3c4 1 6 3 6 6 0 2-1 3-4 3H7c-3 0-4-1-4-4v-4z" fill="${color}"/>
    <path d="M6 31h52" stroke="rgba(0,0,0,.18)" stroke-width="2" stroke-linecap="round"/>
    <path d="M28 19l3 5M33 16l3 6M38 15l3 6" stroke="rgba(255,255,255,.55)" stroke-width="2" stroke-linecap="round"/>
  </svg>`;
}
function shirtIcon(color) {
  return `<svg viewBox="0 0 64 56" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <path d="M24 6l8 6 8-6 9 5 6 9-7 6-2-3v22a3 3 0 0 1-3 3H23a3 3 0 0 1-3-3V23l-2 3-7-6 6-9 9-5z" fill="${color}"/>
    <path d="M24 6c0 4 3.6 7 8 7s8-3 8-7" stroke="rgba(255,255,255,.5)" stroke-width="2.4" stroke-linecap="round"/>
  </svg>`;
}
function cardIcon(color) {
  return `<svg viewBox="0 0 56 64" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
    <rect x="8" y="6" width="40" height="52" rx="5" fill="${color}"/>
    <rect x="14" y="12" width="28" height="22" rx="3" fill="rgba(255,255,255,.85)"/>
    <path d="M28 38l2.3 4.7 5.2.8-3.8 3.6.9 5.1-4.6-2.4-4.6 2.4.9-5.1-3.8-3.6 5.2-.8L28 38z" fill="rgba(255,255,255,.85)"/>
  </svg>`;
}

const SNEAKER_TINT = {
  Jordan: ["#f2d7d9", "#E11B22"],
  Nike: ["#dfe4ef", "#1a1a1a"],
  Adidas: ["#dde0e6", "#1a1a1a"],
  "New Balance": ["#dde7e0", "#2f7d4f"],
  default: ["#e6e6ea", "#9a9aa3"]
};

// Returns [backgroundTint, iconColor, iconFn] for a product's placeholder.
function artFor(item) {
  if (item.category === "Apparel") return ["#e7eaf0", "#5b6473", shirtIcon];
  if (item.category === "Cards") return ["#f1ead7", "#c1992f", cardIcon];
  const t = SNEAKER_TINT[item.brand] || SNEAKER_TINT.default;
  return [t[0], t[1], sneakerIcon];
}

// Inner media element: real photo when present, else styled placeholder.
function mediaInner(item) {
  if (item.image) return `<img src="${item.image}" alt="${item.title}" loading="lazy">`;
  const [tint, ink, icon] = artFor(item);
  return `<div class="ph" style="background:linear-gradient(135deg, ${tint}, #fff)">${icon(ink)}</div>`;
}

// Meta line under a title: cards have no size, so show set/grade only.
function metaText(item) {
  if (item.category === "Cards") return item.colorway || "";
  const parts = [];
  if (item.size) parts.push("Size " + item.size);
  if (item.colorway) parts.push(item.colorway);
  return parts.join(" · ");
}

function money(value, currency) {
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency", currency: currency || "USD", maximumFractionDigits: 0
    }).format(value);
  } catch (e) { return "$" + value; }
}

async function loadProducts() {
  const res = await fetch("data/products.json", { cache: "no-store" });
  if (!res.ok) throw new Error("Could not load products");
  const data = await res.json();
  return data.items || [];
}

const CATEGORY_ORDER = ["All", "Sneakers", "Apparel", "Cards"];

/* ---------------- Storefront (index.html) ---------------- */
function initStore() {
  const grid = document.getElementById("grid");
  if (!grid) return;

  const countEl = document.getElementById("count");
  const searchEl = document.getElementById("search");
  const sortEl = document.getElementById("sort");
  const chipsEl = document.getElementById("chips");

  let all = [];
  let category = "All";
  let query = "";

  function cardHtml(item) {
    const condClass = (item.condition || "").toLowerCase() === "used" ? "used" : "";
    return `<a class="card" href="product.html?id=${encodeURIComponent(item.id)}">
      <div class="card-media">
        ${mediaInner(item)}
        <span class="badge badge-brand">${item.brand}</span>
        <span class="badge badge-cond ${condClass}">${item.condition}</span>
      </div>
      <div class="card-body">
        <span class="card-cat">${item.category}</span>
        <span class="card-title">${item.title}</span>
        <span class="card-meta">${metaText(item)}</span>
        <div class="card-foot">
          <span class="card-price">${money(item.price, item.currency)}</span>
          <span class="card-go">View
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none"><path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
          </span>
        </div>
      </div>
    </a>`;
  }

  function render() {
    let list = all.slice();
    if (category !== "All") list = list.filter(i => i.category === category);
    if (query) {
      const q = query.toLowerCase();
      list = list.filter(i =>
        (i.title + " " + i.brand + " " + (i.colorway || "") + " " + (i.size || "") + " " + i.category).toLowerCase().includes(q)
      );
    }
    const sort = sortEl ? sortEl.value : "featured";
    if (sort === "low") list.sort((a, b) => a.price - b.price);
    else if (sort === "high") list.sort((a, b) => b.price - a.price);

    countEl.textContent = list.length + (list.length === 1 ? " item" : " items");
    grid.innerHTML = list.length
      ? list.map(cardHtml).join("")
      : `<div class="empty">No matches. Try a different search or category.</div>`;
  }

  function buildChips() {
    const present = new Set(all.map(i => i.category));
    const cats = CATEGORY_ORDER.filter(c => c === "All" || present.has(c));
    chipsEl.innerHTML = cats.map(c =>
      `<button class="chip ${c === "All" ? "active" : ""}" data-cat="${c}">${c}</button>`
    ).join("");
    chipsEl.addEventListener("click", e => {
      const btn = e.target.closest(".chip");
      if (!btn) return;
      category = btn.dataset.cat;
      chipsEl.querySelectorAll(".chip").forEach(c => c.classList.toggle("active", c === btn));
      render();
    });
  }

  loadProducts().then(items => {
    all = items;
    buildChips();
    render();
  }).catch(() => {
    grid.innerHTML = `<div class="empty">Couldn't load products right now. Please refresh.</div>`;
  });

  if (searchEl) searchEl.addEventListener("input", e => { query = e.target.value.trim(); render(); });
  if (sortEl) sortEl.addEventListener("change", render);
}

/* ---------------- Product detail (product.html) ---------------- */
function initProduct() {
  const root = document.getElementById("product");
  if (!root) return;

  const id = new URLSearchParams(location.search).get("id");

  loadProducts().then(items => {
    const item = items.find(i => i.id === id) || items[0];
    if (!item) { root.innerHTML = `<div class="wrap empty">Product not found.</div>`; return; }
    document.title = `${item.title} — The Wearforce`;

    const condClass = (item.condition || "").toLowerCase() === "used" ? "used" : "";
    const tags = [];
    if (item.size) tags.push(`<span class="tag">Size ${item.size}</span>`);
    if (item.colorway) tags.push(`<span class="tag">${item.colorway}</span>`);
    tags.push(`<span class="tag badge-cond ${condClass}" style="color:#fff">${item.condition}</span>`);

    root.innerHTML = `
      <div class="wrap">
        <div class="crumbs"><a href="index.html">Shop</a> / <span>${item.category}</span> / ${item.title}</div>
        <div class="pd-grid">
          <div class="pd-media">
            ${mediaInner(item)}
          </div>
          <div class="pd-info">
            <span class="pd-cat">${item.category}</span>
            <h1>${item.title}</h1>
            <div class="pd-tags">${tags.join("")}</div>
            <div class="pd-price">${money(item.price, item.currency)} <small>+ shipping</small></div>
            <p class="pd-desc">${item.description || ""}</p>
            <a class="btn btn-red btn-block pd-buy" href="${item.ebayUrl}" target="_blank" rel="noopener">
              Buy Now
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none"><path d="M5 12h14M13 6l6 6-6 6" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/></svg>
            </a>
            <div class="pd-secure">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none"><path d="M12 2l8 4v6c0 5-3.5 8-8 10-4.5-2-8-5-8-10V6l8-4z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/></svg>
              Checkout is completed securely with eBay Buyer Protection.
            </div>
            <div class="pd-points">
              <div class="pd-point">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M20 6L9 17l-5-5" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round"/></svg>
                <div><strong>100% Authentic</strong>Every item is checked before it ships.</div>
              </div>
              <div class="pd-point">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M12 1v22M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg>
                <div><strong>Fair, Honest Pricing</strong>Priced to be worth it, no hype tax.</div>
              </div>
              <div class="pd-point">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none"><path d="M3 7h13v8H3zM16 10h4l1 5h-5z" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><circle cx="7" cy="18" r="1.6" stroke="currentColor" stroke-width="2"/><circle cx="18" cy="18" r="1.6" stroke="currentColor" stroke-width="2"/></svg>
                <div><strong>Fast US Shipping</strong>Most orders ship within one business day.</div>
              </div>
            </div>
          </div>
        </div>
      </div>`;
  }).catch(() => {
    root.innerHTML = `<div class="wrap empty">Couldn't load this product. Please refresh.</div>`;
  });
}

/* ---------------- Shared: mobile nav ---------------- */
function initNav() {
  const toggle = document.querySelector(".nav-toggle");
  const nav = document.querySelector(".main-nav");
  if (toggle && nav) toggle.addEventListener("click", () => nav.classList.toggle("open"));
}

document.addEventListener("DOMContentLoaded", () => {
  initNav();
  initStore();
  initProduct();
});
