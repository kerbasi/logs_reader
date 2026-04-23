# Logs Reader

A lightweight, zero-dependency Python tool for searching and reading log files in complex directory structures. Designed to replace the legacy `find_log.py` shell script with a robust, cross-platform CLI.

## Features

-   **Smart Search**: Automatically traverses directory structures (`PN/YYYYMM/` or `PN/YYYY/MM/`) to find logs.
-   **Serial Number Resolution**: Resolves arbitrary SNs to Product Numbers (PN) using internal QMS3 service lookup (via `curl`).
-   **No Dependencies**: Built using **only** the Python Standard Library. No `pip install` required.
-   **Interactive CLI**: Colored output and easy-to-use menu for selecting and viewing logs.
-   **Cross-Platform**: Designed for Linux file systems but runs on Windows/Mac for testing.

## Installation

Simply clone the repository or copy the folder to your target machine:

```bash
git clone <your-repo-url> logs_reader
cd logs_reader
```

Requires **Python 3.6+**.

## Usage

### Basic Search
Search for logs by Serial Number. The tool will attempt to resolve the Product Number automatically via the QMS3 service.

```bash
python3 main.py <SN>
```

### Manual Product Number
Skip the QMS3 lookup and search directly by Product Number:

```bash
python3 main.py <SN> --pn <PN>
```

### Additional Search Paths
Append extra directories to scan (the default paths are always included):

```bash
python3 main.py <SN> --path /tmp/custom/logs
```

### Verbose Output
Show search path details and match counts:

```bash
python3 main.py <SN> --verbose
```

## Directory Structure

The tool expects logs to be organized as:

```
<root>/<PN>/<YYYYMM>/          ← e.g. /usr/flexfs/lion_cub/log/ft/S12345/202401/
    <PN>.mlnx                  ← index file; each line records one test run
    DEBUG/
        <logfile>_<SN>.gz      ← actual log files, named with the SN
```

Both `YYYYMM` (flat) and `YYYY/MM` (nested) layouts are supported.

The `.mlnx` index file uses the format:
```
YYYY|MM|DD|HH.MM.SS:SN[<sn>]:ULT[<ult>]:<duration>:<status>:<code>:<detail>
```

This is parsed and displayed as the `Info:` line next to each result.

## Configuration

Default search paths are defined in `main.py`:

| Path | Category |
|------|----------|
| `/usr/flexfs/lion_cub/log/ft` | Functional test logs |
| `/usr/flexfs/lion_cub/log` | General logs |
| `/usr/flexfs/lion_cub/log/customization` | Customization logs |
| `/usr/flexfs/lion_cub/log/dbg/ft` | Debug functional test logs |
| `/usr/flexfs/lion_cub/log/dbg` | Debug logs |
| `/usr/flexfs/lion_cub/log/dbg/customization` | Debug customization logs |

The QMS3 service URL is read from `/usr/flexfs/qms3/site.ws`. If that file is absent (e.g. on a dev machine), PN resolution is skipped and the tool prompts for manual input.

## Development

Run the full test suite:

```bash
python3 -m unittest discover tests/
```

## Legacy Script

`find_log.py` in the repository root is the original shell-style script this tool replaces. It is kept for reference only.

## License
Internal tool.
