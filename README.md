# Raspberry Pi Thermal Viewer

A simple, fast thermal imaging application for Raspberry Pi that displays Seek Thermal camera output on a Waveshare 2.4" SPI LCD display.

## Features

- **Real-time Thermal Display:** Live thermal video feed from Seek Thermal CompactXR or CompactPRO cameras
- **Multiple Color Palettes:** 22 standard OpenCV colormaps (0-21) including grayscale, hot, rainbow, jet, viridis, plasma, and more
- **Command-Line Interface:** Easy-to-use flags for configuration
- **Flat-Field Calibration:** Support for FFC correction via command-line flag
- **High Performance:** Optimized for 20-30 FPS display refresh
- **Waveshare Driver:** Uses official Waveshare driver for reliable display operation

## Hardware Requirements

- Raspberry Pi 3/4/5 running Raspberry Pi OS (Bookworm or later)
- Seek Thermal CompactXR or CompactPRO USB camera
- Waveshare 2.4" LCD (ST7789 controller) with SPI interface

See [setup.md](docs/setup.md) for detailed hardware specifications and wiring instructions.

## Quick Start

### 1. Prerequisites

Ensure your Raspberry Pi has:
- Raspberry Pi OS (Bookworm or later) installed
- SPI interface enabled
- Internet connection for package installation

### 2. Installation

Follow the detailed setup guide in [docs/setup.md](docs/setup.md) for complete installation instructions.

**Quick Start (with pre-built binaries):**

If pre-built libraries are included in the repository, you can skip compilation:

```bash
# Enable SPI
sudo raspi-config nonint do_spi 0
sudo reboot

# Install dependencies
sudo apt update
sudo apt install -y libopencv-dev libusb-1.0-0-dev python3-venv python3-dev \
    python3-pip libjpeg-dev zlib1g-dev p7zip-full

# Clone repository
cd /home/pi
git clone <repository-url> libseek-thermal
cd libseek-thermal/pi_app_repo

# Download Waveshare LCD driver (required for display)
sudo wget https://files.waveshare.com/upload/8/8d/LCD_Module_RPI_code.7z
7z x LCD_Module_RPI_code.7z -o./LCD_Module_code

# Create virtual environment and install Python dependencies
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip wheel
pip install numpy opencv-python pillow gpiozero RPi.GPIO

# Verify pre-built library exists
ls -lh native/build/libseekshim.so
```

**Build from Source (if needed):**

If you need to rebuild or pre-built binaries are not available:

```bash
# Install build dependencies
sudo apt install -y build-essential cmake pkg-config git

# Build libseek library first (from parent repository)
cd /home/pi/libseek-thermal
mkdir -p build
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build

# Build Python wrapper
cd pi_app_repo
mkdir -p native/build
cmake -S native -B native/build -DCMAKE_BUILD_TYPE=Release
cmake --build native/build
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
# Use hot colormap (number 12)
python3 -m app.app --colormap 12

# Or use name
python3 -m app.app --colormap hot
```

**With flat-field calibration:**
```bash
python3 -m app.app --ffc --ffc-path /path/to/ffc.png
```

**All available options:**
```bash
python3 -m app.app --help
```

**Available colormaps (use number or name):**
- `0`/`grayscale` - Grayscale (default)
- `1`/`autumn` - Autumn colors
- `2`/`bone` - Bone colormap
- `3`/`jet` - Jet colormap
- `4`/`winter` - Winter colors
- `5`/`rainbow` - Rainbow
- `6`/`ocean` - Ocean colors
- `7`/`summer` - Summer colors
- `8`/`spring` - Spring colors
- `9`/`cool` - Cool colormap
- `10`/`hsv` - HSV colormap
- `11`/`pink` - Pink colormap
- `12`/`hot` - Hot colormap (red/yellow for hot spots)
- `13`/`parula` - Parula colormap
- `14`/`magma` - Magma colormap
- `15`/`inferno` - Inferno colormap
- `16`/`plasma` - Plasma colormap
- `17`/`viridis` - Viridis colormap
- `18`/`cividis` - Cividis colormap
- `19`/`twilight` - Twilight colormap
- `20`/`twilight_shifted` - Twilight shifted
- `21`/`turbo` - Turbo colormap

