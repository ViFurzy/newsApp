"""
ui/helpers.py — Pure helper functions, icon SVGs, and flag lookup.

No Streamlit calls here — safe to import anywhere, fast to test.
"""
import re
from datetime import datetime
from email.utils import parsedate_to_datetime
from html import unescape

# ── HTML tag stripper ──────────────────────────────────────────────────────────
_HTML_TAG_RE = re.compile("<.*?>")

# ── Flag → CDN image map ───────────────────────────────────────────────────────
FLAG_MAP = {
    "🇺🇸": "https://flagcdn.com/w40/us.png",
    "🇵🇱": "https://flagcdn.com/w40/pl.png",
    "🇬🇧": "https://flagcdn.com/w40/gb.png",
    "🌍": "",
}

# ── Inline SVG icons (used in card HTML) ───────────────────────────────────────
RSS_ICON = (
    '<svg viewBox="0 0 24 24" width="9" height="9" stroke="currentColor" stroke-width="2.5" '
    'fill="none" stroke-linecap="round" stroke-linejoin="round" '
    'style="margin-right:5px;flex-shrink:0;opacity:.65;">'
    '<path d="M4 11a9 9 0 0 1 9 9"/><path d="M4 4a16 16 0 0 1 16 16"/>'
    '<circle cx="5" cy="19" r="1"/></svg>'
)
CHECK_ICON = (
    '<svg viewBox="0 0 24 24" width="9" height="9" stroke="currentColor" stroke-width="2.5" '
    'fill="none" stroke-linecap="round" stroke-linejoin="round" style="margin-right:4px;flex-shrink:0;">'
    '<polyline points="20 6 9 17 4 12"/></svg>'
)
CLOCK_ICON = (
    '<svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;opacity:.5;">'
    '<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>'
)
BOOK_ICON = (
    '<svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
    'stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;opacity:.5;">'
    '<path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>'
    '<path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>'
)


# ── Date / time helpers ────────────────────────────────────────────────────────

def format_date(s: str) -> str:
    if not s:
        return ""
    try:
        return parsedate_to_datetime(s).strftime("%d %b %Y · %H:%M")
    except Exception:
        return s


def relative_time(s: str) -> str:
    if not s:
        return ""
    try:
        dt   = parsedate_to_datetime(s)
        secs = (datetime.now(dt.tzinfo) - dt).total_seconds()
        if secs <    120: return "just now"
        if secs <   3600: return f"{int(secs / 60)}m ago"
        if secs <  86400: return f"{int(secs / 3600)}h ago"
        return f"{int(secs / 86400)}d ago"
    except Exception:
        return format_date(s)


def is_fresh(s: str, hours: int = 3) -> bool:
    if not s:
        return False
    try:
        dt = parsedate_to_datetime(s)
        return (datetime.now(dt.tzinfo) - dt).total_seconds() < hours * 3600
    except Exception:
        return False


# ── Text helpers ───────────────────────────────────────────────────────────────

def estimate_reading_time(text: str) -> str:
    if not text:
        return "1 min"
    mins = max(1, round(len(text.split()) / 200))
    return f"{mins} min read"


def strip_html(text: str) -> str:
    """Plain text: drop tags (incl. one cut off by truncation), decode entities, collapse spaces."""
    if not text:
        return ""
    text = _HTML_TAG_RE.sub("", text)
    text = re.sub(r"<[^>]*$", "", text)          # unterminated tag from a truncated summary
    for _ in range(2):                           # some feeds double-encode (&amp;quot;)
        text = unescape(text)
    return re.sub(r"\s+", " ", text).strip()


