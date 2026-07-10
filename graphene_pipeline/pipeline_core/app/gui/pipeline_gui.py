from __future__ import annotations
import os
import json
import sys
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from config import PROJECT_DIR

PROJECT_ROOT = PROJECT_DIR

from pipeline_core.app.gui.form_panel import FormPanel
from pipeline_core.app.gui.log_panel import LogPanel
from pipeline_core.app.gui.progress_panel import ProgressPanel
from pipeline_core.app.gui.styles import (
    BACKGROUND,
    MIN_HEIGHT,
    MIN_WIDTH,
    PANEL,
    TITLE_FONT,
    WINDOW_HEIGHT,
    WINDOW_TITLE,
    WINDOW_WIDTH,
)
from pipeline_core.app.pipeline_service import PipelineService
from pipeline_core.app.gui.profile_manager import ProfileManager



class PipelineGUI:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(WINDOW_TITLE)
        self.root.geometry(f"{WINDOW_WIDTH}x{WINDOW_HEIGHT}")
        self.root.minsize(MIN_WIDTH, MIN_HEIGHT)
        self.root.configure(bg=BACKGROUND)

        self.service = PipelineService(PROJECT_ROOT)
        self.profile_manager = ProfileManager(PROJECT_ROOT)
        self.current_job = None
        self.seen_event_count = 0

        self.open_acquisition_button = None
        self.open_website_button = None
        self.open_samples_button = None
        self.open_run_button = None
        self.run_another_button = None

        self.build_ui()

    def build_ui(self) -> None:
        header = tk.Frame(self.root, bg=BACKGROUND, padx=16, pady=12)
        header.pack(fill="x")

        title = tk.Label(
            header,
            text="Graphene Pipeline Runner",
            font=TITLE_FONT,
            bg=BACKGROUND,
        )
        title.pack(anchor="w")

        main = tk.Frame(self.root, bg=BACKGROUND, padx=16, pady=16)
        main.pack(fill="both", expand=True)

        main.columnconfigure(0, weight=1)
        main.columnconfigure(1, weight=3)
        main.rowconfigure(0, weight=1)

        self.form_panel = FormPanel(
            main,
            project_root=PROJECT_ROOT,
            on_validate=self.validate_settings,
            on_run=self.run_pipeline,
            on_cancel=self.cancel_pipeline,
            on_save_profile=self.save_profile,
            on_load_profile=self.load_profile,
            on_set_api_key=self.set_roboflow_api_key,
        )

        self.form_panel.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        right = tk.Frame(main, bg=BACKGROUND)
        right.grid(row=0, column=1, sticky="nsew")
        right.rowconfigure(3, weight=0)
        right.columnconfigure(0, weight=1)

        self.job_label = tk.Label(
            right,
            text="Job: none",
            anchor="w",
            bg=BACKGROUND,
        )
        self.job_label.grid(row=0, column=0, sticky="ew", pady=(0, 8))

        self.progress_panel = ProgressPanel(right)
        self.progress_panel.grid(
        row=1,
        column=0,
        sticky="ew",
        pady=(0,5),
    )

        self.actions_frame = tk.Frame(right, bg=BACKGROUND)
        self.actions_frame.grid(row=2, column=0, sticky="ew", pady=(0, 10))
        self.build_completion_actions()

        log_container = tk.Frame(right, bg=PANEL, bd=1, relief="solid")
        log_container.grid(row=3, column=0, sticky="nsew")
        log_container.configure(height=220)
        log_container.grid_propagate(False)
        log_container.rowconfigure(0, weight=1)
        log_container.columnconfigure(0, weight=1)

        self.log_panel = LogPanel(log_container)
        self.log_panel.grid(row=0, column=0, sticky="nsew")

    def build_completion_actions(self) -> None:
        self.open_acquisition_button = tk.Button(
            self.actions_frame,
            text="Open Acquisition Console",
            command=self.open_acquisition_console,
            state="normal",
            width=24,
        )
        self.open_acquisition_button.pack(side="left", padx=(0, 8))

        self.open_website_button = tk.Button(
            self.actions_frame,
            text="Open Website",
            command=self.open_website,
            state="disabled",
            width=18,
        )
        self.open_website_button.pack(side="left", padx=(0, 8))

        self.open_samples_button = tk.Button(
            self.actions_frame,
            text="Open Samples Folder",
            command=self.open_samples_folder,
            state="disabled",
            width=20,
        )
        self.open_samples_button.pack(side="left", padx=(0, 8))

        self.open_run_button = tk.Button(
            self.actions_frame,
            text="Open Run Folder",
            command=self.open_run_folder,
            state="disabled",
            width=18,
        )
        self.open_run_button.pack(side="left", padx=(0, 8))

        self.run_another_button = tk.Button(
            self.actions_frame,
            text="Run Another",
            command=self.reset_for_next_run,
            state="disabled",
            width=16,
        )
        self.run_another_button.pack(side="left")

    def set_completion_actions_enabled(self, enabled: bool) -> None:
        state = "normal" if enabled else "disabled"

        self.open_website_button.config(state=state)
        self.open_samples_button.config(state=state)
        self.open_run_button.config(state=state)
        self.run_another_button.config(state=state)

    def validate_settings(self) -> bool:
        self.log_panel.clear()

        try:
            config = self.form_panel.build_run_config()
            result = self.service.validate(config)

            if result.ok:
                self.log_panel.success("Validation passed.")
            else:
                self.log_panel.error("Validation failed.")

            if result.errors:
                self.log_panel.separator()
                self.log_panel.log("Errors:")
                for error in result.errors:
                    self.log_panel.error(error)

            if result.warnings:
                self.log_panel.separator()
                self.log_panel.log("Warnings:")
                for warning in result.warnings:
                    self.log_panel.warning(warning)

            return result.ok

        except Exception as e:
            self.log_panel.error(f"GUI validation error: {e}")
            messagebox.showerror("Validation Error", str(e))
            return False

    def run_pipeline(self) -> None:
        self.log_panel.clear()
        self.set_completion_actions_enabled(False)

        try:
            config = self.form_panel.build_run_config()
            result = self.service.validate(config)

            if not result.ok:
                self.log_panel.error("Validation failed. Pipeline was not started.")

                for error in result.errors:
                    self.log_panel.error(error)

                return

            if result.warnings:
                self.log_panel.log("Warnings:")
                for warning in result.warnings:
                    self.log_panel.warning(warning)

                self.log_panel.separator()

            skip_copy = Path(config.input.raw_folder).resolve() == (
                PROJECT_ROOT / "data" / "raw_tiles"
            ).resolve()

            self.progress_panel.reset()

            self.current_job = self.service.start_background(
                config=config,
                skip_copy=skip_copy,
            )

            self.seen_event_count = 0

            self.job_label.config(text=f"Job: {self.current_job.job_id}")

            self.log_panel.success(f"Started pipeline job: {self.current_job.job_id}")
            self.log_panel.log(f"Run folder: {self.current_job.run_dir}")
            self.log_panel.separator()

            self.form_panel.set_running(True)

            self.poll_status()

        except Exception as e:
            self.log_panel.error(f"Failed to start pipeline: {e}")
            messagebox.showerror("Pipeline Error", str(e))
            self.form_panel.set_running(False)

    def poll_status(self) -> None:
        if not self.current_job:
            return

        status_path = self.current_job.status_path

        if status_path.exists():
            try:
                with open(status_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                events = data.get("events", [])
                self.progress_panel.update_from_events(events)

                new_events = events[self.seen_event_count:]

                for event in new_events:
                    self.log_panel.append_status_event(event)

                self.seen_event_count = len(events)

            except Exception as e:
                self.log_panel.error(f"Could not read status.json: {e}")

        process = self.current_job.process

        if process and process.poll() is not None:
            return_code = process.returncode

            if return_code == 0:
                self.progress_panel.mark_complete()
                self.log_panel.separator()
                self.log_panel.success("Pipeline complete.")
                self.set_completion_actions_enabled(True)
                messagebox.showinfo(
                    "Pipeline Complete",
                    "Pipeline finished successfully.",
                )
            else:
                self.log_panel.separator()
                self.log_panel.error(f"Pipeline failed. Return code: {return_code}")
                self.open_run_button.config(state="normal")
                messagebox.showerror(
                    "Pipeline Failed",
                    f"Pipeline failed with return code {return_code}.",
                )

            self.form_panel.set_running(False)
            return

        self.root.after(2000, self.poll_status)

    def set_roboflow_api_key(self) -> None:
        key = self.form_panel.roboflow_api_key.get().strip()

        if not key:
            messagebox.showwarning("Roboflow API Key", "No API key entered.")
            return

        os.environ["ROBOFLOW_API_KEY"] = key
        self.log_panel.success("Roboflow API key set for this GUI session.")

    def cancel_pipeline(self) -> None:
        if not self.current_job:
            return

        try:
            self.service.cancel(self.current_job.job_id)
            self.log_panel.warning("Cancel requested.")
            self.progress_panel.mark_cancel_requested()
            self.form_panel.cancel_button.config(state="disabled")
            self.open_run_button.config(state="normal")
        except Exception as e:
            messagebox.showerror("Cancel Error", str(e))

    def open_acquisition_console(self) -> None:
        try:
            subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "pipeline_core.app.acquisition.acquisition_gui",
                ],
                cwd=PROJECT_ROOT,
            )
            self.log_panel.success("Opened Acquisition Console.")
        except Exception as e:
            messagebox.showerror("Open Acquisition Console Error", str(e))

    def open_website(self) -> None:
        try:
            self.service.open_website()
        except Exception as e:
            messagebox.showerror("Open Website Error", str(e))

    def open_samples_folder(self) -> None:
        try:
            self.service.open_samples_folder()
        except Exception as e:
            messagebox.showerror("Open Samples Folder Error", str(e))

    def open_run_folder(self) -> None:
        if not self.current_job:
            return

        try:
            self.service.open_run_folder(self.current_job)
        except Exception as e:
            messagebox.showerror("Open Run Folder Error", str(e))
    
    def save_profile(self) -> None:
        try:
            config = self.form_panel.build_run_config()
            self.profile_manager.save_profile(config)
            self.log_panel.success("Profile saved.")
        except Exception as e:
            messagebox.showerror("Save Profile", str(e))

    def load_profile(self) -> None:
        try:
            config = self.profile_manager.load_profile()

            if config is None:
                return

            self.form_panel.apply_run_config(config)
            self.log_panel.success("Profile loaded.")

        except Exception as e:
            messagebox.showerror("Load Profile", str(e))

    def reset_for_next_run(self) -> None:
        self.current_job = None
        self.seen_event_count = 0
        self.job_label.config(text="Job: none")
        self.progress_panel.reset()
        self.log_panel.clear()
        self.set_completion_actions_enabled(False)
        self.form_panel.set_running(False)


def main() -> None:
    root = tk.Tk()
    PipelineGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
