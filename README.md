# Voice Desk — ربات تلگرام برای کنترل لینوکس

ویس / متن / میانبر → Whisper (محلی) → Ollama → اجرای دستور → خروجی + اسکرین‌شات در تلگرام.

## پیش‌نیاز

```bash
# ابزارها
sudo apt install -y ffmpeg grim   # grim برای اسکرین‌شات Wayland

# مدل متن (اگر نداری)
ollama pull qwen2.5:7b

# بات تلگرام
# 1) @BotFather → /newbot → توکن بگیر
# 2) @userinfobot → یوزرآیدی عددی خودت
```

## نصب و اجرا

```bash
cd ~/Desktop/conect
cp .env.example .env
nano .env   # توکن و ALLOWED_USER_IDS را پر کن

chmod +x run.sh
./run.sh
```

اولین بار `faster-whisper` مدل `base` را دانلود می‌کند (ممکن است چند دقیقه طول بکشد).

## استفاده در تلگرام

| کار | مثال |
|-----|------|
| میانبر | `وضعیت` یا `/s وضعیت` |
| لیست میانبرها | `/shortcuts` |
| متن آزاد | `حجم پوشه دانلود چقدره؟` → مدل دستور می‌سازد → تأیید → اجرا |
| ویس | ویس بفرست با همان مفهوم |
| دستور مستقیم | `/run df -h` |
| فقط اسکرین | `/shot` |

میانبرها در `shortcuts.yaml` تعریف می‌شوند — هر چی بخوای اضافه کن.

## امنیت (مهم)

- فقط `ALLOWED_USER_IDS` پاسخ می‌گیرند.
- دستورهای مدل به‌صورت پیش‌فرض **نیاز به تأیید** دارند (`AUTO_EXECUTE_LLM=false`).
- الگوهای خطرناک (`rm -rf /`, `mkfs`, `reboot`, …) همیشه تأیید می‌خواهند.
- این بات با دسترسی کاربر تو روی سیستم اجرا می‌شود؛ توکن را محرمانه نگه دار.

## سرویس systemd (اختیاری)

```bash
mkdir -p ~/.config/systemd/user
cat > ~/.config/systemd/user/conect-bot.service <<'EOF'
[Unit]
Description=Conect Telegram Linux Bot
After=network.target

[Service]
WorkingDirectory=%h/Desktop/conect
ExecStart=%h/Desktop/conect/run.sh
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
systemctl --user enable --now conect-bot.service
```
