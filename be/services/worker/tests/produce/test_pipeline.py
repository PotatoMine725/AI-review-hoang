"""Cả đường ghép với runner giả (không cần venv VieNeu, HyperFrames, ffprobe, mạng, GPU)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from tests.produce.support import (
    RUN4_INPUT,
    RUN4_SCRIPT,
    FakeRunner,
    contract_run4,
    make_assets,
    make_cfg,
)
from worker.produce.__main__ import main
from worker.produce.config import Limits
from worker.produce.pipeline import produce
from worker.produce.render import WIDE_LIMITS_ENV

pytestmark = pytest.mark.skipif(
    not (RUN4_SCRIPT.is_file() and RUN4_INPUT.is_file()), reason="thiếu dữ liệu run4 trong docs/"
)
LIMITS = Limits(min_total_s=40, max_total_s=45)


def run(
    tmp_path: Path, fake: FakeRunner, script: Path | None = None, **kw: Any
) -> tuple[Any, Path]:
    out = tmp_path / "out"
    res = produce(
        script or contract_run4(tmp_path / "contract"),
        RUN4_INPUT,
        make_assets(tmp_path),
        out,
        cfg=make_cfg(tmp_path),
        runner=fake,
        limits=LIMITS,
        **kw,
    )
    return res, out


def screenshot_script(tmp_path: Path) -> Path:
    """run4 với s05 đòi ảnh AI (kind=ai_generated_image): #88 chưa có layout hiện ảnh cho nó."""
    data = json.loads(contract_run4(tmp_path / "contract").read_text(encoding="utf-8"))
    purpose = data["scenes"][4]["visual_plan"]["purpose"]
    data["scenes"][4]["visual_plan"] = {
        "kind": "ai_generated_image",
        "source_type": "ai_generation",
        "generation_request": "Minh hoạ người dùng xử lý PDF ngay trong trình duyệt",
        "purpose": purpose,
    }
    path = tmp_path / "variant" / RUN4_SCRIPT.name  # cùng tên file để tên plan không đổi
    path.parent.mkdir()
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return path


def test_run4_builds_every_scene_without_skip(tmp_path: Path) -> None:
    fake = FakeRunner(mp4_duration_s=20.0, speak_s=3.0)
    res, _ = run(tmp_path, fake)
    rep = res.report
    assert res.ok and rep["error"] is None
    by = {s["scene_id"]: s for s in rep["scenes"]}
    assert [(k, s["layout"], s["status"]) for k, s in by.items()] == [
        ("s01", "hook", "rendered"),
        ("s02", "feature_clip", "rendered"),
        ("s03", "feature_clip", "rendered"),
        ("s04", "feature_clip", "rendered"),
        ("s05", "claim", "rendered"),
        ("s06", "cta", "rendered"),
    ]
    assert not any(w.startswith("scene_skipped") for w in rep["warnings"])
    assert [s["segment_id"] for s in rep["tts"]["segments"]][-2:] == ["s05-u01", "s06-u01"]


def test_default_fails_on_unsupported_scene_before_any_tts(tmp_path: Path) -> None:
    fake = FakeRunner()
    res, out = run(tmp_path, fake, screenshot_script(tmp_path))
    rep = res.report
    assert not res.ok and rep["status"] == "failed"
    assert rep["error"]["code"] == "unsupported_scene" and rep["error"]["scene_id"] == "s05"
    assert fake.calls == []  # không tốn TTS/render cho kịch bản không dựng được
    s05 = next(s for s in rep["scenes"] if s["scene_id"] == "s05")
    assert s05["layout"] is None and s05["error"]["hint"]
    assert (out / "render_report.json").is_file()


