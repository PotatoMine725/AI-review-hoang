"""Dựng lệnh ffmpeg (một lần chạy, một filter_complex) từ timeline + preset + tỉ lệ.

Mỗi cảnh thành một luồng hình đúng kích thước đầu ra, rồi nối bằng xfade/concat, áp lớp phủ
của preset, đốt phụ đề ASS. Voice đặt đúng mốc bằng adelay, trộn với nhạc nền (tự nhỏ đi khi
có voice nhờ sidechaincompress). Chỉ xử lý chuỗi, không chạy ffmpeg nên test được không cần ffmpeg.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from media import probe_image_size
from presets import FPS, FRAME_SIZE, Motion, Preset, Ratio
from render_plan import RenderPlan
from timeline import TimedScene, Timeline

Encoder = Literal["cpu", "nvenc", "qsv"]

ENCODER_ARGS: dict[Encoder, list[str]] = {
    # Đường chạy mặc định, không cần GPU.
    "cpu": [
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "21",
        "-profile:v",
        "high",
        "-pix_fmt",
        "yuv420p",
    ],  # fmt: skip
    # GPU chỉ là tăng tốc tuỳ chọn: phần lọc hình (zoompan, blur, libass) vẫn chạy trên CPU.
    "nvenc": [
        "-c:v",
        "h264_nvenc",
        "-preset",
        "p5",
        "-rc",
        "vbr",
        "-cq",
        "23",
        "-b:v",
        "0",
        "-profile:v",
        "high",
        "-pix_fmt",
        "yuv420p",
    ],  # fmt: skip
    "qsv": [
        "-c:v",
        "h264_qsv",
        "-global_quality",
        "23",
        "-preset",
        "veryfast",
        "-pix_fmt",
        "nv12",
    ],  # fmt: skip
}

# Ảnh coi là "cùng tỉ lệ" với khung khi lệch dưới 1%.
RATIO_TOLERANCE = 0.01
# Nền mờ làm ở độ phân giải thấp (1/4) rồi phóng lên: nhanh hơn nhiều, trông vẫn mịn.
BLUR_DOWNSCALE = 4


@dataclass(frozen=True)
class BuiltCommand:
    args: list[str]  # lệnh ffmpeg đầy đủ (chạy với cwd = thư mục làm việc)
    filter_script: str  # nội dung file filter_complex
    ass_name: str
    filter_name: str


def _motion_expr(motion: Motion, frames: int, zoom: float) -> str:
    zmax = 1 + zoom
    cx, cy = "iw/2-(iw/zoom/2)", "ih/2-(ih/zoom/2)"
    if motion == "zoom_in":
        return f"z='1+{zoom}*on/{frames}':x='{cx}':y='{cy}'"
    return f"z='{zmax}-{zoom}*on/{frames}':x='{cx}':y='{cy}'"  # zoom_out


def _same_ratio(iw: int, ih: int, w: int, h: int) -> bool:
    return abs(iw / ih - w / h) <= RATIO_TOLERANCE * (w / h)


def _composite(
    src: str, iw: int, ih: int, w: int, h: int, tag: str, shrink: float = 1.0
) -> tuple[list[str], str]:
    """Đặt ảnh/clip vào khung w×h không cắt nội dung: nền là chính nó phóng to + làm mờ,
    ảnh nguyên vẹn ở giữa. Cùng tỉ lệ thì phủ kín khung. Trả (các filter, nhãn đầu ra).

    `shrink` > 1 thu nhỏ ảnh giữa còn 1/shrink khung, chừa chỗ cho zoom Ken Burns: ở mức zoom
    cuối ảnh vừa khít khung, nên zoom không bao giờ cắt mất mép ảnh."""
    if _same_ratio(iw, ih, w, h):
        return [f"[{src}]scale={w}:{h}[c{tag}]"], f"c{tag}"
    fw, fh = int(w / shrink) // 2 * 2, int(h / shrink) // 2 * 2
    qw, qh = w // BLUR_DOWNSCALE, h // BLUR_DOWNSCALE
    return [
        f"[{src}]split=2[bg{tag}][fg{tag}]",
        f"[bg{tag}]scale={qw}:{qh}:force_original_aspect_ratio=increase,crop={qw}:{qh},"
        f"boxblur=10:2,scale={w}:{h},eq=brightness=-0.06[bb{tag}]",
        f"[fg{tag}]scale={fw}:{fh}:force_original_aspect_ratio=decrease[ff{tag}]",
        f"[bb{tag}][ff{tag}]overlay=(W-w)/2:(H-h)/2[c{tag}]",
    ], f"c{tag}"


def _scene_video(ts: TimedScene, k: int | None, preset: Preset, w: int, h: int) -> list[str]:
    """Filter tạo luồng [v{i}] của một cảnh. `k` là chỉ số input hình (None với text_card)."""
    i = ts.index
    tail = f"fps={FPS},settb=1/{FPS},setpts=PTS-STARTPTS,setsar=1,format=yuv420p[v{i}]"
    kind = ts.scene.kind
    if kind == "text_card":
        if preset.card_gradient:
            c0, c1 = preset.card_gradient
            src = (
                f"gradients=s={w}x{h}:r={FPS}:d={ts.duration_s:.4f}:c0={c0}:c1={c1}"
                f":x0=0:y0=0:x1={w}:y1={h}:speed=0.02"
            )
        else:
            src = f"color=c={preset.card_bg}:s={w}x{h}:r={FPS}:d={ts.duration_s:.4f}"
        return [f"{src},{tail}"]

    assert ts.scene.asset is not None and k is not None
    iw, ih = probe_image_size(Path(ts.scene.asset))
    if kind == "image":
        # Làm việc ở kích thước gấp đôi rồi mới zoompan để chuyển động mượt, không giật pixel.
        w2, h2 = w * 2, h * 2
        motion = preset.motions[i % len(preset.motions)]
        pan = (
            f"zoompan={_motion_expr(motion, ts.frames, preset.kb_zoom)}:d={ts.frames}"
            f":s={w}x{h}:fps={FPS}"
        )
        parts, label = _composite(f"{k}:v", iw, ih, w2, h2, str(i), shrink=1 + preset.kb_zoom)
        return [*parts, f"[{label}]{pan},{tail}"]
    # video (vd clip AI): phát lặp nếu ngắn hơn cảnh, cắt đúng thời lượng cảnh.
    parts, label = _composite(f"vin{i}", iw, ih, w, h, str(i))
    return [
        f"[{k}:v]fps={FPS}[vin{i}]",
        *parts,
        f"[{label}]trim=duration={ts.duration_s:.4f},{tail}",
    ]


def _vignette_filters(w: int, h: int) -> list[str]:
    """Vignette qua mặt nạ tạo một lần rồi nhân vào từng khung (`lut2`, chạy đa luồng).

    Filter `vignette` của FFmpeg chạy một luồng và tính từng pixel của mọi khung: riêng nó
    chiếm ~19 s trong ~35 s dựng preset điện ảnh. Mặt nạ dựng từ chính filter đó trên 1 khung
    trắng, chỉ nhân luma (chroma giữ nguyên); khác bản gốc chỉ ở nhiễu dither."""
    return [
        f"color=c=white:s={w}x{h}:r={FPS}:d=0.034,format=yuv420p,vignette=angle=PI/5,"
        "loop=loop=-1:size=1[vmask]",
        # lut2: bảng tra dựng một lần (nhanh); c1/c2='x' giữ nguyên chroma. Đừng thay bằng
        # blend: c1_expr tính biểu thức từng pixel (chậm), c1_opacity=0 làm mất màu.
        "[vgrade][vmask]lut2=c0='x*y/255':c1='x':c2='x':shortest=1[vlit]",
    ]


def _post_chain(preset: Preset, ass_name: str, fonts_dir: str) -> list[str]:
    """Các filter sau lớp màu/vignette: dải đen, viền, phụ đề, ép pixel format."""
    chain: list[str] = []
    if preset.bars_frac:
        f = preset.bars_frac
        chain.append(f"drawbox=x=0:y=0:w=iw:h=ih*{f}:color=black:t=fill")
        chain.append(f"drawbox=x=0:y=ih*{1 - f:.4f}:w=iw:h=ih*{f}:color=black:t=fill")
    if preset.border_px:
        chain.append(f"drawbox=x=0:y=0:w=iw:h=ih:color={preset.border_color}:t={preset.border_px}")
    chain.append(f"ass=filename={ass_name}:fontsdir={fonts_dir}")
    # Ảnh JPEG là full-range (yuvj420p); ép về yuv420p limited-range cho tương thích player.
    chain.append("scale=in_range=auto:out_range=tv,format=yuv420p")
    return chain


def build_command(
    plan: RenderPlan,
    tl: Timeline,
    preset: Preset,
    ratio: Ratio,
    out_path: Path,
    encoder: Encoder = "cpu",
    ass_name: str = "subs.ass",
    filter_name: str = "graph.txt",
    fonts_dir: str = "fonts",
    log_level: str = "info",
) -> BuiltCommand:
    """Lệnh ffmpeg đầy đủ. Chạy với cwd = thư mục làm việc chứa `ass_name` và `filter_name`;
    `fonts_dir` là đường dẫn tương đối từ cwd đến thư mục font (tránh escape ổ đĩa Windows)."""
    w, h = FRAME_SIZE[ratio]
    total = tl.total_s
    inputs: list[str] = []
    n_inputs = 0
    filters: list[str] = []

    # --- Hình ---
    for ts in tl.scenes:
        k: int | None = None
        if ts.scene.kind == "image":
            inputs += ["-i", str(ts.scene.asset)]
            k, n_inputs = n_inputs, n_inputs + 1
        elif ts.scene.kind == "video":
            inputs += ["-stream_loop", "-1", "-t", f"{ts.duration_s + 0.5:.3f}",
                       "-i", str(ts.scene.asset)]  # fmt: skip
            k, n_inputs = n_inputs, n_inputs + 1
        filters += _scene_video(ts, k, preset, w, h)

    n = len(tl.scenes)
    if tl.transition_s == 0:
        joined = "".join(f"[v{i}]" for i in range(n))
        filters.append(f"{joined}concat=n={n}:v=1:a=0[vjoin]")
    elif n == 1:
        filters.append("[v0]null[vjoin]")  # 1 cảnh: không có chuyển cảnh nào để nối
    else:
        cur = "v0"
        for ts in tl.scenes[1:]:
            nxt = "vjoin" if ts.index == n - 1 else f"vx{ts.index}"
            filters.append(
                f"[{cur}][v{ts.index}]xfade=transition={preset.transition}"
                f":duration={tl.transition_s:.4f}:offset={ts.start_s:.4f}[{nxt}]"
            )
            cur = nxt
    post = ",".join(_post_chain(preset, ass_name, fonts_dir))
    if preset.vignette:
        filters.append(f"[vjoin]{preset.grade or 'null'}[vgrade]")
        filters += _vignette_filters(w, h)
        filters.append(f"[vlit]{post}[vout]")
    else:
        pre = f"{preset.grade}," if preset.grade else ""
        filters.append(f"[vjoin]{pre}{post}[vout]")

    # --- Tiếng ---
    stereo = "aresample=48000,aformat=sample_fmts=fltp:channel_layouts=stereo"
    voice_labels: list[str] = []
    for ts in tl.scenes:
        if not ts.scene.voice:
            continue
        inputs += ["-i", str(ts.scene.voice)]
        a = n_inputs
        n_inputs += 1
        ms = round(ts.voice_start_s * 1000)
        filters.append(f"[{a}:a]{stereo},adelay={ms}|{ms}[av{ts.index}]")
        voice_labels.append(f"[av{ts.index}]")
    music_label: str | None = None
    if plan.music:
        inputs += ["-stream_loop", "-1", "-t", f"{total:.3f}", "-i", plan.music]
        m = n_inputs
        n_inputs += 1
        filters.append(
            f"[{m}:a]{stereo},volume={preset.music_volume},afade=t=in:d=1,"
            f"afade=t=out:st={max(total - 1.5, 0):.3f}:d=1.5[mus]"
        )
        music_label = "[mus]"

    if voice_labels:
        filters.append(
            f"{''.join(voice_labels)}amix=inputs={len(voice_labels)}:normalize=0:duration=longest,"
            "loudnorm=I=-16:TP=-1.5:LRA=11,aresample=48000[voice]"
        )
        if music_label:
            filters.append("[voice]asplit=2[vo][vsc]")
            filters.append(
                f"{music_label}[vsc]sidechaincompress=threshold=0.02:ratio=12:attack=10"
                ":release=350[mduck]"
            )
            filters.append("[vo][mduck]amix=inputs=2:normalize=0:duration=first[amix]")
            mix = "amix"
        else:
            mix = "voice"
    elif music_label:
        mix = "mus"
    else:
        filters.append("anullsrc=r=48000:cl=stereo[silence]")
        mix = "silence"
    filters.append(f"[{mix}]apad=whole_dur={total:.3f},atrim=0:{total:.3f}[aout]")

    args = [
        "ffmpeg", "-hide_banner", "-y", "-benchmark", "-nostats", "-v", log_level, *inputs,
        "-/filter_complex", filter_name,
        "-map", "[vout]", "-map", "[aout]",
        *ENCODER_ARGS[encoder], "-r", str(FPS),
        "-c:a", "aac", "-b:a", "160k", "-ar", "48000",
        "-movflags", "+faststart", "-t", f"{total:.3f}", str(out_path),
    ]  # fmt: skip
    return BuiltCommand(
        args=args,
        filter_script=";\n".join(filters) + "\n",
        ass_name=ass_name,
        filter_name=filter_name,
    )
