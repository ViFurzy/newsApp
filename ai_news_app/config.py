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
VIBE_NEWS_FILE   = DATA_DIR / "vibe_news.json"
DESIGN_NEWS_FILE = DATA_DIR / "design_news.json"
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

# Vibe coding / AI-assisted dev. Probed live 2026-10-15 (HTTP 200, fresh, parseable).
# Latent Space and itwiz.pl are broad: ui/filters.py keeps only vibe-relevant items from them.
VIBE_FEEDS = {
    "🇺🇸 Simon Willison":  "https://simonwillison.net/tags/vibe-coding.atom",
    "🇺🇸 Addy Osmani":     "https://addyo.substack.com/feed",
    "🇺🇸 Latent Space":    "https://www.latent.space/feed",
    "🇺🇸 DEV Vibe Coding": "https://dev.to/feed/tag/vibecoding",
    "🌍 r/vibecoding":              "https://www.reddit.com/r/vibecoding/top/.rss?t=week",
    "🇵🇱 ITwiz":           "https://itwiz.pl/feed/",
}

# Design, UX and visual culture. Same probe; dropped: stale (CSS-Tricks, A List Apart, Awwwards)
# and dead/blocked (Codrops, It's Nice That, Core77, Designer News).
DESIGN_FEEDS = {
    "🌍 Smashing Magazine": "https://www.smashingmagazine.com/feed/",
    "🌍 UX Collective":     "https://uxdesign.cc/feed",
    "🇺🇸 NN/g":    "https://www.nngroup.com/feed/rss/",
    "🌍 Abduzeedo":         "https://abduzeedo.com/rss.xml",
    "🌍 Muzli":             "https://medium.muz.li/feed",
    "🇬🇧 Dezeen":  "https://www.dezeen.com/feed/",
    "🇵🇱 Design Alley": "https://www.designalley.pl/feed/",
}

# ── External APIs ──────────────────────────────────────────────────────────────
GAMERPOWER_URL = "https://www.gamerpower.com/api/giveaways?platform=pc"
JIKAN_BASE     = "https://api.jikan.moe/v4"

# ── Dashboard pagination ───────────────────────────────────────────────────────
AI_PER_PAGE     = 6
GAMING_PER_PAGE = 6
ANIME_PER_PAGE  = 6
GAMES_PER_PAGE  = 6   # free-games giveaways per page
VIBE_PER_PAGE   = 6
DESIGN_PER_PAGE = 6

# ── Per-tab page backgrounds (order = tab order) ──────────────────────────────
# Photos are dimmed by the page overlay; "tint" is a faint colour wash. To swap one,
# change the photo id. Alternates (all verified to load) are listed under each section.
def _unsplash(photo_id: str) -> str:
    return f"https://images.unsplash.com/photo-{photo_id}?w=1920&q=50"

TAB_BACKGROUNDS = [
    {"key": "ai",     "image": _unsplash("1677442136019-21780ecad995"), "tint": "rgba(91,156,246,0.040)"},
    {"key": "gaming", "image": _unsplash("1542751371-adc38448a05e"),    "tint": "rgba(34,197,94,0.032)"},
    {"key": "anime",  "image": _unsplash("1578632767115-351597cf2477"), "tint": "rgba(167,139,250,0.040)"},
    # vibe alternates: 1461749280684-dccba630e2f6 (code), 1526374965328-7f61d4dc18c5 (matrix), 1555066931-4365d14bab8c (IDE)
    {"key": "vibe",   "image": _unsplash("1605379399642-870262d3d051"), "tint": "rgba(34,211,238,0.040)"},
    # design alternates: 1550684848-fac1c5b4e853 (colour bubbles), 1561070791-2526d30994b5 (swatches), 1513364776144-60967b0f800f (paint)
    {"key": "design", "image": _unsplash("1541701494587-cb58502866ab"), "tint": "rgba(236,72,153,0.040)"},
    # saved alternates: 1524995997946-a1c2e315a42f (curved library), 1507842217343-583bb7270b66 (shelves)
    {"key": "saved",  "image": _unsplash("1481627834876-b7833e8f5570"), "tint": "rgba(200,112,56,0.045)"},
]

# ── Dashboard live-update poll (seconds) ──────────────────────────────────────
WATCH_INTERVAL_SEC = 60
