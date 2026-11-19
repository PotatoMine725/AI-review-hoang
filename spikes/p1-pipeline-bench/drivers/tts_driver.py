"""Đo TTS VieNeu cho bench P1-07. Chạy bằng venv của spike TTS (#73), không phải venv của bench.

    <p1-tts-vi>/vieneu/.venv/Scripts/python.exe tts_driver.py --tts-dir <p1-tts-vi>/vieneu \
        --plan <pdfcraft-40-45s.json> --device cpu --backend onnx --work <thư mục scratch>

In 1 dòng JSON cuối cùng ra stdout. Không sửa code của spike, chỉ import adapter của nó.
Phần đo: nạp model (lạnh), 1 câu warm-up không tính, 16 câu từng câu, rồi lượt 2 qua cache
theo hash (lần 2 phải gần 0 s).
"""

# pyright: reportMissingImports=false
from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import shutil
import statistics
import sys
import time
import wave
from ctypes import wintypes
from pathlib import Path


def peak_working_set_mb() -> float:
    """RAM đỉnh (PeakWorkingSetSize) của tiến trình hiện tại, MB. Chỉ stdlib."""

    class Counters(ctypes.Structure):
        _fields_ = [("cb", wintypes.DWORD), ("PageFaultCount", wintypes.DWORD),
                    ("PeakWorkingSetSize", ctypes.c_size_t), ("WorkingSetSize", ctypes.c_size_t),
                    ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                    ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                    ("PagefileUsage", ctypes.c_size_t),
                    ("PeakPagefileUsage", ctypes.c_size_t)]  # fmt: skip

    c = Counters()
    c.cb = ctypes.sizeof(c)
    kernel, psapi = ctypes.WinDLL("kernel32"), ctypes.WinDLL("psapi")
    kernel.GetCurrentProcess.restype = wintypes.HANDLE  # mặc định là int 32 bit, cắt mất handle
    psapi.GetProcessMemoryInfo.argtypes = [wintypes.HANDLE, ctypes.c_void_p, wintypes.DWORD]
    if not psapi.GetProcessMemoryInfo(kernel.GetCurrentProcess(), ctypes.byref(c), c.cb):
        return -1.0
    return round(c.PeakWorkingSetSize / 1e6, 1)


def wav_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tts-dir", type=Path, required=True, help="thư mục vieneu/ của spike #73")
    ap.add_argument("--plan", type=Path, required=True)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--backend", default="onnx")
    ap.add_argument("--voice", default="Mai Anh")
    ap.add_argument("--work", type=Path, required=True)
    args = ap.parse_args()

    sys.path.insert(0, str(args.tts_dir))
    from adapter import VieNeuTTS  # noqa: PLC0415  (cần sys.path ở trên)
    from pins import REVISIONS  # noqa: PLC0415
    from tts_common.normalize import normalize_vi  # noqa: PLC0415
    from tts_common.pronunciations import pronunciations_for  # noqa: PLC0415

    plan = json.loads(args.plan.read_text(encoding="utf-8"))
    texts = [g["text"] for s in plan["scenes"] for g in s["narration_segments"]]
    pron = pronunciations_for("vieneu")
    spoken = [normalize_vi(t, pron) for t in texts]
    pron_hash = hashlib.sha256(
        json.dumps(pron, sort_keys=True, ensure_ascii=False).encode()
    ).hexdigest()

    shutil.rmtree(args.work, ignore_errors=True)
    args.work.mkdir(parents=True)
    cache = args.work / "cache"
    cache.mkdir()

    t0 = time.perf_counter()
    tts = VieNeuTTS(args.work / "_tmp", device=args.device, backend=args.backend)
    load_s = time.perf_counter() - t0

    t0 = time.perf_counter()
    warm = tts.synthesize(spoken[0], args.voice)
    warmup_s = time.perf_counter() - t0
    Path(warm.path).unlink(missing_ok=True)

    cuda = args.device != "cpu"
    if cuda:
        import torch

        torch.cuda.reset_peak_memory_stats()

    def key(text: str, voice: str = args.voice) -> str:
        # model + backend + giọng + bảng phát âm + văn bản đã chuẩn hoá: đổi bất kỳ thứ nào là miss
        raw = json.dumps([tts.model, voice, pron_hash, text], ensure_ascii=False)
        return hashlib.sha256(raw.encode()).hexdigest()

    gen: list[float] = []
    audio: list[float] = []
    for text in spoken:
        t0 = time.perf_counter()
        res = tts.synthesize(text, args.voice)
        gen.append(time.perf_counter() - t0)
        audio.append(res.duration_s)
        shutil.move(res.path, cache / f"{key(text)}.wav")
    vram = None
    if cuda:
        import torch

        vram = round(torch.cuda.max_memory_allocated() / 1e6, 1)

    # Lượt 2: đọc lại qua cache theo hash, đo thời gian lấy đủ 16 file
    out = args.work / "from-cache"
    out.mkdir()
    t0 = time.perf_counter()
    hits = 0
    for i, text in enumerate(spoken, start=1):
        src = cache / f"{key(text)}.wav"
        if src.is_file():
            shutil.copyfile(src, out / f"s{i:02d}.wav")
            hits += 1
    cache_s = time.perf_counter() - t0
    # Đổi bảng phát âm hoặc giọng thì phải miss (không trả audio cũ)
    stale_ok = not (cache / f"{key(spoken[0], 'Giọng khác')}.wav").is_file()

    total_gen, total_audio = sum(gen), sum(audio)
    print(
        json.dumps(
            {
                "device": args.device,
                "backend": args.backend,
                "voice": args.voice,
                "model": tts.model,
                "revision": REVISIONS,
                "segments": len(spoken),
                "load_s": round(load_s, 2),
                "warmup_s": round(warmup_s, 2),
                "gen_total_s": round(total_gen, 2),
                "gen_per_segment_s": [round(x, 2) for x in gen],
                "gen_median_s": round(statistics.median(gen), 2),
                "audio_total_s": round(total_audio, 2),
                "rtf": round(total_gen / total_audio, 3),
                "peak_ram_mb": peak_working_set_mb(),
                "peak_vram_mb": vram,
                "cache_hits": hits,
                "cache_s": round(cache_s, 3),
                "cache_miss_on_changed_voice": stale_ok,
                "note": "audio lấy mẫu ngẫu nhiên: duration_s khác nhau giữa các lần",
            },
            ensure_ascii=False,
        )
    )
    shutil.rmtree(args.work / "_tmp", ignore_errors=True)


if __name__ == "__main__":
    main()