# ── Image fallback ─────────────────────────────────────────────────────────────
_UNSPLASH = "https://images.unsplash.com/{}?auto=format&fit=crop&w=800&q=75"
_IMG_AI, _IMG_HW, _IMG_CONSOLE, _IMG_PC, _IMG_ANIME, _IMG_GAME, _IMG_DEFAULT = (
    _UNSPLASH.format(x) for x in (
        "photo-1677442136019-21780ecad995", "photo-1485827404703-89b55fcc595e",
        "photo-1605901309584-818e25960b8f", "photo-1587202372634-32705e3bf49c",
        "photo-1578632767115-351597cf2477", "photo-1552820728-8b83bb6b773f",
        "photo-1518770660439-4636190af475",
    )
)
# Whole-word patterns (a bare "ai" substring matched "again", "main", "Kai"...); first hit wins.
_FALLBACK_RULES = [
    (re.compile(r"\b(?:ai|openai|chatgpt|llms?|gpt|sztuczn\w*|inteligencj\w*)\b"), _IMG_AI),
    (re.compile(r"\b(?:robots?|machine learning|hardware|chips?|processors?)\b"), _IMG_HW),
    (re.compile(r"\b(?:xbox|playstation|nintendo|consoles?|sony)\b"), _IMG_CONSOLE),
    (re.compile(r"\b(?:pc|steam|epic|valve)\b"), _IMG_PC),
    (re.compile(r"\b(?:anime|manga|shonen|seinen|isekai)\b"), _IMG_ANIME),
    (re.compile(r"\b(?:gra|games?|rpg|fps|multiplayer|trailer)\b"), _IMG_GAME),
]
_CATEGORY_DEFAULT = {"ai": _IMG_DEFAULT, "gaming": _IMG_GAME, "anime": _IMG_ANIME}


def get_fallback_image(title: str, summary: str = "", category: str = "") -> str:
    text = (title + " " + summary).lower()
    for rx, url in _FALLBACK_RULES:
        if rx.search(text):
            return url
    return _CATEGORY_DEFAULT.get(category, _IMG_DEFAULT)


# ── Source / flag parsing ──────────────────────────────────────────────────────

def parse_source(source_full: str) -> tuple[str, str]:
    parts = source_full.split(" ", 1)
    if len(parts) == 2 and any(not c.isascii() for c in parts[0]):
        return parts[0], parts[1]
    return "", source_full


def render_flag(flag: str) -> str:
    if not flag or flag not in FLAG_MAP or not FLAG_MAP[flag]:
        return ""
    return f'<div class="nc-flag"><img src="{FLAG_MAP[flag]}" width="20" alt=""></div>'


# ── Expiry / countdown helpers ─────────────────────────────────────────────────

def parse_end_date(s):
    if not s or str(s).strip().upper() == "N/A":
        return None
    try:
        return datetime.strptime(str(s).strip(), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def is_expired(s) -> bool:
    dt = parse_end_date(s)
    return dt is not None and datetime.now() > dt


def format_end_date(s) -> str | None:
    dt = parse_end_date(s)
    return dt.strftime("%d %b %Y") if dt else None


def expiry_class(s) -> str:
    dt = parse_end_date(s)
    if dt is None:
        return ""
    days = (dt - datetime.now()).days
    if days < 1:  return "expiry-urgent"
    if days <= 3: return "expiry-soon"
    return "expiry-ok"


def days_left_label(s) -> str | None:
    dt = parse_end_date(s)
    if dt is None:
        return None
    diff = (dt - datetime.now()).total_seconds()
    if diff <= 0:
        return "Expired"
    total = int(diff)
    days = total // 86400
    hrs  = (total % 86400) // 3600
    mins = (total % 3600) // 60
    secs = total % 60
    if days >= 3:
        return f"{days}d {hrs:02d}h {mins:02d}m"
    if days >= 1:
        return f"{days}d {hrs:02d}h {mins:02d}m {secs:02d}s"
    return f"{hrs:02d}:{mins:02d}:{secs:02d}"


# ── File / stats helpers ───────────────────────────────────────────────────────
import json
import os
import time


def count_items(f) -> int:
    if not os.path.exists(f):
        return 0
    try:
        with open(f, "r", encoding="utf-8") as fp:
            return len(json.load(fp))
    except Exception:
        return 0


def get_file_age_str(filepath) -> str:
    if not os.path.exists(filepath):
        return "never"
    secs = time.time() - os.path.getmtime(filepath)
    if secs <    120: return "just now"
    if secs <   3600: return f"{int(secs / 60)}m ago"
    if secs <  86400: return f"{int(secs / 3600)}h ago"
    return f"{int(secs / 86400)}d ago"
