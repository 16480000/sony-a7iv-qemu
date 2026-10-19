import contextlib,importlib.util,io,json,sys
from pathlib import Path
import numpy as np
sys.path.insert(0,'/usr/lib/python3/dist-packages')
from capstone import Cs,CS_ARCH_ARM64
w=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('c',w/'compare-elf-addresses.py');m=importlib.util.module_from_spec(s)
with contextlib.redirect_stdout(io.StringIO()):s.loader.exec_module(m)
e=m.Elf(m.NEW/'appFw.so');sec=e.elf.get_section_by_name('.text');b=sec.data();a=np.frombuffer(b,dtype='<u4')
dis=Cs(CS_ARCH_ARM64,0)
for imm in [int(x,0) for x in sys.argv[1:]]:
    hits=np.flatnonzero(((a&0xffe00000)==0x52800000)&(((a>>5)&65535)==imm))
    print(hex(imm),[hex(int(sec['sh_addr']+i*4)) for i in hits])
    for i in hits:
        off=max(0,int(i)*4-64);address=sec['sh_addr']+off
        rows=[f'{x.address:09x}: {x.mnemonic:9} {x.op_str}' for x in dis.disasm(b[off:off+256],address)]
        (m.D/f'menu-a7m4/app-{imm:x}-{sec["sh_addr"]+int(i)*4:x}.asm').write_text('\n'.join(rows))
