import json
from datetime import datetime
from pathlib import Path


class ProgressManager:
    def __init__(self, status_path: Path):
        self.status_path = status_path
        self.events: list[dict] = []

    def add(self, stage: str, status: str, message: str = "") -> None:
        event = {
            "time": datetime.now().isoformat(timespec="seconds"),
            "stage": stage,
            "status": status,
            "message": message,
        }

        self.events.append(event)
        self.status_path.parent.mkdir(parents=True, exist_ok=True)
        temp_path = self.status_path.with_suffix(".tmp")

        with open(temp_path, "w", encoding="utf-8") as f:
            json.dump({"events": self.events}, f, indent=2)

        temp_path.replace(self.status_path)

        print(f"[{stage}] {status}: {message}", flush=True)
