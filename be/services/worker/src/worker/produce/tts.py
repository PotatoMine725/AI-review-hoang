"""TTS theo `segment_id` qua adapter VieNeu (#73), có cache theo hash.

Phần gọi spike: `drivers/tts_synth.py` chạy trong venv của #73 (worker không import `vieneu`).
Phần code worker: khoá cache, tra cache, đo `duration_s` từ chính file wav, log từng câu.

Luồng: (1) `normalize` không nạp model → lời đã chuẩn hoá + khoá model + hash bảng phát âm;
(2) tra cache; (3) chỉ khi có câu miss mới gọi `synth` — model nạp **một lần** cho cả video.
Khoá cache = sha256(model gồm backend/thiết bị, backend, giọng, hash bảng phát âm, lời đã chuẩn
hoá): đổi bất kỳ thứ nào là miss, không trả audio cũ.
"""

from __future__ import annotations

import hashlib
import json
import logging
import shutil
import time
import wave
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from worker.produce.config import ProduceConfig
from worker.produce.errors import ProduceError
from worker.produce.runner import Runner, last_json_line, require_ok

log = logging.getLogger("worker.produce.tts")

DRIVER = Path(__file__).resolve().parent / "drivers" / "tts_synth.py"


@dataclass(frozen=True)
class SpokenSegment:
    segment_id: str
    text: str  # lời gốc của M2
    spoken: str  # lời đã chuẩn hoá đưa vào TTS
    wav: Path
    duration_s: float  # đo thật từ file wav
    cached: bool
    synth_s: float | None  # None nếu lấy từ cache


@dataclass(frozen=True)
class TtsRun:
    segments: tuple[SpokenSegment, ...]
    model: str
    load_s: float | None  # None nếu không phải nạp model (toàn bộ từ cache)
    wall_s: float
    hits: int
    misses: int

    def durations(self) -> dict[str, float]:
        return {s.segment_id: s.duration_s for s in self.segments}

    def voices(self) -> dict[str, Path]:
        return {s.segment_id: s.wav for s in self.segments}


def cache_key(model: str, backend: str, voice: str, pron_hash: str, spoken: str) -> str:
    raw = json.dumps([model, backend, voice, pron_hash, spoken], ensure_ascii=False)
    return hashlib.sha256(raw.encode()).hexdigest()


def wav_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


def _driver_cmd(cfg: ProduceConfig, mode: str, request: Path, *extra: str) -> list[str]:
    py = cfg.venv_python(cfg.tts_dir)
    if not py.is_file():
        raise ProduceError(f"thiếu venv của spike TTS #73: {py} (đặt PRODUCE_TTS_SPIKE)")
    return [
        str(py),
        str(DRIVER),
        mode,
        "--tts-dir",
        str(cfg.tts_dir),
        "--request",
        str(request),
        "--device",
        cfg.tts_device,
        "--backend",
        cfg.tts_backend,
        *extra,
    ]


def synthesize(
    segments: Sequence[tuple[str, str]], cfg: ProduceConfig, runner: Runner, work: Path
) -> TtsRun:
    """segments: [(segment_id, lời gốc)] theo thứ tự phát. `work`: thư mục tạm của lần chạy."""
    t_all = time.perf_counter()
    work.mkdir(parents=True, exist_ok=True)
    cfg.cache_dir.mkdir(parents=True, exist_ok=True)

    req = work / "tts-normalize.json"
    req.write_text(
        json.dumps(
            {
                "voice": cfg.voice,
                "segments": [{"segment_id": i, "text": t} for i, t in segments],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    norm = last_json_line(
        require_ok(runner(_driver_cmd(cfg, "normalize", req)), "TTS normalize").stdout
    )
    model, backend, pron_hash = norm["model"], norm["backend"], norm["pron_hash"]
    spoken = {s["segment_id"]: s["spoken"] for s in norm["segments"]}
    originals = dict(segments)

    keys = {i: cache_key(model, backend, cfg.voice, pron_hash, spoken[i]) for i, _ in segments}
    wav_of = {i: cfg.cache_dir / f"{k}.wav" for i, k in keys.items()}
    # Hai câu cùng lời đã chuẩn hoá chỉ sinh một lần
    todo: dict[str, str] = {}
    for i, _ in segments:
        if not wav_of[i].is_file() and keys[i] not in {keys[j] for j in todo}:
            todo[i] = spoken[i]

    synth_s: dict[str, float] = {}
    load_s: float | None = None
    if todo:
        out_dir = work / "tts-out"
        shutil.rmtree(out_dir, ignore_errors=True)
        sreq = work / "tts-synth.json"
        sreq.write_text(
            json.dumps(
                {
                    "voice": cfg.voice,
                    "segments": [{"segment_id": i, "spoken": s} for i, s in todo.items()],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        res = last_json_line(
            require_ok(
                runner(_driver_cmd(cfg, "synth", sreq, "--out-dir", str(out_dir))),
                "TTS synth",
            ).stdout
        )
        load_s = float(res["load_s"])
        for item in res["segments"]:
            sid = item["segment_id"]
            shutil.move(item["wav"], wav_of[sid])
            synth_s[sid] = float(item["synth_s"])

    out: list[SpokenSegment] = []
    for sid, _ in segments:
        wav = wav_of[sid]
        if not wav.is_file():  # câu trùng lời với câu vừa sinh: dùng chung file
            raise ProduceError(f"TTS không tạo ra audio cho {sid}")
        dur = wav_seconds(wav)
        seg = SpokenSegment(
            segment_id=sid,
            text=originals[sid],
            spoken=spoken[sid],
            wav=wav,
            duration_s=dur,
            cached=sid not in synth_s,
            synth_s=synth_s.get(sid),
        )
        log.info(
            "tts segment=%s cached=%s duration_s=%.3f text=%r spoken=%r",
            sid,
            seg.cached,
            dur,
            seg.text,
            seg.spoken,
        )
        out.append(seg)
    misses = len(synth_s)
    return TtsRun(
        segments=tuple(out),
        model=model,
        load_s=load_s,
        wall_s=time.perf_counter() - t_all,
        hits=len(out) - misses,
        misses=misses,
    )
