import io,sys,struct
from pathlib import Path
import numpy as np
sys.path.insert(0,'/mnt/c/Users/16483/Documents/Codex/2026-10-16/new-chat/work/sony-a1m2/pydeps')
from elftools.elf.elffile import ELFFile
path=Path('/opt/sony-a7iv/menu-a7m4/runtime/analysis/menu-root/usr/lib')/sys.argv[1]
b=path.read_bytes();e=ELFFile(io.BytesIO(b));rel=e.get_section_by_name('.rela.plt');sy=e.get_section(rel['sh_link']);plt=e.get_section_by_name('.plt')
sec=e.get_section_by_name('.text');arr=np.frombuffer(sec.data(),dtype='<u4');pcs=np.arange(len(arr),dtype=np.int64)*4+sec['sh_addr'];imm=(arr&0x3ffffff).astype(np.int64);imm=np.where(imm&0x2000000,imm-0x4000000,imm);targets=pcs+imm*4
if sys.argv[2].startswith('0x'):
 target=int(sys.argv[2],0);print('DIRECT',hex(target),[hex(int(x)) for x in pcs[((arr&0xfc000000)==0x94000000)&(targets==target)]]);sys.exit()
for idx,r in enumerate(rel.iter_relocations()):
 name=sy.get_symbol(r['r_info_sym']).name
 if sys.argv[2] not in name:continue
 target=plt['sh_addr']+32+idx*16
 print(name,hex(target),'CALLS',[hex(int(x)) for x in pcs[((arr&0xfc000000)==0x94000000)&(targets==target)]])
