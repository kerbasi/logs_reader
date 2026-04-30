# Logs Reader

A lightweight Python tool for searching and viewing test log files on the Lion Cub line. Supports a GUI and an interactive CLI. Replaces the legacy `find_log.py` shell script.

## Features

- **GUI** (`gui.py`) — tkinter interface with color-coded PASS/FAIL results, clickable rows, threaded search, operator name display
- **CLI** (`main.py`) — colored interactive terminal interface
- **FT / Customization logs** — traverses `PN/YYYYMM/` structures, reads `.mlnx` index files
- **ICT logs** — JSON index over `TRI401`–`TRI421` machine folders with background re-indexing; opens results in LibreOffice Calc
- **SN → PN resolution** — automatic lookup via QMS3 service; falls back to manual entry
- **Operator names** — maps OperID numbers to names via `_RUNNERS` dict in `gui.py`
- **No dependencies** — Python standard library only

## Requirements

- Python 3.6+
- LibreOffice (for opening ICT `.csv` files; falls back to terminal viewer if absent)

## Installation

```bash
git clone <repo-url> logs_reader
cd logs_reader
chmod +x gui.py   # enables double-click launch from Nautilus
```

## Usage

### GUI

```bash
python3 gui.py
# or double-click gui.py in Nautilus (after chmod +x)
```

Enter a Serial Number, optionally a Product Number, and click **Search** (or press Enter). Click any result row to open it. ICT CSV files open in LibreOffice Calc; all others open in a terminal viewer.

Results are color-coded: green = PASS, red = FAIL, blue = other FT logs, teal = ICT logs.

### CLI

```bash
python3 main.py <SN>               # auto-resolve PN via QMS3
python3 main.py <SN> --pn <PN>    # skip QMS3 lookup
python3 main.py <SN> --path /mnt/custom/logs   # extra search directory
python3 main.py <SN> --verbose     # show path and match-count details
```

## Log Types

### FT / Customization logs

```
<root>/<PN>/<YYYYMM>/
    <PN>.mlnx          ← index file, one entry per test run
    DEBUG/
        *<SN>*         ← actual log files
```

Both `YYYYMM` (flat) and `YYYY/MM` (nested) month layouts are supported.

Default search roots:

| Path | Category |
|------|----------|
| `/usr/flexfs/lion_cub/log/ft` | Functional test |
| `/usr/flexfs/lion_cub/log` | General |
| `/usr/flexfs/lion_cub/log/customization` | Customization |
| `/usr/flexfs/lion_cub/log/dbg/ft` | Debug FT |
| `/usr/flexfs/lion_cub/log/dbg` | Debug |
| `/usr/flexfs/lion_cub/log/dbg/customization` | Debug customization |

The `.mlnx` index line format:
```
YYYY|MM|DD|HH.MM.SS:SN[<sn>]:ULT[<ult>]:<duration>:<status>:<code>:<detail>
```

### ICT logs

```
/usr/flexfs/ict_tri_logs/<MACHINE>/<YYYYMM>/*_<SN>_*.csv
```

`MACHINE` is `TRI401` through `TRI421`. Search is by SN only (no PN required).

A JSON index is built in the background on first run and kept warm with incremental re-indexing (hot months every 30 s, full rebuild daily). Search is blocked until the index is ready.

Matching files open in LibreOffice Calc:

```bash
libreoffice --calc --norestore \
  --infilter="Text - txt - csv (StarCalc):44,34,76,1" <file>
```

## Configuration

### QMS3

The QMS3 service URL is read from `/usr/flexfs/qms3/site.ws`. If absent (e.g. on a dev machine), PN resolution is skipped and the tool prompts for manual input.

### Operator names

Edit `_RUNNERS` in `gui.py` to map OperID numbers to human-readable names:

```python
_RUNNERS: Dict[str, str] = {
    "12345": "John Doe",
    "67890": "Jane Smith",
}
```

When an OperID matches an entry, the name is shown in the result info line instead of the raw number.

## Tests

```bash
python3 -m unittest discover tests/
```

## Legacy

`find_log.py` is the original shell-style script this tool replaces. Kept for reference.
