# v1.1.0 — Compatibility update

## Changes

- Removed whole-file hash blocking. Modified executables are accepted when the five regions changed by the unlocker retain their expected instructions and layout.
- Kept exact checks on disk and again in the suspended process before applying patches. Overlapping changes now produce an error identifying the region and RVA.
- Added Extra Options 0.2.34 detection and **Check Extra Options.cmd**, which distinguishes installation from fresh startup-log evidence.
- Restored the normal Windows DLL search directory when launching Azimuth from the packaged executable.
- Retained UTF-8/UTF-16/UTF-32 configuration support, verified save backups, the native FPS selector and memory-only executable patches.

## Install or update

Download **fh2-fps-unlocker-v1.1.0-windows.zip**, extract it, then open **FH2-FPS-Unlocker.exe**. Select **azimuth.exe** if prompted, choose FPS in the original interface and play. Existing installation preferences and saves are retained. Python is not required.

Extra Options is installed separately. See **docs/EXTRA_OPTIONS.md** for installation and startup checks. Its DLL and settings are not bundled or overwritten.

## Validation

25 automated test methods passed. A modified PE with unchanged patch regions was accepted by the packaged executable; a one-byte overlapping FPS patch was rejected at the exact conflicting RVA. I tested Extra Options at a selected 90 FPS cap, used Get In Car, and verified the FPS and 4K livery patches were active together in memory.

Allowing changes elsewhere does not guarantee compatibility with every mod or executable build. Higher-FPS stability and complete simulation correctness remain incompletely validated.
