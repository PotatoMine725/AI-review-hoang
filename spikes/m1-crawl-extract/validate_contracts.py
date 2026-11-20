"""Kiểm tra contract bằng JSON Schema (jsonschema, dependency-group dev).

  uv run python validate_contracts.py

- `docs/specs/contracts/examples/valid-*.json` phải pass `cost-breakdown.v1.schema.json` hoặc `script.v0.schema.json`.
- `docs/specs/contracts/examples/invalid-*.json` phải fail schema tương ứng.
- `docs/specs/contracts/examples/*script*.json` kiểm tra thêm tổng thời lượng 15–60s và fact_ref trỏ tới PKB.
- `data` và `sources` của các PKB trong `output/` phải pass schema PKB v0.2, và cũng phải pass v0.3
  (v0.3 là superset: PKB v0.2 cũ đọc được, coi như `software`).
- `docs/specs/pkb/examples/valid-*.json` (dạng `{data, sources}`) phải pass schema PKB v0.3 và model Pydantic,
  `invalid-*.json` phải bị bắt bởi schema, hoặc bởi kiểm tham chiếu chéo (variant_ref, source_id).
- Với mỗi ví dụ, schema JSON và Pydantic phải cho cùng kết quả (chống lệch giữa 2 nơi khai báo luật).
Thoát với mã 1 nếu có dòng nào sai kỳ vọng.
"""

from __future__ import annotations

import json
import re
import sys
from copy import deepcopy
from pathlib import Path

from jsonschema import Draft202012Validator
from pydantic import ValidationError

from schema_v03 import PKBData as PKBDataV03

ROOT = Path(__file__).resolve().parents[2]
SPECS = ROOT / "docs" / "specs"
EXAMPLES = SPECS / "contracts" / "examples"
PKB_EXAMPLES = SPECS / "pkb" / "examples"
PKB_FILES = sorted(Path(__file__).resolve().parent.glob("output/*/pkb.gemini-3.5-flash-lite.json"))


def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def validator(path: Path) -> Draft202012Validator:
    schema = load(path)
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def first_error(v: Draft202012Validator, doc) -> str:
    errors = sorted(v.iter_errors(doc), key=lambda e: list(e.absolute_path))
    if not errors:
        return ""
    e = errors[0]
    where = "/".join(str(p) for p in e.absolute_path) or "(gốc)"
    return f"{where}: {e.message}"[:90]


def resolve_field_path(data: dict, path_str: str):
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*|\[\d+\])*", path_str):
        raise ValueError("cú pháp phải là key.key[index].key")
    tokens = re.findall(r"[^.\[\]]+|\[\d+\]", path_str)
    curr = data
    for token in tokens:
        if token.startswith("[") and token.endswith("]"):
            curr = curr[int(token[1:-1])]
        else:
            curr = curr[token]
    return curr


def conflict_paths_overlap(field_path: str, conflict_path: str) -> bool:
    """Return true when either valid dot-bracket path contains the other."""
    path_pattern = r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*|\[\d+\])*"
    if not isinstance(field_path, str) or not isinstance(conflict_path, str):
        return False
    if not re.fullmatch(path_pattern, field_path) or not re.fullmatch(path_pattern, conflict_path):
        return False
    path_tokens = re.findall(r"[^.\[\]]+|\[\d+\]", field_path)
    conflict_tokens = re.findall(r"[^.\[\]]+|\[\d+\]", conflict_path)
    common_length = min(len(path_tokens), len(conflict_tokens))
    return path_tokens[:common_length] == conflict_tokens[:common_length]


def pydantic_error(data: dict) -> str:
    """Kiểm bằng model Pydantic v0.3 (nguồn của schema)."""
    try:
        PKBDataV03.model_validate(data)
    except ValidationError as e:
        err = e.errors()[0]
        where = "/".join(str(p) for p in err["loc"]) or "(gốc)"
        return f"{where}: {err['msg']}"[:90]
    return ""


def ref_error(data: dict) -> str:
    """variant_ref phải trỏ tới variants[].id có thật. JSON Schema không diễn đạt được luật này."""
    ids = {v.get("id") for v in data.get("variants", [])}
    refs = [("offers", o) for o in data.get("offers", [])]
    refs += [("media.images", i) for i in (data.get("media") or {}).get("images", [])]
    for where, item in refs:
        ref = item.get("variant_ref")
        if ref is not None and ref not in ids:
            return f"{where}: variant_ref '{ref}' không có trong variants[]"
    return ""


def source_id_error(data: dict, sources: list[dict]) -> str:
    """Mọi `source_id` trong data phải có trong sources[].id."""
    known = {s["id"] for s in sources}
    stack: list = [data]
    while stack:
        node = stack.pop()
        if isinstance(node, dict):
            sid = node.get("source_id")
            if isinstance(sid, str) and sid not in known:
                return f"source_id '{sid}' không có trong sources"
            stack.extend(node.values())
        elif isinstance(node, list):
            stack.extend(node)
    return ""


