"""PHẦN GỌI SPIKE #88 (HyperFrames + FFmpeg). Chạy bằng venv của spike #88.

    <p1-render-v2>/.venv/Scripts/python.exe hf_render.py --spike <p1-render-v2> \
        --plan <render-plan.json> --ratio 16:9 --quality draft --workers 3 --out <thư mục>

Bốn chế độ (`--mode`), mỗi lần chạy in MỘT dòng JSON ra stdout:
- `full` (mặc định): dựng MỘT tỉ lệ nguyên video bằng một tiến trình HyperFrames (đường cũ,
  `render.mode=sequential`; worker chạy hai tiến trình song song cho hai tỉ lệ).
- `prepare`: kiểm phụ đề, chuẩn bị clip (một lần, tuần tự, tránh hai job cùng ghi một file cache),
  in danh sách cảnh + số khung (`render.mode=parallel`).
- `scene`: dựng MỘT cảnh của MỘT tỉ lệ thành MP4 chỉ hình (plan con, timeline con `start_f = 0`),
  có cache theo nội dung (`--cache-dir`).
- `finalize`: nối MP4 các cảnh (FFmpeg concat) rồi gọi `finalize` + `check_output` của #88 trên
  plan/timeline đầy đủ (phụ đề ASS + voice theo mốc tuyệt đối).

Không sửa spike:
- `--quality draft|looks` đổi cờ `-q` của HyperFrames bằng cách bọc `subprocess.run` trong tiến
  trình (spike #88 cố định `looks`), như `hf_driver.py` của #95.
- Mốc 40–45 s của #77 làm `build_timeline`/`check_output` ném lỗi. Worker đặt
  P1_RENDER_MIN_TOTAL_S/MAX_TOTAL_S rộng cho tiến trình này, rồi tự kiểm mốc thật bằng ffprobe
  (báo, không kéo dài, không cắt).
- Phụ đề: #88 mỗi câu một cue và từ chối câu quá giới hạn dòng. Driver thay `render.build_ass`
  bằng bản chia câu dài thành nhiều cue (`../cues.py`, giới hạn lấy từ `subtitles.LINE_CHARS` và
  `MAX_LINES` của #88), rồi gọi `build_ass` gốc của #88 trên plan/timeline đã chia, nên kiểu ASS
  không bị chép lại.
- Dựng theo cảnh dùng lại `compose` của #88 trên plan con. Hợp lệ vì #88 nối các cảnh khít theo
  số khung và mọi animation tính theo thời gian cục bộ của cảnh (xem report render-parallel).
"""

# pyright: reportMissingImports=false
from __future__ import annotations

import argparse
import dataclasses
import functools
import hashlib
import importlib.util
import json
import math
import os
import shlex
import shutil
import subprocess
import sys
import time
from dataclasses import asdict
from pathlib import Path
from types import SimpleNamespace
from typing import Any

TRANSIENT = {"video.mp4", "hyperframes.log", "subs.ass"}  # không tính vào khoá cache


