"""
ui/games.py — Gaming tab rendering: news feed, free-games giveaways, countdown JS.
"""
import html as _html
import json
import re

import streamlit as st
import streamlit.components.v1 as components

from config import FREE_GAMES_FILE, GAMES_NEWS_FILE, GAMES_PER_PAGE, GAMING_PER_PAGE
from ui.cards import render_news_cards, section_header
from ui.filters import filter_for_games_tab
from ui.helpers import (
    CHECK_ICON,
    count_items,
    days_left_label,
    expiry_class,
    get_file_age_str,
    is_expired,
)

_THUMB_W = 92
_THUMB_H = 62


# ── Free-games giveaways column ────────────────────────────────────────────────

def render_free_games_column() -> None:
    """Render the right-hand 'Free Games Now' column inside the Gaming tab."""
    section_header("FREE", "Free Games Now")

    if not FREE_GAMES_FILE.exists():
        st.info("Loading free games… please wait.")
        return

    try:
        with open(FREE_GAMES_FILE, "r", encoding="utf-8") as f:
            free_games = json.load(f)
    except Exception:
        free_games = []

    active = [g for g in free_games if not is_expired(g.get("end_date"))]

    if not active:
        st.markdown('<div class="empty-state">No free games right now</div>', unsafe_allow_html=True)
        return

    total_pages = max(1, (len(active) + GAMES_PER_PAGE - 1) // GAMES_PER_PAGE)
    if st.session_state.free_games_page >= total_pages:
        st.session_state.free_games_page = total_pages - 1

    start      = st.session_state.free_games_page * GAMES_PER_PAGE
    page_games = active[start : start + GAMES_PER_PAGE]

    rows_html = ""
    for idx, game in enumerate(page_games):
        raw_worth  = (game.get("worth") or "").strip()
        show_worth = raw_worth if re.match(r'^\$\d', raw_worth) else ""

        platforms    = game.get("platforms", "")
        end_date_raw = game.get("end_date", "")
        days_lbl     = days_left_label(end_date_raw)
        exp_cls      = expiry_class(end_date_raw)
        delay        = idx * 45

        price_html = f'<span class="gr-price-was">{show_worth}</span>' if show_worth else ""

        expiry_html = (
            f'<span style="white-space:nowrap">&nbsp;·&nbsp;'
            f'<span class="gr-countdown {exp_cls}" data-expiry="{end_date_raw}">{days_lbl}</span></span>'
        ) if days_lbl else ""

        _g_link  = _html.escape(game.get("link", ""))
        _g_title = _html.escape(game.get("title", ""))
        _g_thumb = game.get("thumbnail", "").replace("'", "%27")

        rows_html += (
            f'<a href="{_g_link}" target="_blank" class="gr" '
            f'style="animation-delay:{delay}ms;">'
            f'<div class="gr-thumb" style="width:{_THUMB_W}px;height:{_THUMB_H}px;'
            f'background-size:cover;background-image:url(\'{_g_thumb}\');"></div>'
            f'<div class="gr-body">'
            f'<div style="margin-bottom:5px;display:flex;gap:6px;align-items:center;flex-wrap:wrap;">'
            f'<span class="badge-free">{CHECK_ICON}FREE</span>'
            f'<span style="font-size:.60rem;color:var(--text-3);">{price_html}</span>'
            f'</div>'
            f'<div class="gr-title">{_g_title}</div>'
            f'<div class="gr-meta">{platforms}{expiry_html}</div>'
            f'</div></a>'
        )

    st.markdown(
        f'<div id="fg-container" style="display:flex;flex-direction:column;gap:7px;">'
        f'{rows_html}</div>',
        unsafe_allow_html=True,
    )

    if total_pages > 1:
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        from ui.cards import render_pagination
        render_pagination("free_games_page", total_pages,
                          prev_key="prev_btn", next_key="next_btn")


# ── Countdown JS (live seconds ticker on expiry labels) ────────────────────────

def inject_countdown_js() -> None:
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


# ── Gaming tab ─────────────────────────────────────────────────────────────────

def render_games_tab() -> None:
    """Render the full Gaming tab content (call inside `with tab_games:`)."""
    col_news, col_free = st.columns([2, 1], gap="large")

    with col_news:
        n       = count_items(GAMES_NEWS_FILE)
        updated = get_file_age_str(GAMES_NEWS_FILE)
        section_header("GAMING", "Gaming News", count=n or None, updated=updated if n else None)
        render_news_cards(
            GAMES_NEWS_FILE,
            num_cols=2,
            per_page=GAMING_PER_PAGE,
            page_key="games_news_page",
            filter_fn=filter_for_games_tab,
            category="gaming",
        )

    with col_free:
        render_free_games_column()

    inject_countdown_js()
