import re
import tarfile
import tempfile
import webbrowser
from pathlib import Path
from typing import Optional

_LED_HTML_DIR = Path(__file__).parent.parent / "leds" / "html"
_ARCHIVE_RE = re.compile(r'/usr/log\S+')


def find_led_archive(log_path: str) -> Optional[str]:
    """Scan a log/data file for a LED image archive path (/usr/log...).

    flex* files embed the path on a HD_CAM_LOG line; regular log files on a
    Destination line.  Returns the first match or None.
    """
    try:
        with open(log_path, 'r', errors='ignore') as f:
            for line in f:
                if 'HD_CAM_LOG' in line or 'Destination' in line:
                    m = _ARCHIVE_RE.search(line)
                    if m:
                        return m.group(0)
    except OSError:
        pass
    return None


def build_led_html(archive_path: str) -> Optional[str]:
    """Extract a LED image archive (.dat.gz) and build an HTML gallery.

    Returns the path to the generated led.html, or None on failure.
    """
    archive = Path(archive_path)
    if not archive.exists():
        return None

    basename = archive.name
    name_no_gz = basename[:-3] if basename.endswith('.gz') else basename
    out_dir = Path(tempfile.gettempdir()) / name_no_gz
    out_dir.mkdir(exist_ok=True)

    try:
        with tarfile.open(str(archive), 'r:gz') as tf:
            tf.extractall(str(out_dir))
    except Exception:
        return None

    jpgs = sorted(f.name for f in out_dir.iterdir() if f.suffix.lower() == '.jpg')

    try:
        head = (_LED_HTML_DIR / 'led.html.head').read_text(encoding='utf-8')
        end  = (_LED_HTML_DIR / 'led.html.end').read_text(encoding='utf-8')
    except OSError:
        return None

    img_list = ','.join(f'"{j}"' for j in jpgs)
    html = head + img_list + f"    ];\ndocument.title = '{basename}';\n" + end

    html_file = out_dir / 'led.html'
    html_file.write_text(html, encoding='utf-8')
    return str(html_file)


def open_led_viewer(archive_path: str) -> bool:
    """Build LED gallery HTML and open it in the default browser.

    Returns True on success, False if the archive is missing or extraction fails.
    """
    html_path = build_led_html(archive_path)
    if not html_path:
        return False
    webbrowser.open(Path(html_path).as_uri())
    return True
