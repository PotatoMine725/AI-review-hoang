"""Điều phối: kịch bản M2 → TTS → timeline → plan #88 → MP4 (2 tỉ lệ) → kiểm → `render_report.json`.

Trạng thái trong report:
- `ok`            : mọi MP4 dựng xong và nằm trong mốc 40–45 s (đọc từ config chung #77)
- `out_of_range`  : dựng xong nhưng ngoài mốc; MP4 vẫn giữ nguyên, không kéo dài/cắt
- `failed`        : không ra MP4 (cảnh không hỗ trợ ở chế độ `fail`, thiếu công cụ, render lỗi)
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from worker.m2.validate import validate_input, validate_script
from worker.produce import check
from worker.produce.assets import load_assets
from worker.produce.config import Limits, ProduceConfig, load_limits
from worker.produce.errors import ProduceError, SceneError
from worker.produce.mapping import Mapper, SceneSpec
from worker.produce.qa import OpenAIVisionQA, VisionQA, frame_jobs, run_qa
from worker.produce.render import RatioRender, render_ratios
from worker.produce.runner import Runner, run_process
from worker.produce.stt import OpenAIWordStt, WordStt, dump_words, stt_cost_usd, transcribe_segments
from worker.produce.timeline import Timeline, build_timeline
from worker.produce.tts import TtsRun, synthesize

log = logging.getLogger("worker.produce")
REPORT_NAME = "render_report.json"
SCHEMA = "render-report.v1-spike"


@dataclass(frozen=True)
class ProduceResult:
    report: dict[str, Any]
    report_path: Path

    @property
    def ok(self) -> bool:
        return self.report["status"] != "failed"


def _read(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as ex:
        raise ProduceError(f"không đọc được JSON {path}: {ex}") from ex


def _template_layouts(cfg: ProduceConfig) -> frozenset[str] | None:
    """Layout có trong template #88 trên máy; None khi không có spike (test dùng runner giả)."""
    folder = cfg.render_v2 / "template" / "layouts"
    if not folder.is_dir():
        return None
    return frozenset(p.stem for p in folder.glob("*.html"))


def _scene_report(spec: SceneSpec, timeline: Timeline | None) -> dict[str, Any]:
    in_tl = timeline is not None and any(s.scene_id == spec.scene_id for s in timeline.scenes)
    warnings = list(spec.warnings)
    err = None
    if spec.error:
        err = {"code": spec.error.code, "message": spec.error.message, "hint": spec.error.hint}
        warnings.append(f"{spec.error.code}: {spec.error.message}")
    return {
        "scene_id": spec.scene_id,
        "role": spec.scene["role"],
        "layout": spec.layout,
        "footage": spec.footage,
        "duration_s_actual": round(timeline.scene(spec.scene_id).duration_s, 3)
        if timeline is not None and in_tl
        else 0.0,
        "warnings": warnings,
        "status": "rendered" if in_tl else ("unsupported" if spec.error else "not_built"),
        "derived": spec.derived,
        "error": err,
    }


def _tts_report(tts: TtsRun | None) -> dict[str, Any] | None:
    if tts is None:
        return None
    return {
        "model": tts.model,
        "hits": tts.hits,
        "misses": tts.misses,
        "load_s": None if tts.load_s is None else round(tts.load_s, 2),
        "wall_s": round(tts.wall_s, 2),
        "segments": [
            {
                "segment_id": s.segment_id,
                "text": s.text,
                "spoken": s.spoken,
                "duration_s": round(s.duration_s, 3),
                "cached": s.cached,
                "synth_s": s.synth_s,
            }
            for s in tts.segments
        ],
    }


def _output_report(
    r: RatioRender,
    cfg: ProduceConfig,
    runner: Runner,
    limits: Limits,
    predicted_s: float,
    warnings: list[str],
) -> dict[str, Any]:
    out: dict[str, Any] = {"ratio": r.ratio, "ok": r.ok, "render_wall_s": round(r.wall_s, 1)}
    if not r.ok or r.output is None:
        return {**out, "mp4": None, "error": r.error}
    info = check.probe(r.output, cfg, runner)
    verdict = check.check_duration(info.duration_s, limits)
    delta = info.duration_s - predicted_s
    if abs(delta) > check.PREDICT_TOLERANCE_S:
        warnings.append(
            f"predicted_mismatch[{r.ratio}]: timeline {predicted_s:.2f} s, "
            f"ffprobe {info.duration_s:.2f} s"
        )
    raw = r.raw
    cues: dict[str, int] = raw.get("subtitle_cues") or {}
    for seg_id, n in cues.items():
        warnings.append(
            f"subtitle_split[{r.ratio}]: {seg_id} chia {n} cue "
            "(mốc từng từ nếu có STT, không thì theo số ký tự)"
        )
    return {
        **out,
        "subtitle_cues": cues,
        "mp4": str(r.output),
        "duration_s": round(info.duration_s, 3),
        "size": [info.width, info.height],
        "duration_check": verdict,
        "predicted_s": round(predicted_s, 3),
        "delta_s": round(delta, 3),
        "quality": raw.get("quality"),
        "workers": raw.get("workers"),
        "steps_s": {
            "compose": raw.get("compose_s"),
            "hyperframes": raw.get("hf_wall_s"),
            "hyperframes_phases": raw.get("hf_phases"),
            "ffmpeg": raw.get("ffmpeg_wall_s"),
        },
        "hf_peak_ram_mb": raw.get("hf_peak_ram_mb"),
        "render": raw.get("render"),
    }


