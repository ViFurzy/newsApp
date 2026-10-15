"""
main.py — Background aggregator daemon.

Improvements over v1:
  - All constants imported from config.py (single source of truth)
  - HTTP retries via requests.Session + urllib3 Retry adapter
  - Timeout on every network call
  - Deduplication: new articles are upserted into existing JSON by link
  - Atomic writes: temp-file + os.replace prevents corrupt JSON on crash
  - Full traceback logged on unexpected errors
  - Feeds fetched in parallel; conditional GET (ETag / Last-Modified) skips unchanged feeds
  - Runs every FETCH_INTERVAL_MIN minutes, around the clock; the dashboard only reads
"""
import hashlib
import io
import ipaddress
import json
import os
import re
import socket
import sys
import tempfile
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin, urlparse

import feedparser
import requests
import schedule
from PIL import Image
from requests.adapters import HTTPAdapter
from ui.helpers import https_url, strip_html
from urllib3.util.retry import Retry

# ── Config ─────────────────────────────────────────────────────────────────────
from config import (
    AI_FEEDS,
    AI_NEWS_FILE,
    ANIME_FEEDS,
    ANIME_NEWS_FILE,
    DATA_DIR,
    FREE_GAMES_FILE,
    GAMERPOWER_URL,
    GAMES_FEEDS,
    GAMES_NEWS_FILE,
    FETCH_INTERVAL_MIN,
    IMG_DIR,
    IMG_URL_PREFIX,
    MAX_ENTRIES_PER_FEED,
    STATUS_FILE,
    DESIGN_FEEDS,
    DESIGN_NEWS_FILE,
    VIBE_FEEDS,
    VIBE_NEWS_FILE,
)

# ── HTTP session with retry logic ──────────────────────────────────────────────
_retry_strategy = Retry(
    total=3,
    backoff_factor=0.5,
    status_forcelist=[429, 500, 502, 503, 504],
    allowed_methods=["GET"],
)
_http = requests.Session()
_http.mount("https://", HTTPAdapter(max_retries=_retry_strategy))
_http.mount("http://",  HTTPAdapter(max_retries=_retry_strategy))
_http.headers.update({"User-Agent": "DailyAgg/2.0 (+https://github.com/ViFurzy/newsApp)"})

_REQUEST_TIMEOUT = 15   # seconds per request
_MAX_ITEMS_KEPT  = 90   # keep the N most-recent articles per feed file
_MAX_PER_SOURCE  = 15   # ...but at most N per source, so slow feeds are not crowded out by daily ones


# ── Helpers ────────────────────────────────────────────────────────────────────

