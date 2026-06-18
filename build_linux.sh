#!/bin/bash
# Exit immediately if a command exits with a non-zero status
set -e

echo "=== Log Reader PyInstaller Builder for Linux ==="

# 1. Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 is not installed. Please install it first." >&2
    exit 1
fi

# 2. Check/Install PyInstaller
if ! python3 -c "import PyInstaller" &> /dev/null; then
    echo "PyInstaller not found. Attempting to install it via pip..."
    pip3 install --user pyinstaller || pip3 install pyinstaller || {
        echo "Error: Failed to install PyInstaller. Please install it manually." >&2
        exit 1
    }
fi

# Get pyinstaller path
PYINSTALLER_CMD="pyinstaller"
if ! command -v pyinstaller &> /dev/null; then
    # Fallback to python3 -m PyInstaller
    PYINSTALLER_CMD="python3 -m PyInstaller"
fi

echo "Using PyInstaller: $($PYINSTALLER_CMD --version)"

# 3. Clean previous builds
echo "Cleaning old build artifacts..."
rm -rf build dist log_reader.spec

# 4. Build Standalone Binary
# --onefile: bundle everything into a single binary
# --windowed: disable console window since this is a Tkinter GUI app
# --add-data "screen-...rpm:.": bundle the screen RPM at the root of the extraction dir
# --add-data "leds:leds": bundle the leds/ folder (specifically html gallery assets)
# --name log_reader: output binary name
echo "Compiling gui.py with PyInstaller..."
$PYINSTALLER_CMD --onefile --windowed \
    --add-data "screen-4.6.2-12.el8.x86_64.rpm:." \
    --add-data "leds:leds" \
    --name log_reader \
    gui.py

echo "=================================================="
echo "Build complete! Standalone executable is located at:"
echo "  dist/log_reader"
echo ""
echo "Note: The application will look for 'runners.txt' next to"
echo "the executable. A default 'runners.txt' template will be"
echo "created automatically on its first run if none is found."
echo "=================================================="
