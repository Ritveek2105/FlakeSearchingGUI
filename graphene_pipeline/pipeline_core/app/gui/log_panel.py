"""
Live pipeline log panel.

Encapsulates the scrolling log so the main GUI doesn't need to
manipulate a ScrolledText widget directly.
"""

from __future__ import annotations

import tkinter as tk
from tkinter import scrolledtext

from .styles import (
    LOG_FONT,
    PANEL,
)
from .utils import timestamp


class LogPanel(tk.Frame):
    """
    Scrollable log window used by the GUI.
    """

    def __init__(self, parent):

        super().__init__(
            parent,
            bg=PANEL,
            bd=1,
            relief="solid",
        )

        self.text = scrolledtext.ScrolledText(
            self,
            wrap="word",
            font=LOG_FONT,
            height=16,
        )

        self.text.pack(
            fill="both",
            expand=True,
            padx=8,
            pady=8,
        )

        self.text.configure(state="disabled")

    # --------------------------------------------------

    def clear(self):

        self.text.configure(state="normal")
        self.text.delete("1.0", tk.END)
        self.text.configure(state="disabled")

    # --------------------------------------------------

    def write(self, message: str):

        self.text.configure(state="normal")

        self.text.insert(
            tk.END,
            message,
        )

        self.text.see(tk.END)

        self.text.configure(state="disabled")

    # --------------------------------------------------

    def log(self, message: str):

        self.write(
            f"[{timestamp()}] {message}\n"
        )

    # --------------------------------------------------

    def success(self, message: str):

        self.log(f"✓ {message}")

    # --------------------------------------------------

    def warning(self, message: str):

        self.log(f"⚠ {message}")

    # --------------------------------------------------

    def error(self, message: str):

        self.log(f"❌ {message}")

    # --------------------------------------------------

    def separator(self):

        self.write(
            "-" * 70 + "\n"
        )

    # --------------------------------------------------

    def append_status_event(self, event: dict):

        line = (
            f"[{event.get('time','')}] "
            f"{event.get('stage','')} "
            f"{event.get('status','')}: "
            f"{event.get('message','')}\n"
        )

        self.write(line)