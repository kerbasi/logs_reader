import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

INDEX_PATH = "/tmp/ict_log_index.json"
HOT_REBUILD_INTERVAL = 30
FULL_REBUILD_INTERVAL = 86400


def _yyyymm(dt: datetime) -> str:
    return dt.strftime("%Y%m")


def _hot_months() -> List[str]:
    now = datetime.now()
    if now.month > 1:
        prev = datetime(now.year, now.month - 1, 1)
    else:
        prev = datetime(now.year - 1, 12, 1)
    return [_yyyymm(prev), _yyyymm(now)]


class ICTIndex:
    BASE_PATH = "/usr/flexfs/ict_tri_logs"
    MACHINES = [f"TRI{n:03d}" for n in range(401, 422)]

    def __init__(self, index_path: str = INDEX_PATH):
        self._index_path = index_path
        self._data: Dict[str, List[str]] = {}
        self._lock = threading.RLock()
        self._last_full_build: float = 0.0
        self._load()
        if not self._data:
            self._build(months=_hot_months())
        self._start_background()

    def _load(self) -> None:
        try:
            with open(self._index_path, "r") as f:
                raw = json.load(f)
        except (OSError, json.JSONDecodeError):
            return
        full_built_at = raw.pop("_full_built_at", None)
        raw.pop("_built_at", None)
        if full_built_at:
            try:
                self._last_full_build = datetime.fromisoformat(full_built_at).timestamp()
            except ValueError:
                pass
        with self._lock:
            self._data = raw

    def _save(self, is_full: bool = False) -> None:
        with self._lock:
            payload = dict(self._data)
        payload["_built_at"] = datetime.now().isoformat()
        if is_full:
            payload["_full_built_at"] = datetime.now().isoformat()
        try:
            with open(self._index_path, "w") as f:
                json.dump(payload, f)
        except OSError:
            pass

    def _scan_machine_month(self, machine: str, month: str):
        key = f"{machine}/{month}"
        path = Path(self.BASE_PATH) / machine / month
        try:
            files = [f.name for f in path.iterdir() if f.is_file() and f.name.lower().endswith(".csv")]
        except OSError:
            files = []
        return key, files

    def _build(self, months: Optional[List[str]] = None) -> None:
        tasks = []
        if months is None:
            for machine in self.MACHINES:
                machine_dir = Path(self.BASE_PATH) / machine
                try:
                    for child in machine_dir.iterdir():
                        if child.is_dir() and child.name.isdigit() and len(child.name) == 6:
                            tasks.append((machine, child.name))
                except OSError:
                    pass
        else:
            for machine in self.MACHINES:
                for month in months:
                    tasks.append((machine, month))

        new_data: Dict[str, List[str]] = {}
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(self._scan_machine_month, m, mo): (m, mo) for m, mo in tasks}
            for future in as_completed(futures):
                key, files = future.result()
                new_data[key] = files

        is_full = months is None
        with self._lock:
            if is_full:
                self._data = new_data
            else:
                self._data.update(new_data)
        self._save(is_full=is_full)

    def _start_background(self) -> None:
        threading.Thread(target=self._background_loop, daemon=True).start()

    def _background_loop(self) -> None:
        last_full = self._last_full_build
        while True:
            time.sleep(HOT_REBUILD_INTERVAL)
            if time.time() - last_full >= FULL_REBUILD_INTERVAL:
                self._build(months=None)
                last_full = time.time()
            else:
                self._build(months=_hot_months())

    def search(self, sn: str) -> List[Dict]:
        pattern = re.compile(r"(?<![A-Za-z0-9])" + re.escape(sn) + r"(?![A-Za-z0-9])")
        with self._lock:
            snapshot = dict(self._data)

        results = []
        for key, files in snapshot.items():
            machine, month = key.split("/", 1)
            for fname in files:
                if pattern.search(fname):
                    full_path = Path(self.BASE_PATH) / machine / month / fname
                    try:
                        mtime = full_path.stat().st_mtime
                    except OSError:
                        mtime = 0.0
                    results.append({
                        "path": str(full_path),
                        "name": fname,
                        "date": mtime,
                        "tags": ["ICT", machine],
                        "description": f"{machine} / {month}",
                    })

        results.sort(key=lambda x: x["date"])
        return results


_index: Optional[ICTIndex] = None
_index_lock = threading.Lock()


def get_index() -> ICTIndex:
    global _index
    if _index is None:
        with _index_lock:
            if _index is None:
                _index = ICTIndex()
    return _index
