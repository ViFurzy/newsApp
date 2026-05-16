import streamlit as st
import streamlit.components.v1 as components
import json
import os
import re
import time
import threading
import requests
from datetime import datetime
from email.utils import parsedate_to_datetime
from PIL import Image

_FAVICON_PATH = os.path.join(os.path.dirname(__file__), "vNews_logo.ico")
_favicon = Image.open(_FAVICON_PATH) if os.path.exists(_FAVICON_PATH) else "📰"

st.set_page_config(page_title="Daily Aggregator", page_icon=_favicon, layout="wide")

_HTML_TAG_RE = re.compile('<.*?>')

FLAG_MAP = {
    "🇺🇸": "https://flagcdn.com/w40/us.png",
    "🇵🇱": "https://flagcdn.com/w40/pl.png",
    "🇬🇧": "https://flagcdn.com/w40/gb.png",
    "🌍": "",
}

DATA_DIR = "/app/data"
AI_NEWS_FILE = os.path.join(DATA_DIR, "news.json")
GAMES_NEWS_FILE = os.path.join(DATA_DIR, "games_news.json")
FREE_GAMES_FILE = os.path.join(DATA_DIR, "free_games.json")
ANIME_NEWS_FILE = os.path.join(DATA_DIR, "anime_news.json")

GAMES_PER_PAGE = 8
JIKAN_BASE = "https://api.jikan.moe/v4"

RSS_ICON = '<svg viewBox="0 0 24 24" width="10" height="10" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round" style="margin-right:5px;flex-shrink:0;opacity:.7;"><path d="M4 11a9 9 0 0 1 9 9"></path><path d="M4 4a16 16 0 0 1 16 16"></path><circle cx="5" cy="19" r="1"></circle></svg>'
CLOCK_ICON = '<svg width="10" height="10" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="min-width:10px;opacity:.6;"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>'
CHECK_ICON = '<svg viewBox="0 0 24 24" width="10" height="10" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round" style="margin-right:4px;flex-shrink:0;"><polyline points="20 6 9 17 4 12"></polyline></svg>'
STAR_ICON = '<svg viewBox="0 0 24 24" width="10" height="10" fill="currentColor" stroke="none" style="margin-right:3px;flex-shrink:0;vertical-align:-1px;"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>'

