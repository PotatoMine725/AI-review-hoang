"""Chạy action-script bằng Playwright, có con trỏ giả và nhịp thao tác như người dùng thật.

Hai chế độ:
- `fast=True`: chạy thử (dry-run) khi sinh script, không ghi hình, không nghỉ, gõ bằng `fill`.
- `fast=False`: quay thật (`record_video_dir`), di chuột mượt, gõ chậm, chờ giữa các bước.
"""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from playwright.sync_api import Error as PlaywrightError
from playwright.sync_api import Locator, Page, Playwright, ViewportSize, sync_playwright

from worker.demo import dom
from worker.demo.schema import (
    ActionScript,
    Click,
    Goto,
    Hover,
    Press,
    Scroll,
    Type,
    Upload,
    Wait,
    WaitFor,
)

HOLD_AFTER_LOAD_S = 0.8  # để người xem thấy trang trước khi thao tác
HOLD_AT_END_S = 1.5
THINK_S = 0.35  # nghỉ ngắn giữa hai thao tác

# Con trỏ giả: video của Playwright không có con trỏ hệ điều hành, nên vẽ bằng DOM.
# Vị trí lưu trong sessionStorage để không "nhảy về góc" khi trang điều hướng.
CURSOR_JS = """
(() => {
  const ID = '__demo_cursor';
  const mount = () => {
    if (document.getElementById(ID)) return;
    const st = document.createElement('style');
    st.textContent = '@keyframes __demo_ripple{from{transform:scale(.3);opacity:.7}'
      + 'to{transform:scale(2.4);opacity:0}}';
    const c = document.createElement('div');
    c.id = ID;
    c.style.cssText = 'position:fixed;left:0;top:0;width:26px;height:26px;z-index:2147483647;'
      + 'pointer-events:none;will-change:transform;filter:drop-shadow(0 1px 2px rgba(0,0,0,.45))';
    c.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24"><path d="M3 2l7 19 2.8-7.7'
      + 'L21 11z" fill="#111" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
    const put = (x, y) => {
      c.style.transform = `translate(${x - 3}px,${y - 2}px)`;
      try { sessionStorage.setItem('__dc', JSON.stringify([x, y])); } catch (e) {}
    };
    let p = [-40, -40];
    try { p = JSON.parse(sessionStorage.getItem('__dc')) || p; } catch (e) {}
    put(p[0], p[1]);
    document.documentElement.append(st, c);
    addEventListener('mousemove', (e) => put(e.clientX, e.clientY), true);
    addEventListener('mousedown', (e) => {
      const r = document.createElement('div');
      r.style.cssText = `position:fixed;left:${e.clientX - 16}px;top:${e.clientY - 16}px;`
        + 'width:32px;height:32px;border-radius:50%;background:rgba(59,130,246,.55);'
        + 'z-index:2147483646;pointer-events:none;animation:__demo_ripple .45s ease-out forwards';
      document.documentElement.append(r);
      setTimeout(() => r.remove(), 500);
    }, true);
  };
  if (document.readyState === 'loading') addEventListener('DOMContentLoaded', mount);
  else mount();
})();
"""


class StepFailure(Exception):
    """Một bước thất bại. Kèm DOM lúc đó để LLM sửa script."""

    def __init__(self, index: int, op: str, message: str, snap: dict[str, Any] | None) -> None:
        self.index = index
        self.op = op
        self.message = message
        self.snap = snap
        super().__init__(f"bước {index} ({op}): {message}")


@dataclass
class Focus:
    t_s: float
    rect: tuple[int, int, int, int]
    step: int


@dataclass
class ReplayResult:
    webm: Path | None = None
    start_s: float = 0.0  # mốc nội dung bắt đầu (sau khi trang tải xong)
    end_s: float = 0.0
    focus: Focus | None = None
    step_times_s: list[float] = field(default_factory=list)
    dom_hash: str = ""  # hash DOM trang đầu tại lúc chạy


def ease(t: float) -> float:
    """easeInOutCubic: bắt đầu và dừng nhẹ như tay người."""
    return 4 * t**3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def mouse_path(x0: float, y0: float, x1: float, y1: float, steps: int) -> list[tuple[float, float]]:
    return [
        (x0 + (x1 - x0) * ease(i / steps), y0 + (y1 - y0) * ease(i / steps))
        for i in range(1, steps + 1)
    ]


def _launch(pw: Playwright, chromium_path: str | None, headless: bool):
    return pw.chromium.launch(
        headless=headless,
        executable_path=chromium_path or None,
        args=["--hide-scrollbars", "--force-color-profile=srgb"],
    )


