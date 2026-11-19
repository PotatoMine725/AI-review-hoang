"""Dựng MP4 bằng HyperFrames + FFmpeg của spike #88 (PHẦN GỌI SPIKE, qua `drivers/hf_render.py`).

Hai đường dựng, chọn bằng `cfg.render_mode` (`PRODUCE_RENDER_MODE`, CLI `--render-mode`):

- `sequential` (đường cũ): mỗi tỉ lệ một tiến trình HyperFrames cho cả video, hai tỉ lệ chạy song
  song, mỗi bên `--workers 3` (số đo #95: 146,5 s cho cả hai so với 347 s tuần tự).
- `parallel` (P1-09): chia theo cảnh. Mỗi (cảnh × tỉ lệ) là một job HyperFrames `--workers 1`,
  chạy trong pool `render_jobs` tiến trình (một tiến trình HyperFrames có trần ~5,5-6,6 khung/s,
  nhiều tiến trình tăng tốc được một tỉ lệ tới trần máy ~16-17,5 khung/s). Xong cả cảnh của một
  tỉ lệ thì FFmpeg nối + phụ đề + voice
  (`finalize` của #88 trên plan đầy đủ). MP4 từng cảnh được cache theo nội dung (xem
  `drivers/hf_render.py`), sửa lời một cảnh chỉ dựng lại cảnh đó.

`preview` = `-q draft`, `final` = `-q looks`.

Mốc 40–45 s của #77 làm #88 từ chối video ngắn/dài, nên tiến trình con chạy với mốc rộng; việc kiểm
mốc thật do `check.py` làm bằng ffprobe sau khi dựng (báo, không kéo dài, không cắt).
"""

from __future__ import annotations

import ctypes
import json
import logging
import os
import shutil
import subprocess
import sys
import threading
import time
from collections import deque
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from worker.produce.config import ProduceConfig
from worker.produce.errors import ProduceError
from worker.produce.runner import CANCELLED_RC, Runner, last_json_line

log = logging.getLogger("worker.produce.render")

DRIVER = Path(__file__).resolve().parent / "drivers" / "hf_render.py"
QUALITY = {"preview": "draft", "final": "looks"}
# Mốc rộng chỉ cho tiến trình con của #88; mốc thật kiểm ở check.py.
WIDE_LIMITS_ENV = {"P1_RENDER_MIN_TOTAL_S": "1", "P1_RENDER_MAX_TOTAL_S": "3600"}
RATIO_TAG = {"9:16": "9x16", "16:9": "16x9"}


@dataclass(frozen=True)
class RatioRender:
    ratio: str
    ok: bool
    wall_s: float
    output: Path | None = None
    error: str | None = None
    raw: dict[str, Any] = field(default_factory=dict)


def _env(cfg: ProduceConfig) -> dict[str, str]:
    """Môi trường cho driver: giới hạn tổng thời lượng rộng + biến thêm của HyperFrames."""
    return {**WIDE_LIMITS_ENV, **cfg.hf_env_map}


def _driver_cmd(cfg: ProduceConfig, **opts: object) -> list[str]:
    """`python hf_render.py --spike … --<khoá> <giá trị> …` (khoá có `_` đổi thành `-`)."""
    py = cfg.venv_python(cfg.render_v2)
    if not py.is_file():
        raise ProduceError(f"thiếu venv của spike #88: {py} (đặt PRODUCE_RENDER_V2)")
    cmd = [str(py), str(DRIVER), "--spike", str(cfg.render_v2)]
    for key, value in opts.items():
        if value is None or value is False:
            continue
        flag = "--" + key.replace("_", "-")
        cmd += [flag] if value is True else [flag, str(value)]
    if cfg.hf_args.strip():
        cmd += ["--hf-args", cfg.hf_args]
    return cmd


# ------------------------------------------------------------------ sequential (đường cũ)


