"""CLI (chạy trong services/worker, trên máy truy cập được trang đích):

    uv run playwright install chromium          # một lần
    uv run python -m worker.demo samples --out <fixtures>
    uv run python -m worker.demo generate <brief.json> --fixtures <dir> --scripts <dir> [--regen]
    uv run python -m worker.demo record <script.json> --fixtures <dir> --out <dir> [--assets <f>]
    uv run python -m worker.demo run <brief.json> --fixtures <dir> --scripts <dir> --out <dir>

`run` = generate (nếu chưa có script) rồi record.
Mã thoát: 0 = ok, 2 = lỗi đầu vào/cấu hình, 3 = script hỏng trên trang thật (chạy generate --regen).
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import sys
from pathlib import Path

from worker.demo.errors import DemoError
from worker.m1.extract.__main__ import load_env
from worker.settings import MissingConfigError, Settings

log = logging.getLogger("worker.demo")


def _env_opts() -> tuple[str | None, bool]:
    return os.environ.get("DEMO_CHROMIUM_PATH") or None, os.environ.get("DEMO_HEADLESS", "1") != "0"


def cmd_samples(a: argparse.Namespace) -> int:
    from worker.demo.samples import make_samples

    for p in make_samples(a.out):
        print(p)
    return 0


def cmd_generate(a: argparse.Namespace) -> int:
    from worker.demo.generate import generate
    from worker.demo.llm import OpenAIScriptLLM
    from worker.demo.schema import Brief

    brief = Brief.model_validate_json(a.brief.read_text(encoding="utf-8"))
    target = a.scripts / f"{brief.asset_id}.json"
    if target.exists() and not a.regen:
        print(f"đã có {target} (dùng --regen để sinh lại)")
        return 0
    settings = Settings.from_env()
    settings.require("demo_script")
    model = os.environ.get("DEMO_LLM_MODEL", "").strip()
    if not model:
        raise MissingConfigError(["DEMO_LLM_MODEL"])
    llm = OpenAIScriptLLM(settings.openai_api_key.get_secret_value(), model)
    chromium, headless = _env_opts()
    script = generate(
        brief, llm, fixtures_dir=a.fixtures, chromium_path=chromium, headless=headless
    )
    a.scripts.mkdir(parents=True, exist_ok=True)
    target.write_text(
        json.dumps(script.model_dump(mode="json"), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(
        f"đã ghi {target} ({len(script.steps)} bước; token vào/ra {llm.tokens_in}/{llm.tokens_out})"
    )
    return 0


def cmd_record(a: argparse.Namespace) -> int:
    import shutil
    import tempfile

    from worker.demo.encode import build_asset, probe_duration, to_mp4
    from worker.demo.recorder import StepFailure, replay
    from worker.demo.schema import ActionScript
    from worker.produce.assets import AssetsFile

    script = ActionScript.model_validate_json(a.script.read_text(encoding="utf-8"))
    chromium, headless = _env_opts()
    raw_dir = Path(tempfile.mkdtemp(prefix="demo-rec-"))
    try:
        result = replay(
            script, fixtures_dir=a.fixtures, record_dir=raw_dir, chromium_path=chromium,
            headless=headless and not a.show,
        )  # fmt: skip
    except StepFailure as ex:
        print(f"script hỏng trên trang thật: {ex}\nUI có thể đã đổi: chạy lại với generate --regen",
              file=sys.stderr)  # fmt: skip
        shutil.rmtree(raw_dir, ignore_errors=True)
        return 3
    if script.dom_hash and result.dom_hash != script.dom_hash:
        print(
            f"CẢNH BÁO: DOM trang đầu đã đổi ({script.dom_hash} → {result.dom_hash}); "
            "clip vẫn quay xong, nên xem lại hoặc generate --regen",
            file=sys.stderr,
        )
    if not result.webm:
        raise DemoError("Playwright không trả file video")
    mp4 = a.out / "clips" / f"{script.asset_id}.mp4"
    to_mp4(result.webm, mp4)
    shutil.rmtree(raw_dir, ignore_errors=True)
    duration = probe_duration(mp4)
    base = a.assets.resolve().parent if a.assets else a.out.resolve()
    asset = build_asset(
        script, result, duration, os.path.relpath(mp4.resolve(), base).replace("\\", "/")
    )
    asset_json = asset.model_dump(mode="json", exclude_none=True)
    report = {
        "asset_id": script.asset_id,
        "mp4": str(mp4),
        "duration_s": round(duration, 2),
        "viewport": script.viewport.model_dump(),
        "step_times_s": result.step_times_s,
        "dom_hash": {"script": script.dom_hash, "now": result.dom_hash},
        "generated_by": script.generated_by,
        "asset": asset_json,
    }
    (a.out / f"{script.asset_id}.run.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if a.assets:
        data = (
            json.loads(a.assets.read_text(encoding="utf-8"))
            if a.assets.exists()
            else {"assets": {}}
        )
        data.setdefault("assets", {})[script.asset_id] = asset_json
        AssetsFile.model_validate(data)  # hỏng thì dừng, không ghi file dở
        a.assets.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"đã cập nhật {a.assets}")
    print(f"{mp4} ({duration:.1f} s)")
    return 0


def cmd_run(a: argparse.Namespace) -> int:
    from worker.demo.schema import Brief

    brief = Brief.model_validate_json(a.brief.read_text(encoding="utf-8"))
    code = cmd_generate(a)
    if code:
        return code
    a.script = a.scripts / f"{brief.asset_id}.json"
    return cmd_record(a)


def _parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python -m worker.demo", description=__doc__)
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("samples", help="tạo PDF mẫu để upload")
    s.add_argument("--out", type=Path, required=True)
    s.set_defaults(fn=cmd_samples)

    def common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--fixtures", type=Path, required=True, help="thư mục file mẫu để upload")

    g = sub.add_parser("generate", help="LLM sinh script, chạy thử, sửa lỗi")
    g.add_argument("brief", type=Path)
    common(g)
    g.add_argument("--scripts", type=Path, required=True, help="thư mục lưu script (cache)")
    g.add_argument("--regen", action="store_true", help="sinh lại dù đã có script")
    g.set_defaults(fn=cmd_generate)

    r = sub.add_parser("record", help="quay clip từ script đã có")
    r.add_argument("script", type=Path)
    common(r)
    r.add_argument("--out", type=Path, required=True)
    r.add_argument("--assets", type=Path, help="assets.json cần thêm/cập nhật asset")
    r.add_argument("--show", action="store_true", help="hiện cửa sổ trình duyệt")
    r.set_defaults(fn=cmd_record)

    u = sub.add_parser("run", help="generate (nếu thiếu) rồi record")
    u.add_argument("brief", type=Path)
    common(u)
    u.add_argument("--scripts", type=Path, required=True)
    u.add_argument("--out", type=Path, required=True)
    u.add_argument("--assets", type=Path)
    u.add_argument("--regen", action="store_true")
    u.add_argument("--show", action="store_true")
    u.set_defaults(fn=cmd_run)
    return ap


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    load_env(Path(".env"))
    a = _parser().parse_args(argv)
    try:
        return a.fn(a)
    except (DemoError, MissingConfigError) as ex:
        print(f"lỗi: {ex}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
