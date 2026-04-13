"""Tkinter UI for managing keyboard expander mappings with profile support."""

import tkinter as tk
from tkinter import ttk, messagebox
import db

ACTIONS = ["expand", "store_clipboard", "llm_query", "gen_cover_letter", "gen_resume", "show_ui", "switch_profile"]

ACTION_LABELS = {
    "expand":            "Expand",
    "store_clipboard":   "Store Clipboard",
    "llm_query":         "LLM Query",
    "gen_cover_letter":  "Generate Cover Letter",
    "gen_resume":        "Generate Resume",
    "show_ui":           "Show UI",
    "switch_profile":    "Switch Profile",
}

EXPANSION_LABELS = {
    "expand":            "Expansion text:",
    "store_clipboard":   "Variable name:",
    "llm_query":         "Prompt template:",
    "gen_cover_letter":  "Prompt template:",
    "gen_resume":        "Prompt template:",
    "show_ui":           None,
    "switch_profile":    None,
}

EXPANSION_HINTS = {
    "llm_query":         "Use {{clipboard}}, {{job_description}}, {{resume}}, etc.",
    "gen_cover_letter":  "Use {{resume}}, {{job_description}}, {{date}}, etc. Result saved as PDF in ~/Downloads.",
    "gen_resume":        "Use {{resume}}, {{job_description}}, etc. Result saved as PDF in ~/Downloads.",
    "store_clipboard":   "e.g. job_description, resume, …",
}

_LABEL_TO_ACTION = {v: k for k, v in ACTION_LABELS.items()}


class MappingDialog(tk.Toplevel):
    def __init__(self, parent, title: str,
                 shortcut: str = "", expansion: str = "", action: str = "expand"):
        super().__init__(parent)
        self.title(title)
        self.resizable(True, False)
        self.grab_set()
        self.result: tuple[str, str, str] | None = None
        pad = {"padx": 8, "pady": 4}

        ttk.Label(self, text="Shortcut:").grid(row=0, column=0, sticky="w", **pad)
        self._shortcut_var = tk.StringVar(value=shortcut)
        ttk.Entry(self, textvariable=self._shortcut_var, width=22).grid(row=0, column=1, sticky="ew", **pad)

        ttk.Label(self, text="Action:").grid(row=1, column=0, sticky="w", **pad)
        self._action_var = tk.StringVar()
        action_cb = ttk.Combobox(
            self, textvariable=self._action_var,
            values=[ACTION_LABELS[a] for a in ACTIONS],
            state="readonly", width=20,
        )
        action_cb.grid(row=1, column=1, sticky="ew", **pad)
        self._action_var.trace_add("write", lambda *_: self._on_action_change())

        self._exp_label = ttk.Label(self, text="")
        self._exp_label.grid(row=2, column=0, sticky="nw", **pad)
        self._exp_frame = ttk.Frame(self)
        self._exp_frame.grid(row=2, column=1, sticky="ew", **pad)
        self._expansion_text = tk.Text(self._exp_frame, width=48, height=5, wrap="word")
        self._expansion_text.pack(fill="both", expand=True)
        self._hint_label = ttk.Label(self._exp_frame, text="", foreground="gray",
                                     font=("TkDefaultFont", 9))
        self._hint_label.pack(anchor="w")
        self.columnconfigure(1, weight=1)

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=8)
        ttk.Button(btn_frame, text="Save",   command=self._save).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=4)
        self.bind("<Escape>", lambda _: self.destroy())

        self._action_var.set(ACTION_LABELS.get(action, action))
        self._expansion_text.insert("1.0", expansion)
        self._on_action_change()

    def _current_action(self) -> str:
        return _LABEL_TO_ACTION.get(self._action_var.get(), self._action_var.get())

    def _on_action_change(self):
        action = self._current_action()
        label = EXPANSION_LABELS.get(action)
        if label is None:
            self._exp_label.config(text="")
            self._exp_frame.grid_remove()
        else:
            self._exp_label.config(text=label)
            self._exp_frame.grid()
            self._hint_label.config(text=EXPANSION_HINTS.get(action, ""))

    def _save(self):
        shortcut = self._shortcut_var.get().strip()
        action = self._current_action()
        expansion = self._expansion_text.get("1.0", "end-1c").strip()
        if not shortcut:
            messagebox.showwarning("Validation", "Shortcut cannot be empty.", parent=self)
            return
        if EXPANSION_LABELS.get(action) is not None and not expansion:
            messagebox.showwarning("Validation",
                                   f"'{EXPANSION_LABELS[action]}' cannot be empty.", parent=self)
            return
        self.result = (shortcut, expansion, action)
        self.destroy()


