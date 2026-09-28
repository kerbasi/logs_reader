# Logs Reader for Red Hat Enterprise Linux 8

Extract the entire archive and keep its files together. Python and Tk are
included; installing Python on the target workstation is not required.

```bash
tar -xzf log_reader-rhel8-x86_64.tar.gz
./log_reader/log_reader
```

Run as the normal desktop user, with access to the production `/usr/flexfs`
mounts. A graphical session is required. Edit `runners.txt` beside the executable
to change operator names. The cache is saved next to the application when
writable, otherwise under `~/.cache/logs_reader`.

System tools: curl for QMS3 lookup, less and a terminal emulator for text logs,
LibreOffice for CSV files (optional), and a browser for LED galleries. Ask your
administrator to install missing tools. Ordinary use does not need admin access.

## Build on RHEL 8.8 or later

```bash
sudo dnf install python3.11 python3.11-pip python3.11-tkinter binutils tar gzip
python3.11 -m venv .venv-build
.venv-build/bin/python -m pip install pyinstaller==6.22.3
PYTHON=.venv-build/bin/python bash build_linux.sh
```

## Build with Docker Desktop using Linux containers

From the project directory (create a local `dist` folder first):

```text
docker build --platform linux/amd64 -f packaging/Dockerfile.rhel8 -t logs-reader-rhel8 .
docker create --name logs-reader-export logs-reader-rhel8
docker cp logs-reader-export:/app/dist/log_reader-rhel8-x86_64.tar.gz dist/
docker rm logs-reader-export
```

Rocky Linux 8 provides the EL8 build environment. Test the result on the actual
RHEL workstation: launch it, check all three search modes, open text logs, CSVs
and LED galleries, and restart to verify cache loading. Production mounts and
QMS3 access cannot be verified in the build container.

The directory bundle avoids extracting executable libraries under `/tmp` at
startup. Distribute the whole archive. Build on EL8 and the target CPU
architecture: PyInstaller does not cross-compile or bundle glibc.

References:
- https://pyinstaller.org/en/stable/usage.html
- https://docs.redhat.com/en/documentation/red_hat_enterprise_linux/8/html/configuring_basic_system_settings/installing-and-using-dynamic-programming-languages_configuring-basic-system-settings