# ── CSS ──────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    header[data-testid="stHeader"],
    div[data-testid="stToolbar"],
    #MainMenu, footer { display: none !important; }

    .block-container, [data-testid="block-container"], .stMainBlockContainer {
        max-width: 1560px !important;
        width: 100% !important;
        padding: 2.5rem 2rem 5rem !important;
        margin: 0 auto !important;
    }

    /* ── Design tokens ───────────────────────────── */
    :root {
        --bg:              #0d0d0e;
        --surface:         rgba(255, 255, 255, 0.028);
        --surface-hover:   rgba(255, 255, 255, 0.055);
        --border:          rgba(255, 255, 255, 0.085);
        --border-hover:    rgba(255, 255, 255, 0.20);
        --text-1:          #e3ddd6;
        --text-2:          #7d7870;
        --text-3:          #5a5550;
        --accent:          #c87038;
        --accent-dim:      rgba(200, 112, 56, 0.12);
        --badge-bg:        rgba(200, 112, 56, 0.10);
        --badge-text:      #c87038;
        --badge-border:    rgba(200, 112, 56, 0.28);
        --green:           #5a9e6f;
        --green-bg:        rgba(90, 158, 111, 0.10);
        --green-border:    rgba(90, 158, 111, 0.24);
        --r-card:          4px;
        --r-sm:            3px;
        --font-display:    'Inter', system-ui, sans-serif;
        --font-body:       'Inter', system-ui, sans-serif;
        --font-mono:       'Inter', system-ui, sans-serif;
    }
    [data-theme="light"] {
        --bg:              #f4efe7;
        --surface:         rgba(0, 0, 0, 0.03);
        --surface-hover:   rgba(0, 0, 0, 0.06);
        --border:          rgba(0, 0, 0, 0.09);
        --border-hover:    rgba(0, 0, 0, 0.22);
        --text-1:          #1a1510;
        --text-2:          #6b6158;
        --text-3:          #8c8079;
        --accent:          #9b5220;
        --accent-dim:      rgba(155, 82, 32, 0.10);
        --badge-bg:        rgba(155, 82, 32, 0.09);
        --badge-text:      #9b5220;
        --badge-border:    rgba(155, 82, 32, 0.24);
        --green:           #3d7a52;
        --green-bg:        rgba(61, 122, 82, 0.09);
        --green-border:    rgba(61, 122, 82, 0.22);
    }

    /* ── Base ──────────────────────────────────────── */
    html, body, [class*="css"], .stApp {
        font-family: var(--font-body) !important;
        background-color: var(--bg) !important;
    }
    div[data-testid="stAppViewContainer"], .main {
        background-color: var(--bg) !important;
        transition: background-color 0.3s ease;
    }

    /* ── Scrollbar ─────────────────────────────────── */
    ::-webkit-scrollbar { width: 4px; height: 4px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(255,255,255,.12); border-radius: 2px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,.22); }

    /* ── Tabs ──────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        background: transparent;
        border-bottom: 1px solid var(--border);
        border-radius: 0;
        padding: 0;
        gap: 0;
        justify-content: flex-start;
        width: 100%;
        margin: 0 0 2rem;
        box-shadow: none;
    }
    .stTabs [data-baseweb="tab"] {
        height: 42px;
        border-radius: 0 !important;
        padding: 0 1.4rem;
        font-family: var(--font-body) !important;
        font-weight: 500;
        font-size: .902rem;
        letter-spacing: .02em;
        text-transform: none;
        color: var(--text-2) !important;
        background: transparent !important;
        border: none !important;
        border-bottom: 2px solid transparent !important;
        white-space: nowrap;
        transition: color .18s ease, border-color .18s ease;
    }
    .stTabs [aria-selected="true"] {
        background: transparent !important;
        color: var(--text-1) !important;
        border: none !important;
        border-bottom: 2px solid var(--accent) !important;
        box-shadow: none !important;
        text-shadow: none !important;
        font-weight: 600 !important;
    }
    .stTabs [data-baseweb="tab"]:hover {
        color: var(--text-1) !important;
    }
    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"] { display: none !important; }

    /* ── Section header ────────────────────────────── */
    .section-hdr {
        display: flex;
        align-items: baseline;
        gap: 12px;
        margin: 0 0 18px;
        padding-bottom: 12px;
        border-bottom: 1px solid var(--border);
    }
    .section-hdr-cat {
        font-family: var(--font-mono);
        font-size: .682rem;
        font-weight: 500;
        color: var(--accent);
        letter-spacing: .12em;
        text-transform: uppercase;
        flex-shrink: 0;
    }
    .section-hdr h2 {
        font-family: var(--font-display) !important;
        font-size: 1.265rem;
        font-weight: 700;
        color: var(--text-1);
        margin: 0;
        letter-spacing: -.01em;
    }
    .section-pill {
        margin-left: auto;
        font-size: .638rem;
        font-weight: 500;
        color: var(--text-3);
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 2px;
        padding: 2px 8px;
        letter-spacing: .06em;
        font-family: var(--font-mono);
    }

    /* ── News card ─────────────────────────────────── */
    .news-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: var(--r-card);
        margin-bottom: 18px;
        color: var(--text-1);
        transition: background .22s ease, border-color .22s ease, transform .22s ease;
        height: 420px;
        display: flex;
        flex-direction: column;
        position: relative;
        overflow: hidden;
    }
    .news-card:hover {
        background: var(--surface-hover);
        border-color: var(--border-hover);
        transform: translateY(-3px);
        box-shadow: 0 8px 32px rgba(0,0,0,.35);
    }
    .card-link { position: absolute; inset: 0; z-index: 10; cursor: pointer; }

    .card-img {
        width: 100%;
        height: 175px;
        flex-shrink: 0;
        background-size: cover;
        background-position: center;
        position: relative;
        filter: brightness(0.88);
        transition: filter .22s ease;
    }
    .news-card:hover .card-img { filter: brightness(0.96); }
    .card-img::after {
        content: '';
        position: absolute;
        bottom: 0; left: 0; right: 0;
        height: 48px;
        background: linear-gradient(to bottom, transparent, var(--bg));
        opacity: 0.65;
    }
    .card-flag {
        position: absolute;
        top: 10px; right: 12px;
        z-index: 2;
        filter: drop-shadow(0 1px 4px rgba(0,0,0,.7));
        border-radius: 2px;
        overflow: hidden;
    }
    .card-body {
        padding: 14px 16px 16px;
        display: flex;
        flex-direction: column;
        flex-grow: 1;
        overflow: hidden;
    }
    .source-badge {
        display: inline-flex;
        align-items: center;
        background: var(--badge-bg);
        color: var(--badge-text);
        padding: 2px 8px;
        border-radius: 2px;
        font-size: .638rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: .1em;
        margin-bottom: 9px;
        border: 1px solid var(--badge-border);
        width: fit-content;
        font-family: var(--font-mono);
    }
    .badge-free {
        background: var(--green-bg) !important;
        color: var(--green) !important;
        border-color: var(--green-border) !important;
        font-size: .616rem !important;
        padding: 2px 7px !important;
        margin-bottom: 0 !important;
    }
    .news-title {
        color: var(--text-1);
        font-family: var(--font-display) !important;
        font-size: 1.045rem;
        font-weight: 600;
        line-height: 1.45;
        margin-bottom: 8px;
        transition: color .18s ease;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    .news-card:hover .news-title { color: var(--accent); }
    .news-meta {
        font-size: .704rem;
        color: var(--text-3);
        margin-bottom: 8px;
        display: flex;
        align-items: center;
        gap: 4px;
        font-family: var(--font-mono);
    }
    .news-summary {
        font-size: .902rem;
        line-height: 1.6;
        color: var(--text-2);
        flex-grow: 1;
        display: -webkit-box;
        -webkit-line-clamp: 3;
        -webkit-box-orient: vertical;
        overflow: hidden;
    }
    a { text-decoration: none !important; }

    /* ── Game / Anime list rows ────────────────────── */
    .game-row {
        display: flex;
        align-items: center;
        gap: 12px;
        background: var(--surface);
        border: 1px solid var(--border);
        border-left: 2px solid var(--border-hover);
        border-radius: var(--r-sm);
        padding: 10px 12px;
        margin-bottom: 7px;
        position: relative;
        cursor: pointer;
        transition: background .2s ease, border-color .2s ease, transform .2s ease;
        text-decoration: none !important;
    }
    .game-row:hover {
        background: var(--surface-hover);
        border-left-color: var(--accent);
        border-color: var(--border-hover);
        transform: translateX(4px);
    }
    .game-row-thumb {
        flex-shrink: 0;
        border-radius: 2px;
        background-size: cover;
        background-position: center;
        background-repeat: no-repeat;
        background-color: rgba(255,255,255,.04);
        border: 1px solid var(--border);
        filter: brightness(0.88);
        transition: filter .2s;
    }
    .game-row:hover .game-row-thumb { filter: brightness(1.0); }
    .game-row-body { flex-grow: 1; overflow: hidden; min-width: 0; }
    .game-row-title {
        color: var(--text-1);
        font-size: .902rem;
        font-weight: 500;
        line-height: 1.35;
        margin-bottom: 4px;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        transition: color .18s;
    }
    .game-row:hover .game-row-title { color: var(--accent); }
    .game-row-meta {
        font-size: .682rem;
        color: var(--text-3);
        font-family: var(--font-mono);
    }

    /* ── Pagination ────────────────────────────────── */
    .pagination-row,
    .pagination-row > [data-testid="stColumn"],
    .pagination-row [data-testid="stVerticalBlock"],
    .pagination-row [data-testid="stElementContainer"],
    .pagination-row [data-testid="stMarkdownContainer"],
    .pagination-row div.stButton {
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        padding: 0 !important;
        margin: 0 !important;
        min-height: 0 !important;
        gap: 0 !important;
    }
    .pagination-row [data-testid="stVerticalBlock"] {
        flex-direction: column !important;
    }
    .pagination-label {
        display: flex;
        align-items: center;
        justify-content: center;
        height: 36px;
        width: 100%;
        color: var(--text-2);
        font-weight: 500;
        font-size: .748rem;
        letter-spacing: .08em;
        font-family: var(--font-mono);
        white-space: nowrap;
    }
    .pagination-row div.stButton > button {
        width: 36px !important;
        height: 36px !important;
        border-radius: 2px !important;
        padding: 0 !important;
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-2) !important;
        font-size: .858rem !important;
        transition: all .18s ease !important;
        display: flex !important;
        align-items: center !important;
        justify-content: center !important;
        line-height: 1 !important;
        flex-shrink: 0 !important;
    }
    .pagination-row div.stButton > button:hover {
        background: var(--surface-hover) !important;
        border-color: var(--border-hover) !important;
        color: var(--text-1) !important;
    }
    .pagination-row div.stButton > button:disabled {
        opacity: .2 !important;
        transform: none !important;
    }

    /* ── Alerts ────────────────────────────────────── */
    div[data-testid="stAlert"] {
        border-radius: var(--r-sm) !important;
        border-left-width: 2px !important;
    }

    /* ── Expiry labels ─────────────────────────────── */
    .expiry-ok     { color: var(--text-3); font-family: var(--font-mono); }
    .expiry-soon   { color: #d4a017; font-weight: 600; font-family: var(--font-mono); }
    .expiry-urgent { color: #c94040; font-weight: 600; font-family: var(--font-mono); }

    /* ── Select overrides ──────────────────────────── */
    .stSelectbox label {
        font-size: .792rem !important;
        color: var(--text-2) !important;
        font-family: var(--font-mono) !important;
        text-transform: uppercase !important;
        letter-spacing: .08em !important;
    }
    div[data-baseweb="select"] {
        background: var(--surface) !important;
    }
</style>
""", unsafe_allow_html=True)

# ── Theme toggle ──────────────────────────────────────────────────────────────
components.html("""
<script>
(function() {
    var p = window.parent.document;
    if (p.getElementById('theme-btn')) return;
    var btn = p.createElement('button');
    btn.id = 'theme-btn';
    var sun = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>';
    var moon = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
    var light = false;
    btn.style.cssText = [
        'position:fixed','bottom:24px','right:24px',
        'width:40px','height:40px',
        'border-radius:4px',
        'border:1px solid rgba(255,255,255,0.14)',
        'background:rgba(20,18,16,0.92)',
        'color:#c87038','cursor:pointer','z-index:9999999',
        'box-shadow:0 2px 12px rgba(0,0,0,0.5)',
        'backdrop-filter:blur(8px)','-webkit-backdrop-filter:blur(8px)',
        'transition:all .22s ease',
        'display:flex','align-items:center','justify-content:center','outline:none'
    ].join(';');
    btn.innerHTML = sun;
    btn.onmouseover = function() { btn.style.borderColor = 'rgba(255,255,255,0.28)'; };
    btn.onmouseout  = function() { btn.style.borderColor = light ? 'rgba(0,0,0,0.14)' : 'rgba(255,255,255,0.14)'; };
    btn.onclick = function() {
        light = !light;
        if (light) {
            p.documentElement.setAttribute('data-theme','light');
            btn.innerHTML = moon;
            btn.style.background = 'rgba(240,234,224,0.95)';
            btn.style.color = '#9b5220';
        } else {
            p.documentElement.removeAttribute('data-theme');
            btn.innerHTML = sun;
            btn.style.background = 'rgba(20,18,16,0.92)';
            btn.style.color = '#c87038';
        }
    };
    p.body.appendChild(btn);
})();
</script>
""", height=0, width=0)

# ── Pagination row marker ─────────────────────────────────────────────────────
components.html("""
<script>
(function() {
    var p = window.parent.document;
    function mark() {
        p.querySelectorAll('.pagination-label').forEach(function(label) {
            var block = label.closest('[data-testid="stHorizontalBlock"]');
            if (block && !block.classList.contains('pagination-row')) {
                block.classList.add('pagination-row');
            }
        });
    }
    mark();
    if (!window.parent._paginationObserver) {
        window.parent._paginationObserver = new MutationObserver(mark);
        window.parent._paginationObserver.observe(p.body, {childList: true, subtree: true});
    }
})();
</script>
""", height=0, width=0)

# ── Tab persistence ───────────────────────────────────────────────────────────
components.html("""
<script>
(function() {
    var p = window.parent.document;
    var TAB_KEYS = ['ai', 'gaming', 'anime'];
    var LS_KEY = '_da_active_tab';

    function getTabs() {
        return p.querySelectorAll('[data-baseweb="tab"]');
    }

    function attachListeners() {
        getTabs().forEach(function(tab, idx) {
            if (tab._daTracked) return;
            tab._daTracked = true;
            tab.addEventListener('click', function() {
                try { window.parent.localStorage.setItem(LS_KEY, TAB_KEYS[idx]); } catch(e) {}
            });
        });
    }

    function restoreTab() {
        if (window.parent._daTabRestored) { attachListeners(); return; }
        var tabs = getTabs();
        if (!tabs.length) return;
        window.parent._daTabRestored = true;
        var saved;
        try { saved = window.parent.localStorage.getItem(LS_KEY); } catch(e) {}
        var idx = TAB_KEYS.indexOf(saved);
        if (idx > 0 && tabs[idx]) { tabs[idx].click(); }
        attachListeners();
    }

    setTimeout(restoreTab, 180);

    if (!window.parent._daTabObserver) {
        window.parent._daTabObserver = new MutationObserver(function() {
            attachListeners();
            if (!window.parent._daTabRestored) restoreTab();
        });
        window.parent._daTabObserver.observe(p.body, {childList: true, subtree: true});
    }
})();
</script>
""", height=0, width=0)

# ── Session state ─────────────────────────────────────────────────────────────
for _key in ("free_games_page", "ai_news_page", "games_news_page", "anime_news_page"):
    if _key not in st.session_state:
        st.session_state[_key] = 0

# ── On-visit refresh ──────────────────────────────────────────────────────────
_STALE_AFTER_MINUTES = 30
_fetch_lock = threading.Lock()


def _background_fetch():
    if not _fetch_lock.acquire(blocking=False):
        return
    try:
        import sys
        sys.path.insert(0, "/app")
        from main import fetch_all_data
        fetch_all_data()
    except Exception as e:
        print(f"[dashboard] on-visit fetch error: {e}")
    finally:
        _fetch_lock.release()


def _trigger_on_visit_refresh():
    if st.session_state.get("_visit_fetch_done"):
        return
    st.session_state["_visit_fetch_done"] = True
    try:
        age_min = (time.time() - os.path.getmtime(AI_NEWS_FILE)) / 60
        if age_min < _STALE_AFTER_MINUTES:
            return
    except OSError:
        pass
    threading.Thread(target=_background_fetch, daemon=True).start()


_trigger_on_visit_refresh()


# ── Helpers ───────────────────────────────────────────────────────────────────

def format_date(date_str):
    if not date_str:
        return ""
    try:
        return parsedate_to_datetime(date_str).strftime('%d %b %Y · %H:%M')
    except Exception:
        return date_str


def strip_html(text):
    if not text:
        return ""
    return _HTML_TAG_RE.sub('', text)


def get_fallback_image(title, summary=""):
    text = (title + " " + summary).lower()
    if any(k in text for k in ["ai", "sztuczn", "openai", "chatgpt", "llm", "model", "inteligencj"]):
        return "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&w=600&q=80"
    if any(k in text for k in ["robot", "machine learning", "hardware", "chip"]):
        return "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?auto=format&fit=crop&w=600&q=80"
    if any(k in text for k in ["xbox", "playstation", "nintendo", "console", "sony"]):
        return "https://images.unsplash.com/photo-1605901309584-818e25960b8f?auto=format&fit=crop&w=600&q=80"
    if any(k in text for k in ["pc", "steam", "epic", "valve"]):
        return "https://images.unsplash.com/photo-1587202372634-32705e3bf49c?auto=format&fit=crop&w=600&q=80"
    if any(k in text for k in ["anime", "manga", "shonen", "seinen", "isekai"]):
        return "https://images.unsplash.com/photo-1578632767115-351597cf2477?auto=format&fit=crop&w=600&q=80"
    if any(k in text for k in ["gra", "game", "rpg", "fps", "multiplayer", "trailer"]):
        return "https://images.unsplash.com/photo-1552820728-8b83bb6b773f?auto=format&fit=crop&w=600&q=80"
    return "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=600&q=80"


def parse_source(source_full):
    parts = source_full.split(" ", 1)
    if len(parts) == 2 and any(not c.isascii() for c in parts[0]):
        return parts[0], parts[1]
    return "", source_full


def render_flag(flag):
    if not flag or flag not in FLAG_MAP or not FLAG_MAP[flag]:
        return ""
    return f'<div class="card-flag"><img src="{FLAG_MAP[flag]}" width="22" alt=""></div>'


def parse_end_date(end_date_str):
    if not end_date_str or str(end_date_str).strip().upper() == "N/A":
        return None
    try:
        return datetime.strptime(str(end_date_str).strip(), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def is_expired(end_date_str):
    dt = parse_end_date(end_date_str)
    return dt is not None and datetime.now() > dt


def format_end_date(end_date_str):
    dt = parse_end_date(end_date_str)
    return dt.strftime("%d %b %Y") if dt else None


def expiry_class(end_date_str):
    dt = parse_end_date(end_date_str)
    if dt is None:
        return ""
    days = (dt - datetime.now()).days
    if days < 1:
        return "expiry-urgent"
    if days <= 3:
        return "expiry-soon"
    return "expiry-ok"


def count_items(json_file):
    if not os.path.exists(json_file):
        return 0
    try:
        with open(json_file, "r", encoding="utf-8") as f:
            return len(json.load(f))
    except Exception:
        return 0


def section_header(cat, title, count=None):
    pill = f'<span class="section-pill">{count}</span>' if count else ""
    st.markdown(
        f'<div class="section-hdr">'
        f'<span class="section-hdr-cat">{cat}</span>'
        f'<h2>{title}</h2>'
        f'{pill}</div>',
        unsafe_allow_html=True
    )


def render_pagination(page_key, total_pages, prev_key, next_key, centered=False):
    if total_pages <= 1:
        return
    if centered:
        _, pc1, pc2, pc3, _ = st.columns([3, 1, 2, 1, 3], vertical_alignment="center")
    else:
        pc1, pc2, pc3 = st.columns([1, 2, 1], vertical_alignment="center")
    with pc1:
        if st.button("◀", key=prev_key, disabled=(st.session_state[page_key] <= 0)):
            st.session_state[page_key] -= 1
            st.rerun()
    with pc2:
        st.markdown(
            f"<div class='pagination-label'>{st.session_state[page_key] + 1} / {total_pages}</div>",
            unsafe_allow_html=True,
        )
    with pc3:
        if st.button("▶", key=next_key, disabled=(st.session_state[page_key] >= total_pages - 1)):
            st.session_state[page_key] += 1
            st.rerun()


def render_news_cards(json_file_path, num_cols=3, per_page=None, page_key=None):
    if not os.path.exists(json_file_path):
        st.warning("Data not yet available — waiting for the first fetch.")
        return
    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            items = json.load(f)
    except Exception:
        st.error("Failed to load data. Cache may be updating — please wait.")
        return
    if not items:
        st.info("No articles available yet.")
        return

    def _pub_ts(item):
        try:
            return parsedate_to_datetime(item.get("published", "")).timestamp()
        except Exception:
            return 0.0

    items.sort(key=_pub_ts, reverse=True)

    if per_page and page_key:
        total_pages = max(1, (len(items) + per_page - 1) // per_page)
        if st.session_state[page_key] >= total_pages:
            st.session_state[page_key] = total_pages - 1
        start = st.session_state[page_key] * per_page
        items = items[start:start + per_page]
    else:
        total_pages = 1

    cols = st.columns(num_cols, gap="medium")
    for i, item in enumerate(items):
        flag, source_name = parse_source(item.get("source", ""))
        image_url = item.get("image") or get_fallback_image(item.get("title", ""), item.get("summary", ""))
        summary = strip_html(item.get("summary", ""))[:240]

        card_html = f"""<div class="news-card">
<a href="{item['link']}" target="_blank" class="card-link" aria-label="{item['title']}"></a>
<div class="card-img" style="background-image:url('{image_url}');">{render_flag(flag)}</div>
<div class="card-body">
<span class="source-badge">{RSS_ICON}{source_name}</span>
<div class="news-title">{item['title']}</div>
<div class="news-meta">{CLOCK_ICON}&nbsp;{format_date(item.get('published', ''))}</div>
<div class="news-summary">{summary}…</div>
</div></div>"""
        with cols[i % num_cols]:
            st.markdown(card_html, unsafe_allow_html=True)

    if per_page and page_key and total_pages > 1:
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        render_pagination(page_key, total_pages,
                          prev_key=f"{page_key}_prev", next_key=f"{page_key}_next",
                          centered=True)


# ── Anime genre search ────────────────────────────────────────────────────────

def fetch_genres():
    if "jikan_genres" not in st.session_state:
        try:
            resp = requests.get(f"{JIKAN_BASE}/genres/anime", timeout=8)
            data = resp.json().get("data", [])
            st.session_state.jikan_genres = sorted(data, key=lambda g: g["name"])
        except Exception:
            st.session_state.jikan_genres = []
    return st.session_state.jikan_genres


def fetch_anime_by_genre(genre_id, sort_by="score"):
    cache_key = f"jikan_{genre_id}_{sort_by}"
    if cache_key not in st.session_state:
        try:
            resp = requests.get(
                f"{JIKAN_BASE}/anime",
                params={"genres": genre_id, "order_by": sort_by, "sort": "desc", "limit": 20, "sfw": "true"},
                timeout=10
            )
            st.session_state[cache_key] = resp.json().get("data", [])
        except Exception:
            st.session_state[cache_key] = []
    return st.session_state[cache_key]


def render_anime_row(anime):
    title = anime.get("title", "Unknown")
    score = anime.get("score")
    episodes = anime.get("episodes")
    year = anime.get("year", "")
    status = (anime.get("status") or "").replace("Finished Airing", "Finished").replace("Currently Airing", "Airing")
    image_url = anime.get("images", {}).get("jpg", {}).get("image_url", "")
    url = anime.get("url", "#")

    meta_parts = []
    if score:
        meta_parts.append(f"★ {score}")
    if year:
        meta_parts.append(str(year))
    if episodes:
        meta_parts.append(f"{episodes} ep")
    if status:
        meta_parts.append(status)
    meta = " · ".join(meta_parts)

    return f"""<a href="{url}" target="_blank" class="game-row">
<div class="game-row-thumb" style="width:56px;height:78px;background-image:url('{image_url}');"></div>
<div class="game-row-body">
<div class="game-row-title">{title}</div>
<div class="game-row-meta">{meta}</div>
</div></a>"""


# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_ai, tab_games, tab_anime = st.tabs(["AI & Technology", "Gaming", "Anime"])

# ── AI Tab ────────────────────────────────────────────────────────────────────
with tab_ai:
    n = count_items(AI_NEWS_FILE)
    section_header("AI / TECH", "Artificial Intelligence & Technology", n or None)
    render_news_cards(AI_NEWS_FILE, per_page=6, page_key="ai_news_page")

# ── Gaming Tab ────────────────────────────────────────────────────────────────
with tab_games:
    col_news, col_free = st.columns([2, 1], gap="large")

    with col_news:
        n = count_items(GAMES_NEWS_FILE)
        section_header("GAMING", "Gaming News", n or None)
        render_news_cards(GAMES_NEWS_FILE, num_cols=2, per_page=4, page_key="games_news_page")

    with col_free:
        section_header("FREE", "Free Games")

        if not os.path.exists(FREE_GAMES_FILE):
            st.info("Loading free games… please wait.")
        else:
            try:
                with open(FREE_GAMES_FILE, "r", encoding="utf-8") as f:
                    free_games = json.load(f)
            except Exception:
                free_games = []

            active_games = [g for g in free_games if not is_expired(g.get("end_date"))]

            if not active_games:
                st.info("No free games available right now.")
            else:
                total_pages = max(1, (len(active_games) + GAMES_PER_PAGE - 1) // GAMES_PER_PAGE)
                if st.session_state.free_games_page >= total_pages:
                    st.session_state.free_games_page = total_pages - 1

                # Card area height: 2 rows × (420px card + 18px margin) = 876px
                _GAMES_LIST_HEIGHT = 876

                start = st.session_state.free_games_page * GAMES_PER_PAGE
                rows_html = ""
                for game in active_games[start:start + GAMES_PER_PAGE]:
                    platforms = game.get("platforms", "")
                    worth = game.get("worth", "Paid")
                    end_label = format_end_date(game.get("end_date"))
                    cls = expiry_class(game.get("end_date"))
                    expiry_html = (
                        f' &nbsp;·&nbsp; <span class="{cls}">Until {end_label}</span>'
                        if end_label else ""
                    )
                    rows_html += f"""<a href="{game['link']}" target="_blank" class="game-row">
<div class="game-row-thumb" style="width:88px;height:56px;background-size:contain;background-image:url('{game.get('thumbnail', '')}');"></div>
<div class="game-row-body">
<div style="margin-bottom:4px;"><span class="source-badge badge-free">{CHECK_ICON}FREE · was {worth}</span></div>
<div class="game-row-title">{game['title']}</div>
<div class="game-row-meta">{platforms}{expiry_html}</div>
</div></a>"""

                st.markdown(
                    f'<div style="height:{_GAMES_LIST_HEIGHT}px;overflow-y:auto;'
                    f'padding-right:4px;">{rows_html}</div>',
                    unsafe_allow_html=True
                )

                if total_pages > 1:
                    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
                    render_pagination("free_games_page", total_pages,
                                      prev_key="prev_btn", next_key="next_btn")

# ── Anime Tab ─────────────────────────────────────────────────────────────────
with tab_anime:
    n = count_items(ANIME_NEWS_FILE)
    section_header("ANIME", "Anime News", n or None)
    render_news_cards(ANIME_NEWS_FILE, per_page=6, page_key="anime_news_page")

    st.markdown("<div style='height:24px'></div>", unsafe_allow_html=True)
    st.markdown(
        '<hr style="border:none;border-top:1px solid var(--border);margin:0 0 24px;">',
        unsafe_allow_html=True
    )

    section_header("SEARCH", "Browse by Genre")

    genres = fetch_genres()
    genre_names = ["— Select a genre —"] + [g["name"] for g in genres]

    sc1, sc2 = st.columns([3, 1])
    with sc1:
        selected_genre_name = st.selectbox(
            "Genre", genre_names, key="genre_select", label_visibility="collapsed"
        )
    with sc2:
        sort_option = st.selectbox(
            "Sort", ["Score", "Popularity", "Members"],
            key="genre_sort", label_visibility="collapsed"
        )

    sort_map = {"Score": "score", "Popularity": "popularity", "Members": "members"}
    sort_by = sort_map.get(sort_option, "score")

    if selected_genre_name != "— Select a genre —":
        selected_genre = next((g for g in genres if g["name"] == selected_genre_name), None)
        if selected_genre:
            with st.spinner("Fetching anime…"):
                results = fetch_anime_by_genre(selected_genre["mal_id"], sort_by)
            if results:
                for anime in results:
                    st.markdown(render_anime_row(anime), unsafe_allow_html=True)
            else:
                st.info("No results found for this genre.")
    else:
        st.markdown(
            '<div style="padding:40px 0;text-align:center;color:var(--text-3);'
            'font-family:var(--font-mono);font-size:.792rem;letter-spacing:.1em;">'
            'SELECT A GENRE TO BROWSE ANIME</div>',
            unsafe_allow_html=True
        )