class ProfileSwitcherDialog(tk.Toplevel):
    """Compact popup for switching the active profile (triggered by ///)."""

    def __init__(self, parent, on_switched):
        super().__init__(parent)
        self.title("Switch Profile")
        self.resizable(False, False)
        self.grab_set()
        self._on_switched = on_switched

        ttk.Label(self, text="Select profile:", padding=8).pack()

        self._listbox = tk.Listbox(self, selectmode="single", width=28, height=8,
                                   activestyle="dotbox")
        self._listbox.pack(padx=12, pady=(0, 4))

        current = db.get_current_profile_name()
        for i, name in enumerate(db.get_profiles()):
            self._listbox.insert("end", name)
            if name == current:
                self._listbox.selection_set(i)
                self._listbox.see(i)

        btn_frame = ttk.Frame(self)
        btn_frame.pack(pady=8)
        ttk.Button(btn_frame, text="Switch", command=self._switch).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=4)

        self._listbox.bind("<Double-1>", lambda _: self._switch())
        self.bind("<Return>", lambda _: self._switch())
        self.bind("<Escape>", lambda _: self.destroy())

    def _switch(self):
        sel = self._listbox.curselection()
        if not sel:
            return
        name = self._listbox.get(sel[0])
        try:
            db.set_current_profile(name)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)
            return
        self.destroy()
        self._on_switched()


class ProfileManagerDialog(tk.Toplevel):
    """Dialog for creating, deleting, and switching profiles."""

    def __init__(self, parent, on_changed):
        super().__init__(parent)
        self.title("Manage Profiles")
        self.resizable(False, False)
        self.grab_set()
        self._on_changed = on_changed

        ttk.Label(self, text="Profiles:", padding=(8, 8, 8, 2)).pack(anchor="w")

        list_frame = ttk.Frame(self, padding=(8, 0, 8, 0))
        list_frame.pack(fill="both")
        self._listbox = tk.Listbox(list_frame, selectmode="single", width=30, height=8,
                                   activestyle="dotbox")
        self._listbox.pack(side="left", fill="both", expand=True)
        sb = ttk.Scrollbar(list_frame, orient="vertical", command=self._listbox.yview)
        self._listbox.configure(yscrollcommand=sb.set)
        sb.pack(side="right", fill="y")

        btn_frame = ttk.Frame(self, padding=8)
        btn_frame.pack(fill="x")
        ttk.Button(btn_frame, text="Switch to Selected", command=self._switch).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="+ New Profile",      command=self._create).pack(side="left", padx=2)
        ttk.Button(btn_frame, text="Delete",             command=self._delete).pack(side="left", padx=2)

        self._current_label = ttk.Label(self, text="", foreground="gray", padding=(8, 0, 8, 8))
        self._current_label.pack(anchor="w")

        self._refresh()
        self._listbox.bind("<Double-1>", lambda _: self._switch())

    def _refresh(self):
        current = db.get_current_profile_name()
        self._current_label.config(text=f"Active: {current}")
        self._listbox.delete(0, "end")
        for name in db.get_profiles():
            display = f"{'→ ' if name == current else '  '}{name}"
            self._listbox.insert("end", display)

    def _selected_name(self) -> str | None:
        sel = self._listbox.curselection()
        if not sel:
            return None
        return self._listbox.get(sel[0]).lstrip("→ ").strip()

    def _switch(self):
        name = self._selected_name()
        if not name:
            return
        try:
            db.set_current_profile(name)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)
            return
        self._refresh()
        self._on_changed()

    def _create(self):
        dlg = _InputDialog(self, "New Profile", "Profile name:")
        self.wait_window(dlg)
        if not dlg.result:
            return
        try:
            db.create_profile(dlg.result)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)
            return
        self._refresh()

    def _delete(self):
        name = self._selected_name()
        if not name:
            return
        if not messagebox.askyesno("Confirm Delete",
                                   f'Delete profile "{name}" and all its data?', parent=self):
            return
        try:
            db.delete_profile(name)
        except Exception as e:
            messagebox.showerror("Error", str(e), parent=self)
            return
        self._refresh()
        self._on_changed()


