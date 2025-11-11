"""
Mode management for thermal viewer.
"""

from __future__ import annotations

import dataclasses
from typing import Callable, List, Optional, Sequence, Tuple

import numpy as np

from .processing import (
    COLORMAPS,
    TemperatureModel,
    compute_hotspots,
    highlight_threshold,
)


@dataclasses.dataclass
class ModeHooks:
    save_ffc: Callable[[np.ndarray], Optional[str]]
    reload_camera: Callable[[Optional[str]], None]


@dataclasses.dataclass
class ModeResult:
    status: List[str]
    highlight_mask: Optional[np.ndarray] = None
    banner: Optional[str] = None
    stats: Optional[dict] = None
    highlight_color: Optional[Tuple[int, int, int]] = None


class Mode:
    name = "Mode"

    def on_enter(self, state: "ModeState") -> ModeResult | None:
        return None  # pragma: no cover - default no-op

    def on_exit(self, state: "ModeState") -> None:  # pragma: no cover - default no-op
        return None

    def update(
        self,
        frame_raw: np.ndarray,
        frame_celsius: np.ndarray,
        state: "ModeState",
        temperature_model: TemperatureModel,
    ) -> ModeResult:
        raise NotImplementedError

    def on_button_up(self, state: "ModeState") -> Optional[str]:
        return None

    def on_button_down(self, state: "ModeState") -> Optional[str]:
        return None

    def on_mode_button(self, state: "ModeState") -> tuple[bool, Optional[str]]:
        return False, None


class LiveHighlightMode(Mode):
    name = "Live"

    def update(
        self,
        frame_raw: np.ndarray,
        frame_celsius: np.ndarray,
        state: "ModeState",
        temperature_model: TemperatureModel,
    ) -> ModeResult:
        stats_c = compute_hotspots(frame_celsius)
        stats = state.stats_to_display(stats_c)
        mask = highlight_threshold(frame_celsius, state.threshold_c, state.threshold_mode)
        status = [
            f"Highlight {state.threshold_mode}",
            f"AEL {'ON' if state.auto_exposure_lock else 'OFF'}",
        ]
        return ModeResult(
            status=status,
            highlight_mask=mask,
            stats=stats,
            highlight_color=state.highlight_color(),
        )

    def on_button_up(self, state: "ModeState") -> Optional[str]:
        state.adjust_threshold_display(state.threshold_step)
        return f"Threshold {state.threshold_display:.1f}°{state.temperature_unit} ({state.threshold_mode})"

    def on_button_down(self, state: "ModeState") -> Optional[str]:
        state.adjust_threshold_display(-state.threshold_step)
        return f"Threshold {state.threshold_display:.1f}°{state.temperature_unit} ({state.threshold_mode})"

    def on_mode_button(self, state: "ModeState") -> tuple[bool, Optional[str]]:
        state.cycle_threshold_mode()
        return True, f"Highlight {state.threshold_mode}"


class PaletteMode(Mode):
    name = "Palette"

    def update(
        self,
        frame_raw: np.ndarray,
        frame_celsius: np.ndarray,
        state: "ModeState",
        temperature_model: TemperatureModel,
    ) -> ModeResult:
        stats = state.stats_to_display(compute_hotspots(frame_celsius))
        status = ["UP/DOWN change palette"]
        return ModeResult(status=status, stats=stats)

    def on_button_up(self, state: "ModeState") -> Optional[str]:
        state.increment_palette()
        return f"Palette {state.palette_name}"

    def on_button_down(self, state: "ModeState") -> Optional[str]:
        state.decrement_palette()
        return f"Palette {state.palette_name}"


