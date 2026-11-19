"""Dựng 1 tỉ lệ bằng HyperFrames (#88) cho bench P1-07, có thể ở 720p. Chạy bằng venv của spike #88.

    <p1-render-v2>/.venv/Scripts/python.exe hf_driver.py --spike <p1-render-v2> \
        --plan plans/pdfcraft-40-45s.json --ratio 16:9 --res 720 --out <scratch> --tag t1

HyperFrames 0.8.173 CLI không có tuỳ chọn kích thước/scale/viewport (đã kiểm `render --help`):
kích thước nằm trong `data-width/data-height` của composition và CSS px cố định của template.
Với 720p driver KHÔNG sửa file của spike mà làm trong tiến trình:
  - `compose.FRAME_SIZE` và `render.FRAME_SIZE` → 1280x720 / 720x1280 (composition + kiểm đầu ra);
  - bọc `render.compose` để thêm `#root { transform: scale(2/3) }` vào index.html đã sinh;
  - `subtitles.FRAME_SIZE` GIỮ NGUYÊN 1080p: ASS có PlayRes 1080p nên libass tự co về 720p.
In 1 dòng JSON ra stdout. Không ghi results/ của spike.
"""

# pyright: reportMissingImports=false
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spike", type=Path, required=True)
    ap.add_argument("--plan", type=Path, required=True)
    ap.add_argument("--ratio", choices=["16:9", "9:16"], required=True)
    ap.add_argument("--res", choices=["1080", "720"], default="1080")
    ap.add_argument("--workers", default="auto")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--tag", default="")
    ap.add_argument(
        "--quality", choices=["draft", "looks"], default="looks", help="cờ -q của HyperFrames"
    )
    args = ap.parse_args()

    spike = args.spike.resolve()
    sys.path.insert(0, str(spike))
    import compose as compose_mod  # noqa: PLC0415
    import render as render_mod  # noqa: PLC0415
    from plan import load_plan  # noqa: PLC0415
    from timeline import build_timeline  # noqa: PLC0415

    if args.res == "720":
        small = {"16:9": (1280, 720), "9:16": (720, 1280)}
        compose_mod.FRAME_SIZE = small  # type: ignore[attr-defined]
        render_mod.FRAME_SIZE = small  # type: ignore[attr-defined]
        orig_compose = render_mod.compose

        def zoomed(plan, tl, ratio, work, clip_cache):  # noqa: ANN001, ANN202
            index = orig_compose(plan, tl, ratio, work, clip_cache)
            html = Path(index).read_text(encoding="utf-8")
            html = html.replace("</head>", "<style>#root{zoom:0.666667}</style>\n</head>", 1)
            Path(index).write_text(html, encoding="utf-8")
            return index

        render_mod.compose = zoomed  # type: ignore[assignment]

    if args.quality != "looks":
        real_run = render_mod.subprocess.run

        def run_q(cmd, *a, **kw):  # noqa: ANN001, ANN002, ANN003, ANN202
            cmd = [args.quality if c == "looks" else c for c in cmd]
            return real_run(cmd, *a, **kw)

        render_mod.subprocess.run = run_q  # type: ignore[assignment]

    plan_path = args.plan if args.plan.is_absolute() else spike / args.plan
    plan = load_plan(plan_path)
    tl = build_timeline(plan, render_mod.voice_durations(plan))
    res = render_mod.render_ratio(plan, plan_path, tl, args.ratio, args.out, args.workers,
                                  "auto", args.tag, False, False)  # fmt: skip
    info = render_mod.probe_video(Path(res.output))
    print(
        json.dumps(
            {
                **asdict(res),
                "res": args.res,
                "quality": args.quality,
                "width": info.width,
                "height": info.height,
                "size_mb": round(Path(res.output).stat().st_size / 1e6, 2),
            },
            ensure_ascii=False,
        )
    )


if __name__ == "__main__":
    main()
