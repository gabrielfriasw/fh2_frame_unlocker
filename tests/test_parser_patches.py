import struct, unittest
from unicorn import Uc, UC_ARCH_X86, UC_MODE_64
from unicorn.x86_const import *
import parser_patches as p

class ParserTests(unittest.TestCase):
    def machine(self, image, stub):
        u=Uc(UC_ARCH_X86,UC_MODE_64);u.mem_map(image,0x400000);u.mem_map(stub,0x1000);u.mem_map(0x200000000,0x10000)
        return u
    def test_parser_whitelist_and_heap_string(self):
        for image,stub in [(0x140000000,0x180000000),(0x7ff600000000,0x7ff900000000)]:
            for heap in [False,True]:
                for value in [*map(str,p.RATES),'0','999','-1','60junk','','090','61']:
                    with self.subTest(value=value,heap=heap):
                        u=self.machine(image,stub);mem=0x200000000;u.mem_write(stub,p.parser_code(image));u.reg_write(UC_X86_REG_RBP,mem+0x100);u.reg_write(UC_X86_REG_R12,mem+0x1000)
                        u.mem_write(mem+0x180,struct.pack('<Q',len(value)));u.mem_write(mem+0x188,struct.pack('<Q',15 if heap else 7))
                        if heap:
                            u.mem_write(mem+0x170,struct.pack('<Q',mem+0x3000));u.mem_write(mem+0x3000,value.encode('utf-16le'))
                        else:u.mem_write(mem+0x170,value.encode('utf-16le'))
                        u.mem_write(mem+0x1008,struct.pack('<I',30));u.emu_start(stub,image+0x5de4c,count=500)
                        expected=int(value) if value in list(map(str,p.RATES))+['090'] else 30
                        self.assertEqual(struct.unpack('<I',u.mem_read(mem+0x1008,4))[0],expected)
    def test_pacing_force_preserves_small_and_heap_cleanup(self):
        image,stub=0x140000000,0x180000000
        for rate in p.RATES:
            for existing in [0,1]:
                for capacity in [7,15]:
                    u=self.machine(image,stub);mem=0x200000000;u.mem_write(stub,p.pacing_parser_code(image));u.reg_write(UC_X86_REG_R12,mem+0x1000);u.reg_write(UC_X86_REG_RBX,capacity)
                    u.mem_write(mem+0x1008,struct.pack('<IB',rate,existing));end=image+(0x5dfd0 if capacity==7 else 0x5dfa3);u.emu_start(stub,end,count=100)
                    self.assertEqual(u.mem_read(mem+0x100c,1)[0],1 if rate>60 else existing)
                    if capacity>7:self.assertEqual(u.reg_read(UC_X86_REG_RDX),capacity*2+2)
    def test_dynamic_pacing(self):
        for image in [0x140000000,0x7ff600000000]:
            for rate in [0,*p.RATES]:
                for freq in [3579545,10000000,2400000000]:
                    u=self.machine(image,0x180000000);mem=0x200000000;u.mem_write(image+0x3613d,p.dynamic_pacing());u.mem_write(image+0x32870,bytes.fromhex('48b8')+struct.pack('<Q',freq)+b'\xc3');u.mem_write(image+0x2beec4,struct.pack('<I',rate));u.reg_write(UC_X86_REG_RSP,mem+0x8000)
                    u.emu_start(image+0x3613d,image+0x36183,count=100)
                    self.assertEqual(u.reg_read(UC_X86_REG_RBX),freq//(rate or 60));self.assertEqual(u.reg_read(UC_X86_REG_R15),freq);self.assertEqual(u.reg_read(UC_X86_REG_RSP),mem+0x8000)
