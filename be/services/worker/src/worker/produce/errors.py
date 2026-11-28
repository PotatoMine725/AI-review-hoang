"""Lỗi của đường ghép. Mọi lỗi dự đoán được đều có `code` ổn định để ghi vào report."""

from __future__ import annotations


class ProduceError(Exception):
    """Lỗi chặn cả lần chạy (đầu vào sai, thiếu công cụ, subprocess hỏng)."""


class ProduceAuthError(ProduceError):
    """Dịch vụ ngoài từ chối khoá (401/403): thử tiếp các câu/khung khác cũng vô ích."""


class SceneError(ProduceError):
    """Lỗi của một cảnh: không có layout tương ứng, thiếu asset, clip quá ngắn...

    Không bịa layout: cảnh M2 không ánh xạ được thì báo đúng cảnh đó kèm gợi ý cho M2.
    """

    def __init__(self, scene_id: str, code: str, message: str, hint: str = "") -> None:
        self.scene_id = scene_id
        self.code = code
        self.message = message
        self.hint = hint
        super().__init__(f"{scene_id}: [{code}] {message}" + (f" Gợi ý: {hint}" if hint else ""))
