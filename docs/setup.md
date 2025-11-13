# Hardware Setup Guide

This guide provides detailed instructions for setting up the Raspberry Pi thermal viewer with specific hardware components.

## Hardware Requirements

### Raspberry Pi
- **Model:** Raspberry Pi 3, 4, or 5
- **OS:** Raspberry Pi OS (Bookworm or later)
- **Storage:** Minimum 8GB SD card (16GB+ recommended)

### Thermal Camera
- **Model:** Seek Thermal CompactXR (default) or Seek Thermal CompactPRO
- **Connection:** USB 2.0/3.0
- **Vendor ID:** `289d`
- **Product IDs:** 
  - `0010` - CompactXR
  - `0011` - CompactPRO
- **Resolution:** 206x156 pixels (CompactXR) or 320x240 pixels (CompactPRO)

### Display
- **Model:** Waveshare 2.4" LCD (ST7789 controller)
- **Resolution:** 240x320 pixels
- **Interface:** SPI
- **Connection Details:**
  - SPI Port: 0
  - SPI Device: 0
  - GPIO DC (Data/Command): GPIO 25
  - GPIO RST (Reset): GPIO 24
  - GPIO BL (Backlight): GPIO 18 (optional, PWM-capable, varies by model)
  - Bus Speed: 62.5 MHz

### Buttons
- **Type:** Three momentary push buttons with pull-up resistors
- **GPIO Pin Assignments:**
  - **MODE Button:** GPIO 5 (cycles through operating modes)
  - **DOWN Button:** GPIO 6 (decreases threshold/moves cursor up)
  - **UP Button:** GPIO 13 (increases threshold/moves cursor down)
- **Configuration:** All buttons use internal pull-up resistors (active LOW)

## Hardware Wiring

### Display Connections (Waveshare 2.4" LCD)

Connect the Waveshare 2.4" LCD to the Raspberry Pi SPI interface:

| LCD Pin | Raspberry Pi Pin | Function |
|---------|------------------|----------|
| VCC | 3.3V (Pin 1) | Power |
| GND | GND (Pin 6) | Ground |
| DIN | GPIO 10/MOSI (Pin 19) | SPI Data |
| CLK | GPIO 11/SCLK (Pin 23) | SPI Clock |
| CS | GPIO 8/CE0 (Pin 24) | SPI Chip Select |
| DC | GPIO 25 (Pin 22) | Data/Command |
| RST | GPIO 24 (Pin 18) | Reset |
| BL | GPIO 18 (Pin 12) | Backlight (optional, PWM-capable) |

**Note:** Verify your specific Waveshare model pinout as it may vary slightly.

### Button Connections

Connect three momentary push buttons:

| Button | GPIO Pin | Physical Pin | Function |
|--------|----------|--------------|----------|
| MODE | GPIO 5 | Pin 29 | Cycle modes |
| DOWN | GPIO 6 | Pin 31 | Decrease/Move up |
| UP | GPIO 13 | Pin 33 | Increase/Move down |

**Wiring:**
- One terminal of each button connects to the GPIO pin
- Other terminal connects to GND
- Internal pull-up resistors are enabled in software (no external resistors needed)

### Camera Connection

- Connect the Seek Thermal camera via USB port
- The application will auto-detect the camera type (CompactXR or CompactPRO)
- Ensure USB port provides adequate power (use powered USB hub if needed)

## Software Setup

### 1. Enable Required Interfaces

Enable SPI and I2C interfaces:

```bash
sudo raspi-config nonint do_spi 0
sudo raspi-config nonint do_i2c 0
```

Reboot the Raspberry Pi:

```bash
sudo reboot
```

### 2. Install System Dependencies

Update package lists and install required system packages:

```bash
sudo apt update
sudo apt install -y \
    build-essential \
    cmake \
    pkg-config \
    git \
    libopencv-dev \
    libusb-1.0-0-dev \
    python3-venv \
    python3-dev \
    python3-pip \
    libjpeg-dev \
    zlib1g-dev
```

