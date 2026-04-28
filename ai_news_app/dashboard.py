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
CLOCK_ICON = '<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="min-width:12px;opacity:.7;"><circle cx="12" cy="12" r="10"></circle><polyline points="12 6 12 12 16 14"></polyline></svg>'
CHECK_ICON = '<svg viewBox="0 0 24 24" width="10" height="10" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round" style="margin-right:4px;flex-shrink:0;"><polyline points="20 6 9 17 4 12"></polyline></svg>'

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

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
        --bg:             #07111e;
        --card-fade:      rgba(7, 17, 30, 0.75);
        --card-fade-hover: rgba(7, 17, 30, 0.97);
        --surface:        rgba(13, 25, 48, 0.70);
        --surface-hover:  rgba(13, 25, 48, 0.96);
        --border:         rgba(148, 163, 184, 0.09);
        --border-accent:  rgba(124, 58, 237, 0.45);
        --text-1:         #f1f5f9;
        --text-2:         #64748b;
        --text-3:         #94a3b8;
        --accent:         #7c3aed;
        --accent-2:       #2563eb;
        --accent-glow:    rgba(124, 58, 237, 0.30);
        --badge-bg:       rgba(124, 58, 237, 0.10);
        --badge-text:     #a78bfa;
        --badge-border:   rgba(124, 58, 237, 0.22);
        --green:          #10b981;
        --green-bg:       rgba(16, 185, 129, 0.10);
        --green-border:   rgba(16, 185, 129, 0.22);
        --r-card:         18px;
        --r-sm:           10px;
    }
    [data-theme="light"] {
        --bg:             #eef2f9;
        --card-fade:      rgba(238, 242, 249, 0.8);
        --card-fade-hover: rgba(238, 242, 249, 1);
        --surface:        rgba(255, 255, 255, 0.82);
        --surface-hover:  rgba(255, 255, 255, 1);
        --border:         rgba(15, 23, 42, 0.08);
        --border-accent:  rgba(37, 99, 235, 0.42);
        --text-1:         #0f172a;
        --text-2:         #475569;
        --text-3:         #334155;
        --accent:         #2563eb;
        --accent-2:       #7c3aed;
        --accent-glow:    rgba(37, 99, 235, 0.22);
        --badge-bg:       rgba(37, 99, 235, 0.08);
        --badge-text:     #2563eb;
        --badge-border:   rgba(37, 99, 235, 0.20);
    }

    /* ── Base ───────────────────────────────────── */
    html, body, [class*="css"], .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    }
    div[data-testid="stAppViewContainer"], .main {
        background:
            radial-gradient(ellipse 75% 50% at 15% -5%,  rgba(124,58,237,.11) 0%, transparent 60%),
            radial-gradient(ellipse 60% 45% at 88% 100%, rgba(37,99,235,.08)  0%, transparent 60%),
            var(--bg) !important;
        background-attachment: fixed !important;
        transition: background 0.4s ease;
    }

    /* ── Scrollbar ──────────────────────────────── */
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(148,163,184,.18); border-radius: 99px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(148,163,184,.32); }

    /* ── Tabs — pill switcher ───────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        background: var(--surface);
        backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
        border: 1px solid var(--border);
        border-radius: 14px; padding: 5px; gap: 4px;
        justify-content: center; width: fit-content; margin: 0 auto 2.5rem;
        box-shadow: 0 4px 24px -4px rgba(0,0,0,.18);
    }
    .stTabs [data-baseweb="tab"] {
        height: 42px; border-radius: var(--r-sm) !important;
        padding: 0 1.7rem;
        font-weight: 600; font-size: .92rem; letter-spacing: .01em;
        color: var(--text-2) !important;
        background: transparent !important; border: none !important;
        white-space: nowrap; transition: all .22s ease;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, var(--accent) 0%, var(--accent-2) 100%) !important;
        color: #fff !important; border: none !important;
        box-shadow: 0 4px 16px -3px var(--accent-glow) !important;
    }
    .stTabs [data-baseweb="tab-highlight"],
    .stTabs [data-baseweb="tab-border"] { display: none !important; }

    /* ── Section header ─────────────────────────── */
    .section-hdr {
        display: flex; align-items: center; gap: 10px;
        margin: 0 0 18px; padding-bottom: 14px;
        border-bottom: 1px solid var(--border);
    }
    .section-hdr h2 {
        font-size: 1.05rem; font-weight: 700; color: var(--text-1);
        margin: 0; letter-spacing: -.02em;
    }
    .section-pill {
        margin-left: auto; font-size: .68rem; font-weight: 700;
        color: var(--badge-text); background: var(--badge-bg);
        border: 1px solid var(--badge-border); border-radius: 99px;
        padding: 3px 10px; letter-spacing: .05em; text-transform: uppercase;
    }

    /* ── News card ──────────────────────────────── */
    .news-card {
        background: var(--surface);
        backdrop-filter: blur(18px); -webkit-backdrop-filter: blur(18px);
        border: 1px solid var(--border);
        border-radius: var(--r-card);
        margin-bottom: 18px; color: var(--text-1);
        transition: transform .3s cubic-bezier(.34,1.56,.64,1),
                    box-shadow .3s ease, border-color .3s ease;
        height: 420px;
        display: flex; flex-direction: column;
        position: relative; overflow: hidden;
        box-shadow: 0 2px 14px rgba(0,0,0,.14);
    }
    .news-card:hover {
        transform: translateY(-7px);
        box-shadow: 0 22px 50px -10px rgba(0,0,0,.28), 0 0 0 1px var(--border-accent);
        border-color: var(--border-accent);
    }
    .card-link { position: absolute; inset: 0; z-index: 10; cursor: pointer; }

    /* full-bleed flush image */
    .card-img {
        width: 100%; height: 178px; flex-shrink: 0;
        background-size: cover; background-position: center;
        position: relative;
    }
    .card-img::after {
        content: ''; position: absolute; bottom: 0; left: 0; right: 0; height: 36px;
        background: linear-gradient(to bottom, transparent, var(--card-fade));
        transition: background .3s ease;
    }
    .news-card:hover .card-img::after {
        background: linear-gradient(to bottom, transparent, var(--card-fade-hover));
    }
    .card-flag {
        position: absolute; top: 10px; right: 12px; z-index: 2;
        filter: drop-shadow(0 2px 6px rgba(0,0,0,.55));
        border-radius: 4px; overflow: hidden;
    }

    /* card content */
    .card-body {
        padding: 13px 18px 17px;
        display: flex; flex-direction: column;
        flex-grow: 1; overflow: hidden;
    }
    .source-badge {
        display: inline-flex; align-items: center;
        background: var(--badge-bg); color: var(--badge-text);
        padding: 3px 10px; border-radius: 99px;
        font-size: .68rem; font-weight: 700;
        text-transform: uppercase; letter-spacing: .07em;
        margin-bottom: 9px; border: 1px solid var(--badge-border);
        width: fit-content;
    }
    .badge-free {
        background: var(--green-bg) !important; color: var(--green) !important;
        border-color: var(--green-border) !important;
        font-size: .63rem !important; padding: 3px 9px !important;
        margin-bottom: 0 !important;
    }
    .news-title {
        color: var(--text-1); font-size: 1rem; font-weight: 700;
        line-height: 1.45; margin-bottom: 9px;
        transition: color .2s ease;
        display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
    }
    .news-card:hover .news-title { color: var(--badge-text); }
    .news-meta {
        font-size: .76rem; color: var(--text-2); margin-bottom: 10px;
        display: flex; align-items: center; gap: 5px; font-weight: 500;
    }
    .news-summary {
        font-size: .86rem; line-height: 1.62; color: var(--text-3); flex-grow: 1;
        display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
    }
    a { text-decoration: none !important; }

    /* ── Game list rows ─────────────────────────── */
    .game-row {
        display: flex; align-items: center; gap: 13px;
        background: var(--surface);
        backdrop-filter: blur(14px); -webkit-backdrop-filter: blur(14px);
        border: 1px solid var(--border);
        border-radius: 14px; padding: 11px 13px;
        margin-bottom: 9px; position: relative; cursor: pointer;
        transition: transform .22s ease, box-shadow .22s ease, border-color .22s ease;
        text-decoration: none !important;
    }
    .game-row:hover {
        transform: translateX(5px);
        box-shadow: 0 8px 28px -6px rgba(0,0,0,.28);
        border-color: var(--border-accent);
    }
    .game-row-thumb {
        width: 88px; height: 56px; flex-shrink: 0;
        border-radius: 8px;
        background-size: contain; background-position: center; background-repeat: no-repeat;
        background-color: rgba(0,0,0,.28);
        border: 1px solid var(--border);
    }
    [data-theme="light"] .game-row-thumb { background-color: rgba(0,0,0,.06); }
    .game-row-body { flex-grow: 1; overflow: hidden; min-width: 0; }
    .game-row-title {
        color: var(--text-1); font-size: .84rem; font-weight: 700;
        line-height: 1.35; margin-bottom: 5px;
        display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
        transition: color .2s;
    }
    .game-row:hover .game-row-title { color: var(--badge-text); }
    .game-row-meta { font-size: .68rem; color: var(--text-2); font-weight: 500; }

    /* ── Pagination ─────────────────────────────── */
    .pagination-label {
        text-align: center; color: var(--text-2);
        font-weight: 700; font-size: .78rem;
        letter-spacing: .08em; text-transform: uppercase;
    }
    div[data-testid="stHorizontalBlock"]:has(.pagination-label) div.stButton > button {
        width: 40px !important; height: 40px !important;
        border-radius: 50% !important; padding: 0 !important;
        background: var(--surface) !important;
        border: 1px solid var(--border) !important;
        color: var(--text-3) !important;
        font-size: .85rem !important;
        backdrop-filter: blur(10px);
        transition: all .22s ease !important;
        display: flex !important; align-items: center !important;
        justify-content: center !important; line-height: 1 !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.pagination-label) div.stButton > button:hover {
        background: rgba(124,58,237,.13) !important;
        border-color: var(--accent) !important;
        color: var(--badge-text) !important;
        box-shadow: 0 0 0 3px rgba(124,58,237,.13) !important;
        transform: scale(1.12) !important;
    }
    div[data-testid="stHorizontalBlock"]:has(.pagination-label) div.stButton > button:disabled {
        opacity: .2 !important; transform: none !important; box-shadow: none !important;
    }

    /* ── Alerts ─────────────────────────────────── */
    div[data-testid="stAlert"] {
        border-radius: var(--r-sm) !important;
        backdrop-filter: blur(10px);
    }

    /* ── Expiry labels ──────────────────────────── */
    .expiry-ok     { color: var(--text-2); }
    .expiry-soon   { color: #f59e0b; font-weight: 600; }
    .expiry-urgent { color: #ef4444; font-weight: 600; }
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
    const sun = `<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>`;
    const moon = `<svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>`;
    let light = false;
    btn.style.cssText = 'position:fixed;bottom:30px;right:30px;width:46px;height:46px;border-radius:50%;border:1px solid rgba(255,255,255,0.1);background:rgba(13,25,48,0.88);color:#94a3b8;cursor:pointer;z-index:9999999;box-shadow:0 8px 28px rgba(0,0,0,0.32);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);transition:all .28s cubic-bezier(.34,1.56,.64,1);display:flex;align-items:center;justify-content:center;outline:none;';
    btn.innerHTML = sun;
    btn.onmouseover = () => btn.style.transform = 'scale(1.12)';
    btn.onmouseout  = () => btn.style.transform = 'scale(1)';
    btn.onclick = () => {
        light = !light;
        if (light) {
            p.documentElement.setAttribute('data-theme','light');
            btn.innerHTML = moon;
            btn.style.background = 'rgba(248,250,252,0.96)';
            btn.style.color = '#1e293b';
            btn.style.border = '1px solid rgba(0,0,0,0.1)';
        } else {
            p.documentElement.removeAttribute('data-theme');
            btn.innerHTML = sun;
            btn.style.background = 'rgba(13,25,48,0.88)';
            btn.style.color = '#94a3b8';
            btn.style.border = '1px solid rgba(255,255,255,0.1)';
        }
    };
    p.body.appendChild(btn);
})();
</script>
""", height=0, width=0)

for _key in ("free_games_page", "ai_news_page", "games_news_page"):
    if _key not in st.session_state:
        st.session_state[_key] = 0

# ── On-visit refresh ──────────────────────────────────────────────────────────
# Triggered once per browser session. Fetches fresh data in a background thread
# if the cached JSON is older than 30 minutes (between scheduled runs).

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
        pass  # file missing — fetch immediately
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
        f'<div class="section-hdr"><h2>{icon}&nbsp; {title}</h2>{pill}</div>',
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

            # Drop expired entries before pagination
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
