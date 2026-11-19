"""Action-script: danh sách bước xác định, do LLM sinh một lần và Playwright chạy lại nhiều lần.

Ràng buộc an toàn (script do LLM sinh nên không tin đầu vào):
- `goto` chỉ được đi tới đúng host của `url`;
- `upload` chỉ nhận tên file trần, giải trong thư mục fixture, không có đường dẫn hay `..`;
- không có bước chạy JS tuỳ ý.
"""

from __future__ import annotations

import re
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, model_validator

Rect = tuple[int, int, int, int]

# Cùng giá trị crop với các clip tự quay hiện có (assets.json: [440, 0, 1480, 1080]) để layout
# của khâu dựng dùng clip mới như clip cũ.
DEFAULT_CROP: Rect = (440, 0, 1480, 1080)
_ASSET_ID = re.compile(r"^[a-z0-9][a-z0-9-]{1,63}$")
_FILE_NAME = re.compile(r"^[\w][\w .()-]{0,100}$")


class _Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class _Step(_Model):
    # `focus`: vùng của phần tử này là điểm cần zoom; ghi vào `asset.focus` (cần có selector).
    focus: bool = False
    note: str = Field(default="", max_length=200)


class Goto(_Step):
    op: Literal["goto"]
    url: str


class Wait(_Step):
    op: Literal["wait"]
    ms: int = Field(ge=0, le=10_000)


class WaitFor(_Step):
    op: Literal["wait_for"]
    selector: str = Field(min_length=1, max_length=300)
    state: Literal["visible", "hidden", "attached"] = "visible"
    timeout_ms: int = Field(default=15_000, ge=500, le=60_000)


class Hover(_Step):
    op: Literal["hover"]
    selector: str = Field(min_length=1, max_length=300)


class Click(_Step):
    op: Literal["click"]
    selector: str = Field(min_length=1, max_length=300)


class Type(_Step):
    op: Literal["type"]
    selector: str = Field(min_length=1, max_length=300)
    text: str = Field(min_length=1, max_length=300)
    delay_ms: int = Field(default=70, ge=20, le=250)


class Press(_Step):
    op: Literal["press"]
    key: str = Field(min_length=1, max_length=30)


class Upload(_Step):
    op: Literal["upload"]
    selector: str = Field(min_length=1, max_length=300)  # thường là input[type=file], có thể ẩn
    files: list[str] = Field(min_length=1, max_length=10)  # tên file trong thư mục fixture
    # Vùng nhìn thấy (dropzone) để con trỏ di tới trước khi nạp file, vì input thường bị ẩn.
    hover_selector: str | None = Field(default=None, max_length=300)

    @model_validator(mode="after")
    def _names(self) -> Upload:
        for name in self.files:
            if not _FILE_NAME.match(name) or ".." in name:
                raise ValueError(f"tên file fixture không hợp lệ: {name!r}")
        return self


class Scroll(_Step):
    op: Literal["scroll"]
    dy: int = Field(ge=-4000, le=4000)


Step = Annotated[
    Goto | Wait | WaitFor | Hover | Click | Type | Press | Upload | Scroll,
    Field(discriminator="op"),
]


class Viewport(_Model):
    width: int = Field(default=1920, ge=640, le=3840)
    height: int = Field(default=1080, ge=480, le=2160)


class ActionScript(_Model):
    version: Literal[1] = 1
    asset_id: str  # khoá trong assets.json, vd. "pdfcraft-merge-auto"
    url: str  # trang bắt đầu
    viewport: Viewport = Field(default_factory=Viewport)
    crop: Rect = DEFAULT_CROP
    steps: list[Step] = Field(min_length=1, max_length=40)
    # Dấu vân tay DOM lúc sinh script; khác lúc quay lại = UI đã đổi, nên sinh lại.
    dom_hash: str = ""
    generated_by: str = ""

    @model_validator(mode="after")
    def _check(self) -> ActionScript:
        if not _ASSET_ID.match(self.asset_id):
            raise ValueError("asset_id chỉ gồm a-z, 0-9, '-' (2–64 ký tự)")
        host = urlsplit(self.url).hostname
        if urlsplit(self.url).scheme not in ("http", "https") or not host:
            raise ValueError("url phải là http(s)")
        if not isinstance(self.steps[0], Goto):
            raise ValueError("bước đầu tiên phải là goto")
        for i, s in enumerate(self.steps):
            if isinstance(s, Goto) and urlsplit(s.url).hostname != host:
                raise ValueError(f"steps[{i}]: goto chỉ được ở host {host}")
            if s.focus and not hasattr(s, "selector"):
                raise ValueError(f"steps[{i}]: focus cần bước có selector")
        x0, y0, x1, y1 = self.crop
        if not (0 <= x0 < x1 <= self.viewport.width and 0 <= y0 < y1 <= self.viewport.height):
            raise ValueError("crop nằm ngoài viewport")
        return self


class Brief(_Model):
    """Yêu cầu cho một clip: LLM dựa vào đây để sinh script."""

    asset_id: str
    url: str
    goal: str  # clip cần chứng minh điều gì, theo thứ tự thao tác
    facts: list[str] = Field(default_factory=list)  # câu fact PKB mà clip phải minh hoạ
    fixtures: list[str] = Field(default_factory=list)  # file mẫu có sẵn để upload
    crop: Rect = DEFAULT_CROP
