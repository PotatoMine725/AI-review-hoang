"""Test dùng ffmpeg thật (tự bỏ qua nếu thiếu): CLI báo lỗi plan sai, dựng 1 video fixture."""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from config import load_limits
from media import probe_video
from render import main
from render_plan import RenderPlan, Scene, load_plan
from renderer import DURATION_TOLERANCE_S, render

ROOT = Path(__file__).resolve().parent.parent
needs_ffmpeg = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="thiếu ffmpeg/ffprobe",
)


@needs_ffmpeg
@pytest.mark.parametrize("name", ["too-short", "too-long"])
def test_cli_rejects_out_of_range_plan_without_output(name: str, tmp_path: Path, capsys) -> None:
    code = main([str(ROOT / "plans" / "invalid" / f"{name}.json"), "--out-dir", str(tmp_path)])
    assert code == 2
    assert "LỖI" in capsys.readouterr().err
    assert list(tmp_path.glob("*.mp4")) == []  # lỗi trước khi chạy ffmpeg


@needs_ffmpeg
@pytest.mark.parametrize("ratio,size", [("9:16", (1080, 1920)), ("16:9", (1920, 1080))])
def test_render_fixture_plan(ratio: str, size: tuple[int, int], tmp_path: Path) -> None:
    # dien-anh-toi-gian phủ nhánh kind=video (clip AI giả), letterbox, vignette, fadeblack
    plan = load_plan(ROOT / "plans" / "dien-anh-toi-gian.json")
    res = render(plan, ratio, tmp_path / "o.mp4")  # type: ignore[arg-type]
    info = probe_video(res.path)
    assert (info.width, info.height) == size
    assert info.video_codec == "h264" and info.audio_codec == "aac"
    limits = load_limits()  # 40–45 s; renderer v2 đọc cùng cấu hình này
    assert limits.min_total_s <= info.duration_s <= limits.max_total_s + DURATION_TOLERANCE_S
    assert res.max_rss_mb is None or res.max_rss_mb > 0


def _card_plan(count: int, each_s: float) -> RenderPlan:
    """`count` thẻ chữ, mỗi cảnh một câu voice fixture (s10, 2.3 s) và dài `each_s`."""
    voice = str(ROOT / "assets" / "voice" / "s10.m4a")
    scenes = [
        Scene(role="hook" if i == 0 else "demo", kind="text_card", caption="Thẻ chữ thử độ dài",
              voice=voice, min_duration_s=each_s)
        for i in range(count)
    ]  # fmt: skip
    return RenderPlan(title="t", preset="co-dien", scenes=scenes)


@needs_ffmpeg
@pytest.mark.parametrize("count,each_s", [(1, 42.0), (12, 3.8)])
def test_render_one_and_twelve_scene_plans(count: int, each_s: float, tmp_path: Path) -> None:
    """Số cảnh chỉ bị chặn ở 1–12 (không chặn theo độ dài); dựng thật để chắc filter graph chạy
    được ở hai đầu (1 cảnh không có xfade nào, 12 cảnh là trần)."""
    res = render(_card_plan(count, each_s), "16:9", tmp_path / "o.mp4")
    assert len(res.timeline.scenes) == count
    limits = load_limits()
    lo, hi = limits.min_total_s, limits.max_total_s
    assert lo - DURATION_TOLERANCE_S <= res.info.duration_s <= hi + DURATION_TOLERANCE_S
