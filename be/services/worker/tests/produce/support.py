"""Đồ dùng chung cho test `worker.produce`: cấu hình tạm, runner giả, dữ liệu run4 thật."""

from __future__ import annotations

import json
import os
import threading
import wave
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from worker.produce.config import ProduceConfig
from worker.produce.runner import CANCELLED_RC, RunResult

REPO = Path(__file__).resolve().parents[4]
RUN4_DIR = REPO / "docs" / "report" / "m2-first-run-pdfcraft"
RUN4_SCRIPT = RUN4_DIR / "run4-2026-10-30" / "script.json"
RUN4_INPUT = RUN4_DIR / "input.json"


def make_cfg(tmp: Path, **over: Any) -> ProduceConfig:
    """Cấu hình trỏ vào thư mục tạm, kèm 'venv' giả để qua bước kiểm file tồn tại."""
    tts, render = tmp / "tts-spike", tmp / "render-spike"
    for root in (tts / "vieneu", render):
        py = ProduceConfig.venv_python(root)
        py.parent.mkdir(parents=True, exist_ok=True)
        py.write_text("", encoding="utf-8")
    return ProduceConfig(
        tts_spike=tts,
        render_v2=render,
        render_ff=tmp / "ff",
        cache_dir=tmp / "cache",
        scratch_dir=tmp / "scratch",
        **over,
    )


def load_spike_subtitles() -> Any:
    """`subtitles.py` thật của #88 (giới hạn dòng × ký tự). Bỏ qua test nếu máy không có spike.

    Module spike có tên chung (`plan`, `timeline`, `limits`): nạp xong thì gỡ khỏi sys.modules."""
    import importlib
    import sys

    import pytest

    root = Path(
        os.environ.get("PRODUCE_RENDER_V2")
        or os.environ.get("P1_RENDER_V2")
        or str(ProduceConfig.model_fields["render_v2"].default)
    )
    if not (root / "subtitles.py").is_file():
        pytest.skip("không có spike #88 trên máy này")
    names = ("subtitles", "plan", "timeline", "limits")
    saved = {n: sys.modules.pop(n) for n in names if n in sys.modules}
    sys.path.insert(0, str(root))
    try:
        return importlib.import_module("subtitles")
    except Exception as ex:  # noqa: BLE001 - spike thiếu thư viện thì bỏ qua, không làm đỏ CI
        pytest.skip(f"không nạp được subtitles.py của #88: {ex}")
    finally:
        sys.path.remove(str(root))
        for n in names:
            sys.modules.pop(n, None)
        sys.modules.update(saved)


