"""Với từng khung của cảnh <video>, tìm khung của clip đã chuẩn bị khớp nhất (độ lệch d trong -R..R).
Đường nào chọn đúng khung thì d cố định (= độ lệch bảo đổi của cảnh, thường 0); đường sai có d nhảy.

    python clipmatch.py <mp4> <clip.mp4> <abs_start_frame> <n_frames> [R]
In ra JSON: histogram d, số khung có d != mode, các khung lệch.
"""
import json, re, subprocess, sys, tempfile
from collections import Counter
from pathlib import Path

mp4, clip, start, n = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
R = int(sys.argv[5]) if len(sys.argv) > 5 else 6
tmp = Path(tempfile.mkdtemp(prefix="clipmatch-"))


def psnr_series(d: int) -> list[float]:
    # khung f của cảnh (f = 0..n-1) so với khung f+d của clip
    out_trim = f"trim=start_frame={start + max(0, -d)}:end_frame={start + n},setpts=N/30/TB,crop=920:670:138:175"
    clip_trim = f"trim=start_frame={max(0, d)}:end_frame={n + max(0, d)},setpts=N/30/TB,scale=920:670:flags=bicubic"
    stats = tmp / f"s{d}.txt"
    subprocess.run(
        ["ffmpeg", "-v", "error", "-i", mp4, "-i", clip, "-lavfi",
         f"[0:v]{out_trim}[a];[1:v]{clip_trim}[b];[a][b]psnr=stats_file={stats.name}", "-f", "null", "-"],
        check=True, cwd=tmp)
    vals = []
    for l in stats.read_text().splitlines():
        m = re.search(r"psnr_avg:(\S+)", l)
        vals.append(99.0 if m.group(1) == "inf" else float(m.group(1)))
    return vals


series = {d: psnr_series(d) for d in range(-R, R + 1)}
if len(sys.argv) > 6: Path(sys.argv[6]).write_text(json.dumps({str(d): v for d, v in series.items()}))
best = []
for f in range(n):
    cand = [(series[d][f - max(0, -d)] if 0 <= f - max(0, -d) < len(series[d]) else -1, d) for d in series]
    # f de PSNR chỉ có ý nghĩa khi cả hai khung tồn tại
    best.append(max(cand)[1] if max(cand)[0] > 0 else None)
valid = [b for b in best if b is not None]
mode = Counter(valid).most_common(1)[0][0]
off = [(f, b) for f, b in enumerate(best) if b is not None and b != mode]
print(json.dumps({
    "mp4": mp4, "frames": n, "mode_d": mode,
    "hist": dict(sorted(Counter(valid).items())),
    "off_mode": len(off),
    "off_frames": off[:60],
}, ensure_ascii=False))
