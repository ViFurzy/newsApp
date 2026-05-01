import streamlit as st
import streamlit.components.v1 as components
import json
import os
import re
import time
import threading
from datetime import datetime
from email.utils import parsedate_to_datetime
from PIL import Image

_FAVICON_PATH = os.path.join(os.path.dirname(__file__), "vNews_logo.ico")
_favicon = Image.open(_FAVICON_PATH) if os.path.exists(_FAVICON_PATH) else "⚡"

st.set_page_config(page_title="Daily Aggregator", page_icon=_favicon, layout="wide")

_HTML_TAG_RE = re.compile('<.*?>')

FLAG_MAP = {
    "🇺🇸": "https://flagcdn.com/w40/us.png",
    "🇵🇱": "https://flagcdn.com/w40/pl.png",
}

DATA_DIR = "/app/data"
AI_NEWS_FILE = os.path.join(DATA_DIR, "news.json")
GAMES_NEWS_FILE = os.path.join(DATA_DIR, "games_news.json")
FREE_GAMES_FILE = os.path.join(DATA_DIR, "free_games.json")

GAMES_PER_PAGE = 8

RSS_ICON = '<svg viewBox="0 0 24 24" width="11" height="11" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round" style="margin-right:5px;flex-shrink:0;opacity:.85;"><path d="M4 11a9 9 0 0 1 9 9"></path><path d="M4 4a16 16 0 0 1 16 16"></path><circle cx="5" cy="19" r="1"></circle></svg>'
CLOCK_ICON = '<svg width="11" height="11" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="min-width:11px;opacity:.7;"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>'
CHECK_ICON = '<svg viewBox="0 0 24 24" width="10" height="10" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round" style="margin-right:4px;flex-shrink:0;"><polyline points="20 6 9 17 4 12"></polyline></svg>'

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;500;600;700;800;900&family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');

    header[data-testid="stHeader"],
    div[data-testid="stToolbar"],
    #MainMenu, footer { display: none !important; }

    .block-container, [data-testid="block-container"], .stMainBlockContainer {
        max-width: 1560px !important;
        width: 100% !important;
        padding: 2.5rem 2rem 5rem !important;
        margin: 0 auto !important;
    }

    /* ── Design tokens ──────────────────────────── */
    :root {
        --bg:              #04090f;
        --card-fade:       rgba(4, 9, 15, 0.88);
        --card-fade-hover: rgba(4, 9, 15, 0.98);
        --surface:         rgba(0, 255, 247, 0.025);
        --surface-hover:   rgba(0, 255, 247, 0.058);
        --border:          rgba(0, 255, 247, 0.10);
        --border-accent:   rgba(0, 255, 247, 0.45);
        --text-1:          #cde8ed;
        --text-2:          #2e6475;
        --text-3:          #4d8fa3;
        --accent:          #00fff7;
        --accent-2:        #ff0080;
        --accent-glow:     rgba(0, 255, 247, 0.22);
        --badge-bg:        rgba(0, 255, 247, 0.07);
        --badge-text:      #00fff7;
        --badge-border:    rgba(0, 255, 247, 0.25);
        --green:           #00ff88;
        --green-bg:        rgba(0, 255, 136, 0.07);
        --green-border:    rgba(0, 255, 136, 0.25);
        --r-card:          5px;
        --r-sm:            3px;
        --font-display:    'Orbitron', sans-serif;
        --font-body:       'Space Grotesk', sans-serif;
        --font-mono:       'JetBrains Mono', monospace;
    }
    [data-theme="light"] {
        --bg:              #eaf5f8;
        --card-fade:       rgba(234, 245, 248, 0.88);
        --card-fade-hover: rgba(234, 245, 248, 0.99);
        --surface:         rgba(0, 102, 180, 0.04);
        --surface-hover:   rgba(0, 102, 180, 0.09);
        --border:          rgba(0, 102, 180, 0.13);
        --border-accent:   rgba(0, 102, 180, 0.50);
        --text-1:          #091826;
        --text-2:          #1e5570;
        --text-3:          #0f4060;
        --accent:          #005fb5;
        --accent-2:        #b5005f;
        --accent-glow:     rgba(0, 95, 181, 0.18);
        --badge-bg:        rgba(0, 95, 181, 0.08);
        --badge-text:      #004fa0;
        --badge-border:    rgba(0, 95, 181, 0.22);
        --green:           #007a44;
        --green-bg:        rgba(0, 122, 68, 0.08);
        --green-border:    rgba(0, 122, 68, 0.22);
    }

    /* ── Base ───────────────────────────────────── */
    html, body, [class*="css"], .stApp {
        font-family: var(--font-body), -apple-system, BlinkMacSystemFont, sans-serif !important;
    }

    /* Background: subtle grid + dual-tone radial blooms */
    div[data-testid="stAppViewContainer"], .main {
        background:
            linear-gradient(rgba(0,255,247,0.026) 1px, transparent 1px) 0 0 / 55px 55px,
            linear-gradient(90deg, rgba(0,255,247,0.026) 1px, transparent 1px) 0 0 / 55px 55px,
            radial-gradient(ellipse 80% 55% at 10% 0%,  rgba(0,255,247,.07)  0%, transparent 55%),
            radial-gradient(ellipse 60% 50% at 90% 100%, rgba(255,0,128,.05) 0%, transparent 55%),
            var(--bg) !important;
        background-attachment: fixed !important;
        transition: background 0.4s ease;
    }
    [data-theme="light"] div[data-testid="stAppViewContainer"],
    [data-theme="light"] .main {
        background:
            linear-gradient(rgba(0,95,181,0.04) 1px, transparent 1px) 0 0 / 48px 48px,
            linear-gradient(90deg, rgba(0,95,181,0.04) 1px, transparent 1px) 0 0 / 48px 48px,
            radial-gradient(ellipse 80% 55% at 10% 0%,  rgba(0,95,181,.07)  0%, transparent 55%),
            radial-gradient(ellipse 60% 50% at 90% 100%, rgba(181,0,95,.04) 0%, transparent 55%),
            var(--bg) !important;
    }

    /* ── Scrollbar ──────────────────────────────── */
    ::-webkit-scrollbar { width: 4px; height: 4px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(0,255,247,.18); border-radius: 2px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(0,255,247,.35); }

    /* ── Tabs ──────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        background: rgba(0,255,247,0.025);
        border: 1px solid var(--border);
        border-radius: 3px; padding: 4px; gap: 3px;
        justify-content: center; width: fit-content; margin: 0 auto 2.5rem;
        box-shadow: 0 0 32px -8px rgba(0,255,247,.14), inset 0 0 24px rgba(0,255,247,.02);
    }
    .stTabs [data-baseweb="tab"] {
        height: 40px; border-radius: 2px !important;
        padding: 0 1.9rem;
        font-family: var(--font-display) !important;
        font-weight: 600; font-size: .66rem; letter-spacing: .18em;
        text-transform: uppercase;
        color: var(--text-2) !important;
        background: transparent !important; border: none !important;
        white-space: nowrap; transition: all .22s ease;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(0,255,247,0.09) !important;
        color: var(--accent) !important; border: none !important;
        box-shadow: 0 0 22px -4px var(--accent-glow), inset 0 0 14px rgba(0,255,247,.05) !important;
        text-shadow: 0 0 12px rgba(0,255,247,.55) !important;
    }
    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"] { display: none !important; }

    /* ── Section header ─────────────────────────── */
    .section-hdr {
        display: flex; align-items: center; gap: 10px;
        margin: 0 0 20px; padding-bottom: 14px;
        border-bottom: 1px solid var(--border);
        position: relative;
    }
    .section-hdr::after {
        content: ''; position: absolute; bottom: -1px; left: 0;
        width: 48px; height: 1px;
        background: var(--accent);
        box-shadow: 0 0 8px var(--accent);
    }
    .section-hdr-prefix {
        font-family: var(--font-mono); font-size: .72rem;
        color: var(--accent); opacity: 0.65;
        flex-shrink: 0; user-select: none;
    }
    .section-hdr h2 {
        font-family: var(--font-display) !important;
        font-size: .72rem; font-weight: 700; color: var(--text-1);
        margin: 0; letter-spacing: .14em; text-transform: uppercase;
    }
    .section-pill {
        margin-left: auto; font-size: .58rem; font-weight: 600;
        color: var(--badge-text); background: var(--badge-bg);
        border: 1px solid var(--badge-border); border-radius: 2px;
        padding: 2px 9px; letter-spacing: .1em; text-transform: uppercase;
        font-family: var(--font-mono);
    }

    /* ── News card ──────────────────────────────── */
    .news-card {
        background: var(--surface);
        border: 1px solid var(--border);
        border-top: 2px solid rgba(0,255,247,0.32);
        border-radius: var(--r-card);
        margin-bottom: 18px; color: var(--text-1);
        transition: transform .3s cubic-bezier(.34,1.26,.64,1),
                    box-shadow .3s ease, border-color .3s ease;
        height: 420px;
        display: flex; flex-direction: column;
        position: relative; overflow: hidden;
        box-shadow: 0 2px 22px rgba(0,0,0,.45), inset 0 0 40px rgba(0,255,247,.008);
    }
    /* top glimmer line */
    .news-card::before {
        content: '';
        position: absolute; top: 0; left: 0; right: 0; height: 1px;
        background: linear-gradient(90deg, transparent 0%, var(--accent) 50%, transparent 100%);
        opacity: 0.45; z-index: 1; pointer-events: none;
    }
    /* corner cut */
    .news-card::after {
        content: '';
        position: absolute; bottom: 0; right: 0;
        width: 0; height: 0;
        border-style: solid;
        border-width: 0 0 20px 20px;
        border-color: transparent transparent rgba(0,255,247,0.22) transparent;
        pointer-events: none; z-index: 2;
    }
    .news-card:hover {
        transform: translateY(-7px);
        box-shadow: 0 22px 55px -10px rgba(0,0,0,.55), 0 0 35px -6px var(--accent-glow);
        border-color: var(--border-accent);
        border-top-color: var(--accent);
    }
    .card-link { position: absolute; inset: 0; z-index: 10; cursor: pointer; }

    /* full-bleed image */
    .card-img {
        width: 100%; height: 178px; flex-shrink: 0;
        background-size: cover; background-position: center;
        position: relative;
        filter: saturate(0.78) brightness(0.88);
        transition: filter .3s ease;
    }
    .news-card:hover .card-img { filter: saturate(1.0) brightness(0.95); }
    .card-img::after {
        content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 52px;
        background: linear-gradient(to bottom, transparent, var(--card-fade));
        transition: background .3s ease;
    }
    .news-card:hover .card-img::after {
        background: linear-gradient(to bottom, transparent, var(--card-fade-hover));
    }
    .card-flag {
        position: absolute; top: 10px; right: 12px; z-index: 2;
        filter: drop-shadow(0 2px 6px rgba(0,0,0,.75));
        border-radius: 2px; overflow: hidden;
    }

    /* card content */
    .card-body {
        padding: 14px 18px 18px;
        display: flex; flex-direction: column;
        flex-grow: 1; overflow: hidden;
    }
    .source-badge {
        display: inline-flex; align-items: center;
        background: var(--badge-bg); color: var(--badge-text);
        padding: 3px 10px; border-radius: 2px;
        font-size: .6rem; font-weight: 500;
        text-transform: uppercase; letter-spacing: .1em;
        margin-bottom: 10px; border: 1px solid var(--badge-border);
        width: fit-content;
        font-family: var(--font-mono);
    }
    .badge-free {
        background: var(--green-bg) !important; color: var(--green) !important;
        border-color: var(--green-border) !important;
        font-size: .58rem !important; padding: 2px 9px !important;
        margin-bottom: 0 !important;
        text-shadow: 0 0 8px rgba(0,255,136,.45) !important;
    }
    .news-title {
        color: var(--text-1); font-size: .95rem; font-weight: 600;
        line-height: 1.5; margin-bottom: 9px;
        transition: color .2s ease, text-shadow .2s ease;
        display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
        font-family: var(--font-body);
    }
    .news-card:hover .news-title {
        color: var(--accent);
        text-shadow: 0 0 14px rgba(0,255,247,.28);
    }
    .news-meta {
        font-size: .68rem; color: var(--text-2); margin-bottom: 10px;
        display: flex; align-items: center; gap: 5px; font-weight: 500;
        font-family: var(--font-mono); letter-spacing: .02em;
    }
    .news-summary {
        font-size: .84rem; line-height: 1.65; color: var(--text-3); flex-grow: 1;
        display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
    }
    a { text-decoration: none !important; }

    /* ── Game list rows ─────────────────────────── */
    .game-row {
        display: flex; align-items: center; gap: 13px;
        background: var(--surface);
        border: 1px solid var(--border);
        border-left: 2px solid rgba(0,255,247,0.32);
        border-radius: var(--r-sm); padding: 11px 13px;
        margin-bottom: 8px; position: relative; cursor: pointer;
        transition: transform .22s ease, box-shadow .22s ease, border-color .22s ease;
        text-decoration: none !important;
    }
    .game-row:hover {
        transform: translateX(6px);
        box-shadow: 0 0 26px -6px var(--accent-glow);
        border-color: var(--border-accent);
        border-left-color: var(--accent);
    }
    .game-row-thumb {
        width: 88px; height: 56px; flex-shrink: 0;
        border-radius: 2px;
        background-size: contain; background-position: center; background-repeat: no-repeat;
        background-color: rgba(0,255,247,0.04);
        border: 1px solid var(--border);
        filter: saturate(0.82); transition: filter .2s;
    }
    .game-row:hover .game-row-thumb { filter: saturate(1.05); }
    [data-theme="light"] .game-row-thumb { background-color: rgba(0,0,0,.06); }
    .game-row-body { flex-grow: 1; overflow: hidden; min-width: 0; }
    .game-row-title {
        color: var(--text-1); font-size: .83rem; font-weight: 600;
        line-height: 1.35; margin-bottom: 5px;
        display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
        transition: color .2s, text-shadow .2s;
        font-family: var(--font-body);
    }
    .game-row:hover .game-row-title {
        color: var(--accent);
        text-shadow: 0 0 10px rgba(0,255,247,.25);
    }
    .game-row-meta {
        font-size: .64rem; color: var(--text-2); font-weight: 500;
        font-family: var(--font-mono);
    }

    /* ── Pagination ─────────────────────────────── */
    /* .pagination-row is stamped by JS on the EXACT stHorizontalBlock.
       Every selector starts with it — nothing outside is touched.      */

    /* Flatten every Streamlit wrapper layer so all three cells share
       the same vertical midline.                                        */
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
    /* stVerticalBlock is a column-direction flex — keep that axis */
    .pagination-row [data-testid="stVerticalBlock"] {
        flex-direction: column !important;
    }

    .pagination-label {
        display: flex; align-items: center; justify-content: center;
        height: 38px; width: 100%;
        color: var(--accent);
        font-weight: 600; font-size: .7rem;
        letter-spacing: .18em; text-transform: uppercase;
        font-family: var(--font-mono);
        text-shadow: 0 0 8px rgba(0,255,247,.4);
        white-space: nowrap;
    }
    .pagination-row div.stButton > button {
        width: 38px !important; height: 38px !important;
        border-radius: 2px !important; padding: 0 !important;
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        color: var(--accent) !important;
        font-size: .82rem !important;
        transition: all .22s ease !important;
        display: flex !important; align-items: center !important;
        justify-content: center !important; line-height: 1 !important;
        flex-shrink: 0 !important;
    }
    .pagination-row div.stButton > button:hover {
        background: rgba(0,255,247,.09) !important;
        border-color: var(--accent) !important;
        box-shadow: 0 0 18px -3px var(--accent-glow) !important;
        transform: scale(1.1) !important;
    }
    .pagination-row div.stButton > button:disabled {
        opacity: .15 !important; transform: none !important; box-shadow: none !important;
    }

    /* ── Alerts ─────────────────────────────────── */
    div[data-testid="stAlert"] {
        border-radius: var(--r-sm) !important;
        border-left-width: 2px !important;
    }

    /* ── Expiry labels ──────────────────────────── */
    .expiry-ok     { color: var(--text-2); font-family: var(--font-mono); }
    .expiry-soon   { color: #fbbf24; font-weight: 600; font-family: var(--font-mono); }
    .expiry-urgent { color: #ff4060; font-weight: 600; font-family: var(--font-mono);
                     text-shadow: 0 0 8px rgba(255,64,96,.4); }
</style>
""", unsafe_allow_html=True)

# Theme toggle — injected into parent document once
components.html("""
<script>
(function() {
    const p = window.parent.document;
    if (p.getElementById('theme-btn')) return;
    const btn = p.createElement('button');
    btn.id = 'theme-btn';
    const sun = `<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>`;
    const moon = `<svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`;
    let light = false;
    btn.style.cssText = [
        'position:fixed','bottom:28px','right:28px',
        'width:44px','height:44px',
        'border-radius:3px',
        'border:1px solid rgba(0,255,247,0.25)',
        'background:rgba(4,9,15,0.90)',
        'color:#00fff7','cursor:pointer','z-index:9999999',
        'box-shadow:0 0 22px -6px rgba(0,255,247,0.35)',
        'backdrop-filter:blur(12px)','-webkit-backdrop-filter:blur(12px)',
        'transition:all .28s cubic-bezier(.34,1.56,.64,1)',
        'display:flex','align-items:center','justify-content:center','outline:none'
    ].join(';');
    btn.innerHTML = sun;
    btn.onmouseover = () => {
        btn.style.transform = 'scale(1.1)';
        btn.style.boxShadow = '0 0 30px -4px rgba(0,255,247,0.55)';
    };
    btn.onmouseout  = () => {
        btn.style.transform = 'scale(1)';
        btn.style.boxShadow = light
            ? '0 0 22px -6px rgba(0,95,181,0.35)'
            : '0 0 22px -6px rgba(0,255,247,0.35)';
    };
    btn.onclick = () => {
        light = !light;
        if (light) {
            p.documentElement.setAttribute('data-theme','light');
            btn.innerHTML = moon;
            btn.style.background = 'rgba(234,245,248,0.96)';
            btn.style.color = '#005fb5';
            btn.style.border = '1px solid rgba(0,95,181,0.25)';
            btn.style.boxShadow = '0 0 22px -6px rgba(0,95,181,0.35)';
        } else {
            p.documentElement.removeAttribute('data-theme');
            btn.innerHTML = sun;
            btn.style.background = 'rgba(4,9,15,0.90)';
            btn.style.color = '#00fff7';
            btn.style.border = '1px solid rgba(0,255,247,0.25)';
            btn.style.boxShadow = '0 0 22px -6px rgba(0,255,247,0.35)';
        }
    };
    p.body.appendChild(btn);
})();
</script>
""", height=0, width=0)

# Pagination row marker — separate from theme toggle so it is never blocked
# by the theme button's early-return guard.
# The observer is stored on window.parent so it survives iframe reuse across
# Streamlit re-renders, and mark() runs immediately on each fresh iframe load.
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

for _key in ("free_games_page", "ai_news_page", "games_news_page"):
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


# ── Helpers ──────────────────────────────────────────────────────────────────

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
    if any(k in text for k in ["ai", "sztuczn", "inteligencj", "openai", "chatgpt", "llm", "model"]):
        return "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&w=600&q=80"
    if any(k in text for k in ["robot", "cyborg", "machine learning", "hardware", "chip"]):
        return "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?auto=format&fit=crop&w=600&q=80"
    if any(k in text for k in ["xbox", "playstation", "nintendo", "console", "sony", "microsoft"]):
        return "https://images.unsplash.com/photo-1605901309584-818e25960b8f?auto=format&fit=crop&w=600&q=80"
    if any(k in text for k in ["pc", "steam", "epic", "valve"]):
        return "https://images.unsplash.com/photo-1587202372634-32705e3bf49c?auto=format&fit=crop&w=600&q=80"
    if any(k in text for k in ["gra", "game", "rpg", "fps", "multiplayer", "studio", "trailer"]):
        return "https://images.unsplash.com/photo-1552820728-8b83bb6b773f?auto=format&fit=crop&w=600&q=80"
    if any(k in text for k in ["google", "apple", "meta", "tech", "business"]):
        return "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=600&q=80"
    return "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=600&q=80"


def parse_source(source_full):
    parts = source_full.split(" ", 1)
    if len(parts) == 2 and any(not c.isascii() for c in parts[0]):
        return parts[0], parts[1]
    return "", source_full


def render_flag(flag):
    if not flag:
        return ""
    if flag in FLAG_MAP:
        return f'<div class="card-flag"><img src="{FLAG_MAP[flag]}" width="24" alt=""></div>'
    return f'<div class="card-flag" style="font-size:1.4rem;font-family:\'Segoe UI Emoji\',\'Apple Color Emoji\',sans-serif;">{flag}</div>'


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
    if dt is None:
        return None
    return dt.strftime("%d %b %Y")

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


def section_header(icon, title, count=None):
    pill = f'<span class="section-pill">{count}</span>' if count else ""
    st.markdown(
        f'<div class="section-hdr">'
        f'<span class="section-hdr-prefix">//</span>'
        f'<h2>{icon}&nbsp; {title}</h2>'
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
        if st.button("◀", key=prev_key, help="Previous page",
                     disabled=(st.session_state[page_key] <= 0)):
            st.session_state[page_key] -= 1
            st.rerun()
    with pc2:
        st.markdown(
            f"<div class='pagination-label'>{st.session_state[page_key] + 1} / {total_pages}</div>",
            unsafe_allow_html=True,
        )
    with pc3:
        if st.button("▶", key=next_key, help="Next page",
                     disabled=(st.session_state[page_key] >= total_pages - 1)):
            st.session_state[page_key] += 1
            st.rerun()


def render_news_cards(json_file_path, num_cols=3, per_page=None, page_key=None):
    if not os.path.exists(json_file_path):
        st.warning("Data not yet available — waiting for the first fetch to complete.")
        return

    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            items = json.load(f)
    except Exception:
        st.error("Failed to load data. The cache may be updating — please wait.")
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
</div>
</div>"""
        with cols[i % num_cols]:
            st.markdown(card_html, unsafe_allow_html=True)

    if per_page and page_key and total_pages > 1:
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        render_pagination(page_key, total_pages,
                          prev_key=f"{page_key}_prev", next_key=f"{page_key}_next",
                          centered=True)


# ── Tabs ──────────────────────────────────────────────────────────────────────

tab_ai, tab_games = st.tabs(["⚡  AI News", "🎮  Gaming"])

with tab_ai:
    n = count_items(AI_NEWS_FILE)
    section_header("🗞️", "AI & Technology News", n or None)
    render_news_cards(AI_NEWS_FILE, per_page=6, page_key="ai_news_page")

with tab_games:
    col_news, col_free = st.columns([2, 1], gap="large")

    with col_news:
        n = count_items(GAMES_NEWS_FILE)
        section_header("🎮", "Gaming News", n or None)
        render_news_cards(GAMES_NEWS_FILE, num_cols=2, per_page=4, page_key="games_news_page")

    with col_free:
        section_header("⭐", "Free Games")

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
                st.info("No free games available at this time.")
            else:
                total_pages = max(1, (len(active_games) + GAMES_PER_PAGE - 1) // GAMES_PER_PAGE)

                if st.session_state.free_games_page >= total_pages:
                    st.session_state.free_games_page = total_pages - 1

                start = st.session_state.free_games_page * GAMES_PER_PAGE
                for game in active_games[start:start + GAMES_PER_PAGE]:
                    platforms = game.get("platforms", "")
                    worth = game.get("worth", "Paid")
                    end_label = format_end_date(game.get("end_date"))
                    cls = expiry_class(game.get("end_date"))
                    expiry_html = (
                        f' &nbsp;·&nbsp; <span class="{cls}">Until {end_label}</span>'
                        if end_label else ""
                    )
                    row_html = f"""<a href="{game['link']}" target="_blank" class="game-row">
<div class="game-row-thumb" style="background-image:url('{game.get('thumbnail', '')}');"></div>
<div class="game-row-body">
<div style="margin-bottom:5px;"><span class="source-badge badge-free">{CHECK_ICON}FREE · was {worth}</span></div>
<div class="game-row-title">{game['title']}</div>
<div class="game-row-meta">{platforms}{expiry_html}</div>
</div>
</a>"""
                    st.markdown(row_html, unsafe_allow_html=True)

                if total_pages > 1:
                    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
                    render_pagination("free_games_page", total_pages,
                                      prev_key="prev_btn", next_key="next_btn")
