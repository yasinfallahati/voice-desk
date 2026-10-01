from __future__ import annotations

import asyncio
import logging
import secrets
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, InputMediaPhoto, Update
from telegram.ext import ContextTypes

from bot.config import Settings
from bot.executor import looks_dangerous, run_shell
from bot.llm import OllamaClient
from bot.menu import (
    BTN_LIVE,
    BTN_LIVE_STOP,
    BTN_MENU,
    BTN_SEARCH,
    BTN_SHOT,
    BUTTON_ACTIONS,
    MENU_LABELS,
    chrome_search_cmd,
    main_keyboard,
)
from bot.screenshot import take_screenshot
from bot.shortcuts import ShortcutStore
from bot.stt import ogg_to_wav, transcribe

log = logging.getLogger(__name__)


def _authorized(update: Update, settings: Settings) -> bool:
    user = update.effective_user
    return bool(user and user.id in settings.allowed_user_ids)


async def _deny(update: Update) -> None:
    if update.effective_message:
        await update.effective_message.reply_text("⛔️ دسترسی نداری.")


def _confirm_keyboard(token: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("✅ اجرا", callback_data=f"run:{token}"),
                InlineKeyboardButton("❌ لغو", callback_data=f"cancel:{token}"),
            ]
        ]
    )


async def _send_shot(message, settings: Settings) -> None:
    try:
        shot = take_screenshot(settings.temp_dir)
        with shot.open("rb") as f:
            await message.reply_photo(photo=f, caption="اسکرین‌شات سیستم")
        shot.unlink(missing_ok=True)
    except Exception as exc:
        await message.reply_text(f"اسکرین‌شات نشد: {exc}")


async def _live_loop(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    interval: float = 3.0,
    max_frames: int = 40,
) -> None:
    """اسکرین را هر چند ثانیه آپدیت می‌کند (همان پیام)."""
    settings: Settings = context.bot_data["settings"]
    bot = context.bot
    photo_msg = None
    status_msg = None
    try:
        status_msg = await bot.send_message(
            chat_id,
            f"📺 لایو شروع شد — هر {interval:.0f} ثانیه آپدیت.\n"
            f"حداکثر حدود {int(max_frames * interval / 60)} دقیقه.\n"
            f"برای قطع: {BTN_LIVE_STOP}",
            reply_markup=main_keyboard(),
        )
        for i in range(1, max_frames + 1):
            if context.bot_data.get("live_stop"):
                break
            try:
                shot = await asyncio.to_thread(take_screenshot, settings.temp_dir)
                caption = f"📺 لایو #{i}"
                with shot.open("rb") as f:
                    if photo_msg is None:
                        photo_msg = await bot.send_photo(
                            chat_id, photo=f, caption=caption
                        )
                    else:
                        await photo_msg.edit_media(
                            media=InputMediaPhoto(media=f, caption=caption)
                        )
                shot.unlink(missing_ok=True)
            except Exception as exc:
                log.warning("live frame failed: %s", exc)
                await bot.send_message(chat_id, f"فریم لایو خطا: {exc}")
                break
            await asyncio.sleep(interval)
    finally:
        context.bot_data["live_active"] = False
        context.bot_data["live_task"] = None
        try:
            if status_msg:
                await status_msg.edit_text("⏹ لایو متوقف شد.")
        except Exception:
            await bot.send_message(chat_id, "⏹ لایو متوقف شد.")


