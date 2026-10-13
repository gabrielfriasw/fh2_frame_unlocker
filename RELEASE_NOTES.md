# v1.0.1 — INI encoding fix

Fixed the startup error `utf-8 codec cannot decode byte 0xff in position 0` when reading a UTF-16 azimuth.ini.

The launcher now detects Unicode byte-order marks and reads UTF-8, UTF-16 LE/BE and UTF-32 LE/BE without rewriting the INI. No manual conversion is needed.

Download **fh2-fps-unlocker-v1.0.1-windows.zip**, extract it and use the new **FH2-FPS-Unlocker.exe**. Existing installation preferences and saves are retained.

Validation: 13 automated tests passed. The packaged executable passed its GUI/module self-test and profile verification with a UTF-16 INI; the INI stayed byte-for-byte unchanged.

This fix does not add support for other executable builds or establish DLC-launcher compatibility. Existing exact-build checks and high-FPS testing limitations still apply.
