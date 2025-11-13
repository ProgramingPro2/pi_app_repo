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
from .camera import SeekCamera, SeekCameraError, SyntheticCamera, autodetect_camera_type
from .config import ConfigData, load_config, save_config
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
    camera_type: str = "seek"  # Default to CompactXR
    ffc_path: Optional[str] = None
    use_synthetic: bool = False
    palette_index: int = 2
    display_rotate: int = 0
    display_flip_horizontal: bool = True  # Flip to fix mirrored display
    lcd: str = "waveshare"
    lcd_width: int = 240
    lcd_height: int = 320


class ThermalApp:
    def __init__(self, options: AppOptions, button_controller: Optional[buttons.ButtonController] = None) -> None:
        self.options = options
        self.config = load_config()
        
        # Autodetect camera type on bootup, defaulting to CompactXR ("seek")
        if not self.options.use_synthetic:
            try:
                detected_type = autodetect_camera_type(default="seek")
                self.options.camera_type = detected_type
                # Update config if detection succeeded and differs from stored value
                if detected_type != self.config.camera_type:
                    self.config.camera_type = detected_type
            except Exception:
                # Fall back to config or default if autodetection fails
                self.options.camera_type = self.config.camera_type or self.options.camera_type
        else:
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
            # Try to set up buttons, but don't fail if GPIO is unavailable
            buttons_available = self.button_controller.setup()
            if not buttons_available:
                # No buttons available, clear the controller
                self.button_controller.close()
                self.button_controller = None

        self.camera = self._init_camera()
        self.display = self._init_display()
        
        # Debug: Print display type
        display_type = type(self.display).__name__
        print(f"Using display type: {display_type}")
        if isinstance(self.display, NullDisplay):
            print("WARNING: Using NullDisplay - no actual display output will occur!")
            print("If you have a Waveshare display connected, check:")
            print("  1. SPI is enabled: sudo raspi-config nonint do_spi 0")
            print("  2. luma.lcd is installed: pip install luma.lcd")
            print("  3. RPi.GPIO is installed: pip install RPi.GPIO")
            print("  4. Display wiring is correct")
            print("  5. AppOptions.lcd is set to 'waveshare'")
            print("  6. You are running on a Raspberry Pi (RPi.GPIO only works on Pi hardware)")

    def _init_camera(self):
        if self.options.use_synthetic:
            print("Using synthetic camera (for testing)")
            return SyntheticCamera()
        try:
            print(f"Attempting to open Seek camera (type: {self.options.camera_type})...")
            camera = SeekCamera(camera_type=self.options.camera_type, ffc_path=self.options.ffc_path)
            print(f"Camera opened successfully: {camera.width}x{camera.height}")
            return camera
        except SeekCameraError as e:
            print(f"Failed to open Seek camera: {e}")
            if self.options.use_synthetic:
                print("Falling back to synthetic camera")
                return SyntheticCamera()
            raise

    def _init_display(self):
        if self.options.lcd == "waveshare":
            try:
                display = Waveshare24Display(rotate=self.options.display_rotate)
                print("Display initialized successfully: Waveshare24Display")
                return display
            except Exception as e:
                print(f"Failed to initialize Waveshare display: {e}")
                print("Falling back to NullDisplay (no-op)")
                import traceback
                traceback.print_exc()
                return NullDisplay()
        print("Using NullDisplay (lcd option not set to 'waveshare')")
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
        frame_count = 0
        try:
            while True:
                if self._pending_reload is not None:
                    self._reload_camera_now(self._pending_reload)
                    self._pending_reload = None

                frame_raw = self.camera.read_raw()
                frame_count += 1
                
                # Debug: Print frame info every 30 frames
                if frame_count % 30 == 0:
                    print(f"Frame {frame_count}: shape={frame_raw.shape}, min={frame_raw.min()}, max={frame_raw.max()}, mean={frame_raw.mean():.1f}")
                
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
                # Apply rotation if needed
                if self.options.display_rotate != 0:
                    image = image.rotate(self.options.display_rotate, expand=False)
                # Flip horizontally if display is mirrored (default: True to fix common issue)
                if self.options.display_flip_horizontal:
                    image = image.transpose(Image.FLIP_LEFT_RIGHT)
                
                # Debug: Print image info every 30 frames
                if frame_count % 30 == 0:
                    print(f"Display image: size={image.size}, mode={image.mode}")
                    # Check if image is all black
                    if image.mode == 'RGB':
                        import numpy as np
                        img_array = np.array(image)
                        if img_array.sum() == 0:
                            print("WARNING: Image is completely black!")
                        else:
                            print(f"Image stats: min={img_array.min()}, max={img_array.max()}, mean={img_array.mean():.1f}")
                    
                    # For first frame, try displaying a test pattern to verify display works
                    if frame_count == 30:
                        print("Displaying test pattern to verify display...")
                        test_image = Image.new('RGB', (240, 320), color=(255, 0, 0))  # Red screen
                        try:
                            self.display.show(test_image)
                            await asyncio.sleep(0.5)  # Show red for 0.5 seconds
                            test_image = Image.new('RGB', (240, 320), color=(0, 255, 0))  # Green screen
                            self.display.show(test_image)
                            await asyncio.sleep(0.5)  # Show green for 0.5 seconds
                            test_image = Image.new('RGB', (240, 320), color=(0, 0, 255))  # Blue screen
                            self.display.show(test_image)
                            await asyncio.sleep(0.5)  # Show blue for 0.5 seconds
                            print("Test pattern complete - if you saw red/green/blue, display is working!")
                        except Exception as e:
                            print(f"Error displaying test pattern: {e}")
                
                try:
                    self.display.show(image)
                except Exception as e:
                    print(f"Error displaying image: {e}")
                    import traceback
                    traceback.print_exc()

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

