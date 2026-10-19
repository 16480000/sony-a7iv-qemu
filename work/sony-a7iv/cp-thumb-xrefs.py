import json
from pathlib import Path
import struct
import sys
import numpy as np
sys.path.insert(0,'/usr/lib/python3/dist-packages')
from capstone import Cs,CS_ARCH_ARM,CS_MODE_THUMB

b=Path('/opt/sony-a7iv/menu-a7m4/runtime/analysis/menu-root/cp/cpapp-b.bin').read_bytes()
a=np.frombuffer(b[:len(b)&~1],dtype='<u2').astype(np.int64)
idx=np.flatnonzero(((a[:-1]&0xf800)==0xf000)&((a[1:]&0xd000)==0xd000))
h1=a[idx];h2=a[idx+1]
s=(h1>>10)&1;j1=(h2>>13)&1;j2=(h2>>11)&1
rel=(s<<24)|(((~(j1^s))&1)<<23)|(((~(j2^s))&1)<<22)|((h1&1023)<<12)|((h2&2047)<<1)
rel=np.where(s,rel-(1<<25),rel)
targets=idx*2+4+rel
dis=Cs(CS_ARCH_ARM,CS_MODE_THUMB)
out=Path('/mnt/d/CodexWork/sony-a7iv-qemu/menu-a7m4')
for target in [int(x,0) for x in sys.argv[1:]]:
    found=idx[targets==target]*2
    print(hex(target),[hex(int(x)) for x in found])
    for p in found:
        p=int(p);lines=[]
        for i in dis.disasm(b[max(0,p-80):p+80],max(0,p-80)):
            lines.append(f'{i.address:08x}: {i.mnemonic:9} {i.op_str}')
        (out/f'cp-xref-{target:x}-{p:x}.asm').write_text('\n'.join(lines))