def test_skip_mode_renders_both_ratios_and_flags_out_of_range(tmp_path: Path) -> None:
    fake = FakeRunner(mp4_duration_s=20.0, speak_s=3.0)
    res, out = run(tmp_path, fake, screenshot_script(tmp_path), on_unsupported="skip")
    rep = res.report

    assert res.ok and rep["status"] == "out_of_range"
    assert rep["target_s"]["min"] == 40 and rep["target_s"]["max"] == 45
    assert [o["ratio"] for o in rep["outputs"]] == ["16:9", "9:16"]
    assert {o["duration_check"] for o in rep["outputs"]} == {"too_short"}
    assert rep["actual_s"] == 20.0
    for o in rep["outputs"]:
        assert Path(o["mp4"]).is_file() and o["quality"] == "draft" and o["workers"] == "3"

    # mốc rộng chỉ dành cho tiến trình con; worker tự kiểm mốc thật
    render_envs = [
        e for c, e in zip(fake.calls, fake.envs, strict=True) if Path(c[1]).name == "hf_render.py"
    ]
    assert render_envs == [WIDE_LIMITS_ENV, WIDE_LIMITS_ENV]
    assert fake.count("hf_render.py") == 2

    by = {s["scene_id"]: s for s in rep["scenes"]}
    assert by["s05"]["status"] == "unsupported" and by["s05"]["duration_s_actual"] == 0.0
    assert not by["s06"]["derived"]  # contract hiện hành: M2 tự sinh cảnh cta
    for sid in ("s01", "s02", "s03", "s04", "s06"):
        assert by[sid]["layout"] and by[sid]["duration_s_actual"] > 0
    assert set(by["s02"]) >= {"scene_id", "layout", "footage", "duration_s_actual", "warnings"}
    assert any(w.startswith("scene_skipped[s05]") for w in rep["warnings"])
    assert any(w.startswith("predicted_too_short") for w in rep["warnings"])

    # TTS ghi từng câu với lời gốc, lời chuẩn hoá và độ dài đo thật; s05 không bị đọc
    tts_ids = [s["segment_id"] for s in rep["tts"]["segments"]]
    assert tts_ids == ["s01-u01", "s02-u01", "s03-u01", "s04-u01", "s06-u01"]
    assert rep["tts"]["segments"][0]["duration_s"] == 3.0
    assert fake.modes() == ["normalize", "synth"]

    assert set(rep["timings_s"]) >= {"validate_s", "map_s", "tts_s", "render_s", "total_s"}
    plan = json.loads((out / "script-preview.json").read_text(encoding="utf-8"))
    assert plan["schema_version"] == "render-plan.v2-spike"
    assert json.loads((out / "render_report.json").read_text(encoding="utf-8")) == rep


def test_in_range_video_is_ok(tmp_path: Path) -> None:
    # ffprobe báo 42 s; timeline dự kiến ngắn hơn nhiều nên có cảnh báo lệch, nhưng trạng thái = ok
    res, _ = run(tmp_path, FakeRunner(mp4_duration_s=42.0))
    rep = res.report
    assert rep["status"] == "ok"
    assert any(w.startswith("predicted_mismatch") for w in rep["warnings"])


def test_final_mode_uses_looks_quality(tmp_path: Path) -> None:
    res, _ = run(tmp_path, FakeRunner(), mode="final")
    assert {o["quality"] for o in res.report["outputs"]} == {"looks"}


def test_second_run_reuses_tts_cache(tmp_path: Path) -> None:
    run(tmp_path, FakeRunner())
    fake = FakeRunner()
    res, _ = run(tmp_path, fake)
    assert fake.modes() == ["normalize"]
    assert res.report["tts"]["misses"] == 0 and res.report["tts"]["load_s"] is None


def test_one_ratio_failing_is_reported_as_failed(tmp_path: Path) -> None:
    fake = FakeRunner()
    fake.fail_ratio = "9:16"
    res, _ = run(tmp_path, fake)
    assert res.report["status"] == "failed"
    bad = next(o for o in res.report["outputs"] if o["ratio"] == "9:16")
    assert bad["ok"] is False and "Chrome crash" in bad["error"]
    assert next(o for o in res.report["outputs"] if o["ratio"] == "16:9")["mp4"]


