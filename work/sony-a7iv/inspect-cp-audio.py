from pathlib import Path
import json
import struct
import sys
sys.path.insert(0,r'C:\Users\16483\Documents\Codex\2026-10-16\new-chat\work\sony-a1m2\pydeps')
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB

out=Path('/mnt/d/CodexWork/sony-a7iv-qemu/menu-a7m4')
source=Path('/opt/sony-a7iv/menu-a7m4/runtime/analysis/menu-root/cp/cpapp-b.bin')
b=source.read_bytes()
dis=Cs(CS_ARCH_ARM,CS_MODE_THUMB)
hits=[]
for imm in ([int(x,0) for x in sys.argv[1:]] or [0x32d,0x132d,0x32f,0x132f]):
    positions=set()
    for register in range(16):
        first=0xf240|((imm>>12)&15)|(((imm>>11)&1)<<10)
        second=(((imm>>8)&7)<<12)|(register<<8)|(imm&255)
        needle=struct.pack('<HH',first,second)
        pos=0
        while True:
            pos=b.find(needle,pos)
            if pos<0:break
            if not pos%2:positions.add(pos)
            pos+=1
    hits.append({'immediate':hex(imm),'offsets':[hex(x) for x in sorted(positions)]})
    for p in sorted(positions):
        lines=[f'IMMEDIATE {imm:#x} AT FILE+{p:#x}']
        for i in dis.disasm(b[p-40:p+100],p-40):lines.append(f'{i.address:08x}: {i.mnemonic:9} {i.op_str}')
        (out/f'cp-{imm:x}-{p:x}.asm').write_text('\n'.join(lines))
print(json.dumps(hits,indent=2))
