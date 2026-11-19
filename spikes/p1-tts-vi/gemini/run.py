"""Chạy bộ câu thử với Gemini TTS. CHỈ chạy khi đã có ảnh quota và có cờ --live.

    uv run --env-file .env python run.py --live --voice Kore [--model gemini-3.8-flash-lite-tts]

Số lần gọi tối đa mỗi phiên = (số câu × 1 variant) + 1 warm-up + kịch bản (5 câu). Mặc định chỉ chạy
variant "norm" để tiết kiệm quota.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from tts_common.bench import load_sentences, run_benchmark
from tts_common.script import synthesize_script

from adapter import DEFAULT_MODEL, GeminiTTS

SPIKE = Path(__file__).parent.parent


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--voice", default="Kore")
    ap.add_argument("--model", default=DEFAULT_MODEL)
    ap.add_argument(
        "--live", action="store_true", help="xác nhận gọi API thật (trong quota free tier đã xác minh)"
    )
    ap.add_argument("--max-calls", type=int, default=25)
    args = ap.parse_args()
    if not args.live:
        raise SystemExit("Chưa gọi thật: thêm --live sau khi đã có ảnh quota (xem README).")

    tag = f"gemini-{args.model}-{args.voice}"
    out = SPIKE / "output" / tag
    tts = GeminiTTS(out, model=args.model, live=True, max_calls=args.max_calls)
    data = SPIKE / "sentences.json"

    summary = run_benchmark(
        tts,
        args.voice,
        load_sentences(data),
        variants=("norm",),
        results_path=out / "results.json",
        meta={"calls": "xem tts.calls"},
    )
    print(f"{tag}: RTF tổng {summary['rtf_overall']} (gồm độ trễ mạng) · {tts.calls} lần gọi")

    script = json.loads(data.read_text(encoding="utf-8"))["script"]
    audio = synthesize_script(tts, script, args.voice, merged_path=out / "script.wav")
    (out / "script-timings.json").write_text(
        json.dumps([vars(t) for t in audio.timings], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"script: {audio.duration_s:.1f}s · tổng {tts.calls} lần gọi")


if __name__ == "__main__":
    main()
