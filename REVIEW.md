# Review: 2026-09-28

## Why the deployed interface is old

The supplied `F:\programms\logs_reader-main.zip` contains a GUI identical to
local Git commit `2fed1781da3aae679c0da8bef881dcc8d3a47419`. It has no
`Radiobutton` controls. Archive timestamps are May 2, 2026. The local checkout
started this review at `985d159` (June 18, 2026) and includes the search-type
controls, LED viewer, operator configuration and Linux build support.

The reported missing controls are consistent with launching that older version.
Install the new bundle in a separate folder and update any existing desktop
shortcut to its executable. The live GitHub branch was not inspected; this
comparison is specifically against the supplied ZIP.

## Fixes included

- Product Number mode now calls the PN index rather than matching SN filenames.
- Search failure callbacks retain the error after the worker's exception scope
  ends, allowing the UI to show the error and re-enable search.
- Quoted commas in ICT CSV fields no longer shift PN/operator columns.
- A fresh index starts a full historical scan in the background immediately.
- Hot refreshes retain the full-build timestamp, and cache saves use atomic
  replacement instead of truncating the active file.
- LED galleries use isolated temporary directories, reject archive traversal
  and links, and escape filenames when writing JavaScript.
- Startup no longer attempts sudo RPM/DNF installation or requires screen,
  which the current log viewer does not use.
- Linux packaging runs tests, includes Python/Tk and LED assets, and produces
  a complete directory bundle without deleting the entire build/dist folders.

## Follow-up improvements

- Show a clear warning when production log mounts are unavailable; empty
  results currently do not distinguish a missing share from no matching logs.
- Validate date input strictly, including reversed days within the same month.
- Add cancellation and a common error handler for every search mode; LED
  worker failures and closing the window during callbacks need more coverage.
- Validate all cached JSON fields and retain the previous index on transient
  network scan failures. Valid JSON with an unexpected schema is not fully handled.
- Clean up old LED gallery temporary directories on a later launch, after the
  browser no longer needs them.

## Verification scope

All 82 tests pass on Windows Python 3.14 and EL8 Python 3.11. Regression tests cover PN routing, deferred failures, quoted CSV fields,
historical indexing, full-build metadata, and LED archive handling. The Linux
bundle was built in an EL8 x86-64 container. A virtual-display smoke test verified
all three source GUI modes render and the compiled application starts without
errors. The reproducible check is `packaging/smoke_gui.py`. Production QMS3, mounted shares,
LibreOffice integration and the actual RHEL workstation require an on-site
smoke test. See `packaging/RHEL8.md` for build and launch instructions.