### 3. Clone Repository

If not already cloned:

```bash
cd /home/pi
git clone <repository-url> libseek-thermal
cd libseek-thermal/pi_app_repo
```

### 4. Create Python Virtual Environment

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip wheel
```

### 5. Install Python Dependencies

Install required Python packages:

```bash
pip install numpy opencv-python pillow gpiozero luma.lcd RPi.GPIO
```

**Note:** `RPi.GPIO` is required by `luma.lcd` for SPI display control. It only works on Raspberry Pi hardware.

### 6. Pre-built Libraries (Quick Start)

**If pre-built libraries are included in the repository**, you can skip compilation and proceed directly to running the application (see step 10). The `libseekshim.so` wrapper library should already be present in `native/build/`.

Verify the pre-built library exists:

```bash
ls -lh native/build/libseekshim.so
```

If the file exists, you can skip to step 8 (Configure USB Permissions) or step 10 (Run Application).

### 7. Build from Source (Optional)

If you need to rebuild the libraries or pre-built binaries are not available, follow these steps:

#### 7.1 Build libseek Library

The Python wrapper requires the base `libseek` library to be built first. If you cloned only `pi_app_repo`, you'll need the parent repository:

```bash
cd /home/pi
git clone <parent-repository-url> libseek-thermal
cd libseek-thermal
```

Build libseek (no system-wide installation required):

```bash
mkdir -p build
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build
```

This creates `libseek.so` in `build/src/` directory. Verify it was built:

```bash
ls -lh build/src/libseek.so
```

**Note:** The wrapper will automatically find the library in the parent directory's `build/src/` folder, so no system-wide installation is needed.

#### 7.2 Build Python Wrapper Library

Now build the `libseekshim.so` wrapper library. The CMake configuration will automatically find the locally-built `libseek.so`:

```bash
cd pi_app_repo
mkdir -p native/build
cmake -S native -B native/build -DCMAKE_BUILD_TYPE=Release
cmake --build native/build
```

Verify the library was created:

```bash
ls -lh native/build/libseekshim.so
```

**Alternative: System-wide Installation (Optional)**

If you prefer to install libseek system-wide (requires sudo), you can do:

```bash
cd /home/pi/libseek-thermal
sudo cmake --install build
sudo ldconfig
```

This installs to `/usr/local/lib/` and `/usr/local/include/seek/`, but it's not required for the wrapper to work.

### 8. Configure USB Permissions (Optional)

To allow non-root access to the Seek Thermal camera, create a udev rule:

```bash
sudo nano /etc/udev/rules.d/99-seekthermal.rules
```

Add the following content:

```
SUBSYSTEM=="usb", ATTRS{idVendor}=="289d", ATTRS{idProduct}=="0010", MODE="0666", GROUP="plugdev"
SUBSYSTEM=="usb", ATTRS{idVendor}=="289d", ATTRS{idProduct}=="0011", MODE="0666", GROUP="plugdev"
```

Reload udev rules:

```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

Add your user to the `plugdev` group (if not already):

```bash
sudo usermod -aG plugdev $USER
```

**Note:** You may need to log out and back in for group changes to take effect.

### 9. Test Hardware Connections

#### Test Display

Verify SPI is enabled:

```bash
lsmod | grep spi
```

You should see `spi_bcm2835` loaded.

#### Test Buttons

Test GPIO access:

```bash
gpio readall
```

Verify buttons are wired correctly (optional manual test):

```python
from gpiozero import Button
from signal import pause

def pressed(btn_name):
    print(f"{btn_name} button pressed!")

btn_mode = Button(5, pull_up=True)
btn_down = Button(6, pull_up=True)
btn_up = Button(13, pull_up=True)

btn_mode.when_pressed = lambda: pressed("MODE")
btn_down.when_pressed = lambda: pressed("DOWN")
btn_up.when_pressed = lambda: pressed("UP")

print("Press buttons to test. Press Ctrl+C to exit.")
pause()
```

