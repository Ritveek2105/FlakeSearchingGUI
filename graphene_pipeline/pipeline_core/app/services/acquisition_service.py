from __future__ import annotations

from pipeline_core.app.services.models import (
    ComputeChipPlaneInput,
    ComputeChipPlaneOutput,
    StagePositionInput,
    StagePositionOutput,
)
from pipeline_core.geometry.plane import Point3D, compute_plane


class AcquisitionService:
    def compute_chip_plane(self, request: ComputeChipPlaneInput) -> ComputeChipPlaneOutput:
        points = [
            Point3D(x=point.x, y=point.y, z=point.z)
            for point in request.corners
        ]
        plane = compute_plane(points)
        return ComputeChipPlaneOutput(
            a=plane.a,
            b=plane.b,
            c=plane.c,
            d=plane.d,
            equation=plane.as_equation(),
        )

    def read_stage_position(self, request: StagePositionInput) -> StagePositionOutput:
        controller = request.controller_id or "default"
        return StagePositionOutput(
            x=None,
            y=None,
            z=None,
            is_stub=True,
            message=(
                f"Stage position controller '{controller}' is not wired yet. "
                "Manual position entry remains the active workflow."
            ),
        )
