# Raspberry Pi Thermal Viewer

A real-time thermal imaging application for Raspberry Pi that displays Seek Thermal camera output on a Waveshare 2.4" SPI LCD with button-driven controls.

## Features

- **Real-time Thermal Display:** Live thermal video feed from Seek Thermal CompactXR or CompactPRO cameras
- **Multiple Operating Modes:**
  - Live Highlight Mode with adjustable temperature thresholds
  - Palette Mode with multiple color map options
  - Flat-Field Calibration (FFC) mode
  - Hot/Cold Spot Detection mode
  - Settings menu for configuration
- **Temperature Units:** Switch between Celsius and Fahrenheit
- **Button Controls:** Three-button interface for mode cycling and adjustments
- **Autostart Support:** Systemd service for automatic startup on boot
- **Persistent Configuration:** Settings saved between sessions

## Hardware Requirements

- Raspberry Pi 3/4/5 running Raspberry Pi OS (Bookworm or later)
- Seek Thermal CompactXR or CompactPRO USB camera
- Waveshare 2.4" LCD (ST7789 controller) with SPI interface
- Three momentary push buttons (GPIO 5, 6, 13)

See [setup.md](docs/setup.md) for detailed hardware specifications and wiring instructions.

## Quick Start

### 1. Prerequisites

Ensure your Raspberry Pi has:
- Raspberry Pi OS (Bookworm or later) installed
- SPI interface enabled
- Internet connection for package installation

### 2. Installation

Follow the detailed setup guide in [docs/setup.md](docs/setup.md) for complete installation instructions.

Quick installation summary:

```bash
# Enable SPI
sudo raspi-config nonint do_spi 0
sudo reboot

# Install dependencies
sudo apt update
sudo apt install -y build-essential cmake pkg-config git \
    libopencv-dev libusb-1.0-0-dev python3-venv python3-dev \
    python3-pip libjpeg-dev zlib1g-dev

# Clone repository (if needed)
cd /home/pi
git clone <repository-url> libseek-thermal
cd libseek-thermal/pi_app_repo

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip wheel
pip install numpy opencv-python pillow gpiozero luma.lcd

# Build native library
mkdir -p native/build
cmake -S native -B native/build -DCMAKE_BUILD_TYPE=Release
cmake --build native/build
```

### 3. Run Application

Manual execution:

```bash
source .venv/bin/activate
export LD_LIBRARY_PATH=$(pwd)/native/build:$LD_LIBRARY_PATH
python -m app.app
```

### 4. Autostart Setup

Enable automatic startup on boot:

```bash
sudo cp docs/thermal-viewer.service /etc/systemd/system/
sudo nano /etc/systemd/system/thermal-viewer.service  # Update paths if needed
sudo systemctl daemon-reload
sudo systemctl enable --now thermal-viewer.service
```

## Usage

### Button Controls

- **MODE Button (GPIO 5):** Cycles through operating modes (Live → Palette → FFC → Hot/Cold → Settings → Live...)
- **UP Button (GPIO 13):** Context-sensitive increase action
  - In Live mode: Increases temperature threshold
  - In Palette mode: Cycles to next color palette
  - In Settings: Moves cursor down
- **DOWN Button (GPIO 6):** Context-sensitive decrease action
  - In Live mode: Decreases temperature threshold
  - In Palette mode: Cycles to previous color palette
  - In Settings: Moves cursor up

### Operating Modes

#### 1. Live Highlight Mode
- Continuous thermal video display
- Adjustable temperature threshold with UP/DOWN buttons
- Highlights pixels matching the threshold comparator (>, <, or =)
- Displays hotspot and coldspot temperatures
- Threshold adjustment: ±0.5°C or ±1°F depending on unit setting

#### 2. Palette Mode
- Live thermal video with color map selection
- Cycle through OpenCV color palettes (GRAY, JET, INFERNO, HOT, etc.)
- Banner displays current palette name
- Use UP/DOWN buttons to change palettes

