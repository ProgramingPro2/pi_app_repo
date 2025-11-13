# Raspberry Pi Thermal Viewer

A high-performance thermal imaging application for Raspberry Pi that displays real-time Seek Thermal camera output on a Waveshare 2.4" SPI LCD display.

## Features

- **Real-time Thermal Display:** Live thermal video feed from Seek Thermal CompactXR or CompactPRO cameras
- **22 Color Palettes:** Standard OpenCV colormaps (0-21) including grayscale, hot, rainbow, jet, viridis, plasma, and more
- **Command-Line Interface:** Comprehensive flags for all configuration options
- **Flat-Field Calibration:** Capture and apply FFC correction for improved image quality
- **High Performance:** Optimized for 20-30 FPS display refresh
- **Waveshare Driver:** Uses official Waveshare driver for reliable display operation
- **Autostart Service:** Systemd service for automatic startup on boot

## Hardware Requirements

- **Raspberry Pi:** Model 3, 4, or 5 running Raspberry Pi OS (Bookworm or later)
- **Thermal Camera:** Seek Thermal CompactXR (default) or CompactPRO USB camera
- **Display:** Waveshare 2.4" LCD (ST7789 controller) with SPI interface

See [docs/setup.md](docs/setup.md) for detailed hardware specifications and wiring instructions.

## Quick Start

### 1. Prerequisites

Ensure your Raspberry Pi has:
- Raspberry Pi OS (Bookworm or later) installed
- SPI interface enabled
- Internet connection for package installation

### 2. Installation

**Complete installation steps:**

```bash
# Enable SPI
sudo raspi-config nonint do_spi 0
sudo reboot

# Install system dependencies
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
    zlib1g-dev \
    p7zip-full

# Clone repository
cd /home/pi
git clone <repository-url> libseek-thermal
cd libseek-thermal/pi_app_repo

# Download Waveshare LCD driver
wget https://files.waveshare.com/upload/8/8d/LCD_Module_RPI_code.7z
7z x LCD_Module_RPI_code.7z -o./LCD_Module_code

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip wheel
pip install numpy opencv-python pillow gpiozero luma.lcd RPi.GPIO

# Build libseek library (from parent repository)
cd /home/pi/libseek-thermal
mkdir -p build
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build

# Build Python wrapper
cd pi_app_repo
mkdir -p native/build
cmake -S native -B native/build -DCMAKE_BUILD_TYPE=Release
cmake --build native/build

# Configure USB permissions
sudo nano /etc/udev/rules.d/99-seekthermal.rules
# Add:
# SUBSYSTEM=="usb", ATTRS{idVendor}=="289d", ATTRS{idProduct}=="0010", MODE="0666", GROUP="plugdev"
# SUBSYSTEM=="usb", ATTRS{idVendor}=="289d", ATTRS{idProduct}=="0011", MODE="0666", GROUP="plugdev"

sudo udevadm control --reload-rules
sudo udevadm trigger
sudo usermod -aG plugdev $USER
# Log out and back in for group changes to take effect
```

### 3. Run Application

**Basic usage (grayscale):**
```bash
source .venv/bin/activate
export LD_LIBRARY_PATH=$(pwd)/native/build:$(pwd)/../build/src:$LD_LIBRARY_PATH
python3 -m app.app
```

**With color palette:**
```bash
# Rainbow colormap (number 5)
python3 -m app.app --colormap 5

# Or use name
python3 -m app.app --colormap rainbow

# Hot colormap (red/yellow for hot spots)
python3 -m app.app --colormap 12
```

**With flat-field calibration:**
```bash
# Capture new FFC (cover camera lens first!)
python3 -m app.app --ffc-capture

# Capture FFC and use it immediately
python3 -m app.app --ffc-capture --ffc

# Use existing FFC file
python3 -m app.app --ffc --ffc-path /path/to/ffc.png
```

**All available options:**
```bash
python3 -m app.app --help
```

### 4. Autostart Setup

Enable automatic startup on boot with rainbow colormap:

```bash
# Copy service file
sudo cp docs/thermal-viewer.service /etc/systemd/system/

# Edit if needed (update paths, user, or colormap)
sudo nano /etc/systemd/system/thermal-viewer.service

# Enable and start
sudo systemctl daemon-reload
sudo systemctl enable thermal-viewer.service
sudo systemctl start thermal-viewer.service

# Check status
sudo systemctl status thermal-viewer.service

# View logs
journalctl -u thermal-viewer.service -f
```

