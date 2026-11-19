"""Ánh xạ kịch bản M2 → render plan #88, trên kịch bản run4 thật (LLM sinh, ~19 s)."""

from __future__ import annotations

import importlib.util
import os
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

from tests.produce.support import RUN4_INPUT, RUN4_SCRIPT, load_run4, make_assets, make_cfg
from worker.produce.assets import AssetFocus, AssetPart, load_assets
from worker.produce.mapping import MIN_PART_S, Mapper, SceneSpec, fit_parts
from worker.produce.timeline import build_timeline

pytestmark = pytest.mark.skipif(
    not (RUN4_SCRIPT.is_file() and RUN4_INPUT.is_file()), reason="thiếu dữ liệu run4 trong docs/"
)


def mapper(tmp_path: Path, script: dict[str, Any], inp: dict[str, Any]) -> Mapper:
    assets, base = load_assets(make_assets(tmp_path))
    return Mapper(script, inp, assets, base, make_cfg(tmp_path))


def by_id(specs: list[SceneSpec]) -> dict[str, SceneSpec]:
    return {s.scene_id: s for s in specs}


def build(m: Mapper, specs: list[SceneSpec], seconds: float = 3.0) -> dict[str, Any]:
    kept = [s for s in specs if not s.error]
    segs = [g["segment_id"] for s in kept for g in s.scene["narration_segments"]]
    tl = build_timeline(
        [
            (s.scene_id, [(g["segment_id"], seconds) for g in s.scene["narration_segments"]])
            for s in kept
        ],
        fps=30,
        lead_s=0.1,
        gap_s=0.12,
        tail_s=0.6,
    )
    return m.build_plan(specs, {i: f"/voice/{i}.wav" for i in segs}, tl, ["16:9", "9:16"], "test")


def test_run4_layouts(tmp_path: Path) -> None:
    script, inp = load_run4()
    specs = by_id(mapper(tmp_path, script, inp).plan_scenes())
    assert [(k, s.layout) for k, s in specs.items()] == [
        ("s01", "hook"),
        ("s02", "feature_clip"),
        ("s03", "feature_clip"),
        ("s04", "feature_clip"),
        ("s05", "claim"),
        ("s06", "cta"),
    ]


def test_proof_text_card_without_stat_display_uses_text_only_claim_layout(tmp_path: Path) -> None:
    script, inp = load_run4()
    m = mapper(tmp_path, script, inp)
    specs = m.plan_scenes()
    s05 = by_id(specs)["s05"]
    assert s05.error is None and s05.layout == "claim"
    props = next(s for s in build(m, specs)["scenes"] if s["scene_id"] == "s05")["props"]
    claims = script["scenes"][4]["claims"]
    # claim nguyên văn, đúng thứ tự kịch bản, mỗi chữ có fact_refs riêng; KHÔNG ghép thành stat
    assert props["claim"]["text"] == claims[0]["text"]
    assert [p["text"] for p in props["points"]] == [claims[1]["text"]]
    assert props["claim"]["fact_refs"] and props["points"][0]["fact_refs"]
    assert props["claim"]["fact_refs"] != props["points"][0]["fact_refs"]
    # visual_plan.text không có fact_refs nên không lên hình
    shown = repr(props)
    assert script["scenes"][4]["visual_plan"]["text"] not in shown
    assert "value" not in props and "label" not in props


def test_text_card_without_claims_is_a_clear_error(tmp_path: Path) -> None:
    script, inp = load_run4()
    script = deepcopy(script)
    script["scenes"][4]["claims"] = []
    s05 = by_id(mapper(tmp_path, script, inp).plan_scenes())["s05"]
    assert s05.error is not None and s05.error.code == "unsupported_scene"
    assert "role=proof kind=text_card" in s05.error.message
    assert "stat_display" in s05.error.hint
    assert s05.layout is None


