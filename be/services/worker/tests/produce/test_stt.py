"""Mốc từng từ từ STT: chia cue bám nhịp đọc + adapter OpenAI (httpx giả, không gọi mạng)."""

from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest

from worker.produce.cues import Cue, time_cues, time_cues_words
from worker.produce.errors import ProduceError
from worker.produce.stt import (
    LocalWordStt,
    OpenAIWordStt,
    make_stt,
    parse_words,
    stt_cost_usd,
    transcribe_segments,
)

TEXTS = ["Xử lý PDF miễn phí", "ngay trong trình duyệt"]
# 9 từ; câu dài 3,6 s, nhưng nửa sau đọc chậm hơn nhiều so với tỉ lệ ký tự
WORDS = [
    ("Xử", 0.0, 0.2), ("lý", 0.2, 0.4), ("PDF", 0.4, 0.9), ("miễn", 0.9, 1.2), ("phí,", 1.2, 1.6),
    ("ngay", 2.0, 2.3), ("trong", 2.3, 2.6), ("trình", 2.6, 3.0), ("duyệt.", 3.0, 3.6),
]  # fmt: skip


def test_cue_boundary_follows_first_word_of_next_cue() -> None:
    out = time_cues_words(TEXTS, WORDS, 10.0, 13.6)
    assert out == [Cue(TEXTS[0], 10.0, 12.0), Cue(TEXTS[1], 12.0, 13.6)]
    by_chars = time_cues(TEXTS, 10.0, 13.6)
    assert by_chars[0].end_s != pytest.approx(12.0, abs=0.05)  # khác cách chia theo ký tự


def test_unmatched_words_are_interpolated_and_cues_stay_contiguous() -> None:
    words = [w for w in WORDS if w[0] not in ("PDF", "miễn")]  # STT sót 2 từ
    out = time_cues_words(TEXTS, words, 0.0, 3.6)
    assert out is not None
    assert out[0].start_s == 0.0 and out[-1].end_s == 3.6
    assert out[0].end_s == out[1].start_s
    assert 1.4 < out[0].end_s < 2.1


def test_numbers_and_accents_normalised_for_matching() -> None:
    texts = ["Có 5 công cụ", "miễn phí"]
    words = [("Có", 0, .3), ("năm", .3, .6), ("công", .6, .9), ("cụ", .9, 1.2),
             ("miễn", 1.5, 1.8), ("phí", 1.8, 2.1)]  # fmt: skip
    out = time_cues_words(texts, words, 0.0, 2.1)
    assert out is not None and out[0].end_s == pytest.approx(1.5)


def test_poor_match_returns_none_so_caller_falls_back() -> None:
    junk = [("lorem", 0, 1), ("ipsum", 1, 2), ("dolor", 2, 3)]
    assert time_cues_words(TEXTS, junk, 0.0, 3.0) is None
    assert time_cues_words(TEXTS, [], 0.0, 3.0) is None


def test_boundary_clamped_inside_segment() -> None:
    late = [(w, s + 5, e + 5) for w, s, e in WORDS]  # STT lệch hẳn ra ngoài audio
    out = time_cues_words(TEXTS, late, 0.0, 3.6)
    assert out is not None
    assert out[0].end_s <= 3.6 - 0.05 and out[0].end_s == out[1].start_s


def test_parse_words_skips_broken_items() -> None:
    data = {
        "words": [{"word": " a ", "start": 0, "end": 0.5}, {"word": "b"}, {"start": 1, "end": 2}]
    }
    assert parse_words(data) == [("a", 0.0, 0.5)]


def _wav(tmp_path: Path, name: str = "a.wav", data: bytes = b"RIFFxxxx") -> Path:
    p = tmp_path / name
    p.write_bytes(data)
    return p


def _stt(tmp_path: Path, handler, **kw) -> OpenAIWordStt:  # noqa: ANN001, ANN003
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return OpenAIWordStt("k", cache_dir=tmp_path / "c", client=client, retry_delays_s=(0.0,), **kw)


def test_transcribe_sends_word_granularity_and_caches(tmp_path: Path) -> None:
    seen: list[httpx.Request] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(req)
        return httpx.Response(200, json={"words": [{"word": "xin", "start": 0, "end": 0.3}]})

    stt = _stt(tmp_path, handler)
    wav = _wav(tmp_path)
    assert stt.transcribe(wav) == [("xin", 0.0, 0.3)]
    assert stt.transcribe(wav) == [("xin", 0.0, 0.3)]  # lần 2 từ cache
    assert len(seen) == 1 and stt.calls == 1 and stt.cached == 1
    body = seen[0].content.decode("latin-1")
    assert "timestamp_granularities[]" in body and "whisper-1" in body and "verbose_json" in body
    assert seen[0].headers["authorization"] == "Bearer k"


