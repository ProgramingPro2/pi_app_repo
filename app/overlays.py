"""
Overlay helpers for mode/status notifications.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import List, Tuple


@dataclass
class BannerMessage:
    text: str
    expires_at: float

    def alive(self) -> bool:
        return time.time() < self.expires_at


@dataclass
class BannerQueue:
    default_timeout: float = 2.0
    _messages: List[BannerMessage] = field(default_factory=list, init=False)

    def push(self, text: str, timeout: float | None = None) -> None:
        expiry = time.time() + (timeout if timeout is not None else self.default_timeout)
        self._messages.append(BannerMessage(text=text, expires_at=expiry))

    def active_messages(self) -> List[str]:
        now = time.time()
        self._messages = [msg for msg in self._messages if msg.expires_at > now]
        return [msg.text for msg in self._messages]


def format_status(
    mode_name: str,
    palette_name: str,
    temperature_unit: str,
    threshold: float | None = None,
) -> List[str]:
    parts: List[str] = [f"{mode_name} Mode", f"Palette {palette_name}"]
    if threshold is not None:
        parts.append(f"Target {threshold:.1f}°{temperature_unit}")
    return parts

