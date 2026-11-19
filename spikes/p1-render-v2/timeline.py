"""Tính khung hình: mốc từng câu và từng cảnh theo độ dài voice đo thật (30 fps).

    câu đầu bắt đầu ở lead_s; câu sau bắt đầu sau câu trước gap_s (≤ 0,15 s)
    ranh giới cảnh = giữa khoảng nghỉ trước câu đầu của cảnh sau, làm tròn theo khung hình
    cảnh cuối kết thúc sau câu cuối tail_s

Các cảnh nối khít theo số khung (không hở, không chồng), nên tổng khung = Σ khung từng cảnh.
Hàm thuần: độ dài voice truyền vào, để test không cần ffprobe.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from limits import Limits, load_limits
from plan import PlanError, RenderPlan


def to_frame(seconds: float, fps: int) -> int:
    """Giây → chỉ số khung gần nhất (round-half-up, tránh lệch do số thực)."""
    return int(seconds * fps + 0.5 + 1e-9)


@dataclass(frozen=True)
class TimedSegment:
    segment_id: str
    start_s: float  # tuyệt đối trên video
    duration_s: float

    @property
    def end_s(self) -> float:
        return self.start_s + self.duration_s


@dataclass(frozen=True)
class TimedScene:
    scene_id: str
    start_f: int
    end_f: int  # không gồm khung end_f
    segments: tuple[TimedSegment, ...]
    fps: int

    @property
    def frames(self) -> int:
        return self.end_f - self.start_f

    @property
    def start_s(self) -> float:
        return self.start_f / self.fps

    @property
    def duration_s(self) -> float:
        return self.frames / self.fps


@dataclass(frozen=True)
class Timeline:
    scenes: tuple[TimedScene, ...]
    fps: int

    @property
    def total_frames(self) -> int:
        return self.scenes[-1].end_f

    @property
    def total_s(self) -> float:
        return self.total_frames / self.fps

    @property
    def segments(self) -> tuple[TimedSegment, ...]:
        return tuple(g for s in self.scenes for g in s.segments)

    def max_gap_s(self) -> float:
        """Khoảng nghỉ lớn nhất giữa hai câu liên tiếp."""
        segs = self.segments
        return max((b.start_s - a.end_s for a, b in zip(segs, segs[1:], strict=False)), default=0)


def build_timeline(
    plan: RenderPlan, voice_s: Mapping[str, float], limits: Limits | None = None
) -> Timeline:
    """voice_s: segment_id → độ dài wav (giây). limits: mốc tổng (mặc định config #77)."""
    limits = limits or load_limits()
    fps = plan.fps
    cursor = plan.lead_s
    timed: list[list[TimedSegment]] = []
    for scene in plan.scenes:
        segs = []
        for seg in scene.narration_segments:
            if seg.segment_id not in voice_s:
                raise PlanError(f"thiếu độ dài voice của {seg.segment_id}")
            dur = voice_s[seg.segment_id]
            segs.append(TimedSegment(seg.segment_id, round(cursor, 4), dur))
            cursor += dur + plan.gap_s
        timed.append(segs)

    # Ranh giới cảnh: giữa khoảng nghỉ (câu cuối cảnh trước kết thúc → câu đầu cảnh sau bắt đầu).
    bounds = [0]
    for prev, nxt in zip(timed, timed[1:], strict=False):
        mid = (prev[-1].end_s + nxt[0].start_s) / 2
        bounds.append(to_frame(mid, fps))
    bounds.append(to_frame(timed[-1][-1].end_s + plan.tail_s, fps))

    scenes = tuple(
        TimedScene(s.scene_id, bounds[i], bounds[i + 1], tuple(timed[i]), fps)
        for i, s in enumerate(plan.scenes)
    )
    tl = Timeline(scenes, fps)
    lo, hi = limits.min_total_s, limits.max_total_s
    if not lo <= tl.total_s <= hi:
        raise PlanError(f"tổng {tl.total_s:.2f} s ngoài khoảng {lo:g}–{hi:g} s (config #77)")
    for s in scenes:
        if s.frames <= 0:
            raise PlanError(f"{s.scene_id}: cảnh có 0 khung")
    return tl
