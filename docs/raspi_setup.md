# Raspberry Pi Setup Guide

This guide walks through preparing a Raspberry Pi to launch the Seek CompactXR
thermal viewer on boot with output to the Waveshare 2.4″ SPI LCD.

## 1. Hardware Checklist
- Raspberry Pi 3/4/5 running Raspberry Pi OS (Bookworm or later).
- Seek Thermal CompactXR (USB).
- Waveshare 2.4″ LCD (ST7789) wired to the SPI interface.
- Three momentary push buttons connected to GPIO pins (defaults: `GPIO5` mode,
  `GPIO6` down, `GPIO13` up) with appropriate pull-ups or pull-downs.

## 2. Enable Required Interfaces
```
sudo raspi-config nonint do_spi 0
sudo raspi-config nonint do_i2c 0
```

Reboot afterwards.

## 3. System Packages
Install build requirements, OpenCV, libusb, and OLED dependencies:
```
sudo apt update
sudo apt install \
    build-essential cmake pkg-config git \
    libopencv-dev libusb-1.0-0-dev \
    python3-venv python3-dev python3-pip \
    libjpeg-dev zlib1g-dev
```

## 4. Python Virtual Environment
```
cd /home/pi/libseek-thermal
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip wheel
pip install numpy opencv-python pillow gpiozero luma.lcd
```

All runtime scripts assume the `.venv` virtual environment is active.

## 5. Build `libseek` and the Python Wrapper
The base library has already been installed system-wide, but the custom Python
shim must be compiled on the Pi:
```
mkdir -p pi_app/native/build
cmake -S pi_app/native -B pi_app/native/build -DCMAKE_BUILD_TYPE=Release
cmake --build pi_app/native/build
```

The resulting `libseekshim.so` lives in `pi_app/native/build`.

## 6. Udev Access (Optional)
Create `/etc/udev/rules.d/99-seekthermal.rules`:
```
SUBSYSTEM=="usb", ATTRS{idVendor}=="289d", ATTRS{idProduct}=="0010", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTRS{idVendor}=="289d", ATTRS{idProduct}=="0011", MODE="0666", GROUP="plugdev"
```
Reload rules and reconnect the camera:
```
sudo udevadm control --reload-rules
sudo udevadm trigger
```

## 7. Running the Application Manually
```
source /home/pi/libseek-thermal/.venv/bin/activate
export LD_LIBRARY_PATH=/home/pi/libseek-thermal/pi_app/native/build:$LD_LIBRARY_PATH
python -m pi_app.app.app
```

Modes are cycled with the MODE button; UP/DOWN adjust thresholds, palettes, or
menu selections depending on the active screen. The Settings menu also lets you
toggle between Celsius and Fahrenheit readouts; the threshold adjustment buttons
follow whichever unit is active (±0.5 °C or ±1 °F steps).

## 8. Flat-Field Calibration Workflow
1. Enter **FFC** mode.
2. Cover the camera lens with a uniform-temperature object.
3. Press the UP button to begin capture (60 averaged frames).
4. Wait for the banner indicating the calibration PNG was saved.
5. The viewer reloads itself with the new calibration file automatically.

Calibration images are stored in `~/.config/libseek-pi/ffc/`.

## 9. Autostart with systemd
Use the service template in `docs/thermal-viewer.service`:
```
sudo cp pi_app/docs/thermal-viewer.service /etc/systemd/system/thermal-viewer.service
sudo systemctl daemon-reload
sudo systemctl enable --now thermal-viewer.service
```

Verify with:
```
journalctl -u thermal-viewer.service -f
```

## 10. Manual Testing Checklist
- [ ] Live mode highlights pixels above/below the configured threshold.
- [ ] Palette mode cycles through OpenCV color maps and on-screen banner updates.
- [ ] FFC mode captures a calibration frame and reloads the camera.
- [ ] Hot/Cold mode shows the temperature delta and hotspots in the selected unit.
- [ ] Settings menu toggles Auto Exposure Lock, switches °C/°F, cycles the highlight comparator, and resets the threshold.
- [ ] Systemd service restarts the app automatically after a reboot.

