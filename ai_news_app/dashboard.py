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

_HTML_TAG_RE = re.compile("<.*?>")

FLAG_MAP = {
    "🇺🇸": "https://flagcdn.com/w40/us.png",
    "🇵🇱": "https://flagcdn.com/w40/pl.png",
    "🇬🇧": "https://flagcdn.com/w40/gb.png",
    "🌍": "",
}

DATA_DIR = "/app/data"
AI_NEWS_FILE    = os.path.join(DATA_DIR, "news.json")
GAMES_NEWS_FILE = os.path.join(DATA_DIR, "games_news.json")
FREE_GAMES_FILE = os.path.join(DATA_DIR, "free_games.json")
ANIME_NEWS_FILE = os.path.join(DATA_DIR, "anime_news.json")

GAMES_PER_PAGE = 6
JIKAN_BASE = "https://api.jikan.moe/v4"

RSS_ICON   = '<svg viewBox="0 0 24 24" width="9" height="9" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round" style="margin-right:5px;flex-shrink:0;opacity:.65;"><path d="M4 11a9 9 0 0 1 9 9"/><path d="M4 4a16 16 0 0 1 16 16"/><circle cx="5" cy="19" r="1"/></svg>'
CHECK_ICON = '<svg viewBox="0 0 24 24" width="9" height="9" stroke="currentColor" stroke-width="2.5" fill="none" stroke-linecap="round" stroke-linejoin="round" style="margin-right:4px;flex-shrink:0;"><polyline points="20 6 9 17 4 12"/></svg>'
CLOCK_ICON = '<svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;opacity:.5;"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>'
BOOK_ICON  = '<svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="flex-shrink:0;opacity:.5;"><path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/><path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/></svg>'

# ─────────────────────────────────────────────────────────────────────────────
#  CSS
# ─────────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:ital,opsz,wght@0,14..32,300..900;1,14..32,300..900&display=swap');

header[data-testid="stHeader"],
div[data-testid="stToolbar"],
#MainMenu, footer { display: none !important; }

.block-container,
[data-testid="block-container"],
.stMainBlockContainer {
    max-width: 1600px !important;
    width: 100% !important;
    padding: 0 2.2rem 6rem !important;
    margin: 0 auto !important;
}

/* ── Design tokens ──────────────────────────────────────── */
:root {
    --bg:              #09090b;
    --bg-raised:       #0e0e11;
    --surface:         rgba(255,255,255,0.038);
    --surface-2:       rgba(255,255,255,0.065);
    --surface-hover:   rgba(255,255,255,0.075);
    --border:          rgba(255,255,255,0.080);
    --border-2:        rgba(255,255,255,0.175);
    --text-1:          #f0ece7;
    --text-2:          #89857f;
    --text-3:          #52504c;
    --accent:          #c87038;
    --accent-dim:      rgba(200,112,56,0.12);
    --accent-glow:     rgba(200,112,56,0.20);
    --badge-bg:        rgba(200,112,56,0.10);
    --badge-text:      #c87038;
    --badge-border:    rgba(200,112,56,0.26);
    --live:            #22c55e;
    --live-bg:         rgba(34,197,94,0.12);
    --live-border:     rgba(34,197,94,0.28);
    --blue:            #5b9cf6;
    --blue-bg:         rgba(91,156,246,0.10);
    --blue-border:     rgba(91,156,246,0.25);
    --green:           #22c55e;
    --green-bg:        rgba(34,197,94,0.10);
    --green-border:    rgba(34,197,94,0.26);
    --purple:          #a78bfa;
    --r-card:          10px;
    --r-sm:            5px;
    --r-xs:            3px;
    --font:            'Inter', system-ui, sans-serif;
    --blur:            blur(18px) saturate(160%);
}
[data-theme="light"] {
    --bg:              #f3ede5;
    --bg-raised:       #ebe5dc;
    --surface:         rgba(0,0,0,0.030);
    --surface-2:       rgba(0,0,0,0.055);
    --surface-hover:   rgba(0,0,0,0.070);
    --border:          rgba(0,0,0,0.085);
    --border-2:        rgba(0,0,0,0.200);
    --text-1:          #1a1510;
    --text-2:          #6b6158;
    --text-3:          #8c8079;
    --accent:          #9b5220;
    --accent-dim:      rgba(155,82,32,0.10);
    --accent-glow:     rgba(155,82,32,0.16);
    --badge-bg:        rgba(155,82,32,0.09);
    --badge-text:      #9b5220;
    --badge-border:    rgba(155,82,32,0.22);
    --live:            #16a34a;
    --live-bg:         rgba(22,163,74,0.10);
    --live-border:     rgba(22,163,74,0.26);
    --blue:            #2563eb;
    --blue-bg:         rgba(37,99,235,0.09);
    --blue-border:     rgba(37,99,235,0.22);
    --green:           #16a34a;
    --green-bg:        rgba(22,163,74,0.09);
    --green-border:    rgba(22,163,74,0.22);
    --purple:          #7c3aed;
}

/* ── Base ───────────────────────────────────────────────── */
html, body, [class*="css"], .stApp {
    font-family: var(--font) !important;
    background-color: var(--bg) !important;
}
div[data-testid="stAppViewContainer"], .main {
    background-color: var(--bg) !important;
    transition: background-color 0.3s ease;
}

/* ── Grain texture ──────────────────────────────────────── */
div[data-testid="stAppViewContainer"]::before {
    content: '';
    position: fixed;
    inset: 0;
    pointer-events: none;
    z-index: 0;
    opacity: 0.022;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='300' height='300'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.75' numOctaves='4' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='300' height='300' filter='url(%23n)' opacity='1'/%3E%3C/svg%3E");
    background-size: 200px 200px;
}

/* ── Scrollbar ──────────────────────────────────────────── */
::-webkit-scrollbar { width: 4px; height: 4px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: rgba(255,255,255,.10); border-radius: 2px; }
::-webkit-scrollbar-thumb:hover { background: rgba(255,255,255,.20); }

