from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / ".env")


def _csv_ints(value: str) -> set[int]:
    out: set[int] = set()
    for part in (value or "").split(","):
        part = part.strip()
        if part.isdigit():
            out.add(int(part))
    return out


@dataclass(frozen=True)
class Settings:
    telegram_bot_token: str
    allowed_user_ids: set[int]
    ollama_base_url: str
    ollama_model: str
    whisper_model: str
    whisper_language: str
    command_timeout: int
    auto_execute_llm: bool
    temp_dir: Path
    shortcuts_path: Path


def load_settings() -> Settings:
    token = os.getenv("TELEGRAM_BOT_TOKEN", "").strip()
    if not token or token.startswith("123456"):
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN را در فایل .env تنظیم کن (از @BotFather)."
        )

    allowed = _csv_ints(os.getenv("ALLOWED_USER_IDS", ""))
    if not allowed:
        raise RuntimeError(
            "ALLOWED_USER_IDS را در .env بگذار (یوزرآیدی عددی تلگرام خودت)."
        )

    temp = Path(os.getenv("TEMP_DIR", "/tmp/conect-bot"))
    temp.mkdir(parents=True, exist_ok=True)

    return Settings(
        telegram_bot_token=token,
        allowed_user_ids=allowed,
        ollama_base_url=os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip(
            "/"
        ),
        ollama_model=os.getenv("OLLAMA_MODEL", "qwen2.5:7b"),
        whisper_model=os.getenv("WHISPER_MODEL", "base"),
        whisper_language=os.getenv("WHISPER_LANGUAGE", "fa"),
        command_timeout=int(os.getenv("COMMAND_TIMEOUT", "60")),
        auto_execute_llm=os.getenv("AUTO_EXECUTE_LLM", "false").lower()
        in {"1", "true", "yes"},
        temp_dir=temp,
        shortcuts_path=ROOT / "shortcuts.yaml",
    )