def _safe_write_json(path: Path, data) -> None:
    """Write JSON atomically — no corrupt files on crash."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", dir=path.parent, suffix=".tmp", delete=False, encoding="utf-8"
    ) as tmp:
        json.dump(data, tmp, ensure_ascii=False, indent=2)
    os.replace(tmp.name, path)


def _load_existing(path: Path) -> dict:
    """Return existing articles keyed by link (for dedup upsert)."""
    if not path.exists():
        return {}
    try:
        with open(path, encoding="utf-8") as f:
            return {item["link"]: item for item in json.load(f) if item.get("link")}
    except Exception:
        return {}


def _ts(item: dict) -> float:
    """Parse published timestamp for sorting; returns 0 on failure."""
    from email.utils import parsedate_to_datetime
    try:
        return parsedate_to_datetime(item.get("published", "")).timestamp()
    except Exception:
        return 0.0


def extract_image(entry) -> str:
    """Best-effort image URL extraction from an RSS entry (always https when the host allows it)."""
    return https_url(_extract_image(entry))


def _extract_image(entry) -> str:
    if getattr(entry, "media_content", None):
        return entry.media_content[0].get("url", "")
    if getattr(entry, "enclosures", None):
        for enc in entry.enclosures:
            if enc.get("type", "").startswith("image/") or enc.get("href", "").endswith(
                (".jpg", ".png", ".jpeg", ".webp")
            ):
                return enc.get("href", "")
    if getattr(entry, "media_thumbnail", None):
        return entry.media_thumbnail[0].get("url", "")

    html_content = entry.get("summary", "")
    if "content" in entry and entry.content:
        html_content += str(entry.content[0].value)
    match = re.search(r'<img[^>]+src="([^">]+)"', html_content)
    return match.group(1) if match else ""


# ── Image cache: download once, shrink, serve locally ──────────────────────────
# Why: feed images were slow (Polygon originals ~5 MB), sometimes hotlink-blocked (KDnuggets 403)
# and popped in late. Local ~720px WebP files are fast and cannot be blocked.

_MAX_IMG_BYTES = 6_000_000
_IMG_WIDTH, _IMG_MAX_HEIGHT = 720, 540
_IMG_HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/124.0 Safari/537.36",
                "Accept": "image/webp,image/jpeg,image/png,image/*;q=0.8"}   # no AVIF: Pillow cannot decode it
Image.MAX_IMAGE_PIXELS = 40_000_000    # reject decompression bombs


def _public_host(host: str) -> bool:
    """Feed-supplied URLs must not reach private/loopback/link-local addresses (SSRF)."""
    try:
        return all(ipaddress.ip_address(ai[4][0]).is_global for ai in socket.getaddrinfo(host, None))
    except Exception:
        return False


def _download_image(url: str, referer: str):
    """GET an image following at most 3 redirects, re-validating every hop. Returns bytes or None."""
    for _ in range(4):
        parts = urlparse(url)
        if parts.scheme not in ("http", "https") or not parts.hostname or not _public_host(parts.hostname):
            return None
        resp = _http.get(url, timeout=10, stream=True, allow_redirects=False,
                         headers={**_IMG_HEADERS, "Referer": referer})
        try:
            if resp.is_redirect:
                url = urljoin(url, resp.headers.get("Location", ""))
                continue
            if resp.status_code != 200 or not resp.headers.get("content-type", "").startswith("image/"):
                return None
            data = resp.raw.read(_MAX_IMG_BYTES + 1, decode_content=True)
            return data if len(data) <= _MAX_IMG_BYTES else None
        finally:
            resp.close()
    return None


def _shrink(data: bytes) -> Image.Image:
    im = Image.open(io.BytesIO(data))
    im.load()
    im = im.convert("RGB")
    if im.width > _IMG_WIDTH:
        im = im.resize((_IMG_WIDTH, max(1, round(im.height * _IMG_WIDTH / im.width))), Image.LANCZOS)
    if im.height > _IMG_MAX_HEIGHT:                                   # very tall: keep the middle
        top = (im.height - _IMG_MAX_HEIGHT) // 2
        im = im.crop((0, top, im.width, top + _IMG_MAX_HEIGHT))
    return im


def localize_image(entry: dict) -> dict:
    """Point entry['image'] at a local copy; '' when it cannot be fetched (card then uses a stock fallback)."""
    url = entry.get("image", "")
    if not url or url.startswith(IMG_URL_PREFIX):
        return entry
    name = hashlib.sha1(url.encode("utf-8")).hexdigest()[:16] + ".webp"
    path = IMG_DIR / name
    if not path.exists():
        try:
            data = _download_image(url, entry.get("link", ""))
            if not data:
                entry["image"] = ""
                return entry
            IMG_DIR.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".tmp")
            _shrink(data).save(tmp, "WEBP", quality=74)
            os.replace(tmp, path)
        except Exception:
            entry["image"] = ""
            return entry
    entry["image"] = f"{IMG_URL_PREFIX}/{name}"
    return entry


def prune_images(files: list) -> int:
    """Delete cached images no stored article points at any more. Returns files removed."""
    if not IMG_DIR.exists():
        return 0
    used = set()
    for f in files:
        try:
            with open(f, encoding="utf-8") as fp:
                used |= {Path(i.get("image", "")).name for i in json.load(fp) if i.get("image", "").startswith(IMG_URL_PREFIX)}
        except Exception:
            return 0           # unreadable data file: do not risk deleting images still in use
    removed = 0
    for p in IMG_DIR.iterdir():
        if p.is_file() and p.name not in used:
            p.unlink(missing_ok=True)
            removed += 1
    return removed


# ── RSS fetcher ────────────────────────────────────────────────────────────────

_HTTP_CACHE_FILE = DATA_DIR / "_http_cache.json"   # url -> {etag, modified}


def _load_http_cache() -> dict:
    try:
        with open(_HTTP_CACHE_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _fetch_one(source_name: str, url: str, validators: dict) -> tuple[list[dict], dict, bool]:
    """Fetch one feed. Returns (entries, new_validators, ok); ([], old, True) when unchanged, ([], old, False) on error."""
    headers = {}
    if validators.get("etag"):
        headers["If-None-Match"] = validators["etag"]
    if validators.get("modified"):
        headers["If-Modified-Since"] = validators["modified"]
    try:
        resp = _http.get(url, timeout=_REQUEST_TIMEOUT, headers=headers)
        if resp.status_code == 304:
            return [], validators, True
        resp.raise_for_status()
        entries = parse_entries(resp.text, source_name)
        return entries, {
            "etag":     resp.headers.get("ETag", ""),
            "modified": resp.headers.get("Last-Modified", ""),
        }, True
    except Exception:
        print(f"[{datetime.now()}] RSS fetch error for {source_name}:")
        traceback.print_exc()
        return [], validators, False


def parse_entries(xml_text: str, source_name: str) -> list[dict]:
    """Turn raw feed XML into article dicts (no network)."""
    out = []
    for entry in feedparser.parse(xml_text).entries[:MAX_ENTRIES_PER_FEED]:
        link = getattr(entry, "link", None)
        if not link:
            continue
        title = entry.get("title", "")
        summary_raw = strip_html(entry.get("summary", ""))
        cut = summary_raw.find(f"Informacja {title}") if title else -1   # GRY-Online boilerplate footer
        if cut > 0:
            summary_raw = summary_raw[:cut].rstrip()
        out.append({
            "title":     title,
            "link":      link,
            "published": entry.get("published", ""),
            "source":    source_name,
            "image":     extract_image(entry),
            "summary":   (summary_raw[:350].rstrip() + "…") if len(summary_raw) > 350 else summary_raw,
            "tags":      [t.get("term", "").strip() for t in entry.get("tags", []) if t.get("term", "").strip()][:12],
        })
    return out


def merge_items(existing: dict, new_entries: list[dict]) -> list[dict]:
    """Upsert by link, sort newest first, keep the most recent N."""
    for e in new_entries:
        existing[e["link"]] = e
    kept, per_source = [], {}
    for it in sorted(existing.values(), key=_ts, reverse=True):
        src = it.get("source", "")
        if per_source.get(src, 0) >= _MAX_PER_SOURCE:
            continue
        per_source[src] = per_source.get(src, 0) + 1
        kept.append(it)
        if len(kept) >= _MAX_ITEMS_KEPT:
            break
    return kept


def fetch_rss_feeds(feeds_dict: dict, output_file: Path, http_cache: dict, failed: list) -> int:
    """Fetch all feeds in parallel, upsert into existing JSON, write atomically."""
    use_cache = output_file.exists()   # no data file -> must not get 304s
    with ThreadPoolExecutor(max_workers=len(feeds_dict)) as pool:
        futures = {
            url: pool.submit(_fetch_one, name, url, http_cache.get(url, {}) if use_cache else {})
            for name, url in feeds_dict.items()
        }
    new_entries: list[dict] = []
    for (name, url), fut in zip(feeds_dict.items(), futures.values()):
        entries, validators, ok = fut.result()
        new_entries += entries
        http_cache[url] = validators
        if not ok:
            failed.append(name)

    existing = {link: it for link, it in _load_existing(output_file).items()
                if it.get("source") in feeds_dict}          # drop items of sources removed from config
    items = merge_items(existing, new_entries)
    with ThreadPoolExecutor(max_workers=8) as pool:      # also upgrades older items still on remote URLs
        items = list(pool.map(localize_image, items))
    _safe_write_json(output_file, items)
    return len(items)


# ── GamerPower fetcher ─────────────────────────────────────────────────────────

def fetch_free_games() -> int:
    """Fetch PC giveaways from GamerPower API, upsert, write atomically."""
    try:
        resp = _http.get(GAMERPOWER_URL, timeout=_REQUEST_TIMEOUT)
        resp.raise_for_status()
        data = resp.json()
    except Exception:
        print(f"[{datetime.now()}] GamerPower API error:")
        traceback.print_exc()
        return 0

    allowed = {"steam", "epic", "gog", "ea", "origin"}
    giveaways: list[dict] = []

    for item in data:
        platforms_str = item.get("platforms", "").lower()
        if any(kw in platforms_str for kw in allowed):
            giveaways.append(
                {
                    "title":       item.get("title"),
                    "link":        item.get("open_giveaway_url"),
                    "thumbnail":   item.get("thumbnail"),
                    "description": item.get("description"),
                    "worth":       item.get("worth"),
                    "platforms":   item.get("platforms"),
                    "end_date":    item.get("end_date"),
                }
            )
        if len(giveaways) >= 20:
            break

    _safe_write_json(FREE_GAMES_FILE, giveaways)
    return len(giveaways)


# ── Orchestrator ───────────────────────────────────────────────────────────────

def fetch_all_data() -> None:
    print(f"[{datetime.now()}] Starting data fetch…")
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    http_cache, failed = _load_http_cache(), []
    ai_count    = fetch_rss_feeds(AI_FEEDS,    AI_NEWS_FILE,    http_cache, failed)
    games_count = fetch_rss_feeds(GAMES_FEEDS, GAMES_NEWS_FILE, http_cache, failed)
    anime_count = fetch_rss_feeds(ANIME_FEEDS, ANIME_NEWS_FILE, http_cache, failed)
    vibe_count   = fetch_rss_feeds(VIBE_FEEDS,   VIBE_NEWS_FILE,   http_cache, failed)
    design_count = fetch_rss_feeds(DESIGN_FEEDS, DESIGN_NEWS_FILE, http_cache, failed)
    fg_count    = fetch_free_games()
    _safe_write_json(_HTTP_CACHE_FILE, http_cache)
    _safe_write_json(STATUS_FILE, {"failed": failed})
    prune_images([AI_NEWS_FILE, GAMES_NEWS_FILE, ANIME_NEWS_FILE, VIBE_NEWS_FILE, DESIGN_NEWS_FILE])

    print(
        f"[{datetime.now()}] Done. "
        f"AI ({ai_count}), Games ({games_count}), "
        f"FreeGames ({fg_count}), Anime ({anime_count}), "
        f"Vibe ({vibe_count}), Design ({design_count})."
    )


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    schedule.every(FETCH_INTERVAL_MIN).minutes.do(fetch_all_data)
    print(f"[{datetime.now()}] Aggregator started. Every {FETCH_INTERVAL_MIN} min.")
    fetch_all_data()
    while True:
        schedule.run_pending()
        time.sleep(30)
