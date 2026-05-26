import json
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

INDEX_PATH = str(Path(__file__).parent.parent / "index" / "ict_log_index.json")
HOT_REBUILD_INTERVAL = 300
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


def _parse_csv_fields(path: Path, *field_names: str) -> Dict[str, Optional[str]]:
    """Return values for requested fields from CSV header + first data row."""
    result: Dict[str, Optional[str]] = {f: None for f in field_names}
    targets = {re.sub(r'[^A-Z0-9]', '', f.upper()) for f in field_names}
    norm_to_orig: Dict[str, str] = {
        re.sub(r'[^A-Z0-9]', '', f.upper()): f for f in field_names
    }
    try:
        with open(path, "r", errors="ignore") as fh:
            header: Optional[list] = None
            for i, line in enumerate(fh):
                if i >= 30:
                    break
                cols = [c.strip().strip('"') for c in line.strip().split(",")]
                norm = [re.sub(r'[^A-Z0-9]', '', c.upper()) for c in cols]
                if header is None:
                    if targets & set(norm):
                        header = norm
                else:
                    for t in targets:
                        if t in header:
                            idx = header.index(t)
                            val = cols[idx].strip() if idx < len(cols) else ""
                            result[norm_to_orig[t]] = val or None
                    break
    except OSError:
        pass
    return result


def _parse_oper_id(path: Path) -> Optional[str]:
    """Return operator ID/name from the first matching column (OperID / OperatorID / Operator)."""
    fields = _parse_csv_fields(path, "OperID", "OperatorID", "Operator")
    return fields["OperID"] or fields["OperatorID"] or fields["Operator"]


def _parse_pn(path: Path) -> Optional[str]:
    """Return PN value from CSV header row + the data row below it."""
    for candidate in ("PN", "PartNo", "PartNumber"):
        val = _parse_csv_fields(path, candidate)[candidate]
        if val:
            return val
    return None


