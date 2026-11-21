"""Dựng song song theo cảnh (P1-09): pool, cache, nối, huỷ khi lỗi, và các hàm thuần của driver.

Không cần HyperFrames/FFmpeg: runner giả của `support.py` đóng vai driver (các chế độ
`prepare`/`scene`/`finalize`). Phần chạy thật được đo trong docs/report/render-parallel-2026-11.md.
"""

from __future__ import annotations

import importlib.util
import json
import math
import os
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from tests.produce.support import (
    RUN4_INPUT,
    RUN4_SCRIPT,
    FakeRunner,
    contract_run4,
    make_assets,
    make_cfg,
)
from worker.produce import render
from worker.produce.config import Limits, ProduceConfig
from worker.produce.pipeline import produce
from worker.produce.render import (
    WIDE_LIMITS_ENV,
    effective_jobs,
    order_jobs,
    parts_json,
    render_ratios,
)
from worker.produce.runner import CANCELLED_RC, RunResult, kill_tree, run_process
from worker.produce.timeline import TimedScene, Timeline

DRIVER = Path(render.__file__).parent / "drivers" / "hf_render.py"
RATIOS = ["16:9", "9:16"]
SCENES = ["s01", "s02", "s03"]


@pytest.fixture(autouse=True)
def plenty_of_ram(monkeypatch: pytest.MonkeyPatch) -> None:
    """Số job song song bị cắt theo RAM còn trống; cố định để kết quả không đổi theo máy."""
    monkeypatch.setattr(render, "available_ram_mb", lambda: 64 * 1024)


