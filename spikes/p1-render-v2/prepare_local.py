"""Chép đầu vào thật vào local/ (không commit): clip tự quay và ảnh AI FLUX (#71) của demo
PDFCraft (#78). In SHA-256 để biết chạy lại có cùng đầu vào không.

Voice KHÔNG chép từ #78 (mốc 15–25 s cũ): giọng 40–45 s sinh thẳng vào local/voice-40-45/ bằng
CLI của #73, xem tts_input.py. In SHA-256 của các wav đó nếu đã có.

    uv run python prepare_local.py
    uv run python prepare_local.py --demo <thư mục spikes/p1-demo-pdfcraft> --refs <_refs>
"""

from __future__ import annotations

import argparse
import hashlib
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DEFAULT_DEMO = Path(
    r"D:\Code\AI-Content-Review\AI-review-BE\.claude\worktrees\p1-demo-pdfcraft\spikes\p1-demo-pdfcraft"
)
DEFAULT_REFS = Path(r"D:\Code\AI-Content-Review\_refs")


def files(demo: Path, refs: Path) -> list[tuple[Path, Path]]:
    clips = refs / "assets" / "pdfcraft"
    pairs = []
    for name in ("pdfcraft-pagenum", "pdfcraft-word-export", "pdfcraft-word-result",
                 "pdfcraft-merge"):  # fmt: skip
        pairs.append((clips / f"{name}.mp4", ROOT / "local" / "clips" / f"{name}.mp4"))
    ai = "paperwork-s1.jpg"
    pairs.append((demo / "local" / "ai" / ai, ROOT / "local" / "ai" / ai))
    return pairs


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", type=Path, default=DEFAULT_DEMO)
    ap.add_argument("--refs", type=Path, default=DEFAULT_REFS)
    args = ap.parse_args()
    for src, dst in files(args.demo, args.refs):
        if not src.exists():
            raise SystemExit(f"thiếu {src}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dst)
        digest = hashlib.sha256(dst.read_bytes()).hexdigest()[:16]
        print(f"{digest}  {dst.relative_to(ROOT).as_posix()}")
    for wav in sorted((ROOT / "local" / "voice-40-45").glob("s*.wav")):
        digest = hashlib.sha256(wav.read_bytes()).hexdigest()[:16]
        print(f"{digest}  {wav.relative_to(ROOT).as_posix()}")


if __name__ == "__main__":
    main()
