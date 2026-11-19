"""QA bằng mô hình thị giác (OpenAI) trên khung hình của MP4 đã dựng. Chỉ BÁO, không sửa video.

Mỗi cảnh lấy một khung ở ~60% thời lượng (zoom/phụ đề đã ổn định), gửi kèm lời đọc và phụ đề của
câu đang phát. Mô hình trả JSON: chữ có đọc được không, có bị cắt mép không, tiêu đề có lặp phụ
đề không, hình có hợp lời đọc không. Lỗi mạng/API chỉ thành cảnh báo `qa_failed`, không làm hỏng
video. Adapter mỏng (ADR-0005); bật bằng `PRODUCE_QA_MODEL` (vd. gpt-5.4-mini) + `OPENAI_API_KEY`.
"""

from __future__ import annotations

import base64
import json
import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol

import httpx

from worker.produce.config import ProduceConfig
from worker.produce.errors import ProduceError
from worker.produce.runner import Runner, require_ok
from worker.produce.timeline import Timeline

log = logging.getLogger("worker.produce.qa")

OPENAI_URL = "https://api.openai.com/v1/chat/completions"
FRAME_AT = 0.6  # vị trí khung trong cảnh (0 = đầu, 1 = cuối)
CHECKS = ("readable", "not_cut_off", "title_distinct_from_subtitle", "matches_narration")

SYSTEM = (
    "Bạn kiểm tra một khung hình của video review sản phẩm tiếng Việt (tỉ lệ {ratio}). "
    "Chỉ nhìn ảnh và đối chiếu với chữ được cung cấp; không bịa. "
    "Bối cảnh bố cục: clip thao tác nằm trong khung trình duyệt; ở tỉ lệ 9:16 khung này CỐ Ý "
    "tràn sát mép trái/phải, và phụ đề nằm ở vùng dưới. Mép khung chứa clip không phải lỗi. "
    "Phụ đề được chia thành nhiều cue ngắn nên mỗi lúc chỉ hiện MỘT PHẦN của 'Phụ đề đang "
    "hiện' (đầu, giữa hoặc cuối câu): đó là bình thường, không phải lỗi cụt hay không khớp. "
    "Trả về MỘT object JSON có các khoá boolean: "
    "readable (mọi chữ trên hình đọc rõ, không mờ/vỡ), "
    "not_cut_off (false CHỈ khi một từ hay nút bị cắt đứt giữa chừng hoặc chữ tràn ra ngoài khung; "
    "việc clip chạm mép khung thì vẫn true), "
    "title_distinct_from_subtitle (false CHỈ khi tiêu đề trên hình và phụ đề là cùng một câu hoặc "
    "gần như giống hệt; tên thương hiệu ngắn không tính là lặp; true nếu không có tiêu đề), "
    "matches_narration (so với 'Phụ đề đang hiện', tức câu đang được đọc lúc này, KHÔNG phải cả "
    "cảnh: false CHỈ khi hình mâu thuẫn hoặc rõ ràng không liên quan tới câu đó; 'Lời cả cảnh' "
    "chỉ để hiểu ngữ cảnh); "
    "và issues: danh sách chuỗi ngắn mô tả từng lỗi thật (rỗng nếu không có)."
)


@dataclass(frozen=True)
class FrameJob:
    ratio: str
    scene_id: str
    t_s: float
    narration: str  # lời đọc của cả cảnh
    caption: str  # phụ đề của câu đang phát tại t_s


@dataclass
class FrameVerdict:
    job: FrameJob
    ok: bool
    checks: dict[str, bool]
    issues: list[str]


class VisionQA(Protocol):
    model: str

    def review(self, image_jpeg: bytes, job: FrameJob) -> dict[str, Any]: ...


