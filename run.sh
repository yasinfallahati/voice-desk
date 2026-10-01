#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -U pip
  .venv/bin/pip install -r requirements.txt
fi

if [[ ! -f .env ]]; then
  echo "فایل .env نداری. اول:"
  echo "  cp .env.example .env"
  echo "بعد TELEGRAM_BOT_TOKEN و ALLOWED_USER_IDS را پر کن."
  exit 1
fi

# Ollama باید بالا باشد
if ! curl -sf http://127.0.0.1:11434/api/tags >/dev/null; then
  echo "Ollama در دسترس نیست. اجرا کن: ollama serve"
  exit 1
fi

# httpx اسکیمای socks:// را نمی‌شناسد؛ به socks5:// تبدیل کن
# (معمولاً از Clash / V2Ray روی 10808 می‌آید)
normalize_proxy() {
  local val="${1:-}"
  if [[ "$val" == socks://* ]]; then
    echo "socks5://${val#socks://}"
  else
    echo "$val"
  fi
}
for var in ALL_PROXY all_proxy HTTPS_PROXY https_proxy HTTP_PROXY http_proxy; do
  if [[ -n "${!var:-}" ]]; then
    export "$var=$(normalize_proxy "${!var}")"
  fi
done

# Ollama و سرویس‌های لوکال از پروکسی رد نشوند
export NO_PROXY="127.0.0.1,localhost,::1${NO_PROXY:+,$NO_PROXY}"
export no_proxy="$NO_PROXY"

export PYTHONPATH="$(pwd)"
exec .venv/bin/python -m bot.main
