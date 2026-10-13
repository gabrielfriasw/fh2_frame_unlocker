"""PE fixtures contain only headers, guard signatures and inert padding."""
from pathlib import Path
import struct
import tempfile
import unittest
import engine


def pe_fixture(regions=()):
    raw_size = 0x60000
    data = bytearray(0x200 + raw_size)
    data[:2] = b"MZ"
    struct.pack_into("<I", data, 0x3c, 0x80)
    data[0x80:0x84] = b"PE\0\0"
    struct.pack_into("<HH", data, 0x84, 0x8664, 1)
    struct.pack_into("<H", data, 0x94, 0xf0)
    struct.pack_into("<H", data, 0x98, 0x20b)
    struct.pack_into("<I", data, 0x98 + 56, 0x61000)
    table = 0x98 + 0xf0
    data[table:table + 8] = b".text\0\0\0"
    struct.pack_into("<IIII", data, table + 8, raw_size, 0x1000, raw_size, 0x200)
    struct.pack_into("<I", data, table + 36, 0x60000020)
    for _, rva, original in regions:
        offset = 0x200 + rva - 0x1000
        data[offset:offset + len(original)] = original
    return data


class PatchRegionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.exe = self.root/'azimuth.exe'
        self.game = self.root/'game'
        (self.root/'data').mkdir()
        (self.game/'Mount').mkdir(parents=True)
        (self.root/'data'/'azimuth.ini').write_text('frame_rate=90\n', encoding='utf-8')
        self.data = pe_fixture(engine.guarded_regions())
        self.exe.write_bytes(self.data)
        self.game_exe = self.game/'Mount'/engine.GAME_NAME
        self.game_exe.write_bytes(pe_fixture())

    def test_outside_changes_and_game_mods_are_accepted_without_writes(self):
        # Deliberately unrelated hashes and changed bytes outside all five sites.
        self.data[0x300] ^= 0x5a
        self.exe.write_bytes(self.data)
        game = bytearray(self.game_exe.read_bytes())
        game[0x400] ^= 0xa5
        self.game_exe.write_bytes(game)
        before = {p: p.read_bytes() for p in (self.exe, self.game_exe)}
        self.assertNotEqual(engine.sha256(self.exe), engine.WRAPPER_SHA)
        engine.inspect_installation(self.exe, self.game)
        self.assertEqual(len(engine.validate_patch_regions(self.exe)), 5)
        self.assertEqual(before, {p: p.read_bytes() for p in before})

    def test_every_guard_rejects_a_one_byte_overlap(self):
        for name, rva, original in engine.guarded_regions():
            for index in (0, len(original)-1):
                with self.subTest(region=name, index=index):
                    data = bytearray(self.data)
                    data[0x200 + rva - 0x1000 + index] ^= 1
                    self.exe.write_bytes(data)
                    with self.assertRaisesRegex(RuntimeError, 'Patch conflict in '+name):
                        engine.inspect_installation(self.exe, self.game)
                    self.assertEqual(self.exe.read_bytes(), data)

    def test_truncated_or_non_x64_images_are_refused(self):
        wrong_arch = bytearray(self.data)
        struct.pack_into('<H', wrong_arch, 0x84, 0x14c)
        for value in (b'', b'MZ', bytes(self.data[:0x100]), wrong_arch):
            with self.subTest(size=len(value)):
                self.exe.write_bytes(value)
                with self.assertRaises(RuntimeError):
                    engine.validate_patch_regions(self.exe)

    def test_wrong_section_permissions_and_moved_layout_are_refused(self):
        table = 0x98 + 0xf0
        for offset, value in [(table + 36, 0x40000040), (table + 12, 0x2000)]:
            data = bytearray(self.data)
            struct.pack_into('<I', data, offset, value)
            self.exe.write_bytes(data)
            with self.assertRaises(RuntimeError):
                engine.validate_patch_regions(self.exe)
