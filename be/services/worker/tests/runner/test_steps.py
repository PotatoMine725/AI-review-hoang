import asyncio
from pathlib import Path

import pytest

from tests.runner.fakes import crawl_ok
from worker.m1.extract import service as extract_service
from worker.m1.extract.service import ExtractError, ExtractErrorCode, ExtractResult
from worker.produce.pipeline import ProduceResult
from worker.runner import steps
from worker.runner.steps import GeminiExtractStep, StepError


def call(crawl=None):  # type: ignore[no-untyped-def]
    return asyncio.run(GeminiExtractStep()(crawl or crawl_ok(), Path("/tmp/x")))


def test_success_maps_result(monkeypatch: pytest.MonkeyPatch) -> None:
    async def fake_extract(crawl, store, llm):  # type: ignore[no-untyped-def]
        return ExtractResult(
            data={"identity": {}},
            sources=[{"source_id": "src_01"}],
            cost_breakdown={"items": []},
            warnings=["w"],
        )

    monkeypatch.setattr(steps, "make_llm", lambda: object())
    monkeypatch.setattr(steps, "extract_product", fake_extract)
    out = call()
    assert out.data == {"identity": {}} and out.sources == [{"source_id": "src_01"}]
    assert out.cost_breakdown == {"items": []} and out.warnings == ["w"]


def test_extract_error_keeps_retryable_and_cost(monkeypatch: pytest.MonkeyPatch) -> None:
    async def boom(crawl, store, llm):  # type: ignore[no-untyped-def]
        raise ExtractError(ExtractErrorCode.NO_PAGES, "không có trang", retryable=True)

    monkeypatch.setattr(steps, "make_llm", lambda: object())
    monkeypatch.setattr(steps, "extract_product", boom)
    with pytest.raises(StepError) as e:
        call()
    assert e.value.retryable is True and "extract_no_pages" in e.value.message
    assert "items" in e.value.cost_breakdown


def test_bad_llm_config_is_not_retryable(monkeypatch: pytest.MonkeyPatch) -> None:
    def bad():  # type: ignore[no-untyped-def]
        raise ValueError("LLM_PROVIDER=fixture cần LLM_FIXTURE_PATH")

    monkeypatch.setattr(steps, "make_llm", bad)
    with pytest.raises(StepError) as e:
        call()
    assert e.value.retryable is False and "LLM_FIXTURE_PATH" in e.value.message


def test_module_is_the_one_runner_imports() -> None:
    assert steps.extract_product is extract_service.extract_product


# --- ProduceVideoStep ------------------------------------------------------------------------


def _video_request(tmp_path: Path) -> steps.VideoRequest:
    return steps.VideoRequest(
        script={"scenes": []},
        m2_input={"schema_version": "x"},
        assets_path=tmp_path / "assets.json",
        out_dir=tmp_path / "out",
        mode="final",
        ratios=("16:9",),
    )


def _report(status: str = "completed", **over):  # type: ignore[no-untyped-def]
    rep = {
        "status": status,
        "mode": "final",
        "ratios": ["16:9"],
        "target_s": {"min": 40, "max": 45},
        "actual_s": 42.0,
        "outputs": [
            {
                "ratio": "16:9",
                "ok": True,
                "mp4": "a.mp4",
                "duration_s": 42.0,
                "size": [1920, 1080],
                "duration_check": "ok",
                "render_wall_s": 99.0,  # không đưa vào manifest
            }
        ],
        "warnings": ["w1"],
        "timings_s": {"total_s": 100.0},
        "error": None,
    }
    rep.update(over)
    return rep


def test_produce_video_step_writes_inputs_and_returns_manifest(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, object] = {}

    def fake_produce(script, input_, assets, out, **kw):  # type: ignore[no-untyped-def]
        seen.update(script=script, input=input_, assets=assets, out=out, kw=kw)
        return ProduceResult(_report(), out / "render_report.json")

    monkeypatch.setattr(steps, "produce", fake_produce)
    req = _video_request(tmp_path)
    outcome = asyncio.run(steps.ProduceVideoStep()(req))

    assert (tmp_path / "out" / "inputs" / "script.json").read_text(encoding="utf-8") == (
        '{"scenes": []}'
    )
    assert seen["assets"] == req.assets_path and seen["out"] == req.out_dir
    assert seen["kw"] == {"mode": "final", "ratios": ("16:9",), "cfg": None}
    m = outcome.manifest
    assert m["status"] == "completed" and m["actual_s"] == 42.0
    assert m["outputs"] == [
        {
            "ratio": "16:9",
            "ok": True,
            "mp4": "a.mp4",
            "duration_s": 42.0,
            "size": [1920, 1080],
            "duration_check": "ok",
            "error": None,
        }
    ]
    assert m["report_path"].endswith("render_report.json") and outcome.warnings == ["w1"]


def test_out_of_range_video_is_still_an_outcome(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        steps, "produce", lambda *a, **k: ProduceResult(_report("out_of_range"), Path("r"))
    )
    outcome = asyncio.run(steps.ProduceVideoStep()(_video_request(tmp_path)))
    assert outcome.manifest["status"] == "out_of_range"


def test_failed_produce_raises_step_error_with_code_and_report_path(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    rep = _report("failed", error={"code": "unsupported_scene", "message": "cảnh s05"})
    monkeypatch.setattr(
        steps, "produce", lambda *a, **k: ProduceResult(rep, Path("out/render_report.json"))
    )
    with pytest.raises(StepError) as e:
        asyncio.run(steps.ProduceVideoStep()(_video_request(tmp_path)))
    assert e.value.retryable is False
    assert (
        "unsupported_scene: cảnh s05" in e.value.message and "render_report.json" in e.value.message
    )


def _templates(root: Path) -> Path:
    (root / "template").mkdir(parents=True)
    (root / "template" / "templates.json").write_text(
        '{"default": "nhip-nhanh", "templates": {"nhip-nhanh": {"name": "Nhịp nhanh"},'
        ' "pixel": {"name": "Pixel 8-bit", "description": "d"}}}',
        encoding="utf-8",
    )
    return root


def test_produce_video_step_overrides_template_and_voice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    seen: dict[str, object] = {}

    def fake_produce(script, input_, assets, out, **kw):  # type: ignore[no-untyped-def]
        seen.update(kw)
        return ProduceResult(_report(), out / "render_report.json")

    monkeypatch.setattr(steps, "produce", fake_produce)
    base = steps.ProduceConfig(render_v2=_templates(tmp_path / "rv2"), voice="Hải Đăng")
    req = _video_request(tmp_path)
    req.template, req.voice = "pixel", "Mai Anh"
    asyncio.run(steps.ProduceVideoStep(base)(req))
    cfg = seen["cfg"]
    assert isinstance(cfg, steps.ProduceConfig)
    assert (cfg.template, cfg.voice) == ("pixel", "Mai Anh") and base.voice == "Hải Đăng"


@pytest.mark.parametrize(("template", "voice"), [("khong-co", None), (None, "Giọng lạ")])
def test_produce_video_step_rejects_unknown_choice(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, template: str | None, voice: str | None
) -> None:
    monkeypatch.setattr(steps, "produce", lambda *a, **k: pytest.fail("không được dựng"))
    base = steps.ProduceConfig(render_v2=_templates(tmp_path / "rv2"))
    req = _video_request(tmp_path)
    req.template, req.voice = template, voice
    with pytest.raises(StepError) as e:
        asyncio.run(steps.ProduceVideoStep(base)(req))
    assert e.value.retryable is False and "options." in e.value.message
