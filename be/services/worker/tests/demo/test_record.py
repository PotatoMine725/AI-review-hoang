"""Test trình duyệt thật trên trang giả cục bộ (không đụng mạng ngoài)."""

from __future__ import annotations

from pathlib import Path

import pytest

from worker.demo import dom
from worker.demo.encode import build_asset, probe_duration, to_mp4
from worker.demo.recorder import StepFailure, replay
from worker.demo.samples import make_samples
from worker.demo.schema import ActionScript

pytestmark = pytest.mark.usefixtures("chromium")


def merge_script(url: str, **extra) -> ActionScript:
    steps = [
        {"op": "goto", "url": f"{url}/merge.html"},
        {"op": "upload", "selector": "#f", "files": ["mau-a.pdf", "mau-b.pdf"],
         "hover_selector": "#drop"},
        {"op": "wait_for", "selector": "#list li >> nth=0"},
        {"op": "click", "selector": "#merge"},
        {"op": "wait_for", "selector": "#dl"},
        {"op": "hover", "selector": "#dl", "focus": True},
    ]  # fmt: skip
    return ActionScript.model_validate(
        {"asset_id": "fake-merge", "url": f"{url}/merge.html", "steps": steps, **extra}
    )


@pytest.fixture()
def fixtures(tmp_path: Path) -> Path:
    make_samples(tmp_path / "fx")
    return tmp_path / "fx"


def test_fast_dry_run_passes_and_reports_dom_hash(chromium, site_url, fixtures) -> None:
    r = replay(merge_script(site_url), fixtures_dir=fixtures, fast=True, chromium_path=chromium)
    assert r.dom_hash and r.focus and r.focus.step == 5 and r.webm is None


def test_failure_carries_dom_snapshot(chromium, site_url, fixtures) -> None:
    s = merge_script(site_url)
    bad = s.model_copy(
        update={"steps": [*s.steps[:2], s.steps[3].model_copy(update={"selector": "#nope"})]}
    )
    with pytest.raises(StepFailure) as ei:
        replay(bad, fixtures_dir=fixtures, fast=True, chromium_path=chromium)
    assert ei.value.index == 2
    assert ei.value.snap and any(e["selector"] == "#merge" for e in ei.value.snap["elements"])


def test_record_produces_mp4_and_valid_asset(chromium, site_url, fixtures, tmp_path) -> None:
    script = merge_script(site_url)
    raw = tmp_path / "raw"
    r = replay(script, fixtures_dir=fixtures, record_dir=raw, chromium_path=chromium)
    assert r.webm and r.webm.exists()
    mp4 = tmp_path / "clips" / "fake-merge.mp4"
    to_mp4(r.webm, mp4)
    dur = probe_duration(mp4)
    assert dur > 3  # có nhịp thao tác, không phải tua nhanh
    asset = build_asset(script, r, dur, "clips/fake-merge.mp4")
    assert asset.kind == "clip" and asset.parts[0].end_s <= dur
    assert asset.focus and asset.focus.rect[2] > 0


def test_upload_rejects_file_outside_fixtures(chromium, site_url, fixtures) -> None:
    s = merge_script(site_url)
    steps = [s.steps[0], s.steps[1].model_copy(update={"files": ["khong-co.pdf"]})]
    with pytest.raises(StepFailure, match="khong-co.pdf"):
        replay(s.model_copy(update={"steps": steps}), fixtures_dir=fixtures, fast=True,
               chromium_path=chromium)  # fmt: skip


def test_dom_hash_ignores_geometry() -> None:
    a = {"elements": [{"tag": "a", "selector": "#x", "text": "t", "box": [0, 0, 1, 1]}]}
    b = {"elements": [{"tag": "a", "selector": "#x", "text": "t", "box": [9, 9, 5, 5]}]}
    assert dom.dom_hash(a) == dom.dom_hash(b)


def test_cli_record_merges_into_assets_json(
    chromium, site_url, fixtures, tmp_path, monkeypatch
) -> None:
    import json

    from worker.demo.__main__ import main
    from worker.produce.assets import load_assets

    monkeypatch.setenv("DEMO_CHROMIUM_PATH", chromium)
    sp = tmp_path / "s.json"
    sp.write_text(json.dumps(merge_script(site_url).model_dump(mode="json")), encoding="utf-8")
    assets = tmp_path / "out" / "assets.json"
    assets.parent.mkdir()
    assets.write_text('{"note": "x", "assets": {}}', encoding="utf-8")
    code = main(
        ["record", str(sp), "--fixtures", str(fixtures), "--out", str(tmp_path / "out"),
         "--assets", str(assets)]
    )  # fmt: skip
    assert code == 0
    loaded, _ = load_assets(assets)
    assert loaded.assets["fake-merge"].path == "clips/fake-merge.mp4"
    assert (tmp_path / "out" / "clips" / "fake-merge.mp4").exists()
    assert (tmp_path / "out" / "fake-merge.run.json").exists()


def test_cli_record_exit_3_when_script_breaks(
    chromium, site_url, fixtures, tmp_path, monkeypatch
) -> None:
    import json

    from worker.demo.__main__ import main

    monkeypatch.setenv("DEMO_CHROMIUM_PATH", chromium)
    s = merge_script(site_url)
    bad = s.model_copy(
        update={"steps": [s.steps[0], s.steps[3].model_copy(update={"selector": "#nope"})]}
    )
    sp = tmp_path / "s.json"
    sp.write_text(json.dumps(bad.model_dump(mode="json")), encoding="utf-8")
    assert main(["record", str(sp), "--fixtures", str(fixtures), "--out", str(tmp_path / "o")]) == 3
