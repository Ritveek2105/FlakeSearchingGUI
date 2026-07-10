from datetime import datetime
from pathlib import Path


class PipelineLogger:
    def __init__(self, log_dir: Path):
        log_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        self.log_path = log_dir / f"pipeline_{timestamp}.log"

    def info(self, message: str):
        line = f"[INFO] {datetime.now().strftime('%H:%M:%S')} - {message}"
        print(line)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def warning(self, message: str):
        line = f"[WARNING] {datetime.now().strftime('%H:%M:%S')} - {message}"
        print(line)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")

    def error(self, message: str):
        line = f"[ERROR] {datetime.now().strftime('%H:%M:%S')} - {message}"
        print(line)
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line + "\n")