"""Tổng hợp giọng VieNeu cho các câu mới hoặc đã đổi thương hiệu, ghi vào `local/voice-acme/`.

Câu thoại gốc của spike TTS (PR #73) nhắc một thương hiệu thật. Vì chưa có quyền dùng tên/tư
liệu thương hiệu (BA #52, #67) nên spike dùng thương hiệu giả "Acme Demo". `prepare_real.py` đổi
chữ trong caption; script này tạo giọng khớp với chữ mới (`s<i>.wav`).

Video P1 dài 40–45 s nên còn tạo giọng cho 5 câu mới `prepare_real.EXTRA_TEXT` (`x<k>.wav`).
File đã có thì bỏ qua (giữ nguyên bản đã/sẽ được nghe), thêm `--force` để tổng hợp lại.

`vieneu` KHÔNG phải dependency của spike (spike chỉ cần pydantic + ffmpeg): chạy script này bằng
venv của spike TTS, đã cài sẵn `vieneu`:

    <tts-spike>/spikes/p1-tts-vi/vieneu/.venv/Scripts/python.exe resynth_voice.py

Mô hình giống bộ gốc: VieNeu-TTS v3 Turbo, giọng "Mai Anh", ONNX/CPU.
"""

from __future__ import annotations

import argparse
import importlib
import json
import sys
import wave
from pathlib import Path

from prepare_real import (
    BRAND_FROM,
    BRAND_TO,
    DEFAULT_TTS_CONFIG,
    DEFAULT_TTS_DIR,
    EXTRA_TEXT,
    LOCAL,
)

OUT = LOCAL / "voice-acme"


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--tts-dir", type=Path, default=DEFAULT_TTS_DIR)
    parser.add_argument("--tts-config", default=DEFAULT_TTS_CONFIG)
    parser.add_argument("--voice", default="Mai Anh")
    parser.add_argument("--force", action="store_true", help="tổng hợp lại cả file đã có")
    args = parser.parse_args()

    cfg = args.tts_dir / args.tts_config
    timings = json.loads((cfg / "script-timings.json").read_text(encoding="utf-8"))
    todo = [(f"s{i}", t["text"].replace(BRAND_FROM, BRAND_TO)) for i, t in enumerate(timings, 1)
            if BRAND_FROM in t["text"]]  # fmt: skip
    todo += list(EXTRA_TEXT.items())
    if not args.force:
        have = {name for name, _ in todo if (OUT / f"{name}.wav").is_file()}
        for name in sorted(have):
            print(f"{name}.wav: đã có, bỏ qua (--force để tổng hợp lại)")
        todo = [(name, text) for name, text in todo if name not in have]
    if not todo:
        print("Không câu nào cần tổng hợp.")
        return 0

    try:
        vieneu = importlib.import_module("vieneu")
        np = importlib.import_module("numpy")
    except ImportError as exc:
        print(f"LỖI: thiếu '{exc.name}'. Chạy bằng venv của spike TTS (xem docstring).",
              file=sys.stderr)  # fmt: skip
        return 2

    tts = vieneu.Vieneu(mode="v3turbo", device="cpu", backend="onnx")
    OUT.mkdir(parents=True, exist_ok=True)
    for name, text in todo:
        audio = np.asarray(tts.infer(text, voice=args.voice), dtype=np.float32).reshape(-1)
        pcm = (np.clip(audio, -1.0, 1.0) * 32767.0).astype(np.int16)
        with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(int(tts.sample_rate))
            w.writeframes(pcm.tobytes())
        print(f"{name}.wav: {len(pcm) / tts.sample_rate:.2f} s — {text}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