def _stt_words(
    tts: TtsRun,
    cfg: ProduceConfig,
    stt: WordStt | None,
    plan_path: Path,
    warnings: list[str],
    timings: dict[str, float],
) -> dict[str, Any] | None:
    """Mốc từng từ → `<plan>.words.json` (driver render đọc để chia phụ đề). Lỗi chỉ cảnh báo."""
    plan_path.with_suffix(".words.json").unlink(missing_ok=True)
    if stt is None:
        key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not cfg.stt_model:
            return None
        if not key:
            warnings.append("stt_skipped: PRODUCE_STT_MODEL đặt nhưng thiếu OPENAI_API_KEY")
            return None
        try:
            stt = OpenAIWordStt(key, cfg.stt_model, cache_dir=cfg.cache_dir / "stt")
        except ProduceError as ex:
            warnings.append(f"stt_skipped: {ex}")
            return None
    t0 = time.perf_counter()
    words, stt_warn = transcribe_segments(stt, [(s.segment_id, s.wav) for s in tts.segments])
    warnings.extend(stt_warn)
    sidecar = plan_path.with_suffix(".words.json")
    if words:
        dump_words(words, sidecar)
    timings["stt_s"] = round(time.perf_counter() - t0, 2)
    total_s = sum(s.duration_s for s in tts.segments)
    return {
        "model": stt.model,
        "segments": len(words),
        "of": len(tts.segments),
        "sidecar": str(sidecar) if words else None,
        "api_calls": getattr(stt, "calls", None),
        "cache_hits": getattr(stt, "cached", None),
        "cost_usd_upper": stt_cost_usd(total_s),
    }


def _qa_frames(
    done: list[dict[str, Any]],
    kept: list[SceneSpec],
    timeline: Timeline,
    cfg: ProduceConfig,
    qa: VisionQA | None,
    runner: Runner,
    out_dir: Path,
    warnings: list[str],
) -> dict[str, Any] | None:
    """Mô hình thị giác xem một khung mỗi cảnh trong từng MP4. Chỉ báo, lỗi thành cảnh báo."""
    if qa is None:
        if not cfg.qa_model:
            return None
        key = os.environ.get("OPENAI_API_KEY", "").strip()
        if not key:
            warnings.append("qa_skipped: PRODUCE_QA_MODEL đặt nhưng thiếu OPENAI_API_KEY")
            return None
        qa = OpenAIVisionQA(key, cfg.qa_model)
    scenes = [
        (
            s.scene_id,
            [
                (g["segment_id"], g.get("subtitle_text") or g["text"])
                for g in s.scene["narration_segments"]
            ],
        )
        for s in kept
    ]
    t0 = time.perf_counter()
    jobs = {o["ratio"]: frame_jobs(o["ratio"], timeline, scenes) for o in done}
    mp4s = {o["ratio"]: Path(o["mp4"]) for o in done}
    verdicts, qa_warn = run_qa(qa, mp4s, jobs, cfg, runner, out_dir / "qa-frames")
    warnings.extend(qa_warn)
    return {
        "model": qa.model,
        "wall_s": round(time.perf_counter() - t0, 1),
        "frames": [
            {
                "ratio": v.job.ratio,
                "scene_id": v.job.scene_id,
                "t_s": v.job.t_s,
                "ok": v.ok,
                "checks": v.checks,
                "issues": v.issues,
            }
            for v in verdicts
        ],
        "failed_frames": sum(1 for v in verdicts if not v.ok),
        "tokens_in": getattr(qa, "tokens_in", None),
        "tokens_out": getattr(qa, "tokens_out", None),
    }


