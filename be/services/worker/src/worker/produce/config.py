"""Cấu hình đường ghép (một chỗ duy nhất). Đè bằng biến môi trường `PRODUCE_<TÊN_HOA>`.

Đường dẫn spike #73/#88/#77 chưa nằm trong nhánh này nên mặc định trỏ tới worktree anh em
(`.claude/worktrees/<tên>/spikes/<tên>`), giống `spikes/p1-pipeline-bench`. Tên cũ của bench
(`P1_TTS_VI`, `P1_RENDER_V2`, `P1_RENDER`) vẫn được nhận.
Mốc thời lượng đọc qua `config.py` của #77 (cùng cơ chế với renderer), nhưng mặc định của worker là
30–40 s (`DEFAULT_*_TOTAL_S`); đè bằng `P1_RENDER_MIN_TOTAL_S` / `P1_RENDER_MAX_TOTAL_S`.
"""

from __future__ import annotations

import importlib.util
import os
import shlex
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator

from worker.produce.errors import ProduceError

ENV_PREFIX = "PRODUCE_"
DEFAULT_MIN_TOTAL_S = 30.0  # mục tiêu video 30–40 s (spike #77 mặc định 40–45 s đã cũ)
DEFAULT_MAX_TOTAL_S = 40.0
MAX_GAP_S = 0.15  # tiêu chí khoảng nghỉ giữa hai câu (#88 `gap_s <= 0.15`)

_REPO_ROOT = Path(__file__).resolve().parents[5]
_WORKTREES = _REPO_ROOT.parent


def _spike(name: str) -> Path:
    return _WORKTREES / name / "spikes" / name


class Limits(BaseModel):
    model_config = ConfigDict(frozen=True)
    min_total_s: float
    max_total_s: float