def _load_cues() -> Any:
    """Nạp `produce/cues.py` (chỉ thư viện chuẩn) theo đường dẫn: venv spike không có `worker`."""
    path = Path(__file__).resolve().parent.parent / "cues.py"
    spec = importlib.util.spec_from_file_location("produce_cues", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["produce_cues"] = mod  # dataclass cần module có trong sys.modules
    spec.loader.exec_module(mod)
    return mod


def split_subtitles(
    plan: Any, tl: Any, ratio: str, subtitles: Any, cues: Any
) -> tuple[Any, Any, dict[str, int]]:
    """Plan + timeline mà mỗi câu quá dài đã được chia thành nhiều cue (id `<segment_id>#<k>`).

    Trả (plan, timeline, {segment_id: số cue} chỉ cho câu bị chia)."""
    limit = subtitles.LINE_CHARS[ratio]
    max_lines = subtitles.MAX_LINES

    def fits(text: str) -> bool:
        return len(subtitles.wrap_caption(subtitles._escape(text), limit)) <= max_lines  # noqa: SLF001

    split: dict[str, int] = {}
    new_scenes = []
    new_tl = []
    for scene, ts in zip(plan.scenes, tl.scenes, strict=True):
        segs, timed = [], []
        for seg, tseg in zip(scene.narration_segments, ts.segments, strict=True):
            texts = cues.split_caption(seg.caption, fits)
            if len(texts) <= 1:
                segs.append(seg)
                timed.append(tseg)
                continue
            split[seg.segment_id] = len(texts)
            for k, cue in enumerate(cues.time_cues(texts, tseg.start_s, tseg.end_s), 1):
                cue_id = f"{seg.segment_id}#{k}"
                segs.append(
                    seg.model_copy(update={"segment_id": cue_id, "subtitle_text": cue.text})
                )
                timed.append(
                    dataclasses.replace(
                        tseg,
                        segment_id=cue_id,
                        start_s=cue.start_s,
                        duration_s=cue.end_s - cue.start_s,
                    )
                )
        new_scenes.append(scene.model_copy(update={"narration_segments": segs}))
        new_tl.append(dataclasses.replace(ts, segments=tuple(timed)))
    return (
        plan.model_copy(update={"scenes": new_scenes}),
        dataclasses.replace(tl, scenes=tuple(new_tl)),
        split,
    )


# ---------------------------------------------------------------- cache theo cảnh


def tree_hash(root: Path) -> str:
    """Hash đường dẫn tương đối + nội dung của mọi file trong thư mục project HyperFrames.

    Gồm `index.html`, `template/` (CSS, JS, layout, font, icon) và `media/`: sửa template mà
    `index.html` không đổi vẫn đổi khoá. Mốc tuyệt đối không có trong đó (cảnh con `start_f = 0`),
    nên dời cảnh trên timeline không đổi khoá."""
    h = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file() and p.name not in TRANSIENT):
        h.update(path.relative_to(root).as_posix().encode())
        h.update(b"\0")
        with path.open("rb") as f:
            for chunk in iter(lambda: f.read(1 << 20), b""):
                h.update(chunk)
        h.update(b"\0")
    return h.hexdigest()


def engine_fingerprint(spike: Path) -> dict[str, str]:
    """Phiên bản HyperFrames (package.json + lockfile) và Chrome đã cài trong cache của nó."""
    out: dict[str, str] = {"platform": sys.platform}
    pkg = spike / "node_modules" / "hyperframes" / "package.json"
    if pkg.is_file():
        out["hyperframes"] = json.loads(pkg.read_text(encoding="utf-8")).get("version", "?")
    lock = spike / "package-lock.json"
    if lock.is_file():
        out["lockfile"] = hashlib.sha256(lock.read_bytes()).hexdigest()[:16]
    chrome = Path.home() / ".cache" / "hyperframes" / "chrome" / "chrome-headless-shell"
    if chrome.is_dir():
        out["chrome"] = ",".join(sorted(p.name for p in chrome.iterdir()))
    return out


def scene_key(
    work: Path, ratio: str, quality: str, fps: int, engine: dict[str, str], hf_args: str = ""
) -> tuple[str, str]:
    """(khoá cache, hash cây thư mục). Khoá đổi khi đổi nội dung, tỉ lệ, chất lượng, fps, engine,
    cờ HyperFrames thêm (rỗng thì khoá giữ nguyên như trước)."""
    tree = tree_hash(work)
    key: dict[str, Any] = {
        "tree": tree, "ratio": ratio, "quality": quality, "fps": fps, "engine": engine,
    }  # fmt: skip
    if hf_args.strip():
        key["hf_args"] = hf_args.split()
    payload = json.dumps(key, sort_keys=True)
    return hashlib.sha256(payload.encode()).hexdigest()[:32], tree