The default service file runs with `--colormap 5` (rainbow). Edit the service file to change the colormap or add other options.

## Usage

### Command-Line Options

```bash
python3 -m app.app [OPTIONS]
```

**Camera Options:**
- `--camera-type {seek,seekpro}` - Camera type: 'seek' for CompactXR, 'seekpro' for CompactPRO (default: seek)
- `--synthetic` - Use synthetic camera for testing without hardware

**Display Options:**
- `--colormap {0-21|name}` - Color palette (default: 0/grayscale)
- `--flip-horizontal` - Flip display horizontally
- `--rotate {0,90,180,270}` - Rotate display in degrees (default: 0)
- `--lcd {waveshare,none}` - LCD display type (default: waveshare)

**Flat-Field Calibration Options:**
- `--ffc-path PATH` - Path to flat-field calibration PNG file
- `--ffc` - Enable flat-field calibration (requires --ffc-path or --ffc-capture)
- `--ffc-capture` - Capture a new flat-field calibration (cover camera lens first)
- `--ffc-output PATH` - Output path for captured FFC (default: ~/.config/libseek-pi/ffc/ffc_YYYYMMDD_HHMMSS.png)

**Examples:**

```bash
# Default grayscale display
python3 -m app.app

# Rainbow colormap
python3 -m app.app --colormap 5

# Hot colormap with horizontal flip
python3 -m app.app --colormap 12 --flip-horizontal

# Rotated 90 degrees with jet colormap
python3 -m app.app --colormap 3 --rotate 90

# Use CompactPRO camera
python3 -m app.app --camera-type seekpro

# Capture new FFC
python3 -m app.app --ffc-capture

# Capture FFC and use it immediately
python3 -m app.app --ffc-capture --ffc

# Use existing FFC file
python3 -m app.app --ffc --ffc-path ~/ffc_calibration.png

# Test without hardware (synthetic camera)
python3 -m app.app --synthetic --colormap 5
```

### Available Colormaps

The application supports 22 standard OpenCV colormaps. You can use either the number (0-21) or the name:

| Number | Name | Description |
|--------|------|-------------|
| 0 | grayscale | Grayscale (default) |
| 1 | autumn | Autumn colors (red to yellow) |
| 2 | bone | Bone colormap (blue-white) |
| 3 | jet | Classic jet colormap (blue to red) |
| 4 | winter | Winter colors (blue to cyan) |
| 5 | rainbow | Rainbow spectrum (full color range) |
| 6 | ocean | Ocean colors (blue-green) |
| 7 | summer | Summer colors (green to yellow) |
| 8 | spring | Spring colors (magenta to yellow) |
| 9 | cool | Cool colormap (cyan to magenta) |
| 10 | hsv | HSV colormap (hue-based) |
| 11 | pink | Pink colormap (white to pink) |
| 12 | hot | Hot colormap (black-red-yellow-white) |
| 13 | parula | Parula colormap (MATLAB default) |
| 14 | magma | Magma colormap (black-red-yellow-white) |
| 15 | inferno | Inferno colormap (black-red-yellow) |
| 16 | plasma | Plasma colormap (purple-pink-yellow) |
| 17 | viridis | Viridis colormap (purple-green-yellow) |
| 18 | cividis | Cividis colormap (blue-yellow, colorblind-friendly) |
| 19 | twilight | Twilight colormap (blue-white-red) |
| 20 | twilight_shifted | Twilight shifted colormap |
| 21 | turbo | Turbo colormap (blue-cyan-yellow-red) |

**Popular choices:**
- `5`/`rainbow` - Full spectrum, great for general use
- `12`/`hot` - Red/yellow for hot spots, black for cold
- `3`/`jet` - Classic thermal imaging look
- `17`/`viridis` - Perceptually uniform, colorblind-friendly
- `21`/`turbo` - High contrast, modern look

### Flat-Field Calibration (FFC)

Flat-field calibration improves image quality by correcting for sensor non-uniformities and lens effects.

**To capture a new FFC:**

1. Cover the camera lens completely (use a cap or your hand)
2. Run: `python3 -m app.app --ffc-capture`
3. Wait for the capture to complete (60 frames averaged)
4. The FFC file will be saved to `~/.config/libseek-pi/ffc/ffc_YYYYMMDD_HHMMSS.png`

**To use an FFC:**