class ICTIndex:
    BASE_PATH = "/usr/flexfs/ict_tri_logs"
    MACHINES = [f"TRI{n:03d}" for n in range(401, 422)]

    def __init__(self, index_path: str = INDEX_PATH):
        self._index_path = index_path
        self._data: Dict[str, List[str]] = {}
        self._pn_index: Dict[str, List[str]] = {}
        self._lock = threading.RLock()
        self._ready = threading.Event()
        self._last_full_build: float = 0.0
        self._building = False
        self._status_callbacks: List = []
        self._cb_lock = threading.Lock()
        self._load()
        if not self._data:
            self._build(months=_hot_months())
        self._ready.set()
        self._start_background(immediate_hot=bool(self._data))

    @property
    def is_building(self) -> bool:
        return self._building

    def add_status_callback(self, cb) -> None:
        with self._cb_lock:
            self._status_callbacks.append(cb)

    def _notify(self, msg: str) -> None:
        with self._cb_lock:
            cbs = list(self._status_callbacks)
        for cb in cbs:
            try:
                cb(msg)
            except Exception:
                pass

    def _load(self) -> None:
        try:
            with open(self._index_path, "r") as f:
                raw = json.load(f)
        except (OSError, json.JSONDecodeError):
            return
        full_built_at = raw.pop("_full_built_at", None)
        raw.pop("_built_at", None)
        pn_index = raw.pop("_pn_index", {})
        if full_built_at:
            try:
                self._last_full_build = datetime.fromisoformat(full_built_at).timestamp()
            except ValueError:
                pass
        # Migrate old format {key: [filename, ...]} → {key: {filename: None}}
        migrated: Dict[str, Dict[str, Optional[str]]] = {}
        for k, v in raw.items():
            if isinstance(v, list):
                migrated[k] = {fname: None for fname in v}
            elif isinstance(v, dict):
                migrated[k] = v
        with self._lock:
            self._data = migrated
            self._pn_index = pn_index

    def _save(self, is_full: bool = False) -> None:
        with self._lock:
            payload = dict(self._data)
            payload["_pn_index"] = dict(self._pn_index)
        payload["_built_at"] = datetime.now().isoformat()
        if is_full:
            payload["_full_built_at"] = datetime.now().isoformat()
        try:
            os.makedirs(os.path.dirname(self._index_path), exist_ok=True)
            with open(self._index_path, "w") as f:
                json.dump(payload, f)
        except OSError:
            pass

    def _scan_machine_month(self, machine: str, month: str):
        key = f"{machine}/{month}"
        path = Path(self.BASE_PATH) / machine / month
        file_map: Dict[str, Optional[str]] = {}   # filename → oper_id
        pn_entries: Dict[str, List[str]] = {}
        try:
            for f in path.iterdir():
                if not (f.is_file() and f.name.lower().endswith(".csv")):
                    continue
                fields = _parse_csv_fields(f, "OperID", "OperatorID", "Operator", "PN", "PartNo", "PartNumber")
                oper_id = fields["OperID"] or fields["OperatorID"] or fields["Operator"]
                pn = fields["PN"] or fields["PartNo"] or fields["PartNumber"]
                file_map[f.name] = oper_id
                if pn:
                    pn_entries.setdefault(pn, []).append(f"{key}/{f.name}")
        except OSError:
            pass
        return key, file_map, pn_entries

    def _build(self, months: Optional[List[str]] = None) -> None:
        self._building = True
        scope = "hot months" if months else "full index"
        self._notify(f"ICT index: updating ({scope})…")
        try:
            self._build_inner(months)
        finally:
            self._building = False
            self._notify("ICT index: ready")

    def _build_inner(self, months: Optional[List[str]] = None) -> None:
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

        new_data: Dict[str, Dict[str, Optional[str]]] = {}
        new_pn_index: Dict[str, List[str]] = {}
        with ThreadPoolExecutor(max_workers=20) as executor:
            futures = {executor.submit(self._scan_machine_month, m, mo): (m, mo) for m, mo in tasks}
            for future in as_completed(futures):
                key, file_map, pn_entries = future.result()
                new_data[key] = file_map
                for pn, paths in pn_entries.items():
                    new_pn_index.setdefault(pn, []).extend(paths)

        is_full = months is None
        with self._lock:
            if is_full:
                self._data = new_data
                self._pn_index = new_pn_index
            else:
                rebuilt_keys = set(new_data.keys())
                self._data.update(new_data)
                for pn in list(self._pn_index.keys()):
                    self._pn_index[pn] = [
                        p for p in self._pn_index[pn]
                        if "/".join(p.split("/", 2)[:2]) not in rebuilt_keys
                    ]
                for pn, paths in new_pn_index.items():
                    self._pn_index.setdefault(pn, []).extend(paths)
        self._save(is_full=is_full)

    def _start_background(self, immediate_hot: bool = False) -> None:
        threading.Thread(target=self._background_loop, args=(immediate_hot,), daemon=True).start()

    def _background_loop(self, immediate_hot: bool = False) -> None:
        # If no prior full build is recorded, treat now as the baseline so a
        # full rebuild isn't triggered after the very first HOT_REBUILD_INTERVAL.
        last_full = self._last_full_build if self._last_full_build > 0 else time.time()
        if immediate_hot:
            # Rebuild hot months right away so stale oper_id values are refreshed
            self._build(months=_hot_months())
        while True:
            time.sleep(HOT_REBUILD_INTERVAL)
            if time.time() - last_full >= FULL_REBUILD_INTERVAL:
                self._build(months=None)
                last_full = time.time()
            else:
                self._build(months=_hot_months())

    def search(self, sn: str, from_month: Optional[str] = None, to_month: Optional[str] = None) -> List[Dict]:
        self._ready.wait()
        pattern = re.compile(r"(?<![A-Za-z0-9])" + re.escape(sn) + r"(?![A-Za-z0-9])")
        with self._lock:
            snapshot = dict(self._data)

        results = []
        for key, file_map in snapshot.items():
            machine, month = key.split("/", 1)
            if from_month and month < from_month:
                continue
            if to_month and month > to_month:
                continue
            for fname, oper_id in file_map.items():
                if pattern.search(fname):
                    full_path = Path(self.BASE_PATH) / machine / month / fname
                    try:
                        mtime = full_path.stat().st_mtime
                    except OSError:
                        mtime = 0.0
                    # Lazy oper_id lookup for stale index entries (None = pre-oper_id build)
                    if oper_id is None:
                        oper_id = _parse_oper_id(full_path)
                        with self._lock:
                            if key in self._data and fname in self._data[key]:
                                self._data[key][fname] = oper_id
                    dt_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M") if mtime else ""
                    results.append({
                        "path": str(full_path),
                        "name": fname,
                        "date": mtime,
                        "tags": ["ICT", machine],
                        "description": f"{machine} / {month}",
                        "datetime": dt_str,
                        "oper_id": oper_id,
                    })

        results.sort(key=lambda x: x["date"])
        return results

    def search_by_pn(self, pn: str, from_month: Optional[str] = None, to_month: Optional[str] = None) -> List[Dict]:
        self._ready.wait()
        with self._lock:
            rel_paths = list(self._pn_index.get(pn, []))

        results = []
        for rel_path in rel_paths:
            parts = rel_path.split("/", 2)
            if len(parts) != 3:
                continue
            machine, month, fname = parts
            if from_month and month < from_month:
                continue
            if to_month and month > to_month:
                continue
            full_path = Path(self.BASE_PATH) / machine / month / fname
            try:
                mtime = full_path.stat().st_mtime
            except OSError:
                mtime = 0.0
            dt_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M") if mtime else ""
            oper_id = _parse_oper_id(full_path)
            results.append({
                "path": str(full_path),
                "name": fname,
                "date": mtime,
                "tags": ["ICT", machine],
                "description": f"{machine} / {month}",
                "datetime": dt_str,
                "oper_id": oper_id,
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
