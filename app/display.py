"""
SPI display abstractions for the Waveshare 2.4\" ST7789 panel.
"""

from __future__ import annotations

from typing import Optional

from PIL import Image

try:
    from luma.core.interface.serial import spi
    from luma.lcd.device import st7789
except ImportError:  # pragma: no cover - optional dependency until running on Pi
    spi = None  # type: ignore
    st7789 = None  # type: ignore


class DisplayError(RuntimeError):
    pass


class NullDisplay:
    """
    No-op display useful during development on non-Pi machines.
    """

    def __init__(self) -> None:
        self.last_frame: Optional[Image.Image] = None

    def show(self, image: Image.Image) -> None:
        self.last_frame = image.copy()

    def cleanup(self) -> None:
        self.last_frame = None


class Waveshare24Display:
    """
    Wraps the Waveshare 2.4\" LCD (ST7789) using luma.lcd.
    """

    def __init__(
        self,
        spi_port: int = 0,
        spi_device: int = 0,
        gpio_dc: int = 25,
        gpio_rst: int = 24,
        gpio_bl: Optional[int] = None,
        width: int = 240,
        height: int = 320,
        rotate: int = 0,
    ) -> None:
        if spi is None or st7789 is None:
            raise DisplayError("luma.lcd is not installed; cannot drive Waveshare display.")

        serial = spi(
            port=spi_port,
            device=spi_device,
            gpio_DC=gpio_dc,
            gpio_RST=gpio_rst,
            bus_speed_hz=62_500_000,
        )
        self._device = st7789(serial_interface=serial, width=width, height=height, rotate=rotate)

        if gpio_bl is not None:
            try:
                from gpiozero import PWMLED  # type: ignore
            except ImportError:  # pragma: no cover
                PWMLED = None  # type: ignore
            if PWMLED:
                self._backlight = PWMLED(gpio_bl)
                self._backlight.value = 1.0
            else:
                self._backlight = None
        else:
            self._backlight = None

    def show(self, image: Image.Image) -> None:
        self._device.display(image.convert("RGB"))

    def cleanup(self) -> None:
        try:
            self._device.hide()
        except Exception:
            pass
        if getattr(self, "_backlight", None):
            try:
                self._backlight.close()
            except Exception:
                pass

