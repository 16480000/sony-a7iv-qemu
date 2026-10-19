"""Find Thumb MOVW/MOVT immediate encodings in the original CP (file offsets)."""
from pathlib import Path
import struct
import sys
sys.path.insert(0,'/usr/lib/python3/dist-packages')
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB
b=Path('/opt/sony-a7iv/menu-a7m4/runtime/analysis/menu-root/cp/cpapp-b.bin').read_bytes()
d=Cs(CS_ARCH_ARM,CS_MODE_THUMB)
for value in map(lambda x:int(x,0),sys.argv[1:]):
    for name,base in [('movw',0xf240),('movt',0xf2c0)]:
        hits=set()
        for register in range(16):
            pair=struct.pack('<HH',base|((value>>12)&15)|(((value>>11)&1)<<10),
                (((value>>8)&7)<<12)|(register<<8)|(value&255))
            start=0
            while True:
                start=b.find(pair,start)
                if start<0:break
                if not start%2:hits.add(start)
                start+=1
        print(hex(value),name,[hex(p) for p in sorted(hits)])
        for p in sorted(hits):
            if name=='movt':
                for i in d.disasm(b[max(0,p-24):p+72],max(0,p-24)):
                    print(f'{i.address:08x}: {i.mnemonic:8} {i.op_str}')
