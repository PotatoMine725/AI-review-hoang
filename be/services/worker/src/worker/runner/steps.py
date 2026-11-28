"""Cổng (port) của các bước nặng và adapter mặc định cho crawl.

Runner chỉ biết các Protocol này nên test bằng fake, không cần trình duyệt hay LLM. Provider đổi
chỉ sửa adapter (ADR-0005).
"""

from __future__ import annotations

import asyncio
import json
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
from worker.produce.catalog import CatalogError, check_choice
from worker.produce.config import ProduceConfig
from worker.produce.pipeline import produce


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


@dataclass
class VideoRequest:
    script: dict[str, Any]  # script_revisions.content (đã duyệt)
    m2_input: dict[str, Any]  # input M2 dựng lại từ PKB đã duyệt + `report["input"]` của revision
    assets_path: Path  # assets.json (bảng asset_id → file, TẠM THỜI trên máy render)
    out_dir: Path
    mode: str = "preview"  # preview = `-q draft`, final = `-q looks`
    ratios: tuple[str, ...] = ("16:9", "9:16")
    template: str | None = None  # id trong templates.json; None = PRODUCE_TEMPLATE / mặc định
    voice: str | None = None  # giọng VieNeu; None = PRODUCE_VOICE


@dataclass
class VideoOutcome:
    manifest: dict[str, Any]  # vào generation_jobs.result_manifest
    warnings: list[str] = field(default_factory=list)


class VideoStep(Protocol):
    async def __call__(self, req: VideoRequest) -> VideoOutcome:
        """Dựng MP4 từ kịch bản đã duyệt. Không ra MP4 nào thì raise `StepError`."""
        ...


def video_manifest(report: dict[str, Any], report_path: Path) -> dict[str, Any]:
    """Phần `render_report.json` đủ để đọc kết quả mà không mở file (đường dẫn, độ dài, mốc)."""
    return {
        "status": report["status"],  # completed | out_of_range
        "mode": report["mode"],
        "ratios": report["ratios"],
        "target_s": report.get("target_s"),
        "actual_s": report.get("actual_s"),
        "outputs": [
            {
                k: o.get(k)
                for k in ("ratio", "ok", "mp4", "duration_s", "size", "duration_check", "error")
            }
            for o in report.get("outputs", [])
        ],
        "warnings": report.get("warnings", []),
        "timings_s": report.get("timings_s"),
        "report_path": str(report_path),
    }


class ProduceVideoStep:
    """Adapter mặc định: `worker.produce.produce` (P1-08/P1-09). TTS VieNeu và HyperFrames chạy
    cục bộ qua venv của spike (biến `PRODUCE_*`), nên runner này chỉ chạy trên máy render."""

    def __init__(self, cfg: ProduceConfig | None = None) -> None:
        self._cfg = cfg

    def _job_cfg(self, req: VideoRequest) -> ProduceConfig | None:
        """Cấu hình riêng của job: template/giọng FE chọn đè lên `PRODUCE_*` của máy render."""
        over = {k: v for k, v in (("template", req.template), ("voice", req.voice)) if v}
        if not over:
            return self._cfg
        base = self._cfg or ProduceConfig.from_env()
        try:
            check_choice(base, req.template, req.voice)
        except CatalogError as e:
            raise StepError(str(e)) from e
        return base.model_copy(update=over)

    async def __call__(self, req: VideoRequest) -> VideoOutcome:
        cfg = self._job_cfg(req)
        inputs = req.out_dir / "inputs"
        inputs.mkdir(parents=True, exist_ok=True)
        script_path, input_path = inputs / "script.json", inputs / "input.json"
        script_path.write_text(json.dumps(req.script, ensure_ascii=False), encoding="utf-8")
        input_path.write_text(json.dumps(req.m2_input, ensure_ascii=False), encoding="utf-8")
        res = await asyncio.to_thread(
            produce,
            script_path,
            input_path,
            req.assets_path,
            req.out_dir,
            mode=req.mode,
            ratios=req.ratios,
            cfg=cfg,
        )
        if not res.ok:
            err = res.report.get("error") or {}
            raise StepError(
                f"{err.get('code', 'produce_failed')}: {err.get('message', 'không dựng được MP4')}"
                f" (xem {res.report_path})"
            )
        return VideoOutcome(
            manifest=video_manifest(res.report, res.report_path),
            warnings=list(res.report.get("warnings", [])),
        )
