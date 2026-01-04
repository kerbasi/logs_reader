# Logs Reader

A lightweight, zero-dependency Python tool for searching and reading log files in complex directory structures. Designed to replace legacy shell scripts with a robust, cross-platform CLI.

## Features

-   **Smart Search**: Automatically traverses directory structures (`PN/YYYY/MM/...`) to find logs.
-   **Serial Number Resolution**: Resolves arbitrary SNs to Product Numbers (PN) using internal service lookup (via `curl`).
-   **No Dependencies**: Built using **only** the Python Standard Library. No `pip install` required.
-   **Interactive CLI**: Colored output and easy-to-use menu for selecting and viewing logs.
-   **Cross-Platform**: Designed for Linux file systems but runs on Windows/Mac for testing.

## Installation

Simply clone the repository or copy the folder to your target machine:

```bash
git clone <your-repo-url> logs_reader
cd logs_reader
```

Ensure you have **Python 3.6+** installed.

## Usage

### Basic Search
Search for logs by Serial Number. The tool will attempt to resolve the Product Number automatically.

```bash
python3 main.py <SN>
```

### Manual Product Number
If the automatic resolution fails or you want to search a specific Product Number:

```bash
python3 main.py <SN> --pn <PN>
```

### Custom Search Paths
Add additional directories to scan:

```bash
python3 main.py <SN> --path /tmp/custom/logs
```

## Configuration
Default search paths are defined in `main.py`:
- `/usr/flexfs/lion_cub/log/ft`
- `/usr/flexfs/lion_cub/log`
- `/usr/flexfs/lion_cub/log/customization`
- `/usr/flexfs/lion_cub/dbg/log/ft` (and others)

## Development

Run the test suite to verify logic (works on Windows/Linux):

```bash
python3 tests/test_core.py
```

## License
Internal tool.
