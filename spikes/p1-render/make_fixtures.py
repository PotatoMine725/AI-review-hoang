"""Sinh asset mẫu và plan mẫu bằng ffmpeg (tự tạo 100%, không có tư liệu sản phẩm thật).

    uv run python make_fixtures.py        # ghi assets/ và plans/

Tất cả là "fixture": ảnh vẽ bằng filter ffmpeg, voice là âm sin có nhịp, clip AI giả là nền
chuyển màu. Không dùng ảnh/screenshot sản phẩm thật (BA #52, #67). Kết quả đã commit; chạy
lại cho cùng nội dung (chỉ khác byte do bộ mã hoá).
"""

from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from media import run, tool
from presets import PRESETS

ROOT = Path(__file__).resolve().parent
ASSETS = ROOT / "assets"
PLANS = ROOT / "plans"
FONTS = ROOT / "fonts"
BOLD = "BeVietnamPro-Bold.ttf"

# Độ dài voice fixture = độ dài 10 câu thật của VieNeu theo thứ tự plan (prepare_real.ORDER:
# 5 câu gốc của script-timings.json + 5 câu mới, đo bằng ffprobe 20/10) để plan giống nhau.
# Tổng 41,08 s → timeline 42–44 s, nằm giữa mốc 40–45 s (config.py).
VOICE_S = (3.32, 4.16, 5.68, 3.28, 3.56, 3.68, 3.84, 4.08, 7.16, 2.32)

CAPTIONS = (
    "Bạn còn mất cả buổi để làm một video review?",
    "Chụp màn hình, viết lời, lồng tiếng, cắt ghép — việc nào cũng tốn thời gian.",
    "Dán link sản phẩm, AI dựng sẵn kịch bản và cảnh quay.",
    "Chọn một trong ba phong cách dựng có sẵn.",
    "Xem trước video ở cả khổ dọc lẫn khổ ngang.",
    "Mỗi video chỉ mất vài phút thay vì cả buổi.",
    "Phụ đề tiếng Việt đủ dấu, dễ đọc trên điện thoại.",
    "Tải về định dạng MP4, sẵn sàng để đăng.",
    "Tiết kiệm 390.000đ — dùng thử miễn phí ngay hôm nay!",
    "Bấm vào link để nhận ưu đãi!",
)

# 10 cảnh: (vai trò, ảnh fixture hoặc None = thẻ chữ, dùng clip AI giả ở preset điện ảnh).
# 8/10 cảnh là ảnh (zoompan + nền mờ, loại cảnh nặng nhất) nên phép đo không bị nhẹ đi.
SCENES: tuple[tuple[str, str | None, bool], ...] = (
    ("hook", None, False),
    ("problem", "problem-landscape.jpg", False),
    ("demo", "product-square.jpg", True),  # phủ nhánh kind=video bằng clip AI giả
    ("demo", "result-portrait.jpg", False),
    ("demo", "product-square.jpg", False),
    ("result", "result-portrait.jpg", False),
    ("result", "problem-landscape.jpg", False),
    ("proof", "product-square.jpg", False),
    ("result", "result-portrait.jpg", False),
    ("cta", None, False),
)
IMAGE_SOURCE = {
    "problem-landscape.jpg": "fixture: ảnh tự vẽ bằng ffmpeg (make_fixtures.py)",
    "product-square.jpg": "fixture: ảnh sản phẩm tự vẽ, vuông 1:1 như ảnh FLUX",
    "result-portrait.jpg": "fixture: ảnh tự vẽ bằng ffmpeg",
}


def _ffmpeg(*args: str, cwd: Path | None = None) -> None:
    run([tool("ffmpeg"), "-y", "-v", "error", *args], cwd=cwd)


def _text(tmp: Path, name: str, text: str) -> str:
    """Ghi chữ ra file nhỏ để drawtext đọc (tránh phải escape dấu : , ' trong filter)."""
    path = tmp / f"{name}.txt"
    path.write_text(text, encoding="utf-8")
    return path.name  # tương đối: ffmpeg chạy với cwd = tmp


def _drawtext(tmp: Path, name: str, text: str, size: int, color: str, y: str) -> str:
    # fontfile và textfile tương đối: ffmpeg chạy với cwd = tmp (tránh escape ổ đĩa Windows)
    return (
        f"drawtext=fontfile={BOLD}:textfile={_text(tmp, name, text)}:fontsize={size}"
        f":fontcolor={color}:x=(w-text_w)/2:y={y}"
    )


