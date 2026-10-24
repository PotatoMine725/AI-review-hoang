"""Tính mốc thời gian của từng cảnh từ plan + preset + độ dài voice.

Thời lượng cảnh = max(min_duration_s, lead + độ dài voice + tail), làm tròn lên theo khung hình.
`lead` = thời gian chuyển cảnh đi vào (voice bắt đầu sau khi cảnh đã hiện rõ), `tail` = đệm cuối.
Hai cảnh liền kề chồng nhau `transition_s` (xfade), nên:
    tổng = Σ thời lượng cảnh − (số cảnh − 1) × transition_s
Tổng phải nằm trong khoảng của `config.RenderLimits` (mặc định 40–45 s), nếu không báo lỗi trước
khi chạy ffmpeg. Đây là chỗ DUY NHẤT chặn theo độ dài; số cảnh (1–12) không bị chặn theo độ dài.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from config import RenderLimits, load_limits
from media import probe_duration
from presets import FPS, Preset
from render_plan import PlanError, RenderPlan, Scene

FIRST_LEAD_S = 0.1  # cảnh đầu không có chuyển cảnh đi vào; chừa chút trước khi nói
# Mọi thời lượng là bội của 1/30 s nên sai số cộng dồn chỉ cỡ 1e-13: so với mốc kèm sai số này,
# để plan đúng 40,000 s / 45,000 s không bị loại oan vì làm tròn số thực.
BOUND_EPS_S = 1e-6


def _frames(seconds: float) -> int:
    return math.ceil(round(seconds * FPS, 6))


def quantize(seconds: float) -> float:
    """Làm tròn lên theo khung hình 30 fps, để các cảnh nối khít, không lệch khung."""
    return _frames(seconds) / FPS


@dataclass(frozen=True)
class TimedScene:
    scene: Scene
    index: int
    start_s: float  # thời điểm cảnh bắt đầu trên timeline cuối
    duration_s: float
    voice_start_s: float  # tuyệt đối trên timeline cuối
    voice_s: float  # 0 nếu cảnh im lặng

    @property
    def frames(self) -> int:
        return round(self.duration_s * FPS)

    @property
    def end_s(self) -> float:
        return self.start_s + self.duration_s


@dataclass(frozen=True)
class Timeline:
    scenes: tuple[TimedScene, ...]
    transition_s: float
    total_s: float


def build_timeline(
    plan: RenderPlan,
    preset: Preset,
    duration_of: Callable[[Path], float] = probe_duration,
    limits: RenderLimits | None = None,
) -> Timeline:
    """Dựng timeline và kiểm tra tổng thời lượng theo `limits` (mặc định: `load_limits()`).
    `duration_of` thay được khi test."""
    limits = limits or load_limits()
    x = 0.0 if preset.transition == "cut" else quantize(preset.transition_s)
    tail = quantize(preset.tail_s)
    timed: list[TimedScene] = []
    start = 0.0
    for i, scene in enumerate(plan.scenes):
        voice_s = duration_of(Path(scene.voice)) if scene.voice else 0.0
        lead = FIRST_LEAD_S if i == 0 else x
        raw = lead + voice_s + tail if voice_s else 0.0
        # Mỗi cảnh phải dài hơn 2 lần chuyển cảnh, nếu không xfade chồng cả vào cảnh kế.
        duration = quantize(max(scene.min_duration_s, raw, 2 * x + 1 / FPS))
        timed.append(
            TimedScene(
                scene=scene,
                index=i,
                start_s=start,
                duration_s=duration,
                voice_start_s=start + lead,
                voice_s=voice_s,
            )
        )
        start += duration - x
    total = timed[-1].end_s
    if total < limits.min_total_s - BOUND_EPS_S:
        raise PlanError(
            f"tổng thời lượng {total:.2f} s ngắn hơn mức tối thiểu {limits.min_total_s:g} s "
            f"(preset {preset.id}, {len(plan.scenes)} cảnh). Thêm câu thoại/cảnh hoặc tăng "
            "min_duration_s."
        )
    if total > limits.max_total_s + BOUND_EPS_S:
        raise PlanError(
            f"tổng thời lượng {total:.2f} s vượt mức tối đa {limits.max_total_s:g} s "
            f"(preset {preset.id}, {len(plan.scenes)} cảnh). Rút ngắn voice hoặc bớt cảnh."
        )
    return Timeline(scenes=tuple(timed), transition_s=x, total_s=total)
