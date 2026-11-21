"""Test luôn chạy với mốc mặc định 40–45 s, bất kể biến môi trường của máy dev."""

from __future__ import annotations

import pytest

from config import ENV_MAX, ENV_MIN


@pytest.fixture(autouse=True)
def _default_limits(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv(ENV_MIN, raising=False)
    monkeypatch.delenv(ENV_MAX, raising=False)
