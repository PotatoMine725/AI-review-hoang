"""PHẦN GỌI SPIKE #73 (VieNeu). Chạy bằng venv của spike TTS, KHÔNG phải venv của worker.

    <p1-tts-vi>/vieneu/.venv/Scripts/python.exe tts_synth.py normalize --tts-dir <vieneu> \
        --request req.json --device cpu --backend auto
    <p1-tts-vi>/vieneu/.venv/Scripts/python.exe tts_synth.py synth --tts-dir <vieneu> \
        --request req.json --device cpu --backend auto --out-dir <thư mục>

`normalize`: chỉ chuẩn hoá lời + tính khoá model, KHÔNG nạp model (nhanh), để worker tra cache
trước khi tốn 7–13 s nạp model. Request: {"voice": str, "segments": [{"segment_id", "text"}]}.
`synth`: nạp model 1 lần, sinh từng câu. Request: {"voice": str,
"segments": [{"segment_id", "spoken"}]}; ghi `<segment_id>.wav` vào --out-dir.
Cả hai in một dòng JSON cuối cùng ra stdout. Không sửa code của spike, chỉ import adapter của nó.
"""

# pyright: reportMissingImports=false
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path


def resolve(device: str, backend: str) -> tuple[str, str]:
    """Giống adapter #73: backend auto → CPU dùng ONNX, GPU dùng PyTorch."""
    if device == "auto":
        try:
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
        except ImportError:
            device = "cpu"
    if backend == "auto":
        backend = "onnx" if device == "cpu" else "pytorch"
    return device, backend


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("mode", choices=["normalize", "synth"])
    ap.add_argument("--tts-dir", type=Path, required=True)
    ap.add_argument("--request", type=Path, required=True)
    ap.add_argument("--device", default="cpu")
    ap.add_argument("--backend", default="auto")
    ap.add_argument("--out-dir", type=Path)
    args = ap.parse_args()

    sys.path.insert(0, str(args.tts_dir))
    req = json.loads(args.request.read_text(encoding="utf-8"))
    device, backend = resolve(args.device, args.backend)

    if args.mode == "normalize":
        from pins import REVISIONS, VIENEU_REPO
        from tts_common.normalize import normalize_vi
        from tts_common.pronunciations import pronunciations_for

        pron = pronunciations_for("vieneu")
        pron_hash = hashlib.sha256(
            json.dumps(pron, sort_keys=True, ensure_ascii=False).encode()
        ).hexdigest()
        segs = [
            {
                "segment_id": s["segment_id"],
                "text": s["text"],
                "spoken": normalize_vi(s["text"], pron),
            }
            for s in req["segments"]
        ]
        # cùng công thức `model` của adapter #73, không cần nạp model
        model = f"{VIENEU_REPO}@{REVISIONS[VIENEU_REPO][:8]}[{backend}/{device}]"
        print(
            json.dumps(
                {
                    "model": model,
                    "backend": backend,
                    "device": device,
                    "pron_hash": pron_hash,
                    "segments": segs,
                },
                ensure_ascii=False,
            )
        )
        return

    from adapter import VieNeuTTS

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    tts = VieNeuTTS(out_dir / "_tmp", device=device, backend=backend)
    load_s = time.perf_counter() - t0
    done = []
    for s in req["segments"]:
        t0 = time.perf_counter()
        res = tts.synthesize(s["spoken"], req["voice"])
        synth_s = time.perf_counter() - t0
        dst = out_dir / f"{s['segment_id']}.wav"
        Path(res.path).replace(dst)
        done.append(
            {
                "segment_id": s["segment_id"],
                "wav": str(dst),
                "duration_s": res.duration_s,
                "synth_s": round(synth_s, 3),
            }
        )
    print(
        json.dumps(
            {"model": tts.model, "load_s": round(load_s, 3), "segments": done}, ensure_ascii=False
        )
    )


if __name__ == "__main__":
    main()