def pkb_example_rows(data_v3, source_v3, data_v2) -> list[tuple[str, str, bool, str]]:
    rows: list[tuple[str, str, bool, str]] = []
    for path in sorted(PKB_EXAMPLES.glob("*.json")):
        want_valid = path.name.startswith("valid-")
        if not want_valid and not path.name.startswith("invalid-"):
            continue
        doc = load(path)
        data, sources = doc["data"], doc["sources"]
        schema_err = first_error(data_v3, data)
        sources_err = next((e for s in sources if (e := first_error(source_v3, s))), "")
        refs_err = ref_error(data)
        ids_err = source_id_error(data, sources)
        pyd_err = pydantic_error(data)
        err = schema_err or sources_err or refs_err or ids_err
        note = err or "hợp lệ"
        ok = (not err) == want_valid
        # Schema JSON và Pydantic phải cùng kết luận (source_id vs sources chỉ có ở validator này)
        if bool(schema_err or refs_err) != bool(pyd_err):
            ok = False
            note = f"LỆCH schema={schema_err or refs_err or 'đạt'!r} / pydantic={pyd_err or 'đạt'!r}"
        rows.append((f"examples/{path.name}", "pass" if want_valid else "fail", ok, note))
        if path.name.startswith("valid-v02-"):  # ví dụ v0.2 cũng phải đạt schema v0.2 gốc
            err = first_error(data_v2, data)
            rows.append((f"examples/{path.name} (schema 0.2)", "pass", not err, err or "hợp lệ"))
    return rows


def validate_script_content(doc: dict) -> str:
    """Kiểm tra logic phụ cho script: tổng thời lượng 15-60s và fact_ref trỏ tới PKB ElevenLabs."""
    scenes = doc.get("scenes", [])
    total_duration = sum(s.get("duration_s", 0) for s in scenes)
    if not (15.0 <= total_duration <= 60.0):
        return f"tổng thời lượng {total_duration}s ngoài khoảng 15–60s"

    elevenlabs_pkb_path = (
        ROOT / "spikes" / "m1-crawl-extract" / "output" / "elevenlabs" / "pkb.gemini-3.5-flash-lite.json"
    )
    if elevenlabs_pkb_path.exists():
        pkb = load(elevenlabs_pkb_path)
        valid_sources = {s["id"] for s in pkb.get("sources", [])}
        pkb_data = pkb.get("data", {})
        for s in scenes:
            for c in s.get("claims", []):
                fref = c.get("fact_ref")
                if not fref:
                    continue
                sid = fref.get("source_id")
                if sid not in valid_sources:
                    return f"source_id '{sid}' không có trong sources của PKB"
                fpath = fref.get("field_path", "")
                try:
                    val = resolve_field_path(pkb_data, fpath)
                    if val is None:
                        return f"fact_ref '{fpath}' trả về None"
                except (KeyError, IndexError, TypeError) as ex:
                    return f"fact_ref '{fpath}' không tồn tại trong PKB: {ex}"

    return ""


