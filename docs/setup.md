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
  - GPIO DC (Data/Command): GPIO 25 (Pin 22)
  - GPIO RST (Reset): GPIO 27 (Pin 13)
  - GPIO BL (Backlight): GPIO 18 (Pin 12, PWM-capable)
  - Bus Speed: 50 MHz

## Hardware Wiring

### Display Connections (Waveshare 2.4" LCD)

Connect the Waveshare 2.4" LCD to the Raspberry Pi SPI interface:

| LCD Pin | Raspberry Pi Pin | GPIO | Function |
|---------|------------------|------|----------|
| VCC | Pin 1 | - | 3.3V Power |
| GND | Pin 6 | - | Ground |
| DIN | Pin 19 | GPIO 10/MOSI | SPI Data |
| CLK | Pin 23 | GPIO 11/SCLK | SPI Clock |
| CS | Pin 24 | GPIO 8/CE0 | SPI Chip Select |
| DC | Pin 22 | GPIO 25 | Data/Command |
| RST | Pin 13 | GPIO 27 | Reset |
| BL | Pin 12 | GPIO 18 | Backlight (PWM-capable) |

**Note:** Verify your specific Waveshare model pinout as it may vary slightly.

### Camera Connection

- Connect the Seek Thermal camera via USB port
- The application will auto-detect the camera type (CompactXR or CompactPRO)
- Ensure USB port provides adequate power (use powered USB hub if needed)

## Software Setup

### 1. Enable Required Interfaces

Enable SPI interface:

```bash
sudo raspi-config nonint do_spi 0
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
    zlib1g-dev \
    p7zip-full
```

**Note:** `p7zip-full` is required to extract the Waveshare LCD driver archive.

### 3. Clone Repository

If not already cloned:

```bash
cd /home/pi
git clone <repository-url> libseek-thermal
cd libseek-thermal/pi_app_repo
```

### 4. Download Waveshare LCD Driver

The application uses the official Waveshare driver for reliable display operation:

```bash
# Download the driver archive
wget https://files.waveshare.com/upload/8/8d/LCD_Module_RPI_code.7z

# Extract to LCD_Module_code directory
7z x LCD_Module_RPI_code.7z -o./LCD_Module_code
```

The driver will be automatically detected and used by the application.

### 5. Create Python Virtual Environment

Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip wheel
```

### 6. Install Python Dependencies

Install required Python packages:

```bash
pip install numpy opencv-python pillow gpiozero luma.lcd RPi.GPIO
```

**Note:** `RPi.GPIO` is required by `luma.lcd` for SPI display control. It only works on Raspberry Pi hardware.

### 7. Build libseek Library

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

### 8. Build Python Wrapper Library

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

### 9. Configure USB Permissions

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

### 10. Test Hardware Connections

#### Test Display

Verify SPI is enabled:

```bash
lsmod | grep spi
```

You should see `spi_bcm2835` loaded.

#### Test Camera

Verify camera is detected:

```bash
lsusb | grep -i seek
```

You should see a device with vendor ID `289d`.

### 11. Run Application Manually

Test the application before setting up autostart:

```bash
source .venv/bin/activate
export LD_LIBRARY_PATH=$(pwd)/native/build:$(pwd)/../build/src:$LD_LIBRARY_PATH
python3 -m app.app
```

**Note:** The `LD_LIBRARY_PATH` includes both the wrapper library location and the libseek library location so both can be found at runtime.

The application should:
- Display thermal video on the LCD
- Show live thermal images in real-time

Press `Ctrl+C` to exit.

**Example with different options:**

```bash
# Run with rainbow colormap
python3 -m app.app --colormap 5

# Run with hot colormap and horizontal flip
python3 -m app.app --colormap 12 --flip-horizontal

# Capture flat-field calibration
python3 -m app.app --ffc-capture

# Use FFC with rainbow colormap
python3 -m app.app --ffc --ffc-path ~/.config/libseek-pi/ffc/ffc_*.png --colormap 5

# See all options
python3 -m app.app --help
```

### 12. Configure Autostart

Set up the application to start automatically on boot:

```bash
# Copy service file
sudo cp docs/thermal-viewer.service /etc/systemd/system/thermal-viewer.service
```

Edit the service file to match your installation path and desired options:

```bash
sudo nano /etc/systemd/system/thermal-viewer.service
```

The default service file runs with `--colormap 5` (rainbow). Update paths if your installation differs:

```ini
[Unit]
Description=Thermal Camera Viewer
After=network.target