def test_subtitle_split_is_reported_per_ratio(tmp_path: Path) -> None:
    fake = FakeRunner()
    fake.subtitle_cues = {"9:16": {"s01-u01": 2}}
    res, _ = run(tmp_path, fake)
    out = {o["ratio"]: o for o in res.report["outputs"]}
    assert out["9:16"]["subtitle_cues"] == {"s01-u01": 2} and out["16:9"]["subtitle_cues"] == {}
    assert any(
        w.startswith("subtitle_split[9:16]: s01-u01 chia 2 cue") for w in res.report["warnings"]
    )
    assert not any("subtitle_split[16:9]" in w for w in res.report["warnings"])


def test_single_ratio(tmp_path: Path) -> None:
    fake = FakeRunner()
    res, _ = run(tmp_path, fake, ratios=("9:16",))
    assert [o["ratio"] for o in res.report["outputs"]] == ["9:16"]
    assert fake.count("hf_render.py") == 1


def test_missing_asset_file_stops_before_tts(tmp_path: Path) -> None:
    assets = make_assets(tmp_path)
    (assets.parent / "clips" / "merge.mp4").unlink()
    fake = FakeRunner()
    res = produce(
        contract_run4(tmp_path / "contract"),
        RUN4_INPUT,
        assets,
        tmp_path / "out",
        cfg=make_cfg(tmp_path),
        runner=fake,
        limits=LIMITS,
    )
    assert res.report["status"] == "failed" and "thiếu file media" in res.report["error"]["message"]


