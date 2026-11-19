"""In bảng số đo (markdown) từ output/*/results.json. Chỉ dùng thư viện chuẩn: python summarize.py"""

from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).parent / "output"


def main() -> None:
    rows = []
    for f in sorted(OUT.glob("*/results.json")):
        d = json.loads(f.read_text(encoding="utf-8"))
        # RTF chỉ tính trên variant "norm" để so sánh công bằng giữa các cấu hình
        norm = [s for s in d["samples"] if s["variant"] == "norm"]
        gen, audio = sum(s["gen_s"] for s in norm), sum(s["audio_s"] for s in norm)
        # VRAM: ưu tiên số của torch; không thì chênh lệch nvidia-smi trước/sau khi chạy (chỉ khi dùng GPU)
        on_gpu = d.get("meta", {}).get("device") != "cpu"
        base, peak = d.get("vram_baseline_mb"), d.get("vram_peak_mb")
        vram = d.get("vram_torch_peak_mb") or (peak - base if on_gpu and base is not None and peak else None)
        rows.append(
            (
                f.parent.name,
                f"{gen / audio:.2f}" if audio else "?",
                f"{max(s['rtf'] for s in norm):.2f}",
                f"{d['peak_ram_mb']:.0f}" if d.get("peak_ram_mb") else "?",
                f"{vram:.0f}" if vram else "-",
                f"{audio:.1f}",
            )
        )
    print("| Cấu hình | RTF (tổng) | RTF xấu nhất | RAM đỉnh (MB) | VRAM đỉnh (MB) | Audio (s, 9 câu) |")
    print("|---|---|---|---|---|---|")
    for r in rows:
        print("| " + " | ".join(r) + " |")


if __name__ == "__main__":
    main()
