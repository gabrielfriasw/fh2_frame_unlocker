"""Memory-only hooks for the exact supported Azimuth settings parser."""
import struct
RATES=(30,60,90,120,144,165,180,200)
class Asm:
    def __init__(self):self.code=bytearray();self.labels={};self.fixups=[]
    def emit(self,h):self.code.extend(bytes.fromhex(h))
    def label(self,name):self.labels[name]=len(self.code)
    def branch(self,opcode,label):
        self.emit(opcode);self.fixups.append((len(self.code),label));self.code.extend(b"\0"*4)
    def absolute(self,address):self.emit("ff2500000000");self.code.extend(struct.pack("<Q",address))
    def finish(self):
        for at,name in self.fixups:struct.pack_into("<i",self.code,at,self.labels[name]-(at+4))
        return bytes(self.code)

def parser_code(image):
    a=Asm();a.emit("488b9580000000 4883fa02");a.branch("0f82","done")
    a.emit("4883fa03");a.branch("0f87","done")
    a.emit("4c8d4d70 4883bd8800000007 4c0f474d70 31c0 31c9")
    a.label("digits");a.emit("450fb70449 4183e830 4183f809");a.branch("0f87","done")
    a.emit("6bc00a 4401c0 48ffc1 4839d1");a.branch("0f82","digits")
    for rate in RATES:
        a.emit("3d");a.code.extend(struct.pack("<I",rate));a.branch("0f84","accept")
    a.branch("e9","done");a.label("accept");a.emit("4189442408")
    a.label("done");a.absolute(image+0x5de4c)
    return a.finish()

def pacing_parser_code(image):
    a=Asm();a.emit("41837c24083c");a.branch("0f86","original")
    a.emit("41c644240c01");a.label("original");a.emit("4883fb07")
    a.branch("0f86","small");a.emit("488d145d02000000");a.absolute(image+0x5dfa3)
    a.label("small");a.absolute(image+0x5dfd0)
    return a.finish()

def dynamic_pacing():
    # CALL wrapper QPF helper; retain QPF in R15; divide by actual selected rate.
    code=b"\xe8"+struct.pack("<i",0x32870-(0x3613d+5))+bytes.fromhex("4989c7 31d2")
    site=0x3613d+len(code)
    code+=bytes.fromhex("8b0d")+struct.pack("<i",0x2beec4-(site+6))
    code+=bytes.fromhex("85c9 7505 b93c000000 48f7f1 4889c3")
    return code.ljust(70,b"\x90")

def jump(address,size):
    assert size>=14
    return (bytes.fromhex("ff2500000000")+struct.pack("<Q",address)).ljust(size,b"\x90")

PARSER_RVA=0x5dd80
PARSER_EXPECTED=bytes.fromhex("4c8d4d704c8b55704c8b9d88000000")
PACING_RVA=0x5df95
PACING_EXPECTED=bytes.fromhex("4883fb077635488d145d02000000")
