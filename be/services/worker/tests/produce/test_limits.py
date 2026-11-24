"""Mốc thời lượng của worker mặc định 30–40 s, vẫn đè được bằng biến môi trường của #77."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.produce.support import make_cfg
from worker.produce.config import ProduceConfig, load_limits

SPIKE = Path(__file__).resolve().parents[4] / "spikes" / "p1-render"


def _cfg(tmp_path: Path) -> ProduceConfig:
    return make_cfg(tmp_path).model_copy(update={"render_ff": SPIKE})


def test_default_limits_are_30_to_40(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    for k in ("P1_RENDER_MIN_TOTAL_S", "P1_RENDER_MAX_TOTAL_S"):
        monkeypatch.delenv(k, raising=False)
    lim = load_limits(_cfg(tmp_path))
    assert (lim.min_total_s, lim.max_total_s) == (30.0, 40.0)


def test_env_still_overrides(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("P1_RENDER_MIN_TOTAL_S", "40")
    monkeypatch.setenv("P1_RENDER_MAX_TOTAL_S", "45")
    lim = load_limits(_cfg(tmp_path))
    assert (lim.min_total_s, lim.max_total_s) == (40.0, 45.0)


def test_blank_env_keeps_worker_defaults(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("P1_RENDER_MIN_TOTAL_S", "")
    monkeypatch.setenv("P1_RENDER_MAX_TOTAL_S", "  ")
    lim = load_limits(_cfg(tmp_path))
    assert (lim.min_total_s, lim.max_total_s) == (30.0, 40.0)
