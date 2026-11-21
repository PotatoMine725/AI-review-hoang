"""Test phần thuần (không cần node/Chrome/ffmpeg): đọc slot, zoom, tính khung, mốc 40–45 s,
luật fact_refs, phụ đề, thứ tự voice cho CLI TTS."""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from limits import load_limits
from plan import Clip, ClipPart, PlanError, RenderPlan, load_plan
from slots import (
    MAX_ZOOM,
    ZOOM_ANIM_S,
    clip_css,
    clip_speed,
    focus_time,
    load_layouts,
    normalize_rect,
    read_layout,
    zoom_for,
)
from subtitles import LINE_CHARS, build_ass, wrap_caption
from timeline import build_timeline, to_frame
from tts_input import segments_for_tts

ROOT = Path(__file__).resolve().parent.parent
PLAN = ROOT / "plans" / "pdfcraft-40-45s.json"
LIMITS = load_limits({})  # mặc định của config #77, không phụ thuộc biến môi trường máy chạy


def _plan(voice_s: float = 39.3, **over: Any) -> tuple[RenderPlan, dict[str, float]]:
    """Plan 1 cảnh 1 câu; tổng = lead 0,1 + voice + tail 0,6."""
    data: dict[str, Any] = {
        "schema_version": "render-plan.v2-spike",
        "product": "X",
        "written_by": "test",
        "preset": "dien-anh-toi-gian",
        "ratios": ["16:9"],
        "facts": {"F1": "nguồn"},
        "scenes": [
            {
                "scene_id": "s01",
                "role": "hook",
                "layout": "hook",
                "narration_segments": [
                    {"segment_id": "u1", "text": "Câu", "voice": "v/s01.wav", "fact_refs": ["F1"]}
                ],
                "props": {"title": {"text": "Tiêu đề", "fact_refs": ["F1"]}},
            }
        ],
    }
    data.update(over)
    return RenderPlan.model_validate(data), {"u1": voice_s}


# ---------- đọc layout / slot ----------


def test_read_layout_doc_ten_va_o() -> None:
    html = """<div class="scene" data-layout="feature_clip">
      <div data-slot="clip"><video data-src="clip.src"></video></div>
      <script>TPL.mount("feature_clip");</script></div>"""
    info = read_layout(html)
    assert info.name == "feature_clip"
    assert info.slots == ("clip",)


def test_read_layout_thieu_mount_bi_chan() -> None:
    with pytest.raises(PlanError, match="TPL.mount"):
        read_layout('<div data-layout="stat"></div>')


def test_read_layout_hai_goc_bi_chan() -> None:
    with pytest.raises(PlanError, match="đúng 1"):
        read_layout('<div data-layout="a"></div><div data-layout="b"></div>')


def test_template_that_co_du_5_layout_va_o_clip() -> None:
    layouts = load_layouts(ROOT / "template" / "layouts")
    assert set(layouts) == {"hook", "stat", "feature_clip", "claim", "cta"}
    assert "clip" in layouts["feature_clip"].slots
    assert "clip" not in layouts["claim"].slots  # layout chỉ có chữ, không có ô clip


# ---------- zoom vào clip_focus ----------


def test_normalize_rect_theo_vung_cat() -> None:
    assert normalize_rect((540, 108, 740, 540), (440, 0, 1480, 1080)) == pytest.approx(
        (100 / 1480, 0.1, 0.5, 0.5)
    )


def test_normalize_rect_ngoai_vung_cat_bi_chan() -> None:
    with pytest.raises(PlanError, match="ngoài vùng cắt"):
        normalize_rect((0, 0, 100, 100), (440, 0, 1480, 1080))


def test_zoom_vung_giua_khong_lo_mep() -> None:
    z = zoom_for((0.25, 0.25, 0.5, 0.5))
    assert z.scale == 2.0
    # tâm vùng (0,5; 0,5) → giữa ô: tx = 0,5 − 0,5·2 = −0,5
    assert (z.tx, z.ty) == (-0.5, -0.5)


def test_zoom_kep_tran_va_kep_mep() -> None:
    z = zoom_for((0.9, 0.0, 0.1, 0.1))  # vùng nhỏ ở góc phải trên
    assert z.scale == MAX_ZOOM
    assert z.tx == pytest.approx(1 - MAX_ZOOM)  # không trượt quá mép phải
    assert z.ty == 0  # không trượt quá mép trên


def _clip(*lengths: float, focus: dict[str, Any] | None = None) -> Clip:
    parts, t = [], 0.0
    for n in lengths:
        parts.append(ClipPart(src="c.mp4", start_s=t, end_s=t + n))
        t += n + 1
    return Clip.model_validate({"parts": parts, "crop": (0, 0, 1920, 1080), "focus": focus})