def test_template_without_claim_layout_is_a_clear_error(tmp_path: Path) -> None:
    script, inp = load_run4()
    assets, base = load_assets(make_assets(tmp_path))
    old = frozenset({"hook", "stat", "feature_clip", "cta"})  # template #88 chưa có layout claim
    specs = by_id(Mapper(script, inp, assets, base, make_cfg(tmp_path), layouts=old).plan_scenes())
    err = specs["s05"].error
    assert err is not None and err.code == "layout_missing_in_template"
    assert "spike/p1-render-v2" in err.hint
    assert specs["s01"].error is None and specs["s02"].error is None


def test_stat_display_selects_stat_layout(tmp_path: Path) -> None:
    script, inp = load_run4()
    script = deepcopy(script)
    claim = script["scenes"][4]["claims"][0]
    claim["stat_display"] = {
        "value": "0 đ",
        "label": "Chi phí dùng",
        "unit": None,
        "scope": "Gói miễn phí",
    }
    m = mapper(tmp_path, script, inp)
    specs = m.plan_scenes()
    assert by_id(specs)["s05"].layout == "stat"
    plan = build(m, specs)
    props = next(s for s in plan["scenes"] if s["scene_id"] == "s05")["props"]
    assert props["value"]["text"] == "0 đ" and props["label"]["text"] == "Chi phí dùng"
    assert props["eyebrow"]["text"] == "Gói miễn phí"
    assert props["value"]["fact_refs"] and set(props["value"]["fact_refs"]) <= set(plan["facts"])
    assert any("claims_not_shown" in w for w in by_id(specs)["s05"].warnings)


def test_stat_value_includes_unit(tmp_path: Path) -> None:
    script, inp = load_run4()
    script = deepcopy(script)
    script["scenes"][4]["claims"][0]["stat_display"] = {
        "value": "100",
        "label": "Tệp mỗi lần ghép",
        "unit": "tệp",
        "scope": "Một lần ghép",
    }
    m = mapper(tmp_path, script, inp)
    plan = build(m, m.plan_scenes())
    props = next(s for s in plan["scenes"] if s["scene_id"] == "s05")["props"]
    assert props["value"]["text"] == "100 tệp"


def test_derived_cta_scene(tmp_path: Path) -> None:
    script, inp = load_run4()
    specs = mapper(tmp_path, script, inp).plan_scenes()
    cta = specs[-1]
    assert (cta.scene_id, cta.derived, cta.layout) == ("s06", True, "cta")
    assert cta.scene["narration_segments"] == [
        {"segment_id": "s06-u01", "text": "Xem thêm thông tin"}
    ]
    assert any(w.startswith("cta_narration_derived") for w in cta.warnings)


def test_real_cta_scene_is_not_duplicated(tmp_path: Path) -> None:
    script, inp = load_run4()
    script = deepcopy(script)
    script["scenes"][4]["role"] = "cta"
    specs = mapper(tmp_path, script, inp).plan_scenes()
    assert not any(s.derived for s in specs)
    assert by_id(specs)["s05"].layout == "cta"


