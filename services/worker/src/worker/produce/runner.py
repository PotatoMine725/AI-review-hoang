"""Chạy tiến trình con. Tách thành `Runner` để test thay bằng bản giả (không cần venv/GPU/mạng)."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
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


CANCELLED_RC = -9  # mã trả về khi lệnh bị huỷ (xem `cancel` bên dưới)
POLL_S = 0.25


class Runner(Protocol):
    """`cancel` (tuỳ chọn): đặt cờ này thì tiến trình đang chạy bị giết cả cây và trả
    `RunResult(CANCELLED_RC, ...)`. Runner giả trong test có thể bỏ qua."""

    def __call__(
        self,
        cmd: Sequence[str],
        *,
        cwd: Path | None = None,
        env: Mapping[str, str] | None = None,
        timeout_s: float = 1800,
        cancel: threading.Event | None = None,
    ) -> RunResult: ...


def kill_tree(proc: subprocess.Popen[str]) -> None:
    """Giết tiến trình và MỌI tiến trình con (node → chrome-headless-shell).

    `Popen.kill()` chỉ giết tiến trình trực tiếp: trên Windows, Chrome của HyperFrames sẽ mồ côi."""
    if proc.poll() is not None:
        return
    if sys.platform == "win32":
        subprocess.run(
            ["taskkill", "/PID", str(proc.pid), "/T", "/F"],
            capture_output=True,
            check=False,
        )
    else:
        try:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
        except (ProcessLookupError, PermissionError):
            proc.kill()


def run_process(
    cmd: Sequence[str],
    *,
    cwd: Path | None = None,
    env: Mapping[str, str] | None = None,
    timeout_s: float = 1800,
    cancel: threading.Event | None = None,
) -> RunResult:
    t0 = time.perf_counter()
    proc = subprocess.Popen(
        list(cmd),
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        env={**os.environ, **(env or {})},
        start_new_session=sys.platform != "win32",
    )
    while True:
        try:
            out, err = proc.communicate(timeout=POLL_S)
            return RunResult(proc.returncode, out, err, time.perf_counter() - t0)
        except subprocess.TimeoutExpired:
            if cancel is not None and cancel.is_set():
                kill_tree(proc)
                out, err = proc.communicate()
                return RunResult(CANCELLED_RC, out, err or "huỷ", time.perf_counter() - t0)
            if time.perf_counter() - t0 > timeout_s:
                kill_tree(proc)
                proc.communicate()
                raise subprocess.TimeoutExpired(list(cmd), timeout_s) from None


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