```bash
# Use existing FFC file
python3 -m app.app --ffc --ffc-path /path/to/ffc.png

# Capture and use immediately
python3 -m app.app --ffc-capture --ffc
```

**Tips:**
- Capture FFC when the camera is at operating temperature
- Keep the lens covered during the entire capture process
- Re-capture FFC if you notice image artifacts or non-uniformities
- Store FFC files for reuse across sessions

## Project Structure

```
pi_app_repo/
├── app/
│   ├── app.py           # Main application with command-line interface
│   ├── camera.py        # Seek camera interface
│   ├── display.py       # LCD display driver (Waveshare + luma.lcd fallback)
│   └── processing.py    # Image processing utilities
├── native/
│   ├── CMakeLists.txt   # Build configuration
│   ├── seek_wrapper.cpp # C++ wrapper for libseek
│   └── build/           # Compiled library output (libseekshim.so)
├── LCD_Module_code/     # Waveshare official LCD driver
├── docs/
│   ├── setup.md         # Detailed setup instructions
│   └── thermal-viewer.service  # Systemd service file
└── .venv/               # Python virtual environment
```

## Performance

- **Target frame rate:** 20-30 FPS
- **Optimizations:**
  - NEAREST image resizing for speed
  - Efficient OpenCV colormap application
  - Waveshare official driver for fast display updates
  - Minimal processing overhead
- **Display refresh:** Optimized SPI communication at 50 MHz

## Troubleshooting

### Service Not Starting

Check service status and logs:

```bash
sudo systemctl status thermal-viewer.service
journalctl -u thermal-viewer.service -f
```

Common issues:
- Camera busy: Wait a few seconds after boot for USB devices to initialize
- Library path: Verify `LD_LIBRARY_PATH` in service file includes both `native/build` and `../build/src`
- Permissions: Ensure user is in `plugdev` group

### Display Issues

- **Black or white screen:**
  - Verify SPI is enabled: `lsmod | grep spi`
  - Check wiring connections (DC, RST, SPI pins)
  - Verify GPIO pins match your hardware (DC=25/Pin 22, RST=27/Pin 13, BL=18/Pin 12)
  - Check service logs for display initialization errors

- **Incorrect colors or artifacts:**
  - Try a different colormap: `--colormap 5`
  - Check if FFC is needed: `--ffc-capture --ffc`
  - Verify display model matches ST7789 controller

### Camera Not Detected

- Verify USB connection: `lsusb | grep 289d`
- Check udev rules: `sudo udevadm trigger`
- Ensure user is in `plugdev` group: `groups`
- Verify no other process is using the camera: `lsof /dev/bus/usb/*/*`
- Try unplugging and replugging the camera

### Application Crashes

- Check logs: `journalctl -u thermal-viewer.service -n 50`
- Verify virtual environment is activated in service file
- Check `LD_LIBRARY_PATH` includes the build directory
- Verify all Python dependencies are installed: `pip list`
- Test running manually first: `python3 -m app.app --colormap 5`

### Low Frame Rate

- Ensure SPI bus speed is set correctly (50 MHz)
- Check CPU temperature: `vcgencmd measure_temp`
- Verify adequate power supply (use official Pi power adapter)
- Close unnecessary background processes
- Try simpler colormap (grayscale is fastest)

### LIBUSB Errors

- `LIBUSB_ERROR_BUSY`: Another process is using the camera
- `LIBUSB_ERROR_PIPE`: Camera needs time to initialize (service has 10s delay)
- `LIBUSB_ERROR_NOT_FOUND`: Camera not connected or not detected
- Solution: Ensure camera is connected, wait a few seconds, and try again

## Development

### Running Tests

```bash
source .venv/bin/activate
pytest tests/
```

### Development Mode

Run with synthetic camera (no hardware required):

```bash
python3 -m app.app --synthetic --colormap 5
```

Or in Python:

```python
from app.app import ThermalApp, AppOptions
import asyncio

options = AppOptions(
    use_synthetic=True,
    colormap="5"
)
app = ThermalApp(options)
asyncio.run(app.run())
```

### Building from Source

See [docs/setup.md](docs/setup.md) for detailed build instructions.

## License

[Add license information here]

## Contributing

[Add contributing guidelines here]

## Acknowledgments

- Built on top of `libseek` for Seek Thermal camera support
- Uses Waveshare official LCD driver for reliable display operation
- OpenCV for image processing and standard colormaps (0-21)
- `luma.lcd` as fallback display driver