class FlatFieldCalibrationMode(Mode):
    name = "FFC"

    def __init__(self, hooks: ModeHooks, frames_to_average: int = 60) -> None:
        self.hooks = hooks
        self.frames_to_average = frames_to_average
        self._capturing = False
        self._accumulator: Optional[np.ndarray] = None
        self._captured = 0

    def on_enter(self, state: "ModeState") -> ModeResult:
        self._capturing = False
        self._accumulator = None
        self._captured = 0
        return ModeResult(status=["Cover lens, press UP to start capture"])

    def on_button_up(self, state: "ModeState") -> Optional[str]:
        if not self._capturing:
            self._capturing = True
            self._accumulator = None
            self._captured = 0
            return "Capturing flat field..."
        return None

    def update(
        self,
        frame_raw: np.ndarray,
        frame_celsius: np.ndarray,
        state: "ModeState",
        temperature_model: TemperatureModel,
    ) -> ModeResult:
        status: List[str] = []
        banner: Optional[str] = None

        if self._capturing:
            if self._accumulator is None:
                self._accumulator = np.zeros_like(frame_raw, dtype=np.float32)
            self._accumulator += frame_raw.astype(np.float32)
            self._captured += 1
            status.append(f"Capturing frame {self._captured}/{self.frames_to_average}")

            if self._captured >= self.frames_to_average:
                average = (self._accumulator / float(self._captured)).astype(np.uint16)
                path = self.hooks.save_ffc(average)
                if path:
                    state.ff_last_saved = path
                    banner = f"FFC saved: {path}"
                    self.hooks.reload_camera(path)
                else:
                    banner = "FFC save failed"
                self._capturing = False
                self._accumulator = None
                self._captured = 0
        else:
            status.append("Press UP to capture calibration")
            if state.ff_last_saved:
                status.append("Latest FFC loaded")

        return ModeResult(status=status, banner=banner)


class HotColdMode(Mode):
    name = "Hot/Cold"

    def update(
        self,
        frame_raw: np.ndarray,
        frame_celsius: np.ndarray,
        state: "ModeState",
        temperature_model: TemperatureModel,
    ) -> ModeResult:
        stats_c = compute_hotspots(frame_celsius)
        stats = state.stats_to_display(stats_c)
        hot = stats["max"][0]
        cold = stats["min"][0]
        delta = hot - cold
        status = [
            f"Hot {hot:.1f}°{state.temperature_unit}",
            f"Cold {cold:.1f}°{state.temperature_unit}",
            f"Δ {delta:.1f}°{state.temperature_unit}",
        ]
        # Highlight top and bottom 2% pixels
        high_thresh = np.percentile(frame_celsius, 98)
        low_thresh = np.percentile(frame_celsius, 2)
        mask = np.logical_or(frame_celsius >= high_thresh, frame_celsius <= low_thresh)
        return ModeResult(
            status=status,
            highlight_mask=mask,
            stats=stats,
            highlight_color=(255, 140, 0),
        )


@dataclasses.dataclass
class SettingItem:
    label: str
    action: Callable[["ModeState"], Optional[str]]


class SettingsMode(Mode):
    name = "Settings"

    def __init__(self) -> None:
        self.items: List[SettingItem] = [
            SettingItem("Toggle AEL", self._toggle_ael),
            SettingItem("Units °C/°F", self._toggle_units),
            SettingItem("Cycle Highlight", self._cycle_highlight),
            SettingItem("Reset Threshold", self._reset_threshold),
        ]

    def _toggle_ael(self, state: "ModeState") -> Optional[str]:
        state.auto_exposure_lock = not state.auto_exposure_lock
        return f"AEL {'ON' if state.auto_exposure_lock else 'OFF'}"

    def _toggle_units(self, state: "ModeState") -> Optional[str]:
        state.toggle_temperature_unit()
        return f"Units °{state.temperature_unit}"

    def _cycle_highlight(self, state: "ModeState") -> Optional[str]:
        state.cycle_threshold_mode()
        return f"Highlight {state.threshold_mode}"

    def _reset_threshold(self, state: "ModeState") -> Optional[str]:
        state.set_threshold_to_default()
        return f"Threshold {state.threshold_display:.1f}°{state.temperature_unit}"

    def update(
        self,
        frame_raw: np.ndarray,
        frame_celsius: np.ndarray,
        state: "ModeState",
        temperature_model: TemperatureModel,
    ) -> ModeResult:
        status = ["MODE to activate"]
        for idx, item in enumerate(self.items):
            prefix = ">" if idx == state.settings_index else " "
            status.append(f"{prefix} {item.label}")
        return ModeResult(status=status)

    def on_button_up(self, state: "ModeState") -> Optional[str]:
        state.settings_index = (state.settings_index + 1) % len(self.items)
        return None

    def on_button_down(self, state: "ModeState") -> Optional[str]:
        state.settings_index = (state.settings_index - 1) % len(self.items)
        return None

    def on_mode_button(self, state: "ModeState") -> tuple[bool, Optional[str]]:
        item = self.items[state.settings_index]
        message = item.action(state)
        return True, message


