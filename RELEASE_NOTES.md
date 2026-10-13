# v0.1.0-preview.2 — Direct launch

Download **fh2-fps-unlocker-windows-preview.zip**, extract it and open
**FH2-FPS-Unlocker.exe**. Select your existing azimuth.exe once, then use the
original Frame rate selector. The launcher remembers the installation.

- Uses the selected installation and its saves directly.
- No Python installation required for the Windows package.
- No additional Azimuth installation is created.
- Save backups before launch; executable patches remain memory-only.
- Limits: 30, 60, 90, 120, 144, 165, 180 and 200 FPS.
- Exact supported Azimuth/game hashes are required.

Existing configuration and save progress remain in the selected installation.
Users upgrading from the previous preview must select Azimuth again. No previous
profiles or saves are deleted or migrated automatically.

Experimental pre-release. Start at 90 FPS and validate 120 before higher rates.
The 180-cap prototype previously crashed; higher-rate stability and full
simulation correctness remain unverified. See README.md for measured results.
The new direct-launch flow still needs end-to-end gameplay validation.