def test_plan_content_for_run4(tmp_path: Path) -> None:
    script, inp = load_run4()
    m = mapper(tmp_path, script, inp)
    specs = m.plan_scenes()
    plan = build(m, specs, seconds=3.0)

    assert plan["schema_version"] == "render-plan.v2-spike"
    assert plan["product"] == "PDFCraft"
    assert (plan["lead_s"], plan["gap_s"], plan["tail_s"]) == (0.1, 0.12, 0.6)
    assert [s["scene_id"] for s in plan["scenes"]] == ["s01", "s02", "s03", "s04", "s05", "s06"]

    hook = plan["scenes"][0]
    assert (
        hook["props"]["title"]["text"] == script["hook"]["text"]
    )  # hook.text, không phải visual_plan.text
    assert hook["props"]["image"]["label"] == {
        "text": "Ảnh minh hoạ do AI tạo",
        "exempt": "disclosure",
    }
    assert hook["image"]["path"].endswith("paperwork.jpg")
    assert any(w.startswith("scene_asset_override") for w in specs[0].warnings)
    assert specs[0].footage == "image:ai-paperwork"

    clip_scene = plan["scenes"][1]
    assert clip_scene["layout"] == "feature_clip" and clip_scene["clip"]["crop"] == [
        440,
        0,
        1480,
        1080,
    ]
    # claim đầu trùng nguyên văn phụ đề → tiêu đề là tên tính năng có fact_refs riêng
    assert clip_scene["props"]["title"]["text"] == "Hợp nhất PDF"
    assert clip_scene["props"]["title"]["fact_refs"] == ["src_01:features[0].name"]
    assert plan["facts"]["src_01:features[0].name"] == "Hợp nhất PDF"
    assert clip_scene["props"]["url"] == "pdfcraft.devtoolcafe.com"
    assert specs[1].footage == "clip:pdfcraft-merge"

    # subtitle_text khác lời đọc thì mang theo; câu nào cũng có fact_refs hợp lệ
    assert (
        clip_scene["narration_segments"][0]["subtitle_text"]
        == "Hợp nhất nhiều tệp PDF thành một tài liệu."
    )
    for scene in plan["scenes"]:
        for seg in scene["narration_segments"]:
            assert seg["fact_refs"] and set(seg["fact_refs"]) <= set(plan["facts"])

    cta = plan["scenes"][-1]
    assert cta["props"]["button"] == {"text": "Xem thêm thông tin", "exempt": "cta"}
    assert "url" not in cta["props"]  # cta.destination = null → không lấy identity.website
    assert cta["narration_segments"][0]["fact_refs"] == [m.brand_ref]
    assert not any(w.startswith("cta_without_url") for s in specs for w in s.warnings)


def test_cta_url_only_from_destination(tmp_path: Path) -> None:
    script, inp = load_run4()
    script["cta"]["destination"] = "https://pdfcraft.devtoolcafe.com/tools/merge"
    m = mapper(tmp_path, script, inp)
    cta = build(m, m.plan_scenes())["scenes"][-1]
    assert cta["props"]["url"] == "pdfcraft.devtoolcafe.com/tools/merge"


def test_clip_is_trimmed_not_stretched(tmp_path: Path) -> None:
    script, inp = load_run4()
    m = mapper(tmp_path, script, inp)
    plan = build(m, m.plan_scenes(), seconds=2.0)
    merge = plan["scenes"][1]["clip"]  # asset dài 7,8 s, cảnh ngắn hơn nhiều
    (part,) = merge["parts"]
    assert part["end_s"] - part["start_s"] < 7.8
    # cửa sổ cắt chứa source_t 16,0 → giữ zoom
    assert part["start_s"] <= 16.0 <= part["end_s"]
    assert merge["focus"] == {"part": 0, "source_t": 16.0, "rect": [520, 110, 560, 330]}


def test_focus_kept_when_clip_is_trimmed(tmp_path: Path) -> None:
    script, inp = load_run4()
    m = mapper(tmp_path, script, inp)
    specs = m.plan_scenes()
    build(m, specs, seconds=2.0)
    assert not any(w.startswith("focus_dropped") for w in by_id(specs)["s02"].warnings)


def test_focus_outside_its_part_is_dropped_with_reason(tmp_path: Path) -> None:
    script, inp = load_run4()
    m = mapper(tmp_path, script, inp)
    merge = m.assets.assets["pdfcraft-merge"]
    bad = merge.model_copy(update={"focus": merge.focus.model_copy(update={"source_t": 30.0})})
    m.assets = m.assets.model_copy(update={"assets": {**m.assets.assets, "pdfcraft-merge": bad}})
    specs = m.plan_scenes()
    plan = build(m, specs, seconds=2.0)
    assert "focus" not in plan["scenes"][1]["clip"]
    (w,) = [w for w in by_id(specs)["s02"].warnings if w.startswith("focus_dropped")]
    assert "30.00" in w and "9.80–17.60" in w


