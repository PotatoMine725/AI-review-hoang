"""Dựng thư mục project HyperFrames cho một tỉ lệ: index.html + template + font + media.

    .work/<plan>-<ratio>/
      index.html                ← sinh ra: mỗi cảnh = 1 host chứa đoạn HTML của layout
      template/                 ← chép từ template/ (FE sở hữu) + icons.js sinh từ icons/*.svg
      template/fonts/           ← font OFL
      media/                    ← clip đã cắt/tua, ảnh AI (không commit)

Dữ liệu cảnh đi qua thuộc tính data-vars của host (props + biến CSS); runtime.js đổ vào layout.
Python chỉ sửa layout ở một chỗ: ghi src tĩnh (và id, mốc thời gian cho <video>) theo data-src,
vì HyperFrames chỉ trích khung những video có src + id ngay trong HTML lúc dựng.

Vì sao không dùng sub-composition (data-composition-src) của HyperFrames: sub-composition chỉ được
gắn vào DOM khi tới lượt, mà bước dò video chạy một lần lúc đầu, nên video của cảnh sau bị bỏ qua
(clip đứng hình ở khung đầu). Xem README mục "Bước 0".
"""

from __future__ import annotations

import html
import json
import re
import shutil
from pathlib import Path

from media import prepare_clip
from plan import Ratio, RenderPlan
from slots import LayoutInfo, clip_css, clip_speed, load_layouts
from subtitles import FRAME_SIZE
from timeline import Timeline

ROOT = Path(__file__).resolve().parent
TEMPLATE_DIR = ROOT / "template"
FONTS_DIR = ROOT / "fonts"
RATIO_CLASS = {"9:16": "r916", "16:9": "r169"}


def icons_js(icon_dir: Path) -> str:
    """Gộp SVG Lucide thành window.TPL_ICONS = {tên: "<svg…>"} (giữ dòng license ISC)."""
    icons = {}
    for f in sorted(icon_dir.glob("*.svg")):
        svg = f.read_text(encoding="utf-8")
        svg = svg[svg.index("<svg") :]  # bỏ comment license ở từng file, ghi một lần ở đầu
        icons[f.stem] = " ".join(svg.split())
    return (
        "/* Lucide icons (lucide-static 1.59.0), ISC License, xem template/icons/LICENSE */\n"
        f"window.TPL_ICONS = {json.dumps(icons, ensure_ascii=False, indent=0)};\n"
    )


def check_layouts(plan: RenderPlan, layouts: dict[str, LayoutInfo]) -> None:
    for scene in plan.scenes:
        info = layouts.get(scene.layout)
        if info is None:
            raise ValueError(f"{scene.scene_id}: không có template/layouts/{scene.layout}.html")
        if scene.clip and "clip" not in info.slots:
            raise ValueError(f"{scene.scene_id}: layout {scene.layout} không có ô data-slot='clip'")


def scene_variables(plan: RenderPlan, tl: Timeline, media_paths: dict[str, str]) -> list[dict]:
    """Biến cho từng host: props (+ đường dẫn media) và biến CSS (thời lượng, zoom)."""
    out = []
    for scene, ts in zip(plan.scenes, tl.scenes, strict=True):
        props = json.loads(json.dumps(scene.props))  # bản sao sâu
        css: dict[str, str] = {"--dur": f"{ts.duration_s:.3f}s"}
        if scene.clip:
            props.setdefault("clip", {})["src"] = media_paths[scene.scene_id]
            css.update(clip_css(scene.clip, ts.duration_s))
        if scene.image:
            props.setdefault("image", {})["src"] = media_paths[scene.scene_id]
        out.append({"props": props, "css": css})
    return out


_MEDIA_TAG = re.compile(r'<(video|img)\b([^>]*?)\sdata-src="([^"]+)"([^>]*)>')


def _lookup(data: dict, path: str):
    cur = data
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return None
        cur = cur[key]
    return cur


