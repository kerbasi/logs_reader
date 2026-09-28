"""Run in the EL8 build image: python3.11 packaging/smoke_gui.py."""
import os
from pathlib import Path
import subprocess
import sys
import time
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
display = subprocess.Popen(['Xvfb', ':99', '-screen', '0', '1280x800x24'])
os.environ['DISPLAY'] = ':99'
try:
    for attempt in range(50):
        if Path('/tmp/.X11-unix/X99').exists():
            break
        time.sleep(0.1)
    import tkinter as tk
    from gui import LogReaderApp

    root = tk.Tk()
    with patch.object(LogReaderApp, '_init_ict_status'), patch.object(LogReaderApp, '_check_deps'):
        app = LogReaderApp(root)
        root.update()
        def descendants(widget):
            for child in widget.winfo_children():
                yield child
                yield from descendants(child)
        radios = [w for w in descendants(root) if w.winfo_class() == 'TRadiobutton']
        values = {str(w.cget('value')) for w in radios}
        assert {'sn', 'pn', 'led'} <= values, values
        for mode in ('sn', 'pn', 'led'):
            app._mode.set(mode)
            app._on_mode_change()
            root.update()
        root.destroy()
    binary = Path('/app/dist/rhel8/log_reader/log_reader')
    proc = subprocess.Popen([str(binary)], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        time.sleep(3)
        assert proc.poll() is None, 'Packaged GUI exited during startup'
    finally:
        if proc.poll() is None:
            proc.terminate()
        out, err = proc.communicate(timeout=10)
    assert not err, err.decode(errors='replace')
    print('PASS: all three GUI modes render; compiled application starts without errors.')
finally:
    display.terminate()
    display.wait(timeout=10)
