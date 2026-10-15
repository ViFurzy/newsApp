"""
ui/cards.py — News card / row rendering, pagination, and section headers.

All functions that render Streamlit content for article grids.
"""
import html as _html
import json
import os

import streamlit as st
from email.utils import parsedate_to_datetime

from ui.helpers import (
    BOOK_ICON, CLOCK_ICON, RSS_ICON,
    format_date, get_fallback_image, https_url, is_fresh, needs_anonymous_cors,
    parse_source, relative_time, render_flag,
    estimate_reading_time, strip_html,
)


# ── Section header ─────────────────────────────────────────────────────────────

def section_header(cat: str, title: str, count=None, updated: str = None) -> None:
    pill  = f'<span class="section-pill">{count}</span>' if count else ""
    upd   = f'<span class="section-updated">· {updated}</span>' if updated else ""
    st.markdown(
        f'<div class="section-hdr">'
        f'<div class="section-hdr-top">'
        f'<span class="section-hdr-cat">{cat}</span>'
        f'{upd}{pill}'
        f'</div>'
        f'<h2>{title}</h2>'
        f'</div>',
        unsafe_allow_html=True,
    )


# ── Pagination ─────────────────────────────────────────────────────────────────

def render_pagination(
    page_key: str,
    total_pages: int,
    prev_key: str,
    next_key: str,
    centered: bool = False,
) -> None:
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


# ── Skeleton loaders ───────────────────────────────────────────────────────────

def build_news_skeleton(num_cols: int = 3, count: int = 6) -> str:
    grid_cls = "bg-3" if num_cols == 3 else "bg-2"
    cards = ""
    for i in range(count):
        delay = i * 55
        cards += (
            f'<div class="nc" style="animation-delay:{delay}ms">'
            f'<div class="skel-img" style="aspect-ratio:3/1;min-height:120px;max-height:160px"></div>'
            f'<div class="nc-body">'
            f'<div class="skel-line w40" style="margin-bottom:12px"></div>'
            f'<div class="skel-line h16 w80"></div>'
            f'<div class="skel-line h16 w90"></div>'
            f'<div class="skel-line h14 w60"></div>'
            f'<div class="skel-line w40" style="margin-top:2px"></div>'
            f'</div></div>'
        )
    return f'<div class="bento-grid {grid_cls}">{cards}</div>'


def build_rows_skeleton(count: int = 6, thumb_w: int = 92, thumb_h: int = 62) -> str:
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


# ── Data loading (cached) ──────────────────────────────────────────────────────

def load_sorted_items(json_file_path):
    """Items sorted by date desc; cache is keyed on file mtime so fresh fetches show instantly."""
    path = str(json_file_path)
    mtime = os.path.getmtime(path) if os.path.exists(path) else 0
    return _load_sorted(path, mtime)


@st.cache_data(show_spinner=False)
def _load_sorted(json_file_path: str, _mtime: float):
    if not os.path.exists(json_file_path):
        return None
    try:
        with open(json_file_path, "r", encoding="utf-8") as f:
            items = json.load(f)
    except Exception:
        return []

    def _ts(item):
        try:
            return parsedate_to_datetime(item.get("published", "")).timestamp()
        except Exception:
            return 0.0

    items.sort(key=_ts, reverse=True)
    return items


# ── Search + source chips ──────────────────────────────────────────────────────

def filter_items(items: list[dict], query: str, sources) -> list[dict]:
    """Case-insensitive title/summary match, restricted to the picked sources (none picked = all)."""
    q = (query or "").strip().lower()
    return [
        it for it in items
        if (not sources or it.get("source") in sources)
        and (not q or q in (it.get("title", "") + " " + it.get("summary", "")).lower())
    ]


def _filter_bar(items: list[dict], page_key: str) -> list[dict]:
    """Search box + source chips above a card grid. Picking a source is also 'hide the others'."""
    all_sources = sorted({it.get("source", "") for it in items if it.get("source")})
    c_search, c_src = st.columns([1, 2], vertical_alignment="center")
    with c_search:
        query = st.text_input(
            "Search headlines", key=f"{page_key}_q",
            placeholder="Search headlines", label_visibility="collapsed",
        )
    with c_src:
        picked = st.pills(
            "Sources", all_sources, selection_mode="multi", key=f"{page_key}_src",
            format_func=lambda s: parse_source(s)[1], label_visibility="collapsed",
        ) or []
    sig = (query, tuple(sorted(picked)))
    if st.session_state.get(f"{page_key}_sig") != sig:      # filter changed: back to page 1
        st.session_state[f"{page_key}_sig"] = sig
        st.session_state[page_key] = 0
    return filter_items(items, query, picked)


