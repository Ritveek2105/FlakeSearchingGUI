from __future__ import annotations

import json
import sys
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from config import PROJECT_DIR

PROJECT_ROOT = PROJECT_DIR

from pipeline_core.app.services.acquisition_service import AcquisitionService
from pipeline_core.app.services.models import (
    ComputeChipPlaneInput,
    Point3DInput,
    StagePositionInput,
)
from pipeline_core.geometry.plane import Plane, Point3D

try:
    from pipeline_core.app.gui.styles import BACKGROUND, PANEL, TITLE_FONT, WINDOW_WIDTH
except Exception:
    BACKGROUND = "#f5f7fb"
    PANEL = "#ffffff"
    TITLE_FONT = ("Segoe UI", 16, "bold")
    WINDOW_WIDTH = 1100


class AcquisitionGUI:
    """Companion desktop tool for chip-corner collection and plane fitting.

    This is intentionally separate from the pipeline runner. It shares backend
    logic through pipeline_core.geometry.plane, but does not start or modify a
    processing run yet.
    """

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Graphene Acquisition Console")
        self.root.geometry(f"{max(WINDOW_WIDTH, 1000)}x720")
        self.root.minsize(900, 620)
        self.root.configure(bg=BACKGROUND)

        self.corners: list[Point3D] = []
        self.plane: Plane | None = None
        self.acquisition_service = AcquisitionService()

        self.x_var = tk.StringVar(value="0")
        self.y_var = tk.StringVar(value="0")
        self.z_var = tk.StringVar(value="0")
        self.corner_x_var = tk.StringVar(value="0")
        self.corner_y_var = tk.StringVar(value="0")
        self.corner_z_var = tk.StringVar(value="0")
        self.corner_count_var = tk.IntVar(value=3)
        self.plane_var = tk.StringVar(value="Add three corners, then compute the chip plane.")
        self.pred_x_var = tk.StringVar(value="0")
        self.pred_y_var = tk.StringVar(value="0")
        self.pred_z_var = tk.StringVar(value="")

        self.corner_tree: ttk.Treeview
        self.log_box: tk.Text

        self.build_ui()

    def build_ui(self) -> None:
        header = tk.Frame(self.root, bg=BACKGROUND, padx=16, pady=12)
        header.pack(fill="x")

        tk.Label(
            header,
            text="Graphene Acquisition Console",
            font=TITLE_FONT,
            bg=BACKGROUND,
        ).pack(anchor="w")

        tk.Label(
            header,
            text="Chip corners, plane equation, and future motor-step tracking.",
            bg=BACKGROUND,
            fg="#4b5563",
        ).pack(anchor="w", pady=(4, 0))

        main = tk.Frame(self.root, bg=BACKGROUND, padx=16, pady=12)
        main.pack(fill="both", expand=True)

        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(0, weight=1)

        left = tk.Frame(main, bg=BACKGROUND)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        right = tk.Frame(main, bg=BACKGROUND)
        right.grid(row=0, column=1, sticky="nsew", padx=(10, 0))
        right.rowconfigure(2, weight=1)

        self.build_stage_position_box(left)
        self.build_corner_box(left)
        self.build_plane_box(right)
        self.build_plane_prediction_box(right)
        self.build_log_box(right)

    def panel(self, parent: tk.Widget, title: str) -> tk.LabelFrame:
        box = tk.LabelFrame(
            parent,
            text=title,
            bg=PANEL,
            padx=12,
            pady=10,
            bd=1,
            relief="solid",
        )
        box.pack(fill="x", pady=(0, 12))
        return box

    def build_stage_position_box(self, parent: tk.Widget) -> None:
        box = self.panel(parent, "Stage Position / Motor Steps")

        row = tk.Frame(box, bg=PANEL)
        row.pack(fill="x")

        for label, variable in [
            ("X steps", self.x_var),
            ("Y steps", self.y_var),
            ("Z steps", self.z_var),
        ]:
            group = tk.Frame(row, bg=PANEL)
            group.pack(side="left", fill="x", expand=True, padx=(0, 8))
            tk.Label(group, text=label, bg=PANEL).pack(anchor="w")
            tk.Entry(group, textvariable=variable).pack(fill="x")

        button_row = tk.Frame(box, bg=PANEL)
        button_row.pack(fill="x", pady=(10, 0))

        tk.Button(
            button_row,
            text="Read Stage Position",
            command=self.read_stage_position_placeholder,
            width=20,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            button_row,
            text="Use Manual Values",
            command=self.log_manual_position,
            width=18,
        ).pack(side="left")

    def build_corner_box(self, parent: tk.Widget) -> None:
        box = self.panel(parent, "Chip Corners")

        count_row = tk.Frame(box, bg=PANEL)
        count_row.pack(fill="x", pady=(0, 10))

        tk.Label(count_row, text="Corners to use", bg=PANEL).pack(side="left", padx=(0, 8))
        tk.Spinbox(
            count_row,
            from_=3,
            to=8,
            width=6,
            textvariable=self.corner_count_var,
            command=self.on_corner_count_changed,
        ).pack(side="left")

        entry_row = tk.Frame(box, bg=PANEL)
        entry_row.pack(fill="x", pady=(0, 10))

        for label, variable in [
            ("Corner X", self.corner_x_var),
            ("Corner Y", self.corner_y_var),
            ("Corner Z", self.corner_z_var),
        ]:
            group = tk.Frame(entry_row, bg=PANEL)
            group.pack(side="left", fill="x", expand=True, padx=(0, 8))
            tk.Label(group, text=label, bg=PANEL).pack(anchor="w")
            tk.Entry(group, textvariable=variable).pack(fill="x")

        button_row = tk.Frame(box, bg=PANEL)
        button_row.pack(fill="x", pady=(0, 10))

        tk.Button(
            button_row,
            text="Add Corner",
            command=self.add_corner,
            width=16,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            button_row,
            text="Clear Corners",
            command=self.clear_corners,
            width=16,
        ).pack(side="left", padx=(0, 8))

        tk.Button(
            button_row,
            text="Save Plane JSON",
            command=self.save_plane_json,
            width=18,
        ).pack(side="left")

        columns = ("corner", "x", "y", "z")
        self.corner_tree = ttk.Treeview(box, columns=columns, show="headings", height=5)
        for column, title, width in [
            ("corner", "Corner", 100),
            ("x", "Relative X", 120),
            ("y", "Relative Y", 120),
            ("z", "Relative Z", 120),
        ]:
            self.corner_tree.heading(column, text=title)
            self.corner_tree.column(column, width=width, anchor="center")
        self.corner_tree.pack(fill="x")

        help_text = (
            "Enter chip-corner coordinates here. These values are independent "
            "from the Stage Position / Motor Steps panel."
        )
        tk.Label(box, text=help_text, bg=PANEL, fg="#6b7280", wraplength=420).pack(anchor="w", pady=(8, 0))

    def build_plane_box(self, parent: tk.Widget) -> None:
        box = self.panel(parent, "Plane Equation")

        tk.Button(
            box,
            text="Compute Plane",
            command=self.compute_plane,
            width=18,
        ).pack(anchor="w", pady=(0, 10))

        tk.Label(
            box,
            textvariable=self.plane_var,
            bg=PANEL,
            fg="#111827",
            font=("Consolas", 11),
            wraplength=470,
            justify="left",
        ).pack(anchor="w")

        tk.Button(
            box,
            text="Copy Equation",
            command=self.copy_equation,
            width=18,
        ).pack(anchor="w", pady=(10, 0))

    def build_plane_prediction_box(self, parent: tk.Widget) -> None:
        box = self.panel(parent, "Predict Focus Z From Plane")

        row = tk.Frame(box, bg=PANEL)
        row.pack(fill="x")

        for label, variable in [("X", self.pred_x_var), ("Y", self.pred_y_var)]:
            group = tk.Frame(row, bg=PANEL)
            group.pack(side="left", fill="x", expand=True, padx=(0, 8))
            tk.Label(group, text=label, bg=PANEL).pack(anchor="w")
            tk.Entry(group, textvariable=variable).pack(fill="x")

        tk.Button(row, text="Calculate Z", command=self.calculate_predicted_z, width=14).pack(side="left")

        tk.Label(box, text="Predicted Z", bg=PANEL).pack(anchor="w", pady=(10, 0))
        tk.Entry(box, textvariable=self.pred_z_var, state="readonly").pack(fill="x")

    def build_log_box(self, parent: tk.Widget) -> None:
        box = tk.LabelFrame(
            parent,
            text="Acquisition Log",
            bg=PANEL,
            padx=12,
            pady=10,
            bd=1,
            relief="solid",
        )
        box.pack(fill="both", expand=True)
        box.rowconfigure(0, weight=1)
        box.columnconfigure(0, weight=1)

        self.log_box = tk.Text(box, height=12, wrap="word")
        self.log_box.grid(row=0, column=0, sticky="nsew")

        scrollbar = tk.Scrollbar(box, command=self.log_box.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.log_box.configure(yscrollcommand=scrollbar.set)

        self.log("Acquisition console ready.")

    def current_point_from_fields(self) -> Point3D:
        try:
            return Point3D(
                x=float(self.x_var.get()),
                y=float(self.y_var.get()),
                z=float(self.z_var.get()),
            )
        except ValueError as exc:
            raise ValueError("X, Y, and Z must be numeric motor-step values.") from exc

    def desired_corner_count(self) -> int:
        try:
            count = int(self.corner_count_var.get())
        except (TypeError, ValueError) as exc:
            raise ValueError("Corners to use must be a whole number from 3 to 8.") from exc
        if count < 3 or count > 8:
            raise ValueError("Corners to use must be between 3 and 8.")
        return count

    def corner_point_from_fields(self) -> Point3D:
        try:
            return Point3D(
                x=float(self.corner_x_var.get()),
                y=float(self.corner_y_var.get()),
                z=float(self.corner_z_var.get()),
            )
        except ValueError as exc:
            raise ValueError("Corner X, Y, and Z must be numeric values.") from exc

    def on_corner_count_changed(self) -> None:
        try:
            count = self.desired_corner_count()
        except Exception as exc:
            messagebox.showerror("Invalid corner count", str(exc))
            return

        self.log(f"Corner count set to {count}.")

    def add_corner(self) -> None:
        try:
            desired_count = self.desired_corner_count()
        except Exception as exc:
            messagebox.showerror("Invalid corner count", str(exc))
            return

        if len(self.corners) >= desired_count:
            messagebox.showinfo(
                "Corners complete",
                f"{desired_count} corners have already been added. Clear them to start over.",
            )
            return

        try:
            point = self.corner_point_from_fields()
        except Exception as exc:
            messagebox.showerror("Invalid corner", str(exc))
            return

        self.corners.append(point)
        self.refresh_corner_table()
        self.log(f"Added corner {len(self.corners)}: ({point.x:g}, {point.y:g}, {point.z:g})")

    def clear_corners(self) -> None:
        self.corners.clear()
        self.plane = None
        self.plane_var.set("Add three or more corners, then compute the chip plane.")
        self.pred_z_var.set("")
        self.refresh_corner_table()
        self.log("Cleared corners and plane.")

    def refresh_corner_table(self) -> None:
        for item in self.corner_tree.get_children():
            self.corner_tree.delete(item)

        for index, point in enumerate(self.corners):
            self.corner_tree.insert(
                "",
                "end",
                values=(f"C{index + 1}", f"{point.x:g}", f"{point.y:g}", f"{point.z:g}"),
            )

    def compute_plane(self) -> None:
        try:
            desired_count = self.desired_corner_count()
        except Exception as exc:
            messagebox.showerror("Invalid corner count", str(exc))
            return

        if len(self.corners) != desired_count:
            messagebox.showinfo(
                "Corners required",
                f"Add {desired_count} chip corners before computing the plane.",
            )
            return

        try:
            result = self.acquisition_service.compute_chip_plane(
                ComputeChipPlaneInput(
                    corners=[
                        Point3DInput(x=point.x, y=point.y, z=point.z)
                        for point in self.corners
                    ]
                )
            )
            self.plane = Plane(
                a=result.a,
                b=result.b,
                c=result.c,
                d=result.d,
            )
        except Exception as exc:
            messagebox.showerror("Plane error", str(exc))
            self.log(f"Plane error: {exc}")
            return

        equation = self.plane.as_equation()
        self.plane_var.set(equation)
        self.log(f"Computed chip plane: {equation}")

    def calculate_predicted_z(self) -> None:
        if self.plane is None:
            messagebox.showinfo("Plane required", "Compute a plane first.")
            return

        try:
            x = float(self.pred_x_var.get())
            y = float(self.pred_y_var.get())
            z = self.plane.z_at(x, y)
        except Exception as exc:
            messagebox.showerror("Z calculation failed", str(exc))
            return

        self.pred_z_var.set(f"{z:.6g}")
        self.log(f"Predicted Z at X={x:g}, Y={y:g}: {z:.6g}")

    def save_plane_json(self) -> None:
        if self.plane is None:
            messagebox.showinfo("Plane required", "Compute a plane before saving.")
            return

        default_dir = PROJECT_ROOT / "outputs"
        default_dir.mkdir(parents=True, exist_ok=True)

        path = filedialog.asksaveasfilename(
            initialdir=str(default_dir),
            initialfile="chip_plane.json",
            defaultextension=".json",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
        )
        if not path:
            return

        payload = {
            "version": 1,
            "corners": [point.to_dict() for point in self.corners],
            "plane": self.plane.to_dict(),
        }

        Path(path).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        self.log(f"Saved plane JSON: {path}")

    def read_stage_position_placeholder(self) -> None:
        result = self.acquisition_service.read_stage_position(StagePositionInput())
        messagebox.showinfo(
            "Stage position not wired yet",
            result.message,
        )
        self.log(result.message)

    def log_manual_position(self) -> None:
        try:
            point = self.current_point_from_fields()
        except Exception as exc:
            messagebox.showerror("Invalid position", str(exc))
            return
        self.log(f"Manual position set: X={point.x:g}, Y={point.y:g}, Z={point.z:g}")

    def copy_equation(self) -> None:
        text = self.plane_var.get()
        self.root.clipboard_clear()
        self.root.clipboard_append(text)
        self.log("Plane equation copied to clipboard.")

    def log(self, message: str) -> None:
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")


def main() -> None:
    root = tk.Tk()
    AcquisitionGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
