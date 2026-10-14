"""
config.py — shared constants for main.py and dashboard.py.

DATA_DIR resolves to:
  - $DATA_DIR env-var  (Docker: /app/data)
  - ./data/            (local dev, Windows-safe)
"""
import os
import pathlib

_HERE = pathlib.Path(__file__).parent
DATA_DIR = pathlib.Path(os.environ.get("DATA_DIR", _HERE / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)

AI_NEWS_FILE    = DATA_DIR / "news.json"
GAMES_NEWS_FILE = DATA_DIR / "games_news.json"
FREE_GAMES_FILE = DATA_DIR / "free_games.json"
ANIME_NEWS_FILE = DATA_DIR / "anime_news.json"
CALENDAR_FILE   = DATA_DIR / "anime_calendar.json"
STATUS_FILE     = DATA_DIR / "_status.json"      # sources that failed in the last fetch

# ── Aggregator schedule ────────────────────────────────────────────────────────
FETCH_INTERVAL_MIN   = 30   # daemon fetches every N minutes, around the clock
MAX_ENTRIES_PER_FEED = 10   # newest entries taken from each feed per fetch

# ── RSS feeds ──────────────────────────────────────────────────────────────────
AI_FEEDS = {
    "🇺🇸 TechCrunch AI":        "https://techcrunch.com/category/artificial-intelligence/feed/",
    "🇺🇸 ML Mastery":           "https://machinelearningmastery.com/feed/",
    "🇺🇸 KDnuggets":            "https://www.kdnuggets.com/feed",
    "🇵🇱 Sztuczna Inteligencja": "https://www.sztucznainteligencja.org.pl/feed/",
    "🇵🇱 AntyWeb":              "https://antyweb.pl/feed",
}

GAMES_FEEDS = {
    "🇺🇸 Rock Paper Shotgun": "https://www.rockpapershotgun.com/feed/news",
    "🇺🇸 Polygon":            "https://www.polygon.com/rss/index.xml",
    "🇺🇸 GameRant":           "https://gamerant.com/feed/",
    "🇵🇱 GRY-Online":         "https://www.gry-online.pl/rss/news.xml",
    "🇵🇱 IGN Polska":         "https://pl.ign.com/feed.xml",
}

ANIME_FEEDS = {
    "🌍 Anime News Network": "https://www.animenewsnetwork.com/newsroom/rss.xml",
    "🌍 Anime Corner":       "https://animecorner.me/feed/",
    "🇬🇧 Anime UK News":     "https://animeuknews.net/feed/",
    "🌍 Otaku USA":          "https://otakuusamagazine.com/feed/",
    "🌍 ComicBook Anime":    "https://comicbook.com/anime/rss/",
}

# ── External APIs ──────────────────────────────────────────────────────────────
GAMERPOWER_URL = "https://www.gamerpower.com/api/giveaways?platform=pc"
JIKAN_BASE     = "https://api.jikan.moe/v4"

# ── Dashboard pagination ───────────────────────────────────────────────────────
AI_PER_PAGE     = 6
GAMING_PER_PAGE = 6
ANIME_PER_PAGE  = 6
GAMES_PER_PAGE  = 6   # free-games giveaways per page

# ── Dashboard live-update poll (seconds) ──────────────────────────────────────
WATCH_INTERVAL_SEC = 60
