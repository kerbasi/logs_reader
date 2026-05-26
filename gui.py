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
    r'y(\d{4})[\s_]+m(\d{2})[\s_]+d(\d{2})[\s_]+(\d{2})\.(\d{2})\.(\d{2})'
)
_DATE_RE2 = re.compile(
    r'(\d{4})(\d{2})(\d{2})[_\s](\d{2})\.(\d{2})\.(\d{2})'
)

def _parse_filename_date(fname: str):
    """Extract datetime from filename.

    Handles ICT format  'y2026 m05 d10 14.45.53'
    and standard format '20260504_04.10.16'.
    """
    for pat in (_DATE_RE, _DATE_RE2):
        m = pat.search(fname)
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
    for term in ("xterm", "gnome-terminal", "konsole", "xfce4-terminal",
                 "lxterminal", "urxvt", "alacritty", "kitty"):
        if shutil.which(term):
            if term == "xterm":
                subprocess.Popen([
                    term,
                    "-fa", "Monospace", "-fs", "13",
                    "-bg", _PALETTE["bg"],
                    "-fg", _PALETTE["text"],
                    "-cr", _PALETTE["accent"],
                    "-sl", "10000",
                    "-geometry", "220x55",
                    "-title", Path(filepath).name,
                    "-e", "less", "-SR", filepath,
                ])
            elif term == "gnome-terminal":
                subprocess.Popen([term, "--", "less", "-SR", filepath])
            elif term in ("alacritty", "kitty"):
                subprocess.Popen([term, "-e", "less", "-SR", filepath])
            else:
                subprocess.Popen([term, "-e", f"less -SR '{filepath}'"])
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


def _group_logs(logs: list) -> list:
    """Group SUMMARY companions under their main log as (main, [children]) tuples.

    Matching strategy:
    1. Datetime-key match: parse date from both filenames; match by (parent_dir, dt).
    2. Positional fallback: when dates are unparseable, pair mains and SUMMARYs in
       the same directory in sorted order (1-to-1). Extras stay standalone.
    Only non-None dt keys are used in the index to prevent all undated SUMMARYs
    from collapsing onto the first main.
    """
    mains = []
    summary_by_key: dict = {}   # (parent, dt) → [log, ...]  — only dt != None
    summary_by_dir: dict = {}   # parent → [log, ...]         — dt == None fallback

    for log in logs:
        if "SUMMARY" in log["name"].upper():
            dt = _parse_filename_date(log["name"])
            parent = str(Path(log["path"]).parent)
            if dt is not None:
                summary_by_key.setdefault((parent, dt), []).append(log)
            else:
                summary_by_dir.setdefault(parent, []).append(log)
        else:
            mains.append(log)

    result = []
    # Track which mains in each dir have been processed for positional pairing
    dir_main_counts: dict = {}

    for main in mains:
        dt = _parse_filename_date(main["name"])
        parent = str(Path(main["path"]).parent)

        if dt is not None:
            children = summary_by_key.pop((parent, dt), [])
        else:
            # Positional pairing: assign the next undated SUMMARY in the same dir
            undated = summary_by_dir.get(parent, [])
            idx = dir_main_counts.get(parent, 0)
            dir_main_counts[parent] = idx + 1
            children = [undated[idx]] if idx < len(undated) else []

        result.append((main, children))

    # Remaining unmatched SUMMARYs — show as standalone entries
    for children_list in summary_by_key.values():
        for s in children_list:
            result.append((s, []))
    for parent, undated in summary_by_dir.items():
        used = dir_main_counts.get(parent, 0)
        for s in undated[used:]:
            result.append((s, []))

    return result



def _build_info_line(log: dict) -> str:
    """Return formatted Info line text for a log entry."""
    is_ict = "ICT" in log.get("tags", [])
    if is_ict:
        oper_id = log.get("oper_id") or ""
        oper_name = _RUNNERS.get(oper_id, oper_id) if oper_id else ""
        desc = log.get("description") or ""
        parts = [p for p in (desc, f"Operator: {oper_name}" if oper_name else "") if p]
        return "   |   ".join(parts)
    else:
        raw = log.get("description") or ""
        return format_description(raw) if raw else ""


