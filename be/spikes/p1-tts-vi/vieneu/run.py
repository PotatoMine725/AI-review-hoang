"""Chạy bộ câu thử với VieNeu-TTS.

    uv run python run.py --device cuda --backend pytorch --voice "Mai Anh"
    uv run python run.py --device cpu  --backend pytorch --voice "Mai Anh"
    uv run python run.py --device cpu  --backend onnx    --voice "Mai Anh"

Kết quả: output/vieneu-<voice>-<backend>-<device>/ (wav, không commit) + results.json.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

from tts_common.bench import load_sentences, run_benchmark
from tts_common.normalize import normalizer_for
from tts_common.script import synthesize_script

from adapter import VieNeuTTS

SPIKE = Path(__file__).parent.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="Mai Anh")
    ap.add_argument("--device", default="auto")
    ap.add_argument("--backend", default="auto")
    args = ap.parse_args()

    slug = re.sub(r"\W+", "-", args.voice.lower()).strip("-")
    tag = f"vieneu-{slug}-{args.backend}-{args.device}"
    out = SPIKE / "output" / tag
    tts = VieNeuTTS(out, device=args.device, backend=args.backend)

    vram_torch_mb = None
    try:
        import torch

        if torch.cuda.is_available() and args.device in ("auto", "cuda"):
            torch.cuda.reset_peak_memory_stats()
    except ImportError:
        torch = None  # type: ignore[assignment]

    data = SPIKE / "sentences.json"
    normalize = normalizer_for("vieneu")  # bảng phát âm riêng của VieNeu (không phiên âm ElevenLabs)
    summary = run_benchmark(
        tts,
        args.voice,
        load_sentences(data),
        normalize=normalize,
        results_path=out / "results.json",
        meta={"device": args.device, "backend": args.backend},
    )
    if torch is not None and torch.cuda.is_available() and args.device in ("auto", "cuda"):
        vram_torch_mb = torch.cuda.max_memory_allocated() / 1024 / 1024
        summary["vram_torch_peak_mb"] = round(vram_torch_mb, 1)
        (out / "results.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        f"{tag}: RTF tổng {summary['rtf_overall']} · RAM đỉnh {summary['peak_ram_mb']:.0f} MB"
        f" · VRAM torch đỉnh {vram_torch_mb}"
    )

    script = json.loads(data.read_text(encoding="utf-8"))["script"]
    audio = synthesize_script(tts, script, args.voice, normalize=normalize, merged_path=out / "script.wav")
    (out / "script-timings.json").write_text(
        json.dumps([vars(t) for t in audio.timings], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"script: {audio.duration_s:.1f}s, {len(audio.sentences)} câu")


if __name__ == "__main__":
    main()
