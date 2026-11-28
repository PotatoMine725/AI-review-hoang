"""Danh mục người dùng chọn được cho mỗi job video: template (đọc `templates.json` của spike render)
và giọng VieNeu. Một chỗ duy nhất để API và runner cùng kiểm tra giá trị từ FE."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass

from worker.produce.config import ProduceConfig


@dataclass(frozen=True)
class Voice:
    id: str  # tên preset VieNeu, đúng chuỗi truyền vào `voice=`
    gender: str  # male | female
    region: str  # Bắc | Trung | Nam
    style: str
    featured: bool = False


# Preset của `vieneu/assets/voices_v3_turbo.json` (package 3.8.3, 25 giọng). `featured` = 10 giọng
# tác giả gợi ý, giữ đúng thứ tự của file. Đổi bản VieNeu thì đối chiếu lại danh sách này.
VOICES: tuple[Voice, ...] = (
    Voice("Adam bựa", "male", "Bắc", "Tự nhiên", True),
    Voice("Trúc Ly", "female", "Bắc", "Tự nhiên", True),
    Voice("Thiện Minh", "male", "Bắc", "Kể chuyện", True),
    Voice("Mai Anh", "female", "Bắc", "Tin tức", True),
    Voice("Hải Đăng", "male", "Bắc", "Tự nhiên", True),
    Voice("Thùy Dung", "female", "Nam", "Tin tức", True),
    Voice("Thiền Tâm Đức", "male", "Bắc", "Kể chuyện", True),
    Voice("Ngọc Huyền", "female", "Bắc", "Tự nhiên", True),
    Voice("Quang Sơn", "male", "Trung", "Tự nhiên", True),
    Voice("Ngọc Trân", "female", "Trung", "Tự nhiên", True),
    Voice("Minh Đức", "male", "Bắc", "Tin tức"),
    Voice("Phạm Tuyên", "male", "Bắc", "Tự nhiên"),
    Voice("Thái Sơn", "male", "Nam", "Kể chuyện"),
    Voice("Xuân Vĩnh", "male", "Bắc", "Tự nhiên"),
    Voice("Thanh Bình", "male", "Bắc", "Kể chuyện"),
    Voice("Ngọc Linh", "female", "Bắc", "Kể chuyện"),
    Voice("Đoan Trang", "female", "Bắc", "Tự nhiên"),
    Voice("Thục Đoan", "female", "Nam", "Kể chuyện"),
    Voice("Minh Triết", "male", "Nam", "Tin tức"),
    Voice("Mỹ Duyên", "female", "Nam", "Đọc truyện"),
    Voice("Quỳnh Anh", "female", "Bắc", "Đọc truyện"),
    Voice("Đức Trí", "male", "Nam", "Đọc truyện"),
    Voice("Kim Thanh", "female", "Nam", "Đọc truyện"),
    Voice("Adam", "male", "Nam", "Tự nhiên"),
    Voice("Quốc Tuấn", "male", "Bắc", "Tự nhiên"),
)
VOICE_IDS = frozenset(v.id for v in VOICES)


class CatalogError(ValueError):
    """Giá trị template/giọng không có trong danh mục (lỗi của người gọi, không thử lại)."""


def load_templates(cfg: ProduceConfig) -> tuple[list[dict[str, str]], str] | None:
    """(danh sách {id, name, description}, id mặc định); None khi máy không có spike render."""
    path = cfg.render_v2 / "template" / "templates.json"
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    items = [
        {"id": k, "name": str(t.get("name") or k), "description": str(t.get("description") or "")}
        for k, t in data["templates"].items()
    ]
    return items, str(data["default"])


def catalog(cfg: ProduceConfig) -> dict[str, object]:
    loaded = load_templates(cfg)
    templates, default_template = loaded if loaded else ([], "")
    return {
        "templates": templates,
        "default_template": cfg.template or default_template,
        "voices": [asdict(v) for v in VOICES],
        "default_voice": cfg.voice,
    }


def check_choice(cfg: ProduceConfig, template: object, voice: object) -> None:
    """Kiểm `options.template` / `options.voice` (None = dùng mặc định của máy render).
    Template chỉ kiểm được khi có `templates.json`; không có thì để bước render báo lỗi."""
    if template is not None:
        if not isinstance(template, str) or not template:
            raise CatalogError("options.template phải là chuỗi không rỗng")
        loaded = load_templates(cfg)
        if loaded and template not in {t["id"] for t in loaded[0]}:
            ids = ", ".join(t["id"] for t in loaded[0])
            raise CatalogError(f"options.template không có '{template}' (có: {ids})")
    if voice is not None and (not isinstance(voice, str) or voice not in VOICE_IDS):
        raise CatalogError(f"options.voice không phải giọng VieNeu có sẵn: {voice!r}")