def test_retry_on_503_then_success_and_no_retry_on_401(tmp_path: Path) -> None:
    codes = iter([503, 200])

    def flaky(req: httpx.Request) -> httpx.Response:
        c = next(codes)
        return httpx.Response(c, json={"words": []} if c == 200 else {})

    assert _stt(tmp_path, flaky).transcribe(_wav(tmp_path)) == []
    calls = 0

    def denied(req: httpx.Request) -> httpx.Response:
        nonlocal calls
        calls += 1
        return httpx.Response(401, text="bad key")

    with pytest.raises(ProduceError, match="401"):
        _stt(tmp_path, denied).transcribe(_wav(tmp_path, "b.wav", b"other"))
    assert calls == 1


def test_only_whisper_has_word_timestamps(tmp_path: Path) -> None:
    with pytest.raises(ProduceError, match="whisper-1"):
        OpenAIWordStt("k", model="gpt-4o-transcribe")


def test_transcribe_segments_collects_warnings(tmp_path: Path) -> None:
    class Fake:
        model = "whisper-1"

        def transcribe(self, wav: Path):  # noqa: ANN202
            if wav.name == "bad.wav":
                raise ProduceError("boom")
            return [] if wav.name == "empty.wav" else [("a", 0.0, 1.0)]

    words, warns = transcribe_segments(
        Fake(), [("s1", Path("ok.wav")), ("s2", Path("bad.wav")), ("s3", Path("empty.wav"))]
    )
    assert list(words) == ["s1"]
    assert [w.split("[")[0] for w in warns] == ["stt_failed", "stt_empty"]
    json.dumps(words)


def test_auth_error_stops_stt_after_first_segment() -> None:
    from worker.produce.errors import ProduceAuthError

    class Denied:
        model = "whisper-1"
        calls = 0

        def transcribe(self, wav: Path):  # noqa: ANN202
            Denied.calls += 1
            raise ProduceAuthError("HTTP 401")

    stt = Denied()
    words, warns = transcribe_segments(stt, [(f"s{i}", Path(f"{i}.wav")) for i in range(4)])
    assert words == {} and Denied.calls == 1
    assert len(warns) == 1 and warns[0].startswith("stt_disabled_auth")


# ---------------------------------------------------------------- STT local (faster-whisper giả)


class _FakeWord:
    def __init__(self, word: str, start: float, end: float) -> None:
        self.word, self.start, self.end = word, start, end


class _FakeSeg:
    def __init__(self, words: list[_FakeWord]) -> None:
        self.words = words


class _FakeModel:
    def __init__(self) -> None:
        self.calls = 0

    def transcribe(self, path: str, **kw: object):
        self.calls += 1
        assert kw["language"] == "vi" and kw["word_timestamps"] is True
        return iter([_FakeSeg([_FakeWord(" Xử", 0.0, 0.2), _FakeWord(" lý", 0.2, 0.5)])]), None


def test_local_stt_parses_words_and_caches(tmp_path: Path) -> None:
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"RIFFxxxx")
    model = _FakeModel()
    stt = LocalWordStt("small", cache_dir=tmp_path / "c", _model=model)
    assert stt.model == "local:small"
    assert stt.transcribe(wav) == [("Xử", 0.0, 0.2), ("lý", 0.2, 0.5)]
    assert stt.transcribe(wav) == [("Xử", 0.0, 0.2), ("lý", 0.2, 0.5)]
    assert (model.calls, stt.calls, stt.cached) == (1, 1, 1)


def test_local_stt_missing_library_is_produce_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib

    def boom(name: str):
        raise ImportError(name)

    monkeypatch.setattr(importlib, "import_module", boom)
    wav = tmp_path / "a.wav"
    wav.write_bytes(b"x")
    with pytest.raises(ProduceError, match="stt-local"):
        LocalWordStt("small").transcribe(wav)


def test_make_stt_dispatch() -> None:
    assert isinstance(make_stt("local:small"), LocalWordStt)
    assert isinstance(make_stt("whisper-1", api_key="k"), OpenAIWordStt)
    with pytest.raises(ProduceError):
        make_stt("whisper-1")  # thiếu khoá
    with pytest.raises(ProduceError):
        make_stt("local:")


def test_local_stt_is_free() -> None:
    assert stt_cost_usd(60, "local:small") == 0.0
    assert stt_cost_usd(60) == 0.006
