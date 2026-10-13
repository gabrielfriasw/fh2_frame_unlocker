"""Memory-only patches for the verified Azimuth 0.9.7 native settings UI.

build_native_ui(image_base, stub_base) returns a dict:
  code: bytes to write at stub_base (needs executable protection)
  sites: tuple of {rva, original, replacement} bytes, verify before writing
  offsets: offsets within code for fps, pacing, table
  rates: the selectable rates

The caller owns allocation, original-image hash/byte checks, thread suspension,
page protections and instruction-cache flushing. This module touches no process.
UI continuation RVA 0xd23c performs the original setting persistence operation.
An unknown FPS falls back to 60 in either direction. Above 60 the in-memory
pacing byte is forced to real-time; the caller must also normalize config loads.
The FPS branch keeps pacing unchanged at 30/60. The pacing branch toggles it
at 30/60 (or other <=60 values), while values above 60 remain real-time.
"""
import struct

RATES = (30, 60, 90, 120, 144, 165, 180, 200)
FPS_RVA = 0xD144
PACING_RVA = 0xD165
CONTINUATION_RVA = 0xD23C
FPS_ORIGINAL = bytes.fromhex(
    "488b4b18b81e000000ba3c0000003941080f44c2894108bf05000000e9d7000000"
)
PACING_ORIGINAL = bytes.fromhex(
    "488b4b1880790c000f94c088410cbf06000000e9bf000000"
)


def absolute_jump(address):
    """RIP-indirect jump, 14 bytes, no register or stack clobber."""
    if not isinstance(address, int) or not 0 <= address < 2**64:
        raise ValueError("address must be a uint64")
    return b"\xff\x25\x00\x00\x00\x00" + struct.pack("<Q", address)


class _Code:
    def __init__(self):
        self.data = bytearray()
        self.labels = {}
        self.fixups = []

    def emit(self, data):
        self.data.extend(bytes.fromhex(data) if isinstance(data, str) else data)

    def label(self, name):
        self.labels[name] = len(self.data)

    def relative(self, opcode, target):
        self.emit(opcode)
        self.fixups.append((len(self.data), target))
        self.emit(b"\x00" * 4)

    def finish(self):
        for offset, target in self.fixups:
            struct.pack_into("<i", self.data, offset, self.labels[target] - offset - 4)
        return bytes(self.data)


def build_native_ui(image_base, stub_base):
    """Build both native selector stubs for any valid relocated x64 bases."""
    for base in (image_base, stub_base):
        if not isinstance(base, int) or not 0 <= base <= 2**64 - 0x100000:
            raise ValueError("base outside supported uint64 range")
    c = _Code()
    c.label("fps")
    c.emit("488b4b18")       # mov rcx,[rbx+18h] ; settings
    c.emit("8b4108")         # mov eax,[rcx+8]
    c.relative("4c8d0d", "table")  # lea r9,[rip+table]
    c.emit("4531c0")         # xor r8d,r8d
    c.label("search")
    c.emit("433b0481")       # cmp eax,[r9+r8*4]
    c.relative("0f84", "found")
    c.emit("41ffc0")         # inc r8d
    c.emit("4183f808")       # cmp r8d,8
    c.relative("0f82", "search")
    c.emit("b83c000000")     # unknown setting: safe fallback 60
    c.relative("e9", "store")
    c.label("found")
    c.emit("85d2")           # test edx,edx ; native direction parameter
    c.relative("0f88", "previous")
    c.emit("41ffc0")         # inc r8d
    c.relative("e9", "selected")
    c.label("previous")
    c.emit("41ffc8")         # dec r8d
    c.label("selected")
    c.emit("4183e007")       # and r8d,7 ; circular eight-entry list
    c.emit("438b0481")       # mov eax,[r9+r8*4]
    c.label("store")
    c.emit("894108")         # mov [rcx+8],eax
    c.emit("83f83c")         # cmp eax,60
    c.relative("0f86", "fps_done")  # jbe
    c.emit("c6410c01")       # mov byte [rcx+0ch],1 ; real-time
    c.label("fps_done")
    c.emit("bf05000000")     # mov edi,5 ; native persistence selector
    c.emit(absolute_jump(image_base + CONTINUATION_RVA))
    while len(c.data) % 16:
        c.emit("90")
    c.label("pacing")
    c.emit("488b4b18")       # mov rcx,[rbx+18h]
    c.emit("8379083c")       # cmp dword [rcx+8],60
    c.relative("0f87", "force_realtime")
    c.emit("80790c00")       # cmp byte [rcx+0ch],0
    c.emit("0f94c0")         # sete al
    c.emit("88410c")         # mov [rcx+0ch],al
    c.relative("e9", "pacing_done")
    c.label("force_realtime")
    c.emit("c6410c01")
    c.label("pacing_done")
    c.emit("bf06000000")     # mov edi,6
    c.emit(absolute_jump(image_base + CONTINUATION_RVA))
    while len(c.data) % 4:
        c.emit("90")
    c.label("table")
    c.emit(struct.pack("<8I", *RATES))
    sites = []
    for rva, original, label in (
        (FPS_RVA, FPS_ORIGINAL, "fps"),
        (PACING_RVA, PACING_ORIGINAL, "pacing"),
    ):
        replacement = absolute_jump(stub_base + c.labels[label])
        replacement += b"\x90" * (len(original) - len(replacement))
        sites.append({"rva": rva, "original": original, "replacement": replacement})
    return {
        "code": c.finish(),
        "sites": tuple(sites),
        "offsets": {name: c.labels[name] for name in ("fps", "pacing", "table")},
        "rates": RATES,
    }
