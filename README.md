# Logs Reader

A lightweight, zero-dependency Python tool for searching and viewing test log files. Supports both a GUI and an interactive CLI. Replaces the legacy `find_log.py` shell script.

## Features

- **GUI** (`gui.py`) — tkinter interface with color-coded results, clickable rows, threaded search
- **CLI** (`main.py`) — colored interactive terminal interface
- **FT / Customization logs** — traverses `PN/YYYYMM/` or `PN/YYYY/MM/` structures, reads `.mlnx` index files
- **ICT logs** — scans `TRI401`–`TRI421` machine folders, opens results in LibreOffice Calc
- **SN → PN resolution** — automatic lookup via internal QMS3 service; falls back to manual entry
- **No dependencies** — Python standard library only

## Requirements

- Python 3.6+
- LibreOffice (for opening ICT `.csv` files; falls back to terminal viewer if absent)

## Installation

```bash
git clone <repo-url> logs_reader
cd logs_reader
```

## Usage

### GUI

```bash
python3 gui.py
```

Enter a Serial Number, optionally a Product Number, and click **Search**. Click any result to open it. ICT CSV results open in LibreOffice Calc; all others open in a terminal viewer.

### CLI

```bash
# Auto-resolve PN via QMS3, then search
python3 main.py <SN>

# Skip QMS3 lookup
python3 main.py <SN> --pn <PN>

# Append extra search directories (defaults always included)
python3 main.py <SN> --path /mnt/custom/logs

# Show path and match-count details
python3 main.py <SN> --verbose
```

## Log Types

### FT / Customization logs

```
<root>/<PN>/<YYYYMM>/
    <PN>.mlnx          ← index file, one line per test run
    DEBUG/
        *<SN>*         ← actual log files
```

Both `YYYYMM` (flat) and `YYYY/MM` (nested) layouts are supported.

Default search roots:

| Path | Category |
|------|----------|
| `/usr/flexfs/lion_cub/log/ft` | Functional test |
| `/usr/flexfs/lion_cub/log` | General |
| `/usr/flexfs/lion_cub/log/customization` | Customization |
| `/usr/flexfs/lion_cub/log/dbg/ft` | Debug functional test |
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

`MACHINE` is `TRI401` through `TRI421`. No PN is required — search is by SN only. Matching files open directly in LibreOffice Calc via:

```bash
libreoffice --calc --infilter="Text CSV (StarCalc):44,34,0,1,1" <file>
```

## Configuration

The QMS3 service URL is read from `/usr/flexfs/qms3/site.ws`. If absent (e.g. on a dev machine), PN resolution is skipped and the tool prompts for manual input.

## Tests

```bash
python3 -m unittest discover tests/
```

## Legacy

`find_log.py` is the original shell-style script this tool replaces. Kept for reference.