def instantiate(fragment: str, scene_id: str, start_s: float, duration_s: float, props: dict
                ) -> str:  # fmt: skip
    """Ghi src tĩnh cho <img>/<video> có data-src; video thêm id + data-start/data-duration
    (mốc tuyệt đối trên timeline, HyperFrames dùng để trích đúng khung)."""
    count = 0

    def repl(m: re.Match[str]) -> str:
        nonlocal count
        tag, before, path, after = m.groups()
        src = _lookup(props, path)
        if not src:
            return m.group(0)
        extra = f' src="{html.escape(str(src), quote=True)}"'
        if tag == "video":
            extra += (
                f' id="clip-{scene_id}-{count}" data-start="{start_s:.4f}"'
                f' data-duration="{duration_s:.4f}"'
            )
            count += 1
        return f'<{tag}{before} data-src="{path}"{extra}{after}>'

    return _MEDIA_TAG.sub(repl, fragment)


def build_index(plan: RenderPlan, tl: Timeline, ratio: Ratio, variables: list[dict]) -> str:
    w, h = FRAME_SIZE[ratio]
    hosts = []
    for scene, ts, var in zip(plan.scenes, tl.scenes, variables, strict=True):
        fragment = (TEMPLATE_DIR / "layouts" / f"{scene.layout}.html").read_text(encoding="utf-8")
        body = instantiate(fragment, scene.scene_id, ts.start_s, ts.duration_s, var["props"])
        attr = html.escape(json.dumps(var, ensure_ascii=False), quote=True)
        hosts.append(
            f'<div class="clip scene-host" data-scene="{scene.scene_id}" '
            f'data-start="{ts.start_s:.4f}" data-duration="{ts.duration_s:.4f}" '
            f'data-vars="{attr}">\n{body}</div>'
        )
    host_lines = "\n".join(hosts)
    return f"""<!doctype html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width={w},height={h}">
<!-- Sinh tự động bởi compose.py từ {plan.product} / preset {plan.preset}. Không sửa tay. -->
<link rel="stylesheet" href="template/base.css">
<link rel="stylesheet" href="template/presets/{plan.preset}.css">
<script src="template/icons.js"></script>
<script src="template/runtime.js"></script>
</head>
<body>
<div id="root" class="{RATIO_CLASS[ratio]} preset-{plan.preset}" data-composition-id="root"
     data-width="{w}" data-height="{h}" data-start="0" data-duration="{tl.total_s:.4f}"
     data-no-timeline>
{host_lines}
</div>
</body>
</html>
"""


def compose(plan: RenderPlan, tl: Timeline, ratio: Ratio, work: Path, clip_cache: Path) -> Path:
    """Tạo project HyperFrames trong `work`; trả về đường dẫn index.html."""
    layouts = load_layouts(TEMPLATE_DIR / "layouts")
    check_layouts(plan, layouts)
    # Vùng cắt theo tỉ lệ: cả cắt clip (prepare_clip) lẫn zoom (clip_css) dùng cùng một crop.
    plan = plan.model_copy(
        update={
            "scenes": [
                s.model_copy(update={"clip": s.clip.for_ratio(ratio)}) if s.clip else s
                for s in plan.scenes
            ]
        }
    )
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(TEMPLATE_DIR, work / "template", ignore=shutil.ignore_patterns("icons"))
    shutil.copytree(FONTS_DIR, work / "template" / "fonts")
    (work / "template" / "icons.js").write_text(icons_js(TEMPLATE_DIR / "icons"), encoding="utf-8")
    media = work / "media"
    media.mkdir()

    media_paths: dict[str, str] = {}
    for scene, ts in zip(plan.scenes, tl.scenes, strict=True):
        if scene.clip:
            speed = clip_speed(scene.clip, ts.duration_s)
            src = prepare_clip(scene.clip, ts.duration_s, speed, ROOT, clip_cache, plan.fps)
            dst = media / f"{scene.scene_id}.mp4"
            shutil.copyfile(src, dst)
            media_paths[scene.scene_id] = f"media/{dst.name}"
        elif scene.image:
            src = (ROOT / scene.image.path).resolve()
            dst = media / f"{scene.scene_id}{src.suffix}"
            shutil.copyfile(src, dst)
            media_paths[scene.scene_id] = f"media/{dst.name}"

    index = work / "index.html"
    variables = scene_variables(plan, tl, media_paths)
    index.write_text(build_index(plan, tl, ratio, variables), encoding="utf-8")
    return index
