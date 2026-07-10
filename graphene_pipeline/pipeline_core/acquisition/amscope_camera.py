from __future__ import annotations

import time
from pathlib import Path

import numpy as np
from PIL import Image


class AmScopeCamera:
    """Small pull-mode wrapper around the AmScope/Amcam SDK."""

    def __init__(self) -> None:
        self.hcam = None
        self.buf = None
        self.width = 0
        self.height = 0
        self.latest_frame: np.ndarray | None = None
        self._amcam = None
        self.byte_order = "BGR"

    @staticmethod
    def camera_callback(event, ctx) -> None:
        if event == ctx._amcam.AMCAM_EVENT_IMAGE:
            ctx.on_frame()

    def __enter__(self) -> "AmScopeCamera":
        self.start()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.stop()

    def start(self) -> None:
        try:
            import amcam
        except ImportError:
            try:
                from pipeline_core.acquisition.vendor import amcam
            except ImportError as exc:
                raise RuntimeError(
                    "The AmScope camera SDK module 'amcam' is required for camera capture. "
                    "Install the SDK or keep the vendored amcam.py/amcam.dll files with the package."
                ) from exc

        self._amcam = amcam
        cameras = amcam.Amcam.EnumV2()
        if not cameras:
            raise RuntimeError("No AmScope camera found.")

        self.hcam = amcam.Amcam.Open(cameras[0].id)
        self.hcam.put_Option(amcam.AMCAM_OPTION_BYTEORDER, 1)
        self.width, self.height = self.hcam.get_Size()
        bufsize = self._stride_bytes(self.width) * self.height
        self.buf = bytes(bufsize)
        self.hcam.StartPullModeWithCallback(self.camera_callback, self)

    @staticmethod
    def _stride_bytes(width: int) -> int:
        return ((width * 24 + 31) // 32) * 4

    @classmethod
    def _decode_padded_frame(cls, buffer: bytes, width: int, height: int) -> np.ndarray:
        stride = cls._stride_bytes(width)
        frame = np.frombuffer(buffer, dtype=np.uint8).reshape((height, stride))
        return frame[:, : width * 3].reshape(height, width, 3).copy()

    def on_frame(self) -> None:
        try:
            self.hcam.PullImageV2(self.buf, 24, None)
            self.latest_frame = self._decode_padded_frame(
                self.buf,
                self.width,
                self.height,
            )
        except self._amcam.HRESULTException as exc:
            raise RuntimeError(f"Frame pull failed: hr=0x{exc.hr:x}") from exc

    def get_frame(self, timeout_seconds: float = 5.0) -> np.ndarray:
        deadline = time.time() + timeout_seconds
        while time.time() < deadline:
            if self.latest_frame is not None:
                return self.latest_frame.copy()
            time.sleep(0.05)
        raise TimeoutError("Timed out waiting for a camera frame.")

    def save_frame(self, path: Path, timeout_seconds: float = 5.0) -> Path:
        frame = self.get_frame(timeout_seconds=timeout_seconds)
        path.parent.mkdir(parents=True, exist_ok=True)
        if self.byte_order == "BGR":
            frame = frame[:, :, ::-1]
        Image.fromarray(frame).save(path)
        return path

    def stop(self) -> None:
        if self.hcam is not None:
            self.hcam.Close()
            self.hcam = None

