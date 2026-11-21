"""Mốc thời gian từng từ của lời thoại (OpenAI whisper-1) để chia phụ đề đúng nhịp đọc.

Adapter mỏng (ADR-0005): đổi provider chỉ sửa file này. TTS VieNeu chỉ cho độ dài cả câu, nên
sau khi có wav ta chép lại bằng STT để lấy mốc từng từ. Chỉ `whisper-1` hỗ trợ
`timestamp_granularities=word`; `gpt-4o-transcribe` không có mốc từ.

Kết quả cache theo (model, sha256 của wav) trong `cfg.cache_dir/stt`, chạy lại không tốn tiền.
Lỗi STT KHÔNG làm hỏng video: pipeline ghi cảnh báo và rơi về chia theo số ký tự.
"""

from __future__ import annotations

import hashlib
import json
import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import httpx

from worker.produce.cues import Word
from worker.produce.errors import ProduceError

log = logging.getLogger("worker.produce.stt")

OPENAI_STT_URL = "https://api.openai.com/v1/audio/transcriptions"
WORD_MODEL = "whisper-1"
PRICE_PER_MIN_USD = 0.006  # whisper-1


class WordStt(Protocol):
    model: str

    def transcribe(self, wav: Path) -> list[Word]: ...


@dataclass
class OpenAIWordStt:
    api_key: str
    model: str = WORD_MODEL
    language: str = "vi"
    cache_dir: Path | None = None
    timeout_s: float = 120.0
    client: httpx.Client | None = None
    retry_delays_s: tuple[float, ...] = (3.0, 10.0)
    calls: int = 0  # số lần gọi API thật (không tính cache)
    cached: int = 0

    def __post_init__(self) -> None:
        if self.model != WORD_MODEL:
            raise ProduceError(f"mốc từng từ chỉ có ở {WORD_MODEL}, nhận {self.model!r}")
        self._client = self.client or httpx.Client(timeout=self.timeout_s)

    def _cache_file(self, wav: Path) -> Path | None:
        if self.cache_dir is None:
            return None
        digest = hashlib.sha256(wav.read_bytes()).hexdigest()
        tag = hashlib.sha256(f"{self.model}|{self.language}|{digest}".encode()).hexdigest()
        return self.cache_dir / f"{tag}.json"

    def transcribe(self, wav: Path) -> list[Word]:
        cache = self._cache_file(wav)
        if cache is not None and cache.is_file():
            self.cached += 1
            return parse_words(json.loads(cache.read_text(encoding="utf-8")))
        data = self._call(wav)
        words = parse_words(data)
        if cache is not None:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return words

    def _call(self, wav: Path) -> dict:
        headers = {"Authorization": f"Bearer {self.api_key}"}
        form = {
            "model": self.model,
            "language": self.language,
            "response_format": "verbose_json",
            "timestamp_granularities[]": ["word"],
        }
        err = ""
        for attempt in range(len(self.retry_delays_s) + 1):
            try:
                with wav.open("rb") as fh:
                    r = self._client.post(
                        OPENAI_STT_URL,
                        headers=headers,
                        data=form,
                        files={"file": (wav.name, fh, "audio/wav")},
                    )
            except httpx.HTTPError as ex:
                err = f"lỗi mạng {type(ex).__name__}"
            else:
                if r.status_code == 200:
                    self.calls += 1
                    return r.json()
                err = f"HTTP {r.status_code}: {r.text[:200]}"
                if r.status_code not in (429, 500, 502, 503, 504):
                    raise ProduceError(f"OpenAI STT từ chối: {err}")
            if attempt < len(self.retry_delays_s):
                time.sleep(self.retry_delays_s[attempt])
        raise ProduceError(f"OpenAI STT lỗi sau {len(self.retry_delays_s) + 1} lần: {err}")


def parse_words(data: dict) -> list[Word]:
    """`words` của verbose_json → [(từ, bắt đầu, kết thúc)]; bỏ mục hỏng."""
    out: list[Word] = []
    for w in data.get("words") or []:
        try:
            text, start, end = str(w["word"]).strip(), float(w["start"]), float(w["end"])
        except (KeyError, TypeError, ValueError):
            continue
        if text and end >= start >= 0:
            out.append((text, start, end))
    return out


def transcribe_segments(
    stt: WordStt, segments: Sequence[tuple[str, Path]]
) -> tuple[dict[str, list[Word]], list[str]]:
    """{segment_id: mốc từ} và danh sách cảnh báo (câu nào STT lỗi/trống thì bỏ qua)."""
    words: dict[str, list[Word]] = {}
    warnings: list[str] = []
    done: dict[Path, list[Word]] = {}
    for sid, wav in segments:
        try:
            if wav not in done:
                done[wav] = stt.transcribe(wav)
        except ProduceError as ex:
            warnings.append(f"stt_failed[{sid}]: {ex}")
            continue
        if done[wav]:
            words[sid] = done[wav]
        else:
            warnings.append(f"stt_empty[{sid}]: không có mốc từ")
    return words, warnings


def stt_cost_usd(seconds: float) -> float:
    return round(seconds / 60 * PRICE_PER_MIN_USD, 5)


def dump_words(words: dict[str, list[Word]], path: Path) -> None:
    path.write_text(
        json.dumps({k: [list(w) for w in v] for k, v in words.items()}, ensure_ascii=False),
        encoding="utf-8",
    )
