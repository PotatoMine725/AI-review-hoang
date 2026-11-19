import json
from pathlib import Path

import pytest

from tts_common.normalize import normalizer_for
from tts_common.segments import Segment, load_segments, log_entry, stale_segments

SAMPLES = Path(__file__).parents[2] / "samples"


def _write(tmp_path: Path, data: object) -> Path:
    p = tmp_path / "in.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


def test_segment_id_from_input_or_position(tmp_path: Path) -> None:
    rows = [{"text": "a", "id": "hook"}, {"text": "b"}, {"text": "c", "segment_id": "cta"}]
    p = _write(tmp_path, {"segments": rows})
    assert [(s.index, s.segment_id, s.text) for s in load_segments(p)] == [
        (1, "hook", "a"),
        (2, "s02", "b"),
        (3, "cta", "c"),
    ]


def test_scenes_format(tmp_path: Path) -> None:
    p = _write(tmp_path, {"scenes": [{"voice_text": "x", "scene_id": "sc1"}, {"voice_text": "y"}]})
    assert [(s.segment_id, s.text) for s in load_segments(p)] == [("sc1", "x"), ("s02", "y")]


def test_bad_input(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="segments"):
        load_segments(_write(tmp_path, {"foo": []}))
    with pytest.raises(ValueError, match="trùng"):
        load_segments(_write(tmp_path, {"segments": [{"text": "a", "id": "x"}, {"text": "b", "id": "x"}]}))


def test_log_entry_keeps_link_and_fields() -> None:
    seg = Segment(2, "price", "Giá 390.000đ")
    e = log_entry(seg, "Giá ba trăm chín mươi nghìn đồng", "s02.wav", 3.14159, 1.234, voice="Mai Anh")
    assert e == {
        "segment_id": "price",
        "voice_text": "Giá 390.000đ",
        "normalized": "Giá ba trăm chín mươi nghìn đồng",
        "path": "s02.wav",
        "duration_s": 3.142,
        "gen_s": 1.23,
        "voice": "Mai Anh",
    }


def test_stale_segments_flags_changed_text_table_or_id() -> None:
    segs = [Segment(1, "a", "Gói ElevenLabs"), Segment(2, "b", "Hết")]
    norm = normalizer_for("vieneu")
    log = {str(s.index): log_entry(s, norm(s.text), f"s0{s.index}.wav", 1.0, 1.0, voice="v") for s in segs}
    assert stale_segments(segs, log, lambda s: norm(s.text)) == []
    # đổi bảng phát âm -> đoạn a cũ; đoạn b không ảnh hưởng
    assert stale_segments(segs, log, lambda s: normalizer_for("piper")(s.text)) == ["a"]
    # đổi lời
    assert stale_segments([Segment(1, "a", "Gói khác"), segs[1]], log, lambda s: norm(s.text)) == ["a"]
    # đổi id, hoặc chưa có trong log
    assert stale_segments([Segment(2, "b2", "Hết")], log, lambda s: norm(s.text)) == ["b2"]
    assert stale_segments(segs, {}, lambda s: norm(s.text)) == ["a", "b"]


def test_sample_files_are_consistent() -> None:
    """Log mẫu phải có đủ trường bàn giao và khớp đầu vào mẫu (lời gốc + id) và bảng VieNeu."""
    segs = load_segments(SAMPLES / "segments.sample.json")
    log = json.loads((SAMPLES / "tts-log.sample.json").read_text(encoding="utf-8"))
    norm = normalizer_for("vieneu")
    assert stale_segments(segs, log, lambda s: norm(s.text)) == []
    for seg in segs:
        entry = log[str(seg.index)]
        assert entry["duration_s"] > 0
        assert entry["path"].endswith(".wav")
