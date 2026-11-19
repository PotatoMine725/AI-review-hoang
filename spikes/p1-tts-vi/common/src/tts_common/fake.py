"""FakeTTS: wav im lặng đúng độ dài ước tính, dùng cho CI và test (không gọi dịch vụ nào)."""

from __future__ import annotations

import re

from .provider import TTSCost, TTSProvider, TTSResult, wav_duration_s, write_wav_pcm16

_SAMPLE_RATE = 16000
_SEC_PER_WORD = 0.30  # tiếng Việt: 1 từ ~ 1 âm tiết, đọc quảng cáo ~3 từ/giây
_PAUSE_COMMA_S = 0.15
_PAUSE_SENTENCE_S = 0.35


def estimate_duration_s(text: str, speed: float = 1.0) -> float:
    """Ước tính thời lượng đọc. Dùng để lên kế hoạch cảnh trước khi có audio thật."""
    words = len(re.findall(r"\S+", text))
    commas = len(re.findall(r"[,;:]", text))
    stops = len(re.findall(r"[.!?…]", text))
    base = words * _SEC_PER_WORD + commas * _PAUSE_COMMA_S + stops * _PAUSE_SENTENCE_S
    return base / max(speed, 0.1)


class FakeTTS(TTSProvider):
    name = "fake"
    model = "silent-estimate"

    def synthesize(self, text: str, voice: str, speed: float = 1.0) -> TTSResult:
        duration = estimate_duration_s(text, speed)
        n = int(duration * _SAMPLE_RATE)
        path = self._new_path()
        write_wav_pcm16(path, bytes(n * 2), _SAMPLE_RATE)
        return TTSResult(
            path=path,
            duration_s=wav_duration_s(path),
            timings=None,
            provider=self.name,
            model=self.model,
            cost=TTSCost(unit="characters", quantity=len(text)),
        )
