"""Dựng 1 tỉ lệ bằng FFmpeg (#77) cho bench P1-07, có thể ở 720p. Chạy bằng venv của spike #77.

    <p1-render>/.venv/Scripts/python.exe ff_driver.py --spike <p1-render> \
        --plan local/plans/dien-anh-toi-gian.json --ratio 16:9 --res 720 --out <file.mp4>

Với 720p: gán lại `FRAME_SIZE` ở `graph` và `renderer` trong tiến trình (không sửa file của spike).
`subtitles.FRAME_SIZE` giữ 1080p để PlayRes của ASS không đổi, libass tự co về 720p.
In 1 dòng JSON ra stdout.
"""

# pyright: reportMissingImports=false
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spike", type=Path, required=True)
    ap.add_argument("--plan", type=Path, required=True)
    ap.add_argument("--ratio", choices=["16:9", "9:16"], required=True)
    ap.add_argument("--res", choices=["1080", "720"], default="1080")
    ap.add_argument("--encoder", choices=["cpu", "nvenc", "qsv"], default="cpu")
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    spike = args.spike.resolve()
    sys.path.insert(0, str(spike))
    import graph  # noqa: PLC0415
    import renderer  # noqa: PLC0415
    from render_plan import load_plan  # noqa: PLC0415

    if args.res == "720":
        small = {"16:9": (1280, 720), "9:16": (720, 1280)}
        graph.FRAME_SIZE = small  # type: ignore[attr-defined]
        renderer.FRAME_SIZE = small  # type: ignore[attr-defined]

    plan_path = args.plan if args.plan.is_absolute() else spike / args.plan
    plan = load_plan(plan_path)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()
    res = renderer.render(plan, args.ratio, args.out, encoder=args.encoder)
    wall = time.perf_counter() - t0
    i = res.info
    print(
        json.dumps(
            {
                "ratio": args.ratio,
                "res": args.res,
                "encoder": args.encoder,
                "output": str(args.out),
                "ffmpeg_wall_s": round(res.ffmpeg_wall_s, 2),
                "cpu_s": res.cpu_s,
                "max_rss_mb": res.max_rss_mb,
                "total_wall_s": round(wall, 2),
                "width": i.width,
                "height": i.height,
                "duration_s": round(i.duration_s, 2),
                "size_mb": round(i.size_bytes / 1e6, 2),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
