# DailyAPP — Claude Code Guide

## What this app is
A cyberpunk-themed news aggregator dashboard. It pulls AI/tech and gaming articles from RSS feeds, plus free PC game giveaways from GamerPower API, and presents them in a Streamlit web UI.

## Project layout
```
ai_news_app/
  main.py         # Background aggregator daemon (RSS + GamerPower → JSON)
  dashboard.py    # Streamlit frontend (reads JSON, renders cards/pagination)
  requirements.txt
  Dockerfile
  docker-compose.yml
  start.sh        # Entrypoint: runs main.py in background, Streamlit in foreground
  .env / .env.example
  config.py       # Shared constants (feeds, intervals, per-page counts, file paths)
  ui/             # style.css, fonts.css, styles.py (JS), cards/games/anime/ticker/helpers/filters
  static/fonts/   # Self-hosted woff2 (Geist, Geist Mono, Playfair Display), served via Streamlit static serving
  tests/          # pytest: feed parsing, merge/dedup, failure handling, text cleaning, filters
  data/           # Runtime JSON cache (gitignored, persisted via Docker volume)
```

## Tech stack
- **Python 3.11**, **Streamlit** (UI framework)
- `feedparser`, `schedule`, `requests`, `Pillow`; tests: `pip install -r requirements-dev.txt && pytest tests`
- Docker Compose (single container, dual-process)
- Data: flat JSON files — no database

## Architecture
Two processes share one Docker container via `start.sh`:
1. **main.py** — owns all fetching: every 30 min, 24/7, feeds in parallel with conditional GET (ETag / Last-Modified, cache in `data/_http_cache.json`), writes `data/*.json`
2. **dashboard.py** — Streamlit server on port 8501; read-only. An `st.fragment` polls the data files' mtime every 60 s and reruns the app when they change, so new posts appear without a manual refresh

Data flow: RSS feeds → `feedparser` → `news.json` / `games_news.json`; GamerPower API → `free_games.json` → Streamlit UI.

## Running locally (dev)
```bash
cd ai_news_app
pip install -r requirements.txt
python main.py        # in terminal 1
streamlit run dashboard.py  # in terminal 2
```

## Docker
```bash
cd ai_news_app
docker compose up --build
# Dashboard at http://localhost:8501
```

## Key constants (main.py)
| Symbol | Value | Purpose |
|--------|-------|---------|
| `DATA_DIR` | `/app/data` | JSON output dir (Docker path) |
| `FETCH_INTERVAL_MIN` | 30 | Aggregator interval (config.py) |
| `MAX_ENTRIES_PER_FEED` | 10 | Newest entries per feed per fetch (config.py) |
| `AI_FEEDS` | 5 RSS URLs | TechCrunch, ML Mastery, KDnuggets, 2× Polish |
| `GAMES_FEEDS` | 5 RSS URLs | RPS, Polygon, GameRant, 2× Polish |

## Key constants (dashboard.py)
| Symbol | Value | Purpose |
|--------|-------|---------|
| `GAMES_PER_PAGE` | 8 | Free-games pagination |
| `WATCH_INTERVAL_SEC` | 60 | Live-update poll interval (config.py) |
| `GAMING_PER_PAGE` | 6 | Gaming news cards per page (config.py) |
| `JIKAN_BASE` | `https://api.jikan.moe/v4` | MyAnimeList wrapper API |
| Articles per tab | AI: 6/page · Gaming: 6/page · Anime: 6/page | `AI_PER_PAGE` / `GAMING_PER_PAGE` / `ANIME_PER_PAGE` in config.py |

## Design system
- Dark editorial / news theme (default) / light warm-paper toggle (bottom-right floating button). Tabs: AI & Tech, Gaming, Anime, Saved
- CSS custom properties in `:root` — edit these to change palette globally
- Fonts: Playfair Display (display/headlines), Geist (body/UI), Geist Mono (meta/mono)
- CSS lives in `ai_news_app/ui/style.css`; JS in `ui/styles.py` (one iframe)
- Accent: `#c87038` (warm amber); consistent with newspaper ink aesthetic
- No glow effects, no grid background — clean flat dark surface
- Pagination alignment uses a JS MutationObserver that stamps `.pagination-row` on `stHorizontalBlock` — don't remove it

## Features added in the UX pass
- **Search + source chips** above every news grid (`ui/cards.py: _filter_bar`); picking sources is also how you hide the others. Changing a filter resets to page 1.
- **Read later**: star button on each card; saved cards (full card HTML) live in the browser's `localStorage` key `_da_saved` and render in the **Saved** tab (`_JS_SAVED` in `ui/styles.py`). Per browser, not synced.
- **Failed-source notice**: `main.py` writes `data/_status.json` (`{"failed": [...]}`); the masthead shows it.
- **Ticker**: keyboard-skipped, loop copy is `aria-hidden`, has a pause button (CSS-only checkbox).
- Streamlit theme is pinned `base = "dark"` with amber `primaryColor` in `.streamlit/config.toml`; search/chips are restyled from the app's own CSS tokens so they follow the light toggle.
- Fallback card images use whole-word keyword rules, then a per-tab default; `<img>` has `onerror` fallback + `referrerpolicy="no-referrer"`.
- NEW badge = published < 3 h ago.

## Anime tab features
- **News** — 5 RSS feeds (ANN, Anime Corner, Anime UK News, Otaku USA, ComicBook Anime)
- **Genre Search** — Jikan API (MyAnimeList wrapper, no auth); genres cached in `st.session_state.jikan_genres`; results cached per genre+sort in `st.session_state.jikan_{genre_id}_{sort}`
- **Release Calendar** — stored in `/app/data/anime_calendar.json`; monthly grid view; add/done/delete per entry; navigable by month

## Anime calendar data schema
```json
[{"id": "timestamp_ms", "show": "Title", "episode": "S1E5", "date": "YYYY-MM-DD", "notes": "", "done": false}]
```

## Known issues / improvement areas
1. **Unsplash fallback images** — URLs may break and repeat across cards; could host locally
2. **Tests** — only parser/merge logic covered (`tests/test_main.py`)

## Data schemas
**news.json / games_news.json** (array of):
```json
{"title": "", "link": "", "published": "RFC 2822 string", "source": "🇺🇸 Name", "image": "", "summary": ""}
```
**free_games.json** (array of):
```json
{"title": "", "link": "", "thumbnail": "", "description": "", "worth": "$X.XX", "platforms": "", "end_date": "YYYY-MM-DD HH:MM:SS"}
```

## External dependencies
- GamerPower API: `https://www.gamerpower.com/api/giveaways?platform=pc` (no auth)
- flagcdn.com for flag images in cards
- Unsplash for fallback article images (no auth, URL-based)
- Google Fonts CDN (Playfair Display, Geist, Geist Mono)

## graphify

This project has a knowledge graph at graphify-out/ with god nodes, community structure, and cross-file relationships.

Rules:
- For codebase questions, first run `graphify query "<question>"` when graphify-out/graph.json exists. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts. These return a scoped subgraph, usually much smaller than GRAPH_REPORT.md or raw grep output.
- If graphify-out/wiki/index.md exists, use it for broad navigation instead of raw source browsing.
- Read graphify-out/GRAPH_REPORT.md only for broad architecture review or when query/path/explain do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
