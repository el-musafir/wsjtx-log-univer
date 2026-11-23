"""Graphical interface for the WSJTX Log Unifier.

The window has a selector for the logs to take and unify (double-click a
row to toggle it), a **Read logs** action that counts the QSOs per file,
and a **Save unified log…** action that writes the unified ADIF log.
Everything also works headless from the command line; see
``wsjtx_log_unifier.py``.
"""

from __future__ import annotations

import os

from adi import AdifParseError, parse_adi_file, write_adi
from unify import unify_records

try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError:  # pragma: no cover - tkinter ships with CPython
    tk = None

#: File filters offered by the file dialogs.
ADI_FILTERS = (
    ("ADIF logs (*.adi)", "*.adi"),
    ("WSJT-X / WS log (wsjtx_log.adi)", "wsjtx_log.adi"),
    ("All files", "*.*"),
)


class LogsApp:
    """The WSJTX Log Unifier window and its data logic."""

    def __init__(self, root):
        self.root = root
        # Rows: list of dicts with keys "path", "sel", "count",
        # "records", "error" and "item" (tree item id).
        self.rows = []
        self.dedupe_var = tk.BooleanVar(root, True)
        self.sort_var = tk.BooleanVar(root, True)
        self.status_var = tk.StringVar(root, "Ready.")
        self._tree = None
        self._build_widgets()
        self.set_status("Add logs, read them, then save the unified log.")

    # ------------------------------------------------------------------
    # Data operations (usable without a display, e.g. from tests)
    # ------------------------------------------------------------------

    def add_files(self, paths):
        """Add log files; returns how many were newly added."""
        if paths is None:
            paths = self._pick_files()
        if not paths:
            return 0
        known = {row["path"] for row in self.rows}
        added = 0
        for path in paths:
            if path in known:
                continue
            self.rows.append({
                "path": path,
                "sel": True,
                "count": None,
                "records": None,
                "error": None,
                "item": None,
            })
            known.add(path)
            added += 1
        self._sync_tree()
        self.set_status(self._summary())
        return added

    def add_directory(self, directory=None):
        """Add every ``*.adi`` log below ``directory``; returns new count."""
        if directory is None:
            directory = self._pick_directory()
        if not directory:
            return 0
        logs = []
        for dirpath, dirnames, filenames in os.walk(directory):
            dirnames.sort()
            for name in filenames:
                if name.lower().endswith(".adi"):
                    logs.append(os.path.join(dirpath, name))
        logs.sort()
        return self.add_files(logs) if logs else 0

    def toggle(self, path=None, index=None):
        """Toggle the "take this log" flag; returns the new state or None."""
        row = None
        if path is not None:
            row = next((r for r in self.rows if r["path"] == path), None)
        elif index is not None:
            row = self.rows[index]
        if row is None:
            return None
        row["sel"] = not row["sel"]
        self._sync_tree()
        return row["sel"]

    def read_logs(self):
        """Read all logs; updates per-file counts/errors and the status."""
        for row in self.rows:
            try:
                records = parse_adi_file(row["path"])
            except AdifParseError as exc:
                row["count"] = None
                row["records"] = None
                row["error"] = str(exc)
            else:
                row["count"] = len(records)
                row["records"] = records
                row["error"] = None
        self._sync_tree()
        self.set_status(self._summary())

    def save_unified(self, path=None):
        """Read logs, unify them and save the result.

        Returns the path written, or None when nothing was done.
        """
        self.read_logs()
        selected = [row for row in self.rows if row["sel"]]
        if not selected:
            self._warn("Nothing to do",
                       "No log is selected. Add logs and keep them selected.")
            return None
        records = []
        bad = []
        for row in selected:
            if row["records"] is None:
                bad.append(row["path"])
            else:
                records.extend(row["records"])
        if bad:
            self._warn("Skipped unreadable logs",
                       "Could not read:\n" + "\n".join(bad))
            if not records:
                return None
        if path is None:
            path = self._pick_output()
            if not path:
                return None
        unified, removed = unify_records(
            records,
            dedupe=self.dedupe_var.get(),
            sort=self.sort_var.get(),
        )
        write_adi(path, unified)
        note = f" ({removed} duplicates removed)" if removed else ""
        self.set_status(f"Wrote {len(unified)} QSOs to {path}{note}")
        self._info("Saved", f"Wrote {len(unified)} QSOs to {path}{note}.")
        return path

    def set_status(self, text):
        self.status_var.set(text)

    # ------------------------------------------------------------------
    # Presentation
    # ------------------------------------------------------------------

    def _summary(self):
        total = sum(row["count"] or 0 for row in self.rows)
        selected = sum(row["count"] or 0 for row in self.rows if row["sel"])
        return (f"{len(self.rows)} logs · {selected} selected QSOs · "
                f"{total} QSOs read in total")

    def _build_widgets(self):
        root = self.root
        root.title("WSJTX Log Unifier")
        root.minsize(760, 540)

        ttk.Label(
            root,
            text="Logs to take and unify (double-click a row to toggle):",
        ).pack(anchor="w", padx=12, pady=(10, 0))

        box = ttk.Frame(root)
        box.pack(fill="both", expand=True, padx=12, pady=(0, 6))
        self._tree = tree = ttk.Treeview(
            box,
            columns=("mark", "file", "qso_count"),
            show="headings",
            selectmode="none",
        )
        tree.heading("mark", text="Take", anchor="center")
        tree.heading("file", text="Log file", anchor="w")
        tree.heading("qso_count", text="QSOs read", anchor="e")
        tree.column("mark", anchor="center", width=56, stretch=False)
        tree.column("file", anchor="w")
        tree.column("qso_count", anchor="e", width=90, stretch=False)
        scrollbar = ttk.Scrollbar(box, orient="vertical", command=tree.yview)
        tree.configure(yscrollcommand=scrollbar.set)
        tree.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y", padx=(0, 4))
        tree.bind("<Double-Button-1>", self._on_double_click)
        tree.bind("<space>", self._on_space)

        buttons = ttk.Frame(root)
        buttons.pack(fill="x", padx=12, pady=(0, 6))
        ttk.Button(buttons, text="Add files…",
                   command=self._add_files_button).pack(side="left", padx=2)
        ttk.Button(buttons, text="Add directory…",
                   command=self._add_directory_button).pack(side="left", padx=2)
        ttk.Button(buttons, text="Read logs",
                   command=self.read_logs).pack(side="left", padx=2)
        ttk.Button(buttons, text="Save unified log…",
                   command=self._save_button).pack(side="left", padx=2)
        ttk.Button(buttons, text="Close",
                   command=self.root.destroy).pack(side="right", padx=2)

        options = ttk.Frame(root)
        options.pack(fill="x", padx=12, pady=(0, 2))
        ttk.Checkbutton(
            options,
            text="Remove duplicate QSOs (call, band, time)",
            variable=self.dedupe_var,
        ).pack(side="left", padx=2)
        ttk.Checkbutton(
            options,
            text="Sort QSOs by date/time",
            variable=self.sort_var,
        ).pack(side="left", padx=2)

        ttk.Label(root, textvariable=self.status_var,
                  foreground="gray").pack(anchor="w", padx=12, pady=(0, 8))

    def _sync_tree(self):
        tree = self._tree
        if tree is None:
            return
        for item in tree.get_children():
            tree.delete(item)
        for i, row in enumerate(self.rows):
            item = f"row-{i}"
            row["item"] = item
            mark = "✓" if row["sel"] else "◻"
            count_text = "—" if row["count"] is None else str(row["count"])
            tree.insert("", "end", iid=item,
                        values=(mark, row["path"], count_text))

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------

    def _add_files_button(self):
        self.add_files(None)

    def _add_directory_button(self):
        self.add_directory(None)

    def _save_button(self):
        self.save_unified(None)

    def _on_double_click(self, event=None):
        self._toggle_focused(event)

    def _on_space(self, event=None):
        self._toggle_focused(event)

    def _toggle_focused(self, event=None):
        tree = self._tree
        if tree is None:
            return
        if event is not None:
            item = tree.identify_row(event.y)
        else:
            item = tree.focus()
        if not item:
            return
        for row in self.rows:
            if row["item"] == item:
                self.toggle(path=row["path"])
                return

    # ------------------------------------------------------------------
    # File dialogs and message boxes
    # ------------------------------------------------------------------

    def _pick_files(self):
        return filedialog.askopenfilenames(
            parent=self.root,
            title="Select WSJT-X / WS logs",
            filetypes=ADI_FILTERS,
            multiple=True,
        ) or ()

    def _pick_directory(self):
        return filedialog.askdirectory(
            parent=self.root, title="Select the log directory")

    def _pick_output(self):
        return filedialog.asksaveasfilename(
            parent=self.root,
            title="Save the unified log",
            defaultextension=".adi",
            initialfile="unified_log.adi",
            filetypes=ADI_FILTERS,
        )

    def _warn(self, title, message):
        messagebox.showwarning(title, message, parent=self.root)

    def _info(self, title, message):
        messagebox.showinfo(title, message, parent=self.root)


def run_gui():
    """Create the main window and run the GUI event loop."""
    if tk is None:
        raise SystemExit(
            "The graphical interface needs tkinter, which is not available.")
    root = tk.Tk()
    LogsApp(root)
    root.mainloop()
