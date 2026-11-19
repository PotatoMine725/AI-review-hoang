from __future__ import annotations

import pytest
from pydantic import ValidationError

from worker.demo.recorder import HOLD_AT_END_S, ease, mouse_path
from worker.demo.schema import DEFAULT_CROP, ActionScript

BASE = {"asset_id": "demo-merge", "url": "https://example.com/tool"}


def script(steps: list[dict], **extra) -> dict:
    return {**BASE, "steps": steps, **extra}


GOTO = {"op": "goto", "url": "https://example.com/tool"}


def test_default_crop_centres_the_page_and_end_hold_keeps_clip_long_enough() -> None:
    x, y, w, h = DEFAULT_CROP
    # trang 1920 px có nội dung căn giữa (x ≈ 330–1580): crop phải bao trọn, không lệch một bên
    assert x <= 330 and x + w >= 1580 and abs((x + w / 2) - 960) <= 10
    assert (y, h) == (0, 1080) and x + w <= 1920
    assert HOLD_AT_END_S >= 3.0  # clip tự quay 8,4 s từng ngắn hơn cảnh 14,3 s (tua < 0,6×)


def test_valid_script_roundtrip() -> None:
    s = ActionScript.model_validate(
        script([GOTO, {"op": "click", "selector": "#a", "focus": True}, {"op": "wait", "ms": 500}])
    )
    assert ActionScript.model_validate(s.model_dump(mode="json")) == s


@pytest.mark.parametrize(
    "steps",
    [
        [{"op": "click", "selector": "#a"}],  # thiếu goto đầu
        [GOTO, {"op": "goto", "url": "https://evil.test/"}],  # sang host khác
        [GOTO, {"op": "upload", "selector": "input", "files": ["../etc/passwd"]}],
        [GOTO, {"op": "upload", "selector": "input", "files": ["a/b.pdf"]}],
        [GOTO, {"op": "wait", "ms": 99999}],
        [GOTO, {"op": "eval", "js": "alert(1)"}],  # op lạ
        [GOTO, {"op": "wait", "ms": 10, "focus": True}],  # focus cần selector
        [GOTO, {"op": "click", "selector": "#a", "extra": 1}],
    ],
)
def test_rejects_unsafe_or_malformed_steps(steps: list[dict]) -> None:
    with pytest.raises(ValidationError):
        ActionScript.model_validate(script(steps))


def test_rejects_bad_asset_id_and_crop() -> None:
    with pytest.raises(ValidationError):
        ActionScript.model_validate({**script([GOTO]), "asset_id": "../x"})
    with pytest.raises(ValidationError):
        ActionScript.model_validate(script([GOTO], crop=[0, 0, 5000, 1080]))


def test_mouse_path_is_smooth_and_ends_on_target() -> None:
    pts = mouse_path(0, 0, 300, 120, 20)
    assert pts[-1] == (300, 120)
    xs = [p[0] for p in pts]
    assert xs == sorted(xs)  # chỉ tiến
    d = [b - a for a, b in zip(xs, xs[1:], strict=False)]
    assert d[0] < max(d) > d[-1]  # chậm lúc đầu và cuối (ease in-out)
    assert ease(0) == 0 and ease(1) == 1
