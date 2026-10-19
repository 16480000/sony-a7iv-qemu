from pathlib import Path
import io,sys,struct
import numpy as np
sys.path.insert(0,'/mnt/c/Users/16483/Documents/Codex/2026-10-16/new-chat/work/sony-a1m2/pydeps')
from elftools.elf.elffile import ELFFile
root=Path('/opt/sony-a7iv/menu-a7m4/runtime/analysis/menu-root/usr/kmod')
for path in root.glob('*.ko'):
 raw=path.read_bytes()
 if struct.pack('<I',0x80cf016d) in raw:print('LITERAL',path.name,hex(raw.index(struct.pack('<I',0x80cf016d))))
 elf=ELFFile(io.BytesIO(raw))
 for sec in elf.iter_sections():
  if not(sec['sh_flags']&4) or sec['sh_size']%4:continue
  a=np.frombuffer(sec.data(),dtype='<u4')
  hits=np.flatnonzero(((a&0x7f800000)==0x52800000)&(((a>>5)&65535)==0x16d))
  for k in hits:
   reg=int(a[k]&31)
   for j in range(int(k)+1,min(int(k)+24,len(a))):
    v=int(a[j])
    if v&0x7f800000==0x72800000 and v&31==reg and (v>>5)&65535==0x80cf:
     print('QUEUE',path.name,sec.name,hex(int(k)*4),hex(j*4))
