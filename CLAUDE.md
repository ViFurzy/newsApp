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
  data/           # Runtime JSON cache (gitignored, persisted via Docker volume)
```

## Tech stack
- **Python 3.11**, **Streamlit** (UI framework)
- `feedparser`, `schedule`, `requests`, `Pillow`
- Docker Compose (single container, dual-process)
- Data: flat JSON files — no database

## Architecture
Two processes share one Docker container via `start.sh`:
1. **main.py** — fetches every 2 h (08:00–18:00 UTC), writes `data/*.json`
2. **dashboard.py** — Streamlit server on port 8501; reads JSON; triggers background refresh if file age > 30 min

Data flow: RSS feeds → `feedparser` → `news.json` / `games_news.json`; GamerPower API → `free_games.json` → Streamlit UI.

## Running locally (dev)
```bash
cd ai_news_app
pip install -r requirements.txt
# Windows: set DATA_DIR to a local path in main.py line 12 temporarily
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
| `SCHEDULE_TIMES` | 08–18 UTC every 2 h | When aggregator runs |
| `AI_FEEDS` | 5 RSS URLs | TechCrunch, ML Mastery, KDnuggets, 2× Polish |
| `GAMES_FEEDS` | 5 RSS URLs | RPS, Polygon, GameRant, 2× Polish |

## Key constants (dashboard.py)
| Symbol | Value | Purpose |
|--------|-------|---------|
| `GAMES_PER_PAGE` | 8 | Free-games pagination |
| `_STALE_AFTER_MINUTES` | 30 | On-visit refresh threshold |
| `JIKAN_BASE` | `https://api.jikan.moe/v4` | MyAnimeList wrapper API |
| Articles per tab | AI: 6/page · Gaming: 4/page · Anime: 6/page | Hard-coded in render calls |

## Design system
- Dark editorial / news theme (default) / light warm-paper toggle (bottom-right floating button)
- CSS custom properties in `:root` — edit these to change palette globally
- Fonts: Playfair Display (display/headlines), Inter (body/UI), IBM Plex Mono (meta/mono)
- Accent: `#c87038` (warm amber); consistent with newspaper ink aesthetic
- No glow effects, no grid background — clean flat dark surface
- Pagination alignment uses a JS MutationObserver that stamps `.pagination-row` on `stHorizontalBlock` — don't remove it

## Anime tab features
- **News** — 5 RSS feeds (ANN, Anime Corner, Anime UK News, Otaku USA, ComicBook Anime)
- **Genre Search** — Jikan API (MyAnimeList wrapper, no auth); genres cached in `st.session_state.jikan_genres`; results cached per genre+sort in `st.session_state.jikan_{genre_id}_{sort}`
- **Release Calendar** — stored in `/app/data/anime_calendar.json`; monthly grid view; add/done/delete per entry; navigable by month

## Anime calendar data schema
```json
[{"id": "timestamp_ms", "show": "Title", "episode": "S1E5", "date": "YYYY-MM-DD", "notes": "", "done": false}]
```

## Known issues / improvement areas
1. **No duplicate detection** — same article can appear twice if fetch overlaps
2. **No retry logic** — feed failures are silent; add `HTTPAdapter` with retries
3. **`DATA_DIR` hardcoded to `/app/data`** — breaks on Windows without change
4. **Unsplash fallback images** — URLs may break; could host locally
5. **No test suite** — zero automated tests exist

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
- Google Fonts CDN (Orbitron, Space Grotesk, JetBrains Mono)
