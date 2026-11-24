"""TTS theo segment_id: khoá cache, nạp model một lần, cache miss khi đổi giọng/lời."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.produce.support import FakeRunner, make_cfg
from worker.produce.errors import ProduceError
from worker.produce.tts import cache_key, synthesize

SEGS = [("s01-u01", "Xin Chào"), ("s02-u01", "Tạm Biệt")]


def test_cache_key_changes_with_every_part() -> None:
    base = ("m", "onnx", "Mai Anh", "p1", "xin chào")
    k = cache_key(*base)
    assert cache_key(*base) == k
    for i, other in enumerate(["m2", "pytorch", "Giọng khác", "p2", "lời khác"]):
        changed = list(base)
        changed[i] = other
        assert cache_key(*changed) != k, base[i]


def test_cache_key_depends_on_max_chars_but_zero_keeps_old_key() -> None:
    base = ("m", "onnx", "Hải Đăng", "p1", "xin chào")
    assert cache_key(*base, 0) == cache_key(*base)
    assert cache_key(*base, 60) != cache_key(*base)


def test_first_run_synthesizes_once_with_one_model_load(tmp_path: Path) -> None:
    cfg, fake = make_cfg(tmp_path), FakeRunner(speak_s=2.0)
    run = synthesize(SEGS, cfg, fake, tmp_path / "w")
    assert fake.modes() == ["normalize", "synth"]  # model nạp 1 lần cho cả video
    assert (run.hits, run.misses, run.load_s) == (0, 2, 6.5)
    assert run.durations() == {"s01-u01": pytest.approx(2.0), "s02-u01": pytest.approx(2.0)}
    first = run.segments[0]
    assert (first.text, first.spoken, first.cached) == ("Xin Chào", "xin chào", False)
    assert first.wav.parent == cfg.cache_dir and first.wav.is_file()


def test_second_run_is_all_cache_hits_without_loading_model(tmp_path: Path) -> None:
    cfg = make_cfg(tmp_path)
    synthesize(SEGS, cfg, FakeRunner(), tmp_path / "w")
    fake = FakeRunner()
    run = synthesize(SEGS, cfg, fake, tmp_path / "w")
    assert fake.modes() == ["normalize"]  # không gọi synth → không nạp model
    assert (run.hits, run.misses, run.load_s) == (2, 0, None)
    assert all(s.cached and s.synth_s is None for s in run.segments)


def test_changing_voice_or_text_is_a_miss(tmp_path: Path) -> None:
    cfg = make_cfg(tmp_path)
    synthesize(SEGS, cfg, FakeRunner(), tmp_path / "w")

    other_voice = make_cfg(tmp_path, voice="Giọng khác")
    fake = FakeRunner()
    assert synthesize(SEGS, other_voice, fake, tmp_path / "w").misses == 2

    fake = FakeRunner()
    run = synthesize([SEGS[0], ("s02-u01", "Lời mới")], cfg, fake, tmp_path / "w")
    assert (run.hits, run.misses) == (1, 1)
    assert fake.modes() == ["normalize", "synth"]


def test_device_is_part_of_the_cache_key(tmp_path: Path) -> None:
    synthesize(SEGS, make_cfg(tmp_path), FakeRunner(), tmp_path / "w")
    cuda = make_cfg(tmp_path, tts_device="cuda")
    assert synthesize(SEGS, cuda, FakeRunner(), tmp_path / "w").misses == 2


def test_duplicate_spoken_text_is_synthesized_once(tmp_path: Path) -> None:
    fake = FakeRunner()
    run = synthesize(
        [("s01-u01", "Giống nhau"), ("s02-u01", "giống nhau")],
        make_cfg(tmp_path),
        fake,
        tmp_path / "w",
    )
    assert run.misses == 1
    assert run.segments[0].wav == run.segments[1].wav


def test_missing_venv_is_a_clear_error(tmp_path: Path) -> None:
    cfg = make_cfg(tmp_path / "a").model_copy(update={"tts_spike": tmp_path / "nowhere"})
    with pytest.raises(ProduceError, match="venv của spike TTS"):
        synthesize(SEGS, cfg, FakeRunner(), tmp_path / "w")
