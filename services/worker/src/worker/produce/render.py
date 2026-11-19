"""Dựng MP4 bằng HyperFrames + FFmpeg của spike #88 (PHẦN GỌI SPIKE, qua `drivers/hf_render.py`).

Hai tỉ lệ chạy **song song** (hai tiến trình), mỗi bên `--workers 3` (số đo #95: 146,5 s cho cả hai
so với 347 s tuần tự). `preview` = `-q draft`, `final` = `-q looks`. FFmpeg ghép voice + phụ đề nằm
trong `render_ratio` của #88.

Mốc 40–45 s của #77 làm #88 từ chối video ngắn/dài, nên tiến trình con chạy với mốc rộng; việc kiểm
mốc thật do `check.py` làm bằng ffprobe sau khi dựng (báo, không kéo dài, không cắt).
"""

from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from worker.produce.config import ProduceConfig
from worker.produce.errors import ProduceError
from worker.produce.runner import Runner, last_json_line

log = logging.getLogger("worker.produce.render")

DRIVER = Path(__file__).resolve().parent / "drivers" / "hf_render.py"
QUALITY = {"preview": "draft", "final": "looks"}
# Mốc rộng chỉ cho tiến trình con của #88; mốc thật kiểm ở check.py.
WIDE_LIMITS_ENV = {"P1_RENDER_MIN_TOTAL_S": "1", "P1_RENDER_MAX_TOTAL_S": "3600"}


@dataclass(frozen=True)
class RatioRender:
    ratio: str
    ok: bool
    wall_s: float
    output: Path | None = None
    error: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


def _render_one(
    plan: Path, ratio: str, mode: str, cfg: ProduceConfig, out_dir: Path, runner: Runner
) -> RatioRender:
    py = cfg.venv_python(cfg.render_v2)
    if not py.is_file():
        raise ProduceError(f"thiếu venv của spike #88: {py} (đặt PRODUCE_RENDER_V2)")
    cmd = [
        str(py),
        str(DRIVER),
        "--spike",
        str(cfg.render_v2),
        "--plan",
        str(plan),
        "--ratio",
        ratio,
        "--quality",
        QUALITY[mode],
        "--workers",
        cfg.workers,
        "--out",
        str(out_dir),
    ]
    res = runner(cmd, cwd=cfg.render_v2, env=WIDE_LIMITS_ENV, timeout_s=3600)
    if res.returncode != 0:
        tail = (res.stderr or res.stdout)[-1200:]
        log.error("render %s lỗi: %s", ratio, tail)
        return RatioRender(ratio, False, res.wall_s, error=tail)
    raw = last_json_line(res.stdout)
    return RatioRender(ratio, True, res.wall_s, output=Path(raw["output"]), raw=raw)


def render_ratios(
    plan: Path, ratios: list[str], mode: str, cfg: ProduceConfig, out_dir: Path, runner: Runner
) -> list[RatioRender]:
    if mode not in QUALITY:
        raise ProduceError(f"mode phải là preview hoặc final, nhận {mode!r}")
    out_dir.mkdir(parents=True, exist_ok=True)
    with ThreadPoolExecutor(max_workers=len(ratios)) as pool:
        futures = [pool.submit(_render_one, plan, r, mode, cfg, out_dir, runner) for r in ratios]
        return [f.result() for f in futures]
