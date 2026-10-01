from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import yaml


@dataclass(frozen=True)
class Shortcut:
    name: str
    cmd: str
    desc: str = ""
    dangerous: bool = False


class ShortcutStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self._items: dict[str, Shortcut] = {}
        self.reload()

    def reload(self) -> None:
        raw = yaml.safe_load(self.path.read_text(encoding="utf-8")) or {}
        data = raw.get("shortcuts") or {}
        items: dict[str, Shortcut] = {}
        for name, meta in data.items():
            if isinstance(meta, str):
                items[name] = Shortcut(name=name, cmd=meta)
            else:
                items[name] = Shortcut(
                    name=name,
                    cmd=str(meta.get("cmd", "")).strip(),
                    desc=str(meta.get("desc", "")).strip(),
                    dangerous=bool(meta.get("dangerous", False)),
                )
        self._items = {k: v for k, v in items.items() if v.cmd}

    def get(self, text: str) -> Shortcut | None:
        key = text.strip()
        if key in self._items:
            return self._items[key]
        # بدون فاصله/خط تیره هم match کن
        normalized = key.replace(" ", "").replace("-", "").replace("_", "")
        for name, sc in self._items.items():
            n2 = name.replace(" ", "").replace("-", "").replace("_", "")
            if n2 == normalized:
                return sc
        return None

    def list_text(self) -> str:
        lines = ["میانبرهای تعریف‌شده:", ""]
        for name, sc in self._items.items():
            danger = " ⚠️" if sc.dangerous else ""
            desc = f" — {sc.desc}" if sc.desc else ""
            lines.append(f"• `{name}`{danger}{desc}")
        lines.append("")
        lines.append("ارسال نام میانبر، یا `/s نام`")
        return "\n".join(lines)

    @property
    def names(self) -> list[str]:
        return list(self._items.keys())
