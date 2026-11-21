"""Đo RAM đỉnh của cả cây tiến trình render (node + Chrome headless + ffmpeg) trên Windows.

HyperFrames sinh nhiều tiến trình Chrome, nên RAM của riêng tiến trình node là không đủ.
Một tiến trình PowerShell lấy mẫu mỗi 250 ms tổng WorkingSet của các tiến trình liên quan
SINH RA SAU mốc bắt đầu (bỏ qua Chrome/node đã chạy sẵn của phiên khác). Không cần psutil.
"""

from __future__ import annotations

import subprocess
import sys
import tempfile
import time
from pathlib import Path

_PS = r"""
$t0 = (Get-Date).AddSeconds(-1)
$peak = 0
while (-not (Test-Path '{flag}')) {{
  $p = Get-Process -Name chrome-headless-shell,chrome,node,ffmpeg -ErrorAction SilentlyContinue |
       Where-Object {{ $_.StartTime -gt $t0 }}
  $sum = ($p | Measure-Object WorkingSet64 -Sum).Sum
  if ($sum -gt $peak) {{ $peak = $sum }}
  Start-Sleep -Milliseconds 250
}}
[math]::Round($peak / 1MB)
"""


class PeakRam:
    """with PeakRam() as ram: ...; ram.peak_mb (None nếu không phải Windows)."""

    def __init__(self) -> None:
        self.peak_mb: int | None = None
        self._proc: subprocess.Popen[str] | None = None
        self._dir = Path(tempfile.mkdtemp(prefix="peakram-"))
        self._flag = self._dir / "done.flag"

    def __enter__(self) -> PeakRam:
        if sys.platform == "win32":
            script = self._dir / "sample.ps1"
            script.write_text(_PS.format(flag=self._flag), encoding="utf-8")
            self._proc = subprocess.Popen(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(script)],
                stdout=subprocess.PIPE, text=True,
            )  # fmt: skip
            time.sleep(1.0)  # đợi PowerShell khởi động xong mới bắt đầu lệnh cần đo
        return self

    def __exit__(self, *exc: object) -> None:
        if self._proc is None:
            return
        self._flag.touch()
        out, _ = self._proc.communicate(timeout=30)
        try:
            self.peak_mb = int(out.strip().splitlines()[-1])
        except (ValueError, IndexError):
            self.peak_mb = None
