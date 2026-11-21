"""Timeline từ độ dài audio đo thật. Hàm thuần, cùng công thức `timeline.py` của #88.

    câu đầu bắt đầu ở lead_s; câu sau bắt đầu sau câu trước gap_s
    ranh giới cảnh = giữa khoảng nghỉ trước câu đầu của cảnh sau, làm tròn theo khung hình
    cảnh cuối kết thúc sau câu cuối tail_s

Khoảng nghỉ và chuyển cảnh chỉ tính ở đây một lần. Worker truyền `lead_s/gap_s/tail_s` vào plan
để #88 tính lại ra cùng kết quả; sau khi dựng, tổng dự kiến được so với ffprobe (xem `check.py`).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass


def to_frame(seconds: float, fps: int) -> int:
    """Giây → chỉ số khung gần nhất (round-half-up, tránh lệch do số thực)."""
    return int(seconds * fps + 0.5 + 1e-9)


@dataclass(frozen=True)
class TimedSegment:
    segment_id: str
    start_s: float
    duration_s: float

    @property
    def end_s(self) -> float:
        return self.start_s + self.duration_s


@dataclass(frozen=True)
class TimedScene:
    scene_id: str
    start_f: int
    end_f: int
    segments: tuple[TimedSegment, ...]
    fps: int

    @property
    def duration_s(self) -> float:
        return (self.end_f - self.start_f) / self.fps


@dataclass(frozen=True)
class Timeline:
    scenes: tuple[TimedScene, ...]
    fps: int

    @property
    def total_s(self) -> float:
        return self.scenes[-1].end_f / self.fps

    def scene(self, scene_id: str) -> TimedScene:
        return next(s for s in self.scenes if s.scene_id == scene_id)


def build_timeline(
    scenes: Sequence[tuple[str, Sequence[tuple[str, float]]]],
    *,
    fps: int,
    lead_s: float,
    gap_s: float,
    tail_s: float,
) -> Timeline:
    """scenes: [(scene_id, [(segment_id, duration_s), ...]), ...] theo thứ tự phát."""
    if not scenes or any(not segs for _, segs in scenes):
        raise ValueError("mỗi cảnh cần ít nhất một câu thoại")
    cursor = lead_s
    timed: list[list[TimedSegment]] = []
    for _, segs in scenes:
        row: list[TimedSegment] = []
        for seg_id, dur in segs:
            row.append(TimedSegment(seg_id, round(cursor, 4), dur))
            cursor += dur + gap_s
        timed.append(row)

    bounds = [0]
    for prev, nxt in zip(timed, timed[1:], strict=False):
        bounds.append(to_frame((prev[-1].end_s + nxt[0].start_s) / 2, fps))
    bounds.append(to_frame(timed[-1][-1].end_s + tail_s, fps))

    out = tuple(
        TimedScene(sid, bounds[i], bounds[i + 1], tuple(timed[i]), fps)
        for i, (sid, _) in enumerate(scenes)
    )
    if any(s.end_f <= s.start_f for s in out):
        bad = next(s.scene_id for s in out if s.end_f <= s.start_f)
        raise ValueError(f"{bad}: cảnh có 0 khung")
    return Timeline(out, fps)
