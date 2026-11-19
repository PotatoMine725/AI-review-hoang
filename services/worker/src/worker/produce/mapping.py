"""Kịch bản M2 (đã qua validator) → `render-plan.v2-spike` của #88.

Hai bước, để TTS chỉ chạy cho các cảnh sẽ dựng:
1. `Mapper.plan_scenes()` chọn layout cho từng cảnh, không cần audio. Cảnh không ánh xạ được
   → `SceneError` gắn vào đúng cảnh đó (không bịa layout).
2. `Mapper.build_plan()` sinh props/clip/image khi đã có độ dài audio (clip cần độ dài cảnh).

Bảng ánh xạ (layout #88 `spike/p1-render-v2`: hook, stat, feature_clip, claim, cta):

    role = cta                       → cta
    visual_plan.kind = screen_recording → feature_clip  (cần asset kind=clip trong assets.json)
    role = hook                      → hook             (ảnh từ assets.json, thiếu thì cảnh báo)
    claim có stat_display            → stat             (stat_display là tuỳ chọn, M2 chưa bắt buộc)
    kind = text_card, có claim       → claim            (chỉ chữ: claim nguyên văn, đúng thứ tự)
    còn lại                          → lỗi rõ ở cảnh đó (kind cần hiện ảnh/logo, #88 chưa có layout)

Chữ trên hình chỉ lấy từ trường M2 có `fact_refs`: `hook.text`, `claims[].text`,
`claims[].stat_display`, tên sản phẩm (`identity.name`), CTA. `visual_plan.text` không có
`fact_refs` nên KHÔNG được hiện lên hình (luật chữ trên hình của #88).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from worker.produce.assets import Asset, AssetFocus, AssetPart, AssetsFile, resolve_media
from worker.produce.config import ProduceConfig
from worker.produce.errors import SceneError
from worker.produce.facts import FactBook, FactError
from worker.produce.timeline import TimedScene, Timeline

# Clip được tua nhanh/chậm để khớp lời đọc; ngoài khoảng này thao tác trông giả (slots.py của #88).
MIN_SPEED, MAX_SPEED = 0.6, 2.0
MIN_PART_S = 0.05
# Mốc zoom ưu tiên trong cảnh khi phải cắt clip. #88 (slots.focus_time) kẹp mốc zoom
# ≤ cảnh − ZOOM_ANIM_S (0,9) − 0,1 để zoom chạy xong trước khi hết cảnh.
FOCUS_AT = 0.6
ZOOM_TAIL_S = 1.0
# Tiêu đề cảnh clip coi là trùng phụ đề khi ≥ 60% từ (khác nhau) của nó có trong lời/phụ đề cảnh.
TITLE_DUP_OVERLAP = 0.6
# M2 trỏ tới `features[i]` hoặc trường con của nó (`features[i].description`)
_FEATURE_PATH = re.compile(r"(features\[\d+\])(?:\.\w+)?")
LAYOUTS_88 = "hook, stat, feature_clip, claim, cta"
CLAIM_BRANCH = "spike/p1-render-v2"  # nhánh #88, có layout claim từ commit 4e9f04f
SCHEMA = "render-plan.v2-spike"


@dataclass
class SceneSpec:
    scene: dict[str, Any]
    layout: str | None = None
    warnings: list[str] = field(default_factory=list)
    error: SceneError | None = None
    derived: bool = (
        False  # cảnh worker tự thêm (CTA từ `cta.text`), không có trong `scenes[]` của M2
    )
    asset: tuple[str, Asset] | None = None
    claim_refs: list[list[str]] = field(default_factory=list)  # fact id theo từng claim của cảnh
    claims: list[dict[str, Any]] = field(default_factory=list)
    seg_refs: dict[str, list[str]] = field(default_factory=dict)

    @property
    def scene_id(self) -> str:
        return self.scene["scene_id"]

    @property
    def footage(self) -> str | None:
        if not self.asset or self.layout not in {"feature_clip", "hook"}:
            return None
        key, asset = self.asset
        return f"{asset.kind}:{key}"


def focus_offset(parts: list[AssetPart], focus: AssetFocus) -> float | None:
    """Mốc focus trên dải các đoạn nối liền (giây, tốc độ 1,0); None nếu source_t ngoài đoạn."""
    p = parts[focus.part]
    if not p.start_s <= focus.source_t <= p.end_s:
        return None
    return sum(q.length_s for q in parts[: focus.part]) + focus.source_t - p.start_s


def fit_parts(
    parts: list[AssetPart], scene_s: float, focus: AssetFocus | None = None
) -> tuple[list[tuple[int, AssetPart]], list[str]]:
    """Chọn đoạn clip vừa độ dài cảnh ở tốc độ 1,0: cắt một cửa sổ dài bằng cảnh trên dải các
    đoạn nối liền.

    Có `focus` thì cửa sổ chứa nó, đặt mốc zoom ở FOCUS_AT thời lượng cảnh (kẹp theo mép clip);
    không có, hoặc source_t ngoài đoạn của nó, thì lấy từ đầu. Mảnh ngắn hơn MIN_PART_S ở mép cửa
    sổ bị bỏ. Thiếu thì KHÔNG kéo dài: tua chậm tới mức #88 cho phép (MIN_SPEED) kèm cảnh báo,
    thấp hơn nữa thì `clip_too_short`. Trả [(chỉ số đoạn gốc, đoạn đã cắt)].
    """
    src = sum(p.length_s for p in parts)
    start = 0.0
    at = focus_offset(parts, focus) if focus else None
    if at is not None and src > scene_s:
        target = min(FOCUS_AT * scene_s, scene_s - ZOOM_TAIL_S)
        start = min(max(at - target, 0.0), src - scene_s)
    end = start + scene_s
    kept: list[tuple[int, AssetPart]] = []
    offset = 0.0
    for idx, p in enumerate(parts):
        a, b = max(start, offset), min(end, offset + p.length_s)
        if b - a >= MIN_PART_S:
            cut = {
                "start_s": round(p.start_s + a - offset, 4),
                "end_s": round(p.start_s + b - offset, 4),
            }
            kept.append((idx, p.model_copy(update=cut)))
        offset += p.length_s
    total = sum(p.length_s for _, p in kept)
    remaining = scene_s - total
    warnings: list[str] = []
    if remaining >= MIN_PART_S:
        speed = total / scene_s
        if speed < MIN_SPEED:
            raise ValueError(
                f"clip chỉ có {total:.2f} s cho cảnh {scene_s:.2f} s (tốc độ {speed:.2f} < "
                f"{MIN_SPEED}); chọn thêm đoạn clip trong assets.json"
            )
        warnings.append(
            f"clip_slowed: clip {total:.2f} s cho cảnh {scene_s:.2f} s, tua {speed:.2f}x"
        )
    return kept, warnings


def _host(url: str) -> str:
    return url.removeprefix("https://").removeprefix("http://").removeprefix("www.").rstrip("/")


def _words(text: str) -> list[str]:
    return re.findall(r"\w+", text.lower())


class Mapper:
    def __init__(
        self,
        script: dict[str, Any],
        inp: dict[str, Any],
        assets: AssetsFile,
        assets_base: Path,
        cfg: ProduceConfig,
        layouts: frozenset[str] | None = None,
    ) -> None:
        self.script = script
        self.assets = assets
        self.base = assets_base
        self.cfg = cfg
        # Layout có thật trong template #88 trên máy; None = không kiểm (test, không có spike).
        self.layouts = layouts
        pkb = inp["approved_pkb"]["data"]
        self.facts = FactBook(pkb)
        self.brand = self.facts.text("identity.name")
        self.brand_ref = self.facts.add("identity.name")
        try:
            self.website: str | None = _host(self.facts.text("identity.website"))
        except (KeyError, FactError):
            self.website = None

    # ------------------------------------------------------------------ bước 1: chọn layout

    def plan_scenes(self) -> list[SceneSpec]:
        specs: list[SceneSpec] = []
        for scene in self.script["scenes"]:
            spec = SceneSpec(scene)
            try:
                self._classify(spec)
            except (SceneError, FactError) as ex:
                spec.layout = None
                spec.error = (
                    ex
                    if isinstance(ex, SceneError)
                    else SceneError(spec.scene_id, "fact_ref_invalid", str(ex))
                )
            specs.append(spec)
        derived = self._derive_cta(specs)
        if derived:
            specs.append(derived)
        return specs

    def _classify(self, spec: SceneSpec) -> None:
        scene = spec.scene
        sid, role = spec.scene_id, scene["role"]
        vp = scene.get("visual_plan") or {}
        kind = vp.get("kind")
        spec.claims = [
            c
            for c in scene.get("claims", [])
            if set(c["segment_ids"]) & {g["segment_id"] for g in scene["narration_segments"]}
        ]
        spec.claim_refs = [self.facts.add_refs(c["fact_refs"]) for c in spec.claims]

        if role == "cta":
            spec.layout = "cta"
        elif kind == "screen_recording":
            spec.layout = "feature_clip"
        elif role == "hook":
            spec.layout = "hook"
        elif any(c.get("stat_display") for c in spec.claims):
            spec.layout = "stat"
        elif kind == "text_card" and spec.claims:
            spec.layout = "claim"
        else:
            raise SceneError(
                sid,
                "unsupported_scene",
                f"M2 role={role} kind={kind}: #88 chưa có layout cho tổ hợp này "
                f"(hiện có: {LAYOUTS_88}); layout chỉ-chữ chỉ dùng cho kind=text_card có claim.",
                "kind này cần hiện ảnh/logo mà #88 chưa có layout cho nó; "
                "M2 có thể dùng text_card (claim nguyên văn) hoặc stat_display (layout stat).",
            )
        if self.layouts is not None and spec.layout not in self.layouts:
            raise SceneError(
                sid,
                "layout_missing_in_template",
                f"layout {spec.layout} chưa có trong template #88 ở PRODUCE_RENDER_V2 "
                f"(thấy: {', '.join(sorted(self.layouts)) or 'không có'})",
                f"dùng spike #88 có layout này (nhánh {CLAIM_BRANCH} cho layout claim)",
            )

        for seg in scene["narration_segments"]:
            ids: list[str] = []
            for c, refs in zip(spec.claims, spec.claim_refs, strict=True):
                if seg["segment_id"] in c["segment_ids"]:
                    ids += [r for r in refs if r not in ids]
            if not ids and spec.layout == "cta":
                ids = [self.brand_ref]
            if not ids:
                # Câu dẫn M2 không gắn claim (validator #83 vẫn đạt): để fact_refs rỗng, plan #88
                # đánh dấu exempt="lead". Không lấy ref của claim khác (sẽ thành bịa nguồn).
                spec.warnings.append(
                    f"segment_without_claim: câu {seg['segment_id']} không có claim trỏ tới, "
                    "fact_refs để trống"
                )
            spec.seg_refs[seg["segment_id"]] = ids

        if spec.layout == "feature_clip" and not spec.claims:
            raise SceneError(
                sid,
                "scene_without_claim",
                "cảnh clip không có claim nào để làm tiêu đề (chữ trên hình cần fact_refs)",
            )
        if spec.layout == "hook" and not self.script["hook"].get("fact_refs"):
            seg_id = self._hook_segment(spec)
            if seg_id is None or not spec.seg_refs[seg_id]:
                raise SceneError(
                    sid,
                    "hook_without_fact",
                    "hook không có fact_refs và câu đọc nguyên văn hook.text không có claim",
                    "M2 cần gắn claim cho câu đầu (#83: hook nằm trong claim đã đối chiếu)",
                )

        self._pick_asset(spec, kind, vp.get("asset_id"))

    def _hook_segment(self, spec: SceneSpec) -> str | None:
        """Câu đọc nguyên văn `hook.text` (so sau chuẩn hoá khoảng trắng, như validator #83)."""
        hook = " ".join(self.script["hook"]["text"].split())
        for g in spec.scene["narration_segments"]:
            if " ".join(g["text"].split()) == hook:
                return g["segment_id"]
        return None

    def _pick_asset(self, spec: SceneSpec, kind: str | None, asset_id: str | None) -> None:
        sid = spec.scene_id
        found = self.assets.for_scene(sid, asset_id)
        if spec.layout == "feature_clip":
            if found is None or found[1].kind != "clip":
                raise SceneError(
                    sid,
                    "asset_missing",
                    f"cảnh screen_recording cần asset kind=clip, asset_id={asset_id!r} "
                    "không có trong assets.json",
                    "thêm asset (path, crop, parts) vào assets.json",
                )
            spec.asset = found
        elif spec.layout == "hook":
            if found is None:
                spec.warnings.append(
                    "hook_without_image: cảnh hook không có ảnh trong assets.json, "
                    "khung ảnh của layout hook để trống"
                )
            elif found[1].kind != "image":
                # Validator #83 (29f868a) đã chặn hook trỏ asset không phải ảnh ở phía M2; ở đây
                # chỉ báo lỗi rõ ràng, không fallback và không tự đổi asset.
                raise SceneError(sid, "asset_kind", f"hook cần asset kind=image ({found[0]})")
            else:
                spec.asset = found
                if not asset_id:
                    spec.warnings.append(
                        f"scene_asset_override: ảnh {found[0]} gán bằng assets.json, "
                        f"kịch bản M2 không nêu asset_id (visual_plan.kind={kind})"
                    )

    def _derive_cta(self, specs: list[SceneSpec]) -> SceneSpec | None:
        cta = self.script.get("cta")
        if not cta or any(s.scene["role"] == "cta" for s in specs):
            return None
        nums = [int(s.scene_id[1:]) for s in specs if s.scene_id[1:].isdigit()]
        sid = f"s{(max(nums, default=0) + 1):02d}"
        seg_id = f"{sid}-u01"
        scene = {
            "scene_id": sid,
            "role": "cta",
            "narration_segments": [{"segment_id": seg_id, "text": cta["text"]}],
            "claims": [],
        }
        spec = SceneSpec(scene, layout="cta", derived=True)
        spec.seg_refs[seg_id] = [self.brand_ref]
        spec.warnings.append(
            "cta_narration_derived: M2 chỉ có cta.text (nút), không có lời đọc CTA; "
            "worker đọc nguyên văn cta.text. M2 cần sinh lời đọc CTA (#83)"
        )
        return spec

    # ------------------------------------------------------------------ bước 2: sinh plan

    def build_plan(
        self,
        specs: list[SceneSpec],
        voices: dict[str, str],
        timeline: Timeline,
        ratios: list[str],
        source: str,
    ) -> dict[str, Any]:
        scenes = []
        for spec in specs:
            if spec.error is not None:
                continue
            try:
                scenes.append(self._build_scene(spec, voices, timeline.scene(spec.scene_id)))
            except ValueError as ex:  # clip_too_short
                raise SceneError(spec.scene_id, "clip_too_short", str(ex)) from ex
        cfg = self.cfg
        return {
            "schema_version": SCHEMA,
            "product": self.brand,
            "written_by": f"worker.produce từ kịch bản M2 {self.script['schema_version']}",
            "preset": cfg.preset,
            "ratios": ratios,
            "fps": cfg.fps,
            "lead_s": cfg.lead_s,
            "gap_s": cfg.gap_s,
            "tail_s": cfg.tail_s,
            "source": source,
            "facts": dict(self.facts.facts),
            "scenes": scenes,
        }

    def _text(self, text: str, refs: list[str], **extra: Any) -> dict[str, Any]:
        return {"text": text, "fact_refs": refs, **extra}

    def _clip_title(self, spec: SceneSpec) -> tuple[str, list[str]]:
        """Tiêu đề cảnh clip = claim đầu; nếu gần như trùng lời/phụ đề cùng cảnh thì thay bằng
        tên tính năng (`features[i].name`) mà claim đó trỏ tới. Không tạo chữ mới."""
        first, refs = spec.claims[0], spec.claim_refs[0]
        scene = spec.scene
        spoken = " ".join(
            [scene.get("subtitle_text") or ""]
            + [g.get("subtitle_text") or g["text"] for g in scene["narration_segments"]]
        )
        words = set(_words(first["text"]))
        overlap = len(words & set(_words(spoken))) / max(len(words), 1)
        if overlap < TITLE_DUP_OVERLAP:
            return first["text"], refs
        for ref in first["fact_refs"]:
            m = _FEATURE_PATH.fullmatch(ref["field_path"])
            if not m:
                continue
            path = f"{m.group(1)}.name"
            try:
                name = self.facts.text(path)
            except (KeyError, IndexError, TypeError, ValueError, FactError):
                continue
            spec.warnings.append(
                f"title_shortened: tiêu đề trùng {overlap:.0%} lời/phụ đề, dùng {path} '{name}'"
            )
            return name, [self.facts.add(path, ref.get("source_id"))]
        spec.warnings.append(
            f"title_duplicates_subtitle: tiêu đề trùng {overlap:.0%} lời/phụ đề, "
            "claim không trỏ tới features[i] có tên để thay"
        )
        return first["text"], refs

    def _build_scene(
        self, spec: SceneSpec, voices: dict[str, str], ts: TimedScene
    ) -> dict[str, Any]:
        scene = spec.scene
        segs = scene["narration_segments"]
        narration = []
        for g in segs:
            item: dict[str, Any] = {
                "segment_id": g["segment_id"],
                "text": g["text"],
                "voice": voices[g["segment_id"]],
                "fact_refs": spec.seg_refs[g["segment_id"]],
            }
            if not item["fact_refs"]:
                item["exempt"] = "lead"
            sub = scene.get("subtitle_text")
            if len(segs) == 1 and sub and sub != g["text"]:
                item["subtitle_text"] = sub
            narration.append(item)

        out: dict[str, Any] = {
            "scene_id": spec.scene_id,
            "role": scene["role"],
            "layout": spec.layout,
            "narration_segments": narration,
        }
        build = {
            "hook": self._hook,
            "stat": self._stat,
            "feature_clip": self._feature_clip,
            "claim": self._claim,
            "cta": self._cta,
        }[spec.layout or ""]
        build(spec, out, ts)
        return out

    def _hook(self, spec: SceneSpec, out: dict[str, Any], ts: TimedScene) -> None:
        hook = self.script["hook"]
        if hook.get("fact_refs"):
            refs = self.facts.add_refs(hook["fact_refs"])
        else:
            # Contract #83 (73f4df9): hook.text được đọc nguyên văn ở câu đầu và phải nằm trong
            # claim đã đối chiếu, nên nguồn của hook là fact_refs của chính câu đó (đã kiểm ở
            # _classify). Không lấy ref của câu khác.
            seg_id = self._hook_segment(spec)
            assert seg_id is not None
            refs = spec.seg_refs[seg_id]
            spec.warnings.append(
                f"hook_refs_from_segment: hook không có fact_refs, dùng fact_refs của câu {seg_id}"
            )
        props: dict[str, Any] = {
            "brand": self._text(self.brand, [self.brand_ref], icon=self.cfg.brand_icon),
            "title": self._text(hook["text"], refs),
            "chips": [],
        }
        if spec.asset:
            asset = spec.asset[1]
            out["image"] = {
                "path": str(resolve_media(self.base, asset.path)),
                "source": asset.source or asset.path,
            }
            if asset.label:
                props["image"] = {"label": {"text": asset.label, "exempt": "disclosure"}}
        out["props"] = props

    def _stat(self, spec: SceneSpec, out: dict[str, Any], ts: TimedScene) -> None:
        idx = next(i for i, c in enumerate(spec.claims) if c.get("stat_display"))
        sd = spec.claims[idx]["stat_display"]
        refs = spec.claim_refs[idx]
        value = f"{sd['value']} {sd['unit']}" if sd.get("unit") else sd["value"]
        if len(spec.claims) > 1:
            spec.warnings.append(f"claims_not_shown: {len(spec.claims) - 1} claim khác của cảnh")
        out["props"] = {
            "eyebrow": self._text(sd["scope"], refs),
            "value": self._text(value, refs),
            "label": self._text(sd["label"], refs),
            "visual": {"icon": self.cfg.default_icon, "badge_icon": self.cfg.check_icon},
            "chips": [],
        }

    def _claim(self, spec: SceneSpec, out: dict[str, Any], ts: TimedScene) -> None:
        """Layout chỉ chữ: claim đầu to, các claim sau là ý phụ. Nguyên văn, đúng thứ tự."""
        out["props"] = {
            "eyebrow": self._text(self.brand, [self.brand_ref]),
            "icon": self.cfg.default_icon,
            "claim": self._text(spec.claims[0]["text"], spec.claim_refs[0]),
            "points": [
                self._text(c["text"], refs, icon=self.cfg.check_icon)
                for c, refs in zip(spec.claims[1:], spec.claim_refs[1:], strict=True)
            ],
        }

    def _feature_clip(self, spec: SceneSpec, out: dict[str, Any], ts: TimedScene) -> None:
        assert spec.asset is not None
        asset = spec.asset[1]
        if not spec.claims:
            raise SceneError(spec.scene_id, "no_claims", "cảnh clip không có claim để làm tiêu đề")
        kept, warns = fit_parts(asset.parts, ts.duration_s, asset.focus)
        spec.warnings += warns

        crop = asset.crop
        assert crop is not None
        parts = []
        for _, p in kept:
            part: dict[str, Any] = {
                "src": str(resolve_media(self.base, p.path or asset.path)),
                "start_s": p.start_s,
                "end_s": p.end_s,
            }
            if p.crop:
                part["crop"] = list(p.crop)
            parts.append(part)
        clip: dict[str, Any] = {"parts": parts, "crop": list(crop)}
        if asset.crop_by_ratio:
            clip["crop_by_ratio"] = {r: list(c) for r, c in asset.crop_by_ratio.items()}
        f = asset.focus
        if f:
            new_idx = next((n for n, (orig, _) in enumerate(kept) if orig == f.part), None)
            window = kept[new_idx][1] if new_idx is not None else None
            if new_idx is not None and window and window.start_s <= f.source_t <= window.end_s:
                clip["focus"] = {"part": new_idx, "source_t": f.source_t, "rect": list(f.rect)}
            elif focus_offset(asset.parts, f) is None:
                orig = asset.parts[f.part]
                spec.warnings.append(
                    f"focus_dropped: focus.source_t {f.source_t:.2f} nằm ngoài đoạn gốc "
                    f"{orig.start_s:.2f}–{orig.end_s:.2f} (part {f.part}); sửa assets.json"
                )
            else:
                spec.warnings.append("focus_dropped: vùng zoom nằm ngoài đoạn clip đã cắt")
        out["clip"] = clip

        title, title_refs = self._clip_title(spec)
        out["props"] = {
            "eyebrow": self._text(self.brand, [self.brand_ref]),
            "icon": asset.icon or self.cfg.default_icon,
            "title": self._text(title, title_refs),
            "steps": [
                self._text(c["text"], refs, icon=self.cfg.check_icon)
                for c, refs in zip(spec.claims[1:], spec.claim_refs[1:], strict=True)
            ],
            **({"url": self.website} if self.website else {}),
        }

    def _cta(self, spec: SceneSpec, out: dict[str, Any], ts: TimedScene) -> None:
        cta = self.script.get("cta") or {"text": spec.scene["narration_segments"][0]["text"]}
        # Contract #83: `destination: null` thì cảnh CTA không hiện URL/domain (không lấy
        # identity.website thay), chỉ tên sản phẩm + cta.text.
        url = _host(cta["destination"]) if cta.get("destination") else None
        out["props"] = {
            "brand": self._text(self.brand, [self.brand_ref], icon=self.cfg.brand_icon),
            **({"url": url} if url else {}),
            "chips": [],
            "button": {"text": cta["text"], "exempt": "cta"},
        }
