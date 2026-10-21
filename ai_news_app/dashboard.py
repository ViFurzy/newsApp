"""
dashboard.py — Thin entry point for the DailyAgg Streamlit app.

All rendering logic lives in ui/ sub-modules:
  ui/styles.py   — CSS + JS injection
  ui/helpers.py  — Pure helper functions
  ui/filters.py  — Content-tab filtering
  ui/cards.py    — News card / pagination rendering
  ui/ticker.py   — Masthead + scrolling ticker
  ui/anime.py    — Anime tab (news + genre search)
  ui/games.py    — Gaming tab (news + free games + countdown)
"""
import os
import threading
import time
import traceback
import base64 as _base64
from PIL import Image

import streamlit as st

from config import (
    AI_NEWS_FILE,
    AI_PER_PAGE,
    ANIME_NEWS_FILE,
    DESIGN_NEWS_FILE,
    DESIGN_PER_PAGE,
    FREE_GAMES_FILE,
    GAMES_NEWS_FILE,
    STALE_AFTER_SEC,
    STATUS_FILE,
    VIBE_NEWS_FILE,
    VIBE_PER_PAGE,
    WATCH_INTERVAL_SEC,
)
from ui.styles import inject_styles
from ui.helpers import count_items, get_file_age_str
from ui.filters import filter_for_ai_tab, filter_for_vibe_tab
from ui.cards import render_news_cards, section_header
from ui.ticker import render_dashboard_header
from ui.games import render_games_tab
from ui.anime import render_anime_tab

# ── Favicon / page config ──────────────────────────────────────────────────────
_FAVICON_PATH = os.path.join(os.path.dirname(__file__), "vNews_logo.ico")
_favicon      = Image.open(_FAVICON_PATH) if os.path.exists(_FAVICON_PATH) else "📰"

st.set_page_config(page_title="Daily Aggregator", page_icon=_favicon, layout="wide")

# ── Inject CSS + JS ────────────────────────────────────────────────────────────
inject_styles()

# ── Session state ──────────────────────────────────────────────────────────────
for _k in ("free_games_page", "ai_news_page", "games_news_page", "anime_news_page",
           "vibe_news_page", "design_news_page"):
    if _k not in st.session_state:
        st.session_state[_k] = 0

# ── Live updates ───────────────────────────────────────────────────────────────
# main.py (the daemon) owns fetching. The page just watches the data files and
# re-renders when they change, so new posts appear without a manual refresh.
_WATCHED = (AI_NEWS_FILE, GAMES_NEWS_FILE, ANIME_NEWS_FILE, VIBE_NEWS_FILE, DESIGN_NEWS_FILE,
            FREE_GAMES_FILE, STATUS_FILE)


def _data_stamp() -> float:
    return max((os.path.getmtime(f) for f in _WATCHED if os.path.exists(f)), default=0.0)


_stamp = _data_stamp()


@st.cache_resource
def _fetch_lock():
    return threading.Lock()


def _refresh_if_stale() -> None:
    """Safety net: if the daemon died or hung, a page load past STALE_AFTER_SEC fetches in the background."""
    if time.time() - _stamp < STALE_AFTER_SEC or not _fetch_lock().acquire(blocking=False):
        return

    def _run():
        try:
            import main
            main.fetch_all_data()
        except Exception:
            traceback.print_exc()
        finally:
            _fetch_lock().release()

    threading.Thread(target=_run, daemon=True).start()


_refresh_if_stale()   # the fragment below picks up the new files and reruns


@st.fragment(run_every=WATCH_INTERVAL_SEC)
def _watch_data() -> None:
    if _data_stamp() != _stamp:
        st.rerun()


_watch_data()

# ── Masthead + news ticker ─────────────────────────────────────────────────────
render_dashboard_header()

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_ai, tab_games, tab_anime, tab_vibe, tab_design, tab_saved = st.tabs(
    ["AI & Tech", "Gaming", "Anime", "Vibe Code", "Design", "Saved"]
)

with tab_ai:
    n       = count_items(AI_NEWS_FILE)
    updated = get_file_age_str(AI_NEWS_FILE)
    section_header(
        "AI / TECH", "Artificial Intelligence & Technology",
        count=n or None, updated=updated if n else None,
    )
    render_news_cards(
        AI_NEWS_FILE,
        num_cols=3,
        per_page=AI_PER_PAGE,
        page_key="ai_news_page",
        filter_fn=filter_for_ai_tab,
        category="ai",
    )

with tab_games:
    render_games_tab()

with tab_anime:
    render_anime_tab()

with tab_vibe:
    n       = count_items(VIBE_NEWS_FILE)
    updated = get_file_age_str(VIBE_NEWS_FILE)
    section_header(
        ">_ VIBE CODE", "Vibe Coding & AI Dev Tools",
        count=n or None, updated=updated if n else None,
    )
    render_news_cards(
        VIBE_NEWS_FILE,
        num_cols=3,
        per_page=VIBE_PER_PAGE,
        page_key="vibe_news_page",
        filter_fn=filter_for_vibe_tab,
        category="vibe",
        variant="code",
    )

with tab_design:
    n       = count_items(DESIGN_NEWS_FILE)
    updated = get_file_age_str(DESIGN_NEWS_FILE)
    section_header(
        "DESIGN", "Design, UX & Visual Culture",
        count=n or None, updated=updated if n else None,
    )
    render_news_cards(
        DESIGN_NEWS_FILE,
        num_cols=3,
        per_page=DESIGN_PER_PAGE,
        page_key="design_news_page",
        category="design",
        variant="visual",
    )

with tab_saved:
    section_header("READ LATER", "Saved Stories")
    st.markdown('<div id="da-saved"></div>', unsafe_allow_html=True)  # filled by the stars script