def patch_render_cmd(cmd: list[str], quality: str, extra: list[str]) -> list[str]:
    """Đổi token chất lượng `looks` và chèn cờ thêm ngay sau nó. Chỉ lệnh `hyperframes render`
    có token này nên lệnh ffmpeg/ffprobe không bị đụng tới."""
    if "looks" not in cmd:
        return cmd
    i = cmd.index("looks")
    return [*cmd[:i], quality, *extra, *cmd[i + 1 :]]


def count_packets(mp4: Path, ffprobe: str) -> int:
    """Số khung hình của luồng hình (đọc gói, không giải mã)."""
    proc = subprocess.run(
        [ffprobe, "-v", "error", "-count_packets", "-select_streams", "v:0", "-show_entries",
         "stream=nb_read_packets", "-of", "json", str(mp4)],
        capture_output=True, text=True, check=True,
    )  # fmt: skip
    return int(json.loads(proc.stdout)["streams"][0]["nb_read_packets"])


def write_atomic(src: Path, dst: Path) -> None:
    """Chép src → dst qua file tạm cùng thư mục rồi đổi tên: không ai thấy file dở dang."""
    dst.parent.mkdir(parents=True, exist_ok=True)
    tmp = dst.with_name(f".{dst.name}.tmp-{os.getpid()}")
    shutil.copyfile(src, tmp)
    os.replace(tmp, dst)


def _floor4(x: float) -> float:
    """Làm tròn XUỐNG 4 chữ số thập phân (`compose` của #88 ghi thời lượng bằng `.4f`)."""
    return math.floor(x * 1e4 + 1e-6) / 1e4


def slice_scene(ts: Any, tl: Any, timeline_cls: type) -> Any:
    """Timeline con của MỘT cảnh: `start_f = 0`, giữ nguyên số khung.

    Mọi thứ `compose` của #88 đọc từ timeline đều là thời lượng/mốc của cảnh, nên mốc tuyệt đối
    (cảnh đứng thứ mấy trong video) không lọt vào index.html và không vào khoá cache.

    Thời lượng bị làm tròn XUỐNG 4 chữ số: `N/fps` thường là số thập phân vô hạn (335/30 =
    11,16667), `.4f` làm tròn LÊN thành 11,1667 (= 335,001 khung) và HyperFrames lấy trần ra N+1
    khung. Làm tròn xuống thì không bao giờ vượt N (lệch < 0,0001 s, nhỏ hơn 0,01 khung)."""
    scene_cls, tl_cls = _shaved_types(type(ts), timeline_cls)
    fields = {f.name: getattr(ts, f.name) for f in dataclasses.fields(ts)}
    sub = scene_cls(**{**fields, "start_f": 0, "end_f": ts.end_f - ts.start_f})
    return tl_cls((sub,), tl.fps)


@functools.cache
def _shaved_types(scene_cls: type, timeline_cls: type) -> tuple[type, type]:
    """Lớp con của TimedScene/Timeline (#88) làm tròn thời lượng xuống. Tạo một lần cho mỗi cặp
    lớp, để hai timeline con cùng nội dung so sánh bằng nhau."""

    class Scene(scene_cls):  # type: ignore[misc, valid-type]
        @property
        def duration_s(self) -> float:
            return _floor4((self.end_f - self.start_f) / self.fps)

    class SceneTimeline(timeline_cls):  # type: ignore[misc, valid-type]
        @property
        def total_s(self) -> float:
            return _floor4(self.scenes[-1].end_f / self.fps)

    return Scene, SceneTimeline


def concat_listing(paths: list[Path]) -> str:
    """Nội dung file `-f concat` của FFmpeg: một dòng `file '<đường dẫn tuyệt đối>'` mỗi cảnh."""
    lines = []
    for path in paths:
        quoted = path.resolve().as_posix().replace("'", r"'\''")
        lines.append(f"file '{quoted}'")
    return "\n".join(lines) + "\n"


