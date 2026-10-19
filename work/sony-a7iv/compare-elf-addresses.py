import bisect
import io
import json
from pathlib import Path
import struct
import sys

sys.path.insert(0,'/mnt/c/Users/16483/Documents/Codex/2026-10-16/new-chat/work/sony-a1m2/pydeps')
from elftools.elf.elffile import ELFFile

D=Path('/mnt/d/CodexWork/sony-a7iv-qemu')
OLD=D/'a7c2-reference/comparison-assets'
NEW=Path('/opt/sony-a7iv/menu-a7m4/runtime/analysis/menu-root/usr/lib')

class Elf:
    def __init__(self,path):
        self.raw=path.read_bytes()
        self.elf=ELFFile(io.BytesIO(self.raw))
        self.loads=[x for x in self.elf.iter_segments() if x['p_type']=='PT_LOAD']
        self.symbols={s.name:s for s in self.elf.get_section_by_name('.dynsym').iter_symbols() if s['st_value']}
        self.byaddr={s['st_value']:s for s in self.symbols.values()}
        self.sorted=sorted(self.byaddr)
    def offset(self,va):
        for x in self.loads:
            if x['p_vaddr']<=va<x['p_vaddr']+x['p_filesz']:return va-x['p_vaddr']+x['p_offset']
        raise ValueError(hex(va))
    def va(self,off):
        for x in self.loads:
            if x['p_offset']<=off<x['p_offset']+x['p_filesz']:return off-x['p_offset']+x['p_vaddr']
        raise ValueError(hex(off))
    def q(self,va):return struct.unpack_from('<Q',self.raw,self.offset(va))[0]
    def cstr(self,va):
        off=self.offset(va)
        return self.raw[off:self.raw.index(0,off)].decode()
    def references(self,va):
        needle=struct.pack('<Q',va)
        section=self.elf.get_section_by_name('.data.rel.ro')
        data=section.data();result=[];pos=0
        while True:
            pos=data.find(needle,pos)
            if pos<0:break
            if pos%8==0:result.append(section['sh_addr']+pos)
            pos+=1
        return result
    def describe(self,va):
        index=bisect.bisect_right(self.sorted,va)-1
        if index<0:return {'address':hex(va)}
        sym=self.byaddr[self.sorted[index]]
        return {'address':hex(va),'symbol':sym.name,'symbol_address':hex(sym['st_value']),
                'delta':hex(va-sym['st_value']),'within_size':va-sym['st_value']<sym['st_size']}

old,new=Elf(OLD/'libObj.so'),Elf(NEW/'libObj.so')
addresses=[0x174dbc,0x100d28,0x100cd8,0x100cec,0x100d3c,0x100cb0,0x100eac,0x100c3c,
           0x104404,0x104414,0x133cc8,0x130de8,0x130e00,0x100224,0x2ebde0,0x2ec900,0x26d210]
result=[]
for va in addresses:
    row=old.describe(va)
    sym=new.symbols.get(row.get('symbol',''))
    if sym and row.get('within_size'):
        row['new_address']=hex(sym['st_value']+int(row['delta'],16))
        row['new_symbol_size']=sym['st_size']
    result.append(row)

def rtti(old,new,vptr):
    typeinfo=old.q(vptr-8)
    name=old.cstr(old.q(typeinfo+8))
    off=new.raw.find(name.encode()+b'\0')
    out={'old_vptr':hex(vptr),'type_name':name,'new_vptrs':[]}
    if off<0:return out
    string_va=new.va(off)
    for ref in new.references(string_va):
        typeinfo=ref-8
        for ptr in new.references(typeinfo):
            if new.q(ptr-8)==0:
                out['new_vptrs'].append(hex(ptr+8))
    return out

vtables=[]
for filename,values in [('libObj.so',[0x26d210,0x133cc8]),('appFw.so',[0x58dbf28,0x5b0c480,0x5b0e298])]:
    a,b=Elf(OLD/filename),Elf(NEW/filename)
    for v in values:
        try:vtables.append({'elf':filename,**rtti(a,b,v)})
        except Exception as e:vtables.append({'elf':filename,'old_vptr':hex(v),'error':str(e)})
report={'libObj_symbols':result,'rtti_vtables':vtables}
(D/'menu-a7m4/elf-address-comparison.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
