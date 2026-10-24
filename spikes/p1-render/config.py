"""Mốc thời lượng video: MỘT chỗ duy nhất (lead đổi P1 sang 40–45 s mỗi MP4, 19/10, #80).

Cả bước kiểm plan (`timeline.build_timeline`) lẫn bước kiểm MP4 cuối (`renderer.check_output`)
đọc cùng một `RenderLimits`. Mặc định 40–45 s; đổi bằng biến môi trường, không sửa code:

    P1_RENDER_MIN_TOTAL_S=40  P1_RENDER_MAX_TOTAL_S=45

Renderer v2 (#80) phải đọc chung cấu hình này, không đặt khoảng riêng. Số cảnh KHÔNG bị chặn ở
đây: chỉ chặn theo tổng thời lượng (xem `render_plan.RenderPlan.scenes`).
"""

from __future__ import annotations

import math
import os
from collections.abc import Mapping
from dataclasses import dataclass

ENV_MIN = "P1_RENDER_MIN_TOTAL_S"
ENV_MAX = "P1_RENDER_MAX_TOTAL_S"
DEFAULT_MIN_TOTAL_S = 40.0
DEFAULT_MAX_TOTAL_S = 45.0


class ConfigError(ValueError):
    """Cấu hình sai (vd. biến môi trường không phải số, min > max)."""


@dataclass(frozen=True)
class RenderLimits:
    min_total_s: float = DEFAULT_MIN_TOTAL_S
    max_total_s: float = DEFAULT_MAX_TOTAL_S

    def __post_init__(self) -> None:
        finite = math.isfinite(self.min_total_s) and math.isfinite(self.max_total_s)
        if not (finite and 0 < self.min_total_s <= self.max_total_s):
            raise ConfigError(
                f"mốc thời lượng sai: cần 0 < min ≤ max, nhận min={self.min_total_s:g} s, "
                f"max={self.max_total_s:g} s"
            )


def _read(environ: Mapping[str, str], name: str, default: float) -> float:
    raw = environ.get(name, "").strip()
    if not raw:
        return default
    try:
        return float(raw)
    except ValueError:
        raise ConfigError(f"{name}={raw!r} không phải số (giây)") from None


def load_limits(environ: Mapping[str, str] | None = None) -> RenderLimits:
    """Đọc mốc từ biến môi trường tại thời điểm gọi (không cache), mặc định 40–45 s."""
    env = os.environ if environ is None else environ
    return RenderLimits(
        min_total_s=_read(env, ENV_MIN, DEFAULT_MIN_TOTAL_S),
        max_total_s=_read(env, ENV_MAX, DEFAULT_MAX_TOTAL_S),
    )