def validate_p1_vi_script_content(doc: dict, context: dict) -> str:
    """Kiểm tra fact refs, CTA và asset allowlist của fixture P1-AC-03 tiếng Việt."""
    pkb_path = ROOT / context["pkb_file"]
    pkb = load(pkb_path)
    approved_pkb = context.get("approved_pkb", {"schema_version": "0.2", **pkb})
    valid_sources = {source["id"] for source in approved_pkb.get("sources", [])}
    pkb_data = approved_pkb.get("data", {})
    declared_schema_version = approved_pkb.get("schema_version", pkb_data.get("schema_version"))
    if declared_schema_version not in {"0.2", "0.3"}:
        return f"PKB schema_version '{declared_schema_version}' chưa được hỗ trợ"
    if pkb_data.get("schema_version") != declared_schema_version:
        return "schema_version của wrapper không khớp schema_version trong PKB data"
    if doc.get("pkb_schema_version") != declared_schema_version:
        return "pkb_schema_version của output không khớp PKB đã được người dùng xác nhận"
    expected_product_id = context.get("product_id")
    if expected_product_id is not None and doc.get("product_id") != expected_product_id:
        return "product_id của output không khớp Product đầu vào"
    if doc.get("knowledge_version") != context.get("knowledge_version", doc.get("knowledge_version")):
        return "knowledge_version của output không khớp PKB đã được người dùng xác nhận"
    conflicts = (pkb_data.get("quality") or {}).get("conflicts") or []
    product_id = doc.get("product_id")
    permitted_assets = {
        asset["asset_id"]: asset["kind"]
        for asset in context.get("permitted_assets", [])
        if asset.get("product_id") == product_id
    }
    requested_cta = context.get("content_context", {}).get("cta")
    if requested_cta:
        if doc.get("cta", {}).get("text") != requested_cta.get("text"):
            return "cta.text không giữ nguyên nội dung người dùng cung cấp"
        if doc.get("cta", {}).get("destination") != requested_cta.get("destination"):
            return "cta.destination không giữ nguyên đích người dùng cung cấp"
    elif doc.get("cta", {}).get("destination") is not None:
        return "cta.destination phải null khi người dùng không cung cấp đích"

    def check_refs(refs: list[dict], label: str) -> str:
        for ref in refs:
            source_id = ref.get("source_id")
            field_path = ref.get("field_path", "")
            try:
                value = resolve_field_path(pkb_data, field_path)
            except (KeyError, IndexError, TypeError, ValueError) as ex:
                return f"{label}: fact_ref '{field_path}' không tồn tại: {ex}"
            if value is None:
                return f"{label}: fact_ref '{field_path}' trả về None"
            # A path may point at a nested value (e.g. identity.name.value);
            # use its nearest enclosing PKB fact to validate provenance.
            fact = value if isinstance(value, dict) else None
            prefix = ""
            for token in re.findall(r"[^.\[\]]+|\[\d+\]", field_path):
                prefix += token if token.startswith("[") else ("." if prefix else "") + token
                try:
                    candidate = resolve_field_path(pkb_data, prefix)
                except (KeyError, IndexError, TypeError, ValueError):
                    continue
                if isinstance(candidate, dict) and ("source_id" in candidate or "origin" in candidate):
                    fact = candidate
            if fact is None:
                return f"{label}: field_path '{field_path}' không trỏ tới fact có provenance"
            if fact.get("origin") == "inferred":
                return f"{label}: không dùng fact inferred chưa được người dùng xác nhận '{field_path}'"
            if any(
                isinstance(conflict, dict)
                and any(
                    conflict_paths_overlap(field_path, conflict.get(path_key))
                    for path_key in ("field_path", "field", "path")
                )
                for conflict in conflicts
            ):
                return f"{label}: fact '{field_path}' đang có xung đột chưa được giải quyết"
            fact_source_id = fact.get("source_id")
            if source_id is not None:
                if source_id not in valid_sources:
                    return f"{label}: source_id '{source_id}' không có trong PKB sources"
                if fact_source_id != source_id:
                    return f"{label}: source_id không khớp fact '{field_path}'"
            elif fact_source_id and fact_source_id not in valid_sources:
                return f"{label}: nguồn của fact '{field_path}' không có trong PKB sources"
        return ""

    refs_error = check_refs(doc.get("hook", {}).get("fact_refs", []), "hook")
    if refs_error:
        return refs_error
    refs_error = check_refs(doc.get("cta", {}).get("fact_refs", []), "cta")
    if refs_error:
        return refs_error

    seen_scene_ids: set[str] = set()
    seen_segment_ids: set[str] = set()
    for scene in doc.get("scenes", []):
        scene_id = scene.get("scene_id", "")
        if scene_id in seen_scene_ids:
            return f"scene_id '{scene_id}' bị trùng"
        seen_scene_ids.add(scene_id)
        scene_segment_ids: set[str] = set()
        for segment in scene.get("narration_segments", []):
            segment_id = segment.get("segment_id", "")
            if not segment_id.startswith(f"{scene_id}-u"):
                return f"segment_id '{segment_id}' không thuộc cảnh '{scene_id}'"
            if segment_id in seen_segment_ids:
                return f"segment_id '{segment_id}' bị trùng"
            seen_segment_ids.add(segment_id)
            scene_segment_ids.add(segment_id)
        visual = scene.get("visual_plan", {})
        if visual.get("kind") == "text_card":
            if visual.get("source_type") != "generated_text" or "asset_id" in visual or not visual.get("text"):
                return "text_card phải dùng generated_text, có text và không có asset_id"
        elif visual.get("source_type") == "existing_asset":
            asset_id = visual.get("asset_id")
            if asset_id not in permitted_assets:
                return f"asset_id '{asset_id}' không nằm trong allowlist của Product fixture"
            asset_kind = permitted_assets[asset_id]
            if visual.get("kind") != asset_kind:
                return f"cảnh '{scene_id}': asset_id '{asset_id}' phải dùng visual_plan.kind '{asset_kind}'"
        elif visual.get("source_type") == "ai_generation":
            if not visual.get("generation_request") or "asset_id" in visual:
                return "ai_generation cần generation_request riêng và không được có asset_id"
        elif visual.get("source_type") != "ai_generation":
            return f"source_type '{visual.get('source_type')}' không hợp lệ"
        for claim in scene.get("claims", []):
            claim_segment_ids = claim.get("segment_ids", [])
            if not claim_segment_ids or not set(claim_segment_ids).issubset(scene_segment_ids):
                return f"claim '{claim.get('text', '')[:40]}' không gắn với segment trong cảnh"
            fact_refs = claim.get("fact_refs", [])
            if not fact_refs:
                return f"claim '{claim.get('text', '')[:40]}' thiếu fact_refs"
            refs_error = check_refs(fact_refs, "claim")
            if refs_error:
                return refs_error

    # Compare spoken content without changing words or punctuation.
    def normalize_speech(text: str) -> str:
        return " ".join(text.split())
    scenes = doc.get("scenes", [])
    if not scenes or not scenes[0].get("narration_segments"):
        return "hook cần segment mở đầu"
    if normalize_speech(scenes[0]["narration_segments"][0]["text"]) != normalize_speech(doc["hook"]["text"]):
        return "hook.text phải được đọc trong segment đầu"
    ending = scenes[-1]
    if ending.get("role") != "cta":
        return "cảnh cuối phải có role cta và lời đọc CTA"
    spoken = normalize_speech(" ".join(s["text"] for s in ending.get("narration_segments", [])))
    cta = normalize_speech(doc["cta"]["text"])
    if spoken != cta and not spoken.endswith(" " + cta):
        return "cảnh cta phải kết bằng lời đọc cta.text"
    return ""


