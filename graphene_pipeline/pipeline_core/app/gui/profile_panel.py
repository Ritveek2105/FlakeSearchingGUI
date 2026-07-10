from __future__ import annotations

import tkinter as tk
from tkinter import simpledialog, messagebox

from .styles import BUTTON_WIDTH, LABEL_FONT, PANEL, SECTION_FONT


class ProfilePanel(tk.Frame):
    def __init__(
        self,
        parent,
        profile_names: list[str],
        on_load,
        on_save,
        on_save_as,
        on_delete,
    ):
        super().__init__(parent, bg=PANEL, bd=1, relief="solid", padx=12, pady=12)

        self.on_load = on_load
        self.on_save = on_save
        self.on_save_as = on_save_as
        self.on_delete = on_delete

        self.selected_profile = tk.StringVar(value="")
        self.profile_names = profile_names

        self.build()

    def build(self) -> None:
        title = tk.Label(self, text="Profiles", font=SECTION_FONT, bg=PANEL)
        title.grid(row=0, column=0, columnspan=3, sticky="w", pady=(0, 8))

        label = tk.Label(self, text="Current Profile", font=LABEL_FONT, bg=PANEL)
        label.grid(row=1, column=0, sticky="w", pady=3)

        self.dropdown = tk.OptionMenu(
            self,
            self.selected_profile,
            *(self.profile_names if self.profile_names else [""]),
        )
        self.dropdown.grid(row=1, column=1, columnspan=2, sticky="ew", pady=3)

        button_frame = tk.Frame(self, bg=PANEL)
        button_frame.grid(row=2, column=0, columnspan=3, sticky="w", pady=(10, 0))

        self.load_button = tk.Button(
            button_frame,
            text="Load",
            width=BUTTON_WIDTH,
            command=self.load_selected,
        )
        self.load_button.pack(side="left", padx=(0, 8))

        self.save_button = tk.Button(
            button_frame,
            text="Save",
            width=BUTTON_WIDTH,
            command=self.save_selected,
        )
        self.save_button.pack(side="left", padx=(0, 8))

        self.save_as_button = tk.Button(
            button_frame,
            text="Save As",
            width=BUTTON_WIDTH,
            command=self.save_as,
        )
        self.save_as_button.pack(side="left", padx=(0, 8))

        self.delete_button = tk.Button(
            button_frame,
            text="Delete",
            width=12,
            command=self.delete_selected,
        )
        self.delete_button.pack(side="left")

        self.columnconfigure(1, weight=1)

        self.refresh_profiles(self.profile_names)

    def refresh_profiles(self, profile_names: list[str]) -> None:
        self.profile_names = profile_names

        menu = self.dropdown["menu"]
        menu.delete(0, "end")

        if not profile_names:
            self.selected_profile.set("")
            menu.add_command(label="", command=lambda: self.selected_profile.set(""))
            return

        current = self.selected_profile.get()

        if current not in profile_names:
            current = profile_names[0]

        self.selected_profile.set(current)

        for name in profile_names:
            menu.add_command(
                label=name,
                command=lambda value=name: self.selected_profile.set(value),
            )

    def get_selected_profile(self) -> str:
        return self.selected_profile.get().strip()

    def load_selected(self) -> None:
        name = self.get_selected_profile()

        if not name:
            messagebox.showwarning("Load Profile", "No profile selected.")
            return

        self.on_load(name)

    def save_selected(self) -> None:
        name = self.get_selected_profile()

        if not name:
            self.save_as()
            return

        self.on_save(name)

    def save_as(self) -> None:
        name = simpledialog.askstring(
            "Save Profile As",
            "Profile name:",
        )

        if not name:
            return

        name = name.strip()

        if not name:
            return

        self.on_save_as(name)

    def delete_selected(self) -> None:
        name = self.get_selected_profile()

        if not name:
            messagebox.showwarning("Delete Profile", "No profile selected.")
            return

        confirmed = messagebox.askyesno(
            "Delete Profile",
            f"Delete profile '{name}'?",
        )

        if not confirmed:
            return

        self.on_delete(name)

    def set_running(self, running: bool) -> None:
        state = "disabled" if running else "normal"

        self.load_button.config(state=state)
        self.save_button.config(state=state)
        self.save_as_button.config(state=state)
        self.delete_button.config(state=state)