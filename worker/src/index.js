// Worker entry: cron refreshes each section into KV; the fetch handler serves the API + brand cards
// (everything else is the static dashboard in public/).
//
// KV keys: cat:<ai|games|anime|vibe|design> -> [item]   free -> [giveaway]
//          meta -> {updated:{cat:ms}, failed:{cat:[source]}, kicked:ms}   brand:<key> -> svg
import { CRONS, FEEDS, GAMERPOWER_URL, STALE_AFTER_MS } from "./config.js";
import { BRANDS, FILTERS, cardSvg, findBrand, logoPaths, mergeItems, parseFeed, safeUrl } from "./core.js";

const UA = "DailyAgg/3.0 (+https://github.com/ViFurzy/newsApp)";
const json = (body, init = {}) =>
  new Response(JSON.stringify(body), {
    ...init,
    headers: { "content-type": "application/json", "cache-control": "no-store", ...init.headers },
  });

// ── Refresh ────────────────────────────────────────────────────────────────────

async function fetchFeed(name, url) {
  try {
    const res = await fetch(url, {
      headers: { "user-agent": UA, accept: "application/rss+xml, application/atom+xml, application/xml, text/xml, */*" },
      signal: AbortSignal.timeout(15000),
    });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return { name, ok: true, items: parseFeed(await res.text(), name) };
  } catch (err) {
    console.log(`feed failed: ${name}: ${err.message}`);
    return { name, ok: false, items: [] };
  }
}

async function refreshFree(env) {
  const res = await fetch(GAMERPOWER_URL, { headers: { "user-agent": UA }, signal: AbortSignal.timeout(15000) });
  if (!res.ok) throw new Error(`GamerPower HTTP ${res.status}`);
  const stores = /steam|epic|gog|ea|origin/;
  const games = (await res.json())
    .filter((g) => stores.test((g.platforms ?? "").toLowerCase()) && safeUrl(g.open_giveaway_url))
    .slice(0, 20)
    .map((g) => ({
      title: g.title, link: g.open_giveaway_url, thumbnail: safeUrl(g.thumbnail), worth: g.worth,
      platforms: g.platforms, end_date: g.end_date, // "YYYY-MM-DD HH:MM:SS" (UTC) or "N/A"
    }));
  await env.NEWS.put("free", JSON.stringify(games));
}

async function refresh(env, cat) {
  const results = await Promise.all(Object.entries(FEEDS[cat]).map(([name, url]) => fetchFeed(name, url)));
  const failed = results.filter((r) => !r.ok).map((r) => r.name);
  const meta = (await env.NEWS.get("meta", "json")) ?? { updated: {}, failed: {} };
  meta.failed[cat] = failed;

  if (failed.length < results.length) {
    const old = (await env.NEWS.get(`cat:${cat}`, "json")) ?? [];
    let items = mergeItems(old.filter((i) => i.source in FEEDS[cat]), results.flatMap((r) => r.items));
    if (cat === "ai") {
      items = items.map((i) => {
        const brand = i.image ? null : findBrand(i.title);
        return brand ? { ...i, image: `/brand/${brand.key}.svg` } : i;
      });
    }
    await env.NEWS.put(`cat:${cat}`, JSON.stringify(items));
    meta.updated[cat] = Date.now();
  }
  if (cat === "games") await refreshFree(env).catch((e) => console.log(`free games failed: ${e.message}`));
  await env.NEWS.put("meta", JSON.stringify(meta));
}

const refreshAll = async (env, cats = Object.keys(FEEDS)) => {
  for (const cat of cats) await refresh(env, cat);
};

// ── API ────────────────────────────────────────────────────────────────────────

const stampOf = (meta) => Math.max(0, ...Object.values(meta.updated));

/** Cheap poll target for the page (1 KV read). Also the safety net: stale or empty data kicks a full refresh. */
async function apiStamp(env, ctx) {
  const meta = (await env.NEWS.get("meta", "json")) ?? { updated: {}, failed: {} };
  const stamp = stampOf(meta);
  const stale = Date.now() - stamp > STALE_AFTER_MS;
  const missing = Object.keys(FEEDS).filter((c) => !meta.updated[c]); // e.g. fresh deploy, only some crons have run
  if ((stale || missing.length) && Date.now() - (meta.kicked ?? 0) > 5 * 60 * 1000) {
    meta.kicked = Date.now();
    await env.NEWS.put("meta", JSON.stringify(meta));
    ctx.waitUntil(refreshAll(env, stale ? undefined : missing));
  }
  return json({ stamp });
}

async function apiData(env) {
  const cats = Object.keys(FEEDS);
  const [meta, free, ...lists] = await Promise.all([
    env.NEWS.get("meta", "json"),
    env.NEWS.get("free", "json"),
    ...cats.map((c) => env.NEWS.get(`cat:${c}`, "json")),
  ]);
  const m = meta ?? { updated: {}, failed: {} };
  const tabs = Object.fromEntries(cats.map((c, i) => [c, FILTERS[c](lists[i] ?? [])]));
  return json({ stamp: stampOf(m), updated: m.updated, failed: Object.values(m.failed).flat(), tabs, free: free ?? [] });
}

async function brandCard(env, key) {
  const brand = BRANDS.find((b) => b.key === key);
  if (!brand) return new Response("not found", { status: 404 });
  const headers = { "content-type": "image/svg+xml", "cache-control": "public, max-age=86400" };
  const stored = await env.NEWS.get(`brand:${key}`);
  if (stored) return new Response(stored, { headers });

  let paths = [];
  let final = true;
  if (brand.slug) {
    try {
      const res = await fetch(`https://cdn.simpleicons.org/${brand.slug}/ffffff`, { signal: AbortSignal.timeout(10000) });
      if (res.ok) paths = logoPaths(await res.text());
      else final = res.status === 404; // 404 = no logo, wordmark is final; anything else retries next time
    } catch {
      final = false;
    }
  }
  const svg = cardSvg(brand.label, paths);
  if (final) await env.NEWS.put(`brand:${key}`, svg);
  return new Response(svg, { headers: final ? headers : { ...headers, "cache-control": "no-store" } });
}

export default {
  async fetch(req, env, ctx) {
    const { pathname } = new URL(req.url);
    if (pathname === "/api/stamp") return apiStamp(env, ctx);
    if (pathname === "/api/data") return apiData(env);
    const m = /^\/brand\/([a-z0-9]+)\.svg$/.exec(pathname);
    if (m) return brandCard(env, m[1]);
    return new Response("not found", { status: 404 });
  },

  async scheduled(event, env, ctx) {
    const cat = CRONS[event.cron];
    ctx.waitUntil(cat ? refresh(env, cat) : refreshAll(env));
  },
};
