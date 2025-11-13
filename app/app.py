"""
Simple thermal camera viewer - displays raw thermal image on LCD.
"""

from __future__ import annotations

import argparse
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
    colormap: str = "grayscale"  # grayscale, hot, cool, rainbow, jet, viridis, plasma
    do_ffc: bool = False  # Perform flat field calibration


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
            ffc_path = self.options.ffc_path
            if self.options.do_ffc and ffc_path is None:
                print("Warning: --ffc flag set but no FFC path provided. FFC will be skipped.")
            camera = SeekCamera(camera_type=self.options.camera_type, ffc_path=ffc_path)
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
                
                # Apply color palette
                frame_rgb = self._apply_colormap(frame_normalized)
                
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

    def _apply_colormap(self, gray_frame: np.ndarray) -> np.ndarray:
        """Apply color palette to grayscale thermal image.
        
        Uses standard OpenCV colormap numbers:
        0=grayscale, 1=autumn, 2=bone, 3=jet, 4=winter, 5=rainbow, 6=ocean,
        7=summer, 8=spring, 9=cool, 10=hsv, 11=pink, 12=hot, 13=parula,
        14=magma, 15=inferno, 16=plasma, 17=viridis, 18=cividis, 19=twilight,
        20=twilight_shifted, 21=turbo
        """
        colormap = self.options.colormap.lower()
        
        if colormap == "grayscale" or colormap == "0":
            # Simple grayscale - stack 3 channels
            return np.stack([gray_frame, gray_frame, gray_frame], axis=-1)
        
        # Use OpenCV colormaps if available
        try:
            import cv2
            # Map names to standard cv2 colormap numbers
            colormap_map = {
                "0": 0, "grayscale": 0,
                "1": 1, "autumn": 1,
                "2": 2, "bone": 2,
                "3": 3, "jet": 3,
                "4": 4, "winter": 4,
                "5": 5, "rainbow": 5,
                "6": 6, "ocean": 6,
                "7": 7, "summer": 7,
                "8": 8, "spring": 8,
                "9": 9, "cool": 9,
                "10": 10, "hsv": 10,
                "11": 11, "pink": 11,
                "12": 12, "hot": 12,
                "13": 13, "parula": 13,
                "14": 14, "magma": 14,
                "15": 15, "inferno": 15,
                "16": 16, "plasma": 16,
                "17": 17, "viridis": 17,
                "18": 18, "cividis": 18,
                "19": 19, "twilight": 19,
                "20": 20, "twilight_shifted": 20,
                "21": 21, "turbo": 21,
            }
            
            if colormap in colormap_map:
                cmap_num = colormap_map[colormap]
                if cmap_num == 0:
                    # Grayscale
                    return np.stack([gray_frame, gray_frame, gray_frame], axis=-1)
                # OpenCV colormaps expect uint8 grayscale input
                colored = cv2.applyColorMap(gray_frame, cmap_num)
                # Convert BGR to RGB (OpenCV uses BGR)
                return cv2.cvtColor(colored, cv2.COLOR_BGR2RGB)
        except ImportError:
            pass
        
        # Fallback: simple grayscale if OpenCV not available or unknown colormap
        if colormap != "grayscale" and colormap != "0":
            print(f"Warning: Colormap '{colormap}' not available, using grayscale")
        return np.stack([gray_frame, gray_frame, gray_frame], axis=-1)

    def shutdown(self) -> None:
        try:
            self.camera.close()
        except Exception:
            pass
        try:
            self.display.cleanup()
        except Exception:
            pass


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Thermal camera viewer for Raspberry Pi",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with default settings (grayscale)
  python -m app.app

  # Run with hot colormap (number 12)
  python -m app.app --colormap 12
  # Or use name
  python -m app.app --colormap hot

  # Run with FFC (flat field calibration)
  python -m app.app --ffc --ffc-path /path/to/ffc.png

  # Run with rainbow colormap (5) and horizontal flip
  python -m app.app --colormap 5 --flip-horizontal

Available colormaps (use number or name):
  0/grayscale, 1/autumn, 2/bone, 3/jet, 4/winter, 5/rainbow,
  6/ocean, 7/summer, 8/spring, 9/cool, 10/hsv, 11/pink, 12/hot,
  13/parula, 14/magma, 15/inferno, 16/plasma, 17/viridis,
  18/cividis, 19/twilight, 20/twilight_shifted, 21/turbo
        """
    )
    
    parser.add_argument(
        "--camera-type",
        type=str,
        default="seek",
        choices=["seek", "seekpro"],
        help="Camera type: 'seek' for CompactXR, 'seekpro' for CompactPRO (default: seek)"
    )
    
    parser.add_argument(
        "--ffc-path",
        type=str,
        default=None,
        help="Path to flat field calibration PNG file"
    )
    
    parser.add_argument(
        "--ffc",
        action="store_true",
        help="Perform flat field calibration (requires --ffc-path)"
    )
    
    parser.add_argument(
        "--colormap",
        type=str,
        default="0",
        help="Color palette to use. Can be number (0-21) or name. "
             "0=grayscale, 1=autumn, 2=bone, 3=jet, 4=winter, 5=rainbow, "
             "6=ocean, 7=summer, 8=spring, 9=cool, 10=hsv, 11=pink, 12=hot, "
             "13=parula, 14=magma, 15=inferno, 16=plasma, 17=viridis, "
             "18=cividis, 19=twilight, 20=twilight_shifted, 21=turbo (default: 0)"
    )
    
    parser.add_argument(
        "--flip-horizontal",
        action="store_true",
        help="Flip display horizontally"
    )
    
    parser.add_argument(
        "--rotate",
        type=int,
        default=0,
        choices=[0, 90, 180, 270],
        help="Rotate display (degrees: 0, 90, 180, 270, default: 0)"
    )
    
    parser.add_argument(
        "--synthetic",
        action="store_true",
        help="Use synthetic camera (for testing without hardware)"
    )
    
    parser.add_argument(
        "--lcd",
        type=str,
        default="waveshare",
        choices=["waveshare", "none"],
        help="LCD display type (default: waveshare)"
    )
    
    return parser.parse_args()


async def main() -> None:
    import sys
    args = parse_args()
    
    print("Starting thermal app...", flush=True)
    sys.stdout.flush()
    
    # Convert rotate degrees to luma.lcd rotate value (0-3)
    rotate_value = args.rotate // 90
    
    options = AppOptions(
        camera_type=args.camera_type,
        ffc_path=args.ffc_path,
        use_synthetic=args.synthetic,
        display_rotate=rotate_value,
        display_flip_horizontal=args.flip_horizontal,
        lcd=args.lcd if args.lcd != "none" else "null",
        colormap=args.colormap,
        do_ffc=args.ffc,
    )
    
    print(f"Options: camera={options.camera_type}, colormap={options.colormap}, "
          f"ffc={options.do_ffc}, flip={options.display_flip_horizontal}, rotate={args.rotate}°", flush=True)
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
