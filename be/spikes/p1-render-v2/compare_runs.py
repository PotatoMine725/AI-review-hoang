"""Kiểm tính tất định: hai lần render cùng đầu vào phải cho cùng khung hình.

    uv run python compare_runs.py <run1.mp4> <run2.mp4>
    uv run python compare_runs.py a.mp4 b.mp4 --every 30      # so 1 khung mỗi giây (mặc định)

So MD5 của khung ĐÃ GIẢI MÃ (ffmpeg -f framemd5), không so hash file MP4: hash file đổi theo
metadata/muxer dù hình giống hệt, nên không chứng minh được gì về khung hình.
Ghi kết quả vào results/determinism.json.
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime
from pathlib import Path

from media import run, tool

ROOT = Path(__file__).resolve().parent


def frame_md5(video: Path, every: int) -> dict[int, str]:
    """{chỉ số khung: md5} cho các khung chia hết cho `every` (chỉ luồng hình)."""
    proc = run([
        tool("ffmpeg"), "-v", "error", "-i", str(video), "-map", "0:v:0",
        "-vf", f"select='not(mod(n\\,{every}))'", "-fps_mode", "passthrough",
        "-f", "framemd5", "-",
    ])  # fmt: skip
    out: dict[int, str] = {}
    lines = [x for x in proc.stdout.splitlines() if x and not x.startswith("#")]
    for i, line in enumerate(lines):
        out[i * every] = line.split(",")[-1].strip()
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("a", type=Path)
    ap.add_argument("b", type=Path)
    ap.add_argument("--every", type=int, default=30)
    args = ap.parse_args()
    a, b = frame_md5(args.a, args.every), frame_md5(args.b, args.every)
    same = [n for n in a if a[n] == b.get(n)]
    diff = [n for n in a if a[n] != b.get(n)]
    print(f"{len(same)}/{len(a)} khung giống nhau (mỗi {args.every} khung); khác: {diff[:20]}")
    if len(a) != len(b):
        print(f"số khung khác nhau: {len(a)} và {len(b)}")
    path = ROOT / "results" / "determinism.json"
    path.parent.mkdir(exist_ok=True)
    data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else []
    data.append({
        "at": datetime.now().isoformat(timespec="seconds"), "a": args.a.name, "b": args.b.name,
        "every": args.every, "compared": len(a), "same": len(same), "diff_frames": diff,
        "sample": {str(n): a[n] for n in list(a)[:5]},
    })  # fmt: skip
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
