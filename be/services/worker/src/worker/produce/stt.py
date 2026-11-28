"""Mốc thời gian từng từ của lời thoại để chia phụ đề đúng nhịp đọc.

Hai backend, chọn bằng `PRODUCE_STT_MODEL`: `whisper-1` (OpenAI, cần khoá) hoặc `local:<cỡ>`
(faster-whisper chạy trên máy, không cần khoá, vd. `local:small`; cài bằng
`uv sync --extra stt-local`).

Adapter mỏng (ADR-0005): đổi provider chỉ sửa file này. TTS VieNeu chỉ cho độ dài cả câu, nên
sau khi có wav ta chép lại bằng STT để lấy mốc từng từ. Chỉ `whisper-1` hỗ trợ
`timestamp_granularities=word`; `gpt-4o-transcribe` không có mốc từ.

Kết quả cache theo (model, sha256 của wav) trong `cfg.cache_dir/stt`, chạy lại không tốn tiền.
Lỗi STT KHÔNG làm hỏng video: pipeline ghi cảnh báo và rơi về chia theo số ký tự.
"""

from __future__ import annotations

import hashlib
import importlib
import json
import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

import httpx

from worker.produce.cues import Word
from worker.produce.errors import ProduceAuthError, ProduceError

log = logging.getLogger("worker.produce.stt")

OPENAI_STT_URL = "https://api.openai.com/v1/audio/transcriptions"
WORD_MODEL = "whisper-1"
PRICE_PER_MIN_USD = 0.006  # whisper-1
LOCAL_PREFIX = "local:"


class WordStt(Protocol):
    @property
    def model(self) -> str: ...

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
                if r.status_code in (401, 403):
                    raise ProduceAuthError(f"OpenAI STT từ chối khoá: {err}")
                if r.status_code not in (429, 500, 502, 503, 504):
                    raise ProduceError(f"OpenAI STT từ chối: {err}")
            if attempt < len(self.retry_delays_s):
                time.sleep(self.retry_delays_s[attempt])
        raise ProduceError(f"OpenAI STT lỗi sau {len(self.retry_delays_s) + 1} lần: {err}")


@dataclass
class LocalWordStt:
    """faster-whisper trên máy (CPU int8): miễn phí, không khoá. Thư viện nạp lười, thiếu thì báo
    `ProduceError` để pipeline chỉ cảnh báo và rơi về chia theo ký tự."""

    size: str = "small"
    language: str = "vi"
    device: str = "cpu"
    compute_type: str = "int8"
    cache_dir: Path | None = None
    calls: int = 0  # số lần chạy mô hình thật (không tính cache)
    cached: int = 0
    _model: Any = None

    @property
    def model(self) -> str:
        return f"{LOCAL_PREFIX}{self.size}"

    def _load(self) -> Any:
        if self._model is None:
            try:
                fw = importlib.import_module("faster_whisper")
            except ImportError as ex:
                raise ProduceError(
                    "chưa cài faster-whisper: chạy `uv sync --extra stt-local` "
                    "hoặc bỏ PRODUCE_STT_MODEL"
                ) from ex
            try:
                self._model = fw.WhisperModel(
                    self.size, device=self.device, compute_type=self.compute_type
                )
            except Exception as ex:  # tải/khởi tạo mô hình lỗi (mạng, RAM, tên cỡ sai)
                raise ProduceError(f"không nạp được faster-whisper {self.size!r}: {ex}") from ex
        return self._model

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
        model = self._load()
        try:
            segments, _info = model.transcribe(
                str(wav), language=self.language, word_timestamps=True
            )
            data = {
                "words": [
                    {"word": w.word, "start": w.start, "end": w.end}
                    for seg in segments
                    for w in (seg.words or [])
                ]
            }
        except Exception as ex:
            raise ProduceError(f"faster-whisper lỗi khi chép {wav.name}: {ex}") from ex
        self.calls += 1
        if cache is not None:
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        return parse_words(data)


def make_stt(model: str, *, api_key: str = "", cache_dir: Path | None = None) -> WordStt:
    """`local:<cỡ>` → faster-whisper; còn lại → OpenAI (cần `api_key`)."""
    if model.startswith(LOCAL_PREFIX):
        size = model[len(LOCAL_PREFIX) :].strip()
        if not size:
            raise ProduceError("PRODUCE_STT_MODEL=local: thiếu cỡ mô hình (vd. local:small)")
        return LocalWordStt(size, cache_dir=cache_dir)
    if not api_key:
        raise ProduceError(f"PRODUCE_STT_MODEL={model} cần OPENAI_API_KEY (hoặc dùng local:small)")
    return OpenAIWordStt(api_key, model, cache_dir=cache_dir)


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
        except ProduceAuthError as ex:  # khoá sai: dừng, không gọi tiếp các câu còn lại
            warnings.append(
                f"stt_disabled_auth: {ex}. Bỏ PRODUCE_STT_MODEL hoặc đổi OPENAI_API_KEY"
            )
            break
        except ProduceError as ex:
            warnings.append(f"stt_failed[{sid}]: {ex}")
            continue
        if done[wav]:
            words[sid] = done[wav]
        else:
            warnings.append(f"stt_empty[{sid}]: không có mốc từ")
    return words, warnings


def stt_cost_usd(seconds: float, model: str = WORD_MODEL) -> float:
    if model.startswith(LOCAL_PREFIX):
        return 0.0
    return round(seconds / 60 * PRICE_PER_MIN_USD, 5)


def dump_words(words: dict[str, list[Word]], path: Path) -> None:
    path.write_text(
        json.dumps({k: [list(w) for w in v] for k, v in words.items()}, ensure_ascii=False),
        encoding="utf-8",
    )
