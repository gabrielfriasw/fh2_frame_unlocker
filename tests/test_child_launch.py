from types import SimpleNamespace
import unittest
from unittest.mock import patch
import child_launch as c


class Function:
    def __init__(self, callback):
        self.callback = callback
    def __call__(self, *args):
        return self.callback(*args)


class ChildLaunchTests(unittest.TestCase):
    def test_frozen_directory_is_cleared_then_restored_on_success_and_error(self):
        for fail in (False, True):
            state = {"directory": r"C:\Temp\_MEItest", "calls": []}
            def get_directory(size, buffer):
                if buffer is None:
                    return len(state["directory"]) + 1
                buffer.value = state["directory"]
                return len(buffer.value)
            def set_directory(value):
                state["directory"] = value
                state["calls"].append(value)
                return 1
            kernel = SimpleNamespace(GetDllDirectoryW=Function(get_directory),
                                     SetDllDirectoryW=Function(set_directory))
            with patch.object(c, "os", SimpleNamespace(name="nt")), patch.object(c.sys, "frozen", True, create=True), patch.object(c.ctypes, "WinDLL", return_value=kernel, create=True):
                try:
                    with c.external_dll_search() as reset:
                        self.assertTrue(reset)
                        self.assertIsNone(state["directory"])
                        if fail:
                            raise ValueError("child launch failed")
                except ValueError:
                    self.assertTrue(fail)
            self.assertEqual(state["calls"], [None, r"C:\Temp\_MEItest"])
            self.assertEqual(state["directory"], r"C:\Temp\_MEItest")

    def test_source_mode_leaves_search_path_alone(self):
        with patch.object(c.sys, "frozen", False, create=True), patch.object(c.ctypes, "WinDLL", create=True) as win:
            with c.external_dll_search() as reset:
                self.assertFalse(reset)
            win.assert_not_called()
