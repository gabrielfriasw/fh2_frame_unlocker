"""Keep the bundled launcher's private DLL directory out of Azimuth."""
import ctypes
from ctypes import wintypes as W
from contextlib import contextmanager
import os
import sys


@contextmanager
def external_dll_search():
    if os.name != "nt" or not getattr(sys, "frozen", False):
        yield False
        return
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    get_directory = kernel.GetDllDirectoryW
    get_directory.argtypes, get_directory.restype = [W.DWORD, W.LPWSTR], W.DWORD
    set_directory = kernel.SetDllDirectoryW
    set_directory.argtypes, set_directory.restype = [W.LPCWSTR], W.BOOL
    length = get_directory(0, None)
    previous = ctypes.create_unicode_buffer(length + 1)
    copied = get_directory(len(previous), previous)
    if copied >= len(previous):
        raise RuntimeError("DLL search directory changed during startup. Please retry.")
    if not set_directory(None):
        raise ctypes.WinError(ctypes.get_last_error())
    try:
        yield True
    finally:
        if not set_directory(previous.value or None):
            raise ctypes.WinError(ctypes.get_last_error())
