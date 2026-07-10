"""
Shared GUI utility functions.

These helpers are intentionally independent of the rest of the GUI
so they can be reused by multiple panels.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from tkinter import filedialog


# ---------------------------------------------------------
# Folder Browsing
# ---------------------------------------------------------

def browse_for_folder(initial_dir: Path | str) -> str | None:
    """
    Open a folder browser.

    Returns
    -------
    str | None
        Selected folder path or None if cancelled.
    """

    folder = filedialog.askdirectory(
        title="Select Folder",
        initialdir=str(initial_dir),
    )

    if folder:
        return folder

    return None


# ---------------------------------------------------------
# Formatting
# ---------------------------------------------------------

def format_elapsed(start_time: datetime | None) -> str:
    """
    Convert a start time into a readable elapsed string.
    """

    if start_time is None:
        return "Elapsed: 0s"

    elapsed = datetime.now() - start_time

    total = int(elapsed.total_seconds())

    hours = total // 3600
    minutes = (total % 3600) // 60
    seconds = total % 60

    if hours > 0:
        return f"Elapsed: {hours:d}h {minutes:02d}m {seconds:02d}s"

    if minutes > 0:
        return f"Elapsed: {minutes:d}m {seconds:02d}s"

    return f"Elapsed: {seconds:d}s"


# ---------------------------------------------------------
# Safe conversions
# ---------------------------------------------------------

def safe_int(value: str, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def safe_float(value: str, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------
# Status icons
# ---------------------------------------------------------

STATUS_ICONS = {
    "idle": "□",
    "running": "▶",
    "complete": "✓",
    "warning": "⚠",
    "failed": "❌",
}


def status_icon(status: str) -> str:
    """
    Return a unicode icon for a pipeline status.
    """

    return STATUS_ICONS.get(status.lower(), "□")


# ---------------------------------------------------------
# Path helpers
# ---------------------------------------------------------

def project_relative(project_root: Path, path: Path) -> str:
    """
    Convert an absolute path into a project-relative path
    when possible.
    """

    try:
        return str(path.relative_to(project_root))
    except ValueError:
        return str(path)


# ---------------------------------------------------------
# Logging
# ---------------------------------------------------------

def timestamp() -> str:
    """
    Current time formatted for GUI log messages.
    """

    return datetime.now().strftime("%H:%M:%S")


def format_log(message: str) -> str:
    """
    Prefix a log message with the current timestamp.
    """

    return f"[{timestamp()}] {message}"