// Pure logic (no I/O): feed parsing, merge/dedup, per-tab filters, brand cards.
// Ported from ai_news_app/main.py, ui/filters.py and ui/brands.py.
import { XMLParser } from "fast-xml-parser";
import { MAX_ENTRIES_PER_FEED, MAX_ITEMS_KEPT, MAX_PER_SOURCE } from "./config.js";

// ── Text helpers ───────────────────────────────────────────────────────────────

const ENTITIES = { amp: "&", lt: "<", gt: ">", quot: '"', apos: "'", nbsp: " " };
const decode = (s) =>
  s.replace(/&(?:#(\d+)|#x([0-9a-f]+)|(\w+));/gi, (m, d, h, n) =>
    d ? String.fromCodePoint(+d) : h ? String.fromCodePoint(parseInt(h, 16)) : ENTITIES[n.toLowerCase()] ?? m);

/** Plain text: drop tags (incl. one cut off by truncation), decode entities (twice: some feeds double-encode). */
export function stripHtml(text) {
  if (!text) return "";
  text = text.replace(/<[^>]*>/g, "").replace(/<[^>]*$/, "");
  return decode(decode(text)).replace(/\s+/g, " ").trim();
}

export const safeUrl = (u) => (/^https?:\/\//i.test(u || "") ? u : "");
const httpsUrl = (u) => (u.startsWith("http://") ? "https://" + u.slice(7) : u);

// ── Feed parsing ───────────────────────────────────────────────────────────────

const ARRAYS = new Set(["item", "entry", "category", "link", "enclosure", "media:content", "media:thumbnail"]);
const parser = new XMLParser({
  ignoreAttributes: false,
  attributeNamePrefix: "@_",
  isArray: (name) => ARRAYS.has(name),
});

const txt = (v) => (v && typeof v === "object" && !Array.isArray(v) ? txt(v["#text"]) : v == null ? "" : String(v));

/** Cut the document after the n-th entry: feeds can be 200 KB and we only keep the newest few (saves CPU). */
function capEntries(xml, n) {
  const close = xml.includes("</entry>") ? "</entry>" : "</item>";
  let at = -1;
  for (let i = 0; i < n; i++) {
    at = xml.indexOf(close, at + 1);
    if (at < 0) return xml;
  }
  const tail = close === "</entry>" ? "</feed>" : xml.includes("<rdf:RDF") ? "</rdf:RDF>" : "</channel></rss>";
  return xml.slice(0, at + close.length) + tail;
}

function entryLink(e) {
  for (const l of e.link ?? []) {
    if (typeof l === "string") return l.trim();
    if (l["@_href"] && (!l["@_rel"] || l["@_rel"] === "alternate")) return l["@_href"];
    if (l["#text"]) return String(l["#text"]).trim();
  }
  return "";
}

function entryImage(e, html) {
  const media = e["media:content"]?.[0]?.["@_url"];
  if (media) return media;
  for (const enc of e.enclosure ?? []) {
    const url = enc["@_url"] ?? "";
    if ((enc["@_type"] ?? "").startsWith("image/") || /\.(jpe?g|png|webp)(\?|$)/i.test(url)) return url;
  }
  return e["media:thumbnail"]?.[0]?.["@_url"] ?? /<img[^>]+src=["']([^"']+)["']/i.exec(html)?.[1] ?? "";
}

/** Raw feed XML -> article objects (no network). `now` stands in for entries with no usable date. */
export function parseFeed(xml, source, now = Date.now(), max = MAX_ENTRIES_PER_FEED) {
  const doc = parser.parse(capEntries(xml, max));
  const entries = doc.rss?.channel?.item ?? doc.feed?.entry ?? doc["rdf:RDF"]?.item ?? [];
  const out = [];
  for (const e of entries.slice(0, max)) {
    const link = safeUrl(entryLink(e));
    if (!link) continue;
    const title = stripHtml(txt(e.title));
    const rawHtml = txt(e.description ?? e.summary ?? e.content ?? "");
    let summary = stripHtml(rawHtml);
    const cut = title ? summary.indexOf(`Informacja ${title}`) : -1; // GRY-Online boilerplate footer
    if (cut > 0) summary = summary.slice(0, cut).trimEnd();
    const ts = Date.parse(txt(e.pubDate ?? e.published ?? e.updated ?? e["dc:date"]));
    out.push({
      title,
      link,
      ts: Number.isNaN(ts) ? now : ts,
      source,
      image: safeUrl(httpsUrl(entryImage(e, rawHtml + txt(e["content:encoded"])))),
      summary: summary.length > 350 ? summary.slice(0, 350).trimEnd() + "…" : summary,
      tags: (e.category ?? []).map((c) => (typeof c === "string" ? c : c["@_term"] ?? txt(c)).trim()).filter(Boolean).slice(0, 12),
    });
  }
  return out;
}

/** Upsert by link, newest first, at most MAX_PER_SOURCE per source (so slow feeds are not crowded out), MAX_ITEMS_KEPT total. */
export function mergeItems(existing, fresh) {
  const byLink = new Map(existing.map((i) => [i.link, i]));
  for (const i of fresh) byLink.set(i.link, i);
  const perSource = {};
  const kept = [];
  for (const it of [...byLink.values()].sort((a, b) => b.ts - a.ts)) {
    if ((perSource[it.source] ?? 0) >= MAX_PER_SOURCE) continue;
    perSource[it.source] = (perSource[it.source] ?? 0) + 1;
    kept.push(it);
    if (kept.length >= MAX_ITEMS_KEPT) break;
  }
  return kept;
}

// ── Per-tab filters ────────────────────────────────────────────────────────────

const GAMING_TITLE_TERMS = [
  "xbox", "playstation", "ps5", "ps4", "nintendo", "switch lite", "steam", "gameplay", "game review", "dlc",
  "patch notes", "battle royale", "early access", "game of the year", "game pass", "fortnite", "minecraft",
  "call of duty", "grand theft auto", "league of legends", "counter-strike", "valorant", "overwatch",
  "apex legends", "elden ring", "baldur's gate", "diablo", "world of warcraft", "final fantasy xvi",
  "street fighter", "esports tournament", "gaming chair", "gaming headset",
];
const AI_TECH_TERMS = [
  " ai ", "artificial intelligence", "machine learning", "llm", "gpt", "chatgpt", "openai", "anthropic",
  "deepmind", "neural network", " nlp ", "language model", "generative ai", "diffusion model", "tech ",
  "technology", "software", "hardware", "processor", "chip", "robotics", "algorithm", "data science",
  "startup", "cloud computing", "cybersecurity", "programming", "quantum", "automation",
];
const VIBE_BROAD_SOURCES = ["Latent Space", "ITwiz"];
const VIBE_TERMS = [
  "vibe", "coding", "copilot", "cursor", "claude", "codex", "gemini cli", "agentic", "llm", "prompt", "mcp",
  "developer", "software", "programming", "github", "kodowan", "programow", "programist", "oprogramowani",
];
const NON_GAME_TAGS = new Set([
  "movies", "movies & tv", "tv", "film", "films", "entertainment", "fyi", "filmy", "filmy i seriale", "seriale",
  "serial", "komiksy", "comics", "netflix", "disney+ / disney plus", "hbo max", "prime video",
]);
const GAMES_MIXED_SOURCES = ["GameRant", "Polygon", "GRY-Online"];

const itemText = (i) => ` ${i.title} ${i.summary}`.toLowerCase() + " ";
const has = (text, terms) => terms.some((t) => text.includes(t));
const isGamingTitle = (i) => has(` ${i.title.toLowerCase()} `, GAMING_TITLE_TERMS);

export const FILTERS = {
  ai: (items) => items.filter((i) => !(isGamingTitle(i) && !has(itemText(i), AI_TECH_TERMS))),
  anime: (items) => items.filter((i) => !isGamingTitle(i)),
  vibe: (items) =>
    items.filter((i) => !VIBE_BROAD_SOURCES.some((b) => i.source.includes(b)) || has(itemText(i), VIBE_TERMS)),
  games: (items) =>
    items.filter((i) =>
      i.tags?.length ? !i.tags.some((t) => NON_GAME_TAGS.has(t.toLowerCase())) : !GAMES_MIXED_SOURCES.some((s) => i.source.includes(s))),
  design: (items) => items,
};

// ── Brand cards: image-less AI articles naming a known company get a logo card ─
// [pattern, label, Simple Icons slug | null]. Case-sensitive on purpose: "Apple" the company, not the fruit.
export const BRANDS = [
  ["Meta|Facebook", "Meta", "meta"], ["Instagram", "Instagram", "instagram"], ["WhatsApp", "WhatsApp", "whatsapp"],
  ["Google|Gemini|DeepMind", "Google", "google"], ["OpenAI|ChatGPT", "OpenAI", null],
  ["Anthropic|Claude", "Anthropic", "anthropic"], ["Microsoft|Copilot", "Microsoft", null],
  ["Amazon|AWS", "Amazon", null], ["Apple|iPhone", "Apple", "apple"], ["Nvidia|NVIDIA", "Nvidia", "nvidia"],
  ["Huawei", "Huawei", "huawei"], ["Samsung", "Samsung", "samsung"], ["Xiaomi", "Xiaomi", "xiaomi"],
  ["Intel", "Intel", "intel"], ["AMD", "AMD", "amd"], ["Qualcomm", "Qualcomm", "qualcomm"],
  ["Tesla", "Tesla", "tesla"], ["SpaceX", "SpaceX", "spacex"], ["xAI|Grok", "xAI", null],
  ["DeepSeek", "DeepSeek", "deepseek"], ["Mistral", "Mistral", "mistralai"], ["Perplexity", "Perplexity", "perplexity"],
  ["TikTok|ByteDance", "TikTok", "tiktok"], ["Alibaba|Qwen", "Alibaba", "alibabadotcom"], ["Baidu", "Baidu", "baidu"],
  ["GitHub", "GitHub", "github"], ["Hugging Face", "Hugging Face", "huggingface"], ["Cursor", "Cursor", "cursor"],
  ["Netflix", "Netflix", "netflix"], ["Spotify", "Spotify", "spotify"], ["Uber", "Uber", "uber"],
  ["Stripe", "Stripe", "stripe"], ["Shopify", "Shopify", "shopify"], ["Walmart", "Walmart", null],
  ["Salesforce", "Salesforce", null], ["IBM", "IBM", null], ["Oracle", "Oracle", null], ["Adobe", "Adobe", null],
  ["TechCrunch", "TechCrunch", "techcrunch"], ["PHP", "PHP", "php"], ["Linux", "Linux", "linux"],
  ["Android", "Android", "android"],
].map(([p, label, slug]) => ({ rx: new RegExp(`\\b(?:${p})\\b`), label, slug, key: brandKey(label) }));

export function brandKey(label) {
  return label.toLowerCase().replace(/[^a-z0-9]+/g, "");
}

/** The brand named first in the title, or undefined. */
export function findBrand(title) {
  let best;
  for (const b of BRANDS) {
    const at = title.search(b.rx);
    if (at >= 0 && (!best || at < best.at)) best = { at, brand: b };
  }
  return best?.brand;
}

const esc = (s) => s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

/** Only path data is kept from a Simple Icons SVG; never embed a remote SVG wholesale. */
export const logoPaths = (svg) => [...svg.matchAll(/<path d="([^"]+)"/g)].map((m) => m[1]);

/** 16:9 dark card with the logo + label; wordmark only when there is no logo. */
export function cardSvg(label, paths) {
  const head =
    '<svg xmlns="http://www.w3.org/2000/svg" width="720" height="405" viewBox="0 0 720 405"><defs>' +
    '<linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="#14171f"/>' +
    '<stop offset="1" stop-color="#262b3b"/></linearGradient></defs><rect width="720" height="405" fill="url(#g)"/>';
  if (paths.length) {
    return (
      head +
      `<g transform="translate(305 106) scale(4.6)" fill="#f0ece4">${paths.map((d) => `<path d="${esc(d)}"/>`).join("")}</g>` +
      `<text x="360" y="276" text-anchor="middle" font-family="ui-monospace,Consolas,monospace" font-size="24" ` +
      `letter-spacing="7" fill="#c87038">${esc(label.toUpperCase())}</text></svg>`
    );
  }
  const size = Math.min(72, (640 * 1.6) / label.length).toFixed(0);
  return (
    head +
    `<text x="360" y="222" text-anchor="middle" font-family="Georgia,serif" font-weight="700" font-size="${size}" ` +
    `fill="#f0ece4">${esc(label)}</text><rect x="320" y="250" width="80" height="3" fill="#c87038"/></svg>`
  );
}