def produce(
    script_path: Path,
    input_path: Path,
    assets_path: Path,
    out_dir: Path,
    *,
    mode: str = "preview",
    ratios: tuple[str, ...] = ("16:9", "9:16"),
    cfg: ProduceConfig | None = None,
    runner: Runner = run_process,
    on_unsupported: str = "fail",
    limits: Limits | None = None,
    stt: WordStt | None = None,
    qa: VisionQA | None = None,
) -> ProduceResult:
    cfg = cfg or ProduceConfig.from_env()
    out_dir.mkdir(parents=True, exist_ok=True)
    t_all = time.perf_counter()
    timings: dict[str, float] = {}
    report: dict[str, Any] = {
        "schema": SCHEMA,
        "status": "failed",
        "mode": mode,
        "ratios": list(ratios),
        "script": str(script_path),
        "input": str(input_path),
        "assets": str(assets_path),
        "target_s": None,
        "actual_s": None,
        "predicted_s": None,
        "scenes": [],
        "tts": None,
        "stt": None,
        "qa": None,
        "outputs": [],
        "timings_s": timings,
        "warnings": [],
        "error": None,
    }
    specs: list[SceneSpec] = []
    timeline: Timeline | None = None
    tts: TtsRun | None = None
    try:
        t0 = time.perf_counter()
        script, inp = _read(script_path), _read(input_path)
        inp.pop("_note", None)  # ghi chú cho người đọc, không thuộc contract input (như generate)
        errors = validate_input(inp) or validate_script(script, inp)
        if errors:
            raise ProduceError("kịch bản M2 không qua validator: " + "; ".join(errors[:5]))
        assets, base = load_assets(assets_path)
        limits = limits or load_limits(cfg)
        report["target_s"] = {
            "min": limits.min_total_s,
            "max": limits.max_total_s,
            "script_target_duration_s": script.get("target_duration_s"),
            "script_estimated_duration_s": script.get("estimated_duration_s"),
        }
        timings["validate_s"] = round(time.perf_counter() - t0, 2)

        t0 = time.perf_counter()
        mapper = Mapper(script, inp, assets, base, cfg, layouts=_template_layouts(cfg))
        specs = mapper.plan_scenes()
        bad = [s for s in specs if s.error]
        if bad and on_unsupported == "fail":
            raise bad[0].error  # type: ignore[misc]  # bad[0].error khác None theo điều kiện trên
        for s in bad:
            report["warnings"].append(f"scene_skipped[{s.scene_id}]: {s.error.code}")  # type: ignore[union-attr]
        kept = [s for s in specs if not s.error]
        if not kept:
            raise ProduceError("không còn cảnh nào để dựng")
        timings["map_s"] = round(time.perf_counter() - t0, 2)

        segments = [
            (g["segment_id"], g["text"]) for s in kept for g in s.scene["narration_segments"]
        ]
        work = cfg.scratch_dir / f"{script_path.stem}-{mode}"
        tts = synthesize(segments, cfg, runner, work)
        timings["tts_s"] = round(tts.wall_s, 2)

        dur = tts.durations()
        timeline = build_timeline(
            [
                (
                    s.scene_id,
                    [
                        (g["segment_id"], dur[g["segment_id"]])
                        for g in s.scene["narration_segments"]
                    ],
                )
                for s in kept
            ],
            fps=cfg.fps,
            lead_s=cfg.lead_s,
            gap_s=cfg.gap_s,
            tail_s=cfg.tail_s,
        )
        report["predicted_s"] = round(timeline.total_s, 3)
        verdict = check.check_duration(timeline.total_s, limits)
        if verdict != "ok":
            report["warnings"].append(
                f"predicted_{verdict}: timeline {timeline.total_s:.2f} s ngoài "
                f"{limits.min_total_s:g}–{limits.max_total_s:g} s (vẫn dựng, không kéo dài/cắt)"
            )

        voices = {k: str(v) for k, v in tts.voices().items()}
        plan = mapper.build_plan(
            specs,
            voices,
            timeline,
            list(ratios),
            f"M2 script {script_path.name}, PKB v{inp['approved_pkb'].get('schema_version')}",
        )
        plan_path = out_dir / f"{script_path.stem}-{mode}.json"
        plan_path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
        report["plan"] = str(plan_path)
        report["stt"] = _stt_words(tts, cfg, stt, plan_path, report["warnings"], timings)

        t0 = time.perf_counter()
        renders = render_ratios(plan_path, list(ratios), mode, cfg, out_dir, runner)
        timings["render_s"] = round(time.perf_counter() - t0, 1)

        t0 = time.perf_counter()
        warnings: list[str] = report["warnings"]
        report["outputs"] = [
            _output_report(r, cfg, runner, limits, timeline.total_s, warnings) for r in renders
        ]
        timings["probe_s"] = round(time.perf_counter() - t0, 2)

        done = [o for o in report["outputs"] if o["ok"]]
        if done:
            report["qa"] = _qa_frames(done, kept, timeline, cfg, qa, runner, out_dir, warnings)
        if not done:
            raise ProduceError(
                "cả hai tỉ lệ đều dựng lỗi: " + str(report["outputs"][0]["error"])[:300]
            )
        report["actual_s"] = done[0]["duration_s"]
        failed = [o["ratio"] for o in report["outputs"] if not o["ok"]]
        if failed:
            report["warnings"].append(f"render_failed: {failed}")
        any_bad = any(o["duration_check"] != "ok" for o in done)
        report["status"] = "failed" if failed else ("out_of_range" if any_bad else "ok")
    except SceneError as ex:
        report["error"] = {"code": ex.code, "scene_id": ex.scene_id, "message": str(ex)}
        log.error("%s", ex)
    except ProduceError as ex:
        report["error"] = {"code": "produce_error", "message": str(ex)}
        log.error("%s", ex)
    finally:
        report["scenes"] = [_scene_report(s, timeline) for s in specs]
        report["tts"] = _tts_report(tts)
        timings["total_s"] = round(time.perf_counter() - t_all, 1)
        path = out_dir / REPORT_NAME
        path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return ProduceResult(report, path)
