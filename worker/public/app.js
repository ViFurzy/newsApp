// DailyAgg dashboard. Data: /api/data (full, only fetched when /api/stamp changes). Everything is rendered client-side.
const $ = (s) => document.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
const store = {
  get: (k, d) => { try { return JSON.parse(localStorage.getItem(k)) ?? d; } catch { return d; } },
  set: (k, v) => { try { localStorage.setItem(k, JSON.stringify(v)); } catch {} },
};
const JIKAN = "https://api.jikan.moe/v4";
const POLL_MS = 60_000, POLL_EMPTY_MS = 8_000;

const unsplash = (id) => `https://images.unsplash.com/photo-${id}?w=1920&q=50`;
const TABS = [
  { key: "ai", label: "AI & Tech", cat: "AI / TECH", title: "Artificial Intelligence & Technology", cols: 3, bg: "1677442136019-21780ecad995", tint: "rgba(91,156,246,0.040)" },
  { key: "games", label: "Gaming", cat: "GAMING", title: "Gaming News", cols: 2, side: "free", bg: "1542751371-adc38448a05e", tint: "rgba(34,197,94,0.032)", fb: "gaming" },
  { key: "anime", label: "Anime", cat: "ANIME", title: "Anime News", cols: 2, side: "genre", bg: "1578632767115-351597cf2477", tint: "rgba(167,139,250,0.040)", fb: "anime" },
  { key: "vibe", label: "Vibe Code", cat: ">_ VIBE CODE", title: "Vibe Coding & AI Dev Tools", cols: 3, variant: "code", bg: "1605379399642-870262d3d051", tint: "rgba(34,211,238,0.040)" },
  { key: "design", label: "Design", cat: "DESIGN", title: "Design, UX & Visual Culture", cols: 3, variant: "visual", bg: "1541701494587-cb58502866ab", tint: "rgba(236,72,153,0.040)" },
  { key: "saved", label: "Saved", cat: "READ LATER", title: "Saved Stories", bg: "1481627834876-b7833e8f5570", tint: "rgba(200,112,56,0.045)" },
];
const PER_PAGE = 6;
const TICKER_CATS = { ai: "AI", games: "GAMING", anime: "ANIME", vibe: "VIBE", design: "DESIGN" };

let data = { tabs: {}, free: [], updated: {}, failed: [], stamp: 0 };
let tab = TABS.some((t) => t.key === store.get("_da_tab")) ? store.get("_da_tab") : "ai";
const view = { page: {}, q: {}, picked: {}, genre: "", sort: "score" };
let saved = store.get("_da_saved_v2", {}); // link -> item (+ cat)

