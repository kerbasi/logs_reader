#!/usr/bin/env python3
import sys
import shutil
import re
import threading
import tkinter as tk
from datetime import datetime
from tkinter import ttk, messagebox
from pathlib import Path
from typing import Dict, Optional

sys.path.append(str(Path(__file__).parent))
from src.core import ProductResolver, LogSearcher, ICTLogSearcher
from src.interface import format_description

_RUNNERS: Dict[str, str] = {
    "19476": "Daniel Suima",
    "20992": "Oleg Karonin",
    "21465": "Dan Trievus",
    "19455": "Maxim Malabaev",
    "5590": "Vladimir Volik",
}

DEFAULT_PATHS = [
    "/usr/flexfs/lion_cub/log/ft",
    "/usr/flexfs/lion_cub/log",
    "/usr/flexfs/lion_cub/log/customization",
    "/usr/flexfs/lion_cub/log/dbg/ft",
    "/usr/flexfs/lion_cub/log/dbg",
    "/usr/flexfs/lion_cub/log/dbg/customization",
]


def _parse_month(s: str) -> Optional[str]:
    """Convert 'YYYY-MM' or 'YYYYMM' to 'YYYYMM'. Returns None if blank or invalid."""
    s = s.strip().replace("-", "")
    if len(s) == 6 and s.isdigit():
        return s
    return None


def _merge_dedup(a: list, b: list) -> list:
    seen: set = set()
    result = []
    for item in a + b:
        if item["path"] not in seen:
            seen.add(item["path"])
            result.append(item)
    return result


_DATE_RE = re.compile(
    r'y(\d{4})\s*m(\d{2})\s*d(\d{2})\s+(\d{2})\.(\d{2})\.(\d{2})'
)

def _parse_filename_date(fname: str):
    """Extract datetime from filename like 'y2026 m05 d10 14.45.53'."""
    m = _DATE_RE.search(fname)
    if m:
        try:
            return datetime(int(m.group(1)), int(m.group(2)), int(m.group(3)),
                            int(m.group(4)), int(m.group(5)), int(m.group(6)))
        except ValueError:
            pass
    return None


def _open_in_terminal(filepath: str):
    import subprocess
    if sys.platform == "win32":
        subprocess.Popen(
            ["cmd", "/c", f'more "{filepath}" && pause'],
            creationflags=subprocess.CREATE_NEW_CONSOLE,
        )
        return
    # Try common Linux terminal emulators
    for term in ("xterm", "gnome-terminal", "konsole", "xfce4-terminal",
                 "lxterminal", "urxvt", "alacritty", "kitty"):
        if shutil.which(term):
            if term in ("gnome-terminal",):
                subprocess.Popen([term, "--", "less", "-r", filepath])
            elif term in ("alacritty", "kitty"):
                subprocess.Popen([term, "-e", "less", "-r", filepath])
            else:
                subprocess.Popen([term, "-e", f"less -r {filepath}"])
            return
    raise RuntimeError(
        "No terminal emulator found. Install xterm or set $TERM.")


def _color_tag_for_log(log: dict) -> str:
    name_upper = log.get("name", "").upper()
    if "PASS" in name_upper:
        return "pass_tag"
    if "FAIL" in name_upper:
        return "fail_tag"
    desc = (log.get("description") or "").lower()
    if "pass" in desc:
        return "pass_tag"
    if any(x in desc for x in ("fail", "error", "timeout", "exception")):
        return "fail_tag"
    return "neutral_tag"


_PALETTE = {
    "bg":          "#1e1f2e",
    "bg_widget":   "#272838",
    "bg_input":    "#1a1b2a",
    "accent":      "#7c8cf8",
    "text":        "#e2e4f0",
    "text_dim":    "#c8cad8",
    "pass_col":    "#4ade80",
    "fail_col":    "#f87171",
    "ict_col":     "#38bdf8",
    "neutral_col": "#a5b4fc",
    "border":      "#3a3c52",
    "btn":         "#4338ca",
    "btn_active":  "#5046e5",
    "status_bg":   "#12131f",
    "select_bg":   "#4338ca",
}

