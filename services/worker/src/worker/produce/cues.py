"""Chia phụ đề của một câu thoại thành nhiều cue khi nó vượt giới hạn dòng của tỉ lệ khung hình.

Chỉ dùng thư viện chuẩn: `drivers/hf_render.py` nạp file này bằng đường dẫn và chạy nó trong
venv của spike #88, còn test CI chạy nó trong venv của worker.

Quy tắc:
- Câu vừa giới hạn (`fits`) thì giữ nguyên MỘT cue, y như #88 hiện tại.
- Không vừa thì chia thành ÍT cue nhất, mỗi cue vừa giới hạn. Giữa các cách chia cùng số cue,
  chọn cách các cue dài gần bằng nhau, ưu tiên ngắt sau dấu câu. Chỉ ngắt ở ranh giới từ,
  không bỏ và không đổi chữ nào.
- VieNeu chỉ cho độ dài cả câu (ADR-0004), chưa có mốc từng chữ. Khi có mốc từng từ do STT trả
  (`time_cues_words`, whisper-1 qua OpenAI) thì cue bám theo đó; không có hoặc khớp kém thì rơi
  về `time_cues`: thời gian mỗi cue chia theo TỈ LỆ SỐ KÝ TỰ
  trong khoảng audio của câu: đây là ước lượng, không phải timing thật.
  (Docstring `subtitles.py` của #88 từ chối timing kiểu này; P1-08 chủ động dùng nó thay cho
  việc bắt M2 viết lại phụ đề, và báo cáo ghi rõ.)
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from collections.abc import Callable, Sequence
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


# ---------------------------------------------------------------- mốc từng từ (STT)

# (từ, bắt đầu, kết thúc) tính bằng giây từ đầu file audio của câu.
Word = tuple[str, float, float]
MIN_MATCH_RATIO = 0.5  # < 50% từ của phụ đề khớp với STT: bản chép không đáng tin, bỏ
MIN_CUE_S = 0.05


def _norm(token: str) -> str:
    t = unicodedata.normalize("NFC", token).casefold()
    return re.sub(r"[^\w]+", "", t)


def _word_times(captions: list[str], words: Sequence[Word]) -> list[float] | None:
    """Thời điểm bắt đầu của từng từ phụ đề, ghép với từ STT (SequenceMatcher trên từ đã chuẩn
    hoá); từ không khớp (số, ký hiệu, từ STT chép khác) nội suy giữa hai mốc khớp gần nhất."""
    a = [_norm(w) for w in captions]
    b = [_norm(w[0]) for w in words]
    sm = difflib.SequenceMatcher(a=a, b=b, autojunk=False)
    anchor: dict[int, int] = {}
    for blk in sm.get_matching_blocks():
        for k in range(blk.size):
            if a[blk.a + k]:  # bỏ token chỉ gồm dấu câu
                anchor[blk.a + k] = blk.b + k
    if len(anchor) < MIN_MATCH_RATIO * max(1, sum(1 for x in a if x)):
        return None
    idx = sorted(anchor)
    out: list[float] = []
    for i in range(len(captions)):
        if i in anchor:
            out.append(words[anchor[i]][1])
            continue
        prev = max((j for j in idx if j < i), default=None)
        nxt = min((j for j in idx if j > i), default=None)
        if prev is None:
            out.append(words[anchor[nxt]][1] if nxt is not None else 0.0)  # type: ignore[index]
        elif nxt is None:
            out.append(words[anchor[prev]][2])
        else:
            t0, t1 = words[anchor[prev]][2], words[anchor[nxt]][1]
            out.append(t0 + (t1 - t0) * (i - prev) / (nxt - prev))
    return out


def time_cues_words(
    texts: list[str], words: Sequence[Word], start_s: float, end_s: float
) -> list[Cue] | None:
    """Như `time_cues` nhưng ranh giới cue lấy từ mốc từng từ của STT (giây từ đầu audio câu,
    cộng `start_s`). Trả None khi STT khớp kém để bên gọi rơi về `time_cues`.
    Cue liền nhau, không chồng, đầu = `start_s`, cuối = `end_s`; mỗi cue ≥ MIN_CUE_S."""
    if not texts:
        return []
    captions = " ".join(texts).split()
    times = _word_times(captions, words) if words else None
    if times is None:
        return None
    span = end_s - start_s
    first = 0
    starts = [0.0]
    for t in texts[:-1]:
        first += len(t.split())
        # ranh giới = lúc từ đầu tiên của cue sau bắt đầu được đọc
        starts.append(times[first])
    bounds = [0.0]
    for k in range(1, len(texts)):
        left = (len(texts) - k) * MIN_CUE_S
        bounds.append(min(max(starts[k], bounds[-1] + MIN_CUE_S), span - left))
    bounds.append(span)
    if any(b1 - b0 < MIN_CUE_S - 1e-9 for b0, b1 in zip(bounds, bounds[1:], strict=False)):
        return None  # câu quá ngắn để chia theo mốc: dùng cách chia theo ký tự
    return [Cue(t, start_s + bounds[i], start_s + bounds[i + 1]) for i, t in enumerate(texts)]
