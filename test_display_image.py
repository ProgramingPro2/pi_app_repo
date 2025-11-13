"""
Test displaying an actual image with known values to verify display works
"""

import time
from PIL import Image
import numpy as np

from luma.core.interface.serial import spi
from luma.lcd.device import st7789
from gpiozero import PWMLED

print("Creating display...")
serial = spi(port=0, device=0, gpio_DC=25, gpio_RST=27, bus_speed_hz=50_000_000)
device = st7789(serial_interface=serial, width=240, height=320, rotate=0)

backlight = PWMLED(18)
backlight.value = 1.0
print("Backlight ON")

device.clear()
time.sleep(0.5)

# Create an image similar to what the thermal camera produces
# Mean around 98, range 0-255
print("Creating test image with mean=98 (similar to thermal)...")
arr = np.random.randint(0, 255, (154, 207), dtype=np.uint8)
# Normalize to have mean around 98
arr = (arr.astype(np.float32) * 0.3 + 98).astype(np.uint8)
arr = np.clip(arr, 0, 255)

# Convert to RGB
rgb = np.stack([arr, arr, arr], axis=-1)
img = Image.fromarray(rgb, mode='RGB')
print(f"Test image: min={arr.min()}, max={arr.max()}, mean={arr.mean():.1f}")

# Resize to display size
img = img.resize((240, 320), Image.BILINEAR)
print(f"Resized image: min={np.array(img).min()}, max={np.array(img).max()}, mean={np.array(img).mean():.1f}")

print("Displaying test image - you should see a grayscale pattern")
device.display(img)
time.sleep(5)

# Try a simple gradient
print("Creating gradient...")
grad = np.linspace(0, 255, 240, dtype=np.uint8)
grad_img = np.tile(grad, (320, 1))
grad_rgb = np.stack([grad_img, grad_img, grad_img], axis=-1)
img2 = Image.fromarray(grad_rgb, mode='RGB')
print(f"Gradient: min={grad_img.min()}, max={grad_img.max()}, mean={grad_img.mean():.1f}")

print("Displaying gradient - you should see left-to-right gradient")
device.display(img2)
time.sleep(5)

print("Test complete")
device.hide()
backlight.close()

