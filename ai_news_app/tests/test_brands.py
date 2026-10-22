import pytest

import main
from ui.brands import card_svg, find_brand


@pytest.mark.parametrize("title,label", [
    ("Meta says Muse has over 10M users, with shopping a top activity", "Meta"),
    ("While Amazon blocks AI agents, Walmart rolls out the welcome mat", "Amazon"),
    ("Huawei stawia na Polskę. Wielkie spotkanie branży", "Huawei"),
    ("TechCrunch Founder Summit 2026: Everything you need to know", "TechCrunch"),
    ("Why OpenAI and Microsoft are fighting", "OpenAI"),     # earliest mention wins
])
def test_find_brand(title, label):
    assert find_brand(title)[0] == label


@pytest.mark.parametrize("title", [
    "Recursive launches Flint, a laptop coding model",
    "An apple a day, metaverse hype and Intelligence reports",   # fruit / substrings are not brands
])
def test_find_brand_none(title):
    assert find_brand(title) is None


def test_card_svg_logo_and_wordmark_escape():
    assert '<path d="M0 0"/>' in card_svg("Meta", ["M0 0"])
    assert "<script" not in card_svg("<script>", [])


def test_brand_image_builds_cached_card(monkeypatch, tmp_path):
    monkeypatch.setattr(main, "IMG_DIR", tmp_path)
    calls = []

    class R:
        status_code, text = 200, '<svg><path d="M1 1h2"/></svg>'
        def raise_for_status(self): pass

    monkeypatch.setattr(main._http, "get", lambda *a, **k: calls.append(a) or R())
    e = main.brand_image({"title": "Meta says Muse", "image": ""})
    assert e["image"] == "/app/static/img/brand-meta.svg"
    assert 'd="M1 1h2"' in (tmp_path / "brand-meta.svg").read_text(encoding="utf-8")
    main.brand_image({"title": "Meta again", "image": ""})
    assert len(calls) == 1                                    # second article reuses the cached card


def test_brand_image_keeps_real_images_and_unknown_titles(monkeypatch):
    monkeypatch.setattr(main._http, "get", lambda *a, **k: pytest.fail("no network"))
    assert main.brand_image({"title": "Meta", "image": "/app/static/img/x.webp"})["image"] == "/app/static/img/x.webp"
    assert main.brand_image({"title": "Nothing here", "image": ""})["image"] == ""