def _render_one(
    plan: Path, ratio: str, mode: str, cfg: ProduceConfig, out_dir: Path, runner: Runner
) -> RatioRender:
    cmd = _driver_cmd(
        cfg,
        plan=plan,
        ratio=ratio,
        quality=QUALITY[mode],
        workers=cfg.workers,
        out=out_dir,
    )
    res = runner(cmd, cwd=cfg.render_v2, env=_env(cfg), timeout_s=3600)
    if res.returncode != 0:
        tail = (res.stderr or res.stdout)[-1200:]
        log.error("render %s lỗi: %s", ratio, tail)
        return RatioRender(ratio, False, res.wall_s, error=tail)
    raw = last_json_line(res.stdout)
    raw["render"] = {"mode": "sequential"}
    return RatioRender(ratio, True, res.wall_s, output=Path(raw["output"]), raw=raw)


# ------------------------------------------------------------------ parallel (theo cảnh)


def available_ram_mb() -> int | None:
    """RAM còn trống (MB); None khi không đọc được. Không cần psutil."""
    try:
        if sys.platform == "win32":

            class _Mem(ctypes.Structure):
                _fields_ = [  # noqa: RUF012 - cấu trúc ctypes
                    ("dwLength", ctypes.c_ulong),
                    ("dwMemoryLoad", ctypes.c_ulong),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            mem = _Mem()
            mem.dwLength = ctypes.sizeof(_Mem)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem))  # type: ignore[attr-defined]
            return int(mem.ullAvailPhys // (1024 * 1024))
        pages = os.sysconf("SC_AVPHYS_PAGES")
        return int(pages * os.sysconf("SC_PAGE_SIZE") // (1024 * 1024))
    except (AttributeError, OSError, ValueError):
        return None


def effective_jobs(cfg: ProduceConfig, n_jobs: int, avail_mb: int | None) -> int:
    """Số tiến trình chạy cùng lúc: `render_jobs`, không quá số job, và vừa với RAM còn trống."""
    jobs = min(cfg.render_jobs, n_jobs)
    if avail_mb is not None:
        by_ram = (avail_mb - cfg.render_ram_reserve_mb) // cfg.render_job_ram_mb
        jobs = min(jobs, max(1, int(by_ram)))
    return max(1, jobs)


@dataclass(frozen=True)
class Task:
    kind: str  # "scene" | "final"
    ratio: str
    scene_id: str = ""
    frames: int = 0


@dataclass
class TaskResult:
    task: Task
    ok: bool
    cancelled: bool
    raw: dict[str, Any]
    error: str | None
    wall_s: float


def order_jobs(scenes: list[dict[str, Any]], ratios: list[str]) -> list[Task]:
    """Cảnh dài chạy trước (job dài nhất quyết định thời gian chờ), hoà thì theo thứ tự cảnh."""
    tasks = [Task("scene", r, s["scene_id"], int(s["frames"])) for s in scenes for r in ratios]
    return sorted(tasks, key=lambda t: -t.frames)


def parts_json(scenes: list[dict[str, Any]], done: dict[str, dict[str, Any]]) -> list[dict]:
    """Danh sách MP4 cảnh theo THỨ TỰ CẢNH (không phải thứ tự xong) cho FFmpeg concat."""
    return [
        {"scene_id": s["scene_id"], "path": done[s["scene_id"]]["output"], "frames": s["frames"]}
        for s in scenes
    ]


def _prepare(
    plan: Path, ratios: list[str], mode: str, cfg: ProduceConfig, jobs_dir: Path, runner: Runner
) -> dict[str, Any]:
    cmd = _driver_cmd(
        cfg,
        mode="prepare",
        plan=plan,
        ratios=",".join(ratios),
        quality=QUALITY[mode],
        clips_dir=cfg.scratch_dir / "clips",
        out=jobs_dir,
    )
    res = runner(cmd, cwd=cfg.render_v2, env=_env(cfg), timeout_s=900)
    if res.returncode != 0:
        raise ProduceError((res.stderr or res.stdout)[-1200:])
    return last_json_line(res.stdout)


def render_parallel(
    plan: Path,
    ratios: list[str],
    mode: str,
    cfg: ProduceConfig,
    out_dir: Path,
    runner: Runner,
    *,
    use_cache: bool = True,
) -> list[RatioRender]:
    t_start = time.perf_counter()
    jobs_dir = cfg.scratch_dir / "render" / plan.stem
    jobs_dir.mkdir(parents=True, exist_ok=True)
    try:
        prep = _prepare(plan, ratios, mode, cfg, jobs_dir, runner)
    except ProduceError as ex:
        log.error("chuẩn bị dựng lỗi: %s", ex)
        return [RatioRender(r, False, time.perf_counter() - t_start, error=str(ex)) for r in ratios]
    scenes: list[dict[str, Any]] = prep["scenes"]
    queue: deque[Task] = deque(order_jobs(scenes, ratios))
    n_jobs = effective_jobs(cfg, len(queue), available_ram_mb())
    log.info("dựng song song: %d cảnh × %d tỉ lệ, %d tiến trình", len(scenes), len(ratios), n_jobs)

    cancel = threading.Event()
    cache_dir = cfg.scene_cache_dir if use_cache and cfg.render_cache else None

    def run_task(task: Task) -> TaskResult:
        if cancel.is_set():
            return TaskResult(task, False, True, {}, "huỷ", 0.0)
        if task.kind == "scene":
            cmd = _driver_cmd(
                cfg,
                mode="scene",
                plan=plan,
                ratio=task.ratio,
                scene=task.scene_id,
                quality=QUALITY[mode],
                workers="1",
                out=jobs_dir,
                clips_dir=cfg.scratch_dir / "clips",
                cache_dir=cache_dir,
            )
        else:
            parts_file = jobs_dir / f"parts-{RATIO_TAG[task.ratio]}.json"
            cmd = _driver_cmd(
                cfg,
                mode="finalize",
                plan=plan,
                ratio=task.ratio,
                quality=QUALITY[mode],
                out=out_dir,
                parts=parts_file,
            )
        try:
            res = runner(cmd, cwd=cfg.render_v2, env=_env(cfg), timeout_s=3600, cancel=cancel)
        except (subprocess.TimeoutExpired, OSError) as ex:  # quá giờ cũng là job lỗi: huỷ cả pool
            return TaskResult(task, False, False, {}, f"{type(ex).__name__}: {ex}", 0.0)
        if res.returncode == CANCELLED_RC:
            return TaskResult(task, False, True, {}, "huỷ", res.wall_s)
        if res.returncode != 0:
            return TaskResult(
                task, False, False, {}, (res.stderr or res.stdout)[-1200:], res.wall_s
            )
        try:
            raw = last_json_line(res.stdout)
        except ProduceError as ex:
            return TaskResult(task, False, False, {}, str(ex), res.wall_s)
        return TaskResult(task, True, False, raw, None, res.wall_s)

    done_scenes: dict[str, dict[str, dict[str, Any]]] = {r: {} for r in ratios}
    scene_results: dict[str, list[TaskResult]] = {r: [] for r in ratios}
    scenes_end: dict[str, float] = {}
    finals: dict[str, TaskResult] = {}
    final_end: dict[str, float] = {}
    failure: TaskResult | None = None
    running: dict[Future[TaskResult], Task] = {}

    def _drive(pool: ThreadPoolExecutor) -> None:
        nonlocal failure
        while queue or running:
            while queue and len(running) < n_jobs and not cancel.is_set():
                task = queue.popleft()
                running[pool.submit(run_task, task)] = task
            if not running:
                break
            finished, _ = wait(running, return_when=FIRST_COMPLETED)
            for fut in finished:
                task = running.pop(fut)
                res = fut.result()
                if res.cancelled:
                    continue
                if not res.ok:
                    if failure is None:
                        failure = res
                        log.error(
                            "dựng %s tỉ lệ %s lỗi, huỷ các job còn lại: %s",
                            task.scene_id or "nối/finalize",
                            task.ratio,
                            res.error,
                        )
                        cancel.set()
                    continue
                if task.kind == "final":
                    finals[task.ratio] = res
                    final_end[task.ratio] = time.perf_counter() - t_start
                    continue
                done_scenes[task.ratio][task.scene_id] = res.raw
                scene_results[task.ratio].append(res)
                if len(done_scenes[task.ratio]) == len(scenes) and failure is None:
                    scenes_end[task.ratio] = time.perf_counter() - t_start
                    (jobs_dir / f"parts-{RATIO_TAG[task.ratio]}.json").write_text(
                        json.dumps(parts_json(scenes, done_scenes[task.ratio]), ensure_ascii=False),
                        encoding="utf-8",
                    )
                    queue.appendleft(
                        Task("final", task.ratio)
                    )  # xong thì ghép ngay, trước job khác

    with ThreadPoolExecutor(max_workers=n_jobs) as pool:
        try:
            _drive(pool)
        except BaseException:  # Ctrl+C, lỗi lập trình: đừng để tiến trình HyperFrames chạy mồ côi
            cancel.set()
            raise

    out: list[RatioRender] = []
    for ratio in ratios:
        fin = finals.get(ratio)
        if fin is not None:
            raw = dict(fin.raw)
            sj = [
                {
                    "scene_id": r.raw["scene_id"],
                    "frames": r.raw["frames"],
                    "cache_hit": r.raw["cache_hit"],
                    "wall_s": r.raw["wall_s"],
                    "hf_wall_s": r.raw["hf_wall_s"],
                    "compose_s": r.raw["compose_s"],
                    "key": r.raw["key"],
                }
                for r in sorted(scene_results[ratio], key=lambda x: x.raw["scene_id"])
            ]
            hits = sum(1 for s in sj if s["cache_hit"])
            raw["render"] = {
                "mode": "parallel",
                "jobs": n_jobs,
                "jobs_requested": cfg.render_jobs,
                "cache": cache_dir is not None,
                "cache_hits": hits,
                "cache_misses": len(sj) - hits,
                "prepare_s": prep.get("prepare_s"),
                "scenes_phase_s": round(scenes_end[ratio], 1),
                "scene_jobs": sj,
            }
            raw["compose_s"] = round(sum(s["compose_s"] for s in sj), 1)
            raw["hf_wall_s"] = round(scenes_end[ratio], 1)
            raw["hf_phases"] = {}
            raw["subtitle_cues"] = prep.get("subtitle_cues") or raw.get("subtitle_cues") or {}
            out.append(
                RatioRender(ratio, True, final_end[ratio], output=Path(raw["output"]), raw=raw)
            )
            continue
        if failure is not None and failure.task.ratio == ratio:
            where = (
                f"cảnh {failure.task.scene_id}" if failure.task.kind == "scene" else "nối/finalize"
            )
            err = f"{where} ({ratio}) lỗi: {failure.error}"
        elif failure is not None:
            who = failure.task.scene_id or "nối/finalize"
            err = f"huỷ vì {who} ({failure.task.ratio}) lỗi"
        else:
            err = "không dựng xong (job bị huỷ)"
        out.append(RatioRender(ratio, False, time.perf_counter() - t_start, error=err))
    shutil.rmtree(jobs_dir, ignore_errors=True)
    return out


# ------------------------------------------------------------------ điểm vào


def render_ratios(
    plan: Path,
    ratios: list[str],
    mode: str,
    cfg: ProduceConfig,
    out_dir: Path,
    runner: Runner,
    *,
    render_mode: str | None = None,
    use_cache: bool = True,
) -> list[RatioRender]:
    if mode not in QUALITY:
        raise ProduceError(f"mode phải là preview hoặc final, nhận {mode!r}")
    out_dir.mkdir(parents=True, exist_ok=True)
    if (render_mode or cfg.render_mode) == "parallel":
        return render_parallel(plan, ratios, mode, cfg, out_dir, runner, use_cache=use_cache)
    with ThreadPoolExecutor(max_workers=len(ratios)) as pool:
        futures = [pool.submit(_render_one, plan, r, mode, cfg, out_dir, runner) for r in ratios]
        return [f.result() for f in futures]
