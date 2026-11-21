"""Timeline từ audio đo thật và kiểm thời lượng MP4 (không cần mạng/GPU)."""

from __future__ import annotations

import pytest

from tests.produce.support import FakeRunner, make_cfg
from worker.produce import check
from worker.produce.config import Limits, ProduceConfig
from worker.produce.timeline import build_timeline, to_frame

KW = {"fps": 30, "lead_s": 0.1, "gap_s": 0.12, "tail_s": 0.6}
LIMITS = Limits(min_total_s=40, max_total_s=45)


def test_to_frame_rounds_half_up() -> None:
    assert to_frame(2.5 / 30, 30) == 3  # 2,5 khung → 3, không rơi về 2 do lỗi số thực
    assert to_frame(1.0, 30) == 30


def test_timeline_matches_hand_calculation() -> None:
    tl = build_timeline([("s1", [("a", 2.0)]), ("s2", [("b", 3.0), ("c", 1.0)])], **KW)
    s1, s2 = tl.scenes
    # a: 0,10–2,10; b: 2,22–5,22; c: 5,34–6,34
    assert [g.start_s for g in s2.segments] == [2.22, 5.34]
    # ranh giới cảnh = giữa khoảng nghỉ (2,10 + 2,22)/2 = 2,16 s → khung 65
    assert (s1.start_f, s1.end_f, s2.end_f) == (0, 65, 208)  # 6,34 + 0,6 = 6,94 s → 208 khung
    assert tl.total_s == pytest.approx(208 / 30)
    assert s1.duration_s + s2.duration_s == pytest.approx(tl.total_s)  # nối khít, không hở/chồng


def test_gap_counted_once_between_sentences() -> None:
    one = build_timeline([("s1", [("a", 2.0), ("b", 2.0)])], **KW)
    gap = one.scenes[0].segments[1].start_s - one.scenes[0].segments[0].end_s
    assert gap == pytest.approx(0.12)


def test_timeline_rejects_empty_scene() -> None:
    with pytest.raises(ValueError, match="câu thoại"):
        build_timeline([("s1", [])], **KW)


@pytest.mark.parametrize(
    ("actual", "verdict"),
    [(39.99, "too_short"), (40.0, "ok"), (45.0, "ok"), (45.01, "too_long"), (18.9, "too_short")],
)
def test_check_duration_only_reports(actual: float, verdict: str) -> None:
    assert check.check_duration(actual, LIMITS) == verdict


def test_probe_parses_ffprobe_json(tmp_path) -> None:  # noqa: ANN001
    cfg = make_cfg(tmp_path)
    info = check.probe(tmp_path / "x.mp4", cfg, FakeRunner(mp4_duration_s=19.4))
    assert (info.duration_s, info.width, info.height) == (19.4, 1920, 1080)


def test_gap_above_limit_is_rejected(tmp_path) -> None:  # noqa: ANN001
    with pytest.raises(ValueError, match="gap_s"):
        ProduceConfig(gap_s=0.2)