#### Test Camera

Verify camera is detected:

```bash
lsusb | grep -i seek
```

You should see a device with vendor ID `289d`.

### 10. Run Application Manually

Test the application before setting up autostart:

```bash
source .venv/bin/activate
export LD_LIBRARY_PATH=$(pwd)/native/build:$(pwd)/../build/src:$LD_LIBRARY_PATH
python -m app.app
```

**Note:** The `LD_LIBRARY_PATH` includes both the wrapper library location and the libseek library location so both can be found at runtime.

The application should:
- Display thermal video on the LCD
- Respond to button presses
- Show mode banners when cycling modes

Press `Ctrl+C` to exit.

### 11. Configure Autostart

Set up the application to start automatically on boot:

```bash
sudo cp docs/thermal-viewer.service /etc/systemd/system/thermal-viewer.service
```

Edit the service file to match your installation path:

```bash
sudo nano /etc/systemd/system/thermal-viewer.service
```

Update paths if your installation differs from `/home/pi/libseek-thermal`:

```ini
[Unit]
Description=Seek Thermal Waveshare Viewer
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/libseek-thermal/pi_app_repo
Environment=LD_LIBRARY_PATH=/home/pi/libseek-thermal/pi_app_repo/native/build:/home/pi/libseek-thermal/build/src
ExecStart=/home/pi/libseek-thermal/pi_app_repo/.venv/bin/python -m app.app
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start the service:

```bash
sudo systemctl daemon-reload
sudo systemctl enable thermal-viewer.service
sudo systemctl start thermal-viewer.service
```

Check service status:

```bash
sudo systemctl status thermal-viewer.service
```

View logs:

```bash
journalctl -u thermal-viewer.service -f
```

## Troubleshooting

### Display Not Showing Image

1. Verify SPI is enabled: `lsmod | grep spi`
2. Check wiring connections, especially DC and RST pins
3. Verify display model matches ST7789 controller
4. Check service logs for display initialization errors

### Camera Not Detected

1. Verify USB connection: `lsusb | grep 289d`
2. Check udev rules are loaded: `sudo udevadm trigger`
3. Verify user is in `plugdev` group: `groups`
4. Try running with `sudo` temporarily to test permissions

### Buttons Not Responding

1. Verify GPIO pins are correct (5, 6, 13)
2. Check button wiring (one side to GPIO, other to GND)
3. Test buttons manually with gpiozero
4. Verify no other processes are using the GPIO pins

### Application Crashes on Startup

1. Check logs: `journalctl -u thermal-viewer.service -n 50`
2. Verify virtual environment is activated in service file
3. Check `LD_LIBRARY_PATH` includes the build directory
4. Verify all Python dependencies are installed
5. Test running manually first to see error messages

### Low Frame Rate

1. Ensure SPI bus speed is set correctly (62.5 MHz)
2. Check CPU temperature: `vcgencmd measure_temp`
3. Verify adequate power supply (use official Pi power adapter)
4. Close unnecessary background processes

## Configuration

Configuration is stored in `~/.config/libseek-pi/config.json`. Key settings:

- `camera_type`: "seek" (CompactXR) or "seekpro" (CompactPRO)
- `palette_index`: Color palette selection (0-7)
- `threshold_c`: Temperature threshold in Celsius
- `threshold_mode`: Comparison mode (">", "<", "=")
- `auto_exposure_lock`: Lock exposure settings
- `temperature_unit`: "C" or "F"
- `ffc_path`: Path to flat-field calibration file

Flat-field calibration files are stored in `~/.config/libseek-pi/ffc/`.

## Next Steps

After successful setup:

1. Perform flat-field calibration (FFC mode) for best image quality
2. Adjust temperature thresholds for your use case
3. Experiment with different color palettes
4. Configure autostart for headless operation

See `README.md` for usage instructions and feature overview.