def validate_p1_vi_input_schema(context: dict) -> str:
    """Kiểm tra wrapper input bằng PKB fixture thật và context/asset tổng hợp."""
    pkb = load(ROOT / context["pkb_file"])
    input_schema = validator(SPECS / "m2" / "p1-ac-03-input.v1.schema.json")
    doc = {
        "schema_version": "p1-ac-03-input.v1-draft",
        "product_id": context.get("product_id", "9f8a3c20-7b41-4e89-bc52-1d0e4f3a7a99"),
        "knowledge_version": context.get("knowledge_version", 1),
        "approved_pkb": {
            "status": "approved",
            "schema_version": context.get("pkb_schema_version", pkb["data"].get("schema_version")),
            "data": pkb["data"],
            "sources": pkb["sources"],
        },
        "permitted_assets": context["permitted_assets"],
    }
    if "content_context" in context:
        doc["content_context"] = context["content_context"]
    err = first_error(input_schema, doc)
    if err:
        return err
    if doc["approved_pkb"]["schema_version"] != doc["approved_pkb"]["data"].get("schema_version"):
        return "schema_version của wrapper không khớp schema_version trong PKB data"
    if doc["knowledge_version"] < 1:
        return "knowledge_version phải là phiên bản PKB đã được người dùng xác nhận"
    return ""


