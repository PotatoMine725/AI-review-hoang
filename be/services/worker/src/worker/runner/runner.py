"""Nhận và chạy job `crawl` và `video`.

- `crawl`: claim → crawl → (extract) → tạo PKB `draft` → `completed`/`failed`.
- `video`: claim → nạp script revision `approved` + PKB `approved` (đúng `script_revision` và
  `pkb_version` của job) → kiểm lại bằng validator M2 → TTS + render MP4 (`worker.produce`) →
  `completed`/`failed`. Chạy trên máy render (cần VieNeu/HyperFrames cục bộ), bật bằng
  `--types video`.

Quy ước:
- **Claim không cần migration mới**: `UPDATE ... WHERE id = X AND status = 'queued'` là nguyên tử
  trong Postgres; chỉ runner nhận lại được dòng thì thắng. Hai runner song song không chạy trùng.
- Lỗi `retryable` và còn lượt (`attempts < max_attempts`) thì xếp lại `queued` (DB cho phép
  `running → queued`), chờ lũy thừa 2 trong bộ nhớ trước khi nhận lại. Hết lượt hoặc không retry
  được thì `failed` kèm `error` (bắt buộc theo DB).
- PKB được tạo xong thì ghi `pkb_version` vào job ngay (còn `running`); nếu runner chết giữa
  chừng, lượt sau thấy `pkb_version` đã có và chỉ hoàn tất job, không tạo PKB thứ hai.
- Chưa làm: job kẹt ở `running` khi runner chết (bảng chưa có `updated_at` để tự dọn); cần xếp lại
  bằng tay hoặc thêm cột ở migration sau.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from worker.api.db import Database, Row
from worker.api.errors import DatabaseError
from worker.api.m2_input import build_m2_input
from worker.m1.models import CrawlResult
from worker.runner.steps import (
    CrawlStep,
    ExtractOutcome,
    ExtractStep,
    StepError,
    VideoRequest,
    VideoStep,
)
from worker.settings import Settings

log = logging.getLogger("worker.runner")

CLAIM_COLUMNS = "id,product_id,attempts,pkb_version,script_revision,input_snapshot"
VIDEO_RATIOS = ("16:9", "9:16")
VIDEO_MODES = ("preview", "final")
ERROR_LIMIT = 2000  # khớp check của generation_jobs.error


def _clip(text: str) -> str:
    return text if len(text) <= ERROR_LIMIT else text[: ERROR_LIMIT - 1] + "…"


def build_manifest(
    crawl: CrawlResult, out_dir: Path, extract: ExtractOutcome | None
) -> dict[str, Any]:
    """`result_manifest` của job crawl: đủ để kiểm ≤ 30 trang, mỗi trang có hash."""
    return {
        "root_url": crawl.root_url,
        "partial": crawl.partial,
        "warning": crawl.warning,
        "pages_found": crawl.pages_found,
        "pages_used": crawl.pages_used,
        "crawl_seconds": crawl.crawl_seconds,
        "skipped_counts": crawl.skipped_counts,
        "store_dir": str(out_dir),
        "pages": [
            {
                "source_id": p.source_id,
                "url": p.url,
                "page_type": p.page_type,
                "content_hash": p.content_hash,
                "fit_path": p.fit_path,
                "raw_path": p.raw_path,
            }
            for p in crawl.pages
        ],
        "extract": (
            {"status": "skipped"}
            if extract is None
            else {"status": "completed", "warnings": extract.warnings}
        ),
    }


class JobRunner:
    def __init__(
        self,
        db: Database,
        settings: Settings,
        crawl: CrawlStep | None,
        extract: ExtractStep | None = None,
        *,
        video: VideoStep | None = None,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._db = db
        self._settings = settings
        self._crawl = crawl
        self._extract = extract
        self._video = video
        self._types = [t for t, step in (("crawl", crawl), ("video", video)) if step is not None]
        self._clock = clock
        self._not_before: dict[str, float] = {}  # job_id -> mốc được nhận lại (retry)

    # --- hàng đợi -----------------------------------------------------------------------------
    def _candidates(self, job_type: str) -> list[Row]:
        return self._db.select(
            "generation_jobs",
            {
                "status": "eq.queued",
                "job_type": f"eq.{job_type}",
                "order": "created_at.asc",
                "limit": "10",
                "select": CLAIM_COLUMNS,
            },
        )

    def claim_next(self, job_type: str = "crawl") -> Row | None:
        """Nhận job queued cũ nhất chưa chờ backoff. None nếu không có hoặc thua tranh claim."""
        now = self._clock()
        for row in self._candidates(job_type):
            if self._not_before.get(str(row["id"]), 0.0) > now:
                continue
            claimed = self._db.update(
                "generation_jobs",
                {"id": f"eq.{row['id']}", "status": "eq.queued"},
                {"status": "running", "attempts": int(row.get("attempts") or 0) + 1, "error": None},
            )
            if claimed:  # PostgREST trả dòng đã đổi; rỗng = runner khác đã nhận trước
                return {**row, **claimed[0]}
        return None

    # --- chạy một job -------------------------------------------------------------------------
    async def run_once(self) -> bool:
        """Nhận và chạy tối đa một job. Trả True nếu có job được xử lý."""
        job = next((j for t in self._types if (j := self.claim_next(t)) is not None), None)
        if job is None:
            return False
        job_id = str(job["id"])
        try:
            if job.get("job_type") == "video" or (
                job.get("job_type") is None and job.get("script_revision") is not None
            ):
                await self._run_video_job(job)
            else:
                await self._run_crawl_job(job)
        except StepError as e:
            self._fail(job, e.message, retryable=e.retryable, cost=e.cost_breakdown)
        except DatabaseError as e:
            # DB lỗi: không đoán trạng thái, để job `running` và báo log (xem "Chưa làm").
            log.error("job %s: lỗi DB khi xử lý: %s", job_id, e)
        except Exception as e:  # noqa: BLE001 - mọi lỗi lạ phải kết thúc job, không giết vòng lặp
            log.exception("job %s: lỗi không lường trước", job_id)
            self._fail(job, f"lỗi nội bộ: {type(e).__name__}: {e}", retryable=False)
        return True

    async def _run_crawl_job(self, job: Row) -> None:
        job_id, product_id = str(job["id"]), str(job["product_id"])
        url = (job.get("input_snapshot") or {}).get("website_url")
        if not isinstance(url, str) or not url:
            raise StepError("input_snapshot thiếu website_url")

        if self._crawl is None:  # chỉ khi `claim_next("crawl")` bị gọi tay khi chưa cấu hình crawl
            raise StepError("runner chưa cấu hình bước crawl")
        out_dir = Path(self._settings.page_store_dir) / job_id
        crawl = await self._crawl(url, out_dir)
        if crawl.status == "failed":
            raise StepError(
                f"{crawl.error_code}: {crawl.error_message}"
                if crawl.error_code
                else crawl.error_message,
                retryable=bool(crawl.retryable),
            )

        extract: ExtractOutcome | None = None
        pkb_version = job.get("pkb_version")
        if pkb_version is None and self._extract is not None:
            extract = await self._extract(crawl, out_dir)
            pkb_version = self._db.rpc(
                "create_pkb_version",
                {"p_product_id": product_id, "p_data": extract.data, "p_sources": extract.sources},
            )
            # Ghi ngay để lượt sau (nếu runner chết) không tạo PKB thứ hai.
            self._db.update("generation_jobs", {"id": f"eq.{job_id}"}, {"pkb_version": pkb_version})

        patch: dict[str, Any] = {
            "status": "completed",
            "error": None,
            "result_manifest": build_manifest(crawl, out_dir, extract),
        }
        if extract is not None:
            patch["cost_breakdown"] = extract.cost_breakdown
        self._db.update("generation_jobs", {"id": f"eq.{job_id}"}, patch)
        self._not_before.pop(job_id, None)
        log.info(
            "job %s: completed (pages=%s, pkb_version=%s)", job_id, crawl.pages_used, pkb_version
        )

    # --- job video ----------------------------------------------------------------------------
    def _one(self, table: str, filters: dict[str, str], what: str) -> Row:
        rows = self._db.select(table, filters)
        if not rows:
            raise StepError(f"không tìm thấy {what}")
        return rows[0]

    async def _run_video_job(self, job: Row) -> None:
        if self._video is None:
            raise StepError("runner chưa cấu hình bước video")
        job_id, product_id = str(job["id"]), str(job["product_id"])
        revision, pkb_version = job.get("script_revision"), job.get("pkb_version")
        if not isinstance(revision, int) or not isinstance(pkb_version, int):
            raise StepError("job video thiếu script_revision hoặc pkb_version")
        options = (job.get("input_snapshot") or {}).get("options") or {}

        assets = options.get("assets_path")
        if not isinstance(assets, str) or not assets:
            raise StepError("input_snapshot.options thiếu assets_path (đường dẫn assets.json)")
        assets_path = Path(assets).absolute()  # render chạy ở thư mục khác (cwd của spike)
        if not assets_path.is_file():
            raise StepError(f"assets.json không có trên máy render: {assets_path}")
        mode = options.get("mode", "preview")
        if mode not in VIDEO_MODES:
            raise StepError(f"options.mode phải là một trong {VIDEO_MODES}, nhận {mode!r}")
        ratios = options.get("ratios", list(VIDEO_RATIOS))
        if (
            not isinstance(ratios, list)
            or not ratios
            or any(r not in VIDEO_RATIOS for r in ratios)
            or len(set(ratios)) != len(ratios)
        ):
            raise StepError(f"options.ratios phải là tập con không trùng của {VIDEO_RATIOS}")

        script = self._one(
            "script_revisions",
            {"product_id": f"eq.{product_id}", "revision": f"eq.{revision}"},
            f"script revision {revision}",
        )
        if script["status"] != "approved":
            raise StepError(f"script revision {revision} chưa được duyệt ({script['status']})")
        if script["knowledge_version"] != pkb_version:
            raise StepError(
                f"script revision {revision} sinh từ PKB v{script['knowledge_version']}, "
                f"job đòi PKB v{pkb_version}"
            )
        pkb = self._one(
            "product_knowledge",
            {"product_id": f"eq.{product_id}", "version": f"eq.{pkb_version}"},
            f"PKB version {pkb_version}",
        )
        if pkb["status"] != "approved":
            raise StepError(f"PKB version {pkb_version} chưa được duyệt ({pkb['status']})")
        context = (script.get("report") or {}).get("input")
        if not isinstance(context, dict) or not isinstance(context.get("permitted_assets"), list):
            raise StepError(
                f"script revision {revision} không lưu input.permitted_assets "
                "(sinh trước khi lưu input): sinh lại revision rồi duyệt"
            )
        m2_input = build_m2_input(
            product_id,
            pkb_version,
            pkb,
            context["permitted_assets"],
            context.get("content_context"),
        )

        # Tuyệt đối: bước render chạy tiến trình con với cwd là thư mục spike, đường dẫn tương đối
        # (mặc định `./data/videos`) sẽ trỏ sai chỗ.
        out_dir = (Path(self._settings.video_store_dir) / job_id).absolute()
        outcome = await self._video(
            VideoRequest(
                script=script["content"],
                m2_input=m2_input,
                assets_path=assets_path,
                out_dir=out_dir,
                mode=mode,
                ratios=tuple(ratios),
            )
        )
        self._db.update(
            "generation_jobs",
            {"id": f"eq.{job_id}"},
            {"status": "completed", "error": None, "result_manifest": outcome.manifest},
        )
        self._not_before.pop(job_id, None)
        log.info("job %s: video %s (%s)", job_id, outcome.manifest.get("status"), out_dir)

    def _fail(
        self, job: Row, message: str, *, retryable: bool, cost: dict[str, Any] | None = None
    ) -> None:
        job_id, attempts = str(job["id"]), int(job.get("attempts") or 0)
        message = _clip(message)
        if retryable and attempts < self._settings.runner_max_attempts:
            delay = self._settings.runner_retry_backoff_s * (2 ** (attempts - 1))
            self._not_before[job_id] = self._clock() + delay
            self._db.update(
                "generation_jobs", {"id": f"eq.{job_id}"}, {"status": "queued", "error": message}
            )
            log.warning("job %s: lỗi tạm thời, xếp lại sau %.0fs: %s", job_id, delay, message)
            return
        patch: dict[str, Any] = {"status": "failed", "error": message or "lỗi không rõ"}
        if cost:
            patch["cost_breakdown"] = cost
        self._db.update("generation_jobs", {"id": f"eq.{job_id}"}, patch)
        self._not_before.pop(job_id, None)
        log.error("job %s: failed: %s", job_id, message)