// ── Formatting ─────────────────────────────────────────────────────────────────
const FLAGS = { "🇺🇸": "us", "🇵🇱": "pl", "🇬🇧": "gb" };
const parseSource = (s) => { const [a, ...r] = s.split(" "); return r.length && /[^\x00-\x7f]/.test(a) ? [a, r.join(" ")] : ["", s]; };
const ago = (ts) => {
  const s = (Date.now() - ts) / 1000;
  return s < 120 ? "just now" : s < 3600 ? `${Math.floor(s / 60)}m ago` : s < 86400 ? `${Math.floor(s / 3600)}h ago` : `${Math.floor(s / 86400)}d ago`;
};
const fmtDate = (ts) => new Date(ts).toLocaleString("en-GB", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit" }).replace(",", " ·");
const ICON = (d, extra = "") => `<svg viewBox="0 0 24 24" width="9" height="9" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;${extra}">${d}</svg>`;
const RSS = ICON('<path d="M4 11a9 9 0 0 1 9 9"/><path d="M4 4a16 16 0 0 1 16 16"/><circle cx="5" cy="19" r="1"/>', "margin-right:5px;opacity:.65");
const BOOK = ICON('<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>', "opacity:.5");
const CLOCK = ICON('<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>', "opacity:.5");
const CHECK = ICON('<polyline points="20 6 9 17 4 12"/>', "margin-right:4px");

// ── Fallback images (whole-word keyword rules, then per-tab default) ──────────
const U = (id) => `https://images.unsplash.com/photo-${id}?auto=format&fit=crop&w=800&q=75`;
const IMG = { ai: U("1677442136019-21780ecad995"), hw: U("1485827404703-89b55fcc595e"), console: U("1605901309584-818e25960b8f"),
  pc: U("1587202372634-32705e3bf49c"), anime: U("1578632767115-351597cf2477"), game: U("1552820728-8b83bb6b773f"), dflt: U("1518770660439-4636190af475") };
const RULES = [
  [/\b(?:ai|openai|chatgpt|llms?|gpt|sztuczn\w*|inteligencj\w*)\b/, IMG.ai], [/\b(?:robots?|machine learning|hardware|chips?|processors?)\b/, IMG.hw],
  [/\b(?:xbox|playstation|nintendo|consoles?|sony)\b/, IMG.console], [/\b(?:pc|steam|epic|valve)\b/, IMG.pc],
  [/\b(?:anime|manga|shonen|seinen|isekai)\b/, IMG.anime], [/\b(?:gra|games?|rpg|fps|multiplayer|trailer)\b/, IMG.game],
];
const POOL = {
  vibe: ["1461749280684-dccba630e2f6", "1515879218367-8466d910aaa4", "1605379399642-870262d3d051", "1555066931-4365d14bab8c"].map(U),
  design: ["1558655146-d09347e92766", "1626785774573-4b799315345d", "1586717791821-3f44a563fa4c", "1561070791-2526d30994b5", "1541701494587-cb58502866ab"].map(U),
};
const hash = (s) => [...s].reduce((h, c) => (h * 31 + c.charCodeAt(0)) >>> 0, 7);
function fallbackImage(it, cat) {
  if (POOL[cat]) return POOL[cat][hash(it.title) % POOL[cat].length];
  const text = `${it.title} ${it.summary}`.toLowerCase();
  return RULES.find(([rx]) => rx.test(text))?.[1] ?? { games: IMG.game, anime: IMG.anime }[cat] ?? IMG.dflt;
}

// ── Cards ──────────────────────────────────────────────────────────────────────
function card(it, cat) {
  const [flag, name] = parseSource(it.source);
  const fb = fallbackImage(it, cat);
  const img = it.image || fb;
  const cors = img.includes("medium.com/") ? ' crossorigin="anonymous"' : "";
  const on = !!saved[it.link];
  const mins = Math.max(1, Math.round((it.summary.split(/\s+/).length || 1) / 200));
  return `<div class="nc"><a href="${esc(it.link)}" target="_blank" rel="noopener" class="nc-link" aria-label="${esc(it.title)}"></a>
<button type="button" class="nc-save" data-link="${esc(it.link)}" data-cat="${cat}" aria-pressed="${on}" aria-label="${on ? "Remove from saved" : "Save for later"}">${on ? "★" : "☆"}</button>
<div class="nc-img"><img class="nc-photo" src="${esc(img)}" decoding="async" loading="lazy" alt="" referrerpolicy="no-referrer"${cors} data-fb="${esc(fb)}">${FLAGS[flag] ? `<div class="nc-flag"><img src="https://flagcdn.com/w40/${FLAGS[flag]}.png" width="20" alt=""></div>` : ""}</div>
<div class="nc-body"><div class="nc-meta"><span class="src-badge">${RSS}${esc(name)}</span>${Date.now() - it.ts < 3 * 3600e3 ? ' <span class="badge-new">New</span>' : ""}<span class="nc-time">${ago(it.ts)}</span></div>
<div class="nc-title">${esc(it.title)}</div><div class="nc-summary">${esc(it.summary.slice(0, 300))}</div>
<div class="nc-footer"><span class="nc-footer-item">${BOOK}&nbsp;${mins} min read</span><span class="nc-footer-item">${CLOCK}&nbsp;${fmtDate(it.ts)}</span></div></div></div>`;
}

const header = (t, count, updated) => `<div class="section-hdr"><div class="section-hdr-top"><span class="section-hdr-cat">${esc(t.cat)}</span>${updated ? `<span class="section-updated">· ${updated}</span>` : ""}${count ? `<span class="section-pill">${count}</span>` : ""}</div><h2>${esc(t.title)}</h2></div>`;
const empty = (msg) => `<div class="empty-state">${esc(msg)}</div>`;

// ── Free games + countdown ─────────────────────────────────────────────────────
const endMs = (s) => (/^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d$/.test(s ?? "") ? Date.parse(s.replace(" ", "T") + "Z") : NaN);
function countdown(end) {
  const diff = end - Date.now();
  if (diff <= 0) return ["Expired", "expiry-urgent"];
  const s = Math.floor(diff / 1000), d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
  const p = (n) => String(n).padStart(2, "0");
  if (d >= 3) return [`${d}d ${p(h)}h ${p(m)}m`, "expiry-ok"];
  if (d >= 1) return [`${d}d ${p(h)}h ${p(m)}m ${p(sec)}s`, "expiry-soon"];
  return [`${p(h)}:${p(m)}:${p(sec)}`, h >= 6 ? "expiry-soon" : "expiry-urgent"];
}
function freeColumn() {
  const hd = header({ cat: "FREE", title: "Free Games Now" });
  const active = data.free.filter((g) => !(endMs(g.end_date) <= Date.now()));
  if (!active.length) return hd + empty("No free games right now");
  return hd + `<div class="list">${active.map((g, i) => {
    const end = endMs(g.end_date), [label, cls] = Number.isNaN(end) ? ["", ""] : countdown(end);
    const worth = /^\$\d/.test((g.worth ?? "").trim()) ? `<span class="gr-price-was">${esc(g.worth.trim())}</span>` : "";
    return `<a href="${esc(g.link)}" target="_blank" rel="noopener" class="gr" style="animation-delay:${i * 45}ms"><div class="gr-thumb" style="width:92px;height:62px;background-image:url('${esc(g.thumbnail)}')"></div>
<div class="gr-body"><div style="margin-bottom:5px;display:flex;gap:6px;align-items:center;flex-wrap:wrap"><span class="badge-free">${CHECK}FREE</span><span style="font-size:.6rem;color:var(--text-3)">${worth}</span></div>
<div class="gr-title">${esc(g.title)}</div><div class="gr-meta">${esc(g.platforms)}${label ? `<span style="white-space:nowrap">&nbsp;·&nbsp;<span class="gr-countdown ${cls}" data-end="${end}">${label}</span></span>` : ""}</div></div></a>`;
  }).join("")}</div>`;
}
setInterval(() => document.querySelectorAll(".gr-countdown").forEach((el) => {
  const [label, cls] = countdown(+el.dataset.end);
  el.textContent = label; el.className = `gr-countdown ${cls}`;
}), 1000);

// ── Anime genre browser (Jikan, called straight from the browser) ─────────────
let genres;
const jikan = async (path) => (await (await fetch(JIKAN + path)).json()).data ?? [];
const animeRow = (a, i) => {
  const meta = [a.score && `★ ${a.score}`, a.year, a.episodes && `${a.episodes} ep`, (a.status ?? "").replace("Finished Airing", "Finished").replace("Currently Airing", "Airing")].filter(Boolean).join(" · ");
  return `<a href="${esc(a.url)}" target="_blank" rel="noopener" class="gr" style="animation-delay:${i * 40}ms"><div class="gr-thumb" style="width:54px;height:76px;background-image:url('${esc(a.images?.jpg?.image_url)}')"></div><div class="gr-body"><div class="gr-title">${esc(a.title)}</div><div class="gr-meta">${esc(meta)}</div></div></a>`;
};
function genreColumn() {
  return header({ cat: "SEARCH", title: "Browse by Genre" }) +
    `<div class="genre-bar"><select id="genre" aria-label="Genre"><option value="">Select a genre</option></select>
<select id="sort" aria-label="Sort">${[["score", "Score"], ["popularity", "Popularity"], ["members", "Members"]].map(([v, l]) => `<option value="${v}"${view.sort === v ? " selected" : ""}>${l}</option>`).join("")}</select></div>
<div id="genre-out" style="max-height:800px;overflow-y:auto;padding-right:4px"></div>`;
}
async function initGenre() {
  const sel = $("#genre"), out = $("#genre-out");
  if (!sel) return;
  genres ??= await jikan("/genres/anime").then((g) => g.sort((a, b) => a.name.localeCompare(b.name))).catch(() => []);
  if (!genres.length) genres = undefined; // failed: retry on the next visit
  if (!$("#genre") || !genres) return; // tab changed while loading
  sel.insertAdjacentHTML("beforeend", genres.map((g) => `<option value="${g.mal_id}"${String(g.mal_id) === view.genre ? " selected" : ""}>${esc(g.name)}</option>`).join(""));
  const show = async () => {
    view.genre = sel.value; view.sort = $("#sort").value;
    if (!view.genre) return void (out.innerHTML = empty("Select a genre to browse anime"));
    out.innerHTML = empty("Loading…");
    const list = await jikan(`/anime?genres=${encodeURIComponent(view.genre)}&order_by=${view.sort}&sort=desc&limit=20&sfw=true`).catch(() => []);
    if ($("#genre-out") === out) out.innerHTML = list.length ? `<div class="list">${list.map(animeRow).join("")}</div>` : empty("No results found for this genre");
  };
  sel.onchange = $("#sort").onchange = show;
  show();
}

// ── News tabs: filter bar, grid, pager ─────────────────────────────────────────
const current = () => TABS.find((t) => t.key === tab);
function visibleItems() {
  const q = (view.q[tab] ?? "").trim().toLowerCase(), picked = view.picked[tab];
  return (data.tabs[tab] ?? []).filter((i) => (!picked?.size || picked.has(i.source)) && (!q || `${i.title} ${i.summary}`.toLowerCase().includes(q)));
}
function renderGrid() {
  const t = current(), items = visibleItems(), pages = Math.max(1, Math.ceil(items.length / PER_PAGE));
  const page = (view.page[tab] = Math.min(view.page[tab] ?? 0, pages - 1));
  const searching = view.q[tab] || view.picked[tab]?.size;
  $("#grid").innerHTML = items.length
    ? `<div class="bento-grid ${t.cols === 3 ? "bg-3" : "bg-2"}${t.variant ? ` bg-${t.variant}` : ""}">${items.slice(page * PER_PAGE, (page + 1) * PER_PAGE).map((i) => card(i, t.fb ?? t.key)).join("")}</div>`
    : empty(searching ? "No articles match your search" : data.stamp ? "No articles available yet" : "Waiting for the first fetch…");
  $("#pager").innerHTML = pages > 1
    ? `<div class="pager"><button data-page="${page - 1}" aria-label="Previous page"${page ? "" : " disabled"}>◀</button><span>${page + 1} / ${pages}</span><button data-page="${page + 1}" aria-label="Next page"${page < pages - 1 ? "" : " disabled"}>▶</button></div>` : "";
  sweepImages();
}
function newsColumn(t) {
  const all = data.tabs[tab] ?? [], sources = [...new Set(all.map((i) => i.source))].sort(), picked = view.picked[tab] ?? new Set();
  const updated = data.updated[tab] ? ago(data.updated[tab]) : "";
  return header(t, all.length, updated) + (all.length
    ? `<div class="fbar"><input id="q" type="search" placeholder="Search headlines" aria-label="Search headlines" value="${esc(view.q[tab] ?? "")}">
<div class="chips" role="group" aria-label="Sources">${sources.map((s) => `<button type="button" class="chip" data-src="${esc(s)}" aria-pressed="${picked.has(s)}">${esc(parseSource(s)[1])}</button>`).join("")}</div></div>` : "")
    + `<div id="grid"></div><div id="pager"></div>`;
}
function renderTab() {
  const t = current(), refocus = document.activeElement?.id === "q";
  document.querySelectorAll(".tab").forEach((b) => b.setAttribute("aria-selected", b.dataset.tab === tab));
  if (t.key === "saved") {
    const items = Object.values(saved).reverse();
    $("#panel").innerHTML = header(t) + (items.length ? `<div class="bento-grid bg-2">${items.map((i) => card(i, i.cat)).join("")}</div>` : empty("Nothing saved yet. Use the star on any story."));
    return sweepImages();
  }
  $("#panel").innerHTML = t.side
    ? `<div class="split"><div>${newsColumn(t)}</div><div>${t.side === "free" ? freeColumn() : genreColumn()}</div></div>`
    : newsColumn(t);
  renderGrid();
  if (t.side === "genre") initGenre();
  if (refocus) { const q = $("#q"); q.focus(); q.setSelectionRange(q.value.length, q.value.length); }
}

// ── Masthead + ticker ──────────────────────────────────────────────────────────
function renderMasthead() {
  const n = (k) => data.tabs[k]?.length ?? 0, total = Object.keys(TICKER_CATS).reduce((s, k) => s + n(k), 0);
  const stamp = Math.max(0, ...Object.values(data.updated));
  const failed = data.failed.map((s) => parseSource(s)[1]).join(", ");
  $("#masthead").innerHTML = `<div class="masthead"><div class="masthead-top"><div class="masthead-brand"><img class="masthead-logo" src="/favicon.ico" alt="">Daily<em>Agg</em></div>
<div class="masthead-live"><span class="live-badge"><span class="live-dot"></span>LIVE</span><span class="masthead-count"><strong>${total}</strong>&nbsp;articles</span></div></div>
<div class="masthead-sub"><span class="masthead-date">${new Date().toLocaleDateString("en-GB", { weekday: "short", day: "2-digit", month: "short", year: "numeric" }).replace(/,/g, "").toUpperCase()}</span>
${[["AI", "ai"], ["Gaming", "games"], ["Anime", "anime"], ["Vibe", "vibe"], ["Design", "design"]].map(([l, k]) => `<span class="masthead-sep">·</span><span>${l}&nbsp;<strong>${n(k)}</strong></span>`).join("")}
<span class="masthead-sep">·</span><span>Updated&nbsp;<strong>${stamp ? ago(stamp) : "never"}</strong></span>
${failed ? `<span class="masthead-warn" role="status">${data.failed.length} source${data.failed.length > 1 ? "s" : ""} unavailable: ${esc(failed)}</span>` : ""}</div></div>`;
}
function renderTicker() {
  const items = Object.entries(TICKER_CATS).flatMap(([k, label]) => (data.tabs[k] ?? []).slice(0, 6).map((i) => ({ ...i, label })));
  if (!items.length) return void ($("#ticker").innerHTML = "");
  const build = (hidden) => items.map((i) => `<a href="${esc(i.link)}" target="_blank" rel="noopener" class="t-item" tabindex="-1"${hidden ? ' aria-hidden="true"' : ""}><span class="t-cat">${i.label}</span><span>${esc(i.title)}</span></a><span class="t-sep" aria-hidden="true">◆</span>`).join("");
  $("#ticker").innerHTML = `<div class="ticker-wrap"><input type="checkbox" id="tk-pause" class="tk-pause" aria-label="Pause news ticker"><label for="tk-pause" class="tk-pause-btn" title="Pause or resume ticker"></label>
<div class="ticker-label"><div class="live-dot"></div>LATEST</div><div class="ticker-scroll"><div class="ticker-track">${build(false)}${build(true)}</div></div></div>`;
}

// ── Images: fade in on load, swap to the fallback when broken or slow ─────────
const shown = (img) => img.classList.add("is-loaded");
function fallback(img) {
  const fb = img.dataset.fb;
  if (img.dataset.fell || !fb) { img.style.visibility = "hidden"; return shown(img); }
  img.dataset.fell = "1"; img.removeAttribute("crossorigin"); img.src = fb;
}
function sweepImages() {
  document.querySelectorAll("img.nc-photo:not(.is-loaded)").forEach((img) => {
    if (img.complete) img.naturalWidth ? shown(img) : fallback(img);
    else if (!img._slow) img._slow = setTimeout(() => !img.classList.contains("is-loaded") && fallback(img), 7000);
  });
}
for (const ev of ["load", "error"]) // load/error do not bubble: capture phase
  document.addEventListener(ev, (e) => e.target.classList?.contains("nc-photo") && (ev === "load" ? shown(e.target) : fallback(e.target)), true);

// ── Events ─────────────────────────────────────────────────────────────────────
document.addEventListener("click", (e) => {
  const star = e.target.closest(".nc-save"), chip = e.target.closest(".chip"), pg = e.target.closest("[data-page]"), tb = e.target.closest(".tab");
  if (star) {
    const link = star.dataset.link, cat = star.dataset.cat;
    if (saved[link]) delete saved[link];
    else {
      const it = Object.values(data.tabs).flat().find((i) => i.link === link);
      if (it) saved[link] = { ...it, cat };
    }
    store.set("_da_saved_v2", saved);
    if (tab === "saved") renderTab();
    else { const on = !!saved[link]; star.setAttribute("aria-pressed", on); star.textContent = on ? "★" : "☆"; star.setAttribute("aria-label", on ? "Remove from saved" : "Save for later"); }
  } else if (chip) {
    const set = (view.picked[tab] ??= new Set());
    set.has(chip.dataset.src) ? set.delete(chip.dataset.src) : set.add(chip.dataset.src);
    chip.setAttribute("aria-pressed", set.has(chip.dataset.src));
    view.page[tab] = 0; renderGrid();
  } else if (pg) {
    view.page[tab] = +pg.dataset.page; renderGrid();
  } else if (tb) {
    tab = tb.dataset.tab; store.set("_da_tab", tab); renderTab(); paintBackground();
  }
});
document.addEventListener("input", (e) => {
  if (e.target.id === "q") { view.q[tab] = e.target.value; view.page[tab] = 0; renderGrid(); }
});

// ── Theme + backgrounds ────────────────────────────────────────────────────────
const SUN = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"><circle cx="12" cy="12" r="5"/><path d="M12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4"/></svg>';
const MOON = '<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.8A9 9 0 1 1 11.2 3 7 7 0 0 0 21 12.8z"/></svg>';
const themeBtn = $("#theme"), isLight = () => document.documentElement.dataset.theme === "light";
themeBtn.innerHTML = isLight() ? MOON : SUN;
themeBtn.onclick = () => {
  isLight() ? delete document.documentElement.dataset.theme : (document.documentElement.dataset.theme = "light");
  store.set("_da_theme", isLight() ? "light" : "dark"); themeBtn.innerHTML = isLight() ? MOON : SUN;
};
$("#bgs").innerHTML = TABS.map((t) => `<div class="bg-layer" style="background-image:linear-gradient(var(--ov),var(--ov)),radial-gradient(ellipse 110% 60% at 50% -8%,${t.tint} 0%,transparent 65%),url(${unsplash(t.bg)})"></div>`).join("");
const paintBackground = () => document.querySelectorAll(".bg-layer").forEach((el, i) => el.classList.toggle("on", TABS[i].key === tab));

// ── Live updates: poll the 1-read stamp endpoint, pull full data only when it changes ──
let timer;
async function load() {
  data = await (await fetch("/api/data", { cache: "no-store" })).json();
  renderMasthead(); renderTicker(); renderTab();
}
async function poll() {
  clearTimeout(timer);
  try {
    const { stamp } = await (await fetch("/api/stamp", { cache: "no-store" })).json();
    if (stamp !== data.stamp) await load(); else renderMasthead(); // else: just refresh the "updated N m ago" labels
  } catch { /* offline: try again next tick */ }
  timer = setTimeout(poll, data.stamp ? POLL_MS : POLL_EMPTY_MS);
}
document.addEventListener("visibilitychange", () => !document.hidden && poll());

$("#tabs").innerHTML = TABS.map((t) => `<button class="tab" role="tab" data-tab="${t.key}" aria-selected="${t.key === tab}">${t.label}</button>`).join("");
paintBackground();
renderMasthead();
renderTab();
poll();
