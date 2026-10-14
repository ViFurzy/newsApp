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
import json
import os
import re
import sys
import tempfile
import time
import traceback
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from pathlib import Path

import feedparser
import requests
import schedule
from requests.adapters import HTTPAdapter
from ui.helpers import strip_html
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
    MAX_ENTRIES_PER_FEED,
    STATUS_FILE,
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
_MAX_ITEMS_KEPT  = 60   # keep the N most-recent articles per feed file


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
    """Best-effort image URL extraction from an RSS entry."""
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
        })
    return out


def merge_items(existing: dict, new_entries: list[dict]) -> list[dict]:
    """Upsert by link, sort newest first, keep the most recent N."""
    for e in new_entries:
        existing[e["link"]] = e
    return sorted(existing.values(), key=_ts, reverse=True)[:_MAX_ITEMS_KEPT]


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

    items = merge_items(_load_existing(output_file), new_entries)
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
    fg_count    = fetch_free_games()
    _safe_write_json(_HTTP_CACHE_FILE, http_cache)
    _safe_write_json(STATUS_FILE, {"failed": failed})

    print(
        f"[{datetime.now()}] Done. "
        f"AI ({ai_count}), Games ({games_count}), "
        f"FreeGames ({fg_count}), Anime ({anime_count})."
    )


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    schedule.every(FETCH_INTERVAL_MIN).minutes.do(fetch_all_data)
    print(f"[{datetime.now()}] Aggregator started. Every {FETCH_INTERVAL_MIN} min.")
    fetch_all_data()
    while True:
        schedule.run_pending()
        time.sleep(30)
