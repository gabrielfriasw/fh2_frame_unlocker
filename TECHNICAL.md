# Technical evidence â€” native selector preview

## Supported artifacts

Windows AMD64; Azimuth 0.9.7 and FH2 1.0.0.64. Compatibility is checked by SHA-256, not filenames alone.

* Azimuth: `5d3ce30b440dab2604fe42ff7cd129394f0b98418e22b2a44270f548199bc6a9`
* Game executable: `3ec04c6163fb5614e3d351ba0570d39b846041a257715d6340eceb03ccb7f0a3`

Addresses below are wrapper RVAs unless stated otherwise. Static preferred image base is `0x140000000`; runtime addresses use the actual ASLR base.

## Findings and implementation

| Location | Evidence / use |
|---|---|
| `0x8b40` | Native settings window construction; Frame rate is row 5 |
| `0xc150` | Label formatter reads settings+8 and formats a generic integer followed by fps |
| `0xcf90` | Native input callback; negative direction selects previous, nonnegative selects next |
| `0xd144`, 33 bytes | Original 30/60 selection replaced with a guarded jump to the extended rate cycle |
| `0xd165`, 24 bytes | Pacing selection guarded so rates above 60 retain real-time pacing |
| `0xd23c` | Original callback persistence continuation, with row index in EDI |
| `0x5e650` | Native persistence routine; case 5 writes integer frame_rate, case 6 writes pacing |
| `0x5d810` | Settings parser originally accepts only 30/60 |
| `0x5dd80`, 15 bytes | Parser hook validates a 2â€“3 digit whitelisted FPS value; resumes at 0x5de4c |
| `0x5df95`, 14 bytes | Parser hook enforces real-time above 60 after pacing parsing, preserving cleanup paths |
| `0x35e90` | Presentation/pacing routine containing the original limiter |
| `0x3613d`, 70 bytes | Replaced period calculation reads the selected FPS global and calculates QPF/FPS |
| `0x32870` | Frequency getter used by pacing |
| `0x2beec4` | Selected FPS global; setter at 0x34c20 |

The UI layout and label formatter are unchanged. Extra choices use the original widget and persistence path. Selecting a high rate sets real-time pacing in memory. Because native persistence case 5 only writes FPS, the parser hook also enforces real-time at the next launch even if the INI pacing text was previously fixed.

The wrapper also controls the game's timestep path. Earlier analysis located wrapper patch application at RVA `0x913b0`, and a game branch at **game RVA `0xf587dd`** selecting the real-time path. This mod relies on Azimuth's existing real-time mode. It does not independently establish that every physics, animation, AI or event subsystem is framerate-independent.

## Safety and lifecycle

The launcher checks exact executable hashes and registers the selected installation without duplicating it. Each launch backs up the selected installation's saves, creates Azimuth suspended, checks every patch site's original bytes, allocates stubs, changes their memory to executable/read-only, patches with readback verification, flushes the instruction cache and resumes. Pre-resume failures terminate only the newly created child. Executables remain unchanged on disk.

## Validation status

Seven instruction-emulation test methods passed, including selection in both directions, all supported rates, invalid-value fallback, low/high-rate pacing behavior, parser storage forms, cleanup branches and ASLR relocation. These tests do not replace execution in the real application.

A live process accepted all guarded patches and resumed; the tester confirmed every extra choice appears in the existing UI. Integrated gameplay and close/reopen persistence validation remain pending. Earlier fixed-limit capture results are in README.md and must not be presented as full validation of this revision.

## Analysis provenance

REA/Ghidra evidence records retained privately, excluding proprietary decompilation from this release:

* Callback: `ev_8b7bc85b51a0cc1f7f117314fb1385ed2e3892af33336bb9c69931c8345237b8`
* Persistence: `ev_7b870a4b992b5758649bb758257016df4153237eeeb6b3084da39f3d569dee8d`
* Label drawing: `ev_71161c7a1d7c340b25ba05a720a01e2182e727e1625e1b25e01fd7428499f415`

Machine-code guards in the source are compatibility signatures for specific patch sites; no complete proprietary binary is distributed.