class ProduceConfig(BaseModel):
    model_config = ConfigDict(frozen=True)

    tts_spike: Path = _spike("p1-tts-vi")
    render_v2: Path = _spike("p1-render-v2")
    render_ff: Path = _WORKTREES / "spike-p1-render" / "spikes" / "p1-render"  # chỉ đọc config.py
    cache_dir: Path = Path.home() / ".cache" / "ai-review-produce"
    scratch_dir: Path = Path(tempfile.gettempdir()) / "ai-review-produce"

    voice: str = "Hải Đăng"  # đổi bằng PRODUCE_VOICE; sau này cho người dùng chọn
    # VieNeu `max_chars`: 60 = mỗi câu sinh riêng, ngữ điệu "reset" theo câu. 0 = mặc định của SDK.
    tts_max_chars: int = Field(default=60, ge=0)
    tts_device: str = "cpu"  # cpu = ONNX; cuda = PyTorch; auto = cuda nếu torch thấy GPU
    tts_backend: str = "auto"
    # Mốc từng từ cho phụ đề: "whisper-1" (cần OPENAI_API_KEY), "local:small" (faster-whisper,
    # không cần khoá) hoặc "" = tắt (chia theo ký tự).
    stt_model: str = ""
    # QA khung hình bằng mô hình thị giác OpenAI (vd. "gpt-5.4-mini", cần OPENAI_API_KEY); "" = tắt.
    qa_model: str = ""

    preset: str = "dien-anh-toi-gian"
    fps: int = 30
    lead_s: float = 0.1  # trước câu đầu tiên
    gap_s: float = 0.12  # nghỉ giữa hai câu, 0,12–0,15 s
    tail_s: float = 0.6  # giữ khung cuối sau câu cuối
    workers: str = "3"  # --workers của HyperFrames cho MỖI tỉ lệ (số đo #95: 3 tốt hơn auto)
    # P1-09: dựng song song theo cảnh. `sequential` = đường cũ (mỗi tỉ lệ một tiến trình).
    render_mode: Literal["sequential", "parallel"] = "sequential"
    render_jobs: int = Field(default=4, ge=1)  # số tiến trình HyperFrames chạy cùng lúc (parallel)
    render_job_ram_mb: int = Field(default=1900, ge=256)  # đỉnh RAM mỗi tiến trình (đo: 1,7–1,9 GB)
    render_ram_reserve_mb: int = Field(
        default=2048, ge=0
    )  # chừa lại cho hệ điều hành + trình duyệt
    render_cache: bool = True  # cache MP4 theo cảnh; --no-cache tắt
    # Cờ/biến môi trường thêm cho `hyperframes render` (để đo bench; mặc định rỗng = như cũ).
    hf_args: str = ""  # vd. "--experimental-fast-capture --browser-gpu"
    hf_env: str = ""  # vd. "HYPERFRAMES_RENDER_LOCK=off,KEY=VAL"

    brand_icon: str = "sparkles"  # icon Lucide có sẵn trong template #88
    default_icon: str = "sparkles"
    check_icon: str = "check"

    ffprobe: str = "ffprobe"
    ffmpeg: str = "ffmpeg"

    @field_validator("hf_args")
    @classmethod
    def _hf_args(cls, v: str) -> str:
        shlex.split(v)  # báo lỗi sớm nếu dấu nháy sai
        return v

    @field_validator("gap_s")
    @classmethod
    def _gap(cls, v: float) -> float:
        if not 0 <= v <= MAX_GAP_S:
            raise ValueError(f"gap_s phải trong 0–{MAX_GAP_S} s (tiêu chí khoảng nghỉ), nhận {v}")
        return v

    @property
    def hf_env_map(self) -> dict[str, str]:
        pairs = (p.partition("=") for p in self.hf_env.split(",") if p.strip())
        return {k.strip(): v.strip() for k, _, v in pairs if k.strip()}

    @property
    def scene_cache_dir(self) -> Path:
        """Cache MP4 theo cảnh (nằm ngoài repo, cùng gốc với cache TTS)."""
        return self.cache_dir / "render-scenes"

    @property
    def tts_dir(self) -> Path:
        return self.tts_spike / "vieneu"

    @staticmethod
    def venv_python(root: Path) -> Path:
        return root / ".venv" / ("Scripts/python.exe" if sys.platform == "win32" else "bin/python")

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None) -> Self:
        e = os.environ if env is None else env

        def pick(*names: str) -> str | None:
            for key in names:
                if e.get(key, "").strip():
                    return e[key].strip()
            return None

        raw: dict[str, object] = {}
        legacy = {"tts_spike": "P1_TTS_VI", "render_v2": "P1_RENDER_V2", "render_ff": "P1_RENDER"}
        for field in (
            "tts_spike",
            "render_v2",
            "render_ff",
            "cache_dir",
            "scratch_dir",
            "voice",
            "tts_max_chars",
            "tts_device",
            "tts_backend",
            "stt_model",
            "qa_model",
            "preset",
            "gap_s",
            "workers",
            "render_mode",
            "render_jobs",
            "render_job_ram_mb",
            "render_ram_reserve_mb",
            "render_cache",
            "hf_args",
            "hf_env",
        ):
            names = [ENV_PREFIX + field.upper()]
            if field in legacy:
                names.append(legacy[field])
            val = pick(*names)
            if val is not None:
                raw[field] = val
        return cls.model_validate(raw)


def load_limits(cfg: ProduceConfig) -> Limits:
    """Mốc min/max tổng thời lượng, đọc từ `config.py` của #77 (đã gồm biến môi trường của #77)."""
    path = cfg.render_ff / "config.py"
    if not path.is_file():
        raise ProduceError(f"thiếu config chung của #77: {path} (đặt PRODUCE_RENDER_FF)")
    name = "p1_render_ff_config"
    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise ProduceError(f"không nạp được {path}")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclass cần module có trong sys.modules
    spec.loader.exec_module(mod)
    env = {mod.ENV_MIN: f"{DEFAULT_MIN_TOTAL_S:g}", mod.ENV_MAX: f"{DEFAULT_MAX_TOTAL_S:g}"}
    # Biến rỗng/toàn khoảng trắng bị bỏ qua, nếu không `_read` của #77 quay về mặc định 40–45 s
    env.update({k: v for k in (mod.ENV_MIN, mod.ENV_MAX) if (v := os.environ.get(k, "").strip())})
    lim = mod.load_limits(env)
    return Limits(min_total_s=lim.min_total_s, max_total_s=lim.max_total_s)
