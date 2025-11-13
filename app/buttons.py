"""
GPIO button handling for Raspberry Pi with graceful degradation when developing on a PC.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Optional

try:
    from gpiozero import Button  # type: ignore
except ImportError:  # pragma: no cover - development machines without gpiozero
    Button = None  # type: ignore


ButtonCallback = Callable[[], None]


@dataclass
class ButtonSpec:
    name: str
    pin: int
    on_press: ButtonCallback
    hold_time: float = 0.0
    hold_action: Optional[ButtonCallback] = None


@dataclass
class ButtonController:
    """
    Manages GPIO buttons, debouncing, and callback dispatch.
    """

    specs: Dict[str, ButtonSpec]
    _buttons: Dict[str, object] = field(default_factory=dict, init=False)

    def setup(self) -> None:
        if Button is None:
            return

        for key, spec in self.specs.items():
            try:
                btn = Button(spec.pin, pull_up=True, bounce_time=0.05)
                btn.when_pressed = spec.on_press
                if spec.hold_time and spec.hold_action:
                    btn.hold_time = spec.hold_time
                    btn.when_held = spec.hold_action
                self._buttons[key] = btn
            except (OSError, FileNotFoundError, KeyError, RuntimeError):
                # GPIO not available (e.g., running on non-Pi system)
                # Silently skip button setup - application can run without buttons
                pass

    def close(self) -> None:
        for btn in self._buttons.values():
            try:
                btn.close()
            except Exception:
                pass
        self._buttons.clear()