# ── News card grid ─────────────────────────────────────────────────────────────

def _prefetch_img(url: str) -> str:
    """Hidden <img> that warms the browser cache; same CORS mode as the card so the cache entry is reused."""
    if not url:
        return ""
    cors = ' crossorigin="anonymous"' if needs_anonymous_cors(url) else ""
    return f'<img src="{_html.escape(url, quote=True)}" alt="" decoding="async" referrerpolicy="no-referrer"{cors}>'


def render_news_cards(
    json_file_path,
    num_cols: int = 3,
    per_page: int = None,
    page_key: str = None,
    filter_fn=None,
    category: str = "",
    variant: str = "",
) -> None:
    items = load_sorted_items(str(json_file_path))
    if items is None:
        st.warning("Data not yet available. Waiting for the first fetch.")
        return
    if filter_fn and items:
        items = filter_fn(items)
    searching = False
    if items and page_key:
        items = _filter_bar(items, page_key)
        searching = bool(st.session_state.get(f"{page_key}_q") or st.session_state.get(f"{page_key}_src"))

    placeholder = st.empty()
    placeholder.markdown(build_news_skeleton(num_cols, per_page or 6), unsafe_allow_html=True)
    if not items:
        placeholder.markdown(
            f'<div class="empty-state">{"No articles match your search" if searching else "No articles available yet"}</div>',
            unsafe_allow_html=True,
        )
        return

    upcoming = []
    if per_page and page_key:
        total_pages = max(1, (len(items) + per_page - 1) // per_page)
        if st.session_state[page_key] >= total_pages:
            st.session_state[page_key] = total_pages - 1
        start = st.session_state[page_key] * per_page
        # neighbouring pages: their images are warmed in the browser cache so paging feels instant
        upcoming = items[start + per_page : start + 2 * per_page] + items[max(0, start - per_page) : start]
        items = items[start : start + per_page]
    else:
        total_pages = 1

    grid_cls    = ("bg-3" if num_cols == 3 else "bg-2") + (f" bg-{variant}" if variant else "")
    cards_html  = ""

    for item in items:
        flag, src_name = parse_source(item.get("source", ""))
        fallback_url   = get_fallback_image(item.get("title", ""), item.get("summary", ""), category)
        image_url      = https_url(item.get("image") or fallback_url)
        summary  = strip_html(item.get("summary", ""))[:300]
        rel_t    = relative_time(item.get("published", ""))
        fresh    = is_fresh(item.get("published", ""))
        read_t   = estimate_reading_time(summary)

        _title   = _html.escape(item.get("title", ""))
        _link    = _html.escape(item.get("link", ""))
        _img     = _html.escape(image_url, quote=True)
        _fb      = _html.escape(fallback_url, quote=True)
        _cors    = ' crossorigin="anonymous"' if needs_anonymous_cors(image_url) else ""
        _summary = _html.escape(summary)
        _src     = _html.escape(src_name)

        badges = f'<span class="src-badge">{RSS_ICON}{_src}</span>'
        if fresh:
            badges += ' <span class="badge-new">New</span>'

        cards_html += f"""<div class="nc">
<a href="{_link}" target="_blank" class="nc-link" aria-label="{_title}"></a>
<button type="button" class="nc-save" data-link="{_link}" aria-pressed="false" aria-label="Save for later">&#9734;</button>
<div class="nc-img"><img class="nc-photo" src="{_img}" decoding="async" alt="" referrerpolicy="no-referrer"{_cors} data-fb="{_fb}">{render_flag(flag)}</div>
<div class="nc-body">
<div class="nc-meta">{badges}<span class="nc-time">{rel_t}</span></div>
<div class="nc-title">{_title}</div>
<div class="nc-summary">{_summary}</div>
<div class="nc-footer">
<span class="nc-footer-item">{BOOK_ICON}&nbsp;{read_t}</span>
<span class="nc-footer-item">{CLOCK_ICON}&nbsp;{format_date(item.get('published', ''))}</span>
</div>
</div></div>"""

    prefetch = "".join(_prefetch_img(https_url(it.get("image", ""))) for it in upcoming)
    placeholder.markdown(
        f'<div class="bento-grid {grid_cls}">{cards_html}</div>'
        f'<div class="nc-prefetch" aria-hidden="true">{prefetch}</div>',
        unsafe_allow_html=True,
    )

    if per_page and page_key and total_pages > 1:
        st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
        render_pagination(
            page_key,
            total_pages,
            prev_key=f"{page_key}_prev",
            next_key=f"{page_key}_next",
            centered=True,
        )
