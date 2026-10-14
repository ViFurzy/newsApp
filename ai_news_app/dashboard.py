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
import base64 as _base64
from PIL import Image

import streamlit as st

from config import (
    AI_NEWS_FILE,
    AI_PER_PAGE,
    ANIME_NEWS_FILE,
    FREE_GAMES_FILE,
    GAMES_NEWS_FILE,
    STATUS_FILE,
    WATCH_INTERVAL_SEC,
)
from ui.styles import inject_styles
from ui.helpers import count_items, get_file_age_str
from ui.filters import filter_for_ai_tab
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
for _k in ("free_games_page", "ai_news_page", "games_news_page", "anime_news_page"):
    if _k not in st.session_state:
        st.session_state[_k] = 0

# ── Live updates ───────────────────────────────────────────────────────────────
# main.py (the daemon) owns fetching. The page just watches the data files and
# re-renders when they change, so new posts appear without a manual refresh.
_WATCHED = (AI_NEWS_FILE, GAMES_NEWS_FILE, ANIME_NEWS_FILE, FREE_GAMES_FILE, STATUS_FILE)


def _data_stamp() -> float:
    return max((os.path.getmtime(f) for f in _WATCHED if os.path.exists(f)), default=0.0)


_stamp = _data_stamp()


@st.fragment(run_every=WATCH_INTERVAL_SEC)
def _watch_data() -> None:
    if _data_stamp() != _stamp:
        st.rerun()


_watch_data()

# ── Masthead + news ticker ─────────────────────────────────────────────────────
render_dashboard_header()

# ── Tabs ───────────────────────────────────────────────────────────────────────
tab_ai, tab_games, tab_anime, tab_saved = st.tabs(["AI & Tech", "Gaming", "Anime", "Saved"])

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

with tab_saved:
    section_header("READ LATER", "Saved Stories")
    st.markdown('<div id="da-saved"></div>', unsafe_allow_html=True)  # filled by the stars script
