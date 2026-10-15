"""
ui/ticker.py — Dashboard masthead, live article count, and scrolling news ticker.
"""
import html as _html
import json
import base64
import os
from datetime import datetime
from pathlib import Path

import streamlit as st

from config import (
    AI_NEWS_FILE, ANIME_NEWS_FILE, DESIGN_NEWS_FILE, GAMES_NEWS_FILE, STATUS_FILE, VIBE_NEWS_FILE,
)
from ui.helpers import count_items, get_file_age_str, parse_source
from ui.cards import load_sorted_items
from ui.filters import (
    filter_for_ai_tab, filter_for_anime_tab, filter_for_games_tab, filter_for_vibe_tab,
)

# ── Logo (base64-encoded for inline HTML) ──────────────────────────────────────
_FAVICON_PATH = Path(__file__).parent.parent / "vNews_logo.ico"
_LOGO_B64 = (
    base64.b64encode(_FAVICON_PATH.read_bytes()).decode()
    if _FAVICON_PATH.exists()
    else ""
)
_LOGO_SRC = f"data:image/x-icon;base64,{_LOGO_B64}" if _LOGO_B64 else ""


# ── News ticker ────────────────────────────────────────────────────────────────

def build_ticker_html() -> str:
    all_items  = []
    for filepath, cat, keep in [   # same per-tab filters as the cards, so the ticker never shows off-topic items
        (AI_NEWS_FILE, "AI", filter_for_ai_tab),
        (GAMES_NEWS_FILE, "GAMING", filter_for_games_tab),
        (ANIME_NEWS_FILE, "ANIME", filter_for_anime_tab),
        (VIBE_NEWS_FILE, "VIBE", filter_for_vibe_tab),
        (DESIGN_NEWS_FILE, "DESIGN", lambda items: items),
    ]:
        items = load_sorted_items(str(filepath))
        if items:
            for item in keep(items)[:6]:
                all_items.append({"title": item["title"], "link": item["link"], "cat": cat})

    if not all_items:
        return ""

    def _build(hidden: bool) -> str:
        # Ticker only repeats what the cards show: keep it out of the tab order entirely.
        attrs = ' tabindex="-1" aria-hidden="true"' if hidden else ' tabindex="-1"'
        return "".join(
            f'<a href="{_html.escape(it["link"])}" target="_blank" rel="noopener" class="t-item"{attrs}>'
            f'<span class="t-cat">{it["cat"]}</span>'
            f'<span>{_html.escape(it["title"])}</span>'
            f'</a><span class="t-sep" aria-hidden="true">◆</span>'
            for it in all_items
        )

    inner = _build(False) + _build(True)  # second copy only makes the loop seamless

    return f"""
<div class="ticker-wrap">
  <input type="checkbox" id="tk-pause" class="tk-pause" aria-label="Pause news ticker">
  <label for="tk-pause" class="tk-pause-btn" title="Pause or resume ticker"></label>
  <div class="ticker-label"><div class="live-dot"></div>LATEST</div>
  <div class="ticker-scroll">
    <div class="ticker-track">{inner}</div>
  </div>
</div>"""


# ── Masthead ───────────────────────────────────────────────────────────────────

def _failed_sources_html() -> str:
    try:
        failed = json.loads(Path(STATUS_FILE).read_text(encoding="utf-8")).get("failed", [])
    except Exception:
        return ""
    if not failed:
        return ""
    names = _html.escape(", ".join(parse_source(n)[1] for n in failed))
    word = "source" if len(failed) == 1 else "sources"
    return f'<span class="masthead-warn" role="status" title="{names}">{len(failed)} {word} unavailable: {names}</span>'


def render_dashboard_header() -> None:
    ai_n    = count_items(AI_NEWS_FILE)
    games_n = count_items(GAMES_NEWS_FILE)
    anime_n = count_items(ANIME_NEWS_FILE)
    vibe_n  = count_items(VIBE_NEWS_FILE)
    design_n = count_items(DESIGN_NEWS_FILE)
    total   = ai_n + games_n + anime_n + vibe_n + design_n
    updated = get_file_age_str(AI_NEWS_FILE)
    now_str = datetime.now().strftime("%a, %d %b %Y").upper()

    logo_html = f'<img class="masthead-logo" src="{_LOGO_SRC}" alt="">' if _LOGO_SRC else ""

    header_html = f"""
<div class="masthead">
  <div class="masthead-top">
    <div class="masthead-brand">{logo_html}Daily<em>Agg</em></div>
    <div class="masthead-live">
      <span class="live-badge"><span class="live-dot"></span>LIVE</span>
      <span class="masthead-count"><strong>{total}</strong>&nbsp;articles</span>
    </div>
  </div>
  <div class="masthead-sub">
    <span class="masthead-date">{now_str}</span>
    <span class="masthead-sep">·</span>
    <span>AI&nbsp;<strong>{ai_n}</strong></span>
    <span class="masthead-sep">·</span>
    <span>Gaming&nbsp;<strong>{games_n}</strong></span>
    <span class="masthead-sep">·</span>
    <span>Anime&nbsp;<strong>{anime_n}</strong></span>
    <span class="masthead-sep">·</span>
    <span>Vibe&nbsp;<strong>{vibe_n}</strong></span>
    <span class="masthead-sep">·</span>
    <span>Design&nbsp;<strong>{design_n}</strong></span>
    <span class="masthead-sep">·</span>
    <span>Updated&nbsp;<strong>{updated}</strong></span>
    {_failed_sources_html()}
  </div>
</div>
"""
    st.markdown(header_html + build_ticker_html(), unsafe_allow_html=True)
