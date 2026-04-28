import time
import json
import os
import re
import schedule
import feedparser
import requests
from datetime import datetime

GOTIFY_URL = os.environ.get("GOTIFY_URL", "http://gotify:80/message")
GOTIFY_TOKEN = os.environ.get("GOTIFY_TOKEN", "")

SCHEDULE_TIMES = ["08:00", "10:00", "12:00", "14:00", "16:00", "18:00"]

DATA_DIR = "/app/data"
AI_NEWS_FILE = os.path.join(DATA_DIR, "news.json")
GAMES_NEWS_FILE = os.path.join(DATA_DIR, "games_news.json")
FREE_GAMES_FILE = os.path.join(DATA_DIR, "free_games.json")

AI_FEEDS = {
    "🇺🇸 TechCrunch AI": "https://techcrunch.com/category/artificial-intelligence/feed/",
    "🇺🇸 ML Mastery": "https://machinelearningmastery.com/feed/",
    "🇺🇸 KDnuggets": "https://www.kdnuggets.com/feed",
    "🇵🇱 Sztuczna Inteligencja": "https://www.sztucznainteligencja.org.pl/feed/",
    "🇵🇱 AntyWeb": "https://antyweb.pl/feed"
}

GAMES_FEEDS = {
    "🇺🇸 Rock Paper Shotgun": "https://www.rockpapershotgun.com/feed/news",
    "🇺🇸 Polygon": "https://www.polygon.com/rss/index.xml",
    "🇺🇸 GameRant": "https://gamerant.com/feed/",
    "🇵🇱 GRY-Online": "https://www.gry-online.pl/rss/news.xml",
    "🇵🇱 IGN Polska": "https://pl.ign.com/feed.xml"
}


def extract_image(entry):
    if 'media_content' in entry and entry.media_content:
        return entry.media_content[0].get('url')
    if 'enclosures' in entry and entry.enclosures:
        for enc in entry.enclosures:
            if enc.get('type', '').startswith('image/') or enc.get('href', '').endswith(('.jpg', '.png', '.jpeg', '.webp')):
                return enc.get('href')
    if 'media_thumbnail' in entry and entry.media_thumbnail:
        return entry.media_thumbnail[0].get('url')

    html_content = entry.get('summary', '')
    if 'content' in entry and entry.content:
        html_content += str(entry.content[0].value)

    match = re.search(r'<img[^>]+src="([^">]+)"', html_content)
    if match:
        return match.group(1)
    return ""


def fetch_rss_feeds(feeds_dict, output_file):
    all_news = []
    for source_name, url in feeds_dict.items():
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:4]:
                all_news.append({
                    "title": entry.title,
                    "link": entry.link,
                    "published": entry.get("published", ""),
                    "source": source_name,
                    "image": extract_image(entry),
                    "summary": entry.get("summary", "")[:350] + "..." if entry.get("summary") else ""
                })
        except Exception as e:
            print(f"[{datetime.now()}] RSS fetch error for {source_name}: {e}")

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(all_news, f, ensure_ascii=False, indent=4)

    return len(all_news)


def fetch_free_games():
    try:
        response = requests.get("https://www.gamerpower.com/api/giveaways?platform=pc")
        response.raise_for_status()
        data = response.json()

        allowed_keywords = ["steam", "epic", "gog", "ea", "origin"]
        giveaways = []

        for item in data:
            platforms_str = item.get("platforms", "").lower()
            if any(keyword in platforms_str for keyword in allowed_keywords):
                giveaways.append({
                    "title": item.get("title"),
                    "link": item.get("open_giveaway_url"),
                    "thumbnail": item.get("thumbnail"),
                    "description": item.get("description"),
                    "worth": item.get("worth"),
                    "platforms": item.get("platforms"),
                    "end_date": item.get("end_date")
                })
            if len(giveaways) >= 20:
                break

        with open(FREE_GAMES_FILE, "w", encoding="utf-8") as f:
            json.dump(giveaways, f, ensure_ascii=False, indent=4)

        return len(giveaways)
    except Exception as e:
        print(f"[{datetime.now()}] GamerPower API error: {e}")
        return 0


def fetch_all_data():
    print(f"[{datetime.now()}] Starting data fetch...")
    os.makedirs(DATA_DIR, exist_ok=True)

    ai_count = fetch_rss_feeds(AI_FEEDS, AI_NEWS_FILE)
    games_count = fetch_rss_feeds(GAMES_FEEDS, GAMES_NEWS_FILE)
    free_games_count = fetch_free_games()

    print(f"[{datetime.now()}] Done. AI ({ai_count}), GamesNews ({games_count}), FreeGames ({free_games_count}).")
    send_notification()


def send_notification():
    if not GOTIFY_TOKEN or GOTIFY_TOKEN == "podaj_swoj_token_gotify":
        print(f"[{datetime.now()}] Notification skipped — no token configured.")
        return

    headers = {"X-Gotify-Key": GOTIFY_TOKEN}
    payload = {
        "message": "AI articles and free games fetched successfully!\n\n[Open Dashboard](http://news.local)",
        "title": "Daily Aggregator Ready",
        "priority": 5,
        "extras": {
            "client::display": {"contentType": "text/markdown"}
        }
    }

    try:
        requests.post(GOTIFY_URL, headers=headers, json=payload)
        print(f"[{datetime.now()}] Gotify notification sent.")
    except Exception as e:
        print(f"[{datetime.now()}] Gotify error: {e}")


if __name__ == "__main__":
    for t in SCHEDULE_TIMES:
        schedule.every().day.at(t).do(fetch_all_data)
    print(f"[{datetime.now()}] Daily Aggregator started. Scheduled at: {', '.join(SCHEDULE_TIMES)}.")
    fetch_all_data()
    while True:
        schedule.run_pending()
        time.sleep(60)
