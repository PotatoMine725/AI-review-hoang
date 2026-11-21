import json
import wave
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from tts_common import FakeTTS, estimate_duration_s, split_sentences, synthesize_script

SCHEMA = Path(__file__).parents[4] / "docs" / "specs" / "contracts" / "cost-breakdown.v1.schema.json"


def test_fake_tts_wav_matches_estimate(tmp_path: Path) -> None:
    text = "Bình giữ nhiệt chỉ còn ba trăm chín mươi nghìn đồng."
    res = FakeTTS(tmp_path).synthesize(text, voice="any", speed=1.0)
    assert res.provider == "fake"
    assert res.timings is None
    assert res.duration_s == pytest.approx(estimate_duration_s(text), abs=0.01)
    with wave.open(str(res.path), "rb") as w:
        assert w.getnchannels() == 1
        assert w.getnframes() / w.getframerate() == pytest.approx(res.duration_s)
        assert set(w.readframes(w.getnframes())) == {0}  # im lặng


def test_fake_tts_speed_shortens_audio(tmp_path: Path) -> None:
    tts = FakeTTS(tmp_path)
    slow = tts.synthesize("một hai ba bốn năm sáu", "v", 1.0).duration_s
    fast = tts.synthesize("một hai ba bốn năm sáu", "v", 2.0).duration_s
    assert fast == pytest.approx(slow / 2, abs=0.02)


def test_split_sentences_keeps_numbers_and_abbreviations() -> None:
    text = "Giá 390.000đ, giảm 3.5%. Ở TP.HCM có bán! Bấm link ngay?\nXong…"
    assert split_sentences(text) == [
        "Giá 390.000đ, giảm 3.5%.",
        "Ở TP.HCM có bán!",
        "Bấm link ngay?",
        "Xong…",
    ]


def test_script_timings_are_sequential(tmp_path: Path) -> None:
    script = "Bạn còn mất cả buổi làm video? Giá chỉ 390.000đ. Bấm link ngay!"
    out = synthesize_script(FakeTTS(tmp_path), script, "v", gap_s=0.2, merged_path=tmp_path / "all.wav")
    assert [s.text for s in out.sentences] == split_sentences(script)
    assert out.sentences[1].spoken == "Giá chỉ ba trăm chín mươi nghìn đồng."
    for prev, nxt in zip(out.sentences, out.sentences[1:], strict=False):
        assert nxt.start_s == pytest.approx(prev.end_s + 0.2)
    assert out.path is not None
    with wave.open(str(out.path), "rb") as w:
        assert w.getnframes() / w.getframerate() == pytest.approx(out.duration_s, abs=0.01)


def test_cost_item_conforms_to_cost_breakdown_v1(tmp_path: Path) -> None:
    res = FakeTTS(tmp_path).synthesize("xin chào", "v")
    item = res.cost.to_item(provider=res.provider, model=res.model)
    doc = {"schema_version": 1, "currency": "USD", "items": [item]}
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema).iter_errors(doc))
    assert errors == []
    assert item["category"] == "tts"
