import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

import config  # noqa: E402
from ui.filters import filter_for_vibe_tab  # noqa: E402
from ui.helpers import FLAG_MAP, get_fallback_image, parse_source  # noqa: E402

ALL_FEEDS = {**config.AI_FEEDS, **config.GAMES_FEEDS, **config.ANIME_FEEDS,
             **config.VIBE_FEEDS, **config.DESIGN_FEEDS}


def test_feed_config_is_sane():
    urls = [u for d in (config.VIBE_FEEDS, config.DESIGN_FEEDS) for u in d.values()]
    assert all(u.startswith("https://") for u in urls)
    assert len(urls) == len(set(urls))                                  # no duplicate feeds
    total = len(config.AI_FEEDS) + len(config.GAMES_FEEDS) + len(config.ANIME_FEEDS) \
        + len(config.VIBE_FEEDS) + len(config.DESIGN_FEEDS)
    assert total == len(ALL_FEEDS)                                       # source names unique: card badges/chips key on them


@pytest.mark.parametrize("name", list(config.VIBE_FEEDS) + list(config.DESIGN_FEEDS))
def test_source_flag_is_renderable(name):
    flag, label = parse_source(name)
    assert flag in FLAG_MAP and label                                    # unknown flag would render as nothing


def test_backgrounds_cover_every_tab_in_order():
    assert [b["key"] for b in config.TAB_BACKGROUNDS] == ["ai", "gaming", "anime", "vibe", "design", "saved"]
    assert len({b["image"] for b in config.TAB_BACKGROUNDS}) == 6        # each section has its own picture


ITEMS = [
    {"title": "Cursor ships agent mode", "summary": "", "source": "\U0001F1FA\U0001F1F8 Latent Space"},
    {"title": "Lab-in-the-Loop at compute speed", "summary": "biology", "source": "\U0001F1FA\U0001F1F8 Latent Space"},
    {"title": "Cisco otworzylo laboratorium", "summary": "sieci", "source": "\U0001F1F5\U0001F1F1 ITwiz"},
    {"title": "Vibe Coding podbija rynek", "summary": "", "source": "\U0001F1F5\U0001F1F1 ITwiz"},
    {"title": "Scrimshaw Jukebox", "summary": "", "source": "\U0001F1FA\U0001F1F8 Simon Willison"},   # focused feed: always kept
]


def test_vibe_filter_trims_broad_feeds_only():
    kept = [i["title"] for i in filter_for_vibe_tab(ITEMS)]
    assert kept == ["Cursor ships agent mode", "Vibe Coding podbija rynek", "Scrimshaw Jukebox"]


@pytest.mark.parametrize("category", ["vibe", "design"])
def test_fallback_pool_is_stable_and_varied(category):
    titles = [f"story number {i}" for i in range(40)]
    imgs = [get_fallback_image(t, "", category) for t in titles]
    assert imgs == [get_fallback_image(t, "", category) for t in titles]   # deterministic across reruns
    assert len(set(imgs)) >= 3                                              # not one repeated picture


def _g(source, tags):
    d = {"title": "t", "summary": "", "source": source}
    if tags is not None:
        d["tags"] = tags
    return d


@pytest.mark.parametrize("item,kept", [
    (_g("\U0001F1FA\U0001F1F8 Polygon", ["Gaming", "xbox"]), True),
    (_g("\U0001F1FA\U0001F1F8 Polygon", ["Movies", "Obsession"]), False),
    (_g("\U0001F1FA\U0001F1F8 Polygon", ["TV", "Yellowjackets"]), False),
    (_g("\U0001F1FA\U0001F1F8 Polygon", ["FYI", "Magic: The Gathering"]), False),
    (_g("\U0001F1F5\U0001F1F1 GRY-Online", ["gry", "Rockstar Games"]), True),
    (_g("\U0001F1F5\U0001F1F1 GRY-Online", ["Filmy i seriale", "Netflix"]), False),   # case-insensitive
    (_g("\U0001F1FA\U0001F1F8 GameRant", []), True),                                # tagged but empty: keep
    (_g("\U0001F1FA\U0001F1F8 GameRant", None), False),                              # legacy item from a mixed feed
    (_g("\U0001F1FA\U0001F1F8 Rock Paper Shotgun", None), True),                     # legacy item from a games-only feed
], ids=["polygon-game", "polygon-movie", "polygon-tv", "polygon-fyi", "gry-game", "gry-film-case",
        "empty-tags", "legacy-mixed", "legacy-gamesonly"])
def test_games_tab_filter(item, kept):
    from ui.filters import filter_for_games_tab
    assert bool(filter_for_games_tab([item])) is kept