/* ── Stats header bar ───────────────────────────────────── */
.dash-header {
    display: flex;
    align-items: center;
    padding: 1.6rem 0 0;
    gap: 0;
    margin-bottom: 0;
    border-bottom: 1px solid var(--border);
    padding-bottom: 1rem;
}
.dash-brand {
    font-size: 1.08rem;
    font-weight: 900;
    letter-spacing: -.03em;
    color: var(--text-1);
    margin-right: auto;
    line-height: 1;
}
.dash-brand em {
    font-style: normal;
    color: var(--accent);
}
.dash-stat {
    display: flex;
    align-items: center;
    gap: 5px;
    padding: 4px 14px;
    border-left: 1px solid var(--border);
    font-size: .638rem;
    color: var(--text-3);
    font-weight: 500;
    letter-spacing: .04em;
    white-space: nowrap;
}
.dash-stat strong {
    color: var(--text-1);
    font-weight: 700;
}
.live-badge {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    padding: 3px 9px;
    border-radius: 20px;
    background: var(--live-bg);
    border: 1px solid var(--live-border);
    font-size: .594rem;
    font-weight: 800;
    letter-spacing: .12em;
    color: var(--live);
    text-transform: uppercase;
}
.live-dot {
    width: 5px;
    height: 5px;
    border-radius: 50%;
    background: var(--live);
    flex-shrink: 0;
    animation: live-pulse 2.2s ease-in-out infinite;
}
@keyframes live-pulse {
    0%,100% { box-shadow: 0 0 0 0 rgba(34,197,94,.45); }
    50%      { box-shadow: 0 0 0 4px rgba(34,197,94,0); }
}

/* ── News ticker ────────────────────────────────────────── */
.ticker-wrap {
    overflow: hidden;
    height: 36px;
    display: flex;
    align-items: center;
    border-bottom: 1px solid var(--border);
    margin: 0 -2.2rem 1.8rem;
    position: relative;
    background: var(--surface);
}
.ticker-wrap::before,
.ticker-wrap::after {
    content: '';
    position: absolute;
    top: 0; bottom: 0;
    width: 100px;
    z-index: 3;
    pointer-events: none;
}
.ticker-wrap::before {
    left: 0;
    background: linear-gradient(to right, var(--bg), transparent);
}
.ticker-wrap::after {
    right: 0;
    background: linear-gradient(to left, var(--bg), transparent);
}
.ticker-label {
    flex-shrink: 0;
    padding: 0 14px;
    height: 100%;
    display: flex;
    align-items: center;
    gap: 6px;
    background: var(--bg-raised);
    border-right: 1px solid var(--border-2);
    font-size: .594rem;
    font-weight: 800;
    letter-spacing: .14em;
    color: var(--accent);
    text-transform: uppercase;
    z-index: 4;
}
.ticker-scroll {
    overflow: hidden;
    flex: 1;
    height: 100%;
    display: flex;
    align-items: center;
}
.ticker-track {
    display: inline-flex;
    align-items: center;
    white-space: nowrap;
    animation: ticker-run 90s linear infinite;
}
.ticker-track:hover { animation-play-state: paused; }
@keyframes ticker-run {
    0%   { transform: translateX(0); }
    100% { transform: translateX(-50%); }
}
.t-item {
    display: inline-flex;
    align-items: center;
    gap: 7px;
    padding: 0 22px;
    font-size: .726rem;
    color: var(--text-2);
    text-decoration: none !important;
    transition: color .15s;
    cursor: pointer;
}
.t-item:hover { color: var(--text-1); }
.t-cat {
    font-size: .580rem;
    font-weight: 800;
    letter-spacing: .1em;
    text-transform: uppercase;
    flex-shrink: 0;
}
.t-sep {
    color: var(--text-3);
    font-size: .5rem;
    padding: 0 2px;
    opacity: .5;
}

/* ── Tabs ───────────────────────────────────────────────── */
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
    height: 46px;
    border-radius: 0 !important;
    padding: 0 1.6rem;
    font-family: var(--font) !important;
    font-weight: 500;
    font-size: .88rem;
    letter-spacing: .01em;
    color: var(--text-2) !important;
    background: transparent !important;
    border: none !important;
    border-bottom: 2px solid transparent !important;
    white-space: nowrap;
    transition: color .18s, border-color .18s;
}
.stTabs [aria-selected="true"] {
    background: transparent !important;
    color: var(--text-1) !important;
    border: none !important;
    border-bottom: 2px solid var(--accent) !important;
    font-weight: 700 !important;
    box-shadow: none !important;
}
.stTabs [data-baseweb="tab"]:hover { color: var(--text-1) !important; }
.stTabs [data-baseweb="tab-highlight"],
.stTabs [data-baseweb="tab-border"] { display: none !important; }

/* ── Section header ─────────────────────────────────────── */
.section-hdr {
    display: flex;
    align-items: center;
    gap: 10px;
    margin: 0 0 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--border);
}
.section-hdr-cat {
    font-size: .616rem;
    font-weight: 800;
    color: var(--accent);
    letter-spacing: .16em;
    text-transform: uppercase;
    flex-shrink: 0;
}
.section-hdr h2 {
    font-size: 1.18rem;
    font-weight: 800;
    color: var(--text-1);
    margin: 0;
    letter-spacing: -.025em;
}
.section-pill {
    margin-left: auto;
    font-size: .594rem;
    font-weight: 600;
    color: var(--text-3);
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: 20px;
    padding: 2px 9px;
    letter-spacing: .06em;
}
.section-updated {
    font-size: .616rem;
    color: var(--text-3);
    margin-left: 6px;
}

/* ── Bento grid ─────────────────────────────────────────── */
.bento-grid {
    display: grid;
    gap: 14px;
    margin-bottom: 14px;
}
.bg-3 { grid-template-columns: repeat(3, 1fr); }
.bg-2 { grid-template-columns: repeat(2, 1fr); }

/* ── News card ──────────────────────────────────────────── */
.nc {
    background: var(--surface);
    -webkit-backdrop-filter: var(--blur);
    backdrop-filter: var(--blur);
    border: 1px solid var(--border);
    border-radius: var(--r-card);
    color: var(--text-1);
    display: flex;
    flex-direction: column;
    position: relative;
    overflow: hidden;
    will-change: transform;
    transition: background .22s, border-color .22s, transform .22s, box-shadow .22s;
    animation: nc-in .38s ease both;
}
@keyframes nc-in {
    from { opacity: 0; transform: translateY(14px); }
    to   { opacity: 1; transform: translateY(0); }
}
.nc:nth-child(1) { animation-delay:   0ms; }
.nc:nth-child(2) { animation-delay:  50ms; }
.nc:nth-child(3) { animation-delay: 100ms; }
.nc:nth-child(4) { animation-delay: 150ms; }
.nc:nth-child(5) { animation-delay: 200ms; }
.nc:nth-child(6) { animation-delay: 250ms; }
.nc:hover {
    background: var(--surface-hover);
    border-color: var(--border-2);
    transform: translateY(-3px);
    box-shadow: 0 14px 44px rgba(0,0,0,.50), 0 0 0 1px var(--border-2);
}
.nc-link { position: absolute; inset: 0; z-index: 10; cursor: pointer; }

