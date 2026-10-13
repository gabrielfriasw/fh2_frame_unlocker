"""Exact-build, process-only frame pacing patch. No game code is distributed."""
from __future__ import annotations
import ctypes
from ctypes import wintypes as W
from datetime import datetime, timezone
import hashlib, json, os, re, shutil, struct, subprocess, uuid
from pathlib import Path

WRAPPER_SHA = "5d3ce30b440dab2604fe42ff7cd129394f0b98418e22b2a44270f548199bc6a9"
GAME_SHA = "3ec04c6163fb5614e3d351ba0570d39b846041a257715d6340eceb03ccb7f0a3"
GAME_NAME = "forza_durango_release_final.exe"
RATES = (30, 60, 90, 120, 144, 165, 180, 200)
PATCH_RVA = 0x3613D
PATCH_END = 0x36183
FREQUENCY_GETTER_RVA = 0x32870
PATCH_SIZE = PATCH_END - PATCH_RVA
EXPECTED = bytes.fromhex("416bc71e33d2f7357b8d28008bd8e820c7ffff4c8bf841b801000000413bd8440f47c34c0fafc048b8898888888888888849f7e8498d1c1048c1fb05488bc348c1e83f4803d8")

def require(ok, message):
    if not ok:
        raise RuntimeError(message)


