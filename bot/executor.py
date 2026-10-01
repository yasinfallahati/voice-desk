from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass


DANGEROUS_PATTERNS = [
    r"\brm\s+(-[a-zA-Z]*f[a-zA-Z]*\s+)?(/|~|/home|/var|/usr|/etc)\b",
    r"\bmkfs\b",
    r"\bdd\s+.*\bof=/dev/",
    r"\b:(){ :\|:& };:\b",
    r"\bshutdown\b",
    r"\breboot\b",
    r"\bpoweroff\b",
    r"\bhalt\b",
    r"\binit\s+[06]\b",
    r">\s*/dev/sd",
    r"\bchmod\s+-R\s+777\s+/",
    r"\bchown\s+-R\s+.+\s+/",
    r"\bcurl\s+.+\|\s*(ba)?sh\b",
    r"\bwget\s+.+\|\s*(ba)?sh\b",
]


@dataclass
class RunResult:
    cmd: str
    exit_code: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def ok(self) -> bool:
        return self.exit_code == 0 and not self.timed_out

    def as_telegram_text(self, limit: int = 3500) -> str:
        parts = [f"$ {self.cmd}", f"exit={self.exit_code}"]
        if self.timed_out:
            parts.append("⏱️ timed out")
        out = (self.stdout or "").strip()
        err = (self.stderr or "").strip()
        if out:
            parts.append("--- stdout ---\n" + out)
        if err:
            parts.append("--- stderr ---\n" + err)
        if not out and not err:
            parts.append("(بدون خروجی)")
        text = "\n".join(parts)
        if len(text) > limit:
            text = text[: limit - 20] + "\n…(truncated)"
        return f"```\n{text}\n```"


def looks_dangerous(cmd: str) -> bool:
    for pat in DANGEROUS_PATTERNS:
        if re.search(pat, cmd, flags=re.IGNORECASE):
            return True
    return False


def run_shell(cmd: str, timeout: int = 60, cwd: str | None = None) -> RunResult:
    env = os.environ.copy()
    # برای اپ‌های گرافیکی از همان سشن کاربر
    env.setdefault("DISPLAY", ":0")
    env.setdefault("WAYLAND_DISPLAY", "wayland-0")
    env.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")

    try:
        proc = subprocess.run(
            ["bash", "-lc", cmd],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd or os.path.expanduser("~"),
            env=env,
        )
        return RunResult(
            cmd=cmd,
            exit_code=proc.returncode,
            stdout=proc.stdout,
            stderr=proc.stderr,
        )
    except subprocess.TimeoutExpired as exc:
        return RunResult(
            cmd=cmd,
            exit_code=-1,
            stdout=(exc.stdout or b"").decode("utf-8", "replace")
            if isinstance(exc.stdout, bytes)
            else (exc.stdout or ""),
            stderr=(exc.stderr or b"").decode("utf-8", "replace")
            if isinstance(exc.stderr, bytes)
            else (exc.stderr or "timeout"),
            timed_out=True,
        )
