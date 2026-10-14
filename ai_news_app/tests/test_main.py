"""Run: python -m pytest tests  (or: python tests/test_main.py)"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import merge_items, parse_entries  # noqa: E402

XML = """<?xml version="1.0"?><rss version="2.0"><channel><title>t</title>
<item><title>Old</title><link>https://x/old</link><pubDate>Mon, 01 Jan 2024 10:00:00 GMT</pubDate>
<description>old body</description></item>
<item><title>New</title><link>https://x/new</link><pubDate>Tue, 02 Jan 2024 10:00:00 GMT</pubDate>
<description><![CDATA[<img src="https://x/i.jpg"> body]]></description></item>
<item><title>No link</title></item>
</channel></rss>"""


def test_parse_skips_linkless_and_extracts_image():
    items = parse_entries(XML, "src")
    assert [i["link"] for i in items] == ["https://x/old", "https://x/new"]
    assert items[1]["image"] == "https://x/i.jpg"
    assert items[0]["source"] == "src"


def test_merge_dedups_by_link_and_sorts_newest_first():
    items = parse_entries(XML, "src")
    existing = {i["link"]: i for i in items}
    updated = dict(items[0], title="Old (edited)")
    merged = merge_items(existing, [updated])
    assert len(merged) == 2
    assert [m["link"] for m in merged] == ["https://x/new", "https://x/old"]
    assert merged[1]["title"] == "Old (edited)"


if __name__ == "__main__":
    test_parse_skips_linkless_and_extracts_image()
    test_merge_dedups_by_link_and_sorts_newest_first()
    print("ok")


def test_gry_online_boilerplate_footer_is_trimmed():
    xml = ('<rss version="2.0"><channel><title>t</title><item><title>Big News</title><link>https://x/1</link>'
           '<description>Real text.Informacja Big News została opublikowana w serwisie.</description></item></channel></rss>')
    assert parse_entries(xml, "s")[0]["summary"] == "Real text."


class _Resp:
    def __init__(self, status=200, text="", headers=None):
        self.status_code, self.text, self.headers = status, text, headers or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


def test_fetch_one_reports_failure_and_keeps_validators(monkeypatch):
    import main
    monkeypatch.setattr(main._http, "get", lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom")))
    old = {"etag": "abc"}
    assert main._fetch_one("src", "https://x/feed", old) == ([], old, False)


def test_fetch_one_304_is_ok_not_a_failure(monkeypatch):
    import main
    monkeypatch.setattr(main._http, "get", lambda *a, **k: _Resp(304))
    old = {"etag": "abc"}
    assert main._fetch_one("src", "https://x/feed", old) == ([], old, True)


def test_fetch_rss_feeds_collects_failed_sources(monkeypatch, tmp_path):
    import main
    def fake_get(url, **k):
        return _Resp(200, XML) if url.endswith("/good") else _Resp(500)
    monkeypatch.setattr(main._http, "get", fake_get)
    failed = []
    out = tmp_path / "news.json"
    n = main.fetch_rss_feeds({"Good": "https://x/good", "Bad": "https://x/bad"}, out, {}, failed)
    assert failed == ["Bad"] and n == 2 and out.exists()


def test_merge_keeps_slow_sources_via_per_source_cap():
    import main
    fast = [{"link": f"https://f/{i}", "source": "fast", "published": f"Tue, 02 Jan 2024 {h:02d}:00:00 GMT"}
            for i, h in enumerate(range(23))]                              # 23 recent items
    slow = [{"link": "https://s/1", "source": "slow", "published": "Mon, 01 Jan 2024 01:00:00 GMT"}]
    merged = main.merge_items({}, fast + slow)
    assert sum(1 for m in merged if m["source"] == "fast") == main._MAX_PER_SOURCE
    assert any(m["source"] == "slow" for m in merged)                      # older but still present