def load_driver() -> Any:
    spec = importlib.util.spec_from_file_location("hf_render_parallel_under_test", DRIVER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["hf_render_parallel_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def write_plan(tmp: Path, scene_ids: list[str] = SCENES) -> Path:
    plan = tmp / "plans" / "demo-preview.json"
    plan.parent.mkdir(parents=True, exist_ok=True)
    plan.write_text(json.dumps({"scenes": [{"scene_id": s} for s in scene_ids]}), encoding="utf-8")
    return plan


def go(tmp: Path, fake: FakeRunner, **over: Any) -> list[render.RatioRender]:
    cfg = make_cfg(tmp, render_mode="parallel", render_jobs=2, **over)
    return render_ratios(write_plan(tmp), RATIOS, "preview", cfg, tmp / "out", fake)


# ---------------------------------------------------------------- lập lịch (hàm thuần)


def test_longest_scene_runs_first_and_ties_keep_scene_order() -> None:
    scenes = [
        {"scene_id": "s01", "frames": 115},
        {"scene_id": "s02", "frames": 335},
        {"scene_id": "s03", "frames": 115},
    ]
    got = [(t.scene_id, t.ratio) for t in order_jobs(scenes, RATIOS)]
    assert got == [
        ("s02", "16:9"),
        ("s02", "9:16"),
        ("s01", "16:9"),
        ("s01", "9:16"),
        ("s03", "16:9"),
        ("s03", "9:16"),
    ]


def test_effective_jobs_is_capped_by_ram_and_job_count() -> None:
    cfg = make_cfg(Path("."), render_jobs=6, render_job_ram_mb=1500, render_ram_reserve_mb=2000)
    assert effective_jobs(cfg, 14, None) == 6  # không đọc được RAM: giữ nguyên cấu hình
    assert effective_jobs(cfg, 4, None) == 4  # không nhiều hơn số job
    assert effective_jobs(cfg, 14, 2000 + 3 * 1500 + 100) == 3  # RAM chỉ đủ 3 tiến trình
    assert effective_jobs(cfg, 14, 500) == 1  # RAM cạn vẫn chạy được 1 tiến trình


def test_concat_list_follows_scene_order_not_completion_order() -> None:
    scenes = [{"scene_id": s, "frames": 10 * (i + 1)} for i, s in enumerate(SCENES)]
    done = {s: {"output": f"/cache/{s}.mp4"} for s in reversed(SCENES)}  # xong ngược thứ tự
    assert parts_json(scenes, done) == [
        {"scene_id": "s01", "path": "/cache/s01.mp4", "frames": 10},
        {"scene_id": "s02", "path": "/cache/s02.mp4", "frames": 20},
        {"scene_id": "s03", "path": "/cache/s03.mp4", "frames": 30},
    ]


# ---------------------------------------------------------------- pool + nối (runner giả)


def test_parallel_runs_prepare_every_scene_job_then_one_finalize_per_ratio(tmp_path: Path) -> None:
    fake = FakeRunner()
    out = go(tmp_path, fake)

    assert [r.ok for r in out] == [True, True]
    assert len(fake.hf_calls("prepare")) == 1
    scene_calls = fake.hf_calls("scene")
    assert sorted((c["--scene"], c["--ratio"]) for c in scene_calls) == sorted(
        (s, r) for s in SCENES for r in RATIOS
    )
    assert {c["--workers"] for c in scene_calls} == {"1"}  # mỗi tiến trình --workers 1
    assert {c["--quality"] for c in scene_calls} == {"draft"}
    assert len(fake.hf_calls("finalize")) == 2
    assert fake.parts == {"16:9": SCENES, "9:16": SCENES}
    assert fake.envs and all(e == WIDE_LIMITS_ENV for e in fake.envs)  # mốc rộng cho tiến trình con

    blk = out[0].raw["render"]
    assert blk["mode"] == "parallel" and blk["jobs"] == 2 and blk["jobs_requested"] == 2
    assert blk["cache_misses"] == 3 and blk["cache_hits"] == 0
    assert [j["scene_id"] for j in blk["scene_jobs"]] == SCENES
    assert out[0].raw["frames"] == 180  # Σ khung các cảnh (60 × 3)
    assert not (make_cfg(tmp_path).scratch_dir / "render" / "demo-preview").exists()


def test_scene_jobs_are_never_more_than_the_pool_size(tmp_path: Path) -> None:
    fake = FakeRunner()
    active = peak = 0
    lock = threading.Lock()
    original = fake._scene  # noqa: SLF001

    def slow_scene(arg: dict[str, str], cancel: threading.Event | None) -> Any:
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        time.sleep(0.05)
        try:
            return original(arg, cancel)
        finally:
            with lock:
                active -= 1

    fake._scene = slow_scene  # type: ignore[method-assign]  # noqa: SLF001
    go(tmp_path, fake)
    assert peak == 2


def test_second_run_hits_cache_and_editing_one_scene_rebuilds_only_that_scene(
    tmp_path: Path,
) -> None:
    go(tmp_path, FakeRunner())

    again = go(tmp_path, FakeRunner())
    assert all(r.raw["render"]["cache_hits"] == 3 for r in again)

    edited = FakeRunner()
    edited.salt["s02"] = "đã sửa lời"
    rebuilt = go(tmp_path, edited)
    for r in rebuilt:
        jobs = {j["scene_id"]: j["cache_hit"] for j in r.raw["render"]["scene_jobs"]}
        assert jobs == {"s01": True, "s02": False, "s03": True}
        assert r.raw["render"]["cache_misses"] == 1


def test_cache_off_passes_no_cache_dir_and_rebuilds_everything(tmp_path: Path) -> None:
    go(tmp_path, FakeRunner())
    fake = FakeRunner()
    cfg = make_cfg(tmp_path, render_mode="parallel", render_jobs=2)
    out = render_ratios(
        write_plan(tmp_path), RATIOS, "preview", cfg, tmp_path / "out", fake, use_cache=False
    )
    assert all("--cache-dir" not in c for c in fake.hf_calls("scene"))
    assert all(r.raw["render"]["cache"] is False for r in out)
    assert all(r.raw["render"]["cache_hits"] == 0 for r in out)

    off = make_cfg(tmp_path, render_mode="parallel", render_jobs=2, render_cache=False)
    fake2 = FakeRunner()
    render_ratios(write_plan(tmp_path), RATIOS, "preview", off, tmp_path / "out", fake2)
    assert all("--cache-dir" not in c for c in fake2.hf_calls("scene"))  # PRODUCE_RENDER_CACHE=0


def test_a_failing_scene_cancels_the_rest_and_names_the_scene(tmp_path: Path) -> None:
    fake = FakeRunner()
    fake.fail_scene = ("s02", "16:9")
    fake.hold_until_cancel = {("s01", "9:16")}  # đang chạy khi s02 lỗi → phải bị huỷ
    out = go(tmp_path, fake)

    by = {r.ratio: r for r in out}
    assert not by["16:9"].ok and "cảnh s02" in (by["16:9"].error or "")
    assert "Chrome crash ở s02" in (by["16:9"].error or "")
    assert not by["9:16"].ok and "huỷ vì s02" in (by["9:16"].error or "")
    assert fake.hf_calls("finalize") == []  # không nối khi còn cảnh lỗi
    assert fake.cancelled == [("s01", "9:16")]
    started = {(c["--scene"], c["--ratio"]) for c in fake.hf_calls("scene")}
    assert len(started) < len(SCENES) * len(RATIOS)  # job chưa chạy thì không chạy nữa
    assert ("s03", "9:16") not in started


def test_a_timed_out_job_counts_as_failure_and_cancels_the_rest(tmp_path: Path) -> None:
    fake = FakeRunner()
    fake.hold_until_cancel = {("s01", "9:16")}
    original = fake._scene  # noqa: SLF001

    def scene(arg: dict[str, str], cancel: threading.Event | None) -> Any:
        if (arg["--scene"], arg["--ratio"]) == ("s02", "16:9"):
            raise subprocess.TimeoutExpired(["hf_render.py"], 3600)
        return original(arg, cancel)

    fake._scene = scene  # type: ignore[method-assign]  # noqa: SLF001
    by = {r.ratio: r for r in go(tmp_path, fake)}
    assert not by["16:9"].ok and "TimeoutExpired" in (by["16:9"].error or "")
    assert "cảnh s02" in (by["16:9"].error or "")
    assert not by["9:16"].ok and fake.cancelled == [("s01", "9:16")]
    assert fake.hf_calls("finalize") == []


def test_prepare_failure_fails_every_ratio_without_starting_scene_jobs(tmp_path: Path) -> None:
    fake = FakeRunner()
    fake._prepare = lambda arg: RunResult(1, "", "phụ đề quá dài", 0.1)  # type: ignore[method-assign,assignment]  # noqa: SLF001, E501
    out = go(tmp_path, fake)
    assert [r.ok for r in out] == [False, False]
    assert "phụ đề quá dài" in (out[0].error or "")
    assert fake.hf_calls("scene") == []


def test_sequential_mode_is_unchanged(tmp_path: Path) -> None:
    fake = FakeRunner()
    cfg = make_cfg(tmp_path)  # mặc định sequential
    out = render_ratios(write_plan(tmp_path), RATIOS, "preview", cfg, tmp_path / "out", fake)
    assert [r.ok for r in out] == [True, True]
    assert len(fake.hf_calls("full")) == 2 and fake.hf_calls("scene") == []
    assert out[0].raw["render"] == {"mode": "sequential"}


@pytest.mark.skipif(
    not (RUN4_SCRIPT.is_file() and RUN4_INPUT.is_file()), reason="thiếu dữ liệu run4 trong docs/"
)
def test_pipeline_reports_render_block_in_parallel_mode(tmp_path: Path) -> None:
    fake = FakeRunner(mp4_duration_s=42.0, speak_s=3.0)
    res = produce(
        contract_run4(tmp_path / "contract"),
        RUN4_INPUT,
        make_assets(tmp_path),
        tmp_path / "out",
        cfg=make_cfg(tmp_path, render_mode="parallel", render_jobs=3),
        runner=fake,
        limits=Limits(min_total_s=40, max_total_s=45),
    )
    assert res.ok
    for o in res.report["outputs"]:
        assert o["render"]["mode"] == "parallel" and o["render"]["cache_misses"] == 6
    assert len(fake.hf_calls("scene")) == 12 and len(fake.hf_calls("finalize")) == 2


# ---------------------------------------------------------------- driver: các hàm thuần


def scenes_timeline(frames: list[int]) -> Timeline:
    out, cursor = [], 0
    for i, n in enumerate(frames, 1):
        out.append(TimedScene(f"s{i:02d}", cursor, cursor + n, (), 30))
        cursor += n
    return Timeline(tuple(out), 30)


def test_slicing_keeps_every_frame_and_starts_each_scene_at_zero() -> None:
    drv = load_driver()
    tl = scenes_timeline([115, 335, 296, 182, 114, 92, 94])
    subs = [drv.slice_scene(ts, tl, Timeline) for ts in tl.scenes]
    assert [s.scenes[0].start_f for s in subs] == [0] * 7
    assert [s.scenes[0].end_f for s in subs] == [115, 335, 296, 182, 114, 92, 94]
    assert sum(s.scenes[0].end_f for s in subs) == tl.scenes[-1].end_f == 1228
    assert [s.scenes[0].scene_id for s in subs] == [t.scene_id for t in tl.scenes]


def test_moving_a_scene_on_the_timeline_does_not_change_its_slice() -> None:
    drv = load_driver()
    before = scenes_timeline([100, 335, 90])
    after = scenes_timeline([100 + 7, 335, 90])  # cảnh trước dài thêm: s02 dời mốc tuyệt đối
    a = drv.slice_scene(before.scenes[1], before, Timeline)
    b = drv.slice_scene(after.scenes[1], after, Timeline)
    assert before.scenes[1].start_f != after.scenes[1].start_f
    assert a.scenes[0] == b.scenes[0] and a.total_s == b.total_s


@pytest.mark.parametrize("frames", range(1, 700))
def test_slice_duration_never_rounds_up_to_an_extra_frame(frames: int) -> None:
    """`.4f` làm tròn 335/30 lên 11,1667 (= 335,001 khung) → HyperFrames ra 336 khung."""
    drv = load_driver()
    tl = scenes_timeline([frames])
    sub = drv.slice_scene(tl.scenes[0], tl, Timeline)
    for seconds in (sub.scenes[0].duration_s, sub.total_s):
        written = float(f"{seconds:.4f}")
        assert math.ceil(written * 30 - 1e-9) == frames
        assert abs(seconds - frames / 30) < 1e-4 + 1e-9  # lệch < 0,0001 s


def make_work(root: Path, *, css: str = "a{}", media: bytes = b"clip") -> Path:
    (root / "template").mkdir(parents=True)
    (root / "media").mkdir()
    (root / "index.html").write_text("<html>cảnh</html>", encoding="utf-8")
    (root / "template" / "base.css").write_text(css, encoding="utf-8")
    (root / "media" / "s02.mp4").write_bytes(media)
    return root


ENGINE = {"hyperframes": "0.8.173", "chrome": "win64-152"}


def test_cache_key_changes_with_content_quality_ratio_fps_engine(tmp_path: Path) -> None:
    drv = load_driver()
    base, _ = drv.scene_key(make_work(tmp_path / "a"), "16:9", "draft", 30, ENGINE)

    def key(work: Path, ratio: str = "16:9", quality: str = "draft", fps: int = 30, eng=ENGINE):  # noqa: ANN001, ANN202
        return drv.scene_key(work, ratio, quality, fps, eng)[0]

    assert key(make_work(tmp_path / "same")) == base  # cùng nội dung ở thư mục khác
    assert key(make_work(tmp_path / "m", media=b"clip2")) != base  # đổi asset/clip
    assert key(make_work(tmp_path / "c", css="a{b:c}")) != base  # đổi template mà index.html giữ
    assert key(tmp_path / "a", quality="looks") != base
    assert key(tmp_path / "a", ratio="9:16") != base
    assert key(tmp_path / "a", fps=60) != base
    assert key(tmp_path / "a", eng={**ENGINE, "chrome": "win64-153"}) != base


def test_cache_key_ignores_render_output_and_logs(tmp_path: Path) -> None:
    drv = load_driver()
    work = make_work(tmp_path / "w")
    before, _ = drv.scene_key(work, "16:9", "draft", 30, ENGINE)
    (work / "video.mp4").write_bytes(b"x" * 100)
    (work / "hyperframes.log").write_text("log", encoding="utf-8")
    assert drv.scene_key(work, "16:9", "draft", 30, ENGINE)[0] == before


def test_concat_listing_is_absolute_ordered_and_escapes_quotes(tmp_path: Path) -> None:
    drv = load_driver()
    paths = [tmp_path / "s01.mp4", tmp_path / "it's" / "s02.mp4"]
    lines = drv.concat_listing(paths).splitlines()
    assert lines[0] == f"file '{paths[0].resolve().as_posix()}'"
    assert lines[1].startswith("file '") and r"it'\''s" in lines[1]
    assert len(lines) == 2


def test_write_atomic_leaves_no_temp_file(tmp_path: Path) -> None:
    drv = load_driver()
    src = tmp_path / "src.mp4"
    src.write_bytes(b"data")
    dst = tmp_path / "cache" / "16x9" / "k.mp4"
    drv.write_atomic(src, dst)
    assert dst.read_bytes() == b"data"
    assert [p.name for p in dst.parent.iterdir()] == ["k.mp4"]


# ---------------------------------------------------------------- runner: huỷ + giết cả cây


PARENT = """
import subprocess, sys, time
child = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(120)"])
open(sys.argv[1], "w").write(str(child.pid))
time.sleep(120)
"""


def alive(pid: int) -> bool:
    if sys.platform == "win32":
        out = subprocess.run(
            ["tasklist", "/FI", f"PID eq {pid}", "/NH"], capture_output=True, text=True
        ).stdout
        return str(pid) in out
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    try:  # zombie (chờ init gặt, container không có init thật) coi như đã chết
        stat = Path(f"/proc/{pid}/stat").read_text()
    except OSError:
        return True
    return stat.rsplit(")", 1)[-1].split()[0] != "Z"


def wait_for(path: Path, seconds: float = 20) -> int:
    end = time.time() + seconds
    while time.time() < end:
        if path.is_file() and path.read_text().strip():
            return int(path.read_text())
        time.sleep(0.05)
    raise AssertionError("tiến trình con không khởi động")


def test_cancel_kills_the_whole_process_tree(tmp_path: Path) -> None:
    pid_file = tmp_path / "child.pid"
    cancel = threading.Event()
    result: list[Any] = []
    t = threading.Thread(
        target=lambda: result.append(
            run_process([sys.executable, "-c", PARENT, str(pid_file)], cancel=cancel)
        )
    )
    t.start()
    child = wait_for(pid_file)
    assert alive(child)
    t0 = time.time()
    cancel.set()
    t.join(30)
    assert result and result[0].returncode == CANCELLED_RC
    assert time.time() - t0 < 15
    time.sleep(0.5)
    assert not alive(child), "tiến trình cháu (kiểu chrome-headless-shell) bị bỏ sót"


def test_timeout_kills_the_whole_process_tree(tmp_path: Path) -> None:
    pid_file = tmp_path / "child.pid"
    with pytest.raises(subprocess.TimeoutExpired):
        run_process([sys.executable, "-c", PARENT, str(pid_file)], timeout_s=2)
    child = wait_for(pid_file)
    time.sleep(0.5)
    assert not alive(child)


def test_kill_tree_on_finished_process_is_a_noop() -> None:
    proc = subprocess.Popen([sys.executable, "-c", "pass"], text=True)
    proc.wait()
    kill_tree(proc)


def test_locked_prepare_never_lets_two_writers_create_the_same_clip(tmp_path: Path) -> None:
    """Hai job (hai tỉ lệ) cùng cần một clip chưa có: chỉ một bên tạo, bên kia thấy file đủ."""
    drv = load_driver()
    created: list[str] = []
    active = 0
    overlap = 0
    lock = threading.Lock()

    def slow_prepare(
        clip: Any, scene_s: float, speed: float, root: Path, out: Path, fps: int
    ) -> Path:
        nonlocal active, overlap
        target = out / "clip-x.mp4"
        with lock:
            active += 1
            overlap = max(overlap, active)
        try:
            if not target.exists():
                target.write_bytes(b"partial")
                time.sleep(0.2)  # cửa sổ mà bên kia sẽ thấy file dở nếu không có khoá
                target.write_bytes(b"complete")
                created.append(threading.current_thread().name)
            return target
        finally:
            with lock:
                active -= 1

    wrapped = drv.locked(slow_prepare)
    results: list[bytes] = []
    threads = [
        threading.Thread(
            target=lambda: results.append(
                wrapped(None, 1.0, 1.0, tmp_path, tmp_path / "c", 30).read_bytes()
            )
        )
        for _ in range(4)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join(30)
    assert results == [b"complete"] * 4
    assert len(created) == 1 and overlap == 1


def test_killed_lock_holder_does_not_block_later_jobs(tmp_path: Path) -> None:
    """Khoá bằng file `O_EXCL` còn sót khi tiến trình bị giết → job sau chờ mãi. Khoá của hệ
    điều hành tự nhả: giết tiến trình đang giữ khoá, tiến trình khác phải lấy được ngay."""
    drv = load_driver()
    code = "\n".join(
        [
            "import importlib.util, pathlib, sys, time",
            f"spec = importlib.util.spec_from_file_location('d', {str(DRIVER)!r})",
            "m = importlib.util.module_from_spec(spec); sys.modules['d'] = m",
            "spec.loader.exec_module(m)",
            "def slow(*a): print('held', flush=True); time.sleep(120)",
            f"m.locked(slow)(None, 1, 1, None, pathlib.Path({str(tmp_path / 'c')!r}), 30)",
        ]
    )
    # phiên riêng như run_process: kill_tree giết cả nhóm tiến trình, không được trúng pytest
    proc = subprocess.Popen(
        [sys.executable, "-c", code],
        stdout=subprocess.PIPE,
        text=True,
        start_new_session=sys.platform != "win32",
    )
    assert proc.stdout and proc.stdout.readline().strip() == "held"
    kill_tree(proc)
    proc.wait(10)
    start = time.time()
    out = drv.locked(lambda *a: "ok")(None, 1, 1, tmp_path, tmp_path / "c", 30)
    assert out == "ok" and time.time() - start < 5


def test_locked_prepare_recreates_a_partial_clip_left_by_a_killed_run(tmp_path: Path) -> None:
    drv = load_driver()
    out = tmp_path / "c"
    out.mkdir()
    calls: list[str] = []

    def prepare(*a: Any) -> Path:
        target = out / "clip-y.mp4"
        calls.append("prepare")
        if not target.exists():
            target.write_bytes(b"complete")
        return target

    (out / "clip-y.mp4").write_bytes(b"partial")  # file dở từ lần bị giết giữa chừng
    wrapped = drv.locked(prepare, lambda path, scene_s: path.read_bytes() == b"complete")
    assert wrapped(None, 1.0, 1.0, tmp_path, out, 30).read_bytes() == b"complete"
    assert calls == ["prepare", "prepare"]  # lần đầu thấy file dở, xoá, tạo lại


def test_hf_args_env_and_cache_key(tmp_path: Path) -> None:
    py = ProduceConfig.venv_python(tmp_path)
    py.parent.mkdir(parents=True)
    py.touch()
    plain = ProduceConfig(render_v2=tmp_path)
    cfg = ProduceConfig(
        render_v2=tmp_path, hf_args="--experimental-fast-capture", hf_env="A=1, B=2"
    )
    assert "--hf-args" not in render._driver_cmd(plain, plan="p")
    cmd = render._driver_cmd(cfg, plan="p")
    assert cmd[-1] == "--hf-args=--experimental-fast-capture"
    env = render._env(cfg)
    assert env["A"] == "1" and env["B"] == "2" and env["P1_RENDER_MIN_TOTAL_S"] == "1"
    assert render._env(plain) == render.WIDE_LIMITS_ENV

    drv = load_driver()
    work = make_work(tmp_path / "w")
    base = drv.scene_key(work, "16:9", "draft", 30, ENGINE)[0]
    assert drv.scene_key(work, "16:9", "draft", 30, ENGINE, "")[0] == base
    assert drv.scene_key(work, "16:9", "draft", 30, ENGINE, "--browser-gpu")[0] != base


def test_patch_render_cmd_only_touches_the_hyperframes_command() -> None:
    drv = load_driver()
    hf = ["npx", "hyperframes", "render", "-q", "looks", "-w", "1"]
    assert drv.patch_render_cmd(hf, "draft", ["--browser-gpu"]) == [
        "npx", "hyperframes", "render", "-q", "draft", "--browser-gpu", "-w", "1",
    ]  # fmt: skip
    ff = ["ffmpeg", "-i", "a.mp4", "b.mp4"]
    assert drv.patch_render_cmd(ff, "draft", ["--browser-gpu"]) == ff
