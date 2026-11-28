"""Adapter Gemini cho bước sinh script thao tác (thay OpenAI, khoá OpenAI không còn dùng được)."""

from __future__ import annotations

from typing import Any

import pytest

from worker.demo.errors import DemoError
from worker.demo.llm import GeminiScriptLLM, is_gemini
from worker.m1.llm.client import RawResponse
from worker.m1.llm.errors import ProviderError


class FakeTransport:
    def __init__(self, outcomes: list[Any]) -> None:
        self.outcomes = outcomes
        self.calls: list[dict[str, Any]] = []

    async def generate(self, **kw: Any) -> RawResponse:
        self.calls.append(kw)
        out = self.outcomes.pop(0)
        if isinstance(out, Exception):
            raise out
        return out


def raw(text: str) -> RawResponse:
    return RawResponse(
        text=text, tokens_in=10, tokens_out=5, thoughts_tokens=0, finish_reason="STOP"
    )


def test_is_gemini() -> None:
    assert is_gemini("gemini-3.5-flash-lite") and is_gemini(" Gemini-x")
    assert not is_gemini("gpt-5.4-mini")


def test_gemini_returns_text_and_counts_tokens() -> None:
    t = FakeTransport([raw('{"steps": []}')])
    llm = GeminiScriptLLM("k", "gemini-x", transport=t, retry_delays_s=())
    assert llm.complete("sys", "user") == '{"steps": []}'
    assert llm.name == "gemini:gemini-x" and (llm.tokens_in, llm.tokens_out) == (10, 5)
    assert t.calls[0]["system"] == "sys" and t.calls[0]["response_schema"] is None


def test_gemini_retries_rate_limit_then_succeeds() -> None:
    t = FakeTransport([ProviderError(429, "quota"), raw("{}")])
    llm = GeminiScriptLLM("k", "gemini-x", transport=t, retry_delays_s=(0.0,))
    assert llm.complete("s", "u") == "{}"
    assert len(t.calls) == 2


def test_gemini_does_not_retry_bad_request() -> None:
    t = FakeTransport([ProviderError(400, "bad")])
    llm = GeminiScriptLLM("k", "gemini-x", transport=t, retry_delays_s=(0.0, 0.0))
    with pytest.raises(DemoError, match="từ chối"):
        llm.complete("s", "u")
    assert len(t.calls) == 1


def test_gemini_empty_text_is_error() -> None:
    llm = GeminiScriptLLM("k", "gemini-x", transport=FakeTransport([raw("  ")]), retry_delays_s=())
    with pytest.raises(DemoError, match="rỗng"):
        llm.complete("s", "u")
