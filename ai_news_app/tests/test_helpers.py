import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import parse_entries  # noqa: E402
from ui.helpers import get_fallback_image, strip_html  # noqa: E402


@pytest.mark.parametrize("raw,expected", [
    ("plain", "plain"),
    ("<p>Hi <b>there</b></p>", "Hi there"),
    ("&lsquo;GODZILLA&rsquo; &amp; co", "\u2018GODZILLA\u2019 & co"),
    ('cut off <a href="https://www.gry-', "cut off"),          # truncated, unterminated tag
    ("&amp;quot;Steam&amp;quot;", '"Steam"'),                   # double-encoded
    ("a   \n  b", "a b"),
    ("", ""),
    (None, ""),
], ids=["plain", "tags", "entities", "unterminated-tag", "double-encoded", "whitespace", "empty", "none"])
def test_strip_html(raw, expected):
    assert strip_html(raw) == expected


@pytest.mark.parametrize("title", [
    "The Feature-length Documentary TEZUKA! God of Manga is Live on Kickstarter",
    "Godzilla Vs. Everything Hits Comic Stores March 2027",
    "Again the main chair ran away",                      # contains "ai" only as a substring
], ids=["tezuka", "godzilla", "substring-ai"])
def test_ai_image_not_used_for_substring_matches(title):
    ai_img = get_fallback_image("OpenAI ships a new LLM")
    assert get_fallback_image(title) != ai_img


def test_whole_word_ai_still_matches():
    assert get_fallback_image("How AI changes search") == get_fallback_image("ChatGPT update")


@pytest.mark.parametrize("category,expect_word", [("anime", "1578632767115"), ("gaming", "1552820728"), ("ai", "1518770660439")])
def test_category_default_when_no_keywords(category, expect_word):
    assert expect_word in get_fallback_image("Zzz qqq", "", category)


def test_summary_is_cleaned_before_truncation():
    body = "<p>" + ("word " * 200) + '<a href="https://example.com/very/long">link</a></p>'
    xml = (f'<rss version="2.0"><channel><title>t</title><item><title>x</title>'
           f'<link>https://x/1</link><description><![CDATA[{body}]]></description></item></channel></rss>')
    summary = parse_entries(xml, "s")[0]["summary"]
    assert "<" not in summary and "href" not in summary
    assert len(summary) <= 351 and summary.endswith("\u2026")


ITEMS = [
    {"title": "OpenAI ships GPT", "summary": "model news", "source": "A"},
    {"title": "Steam sale", "summary": "games on discount", "source": "B"},
    {"title": "Anime season", "summary": "Steam mention", "source": "B"},
]


@pytest.mark.parametrize("query,sources,expected_titles", [
    ("", [], ["OpenAI ships GPT", "Steam sale", "Anime season"]),
    ("steam", [], ["Steam sale", "Anime season"]),          # matches title or summary, any case
    ("  STEAM ", ["B"], ["Steam sale", "Anime season"]),
    ("", ["A"], ["OpenAI ships GPT"]),
    ("steam", ["A"], []),
    (None, None, ["OpenAI ships GPT", "Steam sale", "Anime season"]),
], ids=["no-filter", "query", "query+source", "source-only", "no-match", "none-args"])
def test_filter_items(query, sources, expected_titles):
    from ui.cards import filter_items
    assert [i["title"] for i in filter_items(ITEMS, query, sources)] == expected_titles