def write_wav(path: Path, seconds: float, rate: int = 8000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(b"\x00\x00" * round(seconds * rate))


class FakeRunner:
    """Thay cho venv VieNeu, venv #88 và ffprobe. Ghi lại mọi lệnh đã gọi."""

    def __init__(self, mp4_duration_s: float = 20.0, speak_s: float = 2.0) -> None:
        self.calls: list[list[str]] = []
        self.envs: list[Mapping[str, str] | None] = []
        self.mp4_duration_s = mp4_duration_s
        self.speak_s = speak_s
        self.fail_ratio: str | None = None
        # --- dựng song song theo cảnh (P1-09)
        self.scene_frames: dict[str, int] = {}  # scene_id → số khung (mặc định 60)
        self.fail_scene: tuple[str, str] | None = None  # (scene_id, tỉ lệ) bị lỗi
        self.hold_until_cancel: set[tuple[str, str]] = set()  # job chờ tới khi bị huỷ
        self.salt: dict[str, str] = {}  # scene_id → "nội dung" (đổi thì khoá cache đổi)
        self.parts: dict[str, list[str]] = {}  # tỉ lệ → scene_id theo thứ tự đã nối
        self.cancelled: list[tuple[str, str]] = []
        self._lock = threading.Lock()
        self.subtitle_cues: dict[str, dict[str, int]] = {}  # tỉ lệ → {segment_id: số cue}

    def count(self, name: str) -> int:
        return sum(1 for c in self.calls if len(c) > 2 and Path(c[1]).name == name)

    def modes(self) -> list[str]:
        return [c[2] for c in self.calls if len(c) > 2 and Path(c[1]).name == "tts_synth.py"]

    def __call__(
        self,
        cmd: Sequence[str],
        *,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        timeout_s: float = 1800,
        cancel: threading.Event | None = None,
    ) -> RunResult:
        cmd = list(cmd)
        with self._lock:
            self.calls.append(cmd)
            self.envs.append(env)
        arg = {cmd[i]: cmd[i + 1] for i in range(len(cmd) - 1) if cmd[i].startswith("--")}
        if cmd[0].endswith("ffprobe") or cmd[0] == "ffprobe":
            data = {
                "format": {"duration": str(self.mp4_duration_s)},
                "streams": [{"codec_type": "video", "width": 1920, "height": 1080}],
            }
            return RunResult(0, json.dumps(data), "", 0.01)
        if Path(cmd[0]).stem == "ffmpeg":  # QA: cắt một khung hình ra file cuối lệnh
            Path(cmd[-1]).write_bytes(b"\xff\xd8fake-jpeg")
            return RunResult(0, "", "", 0.01)
        driver = Path(cmd[1]).name
        if driver == "tts_synth.py":
            return self._tts(cmd[2], arg)
        if driver == "hf_render.py":
            mode = arg.get("--mode", "full")
            if mode == "prepare":
                return self._prepare(arg)
            if mode == "scene":
                return self._scene(arg, cancel)
            if mode == "finalize":
                return self._finalize(arg)
            return self._render(arg)
        raise AssertionError(f"lệnh lạ: {cmd}")

    def _tts(self, mode: str, arg: dict[str, str]) -> RunResult:
        req = json.loads(Path(arg["--request"]).read_text(encoding="utf-8"))
        device, backend = arg["--device"], arg["--backend"]
        backend = "onnx" if backend == "auto" else backend
        if mode == "normalize":
            out = {
                "model": f"fake@abcd1234[{backend}/{device}]",
                "backend": backend,
                "device": device,
                "pron_hash": "pron1",
                "segments": [
                    {"segment_id": s["segment_id"], "text": s["text"], "spoken": s["text"].lower()}
                    for s in req["segments"]
                ],
            }
            return RunResult(0, "log của thư viện\n" + json.dumps(out), "", 0.01)
        out_dir = Path(arg["--out-dir"])
        done = []
        for s in req["segments"]:
            wav = out_dir / f"{s['segment_id']}.wav"
            write_wav(wav, self.speak_s)
            done.append(
                {
                    "segment_id": s["segment_id"],
                    "wav": str(wav),
                    "duration_s": self.speak_s,
                    "synth_s": 0.5,
                }
            )
        return RunResult(0, json.dumps({"model": "fake", "load_s": 6.5, "segments": done}), "", 7.0)

    def hf_calls(self, mode: str) -> list[dict[str, str]]:
        """Đối số `--khoá giá trị` của mọi lần gọi hf_render.py ở chế độ `mode`."""
        out = []
        for c in self.calls:
            if len(c) > 2 and Path(c[1]).name == "hf_render.py":
                arg = {c[i]: c[i + 1] for i in range(len(c) - 1) if c[i].startswith("--")}
                if arg.get("--mode", "full") == mode:
                    out.append(arg)
        return out

    def _prepare(self, arg: dict[str, str]) -> RunResult:
        plan = json.loads(Path(arg["--plan"]).read_text(encoding="utf-8"))
        scenes = [
            {"scene_id": s["scene_id"], "frames": self.scene_frames.get(s["scene_id"], 60)}
            for s in plan["scenes"]
        ]
        out = {
            "fps": 30,
            "total_frames": sum(s["frames"] for s in scenes),
            "scenes": scenes,
            "subtitle_cues": {},
            "prepare_s": 0.5,
        }
        return RunResult(0, "noise\n" + json.dumps(out), "", 0.5)

    def _scene(self, arg: dict[str, str], cancel: threading.Event | None) -> RunResult:
        sid, ratio = arg["--scene"], arg["--ratio"]
        if (sid, ratio) in self.hold_until_cancel and cancel is not None:
            cancel.wait(10)
            if cancel.is_set():
                with self._lock:
                    self.cancelled.append((sid, ratio))
                return RunResult(CANCELLED_RC, "", "huỷ", 0.1)
        if self.fail_scene == (sid, ratio):
            return RunResult(1, "", f"Chrome crash ở {sid}", 2.0)
        tag = ratio.replace(":", "x")
        key = f"{sid}-{ratio}-{arg['--quality']}-{self.salt.get(sid, '')}"
        cache = arg.get("--cache-dir")
        if cache:
            mp4 = Path(cache) / tag / f"{key}.mp4"
        else:
            mp4 = Path(arg["--out"]) / f"{sid}-{tag}.mp4"
        hit = mp4.is_file()
        if not hit:
            mp4.parent.mkdir(parents=True, exist_ok=True)
            mp4.write_bytes(b"mp4")
        out = {
            "scene_id": sid,
            "ratio": ratio,
            "key": key,
            "frames": self.scene_frames.get(sid, 60),
            "compose_s": 0.1,
            "cache_hit": hit,
            "output": str(mp4),
            "hf_wall_s": 0.0 if hit else 5.0,
            "hf_phases": {},
            "wall_s": 0.2 if hit else 5.5,
        }
        return RunResult(0, "noise\n" + json.dumps(out), "", out["wall_s"])

    def _finalize(self, arg: dict[str, str]) -> RunResult:
        ratio = arg["--ratio"]
        parts = json.loads(Path(arg["--parts"]).read_text(encoding="utf-8"))
        with self._lock:
            self.parts[ratio] = [p["scene_id"] for p in parts]
        plan = Path(arg["--plan"])
        mp4 = Path(arg["--out"]) / f"{plan.stem}-{ratio.replace(':', 'x')}.mp4"
        mp4.write_bytes(b"mp4")
        raw = {
            "ratio": ratio,
            "output": str(mp4),
            "quality": arg["--quality"],
            "workers": "1",
            "ffmpeg_wall_s": 2.0,
            "concat_mode": "copy",
            "concat_reason": None,
            "concat_s": 0.1,
            "frames": sum(p["frames"] for p in parts),
            "subtitle_cues": {},
        }
        return RunResult(0, "noise\n" + json.dumps(raw), "", 2.5)

    def _render(self, arg: dict[str, str]) -> RunResult:
        ratio = arg["--ratio"]
        if ratio == self.fail_ratio:
            return RunResult(1, "", "Chrome crash", 3.0)
        plan = Path(arg["--plan"])
        tag = ratio.replace(":", "x")
        mp4 = Path(arg["--out"]) / f"{plan.stem}-{tag}.mp4"
        mp4.write_bytes(b"mp4")
        raw = {
            "ratio": ratio,
            "output": str(mp4),
            "quality": arg["--quality"],
            "workers": arg["--workers"],
            "compose_s": 1.0,
            "hf_wall_s": 10.0,
            "ffmpeg_wall_s": 2.0,
            "subtitle_cues": self.subtitle_cues.get(ratio, {}),
        }
        return RunResult(0, "noise\n" + json.dumps(raw), "", 12.0)


def contract_run4(dst: Path) -> Path:
    """run4 đã sửa cho hợp contract hiện hành (#83 e33827c): hook được đọc ở segment đầu,
    cảnh cuối role cta kết bằng cta.text. Cùng tên file với run4 để tên plan không đổi."""
    data = json.loads(RUN4_SCRIPT.read_text(encoding="utf-8"))
    data["scenes"][0]["narration_segments"][0]["text"] = data["hook"]["text"]
    cta = data["cta"]["text"]
    data["scenes"].append(
        {
            "scene_id": "s06",
            "role": "cta",
            "narration_segments": [{"segment_id": "s06-u01", "text": cta}],
            "subtitle_text": cta,
            "visual_plan": {
                "kind": "text_card",
                "source_type": "generated_text",
                "text": cta,
                "purpose": "Kêu gọi xem thêm thông tin",
            },
            "claims": [],
        }
    )
    dst.mkdir(parents=True, exist_ok=True)
    path = dst / RUN4_SCRIPT.name
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def load_run4() -> tuple[dict[str, Any], dict[str, Any]]:
    return (
        json.loads(RUN4_SCRIPT.read_text(encoding="utf-8")),
        json.loads(RUN4_INPUT.read_text(encoding="utf-8")),
    )


def make_assets(tmp: Path) -> Path:
    """assets.json cho run4: 3 clip + 1 ảnh AI (file rỗng), s01 dùng ảnh qua scene_assets."""
    files = {
        "clips/merge.mp4": 1,
        "clips/pagenum.mp4": 1,
        "clips/word.mp4": 1,
        "ai/paperwork.jpg": 1,
    }
    for rel in files:
        p = tmp / "assets" / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(b"x")
    crop = [440, 0, 1480, 1080]
    doc = {
        "note": "tạm, thay cho BE Storage",
        "assets": {
            "pdfcraft-merge": {
                "kind": "clip",
                "path": "clips/merge.mp4",
                "crop": crop,
                "parts": [{"start_s": 9.8, "end_s": 17.6}],
                "focus": {"part": 0, "source_t": 16.0, "rect": [520, 110, 560, 330]},
            },
            "pdfcraft-pagenum": {
                "kind": "clip",
                "path": "clips/pagenum.mp4",
                "crop": crop,
                "parts": [{"start_s": 1.6, "end_s": 4.0}, {"start_s": 9.4, "end_s": 11.48}],
            },
            "pdfcraft-word-export": {
                "kind": "clip",
                "path": "clips/word.mp4",
                "crop": crop,
                "parts": [{"start_s": 1.4, "end_s": 3.6}, {"start_s": 5.0, "end_s": 12.0}],
            },
            "ai-paperwork": {
                "kind": "image",
                "path": "ai/paperwork.jpg",
                "label": "Ảnh minh hoạ do AI tạo",
                "source": "Cloudflare FLUX (#71)",
            },
        },
        "scene_assets": {"s01": "ai-paperwork"},
    }
    path = tmp / "assets" / "assets.json"
    path.write_text(json.dumps(doc, ensure_ascii=False), encoding="utf-8")
    return path