class _InputDialog(tk.Toplevel):
    def __init__(self, parent, title: str, prompt: str):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.grab_set()
        self.result: str | None = None
        ttk.Label(self, text=prompt, padding=8).pack()
        self._var = tk.StringVar()
        ttk.Entry(self, textvariable=self._var, width=24).pack(padx=12)
        btn_frame = ttk.Frame(self, padding=8)
        btn_frame.pack()
        ttk.Button(btn_frame, text="OK",     command=self._ok).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=4)
        self.bind("<Return>", lambda _: self._ok())
        self.bind("<Escape>", lambda _: self.destroy())

    def _ok(self):
        val = self._var.get().strip()
        if val:
            self.result = val
        self.destroy()


DEFAULT_MODEL = "gpt-4o-mini"
_FALLBACK_MODELS = ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-4", "gpt-3.5-turbo"]


def _fetch_openai_models(api_key: str) -> list[str]:
    """Return sorted list of chat-capable model IDs from the OpenAI API."""
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    models = [m.id for m in client.models.list() if "gpt" in m.id]
    return sorted(set(models), reverse=True)


class SettingsDialog(tk.Toplevel):
    """Global settings (not per-profile)."""

    def __init__(self, parent):
        super().__init__(parent)
        self.title("Settings")
        self.resizable(False, False)
        self.grab_set()
        pad = {"padx": 12, "pady": 6}

        # API Key row
        ttk.Label(self, text="OpenAI API Key:").grid(row=0, column=0, sticky="w", **pad)
        self._key_var = tk.StringVar(value=db.get_setting("OPENAI_API_KEY"))
        entry = ttk.Entry(self, textvariable=self._key_var, width=44, show="*")
        entry.grid(row=0, column=1, sticky="ew", **pad)
        self._show_key = False
        self._toggle_btn = ttk.Button(self, text="Show", width=6, command=self._toggle_show)
        self._toggle_btn.grid(row=0, column=2, padx=(0, 12))
        self._entry = entry

        # Model row
        ttk.Label(self, text="OpenAI Model:").grid(row=1, column=0, sticky="w", **pad)
        saved_model = db.get_setting("OPENAI_MODEL", DEFAULT_MODEL)
        self._model_var = tk.StringVar(value=saved_model)
        self._model_cb = ttk.Combobox(
            self, textvariable=self._model_var,
            values=_FALLBACK_MODELS, width=30,
        )
        self._model_cb.grid(row=1, column=1, sticky="w", **pad)

        self._model_status = ttk.Label(self, text="", foreground="gray",
                                       font=("TkDefaultFont", 9))
        self._model_status.grid(row=1, column=2, sticky="w", padx=(0, 12))

        # Refresh button — fetch model list from API
        ttk.Button(self, text="↻ Refresh Models",
                   command=self._refresh_models).grid(row=2, column=1, sticky="w",
                                                      padx=12, pady=(0, 4))

        # Cover letter options
        ttk.Separator(self, orient="horizontal").grid(row=3, column=0, columnspan=3,
                                                      sticky="ew", padx=12, pady=(4, 0))
        ttk.Label(self, text="Typing:").grid(row=4, column=0, sticky="w", padx=12, pady=6)
        self._typing_emulation_var = tk.BooleanVar(
            value=db.get_setting("TYPING_EMULATION_ENABLED", "1") == "1"
        )
        ttk.Checkbutton(self, text="Enable human-like typing emulation",
                        variable=self._typing_emulation_var).grid(
                            row=4, column=1, sticky="w", padx=12
                        )

        ttk.Label(self, text="Cover Letter:").grid(row=5, column=0, sticky="w", padx=12, pady=6)
        self._open_finder_var = tk.BooleanVar(
            value=db.get_setting("COVERLETTER_OPEN_FINDER", "1") == "1"
        )
        ttk.Checkbutton(self, text="Open Finder after generation",
                        variable=self._open_finder_var).grid(row=5, column=1, sticky="w", padx=12)

        ttk.Label(self, text="Resume:").grid(row=6, column=0, sticky="w", padx=12, pady=6)
        self._open_finder_resume_var = tk.BooleanVar(
            value=db.get_setting("RESUME_OPEN_FINDER", "1") == "1"
        )
        ttk.Checkbutton(self, text="Open Finder after generation",
                        variable=self._open_finder_resume_var).grid(row=6, column=1, sticky="w", padx=12)

        btn_frame = ttk.Frame(self)
        btn_frame.grid(row=7, column=0, columnspan=3, pady=10)
        ttk.Button(btn_frame, text="Save",   command=self._save).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Cancel", command=self.destroy).pack(side="left", padx=4)

        self.columnconfigure(1, weight=1)
        self.bind("<Return>", lambda _: self._save())
        self.bind("<Escape>", lambda _: self.destroy())

        # Auto-fetch on open if a key is already saved
        if self._key_var.get().strip():
            self.after(100, self._refresh_models)

    def _refresh_models(self):
        api_key = self._key_var.get().strip()
        if not api_key:
            self._model_status.config(text="Enter an API key first.", foreground="orange")
            return
        self._model_status.config(text="Loading…", foreground="gray")
        self._model_cb.config(state="disabled")

        import threading
        threading.Thread(target=self._fetch_and_update, args=(api_key,), daemon=True).start()

    def _fetch_and_update(self, api_key: str):
        try:
            models = _fetch_openai_models(api_key)
            self.after(0, lambda: self._apply_models(models))
        except Exception as e:
            self.after(0, lambda: self._model_status.config(
                text=f"Error: {e}", foreground="red"))
            self.after(0, lambda: self._model_cb.config(state="normal"))

    def _apply_models(self, models: list[str]):
        current = self._model_var.get()
        self._model_cb.config(values=models, state="normal")
        # Keep current selection if it's in the list, otherwise pick first
        if current not in models and models:
            self._model_var.set(models[0])
        self._model_status.config(
            text=f"{len(models)} models loaded", foreground="green")

    def _toggle_show(self):
        self._show_key = not self._show_key
        self._entry.config(show="" if self._show_key else "*")
        self._toggle_btn.config(text="Hide" if self._show_key else "Show")

    def _save(self):
        db.set_setting("OPENAI_API_KEY", self._key_var.get().strip())
        db.set_setting("OPENAI_MODEL", self._model_var.get().strip() or DEFAULT_MODEL)
        db.set_setting("TYPING_EMULATION_ENABLED", "1" if self._typing_emulation_var.get() else "0")
        db.set_setting("COVERLETTER_OPEN_FINDER", "1" if self._open_finder_var.get() else "0")
        db.set_setting("RESUME_OPEN_FINDER", "1" if self._open_finder_resume_var.get() else "0")
        self.destroy()


