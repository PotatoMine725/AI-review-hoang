"""Giao diện TTS adapter (ADR-0005: provider đi sau adapter, chọn bằng config).

Giao diện rút ra từ nhu cầu của spike, chưa phải bản chốt cho worker:
    TTSProvider.synthesize(text, voice, speed) -> TTSResult
"""

from __future__ import annotations

import abc
import uuid
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Literal


@dataclass(frozen=True)
class Timing:
    """Mốc thời gian một đoạn trong audio (giây). Ở spike này chỉ dùng cho mức câu."""

    text: str
    start_s: float
    end_s: float


@dataclass(frozen=True)
class TTSCost:
    """Usage 1 lần gọi, theo đơn vị của provider (ký tự, giây...). Không quy đổi sang token LLM.

    `unit`/`quantity` là cấu trúc NỘI BỘ spike (ghi vào kết quả đo), không phải đề xuất schema.
    Cách ghi usage chính thức thống nhất ở #74; `to_item` chỉ xuất các trường cost-breakdown.v1 hiện cho phép.
    """

    unit: Literal["characters", "seconds", "tokens", "none"]
    quantity: float
    cost_usd: float = 0.0
    cost_status: Literal["exact", "estimated"] = "exact"

    def to_item(
        self,
        *,
        provider: str,
        model: str,
        step: str = "tts",
        attempt: int = 1,
        call_id: str | None = None,
    ) -> dict[str, object]:
        """Item hợp lệ theo cost-breakdown.v1 (category=tts)."""
        return {
            "call_id": call_id or str(uuid.uuid4()),
            "category": "tts",
            "step": step,
            "provider": provider,
            "model": model,
            "attempt": attempt,
            "cache_hit": False,
            "cost_usd": round(self.cost_usd, 6),
            "cost_status": self.cost_status,
        }


@dataclass(frozen=True)
class TTSResult:
    path: Path
    duration_s: float
    timings: list[Timing] | None  # None = provider không có mốc thời gian
    provider: str
    model: str
    cost: TTSCost


class TTSProvider(abc.ABC):
    """Lớp cơ sở. `out_dir` là thư mục ghi wav (local, không commit)."""

    name: str = ""
    model: str = ""
    supports_speed: bool = True  # False: provider bỏ qua `speed`, muốn đổi tốc độ phải xử lý hậu kỳ

    def __init__(self, out_dir: Path) -> None:
        self.out_dir = Path(out_dir)

    @abc.abstractmethod
    def synthesize(self, text: str, voice: str, speed: float = 1.0) -> TTSResult: ...

    def _new_path(self, suffix: str = ".wav") -> Path:
        self.out_dir.mkdir(parents=True, exist_ok=True)
        return self.out_dir / f"{uuid.uuid4().hex[:12]}{suffix}"


def wav_duration_s(path: Path) -> float:
    with wave.open(str(path), "rb") as w:
        return w.getnframes() / w.getframerate()


def write_wav_pcm16(path: Path, samples: bytes, sample_rate: int) -> None:
    """Ghi PCM 16-bit mono."""
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(samples)