def test_clip_speed_trong_khoang() -> None:
    assert clip_speed(_clip(4, 4), 8) == 1.0
    with pytest.raises(PlanError, match="tốc độ"):
        clip_speed(_clip(2), 8)  # 0,25 < 0,6: tua chậm quá trông giả


def test_focus_time_theo_doan_va_toc_do() -> None:
    rect = (0, 0, 960, 540)
    clip = _clip(4, 4, focus={"part": 1, "source_t": 6.0, "rect": rect})
    # đoạn 1 bắt đầu ở nguồn 5,0; source_t 6,0 → 4 + 1 = 5 s clip; tua x1 → 5 s trong cảnh
    assert focus_time(clip, 8) == 5.0
    # cảnh ngắn: kẹp để zoom kịp chạy xong trước khi hết cảnh
    clip2 = _clip(4, 4, focus={"part": 1, "source_t": 8.9, "rect": rect})
    assert focus_time(clip2, 8) <= 8 - ZOOM_ANIM_S - 0.1 + 1e-9
    css = clip_css(clip, 8)
    assert css["--clip-aspect"] == "1920 / 1080" and css["--focus-at"] == "5.0s"


def test_crop_theo_ti_le() -> None:
    clip = _clip(4, focus={"part": 0, "source_t": 1.0, "rect": (1000, 400, 300, 200)})
    clip = clip.model_copy(
        update={"crop": (440, 0, 1480, 1080), "crop_by_ratio": {"9:16": (678, 0, 1242, 1080)}}
    )
    tall, wide = clip.for_ratio("9:16"), clip.for_ratio("16:9")
    assert tall.crop == (678, 0, 1242, 1080) and tall.crop_by_ratio == {}
    assert wide.crop == (440, 0, 1480, 1080)
    assert clip_css(tall, 4)["--clip-aspect"] == "1242 / 1080"
    # zoom tính trên vùng cắt của đúng tỉ lệ: cùng rect, vị trí chuẩn hoá khác nhau
    assert clip_css(tall, 4)["--fx-tx"] != clip_css(wide, 4)["--fx-tx"]


# ---------- tính khung + mốc 40–45 s (đọc từ config #77) ----------


def test_to_frame_lam_tron_len_o_nua() -> None:
    assert to_frame(1 / 60, 30) == 1
    assert to_frame(0.1, 30) == 3


@pytest.mark.parametrize(
    ("voice_s", "ok"),
    [
        (39.3, True),  # tổng đúng 40,000 s = 1200 khung
        (39.3 - 1 / 30, False),  # thiếu 1 khung
        (44.3, True),  # đúng 45,000 s
        (44.3 + 1 / 30, False),  # thừa 1 khung
    ],
)
def test_moc_40_45_sat_bien(voice_s: float, ok: bool) -> None:
    plan, voice = _plan(voice_s)
    if ok:
        assert build_timeline(plan, voice, LIMITS).total_s == pytest.approx(round(voice_s + 0.7, 4))
    else:
        with pytest.raises(PlanError, match="ngoài khoảng"):
            build_timeline(plan, voice, LIMITS)


def test_moc_doc_tu_bien_moi_truong_cua_config_77() -> None:
    plan, voice = _plan(20.0)
    short = load_limits({"P1_RENDER_MIN_TOTAL_S": "15", "P1_RENDER_MAX_TOTAL_S": "25"})
    assert build_timeline(plan, voice, short).total_s == pytest.approx(20.7)
    with pytest.raises(PlanError):
        build_timeline(plan, voice, LIMITS)


def test_plan_that_canh_noi_khit_va_nghi_toi_da_015() -> None:
    plan = load_plan(PLAN)
    voice = {g.segment_id: 2.5 for s in plan.scenes for g in s.narration_segments}
    tl = build_timeline(plan, voice, load_limits({"P1_RENDER_MIN_TOTAL_S": "1"}))
    for a, b in zip(tl.scenes, tl.scenes[1:], strict=False):
        assert a.end_f == b.start_f  # không hở, không chồng
    assert sum(s.frames for s in tl.scenes) == tl.total_frames
    assert tl.max_gap_s() <= 0.15 + 1e-9


# ---------- luật fact_refs ----------


def _raw() -> dict[str, Any]:
    return json.loads(PLAN.read_text(encoding="utf-8"))


def test_plan_that_hop_le_va_moi_cau_co_fact_refs() -> None:
    plan = load_plan(PLAN)
    assert plan.written_by
    assert all(g.fact_refs for s in plan.scenes for g in s.narration_segments)


