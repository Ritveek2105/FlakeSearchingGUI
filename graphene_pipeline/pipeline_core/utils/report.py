import json
from datetime import datetime
from pathlib import Path


class StageReport:
    def __init__(self, report_dir: Path, stage_name: str):
        report_dir.mkdir(parents=True, exist_ok=True)
        self.stage_name = stage_name
        self.report_path = report_dir / f"{stage_name}_report.json"
        self.data = {
            "stage": stage_name,
            "status": "running",
            "started_at": datetime.now().isoformat(timespec="seconds"),
        }

    def update(self, **kwargs):
        self.data.update(kwargs)
        self.save()

    def success(self, **kwargs):
        self.data.update(kwargs)
        self.data["status"] = "success"
        self.data["finished_at"] = datetime.now().isoformat(timespec="seconds")
        self.save()

    def failure(self, error: str, **kwargs):
        self.data.update(kwargs)
        self.data["status"] = "failed"
        self.data["error"] = str(error)
        self.data["finished_at"] = datetime.now().isoformat(timespec="seconds")
        self.save()

    def save(self):
        with open(self.report_path, "w", encoding="utf-8") as f:
            json.dump(self.data, f, indent=2)