from __future__ import annotations

import functools
import http.server
import os
import threading
from collections.abc import Iterator
from pathlib import Path

import pytest

SITE = Path(__file__).parent / "site"


@pytest.fixture(scope="session")
def chromium() -> str:
    """Cần Chromium thật; CI không cài nên bỏ qua. Trên máy dev: DEMO_CHROMIUM_PATH=<chrome>."""
    path = os.environ.get("DEMO_CHROMIUM_PATH")
    if not path or not Path(path).exists():
        pytest.skip("đặt DEMO_CHROMIUM_PATH để chạy test trình duyệt")
    return path


@pytest.fixture(scope="session")
def site_url() -> Iterator[str]:
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(SITE))
    handler.log_message = lambda *a, **k: None  # type: ignore[method-assign]
    srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_address[1]}"
    srv.shutdown()
