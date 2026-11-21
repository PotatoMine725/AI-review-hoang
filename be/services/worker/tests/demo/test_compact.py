"""Tự cắt đoạn chờ của clip quay tự động (không cần trình duyệt)."""

from __future__ import annotations

from worker.demo.encode import IDLE_HEAD_S, IDLE_TAIL_S, build_asset, compact_spans
from worker.demo.recorder import ReplayResult
from worker.demo.schema import ActionScript

URL = "https://example.com/tool"


def script(*steps: dict) -> ActionScript:
    return ActionScript.model_validate(
        {"asset_id": "demo-x", "url": URL, "steps": [{"op": "goto", "url": URL}, *steps]}
    )


def test_long_waits_are_cut_and_actions_kept() -> None:
    s = script(
        {"op": "click", "selector": "#a"},
        {"op": "wait", "ms": 10_000},
        {"op": "click", "selector": "#b"},
    )
    # goto xong 4,0; click 4,0→6,0; chờ 6,0→16,0; click 16,0→18,0; giữ cuối tới 21,0
    r = ReplayResult(start_s=3.5, end_s=21.0, step_times_s=[4.0, 6.0, 16.0, 18.0])
    spans = compact_spans(s, r, duration_s=21.0)
    assert spans[0] == (3.5, 6.0 + IDLE_HEAD_S)  # nối liền: trang tải + click + đầu đoạn chờ
    assert spans[1] == (16.0 - IDLE_TAIL_S, 19.8)  # cuối đoạn chờ + click + giữ cuối 1,8 s
    total = sum(b - a for a, b in spans)
    assert 6.0 < total < 9.0  # thay vì 17,5 s


def test_short_waits_stay_whole() -> None:
    s = script({"op": "wait", "ms": 800}, {"op": "click", "selector": "#a"})
    r = ReplayResult(start_s=1.0, end_s=4.0, step_times_s=[1.2, 2.0, 3.0])
    assert compact_spans(s, r, duration_s=4.0) == [(1.0, 4.0)]


def test_missing_step_times_falls_back_to_one_span() -> None:
    s = script({"op": "click", "selector": "#a"})
    r = ReplayResult(start_s=2.0, end_s=9.0)
    assert compact_spans(s, r, duration_s=8.5) == [(2.0, 8.5)]


def test_asset_keeps_end_and_uses_all_spans() -> None:
    s = script({"op": "wait_for", "selector": "#done", "timeout_ms": 60_000})
    r = ReplayResult(start_s=1.0, end_s=33.0, step_times_s=[1.0, 30.0])
    a = build_asset(s, r, 33.0, "clips/x.mp4")
    assert a.anchor == "end" and len(a.parts) == 2
    assert a.parts[-1].end_s == 31.8  # giữ cuối 1,8 s sau bước cuối
