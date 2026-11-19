"""Chia phụ đề của một câu thoại thành nhiều cue khi nó vượt giới hạn dòng của tỉ lệ khung hình.

Chỉ dùng thư viện chuẩn: `drivers/hf_render.py` nạp file này bằng đường dẫn và chạy nó trong
venv của spike #88, còn test CI chạy nó trong venv của worker.

Quy tắc:
- Câu vừa giới hạn (`fits`) thì giữ nguyên MỘT cue, y như #88 hiện tại.
- Không vừa thì chia thành ÍT cue nhất, mỗi cue vừa giới hạn. Giữa các cách chia cùng số cue,
  chọn cách các cue dài gần bằng nhau, ưu tiên ngắt sau dấu câu. Chỉ ngắt ở ranh giới từ,
  không bỏ và không đổi chữ nào.
- VieNeu chỉ cho độ dài cả câu (ADR-0004), chưa có mốc từng chữ. Thời gian mỗi cue vì thế chia
  theo TỈ LỆ SỐ KÝ TỰ trong khoảng audio của câu: đây là ước lượng, không phải timing thật.
  (Docstring `subtitles.py` của #88 từ chối timing kiểu này; P1-08 chủ động dùng nó thay cho
  việc bắt M2 viết lại phụ đề, và báo cáo ghi rõ.)
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

# Ký tự cho phép ngắt ngay sau nó (hết một ý).
BREAK_AFTER = (",", ";", ":", ".", "!", "?", "…", "—", "–", ")")
# Phạt cho mỗi chỗ ngắt không rơi vào dấu câu, tính bằng (ký tự)² như độ lệch độ dài giữa các cue.
# Nhỏ hơn độ lệch của một cách chia lệch hẳn, nên dấu câu thắng khi các cue vẫn tương đối cân.
SOFT_BREAK_PENALTY = 400.0


@dataclass(frozen=True)
class Cue:
    text: str
    start_s: float
    end_s: float


def _min_cues(words: list[str], fits: Callable[[str], bool]) -> int:
    """Số cue ít nhất để phủ hết `words` (quy hoạch động trên số cue)."""
    n = len(words)
    inf = n + 1
    best = [0] + [inf] * n
    for i in range(1, n + 1):
        for j in range(i - 1, -1, -1):
            # một từ đứng riêng luôn chấp nhận (từ dài hơn dòng thì không thể chia nhỏ hơn)
            if best[j] + 1 < best[i] and (j == i - 1 or fits(" ".join(words[j:i]))):
                best[i] = best[j] + 1
    return best[n]


def split_caption(text: str, fits: Callable[[str], bool]) -> list[str]:
    """Chia `text` thành các cue; nối lại bằng dấu cách ra đúng chữ gốc (khoảng trắng đã chuẩn hoá).

    `fits(cue)`: cue có nằm trong giới hạn dòng không (với #88: `wrap_caption` ra ≤ MAX_LINES dòng).
    """
    words = text.split()
    if not words:
        return []
    whole = " ".join(words)
    if fits(whole):
        return [text if text == whole else whole]

    k = _min_cues(words, fits)
    mean = len(whole) / k
    n = len(words)
    cost: list[list[float]] = [[float("inf")] * (n + 1) for _ in range(k + 1)]
    back: list[list[int]] = [[-1] * (n + 1) for _ in range(k + 1)]
    cost[0][0] = 0.0
    for c in range(1, k + 1):
        for i in range(c, n + 1):
            for j in range(c - 1, i):
                prev = cost[c - 1][j]
                if prev == float("inf"):
                    continue
                chunk = " ".join(words[j:i])
                if not (fits(chunk) or i - j == 1):
                    continue
                step = (len(chunk) - mean) ** 2
                if i < n and not chunk.endswith(BREAK_AFTER):
                    step += SOFT_BREAK_PENALTY
                if prev + step < cost[c][i]:
                    cost[c][i] = prev + step
                    back[c][i] = j
    out: list[str] = []
    i = n
    for c in range(k, 0, -1):
        j = back[c][i]
        out.append(" ".join(words[j:i]))
        i = j
    return out[::-1]


def time_cues(texts: list[str], start_s: float, end_s: float) -> list[Cue]:
    """Chia [start_s, end_s] cho các cue theo số ký tự: liền nhau, không chồng, cuối = `end_s`."""
    if not texts:
        return []
    total = sum(len(t) for t in texts)
    span = end_s - start_s
    cues: list[Cue] = []
    done = 0
    prev_end = start_s
    for idx, t in enumerate(texts):
        done += len(t)
        stop = end_s if idx == len(texts) - 1 else start_s + span * done / total
        cues.append(Cue(t, prev_end, stop))
        prev_end = stop
    return cues