class ManagerWindow(tk.Tk):
    def __init__(self, on_profile_changed=None, get_session=None):
        super().__init__()
        self.title("AutoFiller — Mappings")
        self.minsize(640, 500)
        self._on_profile_changed = on_profile_changed
        self._get_session = get_session or (lambda: {})
        self.protocol("WM_DELETE_WINDOW", self.withdraw)

        self._build_ui()
        self._refresh()
        self._poll_session()

    # ── public API (called from keyboard_expander) ────────────────────────────

    def show_window(self):
        self.after(0, self._do_show)

    def show_profile_switcher(self):
        self.after(0, self._open_profile_switcher)

    # ── internals ─────────────────────────────────────────────────────────────

    def _do_show(self):
        self.deiconify()
        self.lift()
        self.focus_force()

    def _open_profile_switcher(self):
        ProfileSwitcherDialog(self, on_switched=self._after_profile_change)

    def _after_profile_change(self):
        self._update_profile_label()
        self._refresh()
        self._sess_data = None     # force session panel re-render (even if new profile has no vars)
        if self._on_profile_changed:
            self._on_profile_changed()

    def _build_ui(self):
        # ── profile bar ───────────────────────────────────────────────────────
        profile_bar = ttk.Frame(self, padding=(8, 4))
        profile_bar.pack(fill="x")
        ttk.Label(profile_bar, text="Profile:").pack(side="left")
        self._profile_label = ttk.Label(profile_bar, text="", font=("TkDefaultFont", 10, "bold"))
        self._profile_label.pack(side="left", padx=(4, 12))
        ttk.Button(profile_bar, text="Manage Profiles",
                   command=self._open_profile_manager).pack(side="left")
        ttk.Button(profile_bar, text="Settings",
                   command=self._open_settings).pack(side="right")
        self._update_profile_label()

        ttk.Separator(self, orient="horizontal").pack(fill="x")

        # ── mappings toolbar ──────────────────────────────────────────────────
        toolbar = ttk.Frame(self, padding=4)
        toolbar.pack(fill="x")
        ttk.Button(toolbar, text="+ Add",  command=self._add).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Edit",   command=self._edit).pack(side="left", padx=2)
        ttk.Button(toolbar, text="Delete", command=self._delete).pack(side="left", padx=2)

        # ── mappings table ────────────────────────────────────────────────────
        frame = ttk.Frame(self)
        frame.pack(fill="both", expand=True, padx=8, pady=(0, 4))

        cols = ("shortcut", "action", "expansion")
        self._tree = ttk.Treeview(frame, columns=cols, show="headings", selectmode="browse")
        self._tree.heading("shortcut",  text="Shortcut")
        self._tree.heading("action",    text="Action")
        self._tree.heading("expansion", text="Expansion / Variable / Prompt")
        self._tree.column("shortcut",  width=90,  stretch=False)
        self._tree.column("action",    width=120, stretch=False)
        self._tree.column("expansion", width=400)
        sb = ttk.Scrollbar(frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self._tree.bind("<Double-1>",  lambda _: self._edit())
        self._tree.bind("<Delete>",    lambda _: self._delete())
        self._tree.bind("<BackSpace>", lambda _: self._delete())

        # ── session variables panel ───────────────────────────────────────────
        ttk.Separator(self, orient="horizontal").pack(fill="x", padx=8)
        session_frame = ttk.LabelFrame(self, text="Session Variables", padding=4)
        session_frame.pack(fill="both", padx=8, pady=(4, 8))
        session_frame.rowconfigure(0, weight=1)
        session_frame.columnconfigure(1, weight=1)

        self._sess_listbox = tk.Listbox(session_frame, width=18, exportselection=False)
        self._sess_listbox.grid(row=0, column=0, sticky="ns", padx=(0, 4))
        self._sess_listbox.bind("<<ListboxSelect>>", lambda _: self._on_sess_select())

        text_frame = ttk.Frame(session_frame)
        text_frame.grid(row=0, column=1, sticky="nsew")
        text_frame.rowconfigure(0, weight=1)
        text_frame.columnconfigure(0, weight=1)
        self._sess_text = tk.Text(text_frame, wrap="word", state="disabled",
                                  relief="flat", bg=self.cget("bg"))
        vsb = ttk.Scrollbar(text_frame, orient="vertical", command=self._sess_text.yview)
        self._sess_text.configure(yscrollcommand=vsb.set)
        self._sess_text.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self._sess_data: dict[str, str] | None = None

    def _update_profile_label(self):
        self._profile_label.config(text=db.get_current_profile_name())

    def _open_profile_manager(self):
        ProfileManagerDialog(self, on_changed=self._after_profile_change)

    def _open_settings(self):
        SettingsDialog(self)

    # ── session panel ─────────────────────────────────────────────────────────

    def _on_sess_select(self):
        sel = self._sess_listbox.curselection()
        if not sel:
            return
        value = self._sess_data.get(self._sess_listbox.get(sel[0]), "")
        self._sess_text.config(state="normal")
        self._sess_text.delete("1.0", "end")
        self._sess_text.insert("1.0", value)
        self._sess_text.config(state="disabled")

    def _poll_session(self):
        new_data = self._get_session()
        if new_data != self._sess_data:
            self._sess_data = new_data
            sel = self._sess_listbox.curselection()
            selected_name = self._sess_listbox.get(sel[0]) if sel else None
            self._sess_listbox.delete(0, "end")
            names = sorted(new_data)
            for name in names:
                self._sess_listbox.insert("end", name)
            if names:
                idx = names.index(selected_name) if selected_name in names else 0
                self._sess_listbox.selection_set(idx)
                self._on_sess_select()
            else:
                self._sess_text.config(state="normal")
                self._sess_text.delete("1.0", "end")
                self._sess_text.insert("1.0", "(none stored yet)")
                self._sess_text.config(state="disabled")
        self.after(1000, self._poll_session)

    # ── mappings CRUD ─────────────────────────────────────────────────────────

    def _refresh(self):
        self._tree.delete(*self._tree.get_children())
        for shortcut, entry in db.get_all().items():
            action_label = ACTION_LABELS.get(entry["action"], entry["action"])
            preview = entry["expansion"].replace("\n", " ")[:80]
            self._tree.insert("", "end", values=(shortcut, action_label, preview))

    def _notify(self):
        if self._on_profile_changed:
            self._on_profile_changed()

    def _add(self):
        dlg = MappingDialog(self, "Add Mapping")
        self.wait_window(dlg)
        if dlg.result:
            shortcut, expansion, action = dlg.result
            try:
                db.add(shortcut, expansion, action)
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self)
                return
            self._refresh()
            self._notify()

    def _edit(self):
        sel = self._tree.selection()
        if not sel:
            return
        shortcut, action_label, _ = self._tree.item(sel[0], "values")
        entry = db.get_all().get(shortcut, {})
        action_key = _LABEL_TO_ACTION.get(action_label, "expand")
        dlg = MappingDialog(self, "Edit Mapping",
                            shortcut=shortcut,
                            expansion=entry.get("expansion", ""),
                            action=action_key)
        self.wait_window(dlg)
        if dlg.result:
            new_shortcut, new_expansion, new_action = dlg.result
            try:
                db.update(shortcut, new_shortcut, new_expansion, new_action)
            except Exception as e:
                messagebox.showerror("Error", str(e), parent=self)
                return
            self._refresh()
            self._notify()

    def _delete(self):
        sel = self._tree.selection()
        if not sel:
            return
        shortcut, _, _ = self._tree.item(sel[0], "values")
        if not messagebox.askyesno("Confirm Delete", f'Delete shortcut "{shortcut}"?', parent=self):
            return
        db.delete(shortcut)
        self._refresh()
        self._notify()
