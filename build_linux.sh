#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
if [[ "$(uname -s)" != Linux ]]; then
    echo 'Build on EL8 Linux or use packaging/Dockerfile.rhel8.' >&2
    exit 1
fi
PYTHON="${PYTHON:-python3.11}"
"$PYTHON" -c 'import tkinter, PyInstaller'
"$PYTHON" -m unittest discover -s tests
"$PYTHON" -m PyInstaller --noconfirm --clean --onedir \
    --distpath dist/rhel8 --workpath build/rhel8 --specpath build \
    --add-data "$(pwd)/leds/html:leds/html" --name log_reader gui.py
cp runners.txt dist/rhel8/log_reader/runners.txt
cp packaging/RHEL8.md dist/rhel8/log_reader/README.txt
tar -C dist/rhel8 -czf "dist/log_reader-rhel8-$(uname -m).tar.gz" log_reader
echo "Created dist/log_reader-rhel8-$(uname -m).tar.gz"