def _try_lock(f: Any) -> bool:
    """Khoá độc quyền không chờ trên file đã mở. Khoá của hệ điều hành: tiến trình bị giết (huỷ
    pool, quá giờ) thì khoá tự nhả, không để lại khoá mồ côi như khoá bằng file `O_EXCL`."""
    f.seek(0)
    try:
        if sys.platform == "win32":
            import msvcrt

            msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl

            fcntl.flock(f.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        return False
    return True


def _unlock(f: Any) -> None:
    f.seek(0)
    if sys.platform == "win32":
        import msvcrt

        msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
    else:
        import fcntl

        fcntl.flock(f.fileno(), fcntl.LOCK_UN)


def locked(prepare_clip: Any, valid: Any = None) -> Any:
    """Bọc `prepare_clip` của #88 bằng khoá của hệ điều hành trên `<thư mục clip>/.prepare.lock`:
    `prepare_clip` ghi thẳng vào đường dẫn đích và coi file đã có là xong, nên hai tiến trình cùng
    khoá cache sẽ ghi đè nhau hoặc một bên đọc file dở. File đã có thì không tốn gì.

    `valid(path, scene_s) -> bool` (tuỳ chọn): file có sẵn mà hỏng/ngắn (lần trước bị giết giữa
    chừng) thì xoá và tạo lại, thay vì đưa file dở cho HyperFrames ("moov atom not found")."""

    def wrapper(
        clip: Any, scene_s: float, speed: float, root: Path, out_dir: Path, fps: int
    ) -> Path:
        out_dir.mkdir(parents=True, exist_ok=True)
        with (out_dir / ".prepare.lock").open("a+b") as f:
            while not _try_lock(f):
                time.sleep(0.1)
            try:
                path = prepare_clip(clip, scene_s, speed, root, out_dir, fps)
                if valid is not None and not valid(path, scene_s):
                    path.unlink(missing_ok=True)
                    path = prepare_clip(clip, scene_s, speed, root, out_dir, fps)
                return path
            finally:
                _unlock(f)

    return wrapper


def install_clip_guard(ctx: SimpleNamespace) -> None:
    """Thay `prepare_clip` mà `compose` của #88 gọi bằng bản có khoá + kiểm file."""

    def valid(path: Path, scene_s: float) -> bool:
        try:
            return ctx.media.probe_duration(path) >= scene_s - 0.2
        except Exception:  # noqa: BLE001 - ffprobe không đọc được file thì coi như hỏng
            return False

    ctx.compose.prepare_clip = locked(ctx.media.prepare_clip, valid)


class _NoRam:
    """Thay `measure.PeakRam`: mỗi job chạy cạnh các job khác nên số đo theo job sẽ gồm cả Chrome
    của job khác. Worker đo RAM đỉnh một lần quanh cả pool."""

    peak_mb: None = None

    def __enter__(self) -> _NoRam:
        return self

    def __exit__(self, *exc: object) -> None:
        return None


# ---------------------------------------------------------------- nạp spike


def load_context(args: argparse.Namespace) -> SimpleNamespace:
    spike = args.spike.resolve()
    sys.path.insert(0, str(spike))
    import compose as compose_mod
    import media
    import render as render_mod
    import subtitles
    from plan import load_plan
    from timeline import build_timeline

    extra = shlex.split(args.hf_args)
    if args.quality != "looks" or extra:
        real_run = render_mod.subprocess.run

        def run_q(cmd, *a, **kw):  # noqa: ANN001, ANN002, ANN003, ANN202
            return real_run(patch_render_cmd(list(cmd), args.quality, extra), *a, **kw)

        render_mod.subprocess.run = run_q

    cues = _load_cues()
    split_log: dict[str, int] = {}
    original_build_ass = subtitles.build_ass

    def build_ass_split(plan_in: Any, tl_in: Any, ratio: str) -> str:
        plan_s, tl_s, split = split_subtitles(plan_in, tl_in, ratio, subtitles, cues)
        split_log.update(split)
        return original_build_ass(plan_s, tl_s, ratio)

    render_mod.build_ass = build_ass_split  # render.py import tên này trực tiếp

    plan = load_plan(args.plan)
    tl = build_timeline(plan, render_mod.voice_durations(plan))
    return SimpleNamespace(
        spike=spike, compose=compose_mod, media=media, render=render_mod, plan=plan, tl=tl,
        build_ass=build_ass_split, split_log=split_log,
    )  # fmt: skip


# ---------------------------------------------------------------- chế độ


def mode_full(args: argparse.Namespace, ctx: SimpleNamespace) -> dict[str, Any]:
    # #88 chỉ dựng phụ đề ở bước ghép cuối, sau ~4 phút chụp hình. Dựng thử trước để lỗi còn lại
    # (vd. cue vẫn quá giới hạn) hiện sau vài giây. Không bỏ chữ nào.
    ctx.build_ass(ctx.plan, ctx.tl, args.ratio)
    res = ctx.render.render_ratio(
        ctx.plan, args.plan, ctx.tl, args.ratio, args.out, args.workers, "auto", args.tag,
        False, False,
    )  # fmt: skip
    return {**asdict(res), "quality": args.quality, "subtitle_cues": dict(ctx.split_log)}


def mode_prepare(args: argparse.Namespace, ctx: SimpleNamespace) -> dict[str, Any]:
    """Kiểm phụ đề của mọi tỉ lệ, chuẩn bị clip một lần, trả danh sách cảnh."""
    t0 = time.perf_counter()
    for ratio in args.ratios.split(","):
        ctx.build_ass(ctx.plan, ctx.tl, ratio)
    from timeline import Timeline  # của #88 (đã nằm trên sys.path)

    install_clip_guard(ctx)
    scratch = args.out / "prepare"
    # Chuẩn bị clip bằng CHÍNH `compose` của #88 trên plan con, cho từng cảnh và từng tỉ lệ. Khoá
    # cache clip của #88 chứa `clip.model_dump()` (có bản cắt theo tỉ lệ ở spike `claim`),
    # `round(scene_s, 4)` và fps; tự tính lại khoá ở đây từng làm job dựng cảnh tạo thêm clip mới
    # cùng lúc (hai tỉ lệ ghi đè nhau, bị huỷ giữa chừng thì để lại file dở).
    for ratio in args.ratios.split(","):
        for scene, ts in zip(ctx.plan.scenes, ctx.tl.scenes, strict=True):
            if not scene.clip:
                continue
            sub_plan = ctx.plan.model_copy(update={"scenes": [scene]})
            work = scratch / f"{scene.scene_id}-{ratio.replace(':', 'x')}"
            ctx.compose.compose(
                sub_plan, slice_scene(ts, ctx.tl, Timeline), ratio, work, args.clips_dir
            )
            shutil.rmtree(work, ignore_errors=True)
    shutil.rmtree(scratch, ignore_errors=True)
    return {
        "fps": ctx.tl.fps,
        "total_frames": ctx.tl.total_frames,
        "scenes": [{"scene_id": s.scene_id, "frames": s.frames} for s in ctx.tl.scenes],
        "subtitle_cues": dict(ctx.split_log),
        "prepare_s": round(time.perf_counter() - t0, 2),
    }


def mode_scene(args: argparse.Namespace, ctx: SimpleNamespace) -> dict[str, Any]:
    from timeline import Timeline  # của #88 (đã nằm trên sys.path)

    t_all = time.perf_counter()
    ctx.render.PeakRam = _NoRam
    idx = next(i for i, s in enumerate(ctx.plan.scenes) if s.scene_id == args.scene)
    scene, ts = ctx.plan.scenes[idx], ctx.tl.scenes[idx]
    sub_plan = ctx.plan.model_copy(update={"scenes": [scene]})
    sub_tl = slice_scene(ts, ctx.tl, Timeline)
    tag = ctx.render.RATIO_TAG[args.ratio]
    work = args.out / f"{scene.scene_id}-{tag}"
    args.out.mkdir(parents=True, exist_ok=True)

    t0 = time.perf_counter()
    clips = args.clips_dir or ctx.compose.ROOT / ".work" / "clips"
    # `prepare` đã tạo mọi clip; khoá ở đây chỉ để lỡ có clip chưa có thì hai job không cùng ghi.
    install_clip_guard(ctx)
    ctx.compose.compose(sub_plan, sub_tl, args.ratio, work, clips)
    compose_s = time.perf_counter() - t0
    key, tree = scene_key(
        work, args.ratio, args.quality, ctx.plan.fps, engine_fingerprint(ctx.spike), args.hf_args
    )
    ffprobe = ctx.media.tool("ffprobe")
    base: dict[str, Any] = {
        "scene_id": scene.scene_id, "ratio": args.ratio, "key": key, "tree": tree[:16],
        "frames": ts.frames, "compose_s": round(compose_s, 2),
    }  # fmt: skip

    cached = args.cache_dir / tag / f"{key}.mp4" if args.cache_dir else None
    if cached is not None and cached.is_file() and count_packets(cached, ffprobe) == ts.frames:
        shutil.rmtree(work, ignore_errors=True)
        return {**base, "cache_hit": True, "output": str(cached), "hf_wall_s": 0.0,
                "hf_phases": {}, "wall_s": round(time.perf_counter() - t_all, 2)}  # fmt: skip

    video = work / "video.mp4"
    hf_wall, phases, mode, _ = ctx.render.run_hyperframes(
        work, video, ctx.plan.fps, args.workers, "auto"
    )
    got = count_packets(video, ffprobe)
    if got != ts.frames:  # data-duration ghi .4f nên cảnh lệch 1 khung là có thể: báo, không đoán
        raise RuntimeError(
            f"{scene.scene_id}: HyperFrames ra {got} khung, timeline cần {ts.frames}"
        )
    if cached is not None:
        write_atomic(video, cached)
        output = cached
    else:
        output = args.out / f"{scene.scene_id}-{tag}.mp4"
        shutil.copyfile(video, output)
    if not args.keep_work:
        shutil.rmtree(work, ignore_errors=True)
    return {**base, "cache_hit": False, "output": str(output), "hf_wall_s": round(hf_wall, 1),
            "hf_phases": phases, "hf_mode": mode,
            "wall_s": round(time.perf_counter() - t_all, 2)}  # fmt: skip


def concat(
    parts: list[dict[str, Any]], work: Path, out: Path, ctx: SimpleNamespace
) -> dict[str, Any]:
    """FFmpeg concat demuxer theo thứ tự cảnh. Ưu tiên `-c copy`; lệch khung thì encode lại."""
    ffmpeg, ffprobe = ctx.media.tool("ffmpeg"), ctx.media.tool("ffprobe")
    listing = work / "concat.txt"
    lines = []
    for p in parts:
        path = Path(p["path"]).resolve().as_posix().replace("'", "'\\''")
        lines.append(f"file '{path}'")
    listing.write_text("\n".join(lines) + "\n", encoding="utf-8")
    expected = sum(p["frames"] for p in parts)
    base = [ffmpeg, "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", str(listing), "-an"]
    t0 = time.perf_counter()
    ctx.media.run([*base, "-c", "copy", str(out)])
    got = count_packets(out, ffprobe)
    info: dict[str, Any] = {"concat_mode": "copy", "concat_reason": None}
    if got != expected:
        info = {
            "concat_mode": "reencode",
            "concat_reason": f"-c copy ra {got} khung, cần {expected}",
        }
        ctx.media.run([*base, *ctx.render.ENCODE_ARGS, "-r", str(ctx.plan.fps), str(out)])
        got = count_packets(out, ffprobe)
    if got != expected:
        raise RuntimeError(f"nối cảnh ra {got} khung, tổng khung các cảnh là {expected}")
    return {**info, "concat_s": round(time.perf_counter() - t0, 2), "frames": got}


def mode_finalize(args: argparse.Namespace, ctx: SimpleNamespace) -> dict[str, Any]:
    t_all = time.perf_counter()
    ctx.render.PeakRam = _NoRam
    parts = json.loads(args.parts.read_text(encoding="utf-8"))
    ids = [p["scene_id"] for p in parts]
    if ids != [s.scene_id for s in ctx.plan.scenes]:
        raise RuntimeError(f"danh sách cảnh để nối {ids} khác plan")
    tag = ctx.render.RATIO_TAG[args.ratio]
    work = args.parts.parent / f"final-{tag}"  # cạnh file parts, không làm bẩn thư mục ra
    if work.exists():
        shutil.rmtree(work)
    (work / "template").mkdir(parents=True)
    shutil.copytree(ctx.compose.FONTS_DIR, work / "template" / "fonts")  # đường dẫn subs tương đối
    video = work / "video.mp4"
    cat = concat(parts, work, video, ctx)
    suffix = f"-{args.tag}" if args.tag else ""
    out = args.out / f"{args.plan.stem}-{tag}{suffix}.mp4"
    ff_wall, _ = ctx.render.finalize(ctx.plan, ctx.tl, args.ratio, work, video, out)
    ctx.render.check_output(ctx.media.probe_video(out), args.ratio, ctx.tl)
    if not args.keep_work:
        shutil.rmtree(work, ignore_errors=True)
    return {
        "ratio": args.ratio, "output": str(out), "total_s": round(ctx.tl.total_s, 3),
        "ffmpeg_wall_s": round(ff_wall, 1), "workers": "1", "quality": args.quality,
        "subtitle_cues": dict(ctx.split_log), **cat,
        "total_wall_s": round(time.perf_counter() - t_all, 1),
    }  # fmt: skip


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["full", "prepare", "scene", "finalize"], default="full")
    ap.add_argument("--spike", type=Path, required=True)
    ap.add_argument("--plan", type=Path, required=True)
    ap.add_argument("--ratio", choices=["16:9", "9:16"])
    ap.add_argument("--ratios", default="16:9,9:16", help="prepare: các tỉ lệ cần kiểm phụ đề")
    ap.add_argument("--quality", choices=["draft", "looks"], default="looks")
    ap.add_argument("--workers", default="3")
    ap.add_argument("--hf-args", default="", help="cờ thêm cho `hyperframes render`, vd. bench")
    ap.add_argument("--out", type=Path, help="thư mục ra (full, finalize) hoặc thư mục job (scene)")
    ap.add_argument("--tag", default="")
    ap.add_argument("--scene", default="", help="scene: scene_id cần dựng")
    ap.add_argument("--clips-dir", type=Path, help="thư mục clip đã chuẩn bị, dùng chung các job")
    ap.add_argument(
        "--cache-dir", type=Path, help="scene: thư mục cache MP4 cảnh (bỏ = không cache)"
    )
    ap.add_argument(
        "--parts", type=Path, help="finalize: JSON [{scene_id, path, frames}] theo thứ tự"
    )
    ap.add_argument("--keep-work", action="store_true")
    args = ap.parse_args()
    if args.mode != "prepare" and not (args.ratio and args.out):
        ap.error("--ratio và --out là bắt buộc (trừ --mode prepare)")
    if args.mode == "prepare" and not args.clips_dir:
        ap.error("--mode prepare cần --clips-dir")
    if args.mode == "scene" and not args.scene:
        ap.error("--mode scene cần --scene")
    if args.mode == "finalize" and not args.parts:
        ap.error("--mode finalize cần --parts")

    ctx = load_context(args)
    handler = {
        "full": mode_full, "prepare": mode_prepare, "scene": mode_scene, "finalize": mode_finalize,
    }[args.mode]  # fmt: skip
    print(json.dumps(handler(args, ctx), ensure_ascii=False))


if __name__ == "__main__":
    main()
