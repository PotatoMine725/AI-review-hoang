"""Plan → đầu vào cho CLI sinh giọng của #73 (`vieneu/synth_segments.py`).

    uv run python tts_input.py plans/pdfcraft-40-45s.json      # ghi local/voice-40-45/segments.json
    # rồi chạy bằng venv của spike TTS (vieneu không phải dependency của spike này):
    <p1-tts-vi>/vieneu/.venv/Scripts/python.exe synth_segments.py <đường dẫn segments.json> \
        --device cpu --backend onnx --voice "Mai Anh" --out-dir <thư mục spike>/local/voice-40-45

CLI #73 đặt tên s01.wav, s02.wav... theo thứ tự câu, nên `voice` của câu thứ i trong plan phải là
<thư mục>/s{i:02d}.wav. Script kiểm điều này trước khi xuất.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path, PurePosixPath

from plan import PlanError, RenderPlan, load_plan

ROOT = Path(__file__).resolve().parent


def segments_for_tts(plan: RenderPlan) -> tuple[str, list[dict[str, str]]]:
    """Trả (thư mục voice, danh sách {"text"} theo thứ tự đọc)."""
    segs = [g for s in plan.scenes for g in s.narration_segments]
    folders = {str(PurePosixPath(g.voice).parent) for g in segs}
    if len(folders) != 1:
        raise PlanError(f"mọi voice phải nằm chung một thư mục, thấy {sorted(folders)}")
    for i, g in enumerate(segs, start=1):
        if PurePosixPath(g.voice).name != f"s{i:02d}.wav":
            raise PlanError(f"{g.segment_id}: voice phải là s{i:02d}.wav (thứ tự đọc): {g.voice}")
    return folders.pop(), [{"text": g.text} for g in segs]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("plan", type=Path)
    args = ap.parse_args()
    folder, segments = segments_for_tts(load_plan(args.plan))
    out = ROOT / folder / "segments.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    body = json.dumps({"segments": segments}, ensure_ascii=False, indent=2)
    out.write_text(body, encoding="utf-8")
    print(f"{len(segments)} câu → {out}")


if __name__ == "__main__":
    main()
