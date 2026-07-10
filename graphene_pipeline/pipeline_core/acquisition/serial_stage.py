from __future__ import annotations

import time
from dataclasses import dataclass
from typing import TextIO


@dataclass(frozen=True)
class Calibration:
    x_units_per_step: float = 1.0
    y_units_per_step: float = 1.0
    z_units_per_step: float = 1.0


@dataclass(frozen=True)
class StepPosition:
    x_steps: int
    y_steps: int
    z_steps: int

    def to_coordinates(self, calibration: Calibration) -> tuple[float, float, float]:
        return (
            self.x_steps * calibration.x_units_per_step,
            self.y_steps * calibration.y_units_per_step,
            self.z_steps * calibration.z_units_per_step,
        )


def parse_arduino_line(line: str) -> StepPosition | None:
    line = line.strip()
    if not line:
        return None

    parts = [part.strip() for part in line.split(",")]
    if parts and parts[0].upper() == "POS":
        parts = parts[1:]

    if len(parts) != 3:
        return None

    try:
        return StepPosition(
            x_steps=int(parts[0]),
            y_steps=int(parts[1]),
            z_steps=int(parts[2]),
        )
    except ValueError:
        return None


class ArduinoStageController:
    """Serial controller for the Arduino motor protocol used by the microscope.

    The current Arduino sketch is expected to accept relative move commands like
    X50, Y-50, or Z10 followed by a newline. Position reads accept either lines
    in the form POS,x,y,z or plain x,y,z.
    """

    def __init__(
        self,
        port: str = "COM3",
        baudrate: int = 115200,
        timeout: float = 0.25,
        startup_delay_seconds: float = 2.0,
        position_request_command: str | None = "P",
    ) -> None:
        self.port = port
        self.baudrate = baudrate
        self.timeout = timeout
        self.startup_delay_seconds = startup_delay_seconds
        self.position_request_command = position_request_command
        self.serial_connection = None

    def __enter__(self) -> "ArduinoStageController":
        self.open()
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def open(self) -> None:
        if self.serial_connection is not None:
            return
        try:
            import serial
        except ImportError as exc:
            raise RuntimeError(
                "pyserial is required for Arduino stage control. Install the package with pyserial."
            ) from exc

        self.serial_connection = serial.Serial(
            self.port,
            self.baudrate,
            timeout=self.timeout,
        )
        time.sleep(self.startup_delay_seconds)
        self.serial_connection.reset_input_buffer()

    def close(self) -> None:
        if self.serial_connection is not None:
            self.serial_connection.close()
            self.serial_connection = None

    def _require_connection(self):
        if self.serial_connection is None:
            raise RuntimeError("Arduino stage controller is not open.")
        return self.serial_connection

    def move_relative(self, axis: str, steps: int) -> None:
        axis = axis.upper().strip()
        if axis not in {"X", "Y", "Z"}:
            raise ValueError("axis must be X, Y, or Z")
        connection = self._require_connection()
        connection.write(f"{axis}{int(steps)}\n".encode("ascii"))

    def read_position(self, timeout_seconds: float = 10.0) -> StepPosition:
        connection = self._require_connection()
        deadline = time.time() + timeout_seconds

        if self.position_request_command:
            connection.write(f"{self.position_request_command}\n".encode("ascii"))

        while time.time() < deadline:
            raw = connection.readline().decode("utf-8", errors="replace")
            position = parse_arduino_line(raw)
            if position is not None:
                return position

        raise TimeoutError("No valid stage position received from Arduino.")