.nc-img {
    width: 100%;
    height: 158px;
    flex-shrink: 0;
    background-size: cover;
    background-position: center;
    position: relative;
    overflow: hidden;
    transition: height .22s;
}
.nc-img::after {
    content: '';
    position: absolute;
    bottom: 0; left: 0; right: 0;
    height: 60px;
    background: linear-gradient(to bottom, transparent, var(--bg));
    opacity: .7;
}
.nc-flag {
    position: absolute;
    top: 10px; right: 12px;
    z-index: 2;
    filter: drop-shadow(0 1px 4px rgba(0,0,0,.75));
    border-radius: 2px;
}


.nc-body {
    padding: 14px 16px 16px;
    display: flex;
    flex-direction: column;
    flex-grow: 1;
}
.nc-meta {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 8px;
    flex-wrap: wrap;
}
.src-badge {
    display: inline-flex;
    align-items: center;
    background: var(--badge-bg);
    color: var(--badge-text);
    padding: 2px 7px;
    border-radius: var(--r-xs);
    font-size: .594rem;
    font-weight: 800;
    text-transform: uppercase;
    letter-spacing: .10em;
    border: 1px solid var(--badge-border);
    flex-shrink: 0;
}
.badge-new {
    display: inline-flex;
    align-items: center;
    background: var(--blue-bg);
    color: var(--blue);
    border: 1px solid var(--blue-border);
    padding: 2px 6px;
    border-radius: var(--r-xs);
    font-size: .558rem;
    font-weight: 800;
    letter-spacing: .10em;
    text-transform: uppercase;
    animation: badge-blink 3s ease-in-out infinite;
}
@keyframes badge-blink {
    0%,100% { opacity: 1; }
    50%      { opacity: .65; }
}
.badge-top {
    display: inline-flex;
    align-items: center;
    background: var(--accent-dim);
    color: var(--accent);
    border: 1px solid var(--badge-border);
    padding: 2px 6px;
    border-radius: var(--r-xs);
    font-size: .558rem;
    font-weight: 800;
    letter-spacing: .10em;
    text-transform: uppercase;
}
.badge-free {
    display: inline-flex;
    align-items: center;
    background: var(--green-bg);
    color: var(--green);
    border: 1px solid var(--green-border);
    padding: 2px 7px;
    border-radius: var(--r-xs);
    font-size: .580rem;
    font-weight: 800;
    letter-spacing: .08em;
}
.nc-time {
    font-size: .616rem;
    color: var(--text-3);
    margin-left: auto;
    white-space: nowrap;
}
.nc-title {
    color: var(--text-1);
    font-size: .95rem;
    font-weight: 700;
    line-height: 1.46;
    margin-bottom: 8px;
    letter-spacing: -.012em;
    transition: color .18s;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
.nc:hover .nc-title { color: var(--accent); }
.nc-summary {
    font-size: .858rem;
    line-height: 1.65;
    color: var(--text-2);
    flex-grow: 1;
    display: -webkit-box;
    -webkit-line-clamp: 3;
    -webkit-box-orient: vertical;
    overflow: hidden;
}
.nc-footer {
    display: flex;
    align-items: center;
    gap: 10px;
    margin-top: 12px;
    padding-top: 10px;
    border-top: 1px solid var(--border);
    font-size: .616rem;
    color: var(--text-3);
}
.nc-footer-item {
    display: inline-flex;
    align-items: center;
    gap: 3px;
}
a { text-decoration: none !important; }

/* ── Game / Anime rows ──────────────────────────────────── */
.gr {
    display: flex;
    align-items: center;
    gap: 12px;
    background: var(--surface);
    -webkit-backdrop-filter: var(--blur);
    backdrop-filter: var(--blur);
    border: 1px solid var(--border);
    border-left: 3px solid transparent;
    border-radius: var(--r-sm);
    padding: 10px 13px 10px 10px;
    margin-bottom: 7px;
    position: relative;
    cursor: pointer;
    transition: background .2s, border-color .2s, transform .2s, box-shadow .2s;
    text-decoration: none !important;
    will-change: transform;
    animation: nc-in .35s ease both;
}
.gr:nth-child(1) { animation-delay:   0ms; }
.gr:nth-child(2) { animation-delay:  40ms; }
.gr:nth-child(3) { animation-delay:  80ms; }
.gr:nth-child(4) { animation-delay: 120ms; }
.gr:nth-child(5) { animation-delay: 160ms; }
.gr:nth-child(6) { animation-delay: 200ms; }
.gr:hover {
    background: var(--surface-2);
    border-left-color: var(--accent);
    border-color: var(--border-2);
    transform: translateX(4px);
    box-shadow: 0 4px 20px rgba(0,0,0,.30);
}
.gr-thumb {
    flex-shrink: 0;
    border-radius: var(--r-xs);
    background-size: cover;
    background-position: center;
    background-color: var(--surface-2);
    border: 1px solid var(--border);
    transition: filter .2s;
}
.gr:hover .gr-thumb { filter: brightness(1.06); }
.gr-body { flex-grow: 1; overflow: hidden; min-width: 0; }
.gr-title {
    color: var(--text-1);
    font-size: .88rem;
    font-weight: 600;
    line-height: 1.35;
    margin-bottom: 5px;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    transition: color .18s;
}
.gr:hover .gr-title { color: var(--accent); }
.gr-meta {
    font-size: .616rem;
    color: var(--text-3);
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
}
.gr-price-was {
    text-decoration: line-through;
    opacity: .55;
    font-size: .594rem;
}
.gr-price-free {
    color: var(--green);
    font-weight: 700;
    font-size: .638rem;
}
.expiry-ok     { color: var(--text-3); }
.expiry-soon   { color: #d4a017; font-weight: 600; }
.expiry-urgent { color: #d94040; font-weight: 700; }

/* ── Pagination ─────────────────────────────────────────── */
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
.pagination-row [data-testid="stVerticalBlock"] { flex-direction: column !important; }
.pagination-label {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 36px;
    width: 100%;
    color: var(--text-2);
    font-weight: 600;
    font-size: .726rem;
    letter-spacing: .08em;
    white-space: nowrap;
}
.pagination-row div.stButton > button {
    width: 36px !important;
    height: 36px !important;
    border-radius: var(--r-sm) !important;
    padding: 0 !important;
    background: var(--surface) !important;
    border: 1px solid var(--border) !important;
    color: var(--text-2) !important;
    font-size: .858rem !important;
    transition: all .18s !important;
    display: flex !important;
    align-items: center !important;
    justify-content: center !important;
    flex-shrink: 0 !important;
}
.pagination-row div.stButton > button:hover {
    background: var(--surface-2) !important;
    border-color: var(--border-2) !important;
    color: var(--text-1) !important;
}
.pagination-row div.stButton > button:disabled { opacity: .22 !important; }

/* ── Alerts ─────────────────────────────────────────────── */
div[data-testid="stAlert"] {
    border-radius: var(--r-sm) !important;
    border-left-width: 2px !important;
}

/* ── Selects ────────────────────────────────────────────── */
.stSelectbox label {
    font-size: .748rem !important;
    color: var(--text-2) !important;
    text-transform: uppercase !important;
    letter-spacing: .09em !important;
    font-weight: 700 !important;
}
div[data-baseweb="select"] { background: var(--surface) !important; }

/* ── Empty state ────────────────────────────────────────── */
.empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 60px 20px;
    text-align: center;
    color: var(--text-3);
    font-size: .792rem;
    letter-spacing: .08em;
    text-transform: uppercase;
    border: 1px dashed var(--border);
    border-radius: var(--r-card);
}

/* ── Skeleton loading ─────────────────────────────────── */
@keyframes shimmer {
    0%   { background-position: -400% 0; }
    100% { background-position:  400% 0; }
}
.skel-img, .skel-line, .skel-thumb {
    background: linear-gradient(90deg,
        var(--surface) 0%, var(--surface-2) 38%,
        var(--surface-2) 62%, var(--surface) 100%);
    background-size: 400% 100%;
    animation: shimmer 1.6s ease infinite;
}
.skel-img  { width: 100%; flex-shrink: 0; }
.skel-line { border-radius: 4px; margin-bottom: 9px; height: 10px; }
.skel-line.h14 { height: 14px; }
.skel-line.h16 { height: 16px; }
.skel-line.w90 { width: 90%; }
.skel-line.w80 { width: 80%; }
.skel-line.w60 { width: 60%; }
.skel-line.w40 { width: 40%; }
.skel-row {
    display: flex;
    align-items: center;
    gap: 12px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-left: 3px solid transparent;
    border-radius: var(--r-sm);
    padding: 10px 13px;
    margin-bottom: 7px;
    animation: nc-in .35s ease both;
}
.skel-thumb { flex-shrink: 0; border-radius: var(--r-xs); }
.skel-row-body { flex-grow: 1; }
</style>
""", unsafe_allow_html=True)

# ─────────────────────────────────────────────────────────────────────────────
#  JS: preconnect hints
# ─────────────────────────────────────────────────────────────────────────────
components.html("""
<script>
(function(){
    var h = window.parent.document.head;
    [
        {rel:'preconnect',href:'https://fonts.googleapis.com'},
        {rel:'preconnect',href:'https://fonts.gstatic.com',co:true},
        {rel:'dns-prefetch',href:'https://images.unsplash.com'},
        {rel:'dns-prefetch',href:'https://flagcdn.com'},
        {rel:'dns-prefetch',href:'https://api.jikan.moe'},
        {rel:'dns-prefetch',href:'https://cdn.gamerpower.com'},
    ].forEach(function(x){
        if(h.querySelector('link[href="'+x.href+'"]'))return;
        var l=window.parent.document.createElement('link');
        l.rel=x.rel;l.href=x.href;
        if(x.co)l.crossOrigin='';
        h.appendChild(l);
    });
})();
</script>
""", height=0, width=0)

# ─────────────────────────────────────────────────────────────────────────────
#  JS: theme toggle
# ─────────────────────────────────────────────────────────────────────────────
components.html("""
<script>
(function(){
    var p=window.parent.document;
    if(p.getElementById('da-theme-btn'))return;
    var btn=p.createElement('button');
    btn.id='da-theme-btn';
    var sun='<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>';
    var moon='<svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/></svg>';
    var light=false;
    btn.style.cssText='position:fixed;bottom:24px;right:24px;width:40px;height:40px;border-radius:8px;border:1px solid rgba(255,255,255,0.12);background:rgba(14,14,17,0.90);color:#c87038;cursor:pointer;z-index:9999999;box-shadow:0 2px 16px rgba(0,0,0,.6);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);transition:all .22s ease;display:flex;align-items:center;justify-content:center;outline:none;';
    btn.innerHTML=sun;
    btn.onmouseover=function(){btn.style.borderColor=light?'rgba(0,0,0,0.22)':'rgba(255,255,255,0.26)';};
    btn.onmouseout=function(){btn.style.borderColor=light?'rgba(0,0,0,0.12)':'rgba(255,255,255,0.12)';};
    btn.onclick=function(){
        light=!light;
        if(light){
            p.documentElement.setAttribute('data-theme','light');
            btn.innerHTML=moon;
            btn.style.background='rgba(235,229,220,0.95)';
            btn.style.color='#9b5220';
        }else{
            p.documentElement.removeAttribute('data-theme');
            btn.innerHTML=sun;
            btn.style.background='rgba(14,14,17,0.90)';
            btn.style.color='#c87038';
        }
    };
    p.body.appendChild(btn);
})();
</script>
""", height=0, width=0)

# ─────────────────────────────────────────────────────────────────────────────
#  JS: pagination row marker
# ─────────────────────────────────────────────────────────────────────────────
components.html("""
<script>
(function(){
    var p=window.parent.document;
    function mark(){
        p.querySelectorAll('.pagination-label').forEach(function(lbl){
            var b=lbl.closest('[data-testid="stHorizontalBlock"]');
            if(b&&!b.classList.contains('pagination-row'))b.classList.add('pagination-row');
        });
    }
    mark();
    if(!window.parent._pgObs){
        window.parent._pgObs=new MutationObserver(mark);
        window.parent._pgObs.observe(p.body,{childList:true,subtree:true});
    }
})();
</script>
""", height=0, width=0)

# ─────────────────────────────────────────────────────────────────────────────
#  JS: tab persistence + loader overlay
# ─────────────────────────────────────────────────────────────────────────────
components.html("""
<script>
(function(){
    var p=window.parent.document;
    var TAB_KEYS=['ai','gaming','anime'];
    var LS_KEY='_da_active_tab';

    if(!p.getElementById('da-loader')&&!window.parent._daTabRestored){
        var ov=p.createElement('div');
        ov.id='da-loader';
        ov.style.cssText='position:fixed;inset:0;background:#09090b;z-index:9999999;transition:opacity 0.15s ease;pointer-events:none;';
        p.body.appendChild(ov);
    }

    function hideLoader(){
        var el=p.getElementById('da-loader');
        if(!el)return;
        el.style.opacity='0';
        setTimeout(function(){if(el&&el.parentNode)el.parentNode.removeChild(el);},180);
    }

    function getTabs(){ return p.querySelectorAll('[data-baseweb="tab"]'); }

    function attachListeners(){
        getTabs().forEach(function(tab,idx){
            if(tab._daTracked)return;
            tab._daTracked=true;
            tab.addEventListener('click',function(){
                try{window.parent.localStorage.setItem(LS_KEY,TAB_KEYS[idx]);}catch(e){}
            });
        });
    }

    function restoreTab(){
        if(window.parent._daTabRestored){attachListeners();hideLoader();return;}
        var tabs=getTabs();
        if(!tabs.length)return;
        window.parent._daTabRestored=true;
        var saved;
        try{saved=window.parent.localStorage.getItem(LS_KEY);}catch(e){}
        var idx=TAB_KEYS.indexOf(saved);
        if(idx>0&&tabs[idx]){tabs[idx].click();setTimeout(hideLoader,120);}
        else{hideLoader();}
        attachListeners();
    }

    restoreTab();

    if(!window.parent._daTabObs){
        window.parent._daTabObs=new MutationObserver(function(){
            attachListeners();
            if(!window.parent._daTabRestored)restoreTab();
        });
        window.parent._daTabObs.observe(p.body,{childList:true,subtree:true});
    }
})();
</script>
""", height=0, width=0)

# ─────────────────────────────────────────────────────────────────────────────
#  Session state
# ─────────────────────────────────────────────────────────────────────────────
for _k in ("free_games_page","ai_news_page","games_news_page","anime_news_page"):
    if _k not in st.session_state:
        st.session_state[_k] = 0

# ─────────────────────────────────────────────────────────────────────────────
#  On-visit background refresh
# ─────────────────────────────────────────────────────────────────────────────
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
        print(f"[dashboard] refresh error: {e}")
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


# ─────────────────────────────────────────────────────────────────────────────
#  Helpers
# ─────────────────────────────────────────────────────────────────────────────

def format_date(s):
    if not s:
        return ""
    try:
        return parsedate_to_datetime(s).strftime("%d %b %Y · %H:%M")
    except Exception:
        return s


def relative_time(s):
    if not s:
        return ""
    try:
        dt   = parsedate_to_datetime(s)
        secs = (datetime.now(dt.tzinfo) - dt).total_seconds()
        if secs <   120: return "just now"
        if secs <  3600: return f"{int(secs/60)}m ago"
        if secs < 86400: return f"{int(secs/3600)}h ago"
        return f"{int(secs/86400)}d ago"
    except Exception:
        return format_date(s)


def is_fresh(s, hours=10):
    if not s:
        return False
    try:
        dt = parsedate_to_datetime(s)
        return (datetime.now(dt.tzinfo) - dt).total_seconds() < hours * 3600
    except Exception:
        return False


def estimate_reading_time(text):
    if not text:
        return "1 min"
    mins = max(1, round(len(text.split()) / 200))
    return f"{mins} min read"


def strip_html(text):
    return _HTML_TAG_RE.sub("", text) if text else ""


def get_fallback_image(title, summary=""):
    text = (title + " " + summary).lower()
    if any(k in text for k in ["ai","sztuczn","openai","chatgpt","llm","model","inteligencj"]):
        return "https://images.unsplash.com/photo-1677442136019-21780ecad995?auto=format&fit=crop&w=800&q=75"
    if any(k in text for k in ["robot","machine learning","hardware","chip","processor"]):
        return "https://images.unsplash.com/photo-1485827404703-89b55fcc595e?auto=format&fit=crop&w=800&q=75"
    if any(k in text for k in ["xbox","playstation","nintendo","console","sony"]):
        return "https://images.unsplash.com/photo-1605901309584-818e25960b8f?auto=format&fit=crop&w=800&q=75"
    if any(k in text for k in ["pc","steam","epic","valve"]):
        return "https://images.unsplash.com/photo-1587202372634-32705e3bf49c?auto=format&fit=crop&w=800&q=75"
    if any(k in text for k in ["anime","manga","shonen","seinen","isekai"]):
        return "https://images.unsplash.com/photo-1578632767115-351597cf2477?auto=format&fit=crop&w=800&q=75"
    if any(k in text for k in ["gra","game","rpg","fps","multiplayer","trailer"]):
        return "https://images.unsplash.com/photo-1552820728-8b83bb6b773f?auto=format&fit=crop&w=800&q=75"
    return "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=800&q=75"


def parse_source(source_full):
    parts = source_full.split(" ", 1)
    if len(parts) == 2 and any(not c.isascii() for c in parts[0]):
        return parts[0], parts[1]
    return "", source_full


def render_flag(flag):
    if not flag or flag not in FLAG_MAP or not FLAG_MAP[flag]:
        return ""
    return f'<div class="nc-flag"><img src="{FLAG_MAP[flag]}" width="20" alt=""></div>'


def parse_end_date(s):
    if not s or str(s).strip().upper() == "N/A":
        return None
    try:
        return datetime.strptime(str(s).strip(), "%Y-%m-%d %H:%M:%S")
    except ValueError:
        return None


def is_expired(s):
    dt = parse_end_date(s)
    return dt is not None and datetime.now() > dt


def format_end_date(s):
    dt = parse_end_date(s)
    return dt.strftime("%d %b %Y") if dt else None


def expiry_class(s):
    dt = parse_end_date(s)
    if dt is None:
        return ""
    days = (dt - datetime.now()).days
    if days < 1:   return "expiry-urgent"
    if days <= 3:  return "expiry-soon"
    return "expiry-ok"


def days_left_label(s):
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


def count_items(f):
    if not os.path.exists(f):
        return 0
    try:
        with open(f, "r", encoding="utf-8") as fp:
            return len(json.load(fp))
    except Exception:
        return 0


def get_file_age_str(filepath):
    if not os.path.exists(filepath):
        return "—"
    secs = time.time() - os.path.getmtime(filepath)
    if secs <   120: return "just now"
    if secs <  3600: return f"{int(secs/60)}m ago"
    if secs < 86400: return f"{int(secs/3600)}h ago"
    return f"{int(secs/86400)}d ago"


def section_header(cat, title, count=None, updated=None):
    pill  = f'<span class="section-pill">{count}</span>' if count else ""
    upd   = f'<span class="section-updated">· {updated}</span>' if updated else ""
    st.markdown(
        f'<div class="section-hdr">'
        f'<span class="section-hdr-cat">{cat}</span>'
        f'<h2>{title}</h2>'
        f'{upd}{pill}</div>',
        unsafe_allow_html=True,
    )


def render_pagination(page_key, total_pages, prev_key, next_key, centered=False):
    if total_pages <= 1:
        return
    if centered:
        _, pc1, pc2, pc3, _ = st.columns([3,1,2,1,3], vertical_alignment="center")
    else:
        pc1, pc2, pc3 = st.columns([1,2,1], vertical_alignment="center")
    with pc1:
        if st.button("◀", key=prev_key, disabled=(st.session_state[page_key] <= 0)):
            st.session_state[page_key] -= 1
            st.rerun()
    with pc2:
        st.markdown(
            f"<div class='pagination-label'>{st.session_state[page_key]+1} / {total_pages}</div>",
            unsafe_allow_html=True,
        )
    with pc3:
        if st.button("▶", key=next_key, disabled=(st.session_state[page_key] >= total_pages-1)):
            st.session_state[page_key] += 1
            st.rerun()


def build_news_skeleton(num_cols=3, count=6):
    grid_cls = "bg-3" if num_cols == 3 else "bg-2"
    cards = ""
    for i in range(count):
        delay = i * 55
        cards += (
            f'<div class="nc" style="animation-delay:{delay}ms">'
            f'<div class="skel-img" style="height:158px"></div>'
            f'<div class="nc-body">'
            f'<div class="skel-line w40" style="margin-bottom:12px"></div>'
            f'<div class="skel-line h16 w80"></div>'
            f'<div class="skel-line h16 w90"></div>'
            f'<div class="skel-line h14 w60"></div>'
            f'<div class="skel-line w40" style="margin-top:2px"></div>'
            f'</div></div>'
        )
    return f'<div class="bento-grid {grid_cls}">{cards}</div>'


def build_rows_skeleton(count=6, thumb_w=92, thumb_h=62):
    rows = ""
    for i in range(count):
        delay = i * 45
        rows += (
            f'<div class="skel-row" style="animation-delay:{delay}ms">'
            f'<div class="skel-thumb" style="width:{thumb_w}px;height:{thumb_h}px"></div>'
            f'<div class="skel-row-body">'
            f'<div class="skel-line h14 w80" style="margin-bottom:8px"></div>'
            f'<div class="skel-line w60"></div>'
            f'</div></div>'
        )
    return rows


def load_sorted_items(json_file_path):
    if not os.path.exists(json_file_path):
        return None
    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            items = json.load(f)
    except Exception:
        return []

    def _ts(item):
        try:
            return parsedate_to_datetime(item.get("published","")).timestamp()
        except Exception:
            return 0.0

    items.sort(key=_ts, reverse=True)
    return items


def render_news_cards(json_file_path, num_cols=3, per_page=None, page_key=None):
    placeholder = st.empty()
    placeholder.markdown(build_news_skeleton(num_cols, per_page or 6), unsafe_allow_html=True)

    items = load_sorted_items(json_file_path)
    if items is None:
        placeholder.warning("Data not yet available — waiting for the first fetch.")
        return
    if not items:
        placeholder.markdown('<div class="empty-state">No articles available yet</div>', unsafe_allow_html=True)
        return

    if per_page and page_key:
        total_pages = max(1, (len(items) + per_page - 1) // per_page)
        if st.session_state[page_key] >= total_pages:
            st.session_state[page_key] = total_pages - 1
        start = st.session_state[page_key] * per_page
        items = items[start:start + per_page]
    else:
        total_pages = 1

    grid_cls = "bg-3" if num_cols == 3 else "bg-2"

    cards_html = ""
    for i, item in enumerate(items):
        flag, src_name  = parse_source(item.get("source",""))
        image_url       = item.get("image") or get_fallback_image(item.get("title",""), item.get("summary",""))
        summary         = strip_html(item.get("summary",""))[:300]
        rel_t           = relative_time(item.get("published",""))
        fresh           = is_fresh(item.get("published",""))
        read_t          = estimate_reading_time(summary)

        badges = f'<span class="src-badge">{RSS_ICON}{src_name}</span>'
        if fresh:
            badges += ' <span class="badge-new">New</span>'

        cards_html += f"""<div class="nc">
<a href="{item['link']}" target="_blank" class="nc-link" aria-label="{item['title']}"></a>
<div class="nc-img" style="background-image:url('{image_url}');">{render_flag(flag)}</div>
<div class="nc-body">
<div class="nc-meta">{badges}<span class="nc-time">{rel_t}</span></div>
<div class="nc-title">{item['title']}</div>
<div class="nc-summary">{summary}</div>
<div class="nc-footer">
<span class="nc-footer-item">{BOOK_ICON}&nbsp;{read_t}</span>
<span class="nc-footer-item">{CLOCK_ICON}&nbsp;{format_date(item.get('published',''))}</span>
</div>
</div></div>"""

    placeholder.markdown(
        f'<div class="bento-grid {grid_cls}">{cards_html}</div>',
        unsafe_allow_html=True,
    )

    if per_page and page_key and total_pages > 1:
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        render_pagination(page_key, total_pages,
                          prev_key=f"{page_key}_prev",
                          next_key=f"{page_key}_next",
                          centered=True)


# ─────────────────────────────────────────────────────────────────────────────
#  Stats header + news ticker
# ─────────────────────────────────────────────────────────────────────────────

def build_ticker_html():
    CAT_COLORS = {"AI": "#c87038", "GAMING": "#5b9cf6", "ANIME": "#a78bfa"}
    all_items  = []
    for filepath, cat in [(AI_NEWS_FILE,"AI"), (GAMES_NEWS_FILE,"GAMING"), (ANIME_NEWS_FILE,"ANIME")]:
        items = load_sorted_items(filepath)
        if items:
            for item in items[:6]:
                all_items.append({"title": item["title"], "link": item["link"], "cat": cat})

    if not all_items:
        return ""

    inner = ""
    for it in all_items:
        col = CAT_COLORS.get(it["cat"], "#c87038")
        title_escaped = it["title"].replace('"', "&quot;").replace("'", "&#39;")
        inner += (
            f'<a href="{it["link"]}" target="_blank" class="t-item">'
            f'<span class="t-cat" style="color:{col}">{it["cat"]}</span>'
            f'<span>{title_escaped}</span>'
            f'</a><span class="t-sep">◆</span>'
        )
    inner = inner * 2  # seamless loop

    return f"""
<div class="ticker-wrap">
  <div class="ticker-label"><div class="live-dot"></div>LATEST</div>
  <div class="ticker-scroll">
    <div class="ticker-track">{inner}</div>
  </div>
</div>"""


def render_dashboard_header():
    ai_n     = count_items(AI_NEWS_FILE)
    games_n  = count_items(GAMES_NEWS_FILE)
    anime_n  = count_items(ANIME_NEWS_FILE)
    total    = ai_n + games_n + anime_n
    updated  = get_file_age_str(AI_NEWS_FILE)

    header_html = f"""
<div class="dash-header">
  <div class="dash-brand">Daily<em>Agg</em></div>
  <div class="dash-stat">
    <span class="live-badge"><span class="live-dot"></span>LIVE</span>
  </div>
  <div class="dash-stat"><strong>{total}</strong>&nbsp;articles</div>
  <div class="dash-stat">AI&nbsp;<strong>{ai_n}</strong></div>
  <div class="dash-stat">Gaming&nbsp;<strong>{games_n}</strong></div>
  <div class="dash-stat">Anime&nbsp;<strong>{anime_n}</strong></div>
  <div class="dash-stat">Updated&nbsp;<strong>{updated}</strong></div>
</div>
"""
    st.markdown(header_html + build_ticker_html(), unsafe_allow_html=True)


render_dashboard_header()

# ─────────────────────────────────────────────────────────────────────────────
#  Anime helpers
# ─────────────────────────────────────────────────────────────────────────────

def fetch_genres():
    if "jikan_genres" not in st.session_state:
        try:
            r = requests.get(f"{JIKAN_BASE}/genres/anime", timeout=8)
            st.session_state.jikan_genres = sorted(r.json().get("data",[]), key=lambda g: g["name"])
        except Exception:
            st.session_state.jikan_genres = []
    return st.session_state.jikan_genres


def fetch_anime_by_genre(genre_id, sort_by="score"):
    key = f"jikan_{genre_id}_{sort_by}"
    if key not in st.session_state:
        try:
            r = requests.get(
                f"{JIKAN_BASE}/anime",
                params={"genres": genre_id, "order_by": sort_by, "sort": "desc",
                        "limit": 20, "sfw": "true"},
                timeout=10,
            )
            st.session_state[key] = r.json().get("data",[])
        except Exception:
            st.session_state[key] = []
    return st.session_state[key]


def render_anime_row(anime, idx=0):
    title     = anime.get("title","Unknown")
    score     = anime.get("score")
    episodes  = anime.get("episodes")
    year      = anime.get("year","")
    status    = (anime.get("status") or "").replace("Finished Airing","Finished").replace("Currently Airing","Airing")
    image_url = anime.get("images",{}).get("jpg",{}).get("image_url","")
    url       = anime.get("url","#")

    parts = []
    if score:    parts.append(f"★ {score}")
    if year:     parts.append(str(year))
    if episodes: parts.append(f"{episodes} ep")
    if status:   parts.append(status)
    meta = " · ".join(parts)

    delay = idx * 40
    return (
        f'<a href="{url}" target="_blank" class="gr" style="animation-delay:{delay}ms">'
        f'<div class="gr-thumb" style="width:54px;height:76px;background-image:url(\'{image_url}\');"></div>'
        f'<div class="gr-body">'
        f'<div class="gr-title">{title}</div>'
        f'<div class="gr-meta">{meta}</div>'
        f'</div></a>'
    )


# ─────────────────────────────────────────────────────────────────────────────
#  Tabs
# ─────────────────────────────────────────────────────────────────────────────
tab_ai, tab_games, tab_anime = st.tabs(["AI & Technology", "Gaming", "Anime"])

# ── AI Tab ────────────────────────────────────────────────────────────────────
with tab_ai:
    n       = count_items(AI_NEWS_FILE)
    updated = get_file_age_str(AI_NEWS_FILE)
    section_header("AI / TECH", "Artificial Intelligence & Technology",
                   count=n or None, updated=updated if n else None)
    render_news_cards(AI_NEWS_FILE, num_cols=3, per_page=6, page_key="ai_news_page")

# ── Gaming Tab ────────────────────────────────────────────────────────────────
with tab_games:
    col_news, col_free = st.columns([2, 1], gap="large")

    with col_news:
        n       = count_items(GAMES_NEWS_FILE)
        updated = get_file_age_str(GAMES_NEWS_FILE)
        section_header("GAMING", "Gaming News", count=n or None, updated=updated if n else None)
        render_news_cards(GAMES_NEWS_FILE, num_cols=2, per_page=4, page_key="games_news_page")

    with col_free:
        section_header("FREE", "Free Games Now")

        if not os.path.exists(FREE_GAMES_FILE):
            st.info("Loading free games… please wait.")
        else:
            try:
                with open(FREE_GAMES_FILE, "r", encoding="utf-8") as f:
                    free_games = json.load(f)
            except Exception:
                free_games = []

            active = [g for g in free_games if not is_expired(g.get("end_date"))]

            if not active:
                st.markdown('<div class="empty-state">No free games right now</div>', unsafe_allow_html=True)
            else:
                total_pages = max(1, (len(active) + GAMES_PER_PAGE - 1) // GAMES_PER_PAGE)
                if st.session_state.free_games_page >= total_pages:
                    st.session_state.free_games_page = total_pages - 1

                start      = st.session_state.free_games_page * GAMES_PER_PAGE
                page_games = active[start : start + GAMES_PER_PAGE]

                _THUMB_W = 92
                _THUMB_H = 62

                rows_html = ""
                for idx, game in enumerate(page_games):
                    raw_worth = (game.get("worth") or "").strip()
                    # Only show original price if it looks like a real dollar amount
                    show_worth = raw_worth if re.match(r'^\$\d', raw_worth) else ""

                    platforms    = game.get("platforms","")
                    end_date_raw = game.get("end_date","")
                    days_lbl     = days_left_label(end_date_raw)
                    exp_cls      = expiry_class(end_date_raw)
                    delay        = idx * 45

                    price_html = ""
                    if show_worth:
                        price_html = (
                            f'<span class="gr-price-was">{show_worth}</span>'
                            f'<span class="gr-price-free">FREE</span>'
                        )
                    else:
                        price_html = '<span class="gr-price-free">FREE</span>'

                    expiry_html = (
                        f'&nbsp;·&nbsp;<span class="gr-countdown {exp_cls}" data-expiry="{end_date_raw}">{days_lbl}</span>'
                    ) if days_lbl else ""

                    rows_html += (
                        f'<a href="{game["link"]}" target="_blank" class="gr" '
                        f'style="animation-delay:{delay}ms;">'
                        f'<div class="gr-thumb" style="width:{_THUMB_W}px;height:{_THUMB_H}px;'
                        f'background-size:cover;background-image:url(\'{game.get("thumbnail","")}\');"></div>'
                        f'<div class="gr-body">'
                        f'<div style="margin-bottom:5px;display:flex;gap:6px;align-items:center;flex-wrap:wrap;">'
                        f'<span class="badge-free">{CHECK_ICON}FREE</span>'
                        f'<span style="font-size:.60rem;color:var(--text-3);">{price_html}</span>'
                        f'</div>'
                        f'<div class="gr-title">{game["title"]}</div>'
                        f'<div class="gr-meta">{platforms}{expiry_html}</div>'
                        f'</div></a>'
                    )

                st.markdown(
                    f'<div id="fg-container" style="display:flex;flex-direction:column;gap:7px;'
                    f'max-height:900px;overflow-y:auto;padding-right:4px;">'
                    f'{rows_html}</div>',
                    unsafe_allow_html=True,
                )

                if total_pages > 1:
                    st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
                    render_pagination("free_games_page", total_pages,
                                      prev_key="prev_btn", next_key="next_btn")

    components.html("""
<script>
(function(){
    var p=window.parent.document;
    function pad(n){return String(n).padStart(2,'0');}
    function tick(){
        p.querySelectorAll('.gr-countdown[data-expiry]').forEach(function(el){
            var raw=el.getAttribute('data-expiry');
            if(!raw)return;
            var d=new Date(raw.replace(' ','T'));
            if(isNaN(d.getTime()))return;
            var diff=d-new Date();
            if(diff<=0){el.textContent='Expired';el.className='gr-countdown expiry-urgent';return;}
            var s=Math.floor(diff/1000);
            var days=Math.floor(s/86400);
            var hrs=Math.floor((s%86400)/3600);
            var mins=Math.floor((s%3600)/60);
            var sec=s%60;
            var label,cls;
            if(days>=3){
                label=days+'d '+pad(hrs)+'h '+pad(mins)+'m';
                cls='gr-countdown expiry-ok';
            }else if(days>=1){
                label=days+'d '+pad(hrs)+'h '+pad(mins)+'m '+pad(sec)+'s';
                cls='gr-countdown expiry-soon';
            }else if(hrs>=6){
                label=pad(hrs)+':'+pad(mins)+':'+pad(sec);
                cls='gr-countdown expiry-soon';
            }else{
                label=pad(hrs)+':'+pad(mins)+':'+pad(sec);
                cls='gr-countdown expiry-urgent';
            }
            el.textContent=label;
            el.className=cls;
        });
    }
    tick();
    if(window.parent._cdInterval){clearInterval(window.parent._cdInterval);}
    window.parent._cdInterval=setInterval(tick,1000);
})();
</script>
""", height=0, width=0)

# ── Anime Tab ─────────────────────────────────────────────────────────────────
with tab_anime:
    col_news, col_search = st.columns([2, 1], gap="large")

    with col_news:
        n       = count_items(ANIME_NEWS_FILE)
        updated = get_file_age_str(ANIME_NEWS_FILE)
        section_header("ANIME", "Anime News", count=n or None, updated=updated if n else None)
        render_news_cards(ANIME_NEWS_FILE, num_cols=2, per_page=4, page_key="anime_news_page")

    with col_search:
        section_header("SEARCH", "Browse by Genre")

        genres      = fetch_genres()
        genre_names = ["— Select a genre —"] + [g["name"] for g in genres]

        sc1, sc2 = st.columns([3,1])
        with sc1:
            selected_genre_name = st.selectbox(
                "Genre", genre_names, key="genre_select", label_visibility="collapsed"
            )
        with sc2:
            sort_option = st.selectbox(
                "Sort", ["Score","Popularity","Members"],
                key="genre_sort", label_visibility="collapsed"
            )

        sort_map = {"Score":"score","Popularity":"popularity","Members":"members"}
        sort_by  = sort_map.get(sort_option,"score")

        if selected_genre_name != "— Select a genre —":
            selected_genre = next((g for g in genres if g["name"] == selected_genre_name), None)
            if selected_genre:
                anime_ph = st.empty()
                anime_ph.markdown(
                    f'<div style="display:flex;flex-direction:column;gap:7px;padding-right:4px;">'
                    f'{build_rows_skeleton(8, thumb_w=54, thumb_h=76)}</div>',
                    unsafe_allow_html=True,
                )
                results = fetch_anime_by_genre(selected_genre["mal_id"], sort_by)
                if results:
                    rows_html = "".join(render_anime_row(a, i) for i, a in enumerate(results))
                    anime_ph.markdown(
                        f'<div id="ac" style="display:flex;flex-direction:column;gap:7px;'
                        f'height:800px;overflow-y:auto;padding-right:4px;">'
                        f'{rows_html}</div>',
                        unsafe_allow_html=True,
                    )
                else:
                    anime_ph.info("No results found for this genre.")
        else:
            st.markdown(
                '<div class="empty-state">Select a genre to browse anime</div>',
                unsafe_allow_html=True,
            )

    components.html("""
<script>
(function(){
    var p=window.parent.document;
    function syncAC(){
        var ac=p.getElementById('ac');
        if(!ac)return;
        var block=ac.closest('[data-testid="stHorizontalBlock"]');
        if(!block)return;
        var cols=block.querySelectorAll(':scope>[data-testid="stColumn"]');
        if(cols.length<2)return;
        var prev=ac.style.height;
        ac.style.height='0px';
        var overhead=cols[1].offsetHeight;
        ac.style.height=prev;
        var newsH=cols[0].offsetHeight;
        if(newsH<100)return;
        var t=newsH-overhead;
        if(t>80)ac.style.height=t+'px';
    }
    var _t=0;
    function trySyncAC(){syncAC();_t++;if(_t<6)setTimeout(trySyncAC,300);}
    setTimeout(trySyncAC,200);
    if(!window.parent._acObs){
        window.parent._acObs=new MutationObserver(function(){var ac=p.getElementById('ac');if(ac)syncAC();});
        window.parent._acObs.observe(p.body,{childList:true,subtree:true,attributes:false});
    }
})();
</script>
""", height=0, width=0)
