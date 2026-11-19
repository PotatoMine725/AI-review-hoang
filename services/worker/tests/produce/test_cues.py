"""Chia phụ đề thành nhiều cue theo giới hạn dòng từng tỉ lệ (cues.py + phần ghép trong driver)."""

from __future__ import annotations

import dataclasses
import importlib.util
import json
import random
import sys
from collections.abc import Callable
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from pydantic import BaseModel

from tests.produce.support import RUN4_SCRIPT, load_spike_subtitles
from worker.produce import cues
from worker.produce.cues import Cue, split_caption, time_cues

DRIVER = Path(cues.__file__).parent / "drivers" / "hf_render.py"


def stub_wrap(text: str, max_chars: int) -> list[str]:
    """Xuống dòng tham lam theo từ, cùng ý với `wrap_caption` của #88 (từ dài đứng riêng)."""
    lines: list[str] = [""]
    for w in text.split():
        if lines[-1] and len(lines[-1]) + 1 + len(w) > max_chars:
            lines.append(w)
        else:
            lines[-1] = f"{lines[-1]} {w}".strip()
    return lines


def make_fits(max_chars: int, max_lines: int = 2) -> Callable[[str], bool]:
    return lambda text: len(stub_wrap(text, max_chars)) <= max_lines


CAPTION = (
    "Xử lý PDF miễn phí, riêng tư và mạnh mẽ ngay trong trình duyệt."  # 63 ký tự, như s01 của run4
)


# ---------------------------------------------------------------- split_caption


def test_caption_that_fits_stays_one_cue_unchanged() -> None:
    fits = make_fits(24)
    assert split_caption("Hợp nhất nhiều tệp PDF.", fits) == ["Hợp nhất nhiều tệp PDF."]
    assert split_caption(CAPTION, make_fits(50)) == [CAPTION]  # 16:9: 2 dòng × 50 ký tự là đủ


def test_empty_caption_has_no_cue() -> None:
    assert split_caption("   ", make_fits(24)) == []


def test_long_caption_splits_into_fewest_cues_each_within_limit() -> None:
    fits = make_fits(24)
    out = split_caption(CAPTION, fits)
    assert len(out) == 2  # 63 ký tự > 2 × 24 nhưng chia hai là đủ
    assert all(fits(c) for c in out)
    assert " ".join(out).split() == CAPTION.split()


def test_break_prefers_punctuation_over_a_slightly_better_balance() -> None:
    assert split_caption(CAPTION, make_fits(24)) == [
        "Xử lý PDF miễn phí,",
        "riêng tư và mạnh mẽ ngay trong trình duyệt.",
    ]


def test_without_punctuation_breaks_at_word_boundaries_and_balances() -> None:
    text = "Ghép nhiều tệp PDF thành một tài liệu duy nhất chỉ với vài thao tác đơn giản"
    out = split_caption(text, make_fits(24))
    assert " ".join(out).split() == text.split()
    assert max(len(c) for c in out) - min(len(c) for c in out) <= 12  # không có cue lẻ loi vài chữ


def test_word_longer_than_a_line_stands_alone_and_nothing_is_dropped() -> None:
    word = "x" * 30
    text = f"Truy cập {word} ngay hôm nay để dùng thử miễn phí hoàn toàn nhé bạn"
    out = split_caption(text, make_fits(12))
    assert " ".join(out).split() == text.split()
    assert any(word in c for c in out)
    assert all(make_fits(12)(c) or " " not in c for c in out)


def test_whitespace_is_normalised_but_words_are_untouched() -> None:
    assert split_caption("a  b\n c", make_fits(24)) == ["a b c"]


def test_random_captions_never_lose_a_word_and_every_cue_fits() -> None:
    rng = random.Random(7)
    alphabet = [
        "PDF",
        "tệp",
        "miễn",
        "phí,",
        "trình",
        "duyệt.",
        "và",
        "một",
        "ghép",
        "nhiều",
        "đơn",
    ]
    for max_chars in (14, 20, 24, 50):
        fits = make_fits(max_chars)
        for _ in range(80):
            words = [rng.choice(alphabet) for _ in range(rng.randint(1, 40))]
            text = " ".join(words)
            out = split_caption(text, fits)
            assert " ".join(out).split() == words
            assert all(fits(c) for c in out)
            if fits(text):
                assert len(out) == 1


# ---------------------------------------------------------------- time_cues


def test_cues_are_contiguous_and_cover_the_segment_exactly() -> None:
    out = time_cues(
        ["Xử lý PDF miễn phí,", "riêng tư và mạnh mẽ ngay trong trình duyệt."], 2.0, 6.7
    )
    assert out[0].start_s == 2.0 and out[-1].end_s == 6.7
    assert out[0].end_s == out[1].start_s  # không hở, không chồng
    # tỉ lệ số ký tự: cue dài hơn thì hiện lâu hơn
    assert (out[0].end_s - out[0].start_s) / (out[1].end_s - out[1].start_s) == pytest.approx(
        19 / 43
    )


def test_cue_boundaries_stay_distinct_after_ass_centisecond_rounding() -> None:
    rng = random.Random(3)
    for _ in range(200):
        start = round(rng.uniform(0, 30), 4)
        texts = [
            " ".join("ab" * rng.randint(1, 6) for _ in range(rng.randint(1, 5))) for _ in range(3)
        ]
        out = time_cues(texts, start, start + rng.uniform(2, 9))
        cs = [round(c.start_s * 100) for c in out] + [round(out[-1].end_s * 100)]
        assert cs == sorted(cs) and len(set(cs)) == len(cs)
        for a, b in zip(out, out[1:], strict=False):
            assert a.end_s == b.start_s


