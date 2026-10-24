"""Dòng lệnh: dựng 1 render plan thành MP4.

uv run python render.py plans/hoat-hinh-do-hoa.json --ratio 9:16
uv run python render.py plans/co-dien.json --ratio both --encoder nvenc
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from config import ConfigError
from graph import Encoder
from media import MediaError
from presets import RATIOS, Ratio
from render_plan import PlanError, load_plan
from renderer import ROOT, render


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dựng render plan thành MP4 (FFmpeg).")
    parser.add_argument("plan", type=Path, help="file plan JSON")
    parser.add_argument("--ratio", choices=[*RATIOS, "both"], default="both")
    parser.add_argument("--encoder", choices=["cpu", "nvenc", "qsv"], default="cpu")
    parser.add_argument("--out", type=Path, help="file đầu ra (chỉ khi chọn 1 tỉ lệ)")
    parser.add_argument("--out-dir", type=Path, default=ROOT / "output", help="thư mục đầu ra")
    parser.add_argument("--verbose", action="store_true", help="ffmpeg -v verbose, ghi .log")
    args = parser.parse_args(argv)

    ratios: list[Ratio] = list(RATIOS) if args.ratio == "both" else [args.ratio]
    if args.out and len(ratios) > 1:
        parser.error("--out chỉ dùng được với một tỉ lệ")
    encoder: Encoder = args.encoder
    try:
        plan = load_plan(args.plan)
        for ratio in ratios:
            name = f"{args.plan.stem}-{ratio.replace(':', 'x')}"
            out = args.out or args.out_dir / f"{name}.mp4"
            res = render(plan, ratio, out, encoder=encoder, verbose=args.verbose)
            i = res.info
            print(
                f"OK {out}  {i.width}x{i.height} {i.duration_s:.2f}s {i.size_bytes / 1e6:.2f}MB"
                f"  ffmpeg {res.ffmpeg_wall_s:.1f}s ({encoder})"
            )
    except (PlanError, MediaError, ConfigError, KeyError) as exc:
        print(f"LỖI: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
