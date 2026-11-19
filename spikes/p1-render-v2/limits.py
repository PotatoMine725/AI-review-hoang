"""Mốc thời lượng video: đọc CHUNG cấu hình của renderer #77 (`spikes/p1-render/config.py`).

Không chép số 40–45 s sang đây. Nạp thẳng file config của #77 bằng importlib (đặt tên module
riêng để không trùng với module nào của spike này), nên hai renderer luôn cùng một mốc và cùng
biến môi trường `P1_RENDER_MIN_TOTAL_S` / `P1_RENDER_MAX_TOTAL_S`.
Đổi lại: spike v2 phụ thuộc đường dẫn ../p1-render (cùng branch, #77 merge trước).
"""

from __future__ import annotations

import importlib.util
import sys
from collections.abc import Mapping
from pathlib import Path
from types import ModuleType
from typing import Protocol, cast

CONFIG_PATH = Path(__file__).resolve().parent.parent / "p1-render" / "config.py"
_MODULE = "p1_render_config"


class Limits(Protocol):
    min_total_s: float
    max_total_s: float


def _config() -> ModuleType:
    if _MODULE in sys.modules:
        return sys.modules[_MODULE]
    if not CONFIG_PATH.exists():
        raise FileNotFoundError(f"thiếu config chung của #77: {CONFIG_PATH}")
    spec = importlib.util.spec_from_file_location(_MODULE, CONFIG_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[_MODULE] = mod  # dataclass cần module có trong sys.modules
    spec.loader.exec_module(mod)
    return mod


def load_limits(environ: Mapping[str, str] | None = None) -> Limits:
    """Mốc min/max tổng thời lượng (giây), đọc lại môi trường mỗi lần gọi."""
    return cast(Limits, _config().load_limits(environ))
