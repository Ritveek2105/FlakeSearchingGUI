from __future__ import annotations

import tkinter as tk
from datetime import datetime
from tkinter import ttk

from .styles import PANEL, SECTION_FONT, STATUS_FONT
from .utils import format_elapsed, status_icon


class ProgressPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(
            parent,
            bg=PANEL,
            bd=1,
            relief="solid",
            padx=10,
            pady=10,
        )

        self.stage_order = [
            "validation",
            "input",
            "stage1",
            "stage1_5",
            "stage2",
            "stage3",
            "stage5",
            "stage6",
        ]

        self.stage_labels = {
            "validation": "Validation",
            "input": "Input Copy",
            "stage1": "Stage 1: Tile Correction",
            "stage1_5": "Stage 1.5: Stitching",
            "stage2": "Stage 2: Global Correction",
            "stage3": "Stage 3: Detection",
            "stage5": "Stage 5: DZI Generation",
            "stage6": "Stage 6: Publish",
        }

        self.stage_status_vars: dict[str, tk.StringVar] = {}
        self.progress_var = tk.DoubleVar(value=0)
        self.current_stage_var = tk.StringVar(value="Current Stage: Idle")
        self.elapsed_var = tk.StringVar(value="Elapsed: 0s")
        self.start_time: datetime | None = None

        self.build()

    def build(self) -> None:
        title = tk.Label(
            self,
            text="Progress Dashboard",
            font=SECTION_FONT,
            bg=PANEL,
        )
        title.pack(anchor="w", pady=(0, 4))

        current = tk.Label(
            self,
            textvariable=self.current_stage_var,
            font=STATUS_FONT,
            bg=PANEL,
        )
        current.pack(anchor="w")

        self.progress_bar = ttk.Progressbar(
            self,
            variable=self.progress_var,
            maximum=100,
        )
        self.progress_bar.pack(fill="x", pady=4)

        elapsed = tk.Label(
            self,
            textvariable=self.elapsed_var,
            bg=PANEL,
        )
        elapsed.pack(anchor="w", pady=(0, 4))

        for stage_key in self.stage_order:
            var = tk.StringVar(value=f"{status_icon('idle')} {self.stage_labels[stage_key]}")
            self.stage_status_vars[stage_key] = var

            label = tk.Label(
                self,
                textvariable=var,
                anchor="w",
                bg=PANEL,
            )
            label.pack(anchor="w", pady=1)

    def reset(self) -> None:
        self.progress_var.set(0)
        self.current_stage_var.set("Current Stage: Idle")
        self.elapsed_var.set("Elapsed: 0s")
        self.start_time = datetime.now()

        for stage_key in self.stage_order:
            self.stage_status_vars[stage_key].set(
                f"{status_icon('idle')} {self.stage_labels[stage_key]}"
            )

    def update_from_events(self, events: list[dict]) -> None:
        completed = set()
        running = None
        failed = None

        for event in events:
            stage = event.get("stage")
            status = event.get("status")

            if stage not in self.stage_order:
                continue

            if status == "started":
                running = stage

            if status in ("complete", "skipped"):
                completed.add(stage)

            if status == "failed":
                failed = stage

        for stage_key in self.stage_order:
            label = self.stage_labels[stage_key]

            if failed == stage_key:
                self.stage_status_vars[stage_key].set(
                    f"{status_icon('failed')} {label}"
                )
            elif stage_key in completed:
                self.stage_status_vars[stage_key].set(
                    f"{status_icon('complete')} {label}"
                )
            elif running == stage_key:
                self.stage_status_vars[stage_key].set(
                    f"{status_icon('running')} {label}"
                )
            else:
                self.stage_status_vars[stage_key].set(
                    f"{status_icon('idle')} {label}"
                )

        percent = (len(completed) / len(self.stage_order)) * 100
        self.progress_var.set(percent)

        if failed:
            self.current_stage_var.set(
                f"Current Stage: Failed at {self.stage_labels[failed]}"
            )
        elif running:
            self.current_stage_var.set(
                f"Current Stage: {self.stage_labels[running]}"
            )
        elif len(completed) == len(self.stage_order):
            self.current_stage_var.set("Current Stage: Complete")
        else:
            self.current_stage_var.set("Current Stage: Waiting")

        self.elapsed_var.set(format_elapsed(self.start_time))

    def mark_complete(self) -> None:
        self.progress_var.set(100)
        self.current_stage_var.set("Current Stage: Complete")
        self.elapsed_var.set(format_elapsed(self.start_time))

    def mark_cancel_requested(self) -> None:
        self.current_stage_var.set("Current Stage: Cancel requested")