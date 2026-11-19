"""Adapter Piper (chạy local bằng onnxruntime). Giọng tải từ rhasspy/piper-voices (xem README)."""

from __future__ import annotations

import wave
from pathlib import Path

from piper import PiperVoice, SynthesisConfig
from tts_common import TTSCost, TTSProvider, TTSResult
from tts_common.provider import wav_duration_s


class PiperTTS(TTSProvider):
    name = "piper"

    def __init__(self, out_dir: Path, models_dir: Path, *, use_cuda: bool = False) -> None:
        super().__init__(out_dir)
        self.models_dir = Path(models_dir)
        self.use_cuda = use_cuda
        self.model = "piper-vi_VN"
        self._voices: dict[str, PiperVoice] = {}

    def _voice(self, voice: str) -> PiperVoice:
        # voice = "vais1000-medium" -> models/vi_VN-vais1000-medium.onnx
        if voice not in self._voices:
            path = self.models_dir / f"vi_VN-{voice}.onnx"
            self._voices[voice] = PiperVoice.load(path, use_cuda=self.use_cuda)
        return self._voices[voice]

    def synthesize(self, text: str, voice: str, speed: float = 1.0) -> TTSResult:
        v = self._voice(voice)
        path = self._new_path()
        cfg = SynthesisConfig(length_scale=1.0 / max(speed, 0.1))  # length_scale lớn = đọc chậm
        with wave.open(str(path), "wb") as wav:
            v.synthesize_wav(text, wav, syn_config=cfg)
        return TTSResult(
            path=path,
            duration_s=wav_duration_s(path),
            timings=None,  # phụ đề căn theo câu (tts_common.synthesize_script)
            provider=self.name,
            model=f"{self.model}/{voice}",
            cost=TTSCost(unit="characters", quantity=len(text), cost_usd=0.0),
        )
