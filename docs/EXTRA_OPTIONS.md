# Extra Options compatibility

Use [Forza Horizon 2 Extra Options by RokkuDayo](https://github.com/RokkuDayo/ForzaHorizon2_ExtraOptions) alongside the FPS unlocker. The adapter reviewed here is **0.2.34**, with the investigated Azimuth 0.9.7 layout and FH2 1.0.0.64.

## Install

1. Close Azimuth and back up any existing `data/bin/azimuth-tls.dll` and saves before installing Extra Options.
2. Download Extra Options from its own repository. Extract the three files inside its **Azimuth** folder to your existing `Azimuth/data/bin`, following its installation instructions.
3. Open **FH2-FPS-Unlocker.exe**, select that installation's **azimuth.exe**, and choose FPS in the original UI.
4. Configure graphics and features in `data/bin/FH2_ExtraOptions.ini`. The unlocker does not change this file or replace the installed DLL.

Keep the process named **azimuth.exe**. Extra Options' Azimuth adapter checks that exact basename. Renamed launchers such as `azimuth_120fps.exe` are rejected by the reviewed adapter.

## Check startup

After entering the game, run **Check Extra Options.cmd** from the unlocker package. It reports the installed adapter and whether a new startup log reports `OK`, `DISABLED` or `REFUSED`. An old log is not used as proof that the current startup succeeded. A JSON report is saved in the profile directory.

Extra Options writes its log to `data/bin/FH2_ExtraOptions.log`. Successful initialization is not a guarantee that every feature works or that a selected FPS limit is sustainable.

The Extra Options INI must be UTF-8/ASCII for version 0.2.34. This is separate from **Azimuth's** `data/azimuth.ini`, which the unlocker accepts in UTF-8 or BOM-marked UTF-16/32. Neither file is automatically converted.

## How the two mods coexist

The FPS unlocker patches the native selector, settings parser and pacing calculation before resuming Azimuth. Extra Options is loaded later by Azimuth through its normal TLS helper path. Its livery and save adapter code ranges do not overlap the FPS patches. The launcher restores the normal Windows DLL search directory while creating Azimuth so its bundled Python DLL directory is not inherited.

Extra Options can increase graphics workload. Keep its settings identical when comparing performance. The unlocker does not disable features to inflate FPS or override Extra Options' settings.

## Validation

I tested the combination at a selected 90 FPS cap. A fresh Extra Options log reported successful initialization, and I used Get In Car to change cars in game. Read-only memory checks confirmed the FPS selector/parser/pacing patches, the real-time timestep branch, and the 4K livery patch bytes remained active together. The on-disk Azimuth and game executable hashes stayed unchanged.

This confirms the tested startup and features; it is not a sustained-framerate benchmark or validation of every Extra Options feature, build or FPS limit.

Source reviewed: [commit d6828e5](https://github.com/RokkuDayo/ForzaHorizon2_ExtraOptions/tree/d6828e5a8580e7dabeea7cbeec50524dc7ec2e97). The independently downloaded 0.2.34 Azimuth adapter has SHA-256 `3ef8b360965146a28fbe8957a35bbef937533e73bcb9b1b42ce6872189919698`.

Extra Options is installed separately and remains under its own license. Its DLL, settings and source are not bundled with this mod.