def test_single_cue_keeps_the_whole_span() -> None:
    assert time_cues(["abc"], 1.0, 3.0) == [Cue("abc", 1.0, 3.0)]
    assert time_cues([], 1.0, 3.0) == []


# ---------------------------------------------------------------- với giới hạn thật của #88


def test_run4_captions_fit_real_limits_of_both_ratios() -> None:
    sub = load_spike_subtitles()
    script = json.loads(RUN4_SCRIPT.read_text(encoding="utf-8"))
    captions = [
        s.get("subtitle_text") or g["text"]
        for s in script["scenes"]
        for g in s["narration_segments"]
    ]
    for ratio in ("9:16", "16:9"):

        def fits(text: str, ratio: str = ratio) -> bool:
            return len(sub.wrap_caption(sub._escape(text), sub.LINE_CHARS[ratio])) <= sub.MAX_LINES  # noqa: SLF001

        for cap in captions:
            out = split_caption(cap, fits)
            assert " ".join(out).split() == cap.split()
            assert all(fits(c) for c in out), (ratio, cap, out)
    s01 = captions[0]
    assert (
        len(split_caption(s01, lambda t: len(sub.wrap_caption(t, sub.LINE_CHARS["9:16"])) <= 2))
        == 2
    )
    assert split_caption(s01, lambda t: len(sub.wrap_caption(t, sub.LINE_CHARS["16:9"])) <= 2) == [
        s01
    ]


# ---------------------------------------------------------------- phần ghép trong driver


class Seg(BaseModel):
    segment_id: str
    text: str
    subtitle_text: str | None = None

    @property
    def caption(self) -> str:
        return self.subtitle_text or self.text


class Scene(BaseModel):
    scene_id: str
    narration_segments: list[Seg]


class Plan(BaseModel):
    scenes: list[Scene]


@dataclasses.dataclass(frozen=True)
class TSeg:
    segment_id: str
    start_s: float
    duration_s: float

    @property
    def end_s(self) -> float:
        return self.start_s + self.duration_s


@dataclasses.dataclass(frozen=True)
class TScene:
    scene_id: str
    segments: tuple[TSeg, ...]


@dataclasses.dataclass(frozen=True)
class TLine:
    scenes: tuple[TScene, ...]

    @property
    def segments(self) -> tuple[TSeg, ...]:
        return tuple(g for s in self.scenes for g in s.segments)


def load_driver() -> Any:
    spec = importlib.util.spec_from_file_location("hf_render_under_test", DRIVER)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["hf_render_under_test"] = mod
    spec.loader.exec_module(mod)
    return mod


def fake_subtitles(max_chars: int) -> Any:
    return SimpleNamespace(
        LINE_CHARS={"9:16": max_chars, "16:9": 50},
        MAX_LINES=2,
        wrap_caption=stub_wrap,
        _escape=lambda t: t,
    )


def test_driver_splits_long_captions_and_leaves_the_rest_alone() -> None:
    driver = load_driver()
    plan = Plan(
        scenes=[
            Scene(
                scene_id="s01",
                narration_segments=[Seg(segment_id="s01-u01", text="x", subtitle_text=CAPTION)],
            ),
            Scene(
                scene_id="s02", narration_segments=[Seg(segment_id="s02-u01", text="Ngắn thôi.")]
            ),
        ]
    )
    tl = TLine(
        scenes=(
            TScene("s01", (TSeg("s01-u01", 0.1, 4.0),)),
            TScene("s02", (TSeg("s02-u01", 4.22, 2.0),)),
        )
    )
    plan2, tl2, split = driver.split_subtitles(plan, tl, "9:16", fake_subtitles(24), cues)

    assert split == {"s01-u01": 2}
    segs = tl2.segments
    assert [g.segment_id for g in segs] == ["s01-u01#1", "s01-u01#2", "s02-u01"]
    assert segs[0].start_s == 0.1 and segs[0].end_s == segs[1].start_s
    assert segs[1].end_s == pytest.approx(4.1)  # cue cuối kết thúc đúng chỗ câu gốc kết thúc
    assert segs[2] == tl.segments[1]  # câu vừa giới hạn đi qua nguyên vẹn
    captions = [g.caption for s in plan2.scenes for g in s.narration_segments]
    assert " ".join(captions[:2]) == CAPTION
    assert captions[2] == "Ngắn thôi."
    # plan gốc không bị đổi
    assert plan.scenes[0].narration_segments[0].segment_id == "s01-u01"


def test_driver_16x9_limit_keeps_the_same_caption_in_one_cue() -> None:
    driver = load_driver()
    plan = Plan(
        scenes=[
            Scene(
                scene_id="s01",
                narration_segments=[Seg(segment_id="s01-u01", text="x", subtitle_text=CAPTION)],
            )
        ]
    )
    tl = TLine(scenes=(TScene("s01", (TSeg("s01-u01", 0.1, 4.0),)),))
    _, tl2, split = driver.split_subtitles(plan, tl, "16:9", fake_subtitles(24), cues)
    assert split == {} and [g.segment_id for g in tl2.segments] == ["s01-u01"]