_FONT_UI   = None
_FONT_MONO = None


def _apply_theme(root):
    global _FONT_UI, _FONT_MONO

    from tkinter import font as tkfont

    available = set(tkfont.families())

    _ui_name = "TkDefaultFont"
    for candidate in ["Ubuntu", "DejaVu Sans", "Liberation Sans", "Segoe UI", "Helvetica"]:
        if candidate in available:
            _ui_name = candidate
            break
    _FONT_UI = (_ui_name, 13)

    _mono_name = "TkFixedFont"
    for candidate in ["DejaVu Sans Mono", "Liberation Mono", "Consolas", "Courier New"]:
        if candidate in available:
            _mono_name = candidate
            break
    _FONT_MONO = (_mono_name, 12)

    style = ttk.Style(root)
    style.theme_use("clam")

    root.configure(bg=_PALETTE["bg"])

    style.configure(".",
        background=_PALETTE["bg"],
        foreground=_PALETTE["text"],
        font=_FONT_UI,
        bordercolor=_PALETTE["border"],
        darkcolor=_PALETTE["bg"],
        lightcolor=_PALETTE["bg"],
        troughcolor=_PALETTE["bg"],
        focuscolor=_PALETTE["accent"],
    )

    style.configure("TFrame",
        background=_PALETTE["bg"],
    )

    style.configure("TLabelframe",
        background=_PALETTE["bg"],
        bordercolor=_PALETTE["border"],
        relief="flat",
    )

    style.configure("TLabelframe.Label",
        background=_PALETTE["bg"],
        foreground=_PALETTE["accent"],
        font=_FONT_UI,
    )

    style.configure("TButton",
        background=_PALETTE["btn"],
        foreground=_PALETTE["text"],
        borderwidth=0,
        relief="flat",
        padding=(14, 7),
        font=_FONT_UI,
        focuscolor=_PALETTE["accent"],
    )
    style.map("TButton",
        background=[
            ("active",   _PALETTE["btn_active"]),
            ("pressed",  _PALETTE["btn_active"]),
            ("disabled", _PALETTE["bg_widget"]),
        ],
        foreground=[
            ("disabled", _PALETTE["text_dim"]),
        ],
        relief=[
            ("pressed", "flat"),
        ],
    )

    style.configure("TEntry",
        fieldbackground=_PALETTE["bg_input"],
        foreground=_PALETTE["text"],
        insertcolor=_PALETTE["text"],
        bordercolor=_PALETTE["border"],
        lightcolor=_PALETTE["bg_input"],
        darkcolor=_PALETTE["bg_input"],
        selectbackground=_PALETTE["select_bg"],
        selectforeground=_PALETTE["text"],
        padding=(4, 4),
        font=_FONT_UI,
    )
    style.map("TEntry",
        bordercolor=[
            ("focus", _PALETTE["accent"]),
        ],
        lightcolor=[
            ("focus", _PALETTE["accent"]),
        ],
    )

    style.configure("TLabel",
        background=_PALETTE["bg"],
        foreground=_PALETTE["text"],
        font=_FONT_UI,
    )

    style.configure("TScrollbar",
        background=_PALETTE["bg_widget"],
        troughcolor=_PALETTE["bg"],
        bordercolor=_PALETTE["bg"],
        arrowcolor=_PALETTE["bg"],
        arrowsize=0,
        relief="flat",
        width=8,
    )
    style.map("TScrollbar",
        background=[
            ("active", _PALETTE["border"]),
        ],
    )

    style.configure("Status.TLabel",
        background=_PALETTE["status_bg"],
        foreground=_PALETTE["text_dim"],
        font=(_FONT_UI[0], _FONT_UI[1] - 1),
        anchor="w",
    )

    style.configure("Dim.TLabel",
        background=_PALETTE["bg"],
        foreground=_PALETTE["text_dim"],
        font=(_FONT_UI[0], _FONT_UI[1] - 1),
    )

    style.configure("TRadiobutton",
        background=_PALETTE["bg"],
        foreground=_PALETTE["text"],
        font=_FONT_UI,
        focuscolor=_PALETTE["accent"],
        indicatorrelief="flat",
    )
    style.map("TRadiobutton",
        background=[("active", _PALETTE["bg"])],
        foreground=[("active", _PALETTE["text"])],
        indicatorcolor=[
            ("selected", _PALETTE["accent"]),
            ("active",   _PALETTE["bg_widget"]),
            ("!selected", _PALETTE["bg_input"]),
        ],
    )

    style.configure("TCheckbutton",
        background=_PALETTE["bg"],
        foreground=_PALETTE["text"],
        font=_FONT_UI,
        focuscolor=_PALETTE["accent"],
        indicatorrelief="flat",
    )
    style.map("TCheckbutton",
        background=[("active", _PALETTE["bg"])],
        foreground=[("active", _PALETTE["text"])],
        indicatorcolor=[
            ("selected", _PALETTE["accent"]),
            ("active",   _PALETTE["bg_widget"]),
            ("!selected", _PALETTE["bg_input"]),
        ],
    )

    style.configure("Treeview",
        background=_PALETTE["bg_widget"],
        foreground=_PALETTE["text"],
        fieldbackground=_PALETTE["bg_widget"],
        rowheight=22,
        borderwidth=0,
        relief="flat",
        font=_FONT_MONO,
    )
    style.configure("Treeview.Heading",
        background=_PALETTE["bg"],
        foreground=_PALETTE["text_dim"],
        borderwidth=1,
        relief="flat",
        font=(_FONT_UI[0], _FONT_UI[1] - 1),
    )
    style.map("Treeview",
        background=[("selected", _PALETTE["select_bg"])],
        foreground=[("selected", _PALETTE["text"])],
    )
    style.map("Treeview.Heading",
        background=[("active", _PALETTE["bg_widget"])],
        relief=[("active", "flat")],
    )


class LogReaderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Log Reader")
        self.root.minsize(900, 700)

        self._logs: list = []
        self._extra_paths: list = list(DEFAULT_PATHS)
        self._show_pass = tk.BooleanVar(value=True)
        self._show_fail = tk.BooleanVar(value=True)
        self._mode = tk.StringVar(value="sn")
        self._displayed_logs: list = []
        self._sort_col: str = "date"
        self._sort_rev: bool = True
        self._paths_expanded = False

        _apply_theme(root)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = self.root
        root.columnconfigure(0, weight=1)
        root.rowconfigure(1, weight=1)  # results zone

        # ── Zone 1: Search panel ──────────────────────────────────────
        search_frame = ttk.LabelFrame(root, text="Search", padding=6)
        search_frame.grid(row=0, column=0, sticky="NSEW", padx=6, pady=(6, 2))
        search_frame.columnconfigure(1, weight=1)

        # Row 0 — Mode radio buttons
        mode_frame = ttk.Frame(search_frame)
        mode_frame.grid(row=0, column=0, columnspan=2, sticky="W")
        ttk.Radiobutton(
            mode_frame, text="Serial Number", variable=self._mode, value="sn",
            command=self._on_mode_change,
        ).pack(side="left", padx=(0, 16))
        ttk.Radiobutton(
            mode_frame, text="Product Number (ICT only)", variable=self._mode, value="pn",
            command=self._on_mode_change,
        ).pack(side="left")

        # Row 1 — Single search entry (label swaps with mode)
        entry_row = ttk.Frame(search_frame)
        entry_row.grid(row=1, column=0, columnspan=2, sticky="EW", pady=(6, 0))
        entry_row.columnconfigure(1, weight=1)
        self._search_entry_label = ttk.Label(entry_row, text="Serial Number:", width=22)
        self._search_entry_label.grid(row=0, column=0, sticky="W", padx=(0, 4))
        self.search_entry = ttk.Entry(entry_row)
        self.search_entry.grid(row=0, column=1, sticky="EW")
        self.search_entry.bind("<Return>", lambda _e: self._start_search())

        # Row 2 — Period filter (PN mode only; hidden initially)
        _cur_month = datetime.now().strftime("%Y-%m")
        self._period_row = ttk.Frame(search_frame)
        self._period_row.grid(row=2, column=0, columnspan=2, sticky="W", pady=(6, 0))
        ttk.Label(self._period_row, text="Period:").pack(side="left", padx=(0, 4))
        ttk.Label(self._period_row, text="From:").pack(side="left", padx=(0, 4))
        self.from_month_entry = ttk.Entry(self._period_row, width=10)
        self.from_month_entry.insert(0, _cur_month)
        self.from_month_entry.pack(side="left")
        ttk.Label(self._period_row, text="To:", style="Dim.TLabel").pack(side="left", padx=(10, 4))
        self.to_month_entry = ttk.Entry(self._period_row, width=10)
        self.to_month_entry.insert(0, _cur_month)
        self.to_month_entry.pack(side="left")
        ttk.Label(self._period_row, text="  (YYYY-MM)", style="Dim.TLabel").pack(side="left", padx=(6, 0))
        self._period_row.grid_remove()  # hidden in SN mode

        # Row 2 — Paths toggle header (SN mode only)
        self._paths_header = ttk.Frame(search_frame)
        self._paths_header.grid(row=2, column=0, columnspan=2, sticky="W", pady=(6, 0))
        self._paths_toggle_btn = ttk.Button(
            self._paths_header, text=self._paths_btn_text(),
            command=self._toggle_paths, padding=(4, 2),
        )
        self._paths_toggle_btn.pack(side="left")

        # Row 3 — Extra path + buttons (SN mode only, collapsed by default)
        self._path_row = ttk.Frame(search_frame)
        self._path_row.grid(row=3, column=0, columnspan=2, sticky="EW", pady=(4, 0))
        self._path_row.columnconfigure(1, weight=1)
        ttk.Label(self._path_row, text="Extra path:").grid(row=0, column=0, sticky="W", padx=(0, 4))
        self.path_entry = ttk.Entry(self._path_row)
        self.path_entry.grid(row=0, column=1, sticky="EW", padx=(0, 8))
        path_btn_frame = ttk.Frame(self._path_row)
        path_btn_frame.grid(row=0, column=2, sticky="W")
        ttk.Button(path_btn_frame, text="Add", command=self._add_path).pack(side="left", padx=(0, 4))
        ttk.Button(path_btn_frame, text="Remove", command=self._remove_path).pack(side="left")
        self._path_row.grid_remove()

        # Row 4 — Path listbox (SN mode only, collapsed by default)
        self._lb_frame = ttk.Frame(search_frame)
        self._lb_frame.grid(row=4, column=0, columnspan=2, sticky="EW", pady=(2, 0))
        self._lb_frame.columnconfigure(0, weight=1)

        self.path_listbox = tk.Listbox(
            self._lb_frame, height=3, selectmode=tk.SINGLE, activestyle="dotbox",
            bg=_PALETTE["bg_input"], fg=_PALETTE["text"],
            selectbackground=_PALETTE["select_bg"],
            selectforeground=_PALETTE["text"],
            borderwidth=0, highlightthickness=1,
            highlightcolor=_PALETTE["border"],
            highlightbackground=_PALETTE["border"],
            relief="flat",
        )
        self.path_listbox.grid(row=0, column=0, sticky="EW")
        lb_scroll = ttk.Scrollbar(
            self._lb_frame, orient="vertical", command=self.path_listbox.yview)
        lb_scroll.grid(row=0, column=1, sticky="NS")
        self.path_listbox.configure(yscrollcommand=lb_scroll.set)
        for p in self._extra_paths:
            self.path_listbox.insert(tk.END, p)
        self._lb_frame.grid_remove()

        # Row 5 — Search button
        self.search_btn = ttk.Button(
            search_frame, text="Search", command=self._start_search)
        self.search_btn.grid(
            row=5, column=0, columnspan=2, sticky="EW", pady=(8, 0))

        self.search_entry.focus()

        # ── Zone 2: Results list ──────────────────────────────────────
        results_frame = ttk.LabelFrame(root, text="Results", padding=6)
        results_frame.grid(
            row=1, column=0, sticky="NSEW", padx=6, pady=2)
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(1, weight=1)

        # Row 0 — count label + filter checkboxes
        header_frame = ttk.Frame(results_frame)
        header_frame.grid(row=0, column=0, sticky="EW")
        header_frame.columnconfigure(0, weight=1)

        self.results_count_label = ttk.Label(
            header_frame, text="No results yet.", style="Dim.TLabel")
        self.results_count_label.grid(row=0, column=0, sticky="W")

        ttk.Checkbutton(
            header_frame, text="Pass",
            variable=self._show_pass, command=self._apply_filter,
        ).grid(row=0, column=1, padx=(8, 0))
        ttk.Checkbutton(
            header_frame, text="Fail",
            variable=self._show_fail, command=self._apply_filter,
        ).grid(row=0, column=2, padx=(4, 0))

        tree_frame = ttk.Frame(results_frame)
        tree_frame.grid(row=1, column=0, sticky="NSEW")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        self._tree = ttk.Treeview(
            tree_frame,
            columns=("name", "date", "machine", "oper"),
            show="headings",
            selectmode="browse",
        )
        self._tree.grid(row=0, column=0, sticky="NSEW")

        self._tree.column("name",    width=380, stretch=True,  minwidth=150, anchor="w")
        self._tree.column("date",    width=155, stretch=False, minwidth=120, anchor="w")
        self._tree.column("machine", width=72,  stretch=False, minwidth=60,  anchor="w")
        self._tree.column("oper",    width=130, stretch=False, minwidth=80,  anchor="w")

        for col in ("name", "date", "machine", "oper"):
            self._tree.heading(col, command=lambda c=col: self._sort_by_column(c))

        self._tree.tag_configure("pass",    foreground=_PALETTE["pass_col"])
        self._tree.tag_configure("fail",    foreground=_PALETTE["fail_col"])
        self._tree.tag_configure("neutral", foreground=_PALETTE["neutral_col"])

        tree_vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        tree_vsb.grid(row=0, column=1, sticky="NS")
        self._tree.configure(yscrollcommand=tree_vsb.set)

        self._tree.bind("<Double-ButtonRelease-1>", self._on_tree_activate)
        self._tree.bind("<Return>", self._on_tree_activate)

        # ── Status bar ────────────────────────────────────────────────
        self.status_var = tk.StringVar(value="Ready.")
        status_bar = ttk.Label(
            root, textvariable=self.status_var,
            style="Status.TLabel", anchor="w", padding=(6, 3))
        status_bar.grid(row=2, column=0, sticky="EW", padx=0, pady=0)

    # ------------------------------------------------------------------
    # Path management
    # ------------------------------------------------------------------

    def _add_path(self):
        p = self.path_entry.get().strip()
        if p and p not in self._extra_paths:
            self._extra_paths.append(p)
            self.path_listbox.insert(tk.END, p)
        self.path_entry.delete(0, tk.END)
        self._paths_toggle_btn.configure(text=self._paths_btn_text())

    def _remove_path(self):
        sel = self.path_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self.path_listbox.delete(idx)
        self._extra_paths.pop(idx)
        self._paths_toggle_btn.configure(text=self._paths_btn_text())

    def _paths_btn_text(self) -> str:
        arrow = "▼" if self._paths_expanded else "▶"
        return f"{arrow}  Extra paths ({len(self._extra_paths)})"

    def _toggle_paths(self):
        self._paths_expanded = not self._paths_expanded
        self._update_paths_visibility()

    def _update_paths_visibility(self):
        self._paths_toggle_btn.configure(text=self._paths_btn_text())
        if self._paths_expanded:
            self._path_row.grid()
            self._lb_frame.grid()
        else:
            self._path_row.grid_remove()
            self._lb_frame.grid_remove()

    def _on_mode_change(self):
        if self._mode.get() == "pn":
            self._search_entry_label.configure(text="Product Number:")
            self._paths_header.grid_remove()
            self._path_row.grid_remove()
            self._lb_frame.grid_remove()
            self._period_row.grid()
        else:
            self._search_entry_label.configure(text="Serial Number:")
            self._period_row.grid_remove()
            self._paths_header.grid()
            self._update_paths_visibility()
        self.search_entry.delete(0, tk.END)
        self.search_entry.focus()

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _start_search(self):
        mode = self._mode.get()
        term = self.search_entry.get().strip()
        if not term:
            label = "Serial" if mode == "sn" else "Product"
            self.status_var.set(f"Error: enter {label} Number.")
            return

        from_month = to_month = None
        if mode == "pn":
            from_month = _parse_month(self.from_month_entry.get())
            to_month   = _parse_month(self.to_month_entry.get())
            if from_month and to_month and from_month > to_month:
                self.status_var.set("Error: 'From' month must not be after 'To' month.")
                return

        self.search_btn.configure(state="disabled")
        self.status_var.set("Searching…")
        self._clear_results()

        t = threading.Thread(
            target=self._search_worker,
            args=(mode, term, list(self._extra_paths), from_month, to_month),
            daemon=True,
        )
        t.start()

    def _search_worker(self, mode: str, term: str, paths: list, from_month=None, to_month=None):
        if mode == "pn":
            try:
                logs = ICTLogSearcher().search(term, from_month=from_month, to_month=to_month)
                logs.sort(key=lambda x: x["date"], reverse=True)
            except Exception as exc:
                self.root.after(0, lambda: self._search_done([], f"Search error: {exc}"))
                return
            self.root.after(0, lambda: self._search_done(logs))
            return

        # SN mode — no date filter
        sn = term
        resolved_pn = None
        try:
            resolved_pn = ProductResolver().get_product_pn(sn)
        except Exception:
            pass

        if not resolved_pn:
            event = threading.Event()
            result_holder = [None]

            def ask_pn():
                result_holder[0] = self._ask_manual_pn(sn)
                event.set()

            self.root.after(0, ask_pn)
            event.wait()
            resolved_pn = result_holder[0]

        if not resolved_pn:
            self.root.after(
                0, lambda: self._search_done([], "PN resolution failed — search aborted."))
            return

        try:
            ict = ICTLogSearcher()
            if resolved_pn.upper().startswith("SFG"):
                logs = ict.search(sn)
            else:
                logs = LogSearcher(paths).search(resolved_pn, sn)
                if not logs:
                    logs = ict.search(sn)
            logs.sort(key=lambda x: x["date"], reverse=True)
        except Exception as exc:
            self.root.after(0, lambda: self._search_done([], f"Search error: {exc}"))
            return

        self.root.after(0, lambda: self._search_done(logs))

    def _ask_manual_pn(self, sn: str):
        dialog = tk.Toplevel(self.root)
        dialog.configure(bg=_PALETTE["bg"])
        dialog.title("Product Number Required")
        dialog.resizable(False, False)
        dialog.grab_set()

        ttk.Label(
            dialog,
            text=f"Could not resolve PN for SN '{sn}'.\nEnter Product Number manually:",
            padding=10,
        ).pack()
        entry = ttk.Entry(dialog, width=30)
        entry.pack(padx=10, pady=(0, 6))
        entry.focus()

        result = [None]

        def ok():
            result[0] = entry.get().strip() or None
            dialog.destroy()

        def cancel():
            dialog.destroy()

        btn_frame = ttk.Frame(dialog)
        btn_frame.pack(pady=(0, 10))
        ttk.Button(btn_frame, text="OK", command=ok).pack(side="left", padx=4)
        ttk.Button(btn_frame, text="Cancel", command=cancel).pack(
            side="left", padx=4)
        entry.bind("<Return>", lambda _e: ok())
        dialog.wait_window()
        return result[0]

    def _search_done(self, logs: list, error_msg: str = ""):
        self.search_btn.configure(state="normal")
        if error_msg:
            self.status_var.set(error_msg)
            return
        self._logs = logs
        count = len(logs)
        self.status_var.set(
            f"Found {count} log{'s' if count != 1 else ''}." if count
            else "No logs found."
        )
        self._apply_filter()

    def _apply_filter(self):
        show_pass = self._show_pass.get()
        show_fail = self._show_fail.get()

        def _keep(log: dict) -> bool:
            tag = _color_tag_for_log(log)
            if tag == "pass_tag":
                return show_pass
            if tag == "fail_tag":
                return show_fail
            return True

        filtered = [log for log in self._logs if _keep(log)]
        filtered.sort(key=self._sort_key, reverse=self._sort_rev)
        self._populate_results(filtered)
        self._update_heading_arrows()

        total = len(self._logs)
        shown = len(filtered)
        if total == 0:
            self.results_count_label.configure(text="No results.")
        elif shown == total:
            self.results_count_label.configure(
                text=f"{total} result{'s' if total != 1 else ''}")
        else:
            self.results_count_label.configure(
                text=f"{shown} of {total} result{'s' if total != 1 else ''}")

    def _sort_key(self, log: dict):
        col = self._sort_col
        if col == "date":
            dt = _parse_filename_date(log["name"])
            if dt:
                return dt
            ts = log.get("date") or 0.0
            return datetime.fromtimestamp(ts) if ts else datetime.min
        if col == "name":
            return log.get("name", "").lower()
        if col == "machine":
            tags = log.get("tags", [])
            return tags[1] if len(tags) > 1 else ""
        if col == "oper":
            oid = log.get("oper_id") or ""
            return _RUNNERS.get(oid, oid).lower()
        return ""

    def _sort_by_column(self, col: str):
        if self._sort_col == col:
            self._sort_rev = not self._sort_rev
        else:
            self._sort_col = col
            self._sort_rev = (col == "date")
        self._apply_filter()

    def _update_heading_arrows(self):
        labels = {"name": "File", "date": "Date", "machine": "Machine", "oper": "Operator"}
        for col, label in labels.items():
            arrow = (" ↓" if self._sort_rev else " ↑") if col == self._sort_col else ""
            self._tree.heading(col, text=label + arrow)

    # ------------------------------------------------------------------
    # Results display
    # ------------------------------------------------------------------

    def _clear_results(self):
        self._logs = []
        self._displayed_logs = []
        self._tree.delete(*self._tree.get_children())
        self.results_count_label.configure(text="Searching…")

    def _populate_results(self, logs: list):
        self._displayed_logs = logs
        self._tree.delete(*self._tree.get_children())

        for idx, log in enumerate(logs):
            is_ict = "ICT" in log.get("tags", [])

            dt = _parse_filename_date(log["name"])
            if dt:
                date_str = dt.strftime("%Y-%m-%d  %H:%M:%S")
            elif log.get("datetime"):
                date_str = log["datetime"]
            else:
                date_str = ""

            machine = log["tags"][1] if is_ict and len(log.get("tags", [])) > 1 else ""

            oper_id = log.get("oper_id") or ""
            oper_label = _RUNNERS.get(oper_id, oper_id) if oper_id else ""

            row_tag = _color_tag_for_log(log).replace("_tag", "")

            self._tree.insert(
                "", "end",
                iid=str(idx),
                values=(log["name"], date_str, machine, oper_label),
                tags=(row_tag,),
            )

    # ------------------------------------------------------------------
    # File viewer
    # ------------------------------------------------------------------

    def _open_in_libreoffice(self, filepath):
        import subprocess
        try:
            subprocess.Popen([
                "libreoffice", "--calc", "--norestore",
                "--infilter=Text - txt - csv (StarCalc):44,34,76,1",
                filepath,
            ])
        except FileNotFoundError:
            self.status_var.set("LibreOffice not found, opening in terminal...")
            _open_in_terminal(filepath)

    def _on_tree_activate(self, event=None):
        sel = self._tree.selection()
        if not sel:
            return
        try:
            log = self._displayed_logs[int(sel[0])]
        except (IndexError, ValueError):
            return
        filepath = log["path"]
        try:
            if filepath.lower().endswith(".csv"):
                self._open_in_libreoffice(filepath)
            else:
                _open_in_terminal(filepath)
            self.status_var.set(f"Opened: {Path(filepath).name}")
        except Exception as exc:
            self.status_var.set(f"Error opening file: {exc}")


if __name__ == "__main__":
    root = tk.Tk()
    app = LogReaderApp(root)
    root.mainloop()
