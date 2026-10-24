"""Ghép đầu vào THẬT từ 2 spike khác vào plan, ghi vào `local/` (không commit).

- Voice: output VieNeu-TTS của spike TTS (PR #73, ADR-0004), 10 câu theo `ORDER`: câu gốc cắt
  từ `script.wav` theo `script-timings.json` (mốc từng câu); câu đổi thương hiệu và 5 câu mới
  lấy từ `local/voice-acme/` (tạo bằng `resynth_voice.py`).
- Cảnh AI: ảnh FLUX 1024×1024 do spike cảnh AI (PR #71) gọi thật qua Cloudflare.
- Ảnh khác (vấn đề): fixture tự vẽ của spike này. Chưa có quyền dùng tư liệu sản phẩm thật
  (BA #52, #67) nên không dùng ảnh/screenshot sản phẩm.

    uv run python prepare_real.py
    uv run python render.py local/plans/hoat-hinh-do-hoa.json --ratio both
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
from pathlib import Path

from make_fixtures import fixture_plan
from media import MediaError, run, tool
from presets import PRESETS

ROOT = Path(__file__).resolve().parent
LOCAL = ROOT / "local"

# Mặc định theo máy dev; đổi bằng tham số hoặc biến môi trường.
DEFAULT_TTS_DIR = Path(
    os.environ.get("P1_TTS_OUTPUT", r"D:\Code\AI-Content-Review\tts-spike-output")
)
DEFAULT_TTS_CONFIG = "vieneu-mai-anh-onnx-cpu"  # VieNeu-TTS v3 Turbo, giọng Mai Anh, ONNX/CPU
# Câu thoại gốc của spike TTS nhắc một thương hiệu thật; chưa có quyền dùng nên đổi sang
# thương hiệu giả (caption đổi ở đây, giọng tạo lại bằng resynth_voice.py).
BRAND_FROM = "Lock&Lock"
BRAND_TO = "Acme Demo"
# Video P1 dài 40–45 s (lead, 19/10) nhưng 5 câu gốc của spike TTS chỉ đọc ~22 s. Thêm 5 câu mới,
# cùng mô hình và giọng VieNeu (tổng hợp bằng resynth_voice.py), chen vào giữa 5 câu gốc. Không
# kéo dài bằng khoảng lặng hay tua chậm: độ dài video đến từ thời lượng giọng thật.
EXTRA_TEXT = {
    "x1": "Chụp ảnh, viết lời, lồng tiếng, cắt ghép, việc nào cũng tốn thời gian.",
    "x2": "Thân bình gọn nhẹ, vừa túi xách, tiện mang theo mỗi ngày.",
    "x3": "Phù hợp cho dân văn phòng, học sinh và cả những chuyến đi xa.",
    "x4": "Có nhiều màu sắc để bạn chọn, hợp với mọi phong cách và sở thích.",
    "x5": "Xem thông số chi tiết và cách sử dụng ngay trong phần mô tả bên dưới.",
}
# Thứ tự 10 câu của plan: số nguyên = câu gốc thứ i (từ 1) của script-timings.json,
# chuỗi = khoá câu mới trong EXTRA_TEXT. Vai trò và ảnh từng cảnh: make_fixtures.SCENES.
ORDER: tuple[int | str, ...] = (1, "x1", 2, "x2", 3, "x3", "x4", "x5", 4, 5)
# Hai ảnh AI thật (FLUX) đặt vào cảnh 3 ("Bình giữ nhiệt Acme Demo…") và cảnh 5 ("Nắp khóa kín…").
AI_SCENES = (2, 4)
# ROOT = <repo>/.claude/worktrees/<tên>/spikes/p1-render → <repo>/.claude/worktrees
_WORKTREES = ROOT.parents[2]
DEFAULT_AI_DIR = Path(
    os.environ.get(
        "P1_AI_SCENE_OUTPUT",
        str(_WORKTREES / "p1-ai-scene" / "spikes" / "p1-ai-scene" / "output" / "real"),
    )
)


def cut_voice(tts_dir: Path, config: str) -> list[dict]:
    """Ghép `local/voice/s{p}.wav` (p = vị trí trong plan, từ 1) theo ORDER: câu gốc thì cắt
    script.wav theo mốc câu, câu đổi thương hiệu hoặc câu mới thì chép giọng tổng hợp lại.
    Trả danh sách {text} theo thứ tự plan."""
    cfg = tts_dir / config
    timings = json.loads((cfg / "script-timings.json").read_text(encoding="utf-8"))
    out = LOCAL / "voice"
    out.mkdir(parents=True, exist_ok=True)
    lines: list[dict] = []
    for pos, entry in enumerate(ORDER, start=1):
        dest = out / f"s{pos}.wav"
        redo: Path | None = None  # giọng tổng hợp lại, nếu có
        cut: dict | None = None  # câu gốc cắt từ script.wav, nếu có
        if isinstance(entry, str):
            text = EXTRA_TEXT[entry]
            redo = LOCAL / "voice-acme" / f"{entry}.wav"
        else:
            text = timings[entry - 1]["text"]
            if BRAND_FROM in text:
                # Câu có tên thương hiệu gốc: dùng giọng tạo lại với tên giả, không dùng bản cắt.
                text = text.replace(BRAND_FROM, BRAND_TO)
                redo = LOCAL / "voice-acme" / f"s{entry}.wav"
            else:
                cut = timings[entry - 1]
        if redo is not None:
            if not redo.is_file():
                raise MediaError(
                    f"vị trí {pos} ('{text}') cần giọng tổng hợp lại: chạy resynth_voice.py "
                    f"(bằng venv của spike TTS) để tạo {redo}"
                )
            shutil.copy(redo, dest)
        elif cut is not None:
            run([
                tool("ffmpeg"), "-y", "-v", "error", "-i", str(cfg / "script.wav"),
                "-ss", f"{cut['start_s']:.3f}", "-to", f"{cut['end_s'] + 0.04:.3f}",
                "-c:a", "pcm_s16le", str(dest),
            ])  # fmt: skip
        lines.append({"text": text})
    return lines


def copy_ai_images(ai_dir: Path, count: int = 2) -> list[dict]:
    """Chép `count` ảnh AI thật (khác nhau) vào local/ai/, kèm request id của Cloudflare."""
    metas = sorted((ai_dir / "images").glob("*.json"))
    if len(metas) < count:
        raise MediaError(f"cần ≥ {count} ảnh AI trong {ai_dir / 'images'}, có {len(metas)}")
    out = LOCAL / "ai"
    out.mkdir(parents=True, exist_ok=True)
    picked = []
    for i, meta_path in enumerate(metas[:count], start=1):
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        dest = out / f"ai-{i}.{meta['ext']}"
        shutil.copy(meta_path.with_suffix(f".{meta['ext']}"), dest)
        picked.append({
            "file": dest.name, "model": meta["model"], "request_id": meta["request_id"],
            "width": meta["width"], "height": meta["height"],
        })  # fmt: skip
    (out / "SOURCES.json").write_text(json.dumps(picked, indent=2), encoding="utf-8")
    return picked


def real_plan(preset_id: str, timings: list[dict], ai: list[dict], config: str) -> dict:
    """Plan thật: 10 cảnh như fixture, thay voice/caption/ảnh AI. Đường dẫn tính từ local/plans/."""
    plan = fixture_plan(preset_id)
    scenes = plan["scenes"]
    for i, scene in enumerate(scenes):
        scene["voice"] = f"../voice/s{i + 1}.wav"
        scene["caption"] = timings[i]["text"]
        scene["min_duration_s"] = 1.5
        if scene.get("asset", "").startswith("../assets/"):
            scene["asset"] = scene["asset"].replace("../assets/", "../../assets/")
    scenes[0]["source"] = f"voice: VieNeu-TTS {config} (spike PR #73)"
    for i, img in zip(AI_SCENES, ai, strict=True):
        scene = scenes[i]
        scene.update(
            kind="image",
            asset=f"../ai/{img['file']}",
            source=f"AI thật: {img['model']}, cf-ray {img['request_id']} (spike PR #71)",
        )
    if plan.get("music"):
        plan["music"] = plan["music"].replace("../assets/", "../../assets/")
    plan["title"] = f"Thật: {PRESETS[preset_id].label} (VieNeu + FLUX)"
    return plan


def main() -> int:
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--tts-dir", type=Path, default=DEFAULT_TTS_DIR)
    parser.add_argument("--tts-config", default=DEFAULT_TTS_CONFIG)
    parser.add_argument("--ai-dir", type=Path, default=DEFAULT_AI_DIR)
    args = parser.parse_args()
    try:
        timings = cut_voice(args.tts_dir, args.tts_config)
        ai = copy_ai_images(args.ai_dir)
    except (MediaError, OSError, KeyError) as exc:
        print(f"LỖI: {exc}", file=sys.stderr)
        return 2
    plans = LOCAL / "plans"
    plans.mkdir(parents=True, exist_ok=True)
    for preset_id in PRESETS:
        text = json.dumps(real_plan(preset_id, timings, ai, args.tts_config),
                          ensure_ascii=False, indent=2)  # fmt: skip
        (plans / f"{preset_id}.json").write_text(text + "\n", encoding="utf-8")
    print(f"OK: {len(timings)} câu voice, {len(ai)} ảnh AI → {LOCAL}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
