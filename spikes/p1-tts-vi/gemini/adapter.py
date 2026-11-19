"""Adapter Gemini TTS (API `interactions` của google-genai, theo tài liệu speech-generation tra 14/10/2026).

KHÔNG gọi thật mặc định: cần `live=True`. Chỉ bật sau khi có ảnh quota của project (xem README).
Free tier: nội dung gửi lên có thể được Google dùng cải thiện sản phẩm (trang giá, tra 14/10/2026),
nên chỉ gửi kịch bản/câu thử, không gửi upload của merchant hay dữ liệu nhạy cảm.
"""

from __future__ import annotations

import base64
import os
from pathlib import Path
from typing import Any

from tts_common import TTSCost, TTSProvider, TTSResult
from tts_common.provider import wav_duration_s, write_wav_pcm16

DEFAULT_MODEL = "gemini-3.8-flash-tts"  # còn: gemini-3.8-flash-lite-tts
PCM_SAMPLE_RATE = 24000  # tài liệu: WAV 16-bit mono 24 kHz
DEFAULT_STYLE = "clear, natural, upbeat advertising voice, speaking Vietnamese"


class LiveCallsDisabledError(RuntimeError):
    pass


class GeminiTTS(TTSProvider):
    name = "google"
    supports_speed = False  # không có tham số tốc độ; chỉ gợi ý bằng style ("speaking rapidly/slowly")

    def __init__(
        self,
        out_dir: Path,
        *,
        model: str = DEFAULT_MODEL,
        style: str | None = DEFAULT_STYLE,
        live: bool = False,
        max_calls: int = 25,
        client: Any | None = None,
    ) -> None:
        super().__init__(out_dir)
        self.model = model
        self.style = style
        self.live = live
        self.max_calls = max_calls
        self.calls = 0
        self._client = client  # tiêm client giả khi test; None = tạo client thật khi cần

    def _get_client(self) -> Any:
        if self._client is None:
            from google import genai

            key = os.environ.get("GEMINI_API_KEY")
            if not key:
                raise RuntimeError(
                    "thiếu GEMINI_API_KEY (đặt trong .env, chạy bằng `uv run --env-file .env`)"
                )
            self._client = genai.Client(api_key=key)
        return self._client

    def _style_for(self, speed: float) -> str | None:
        hint = "speaking rapidly" if speed > 1.15 else "speaking slowly" if speed < 0.85 else None
        parts = [p for p in (self.style, hint) if p]
        return ", ".join(parts) or None

    def synthesize(self, text: str, voice: str, speed: float = 1.0) -> TTSResult:
        if self._client is None and not self.live:
            raise LiveCallsDisabledError("Gemini TTS chưa được bật gọi thật (live=False); chờ ảnh quota.")
        if self.calls >= self.max_calls:
            raise RuntimeError(
                f"đã đạt giới hạn {self.max_calls} lần gọi trong phiên; dừng để không vượt quota"
            )
        self.calls += 1

        content: dict[str, Any] = {"type": "text", "text": text}
        style = self._style_for(speed)
        if style:
            content["annotations"] = [{"type": "speech_metadata", "style": style}]
        interaction = self._get_client().interactions.create(
            model=self.model,
            input=[{"type": "user_input", "content": [content]}],
            response_format={"type": "audio"},
            generation_config={"speech_config": [{"voice": voice}]},
        )

        data = base64.b64decode(interaction.output_audio.data)
        path = self._new_path()
        if data[:4] == b"RIFF":
            path.write_bytes(data)
        else:  # PCM thô
            write_wav_pcm16(path, data, PCM_SAMPLE_RATE)

        return TTSResult(
            path=path,
            duration_s=wav_duration_s(path),
            timings=None,
            provider=self.name,
            model=self.model,
            cost=self._cost(interaction, text),
        )

    @staticmethod
    def _cost(interaction: Any, text: str) -> TTSCost:
        """Tính theo usage nếu provider trả về (token), không thì ước tính theo số ký tự."""
        usage = getattr(interaction, "usage", None)
        total = getattr(usage, "total_tokens", None) if usage is not None else None
        if isinstance(total, int):
            return TTSCost(unit="tokens", quantity=total, cost_usd=0.0, cost_status="exact")
        return TTSCost(unit="characters", quantity=len(text), cost_usd=0.0, cost_status="estimated")