[Service]
Type=simple
User=jpearce
WorkingDirectory=/home/jpearce/pi_app_repo
Environment="PATH=/home/jpearce/pi_app_repo/.venv/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="LD_LIBRARY_PATH=/home/jpearce/pi_app_repo/native/build:/home/jpearce/libseek-thermal/build/src"
# Wait for USB devices to be ready and ensure camera is available
ExecStartPre=/bin/sleep 10
ExecStart=/home/jpearce/pi_app_repo/.venv/bin/python3 -m app.app --colormap 5
Restart=always
RestartSec=15
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

**Key settings to update:**
- `User` - Your Raspberry Pi username (default: `jpearce` or `pi`)
- `WorkingDirectory` - Path to `pi_app_repo` directory
- `Environment` paths - Update to match your installation
- `ExecStart` - Add additional flags as needed (e.g., `--ffc`, `--rotate 90`)

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

**Service management commands:**

```bash
# Start service
sudo systemctl start thermal-viewer.service

# Stop service
sudo systemctl stop thermal-viewer.service

# Restart service
sudo systemctl restart thermal-viewer.service

# Disable autostart
sudo systemctl disable thermal-viewer.service

# View recent logs
journalctl -u thermal-viewer.service -n 50

# Follow logs in real-time
journalctl -u thermal-viewer.service -f
```

## Troubleshooting

### Display Not Showing Image

1. **Verify SPI is enabled:**
   ```bash
   lsmod | grep spi
   ```
   You should see `spi_bcm2835` loaded.

2. **Check wiring connections:**
   - Verify all pins are connected correctly
   - Check DC (GPIO 25, Pin 22) and RST (GPIO 27, Pin 13) connections
   - Ensure backlight (GPIO 18, Pin 12) is connected

3. **Verify display model:**
   - Ensure display uses ST7789 controller
   - Check that Waveshare driver is extracted in `LCD_Module_code/`

4. **Check service logs:**
   ```bash
   journalctl -u thermal-viewer.service -n 50
   ```
   Look for display initialization errors.

5. **Test display manually:**
   ```bash
   source .venv/bin/activate
   python3 -m app.app --colormap 5
   ```

### Camera Not Detected

1. **Verify USB connection:**
   ```bash
   lsusb | grep 289d
   ```
   You should see a device with vendor ID `289d`.

2. **Check udev rules:**
   ```bash
   sudo udevadm trigger
   cat /etc/udev/rules.d/99-seekthermal.rules
   ```

3. **Verify user permissions:**
   ```bash
   groups
   ```
   You should see `plugdev` in the list.

4. **Check for other processes:**
   ```bash
   lsof /dev/bus/usb/*/* | grep 289d
   ```
   If another process is using the camera, stop it first.

5. **Try unplugging and replugging:**
   - Physically disconnect and reconnect the camera
   - Wait a few seconds for USB enumeration

### Application Crashes on Startup

1. **Check service logs:**
   ```bash
   journalctl -u thermal-viewer.service -n 50
   ```

2. **Verify virtual environment:**
   - Ensure `.venv` exists and is activated in service file
   - Check Python path in service file matches your installation

3. **Check library paths:**
   - Verify `LD_LIBRARY_PATH` includes both `native/build` and `../build/src`
   - Test manually: `export LD_LIBRARY_PATH=$(pwd)/native/build:$(pwd)/../build/src:$LD_LIBRARY_PATH`

4. **Verify Python dependencies:**
   ```bash
   source .venv/bin/activate
   pip list | grep -E "(numpy|opencv|pillow|gpiozero|luma|RPi)"
   ```

5. **Test running manually:**
   ```bash
   source .venv/bin/activate
   export LD_LIBRARY_PATH=$(pwd)/native/build:$(pwd)/../build/src:$LD_LIBRARY_PATH
   python3 -m app.app --colormap 5
   ```
   This will show error messages that may not appear in service logs.

### Low Frame Rate

1. **Check SPI bus speed:**
   - Application uses 50 MHz (set in code)
   - Verify SPI is enabled: `lsmod | grep spi`

