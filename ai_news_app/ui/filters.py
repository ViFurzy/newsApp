"""
ui/filters.py — Content-level signal words and tab-assignment filters.

Pure functions; no Streamlit dependency.
"""

# ── Gaming signals — strong title-level indicators ────────────────────────────
_GAMING_TITLE_TERMS = frozenset([
    "xbox", "playstation", "ps5", "ps4", "nintendo", "switch lite",
    "steam", "gameplay", "game review", "dlc", "patch notes",
    "battle royale", "early access", "game of the year", "game pass",
    "fortnite", "minecraft", "call of duty", "grand theft auto",
    "league of legends", "counter-strike", "valorant", "overwatch",
    "apex legends", "elden ring", "baldur's gate", "diablo",
    "world of warcraft", "final fantasy xvi", "street fighter",
    "esports tournament", "gaming chair", "gaming headset",
])

# ── AI/tech signals — presence keeps item in AI tab even if gaming terms appear
_AI_TECH_TERMS = frozenset([
    " ai ", "artificial intelligence", "machine learning", "llm", "gpt",
    "chatgpt", "openai", "anthropic", "deepmind", "neural network",
    " nlp ", "language model", "generative ai", "diffusion model",
    "tech ", "technology", "software", "hardware", "processor", "chip",
    "robotics", "algorithm", "data science", "startup", "cloud computing",
    "cybersecurity", "programming", "quantum", "automation",
])


def _item_text(item: dict) -> str:
    return " " + (item.get("title", "") + " " + item.get("summary", "")).lower() + " "


def _is_gaming_title(item: dict) -> bool:
    t = " " + item.get("title", "").lower() + " "
    return any(term in t for term in _GAMING_TITLE_TERMS)


def _has_ai_signal(item: dict) -> bool:
    return any(term in _item_text(item) for term in _AI_TECH_TERMS)


def filter_for_ai_tab(items: list[dict]) -> list[dict]:
    """Drop articles that are pure gaming with no AI/tech angle."""
    return [it for it in items if not (_is_gaming_title(it) and not _has_ai_signal(it))]


def filter_for_anime_tab(items: list[dict]) -> list[dict]:
    """Drop gaming articles from the anime tab (anime-based games belong in Gaming)."""
    return [it for it in items if not _is_gaming_title(it)]
