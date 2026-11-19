from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from worker.demo.errors import DemoError
from worker.demo.generate import build_prompt, generate, parse_script
from worker.demo.recorder import ReplayResult, StepFailure
from worker.demo.schema import ActionScript, Brief

BRIEF = Brief(
    asset_id="demo-merge",
    url="https://example.com/tool",
    goal="Ghép 2 PDF",
    facts=["Bấm Merge để gộp tất cả tệp thành một PDF"],
    fixtures=["a.pdf", "b.pdf"],
)
SNAP: dict[str, Any] = {"title": "t", "url": BRIEF.url, "headings": [], "elements": [
    {"tag": "button", "text": "Merge", "selector": "#merge", "box": [0, 0, 1, 1]}
]}  # fmt: skip
GOTO = {"op": "goto", "url": BRIEF.url}


class FakeLLM:
    name = "fake:test"

    def __init__(self, *replies: dict | str) -> None:
        self.replies = list(replies)
        self.prompts: list[str] = []

    def complete(self, system: str, user: str) -> str:
        self.prompts.append(user)
        r = self.replies.pop(0)
        return r if isinstance(r, str) else json.dumps(r)


def _gen(llm: FakeLLM, dry_run, **kw) -> ActionScript:
    return generate(
        BRIEF, llm, fixtures_dir=Path("."), snapshot=lambda _u: SNAP, dry_run=dry_run, **kw
    )


def test_parse_forces_brief_fields_and_ignores_llm_url() -> None:
    raw = json.dumps({"steps": [GOTO], "url": "https://evil.test", "asset_id": "x"})
    s = parse_script(raw, BRIEF, generated_by="m", dom_hash="h")
    assert (s.asset_id, s.url, s.dom_hash, s.generated_by) == ("demo-merge", BRIEF.url, "h", "m")


def test_generate_ok_first_round() -> None:
    llm = FakeLLM({"steps": [GOTO, {"op": "click", "selector": "#merge"}]})
    s = _gen(llm, lambda _s: ReplayResult())
    assert len(s.steps) == 2 and s.dom_hash and s.generated_by == "fake:test"
    assert len(llm.prompts) == 1 and "#merge" in llm.prompts[0]


def test_failed_step_is_sent_back_with_dom_and_fixed() -> None:
    bad = {"steps": [GOTO, {"op": "click", "selector": "#nope"}]}
    good = {"steps": [GOTO, {"op": "click", "selector": "#merge"}]}
    llm = FakeLLM(bad, good)
    fail_dom = {"elements": [{"selector": "#only-after-upload"}]}

    def dry(s: ActionScript) -> ReplayResult:
        if getattr(s.steps[1], "selector", "") == "#nope":
            raise StepFailure(1, "click", "Timeout 8000ms", fail_dom)
        return ReplayResult()

    s = _gen(llm, dry)
    assert s.steps[1].selector == "#merge"
    second = llm.prompts[1]
    assert "#nope" in second and "Timeout 8000ms" in second and "#only-after-upload" in second


def test_schema_error_and_unknown_fixture_trigger_repair() -> None:
    llm = FakeLLM(
        "not json",
        {"steps": [GOTO, {"op": "upload", "selector": "input", "files": ["zzz.pdf"]}]},
        {"steps": [GOTO, {"op": "upload", "selector": "input", "files": ["a.pdf"]}]},
    )
    s = _gen(llm, lambda _s: ReplayResult())
    assert s.steps[1].files == ["a.pdf"]
    assert "zzz.pdf" in llm.prompts[2]


def test_gives_up_after_max_rounds() -> None:
    llm = FakeLLM("x", "x", "x")
    with pytest.raises(DemoError, match="3 vòng"):
        _gen(llm, lambda _s: ReplayResult(), max_rounds=3)


def test_prompt_lists_goal_facts_fixtures() -> None:
    p = build_prompt(BRIEF, SNAP)
    assert "Ghép 2 PDF" in p and "a.pdf" in p and "Merge" in p
