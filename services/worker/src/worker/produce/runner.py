"""Chạy tiến trình con. Tách thành `Runner` để test thay bằng bản giả (không cần venv/GPU/mạng)."""

from __future__ import annotations

import json
import os
import subprocess
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from worker.produce.errors import ProduceError


@dataclass(frozen=True)
class RunResult:
    returncode: int
    stdout: str
    stderr: str
    wall_s: float


class Runner(Protocol):
    def __call__(
        self,
        cmd: Sequence[str],
        *,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        timeout_s: float = 1800,
    ) -> RunResult: ...


def run_process(
    cmd: Sequence[str],
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    timeout_s: float = 1800,
) -> RunResult:
    t0 = time.perf_counter()
    p = subprocess.run(
        list(cmd),
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_s,
        env={**os.environ, **(env or {})},
    )
    return RunResult(p.returncode, p.stdout, p.stderr, time.perf_counter() - t0)


def last_json_line(text: str) -> dict[str, Any]:
    """Driver in kết quả ở dòng JSON cuối cùng của stdout (các dòng trước là log của thư viện)."""
    for line in reversed(text.strip().splitlines()):
        if line.startswith("{"):
            return json.loads(line)
    raise ProduceError("tiến trình con không in dòng JSON: " + text[-400:])


def require_ok(res: RunResult, what: str) -> RunResult:
    if res.returncode != 0:
        tail = (res.stderr or res.stdout)[-800:]
        raise ProduceError(f"{what} lỗi (mã {res.returncode}): {tail}")
    return res
