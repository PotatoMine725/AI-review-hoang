"""Tách câu và sinh audio theo câu để căn phụ đề mức câu (không cần timestamp theo từ).

Cách làm: mỗi câu là 1 lần synthesize; độ dài từng câu cộng dồn (kèm khoảng nghỉ) cho ra mốc start/end.
"""

from __future__ import annotations

import re
import wave
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from .normalize import normalize_vi
from .provider import Timing, TTSProvider, TTSResult

# Cắt sau . ! ? … khi theo sau là khoảng trắng hoặc hết chuỗi. "390.000đ", "TP.HCM", "3.5" không bị cắt.
_SENT_END = re.compile(r"(?<=[.!?…])\s+|\n+")


def split_sentences(text: str) -> list[str]:
    return [p.strip() for p in _SENT_END.split(text) if p.strip()]


@dataclass(frozen=True)
class SentenceAudio:
    text: str  # câu gốc, dùng làm phụ đề
    spoken: str  # câu đã chuẩn hoá, đưa vào TTS
    result: TTSResult
    start_s: float
    end_s: float


@dataclass(frozen=True)
class ScriptAudio:
    sentences: list[SentenceAudio]
    duration_s: float
    path: Path | None  # file wav ghép; None nếu không ghép

    @property
    def timings(self) -> list[Timing]:
        return [Timing(s.text, s.start_s, s.end_s) for s in self.sentences]


def synthesize_script(
    provider: TTSProvider,
    text: str,
    voice: str,
    speed: float = 1.0,
    *,
    normalize: Callable[[str], str] | None = normalize_vi,
    gap_s: float = 0.2,
    merged_path: Path | None = None,
) -> ScriptAudio:
    """Sinh audio từng câu, trả mốc thời gian từng câu; ghép thành 1 wav nếu có `merged_path`."""
    sentences: list[SentenceAudio] = []
    cursor = 0.0
    for sent in split_sentences(text):
        spoken = normalize(sent) if normalize else sent
        res = provider.synthesize(spoken, voice, speed)
        sentences.append(SentenceAudio(sent, spoken, res, cursor, cursor + res.duration_s))
        cursor += res.duration_s + gap_s
    total = max(cursor - gap_s, 0.0)
    if merged_path is not None and sentences:
        _concat_wavs([s.result.path for s in sentences], merged_path, gap_s)
    return ScriptAudio(sentences, total, merged_path)


def _concat_wavs(paths: list[Path], out: Path, gap_s: float) -> None:
    """Ghép các wav cùng định dạng, chèn khoảng im lặng `gap_s` giữa các câu."""
    out.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(paths[0]), "rb") as first:
        params = first.getparams()
    gap = bytes(int(gap_s * params.framerate) * params.sampwidth * params.nchannels)
    with wave.open(str(out), "wb") as dst:
        dst.setparams(params)
        for i, p in enumerate(paths):
            with wave.open(str(p), "rb") as src:
                if src.getparams()[:3] != params[:3] or src.getframerate() != params.framerate:
                    raise ValueError(f"định dạng wav khác nhau: {p}")
                if i:
                    dst.writeframes(gap)
                dst.writeframes(src.readframes(src.getnframes()))
