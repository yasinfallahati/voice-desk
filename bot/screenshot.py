from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path


def take_screenshot(out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = out_dir / f"shot-{stamp}.png"

    env = {
        **dict(**{k: v for k, v in __import__("os").environ.items()}),
    }
    env.setdefault("DISPLAY", ":0")
    env.setdefault("WAYLAND_DISPLAY", "wayland-0")
    env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{__import__('os').getuid()}")

    errors: list[str] = []

    # 1) grim (Wayland)
    if shutil.which("grim"):
        r = subprocess.run(
            ["grim", str(path)], capture_output=True, text=True, env=env
        )
        if r.returncode == 0 and path.exists():
            return path
        errors.append(f"grim: {r.stderr.strip() or r.stdout.strip()}")

    # 2) gnome-screenshot
    if shutil.which("gnome-screenshot"):
        r = subprocess.run(
            ["gnome-screenshot", "-f", str(path)],
            capture_output=True,
            text=True,
            env=env,
        )
        if r.returncode == 0 and path.exists():
            return path
        errors.append(f"gnome-screenshot: {r.stderr.strip() or r.stdout.strip()}")

    # 3) ImageMagick import (X11)
    if shutil.which("import"):
        r = subprocess.run(
            ["import", "-window", "root", str(path)],
            capture_output=True,
            text=True,
            env=env,
        )
        if r.returncode == 0 and path.exists():
            return path
        errors.append(f"import: {r.stderr.strip() or r.stdout.strip()}")

    # 4) scrot
    if shutil.which("scrot"):
        r = subprocess.run(
            ["scrot", str(path)], capture_output=True, text=True, env=env
        )
        if r.returncode == 0 and path.exists():
            return path
        errors.append(f"scrot: {r.stderr.strip() or r.stdout.strip()}")

    raise RuntimeError(
        "اسکرین‌شات گرفته نشد. روی Wayland معمولاً `sudo apt install grim` کافیست.\n"
        + "\n".join(errors)
    )
