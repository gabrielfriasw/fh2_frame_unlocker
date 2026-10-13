"""Read-only detection of the independently installed Extra Options adapter.

No third-party code or DLL is loaded by this module. Installation and runtime
log evidence are deliberately separate: an old OK log is not a current success.
"""
import hashlib
from pathlib import Path

UPSTREAM = "https://github.com/RokkuDayo/ForzaHorizon2_ExtraOptions"
KNOWN_ADAPTERS = {
    "3ef8b360965146a28fbe8957a35bbef937533e73bcb9b1b42ce6872189919698": "0.2.34",
}
VANILLA_ADAPTER_SHA = "798864645e9dfabce907d6964a6eac807d9747b634da1ced204591de28ae343b"


def fingerprint(path):
    path = Path(path)
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            digest.update(chunk)
    stat = path.stat()
    return {"sha256": digest.hexdigest(), "size": stat.st_size, "mtime_ns": stat.st_mtime_ns}


def inspect(runtime):
    directory = Path(runtime) / "data" / "bin"
    result = {"upstream": UPSTREAM, "state": "not_detected", "version": None,
              "files": {}, "warnings": [], "runtime_confirmed": False}
    try:
        for name in ("azimuth-tls.dll", "FH2_ExtraOptions.ini", "Gamerpic.png", "FH2_ExtraOptions.log"):
            result["files"][name] = fingerprint(directory / name)
        helper = result["files"]["azimuth-tls.dll"]
        if helper and helper["sha256"] in KNOWN_ADAPTERS:
            result.update(state="recognized_adapter", version=KNOWN_ADAPTERS[helper["sha256"]])
            if not result["files"]["FH2_ExtraOptions.ini"]:
                result["warnings"].append("Extra Options INI is missing; its built-in defaults may be used.")
        elif helper and helper["sha256"] != VANILLA_ADAPTER_SHA:
            result["state"] = "unrecognized_adapter"
            result["warnings"].append("TLS helper is not a recognized Extra Options release. Compatibility is unverified.")
        elif result["files"]["FH2_ExtraOptions.ini"]:
            result["state"] = "settings_without_adapter"
            result["warnings"].append("Extra Options settings exist but its adapter is not installed.")
        ini = directory / "FH2_ExtraOptions.ini"
        if ini.is_file():
            raw = ini.read_bytes()
            if b"\0" in raw:
                result["warnings"].append("Extra Options 0.2.34 requires its own INI to be UTF-8/ASCII, not UTF-16.")
    except OSError as exc:
        result.update(state="inspection_error", error=str(exc))
    return result


def observe_log(runtime, before):
    """Report startup-log changes, without treating stale output as active."""
    path = Path(runtime) / "data" / "bin" / "FH2_ExtraOptions.log"
    result = {"state": "not_observed", "runtime_confirmed": False,
              "scope": "Extra Options startup only; not gameplay or performance validation"}
    if not before:
        return result
    try:
        after = fingerprint(path)
        old = before.get("files", {}).get("FH2_ExtraOptions.log")
        if not after or after == old:
            return result
        helper = fingerprint(path.parent / "azimuth-tls.dll")
        if helper != before.get("files", {}).get("azimuth-tls.dll"):
            result["state"] = "adapter_changed"
            return result
        # The log is bounded and read as data, never as executable instructions.
        with path.open("rb") as stream:
            lines = stream.read(16384).decode("utf-8-sig", errors="replace").splitlines()
        if len(lines) < 2 or "Extra Options" not in lines[0] or "Azimuth TLS adapter" not in lines[0]:
            result["state"] = "unrecognized_log"
            return result
        result.update(header=lines[0], status=lines[1], log=after)
        if lines[1].startswith("OK:"):
            result["state"] = "startup_ok"
            # Only promote a reviewed adapter's new log to startup evidence.
            result["runtime_confirmed"] = before.get("state") == "recognized_adapter"
        elif lines[1].startswith("DISABLED:"):
            result["state"] = "disabled"
        elif lines[1].startswith("REFUSED:"):
            result["state"] = "refused"
        else:
            result["state"] = "unrecognized_status"
    except OSError as exc:
        result.update(state="inspection_error", error=str(exc))
    return result


def report_summary(report):
    installed = report["extra_options"]
    state = installed["state"]
    if state == "recognized_adapter":
        title = "Extra Options " + str(installed["version"]) + " detected."
    elif state == "settings_without_adapter":
        title = "Extra Options settings found, but its DLL is not installed."
    elif state == "not_detected":
        title = "Extra Options is not installed in this Azimuth folder."
    else:
        title = "Extra Options installation could not be verified."
    startup = report["startup"]
    messages = {"not_observed": "No new startup log yet. Start the game through the unlocker, then check again.",
                "startup_ok": "A new Extra Options log reports successful initialization.",
                "disabled": "Extra Options is disabled in its settings.",
                "refused": "Extra Options refused to initialize. See its message below.",
                "adapter_changed": "The installed DLL changed since launch. Restart the game before checking.",
                "unrecognized_log": "The startup log format is not recognized.",
                "unrecognized_status": "The startup result is not recognized.",
                "inspection_error": "The startup log could not be read."}
    lines = [title, messages.get(startup["state"], "Startup has not been verified.")]
    if startup.get("status"):
        lines.append(startup["status"])
    lines.extend(installed.get("warnings", []))
    lines.append("This checks startup only; gameplay and FPS still need testing.")
    return "\n\n".join(lines)
