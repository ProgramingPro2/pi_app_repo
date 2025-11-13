"""
Simple thermal camera viewer - displays raw thermal image on LCD.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Optional

import numpy as np
from PIL import Image

from .camera import SeekCamera, SeekCameraError, SyntheticCamera
from .display import NullDisplay, Waveshare24Display


@dataclass
class AppOptions:
    camera_type: str = "seek"
    ffc_path: Optional[str] = None
    use_synthetic: bool = False
    display_rotate: int = 0
    display_flip_horizontal: bool = False
    lcd: str = "waveshare"
    lcd_width: int = 240
    lcd_height: int = 320


class ThermalApp:
    def __init__(self, options: AppOptions) -> None:
        self.options = options
        
        # Initialize camera
        self.camera = self._init_camera()
        
        # Initialize display
        self.display = self._init_display()
        
        print(f"Camera: {self.camera.width}x{self.camera.height}")
        print(f"Display: {type(self.display).__name__}")

    def _init_camera(self):
        if self.options.use_synthetic:
            print("Using synthetic camera")
            return SyntheticCamera()
        try:
            print(f"Opening Seek camera (type: {self.options.camera_type})...")
            camera = SeekCamera(camera_type=self.options.camera_type, ffc_path=self.options.ffc_path)
            print(f"Camera opened: {camera.width}x{camera.height}")
            # Give camera a moment to stabilize (reduced delay for faster startup)
            import time
            time.sleep(0.2)
            # Read a few frames to let camera warm up (reduced for faster startup)
            for i in range(3):
                try:
                    camera.read_raw()
                except Exception:
                    pass
                time.sleep(0.05)
            print("Camera warmed up")
            return camera
        except SeekCameraError as e:
            print(f"Failed to open camera: {e}")
            if self.options.use_synthetic:
                return SyntheticCamera()
            raise

    def _init_display(self):
        if self.options.lcd == "waveshare":
            try:
                display = Waveshare24Display(rotate=self.options.display_rotate)
                print("Display initialized: Waveshare24Display")
                return display
            except Exception as e:
                print(f"Failed to initialize display: {e}")
                import traceback
                traceback.print_exc()
                return NullDisplay()
        return NullDisplay()

    async def run(self) -> None:
        frame_count = 0
        consecutive_errors = 0
        max_errors = 10
        try:
            while True:
                try:
                    # Read raw frame from camera
                    frame_raw = self.camera.read_raw()
                    consecutive_errors = 0
                    frame_count += 1
                except SeekCameraError as e:
                    consecutive_errors += 1
                    if consecutive_errors >= max_errors:
                        print(f"Too many camera errors ({consecutive_errors}), shutting down")
                        break
                    print(f"Camera read error (attempt {consecutive_errors}/{max_errors}): {e}")
                    await asyncio.sleep(0.5)
                    continue
                except Exception as e:
                    consecutive_errors += 1
                    if consecutive_errors >= max_errors:
                        print(f"Unexpected error ({consecutive_errors}): {e}")
                        import traceback
                        traceback.print_exc()
                        break
                    print(f"Unexpected error (attempt {consecutive_errors}/{max_errors}): {e}")
                    await asyncio.sleep(0.5)
                    continue
                
                # Normalize to 0-255 range with better handling
                frame_min = float(frame_raw.min())
                frame_max = float(frame_raw.max())
                frame_range = frame_max - frame_min
                
                # Debug first 5 frames and then every 120 frames (reduced for performance)
                if frame_count <= 5 or frame_count % 120 == 0:
                    print(f"Frame {frame_count}: raw min={frame_min:.0f}, max={frame_max:.0f}, range={frame_range:.0f}, shape={frame_raw.shape}", flush=True)
                
                # Normalize frame - optimized for speed
                if frame_range > 10:  # Need at least 10 units of range
                    # Normalize to 0-255 (optimized calculation)
                    frame_normalized = ((frame_raw.astype(np.float32) - frame_min) / frame_range * 255.0).astype(np.uint8)
                elif frame_range > 0:
                    # Very small range - stretch it more aggressively
                    padding = max(100.0, frame_range * 2)
                    frame_center = (frame_min + frame_max) * 0.5
                    frame_min_adj = frame_center - padding
                    frame_range_adj = padding * 2.0
                    frame_normalized = np.clip(((frame_raw.astype(np.float32) - frame_min_adj) / frame_range_adj * 255.0), 0, 255).astype(np.uint8)
                else:
                    # All pixels same value - show as mid-gray
                    frame_normalized = np.full_like(frame_raw, 128, dtype=np.uint8)
                
                # Convert to RGB (grayscale thermal image)
                # Stack the grayscale channel 3 times to make RGB
                frame_rgb = np.stack([frame_normalized, frame_normalized, frame_normalized], axis=-1)
                
                # Create PIL image from numpy array
                image = Image.fromarray(frame_rgb, mode='RGB')
                
                # Resize to display size (using faster resize method)
                image = image.resize((self.options.lcd_width, self.options.lcd_height), Image.NEAREST)  # NEAREST is faster than BILINEAR
                
                # Apply flip if needed
                if self.options.display_flip_horizontal:
                    image = image.transpose(Image.FLIP_LEFT_RIGHT)
                
                # Display
                self.display.show(image)
                
                # Minimal delay for frame rate control (optimized for higher FPS)
                await asyncio.sleep(0.03)  # ~30 FPS target
        finally:
            self.shutdown()

    def shutdown(self) -> None:
        try:
            self.camera.close()
        except Exception:
            pass
        try:
            self.display.cleanup()
        except Exception:
            pass


async def main() -> None:
    import sys
    print("Starting thermal app...", flush=True)
    sys.stdout.flush()
    options = AppOptions()
    print(f"Options: {options}", flush=True)
    sys.stdout.flush()
    try:
        app = ThermalApp(options)
        print("App initialized, starting run loop...", flush=True)
        sys.stdout.flush()
        await app.run()
    except Exception as e:
        print(f"Fatal error in main: {e}", flush=True)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