def make_images(tmp: Path) -> None:
    out = ASSETS / "img"
    out.mkdir(parents=True, exist_ok=True)
    jpg = ["-frames:v", "1", "-q:v", "4"]

    # 1) Ảnh ngang 16:9-ish (1600×900): giả bước "vấn đề" (quy trình thủ công).
    vf = (
        "gradients=s=1600x900:c0=0x1e3a8a:c1=0x0ea5e9:x0=0:y0=0:x1=1600:y1=900:d=1:r=1,"
        "drawbox=x=140:y=150:w=1320:h=600:color=white@0.92:t=fill,"
        "drawbox=x=140:y=150:w=1320:h=70:color=0x1e293b:t=fill,"
        "drawbox=x=200:y=280:w=720:h=34:color=0x94a3b8:t=fill,"
        "drawbox=x=200:y=350:w=980:h=34:color=0xcbd5e1:t=fill,"
        "drawbox=x=200:y=420:w=860:h=34:color=0xcbd5e1:t=fill,"
        "drawbox=x=200:y=490:w=940:h=34:color=0xcbd5e1:t=fill,"
        + _drawtext(tmp, "p1", "ẢNH MẪU TỰ TẠO (fixture)", 54, "0x1e293b", "600")
    )
    _ffmpeg("-f", "lavfi", "-i", vf, *jpg, str(out / "problem-landscape.jpg"), cwd=tmp)

    # 2) Ảnh vuông 1:1 (1200×1200): "sản phẩm" vẽ bằng hình khối (giống tỉ lệ ảnh FLUX 1024²).
    vf = (
        "gradients=s=1200x1200:c0=0xfde68a:c1=0xfb923c:x0=0:y0=0:x1=1200:y1=1200:d=1:r=1,"
        "drawbox=x=420:y=130:w=360:h=110:color=0x0f172a:t=fill,"
        "drawbox=x=360:y=240:w=480:h=800:color=0x0d9488:t=fill,"
        "drawbox=x=400:y=420:w=400:h=320:color=white@0.95:t=fill,"
        + _drawtext(tmp, "p2", "SẢN PHẨM MẪU", 52, "0x0f172a", "540")
        + ","
        + _drawtext(tmp, "p2b", "(fixture, tự vẽ)", 36, "0x334155", "610")
    )
    _ffmpeg("-f", "lavfi", "-i", vf, *jpg, str(out / "product-square.jpg"), cwd=tmp)

    # 3) Ảnh dọc (900×1600): "kết quả" trước/sau bằng cột.
    vf = (
        "color=c=0x10b981:s=900x1600:d=1:r=1,"
        "drawbox=x=0:y=0:w=900:h=800:color=0x059669@0.6:t=fill,"
        "drawbox=x=170:y=1000:w=200:h=360:color=0xfca5a5:t=fill,"
        "drawbox=x=530:y=1180:w=200:h=180:color=white:t=fill,"
        + _drawtext(tmp, "p3b", "ẢNH MẪU TỰ TẠO (fixture)", 46, "white", "260")
        + ","
        + _drawtext(tmp, "p3a", "TRƯỚC          SAU", 44, "white", "1390")
    )
    _ffmpeg("-f", "lavfi", "-i", vf, *jpg, str(out / "result-portrait.jpg"), cwd=tmp)


def make_clip(tmp: Path) -> None:
    out = ASSETS / "clip"
    out.mkdir(parents=True, exist_ok=True)
    # Clip "AI giả" 4 s, 16:9 (nền chuyển màu): đại diện clip do model video sinh (kind = video).
    vf = "gradients=s=1280x720:r=30:d=4:c0=0x7c3aed:c1=0x06b6d4:speed=0.08," + _drawtext(
        tmp, "clip", "CLIP AI GIẢ (fixture)", 56, "white", "60"
    )
    _ffmpeg(
        "-f", "lavfi", "-i", vf, "-c:v", "libx264", "-crf", "32", "-preset", "veryfast",
        "-pix_fmt", "yuv420p", "-an", str(out / "fake-ai-clip.mp4"), cwd=tmp,
    )  # fmt: skip


