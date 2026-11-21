"""Test logic thuần (timeline, phụ đề, dựng lệnh): không cần ffmpeg."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from config import ENV_MAX, ENV_MIN, ConfigError, RenderLimits, load_limits
from graph import build_command
from media import MediaError, VideoInfo
from presets import PRESETS
from render_plan import PlanError, RenderPlan, Scene
from renderer import check_output
from subtitles import build_ass, chunk_caption, split_times
from timeline import build_timeline

# Độ dài 10 câu thật của VieNeu theo thứ tự plan (5 câu gốc script-timings.json + 5 câu mới,
# đo bằng ffprobe 20/10): tổng 41.08 s.
REAL_VOICE_S = [3.32, 4.16, 5.68, 3.28, 3.56, 3.68, 3.84, 4.08, 7.16, 2.32]
SENTENCE = "Tiết kiệm 390.000đ — dùng thử miễn phí ngay hôm nay!"
ROLES = ["hook", "problem", "demo", "demo", "demo", "result", "result", "proof", "result", "cta"]


def make_plan(preset: str, durations: list[float], min_s: float = 1.5) -> RenderPlan:
    scenes = [
        Scene(
            role=role,  # type: ignore[arg-type]
            kind="text_card",
            caption=SENTENCE,
            voice=f"v{i}.wav",
            min_duration_s=min_s,
        )
        for i, role in enumerate(ROLES[: len(durations)])
    ]
    return RenderPlan(title="t", preset=preset, scenes=scenes)


def fake_duration(durations: list[float]):
    table = {f"v{i}.wav": d for i, d in enumerate(durations)}
    return lambda p: table[Path(p).name]


def cards(durations: list[float], preset_id: str = "co-dien") -> RenderPlan:
    """Plan toàn thẻ chữ không voice: thời lượng cảnh = `min_duration_s` (chính xác theo khung)."""
    scenes = [
        Scene(role="hook" if i == 0 else "demo", kind="text_card", caption="Thẻ chữ",
              min_duration_s=d)
        for i, d in enumerate(durations)
    ]  # fmt: skip
    return RenderPlan(title="t", preset=preset_id, scenes=scenes)


def total_of(durations: list[float], preset_id: str = "co-dien") -> float:
    return build_timeline(cards(durations, preset_id), PRESETS[preset_id]).total_s


@pytest.mark.parametrize("preset_id", list(PRESETS))
def test_real_voice_fits_default_window(preset_id: str) -> None:
    limits = load_limits()
    tl = build_timeline(
        make_plan(preset_id, REAL_VOICE_S), PRESETS[preset_id], fake_duration(REAL_VOICE_S)
    )
    assert (limits.min_total_s, limits.max_total_s) == (40.0, 45.0)
    assert limits.min_total_s <= tl.total_s <= limits.max_total_s
    # cảnh nối khít: cảnh sau bắt đầu trước khi cảnh trước hết đúng bằng thời gian chuyển cảnh
    for a, b in zip(tl.scenes, tl.scenes[1:], strict=False):
        assert b.start_s == pytest.approx(a.end_s - tl.transition_s, abs=1e-6)
    # voice không bao giờ vượt quá cảnh của nó
    assert all(s.voice_start_s + s.voice_s <= s.end_s + 1e-6 for s in tl.scenes)
    # chuyển cảnh chồng đúng một lần: tổng = Σ thời lượng cảnh − (n−1)·chuyển cảnh
    n = len(tl.scenes)
    assert tl.total_s == pytest.approx(
        sum(s.duration_s for s in tl.scenes) - (n - 1) * tl.transition_s, abs=1e-6
    )


# 1 khung = 1/30 s: 39.96 s làm tròn lên 1199 khung = 39.9667 s (dưới 40 một khung);
# 45.03 s làm tròn lên 1351 khung = 45.0333 s (trên 45 một khung).
@pytest.mark.parametrize(
    "seconds,expected",
    [(20.0, "ngắn hơn mức tối thiểu 40"), (39.96, "ngắn hơn mức tối thiểu 40"),
     (45.03, "vượt mức tối đa 45"), (60.0, "vượt mức tối đa 45")],
)  # fmt: skip
def test_plan_outside_40_45_raises_clear_error(seconds: float, expected: str) -> None:
    with pytest.raises(PlanError, match=expected):
        total_of([seconds])


@pytest.mark.parametrize("seconds,total", [(40.0, 40.0), (42.5, 42.5), (45.0, 45.0)])
def test_plan_at_and_inside_the_bounds_is_accepted(seconds: float, total: float) -> None:
    assert total_of([seconds]) == pytest.approx(total, abs=1e-9)


def test_exact_bounds_with_transitions_are_not_rejected_by_float_error() -> None:
    # 2 cảnh co-dien (chuyển cảnh 0,3 s): 20 + 20,3 − 0,3 = 40 s và 22,5 + 22,8 − 0,3 = 45 s
    assert total_of([20.0, 20.3]) == pytest.approx(40.0, abs=1e-9)
    assert total_of([22.5, 22.8]) == pytest.approx(45.0, abs=1e-9)


@pytest.mark.parametrize("count,each", [(1, 42.0), (2, 22.0), (12, 3.8)])
def test_scene_count_from_1_to_12_is_limited_only_by_total_duration(
    count: int, each: float
) -> None:
    durations = [each] * count
    assert 40 <= total_of(durations) <= 45


def test_scene_count_outside_1_to_12_is_a_schema_error() -> None:
    with pytest.raises(ValidationError):
        cards([3.5] * 13)
    with pytest.raises(ValidationError):
        RenderPlan(title="t", preset="co-dien", scenes=[])


def test_limits_are_read_from_one_place_and_can_be_overridden(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert load_limits() == RenderLimits(40.0, 45.0)
    with pytest.raises(PlanError, match="ngắn hơn mức tối thiểu 40"):
        total_of([20.0])
    monkeypatch.setenv(ENV_MIN, "15")
    monkeypatch.setenv(ENV_MAX, "25")
    assert load_limits() == RenderLimits(15.0, 25.0)
    assert total_of([20.0]) == pytest.approx(20.0)  # cùng plan, mốc mới: hợp lệ
    with pytest.raises(PlanError, match="vượt mức tối đa 25"):
        total_of([42.0])
    # tham số `limits` ưu tiên hơn môi trường
    tl = build_timeline(cards([42.0]), PRESETS["co-dien"], limits=RenderLimits(40.0, 45.0))
    assert tl.total_s == pytest.approx(42.0)


@pytest.mark.parametrize(
    "env",
    [{ENV_MIN: "50", ENV_MAX: "40"}, {ENV_MIN: "abc"}, {ENV_MAX: "0"}, {ENV_MIN: "nan"}],
)
def test_bad_limits_are_rejected(env: dict[str, str]) -> None:
    with pytest.raises(ConfigError):
        load_limits(env)


def make_info(duration_s: float) -> VideoInfo:
    return VideoInfo(
        width=1920, height=1080, fps=30.0, duration_s=duration_s,
        video_codec="h264", audio_codec="aac", size_bytes=1,
    )  # fmt: skip


def check_mp4(tl_seconds: float, probed_s: float, limits: RenderLimits | None = None) -> None:
    tl = build_timeline(cards([tl_seconds]), PRESETS["co-dien"], limits=limits)
    check_output(make_info(probed_s), "16:9", tl, limits)


def test_final_mp4_duration_must_be_inside_the_same_window() -> None:
    check_mp4(42.0, 42.0)
    check_mp4(45.0, 45.02)  # đúng mốc trên, ffprobe lệch nhẹ do khung AAC: vẫn đạt
    check_mp4(40.0, 39.98)
    with pytest.raises(MediaError, match="ngoài khoảng cho phép 40–45"):
        check_mp4(45.0, 45.3)
    with pytest.raises(MediaError, match="ngoài khoảng cho phép 40–45"):
        check_mp4(40.0, 39.8)


def test_final_mp4_check_uses_the_limits_it_is_given() -> None:
    narrow = RenderLimits(10.0, 20.0)
    with pytest.raises(PlanError):  # plan 42 s đã bị loại ở bước kiểm plan
        check_mp4(42.0, 42.0, narrow)
    tl = build_timeline(cards([42.0]), PRESETS["co-dien"])
    with pytest.raises(MediaError, match="ngoài khoảng cho phép 10–20"):
        check_output(make_info(42.0), "16:9", tl, narrow)  # cùng MP4, mốc khác → bị loại


def test_scene_requires_asset_for_image_and_video() -> None:
    with pytest.raises(ValueError, match="cần 'asset'"):
        Scene(role="demo", kind="image", caption="x")
    with pytest.raises(ValueError, match="không dùng 'asset'"):
        Scene(role="hook", kind="text_card", caption="x", asset="a.jpg")


def test_chunk_caption_respects_max_words_and_keeps_all_words() -> None:
    text = "Giá chỉ còn 390.000đ, giảm 25% đến hết ngày 31/10/2026."
    chunks = chunk_caption(text, 5)
    assert " ".join(chunks) == text
    assert all(len(c.split()) <= 5 for c in chunks)
    assert chunk_caption("", 5) == []


def test_split_times_is_contiguous() -> None:
    parts = split_times(["abc", "de", "fghij"], 2.0, 5.0)
    assert parts[0][0] == 2.0 and parts[-1][1] == 5.0
    assert all(a[1] == b[0] for a, b in zip(parts, parts[1:], strict=False))


@pytest.mark.parametrize("ratio", ["9:16", "16:9"])
def test_ass_keeps_vietnamese_text_and_safe_margins(ratio: str) -> None:
    preset = PRESETS["hoat-hinh-do-hoa"]
    plan = make_plan(preset.id, REAL_VOICE_S)
    tl = build_timeline(plan, preset, fake_duration(REAL_VOICE_S))
    ass = build_ass(tl, preset, ratio)  # type: ignore[arg-type]
    assert "Tiết kiệm 390.000đ — dùng" in ass.replace("\n", " ") or "đ —" in ass
    w, h = (1080, 1920) if ratio == "9:16" else (1920, 1080)
    assert f"PlayResX: {w}" in ass and f"PlayResY: {h}" in ass
    # lề dưới của phụ đề 9:16 phải lớn hơn 16:9 (tránh vùng giao diện TikTok/Reels)
    margin = int(
        next(line for line in ass.splitlines() if line.startswith("Style: Sub")).split(",")[-2]
    )
    assert margin == preset.sub_margin_v[ratio]


def test_vignette_uses_prebuilt_mask_not_single_thread_filter(tmp_path: Path) -> None:
    """Filter `vignette` đơn luồng làm preset điện ảnh chậm gấp ~2 lần: chỉ dùng nó để dựng
    mặt nạ 1 khung rồi nhân vào video bằng lut2 (xem ADR-0003, known issue đã sửa)."""
    preset = PRESETS["dien-anh-toi-gian"]
    plan = make_plan(preset.id, REAL_VOICE_S)
    tl = build_timeline(plan, preset, fake_duration(REAL_VOICE_S))
    script = build_command(plan, tl, preset, "9:16", tmp_path / "o.mp4").filter_script
    assert "loop=loop=-1:size=1[vmask]" in script and "lut2=" in script
    assert script.count("vignette=") == 1  # chỉ trong nhánh mặt nạ, không áp lên video chính
    assert "[vjoin]eq=" in script and "[vlit]" in script


@pytest.mark.parametrize("preset_id", list(PRESETS))
def test_single_scene_plan_defines_the_joined_video_stream(preset_id: str, tmp_path: Path) -> None:
    """1 cảnh thì không có chuyển cảnh nào để nối: vòng xfade rỗng, nên phải tự nối [v0] → [vjoin]
    (nếu không, ffmpeg báo thiếu nhãn [vjoin])."""
    plan = cards([42.0], preset_id)
    tl = build_timeline(plan, PRESETS[preset_id])
    script = build_command(plan, tl, PRESETS[preset_id], "9:16", tmp_path / "o.mp4").filter_script
    assert "[v0]null[vjoin]" in script and "xfade" not in script


def test_two_scene_plan_has_exactly_one_xfade_into_vjoin(tmp_path: Path) -> None:
    plan = cards([22.0, 22.0])
    tl = build_timeline(plan, PRESETS["co-dien"])
    script = build_command(plan, tl, PRESETS["co-dien"], "9:16", tmp_path / "o.mp4").filter_script
    assert script.count("xfade=") == 1 and "[v0][v1]xfade=" in script and "[vjoin]" in script


def test_command_uses_xfade_or_concat_and_maps_audio(tmp_path: Path) -> None:
    for preset in PRESETS.values():
        plan = make_plan(preset.id, REAL_VOICE_S)
        tl = build_timeline(plan, preset, fake_duration(REAL_VOICE_S))
        cmd = build_command(plan, tl, preset, "9:16", tmp_path / "o.mp4")
        assert "xfade=transition=" + preset.transition in cmd.filter_script
        assert "[vout]" in cmd.args and "[aout]" in cmd.args
        assert "libx264" in cmd.args and "-r" in cmd.args
        assert "ass=filename=subs.ass:fontsdir=fonts" in cmd.filter_script