2. **Monitor CPU temperature:**
   ```bash
   vcgencmd measure_temp
   ```
   If temperature is high (>80°C), add cooling or reduce load.

3. **Verify power supply:**
   - Use official Raspberry Pi power adapter
   - Check for low voltage warnings: `vcgencmd get_throttled`

4. **Close unnecessary processes:**
   ```bash
   systemctl list-units --type=service --state=running
   ```
   Disable services you don't need.

5. **Try simpler colormap:**
   - Grayscale (0) is fastest
   - Complex colormaps (rainbow, turbo) are slower

### LIBUSB Errors

**LIBUSB_ERROR_BUSY:**
- Another process is using the camera
- Solution: Stop other processes or wait a few seconds

**LIBUSB_ERROR_PIPE:**
- Camera needs time to initialize
- Solution: Service has 10-second delay (`ExecStartPre=/bin/sleep 10`), but you may need to increase it

**LIBUSB_ERROR_NOT_FOUND:**
- Camera not connected or not detected
- Solution: Check USB connection, verify with `lsusb`, reload udev rules

**Segmentation fault:**
- Usually indicates camera initialization issue
- Solution: Ensure camera is fully connected, wait longer before starting, check service logs

### Service Not Starting

1. **Check service status:**
   ```bash
   sudo systemctl status thermal-viewer.service
   ```

2. **View detailed logs:**
   ```bash
   journalctl -u thermal-viewer.service -n 100 --no-pager
   ```

3. **Verify service file syntax:**
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl cat thermal-viewer.service
   ```

4. **Test ExecStart command manually:**
   ```bash
   cd /home/jpearce/pi_app_repo
   source .venv/bin/activate
   export LD_LIBRARY_PATH=$(pwd)/native/build:$(pwd)/../build/src:$LD_LIBRARY_PATH
   /home/jpearce/pi_app_repo/.venv/bin/python3 -m app.app --colormap 5
   ```

5. **Check file permissions:**
   - Ensure service file is readable: `sudo chmod 644 /etc/systemd/system/thermal-viewer.service`
   - Verify user in service file has access to all paths

## Configuration

The application uses command-line flags for configuration. No config file is needed.

**Command-line options:**
- `--camera-type {seek,seekpro}` - Camera type (default: seek)
- `--ffc-path PATH` - Path to flat-field calibration PNG file
- `--ffc` - Enable flat-field calibration
- `--ffc-capture` - Capture a new flat-field calibration
- `--ffc-output PATH` - Output path for captured FFC
- `--colormap {0-21|name}` - Color palette (0=grayscale default)
- `--flip-horizontal` - Flip display horizontally
- `--rotate {0,90,180,270}` - Rotate display in degrees
- `--synthetic` - Use synthetic camera for testing
- `--lcd {waveshare,none}` - LCD display type

**Available colormaps (0-21):**
- 0=grayscale, 1=autumn, 2=bone, 3=jet, 4=winter, 5=rainbow
- 6=ocean, 7=summer, 8=spring, 9=cool, 10=hsv, 11=pink, 12=hot
- 13=parula, 14=magma, 15=inferno, 16=plasma, 17=viridis
- 18=cividis, 19=twilight, 20=twilight_shifted, 21=turbo

See `python3 -m app.app --help` for complete usage information.

## Next Steps

After successful setup:

1. **Try different color palettes:**
   ```bash
   python3 -m app.app --colormap 12  # Hot
   python3 -m app.app --colormap 3   # Jet
   python3 -m app.app --colormap 17  # Viridis
   ```

2. **Perform flat-field calibration:**
   ```bash
   # Cover camera lens, then:
   python3 -m app.app --ffc-capture
   
   # Use the captured FFC
   python3 -m app.app --ffc --ffc-path ~/.config/libseek-pi/ffc/ffc_*.png
   ```

3. **Experiment with rotation and flip:**
   ```bash
   python3 -m app.app --colormap 5 --rotate 90
   python3 -m app.app --colormap 5 --flip-horizontal
   ```

4. **Configure autostart:**
   - Edit service file to add your preferred options
   - Enable service for headless operation

5. **Optimize for your use case:**
   - Adjust colormap for your application
   - Capture FFC for better image quality
   - Fine-tune rotation/flip for your mounting orientation

See `README.md` for complete usage instructions and all available options.
