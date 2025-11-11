"""
Main application loop wiring camera, processing, display, and inputs together.
"""

from __future__ import annotations

import asyncio
import datetime
import pathlib
from dataclasses import dataclass
from typing import Optional

import numpy as np
from PIL import Image

from . import buttons
from .camera import SeekCamera, SeekCameraError, SyntheticCamera
from .display import NullDisplay, Waveshare24Display
from .modes import ModeHooks, ModeManager
from .overlays import BannerQueue, format_status
from .processing import (
    COLORMAPS,
    TemperatureModel,
    apply_colormap,
    normalize_to_8bit,
    render_overlay,
)


@dataclass
class AppOptions:
    camera_type: str = "seekpro"
    ffc_path: Optional[str] = None
    use_synthetic: bool = False
    palette_index: int = 2
    display_rotate: int = 0
    lcd: str = "waveshare"
    lcd_width: int = 240
    lcd_height: int = 320


class ThermalApp:
    def __init__(self, options: AppOptions, button_controller: Optional[buttons.ButtonController] = None) -> None:
        self.options = options
        self.config = load_config()
        self.options.camera_type = self.config.camera_type or self.options.camera_type
        self.options.palette_index = self.config.palette_index
        if self.config.ffc_path:
            self.options.ffc_path = self.config.ffc_path

        self.temperature_model = TemperatureModel()
        self.banner_queue = BannerQueue()
        self._ffc_directory = pathlib.Path.home() / ".config" / "libseek-pi" / "ffc"
        self._pending_reload: Optional[str] = None

        self.mode_manager = ModeManager(
            self.temperature_model,
            ModeHooks(save_ffc=self._save_ffc, reload_camera=self._request_camera_reload),
        )
        self.mode_manager.state.palette_idx = options.palette_index
        self.mode_manager.state.ff_last_saved = options.ffc_path
        self.mode_manager.state.threshold_c = self.config.threshold_c
        self.mode_manager.state.threshold_mode = self.config.threshold_mode
        self.mode_manager.state.auto_exposure_lock = self.config.auto_exposure_lock
        self.mode_manager.state.temperature_unit = self.config.temperature_unit
        self.mode_manager.state.default_threshold_c = self.config.default_threshold_c
        self.mode_manager.state.default_threshold_f = self.config.default_threshold_f

        self.button_controller = button_controller or self._build_default_buttons()
        if self.button_controller:
            self.button_controller.setup()

        self.camera = self._init_camera()
        self.display = self._init_display()

    def _init_camera(self):
        if self.options.use_synthetic:
            return SyntheticCamera()
        try:
            return SeekCamera(camera_type=self.options.camera_type, ffc_path=self.options.ffc_path)
        except SeekCameraError:
            if self.options.use_synthetic:
                return SyntheticCamera()
            raise

    def _init_display(self):
        if self.options.lcd == "waveshare":
            try:
                return Waveshare24Display(rotate=self.options.display_rotate)
            except Exception:
                return NullDisplay()
        return NullDisplay()

    def _build_default_buttons(self) -> Optional[buttons.ButtonController]:
        if buttons.Button is None:
            return None

        specs = {
            "mode": buttons.ButtonSpec(name="MODE", pin=5, on_press=self._handle_mode_button),
            "down": buttons.ButtonSpec(name="DOWN", pin=6, on_press=self._handle_down_button),
            "up": buttons.ButtonSpec(name="UP", pin=13, on_press=self._handle_up_button),
        }
        return buttons.ButtonController(specs=specs)

    def _handle_mode_button(self) -> None:
        consumed, message = self.mode_manager.handle_mode_press()
        if consumed:
            if message:
                self.banner_queue.push(message)
            return

        banner = self.mode_manager.cycle()
        if banner:
            self.banner_queue.push(banner)

    def _handle_down_button(self) -> None:
        message = self.mode_manager.handle_button_down()
        if message:
            self.banner_queue.push(message)

    def _handle_up_button(self) -> None:
        message = self.mode_manager.handle_button_up()
        if message:
            self.banner_queue.push(message)

    async def run(self) -> None:
        try:
            while True:
                if self._pending_reload is not None:
                    self._reload_camera_now(self._pending_reload)
                    self._pending_reload = None

                frame_raw = self.camera.read_raw()
                mode_result = self.mode_manager.update(frame_raw)

                palette_name, palette_value = COLORMAPS[self.mode_manager.state.palette_idx]
                gray8 = normalize_to_8bit(frame_raw, lock=self.mode_manager.state.auto_exposure_lock)
                color_bgr = apply_colormap(gray8, palette_value)

                threshold_value = (
                    self.mode_manager.state.threshold_display
                    if self.mode_manager.current.name == "Live"
                    else None
                )
                base_status = format_status(
                    mode_name=self.mode_manager.current.name,
                    palette_name=palette_name,
                    temperature_unit=self.mode_manager.state.temperature_unit,
                    threshold=threshold_value,
                )
                status_lines = base_status + mode_result.status + self.banner_queue.active_messages()

                image = render_overlay(
                    color_bgr,
                    self.temperature_model.to_celsius(frame_raw),
                    mode_result.stats,
                    status_lines,
                    temperature_unit=self.mode_manager.state.temperature_unit,
                    highlight_mask=mode_result.highlight_mask,
                    highlight_color=mode_result.highlight_color,
                )
                image = self._resize_for_display(image)
                self.display.show(image)

                if mode_result.banner:
                    self.banner_queue.push(mode_result.banner)

                await asyncio.sleep(0)
        finally:
            self.shutdown()

    def _resize_for_display(self, image: Image.Image) -> Image.Image:
        if isinstance(self.display, NullDisplay):
            return image
        return image.resize((self.options.lcd_width, self.options.lcd_height), Image.BILINEAR)

    def shutdown(self) -> None:
        try:
            save_config(
                ConfigData(
                    camera_type=self.options.camera_type,
                    palette_index=self.mode_manager.state.palette_idx,
                    threshold_c=self.mode_manager.state.threshold_c,
                    threshold_mode=self.mode_manager.state.threshold_mode,
                    auto_exposure_lock=self.mode_manager.state.auto_exposure_lock,
                    ffc_path=self.mode_manager.state.ff_last_saved,
                    temperature_unit=self.mode_manager.state.temperature_unit,
                    default_threshold_c=self.mode_manager.state.default_threshold_c,
                    default_threshold_f=self.mode_manager.state.default_threshold_f,
                )
            )
        except Exception:
            pass

        try:
            self.camera.close()
        except Exception:
            pass
        if self.button_controller:
            self.button_controller.close()
        try:
            self.display.cleanup()
        except Exception:
            pass

    def _save_ffc(self, frame: np.ndarray) -> Optional[str]:
        try:
            import cv2
        except ImportError:
            return None

        self._ffc_directory.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        path = self._ffc_directory / f"ffc_{timestamp}.png"
        if cv2.imwrite(str(path), frame):
            return str(path)
        return None

    def _request_camera_reload(self, ffc_path: Optional[str]) -> None:
        self._pending_reload = ffc_path

    def _reload_camera_now(self, ffc_path: Optional[str]) -> None:
        try:
            self.camera.close()
        except Exception:
            pass

        self.options.ffc_path = ffc_path
        self.camera = self._init_camera()
        self.mode_manager.state.ff_last_saved = ffc_path


async def main() -> None:
    app = ThermalApp(AppOptions())
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())

