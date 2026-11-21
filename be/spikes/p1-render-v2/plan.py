"""Render plan v2: dữ liệu cảnh cho template HTML.

Giữ tên trường của contract M2 (PR #83): `scene_id`, `role`, `narration_segments[].segment_id`,
`fact_refs`. Phần riêng của renderer: `layout`, `props` (dữ liệu đổ vào template), `clip`, `image`.

Luật chữ trên hình (benchmark NotebookLM, #80): mọi chữ hiện trên thẻ phải có `fact_refs` trỏ tới
`facts` của plan. Miễn trừ: cảnh `cta`, URL, và nhãn công khai ("Ảnh minh hoạ do AI tạo").
Phụ đề là bản chép lời đọc nên không thuộc luật này.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Layout = Literal["hook", "stat", "feature_clip", "claim", "cta"]
Ratio = Literal["9:16", "16:9"]

# Khoá props được phép là chuỗi trần (không phải chữ hiển thị cần nguồn).
PLAIN_KEYS = {"url", "src", "icon", "badge_icon"}
# Lý do miễn fact_refs hợp lệ cho một mục chữ.
EXEMPT_REASONS = {"cta", "url", "disclosure"}


class PlanError(ValueError):
    """Plan sai: thiếu nguồn cho chữ, layout không có ô clip, thời lượng ngoài khoảng..."""


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Segment(_Model):
    segment_id: str
    text: str  # lời đọc (đúng câu đã đưa vào TTS)
    voice: str  # file wav đo thật, tương đối với thư mục spike
    fact_refs: list[str] = Field(default_factory=list)  # câu thoại trỏ tới facts (#80, #83)
    # "lead": câu dẫn M2 không mang claim (validator #83 cho phép), được để fact_refs rỗng.
    exempt: Literal["lead"] | None = None
    subtitle_text: str | None = None  # chữ phụ đề nếu khác lời đọc (vd URL viết liền)

    @model_validator(mode="after")
    def _refs(self) -> Segment:
        if not self.fact_refs and self.exempt is None:
            msg = f"{self.segment_id}: câu thoại thiếu fact_refs (câu dẫn: exempt='lead')"
            raise ValueError(msg)
        return self

    @property
    def caption(self) -> str:
        return self.subtitle_text or self.text


class ClipPart(_Model):
    src: str
    start_s: float = Field(ge=0)
    end_s: float
    # Vùng cắt [x, y, w, h] theo pixel nguồn; bỏ trống thì dùng `Clip.crop`.
    crop: tuple[int, int, int, int] | None = None

    @model_validator(mode="after")
    def _order(self) -> ClipPart:
        if self.end_s <= self.start_s:
            raise ValueError(f"đoạn clip {self.src}: end_s phải > start_s")
        return self

    @property
    def length_s(self) -> float:
        return self.end_s - self.start_s


class ClipFocus(_Model):
    """Vùng cần zoom: thời điểm theo clip nguồn + hình chữ nhật [x, y, w, h] pixel nguồn."""

    part: int = Field(ge=0)
    source_t: float
    rect: tuple[int, int, int, int]


class Clip(_Model):
    parts: list[ClipPart] = Field(min_length=1)
    crop: tuple[int, int, int, int]
    # Vùng cắt riêng cho từng tỉ lệ (vd 16:9 cắt rộng, 9:16 cắt gần vuông để ô clip to hơn);
    # tỉ lệ không có ở đây dùng `crop`. Không áp cho đoạn có `ClipPart.crop` riêng.
    crop_by_ratio: dict[Ratio, tuple[int, int, int, int]] = Field(default_factory=dict)
    focus: ClipFocus | None = None
    clip_refs: list[str] = Field(default_factory=list)  # bằng chứng clip (V01...) trong facts

    def for_ratio(self, ratio: Ratio) -> Clip:
        """Bản clip dùng cho `ratio`: `crop` = vùng cắt của tỉ lệ đó, bỏ `crop_by_ratio`."""
        crop = self.crop_by_ratio.get(ratio, self.crop)
        return self.model_copy(update={"crop": crop, "crop_by_ratio": {}})


class Image(_Model):
    path: str
    source: str  # ghi nguồn (vd "Cloudflare FLUX, #71")


class Scene(_Model):
    scene_id: str
    role: str
    layout: Layout
    narration_segments: list[Segment] = Field(min_length=1)
    props: dict[str, Any]
    clip: Clip | None = None
    image: Image | None = None


class RenderPlan(_Model):
    schema_version: Literal["render-plan.v2-spike"]
    product: str
    # Ai viết lời đọc: "viết tay", "agent"... Chưa phải LLM của pipeline M2 (#83).
    written_by: str = Field(min_length=1)
    preset: str
    ratios: list[Ratio]
    fps: int = 30
    lead_s: float = 0.1  # trước câu đầu tiên
    gap_s: float = Field(default=0.12, le=0.15)  # nghỉ giữa hai câu (tiêu chí ≤ 0,15 s)
    tail_s: float = 0.6  # giữ khung CTA sau câu cuối
    source: str = ""  # ghi chú nguồn của lời đọc / facts
    facts: dict[str, str]  # id → trích dẫn nguyên văn (lấy từ p1-demo-pdfcraft/facts.json)
    scenes: list[Scene] = Field(min_length=1)

    @model_validator(mode="after")
    def _check(self) -> RenderPlan:
        ids = [s.scene_id for s in self.scenes]
        if len(set(ids)) != len(ids):
            raise ValueError("scene_id bị trùng")
        seg_ids = [g.segment_id for s in self.scenes for g in s.narration_segments]
        if len(set(seg_ids)) != len(seg_ids):
            raise ValueError("segment_id bị trùng")
        for scene in self.scenes:
            for seg in scene.narration_segments:
                missing = [r for r in seg.fact_refs if r not in self.facts]
                if missing:
                    raise ValueError(f"{seg.segment_id}: fact_refs không có trong facts: {missing}")
            check_props(scene, set(self.facts))
            if scene.layout == "feature_clip" and scene.clip is None:
                raise ValueError(f"{scene.scene_id}: layout feature_clip cần `clip`")
            if scene.clip:
                missing = [r for r in scene.clip.clip_refs if r not in self.facts]
                if missing:
                    raise ValueError(f"{scene.scene_id}: clip_refs không có trong facts: {missing}")
                focus = scene.clip.focus
                if focus and focus.part >= len(scene.clip.parts):
                    raise ValueError(f"{scene.scene_id}: clip.focus.part vượt số đoạn clip")
        return self


def _walk_text_items(value: Any, path: str):
    """Duyệt props, trả (đường dẫn, mục) cho mọi chữ hiển thị: dict có 'text' hoặc chuỗi trần."""
    if isinstance(value, dict):
        if "text" in value:
            yield path, value
        for key, child in value.items():
            if key in {"text", "highlight", "fact_refs", "exempt", "accent"}:
                continue
            if isinstance(child, str):
                if key not in PLAIN_KEYS:
                    yield f"{path}.{key}", child
            else:
                yield from _walk_text_items(child, f"{path}.{key}")
    elif isinstance(value, list):
        for i, child in enumerate(value):
            yield from _walk_text_items(child, f"{path}[{i}]")
    elif isinstance(value, str):
        yield path, value


def check_props(scene: Scene, fact_ids: set[str]) -> None:
    """Chữ trên hình phải có fact_refs hợp lệ (trừ cảnh cta, URL, nhãn công khai)."""
    problems: list[str] = []
    for path, item in _walk_text_items(scene.props, "props"):
        if isinstance(item, str):
            if scene.layout != "cta":
                problems.append(f"{path}: chữ trần '{item}' không có fact_refs")
            continue
        refs = item.get("fact_refs") or []
        exempt = item.get("exempt")
        if exempt is not None and exempt not in EXEMPT_REASONS:
            problems.append(f"{path}: lý do miễn '{exempt}' không hợp lệ")
        if not refs and exempt is None and scene.layout != "cta":
            problems.append(f"{path}: '{item['text']}' thiếu fact_refs")
        unknown = [r for r in refs if r not in fact_ids]
        if unknown:
            problems.append(f"{path}: fact_refs không có trong facts: {unknown}")
        hl = item.get("highlight")
        if hl and hl not in item["text"]:
            problems.append(f"{path}: highlight '{hl}' không nằm trong chữ")
    if problems:
        raise PlanError(f"{scene.scene_id}: " + "; ".join(problems))


def load_plan(path: Path) -> RenderPlan:
    data = json.loads(path.read_text(encoding="utf-8"))
    return RenderPlan.model_validate(data)
