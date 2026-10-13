import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import extra_options as e


class ExtraOptionsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / "data" / "bin"
        self.bin.mkdir(parents=True)
        self.helper = self.bin / "azimuth-tls.dll"
        self.ini = self.bin / "FH2_ExtraOptions.ini"
        self.log = self.bin / "FH2_ExtraOptions.log"
        fixture = b"reviewed test fixture, never loaded"
        self.helper.write_bytes(fixture)
        digest = hashlib.sha256(fixture).hexdigest()
        mock = patch.dict(e.KNOWN_ADAPTERS, {digest: "test"})
        mock.start()
        self.addCleanup(mock.stop)
        self.ini.write_bytes(b"[Global]\nEnabled=1\n")

    def write_log(self, status):
        self.log.write_text("Forza Horizon 2 Extra Options test - Azimuth TLS adapter\n" + status + "\n", encoding="utf-8")

    def test_inspection_is_read_only_and_not_runtime_success(self):
        before = {p.name: p.read_bytes() for p in self.bin.iterdir()}
        info = e.inspect(self.root)
        self.assertEqual(info["state"], "recognized_adapter")
        self.assertFalse(info["runtime_confirmed"])
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.bin.iterdir()})

    def test_stale_ok_log_is_not_current_success(self):
        self.write_log("OK: requested tweaks applied in memory.")
        before = e.inspect(self.root)
        result = e.observe_log(self.root, before)
        self.assertEqual(result["state"], "not_observed")
        self.assertFalse(result["runtime_confirmed"])

    def test_new_log_distinguishes_success_disabled_and_refusal(self):
        before = e.inspect(self.root)
        for status, state, ok in [("OK: requested tweaks applied in memory.", "startup_ok", True),
                                  ("DISABLED: no memory changes made.", "disabled", False),
                                  ("REFUSED: unexpected loaded bytes.", "refused", False)]:
            with self.subTest(status=status):
                self.write_log(status)
                info = e.observe_log(self.root, before)
                self.assertEqual(info["state"], state)
                self.assertEqual(info["runtime_confirmed"], ok)

    def test_changed_or_unknown_helper_is_not_confirmed(self):
        before = e.inspect(self.root)
        self.helper.write_bytes(b"different helper")
        self.write_log("OK: requested tweaks applied in memory.")
        self.assertEqual(e.observe_log(self.root, before)["state"], "adapter_changed")
        unknown = e.inspect(self.root)
        self.assertEqual(unknown["state"], "unrecognized_adapter")
        self.log.write_bytes(b"")
        unknown = e.inspect(self.root)
        self.write_log("OK: requested tweaks applied in memory.")
        self.assertFalse(e.observe_log(self.root, unknown)["runtime_confirmed"])

    def test_missing_and_orphan_settings(self):
        self.helper.unlink()
        self.assertEqual(e.inspect(self.root)["state"], "settings_without_adapter")
        self.ini.unlink()
        self.assertEqual(e.inspect(self.root)["state"], "not_detected")

    def test_ini_encoding_warning_does_not_rewrite_it(self):
        self.ini.write_text("[Global]\nEnabled=1\n", encoding="utf-16")
        original = self.ini.read_bytes()
        info = e.inspect(self.root)
        self.assertTrue(any("UTF-16" in line for line in info["warnings"]))
        self.assertEqual(self.ini.read_bytes(), original)