def main() -> int:
    rows: list[tuple[str, str, bool, str]] = []  # (file, kỳ vọng, đạt, ghi chú)

    cost_v = validator(SPECS / "contracts" / "cost-breakdown.v1.schema.json")
    script_v = validator(SPECS / "contracts" / "script.v0.schema.json")
    p1_vi_script_v = validator(SPECS / "m2" / "p1-ac-03-script-vi.v1.schema.json")

    for path in sorted(EXAMPLES.glob("*.json")):
        want_valid = path.name.startswith("valid-")
        if not want_valid and not path.name.startswith("invalid-"):
            continue

        doc = load(path)
        if "-script-" in path.name:
            err = first_error(script_v, doc)
            if want_valid and not err:
                err = validate_script_content(doc)
            rows.append(
                (
                    path.name,
                    "pass" if want_valid else "fail",
                    (not err) == want_valid,
                    err or "hợp lệ",
                )
            )
        else:
            err = first_error(cost_v, doc)
            rows.append(
                (
                    path.name,
                    "pass" if want_valid else "fail",
                    (not err) == want_valid,
                    err or "hợp lệ",
                )
            )

    p1_vi_examples = SPECS / "m2" / "examples"
    input_context_path = p1_vi_examples / "valid-script-p1-ac-03-vi.context.json"
    input_context = load(input_context_path)
    input_error = validate_p1_vi_input_schema(input_context)
    rows.append(
        (
            "m2/p1-ac-03-input.v1.schema.json",
            "pass",
            not input_error,
            input_error or "PKB + synthetic allowlist/content context pass",
        )
    )
    standalone_context = {**input_context}
    standalone_context.pop("content_context", None)
    standalone_error = validate_p1_vi_input_schema(standalone_context)
    rows.append(
        (
            "m2/input-without-campaign.json",
            "pass",
            not standalone_error,
            standalone_error or "PKB + allowlist pass without Campaign/Affiliate context",
        )
    )
    for label, description, want_valid in (
        ("absent", None, True),
        ("one-character", "A", True),
        ("max-length", "A" * 2000, True),
        ("too-long", "A" * 2001, False),
        ("empty", "", False),
        ("whitespace", " \n\t", False),
        ("wrong-type", 123, False),
    ):
        description_context = deepcopy(input_context)
        if description is None:
            description_context["content_context"].pop("video_description", None)
        else:
            description_context["content_context"]["video_description"] = description
        err = validate_p1_vi_input_schema(description_context)
        rows.append(
            (
                f"m2/video-description-{label}",
                "pass" if want_valid else "fail",
                (not err) == want_valid,
                err or "hợp lệ",
            )
        )

    mismatched_pkb_context = {**input_context, "pkb_schema_version": "0.3"}
    mismatched_pkb_error = validate_p1_vi_input_schema(mismatched_pkb_context)
    rows.append(
        (
            "m2/input-pkb-version-must-match-data.json",
            "fail",
            bool(mismatched_pkb_error),
            mismatched_pkb_error or "mismatched PKB schema version was accepted",
        )
    )
    for path in sorted(p1_vi_examples.glob("*-script-p1-ac-03-vi*.json")):
        if path.name.endswith(".context.json"):
            continue
        want_valid = path.name.startswith("valid-")
        doc = load(path)
        err = first_error(p1_vi_script_v, doc)
        if not err:
            err = validate_p1_vi_script_content(doc, input_context)
        rows.append(
            (
                f"m2/examples/{path.name}",
                "pass" if want_valid else "fail",
                (not err) == want_valid,
                err or "hợp lệ",
            )
        )

    p1_script_path = p1_vi_examples / "valid-script-p1-ac-03-vi.json"
    p1_script = load(p1_script_path)
    for case, want_error in (("hook-mismatch", "hook.text"), ("missing-cta-scene", "role cta"),
                             ("cta-not-spoken", "cta.text"), ("speech-whitespace", "")):
        speech_script = deepcopy(p1_script)
        if case == "hook-mismatch":
            speech_script["scenes"][0]["narration_segments"][0]["text"] = "Nội dung khác."
        elif case == "missing-cta-scene":
            speech_script["scenes"][-1]["role"] = "result"
        elif case == "cta-not-spoken":
            speech_script["scenes"][-1]["narration_segments"][0]["text"] = "Lời kết khác."
        else:
            speech_script["scenes"][0]["narration_segments"][0]["text"] = "  " + speech_script["hook"]["text"] + "\n"
        err = validate_p1_vi_script_content(speech_script, input_context)
        rows.append((f"m2/{case}", "fail" if want_error else "pass",
                     want_error in err if want_error else not err, err or "hợp lệ"))

    stat_script = deepcopy(p1_script)
    stat = {"value": "40", "label": "Giá trị fixture", "unit": "%", "scope": "Synthetic schema check only"}
    stat_script["scenes"][0]["claims"][0]["stat_display"] = stat
    for missing in (None, "value", "label", "unit", "scope"):
        candidate = deepcopy(stat_script)
        if missing:
            del candidate["scenes"][0]["claims"][0]["stat_display"][missing]
        err = first_error(p1_vi_script_v, candidate)
        rows.append((f"m2/stat-display-{missing or 'complete'}", "fail" if missing else "pass",
                     bool(err) if missing else not err, err or "schema only; meaning not verified"))

    description_ref_script = deepcopy(p1_script)
    description_ref_script["scenes"][0]["claims"][0]["fact_refs"] = [
        {"field_path": "content_context.video_description"}
    ]
    description_ref_error = validate_p1_vi_script_content(description_ref_script, input_context)
    rows.append(
        (
            "m2/video-description-is-not-pkb-fact",
            "fail",
            bool(description_ref_error),
            description_ref_error or "description accepted as fact",
        )
    )

    wrong_output_schema = deepcopy(p1_script)
    wrong_output_schema["schema_version"] = "0.3"
    wrong_output_schema_error = first_error(p1_vi_script_v, wrong_output_schema)
    rows.append(
        (
            "m2/output-schema-version-must-use-contract-constant.json",
            "fail",
            bool(wrong_output_schema_error),
            wrong_output_schema_error or "incorrect schema_version was accepted",
        )
    )
    wrong_product_id_context = {**input_context, "product_id": "00000000-0000-4000-8000-000000000000"}
    wrong_product_id_error = validate_p1_vi_script_content(p1_script, wrong_product_id_context)
    rows.append(
        (
            "m2/output-product-id-must-match-input.json",
            "fail",
            bool(wrong_product_id_error),
            wrong_product_id_error or "output product_id did not match input",
        )
    )
    wrong_knowledge_version_context = {**input_context, "knowledge_version": 2}
    wrong_knowledge_version_error = validate_p1_vi_script_content(
        p1_script, wrong_knowledge_version_context
    )
    rows.append(
        (
            "m2/output-knowledge-version-must-match-input.json",
            "fail",
            bool(wrong_knowledge_version_error),
            wrong_knowledge_version_error or "output knowledge_version did not match input",
        )
    )
    for target_duration, want_valid in ((39, False), (40, True), (45, True), (46, False)):
        duration_script = deepcopy(p1_script)
        duration_script["target_duration_s"] = target_duration
        duration_error = first_error(p1_vi_script_v, duration_script)
        if not duration_error:
            duration_error = validate_p1_vi_script_content(duration_script, input_context)
        rows.append(
            (
                f"m2/target-duration-{target_duration}s-contract-only",
                "pass" if want_valid else "fail",
                (not duration_error) == want_valid,
                duration_error or "target nằm trong contract 40–45s; không đo MP4 thực tế",
            )
        )

    ai_visual_script = json.loads(json.dumps(p1_script))
    ai_visual = ai_visual_script["scenes"][0]["visual_plan"]
    ai_visual.pop("asset_id")
    ai_visual["kind"] = "ai_generated_image"
    ai_visual["source_type"] = "ai_generation"
    ai_visual["generation_request"] = "Ảnh minh họa trừu tượng, không khẳng định tính năng mới."
    ai_visual_schema_error = first_error(p1_vi_script_v, ai_visual_script)
    if not ai_visual_schema_error:
        ai_visual_schema_error = validate_p1_vi_script_content(ai_visual_script, input_context)
    rows.append(
        (
            "m2/ai-generation-request-is-not-asset",
            "pass",
            not ai_visual_schema_error,
            ai_visual_schema_error or "AI image requirement is separate from stored allowlisted assets",
        )
    )

    one_scene_script = deepcopy(p1_script)
    one_scene_script["scenes"] = one_scene_script["scenes"][:1]
    one_scene_script["scenes"][0]["narration_segments"].append(
        {"segment_id": "s01-u02", "text": p1_script["cta"]["text"]}
    )
    one_scene_script["scenes"][0]["role"] = "cta"
    one_scene_error = first_error(p1_vi_script_v, one_scene_script)
    if not one_scene_error:
        one_scene_error = validate_p1_vi_script_content(one_scene_script, input_context)
    rows.append(
        (
            "m2/one-scene-with-multiple-tts-segments.json",
            "pass",
            not one_scene_error,
            one_scene_error or "One scene and ordered segments are valid; duration remains an integration check",
        )
    )

    def script_with_scene_count(count: int) -> dict:
        doc = deepcopy(p1_script)
        template = p1_script["scenes"][0]
        doc["scenes"] = []
        for index in range(1, count + 1):
            scene = deepcopy(template)
            scene_id = f"s{index:02d}"
            scene["scene_id"] = scene_id
            segment_ids = []
            for segment_index, segment in enumerate(scene["narration_segments"], start=1):
                segment_id = f"{scene_id}-u{segment_index:02d}"
                segment["segment_id"] = segment_id
                segment_ids.append(segment_id)
            for claim in scene["claims"]:
                claim["segment_ids"] = segment_ids
            doc["scenes"].append(scene)
        doc["scenes"][-1]["role"] = "cta"
        doc["scenes"][-1]["narration_segments"].append(
            {"segment_id": f"s{count:02d}-u02", "text": doc["cta"]["text"]}
        )
        return doc

    for scene_count, want_valid in ((12, True), (13, False)):
        scene_count_script = script_with_scene_count(scene_count)
        scene_count_error = first_error(p1_vi_script_v, scene_count_script)
        if not scene_count_error:
            scene_count_error = validate_p1_vi_script_content(scene_count_script, input_context)
        rows.append(
            (
                f"m2/{scene_count}-scenes-{'within' if want_valid else 'over'}-technical-limit.json",
                "pass" if want_valid else "fail",
                (not scene_count_error) == want_valid,
                scene_count_error or f"{scene_count} scenes {'accepted' if want_valid else 'unexpectedly accepted'}",
            )
        )

    text_card_asset_script = deepcopy(p1_script)
    text_card_asset = text_card_asset_script["scenes"][3]["visual_plan"]
    text_card_asset["source_type"] = "generated_text"
    text_card_asset["text"] = "CTA card"
    text_card_asset["asset_id"] = "fixture:card:cta"
    text_card_schema_error = first_error(p1_vi_script_v, text_card_asset_script)
    rows.append(
        (
            "m2/text-card-must-not-reference-an-asset.json",
            "fail",
            bool(text_card_schema_error),
            text_card_schema_error or "text_card with asset_id was accepted",
        )
    )

    owner_context = deepcopy(input_context)
    owner_context["approved_pkb"] = {
        "schema_version": "0.2",
        "data": deepcopy(load(ROOT / owner_context["pkb_file"])["data"]),
        "sources": load(ROOT / owner_context["pkb_file"])["sources"],
    }
    owner_fact = owner_context["approved_pkb"]["data"]["identity"]["category"]
    owner_fact["origin"] = "owner"
    owner_fact.pop("source_id", None)
    owner_script = deepcopy(p1_script)
    owner_script["hook"]["fact_refs"][0].pop("source_id", None)
    owner_script["scenes"][0]["claims"][0]["fact_refs"][0].pop("source_id", None)
    owner_error = validate_p1_vi_script_content(owner_script, owner_context)
    rows.append(
        (
            "m2/owner-fact-reference-without-crawl-source.json",
            "pass",
            not owner_error,
            owner_error or "Owner fact resolves by field_path without a fabricated crawl source",
        )
    )

    inferred_context = deepcopy(owner_context)
    inferred_context["approved_pkb"]["data"]["identity"]["category"]["origin"] = "inferred"
    inferred_script = deepcopy(owner_script)
    inferred_error = validate_p1_vi_script_content(inferred_script, inferred_context)
    rows.append(
        (
            "m2/unapproved-inferred-fact-is-rejected.json",
            "fail",
            bool(inferred_error),
            inferred_error or "unapproved inferred fact was accepted",
        )
    )

    conflict_context = deepcopy(owner_context)
    quality = conflict_context["approved_pkb"]["data"].get("quality") or {}
    quality["conflicts"] = [{"field_path": "identity.category"}]
    conflict_context["approved_pkb"]["data"]["quality"] = quality
    conflict_error = validate_p1_vi_script_content(deepcopy(owner_script), conflict_context)
    rows.append(
        (
            "m2/unresolved-conflict-fact-is-rejected.json",
            "fail",
            "đang có xung đột" in conflict_error,
            conflict_error or "fact in unresolved conflict was accepted",
        )
    )

    def script_with_refs(field_path: str, source_id: str) -> dict:
        script = deepcopy(p1_script)
        refs = [*script["hook"]["fact_refs"], *script["scenes"][0]["claims"][0]["fact_refs"]]
        for ref in refs:
            ref["field_path"] = field_path
            ref["source_id"] = source_id
        return script

    # The input fixture stores a PKB file reference; materialize the same
    # approved wrapper used by the input contract before injecting conflicts.
    conflict_base_context = deepcopy(input_context)
    conflict_pkb = load(ROOT / input_context["pkb_file"])
    conflict_base_context["approved_pkb"] = {
        "schema_version": input_context["pkb_schema_version"],
        "data": deepcopy(conflict_pkb["data"]),
        "sources": deepcopy(conflict_pkb["sources"]),
    }

    conflict_path_cases = (
        (
            "m2/conflict-parent-blocks-child-reference.json",
            "identity.category.value",
            "src_01",
            "identity.category",
            False,
            "field_path",
        ),
        (
            "m2/conflict-field-alias-blocks-nested-reference.json",
            "identity.category.value",
            "src_01",
            "identity.category",
            False,
            "field",
        ),
        (
            "m2/conflict-child-blocks-fact-reference.json",
            "identity.category",
            "src_01",
            "identity.category.value",
            False,
            "field_path",
        ),
        (
            "m2/conflict-child-blocks-parent-reference.json",
            "pricing.plans[0]",
            "src_02",
            "pricing.plans[0].list_price",
            False,
            "field_path",
        ),
        (
            "m2/conflict-does-not-block-sibling-reference.json",
            "pricing.plans[0].name",
            "src_02",
            "pricing.plans[0].list_price",
            True,
            "field_path",
        ),
        (
            "m2/array-index-conflict-paths-use-token-boundaries.json",
            "pricing.plans[1].list_price",
            "src_02",
            "pricing.plans[10].list_price",
            True,
            "field_path",
        ),
        (
            "m2/conflict-does-not-block-unrelated-fact.json",
            "identity.category",
            "src_01",
            "pricing.plans[0].list_price",
            True,
            "field_path",
        ),
    )
    for case_name, ref_path, source_id, conflict_path, want_valid, conflict_key in conflict_path_cases:
        path_context = deepcopy(conflict_base_context)
        quality = path_context["approved_pkb"]["data"].get("quality") or {}
        quality["conflicts"] = [{conflict_key: conflict_path}]
        path_context["approved_pkb"]["data"]["quality"] = quality
        path_error = validate_p1_vi_script_content(
            script_with_refs(ref_path, source_id), path_context
        )
        path_handled_as_expected = (
            not path_error if want_valid else "đang có xung đột" in path_error
        )
        rows.append(
            (
                case_name,
                "pass" if want_valid else "fail",
                path_handled_as_expected,
                path_error or f"conflict path handling {'accepted' if want_valid else 'unexpectedly accepted'}",
            )
        )

    wrong_source_script = deepcopy(p1_script)
    wrong_source_script["hook"]["fact_refs"][0]["source_id"] = "src_02"
    wrong_source_error = validate_p1_vi_script_content(wrong_source_script, input_context)
    rows.append(
        (
            "m2/source-id-must-match-referenced-fact.json",
            "fail",
            bool(wrong_source_error),
            wrong_source_error or "source_id not matching its fact was accepted",
        )
    )

    malformed_path_script = deepcopy(p1_script)
    malformed_path_script["hook"]["fact_refs"][0]["field_path"] = "identity..category"
    malformed_path_error = validate_p1_vi_script_content(malformed_path_script, input_context)
    rows.append(
        (
            "m2/fact-ref-path-syntax.json",
            "fail",
            bool(malformed_path_error),
            malformed_path_error or "malformed field_path was accepted",
        )
    )

    wrong_cta_script = json.loads(json.dumps(p1_script))
    wrong_cta_script["cta"]["destination"] = "https://unprovided.example/"
    wrong_cta_error = validate_p1_vi_script_content(wrong_cta_script, input_context)
    rows.append(
        (
            "m2/cta-destination-must-match-input.json",
            "fail",
            bool(wrong_cta_error),
            wrong_cta_error or "CTA destination differed from supplied input",
        )
    )

    invalid_cta_ref_script = deepcopy(p1_script)
    invalid_cta_ref_script["cta"]["fact_refs"] = [{"field_path": "identity..website"}]
    invalid_cta_ref_error = validate_p1_vi_script_content(invalid_cta_ref_script, input_context)
    rows.append(
        (
            "m2/cta-fact-refs-must-resolve-to-pkb.json",
            "fail",
            bool(invalid_cta_ref_error),
            invalid_cta_ref_error or "invalid CTA fact ref was accepted",
        )
    )

    valid_cta_ref_script = deepcopy(p1_script)
    valid_cta_ref_script["cta"]["fact_refs"] = [
        {"source_id": "src_01", "field_path": "identity.category"}
    ]
    valid_cta_ref_error = validate_p1_vi_script_content(valid_cta_ref_script, standalone_context)
    rows.append(
        (
            "m2/cta-fact-refs-are-validated-like-claim-refs.json",
            "pass",
            not valid_cta_ref_error,
            valid_cta_ref_error or "CTA fact ref resolves and matches its source",
        )
    )

    standalone_script = json.loads(json.dumps(p1_script))
    standalone_script.update(
        {
            "platform": "tiktok",
            "audience": "Người xem phổ thông",
            "context_defaults_applied": ["platform", "intent", "audience", "cta"],
            "intent": "awareness",
            "cta": {"text": "Xem thêm thông tin.", "destination": None},
        }
    )
    standalone_script["scenes"][-1]["narration_segments"][0]["text"] = standalone_script["cta"]["text"]
    standalone_schema_error = first_error(p1_vi_script_v, standalone_script)
    if not standalone_schema_error:
        standalone_schema_error = validate_p1_vi_script_content(standalone_script, standalone_context)
    rows.append(
        (
            "m2/script-without-campaign-context.json",
            "pass",
            not standalone_schema_error,
            standalone_schema_error or "Explicit defaults used without Campaign/Affiliate",
        )
    )

    # Run12: a neutral call to action belongs in narration/cta, not a fabricated claim.
    # Keep the empty-claims path valid without exempting product claims in CTA scenes.
    for add_claim in (False, True):
        neutral_cta_script = deepcopy(standalone_script)
        scene = neutral_cta_script["scenes"][-1]
        scene["subtitle_text"] = neutral_cta_script["cta"]["text"]
        scene["visual_plan"]["text"] = neutral_cta_script["cta"]["text"]
        scene["claims"] = []
        if add_claim:
            scene["claims"].append({
                "text": "Sản phẩm miễn phí.",
                "type": "pricing",
                "segment_ids": [scene["narration_segments"][0]["segment_id"]],
                "fact_refs": [],
            })
        error = first_error(p1_vi_script_v, neutral_cta_script)
        if not error:
            error = validate_p1_vi_script_content(neutral_cta_script, standalone_context)
        rows.append((
            "m2/cta-product-claim-still-needs-refs" if add_claim else "m2/neutral-cta-empty-claims",
            "fail" if add_claim else "pass",
            "thiếu fact_refs" in error if add_claim else not error,
            error or "neutral CTA remains spoken without a product claim",
        ))

    wrong_product_context = json.loads(json.dumps(input_context))
    wrong_product_context["permitted_assets"][0]["product_id"] = "00000000-0000-4000-8000-000000000000"
    wrong_product_script = json.loads(json.dumps(p1_script))
    wrong_product_error = validate_p1_vi_script_content(wrong_product_script, wrong_product_context)
    rows.append(
        (
            "m2/asset-from-different-product.json",
            "fail",
            bool(wrong_product_error),
            wrong_product_error or "asset from another Product was accepted",
        )
    )

    wrong_asset_kind_script = deepcopy(p1_script)
    wrong_asset_kind_script["scenes"][0]["visual_plan"]["kind"] = "logo"
    wrong_asset_kind_error = first_error(p1_vi_script_v, wrong_asset_kind_script)
    if not wrong_asset_kind_error:
        wrong_asset_kind_error = validate_p1_vi_script_content(wrong_asset_kind_script, input_context)
    rows.append(
        (
            "m2/screen-recording-cannot-be-used-as-logo.json",
            "fail",
            "phải dùng visual_plan.kind 'screen_recording'" in wrong_asset_kind_error,
            wrong_asset_kind_error or "screen recording was accepted as a logo",
        )
    )

    data_v = validator(SPECS / "pkb" / "pkb-data.v0.2.schema.json")
    source_v = validator(SPECS / "pkb" / "pkb-sources.v0.2.schema.json")
    data_v3 = validator(SPECS / "pkb" / "pkb-data.v0.3.schema.json")
    source_v3 = validator(SPECS / "pkb" / "pkb-sources.v0.3.schema.json")
    for path in PKB_FILES:
        doc = load(path)
        name = f"{path.parent.name}/{path.name}"
        err = first_error(data_v, doc["data"])
        rows.append((f"{name} (data)", "pass", not err, err or "hợp lệ"))
        err = next((e for s in doc["sources"] if (e := first_error(source_v, s))), "")
        rows.append((f"{name} (sources)", "pass", not err, err or "hợp lệ"))
        err = first_error(data_v3, doc["data"])  # superset: PKB v0.2 cũ vẫn hợp lệ ở schema 0.3
        rows.append((f"{name} (data, schema 0.3)", "pass", not err, err or "hợp lệ"))
        err = next((e for s in doc["sources"] if (e := first_error(source_v3, s))), "")
        rows.append((f"{name} (sources, schema 0.3)", "pass", not err, err or "hợp lệ"))

    rows += pkb_example_rows(data_v3, source_v3, data_v)

    width = max(len(r[0]) for r in rows)
    print(f"{'File'.ljust(width)}  Kỳ vọng  Kết quả  Ghi chú")
    for name, want, ok, note in rows:
        print(f"{name.ljust(width)}  {want.ljust(7)}  {'ĐẠT' if ok else 'SAI'.ljust(3)}     {note}")
    bad = [r for r in rows if not r[2]]
    print(f"\n{len(rows) - len(bad)}/{len(rows)} đạt kỳ vọng")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore[attr-defined]
    raise SystemExit(main())