def test_screen_recording_without_asset_is_scene_error(tmp_path: Path) -> None:
    script, inp = load_run4()
    script = deepcopy(script)
    script["scenes"][1]["visual_plan"]["asset_id"] = "khong-co"
    s02 = by_id(mapper(tmp_path, script, inp).plan_scenes())["s02"]
    assert s02.error is not None and s02.error.code == "asset_missing"


@pytest.mark.parametrize("kind", ["screenshot", "product_asset", "logo"])
def test_other_visual_kinds_have_no_layout(tmp_path: Path, kind: str) -> None:
    script, inp = load_run4()
    script = deepcopy(script)
    script["scenes"][4]["visual_plan"]["kind"] = kind
    s05 = by_id(mapper(tmp_path, script, inp).plan_scenes())["s05"]
    assert s05.error is not None and s05.error.code == "unsupported_scene"


def test_hook_without_image_warns(tmp_path: Path) -> None:
    script, inp = load_run4()
    m = mapper(tmp_path, script, inp)
    m.assets = m.assets.model_copy(update={"scene_assets": {}})
    s01 = by_id(m.plan_scenes())["s01"]
    assert s01.layout == "hook" and s01.asset is None
    assert any(w.startswith("hook_without_image") for w in s01.warnings)


def test_hook_pointing_to_clip_is_a_clear_scene_error(tmp_path: Path) -> None:
    # run7/run8 (#92): hook kind=logo + asset_id là clip. Validator #83 chặn ở phía M2; produce
    # báo lỗi rõ ở đúng cảnh, không fallback và không tự đổi asset.
    script, inp = load_run4()
    script = deepcopy(script)
    script["scenes"][0]["visual_plan"] = {
        "kind": "logo",
        "source_type": "existing_asset",
        "asset_id": "pdfcraft-merge",
        "purpose": "Giới thiệu giao diện chính",
    }
    s01 = by_id(mapper(tmp_path, script, inp).plan_scenes())["s01"]
    assert s01.error is not None and s01.error.code == "asset_kind"
    assert s01.error.scene_id == "s01" and "pdfcraft-merge" in s01.error.message


def test_claim_ref_to_bool_value_is_valid(tmp_path: Path) -> None:
    # Prompt #83 4c5b72b lấy `pricing.free_plan.value` (bool) làm ví dụ fact_ref.
    script, inp = load_run4()
    script = deepcopy(script)
    script["scenes"][1]["claims"][0]["fact_refs"].append(
        {"source_id": "src_01", "field_path": "pricing.free_plan.value"}
    )
    m = mapper(tmp_path, script, inp)
    s02 = by_id(m.plan_scenes())["s02"]
    assert s02.error is None
    assert m.facts.facts["src_01:pricing.free_plan.value"] == "Hoàn toàn Miễn phí"


# ---- fit_parts


def part(a: float, b: float) -> AssetPart:
    return AssetPart(start_s=a, end_s=b)


def test_fit_parts_trims_overflow() -> None:
    kept, warns = fit_parts([part(1.0, 5.0), part(10.0, 14.0)], 6.0)
    assert [(i, p.start_s, p.end_s) for i, p in kept] == [(0, 1.0, 5.0), (1, 10.0, 12.0)]
    assert warns == []


def test_fit_parts_slows_within_bounds_and_warns() -> None:
    kept, warns = fit_parts([part(0.0, 4.0)], 5.0)  # tốc độ 0,8
    assert len(kept) == 1 and warns and warns[0].startswith("clip_slowed")


def test_fit_parts_too_short_is_error() -> None:
    with pytest.raises(ValueError, match="chỉ có 2.00 s"):
        fit_parts([part(0.0, 2.0)], 5.0)  # tốc độ 0,4 < 0,6


def focus(p: int, t: float) -> AssetFocus:
    return AssetFocus(part=p, source_t=t, rect=(0, 0, 100, 100))


