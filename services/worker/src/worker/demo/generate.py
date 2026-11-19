"""Sinh action-script bằng LLM, chạy thử trên trang thật, lỗi thì đưa lại cho LLM sửa."""

from __future__ import annotations

import json
import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from playwright.sync_api import sync_playwright
from pydantic import ValidationError

from worker.demo import dom
from worker.demo.errors import DemoError
from worker.demo.llm import ScriptLLM
from worker.demo.recorder import ReplayResult, StepFailure, _launch, replay
from worker.demo.schema import ActionScript, Brief, Viewport

log = logging.getLogger("worker.demo")

SYSTEM = """\
You write deterministic browser action scripts that a Playwright runner replays to record a \
short product-demo screen clip. You never drive the browser yourself.

Reply with ONE JSON object: {"steps": [...]}. No markdown, no comments.

Allowed steps (field "op"):
- {"op":"goto","url":...}                      first step only, same host as the start page
- {"op":"wait","ms":0-10000}                   pause so a viewer can read
- {"op":"wait_for","selector":...,"state":"visible|hidden|attached","timeout_ms":...}
- {"op":"hover"|"click","selector":...}
- {"op":"type","selector":...,"text":...,"delay_ms":20-250}
- {"op":"press","key":"Enter"}
- {"op":"upload","selector":"input[type=file]","files":["name.pdf"],
  "hover_selector":<visible dropzone>}
- {"op":"scroll","dy":-4000..4000}
Any step may carry "focus": true (needs a selector): marks the element a later zoom should \
target. Use it once, on the element that proves the claim (e.g. the result or download button).

Rules:
- Selectors are Playwright selectors and MUST match exactly one element (strict mode; use
  "... >> nth=0" when several match). Prefer the "selector" hints in the DOM list. Never invent \
elements that are not in the DOM list, except elements that only appear after your own actions: \
for those use role/text selectors and ALWAYS place a wait_for before using them.
- Upload only file names from "fixtures". Never type secrets or personal data.
- Show the flow a viewer needs, in order: page ready, add input, run the action, the result \
visible. 8-20 steps. Put a short "wait" (600-1500 ms) before the final result so it can be read.
- Do not navigate to other hosts, do not click ads, cookie banners may be dismissed with one click.
- Fix only what the error says when repairing; keep working steps unchanged.
"""


def _compact(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, separators=(",", ":"))


def build_prompt(
    brief: Brief,
    snap: dict[str, Any],
    *,
    previous: list[dict[str, Any]] | None = None,
    error: str | None = None,
    fail_snap: dict[str, Any] | None = None,
) -> str:
    parts = [
        f"Clip goal: {brief.goal}",
        f"Product facts the clip must illustrate: {_compact(brief.facts)}",
        f"fixtures (files available for upload): {_compact(brief.fixtures)}",
        f"Start page DOM: {_compact(snap)}",
    ]
    if previous is not None:
        parts += [
            f"Your previous script steps: {_compact(previous)}",
            f"It failed: {error}",
        ]
        if fail_snap:
            parts.append(f"DOM at the moment of failure: {_compact(fail_snap)}")
        parts.append('Return the corrected full {"steps": [...]}.')
    return "\n\n".join(parts)


def parse_script(raw: str, brief: Brief, *, generated_by: str, dom_hash: str) -> ActionScript:
    """Chỉ lấy `steps` từ LLM; asset_id/url/crop luôn lấy từ brief (không tin LLM)."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as ex:
        raise ValueError(f"không phải JSON: {ex}") from ex
    if not isinstance(data, dict) or not isinstance(data.get("steps"), list):
        raise ValueError('thiếu {"steps": [...]}')
    return ActionScript.model_validate(
        {
            "asset_id": brief.asset_id,
            "url": brief.url,
            "crop": brief.crop,
            "steps": data["steps"],
            "dom_hash": dom_hash,
            "generated_by": generated_by,
        }
    )


def _check_fixtures(script: ActionScript, brief: Brief) -> None:
    for i, s in enumerate(script.steps):
        for name in getattr(s, "files", []):
            if name not in brief.fixtures:
                raise ValueError(f"steps[{i}]: file {name!r} không có trong fixtures")


def snapshot_url(url: str, *, chromium_path: str | None = None, headless: bool = True) -> dict:
    vp = Viewport()
    with sync_playwright() as pw:
        browser = _launch(pw, chromium_path, headless)
        try:
            page = browser.new_page(viewport={"width": vp.width, "height": vp.height})
            page.goto(url, wait_until="load", timeout=45_000)
            page.wait_for_load_state("networkidle", timeout=15_000)
            return dom.snapshot(page)
        finally:
            browser.close()


def generate(
    brief: Brief,
    llm: ScriptLLM,
    *,
    fixtures_dir: Path,
    chromium_path: str | None = None,
    headless: bool = True,
    max_rounds: int = 4,
    snapshot: Callable[[str], dict[str, Any]] | None = None,
    dry_run: Callable[[ActionScript], ReplayResult] | None = None,
) -> ActionScript:
    """Vòng: sinh → kiểm schema → chạy thử → (lỗi) sửa. Tối đa `max_rounds` lần gọi LLM."""
    snap = (
        snapshot or (lambda u: snapshot_url(u, chromium_path=chromium_path, headless=headless))
    )(brief.url)
    h = dom.dom_hash(snap)
    run = dry_run or (
        lambda s: replay(
            s, fixtures_dir=fixtures_dir, fast=True, chromium_path=chromium_path, headless=headless
        )
    )
    previous: list[dict[str, Any]] | None = None
    error: str | None = None
    fail_snap: dict[str, Any] | None = None
    for round_no in range(1, max_rounds + 1):
        raw = llm.complete(
            SYSTEM, build_prompt(brief, snap, previous=previous, error=error, fail_snap=fail_snap)
        )
        try:
            script = parse_script(raw, brief, generated_by=llm.name, dom_hash=h)
            _check_fixtures(script, brief)
        except (ValueError, ValidationError) as ex:
            log.warning("vòng %d: script sai schema: %s", round_no, str(ex)[:300])
            previous, error, fail_snap = _prev_steps(raw), f"schema: {str(ex)[:600]}", None
            continue
        try:
            run(script)
        except StepFailure as ex:
            log.warning("vòng %d: %s", round_no, ex)
            previous = [s.model_dump(exclude_defaults=True) for s in script.steps]
            error, fail_snap = f"step index {ex.index} ({ex.op}): {ex.message}", ex.snap
            continue
        log.info("vòng %d: script chạy thử OK (%d bước)", round_no, len(script.steps))
        return script
    raise DemoError(f"không sinh được script chạy được sau {max_rounds} vòng; lỗi cuối: {error}")


def _prev_steps(raw: str) -> list[dict[str, Any]]:
    try:
        steps = json.loads(raw).get("steps", [])
        return steps if isinstance(steps, list) else []
    except (json.JSONDecodeError, AttributeError):
        return []
