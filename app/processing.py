"""
Frame processing utilities: temperature estimation, colormap conversion, overlays.
"""

from __future__ import annotations

import dataclasses
import os
from typing import Dict, List, Tuple

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont


COLORMAPS: List[Tuple[str, int]] = [
    ("GRAY", -1),
    ("AUTUMN", cv2.COLORMAP_AUTUMN),
    ("BONE", cv2.COLORMAP_BONE),
    ("JET", cv2.COLORMAP_JET),
    ("WINTER", cv2.COLORMAP_WINTER),
    ("RAINBOW", cv2.COLORMAP_RAINBOW),
    ("OCEAN", cv2.COLORMAP_OCEAN),
    ("SUMMER", cv2.COLORMAP_SUMMER),
    ("SPRING", cv2.COLORMAP_SPRING),
    ("COOL", cv2.COLORMAP_COOL),
    ("HSV", cv2.COLORMAP_HSV),
    ("PINK", cv2.COLORMAP_PINK),
    ("HOT", cv2.COLORMAP_HOT),
    ("PARULA", cv2.COLORMAP_PARULA),
    ("MAGMA", cv2.COLORMAP_MAGMA),
    ("INFERNO", cv2.COLORMAP_INFERNO),
    ("PLASMA", cv2.COLORMAP_PLASMA),
    ("VIRIDIS", cv2.COLORMAP_VIRIDIS),
    ("CIVIDIS", cv2.COLORMAP_CIVIDIS),
    ("TWILIGHT", cv2.COLORMAP_TWILIGHT),
    ("TWILIGHT_SHIFTED", cv2.COLORMAP_TWILIGHT_SHIFTED),
    ("TURBO", cv2.COLORMAP_TURBO),
]

_FONT_MAIN: ImageFont.ImageFont
_FONT_SMALL: ImageFont.ImageFont
_FONT_PATH_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
]

for _path in _FONT_PATH_CANDIDATES:
    if os.path.exists(_path):
        try:
            _FONT_MAIN = ImageFont.truetype(_path, 16)
            _FONT_SMALL = ImageFont.truetype(_path, 14)
            break
        except OSError:
            continue
else:
    _FONT_MAIN = ImageFont.load_default()
    _FONT_SMALL = _FONT_MAIN

@dataclasses.dataclass
class TemperatureModel:
    """
    Linear temperature approximation for Seek raw counts.

    The real camera needs an absolute calibration curve; by default we use
    a rough scale/offset that maps counts to degrees Celsius. Users can
    refine this via configuration.
    """

    scale: float = 0.04  # counts to Kelvin approximation
    offset: float = 273.15

    def to_celsius(self, frame: np.ndarray) -> np.ndarray:
        return frame.astype(np.float32) * self.scale - self.offset


def normalize_to_8bit(frame: np.ndarray, lock: bool = False) -> np.ndarray:
    """
    Normalize a 16-bit frame into 8-bit space suitable for color mapping.
    """
    if lock:
        return cv2.convertScaleAbs(frame, alpha=1.0 / 256.0)

    min_val = float(frame.min())
    max_val = float(frame.max())
    if max_val <= min_val:
        return np.zeros_like(frame, dtype=np.uint8)

    normalized = ((frame - min_val) / (max_val - min_val) * 255.0).astype(np.uint8)
    return normalized


def apply_colormap(gray8: np.ndarray, colormap: int) -> np.ndarray:
    if colormap == -1:
        return cv2.cvtColor(gray8, cv2.COLOR_GRAY2RGB)
    return cv2.applyColorMap(gray8, colormap)


def compute_hotspots(frame: np.ndarray) -> Dict[str, Tuple[float, Tuple[int, int]]]:
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(frame.astype(np.float32))
    return {
        "min": (float(min_val), (int(min_loc[0]), int(min_loc[1]))),
        "max": (float(max_val), (int(max_loc[0]), int(max_loc[1]))),
    }


def highlight_threshold(frame_c: np.ndarray, target: float, mode: str = ">") -> np.ndarray:
    """
    Create a boolean mask selecting pixels above/below/near a temperature.
    Mode accepts '>', '<', '='.
    """
    if mode == ">":
        return frame_c > target
    if mode == "<":
        return frame_c < target
    tolerance = 0.5  # degrees Celsius
    return np.abs(frame_c - target) <= tolerance


def render_overlay(
    rgb_frame: np.ndarray,
    temperature_frame: np.ndarray,
    stats: Dict[str, Tuple[float, Tuple[int, int]]] | None,
    status_lines: List[str],
    temperature_unit: str,
    highlight_mask: np.ndarray | None = None,
    highlight_color: Tuple[int, int, int] | None = None,
) -> Image.Image:
    """
    Convert numpy arrays into a PIL Image with overlays.

    The incoming rgb_frame must be shape (H, W, 3) in BGR order. This function
    converts to RGB before creating the PIL image.
    """
    rgb = cv2.cvtColor(rgb_frame, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(rgb)
    draw = ImageDraw.Draw(image)

    width, height = image.size

    if highlight_mask is not None:
        overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        points = np.argwhere(highlight_mask)
        if points.size:
            color = highlight_color or (255, 255, 0)
            # Sample more aggressively to avoid stripes and overdrawing
            # Use fewer points for smoother highlight
            step = max(1, len(points) // 800)  # Reduced from 1500 to 800 for better coverage
            # Use smaller highlight dots
            for y, x in points[::step]:
                x0, y0 = max(0, int(x) - 1), max(0, int(y) - 1)
                x1, y1 = min(width, int(x) + 1), min(height, int(y) + 1)
                overlay_draw.rectangle(
                    (x0, y0, x1, y1),
                    fill=(color[0], color[1], color[2], 120),  # Reduced opacity from 160 to 120
                )
        image = Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")
        draw = ImageDraw.Draw(image)

    if stats:
        for label, (value, (x, y)) in stats.items():
            text = f"{label.upper()} {value:.1f}°{temperature_unit}"
            draw.text((x, y), text, fill=(255, 255, 255), font=_FONT_SMALL)

    if status_lines:
        # Use smaller font and padding for compact overlay
        padding = 3
        line_spacing = 1
        line_metrics = []
        max_width = 0
        # Use small font for status text
        status_font = _FONT_SMALL
        for line in status_lines:
            bbox = draw.textbbox((0, 0), line, font=status_font)
            width_line = bbox[2] - bbox[0]
            height_line = bbox[3] - bbox[1]
            line_metrics.append((line, width_line, height_line))
            max_width = max(max_width, width_line)

        total_height = sum(h for _, _, h in line_metrics) + line_spacing * (len(line_metrics) - 1)
        x0 = width - max_width - padding * 2
        y0 = height - total_height - padding * 2
        # Semi-transparent black background
        overlay_bg = Image.new("RGBA", image.size, (0, 0, 0, 180))
        overlay_draw = ImageDraw.Draw(overlay_bg)
        overlay_draw.rectangle((x0, y0, width, height), fill=(0, 0, 0, 200))
        image = Image.alpha_composite(image.convert("RGBA"), overlay_bg).convert("RGB")
        draw = ImageDraw.Draw(image)

        cursor_y = y0 + padding
        for line, line_w, line_h in line_metrics:
            draw.text((width - max_width - padding, cursor_y), line, fill=(255, 255, 255), font=status_font)
            cursor_y += line_h + line_spacing

    return image

