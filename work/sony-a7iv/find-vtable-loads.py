import contextlib,importlib.util,io,json,struct,sys
from pathlib import Path
import numpy as np
w=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('c',w/'compare-elf-addresses.py');m=importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()):spec.loader.exec_module(m)
e=m.Elf(m.NEW/'appFw.so')
print('346 constructor vtable:',hex(e.q(0x59df898)+16))
wrong=e.q(0x59df898)+16
print('346 type:',e.cstr(e.q(e.q(wrong-8)+8)))
vptr=int(sys.argv[1],0) if len(sys.argv)>1 else 0x599e090
needle=struct.pack('<Q',vptr-16);pos=0;got=[]
while True:
    pos=e.raw.find(needle,pos)
    if pos<0:break
    if not pos%8:
        try:got.append(e.va(pos))
        except ValueError:pass
    pos+=1
sec=e.elf.get_section_by_name('.text');a=np.frombuffer(sec.data(),dtype='<u4').astype(np.int64)
idx=np.flatnonzero((a&0x9f000000)==0x90000000);op=a[idx];regs=op&31
imm=(((op>>5)&0x7ffff)<<2)|((op>>29)&3);imm=np.where(imm&(1<<20),imm-(1<<21),imm)
pages=((sec['sh_addr']+idx*4)&~4095)+(imm<<12)
rows=[]
for delta in range(1,12):
    ins=a[np.minimum(idx+delta,len(a)-1)]
    hits=((ins&0xffc00000)==0xf9400000)&(((ins>>5)&31)==regs)&np.isin(pages+(((ins>>10)&4095)*8),got)
    for i in np.flatnonzero(hits):
        address=int(sec['sh_addr']+idx[i]*4)
        rows.append({'adrp':hex(address),'load':hex(address+delta*4),'got':hex(int(pages[i]+((ins[i]>>10)&4095)*8))})
print(json.dumps({'vptr':hex(vptr),'got':[hex(x) for x in got],'code_loads':rows},indent=2))
(m.D/'menu-a7m4/menu-vtable-loads.json').write_text(json.dumps({'vptr':hex(vptr),'got':[hex(x) for x in got],'code_loads':rows},indent=2))
