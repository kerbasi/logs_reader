import sys
import shutil
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from src.core import ProductResolver, LogSearcher
from src.interface import format_description

DEFAULT_PATHS = [
    "/usr/flexfs/lion_cub/log/ft",
    "/usr/flexfs/lion_cub/log",
    "/usr/flexfs/lion_cub/log/customization",
    "/usr/flexfs/lion_cub/log/dbg/ft",
    "/usr/flexfs/lion_cub/log/dbg",
    "/usr/flexfs/lion_cub/log/dbg/customization",
]


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
    desc = (log.get("description") or "").lower()
    if "pass" in desc:
        return "pass_tag"
    if any(x in desc for x in ("fail", "error", "timeout", "exception")):
        return "fail_tag"
    return "neutral_tag"


class LogReaderApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Log Reader")
        self.root.minsize(900, 700)

        self._logs: list = []
        self._extra_paths: list = list(DEFAULT_PATHS)

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
        search_frame.columnconfigure(3, weight=1)

        # Row 0 — SN / PN entries
        ttk.Label(search_frame, text="Serial Number:").grid(
            row=0, column=0, sticky="W", padx=(0, 4))
        self.sn_entry = ttk.Entry(search_frame)
        self.sn_entry.grid(row=0, column=1, sticky="EW", padx=(0, 12))

        ttk.Label(search_frame, text="Product Number (optional):").grid(
            row=0, column=2, sticky="W", padx=(0, 4))
        self.pn_entry = ttk.Entry(search_frame)
        self.pn_entry.grid(row=0, column=3, sticky="EW")

        # Row 1 — extra path entry + buttons
        ttk.Label(search_frame, text="Extra path:").grid(
            row=1, column=0, sticky="W", pady=(6, 0), padx=(0, 4))
        self.path_entry = ttk.Entry(search_frame)
        self.path_entry.grid(
            row=1, column=1, sticky="EW", pady=(6, 0), padx=(0, 8))

        btn_frame = ttk.Frame(search_frame)
        btn_frame.grid(row=1, column=2, columnspan=2, sticky="W", pady=(6, 0))
        ttk.Button(btn_frame, text="Add Path", command=self._add_path).pack(
            side="left", padx=(0, 4))
        ttk.Button(btn_frame, text="Remove", command=self._remove_path).pack(
            side="left")

        # Row 2 — path listbox
        lb_frame = ttk.Frame(search_frame)
        lb_frame.grid(
            row=2, column=0, columnspan=4, sticky="EW", pady=(4, 0))
        lb_frame.columnconfigure(0, weight=1)

        self.path_listbox = tk.Listbox(lb_frame, height=3,
                                       selectmode=tk.SINGLE,
                                       activestyle="dotbox")
        self.path_listbox.grid(row=0, column=0, sticky="EW")
        lb_scroll = ttk.Scrollbar(
            lb_frame, orient="vertical", command=self.path_listbox.yview)
        lb_scroll.grid(row=0, column=1, sticky="NS")
        self.path_listbox.configure(yscrollcommand=lb_scroll.set)
        for p in self._extra_paths:
            self.path_listbox.insert(tk.END, p)

        # Row 3 — Search button
        self.search_btn = ttk.Button(
            search_frame, text="Search", command=self._start_search)
        self.search_btn.grid(
            row=3, column=0, columnspan=4, sticky="EW", pady=(8, 0))
        self.sn_entry.bind("<Return>", lambda _e: self._start_search())

        # ── Zone 2: Results list ──────────────────────────────────────
        results_frame = ttk.LabelFrame(root, text="Results", padding=6)
        results_frame.grid(
            row=1, column=0, sticky="NSEW", padx=6, pady=2)
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(1, weight=1)

        self.results_count_label = ttk.Label(
            results_frame, text="No results yet.")
        self.results_count_label.grid(row=0, column=0, sticky="W")

        res_text_frame = ttk.Frame(results_frame)
        res_text_frame.grid(row=1, column=0, sticky="NSEW")
        res_text_frame.columnconfigure(0, weight=1)
        res_text_frame.rowconfigure(0, weight=1)

        self.results_text = tk.Text(
            res_text_frame, state="disabled", wrap="none",
            cursor="arrow", font=("TkFixedFont", 9))
        self.results_text.grid(row=0, column=0, sticky="NSEW")

        res_vsb = ttk.Scrollbar(
            res_text_frame, orient="vertical",
            command=self.results_text.yview)
        res_vsb.grid(row=0, column=1, sticky="NS")
        res_hsb = ttk.Scrollbar(
            res_text_frame, orient="horizontal",
            command=self.results_text.xview)
        res_hsb.grid(row=1, column=0, sticky="EW")
        self.results_text.configure(
            yscrollcommand=res_vsb.set, xscrollcommand=res_hsb.set)

        # Colour tags
        self.results_text.tag_configure(
            "pass_tag", foreground="green")
        self.results_text.tag_configure(
            "fail_tag", foreground="red")
        self.results_text.tag_configure(
            "neutral_tag", foreground="#1a6fbf")
        self.results_text.tag_configure(
            "meta_tag", foreground="#666666")
        self.results_text.tag_configure(
            "clickable", font=("TkFixedFont", 9, "underline"))

        self.results_text.bind("<Button-1>", self._on_result_click)

        # ── Status bar ────────────────────────────────────────────────
        self.status_var = tk.StringVar(value="Ready.")
        status_bar = ttk.Label(
            root, textvariable=self.status_var,
            relief="sunken", anchor="w", padding=(4, 2))
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

    def _remove_path(self):
        sel = self.path_listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self.path_listbox.delete(idx)
        self._extra_paths.pop(idx)

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def _start_search(self):
        sn = self.sn_entry.get().strip()
        if not sn:
            self.status_var.set("Error: Serial Number is required.")
            return

        pn = self.pn_entry.get().strip() or None

        self.search_btn.configure(state="disabled")
        self.status_var.set("Searching…")
        self._clear_results()

        t = threading.Thread(
            target=self._search_worker,
            args=(sn, pn, list(self._extra_paths)),
            daemon=True,
        )
        t.start()

    def _search_worker(self, sn: str, pn_hint, paths: list):
        resolved_pn = pn_hint

        if not resolved_pn:
            try:
                resolver = ProductResolver()
                resolved_pn = resolver.get_product_pn(sn)
            except Exception as exc:
                resolved_pn = None

        if not resolved_pn:
            # Ask user for manual entry on the main thread
            event = threading.Event()
            result_holder = [None]

            def ask_pn():
                val = self._ask_manual_pn(sn)
                result_holder[0] = val
                event.set()

            self.root.after(0, ask_pn)
            event.wait()
            resolved_pn = result_holder[0]

        if not resolved_pn:
            self.root.after(
                0, lambda: self._search_done(
                    [], "PN resolution failed — search aborted."))
            return

        try:
            searcher = LogSearcher(paths)
            logs = searcher.search(resolved_pn, sn)
            # Sort newest first (mirrors console display_results)
            logs.sort(key=lambda x: x["date"], reverse=True)
        except Exception as exc:
            self.root.after(
                0, lambda: self._search_done([], f"Search error: {exc}"))
            return

        self.root.after(0, lambda: self._search_done(logs))

    def _ask_manual_pn(self, sn: str):
        dialog = tk.Toplevel(self.root)
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
        self._populate_results(logs)
        count = len(logs)
        self.status_var.set(
            f"Found {count} log{'s' if count != 1 else ''}." if count
            else "No logs found."
        )
        self.results_count_label.configure(
            text=f"{count} result{'s' if count != 1 else ''}" if count
            else "No results.")

    # ------------------------------------------------------------------
    # Results display
    # ------------------------------------------------------------------

    def _clear_results(self):
        self._logs = []
        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", tk.END)
        self.results_text.configure(state="disabled")
        self.results_count_label.configure(text="Searching…")

    def _populate_results(self, logs: list):
        self.results_text.configure(state="normal")
        self.results_text.delete("1.0", tk.END)

        # Tag for each log index stored as "row_N"
        for idx, log in enumerate(logs):
            color_tag = _color_tag_for_log(log)
            line_tag = f"row_{idx}"
            start = self.results_text.index(tk.INSERT)

            header = f"[{idx + 1}] {log['name']}\n"
            self.results_text.insert(tk.END, header, (color_tag, "clickable", line_tag))

            path_line = f"    Path: {log['path']}\n"
            self.results_text.insert(tk.END, path_line, ("meta_tag", line_tag))

            if log.get("description"):
                info_line = f"    Info: {format_description(log['description'])}\n"
                self.results_text.insert(tk.END, info_line, ("meta_tag", line_tag))

            self.results_text.insert(tk.END, "\n")

            # Bind click on entire block
            self.results_text.tag_bind(
                line_tag, "<Button-1>",
                lambda _e, i=idx: self._load_file(i),
            )
            self.results_text.tag_configure(line_tag)

        self.results_text.configure(state="disabled")

    def _on_result_click(self, event):
        # Handled by per-row tag bindings; this is a fallback no-op
        pass

    # ------------------------------------------------------------------
    # File viewer
    # ------------------------------------------------------------------

    def _load_file(self, idx: int):
        if idx < 0 or idx >= len(self._logs):
            return
        filepath = self._logs[idx]["path"]
        try:
            _open_in_terminal(filepath)
            self.status_var.set(f"Opened: {Path(filepath).name}")
        except Exception as exc:
            self.status_var.set(f"Error opening file: {exc}")


if __name__ == "__main__":
    root = tk.Tk()
    app = LogReaderApp(root)
    root.mainloop()
