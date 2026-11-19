"""PHẦN GỌI SPIKE #88 (HyperFrames + FFmpeg). Chạy bằng venv của spike #88.

    <p1-render-v2>/.venv/Scripts/python.exe hf_render.py --spike <p1-render-v2> \
        --plan <render-plan.json> --ratio 16:9 --quality draft --workers 3 --out <thư mục>

Dựng MỘT tỉ lệ (worker chạy hai tiến trình song song cho hai tỉ lệ). In một dòng JSON ra stdout.
Không sửa spike:
- `--quality draft|looks` đổi cờ `-q` của HyperFrames bằng cách bọc `subprocess.run` trong tiến
  trình (spike #88 cố định `looks`), như `hf_driver.py` của #95.
- Mốc 40–45 s của #77 làm `build_timeline`/`check_output` ném lỗi. Worker đặt
  P1_RENDER_MIN_TOTAL_S/MAX_TOTAL_S rộng cho tiến trình này, rồi tự kiểm mốc thật bằng ffprobe
  (báo, không kéo dài, không cắt).
- Phụ đề: #88 mỗi câu một cue và từ chối câu quá giới hạn dòng. Driver thay `render.build_ass`
  bằng bản chia câu dài thành nhiều cue (`../cues.py`, giới hạn lấy từ `subtitles.LINE_CHARS` và
  `MAX_LINES` của #88), rồi gọi `build_ass` gốc của #88 trên plan/timeline đã chia, nên kiểu ASS
  không bị chép lại.
"""

# pyright: reportMissingImports=false
from __future__ import annotations

import argparse
import dataclasses
import importlib.util
import json
import sys
from dataclasses import asdict
from pathlib import Path
from typing import Any


def _load_cues() -> Any:
    """Nạp `produce/cues.py` (chỉ thư viện chuẩn) theo đường dẫn: venv spike không có `worker`."""
    path = Path(__file__).resolve().parent.parent / "cues.py"
    spec = importlib.util.spec_from_file_location("produce_cues", path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["produce_cues"] = mod  # dataclass cần module có trong sys.modules
    spec.loader.exec_module(mod)
    return mod


def split_subtitles(
    plan: Any, tl: Any, ratio: str, subtitles: Any, cues: Any
) -> tuple[Any, Any, dict[str, int]]:
    """Plan + timeline mà mỗi câu quá dài đã được chia thành nhiều cue (id `<segment_id>#<k>`).

    Trả (plan, timeline, {segment_id: số cue} chỉ cho câu bị chia)."""
    limit = subtitles.LINE_CHARS[ratio]
    max_lines = subtitles.MAX_LINES

    def fits(text: str) -> bool:
        return len(subtitles.wrap_caption(subtitles._escape(text), limit)) <= max_lines  # noqa: SLF001

    split: dict[str, int] = {}
    new_scenes = []
    new_tl = []
    for scene, ts in zip(plan.scenes, tl.scenes, strict=True):
        segs, timed = [], []
        for seg, tseg in zip(scene.narration_segments, ts.segments, strict=True):
            texts = cues.split_caption(seg.caption, fits)
            if len(texts) <= 1:
                segs.append(seg)
                timed.append(tseg)
                continue
            split[seg.segment_id] = len(texts)
            for k, cue in enumerate(cues.time_cues(texts, tseg.start_s, tseg.end_s), 1):
                cue_id = f"{seg.segment_id}#{k}"
                segs.append(
                    seg.model_copy(update={"segment_id": cue_id, "subtitle_text": cue.text})
                )
                timed.append(
                    dataclasses.replace(
                        tseg,
                        segment_id=cue_id,
                        start_s=cue.start_s,
                        duration_s=cue.end_s - cue.start_s,
                    )
                )
        new_scenes.append(scene.model_copy(update={"narration_segments": segs}))
        new_tl.append(dataclasses.replace(ts, segments=tuple(timed)))
    return (
        plan.model_copy(update={"scenes": new_scenes}),
        dataclasses.replace(tl, scenes=tuple(new_tl)),
        split,
    )


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--spike", type=Path, required=True)
    ap.add_argument("--plan", type=Path, required=True)
    ap.add_argument("--ratio", choices=["16:9", "9:16"], required=True)
    ap.add_argument("--quality", choices=["draft", "looks"], default="looks")
    ap.add_argument("--workers", default="3")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--tag", default="")
    args = ap.parse_args()

    spike = args.spike.resolve()
    sys.path.insert(0, str(spike))
    import render as render_mod
    from plan import load_plan
    from timeline import build_timeline

    if args.quality != "looks":
        real_run = render_mod.subprocess.run

        def run_q(cmd, *a, **kw):  # noqa: ANN001, ANN002, ANN003, ANN202
            return real_run([args.quality if c == "looks" else c for c in cmd], *a, **kw)

        render_mod.subprocess.run = run_q

    import subtitles

    cues = _load_cues()
    split_log: dict[str, int] = {}
    original_build_ass = subtitles.build_ass

    def build_ass_split(plan_in: Any, tl_in: Any, ratio: str) -> str:
        plan_s, tl_s, split = split_subtitles(plan_in, tl_in, ratio, subtitles, cues)
        split_log.update(split)
        return original_build_ass(plan_s, tl_s, ratio)

    render_mod.build_ass = build_ass_split  # render.py import tên này trực tiếp

    plan = load_plan(args.plan)
    tl = build_timeline(plan, render_mod.voice_durations(plan))
    # #88 chỉ dựng phụ đề ở bước ghép cuối, sau ~4 phút chụp hình. Dựng thử trước để lỗi còn lại
    # (vd. cue vẫn quá giới hạn) hiện sau vài giây. Không bỏ chữ nào.
    build_ass_split(plan, tl, args.ratio)
    res = render_mod.render_ratio(
        plan, args.plan, tl, args.ratio, args.out, args.workers, "auto", args.tag, False, False
    )
    out = {**asdict(res), "quality": args.quality, "subtitle_cues": dict(split_log)}
    print(json.dumps(out, ensure_ascii=False))


if __name__ == "__main__":
    main()
