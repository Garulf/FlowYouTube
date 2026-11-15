"""Render the README screenshots and hero image with flow-render.

Usage (from the repo root, with uv installed):

    python docs/screenshots/render.py

flow-render is run through ``uvx --from flow-render==0.15.0``. Each
``<shot>.json`` is a flow-render config whose results give a ``thumb`` gradient
instead of an image ``icon``, so the screenshots use made-up video thumbnails.
"""
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SHOTS_DIR = ROOT / "docs" / "screenshots"
ASSETS_DIR = ROOT / ".github" / "assets"
FLOW_RENDER = ["uvx", "--from", "flow-render==0.15.0", "flow-render"]
THEMES = ["dark", "light"]
HERO = {"shot": "hero", "theme": "dark", "css": ["win11-dark.css", "docs/screenshots/hero.css"]}

THUMB_SVG = """<svg xmlns="http://www.w3.org/2000/svg" width="160" height="90" viewBox="0 0 160 90">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
<stop offset="0" stop-color="{start}"/><stop offset="1" stop-color="{end}"/></linearGradient></defs>
<rect width="160" height="90" rx="10" fill="url(#g)"/>
<path d="M68 31 L96 45 L68 59 Z" fill="#FFFFFF" fill-opacity="0.9"/>
</svg>
"""


def thumbnail(colors, out_dir: Path) -> Path:
    start, end = colors
    path = out_dir / f"thumb-{start.lstrip('#')}-{end.lstrip('#')}.svg"
    path.write_text(THUMB_SVG.format(start=start, end=end), encoding="utf-8")
    return path


def flow_render(args, out_path: Path) -> None:
    with tempfile.TemporaryDirectory() as out_dir:
        subprocess.run([*FLOW_RENDER, *args, "-o", out_dir], check=True, cwd=ROOT)
        (rendered,) = Path(out_dir).glob("*.png")
        shutil.move(str(rendered), out_path)
    print(f"Wrote {out_path}")


def render_config(shot: str, css, out_path: Path, work: Path) -> None:
    config = json.loads((SHOTS_DIR / f"{shot}.json").read_text(encoding="utf-8"))
    config["icon"] = str((SHOTS_DIR / config["icon"]).resolve())
    for result in config["results"]:
        result["icon"] = str(thumbnail(result.pop("thumb"), work))
    config["css"] = css
    config_path = work / f"{shot}-{out_path.stem}.json"
    config_path.write_text(json.dumps(config), encoding="utf-8")
    flow_render(["-c", str(config_path)], out_path)


def main() -> None:
    shots = sorted(path.stem for path in SHOTS_DIR.glob("*.json") if path.stem != HERO["shot"])
    ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        work = Path(tmp)
        for shot in shots:
            for theme in THEMES:
                render_config(shot, f"win11-{theme}.css", ASSETS_DIR / f"{shot}-{theme}.png", work)
        render_config(HERO["shot"], HERO["css"], ASSETS_DIR / "hero.png", work)

        package = subprocess.run([str(ROOT / "scripts" / "package.sh"), str(work / "dist")], check=True, capture_output=True, text=True)
        plugin_zip = package.stdout.strip().splitlines()[-1]
        for theme in THEMES:
            flow_render(["-u", plugin_zip, "-i", "-s", f"win11-{theme}", "--hide-caret"], ASSETS_DIR / f"install-{theme}.png")


if __name__ == "__main__":
    sys.exit(main())
