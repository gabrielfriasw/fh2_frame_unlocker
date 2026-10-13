"""Offline execution of actual x64 patch bytes; no game or Windows hooks."""
import pathlib
import struct
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
sys.path.insert(0, r"D:\FH2-analysis-20261013\tools\python-libs")
import native_patches as n
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64
from unicorn.x86_const import *


class NativePatchTests(unittest.TestCase):
    BASES = ((0x140000000, 0x180000000), (0x7FF600000000, 0x1CF00000000),
             (0x400000, 0x600000))

    def execute(self, image, stub, case, fps, pacing, direction):
        plan = n.build_native_ui(image, stub)
        uc = Uc(UC_ARCH_X86, UC_MODE_64)
        uc.mem_map(image, 0x10000)
        uc.mem_map(stub, 0x1000)
        uc.mem_map(0x100000, 0x4000)
        uc.mem_map(0x200000, 0x4000)
        uc.mem_write(stub, plan["code"])
        for site in plan["sites"]:
            uc.mem_write(image + site["rva"], site["replacement"])
        obj, settings, stack = 0x100100, 0x101000, 0x202000
        uc.mem_write(obj + 0x18, struct.pack("<Q", settings))
        sentinel = bytearray(b"\xa5" * 64)
        struct.pack_into("<I", sentinel, 8, fps)
        sentinel[12] = pacing
        uc.mem_write(settings, bytes(sentinel))
        uc.mem_write(stack - 0x100, b"\xb6" * 0x200)
        preserved = {UC_X86_REG_RBX: obj, UC_X86_REG_RBP: 0x123,
                     UC_X86_REG_RSI: 0x456, UC_X86_REG_RSP: stack,
                     UC_X86_REG_R12: 0x789, UC_X86_REG_R13: 0xABC,
                     UC_X86_REG_R14: 0xDEF, UC_X86_REG_R15: 0xFED}
        for reg, value in preserved.items():
            uc.reg_write(reg, value)
        uc.reg_write(UC_X86_REG_EDX, direction & 0xFFFFFFFF)
        uc.reg_write(UC_X86_REG_RDI, 0x9999999900000000)
        entry = n.FPS_RVA if case == "fps" else n.PACING_RVA
        uc.emu_start(image + entry, image + n.CONTINUATION_RVA, count=200)
        self.assertEqual(uc.reg_read(UC_X86_REG_RIP), image + n.CONTINUATION_RVA)
        for reg, value in preserved.items():
            self.assertEqual(uc.reg_read(reg), value)
        self.assertEqual(uc.reg_read(UC_X86_REG_RDI), 5 if case == "fps" else 6)
        self.assertEqual(bytes(uc.mem_read(stack - 0x100, 0x200)), b"\xb6" * 0x200)
        actual = bytearray(uc.mem_read(settings, 64))
        result_fps = struct.unpack_from("<I", actual, 8)[0]
        result_pacing = actual[12]
        actual[8:13] = sentinel[8:13]
        self.assertEqual(actual, sentinel)
        return result_fps, result_pacing

    def test_all_rates_directions_pacing_and_bases(self):
        for bases in self.BASES:
            for rate in n.RATES:
                for direction in (-2**31, -1, 0, 1, 2**31-1):
                    for pacing in (0, 1):
                        with self.subTest(bases=bases, rate=rate, direction=direction, pacing=pacing):
                            idx = (n.RATES.index(rate) + (-1 if direction < 0 else 1)) % 8
                            want = n.RATES[idx]
                            result = self.execute(*bases, "fps", rate, pacing, direction)
                            self.assertEqual(result, (want, 1 if want > 60 else pacing))

    def test_invalid_rate_falls_back_to_60(self):
        for bases in self.BASES:
            for rate in (0, 1, 59, 61, 1000, 0xFFFFFFFF):
                for direction in (-1, 1):
                    for pacing in (0, 1):
                        self.assertEqual(self.execute(*bases,"fps",rate,pacing,direction),(60,pacing))

    def test_pacing_toggle_and_high_rate_guard(self):
        for bases in self.BASES:
            for rate in n.RATES:
                for pacing in (0, 1, 2):
                    self.assertEqual(self.execute(*bases,"pacing",rate,pacing,0),
                                     (rate, 1 if rate > 60 else int(pacing == 0)))

    def test_guards_and_jump_layout(self):
        for bases in self.BASES:
            plan=n.build_native_ui(*bases)
            self.assertEqual(len(plan["sites"]),2)
            for site, label in zip(plan["sites"],("fps","pacing")):
                self.assertEqual(len(site["replacement"]),len(site["original"]))
                self.assertEqual(site["replacement"][:6],bytes.fromhex("ff2500000000"))
                self.assertEqual(struct.unpack_from("<Q",site["replacement"],6)[0],
                                 bases[1]+plan["offsets"][label])
            self.assertEqual(plan["sites"][0]["original"],n.FPS_ORIGINAL)
            self.assertEqual(plan["sites"][1]["original"],n.PACING_ORIGINAL)
        for bad in (-1,2**64,"0x140000000"):
            with self.assertRaises(ValueError): n.build_native_ui(bad,0x100000)


if __name__ == "__main__":
    unittest.main()
