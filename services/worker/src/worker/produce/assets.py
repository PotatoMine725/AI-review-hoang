"""Bảng `asset_id` → file media. TẠM THỜI, thay cho BE Storage (chưa có).

File `assets.json`:

    {
      "note": "tạm, thay cho BE Storage",
      "assets": {
        "pdfcraft-merge": {
          "kind": "clip", "path": "clips/pdfcraft-merge.mp4", "crop": [440, 0, 1480, 1080],
          "parts": [{"start_s": 9.8, "end_s": 17.6}],
          "focus": {"part": 0, "source_t": 16.0, "rect": [520, 110, 560, 330]}
        },
        "ai-paperwork": {"kind": "image", "path": "ai/paperwork-s1.jpg",
                         "label": "Ảnh minh hoạ do AI tạo", "source": "Cloudflare FLUX (#71)"}
      },
      "scene_assets": {"s01": "ai-paperwork"}
    }

`scene_assets` gán asset cho cảnh mà kịch bản M2 không nêu `asset_id` (vd. ảnh của cảnh hook
dạng text_card). Đường dẫn tương đối tính từ thư mục chứa `assets.json`.
Crop, đoạn clip và vùng zoom là quyết định biên tập, M2 không sinh ra chúng.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from worker.produce.errors import ProduceError

Rect = tuple[int, int, int, int]


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AssetPart(_Model):
    start_s: float = Field(ge=0)
    end_s: float
    path: str | None = None  # đoạn lấy từ file khác của cùng asset; bỏ trống = `Asset.path`
    crop: Rect | None = None

    @model_validator(mode="after")
    def _order(self) -> AssetPart:
        if self.end_s <= self.start_s:
            raise ValueError("end_s phải > start_s")
        return self

    @property
    def length_s(self) -> float:
        return self.end_s - self.start_s


class AssetFocus(_Model):
    part: int = Field(ge=0)
    source_t: float
    rect: Rect


class Asset(_Model):
    kind: Literal["clip", "image"]
    path: str
    crop: Rect | None = None  # bắt buộc với clip
    # vùng cắt riêng theo tỉ lệ ("16:9"/"9:16") để ô clip to hơn; thiếu thì dùng `crop` (#88)
    crop_by_ratio: dict[Literal["16:9", "9:16"], Rect] = Field(default_factory=dict)
    parts: list[AssetPart] = Field(default_factory=list)
    focus: AssetFocus | None = None
    icon: str | None = None
    label: str | None = None  # nhãn công khai trên ảnh, vd. "Ảnh minh hoạ do AI tạo"
    source: str | None = None

    @model_validator(mode="after")
    def _kind(self) -> Asset:
        if self.kind == "clip":
            if self.crop is None or not self.parts:
                raise ValueError("clip cần `crop` và ít nhất một mục trong `parts`")
            if self.focus and self.focus.part >= len(self.parts):
                raise ValueError("focus.part vượt số đoạn clip")
        return self


class AssetsFile(_Model):
    note: str = ""
    assets: dict[str, Asset]
    scene_assets: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _refs(self) -> AssetsFile:
        unknown = sorted(set(self.scene_assets.values()) - set(self.assets))
        if unknown:
            raise ValueError(f"scene_assets trỏ tới asset không có: {unknown}")
        return self

    def for_scene(self, scene_id: str, asset_id: str | None) -> tuple[str, Asset] | None:
        """Asset của cảnh: `asset_id` của M2 nếu có, không thì `scene_assets[scene_id]`."""
        key = asset_id or self.scene_assets.get(scene_id)
        if key is None:
            return None
        asset = self.assets.get(key)
        return (key, asset) if asset else None


def load_assets(path: Path) -> tuple[AssetsFile, Path]:
    """Trả (nội dung, thư mục gốc để giải đường dẫn tương đối)."""
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return AssetsFile.model_validate(data), path.resolve().parent
    except (OSError, ValueError) as ex:
        raise ProduceError(f"assets.json không đọc được ({path}): {ex}") from ex


def resolve_media(base: Path, rel: str) -> Path:
    """Đường dẫn tuyệt đối của file media; không có file thì báo ngay (trước khi tốn công TTS)."""
    p = Path(rel)
    p = p if p.is_absolute() else (base / p)
    p = p.resolve()
    if not p.is_file():
        raise ProduceError(f"thiếu file media {p}")
    return p
