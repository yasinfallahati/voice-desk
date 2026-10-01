from __future__ import annotations

from telegram import KeyboardButton, ReplyKeyboardMarkup

# برچسب دکمه‌ها — باید با handler یکی باشد
BTN_SHUTDOWN = "⏻ خاموش"
BTN_SHOT = "📸 اسکرین"
BTN_LIVE = "📺 لایو صفحه"
BTN_LIVE_STOP = "⏹ توقف لایو"
BTN_CURSOR = "🖥 Cursor"
BTN_CHROME = "🌐 Chrome"
BTN_VPN = "🛡 فیلترشکن"
BTN_SEARCH = "🔎 جستجو Chrome"
BTN_STATUS = "📊 وضعیت"
BTN_LOCK = "🔒 قفل"
BTN_TERMINAL = "💻 ترمینال"
BTN_BATTERY = "🔋 باتری"
BTN_MENU = "📋 منو"

MENU_LABELS = {
    BTN_SHUTDOWN,
    BTN_SHOT,
    BTN_LIVE,
    BTN_LIVE_STOP,
    BTN_CURSOR,
    BTN_CHROME,
    BTN_VPN,
    BTN_SEARCH,
    BTN_STATUS,
    BTN_LOCK,
    BTN_TERMINAL,
    BTN_BATTERY,
    BTN_MENU,
}


def main_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        [
            [KeyboardButton(BTN_SHOT), KeyboardButton(BTN_LIVE)],
            [KeyboardButton(BTN_LIVE_STOP), KeyboardButton(BTN_STATUS)],
            [KeyboardButton(BTN_CURSOR), KeyboardButton(BTN_CHROME)],
            [KeyboardButton(BTN_VPN), KeyboardButton(BTN_SEARCH)],
            [KeyboardButton(BTN_LOCK), KeyboardButton(BTN_TERMINAL)],
            [KeyboardButton(BTN_BATTERY), KeyboardButton(BTN_SHUTDOWN)],
            [KeyboardButton(BTN_MENU)],
        ],
        resize_keyboard=True,
        is_persistent=True,
    )


# دستورهای shell مربوط به هر دکمه (جستجو جداست)
BUTTON_ACTIONS: dict[str, dict] = {
    BTN_CURSOR: {
        "cmd": "nohup cursor >/dev/null 2>&1 & echo 'Cursor opened'",
        "explain": "باز کردن Cursor",
        "confirm": False,
        "shot": False,
    },
    BTN_CHROME: {
        "cmd": "nohup google-chrome-stable >/dev/null 2>&1 & echo 'Chrome opened'",
        "explain": "باز کردن Chrome",
        "confirm": False,
        "shot": False,
    },
    BTN_VPN: {
        "cmd": (
            "if ss -ltn 2>/dev/null | grep -q ':10808'; then "
            "echo 'فیلترشکن از قبل روشنه (پورت 10808)'; "
            "else "
            "nohup v2rayn >/dev/null 2>&1 & sleep 2; "
            "if ss -ltn 2>/dev/null | grep -q ':10808'; then echo 'v2rayN شروع شد'; "
            "else echo 'v2rayN اجرا شد — چند ثانیه صبر کن تا پروکسی بالا بیاید'; fi; "
            "fi"
        ),
        "explain": "روشن کردن فیلترشکن (v2rayN)",
        "confirm": False,
        "shot": False,
    },
    BTN_STATUS: {
        "cmd": (
            "uptime; echo '---'; free -h; echo '---'; "
            "df -h / /home 2>/dev/null; echo '---'; "
            "sensors 2>/dev/null || echo 'sensors N/A'"
        ),
        "explain": "وضعیت سیستم",
        "confirm": False,
        "shot": False,
    },
    BTN_LOCK: {
        "cmd": (
            "loginctl lock-session 2>/dev/null "
            "|| gnome-screensaver-command -l 2>/dev/null "
            "|| qdbus org.freedesktop.ScreenSaver /ScreenSaver Lock 2>/dev/null; "
            "echo locked"
        ),
        "explain": "قفل صفحه",
        "confirm": False,
        "shot": False,
    },
    BTN_TERMINAL: {
        "cmd": (
            "nohup gnome-terminal >/dev/null 2>&1 "
            "|| nohup kitty >/dev/null 2>&1 "
            "|| nohup xdg-terminal >/dev/null 2>&1 & "
            "echo 'terminal started'"
        ),
        "explain": "باز کردن ترمینال",
        "confirm": False,
        "shot": False,
    },
    BTN_BATTERY: {
        "cmd": (
            "upower -i $(upower -e | grep BAT) 2>/dev/null "
            "| grep -E 'state|percentage|time' "
            "|| cat /sys/class/power_supply/BAT*/uevent 2>/dev/null "
            "| grep -E 'STATUS|CAPACITY'"
        ),
        "explain": "وضعیت باتری",
        "confirm": False,
        "shot": False,
    },
    BTN_SHUTDOWN: {
        "cmd": "systemctl poweroff",
        "explain": "خاموش کردن سیستم",
        "confirm": True,
        "shot": False,
        "dangerous": True,
    },
}


def chrome_search_cmd(query: str) -> str:
    from urllib.parse import quote_plus

    q = quote_plus(query.strip())
    url = f"https://www.google.com/search?q={q}"
    # اگر بعداً سایت دیگه‌ای خواستی، همین URL را عوض کن
    return (
        f'nohup google-chrome-stable {url!r} >/dev/null 2>&1 & '
        f'echo "Chrome search: {query.strip()}"'
    )