def focus_offset(kept: list[tuple[int, AssetPart]], f: AssetFocus) -> float:
    """Mốc focus tính từ đầu cảnh (tốc độ 1,0), theo các đoạn đã cắt."""
    before = 0.0
    for orig, p in kept:
        if orig == f.part:
            assert p.start_s <= f.source_t <= p.end_s
            return before + f.source_t - p.start_s
        before += p.length_s
    raise AssertionError("đoạn chứa focus bị bỏ")


def total(kept: list[tuple[int, AssetPart]]) -> float:
    return sum(p.length_s for _, p in kept)


# Ba asset PDFCraft thật (assets.pdfcraft.json, lấy từ plan #88) với độ dài cảnh của run-b1.
REAL_CLIPS = {
    "merge": ([part(9.8, 17.6)], focus(0, 16.0), 3.6),
    "pagenum": ([part(1.6, 4.0), part(9.4, 11.48), part(11.62, 13.6)], focus(2, 11.9), 4.0),
    "word-export": ([part(1.4, 3.6), part(0.0, 7.0)], focus(1, 4.0), 3.8),
}


@pytest.mark.parametrize("name", list(REAL_CLIPS))
def test_fit_parts_window_contains_focus_at_60_percent(name: str) -> None:
    parts, f, scene_s = REAL_CLIPS[name]
    kept, warns = fit_parts(parts, scene_s, f)
    assert warns == []
    assert total(kept) == pytest.approx(scene_s, abs=MIN_PART_S)
    assert focus_offset(kept, f) == pytest.approx(0.6 * scene_s, abs=MIN_PART_S)


def test_fit_parts_focus_target_leaves_room_for_zoom_on_short_scene() -> None:
    # cảnh 2 s: 60% = 1,2 s nhưng #88 kẹp mốc zoom ≤ scene − 1,0 s → nhắm 1,0 s
    kept, _ = fit_parts([part(0.0, 10.0)], 2.0, focus(0, 5.0))
    assert focus_offset(kept, focus(0, 5.0)) == pytest.approx(1.0)


def test_fit_parts_window_clamped_to_clip_edges() -> None:
    kept, _ = fit_parts([part(0.0, 6.0)], 4.0, focus(0, 0.5))  # focus sát đầu
    assert [(p.start_s, p.end_s) for _, p in kept] == [(0.0, 4.0)]
    kept, _ = fit_parts([part(0.0, 6.0)], 4.0, focus(0, 5.9))  # focus sát cuối
    assert [(p.start_s, p.end_s) for _, p in kept] == [(2.0, 6.0)]


def test_fit_parts_drops_slivers_at_window_edge() -> None:
    # cửa sổ 2,38–6,38 chỉ chạm 0,02 s cuối của đoạn 0 → bỏ mảnh đó
    kept, _ = fit_parts([part(0.0, 2.4), part(10.0, 14.0)], 4.0, focus(1, 12.38))
    assert [i for i, _ in kept] == [1]
    assert all(p.length_s >= MIN_PART_S for _, p in kept)


def test_fit_parts_focus_outside_part_falls_back_to_start() -> None:
    kept, _ = fit_parts([part(1.0, 9.0)], 3.0, focus(0, 20.0))
    assert [(p.start_s, p.end_s) for _, p in kept] == [(1.0, 4.0)]


def test_fit_parts_short_clip_keeps_everything_with_focus() -> None:
    parts = [part(0.0, 2.0), part(5.0, 7.0)]
    kept, _ = fit_parts(parts, 4.0, focus(1, 6.0))
    assert [(i, p.start_s, p.end_s) for i, p in kept] == [(0, 0.0, 2.0), (1, 5.0, 7.0)]


# ---- khớp với plan model thật của #88 (chỉ chạy khi có spike trên máy)