### 4. Autostart Setup

Enable automatic startup on boot:

```bash
sudo cp docs/thermal-viewer.service /etc/systemd/system/
sudo nano /etc/systemd/system/thermal-viewer.service  # Update paths if needed
sudo systemctl daemon-reload
sudo systemctl enable --now thermal-viewer.service
```

## Usage

### Command-Line Options

The application supports various command-line flags for configuration:

```bash
python3 -m app.app [OPTIONS]
```

**Options:**
- `--camera-type {seek,seekpro}` - Camera type (default: seek)
- `--ffc-path PATH` - Path to flat-field calibration PNG file
- `--ffc` - Enable flat-field calibration (requires --ffc-path)
- `--colormap {0-21|name}` - Color palette (default: 0/grayscale)
- `--flip-horizontal` - Flip display horizontally
- `--rotate {0,90,180,270}` - Rotate display in degrees (default: 0)
- `--synthetic` - Use synthetic camera for testing
- `--lcd {waveshare,none}` - LCD display type (default: waveshare)

**Examples:**

```bash
# Default grayscale display
python3 -m app.app

# Hot colormap (shows red/yellow for hot spots)
python3 -m app.app --colormap 12
# Or: python3 -m app.app --colormap hot

# Rainbow colormap with horizontal flip
python3 -m app.app --colormap 5 --flip-horizontal

# With flat-field calibration
python3 -m app.app --ffc --ffc-path /path/to/ffc.png

# Rotated 90 degrees with jet colormap
python3 -m app.app --colormap 3 --rotate 90

# Use CompactPRO camera
python3 -m app.app --camera-type seekpro
```

### Color Palettes

The application supports 22 standard OpenCV colormaps (0-21). You can use either the number or the name:

| Number | Name | Description |
|--------|------|-------------|
| 0 | grayscale | Grayscale (default) |
| 1 | autumn | Autumn colors |
| 2 | bone | Bone colormap |
| 3 | jet | Classic jet colormap |
| 4 | winter | Winter colors |
| 5 | rainbow | Rainbow spectrum |
| 6 | ocean | Ocean colors |
| 7 | summer | Summer colors |
| 8 | spring | Spring colors |
| 9 | cool | Cool colormap |
| 10 | hsv | HSV colormap |
| 11 | pink | Pink colormap |
| 12 | hot | Hot colormap (red/yellow for hot) |
| 13 | parula | Parula colormap |
| 14 | magma | Magma colormap |
| 15 | inferno | Inferno colormap |
| 16 | plasma | Plasma colormap |
| 17 | viridis | Viridis colormap |
| 18 | cividis | Cividis colormap |
| 19 | twilight | Twilight colormap |
| 20 | twilight_shifted | Twilight shifted |
| 21 | turbo | Turbo colormap |

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
│   └── build/           # Compiled library output
├── LCD_Module_code/     # Waveshare official LCD driver
├── docs/
│   ├── setup.md         # Detailed setup instructions
│   └── thermal-viewer.service  # Systemd service file (optional)
└── tests/               # Unit tests
```

## Performance

- Target frame rate: 20-30 FPS
- Optimized image processing pipeline
- Fast display updates using Waveshare official driver
- Efficient color palette application using OpenCV

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

See [docs/setup.md](docs/setup.md) for detailed troubleshooting steps.

## Development

### Running Tests

```bash
source .venv/bin/activate
pytest tests/
```

### Development Mode

Run with synthetic camera (no hardware required):

```bash
python3 -m app.app --synthetic
```

Or in Python:

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
- Uses Waveshare official LCD driver for reliable display operation
- OpenCV for image processing and standard colormaps (0-21)

