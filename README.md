<div align="center">

# FH2 FPS Unlocker

**Take Forza Horizon 2 beyond 60 FPS on Azimuth.**

Choose your frame-rate limit from the original Azimuth interface.

**30 · 60 · 90 · 120 · 144 · 165 · 180 · 200 FPS**

Version 1.1.0 · Windows x64 · MIT-licensed mod source

[Getting started](#getting-started) · [Test results](#test-results) · [Troubleshooting](#troubleshooting) · [Technical notes](TECHNICAL.md)

**[Download v1.1.0](https://github.com/gabrielfriasw/fh2_frame_unlocker/releases/tag/v1.1.0)** — choose `fh2-fps-unlocker-v1.1.0-windows.zip` under Assets. No Python installation needed.

</div>

---

![Forza Horizon 2 running in Azimuth with the performance overlay showing 144 FPS](docs/images/fh2-gameplay-144-fps.png)

*A screenshot from my game. The overlay reads 144 FPS at this moment; this is not a sustained-performance benchmark.*

## What it does

Adds 30, 60, 90, 120, 144, 165, 180 and 200 FPS to Azimuth's original **Frame rate** selector. The launcher uses your selected installation directly and applies executable patches only in memory. No frame generation is used.

## Getting started

1. Download **fh2-fps-unlocker-v1.1.0-windows.zip** from the release and extract it.
2. Save and close Azimuth, then open **FH2-FPS-Unlocker.exe**.
3. On first launch, select your existing **azimuth.exe**. Its game folder must already be configured in Azimuth.
4. Choose **Frame rate** in the original interface and start the game. Begin testing at 90 FPS.

Next time, open the same unlocker executable. It remembers the installation. No Python installation or additional installation folder is required for the Windows package. Your existing saves remain in use, and progress is saved in the same installation.

Above 60 FPS, real-time pacing is enforced. Other graphics settings are retained; VSync or external limits can restrict achieved FPS.

**Compatibility:** Windows 11 x64, the Azimuth 0.9.7 patch layout and FH2 Xbox One 1.0.0.64. The five regions modified by this tool must match their expected instructions; see [TECHNICAL.md](TECHNICAL.md). Whole-file hashes are diagnostic only. Modifications outside these regions are accepted, but compatibility with every modification is not guaranteed. Extra Options 0.2.34 was tested alongside the unlocker; see [installation and startup checks](docs/EXTRA_OPTIONS.md). Other third-party modifications remain unverified.

To select another installation, run:

```powershell
.\FH2-FPS-Unlocker.exe --setup
```

Source users can run `python unlock.py` with 64-bit Python and Tkinter. Development used Python 3.14. `Run.cmd` uses the Windows Python launcher.

## Test results

I captured these measurements on **my PC with earlier fixed-limit prototypes**, using 90-second capture windows. They are not benchmarks of the newly integrated selector.

| Selected limit | Average presentations/s | Observed behavior |
|---|---:|---|
| 60 FPS | 59.96 | Driving felt normal to me |
| 90 FPS | 89.47 | Driving felt stable to me |
| 180 FPS | 110.69 | A later crash reported `D3D12 DEVICE_HUNG` (`0x887a0006`) |
| 200 FPS | 137.48 | No crash during the capture at 1080p/low; 33 dropped presentations |

**A 200 FPS setting does not mean the game reaches 200 FPS.** Presentation measurements also do not independently prove that every frame contains a unique game render.

The cause of the 180 FPS crash has not been established. Neither 180 nor 200 FPS is considered validated stable. Dedicated driving tests at 120, 144 and 165 FPS remain outstanding, and physics, AI, animations and events have not been exhaustively validated at higher rates.

The current suite has 25 automated test methods covering patch instructions, INI encodings, save backups, region conflicts and Extra Options diagnostics. I also tested Extra Options 0.2.34 with a selected 90 FPS cap, including Get In Car and live verification of 4K livery patches. These checks do not validate every feature or higher-rate performance.

## Saves and reverting

Before each launch, saves are backed up under `%LOCALAPPDATA%/FH2FPSUnlocker/profiles/<profile>/save-backups`. This folder also contains a configuration snapshot and session journals. Backups can accumulate over time.

The mod uses the installation you selected. To restore a save, close Azimuth, preserve its current `data/saves` directory, and restore the chosen backup's `saves` directory there.

To stop using the mod, close it and start Azimuth normally. Executable patches disappear when the process exits. FPS choices saved in Azimuth's configuration remain; select 30 or 60 in the normal interface. Setup does not rewrite the installation's configuration or executable files.

Configuration files in UTF-8 and BOM-marked UTF-16/UTF-32 are read automatically; no manual conversion is needed.

## Troubleshooting

| Problem | What to check |
|---|---|
| Patch conflict | The error identifies the affected region and RVA. Another mod overlaps our patch, or the executable layout differs. |
| Game folder not found | Configure the game folder in Azimuth, close it, then retry setup. |
| Only 30/60 appear | Start through FH2-FPS-Unlocker.exe. |
| FPS below the selected limit | Check VSync, external caps and hardware load. The limit is a ceiling. |
| Azimuth already running | Save and close it before launching the mod. |
| Crash or unusual behavior | Return to a lower cap and record the conditions. |

## Helping test

Community reports are useful when the conditions can be reproduced:

1. Establish a 60 FPS baseline, then repeat the same route at 90 FPS.
2. Keep weather, camera, resolution and graphics settings consistent.
3. Capture frametimes and note steering, collisions, race timers, animations and crashes.
4. Test 120 FPS before proceeding to higher limits.
5. Close and reopen through the unlocker to check that the selected limit persists.

For a bug report, include:

```text
Azimuth / game build:
CPU / GPU / RAM:
Windows / graphics driver:
Selected FPS / observed FPS:
Resolution / graphics / VSync:
Route or event:
Steps to reproduce:
Expected / actual behavior:
Does it also happen at 60 FPS?
```

Review diagnostics before sharing them: journals can contain local paths. Do not attach saves, memory dumps, game assets or proprietary executables.

## Development

The launcher uses Python's standard library. Instruction-emulation tests additionally use Unicorn:

```powershell
python -m pip install -r requirements-dev.txt
python -m unittest discover -s tests -v
```

| File | Purpose |
|---|---|
| `unlock.py` | First-run folder selection and launch entry point |
| `engine.py` | Compatibility checks, save backups and process patching |
| `native_patches.py` | Extended selection in Azimuth's original UI |
| `parser_patches.py` | Saved-rate parsing and dynamic frame pacing |
| `tests/` | Instruction-emulation tests |

Run `Build.cmd` with 64-bit Python installed to build `dist/FH2-FPS-Unlocker.exe`. It uses the pinned PyInstaller dependency and its [one-file, windowed mode](https://www.pyinstaller.org/en/stable/usage.html). Bundled Python and third-party runtime components retain their own licenses.

Read [TECHNICAL.md](TECHNICAL.md) for addresses, evidence and validation limits. Contributions should retain region checks, reversible patching and clear test evidence.

## Credits and license

Thanks to the Azimuth developers and the community testing Forza Horizon 2 on PC.

This is an independent, unofficial project, not affiliated with or endorsed by Microsoft, Xbox, the Forza developers or the Azimuth developers.

The [MIT license](LICENSE) covers this project's own mod code. Azimuth and Forza Horizon 2 remain the property of their respective owners. Bring your own installation; this repository does not distribute their executables or assets.
