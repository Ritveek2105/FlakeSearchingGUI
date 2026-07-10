from __future__ import annotations

import tkinter as tk
from pathlib import Path

from pipeline_core.runtime.run_config import (
    DetectionConfig,
    InputConfig,
    PublishConfig,
    RunConfig,
    SampleConfig,
    StitchingConfig,
)

from .styles import BUTTON_WIDTH, ENTRY_WIDTH, LABEL_FONT, PANEL, SECTION_FONT
from .utils import browse_for_folder, safe_float, safe_int


class FormPanel(tk.Frame):
    def __init__(
        self,
        parent,
        project_root: Path,
        on_validate,
        on_run,
        on_cancel,
        on_save_profile,
        on_load_profile,
        on_set_api_key,
    ):
        super().__init__(parent, bg=PANEL, bd=1, relief="solid")

        self.project_root = project_root
        self.on_validate = on_validate
        self.on_run = on_run
        self.on_cancel = on_cancel
        self.on_save_profile = on_save_profile
        self.on_load_profile = on_load_profile
        self.on_set_api_key = on_set_api_key

        self.canvas = tk.Canvas(self, bg=PANEL, highlightthickness=0)
        self.scrollbar = tk.Scrollbar(
            self,
            orient="vertical",
            command=self.canvas.yview,
        )
        self.horizontal_scrollbar = tk.Scrollbar(
            self,
            orient="horizontal",
            command=self.canvas.xview,
        )

        self.canvas.configure(
            xscrollcommand=self.horizontal_scrollbar.set,
            yscrollcommand=self.scrollbar.set,
        )
        self.scrollbar.pack(side="right", fill="y")
        self.horizontal_scrollbar.pack(side="bottom", fill="x")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.content = tk.Frame(self.canvas, bg=PANEL, padx=12, pady=12)
        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.content,
            anchor="nw",
        )

        self.content.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )

        def resize_canvas(event):
            content_width = max(event.width, self.content.winfo_reqwidth())
            self.canvas.itemconfigure(self.canvas_window, width=content_width)
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        self.canvas.bind("<Configure>", resize_canvas)

        def mousewheel(event):
            self.canvas.yview_scroll(int(-event.delta / 120), "units")

        self.canvas.bind_all("<MouseWheel>", mousewheel)

        self.raw_folder = tk.StringVar(value=str(project_root / "data" / "raw_tiles"))
        self.sample_name = tk.StringVar(value="")
        self.material_type = tk.StringVar(value="graphene")
        self.objective = tk.StringVar(value="20x")
        self.camera = tk.StringVar(value="AmScope MU1203-BI")
        self.operator = tk.StringVar(value="Jason Zheng")
        self.notes = tk.StringVar(value="")

        self.grid_x = tk.StringVar(value="3")
        self.grid_y = tk.StringVar(value="1")
        self.tile_overlap = tk.StringVar(value="40")
        self.scan_order = tk.StringVar(value="HORIZONTALCONTINUOUS")
        self.grid_origin = tk.StringVar(value="UL")
        self.first_tile_index = tk.StringVar(value="1")

        self.raw_pattern = tk.StringVar(value="{p}.jpg")
        self.corrected_pattern = tk.StringVar(value="{p}_corrected.tif")

        self.detection_mode = tk.StringVar(value="manual")
        self.roboflow_confidence = tk.StringVar(value="0.35")
        self.roboflow_model_id = tk.StringVar(value="grapheneflakes-72y6l-szuyj/2")
        self.roboflow_api_key = tk.StringVar(value="")
        self.inference_tile_size = tk.StringVar(value="1024")
        self.inference_tile_overlap = tk.StringVar(value="200")

        self.roboflow_rows: list[tk.Widget] = []

        self.build()
        self.update_detection_visibility()

    def build(self) -> None:
        row = 0

        self.add_section(row, "Sample Information")
        row += 1

        row = self.add_folder_row(row, "Raw Tile Folder", self.raw_folder)
        row = self.add_entry_row(row, "Sample Name", self.sample_name)
        row = self.add_entry_row(row, "Material Type", self.material_type)
        row = self.add_entry_row(row, "Objective", self.objective)
        row = self.add_entry_row(row, "Camera", self.camera)
        row = self.add_entry_row(row, "Operator", self.operator)
        row = self.add_entry_row(row, "Notes", self.notes)

        self.add_section(row, "Stitching Settings")
        row += 1

        row = self.add_entry_row(row, "Grid Size X", self.grid_x)
        row = self.add_entry_row(row, "Grid Size Y", self.grid_y)
        row = self.add_entry_row(row, "Tile Overlap", self.tile_overlap)
        row = self.add_entry_row(row, "Scan Order", self.scan_order)
        row = self.add_dropdown_row(row, "Grid Origin", self.grid_origin, ["UL", "UR", "LL", "LR"])
        row = self.add_entry_row(row, "First Tile Index", self.first_tile_index)
        row = self.add_entry_row(row, "Raw File Pattern", self.raw_pattern)
        row = self.add_entry_row(row, "Corrected File Pattern", self.corrected_pattern)

        self.add_section(row, "Detection Settings")
        row += 1

        row = self.add_dropdown_row(
            row,
            "Detection Mode",
            self.detection_mode,
            ["manual", "roboflow"],
            command=lambda *_: self.update_detection_visibility(),
        )

        self.manual_note = tk.Label(
            self.content,
            text="Manual mode skips Roboflow. You will add annotations on the website after publishing.",
            font=LABEL_FONT,
            bg=PANEL,
            wraplength=360,
            justify="left",
        )
        self.manual_note.grid(row=row, column=0, columnspan=3, sticky="w", pady=(4, 8))
        row += 1

        row = self.add_entry_row(row, "Roboflow Confidence", self.roboflow_confidence, track="roboflow")
        row = self.add_entry_row(row, "Roboflow Model ID", self.roboflow_model_id, track="roboflow")
        row = self.add_password_row(row, "Roboflow API Key", self.roboflow_api_key, track="roboflow")
        row = self.add_entry_row(row, "Inference Tile Size", self.inference_tile_size, track="roboflow")
        row = self.add_entry_row(row, "Inference Tile Overlap", self.inference_tile_overlap, track="roboflow")

        self.add_section(row, "Profiles")
        row += 1

        profile_frame = tk.Frame(self.content, bg=PANEL)
        profile_frame.grid(row=row, column=0, columnspan=3, sticky="w", pady=(4, 10))

        self.save_profile_button = tk.Button(
            profile_frame,
            text="Save Profile",
            width=BUTTON_WIDTH,
            command=self.on_save_profile,
        )
        self.save_profile_button.pack(side="left", padx=(0, 8))

        self.load_profile_button = tk.Button(
            profile_frame,
            text="Load Profile",
            width=BUTTON_WIDTH,
            command=self.on_load_profile,
        )
        self.load_profile_button.pack(side="left")

        row += 1

        button_frame = tk.Frame(self.content, bg=PANEL)
        button_frame.grid(row=row, column=0, columnspan=3, sticky="w", pady=(14, 0))

        self.validate_button = tk.Button(
            button_frame,
            text="Validate",
            width=BUTTON_WIDTH,
            command=self.on_validate,
        )
        self.validate_button.pack(side="left", padx=(0, 8))

        self.set_api_key_button = tk.Button(
            button_frame,
            text="Set API Key",
            width=BUTTON_WIDTH,
            command=self.on_set_api_key,
        )
        self.set_api_key_button.pack(side="left", padx=(0, 8))

        self.run_button = tk.Button(
            button_frame,
            text="Run Pipeline",
            width=BUTTON_WIDTH,
            command=self.on_run,
        )
        self.run_button.pack(side="left", padx=(0, 8))

        self.cancel_button = tk.Button(
            button_frame,
            text="Cancel",
            width=12,
            command=self.on_cancel,
            state="disabled",
        )
        self.cancel_button.pack(side="left")

        self.content.columnconfigure(1, weight=1)

    def update_detection_visibility(self) -> None:
        mode = self.detection_mode.get().lower().strip()

        if mode == "manual":
            self.manual_note.grid()
            for widget in self.roboflow_rows:
                widget.grid_remove()
        else:
            self.manual_note.grid_remove()
            for widget in self.roboflow_rows:
                widget.grid()

    def add_section(self, row: int, text: str) -> None:
        label = tk.Label(self.content, text=text, font=SECTION_FONT, bg=PANEL)
        label.grid(row=row, column=0, columnspan=3, sticky="w", pady=(14, 6))

    def add_password_row(
        self,
        row: int,
        label_text: str,
        variable: tk.StringVar,
        track: str | None = None,
    ) -> int:
        label = tk.Label(self.content, text=label_text, font=LABEL_FONT, bg=PANEL)
        label.grid(row=row, column=0, sticky="w", pady=3)

        entry = tk.Entry(
            self.content,
            textvariable=variable,
            width=ENTRY_WIDTH,
            show="*",
        )
        entry.grid(row=row, column=1, columnspan=2, sticky="ew", pady=3)

        if track == "roboflow":
            self.roboflow_rows.extend([label, entry])

        return row + 1

    def add_entry_row(
        self,
        row: int,
        label_text: str,
        variable: tk.StringVar,
        track: str | None = None,
    ) -> int:
        label = tk.Label(self.content, text=label_text, font=LABEL_FONT, bg=PANEL)
        label.grid(row=row, column=0, sticky="w", pady=3)

        entry = tk.Entry(self.content, textvariable=variable, width=ENTRY_WIDTH)
        entry.grid(row=row, column=1, columnspan=2, sticky="ew", pady=3)

        if track == "roboflow":
            self.roboflow_rows.extend([label, entry])

        return row + 1

    def add_dropdown_row(
        self,
        row: int,
        label_text: str,
        variable: tk.StringVar,
        values: list[str],
        command=None,
    ) -> int:
        label = tk.Label(self.content, text=label_text, font=LABEL_FONT, bg=PANEL)
        label.grid(row=row, column=0, sticky="w", pady=3)

        dropdown = tk.OptionMenu(self.content, variable, *values, command=command)
        dropdown.grid(row=row, column=1, columnspan=2, sticky="ew", pady=3)

        return row + 1

    def add_folder_row(self, row: int, label_text: str, variable: tk.StringVar) -> int:
        label = tk.Label(self.content, text=label_text, font=LABEL_FONT, bg=PANEL)
        label.grid(row=row, column=0, sticky="w", pady=3)

        entry = tk.Entry(self.content, textvariable=variable, width=ENTRY_WIDTH)
        entry.grid(row=row, column=1, sticky="ew", pady=3)

        button = tk.Button(self.content, text="Browse", command=self.browse_raw_folder)
        button.grid(row=row, column=2, sticky="ew", padx=(6, 0), pady=3)

        return row + 1

    def browse_raw_folder(self) -> None:
        folder = browse_for_folder(self.project_root)

        if folder:
            self.raw_folder.set(folder)

    def set_running(self, running: bool) -> None:
        if running:
            self.run_button.config(state="disabled")
            self.validate_button.config(state="disabled")
            self.save_profile_button.config(state="disabled")
            self.load_profile_button.config(state="disabled")
            self.cancel_button.config(state="normal")
        else:
            self.run_button.config(state="normal")
            self.validate_button.config(state="normal")
            self.save_profile_button.config(state="normal")
            self.load_profile_button.config(state="normal")
            self.cancel_button.config(state="disabled")

    def build_run_config(self) -> RunConfig:
        return RunConfig(
            sample=SampleConfig(
                sample_name=self.sample_name.get(),
                material_type=self.material_type.get(),
                objective=self.objective.get(),
                camera=self.camera.get(),
                operator=self.operator.get(),
                notes=self.notes.get(),
            ),
            input=InputConfig(
                raw_folder=self.raw_folder.get(),
                raw_file_pattern=self.raw_pattern.get(),
                corrected_file_pattern=self.corrected_pattern.get(),
            ),
            stitching=StitchingConfig(
                grid_size_x=safe_int(self.grid_x.get(), 1),
                grid_size_y=safe_int(self.grid_y.get(), 1),
                tile_overlap=safe_int(self.tile_overlap.get(), 40),
                scan_order=self.scan_order.get(),
                grid_origin=self.grid_origin.get(),
                first_tile_index=safe_int(self.first_tile_index.get(), 1),
            ),
            detection=DetectionConfig(
                mode=self.detection_mode.get(),
                roboflow_confidence=safe_float(self.roboflow_confidence.get(), 0.35),
                roboflow_model_id=self.roboflow_model_id.get(),
                tile_size=safe_int(self.inference_tile_size.get(), 1024),
                tile_overlap=safe_int(self.inference_tile_overlap.get(), 200),
            ),
            publish=PublishConfig(
                mode="new",
                sample_id=None,
            ),
        )

    def apply_run_config(self, config: RunConfig) -> None:
        self.sample_name.set(config.sample.sample_name)
        self.material_type.set(config.sample.material_type)
        self.objective.set(config.sample.objective)
        self.camera.set(config.sample.camera)
        self.operator.set(config.sample.operator)
        self.notes.set(config.sample.notes)

        self.raw_folder.set(config.input.raw_folder)
        self.raw_pattern.set(config.input.raw_file_pattern)
        self.corrected_pattern.set(config.input.corrected_file_pattern)

        self.grid_x.set(str(config.stitching.grid_size_x))
        self.grid_y.set(str(config.stitching.grid_size_y))
        self.tile_overlap.set(str(config.stitching.tile_overlap))
        self.scan_order.set(config.stitching.scan_order)
        self.grid_origin.set(config.stitching.grid_origin)
        self.first_tile_index.set(str(config.stitching.first_tile_index))

        self.detection_mode.set(config.detection.mode)
        self.roboflow_confidence.set(str(config.detection.roboflow_confidence))
        self.roboflow_model_id.set(config.detection.roboflow_model_id)
        self.inference_tile_size.set(str(config.detection.tile_size))
        self.inference_tile_overlap.set(str(config.detection.tile_overlap))

        self.update_detection_visibility()
