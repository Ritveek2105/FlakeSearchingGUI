from __future__ import annotations

import math
from dataclasses import asdict, dataclass

import numpy as np


@dataclass(frozen=True)
class Point3D:
    """A point in microscope motor-step space."""

    x: float
    y: float
    z: float

    def to_dict(self) -> dict[str, float]:
        return asdict(self)


@dataclass(frozen=True)
class Plane:
    """Plane equation: ax + by + cz + d = 0."""

    a: float
    b: float
    c: float
    d: float

    def as_equation(self) -> str:
        return f"{self.a:.8g}x + {self.b:.8g}y + {self.c:.8g}z + {self.d:.8g} = 0"

    def to_dict(self) -> dict[str, float | str]:
        return {
            "a": self.a,
            "b": self.b,
            "c": self.c,
            "d": self.d,
            "equation": self.as_equation(),
        }

    def z_at(self, x: float, y: float) -> float:
        """Return z on the plane at motor-step coordinate (x, y)."""
        if self.c == 0:
            raise ValueError("Cannot solve for z because plane coefficient c is zero.")
        return -(self.a * x + self.b * y + self.d) / self.c


def _plane_from_three_points(points: list[Point3D]) -> Plane:
    if len(points) != 3:
        raise ValueError("Exactly three chip corners are required.")

    p1, p2, p3 = points

    u = Point3D(p2.x - p1.x, p2.y - p1.y, p2.z - p1.z)
    v = Point3D(p3.x - p1.x, p3.y - p1.y, p3.z - p1.z)

    a = u.y * v.z - u.z * v.y
    b = u.z * v.x - u.x * v.z
    c = u.x * v.y - u.y * v.x

    norm = math.sqrt(a * a + b * b + c * c)
    if norm == 0:
        raise ValueError("The three corners are collinear; a chip plane cannot be computed.")

    a /= norm
    b /= norm
    c /= norm
    d = -(a * p1.x + b * p1.y + c * p1.z)

    return Plane(a=a, b=b, c=c, d=d)


def _best_fit_plane(points: list[Point3D]) -> Plane:
    coordinates = np.array([[point.x, point.y, point.z] for point in points], dtype=float)
    centroid = coordinates.mean(axis=0)
    centered = coordinates - centroid

    _, singular_values, vh = np.linalg.svd(centered, full_matrices=False)
    normal = vh[-1]
    norm = np.linalg.norm(normal)
    if norm == 0 or singular_values[1] == 0:
        raise ValueError("The chip corners are collinear; a chip plane cannot be computed.")

    normal = normal / norm
    a, b, c = normal.tolist()
    d = -float(np.dot(normal, centroid))

    return Plane(a=float(a), b=float(b), c=float(c), d=d)


def compute_plane(points: list[Point3D]) -> Plane:
    """Compute a normalized chip plane from three or more corner points."""
    if len(points) < 3:
        raise ValueError("At least three chip corners are required.")
    if len(points) == 3:
        return _plane_from_three_points(points)
    return _best_fit_plane(points)