@dataclasses.dataclass
class ModeState:
    palette_idx: int = 0
    palette_names: Sequence[str] = dataclasses.field(default_factory=list)
    threshold_c: float = 30.0
    threshold_mode: str = ">"
    auto_exposure_lock: bool = False
    threshold_floor: float = -20.0
    threshold_ceiling: float = 120.0
    settings_index: int = 0
    ff_path_dir: Optional[str] = None
    ff_basename: str = "flat_field.png"
    ff_last_saved: Optional[str] = None
    _threshold_modes: Sequence[str] = (">", "<", "=")
    temperature_unit: str = "C"
    default_threshold_c: float = 30.0
    default_threshold_f: float = 86.0

    @property
    def palette_name(self) -> str:
        if not self.palette_names:
            return f"#{self.palette_idx}"
        return self.palette_names[self.palette_idx % len(self.palette_names)]

    @property
    def threshold_display(self) -> float:
        return self.convert_c_to_display(self.threshold_c)

    @property
    def default_threshold_display(self) -> float:
        if self.temperature_unit == "C":
            return self.convert_c_to_display(self.default_threshold_c)
        return self.default_threshold_f

    @property
    def threshold_step(self) -> float:
        return 0.5 if self.temperature_unit == "C" else 1.0

    def increment_palette(self) -> None:
        if not self.palette_names:
            return
        self.palette_idx = (self.palette_idx + 1) % len(self.palette_names)

    def decrement_palette(self) -> None:
        if not self.palette_names:
            return
        self.palette_idx = (self.palette_idx - 1) % len(self.palette_names)

    def cycle_threshold_mode(self) -> None:
        idx = self._threshold_modes.index(self.threshold_mode)
        idx = (idx + 1) % len(self._threshold_modes)
        self.threshold_mode = self._threshold_modes[idx]

    def convert_c_to_display(self, value: float) -> float:
        return value if self.temperature_unit == "C" else value * 9.0 / 5.0 + 32.0

    def convert_display_to_c(self, value: float) -> float:
        return value if self.temperature_unit == "C" else (value - 32.0) * 5.0 / 9.0

    def adjust_threshold_display(self, delta_display: float) -> None:
        new_display = self.threshold_display + delta_display
        new_c = self.convert_display_to_c(new_display)
        new_c = max(min(new_c, self.threshold_ceiling), self.threshold_floor)
        self.threshold_c = new_c

    def toggle_temperature_unit(self) -> None:
        self.temperature_unit = "F" if self.temperature_unit == "C" else "C"

    def stats_to_display(self, stats: dict) -> dict:
        converted = {}
        for key, (value, coords) in stats.items():
            converted[key] = (self.convert_c_to_display(value), coords)
        return converted

    def set_threshold_to_default(self) -> None:
        if self.temperature_unit == "C":
            self.threshold_c = self.default_threshold_c
        else:
            self.threshold_c = self.convert_display_to_c(self.default_threshold_f)

    def highlight_color(self) -> Tuple[int, int, int]:
        if self.threshold_mode == ">":
            return (255, 0, 0)
        if self.threshold_mode == "<":
            return (0, 136, 255)
        return (255, 255, 255)


class ModeManager:
    """
    Keeps track of the active mode and handles button routing.
    """

    def __init__(self, temperature_model: TemperatureModel, hooks: ModeHooks) -> None:
        self.temperature_model = temperature_model
        self.hooks = hooks
        palette_names = [name for name, _ in COLORMAPS]
        self.state = ModeState(palette_names=palette_names)
        self.modes: List[Mode] = [
            LiveHighlightMode(),
            PaletteMode(),
            FlatFieldCalibrationMode(hooks),
            HotColdMode(),
            SettingsMode(),
        ]
        self._index = 0

    @property
    def current(self) -> Mode:
        return self.modes[self._index]

    def cycle(self) -> Optional[str]:
        self.current.on_exit(self.state)
        self._index = (self._index + 1) % len(self.modes)
        result = self.current.on_enter(self.state)
        if isinstance(result, ModeResult) and result.banner:
            return result.banner
        return f"{self.current.name} Mode"

    def handle_mode_press(self) -> tuple[bool, Optional[str]]:
        return self.current.on_mode_button(self.state)

    def handle_button_up(self) -> Optional[str]:
        return self.current.on_button_up(self.state)

    def handle_button_down(self) -> Optional[str]:
        return self.current.on_button_down(self.state)

    def update(self, frame_raw: np.ndarray) -> ModeResult:
        frame_c = self.temperature_model.to_celsius(frame_raw)
        return self.current.update(frame_raw, frame_c, self.state, self.temperature_model)

