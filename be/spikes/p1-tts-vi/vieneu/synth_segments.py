"""CLI bàn giao cho M2: sinh giọng VieNeu theo TỪNG ĐOẠN (câu/scene) và ghi độ dài đo thật.

    uv run python synth_segments.py ../samples/segments.sample.json --device cpu --backend onnx
    uv run python synth_segments.py kich-ban.json --voice "Hải Đăng" --pronunciations bang-phat-am.json
    uv run python synth_segments.py kich-ban.json --only 3 5      # chỉ sinh lại đoạn 3 và 5

Đầu vào (JSON), một trong hai dạng:
    {"segments": [{"text": "Câu 1..."}, ...]}      # hoặc "scenes": [{"voice_text": "..."}]
Đầu ra trong --out-dir (mặc định output/handoff/):
    s01.wav, s02.wav, ...   audio từng đoạn (KHÔNG commit)
    tts-log.json            cùng dạng với spikes/p1-demo-pdfcraft/runs/*/tts-log.json (#78):
                            khoá "1", "2"... + "_meta". Mỗi đoạn: segment_id, voice_text (lời gốc),
                            normalized (văn bản đưa vào TTS), path, duration_s, gen_s, voice.
                            segment_id lấy từ "id"/"segment_id" của đầu vào; thiếu thì s01, s02...
Bảng phát âm: bảng riêng của VieNeu (`pronunciations_for("vieneu")`), gộp đè file --pronunciations nếu có.
Sửa lời hoặc bảng phát âm rồi chỉ chạy --only: CLI cảnh báo các đoạn còn lại trong log đã cũ,
phải sinh lại audio và cập nhật timing.

Renderer phải lấy `duration_s` từ log của LẦN CHẠY THẬT (hoặc đo lại từ file wav), không dùng log mẫu:
VieNeu lấy mẫu ngẫu nhiên nên mỗi lần sinh ra độ dài khác nhau.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
import time
from pathlib import Path
from typing import Any

from tts_common.normalize import normalize_vi
from tts_common.pronunciations import load_pronunciations, pronunciations_for
from tts_common.segments import Segment, load_segments, log_entry, stale_segments

from adapter import VieNeuTTS
from pins import REMOTE_CODE_SHA256, REVISIONS

SPIKE = Path(__file__).parent.parent


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("script", type=Path)
    ap.add_argument("--voice", default="Mai Anh")
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--backend", default="onnx", choices=["onnx", "pytorch", "auto"])
    ap.add_argument("--pronunciations", type=Path, help="JSON {từ: cách đọc}, gộp đè lên bảng mặc định")
    ap.add_argument("--out-dir", type=Path, default=SPIKE / "output" / "handoff")
    ap.add_argument("--only", type=int, nargs="*", help="chỉ sinh các đoạn này (đánh số từ 1)")
    args = ap.parse_args()

    try:
        segments = load_segments(args.script)
    except ValueError as e:
        raise SystemExit(str(e)) from e
    pron = pronunciations_for("vieneu")
    if args.pronunciations:
        pron = load_pronunciations(args.pronunciations, "vieneu")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    log_path = args.out_dir / "tts-log.json"
    log: dict[str, Any] = json.loads(log_path.read_text(encoding="utf-8")) if log_path.is_file() else {}

    def spoken_of(seg: Segment) -> str:
        return normalize_vi(seg.text, pron)

    if args.only:
        skipped = [s for s in segments if s.index not in args.only]
        stale = stale_segments(skipped, log, spoken_of)
        if stale:
            print(
                f"CẢNH BÁO: đoạn {', '.join(stale)} không khớp log cũ (lời hoặc bảng phát âm đã đổi): "
                "sinh lại audio và cập nhật duration_s, không dùng lại thời lượng cũ.",
                file=sys.stderr,
            )
    tts = VieNeuTTS(args.out_dir / "_tmp", device=args.device, backend=args.backend)
    for seg in segments:
        if args.only and seg.index not in args.only:
            continue
        i = seg.index
        spoken = spoken_of(seg)
        t0 = time.monotonic()
        res = tts.synthesize(spoken, args.voice)
        gen_s = time.monotonic() - t0
        dest = args.out_dir / f"s{i:02d}.wav"
        shutil.move(res.path, dest)
        log[str(i)] = log_entry(seg, spoken, dest.name, res.duration_s, gen_s, voice=args.voice)
        print(f"{seg.segment_id} {res.duration_s:5.2f}s (sinh {gen_s:4.1f}s) | {spoken}")
    shutil.rmtree(args.out_dir / "_tmp", ignore_errors=True)

    log["_meta"] = {
        "provider": tts.name,
        "model": tts.model,
        "voice": args.voice,
        "sample_rate": tts.sample_rate,
        "revisions": REVISIONS,
        "remote_code_sha256": REMOTE_CODE_SHA256,
        "pronunciations": f"vieneu + {args.pronunciations}" if args.pronunciations else "vieneu",
        "note": "mẫu ngẫu nhiên: duration_s khác nhau giữa các lần chạy",
    }
    log_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")
    total = sum(v["duration_s"] for k, v in log.items() if k != "_meta")
    print(f"tổng thoại {total:.2f} s → {args.out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
