import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))


@pytest.fixture(autouse=True)
def _no_image_downloads(request, monkeypatch):
    """Feed-fetch tests must never touch the network for images."""
    if request.node.get_closest_marker("real_images"):
        return
    import main
    monkeypatch.setattr(main, "localize_image", lambda entry: entry)
