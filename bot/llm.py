from __future__ import annotations

import json
import re
from dataclasses import dataclass

import httpx


SYSTEM_PROMPT = """تو یک دستیار لینوکس هستی که فقط یک دستور bash خروجی می‌دهی.
قوانین:
- فقط یک خط دستور bash برگردان، بدون توضیح و بدون markdown.
- اگر ورودی فارسی است، منظور کاربر را به دستور لینوکس ترجمه کن.
- دستور باید امن و غیرمخرب باشد؛ از rm -rf روی روت، mkfs، dd روی دیسک، shutdown/reboot خودداری کن مگر کاربر صریحاً بخواهد.
- اگر درخواست مبهم است، یک دستور تشخیصی امن پیشنهاد بده (مثل ls یا systemctl status).
- خروجی فقط JSON با این شکل:
{"cmd":"...","explain":"..."}
"""


@dataclass
class Plan:
    cmd: str
    explain: str


class OllamaClient:
    def __init__(self, base_url: str, model: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.model = model

    async def plan_command(self, user_text: str) -> Plan:
        payload = {
            "model": self.model,
            "stream": False,
            "format": "json",
            "options": {"temperature": 0.1},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": f"درخواست کاربر:\n{user_text}\n\nفقط JSON برگردان.",
                },
            ],
        }
        async with httpx.AsyncClient(timeout=120.0) as client:
            r = await client.post(f"{self.base_url}/api/chat", json=payload)
            r.raise_for_status()
            data = r.json()

        content = (data.get("message") or {}).get("content") or ""
        return _parse_plan(content, fallback_text=user_text)


def _parse_plan(content: str, fallback_text: str) -> Plan:
    content = content.strip()
    try:
        obj = json.loads(content)
        cmd = str(obj.get("cmd") or "").strip()
        explain = str(obj.get("explain") or "").strip()
        if cmd:
            return Plan(cmd=cmd, explain=explain or "دستور پیشنهادی مدل")
    except json.JSONDecodeError:
        pass

    # اگر مدل خارج از JSON جواب داد
    m = re.search(r"\{.*\}", content, flags=re.DOTALL)
    if m:
        try:
            obj = json.loads(m.group(0))
            cmd = str(obj.get("cmd") or "").strip()
            if cmd:
                return Plan(
                    cmd=cmd,
                    explain=str(obj.get("explain") or "دستور پیشنهادی مدل").strip(),
                )
        except json.JSONDecodeError:
            pass

    # آخرین تلاش: خطی که شبیه دستور است
    for line in content.splitlines():
        line = line.strip().strip("`")
        if not line or line.startswith("{"):
            continue
        if " " in line or line.startswith(
            ("ls", "cd", "cat", "df", "ps", "ip", "systemctl", "free", "uptime")
        ):
            return Plan(cmd=line, explain="استخراج خام از خروجی مدل")

    raise ValueError(f"نتوانستم دستور معتبری از مدل بگیرم.\nخروجی:\n{content[:500]}")