_PALETTE = {
    "bg":                   "#18181B",   # app window bg (near-black)
    "bg_widget":            "#27272A",   # panel / list bg
    "bg_input":             "#1F1F23",   # entry field bg
    "accent":               "#3B82F6",   # calm blue accent
    "text":                 "#F4F4F5",   # primary text
    "text_dim":             "#71717A",   # secondary text (paths, info)
    "pass_col":             "#10B981",   # pass green
    "fail_col":             "#F87171",   # fail red (soft)
    "ict_col":              "#38BDF8",   # ICT sky-blue
    "neutral_col":          "#94A3B8",   # neutral slate
    "number_col":           "#06B6D4",   # teal for [n] result numbers
    "border":               "#3F3F46",   # subtle border
    "btn":                  "#2563EB",   # primary button (Search)
    "btn_active":           "#1D4ED8",   # primary hover
    "btn_secondary":        "#3F3F46",   # secondary button (Add Path)
    "btn_secondary_active": "#52525B",
    "btn_danger":           "#7F1D1D",   # danger button (Remove)
    "btn_danger_active":    "#991B1B",
    "status_bg":            "#09090B",   # status bar
    "select_bg":            "#2563EB",
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

    style.configure("TFrame", background=_PALETTE["bg"])

    style.configure("TLabelframe",
        background=_PALETTE["bg"],
        bordercolor=_PALETTE["border"],
        relief="groove",
    )
    style.configure("TLabelframe.Label",
        background=_PALETTE["bg"],
        foreground=_PALETTE["accent"],
        font=(_FONT_UI[0], _FONT_UI[1] - 1),
        padding=(4, 0),
    )

    # ── Primary button (Search) ───────────────────────────────────────
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
        foreground=[("disabled", _PALETTE["text_dim"])],
        relief=[("pressed", "flat")],
    )

    # ── Secondary button (Add Path, ▶ toggle) ────────────────────────
    style.configure("Secondary.TButton",
        background=_PALETTE["btn_secondary"],
        foreground=_PALETTE["text"],
        borderwidth=0,
        relief="flat",
        padding=(10, 6),
        font=_FONT_UI,
        focuscolor=_PALETTE["accent"],
    )
    style.map("Secondary.TButton",
        background=[
            ("active",  _PALETTE["btn_secondary_active"]),
            ("pressed", _PALETTE["btn_secondary_active"]),
        ],
        relief=[("pressed", "flat")],
    )

    # ── Danger button (Remove) ───────────────────────────────────────
    style.configure("Danger.TButton",
        background=_PALETTE["btn_danger"],
        foreground=_PALETTE["text"],
        borderwidth=0,
        relief="flat",
        padding=(10, 6),
        font=_FONT_UI,
        focuscolor=_PALETTE["accent"],
    )
    style.map("Danger.TButton",
        background=[
            ("active",  _PALETTE["btn_danger_active"]),
            ("pressed", _PALETTE["btn_danger_active"]),
        ],
        relief=[("pressed", "flat")],
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
        padding=(5, 5),
        font=_FONT_UI,
    )
    style.map("TEntry",
        bordercolor=[("focus", _PALETTE["accent"])],
        lightcolor=[("focus", _PALETTE["accent"])],
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
        width=7,
    )
    style.map("TScrollbar",
        background=[("active", _PALETTE["border"])],
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
            ("selected",  _PALETTE["accent"]),
            ("active",    _PALETTE["bg_widget"]),
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
            ("selected",  _PALETTE["accent"]),
            ("active",    _PALETTE["bg_widget"]),
            ("!selected", _PALETTE["bg_input"]),
        ],
    )

    style.configure("Treeview",
        background=_PALETTE["bg_widget"],
        foreground=_PALETTE["text"],
        fieldbackground=_PALETTE["bg_widget"],
        rowheight=24,
        borderwidth=0,
        relief="flat",
        font=_FONT_MONO,
    )
    style.configure("Treeview.Heading",
        background=_PALETTE["bg_input"],
        foreground=_PALETTE["neutral_col"],
        borderwidth=0,
        relief="flat",
        font=(_FONT_UI[0], _FONT_UI[1] - 1),
        padding=(6, 4),
    )
    style.map("Treeview",
        background=[("selected", _PALETTE["select_bg"])],
        foreground=[("selected", _PALETTE["text"])],
    )
    style.map("Treeview.Heading",
        background=[("active", _PALETTE["bg_widget"])],
        foreground=[("active", _PALETTE["text"])],
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
        self._iid_to_log: dict = {}
        self._sort_col: str = "date"
        self._sort_rev: bool = True
        self._paths_expanded = False

        self._ict_index_var = tk.StringVar()

        _apply_theme(root)
        self._build_ui()
        self._init_ict_status()

    def _init_ict_status(self):
        def _setup():
            try:
                from src.ict_index import get_index
                idx = get_index()

                def on_status(msg: str):
                    self.root.after(0, lambda m=msg: self._set_ict_status(m))

                idx.add_status_callback(on_status)
                if idx.is_building:
                    self.root.after(0, lambda: self._set_ict_status("ICT index: updating…"))
            except Exception:
                pass  # status notifications are best-effort

        threading.Thread(target=_setup, daemon=True).start()

    def _set_ict_status(self, msg: str):
        self._ict_index_var.set(msg)
        if msg:
            self._ict_index_label.grid()
        else:
            self._ict_index_label.grid_remove()
        if msg == "ICT index: ready":
            self.root.after(3000, lambda: self._set_ict_status(""))

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
        self._search_var = tk.StringVar()
        self.search_entry = ttk.Entry(entry_row, textvariable=self._search_var)
        self.search_entry.grid(row=0, column=1, sticky="EW")
        self.search_entry.bind("<Return>", lambda _e: self._start_search())

        def _force_upper(*_):
            val = self._search_var.get()
            upper = val.upper()
            if val != upper:
                try:
                    pos = self.search_entry.index(tk.INSERT)
                    self._search_var.set(upper)
                    self.search_entry.icursor(pos)
                except Exception:
                    self._search_var.set(upper)

        self._search_var.trace_add("write", _force_upper)

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
            command=self._toggle_paths, style="Secondary.TButton",
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
        ttk.Button(path_btn_frame, text="Add", command=self._add_path,
                   style="Secondary.TButton").pack(side="left", padx=(0, 4))
        ttk.Button(path_btn_frame, text="Remove", command=self._remove_path,
                   style="Danger.TButton").pack(side="left")
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
        results_frame.rowconfigure(2, weight=1)

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

        self._ict_index_label = ttk.Label(
            results_frame, textvariable=self._ict_index_var, style="Dim.TLabel")
        self._ict_index_label.grid(row=1, column=0, sticky="W", padx=2, pady=(0, 2))
        self._ict_index_label.grid_remove()

        results_inner = ttk.Frame(results_frame)
        results_inner.grid(row=2, column=0, sticky="NSEW")
        results_inner.columnconfigure(0, weight=1)
        results_inner.rowconfigure(0, weight=1)

        # ── SN results: text widget (shown in SN mode) ─────────────────
        self._sn_frame = ttk.Frame(results_inner)
        self._sn_frame.grid(row=0, column=0, sticky="NSEW")
        self._sn_frame.columnconfigure(0, weight=1)
        self._sn_frame.rowconfigure(0, weight=1)

        self._text = tk.Text(
            self._sn_frame,
            state="disabled",
            wrap="none",
            bg=_PALETTE["bg_widget"],
            fg=_PALETTE["text"],
            font=_FONT_MONO,
            borderwidth=0,
            highlightthickness=0,
            selectbackground=_PALETTE["select_bg"],
            selectforeground=_PALETTE["text"],
            cursor="arrow",
            padx=12,
            pady=8,
            spacing1=1,
            spacing3=3,
        )
        self._text.grid(row=0, column=0, sticky="NSEW")
        self._text.tag_configure("pass",    foreground=_PALETTE["pass_col"])
        self._text.tag_configure("fail",    foreground=_PALETTE["fail_col"])
        self._text.tag_configure("neutral", foreground=_PALETTE["neutral_col"])
        self._text.tag_configure("dim",     foreground=_PALETTE["text_dim"])
        self._text.tag_configure("number",  foreground=_PALETTE["number_col"])

        sn_vsb = ttk.Scrollbar(self._sn_frame, orient="vertical", command=self._text.yview)
        sn_vsb.grid(row=0, column=1, sticky="NS")
        sn_hsb = ttk.Scrollbar(self._sn_frame, orient="horizontal", command=self._text.xview)
        sn_hsb.grid(row=1, column=0, sticky="EW")
        self._text.configure(yscrollcommand=sn_vsb.set, xscrollcommand=sn_hsb.set)

        # ── ICT/PN results: treeview (shown in PN mode, hidden by default) ─
        self._ict_frame = ttk.Frame(results_inner)
        self._ict_frame.grid(row=0, column=0, sticky="NSEW")
        self._ict_frame.columnconfigure(0, weight=1)
        self._ict_frame.rowconfigure(0, weight=1)
        self._ict_frame.grid_remove()

        self._tree = ttk.Treeview(
            self._ict_frame,
            columns=("name", "date", "machine", "oper"),
            show="headings",
            selectmode="browse",
        )
        self._tree.grid(row=0, column=0, sticky="NSEW")
        self._tree.column("name",    width=260, stretch=True,  minwidth=150, anchor="w")
        self._tree.column("date",    width=170, stretch=False, minwidth=140, anchor="w")
        self._tree.column("machine", width=80,  stretch=False, minwidth=60,  anchor="w")
        self._tree.column("oper",    width=160, stretch=False, minwidth=80,  anchor="w")

        for col in ("name", "date", "machine", "oper"):
            self._tree.heading(col, command=lambda c=col: self._sort_by_column(c))

        self._tree.tag_configure("pass",    foreground=_PALETTE["pass_col"])
        self._tree.tag_configure("fail",    foreground=_PALETTE["fail_col"])
        self._tree.tag_configure("neutral", foreground=_PALETTE["neutral_col"])
        self._tree.tag_configure("info",    foreground=_PALETTE["text_dim"])


        ict_vsb = ttk.Scrollbar(self._ict_frame, orient="vertical", command=self._tree.yview)
        ict_vsb.grid(row=0, column=1, sticky="NS")
        self._tree.configure(yscrollcommand=ict_vsb.set)

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
            self._sn_frame.grid_remove()
            self._ict_frame.grid()
        else:
            self._search_entry_label.configure(text="Serial Number:")
            self._period_row.grid_remove()
            self._paths_header.grid()
            self._update_paths_visibility()
            self._ict_frame.grid_remove()
            self._sn_frame.grid()
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
        is_pn_mode = self._mode.get() == "pn"
        capped = is_pn_mode and shown > self._TREE_MAX_ROWS
        if total == 0:
            self.results_count_label.configure(text="No results.")
        elif capped:
            self.results_count_label.configure(
                text=f"Showing {self._TREE_MAX_ROWS} of {shown} results"
                     + (f" (of {total} total)" if shown != total else ""))
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
        labels = {"name": "File", "date": "Date", "machine": "Station", "oper": "Operator"}
        for col, label in labels.items():
            arrow = (" ↓" if self._sort_rev else " ↑") if col == self._sort_col else ""
            self._tree.heading(col, text=label + arrow)

    # ------------------------------------------------------------------
    # Results display
    # ------------------------------------------------------------------

    def _clear_results(self):
        self._logs = []
        self._displayed_logs = []
        self._iid_to_log = {}
        self._tree.delete(*self._tree.get_children())
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")
        self._text.configure(state="disabled")
        self.results_count_label.configure(text="Searching…")

    def _populate_results(self, logs: list):
        if self._mode.get() == "pn":
            self._populate_tree_results(logs)
        else:
            self._populate_text_results(logs)

    def _populate_text_results(self, logs: list):
        self._displayed_logs = logs
        self._iid_to_log = {}
        self._text.configure(state="normal")
        self._text.delete("1.0", "end")

        grouped = _group_logs(logs)
        counter = 0
        for main, companions in grouped:
            counter += 1
            iid = str(counter - 1)
            self._iid_to_log[iid] = main
            tag = _color_tag_for_log(main).replace("_tag", "")
            fname_tag = f"fname_{iid}"

            if counter > 1:
                self._text.insert("end", "\n")

            self._text.insert("end", f"[{counter}]", "number")
            self._text.insert("end", " ")
            self._text.insert("end", main["name"] + "\n", (tag, fname_tag))
            self._text.tag_bind(fname_tag, "<Double-Button-1>",
                                lambda e, i=iid: self._open_log_by_iid(i))
            self._text.tag_configure(fname_tag, underline=False)

            self._text.insert("end", f"      Path: {main['path']}\n", "dim")
            info = _build_info_line(main)
            if info:
                self._text.insert("end", f"      Info: {info}\n", "dim")

            for cidx, child in enumerate(companions):
                ciid = f"c{counter - 1}_{cidx}"
                self._iid_to_log[ciid] = child
                ctag = _color_tag_for_log(child).replace("_tag", "")
                cfname_tag = f"fname_{ciid}"
                self._text.insert("end", "      └ ")
                self._text.insert("end", child["name"] + "\n", (ctag, cfname_tag))
                self._text.tag_bind(cfname_tag, "<Double-Button-1>",
                                    lambda e, i=ciid: self._open_log_by_iid(i))
                self._text.tag_configure(cfname_tag, underline=False)
                self._text.insert("end", f"           Path: {child['path']}\n", "dim")

        self._text.configure(state="disabled")

    _TREE_MAX_ROWS = 300

    def _populate_tree_results(self, logs: list):
        self._displayed_logs = logs
        self._iid_to_log = {}
        self._tree.delete(*self._tree.get_children())

        visible = logs[:self._TREE_MAX_ROWS]
        for idx, (main, companions) in enumerate(_group_logs(visible)):
            parent_iid = f"g{idx}"
            tags = main.get("tags", [])
            dt = _parse_filename_date(main["name"])
            date_str = dt.strftime("%Y-%m-%d  %H:%M:%S") if dt else (main.get("datetime") or "")
            machine = tags[1] if len(tags) > 1 else ""
            tag = _color_tag_for_log(main).replace("_tag", "")

            oper_id = main.get("oper_id") or ""
            oper_name = _RUNNERS.get(oper_id, oper_id) if oper_id else ""

            self._tree.insert("", "end", iid=parent_iid,
                              values=(main["name"], date_str, machine, oper_name), tags=(tag,))
            self._iid_to_log[parent_iid] = main

            # Info sub-row: path only (no stat() call — too slow for large remote result sets)
            self._tree.insert("", "end", iid=f"{parent_iid}_i",
                              values=(f"    Path: {main['path']}", "", "", ""), tags=("info",))
            self._iid_to_log[f"{parent_iid}_i"] = main

            # SUMMARY companions
            for cidx, child in enumerate(companions):
                child_iid = f"g{idx}c{cidx}"
                dt_c = _parse_filename_date(child["name"])
                date_str_c = dt_c.strftime("%Y-%m-%d  %H:%M:%S") if dt_c else (child.get("datetime") or "")
                machine_c = child.get("tags", ["", ""])[1] if len(child.get("tags", [])) > 1 else ""
                ctag = _color_tag_for_log(child).replace("_tag", "")
                self._tree.insert("", "end", iid=child_iid,
                                  values=("  └ " + child["name"], date_str_c, machine_c, ""), tags=(ctag,))
                self._iid_to_log[child_iid] = child

    # ------------------------------------------------------------------
    # File viewer
    # ------------------------------------------------------------------

    def _open_log_by_iid(self, iid: str):
        log = self._iid_to_log.get(iid)
        if not log:
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
        self._open_log_by_iid(sel[0])


if __name__ == "__main__":
    root = tk.Tk()
    app = LogReaderApp(root)
    if sys.platform == "win32":
        root.state("zoomed")
    else:
        try:
            root.attributes("-zoomed", True)
        except tk.TclError:
            pass
    root.mainloop()