def _plan_model_88() -> Any:
    root = Path(
        os.environ.get("PRODUCE_RENDER_V2")
        or os.environ.get("P1_RENDER_V2")
        or make_cfg_path_default()
    )
    path = root / "plan.py"
    if not path.is_file():
        pytest.skip("không có spike #88 trên máy này")
    if '"claim"' not in path.read_text(encoding="utf-8"):
        pytest.skip(
            "spike #88 ở đường dẫn này chưa có layout claim (cần spike/p1-render-v2 từ 4e9f04f)"
        )
    sys.path.insert(0, str(root))
    try:
        spec = importlib.util.spec_from_file_location("p1_render_v2_plan", path)
        assert spec and spec.loader
        mod = importlib.util.module_from_spec(spec)
        sys.modules["p1_render_v2_plan"] = mod
        spec.loader.exec_module(mod)
        return mod
    finally:
        sys.path.remove(str(root))


def make_cfg_path_default() -> str:
    from worker.produce.config import ProduceConfig

    return str(ProduceConfig.model_fields["render_v2"].default)


def test_plan_is_accepted_by_render_plan_v2_model(tmp_path: Path) -> None:
    mod = _plan_model_88()
    script, inp = load_run4()
    m = mapper(tmp_path, script, inp)
    plan = build(m, m.plan_scenes(), seconds=4.0)
    parsed = mod.RenderPlan.model_validate(plan)  # gồm luật chữ trên hình phải có fact_refs
    assert [s.layout for s in parsed.scenes] == [
        "hook",
        "feature_clip",
        "feature_clip",
        "feature_clip",
        "claim",
        "cta",
    ]


def test_zoom_lands_at_focus_target_in_88_slots(tmp_path: Path) -> None:
    mod = _plan_model_88()
    root = Path(mod.__file__).parent
    sys.path.insert(0, str(root))
    try:
        import slots  # pyright: ignore[reportMissingImports]
    finally:
        sys.path.remove(str(root))
    script, inp = load_run4()
    m = mapper(tmp_path, script, inp)
    seconds = 4.0
    parsed = mod.RenderPlan.model_validate(build(m, m.plan_scenes(), seconds=seconds))
    clips = [s for s in parsed.scenes if s.layout == "feature_clip"]
    assert clips and all(s.clip.focus for s in clips if s.scene_id == "s02")
    for s in clips:
        if s.clip.focus is None:
            continue
        scene_s = sum(p.length_s for p in s.clip.parts)  # tốc độ 1,0: clip dài đúng bằng cảnh
        slots.clip_speed(s.clip, scene_s)  # không PlanError
        target = min(0.6 * scene_s, scene_s - 1.0)
        assert slots.focus_time(s.clip, scene_s) == pytest.approx(target, abs=0.06)


def test_segment_without_claim_keeps_empty_refs(tmp_path: Path) -> None:
    script, inp = load_run4()
    scene = script["scenes"][1]
    scene["narration_segments"].append({"segment_id": "s02-u02", "text": "Câu nối không claim."})
    m = mapper(tmp_path, script, inp)
    specs = m.plan_scenes()
    s02 = by_id(specs)["s02"]
    assert s02.error is None and s02.layout == "feature_clip"
    assert s02.seg_refs["s02-u02"] == []
    assert any(w.startswith("segment_without_claim: câu s02-u02") for w in s02.warnings)
    seg = build(m, specs)["scenes"][1]["narration_segments"][-1]
    assert seg["fact_refs"] == [] and seg["exempt"] == "lead"
    first = build(m, specs)["scenes"][1]["narration_segments"][0]
    assert first["fact_refs"] and "exempt" not in first


def test_clip_scene_without_any_claim_is_rejected(tmp_path: Path) -> None:
    script, inp = load_run4()
    script["scenes"][1]["claims"] = []
    s02 = by_id(mapper(tmp_path, script, inp).plan_scenes())["s02"]
    assert s02.error is not None and "scene_without_claim" in str(s02.error)


