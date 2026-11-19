"""CLI (chạy trong services/worker):

    uv run python -m worker.produce <script.json> --input <input.json> \\
        --assets <assets.json> --out <dir> [--mode preview|final] [--ratios 16:9,9:16] \\
        [--render-mode sequential|parallel] [--render-jobs N] [--no-cache]

Mã thoát: 0 = có MP4 (kể cả `out_of_range`, xem `status` trong render_report.json),
2 = không ra MP4.
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from worker.produce.config import ProduceConfig
from worker.produce.pipeline import produce

VALID_RATIOS = {"16:9", "9:16"}


def _ratios(value: str) -> tuple[str, ...]:
    ratios = tuple(r.strip() for r in value.split(",") if r.strip())
    if not ratios or not set(ratios) <= VALID_RATIOS or len(set(ratios)) != len(ratios):
        raise argparse.ArgumentTypeError(
            "--ratios chỉ nhận 16:9 và/hoặc 9:16, cách nhau bởi dấu phẩy"
        )
    return ratios


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m worker.produce", description=__doc__)
    ap.add_argument("script", type=Path, help="kịch bản M2 (p1-ac-03-script-vi.v1) đã sinh")
    ap.add_argument(
        "--input", type=Path, required=True, help="input.json đã dùng để sinh kịch bản (cần PKB)"
    )
    ap.add_argument(
        "--assets",
        type=Path,
        required=True,
        help="assets.json: asset_id → file (tạm, thay BE Storage)",
    )
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--mode", choices=["preview", "final"], default="preview")
    ap.add_argument("--ratios", type=_ratios, default=("16:9", "9:16"))
    ap.add_argument(
        "--on-unsupported",
        choices=["fail", "skip"],
        default="fail",
        help="cảnh M2 không có layout: fail (mặc định, không dựng) "
        "hoặc skip (bỏ cảnh đó, ghi vào report)",
    )
    ap.add_argument(
        "--render-mode",
        choices=["sequential", "parallel"],
        help="sequential = mỗi tỉ lệ một tiến trình HyperFrames; parallel = chia theo cảnh "
        "(mặc định lấy PRODUCE_RENDER_MODE)",
    )
    ap.add_argument(
        "--render-jobs",
        type=int,
        help="parallel: số tiến trình HyperFrames chạy cùng lúc (mặc định PRODUCE_RENDER_JOBS)",
    )
    ap.add_argument(
        "--no-cache",
        action="store_true",
        help="parallel: không đọc/ghi cache MP4 theo cảnh (dựng lại mọi cảnh)",
    )
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    over: dict[str, object] = {}
    if args.render_mode:
        over["render_mode"] = args.render_mode
    if args.render_jobs:
        over["render_jobs"] = args.render_jobs
    if args.no_cache:
        over["render_cache"] = False
    cfg = ProduceConfig.from_env()
    cfg = ProduceConfig.model_validate({**cfg.model_dump(), **over}) if over else cfg
    result = produce(
        args.script,
        args.input,
        args.assets,
        args.out,
        mode=args.mode,
        ratios=args.ratios,
        cfg=cfg,
        on_unsupported=args.on_unsupported,
    )
    rep = result.report
    print(f"status={rep['status']} actual_s={rep['actual_s']} report={result.report_path}")
    for o in rep["outputs"]:
        print(
            f"  {o['ratio']}: {o.get('mp4')} ({o.get('duration_s')} s, {o.get('duration_check')})"
        )
    if rep["error"]:
        print(f"  lỗi: {rep['error']['message']}", file=sys.stderr)
    return 0 if result.ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