def sha256(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(4 * 1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)


def inside(path, root):
    return path.resolve().is_relative_to(root.resolve())


def files_in(root):
    require(root.is_dir(), f"Pasta ausente: {root}")
    result = []
    for path in root.rglob("*"):
        # Refuse symlinks and junctions; copy and hashing must stay in the tree.
        attributes = getattr(path.lstat(), "st_file_attributes", 0)
        require(not attributes & 0x400, f"Reparse point recusado: {path}")
        require(inside(path, root), f"Caminho fora da pasta: {path}")
        if path.is_file():
            result.append(path)
    return sorted(result)


def tree_hashes(root):
    return {str(p.relative_to(root)): sha256(p) for p in files_in(root)}


def pe_bytes_at_rva(path, rva, size):
    data = Path(path).read_bytes()
    require(data[:2] == b"MZ", "Assinatura DOS invÃ¡lida.")
    pe = struct.unpack_from("<I", data, 0x3C)[0]
    require(data[pe:pe + 4] == b"PE\0\0", "Assinatura PE invÃ¡lida.")
    machine, count = struct.unpack_from("<HH", data, pe + 4)
    optional_size = struct.unpack_from("<H", data, pe + 20)[0]
    require(machine == 0x8664 and struct.unpack_from("<H", data, pe + 24)[0] == 0x20B,
            "O patch exige PE32+ AMD64.")
    sections = pe + 24 + optional_size
    for i in range(count):
        entry = sections + i * 40
        _, virtual_address, raw_size, raw_offset = struct.unpack_from("<IIII", data, entry + 8)
        if virtual_address <= rva and rva + size <= virtual_address + raw_size:
            offset = raw_offset + rva - virtual_address
            require(offset + size <= len(data), "SeÃ§Ã£o truncada.")
            return data[offset:offset + size], offset
    raise RuntimeError("RVA nÃ£o coberto integralmente por uma seÃ§Ã£o com bytes em disco.")


def build_patch(fps):
    require(fps in RATES, "FPS nÃ£o suportado.")
    # CALL QPF getter; MOV R15,RAX; XOR EDX,EDX; MOV ECX,fps;
    # DIV RCX; MOV RBX,RAX. R15 retains QPF; RBX receives floor(QPF/fps).
    code = (b"\xE8" + struct.pack("<i", FREQUENCY_GETTER_RVA - (PATCH_RVA + 5))
            + b"\x49\x89\xC7\x31\xD2\xB9" + struct.pack("<I", fps)
            + b"\x48\xF7\xF1\x48\x89\xC3")
    require(len(code) <= PATCH_SIZE, "Patch excede o bloco autorizado.")
    return code.ljust(PATCH_SIZE, b"\x90")


def config_values(path):
    pairs = {}
    for line in path.read_text(encoding="utf-8-sig").splitlines():
        if line.strip().startswith(("#", ";", "[")) or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        require(key not in pairs, f"ConfiguraÃ§Ã£o duplicada: {key}")
        pairs[key] = value.strip()
    return pairs


def patch_suspended(runtime, journal, journal_path):
    import parser_patches, native_patches
    baseline = False
    expected, replacement = EXPECTED, parser_patches.dynamic_pacing()
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    ntdll = ctypes.WinDLL("ntdll")
    SIZE = ctypes.c_size_t
    PTR = ctypes.c_void_p

    class STARTUPINFO(ctypes.Structure):
        _fields_ = [("cb", W.DWORD), ("lpReserved", W.LPWSTR), ("lpDesktop", W.LPWSTR),
                    ("lpTitle", W.LPWSTR), ("dwX", W.DWORD), ("dwY", W.DWORD),
                    ("dwXSize", W.DWORD), ("dwYSize", W.DWORD), ("dwXCountChars", W.DWORD),
                    ("dwYCountChars", W.DWORD), ("dwFillAttribute", W.DWORD), ("dwFlags", W.DWORD),
                    ("wShowWindow", W.WORD), ("cbReserved2", W.WORD), ("lpReserved2", PTR),
                    ("hStdInput", W.HANDLE), ("hStdOutput", W.HANDLE), ("hStdError", W.HANDLE)]

    class PROCESS_INFORMATION(ctypes.Structure):
        _fields_ = [("hProcess", W.HANDLE), ("hThread", W.HANDLE), ("dwProcessId", W.DWORD), ("dwThreadId", W.DWORD)]

    class PROCESS_BASIC_INFORMATION(ctypes.Structure):
        _fields_ = [("ExitStatus", ctypes.c_long), ("PebBaseAddress", PTR), ("AffinityMask", SIZE),
                    ("BasePriority", ctypes.c_long), ("UniqueProcessId", SIZE), ("InheritedFromUniqueProcessId", SIZE)]

    def api(name, restype, argtypes):
        fn = getattr(kernel, name)
        fn.restype, fn.argtypes = restype, argtypes
        return fn

    create = api("CreateProcessW", W.BOOL, [W.LPCWSTR, W.LPWSTR, PTR, PTR, W.BOOL, W.DWORD, PTR,
                                           W.LPCWSTR, ctypes.POINTER(STARTUPINFO), ctypes.POINTER(PROCESS_INFORMATION)])
    read = api("ReadProcessMemory", W.BOOL, [W.HANDLE, PTR, PTR, SIZE, ctypes.POINTER(SIZE)])
    write = api("WriteProcessMemory", W.BOOL, [W.HANDLE, PTR, PTR, SIZE, ctypes.POINTER(SIZE)])
    protect = api("VirtualProtectEx", W.BOOL, [W.HANDLE, PTR, SIZE, W.DWORD, ctypes.POINTER(W.DWORD)])
    flush = api("FlushInstructionCache", W.BOOL, [W.HANDLE, PTR, SIZE])
    resume = api("ResumeThread", W.DWORD, [W.HANDLE])
    terminate = api("TerminateProcess", W.BOOL, [W.HANDLE, W.UINT])
    close = api("CloseHandle", W.BOOL, [W.HANDLE])
    query = ntdll.NtQueryInformationProcess
    query.restype, query.argtypes = ctypes.c_long, [W.HANDLE, W.ULONG, PTR, W.ULONG, ctypes.POINTER(W.ULONG)]

    def wincheck(result, operation):
        if not result:
            raise ctypes.WinError(ctypes.get_last_error(), operation)

    si, pi = STARTUPINFO(), PROCESS_INFORMATION()
    si.cb = ctypes.sizeof(si)
    resumed = False
    try:
        command = ctypes.create_unicode_buffer(subprocess.list2cmdline([str(runtime / "azimuth.exe")]))
        wincheck(create(str(runtime / "azimuth.exe"), command, None, None, False, 0x4, None,
                        str(runtime), ctypes.byref(si), ctypes.byref(pi)), "CreateProcessW suspended")
        journal.update(pid=pi.dwProcessId, status="suspended")

        def rpm(address, count):
            buffer, done = ctypes.create_string_buffer(count), SIZE()
            wincheck(read(pi.hProcess, address, buffer, count, ctypes.byref(done)), "ReadProcessMemory")
            require(done.value == count, "Leitura parcial de memÃ³ria.")
            return buffer.raw

        info, returned = PROCESS_BASIC_INFORMATION(), W.ULONG()
        status = query(pi.hProcess, 0, ctypes.byref(info), ctypes.sizeof(info), ctypes.byref(returned))
        require(status >= 0 and info.PebBaseAddress, f"NtQueryInformationProcess falhou: {status:#x}")
        image_base = struct.unpack("<Q", rpm(info.PebBaseAddress + 0x10, 8))[0]
        require(rpm(image_base, 2) == b"MZ", "Image base invÃ¡lida.")
        address = image_base + PATCH_RVA
        require(rpm(address, len(expected)) == expected, "Bytes na memÃ³ria diferentes do backup; patch recusado.")
        journal.update(image_base=hex(image_base), patch_va=hex(address), status="bytes_verified")
        write_json(journal_path, journal)
        # Allocate dedicated leaf stubs: no DLL injection, no persistent EXE changes.
        allocate = api("VirtualAllocEx", PTR, [W.HANDLE, PTR, SIZE, W.DWORD, W.DWORD])
        stub_base = allocate(pi.hProcess, None, 4096, 0x3000, 0x04)
        wincheck(stub_base, "Allocate native selector stubs")
        plan = native_patches.build_native_ui(image_base, stub_base)
        # plan: documented builder returns code and exact guarded sites.
        stub_code = plan["code"]
        ui_sites = [(s["rva"],s["original"],s["replacement"]) for s in plan["sites"]]
        parser_at, pacing_at = stub_base + 0x800, stub_base + 0xC00
        parser_code = parser_patches.parser_code(image_base)
        pacing_code = parser_patches.pacing_parser_code(image_base)
        require(len(stub_code) < 0x800 and len(parser_code) < 0x400 and len(pacing_code) < 0x400, "Stub layout overflow")
        sites = list(ui_sites) + [
            (parser_patches.PARSER_RVA, parser_patches.PARSER_EXPECTED, parser_patches.jump(parser_at, len(parser_patches.PARSER_EXPECTED))),
            (parser_patches.PACING_RVA, parser_patches.PACING_EXPECTED, parser_patches.jump(pacing_at, len(parser_patches.PACING_EXPECTED)))]
        for rva, before, after in sites:
            require(rpm(image_base+rva,len(before)) == before and len(before)==len(after), "Native UI instructions changed; refusing patch")
        for target, content in [(stub_base,stub_code),(parser_at,parser_code),(pacing_at,pacing_code)]:
            buffer, done = ctypes.create_string_buffer(content), SIZE()
            wincheck(write(pi.hProcess,target,buffer,len(content),ctypes.byref(done)), "Write native stub")
            require(done.value==len(content) and rpm(target,len(content))==content,"Native stub verification failed")
        old=W.DWORD()
        wincheck(protect(pi.hProcess,stub_base,4096,0x20,ctypes.byref(old)),"Protect native stubs RX")
        wincheck(flush(pi.hProcess,stub_base,4096),"Flush native stubs")
        for rva,before,after in sites:
            target=image_base+rva; old,ignored=W.DWORD(),W.DWORD()
            wincheck(protect(pi.hProcess,target,len(after),0x40,ctypes.byref(old)),"Protect selector")
            try:
                buffer,done=ctypes.create_string_buffer(after),SIZE()
                wincheck(write(pi.hProcess,target,buffer,len(after),ctypes.byref(done)),"Write selector")
                require(done.value==len(after) and rpm(target,len(after))==after,"Selector verification failed")
                wincheck(flush(pi.hProcess,target,len(after)),"Flush selector")
            finally:
                wincheck(protect(pi.hProcess,target,len(after),old.value,ctypes.byref(ignored)),"Restore selector protection")
        journal["native_ui"]={"stub_base":hex(stub_base),"sites":[{"rva":hex(r),"before":b.hex(),"after":a.hex()} for r,b,a in sites]}
        write_json(journal_path,journal)
        if not baseline:
            old, ignored = W.DWORD(), W.DWORD()
            wincheck(protect(pi.hProcess, address, len(replacement), 0x40, ctypes.byref(old)), "VirtualProtectEx RWX")
            try:
                buffer, done = ctypes.create_string_buffer(replacement), SIZE()
                wincheck(write(pi.hProcess, address, buffer, len(replacement), ctypes.byref(done)), "WriteProcessMemory")
                require(done.value == len(replacement), "Escrita parcial de memÃ³ria.")
                require(rpm(address, len(replacement)) == replacement, "VerificaÃ§Ã£o do patch falhou.")
                wincheck(flush(pi.hProcess, address, len(replacement)), "FlushInstructionCache")
            finally:
                wincheck(protect(pi.hProcess, address, len(replacement), old.value, ctypes.byref(ignored)), "Restaurar proteÃ§Ã£o")
            journal.update(status="patched_suspended", original_protection=hex(old.value))
        else:
            journal.update(status="baseline_suspended_no_patch")
        write_json(journal_path, journal)
        previous_count = resume(pi.hThread)
        require(previous_count != 0xFFFFFFFF, "ResumeThread falhou.")
        # Any success can permit execution; never terminate after successful resume.
        resumed = True
        journal.update(status="resumed", resume_previous_count=previous_count,
                       resumed_utc=datetime.now(timezone.utc).isoformat())
        write_json(journal_path, journal)
        print(f"PID {pi.dwProcessId}: native FPS selector and dynamic pacing applied in memory.")
        print(f"DiÃ¡rio: {journal_path}\nO jogo NÃƒO foi validado por este lanÃ§amento.")
    except BaseException as error:
        journal.update(status="error_after_resume" if resumed else "error_before_resume", error=str(error))
        if pi.hProcess and not resumed:
            journal["terminated_suspended_child"] = bool(terminate(pi.hProcess, 1))
        write_json(journal_path, journal)
        raise
    finally:
        if pi.hThread:
            close(pi.hThread)
        if pi.hProcess:
            close(pi.hProcess)

    return int(pi.dwProcessId)


def check_tree(root):
    root = Path(root)
    require(root.is_dir(), f"Directory not found: {root}")
    require(not (getattr(root.lstat(), "st_file_attributes", 0) & 0x400) and not root.is_symlink(), "Linked directories are not supported.")
    return files_in(root)


def detect_game(source):
    try:
        value = config_values(Path(source) / "data" / "azimuth.ini").get("game_folder", "")
        candidate = Path(value)
        if not candidate.is_absolute():
            candidate = Path(source) / candidate
        if (candidate / "Mount" / GAME_NAME).is_file():
            return str(candidate.resolve())
    except (OSError, RuntimeError):
        pass
    return ""


def inspect_installation(exe, game):
    exe, game = Path(exe).resolve(), Path(game).resolve()
    require(exe.name.lower() == "azimuth.exe" and exe.is_file(), "Select azimuth.exe.")
    require(sha256(exe) == WRAPPER_SHA, "Unsupported Azimuth build. No files were patched.")
    require(sha256(game / "Mount" / GAME_NAME) == GAME_SHA, "Unsupported or missing FH2 game executable.")
    require(pe_bytes_at_rva(exe, PATCH_RVA, PATCH_SIZE)[0] == EXPECTED, "Unexpected pacing instructions.")
    config_values(exe.parent / "data" / "azimuth.ini")
    return exe, game


def running_azimuth():
    if os.name != "nt":
        return []
    class ENTRY(ctypes.Structure):
        _fields_ = [("dwSize", W.DWORD), ("cntUsage", W.DWORD), ("pid", W.DWORD),
                    ("heap", ctypes.c_size_t), ("module", W.DWORD), ("threads", W.DWORD),
                    ("parent", W.DWORD), ("priority", W.LONG), ("flags", W.DWORD), ("exe", W.WCHAR * 260)]
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    kernel.CreateToolhelp32Snapshot.argtypes = [W.DWORD, W.DWORD]
    kernel.CreateToolhelp32Snapshot.restype = W.HANDLE
    kernel.Process32FirstW.argtypes = kernel.Process32NextW.argtypes = [W.HANDLE, ctypes.POINTER(ENTRY)]
    kernel.CloseHandle.argtypes = [W.HANDLE]
    handle = kernel.CreateToolhelp32Snapshot(2, 0)
    require(handle != ctypes.c_void_p(-1).value, "Could not check running games.")
    found = []
    try:
        entry = ENTRY(); entry.dwSize = ctypes.sizeof(entry)
        ok = kernel.Process32FirstW(handle, ctypes.byref(entry))
        while ok:
            if entry.exe.lower() == "azimuth.exe":
                found.append(int(entry.pid))
            ok = kernel.Process32NextW(handle, ctypes.byref(entry))
    finally:
        kernel.CloseHandle(handle)
    return found


def prepare(exe, game, workspace):
    require(not running_azimuth(), "Save and close Azimuth before setup.")
    exe, game = inspect_installation(exe, game)
    workspace = Path(workspace).resolve()
    require(not inside(workspace, exe.parent) and not inside(exe.parent, workspace), "Keep backup storage separate from Azimuth.")
    require(not inside(workspace, game) and not inside(game, workspace), "Keep backup storage separate from game assets.")
    require(not workspace.exists() or not any(workspace.iterdir()), "Choose an empty settings directory.")
    require(Path(detect_game(exe.parent)).resolve() == game, "Set the game folder in Azimuth first, then close it and retry.")
    workspace.mkdir(parents=True, exist_ok=True)
    shutil.copy2(exe.parent / "data" / "azimuth.ini", workspace / "azimuth-before.ini")
    state = {"format": "fh2-fps-unlocker-direct-v2", "source": str(exe), "game": str(game),
             "created_utc": datetime.now(timezone.utc).isoformat()}
    write_json(workspace / "profile.json", state)
    snapshot_saves(workspace, "initial")
    return state


def runtime_path(workspace):
    state = load_json(Path(workspace) / "profile.json")
    require(state.get("format") == "fh2-fps-unlocker-direct-v2", "Run setup to select your Azimuth installation.")
    return Path(state["source"]).resolve().parent


def snapshot_saves(workspace, session):
    source = runtime_path(workspace) / "data" / "saves"
    target = workspace / "save-backups" / session
    require(not target.exists(), "Save backup already exists.")
    target.mkdir(parents=True)
    hashes = tree_hashes(source) if source.is_dir() else {}
    if source.is_dir():
        check_tree(source)
        shutil.copytree(source, target / "saves")
        require(tree_hashes(target / "saves") == hashes, "Save backup verification failed.")
    write_json(target / "manifest.json", hashes)
    return str(target)


def validate_profile(workspace):
    workspace = Path(workspace).resolve()
    state = load_json(workspace / "profile.json")
    runtime = runtime_path(workspace)
    inspect_installation(runtime / "azimuth.exe", state["game"])
    values = config_values(runtime / "data" / "azimuth.ini")
    require(values.get("frame_rate") in [str(n) for n in RATES], "Unsupported saved FPS value.")
    require(Path(detect_game(runtime)).resolve() == Path(state["game"]).resolve(), "Game path changed. Run setup again.")
    return state, values


def launch(workspace):
    require(os.name == "nt" and ctypes.sizeof(ctypes.c_void_p) == 8, "Windows x64 is required.")
    require(not running_azimuth(), "Save and close Azimuth before launching another session.")
    workspace = Path(workspace).resolve()
    state, values = validate_profile(workspace)
    session = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    snapshot = snapshot_saves(workspace, session)
    journal = {"session_id": session, "initial_fps": int(values["frame_rate"]), "status": "preflight", "experimental_unverified": True,
               "wrapper_sha256": WRAPPER_SHA, "game_sha256": GAME_SHA, "runtime_settings": values,
               "saves_backup": snapshot, "patch_rva": hex(PATCH_RVA), "expected": EXPECTED.hex(),
               "selection": "native Azimuth Frame rate row; final selection may differ from initial_fps"}
    path = workspace / "journals" / (session + ".json")
    write_json(path, journal)
    return patch_suspended(runtime_path(workspace), journal, path)
