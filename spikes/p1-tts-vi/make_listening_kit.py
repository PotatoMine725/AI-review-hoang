"""Tạo bộ nghe mù cho phiếu chấm: python make_listening_kit.py

- Chép các clip vào output/listening/ với tên là mã ngẫu nhiên (L01.wav, L02.wav...), xáo thứ tự.
- Ghi output/listening/scoring-sheet.csv (người nghe điền 4 cột điểm 1-5) và output/answer-key.json
  (mã -> ứng viên). answer-key.json nằm NGOÀI listening/ để chia sẻ listening/ không lộ đáp án;
  chỉ mở sau khi mọi người chấm xong.
- Người điều phối KHÔNG tự chấm thay; chỉ người nghe điền điểm.

Chỉnh CONFIGS khi có thêm cấu hình (vd. Gemini sau khi có quota).
"""

from __future__ import annotations

import csv
import json
import random
import shutil
from pathlib import Path

HERE = Path(__file__).parent
OUT = HERE / "output"
KIT = OUT / "listening"
# thư mục kết quả cần đưa vào nghe. Bản PyTorch-CPU bỏ qua (cùng model với PyTorch-GPU);
# bản ONNX-CPU GIỮ vì là bản export/runtime khác, và là đường chạy khi worker không có GPU

CONFIGS = [
    "piper-vais1000-medium-cpu",
    "piper-25hours_single-low-cpu",
    "vieneu-mai-anh-pytorch-cuda",
    "vieneu-mai-anh-onnx-cpu",
    "vieneu-hải-đăng-pytorch-cuda",
]
RAW_IDS = {
    "s2-price-pct",
    "s3-million-en",
    "s6-date-money",
    "s7-decimal-range",
}  # nghe thêm bản KHÔNG chuẩn hoá
SEED = 20261016


def main() -> None:
    clips: list[tuple[str, str, str, Path]] = []  # (config, sentence_id, variant, wav)
    for cfg in CONFIGS:
        f = OUT / cfg / "results.json"
        if not f.exists():
            print(f"bỏ qua (chưa có kết quả): {cfg}")
            continue
        for s in json.loads(f.read_text(encoding="utf-8"))["samples"]:
            if s["variant"] == "norm" or s["id"] in RAW_IDS:
                clips.append((cfg, s["id"], s["variant"], Path(s["path"])))

    random.Random(SEED).shuffle(clips)
    if KIT.exists():
        shutil.rmtree(KIT)
    KIT.mkdir(parents=True)

    sentences = {
        s["id"]: s["text"]
        for s in json.loads((HERE / "sentences.json").read_text(encoding="utf-8"))["sentences"]
    }
    key: dict[str, dict[str, str]] = {}
    with (KIT / "scoring-sheet.csv").open("w", newline="", encoding="utf-8-sig") as fh:
        w = csv.writer(fh)
        w.writerow(
            [
                "clip",
                "câu (gốc)",
                "tự nhiên 1-5",
                "đúng dấu/thanh 1-5",
                "đọc số 1-5",
                "đọc tên riêng 1-5",
                "ghi chú",
            ]
        )
        for i, (cfg, sid, variant, wav) in enumerate(clips, 1):
            code = f"L{i:02d}"
            shutil.copy2(wav, KIT / f"{code}.wav")
            key[code] = {"config": cfg, "sentence": sid, "variant": variant}
            w.writerow([code, sentences[sid], "", "", "", "", ""])
    (OUT / "answer-key.json").write_text(json.dumps(key, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"{len(clips)} clip → {KIT} (đưa listening/ cho người nghe; giữ output/answer-key.json riêng)")


if __name__ == "__main__":
    main()
