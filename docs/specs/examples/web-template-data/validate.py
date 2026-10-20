"""Check review fixtures against pinned Git sources; never run rendering or AI."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import SchemaError, ValidationError

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
LAYOUTS = {
    "hook",
    "problem",
    "feature_clip",
    "stat",
    "steps",
    "before_after",
    "highlight_zoom",
    "cta",
}
PRESETS = {"hoat-hinh-do-hoa", "dien-anh-toi-gian", "co-dien"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def read_json(name: str) -> dict:
    return json.loads((HERE / name).read_text(encoding="utf-8"))


def blob(commit: str, path: str) -> bytes:
    require(bool(re.fullmatch(r"[0-9a-f]{40}", commit)), "Source commit must be a full SHA")
    result = subprocess.run(
        ["git", "show", f"{commit}:{path}"],
        cwd=REPO,
        check=False,
        capture_output=True,
        timeout=30,
    )
    require(result.returncode == 0, f"Cannot read pinned source {commit}:{path}; fetch PR branch")
    return result.stdout


def pointer(document: dict, value: str):
    require(value.startswith("/"), "Title binding must use a JSON Pointer")
    current = document
    for token in value[1:].split("/"):
        key = token.replace("~1", "/").replace("~0", "~")
        if isinstance(current, list):
            require(bool(re.fullmatch(r"0|[1-9][0-9]*", key)), f"Invalid array index: {key}")
            current = current[int(key)]
        else:
            current = current[key]
    return current


def validate_selection(selection: dict, script: dict) -> int:
    require(selection["status"] == "draft_for_review", "Selection must stay a review draft")
    require(selection["render_status"] == "blocked", "Fixture must not claim render readiness")
    require(selection["render_blockers"], "Missing render dependencies must remain explicit")
    require(selection["preset"] in PRESETS, "Unknown preset")
    require(set(selection["aspect_ratios"]) == {"9:16", "16:9"}, "Both P1 ratios required")
    scenes = {scene["scene_id"]: scene for scene in script["scenes"]}
    require(len(scenes) == len(script["scenes"]), "M2 scene IDs must be unique")
    segment_ids = [
        segment["segment_id"]
        for scene in script["scenes"]
        for segment in scene["narration_segments"]
    ]
    require(len(set(segment_ids)) == len(segment_ids), "M2 segment IDs must be unique")
    selections = selection["scenes"]
    ids = [item["scene_id"] for item in selections]
    require(len(ids) == len(set(ids)) and set(ids) == set(scenes), "Scene selection must match M2")
    blocked = 0
    for item in selections:
        scene = scenes[item["scene_id"]]
        require(item["layout"] in LAYOUTS, "Unknown layout")
        binding = item["title_ref"]
        require(binding["scope"] in {"script", "scene"}, "Unknown binding scope")
        target = script if binding["scope"] == "script" else scene
        title = pointer(target, binding["pointer"])
        require(
            isinstance(title, str) and bool(title.strip()), "Title must reference existing text"
        )
        local_segments = {segment["segment_id"] for segment in scene["narration_segments"]}
        for claim in scene["claims"]:
            require(set(claim["segment_ids"]) <= local_segments, "Claim links to wrong scene")
        if item["layout"] == "feature_clip":
            visual = scene["visual_plan"]
            require(
                visual["kind"] == "screen_recording"
                and visual["source_type"] == "existing_asset"
                and bool(visual.get("asset_id")),
                "feature_clip requires a referenced recording (not a resolved file yet)",
            )
        if item["layout"] == "stat":
            require(
                set(item["missing_inputs"]) == {"stat.value", "stat.label", "stat.fact_refs"},
                "The upstream fixture has no structured stat; keep the gap explicit",
            )
        if item["missing_inputs"]:
            require(item.get("content_status") == "blocked", "Missing layout input must block")
            blocked += 1
    return blocked


def validate_pdfcraft(manifest: dict) -> int:
    require(manifest["status"] == "legacy_reference_only", "Legacy status lost")
    require(manifest["m2_conformance"] == "not_m2_output", "Do not pass legacy data off as M2")
    require(manifest["p1_duration_status"] == "not_met_by_legacy_run", "Legacy is not new P1")
    for key in (
        "confirmed_product_id",
        "confirmed_knowledge_version",
        "confirmed_pkb_schema_version",
    ):
        require(manifest[key] is None, f"Do not invent confirmed metadata: {key}")
    source = manifest["source"]
    commit = source["commit"]
    base = source["base_path"]
    files = manifest["files"]
    paths = [item["path"] for item in files]
    require(len(set(paths)) == len(paths), "Duplicate manifest source")
    for item in files:
        content = blob(commit, item["path"])
        require(hashlib.sha256(content).hexdigest() == item["sha256"], "Source hash mismatch")
        json.loads(content)
    script = json.loads(blob(commit, manifest["selected_script"]))
    timeline = json.loads(blob(commit, base + "runs/pagenum-word/timeline.json"))
    tts = json.loads(blob(commit, base + "runs/pagenum-word/tts-log.json"))
    facts = json.loads(blob(commit, base + "facts.json"))
    require(
        manifest["legacy_measured_total_s"] == timeline["total_s"] == 22.0, "Keep measured duration"
    )
    rows = manifest["scene_migration_candidates"]
    require(len(rows) == len(script["scenes"]) == len(timeline["scenes"]), "Legacy scene mismatch")
    for index, row in enumerate(rows, 1):
        scene = script["scenes"][index - 1]
        timing = timeline["scenes"][index - 1]
        require(row["legacy_scene_number"] == index, "Legacy order changed")
        require(row["script_pointer"] == f"/scenes/{index - 1}", "Wrong legacy pointer")
        require(row["proposed_scene_id"] == f"s{index:02d}", "Wrong proposed scene ID")
        require(row["proposed_segment_id"] == f"s{index:02d}-u01", "Wrong proposed segment ID")
        require(row["canonical_m2_fact_refs"] is None, "Canonical PKB refs are not supplied")
        require(row["legacy_fact_ids"] == scene["fact_refs"], "Legacy fact refs changed")
        require(row["legacy_clip_refs"] == scene.get("clip_refs", []), "Legacy clip refs changed")
        require(tts[row["tts_log_key"]]["voice_text"] == scene["voice_text"], "Wrong TTS mapping")
        require(
            row["legacy_timeline"]
            == {
                "start_s": timing["start_s"],
                "duration_s": timing["duration_s"],
                "voice_s": timing["voice_s"],
            },
            "Do not alter legacy timings",
        )
        if scene.get("asset"):
            media = row["media"]
            require(media["legacy_path"] == scene["asset"], "Legacy media changed")
            require(media["resolved_asset_id"] is None, "Missing media has no resolved ID")
        else:
            require(row["media"] is None, "Text card must not invent an asset")
    fact_rows = manifest["fact_mapping_review"]
    require(len(fact_rows) == len(facts["facts"]), "Fact index incomplete")
    for actual, original in zip(fact_rows, facts["facts"], strict=True):
        require(actual["legacy_fact_id"] == original["id"], "Fact order changed")
        require(actual["source_id"] == original["source_id"], "Fact source changed")
        require(actual["origin"] == original["origin"], "Manual does not mean owner")
        require(actual["canonical_field_path"] is None, "Canonical path is unconfirmed")
        require(actual["conflicts_with"] == original.get("conflicts_with"), "Conflict lost")
    return len(files)


def main() -> None:
    selection = read_json("template-selection.proposal.json")
    source = selection["m2_source"]
    snapshot = (HERE / source["local_file"]).read_bytes()
    require(snapshot == blob(source["commit"], source["path"]), "M2 snapshot changed")
    require(hashlib.sha256(snapshot).hexdigest() == source["sha256"], "M2 snapshot hash mismatch")
    script = json.loads(snapshot)
    schema = json.loads(blob(source["commit"], "docs/specs/m2/p1-ac-03-script-vi.v1.schema.json"))
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema, format_checker=FormatChecker()).validate(script)
    blocked = validate_selection(selection, script)
    source_count = validate_pdfcraft(read_json("pdfcraft-source-manifest.json"))
    print(f"PASS: upstream M2 schema + pinned snapshot; {len(selection['scenes'])} scene bindings")
    print(f"PASS: {source_count} PDFCraft source hashes; 6 legacy scene/TTS/timeline mappings")
    print(f"REVIEW: {blocked} layout blocked; media/timeline/renderer remain unconfirmed")


if __name__ == "__main__":
    try:
        main()
    except (
        ValueError,
        KeyError,
        IndexError,
        OSError,
        subprocess.SubprocessError,
        SchemaError,
        ValidationError,
    ) as error:
        raise SystemExit(f"FAIL: {error}") from error
