"""Chạy bộ nhận job: `uv run python -m worker.runner` (tiến trình riêng, tách khỏi API).

Cần `.env`: SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY (và SUPABASE_ANON_KEY cho client DB dùng chung).
`--once`: xử lý mọi job đang chờ rồi thoát (dùng khi chạy tay/cron).
`--types crawl,video`: loại job nhận (mặc định `crawl`). `video` chỉ chạy trên máy render (VieNeu,
HyperFrames, FFmpeg cục bộ, biến `PRODUCE_*`).
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import os
import sys
from pathlib import Path

from worker.api.db import PostgrestDatabase
from worker.m1.extract.__main__ import load_env
from worker.runner.runner import JobRunner
from worker.runner.steps import Crawl4AICrawlStep, GeminiExtractStep, ProduceVideoStep
from worker.settings import MissingConfigError, Settings


async def _loop(runner: JobRunner, interval_s: float, once: bool) -> None:
    while True:
        if await runner.run_once():
            continue  # còn việc thì nhận tiếp ngay
        if once:
            return
        await asyncio.sleep(interval_s)


def main() -> int:
    parser = argparse.ArgumentParser(prog="python -m worker.runner", description=__doc__)
    parser.add_argument("--once", action="store_true", help="Hết job thì thoát")
    parser.add_argument(
        "--types", default="crawl", help="Loại job nhận, cách nhau dấu phẩy: crawl, video"
    )
    args = parser.parse_args()
    types = {t.strip() for t in args.types.split(",") if t.strip()}
    if not types or not types <= {"crawl", "video"}:
        parser.error("--types chỉ nhận crawl và/hoặc video")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")

    load_env(Path(".env"))
    settings = Settings.from_env()
    try:
        settings.require("api", "runner")
        if "crawl" in types and os.environ.get("LLM_PROVIDER", "gemini") != "fixture":
            settings.require("extract")
    except MissingConfigError as e:
        print(e, file=sys.stderr)
        return 2
    runner = JobRunner(
        PostgrestDatabase(settings),
        settings,
        Crawl4AICrawlStep() if "crawl" in types else None,
        GeminiExtractStep() if "crawl" in types else None,
        video=ProduceVideoStep() if "video" in types else None,
    )
    try:
        asyncio.run(_loop(runner, settings.runner_poll_interval_s, args.once))
    except KeyboardInterrupt:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
