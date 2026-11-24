"""Adapter VieNeu-TTS v3 Turbo (SDK `vieneu`, weight pnnbao-ump/VieNeu-TTS-v3-Turbo, Apache-2.0)."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np
from tts_common import TTSCost, TTSProvider, TTSResult
from tts_common.provider import write_wav_pcm16
from vieneu import Vieneu

from pins import REVISIONS, VIENEU_REPO, vieneu_kwargs


class VieNeuTTS(TTSProvider):
    name = "vieneu"
    supports_speed = False  # SDK không có tham số tốc độ; muốn chỉnh phải xử lý hậu kỳ (vd. ffmpeg atempo)

    def __init__(self, out_dir: Path, *, device: str = "auto", backend: str = "auto") -> None:
        super().__init__(out_dir)
        if backend == "auto":  # giống SDK: CPU -> ONNX, GPU -> PyTorch (cần biết trước để ghim đúng repo)
            backend = "onnx" if device == "cpu" else "pytorch"
        # SDK khai báo kiểu quá rộng (Optional/Union) nên coi là Any
        self._tts: Any = Vieneu(mode="v3turbo", device=device, backend=backend, **vieneu_kwargs(backend))
        self.model = f"{VIENEU_REPO}@{REVISIONS[VIENEU_REPO][:8]}[{backend}/{device}]"
        self.sample_rate = int(self._tts.sample_rate)

    def synthesize(
        self, text: str, voice: str, speed: float = 1.0, **infer_kwargs: Any
    ) -> TTSResult:
        """`infer_kwargs` đi thẳng vào `Vieneu.infer` (vd. `max_chars=60`, `temperature`)."""
        audio = np.asarray(self._tts.infer(text, voice=voice, **infer_kwargs), dtype=np.float32).reshape(-1)
        pcm = (np.clip(audio, -1.0, 1.0) * 32767.0).astype(np.int16)
        path = self._new_path()
        write_wav_pcm16(path, pcm.tobytes(), self.sample_rate)
        return TTSResult(
            path=path,
            duration_s=len(pcm) / self.sample_rate,
            timings=None,
            provider=self.name,
            model=self.model,
            cost=TTSCost(unit="characters", quantity=len(text), cost_usd=0.0),
        )
