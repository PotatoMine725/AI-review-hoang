"""Lớp gọi LLM của M1. Code nghiệp vụ chỉ dùng `make_llm` và `LLM`, không import SDK provider."""

from __future__ import annotations

from worker.m1.llm.client import LLM, LLMResult, RawResponse, Transport
from worker.m1.llm.config import LLMSettings
from worker.m1.llm.cost import CostBreakdown, CostItem
from worker.m1.llm.errors import LLMError, LLMErrorCode, ProviderError

__all__ = [
    "LLM",
    "CostBreakdown",
    "CostItem",
    "LLMError",
    "LLMErrorCode",
    "LLMResult",
    "LLMSettings",
    "ProviderError",
    "RawResponse",
    "Transport",
    "make_llm",
]


def make_llm(settings: LLMSettings | None = None) -> LLM:
    """Chọn transport theo `LLM_PROVIDER`. Import gemini muộn để chế độ fixture không cần SDK."""
    settings = settings or LLMSettings.from_env()
    if settings.provider == "fixture":
        from worker.m1.llm.fixture import FixtureTransport

        if not settings.fixture_path:
            raise ValueError("LLM_PROVIDER=fixture cần LLM_FIXTURE_PATH")
        return LLM(FixtureTransport.from_file(settings.fixture_path), settings)
    from worker.m1.llm.gemini import GeminiTransport

    return LLM(GeminiTransport(settings.api_key, settings.timeout_s), settings)
