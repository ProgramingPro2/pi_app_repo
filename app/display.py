"""
SPI display abstractions for the Waveshare 2.4\" ST7789 panel.
Uses Waveshare's official driver for reliable operation.
"""

from __future__ import annotations

from typing import Optional
import sys
from pathlib import Path

from PIL import Image

# Try to import Waveshare's official driver
try:
    # Add Waveshare driver path if LCD_Module_code exists
    waveshare_path = Path(__file__).resolve().parent.parent / "LCD_Module_code" / "LCD_Module_RPI_code" / "RaspberryPi" / "python"
    if waveshare_path.exists():
        sys.path.insert(0, str(waveshare_path))
    from lib import LCD_2inch4
    WAVESHARE_AVAILABLE = True
except ImportError:
    LCD_2inch4 = None  # type: ignore
    WAVESHARE_AVAILABLE = False

# Fallback to luma.lcd if Waveshare driver not available
try:
    from luma.core.interface.serial import spi
    from luma.lcd.device import st7789
    LUMA_AVAILABLE = True
except ImportError:
    spi = None  # type: ignore
    st7789 = None  # type: ignore
    LUMA_AVAILABLE = False


class DisplayError(RuntimeError):
    pass


class NullDisplay:
    """
    No-op display useful during development on non-Pi machines.
    """

    def __init__(self) -> None:
        self.last_frame: Optional[Image.Image] = None
        self._frame_count = 0

    def show(self, image: Image.Image) -> None:
        self.last_frame = image.copy()
        self._frame_count += 1
        # Print every 30 frames to avoid spam
        if self._frame_count % 30 == 0:
            print(f"NullDisplay: Frame {self._frame_count} (no actual display output)")

    def cleanup(self) -> None:
        self.last_frame = None


class Waveshare24Display:
    """
    Wraps the Waveshare 2.4\" LCD (ST7789) using Waveshare's official driver.
    Falls back to luma.lcd if Waveshare driver is not available.
    """

    def __init__(
        self,
        spi_port: int = 0,
        spi_device: int = 0,
        gpio_dc: int = 25,  # Pin 22
        gpio_rst: int = 27,  # Pin 13 (Waveshare 2.4" uses GPIO 27, not 24)
        gpio_bl: Optional[int] = 18,  # Pin 12 (GPIO 18)
        width: int = 240,
        height: int = 320,
        rotate: int = 0,
    ) -> None:
        self.width = width
        self.height = height
        self.rotate = rotate
        self._use_waveshare = False
        self._backlight = None
        
        # Prefer Waveshare's official driver if available
        if WAVESHARE_AVAILABLE and LCD_2inch4 is not None:
            try:
                print("Using Waveshare official driver...")
                self._device = LCD_2inch4.LCD_2inch4()
                self._device.Init()
                self._use_waveshare = True
                print(f"Waveshare display initialized: {width}x{height}")
                return
            except Exception as e:
                print(f"Failed to initialize Waveshare driver: {e}")
                print("Falling back to luma.lcd...")
        
        # Fallback to luma.lcd
        if not LUMA_AVAILABLE or spi is None or st7789 is None:
            raise DisplayError(
                "Neither Waveshare driver nor luma.lcd is available. "
                "Install Waveshare driver or: pip install luma.lcd"
            )
        
        # Check if RPi.GPIO is available (required by luma.lcd)
        try:
            import RPi.GPIO  # noqa: F401
        except ImportError:
            raise DisplayError(
                "RPi.GPIO is not installed. Install it with: pip install RPi.GPIO\n"
                "Note: RPi.GPIO only works on Raspberry Pi hardware."
            )

        print(f"Using luma.lcd fallback: port={spi_port}, device={spi_device}, DC={gpio_dc}, RST={gpio_rst}, BL={gpio_bl}")
        try:
            serial = spi(
                port=spi_port,
                device=spi_device,
                gpio_DC=gpio_dc,
                gpio_RST=gpio_rst,
                bus_speed_hz=50_000_000,
            )
            self._device = st7789(serial_interface=serial, width=width, height=height, rotate=rotate)
            print(f"luma.lcd ST7789 device created: {width}x{height}, rotate={rotate}")
        except Exception as e:
            print(f"Failed to create luma.lcd device: {e}")
            raise

        # Enable backlight (GPIO 18 = Pin 12 for Waveshare 2.4")
        if gpio_bl is not None:
            try:
                from gpiozero import PWMLED  # type: ignore
                try:
                    self._backlight = PWMLED(gpio_bl)
                    self._backlight.value = 1.0
                    print(f"Backlight enabled on GPIO {gpio_bl}")
                except Exception as e:
                    print(f"Warning: Could not enable backlight: {e}")
                    self._backlight = None
            except ImportError:
                print("Warning: gpiozero not available for backlight control")
                self._backlight = None
    
    def _gpio_to_pin(self, gpio: int) -> int:
        """Convert GPIO number to physical pin number (for reference)"""
        gpio_to_pin_map = {
            18: 12, 27: 13, 25: 22, 24: 18, 23: 16, 22: 15,
            10: 19, 11: 23, 8: 24
        }
        return gpio_to_pin_map.get(gpio, gpio)

    def show(self, image: Image.Image) -> None:
        try:
            # Convert to RGB and ensure proper format
            if image.mode != "RGB":
                rgb_image = image.convert("RGB")
            else:
                rgb_image = image.copy()
            
            # Ensure image is the right size for display
            if rgb_image.size != (self.width, self.height):
                rgb_image = rgb_image.resize((self.width, self.height), Image.BILINEAR)
            
            # Apply rotation if needed
            if self.rotate != 0:
                rgb_image = rgb_image.rotate(-self.rotate * 90, expand=False)
            
            # Debug: Check image data before sending
            if hasattr(self, '_frame_count'):
                self._frame_count += 1
            else:
                self._frame_count = 1
            
            # Reduced debug output for performance (only first frame and every 120 frames)
            if self._frame_count <= 1 or self._frame_count % 120 == 0:
                import numpy as np
                img_array = np.array(rgb_image)
                print(f"Display.show() frame {self._frame_count}: size={rgb_image.size}, mode={rgb_image.mode}, "
                      f"min={img_array.min()}, max={img_array.max()}, mean={img_array.mean():.1f}")
            
            # Display using Waveshare driver or luma.lcd
            if self._use_waveshare:
                # Waveshare's ShowImage method
                self._device.ShowImage(rgb_image)
            else:
                # luma.lcd display method
                self._device.display(rgb_image)
            
        except Exception as e:
            print(f"Error in display.show(): {e}")
            import traceback
            traceback.print_exc()
            raise

    def cleanup(self) -> None:
        try:
            if self._use_waveshare:
                self._device.module_exit()
            else:
                self._device.hide()
        except Exception:
            pass
        if getattr(self, "_backlight", None):
            try:
                self._backlight.close()
            except Exception:
                pass

