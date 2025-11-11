"""
Camera interface that bridges libseek to Python via the seekshim wrapper.
"""

from __future__ import annotations

import ctypes
import os
import pathlib
from typing import Optional

import numpy as np


class SeekCameraError(RuntimeError):
    """Raised when the camera wrapper encounters an unrecoverable error."""


class SeekCamera:
    """
    Thin wrapper around the native `seekshim` shared library.

    Parameters
    ----------
    camera_type:
        `"seek"` for Compact/CompactXR, `"seekpro"` for the CompactPRO.
    ffc_path:
        Optional flat field calibration PNG to load on startup.
    shim_path:
        Explicit path to the `libseekshim.so`. If omitted the loader searches
        the build directory and LD_LIBRARY_PATH.
    """

    _CAMERA_TYPES = {
        "seek": 0,
        "seekcompact": 0,
        "compactxr": 0,
        "seekpro": 1,
        "compactpro": 1,
    }

    def __init__(
        self,
        camera_type: str = "seekpro",
        ffc_path: Optional[str] = None,
        shim_path: Optional[str] = None,
    ) -> None:
        self._camera_type = camera_type.lower()
        if self._camera_type not in self._CAMERA_TYPES:
            raise ValueError(f"Unsupported camera type: {camera_type!r}")

        self._shim = self._load_shim(shim_path)
        self._handle = self._shim.seek_open(
            self._CAMERA_TYPES[self._camera_type],
            ffc_path.encode("utf-8") if ffc_path else None,
        )
        if not self._handle:
            raise SeekCameraError("Failed to open Seek camera (is it connected?)")

        width = ctypes.c_int()
        height = ctypes.c_int()
        ok = self._shim.seek_get_dimensions(self._handle, ctypes.byref(width), ctypes.byref(height))
        if not ok:
            self._close_handle()
            raise SeekCameraError("Unable to query Seek camera frame dimensions")

        self.width = int(width.value)
        self.height = int(height.value)
        self._buffer = np.empty((self.height, self.width), dtype=np.uint16)

    def _load_shim(self, shim_path: Optional[str]) -> ctypes.CDLL:
        candidates = []
        if shim_path:
            candidates.append(pathlib.Path(shim_path))
        env_path = os.environ.get("SEEK_SHIM_PATH")
        if env_path:
            candidates.append(pathlib.Path(env_path))

        cwd_candidates = [
            pathlib.Path(__file__).resolve().parent.parent / "native" / "build" / "libseekshim.so",
            pathlib.Path(__file__).resolve().parent.parent / "native" / "libseekshim.so",
        ]

        for candidate in candidates + cwd_candidates:
            if candidate and candidate.exists():
                lib = ctypes.CDLL(str(candidate))
                break
        else:
            lib = ctypes.CDLL("libseekshim.so")

        lib.seek_open.restype = ctypes.c_void_p
        lib.seek_open.argtypes = (ctypes.c_int, ctypes.c_char_p)
        lib.seek_close.restype = None
        lib.seek_close.argtypes = (ctypes.c_void_p,)
        lib.seek_get_dimensions.restype = ctypes.c_int
        lib.seek_get_dimensions.argtypes = (
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_int),
            ctypes.POINTER(ctypes.c_int),
        )
        lib.seek_read_frame.restype = ctypes.c_int
        lib.seek_read_frame.argtypes = (
            ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint16),
            ctypes.c_int,
        )
        return lib

    def read_raw(self) -> np.ndarray:
        """
        Retrieve a 16-bit frame from the camera.

        Returns
        -------
        numpy.ndarray
            A view backed by the internal buffer of shape (H, W) and dtype uint16.
        """
        count = self._shim.seek_read_frame(
            self._handle,
            self._buffer.ctypes.data_as(ctypes.POINTER(ctypes.c_uint16)),
            self._buffer.size,
        )
        if count < 0:
            raise SeekCameraError(f"seek_read_frame failed with code {count}")
        return self._buffer.reshape(self.height, self.width)

    def close(self) -> None:
        """Release the camera handle."""
        self._close_handle()

    def _close_handle(self) -> None:
        if getattr(self, "_handle", None):
            self._shim.seek_close(self._handle)
            self._handle = None

    def __enter__(self) -> "SeekCamera":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def __del__(self) -> None:
        try:
            self.close()
        except Exception:
            pass


class SyntheticCamera(SeekCamera):
    """
    Dummy implementation that generates gradient frames for development without hardware.
    """

    def __init__(self, width: int = 206, height: int = 156) -> None:
        self.width = width
        self.height = height
        self._shim = None
        self._handle = None
        self._buffer = np.zeros((self.height, self.width), dtype=np.uint16)
        self._phase = 0

    def read_raw(self) -> np.ndarray:
        xv, yv = np.meshgrid(
            np.linspace(0, 65535, self.width, dtype=np.float32),
            np.linspace(0, 65535, self.height, dtype=np.float32),
        )
        frame = (xv * np.sin(self._phase) + yv * np.cos(self._phase)).astype(np.uint16)
        self._buffer[:, :] = frame
        self._phase += 0.1
        return self._buffer

    def close(self) -> None:
        self._buffer.fill(0)