#### 3. Flat-Field Calibration (FFC) Mode
- Performs flat-field correction for improved image quality
- Instructions displayed on screen
- Cover camera lens with uniform-temperature object
- Press UP button to begin capture (averages 60 frames)
- Calibration file saved to `~/.config/libseek-pi/ffc/`
- Camera automatically reloads with new calibration

#### 4. Hot/Cold Spot Mode
- Highlights top/bottom 2% of pixels
- Displays minimum and maximum temperatures
- Shows temperature delta in current unit (°C or °F)

#### 5. Settings Menu
Navigate with UP/DOWN, activate with MODE button:
- **Toggle AEL:** Enable/disable auto exposure lock
- **Units °C/°F:** Switch between Celsius and Fahrenheit
- **Cycle Highlight:** Rotate threshold comparator (>, <, =)
- **Reset Threshold:** Restore default temperature threshold

### Temperature Units

Switch between Celsius and Fahrenheit in the Settings menu. Threshold adjustments automatically adapt:
- Celsius: ±0.5°C increments
- Fahrenheit: ±1°F increments

## Configuration

Configuration is stored in `~/.config/libseek-pi/config.json`. The application automatically:
- Detects camera type (CompactXR or CompactPRO)
- Loads the most recent flat-field calibration file
- Saves settings on exit

### Configuration Options

- `camera_type`: "seek" (CompactXR) or "seekpro" (CompactPRO)
- `palette_index`: Selected color palette (0-7)
- `threshold_c`: Temperature threshold in Celsius
- `threshold_mode`: Comparison operator (">", "<", "=")
- `auto_exposure_lock`: Lock exposure settings
- `temperature_unit`: "C" or "F"
- `ffc_path`: Path to flat-field calibration PNG file

## Project Structure

```
pi_app_repo/
├── app/
│   ├── app.py           # Main application loop
│   ├── camera.py        # Seek camera interface
│   ├── display.py       # LCD display driver
│   ├── buttons.py       # GPIO button handling
│   ├── modes.py         # Operating mode state machine
│   ├── processing.py    # Image processing and temperature calculations
│   ├── overlays.py      # Text and graphics overlays
│   └── config.py        # Configuration management
├── native/
│   ├── CMakeLists.txt   # Build configuration
│   ├── seek_wrapper.cpp # C++ wrapper for libseek
│   └── build/           # Compiled library output
├── docs/
│   ├── setup.md         # Detailed setup instructions
│   ├── architecture.md  # System architecture documentation
│   └── thermal-viewer.service  # Systemd service file
└── tests/               # Unit tests
```

## Performance

- Target frame rate: 8-9 FPS
- Frame processing: ~120ms per frame
- Automatic frame skipping if processing exceeds target time
- Optimized with preallocated buffers and efficient image processing

## Troubleshooting

### Service Not Starting

Check service status and logs:

```bash
sudo systemctl status thermal-viewer.service
journalctl -u thermal-viewer.service -f
```

### Display Issues

- Verify SPI is enabled: `lsmod | grep spi`
- Check wiring connections (DC, RST, SPI pins)
- Review display initialization errors in logs

### Camera Not Detected

- Verify USB connection: `lsusb | grep 289d`
- Check udev rules: `sudo udevadm trigger`
- Ensure user is in `plugdev` group

### Buttons Not Working

- Verify GPIO pins (5, 6, 13)
- Check button wiring (GPIO to button, button to GND)
- Test with gpiozero manually

See [docs/setup.md](docs/setup.md) for detailed troubleshooting steps.

## Development

### Running Tests

```bash
source .venv/bin/activate
pytest tests/
```

### Development Mode

Run with synthetic camera (no hardware required):

```python
from app.app import ThermalApp, AppOptions
import asyncio

app = ThermalApp(AppOptions(use_synthetic=True))
asyncio.run(app.run())
```

## License

[Add license information here]

## Contributing

[Add contributing guidelines here]

## Acknowledgments

- Built on top of `libseek` for Seek Thermal camera support
- Uses `luma.lcd` for ST7789 display driver
- OpenCV for image processing and color mapping