@dataclass
class OpenAIVisionQA:
    api_key: str
    model: str
    timeout_s: float = 120.0
    client: httpx.Client | None = None
    retry_delays_s: tuple[float, ...] = (3.0, 10.0)
    tokens_in: int = 0
    tokens_out: int = 0
    calls: int = field(default=0)

    def __post_init__(self) -> None:
        self._client = self.client or httpx.Client(timeout=self.timeout_s)

    def review(self, image_jpeg: bytes, job: FrameJob) -> dict[str, Any]:
        b64 = base64.b64encode(image_jpeg).decode()
        user = [
            {
                "type": "text",
                "text": f"Phụ đề đang hiện: {job.caption}\nLời cả cảnh (ngữ cảnh): {job.narration}",
            },
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
        ]
        body = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM.format(ratio=job.ratio)},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        err = ""
        for attempt in range(len(self.retry_delays_s) + 1):
            try:
                r = self._client.post(OPENAI_URL, json=body, headers=headers)
            except httpx.HTTPError as ex:
                err = f"lỗi mạng {type(ex).__name__}"
            else:
                if r.status_code == 200:
                    return self._parse(r.json())
                err = f"HTTP {r.status_code}: {r.text[:200]}"
                if r.status_code not in (429, 500, 502, 503, 504):
                    raise ProduceError(f"OpenAI QA từ chối: {err}")
            if attempt < len(self.retry_delays_s):
                time.sleep(self.retry_delays_s[attempt])
        raise ProduceError(f"OpenAI QA lỗi sau {len(self.retry_delays_s) + 1} lần: {err}")

    def _parse(self, data: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        usage = data.get("usage") or {}
        self.tokens_in += int(usage.get("prompt_tokens", 0))
        self.tokens_out += int(usage.get("completion_tokens", 0))
        try:
            out = json.loads(data["choices"][0]["message"]["content"])
        except (KeyError, IndexError, TypeError, ValueError) as ex:
            raise ProduceError("OpenAI QA trả response không phải JSON") from ex
        if not isinstance(out, dict):
            raise ProduceError("OpenAI QA trả JSON không phải object")
        return out


def verdict_from(job: FrameJob, raw: dict[str, Any]) -> FrameVerdict:
    """Khoá thiếu coi là chưa kiểm được (False) để lỗi không bị bỏ sót."""
    checks = {k: raw.get(k) is True for k in CHECKS}
    issues = [str(i) for i in raw.get("issues") or [] if str(i).strip()]
    return FrameVerdict(job, all(checks.values()), checks, issues)


def frame_jobs(
    ratio: str, timeline: Timeline, scenes: Sequence[tuple[str, list[tuple[str, str]]]]
) -> list[FrameJob]:
    """scenes: [(scene_id, [(segment_id, phụ đề), ...])]; mỗi cảnh một khung."""
    jobs: list[FrameJob] = []
    for scene_id, segs in scenes:
        ts = timeline.scene(scene_id)
        t = ts.start_f / ts.fps + FRAME_AT * ts.duration_s
        caption = ""
        text = {sid: cap for sid, cap in segs}
        for seg in ts.segments:
            if seg.start_s <= t <= seg.end_s:
                caption = text.get(seg.segment_id, "")
        jobs.append(FrameJob(ratio, scene_id, round(t, 2), " ".join(c for _, c in segs), caption))
    return jobs


def extract_frame(mp4: Path, t_s: float, out: Path, cfg: ProduceConfig, runner: Runner) -> bytes:
    require_ok(
        runner(
            [cfg.ffmpeg, "-v", "error", "-y", "-ss", f"{t_s:.3f}", "-i", str(mp4),
             "-frames:v", "1", "-q:v", "3", str(out)],
            timeout_s=120,
        ),
        f"ffmpeg khung {t_s:.1f}s {mp4.name}",
    )  # fmt: skip
    return out.read_bytes()


def run_qa(
    qa: VisionQA,
    mp4_by_ratio: dict[str, Path],
    jobs_by_ratio: dict[str, list[FrameJob]],
    cfg: ProduceConfig,
    runner: Runner,
    work: Path,
) -> tuple[list[FrameVerdict], list[str]]:
    """Duyệt mọi khung; lỗi từng khung thành cảnh báo, các khung còn lại vẫn chạy."""
    work.mkdir(parents=True, exist_ok=True)
    verdicts: list[FrameVerdict] = []
    warnings: list[str] = []
    for ratio, jobs in jobs_by_ratio.items():
        mp4 = mp4_by_ratio.get(ratio)
        if mp4 is None:
            continue
        for job in jobs:
            tag = f"{ratio.replace(':', 'x')}-{job.scene_id}"
            try:
                jpeg = extract_frame(mp4, job.t_s, work / f"{tag}.jpg", cfg, runner)
                v = verdict_from(job, qa.review(jpeg, job))
            except (ProduceError, OSError) as ex:
                warnings.append(f"qa_failed[{ratio}/{job.scene_id}]: {ex}")
                continue
            verdicts.append(v)
            if not v.ok:
                bad = [k for k, ok in v.checks.items() if not ok]
                detail = "; ".join(v.issues) or ", ".join(bad)
                warnings.append(f"qa_issue[{ratio}/{job.scene_id}@{job.t_s}s]: {detail}")
    return verdicts, warnings
