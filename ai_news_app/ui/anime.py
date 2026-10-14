"""
ui/anime.py — Anime tab rendering: news, genre browser, and the sync JS.
"""
import html as _html

import requests
import streamlit as st
import streamlit.components.v1 as components

from config import ANIME_NEWS_FILE, JIKAN_BASE, ANIME_PER_PAGE
from ui.cards import build_rows_skeleton, load_sorted_items, render_news_cards, section_header
from ui.helpers import count_items, get_file_age_str
from ui.filters import filter_for_anime_tab


# ── Jikan API (cached) ─────────────────────────────────────────────────────────

@st.cache_data(ttl=3600, show_spinner=False)
def fetch_genres() -> list[dict]:
    """Fetch anime genre list from Jikan API. Cached for 1 hour."""
    try:
        r = requests.get(f"{JIKAN_BASE}/genres/anime", timeout=8)
        return sorted(r.json().get("data", []), key=lambda g: g["name"])
    except Exception:
        return []


@st.cache_data(ttl=600, show_spinner=False)
def fetch_anime_by_genre(genre_id: int, sort_by: str = "score") -> list[dict]:
    """Fetch anime by genre from Jikan API. Cached for 10 minutes."""
    try:
        r = requests.get(
            f"{JIKAN_BASE}/anime",
            params={"genres": genre_id, "order_by": sort_by, "sort": "desc",
                    "limit": 20, "sfw": "true"},
            timeout=10,
        )
        return r.json().get("data", [])
    except Exception:
        return []


# ── Row renderer ───────────────────────────────────────────────────────────────

def render_anime_row(anime: dict, idx: int = 0) -> str:
    title     = _html.escape(anime.get("title", "Unknown"))
    score     = anime.get("score")
    episodes  = anime.get("episodes")
    year      = anime.get("year", "")
    status    = _html.escape(
        (anime.get("status") or "")
        .replace("Finished Airing", "Finished")
        .replace("Currently Airing", "Airing")
    )
    image_url = anime.get("images", {}).get("jpg", {}).get("image_url", "").replace("'", "%27")
    url       = _html.escape(anime.get("url", "#"))

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


# ── Anime tab ──────────────────────────────────────────────────────────────────

def render_anime_tab() -> None:
    """Render the full Anime tab content (call inside `with tab_anime:`)."""
    col_news, col_search = st.columns([2, 1], gap="large")

    # ── Left: anime news feed ──────────────────────────────────────────────────
    with col_news:
        n       = count_items(ANIME_NEWS_FILE)
        updated = get_file_age_str(ANIME_NEWS_FILE)
        section_header("ANIME", "Anime News", count=n or None, updated=updated if n else None)
        render_news_cards(
            ANIME_NEWS_FILE,
            num_cols=2,
            per_page=ANIME_PER_PAGE,
            page_key="anime_news_page",
            category="anime",
            filter_fn=filter_for_anime_tab,
        )

    # ── Right: genre browser ───────────────────────────────────────────────────
    with col_search:
        section_header("SEARCH", "Browse by Genre")

        genres      = fetch_genres()
        genre_names = ["Select a genre"] + [g["name"] for g in genres]

        sc1, sc2 = st.columns([3, 1])
        with sc1:
            selected_genre_name = st.selectbox(
                "Genre", genre_names, key="genre_select", label_visibility="collapsed"
            )
        with sc2:
            sort_option = st.selectbox(
                "Sort", ["Score", "Popularity", "Members"],
                key="genre_sort", label_visibility="collapsed",
            )

        sort_map = {"Score": "score", "Popularity": "popularity", "Members": "members"}
        sort_by  = sort_map.get(sort_option, "score")

        if selected_genre_name != "Select a genre":
            selected_genre = next(
                (g for g in genres if g["name"] == selected_genre_name), None
            )
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

    # ── Sync JS: match genre-list height to news column height ─────────────────
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