def test_invalid_script_is_rejected(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text("{}", encoding="utf-8")
    res = produce(
        bad,
        RUN4_INPUT,
        make_assets(tmp_path),
        tmp_path / "out",
        cfg=make_cfg(tmp_path),
        runner=FakeRunner(),
        limits=LIMITS,
    )
    assert res.report["status"] == "failed" and "validator" in res.report["error"]["message"]


def test_cli_rejects_bad_ratio(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.raises(SystemExit):
        main(["x.json", "--input", "i", "--assets", "a", "--out", "o", "--ratios", "1:1"])
    assert "--ratios" in capsys.readouterr().err


# ---------------------------------------------------------------- STT + QA khung hình (P1, OpenAI)


class FakeStt:
    model = "whisper-1"

    def __init__(self) -> None:
        self.seen: list[Path] = []

    def transcribe(self, wav: Path) -> list[tuple[str, float, float]]:
        self.seen.append(wav)
        return [("xin", 0.0, 0.3), ("chào", 0.3, 0.6)]


class FakeQa:
    model = "fake-vision"
    tokens_in = 10
    tokens_out = 5

    def __init__(self, bad_scene: str | None = None) -> None:
        self.bad_scene = bad_scene
        self.jobs: list[Any] = []

    def review(self, image_jpeg: bytes, job: Any) -> dict[str, Any]:
        self.jobs.append(job)
        assert image_jpeg.startswith(b"\xff\xd8")
        bad = job.scene_id == self.bad_scene
        return {
            "readable": True,
            "not_cut_off": not bad,
            "title_distinct_from_subtitle": True,
            "matches_narration": True,
            "issues": ["chữ bị cắt ở mép phải"] if bad else [],
        }


def test_stt_writes_sidecar_next_to_plan(tmp_path: Path) -> None:
    stt = FakeStt()
    res, out = run(tmp_path, FakeRunner(), stt=stt)
    assert res.report["stt"]["model"] == "whisper-1" and res.report["stt"]["segments"] > 0
    sidecar = Path(res.report["stt"]["sidecar"])
    assert sidecar == Path(res.report["plan"]).with_suffix(".words.json") and sidecar.parent == out
    data = json.loads(sidecar.read_text(encoding="utf-8"))
    assert data["s01-u01"][0] == ["xin", 0.0, 0.3]


def test_stt_off_by_default_and_stale_sidecar_removed(tmp_path: Path) -> None:
    res, out = run(tmp_path, FakeRunner(), stt=FakeStt())
    sidecar = Path(res.report["stt"]["sidecar"])
    assert sidecar.is_file()
    res2, _ = run(tmp_path, FakeRunner())  # lần sau không bật STT
    assert res2.report["stt"] is None and not sidecar.exists()


def test_qa_reports_one_frame_per_scene_per_ratio(tmp_path: Path) -> None:
    qa = FakeQa(bad_scene="s02")
    fake = FakeRunner()
    res, out = run(tmp_path, fake, qa=qa)
    rep = res.report["qa"]
    scenes = len(res.report["scenes"])
    assert rep["model"] == "fake-vision" and len(rep["frames"]) == 2 * scenes
    assert rep["failed_frames"] == 2 and {f["scene_id"] for f in rep["frames"] if not f["ok"]} == {
        "s02"
    }
    assert any(w.startswith("qa_issue[9:16/s02@") and "bị cắt" in w for w in res.report["warnings"])
    assert all(j.narration and 0 < j.t_s < 60 for j in qa.jobs)
    assert (out / "qa-frames").is_dir()
    assert sum(1 for c in fake.calls if Path(c[0]).stem == "ffmpeg") == 2 * scenes
    assert res.report["status"] == "out_of_range" or res.ok  # QA không đổi trạng thái video


def test_qa_failure_is_only_a_warning(tmp_path: Path) -> None:
    class Broken(FakeQa):
        def review(self, image_jpeg: bytes, job: Any) -> dict[str, Any]:
            from worker.produce.errors import ProduceError

            raise ProduceError("hết quota")

    res, _ = run(tmp_path, FakeRunner(), qa=Broken())
    assert res.ok and res.report["qa"]["frames"] == []
    assert any(w.startswith("qa_failed[") and "hết quota" in w for w in res.report["warnings"])


def test_qa_and_stt_skipped_without_key(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from worker.produce.config import ProduceConfig

    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    cfg = make_cfg(tmp_path)
    cfg = ProduceConfig.model_validate(
        {**cfg.model_dump(), "stt_model": "whisper-1", "qa_model": "x"}
    )
    res = produce(
        contract_run4(tmp_path / "contract"),
        RUN4_INPUT,
        make_assets(tmp_path),
        tmp_path / "out",
        cfg=cfg,
        runner=FakeRunner(),
        limits=LIMITS,
    )
    assert res.report["stt"] is None and res.report["qa"] is None
    assert any(w.startswith("stt_skipped") for w in res.report["warnings"])
    assert any(w.startswith("qa_skipped") for w in res.report["warnings"])


def test_cli_loads_env_file_without_overriding_set_vars(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    env = tmp_path / ".env"
    env.write_text(
        "PRODUCE_STT_MODEL=whisper-1\nPRODUCE_QA_MODEL=gpt-5.4-mini\nPRODUCE_VOICE=Hải Đăng\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("PRODUCE_STT_MODEL", raising=False)
    monkeypatch.delenv("PRODUCE_QA_MODEL", raising=False)
    monkeypatch.setenv("PRODUCE_VOICE", "Mai Anh")  # đã đặt trong shell thì thắng .env
    seen: dict[str, Any] = {}

    def fake_produce(*a: Any, cfg: Any, **kw: Any) -> Any:
        seen["cfg"] = cfg
        raise SystemExit(0)

    monkeypatch.setattr("worker.produce.__main__.produce", fake_produce)
    with pytest.raises(SystemExit):
        main(["s.json", "--input", "i.json", "--assets", "a.json", "--out", "o", "--env", str(env)])
    cfg = seen["cfg"]
    assert (cfg.stt_model, cfg.qa_model, cfg.voice) == ("whisper-1", "gpt-5.4-mini", "Mai Anh")


def test_assets_and_script_files_with_bom_are_readable(tmp_path: Path) -> None:
    """PowerShell 5 `Set-Content -Encoding utf8` ghi BOM; không được làm hỏng đọc JSON."""
    from worker.produce.assets import load_assets

    assets = make_assets(tmp_path)
    assets.write_bytes(b"\xef\xbb\xbf" + assets.read_bytes())
    loaded, _ = load_assets(assets)
    assert loaded.assets
