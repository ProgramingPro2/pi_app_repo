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
        try:
            while True:
                # Read raw frame from camera
                frame_raw = self.camera.read_raw()
                frame_count += 1
                
                # Normalize to 0-255 range
                frame_min = frame_raw.min()
                frame_max = frame_raw.max()
                
                # Debug every 30 frames
                if frame_count % 30 == 0:
                    print(f"Frame {frame_count}: raw min={frame_min}, max={frame_max}, shape={frame_raw.shape}")
                
                if frame_max > frame_min:
                    frame_normalized = ((frame_raw.astype(np.float32) - frame_min) / (frame_max - frame_min) * 255).astype(np.uint8)
                else:
                    print(f"WARNING: Frame {frame_count} has no range (min==max={frame_min})")
                    frame_normalized = np.zeros_like(frame_raw, dtype=np.uint8)
                
                # Check if normalized frame is all white
                if frame_normalized.max() == 255 and frame_normalized.min() == 255:
                    print(f"WARNING: Frame {frame_count} normalized to all white!")
                
                # Convert to RGB (grayscale thermal image)
                frame_rgb = np.stack([frame_normalized] * 3, axis=-1)
                
                # Create PIL image
                image = Image.fromarray(frame_rgb, mode='RGB')
                
                # Check image before resize
                if frame_count % 30 == 0:
                    img_array = np.array(image)
                    print(f"PIL image: min={img_array.min()}, max={img_array.max()}, mean={img_array.mean():.1f}")
                
                # Resize to display size
                image = image.resize((self.options.lcd_width, self.options.lcd_height), Image.BILINEAR)
                
                # Check image after resize
                if frame_count % 30 == 0:
                    img_array = np.array(image)
                    if (img_array == 255).all():
                        print(f"WARNING: Image is all white after resize!")
                    print(f"Resized image: min={img_array.min()}, max={img_array.max()}, mean={img_array.mean():.1f}")
                
                # Apply flip if needed
                if self.options.display_flip_horizontal:
                    image = image.transpose(Image.FLIP_LEFT_RIGHT)
                
                # Display
                try:
                    self.display.show(image)
                except Exception as e:
                    print(f"Error displaying frame {frame_count}: {e}")
                    import traceback
                    traceback.print_exc()
                
                # Small delay to prevent overwhelming the display
                await asyncio.sleep(0.1)  # ~10 FPS
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
    app = ThermalApp(AppOptions())
    await app.run()


if __name__ == "__main__":
    asyncio.run(main())
