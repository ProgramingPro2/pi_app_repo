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
        try:
            while True:
                # Read raw frame from camera
                frame_raw = self.camera.read_raw()
                
                # Normalize to 0-255 range
                frame_min = frame_raw.min()
                frame_max = frame_raw.max()
                if frame_max > frame_min:
                    frame_normalized = ((frame_raw.astype(np.float32) - frame_min) / (frame_max - frame_min) * 255).astype(np.uint8)
                else:
                    frame_normalized = np.zeros_like(frame_raw, dtype=np.uint8)
                
                # Convert to RGB (grayscale thermal image)
                frame_rgb = np.stack([frame_normalized] * 3, axis=-1)
                
                # Create PIL image
                image = Image.fromarray(frame_rgb, mode='RGB')
                
                # Resize to display size
                image = image.resize((self.options.lcd_width, self.options.lcd_height), Image.BILINEAR)
                
                # Apply flip if needed
                if self.options.display_flip_horizontal:
                    image = image.transpose(Image.FLIP_LEFT_RIGHT)
                
                # Display
                self.display.show(image)
                
                await asyncio.sleep(0)
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
