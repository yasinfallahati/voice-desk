from __future__ import annotations

import asyncio
import logging
import os

from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
)

from bot.config import load_settings
from bot import handlers
from bot.llm import OllamaClient
from bot.shortcuts import ShortcutStore


logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("conect")


def _fix_proxy_env() -> None:
    """httpx فقط socks5:// / socks4:// را می‌فهمد، نه socks://."""
    for key in (
        "ALL_PROXY",
        "all_proxy",
        "HTTPS_PROXY",
        "https_proxy",
        "HTTP_PROXY",
        "http_proxy",
    ):
        val = os.environ.get(key)
        if val and val.startswith("socks://"):
            os.environ[key] = "socks5://" + val[len("socks://") :]

    # مدل و API لوکال از پروکسی رد نشوند
    local = "127.0.0.1,localhost,::1"
    for key in ("NO_PROXY", "no_proxy"):
        cur = os.environ.get(key, "")
        parts = {p.strip() for p in cur.split(",") if p.strip()}
        parts.update(local.split(","))
        os.environ[key] = ",".join(sorted(parts))


def main() -> None:
    _fix_proxy_env()
    settings = load_settings()
    store = ShortcutStore(settings.shortcuts_path)
    llm = OllamaClient(settings.ollama_base_url, settings.ollama_model)

    app = Application.builder().token(settings.telegram_bot_token).build()
    app.bot_data["settings"] = settings
    app.bot_data["shortcuts"] = store
    app.bot_data["llm"] = llm
    app.bot_data["pending"] = {}
    app.bot_data["live_active"] = False
    app.bot_data["live_stop"] = False
    app.bot_data["live_task"] = None

    app.add_handler(CommandHandler("start", handlers.cmd_start))
    app.add_handler(CommandHandler("help", handlers.cmd_help))
    app.add_handler(CommandHandler("menu", handlers.cmd_menu))
    app.add_handler(CommandHandler("shortcuts", handlers.cmd_shortcuts))
    app.add_handler(CommandHandler("shot", handlers.cmd_shot))
    app.add_handler(CommandHandler("live", handlers.cmd_live))
    app.add_handler(CommandHandler("stoplive", handlers.cmd_stoplive))
    app.add_handler(CommandHandler("run", handlers.cmd_run))
    app.add_handler(CommandHandler("s", handlers.cmd_s))
    app.add_handler(CallbackQueryHandler(handlers.on_callback))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, handlers.on_voice))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.on_text))

    log.info(
        "Bot starting | model=%s | users=%s | shortcuts=%d",
        settings.ollama_model,
        sorted(settings.allowed_user_ids),
        len(store.names),
    )
    # Python 3.14 دیگر به صورت خودکار event loop نمی‌سازد
    asyncio.set_event_loop(asyncio.new_event_loop())
    app.run_polling(allowed_updates=["message", "callback_query"])


if __name__ == "__main__":
    main()
