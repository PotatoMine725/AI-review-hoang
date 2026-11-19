from pathlib import Path
from typing import Any

import pytest

from worker.produce import bench
from worker.produce.config import ProduceConfig
from worker.produce.pipeline import ProduceResult


def test_parse_config_variants() -> None:
    base = ProduceConfig()
    seq = bench.parse_config("seq3", base, warm=False)
    assert (seq.render_mode, seq.workers, seq.tts_device) == ("sequential", "3", "cpu")
    par = bench.parse_config("par6+cuda", base, warm=False)
    assert (par.render_mode, par.render_jobs, par.tts_device) == ("parallel", 6, "cuda")
    assert par.render_cache is False  # cold: mỗi lượt dựng lại mọi cảnh
    assert bench.parse_config("par4", base, warm=True).render_cache is True
    assert bench.parse_config("seq2", base, warm=True).render_cache is False


def test_parse_config_hyperframes_suffixes() -> None:
    base = ProduceConfig()
    cfg = bench.parse_config("par4+nolock+fast+gpu", base, warm=False)
    assert cfg.hf_args == "--experimental-fast-capture --browser-gpu"
    assert cfg.hf_env_map == {"HYPERFRAMES_RENDER_LOCK": "off"}
    assert cfg.tts_device == "cpu"
    plain = bench.parse_config("par4", base, warm=False)
    assert plain.hf_args == "" and plain.hf_env_map == {}


@pytest.mark.parametrize("name", ["fast", "par", "par4+nvenc", "seq", "par4+fast+x"])
def test_parse_config_rejects_unknown(name: str) -> None:
    with pytest.raises(ValueError):
        bench.parse_config(name, ProduceConfig(), warm=False)


def _report(total: float = 100.0, **over: Any) -> dict[str, Any]:
    rep: dict[str, Any] = {
        "status": "completed",
        "actual_s": 42.0,
        "timings_s": {"tts_s": 20.0, "render_s": 70.0, "total_s": total},
        "outputs": [{"ok": True, "hf_peak_ram_mb": 5000, "render": {"mode": "parallel"}}],
        "warnings": [],
        "error": None,
    }
    rep.update(over)
    return rep


def test_matrix_records_failures_and_keeps_going(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(bench.GpuSampler, "available", False, raising=False)
    calls: list[tuple[str, int]] = []

    def fake(script, inp, assets, out, **kw):  # type: ignore[no-untyped-def]
        cfg = kw["cfg"]
        calls.append((cfg.render_mode, cfg.render_jobs))
        if cfg.render_jobs == 6:
            raise RuntimeError("Chrome crash")
        failed = cfg.render_mode == "sequential"
        rep = (
            _report(status="failed", error={"code": "x", "message": "boom"})
            if failed
            else _report()
        )
        return ProduceResult(rep, out / "render_report.json")

    runs = bench.run_matrix(
        tmp_path / "s.json",
        tmp_path / "i.json",
        tmp_path / "a.json",
        tmp_path / "out",
        ["seq3", "par4", "par6"],
        repeat=2,
        mode="preview",
        ratios=("16:9",),
        warm=False,
        base=ProduceConfig(),
        produce_fn=fake,
    )
    assert len(runs) == 6 and len(calls) == 6
    by = {(r["config"], r["run"]): r for r in runs}
    assert by[("par4", 1)]["ok"] and by[("par4", 1)]["hf_peak_ram_mb"] == 5000
    assert by[("par6", 1)]["error"] == "RuntimeError: Chrome crash" and not by[("par6", 1)]["ok"]
    assert by[("seq3", 1)]["error"] == "x: boom"

    md = bench.markdown(runs, {"mode": "preview", "ratios": ["16:9"], "cache": "cold", "repeat": 2})
    assert "| par4 | 2/2 | 20.0 | 70.0 | 100.0 | 5000 | - | - | - |" in md
    assert "| par6 | 0/2 |" in md and "Chrome crash" in md


def test_gpu_sampler_without_nvidia_smi_is_empty(monkeypatch) -> None:  # type: ignore[no-untyped-def]
    monkeypatch.setattr(bench.shutil, "which", lambda _: None)
    with bench.GpuSampler(0.01) as g:
        pass
    assert g.available is False and g.peaks()["samples"] == 0


def test_cli_rejects_bad_config(tmp_path: Path, capsys) -> None:  # type: ignore[no-untyped-def]
    with pytest.raises(SystemExit):
        bench.main(
            ["s.json", "--input", "i", "--assets", "a", "--out", str(tmp_path), "--configs", "gpu9"]
        )
    assert "cấu hình không hợp lệ" in capsys.readouterr().err


def test_markdown_shows_hyperframes_version() -> None:
    meta = {"mode": "preview", "ratios": ["16:9"], "cache": "cold", "repeat": 1}
    assert "HyperFrames ?" in bench.markdown([], meta)
    assert "HyperFrames 0.9.69" in bench.markdown([], {**meta, "hyperframes": "0.9.69"})