async def _start_live(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.bot_data.get("live_active"):
        await update.effective_message.reply_text(
            "لایو از قبل روشنه. برای قطع: ⏹ توقف لایو"
        )
        return
    context.bot_data["live_stop"] = False
    context.bot_data["live_active"] = True
    task = asyncio.create_task(
        _live_loop(context, update.effective_chat.id),
        name="conect-live-view",
    )
    context.bot_data["live_task"] = task


async def _stop_live(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not context.bot_data.get("live_active"):
        await update.effective_message.reply_text("لایوی در حال اجرا نیست.")
        return
    context.bot_data["live_stop"] = True
    await update.effective_message.reply_text("⏹ دارم لایو را قطع می‌کنم…")


async def _show_menu(update: Update, text: str | None = None) -> None:
    await update.effective_message.reply_text(
        text
        or (
            "منوی سریع آماده است.\n"
            "دکمه‌ها را بزن، یا متن/ویس آزاد بفرست.\n\n"
            "🔎 جستجو Chrome → اول می‌پرسد چی سرچ کنی، بعد کروم را با گوگل باز می‌کند."
        ),
        reply_markup=main_keyboard(),
    )


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    if not _authorized(update, settings):
        await _deny(update)
        return
    context.user_data.pop("awaiting_search", None)
    await _show_menu(
        update,
        "سلام! به سیستم لینوکس‌ات وصل‌ام.\n"
        "از دکمه‌های پایین استفاده کن، یا متن/ویس بفرست.",
    )


async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await cmd_start(update, context)


async def cmd_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    if not _authorized(update, settings):
        await _deny(update)
        return
    context.user_data.pop("awaiting_search", None)
    await _show_menu(update)


async def cmd_shortcuts(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    store: ShortcutStore = context.bot_data["shortcuts"]
    if not _authorized(update, settings):
        await _deny(update)
        return
    await update.effective_message.reply_text(
        store.list_text(), parse_mode="Markdown", reply_markup=main_keyboard()
    )


async def cmd_shot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    if not _authorized(update, settings):
        await _deny(update)
        return
    await update.effective_message.reply_text("📸 اسکرین‌شات:")
    await _send_shot(update.effective_message, settings)


async def cmd_live(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    if not _authorized(update, settings):
        await _deny(update)
        return
    await _start_live(update, context)


async def cmd_stoplive(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    if not _authorized(update, settings):
        await _deny(update)
        return
    await _stop_live(update, context)


async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    if not _authorized(update, settings):
        await _deny(update)
        return
    cmd = " ".join(context.args or []).strip()
    if not cmd:
        await update.effective_message.reply_text(
            "مثال: `/run df -h`", parse_mode="Markdown"
        )
        return
    await _queue_or_run(
        update, context, cmd, explain="دستور مستقیم", force_confirm=True
    )


async def cmd_s(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    store: ShortcutStore = context.bot_data["shortcuts"]
    if not _authorized(update, settings):
        await _deny(update)
        return
    name = " ".join(context.args or []).strip()
    if not name:
        await update.effective_message.reply_text(
            store.list_text(), parse_mode="Markdown"
        )
        return
    sc = store.get(name)
    if not sc:
        await update.effective_message.reply_text("میانبر پیدا نشد. `/shortcuts`")
        return
    await _queue_or_run(
        update,
        context,
        sc.cmd,
        explain=sc.desc or sc.name,
        force_confirm=sc.dangerous,
        is_shortcut=True,
    )


async def _handle_menu_button(
    update: Update, context: ContextTypes.DEFAULT_TYPE, text: str
) -> bool:
    """اگر متن یکی از دکمه‌های منو بود، True برمی‌گرداند."""
    if text not in MENU_LABELS:
        return False

    settings: Settings = context.bot_data["settings"]

    if text == BTN_MENU:
        context.user_data.pop("awaiting_search", None)
        await _show_menu(update)
        return True

    if text == BTN_SHOT:
        await update.effective_message.reply_text("📸 اسکرین‌شات:")
        await _send_shot(update.effective_message, settings)
        return True

    if text == BTN_LIVE:
        await _start_live(update, context)
        return True

    if text == BTN_LIVE_STOP:
        await _stop_live(update, context)
        return True

    if text == BTN_SEARCH:
        context.user_data["awaiting_search"] = True
        await update.effective_message.reply_text(
            "چی می‌خوای سرچ کنی؟\n"
            "متن یا ویس بفرست — بعد کروم با گوگل باز می‌شود.\n"
            "(برای لغو: /menu)",
            reply_markup=main_keyboard(),
        )
        return True

    action = BUTTON_ACTIONS.get(text)
    if not action:
        return True

    await _queue_or_run(
        update,
        context,
        action["cmd"],
        explain=action.get("explain", text),
        force_confirm=bool(action.get("confirm") or action.get("dangerous")),
        is_shortcut=True,
        with_shot=bool(action.get("shot", False)),
    )
    return True


async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    store: ShortcutStore = context.bot_data["shortcuts"]
    llm: OllamaClient = context.bot_data["llm"]
    if not _authorized(update, settings):
        await _deny(update)
        return

    text = (update.effective_message.text or "").strip()
    if not text:
        return

    # فلو جستجوی کروم
    if context.user_data.get("awaiting_search"):
        if text in MENU_LABELS:
            context.user_data.pop("awaiting_search", None)
            await _handle_menu_button(update, context, text)
            return
        context.user_data.pop("awaiting_search", None)
        cmd = chrome_search_cmd(text)
        await _queue_or_run(
            update,
            context,
            cmd,
            explain=f"جستجو در Chrome: {text}",
            force_confirm=False,
            is_shortcut=True,
            with_shot=False,
        )
        return

    if await _handle_menu_button(update, context, text):
        return

    sc = store.get(text)
    if sc:
        await _queue_or_run(
            update,
            context,
            sc.cmd,
            explain=sc.desc or sc.name,
            force_confirm=sc.dangerous,
            is_shortcut=True,
        )
        return

    await update.effective_message.reply_text("🧠 دارم با مدل محلی دستور می‌سازم…")
    try:
        plan = await llm.plan_command(text)
    except Exception as exc:
        await update.effective_message.reply_text(f"خطای مدل: {exc}")
        return

    await _queue_or_run(
        update,
        context,
        plan.cmd,
        explain=plan.explain,
        force_confirm=not settings.auto_execute_llm,
    )


async def on_voice(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    if not _authorized(update, settings):
        await _deny(update)
        return

    voice = update.effective_message.voice or update.effective_message.audio
    if not voice:
        return

    await update.effective_message.reply_text("🎙️ در حال تبدیل ویس به متن…")
    ogg = settings.temp_dir / f"voice-{voice.file_unique_id}.ogg"
    wav = settings.temp_dir / f"voice-{voice.file_unique_id}.wav"

    try:
        tg_file = await context.bot.get_file(voice.file_id)
        await tg_file.download_to_drive(custom_path=str(ogg))
        await asyncio.to_thread(ogg_to_wav, ogg, wav)
        text = await asyncio.to_thread(
            transcribe, wav, settings.whisper_model, settings.whisper_language
        )
    except Exception as exc:
        log.exception("STT failed")
        await update.effective_message.reply_text(f"خطای STT: {exc}")
        return
    finally:
        Path(ogg).unlink(missing_ok=True)
        Path(wav).unlink(missing_ok=True)

    if not text:
        await update.effective_message.reply_text("متنی از ویس استخراج نشد.")
        return

    await update.effective_message.reply_text(f"📝 تشخیص داده شد:\n{text}")

    # اگر منتظر عبارت جستجو هستیم
    if context.user_data.get("awaiting_search"):
        context.user_data.pop("awaiting_search", None)
        cmd = chrome_search_cmd(text)
        await _queue_or_run(
            update,
            context,
            cmd,
            explain=f"جستجو در Chrome: {text}",
            force_confirm=False,
            is_shortcut=True,
            with_shot=False,
        )
        return

    store: ShortcutStore = context.bot_data["shortcuts"]
    llm: OllamaClient = context.bot_data["llm"]

    if await _handle_menu_button(update, context, text):
        return

    sc = store.get(text)
    if sc:
        await _queue_or_run(
            update,
            context,
            sc.cmd,
            explain=sc.desc or sc.name,
            force_confirm=sc.dangerous,
            is_shortcut=True,
        )
        return

    await update.effective_message.reply_text("🧠 دارم با مدل محلی دستور می‌سازم…")
    try:
        plan = await llm.plan_command(text)
    except Exception as exc:
        await update.effective_message.reply_text(f"خطای مدل: {exc}")
        return

    await _queue_or_run(
        update,
        context,
        plan.cmd,
        explain=plan.explain,
        force_confirm=not settings.auto_execute_llm,
    )


async def on_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    settings: Settings = context.bot_data["settings"]
    q = update.callback_query
    if not q:
        return

    if not _authorized(update, settings):
        await q.answer("دسترسی نداری", show_alert=True)
        return

    await q.answer()
    data = q.data or ""
    action, _, token = data.partition(":")
    pending: dict = context.bot_data.setdefault("pending", {})
    item = pending.pop(token, None)
    if not item:
        await q.edit_message_text("این درخواست منقضی شده.")
        return

    if action == "cancel":
        await q.edit_message_text("❌ لغو شد.")
        return

    if action == "run":
        await q.edit_message_text(
            f"▶️ در حال اجرا:\n`{item['cmd']}`", parse_mode="Markdown"
        )
        result = await asyncio.to_thread(
            run_shell, item["cmd"], settings.command_timeout
        )
        await q.message.reply_text(result.as_telegram_text(), parse_mode="Markdown")
        if item.get("shot", True):
            await _send_shot(q.message, settings)


async def _queue_or_run(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    cmd: str,
    explain: str = "",
    force_confirm: bool = True,
    is_shortcut: bool = False,
    with_shot: bool = True,
) -> None:
    settings: Settings = context.bot_data["settings"]
    danger = looks_dangerous(cmd)
    need_confirm = force_confirm or danger

    prefix = "میانبر" if is_shortcut else "دستور"
    body = f"*{prefix}*\n"
    if explain:
        body += f"{explain}\n"
    body += f"```\n{cmd}\n```"
    if danger:
        body += "\n⚠️ این دستور بالقوه خطرناک به نظر می‌رسد."

    msg = update.effective_message
    if need_confirm:
        token = secrets.token_hex(8)
        pending: dict = context.bot_data.setdefault("pending", {})
        pending[token] = {"cmd": cmd, "shot": with_shot}
        await msg.reply_text(
            body + "\nتأیید می‌کنی؟",
            parse_mode="Markdown",
            reply_markup=_confirm_keyboard(token),
        )
        return

    await msg.reply_text(body + "\n▶️ در حال اجرا…", parse_mode="Markdown")
    result = await asyncio.to_thread(run_shell, cmd, settings.command_timeout)
    await msg.reply_text(result.as_telegram_text(), parse_mode="Markdown")
    if with_shot:
        await _send_shot(msg, settings)