def make_audio() -> None:
    voice = ASSETS / "voice"
    voice.mkdir(parents=True, exist_ok=True)
    for i, dur in enumerate(VOICE_S, start=1):
        # Âm sin nhịp 4 Hz, cao độ khác nhau từng câu: nghe được, không phải giọng người.
        src = f"sine=f={200 + 30 * i}:d={dur}:r=24000,tremolo=f=4:d=0.7,volume=0.35"
        _ffmpeg("-f", "lavfi", "-i", src, "-ac", "1", "-c:a", "aac", "-b:a", "48k",
                str(voice / f"s{i}.m4a"))  # fmt: skip
    music = ASSETS / "music"
    music.mkdir(parents=True, exist_ok=True)
    chord = "0.2*sin(2*PI*196*t)+0.15*sin(2*PI*247*t)+0.15*sin(2*PI*294*t)"
    _ffmpeg("-f", "lavfi", "-i", f"aevalsrc='{chord}':d=12:s=24000", "-ac", "1",
            "-c:a", "aac", "-b:a", "48k", str(music / "pad.m4a"))  # fmt: skip


def fixture_plan(preset_id: str) -> dict:
    """Plan 10 cảnh Hook → Problem → Demo → Result → Proof → CTA (`SCENES`). Đường dẫn tính từ
    plans/."""
    cinematic = preset_id == "dien-anh-toi-gian"  # phủ nhánh kind=video bằng clip AI giả
    scenes: list[dict] = []
    for i, (role, image, clip) in enumerate(SCENES):
        scene: dict = {"role": role}
        if image is None:
            scene["kind"] = "text_card"
        elif clip and cinematic:
            scene |= {"kind": "video", "asset": "../assets/clip/fake-ai-clip.mp4"}
        else:
            scene |= {"kind": "image", "asset": f"../assets/img/{image}"}
        scene |= {"caption": CAPTIONS[i], "voice": f"../assets/voice/s{i + 1}.m4a"}
        if image is None:
            scene["min_duration_s"] = 2.5 if role == "hook" else 2.0
        elif clip and cinematic:
            scene["source"] = "fixture: clip AI giả (gradients + chữ)"
        else:
            scene["source"] = IMAGE_SOURCE[image]
        scenes.append(scene)
    plan: dict = {
        "title": f"Fixture {PRESETS[preset_id].label}",
        "preset": preset_id,
        "language": "vi",
        "scenes": scenes,
    }
    if preset_id == "co-dien":  # phủ nhánh nhạc nền + sidechain
        plan["music"] = "../assets/music/pad.m4a"
    return plan


def make_plans() -> None:
    PLANS.mkdir(exist_ok=True)
    for preset_id in PRESETS:
        text = json.dumps(fixture_plan(preset_id), ensure_ascii=False, indent=2)
        (PLANS / f"{preset_id}.json").write_text(text + "\n", encoding="utf-8")

    invalid = PLANS / "invalid"
    invalid.mkdir(exist_ok=True)

    def card(role: str, seconds: float) -> dict:
        return {
            "role": role,
            "kind": "text_card",
            "caption": "Thẻ chữ thử độ dài",
            "min_duration_s": seconds,
        }

    cases = {
        # 3 × 12 s − 2 × 0,3 s = 35,4 s (< 40 s): phải báo lỗi "ngắn hơn mức tối thiểu"
        "too-short": [card("hook", 12), card("demo", 12), card("cta", 12)],
        # 3 × 16 s − 2 × 0,3 s = 47,4 s (> 45 s): phải báo lỗi "vượt mức tối đa"
        "too-long": [card("hook", 16), card("demo", 16), card("cta", 16)],
    }
    for name, scenes in cases.items():
        plan = {"title": f"Plan lỗi: {name}", "preset": "co-dien", "language": "vi",
                "scenes": scenes}  # fmt: skip
        (invalid / f"{name}.json").write_text(
            json.dumps(plan, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="fx-") as t:
        tmp = Path(t)
        shutil.copy(FONTS / BOLD, tmp / BOLD)
        make_images(tmp)
        make_clip(tmp)
    make_audio()
    make_plans()
    print("OK: assets/ và plans/ đã sinh.")


if __name__ == "__main__":
    main()