def test_cau_thieu_fact_refs_bi_chan() -> None:
    data = _raw()
    data["scenes"][0]["narration_segments"][0]["fact_refs"] = []
    with pytest.raises(ValidationError, match="thiếu fact_refs"):
        RenderPlan.model_validate(data)


def test_cau_dan_exempt_lead_duoc_de_trong_fact_refs() -> None:
    data = _raw()
    seg = data["scenes"][0]["narration_segments"][0]
    seg["fact_refs"] = []
    seg["exempt"] = "lead"
    plan = RenderPlan.model_validate(data)
    assert plan.scenes[0].narration_segments[0].fact_refs == []
    seg["exempt"] = "other"
    with pytest.raises(ValidationError):
        RenderPlan.model_validate(data)


def test_cau_tro_fact_khong_ton_tai_bi_chan() -> None:
    data = _raw()
    data["scenes"][1]["narration_segments"][0]["fact_refs"] = ["F99"]
    with pytest.raises(ValidationError, match="F99"):
        RenderPlan.model_validate(data)


def test_chu_tren_hinh_khong_nguon_bi_chan_tru_cta() -> None:
    data = _raw()
    bad = copy.deepcopy(data)
    del bad["scenes"][1]["props"]["value"]["fact_refs"]
    with pytest.raises(ValidationError, match="thiếu fact_refs"):
        RenderPlan.model_validate(bad)
    cta = copy.deepcopy(data)
    cta["scenes"][-1]["props"]["extra"] = "Chữ CTA tự do"
    RenderPlan.model_validate(cta)  # cảnh cta được miễn


def test_layout_claim_chu_phai_co_nguon() -> None:
    """Layout chỉ-chữ vẫn theo luật chữ trên hình: claim và ý phụ cần fact_refs."""
    data = _raw()
    fid = next(iter(data["facts"]))
    data["scenes"].insert(
        1,
        {
            "scene_id": "s90",
            "role": "proof",
            "layout": "claim",
            "narration_segments": [
                {"segment_id": "u90", "text": "Câu", "voice": "v/s90.wav", "fact_refs": [fid]}
            ],
            "props": {
                "eyebrow": {"text": "X", "fact_refs": [fid]},
                "icon": "sparkles",
                "claim": {"text": "Nguyên văn claim", "fact_refs": [fid]},
                "points": [{"text": "Ý phụ", "fact_refs": [fid], "icon": "check"}],
            },
        },
    )
    RenderPlan.model_validate(data)
    bad = copy.deepcopy(data)
    del bad["scenes"][1]["props"]["points"][0]["fact_refs"]
    with pytest.raises(ValidationError, match="thiếu fact_refs"):
        RenderPlan.model_validate(bad)


# ---------- phụ đề ----------


def test_wrap_caption_can_bang_khong_cat_tu() -> None:
    rows = wrap_caption("PDFCraft miễn phí, chạy ngay trong trình duyệt.", 24)
    assert len(rows) == 2 and all(len(r) <= 24 for r in rows)
    assert " ".join(rows) == "PDFCraft miễn phí, chạy ngay trong trình duyệt."
    assert wrap_caption("Vào pdfcraft.devtoolcafe.com", 24) == ["Vào", "pdfcraft.devtoolcafe.com"]


def test_phu_de_moi_cau_mot_dong_su_kien_dung_moc_voice() -> None:
    plan = load_plan(PLAN)
    voice = {g.segment_id: 2.5 for s in plan.scenes for g in s.narration_segments}
    tl = build_timeline(plan, voice, load_limits({"P1_RENDER_MIN_TOTAL_S": "1"}))
    for ratio in ("16:9", "9:16"):
        ass = build_ass(plan, tl, ratio)
        events = [x for x in ass.splitlines() if x.startswith("Dialogue:")]
        assert len(events) == len(tl.segments)  # không chia cụm theo số ký tự (timing giả)
        for ev in events:
            rows = ev.split(",", 9)[9].split("}", 1)[1].split(r"\N")
            assert len(rows) <= 2
            assert all(len(r) <= LINE_CHARS[ratio] or " " not in r for r in rows)


# ---------- đầu vào CLI TTS ----------


def test_tts_input_theo_thu_tu_doc() -> None:
    folder, segs = segments_for_tts(load_plan(PLAN))
    assert folder == "local/voice-40-45"
    assert len(segs) == 16 and segs[0]["text"].startswith("Cần xử lý PDF")


def test_tts_input_sai_ten_file_bi_chan() -> None:
    data = _raw()
    data["scenes"][0]["narration_segments"][0]["voice"] = "local/voice-40-45/s09.wav"
    with pytest.raises(PlanError, match="s01.wav"):
        segments_for_tts(RenderPlan.model_validate(data))
