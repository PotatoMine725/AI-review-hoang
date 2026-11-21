"""QA khung hình bằng mô hình thị giác: adapter OpenAI (httpx giả) và đọc kết quả."""

from __future__ import annotations

import json

import httpx
import pytest

from worker.produce.errors import ProduceError
from worker.produce.qa import FrameJob, OpenAIVisionQA, frame_jobs, verdict_from
from worker.produce.timeline import build_timeline

JOB = FrameJob("9:16", "s01", 3.0, "Lời đọc.", "Phụ đề.")


def _qa(handler, **kw) -> OpenAIVisionQA:  # noqa: ANN001, ANN003
    client = httpx.Client(transport=httpx.MockTransport(handler))
    return OpenAIVisionQA("k", "gpt-5.4-mini", client=client, retry_delays_s=(0.0,), **kw)


def _ok(content: dict | str) -> httpx.Response:
    text = content if isinstance(content, str) else json.dumps(content)
    return httpx.Response(
        200,
        json={
            "choices": [{"message": {"content": text}}],
            "usage": {"prompt_tokens": 100, "completion_tokens": 20},
        },
    )


def test_review_sends_image_and_texts_and_counts_tokens() -> None:
    seen: list[dict] = []

    def handler(req: httpx.Request) -> httpx.Response:
        seen.append(json.loads(req.content))
        assert req.headers["authorization"] == "Bearer k"
        return _ok({"readable": True})

    qa = _qa(handler)
    assert qa.review(b"\xff\xd8abc", JOB) == {"readable": True}
    body = seen[0]
    user = body["messages"][1]["content"]
    assert body["model"] == "gpt-5.4-mini" and body["response_format"] == {"type": "json_object"}
    assert "Lời đọc." in user[0]["text"] and "Phụ đề." in user[0]["text"]
    assert user[0]["text"].startswith("Phụ đề đang hiện: Phụ đề.")  # câu đang đọc đứng trước
    assert user[1]["image_url"]["url"].startswith("data:image/jpeg;base64,")
    assert "9:16" in body["messages"][0]["content"]
    assert (qa.tokens_in, qa.tokens_out, qa.calls) == (100, 20, 1)


def test_retries_503_but_not_401_and_rejects_non_json() -> None:
    codes = iter([503, 200])

    def flaky(req: httpx.Request) -> httpx.Response:
        return _ok({"readable": True}) if next(codes) == 200 else httpx.Response(503)

    assert _qa(flaky).review(b"x", JOB) == {"readable": True}
    with pytest.raises(ProduceError, match="401"):
        _qa(lambda r: httpx.Response(401, text="no")).review(b"x", JOB)
    with pytest.raises(ProduceError, match="JSON"):
        _qa(lambda r: _ok("không phải json")).review(b"x", JOB)


def test_missing_checks_count_as_failed() -> None:
    v = verdict_from(JOB, {"readable": True, "not_cut_off": True, "issues": ["a", " "]})
    assert not v.ok and v.issues == ["a"]
    assert not v.checks["matches_narration"]
    full = dict.fromkeys(("readable", "not_cut_off", "title_distinct_from_subtitle"), True)
    assert verdict_from(JOB, {**full, "matches_narration": True}).ok


def test_frame_jobs_pick_caption_playing_at_frame_time() -> None:
    tl = build_timeline(
        [("s01", [("s01-u01", 2.0), ("s01-u02", 4.0)])], fps=30, lead_s=0.1, gap_s=0.12, tail_s=0.6
    )
    jobs = frame_jobs("16:9", tl, [("s01", [("s01-u01", "một"), ("s01-u02", "hai")])])
    assert len(jobs) == 1 and jobs[0].narration == "một hai"
    assert jobs[0].caption == "hai"  # 0,6 × thời lượng cảnh rơi vào câu thứ hai
    assert 0 < jobs[0].t_s < tl.total_s
