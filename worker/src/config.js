// Feeds, limits and schedule. Mirrors ai_news_app/config.py.

export const FEEDS = {
  ai: {
    "🇺🇸 TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "🇺🇸 ML Mastery": "https://machinelearningmastery.com/feed/",
    "🇺🇸 KDnuggets": "https://www.kdnuggets.com/feed",
    "🇵🇱 Sztuczna Inteligencja": "https://www.sztucznainteligencja.org.pl/feed/",
    "🇵🇱 AntyWeb": "https://antyweb.pl/feed",
  },
  games: {
    "🇺🇸 Rock Paper Shotgun": "https://www.rockpapershotgun.com/feed/news",
    "🇺🇸 Polygon": "https://www.polygon.com/rss/index.xml",
    "🇺🇸 GameRant": "https://gamerant.com/feed/gaming/", // main feed mixes in anime/movies/TV
    "🇵🇱 GRY-Online": "https://www.gry-online.pl/rss/news.xml",
    "🇵🇱 Eurogamer PL": "https://www.eurogamer.pl/feed",
    "🇵🇱 CD-Action": "https://cdaction.pl/rss",
  },
  anime: {
    "🌍 Anime News Network": "https://www.animenewsnetwork.com/newsroom/rss.xml",
    "🌍 Anime Corner": "https://animecorner.me/feed/",
    "🇬🇧 Anime UK News": "https://animeuknews.net/feed/",
    "🌍 Otaku USA": "https://otakuusamagazine.com/feed/",
    "🌍 ComicBook Anime": "https://comicbook.com/anime/rss/",
    "🌍 MyAnimeList": "https://myanimelist.net/rss/news.xml", // ships a thumbnail for every item
  },
  vibe: {
    "🇺🇸 Simon Willison": "https://simonwillison.net/tags/vibe-coding.atom",
    "🇺🇸 Addy Osmani": "https://addyo.substack.com/feed",
    "🇺🇸 Latent Space": "https://www.latent.space/feed",
    "🇺🇸 DEV Vibe Coding": "https://dev.to/feed/tag/vibecoding",
    "🌍 r/vibecoding": "https://www.reddit.com/r/vibecoding/top/.rss?t=week",
    "🇵🇱 ITwiz": "https://itwiz.pl/feed/",
  },
  design: {
    "🌍 Smashing Magazine": "https://www.smashingmagazine.com/feed/",
    "🌍 UX Collective": "https://uxdesign.cc/feed",
    "🇺🇸 NN/g": "https://www.nngroup.com/feed/rss/",
    "🌍 Abduzeedo": "https://abduzeedo.com/rss.xml",
    "🌍 Muzli": "https://medium.muz.li/feed",
    "🇬🇧 Dezeen": "https://www.dezeen.com/feed/",
    "🇵🇱 Design Alley": "https://www.designalley.pl/feed/",
  },
};

export const GAMERPOWER_URL = "https://www.gamerpower.com/api/giveaways?platform=pc";

// cron expression (as in wrangler.toml) -> section it refreshes
export const CRONS = {
  "0,30 * * * *": "ai",
  "5,35 * * * *": "games",
  "10,40 * * * *": "anime",
  "15,45 * * * *": "vibe",
  "20,50 * * * *": "design",
};

// Sections whose feeds ship no images: read og:image from the article page, at most OG_PER_RUN pages per cron run.
export const OG_IMAGE_CATS = ["anime"];
export const OG_PER_RUN = 12;

export const MAX_ENTRIES_PER_FEED = 10;
export const MAX_ITEMS_KEPT = 90;
export const MAX_PER_SOURCE = 15;
export const STALE_AFTER_MS = 60 * 60 * 1000; // /api/stamp kicks a refresh when data is older than this
