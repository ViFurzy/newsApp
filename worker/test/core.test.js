import assert from "node:assert/strict";
import { test } from "node:test";
import { FILTERS, cardSvg, findBrand, matchBanner, mergeItems, ogImage, parseFeed, stripHtml } from "../src/core.js";

const NOW = Date.parse("2026-10-23T12:00:00Z");

const RSS = `<?xml version="1.0"?><rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/" xmlns:content="http://purl.org/rss/1.0/modules/content/"><channel>
<item><title>Meta &amp; friends</title><link>http://a.test/1</link><pubDate>Thu, 22 Oct 2026 10:00:00 GMT</pubDate>
<description><![CDATA[<p>Hello &amp;amp; <b>world</b></p><img src="http://img.test/x.jpg">]]></description><category>AI</category><category>Movies</category></item>
<item><title>No date</title><link>https://a.test/2</link><media:content url="https://img.test/m.png"/></item>
<item><title>No link</title></item>
</channel></rss>`;

const ATOM = `<feed xmlns="http://www.w3.org/2005/Atom"><entry><title type="html">Atom post</title>
<link rel="alternate" href="https://b.test/p"/><updated>2026-10-23T09:00:00Z</updated><summary>S</summary><category term="vibe"/></entry></feed>`;

test("parses RSS: entities, https upgrade, tags, missing date/link", () => {
  const items = parseFeed(RSS, "src", NOW);
  assert.equal(items.length, 2); // item without link dropped
  assert.equal(items[0].title, "Meta & friends");
  assert.equal(items[0].summary, "Hello & world");
  assert.equal(items[0].image, "https://img.test/x.jpg");
  assert.deepEqual(items[0].tags, ["AI", "Movies"]);
  assert.equal(items[0].ts, Date.parse("2026-10-22T10:00:00Z"));
  assert.equal(items[1].ts, NOW);
  assert.equal(items[1].image, "https://img.test/m.png");
});

test("parses Atom and caps entries", () => {
  const [e] = parseFeed(ATOM, "atom", NOW);
  assert.deepEqual([e.title, e.link, e.tags], ["Atom post", "https://b.test/p", ["vibe"]]);
  const many = `<rss><channel>${Array.from({ length: 30 }, (_, i) => `<item><title>t${i}</title><link>https://x.test/${i}</link></item>`).join("")}</channel></rss>`;
  assert.equal(parseFeed(many, "s", NOW).length, 10);
});

test("rejects non-http links", () => {
  const xml = `<rss><channel><item><title>x</title><link>javascript:alert(1)</link></item></channel></rss>`;
  assert.equal(parseFeed(xml, "s", NOW).length, 0);
});

test("merge upserts by link, sorts newest first, caps per source", () => {
  const mk = (n, ts, source = "s") => ({ title: `t${n}`, link: `https://x.test/${n}`, ts, source });
  const old = [mk(1, 1), mk(2, 2)];
  const merged = mergeItems(old, [mk(2, 5), mk(3, 3)]);
  assert.deepEqual(merged.map((i) => i.link.slice(-1)), ["2", "3", "1"]);
  const flood = Array.from({ length: 40 }, (_, n) => mk(n, n));
  assert.equal(mergeItems([], flood).length, 15);
});

test("merge keeps an image the cron added when the fresh feed copy has none", () => {
  const old = [{ title: "a", link: "https://x.test/1", ts: 1, source: "s", image: "https://i.test/og.jpg", ogTried: true }];
  const [m] = mergeItems(old, [{ title: "a", link: "https://x.test/1", ts: 2, source: "s", image: "" }]);
  assert.equal(m.image, "https://i.test/og.jpg");
  assert.equal(m.ogTried, true);
  assert.equal(m.ts, 2);
});

test("media:thumbnail as element text (MyAnimeList) and og:image in either attribute order", () => {
  const xml = `<rss><channel><item><title>x</title><link>https://m.test/1</link><media:thumbnail>http://cdn.test/t.jpg</media:thumbnail></item></channel></rss>`;
  assert.equal(parseFeed(xml, "s", NOW)[0].image, "https://cdn.test/t.jpg");
  assert.equal(ogImage(`<meta property="og:image" content="https://a.test/1.jpg" /><meta property="og:image:width" content="600">`), "https://a.test/1.jpg");
  assert.equal(ogImage(`<meta content='http://a.test/2.jpg' property='og:image'>`), "https://a.test/2.jpg");
  assert.equal(ogImage(`<meta property="og:image" content="javascript:x">`), "");
  assert.equal(ogImage("<html></html>"), "");
});

test("matchBanner: whole-word, season suffix dropped, longest title wins, short/foreign titles ignored", () => {
  const show = (english, romaji, bannerImage) => ({ title: { english, romaji }, bannerImage });
  const shows = [show("Black Clover Season 2", "Black Clover", "https://a.test/bc.jpg"), show("One Piece", "ONE PIECE", "https://a.test/op.jpg"),
    show("Clover", null, "https://a.test/short.jpg"), show(null, "Bleach: Sennen Kessen-hen", "https://a.test/bl.jpg"), show("Gin", "銀", "https://a.test/gin.jpg")];
  assert.equal(matchBanner("Black Clover Season 2 Episode 4 Preview Teases Nacht", shows), "https://a.test/bc.jpg");
  assert.equal(matchBanner("New One Piece Fan Letter Campaign", shows), "https://a.test/op.jpg");
  assert.equal(matchBanner("Someone Begins Cloverfield Anime", shows), ""); // not a whole word
  assert.equal(matchBanner("Gin the movie", shows), ""); // too short
  assert.equal(matchBanner("Unrelated headline", shows), "");
});

test("games filter drops film/TV by tag; ai filter drops pure gaming", () => {
  const g = (source, tags) => ({ title: "t", summary: "", source, tags });
  assert.equal(FILTERS.games([g("🇺🇸 Polygon", ["Movies"]), g("🇺🇸 Polygon", ["Games"]), g("🇺🇸 Polygon", []), g("🇺🇸 RPS", [])]).length, 2);
  const a = (title) => ({ title, summary: "", source: "s" });
  assert.equal(FILTERS.ai([a("Xbox Game Pass update"), a("OpenAI boosts Xbox"), a("New chip")]).length, 2);
});

test("brand detection: first named company, case-sensitive, svg escaped", () => {
  assert.equal(findBrand("Huawei and Meta announce a deal").label, "Huawei");
  assert.equal(findBrand("An apple a day"), undefined);
  assert.equal(findBrand("Amazon launches Alexa").key, "amazon");
  assert.ok(!cardSvg("A<B", []).includes("<B"));
});

test("stripHtml handles truncated tags and double-encoding", () => {
  assert.equal(stripHtml("a &amp;quot;b&amp;quot; <p>c</p> <a href="), 'a "b" c');
});
