import asyncio
from pathlib import Path

import pytest

from tests.runner.fakes import (
    FakeCrawl,
    FakeVideo,
    JobsDb,
    approved_pkb,
    approved_script,
    job,
    video_job,
)
from worker.runner.runner import JobRunner
from worker.runner.steps import StepError
from worker.settings import Settings


def make(
    tmp_path: Path, db: JobsDb, video: FakeVideo, crawl: FakeCrawl | None = None, **s: object
) -> JobRunner:
    settings = Settings(video_store_dir=str(tmp_path / "videos"), **s)  # type: ignore[arg-type]
    return JobRunner(db, settings, crawl, video=video)


def setup(tmp_path: Path, **over: object) -> tuple[JobsDb, Path]:
    assets = tmp_path / "assets.json"
    assets.write_text("{}", encoding="utf-8")
    snapshot = {"options": {"assets_path": str(assets), **over}}  # type: ignore[dict-item]
    db = JobsDb(video_job(input_snapshot=snapshot))
    db.tables = {"script_revisions": [approved_script()], "product_knowledge": [approved_pkb()]}
    return db, assets


def run(runner: JobRunner) -> bool:
    return asyncio.run(runner.run_once())


def test_video_job_builds_input_from_approved_pkb_and_completes(tmp_path: Path) -> None:
    db, assets = setup(tmp_path, mode="final", ratios=["9:16"])
    video = FakeVideo()
    assert run(make(tmp_path, db, video)) is True
    j = db.by_id("v1")
    assert j["status"] == "completed" and j["error"] is None
    assert j["result_manifest"] == {"status": "completed", "outputs": []}
    (req,) = video.requests
    assert req.script == {"scenes": [{"scene_id": "s01"}]}
    assert req.assets_path == assets and req.mode == "final" and req.ratios == ("9:16",)
    assert req.out_dir == tmp_path / "videos" / "v1"
    # input dựng lại đúng thứ đã dùng khi sinh: PKB đã duyệt + permitted_assets/context đã lưu
    assert req.m2_input["permitted_assets"] == [{"asset_id": "a1"}]
    assert req.m2_input["content_context"] == {"x": 1}
    assert req.m2_input["knowledge_version"] == 1
    assert req.m2_input["approved_pkb"]["data"]["identity"] == {"name": "X"}


def test_defaults_are_preview_and_both_ratios(tmp_path: Path) -> None:
    db, _ = setup(tmp_path)
    video = FakeVideo()
    run(make(tmp_path, db, video))
    assert video.requests[0].mode == "preview"
    assert video.requests[0].ratios == ("16:9", "9:16")


@pytest.mark.parametrize(
    ("script", "pkb", "options", "needle"),
    [
        ({"status": "in_review"}, {}, {}, "chưa được duyệt"),
        ({"knowledge_version": 5}, {}, {}, "PKB v5"),
        ({}, {"status": "draft"}, {}, "PKB version 1 chưa được duyệt"),
        ({"report": {}}, {}, {}, "permitted_assets"),
        ({}, {}, {"mode": "fast"}, "options.mode"),
        ({}, {}, {"ratios": ["1:1"]}, "options.ratios"),
        ({}, {}, {"ratios": []}, "options.ratios"),
        ({}, {}, {"ratios": ["16:9", "16:9"]}, "options.ratios"),
    ],
)
def test_bad_inputs_fail_without_rendering(
    tmp_path: Path, script: dict, pkb: dict, options: dict, needle: str
) -> None:
    db, _ = setup(tmp_path, **options)
    db.tables = {
        "script_revisions": [approved_script(**script)],
        "product_knowledge": [approved_pkb(**pkb)],
    }
    video = FakeVideo()
    run(make(tmp_path, db, video))
    j = db.by_id("v1")
    assert j["status"] == "failed" and needle in j["error"]
    assert video.requests == []


def test_missing_assets_path_or_file_fails(tmp_path: Path) -> None:
    db = JobsDb(video_job(input_snapshot={"options": {}}))
    run(make(tmp_path, db, FakeVideo()))
    assert "assets_path" in db.by_id("v1")["error"]

    db = JobsDb(video_job(input_snapshot={"options": {"assets_path": str(tmp_path / "no.json")}}))
    run(make(tmp_path, db, FakeVideo()))
    assert "không có trên máy render" in db.by_id("v1")["error"]


def test_missing_script_revision_row_fails(tmp_path: Path) -> None:
    db, _ = setup(tmp_path)
    db.tables["script_revisions"] = []
    run(make(tmp_path, db, FakeVideo()))
    assert "không tìm thấy script revision 2" in db.by_id("v1")["error"]


def test_step_error_marks_job_failed_without_retry(tmp_path: Path) -> None:
    db, _ = setup(tmp_path)
    run(make(tmp_path, db, FakeVideo(StepError("scene_unsupported: s03"))))
    j = db.by_id("v1")
    assert j["status"] == "failed" and j["error"] == "scene_unsupported: s03"
    assert j["attempts"] == 1


def test_runner_only_claims_enabled_job_types(tmp_path: Path) -> None:
    db, _ = setup(tmp_path)
    db.jobs.append(job("c1"))
    video = FakeVideo()
    crawl_only = JobRunner(db, Settings(), FakeCrawl())
    assert crawl_only._types == ["crawl"]  # noqa: SLF001
    video_only = make(tmp_path, db, video)
    assert run(video_only) is True
    assert db.by_id("v1")["status"] == "completed"
    assert db.by_id("c1")["status"] == "queued"  # job crawl không bị runner video nhận
    assert run(video_only) is False
