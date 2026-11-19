"""Chạy bộ câu thử với Piper: uv run python run.py [--cuda] [--voice vais1000-medium]

Kết quả: output/piper-<voice>/ (wav, không commit) + results.json (số đo).
"""

from __future__ import annotations

import argparse
from pathlib import Path

from tts_common.bench import load_sentences, run_benchmark
from tts_common.script import synthesize_script

from adapter import PiperTTS

HERE = Path(__file__).parent
SPIKE = HERE.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="vais1000-medium")
    ap.add_argument("--cuda", action="store_true", help="chạy onnxruntime GPU (cần onnxruntime-gpu)")
    args = ap.parse_args()

    tag = f"piper-{args.voice}" + ("-gpu" if args.cuda else "-cpu")
    out = SPIKE / "output" / tag
    tts = PiperTTS(out, HERE / "models", use_cuda=args.cuda)
    data = SPIKE / "sentences.json"

    summary = run_benchmark(
        tts,
        args.voice,
        load_sentences(data),
        results_path=out / "results.json",
        meta={"device": "cuda" if args.cuda else "cpu"},
    )
    print(f"{tag}: RTF tổng {summary['rtf_overall']} · RAM đỉnh {summary['peak_ram_mb']:.0f} MB")

    # Kịch bản đầy đủ: audio theo câu + mốc thời gian câu cho phụ đề
    import json

    script = json.loads(data.read_text(encoding="utf-8"))["script"]
    audio = synthesize_script(tts, script, args.voice, merged_path=out / "script.wav")
    (out / "script-timings.json").write_text(
        json.dumps([vars(t) for t in audio.timings], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"script: {audio.duration_s:.1f}s, {len(audio.sentences)} câu → {out / 'script.wav'}")


if __name__ == "__main__":
    main()
