"""Render plan: mô tả 1 video độc lập với tỉ lệ khung (Pydantic v2).

1 plan dựng được cả 9:16 lẫn 16:9. Đường dẫn trong file JSON tính từ thư mục chứa file plan.
Plan độc lập với `script.v0.schema.json` của M2 (schema đó cố định `language: "en"` và
`aspect_ratio: "9:16"`; P1 cần tiếng Việt và 2 tỉ lệ — xem README, mục câu hỏi mở).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

MIN_SCENES = 1
MAX_SCENES = 12  # trần kỹ thuật của filter graph (chưa đo nhiều hơn); độ dài chặn theo config.py

Role = Literal["hook", "problem", "demo", "result", "proof", "cta"]
Kind = Literal["image", "video", "text_card"]


class PlanError(ValueError):
    """Plan sai: báo lỗi rõ cho người dùng, không chạy ffmpeg."""


class Scene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    role: Role  # Hook → Problem → Demo → Result → CTA
    kind: Kind  # image = ảnh tĩnh + Ken Burns; video = clip (vd cảnh AI); text_card = thẻ chữ
    asset: str | None = None  # bắt buộc với image/video
    caption: str = Field(min_length=1, max_length=200)  # tiếng Việt; hiện thành phụ đề
    voice: str | None = None  # file audio của cảnh; không có = cảnh im lặng
    min_duration_s: float = Field(default=2.0, gt=0)  # trần tổng nằm ở config.py, không ở cảnh
    source: str | None = None  # ghi nguồn asset (fixture, AI thật + request id, ...)

    @model_validator(mode="after")
    def _check_asset(self) -> Self:
        if self.kind in ("image", "video") and not self.asset:
            raise ValueError(f"cảnh {self.kind} cần 'asset'")
        if self.kind == "text_card" and self.asset:
            raise ValueError("text_card không dùng 'asset'")
        return self


class RenderPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    preset: str  # id preset (presets.PRESETS)
    scenes: list[Scene] = Field(min_length=MIN_SCENES, max_length=MAX_SCENES)
    music: str | None = None  # nhạc nền tuỳ chọn; tự nhỏ đi khi có voice
    language: Literal["vi"] = "vi"


def load_plan(path: Path) -> RenderPlan:
    """Đọc plan JSON, kiểm tra schema và sự tồn tại của file; trả plan với đường dẫn tuyệt đối."""
    path = path.resolve()
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise PlanError(f"không thấy file plan: {path}") from None
    except json.JSONDecodeError as exc:
        raise PlanError(f"{path.name} không phải JSON hợp lệ: {exc}") from exc
    try:
        plan = RenderPlan.model_validate(raw)
    except ValidationError as exc:
        lines = [f"{'.'.join(str(p) for p in e['loc'])}: {e['msg']}" for e in exc.errors()]
        raise PlanError(f"plan {path.name} sai schema:\n  " + "\n  ".join(lines)) from exc

    base = path.parent

    def resolve(rel: str, what: str) -> str:
        target = (base / rel).resolve()
        if not target.is_file():
            raise PlanError(f"{what} không tồn tại: {target}")
        return str(target)

    for i, scene in enumerate(plan.scenes, start=1):
        if scene.asset:
            scene.asset = resolve(scene.asset, f"cảnh {i}: asset")
        if scene.voice:
            scene.voice = resolve(scene.voice, f"cảnh {i}: voice")
    if plan.music:
        plan.music = resolve(plan.music, "nhạc nền")
    return plan
