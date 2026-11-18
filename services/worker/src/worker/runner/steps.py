"""Cổng (port) của các bước nặng và adapter mặc định cho crawl.

Runner chỉ biết các Protocol này nên test bằng fake, không cần trình duyệt hay LLM. Provider đổi
chỉ sửa adapter (ADR-0005).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

from worker.m1.config import CrawlOptions, CrawlSettings
from worker.m1.crawl.fetcher import Crawl4AIFetcher
from worker.m1.crawl.service import crawl_product
from worker.m1.crawl.store import LocalPageStore
from worker.m1.extract.service import ExtractError, extract_product
from worker.m1.llm import make_llm
from worker.m1.models import CrawlResult


class StepError(Exception):
    """Lỗi của một bước. `retryable` quyết định runner xếp lại hàng hay đánh `failed`."""

    def __init__(
        self, message: str, *, retryable: bool = False, cost_breakdown: dict[str, Any] | None = None
    ) -> None:
        super().__init__(message)
        self.message = message
        self.retryable = retryable
        self.cost_breakdown = cost_breakdown or {}


@dataclass
class ExtractOutcome:
    data: dict[str, Any]  # product_knowledge.data (PKB v0.3)
    sources: list[dict[str, Any]]  # product_knowledge.sources
    cost_breakdown: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)


class CrawlStep(Protocol):
    async def __call__(self, url: str, out_dir: Path) -> CrawlResult:
        """Crawl `url`, ghi markdown vào `out_dir`. Lỗi crawl nằm trong `CrawlResult`."""
        ...


class ExtractStep(Protocol):
    async def __call__(self, crawl: CrawlResult, out_dir: Path) -> ExtractOutcome:
        """Dựng PKB v0.3 từ kết quả crawl. Lỗi thì raise `StepError`."""
        ...


class Crawl4AICrawlStep:
    """Adapter mặc định: `crawl_product` của M1 với Crawl4AI. Cần `playwright install chromium`."""

    def __init__(self, settings: CrawlSettings | None = None) -> None:
        self._settings = settings or CrawlSettings.from_env()

    async def __call__(self, url: str, out_dir: Path) -> CrawlResult:
        async with Crawl4AIFetcher(self._settings) as fetcher:
            return await crawl_product(
                url,
                CrawlOptions(),
                fetcher,
                LocalPageStore(out_dir),
                settings=self._settings,
            )


class GeminiExtractStep:
    """Adapter mặc định: `extract_product` của M1 (1 lời gọi LLM), provider theo `LLM_PROVIDER`."""

    async def __call__(self, crawl: CrawlResult, out_dir: Path) -> ExtractOutcome:
        try:
            llm = make_llm()
        except ValueError as e:  # cấu hình LLM sai (vd. fixture thiếu đường dẫn): không retry
            raise StepError(f"cấu hình LLM không hợp lệ: {e}") from e
        try:
            res = await extract_product(crawl, LocalPageStore(out_dir), llm)
        except ExtractError as e:
            raise StepError(
                e.message, retryable=e.retryable, cost_breakdown=e.cost_breakdown
            ) from e
        return ExtractOutcome(
            data=res.data,
            sources=res.sources,
            cost_breakdown=res.cost_breakdown,
            warnings=res.warnings,
        )
