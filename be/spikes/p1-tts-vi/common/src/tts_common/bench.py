"""Chạy bộ câu thử qua 1 provider và đo: thời gian sinh, RTF, RAM, VRAM. Không chấm chất lượng."""

from __future__ import annotations

import json
import platform
import subprocess
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from pathlib import Path

from .normalize import normalize_vi
from .provider import TTSProvider


@dataclass
class Sample:
    id: str
    variant: str  # "norm" = qua normalize_vi, "raw" = văn bản gốc
    focus: str
    text_in: str  # văn bản gửi cho TTS
    chars: int
    words: int
    gen_s: float
    audio_s: float
    rtf: float  # gen_s / audio_s; < 1 là nhanh hơn thời gian thực
    path: str
    cost_unit: str
    cost_quantity: float


def peak_ram_mb() -> float | None:
    """RAM đỉnh (working set) của chính tiến trình này, MB."""
    if platform.system() == "Windows":
        import ctypes
        from ctypes import wintypes

        class Counters(ctypes.Structure):
            _fields_ = [  # noqa: RUF012
                ("cb", wintypes.DWORD),
                ("PageFaultCount", wintypes.DWORD),
                ("PeakWorkingSetSize", ctypes.c_size_t),
                ("WorkingSetSize", ctypes.c_size_t),
                ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPagedPoolUsage", ctypes.c_size_t),
                ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
                ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
                ("PagefileUsage", ctypes.c_size_t),
                ("PeakPagefileUsage", ctypes.c_size_t),
            ]

        c = Counters()
        c.cb = ctypes.sizeof(c)
        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.GetCurrentProcess.restype = wintypes.HANDLE
        kernel32.K32GetProcessMemoryInfo.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(Counters),
            wintypes.DWORD,
        ]
        kernel32.K32GetProcessMemoryInfo.restype = wintypes.BOOL
        if kernel32.K32GetProcessMemoryInfo(kernel32.GetCurrentProcess(), ctypes.byref(c), c.cb):
            return c.PeakWorkingSetSize / 1024 / 1024
        return None
    return None  # spike chạy trên Windows; nơi khác không đo


def gpu_used_mb() -> float | None:
    """VRAM đang dùng toàn GPU (nvidia-smi), MB. None nếu không có GPU NVIDIA."""
    try:
        out = subprocess.run(
            ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        ).stdout.strip()
        return float(out.splitlines()[0])
    except Exception:
        return None


def run_benchmark(
    provider: TTSProvider,
    voice: str,
    sentences: list[dict[str, str]],
    *,
    variants: tuple[str, ...] = ("norm", "raw"),
    speed: float = 1.0,
    normalize: Callable[[str], str] = normalize_vi,
    warmup: bool = True,
    results_path: Path | None = None,
    meta: dict[str, object] | None = None,
) -> dict[str, object]:
    """Chạy từng câu × từng variant. Lần gọi khởi động (warm-up) không tính vào số đo."""
    if warmup:
        provider.synthesize(normalize("Xin chào các bạn."), voice, speed)
    vram_base = gpu_used_mb()
    vram_peak = vram_base
    samples: list[Sample] = []
    for item in sentences:
        for variant in variants:
            text_in = normalize(item["text"]) if variant == "norm" else item["text"]
            t0 = time.perf_counter()
            res = provider.synthesize(text_in, voice, speed)
            gen_s = time.perf_counter() - t0
            used = gpu_used_mb()
            if used is not None and (vram_peak is None or used > vram_peak):
                vram_peak = used
            samples.append(
                Sample(
                    id=item["id"],
                    variant=variant,
                    focus=item.get("focus", ""),
                    text_in=text_in,
                    chars=len(text_in),
                    words=len(text_in.split()),
                    gen_s=round(gen_s, 3),
                    audio_s=round(res.duration_s, 3),
                    rtf=round(gen_s / res.duration_s, 3) if res.duration_s else float("inf"),
                    path=str(res.path),
                    cost_unit=res.cost.unit,
                    cost_quantity=res.cost.quantity,
                )
            )
    total_gen = sum(s.gen_s for s in samples)
    total_audio = sum(s.audio_s for s in samples)
    summary: dict[str, object] = {
        "provider": provider.name,
        "model": provider.model,
        "voice": voice,
        "speed": speed,
        "meta": meta or {},
        "total_gen_s": round(total_gen, 2),
        "total_audio_s": round(total_audio, 2),
        "rtf_overall": round(total_gen / total_audio, 3) if total_audio else None,
        "peak_ram_mb": peak_ram_mb(),
        "vram_baseline_mb": vram_base,
        "vram_peak_mb": vram_peak,
        "samples": [asdict(s) for s in samples],
    }
    if results_path is not None:
        results_path.parent.mkdir(parents=True, exist_ok=True)
        results_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    return summary


def load_sentences(path: Path) -> list[dict[str, str]]:
    return json.loads(path.read_text(encoding="utf-8"))["sentences"]