def test_clip_title_kept_when_not_duplicate(tmp_path: Path) -> None:
    script, inp = load_run4()
    scene = script["scenes"][1]
    scene["subtitle_text"] = None
    for g in scene["narration_segments"]:
        g["text"] = "Kéo thả các tệp vào ô bên phải."
        g.pop("subtitle_text", None)
    m = mapper(tmp_path, script, inp)
    specs = m.plan_scenes()
    title = build(m, specs)["scenes"][1]["props"]["title"]["text"]
    assert title == scene["claims"][0]["text"]
    assert not any(w.startswith("title_") for w in by_id(specs)["s02"].warnings)


def test_clip_title_duplicate_without_feature_name_warns(tmp_path: Path) -> None:
    script, inp = load_run4()
    claim = script["scenes"][1]["claims"][0]
    claim["fact_refs"] = [{"source_id": "src_10", "field_path": "limitations[0]"}]
    m = mapper(tmp_path, script, inp)
    specs = m.plan_scenes()
    title = build(m, specs)["scenes"][1]["props"]["title"]["text"]
    assert title == claim["text"]
    assert any(w.startswith("title_duplicates_subtitle") for w in by_id(specs)["s02"].warnings)


def test_clip_title_shortened_when_claim_points_to_feature_subfield(tmp_path: Path) -> None:
    """M2 thật trỏ `features[i].description`, không phải `features[i]`: vẫn thay bằng tên."""
    script, inp = load_run4()
    claim = script["scenes"][1]["claims"][0]
    claim["fact_refs"] = [
        {"source_id": r["source_id"], "field_path": "features[0].description"}
        for r in claim["fact_refs"]
    ]
    m = mapper(tmp_path, script, inp)
    specs = m.plan_scenes()
    title = build(m, specs)["scenes"][1]["props"]["title"]
    assert title["text"] == "Hợp nhất PDF"
    assert title["fact_refs"] == ["src_01:features[0].name"]
    assert any(w.startswith("title_shortened") for w in by_id(specs)["s02"].warnings)


def test_crop_by_ratio_passed_to_plan(tmp_path: Path) -> None:
    import json

    path = make_assets(tmp_path)
    doc = json.loads(path.read_text(encoding="utf-8"))
    doc["assets"]["pdfcraft-merge"]["crop_by_ratio"] = {"9:16": [440, 0, 1242, 1080]}
    path.write_text(json.dumps(doc), encoding="utf-8")
    script, inp = load_run4()
    assets, base = load_assets(path)
    m = Mapper(script, inp, assets, base, make_cfg(tmp_path))
    clip = build(m, m.plan_scenes())["scenes"][1]["clip"]
    assert clip["crop"] == [440, 0, 1480, 1080]
    assert clip["crop_by_ratio"] == {"9:16": [440, 0, 1242, 1080]}
    assert "crop_by_ratio" not in build(m, m.plan_scenes())["scenes"][2]["clip"]


def test_hook_without_fact_refs_uses_its_own_segment_refs(tmp_path: Path) -> None:
    script, inp = load_run4()
    script["hook"].pop("fact_refs", None)
    script["hook"]["text"] = "  " + script["scenes"][0]["narration_segments"][0]["text"] + " "
    m = mapper(tmp_path, script, inp)
    specs = m.plan_scenes()
    hook = build(m, specs)["scenes"][0]["props"]["title"]
    assert hook["fact_refs"] == by_id(specs)["s01"].seg_refs["s01-u01"] != []
    assert any(w.startswith("hook_refs_from_segment:") for w in by_id(specs)["s01"].warnings)


def test_hook_without_fact_refs_and_no_matching_segment_is_rejected(tmp_path: Path) -> None:
    script, inp = load_run4()
    script["hook"].pop("fact_refs", None)
    script["hook"]["text"] = "Một câu hook không ai đọc."
    s01 = by_id(mapper(tmp_path, script, inp).plan_scenes())["s01"]
    assert s01.error is not None and "hook_without_fact" in str(s01.error)
