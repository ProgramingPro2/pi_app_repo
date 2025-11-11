# Raspberry Pi Thermal Viewer Architecture

This document outlines the structure for the Raspberry Pi application that will display Seek CompactXR frames on a Waveshare 2.4″ SPI LCD (ST7789) and provide button-driven controls.

## Technology Choices
- **Language:** Python 3 running inside a project-local virtual environment (`.venv`) for ease of iterating on UI logic and GPIO handling.
- **Camera access:** `ctypes` bindings on top of the already-installed `libseek.so`, using the same data flow as the C++ examples (`SeekCam::read()` then OpenCV processing).
- **Image processing:** `opencv-python` and `numpy` to normalize and colorize 16‑bit frames, plus temperature calculations.
- **Display driver:** `luma.lcd` (ST7789) or Waveshare’s official Python driver, selected behind an abstraction so the hardware layer can be swapped if needed.
- **GPIO buttons:** `gpiozero` (internally relies on `RPi.GPIO`) for simple edge detection and debouncing.
- **Overlay rendering:** `Pillow` to stamp text/graphics (current mode, palette name, temperature readouts) over the processed RGB frames before pushing them to the LCD.
- **Async loop:** `asyncio` event loop driving frame acquisition, render updates, and button events without blocking.

## Directory Layout
```
pi_app/
  app/
    __init__.py
    camera.py        # Thin wrapper around libseek for frame capture + FFC handling
    processing.py    # Temperature math, palette conversion, hotspot detection
    display.py       # SPI LCD abstraction built on luma.lcd or Waveshare driver
    buttons.py       # GPIO button manager with debounced callbacks
    modes.py         # Mode state machine, threshold logic, palette cycling
    overlays.py      # Text/graphics helpers (mode banner, temperature HUD)
    config.py        # Load/store JSON config (palette, thresholds, FFC file path)
    app.py           # Main asyncio application tying everything together
  docs/
    architecture.md  # <— this file
    raspi_setup.md   # Platform setup + dependency installation (to be written)
  tests/
    __init__.py
    test_modes.py    # Unit coverage for state machine + threshold math
    test_config.py   # Config persistence tests
```

## Button Mapping & Interactions
- **BTN_MODE:** Cycle through Modes 1→5, wraps around. Shows transient banner (e.g. “Palette Mode”) in the lower-right corner for 2 seconds.
- **BTN_DEC:** Context-sensitive “down” action. In live/threshold mode it decreases the highlighted temperature target. In settings mode it moves the cursor up.
- **BTN_INC:** Context-sensitive “up” action (increase threshold / move cursor down).

## Operating Modes
1. **Live Highlight Mode:** Continuous view with adjustable hot/cold threshold. Pixels matching the comparator (`>`, `<`, or `=`) sparkle in yellow; hotspot/coldspot labels show the extreme values in the selected temperature unit.
2. **Palette Mode:** Keeps streaming video while BTN_UP/BTN_DOWN cycle OpenCV colormaps (GRAY, JET, INFERNO, HOT, etc.). A banner confirms each selection.
3. **Flat-Field Calibration:** Guides the user to cover the lens, averages 60 frames, saves the PNG to `~/.config/libseek-pi/ffc/`, and hot-reloads the camera with the new correction.
4. **Hot/Cold Spot Mode:** Highlights the top/bottom 2 % of pixels, overlays min/max readings, and reports the delta in the current unit (°C or °F).
5. **Settings Page:** Menu overlay listing:
   - `Toggle AEL` — switch auto exposure lock.
   - `Units °C/°F` — toggle the display/inputs between Celsius and Fahrenheit (threshold increments update accordingly).
   - `Cycle Highlight` — rotate the comparator between `>`, `<`, `=`.
   - `Reset Threshold` — snap back to the configured default threshold.
   BTN_DEC/BTN_INC move the cursor; BTN_MODE activates the highlighted option.

## Data & Configuration
- Configuration stored in `~/.config/libseek-pi/config.json` (camera type, palette index, threshold value, comparator, auto-exposure lock, temperature unit, most recent FFC path).
- Flat-field PNGs saved per camera type with timestamps; newest valid file auto-loaded on boot.
- Transient messages managed by an in-app queue with timeout so multiple notifications don’t overlap.

## Performance Considerations
- Target 8–9 FPS; skip frames gracefully if processing exceeds 120 ms.
- Use preallocated numpy buffers and avoid reallocating PIL images per frame.
- Allow headless “diagnostic” logging via stdout (captured by systemd).

## Next Steps
1. Implement `camera.py` with ctypes bindings and unit-testable frame stubs.
2. Prototype the conversion pipeline (seek frame → normalized temperature → RGB image).
3. Integrate LCD output and button callbacks on the Raspberry Pi hardware.
4. Flesh out mode logic and overlays, then add tests for state machine behaviour.
5. Document system setup, service installation, and manual testing procedures.