class _Runner:
    def __init__(
        self,
        page: Page,
        script: ActionScript,
        fixtures: Path,
        fast: bool,
        clock: Callable[[], float],
    ) -> None:
        self.page = page
        self.script = script
        self.fixtures = fixtures
        self.fast = fast
        self.clock = clock
        self.pos = (-40.0, -40.0)
        self.result = ReplayResult()

    # --- nhịp ---
    def pause(self, seconds: float) -> None:
        if not self.fast and seconds > 0:
            self.page.wait_for_timeout(seconds * 1000)

    def _loc(self, selector: str) -> Locator:
        return self.page.locator(selector)

    def _center(self, loc: Locator) -> tuple[float, float]:
        loc.scroll_into_view_if_needed(timeout=8000)
        box = loc.bounding_box(timeout=8000)
        if not box:
            raise PlaywrightError("phần tử không có hộp hiển thị")
        return box["x"] + box["width"] / 2, box["y"] + box["height"] / 2

    def move_to(self, x: float, y: float) -> None:
        x0, y0 = self.pos
        if self.fast:
            self.page.mouse.move(x, y)
        else:
            dist = ((x - x0) ** 2 + (y - y0) ** 2) ** 0.5
            steps = max(12, min(70, int(dist / 12)))
            duration = max(0.35, min(1.1, 0.25 + dist / 1800))
            for px, py in mouse_path(x0, y0, x, y, steps):
                self.page.mouse.move(px, py)
                self.page.wait_for_timeout(duration * 1000 / steps)
        self.pos = (x, y)

    def _focus(self, index: int, loc: Locator) -> None:
        box = loc.bounding_box()
        if box:
            rect = (round(box["x"]), round(box["y"]), round(box["width"]), round(box["height"]))
            self.result.focus = Focus(self.clock(), rect, index)

    # --- bước ---
    def run_step(self, index: int, step: Any) -> None:
        match step:
            case Goto():
                self.page.goto(step.url, wait_until="load", timeout=45_000)
                self.page.wait_for_load_state("networkidle", timeout=15_000)
                if index == 0:
                    self.result.dom_hash = dom.dom_hash(dom.snapshot(self.page))
                    self.pause(HOLD_AFTER_LOAD_S)
                    self.result.start_s = max(0.0, self.clock() - 0.3)
            case Wait():
                self.pause(step.ms / 1000)
            case WaitFor():
                self._loc(step.selector).wait_for(state=step.state, timeout=step.timeout_ms)
            case Hover():
                loc = self._loc(step.selector)
                self.move_to(*self._center(loc))
                self.pause(THINK_S)
                if step.focus:
                    self._focus(index, loc)
            case Click():
                loc = self._loc(step.selector)
                self.move_to(*self._center(loc))
                self.pause(0.15)
                loc.click(timeout=8000)
                self.pause(THINK_S)
                if step.focus:
                    self._focus(index, loc)
            case Type():
                loc = self._loc(step.selector)
                self.move_to(*self._center(loc))
                loc.click(timeout=8000)
                if self.fast:
                    loc.fill(step.text, timeout=8000)
                else:
                    self.page.keyboard.type(step.text, delay=step.delay_ms)
                self.pause(THINK_S)
                if step.focus:
                    self._focus(index, loc)
            case Press():
                self.page.keyboard.press(step.key)
                self.pause(THINK_S)
            case Upload():
                paths = [self._fixture(n) for n in step.files]
                if step.hover_selector:
                    self.move_to(*self._center(self._loc(step.hover_selector)))
                    self.pause(0.4)
                loc = self._loc(step.selector)
                loc.set_input_files([str(p) for p in paths], timeout=8000)
                self.pause(THINK_S)
                if step.focus:
                    self._focus(index, self._loc(step.hover_selector or step.selector))
            case Scroll():
                self._scroll(step.dy)
            case _:  # pragma: no cover - union đã đủ
                raise PlaywrightError(f"op không hỗ trợ: {step!r}")

    def _fixture(self, name: str) -> Path:
        p = (self.fixtures / name).resolve()
        if not p.is_file() or self.fixtures.resolve() not in p.parents:
            raise PlaywrightError(f"không có file fixture {name} trong {self.fixtures}")
        return p

    def _scroll(self, dy: int) -> None:
        if self.fast:
            self.page.mouse.wheel(0, dy)
            return
        steps = max(6, abs(dy) // 40)
        done = 0
        for i in range(1, steps + 1):
            target = round(dy * ease(i / steps))
            self.page.mouse.wheel(0, target - done)
            done = target
            self.page.wait_for_timeout(16)
        self.pause(THINK_S)


def replay(
    script: ActionScript,
    *,
    fixtures_dir: Path,
    record_dir: Path | None = None,
    fast: bool = False,
    chromium_path: str | None = None,
    headless: bool = True,
) -> ReplayResult:
    """Chạy script. `record_dir` đặt = có quay (ra file .webm). Lỗi bước → `StepFailure`."""
    with sync_playwright() as pw:
        browser = _launch(pw, chromium_path, headless)
        try:
            vp = ViewportSize(width=script.viewport.width, height=script.viewport.height)
            ctx = browser.new_context(
                viewport=vp,
                device_scale_factor=1,
                color_scheme="light",
                accept_downloads=True,
                record_video_dir=str(record_dir) if record_dir else None,
                record_video_size=vp if record_dir else None,
            )
            ctx.add_init_script(CURSOR_JS)
            ctx.set_default_timeout(15_000)
            page = ctx.new_page()
            t0 = time.monotonic()
            runner = _Runner(page, script, fixtures_dir, fast, lambda: time.monotonic() - t0)
            for i, step in enumerate(script.steps):
                try:
                    runner.run_step(i, step)
                except PlaywrightError as ex:
                    snap = _safe_snapshot(page)
                    raise StepFailure(i, step.op, str(ex).splitlines()[0][:300], snap) from ex
                runner.result.step_times_s.append(round(runner.clock(), 3))
            runner.pause(HOLD_AT_END_S)
            runner.result.end_s = runner.clock()
            video = page.video
            ctx.close()  # chốt file video
            if record_dir and video:
                runner.result.webm = Path(video.path())
            return runner.result
        finally:
            browser.close()


def _safe_snapshot(page: Page) -> dict[str, Any] | None:
    try:
        return dom.snapshot(page)
    except PlaywrightError:
        return None
