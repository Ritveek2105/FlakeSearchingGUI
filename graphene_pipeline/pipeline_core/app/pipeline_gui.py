import json
import sys
import tkinter as tk
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox, scrolledtext, ttk


from config import PROJECT_DIR

PROJECT_ROOT = PROJECT_DIR


from pipeline_core.app.pipeline_service import PipelineService
from pipeline_core.runtime.run_config import (
    DetectionConfig,
    InputConfig,
    PublishConfig,
    RunConfig,
    SampleConfig,
    StitchingConfig,
)


class PipelineGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Graphene Pipeline")
        self.root.geometry("1100x850")
        self.root.minsize(900, 700)

        self.service = PipelineService(PROJECT_ROOT)
        self.current_job = None
        self.seen_event_count = 0

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

        self.stage_status_vars = {}
        self.progress_var = tk.DoubleVar(value=0)
        self.current_stage_var = tk.StringVar(value="Current Stage: Idle")
        self.elapsed_var = tk.StringVar(value="Elapsed: 0s")
        self.start_time = None

        self.raw_folder = tk.StringVar(value=str(PROJECT_ROOT / "data" / "raw_tiles"))
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
        self.first_tile_index = tk.StringVar(value="1")

        self.raw_pattern = tk.StringVar(value="{p}.jpg")
        self.corrected_pattern = tk.StringVar(value="{p}_corrected.tif")

        self.roboflow_confidence = tk.StringVar(value="0.35")
        self.roboflow_model_id = tk.StringVar(value="grapheneflakes-72y6l-szuyj/2")
        self.inference_tile_size = tk.StringVar(value="1024")
        self.inference_tile_overlap = tk.StringVar(value="200")

        self.build_ui()

    def build_ui(self):
        # ---------- Scrollable window ----------
        container = tk.Frame(self.root)
        container.pack(fill="both", expand=True)

        canvas = tk.Canvas(container, highlightthickness=0)
        scrollbar = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)

        frame = tk.Frame(canvas, padx=16, pady=16)

        frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )

        canvas.create_window((0, 0), window=frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

# Mouse wheel scrolling
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

        canvas.bind_all("<MouseWheel>", _on_mousewheel)
        

        title = tk.Label(frame, text="Graphene Pipeline Runner", font=("Arial", 18, "bold"))
        title.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 16))

        row = 1

        row = self.add_folder_row(frame, row, "Raw Tile Folder", self.raw_folder)
        row = self.add_entry_row(frame, row, "Sample Name", self.sample_name)
        row = self.add_entry_row(frame, row, "Material Type", self.material_type)
        row = self.add_entry_row(frame, row, "Objective", self.objective)
        row = self.add_entry_row(frame, row, "Camera", self.camera)
        row = self.add_entry_row(frame, row, "Operator", self.operator)
        row = self.add_entry_row(frame, row, "Notes", self.notes)

        self.add_section(frame, row, "Stitching Settings")
        row += 1

        row = self.add_entry_row(frame, row, "Grid Size X", self.grid_x)
        row = self.add_entry_row(frame, row, "Grid Size Y", self.grid_y)
        row = self.add_entry_row(frame, row, "Tile Overlap", self.tile_overlap)
        row = self.add_entry_row(frame, row, "Scan Order", self.scan_order)
        row = self.add_entry_row(frame, row, "First Tile Index", self.first_tile_index)
        row = self.add_entry_row(frame, row, "Raw File Pattern", self.raw_pattern)
        row = self.add_entry_row(frame, row, "Corrected File Pattern", self.corrected_pattern)

        self.add_section(frame, row, "Detection Settings")
        row += 1

        row = self.add_entry_row(frame, row, "Roboflow Confidence", self.roboflow_confidence)
        row = self.add_entry_row(frame, row, "Roboflow Model ID", self.roboflow_model_id)
        row = self.add_entry_row(frame, row, "Inference Tile Size", self.inference_tile_size)
        row = self.add_entry_row(frame, row, "Inference Tile Overlap", self.inference_tile_overlap)

        button_frame = tk.Frame(frame)
        button_frame.grid(row=row, column=0, columnspan=3, sticky="w", pady=16)

        self.validate_button = tk.Button(
            button_frame,
            text="Validate Settings",
            command=self.validate_settings,
            width=20,
        )
        self.validate_button.pack(side="left", padx=(0, 8))

        self.run_button = tk.Button(
            button_frame,
            text="Run Pipeline",
            command=self.run_pipeline,
            width=20,
        )
        self.run_button.pack(side="left", padx=(0, 8))

        self.cancel_button = tk.Button(
            button_frame,
            text="Cancel",
            command=self.cancel_pipeline,
            width=12,
            state="disabled",
        )
        self.cancel_button.pack(side="left")

        row += 1

        self.job_label = tk.Label(frame, text="Job: none", anchor="w")
        self.job_label.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 8))

        row += 1

        self.add_section(frame, row, "Progress Dashboard")
        row += 1

        dashboard = tk.Frame(frame, bd=1, relief="solid", padx=10, pady=10)
        dashboard.grid(row=row, column=0, columnspan=3, sticky="ew", pady=(0, 10))

        tk.Label(
            dashboard,
            textvariable=self.current_stage_var,
            font=("Arial", 11, "bold"),
        ).pack(anchor="w")

        self.progress_bar = ttk.Progressbar(
            dashboard,
            variable=self.progress_var,
            maximum=100,
        )
        self.progress_bar.pack(fill="x", pady=6)

        tk.Label(dashboard, textvariable=self.elapsed_var).pack(anchor="w")

        for stage_key in self.stage_order:
            var = tk.StringVar(value=f"□ {self.stage_labels[stage_key]}")
            self.stage_status_vars[stage_key] = var
            tk.Label(dashboard, textvariable=var, anchor="w").pack(anchor="w")

        row += 1

        self.output = scrolledtext.ScrolledText(frame, height=12, wrap="word")
        self.output.grid(row=row, column=0, columnspan=3, sticky="nsew")

        frame.columnconfigure(1, weight=1)
        frame.rowconfigure(row, weight=1)

    def add_section(self, frame, row, text):
        label = tk.Label(frame, text=text, font=("Arial", 12, "bold"))
        label.grid(row=row, column=0, columnspan=3, sticky="w", pady=(16, 6))

    def add_entry_row(self, frame, row, label_text, variable):
        label = tk.Label(frame, text=label_text)
        label.grid(row=row, column=0, sticky="w", pady=3)

        entry = tk.Entry(frame, textvariable=variable)
        entry.grid(row=row, column=1, columnspan=2, sticky="ew", pady=3)

        return row + 1

    def add_folder_row(self, frame, row, label_text, variable):
        label = tk.Label(frame, text=label_text)
        label.grid(row=row, column=0, sticky="w", pady=3)

        entry = tk.Entry(frame, textvariable=variable)
        entry.grid(row=row, column=1, sticky="ew", pady=3)

        button = tk.Button(frame, text="Browse", command=self.browse_raw_folder)
        button.grid(row=row, column=2, sticky="ew", padx=(6, 0), pady=3)

        return row + 1

    def browse_raw_folder(self):
        folder = filedialog.askdirectory(
            title="Select raw tile folder",
            initialdir=str(PROJECT_ROOT),
        )

        if folder:
            self.raw_folder.set(folder)

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
                grid_size_x=int(self.grid_x.get()),
                grid_size_y=int(self.grid_y.get()),
                tile_overlap=int(self.tile_overlap.get()),
                scan_order=self.scan_order.get(),
                first_tile_index=int(self.first_tile_index.get()),
            ),
            detection=DetectionConfig(
                roboflow_confidence=float(self.roboflow_confidence.get()),
                roboflow_model_id=self.roboflow_model_id.get(),
                tile_size=int(self.inference_tile_size.get()),
                tile_overlap=int(self.inference_tile_overlap.get()),
            ),
            publish=PublishConfig(
                mode="new",
                sample_id=None,
            ),
        )

    def reset_dashboard(self):
        self.progress_var.set(0)
        self.current_stage_var.set("Current Stage: Idle")
        self.elapsed_var.set("Elapsed: 0s")
        self.start_time = datetime.now()

        for stage_key in self.stage_order:
            self.stage_status_vars[stage_key].set(f"□ {self.stage_labels[stage_key]}")

    def update_dashboard_from_events(self, events):
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
                self.stage_status_vars[stage_key].set(f"❌ {label}")
            elif stage_key in completed:
                self.stage_status_vars[stage_key].set(f"✓ {label}")
            elif running == stage_key:
                self.stage_status_vars[stage_key].set(f"▶ {label}")
            else:
                self.stage_status_vars[stage_key].set(f"□ {label}")

        percent = (len(completed) / len(self.stage_order)) * 100
        self.progress_var.set(percent)

        if failed:
            self.current_stage_var.set(f"Current Stage: Failed at {self.stage_labels[failed]}")
        elif running:
            self.current_stage_var.set(f"Current Stage: {self.stage_labels[running]}")
        elif len(completed) == len(self.stage_order):
            self.current_stage_var.set("Current Stage: Complete")
        else:
            self.current_stage_var.set("Current Stage: Waiting")

        if self.start_time:
            elapsed = datetime.now() - self.start_time
            seconds = int(elapsed.total_seconds())
            self.elapsed_var.set(f"Elapsed: {seconds}s")

    def validate_settings(self) -> bool:
        self.output.delete("1.0", tk.END)

        try:
            config = self.build_run_config()
            result = self.service.validate(config)

            if result.ok:
                self.output.insert(tk.END, "Validation passed.\n\n")
            else:
                self.output.insert(tk.END, "Validation failed.\n\n")

            if result.errors:
                self.output.insert(tk.END, "Errors:\n")
                for error in result.errors:
                    self.output.insert(tk.END, f"  ❌ {error}\n")
                self.output.insert(tk.END, "\n")

            if result.warnings:
                self.output.insert(tk.END, "Warnings:\n")
                for warning in result.warnings:
                    self.output.insert(tk.END, f"  ⚠️ {warning}\n")
                self.output.insert(tk.END, "\n")

            return result.ok

        except Exception as e:
            self.output.insert(tk.END, f"GUI error:\n{e}\n")
            messagebox.showerror("Validation Error", str(e))
            return False

    def run_pipeline(self):
        self.output.delete("1.0", tk.END)

        try:
            config = self.build_run_config()
            result = self.service.validate(config)

            if not result.ok:
                self.output.insert(tk.END, "Validation failed. Pipeline was not started.\n\n")
                for error in result.errors:
                    self.output.insert(tk.END, f"  ❌ {error}\n")
                return

            if result.warnings:
                self.output.insert(tk.END, "Warnings:\n")
                for warning in result.warnings:
                    self.output.insert(tk.END, f"  ⚠️ {warning}\n")
                self.output.insert(tk.END, "\n")

            skip_copy = Path(config.input.raw_folder).resolve() == (
                PROJECT_ROOT / "data" / "raw_tiles"
            ).resolve()

            self.reset_dashboard()

            self.current_job = self.service.start_background(
                config=config,
                skip_copy=skip_copy,
            )

            self.seen_event_count = 0
            self.job_label.config(text=f"Job: {self.current_job.job_id}")
            self.output.insert(tk.END, f"Started pipeline job: {self.current_job.job_id}\n")
            self.output.insert(tk.END, f"Run folder: {self.current_job.run_dir}\n\n")

            self.run_button.config(state="disabled")
            self.validate_button.config(state="disabled")
            self.cancel_button.config(state="normal")

            self.poll_status()

        except Exception as e:
            self.output.insert(tk.END, f"Failed to start pipeline:\n{e}\n")
            messagebox.showerror("Pipeline Error", str(e))

    def poll_status(self):
        if not self.current_job:
            return

        status_path = self.current_job.status_path

        if status_path.exists():
            try:
                with open(status_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                events = data.get("events", [])
                self.update_dashboard_from_events(events)

                new_events = events[self.seen_event_count:]

                for event in new_events:
                    line = (
                        f"[{event.get('time', '')}] "
                        f"{event.get('stage', '')} "
                        f"{event.get('status', '')}: "
                        f"{event.get('message', '')}\n"
                    )
                    self.output.insert(tk.END, line)
                    self.output.see(tk.END)

                self.seen_event_count = len(events)

            except Exception as e:
                self.output.insert(tk.END, f"Could not read status.json: {e}\n")

        process = self.current_job.process

        if process and process.poll() is not None:
            return_code = process.returncode

            if return_code == 0:
                self.progress_var.set(100)
                self.current_stage_var.set("Current Stage: Complete")
                self.output.insert(tk.END, "\nPipeline complete.\n")
                messagebox.showinfo("Pipeline Complete", "Pipeline finished successfully.")
            else:
                self.output.insert(tk.END, f"\nPipeline failed. Return code: {return_code}\n")
                messagebox.showerror(
                    "Pipeline Failed",
                    f"Pipeline failed with return code {return_code}.",
                )

            self.run_button.config(state="normal")
            self.validate_button.config(state="normal")
            self.cancel_button.config(state="disabled")
            return

        self.root.after(2000, self.poll_status)

    def cancel_pipeline(self):
        if not self.current_job:
            return

        try:
            self.service.cancel(self.current_job.job_id)
            self.output.insert(tk.END, "\nCancel requested.\n")
            self.current_stage_var.set("Current Stage: Cancel requested")
            self.cancel_button.config(state="disabled")
        except Exception as e:
            messagebox.showerror("Cancel Error", str(e))


def main():
    root = tk.Tk()
    PipelineGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
