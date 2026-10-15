import io
import json

import pytest
from PIL import Image

import main

pytestmark = pytest.mark.real_images


def _png(w, h, color=(200, 80, 40)):
    buf = io.BytesIO()
    Image.new("RGB", (w, h), color).save(buf, "PNG")
    return buf.getvalue()


class _Raw:
    def __init__(self, data):
        self._d = data

    def read(self, n, decode_content=True):
        return self._d[:n]


class _Resp:
    def __init__(self, status=200, ctype="image/png", data=b"", location=None):
        self.status_code = status
        self.headers = {"content-type": ctype, **({"Location": location} if location else {})}
        self.is_redirect = location is not None
        self.raw = _Raw(data)

    def close(self):
        pass


@pytest.mark.parametrize("host,ok", [
    ("8.8.8.8", True),
    ("127.0.0.1", False), ("10.0.0.5", False), ("192.168.1.10", False),
    ("169.254.169.254", False),            # cloud metadata endpoint
    ("::1", False), ("localhost", False),
])
def test_public_host(host, ok):
    assert main._public_host(host) is ok


def test_download_never_requests_private_hosts(monkeypatch):
    monkeypatch.setattr(main._http, "get", lambda *a, **k: pytest.fail("must not request a private host"))
    assert main._download_image("http://127.0.0.1/x.png", "https://r/") is None
    assert main._download_image("http://169.254.169.254/latest/meta-data", "https://r/") is None
    assert main._download_image("file:///etc/passwd", "https://r/") is None


def test_download_revalidates_redirect_targets(monkeypatch):
    calls = []

    def fake_get(url, **k):
        calls.append(url)
        return _Resp(302, location="http://10.0.0.5/secret.png")      # public host redirecting inward

    monkeypatch.setattr(main, "_public_host", lambda h: not h.startswith("10."))
    monkeypatch.setattr(main._http, "get", fake_get)
    assert main._download_image("https://cdn.example/a.png", "https://r/") is None
    assert calls == ["https://cdn.example/a.png"]                       # the private hop was never requested


@pytest.mark.parametrize("resp,expected_none", [
    (_Resp(200, "text/html", b"<html>"), True),
    (_Resp(403, "image/png", b"x"), True),
    (_Resp(200, "image/png", b"x" * (main._MAX_IMG_BYTES + 5)), True),
    (_Resp(200, "image/png", b"ok"), False),
], ids=["not-an-image", "forbidden", "too-big", "fine"])
def test_download_validation(monkeypatch, resp, expected_none):
    monkeypatch.setattr(main, "_public_host", lambda h: True)
    monkeypatch.setattr(main._http, "get", lambda *a, **k: resp)
    assert (main._download_image("https://cdn.example/a.png", "https://r/") is None) is expected_none


@pytest.fixture
def img_dir(tmp_path, monkeypatch):
    d = tmp_path / "img"
    monkeypatch.setattr(main, "IMG_DIR", d)
    return d


def test_localize_shrinks_and_does_not_redownload(monkeypatch, img_dir):
    n = []
    monkeypatch.setattr(main, "_download_image", lambda u, r: n.append(u) or _png(2000, 1000))
    e = main.localize_image({"image": "https://cdn.example/big.png", "link": "https://a/1"})
    assert e["image"].startswith(main.IMG_URL_PREFIX + "/") and e["image"].endswith(".webp")
    saved = img_dir / e["image"].rsplit("/", 1)[1]
    with Image.open(saved) as im:
        assert im.width == 720 and im.height == 360
    main.localize_image({"image": "https://cdn.example/big.png", "link": "https://a/1"})
    assert len(n) == 1                                                  # second call hit the cache


def test_localize_crops_very_tall_images(monkeypatch, img_dir):
    monkeypatch.setattr(main, "_download_image", lambda u, r: _png(720, 3000))
    e = main.localize_image({"image": "https://cdn.example/tall.png", "link": "https://a/1"})
    with Image.open(img_dir / e["image"].rsplit("/", 1)[1]) as im:
        assert im.height == main._IMG_MAX_HEIGHT


@pytest.mark.parametrize("download", [lambda u, r: None, lambda u, r: b"not an image"], ids=["blocked", "corrupt"])
def test_localize_failure_clears_image_so_card_uses_fallback(monkeypatch, img_dir, download):
    monkeypatch.setattr(main, "_download_image", download)
    assert main.localize_image({"image": "https://cdn.example/x.png", "link": "https://a/1"})["image"] == ""


def test_localize_leaves_empty_and_already_local_alone(img_dir):
    assert main.localize_image({"image": ""})["image"] == ""
    local = {"image": main.IMG_URL_PREFIX + "/abc.webp"}
    assert main.localize_image(dict(local)) == local


def test_prune_removes_only_unreferenced(tmp_path, img_dir):
    img_dir.mkdir()
    (img_dir / "keep.webp").write_bytes(b"1")
    (img_dir / "drop.webp").write_bytes(b"1")
    data = tmp_path / "news.json"
    data.write_text(json.dumps([{"image": f"{main.IMG_URL_PREFIX}/keep.webp"}, {"image": ""}]), encoding="utf-8")
    assert main.prune_images([data]) == 1
    assert sorted(p.name for p in img_dir.iterdir()) == ["keep.webp"]


def test_prune_does_nothing_if_a_data_file_is_unreadable(tmp_path, img_dir):
    img_dir.mkdir()
    (img_dir / "a.webp").write_bytes(b"1")
    bad = tmp_path / "news.json"
    bad.write_text("{broken", encoding="utf-8")
    assert main.prune_images([bad]) == 0 and (img_dir / "a.webp").exists()
