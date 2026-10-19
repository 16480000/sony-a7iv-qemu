"""Read-only AArch64 relocatable kernel module analysis with relocation names."""
import argparse
from pathlib import Path
import sys
import re
sys.path.insert(0,'/usr/lib/python3/dist-packages')
sys.path.insert(0,'/mnt/c/Users/16483/Documents/Codex/2026-10-16/new-chat/work/sony-a1m2/pydeps')
from capstone import Cs,CS_ARCH_ARM64
from elftools.elf.elffile import ELFFile
p=argparse.ArgumentParser()
p.add_argument('symbol')
p.add_argument('length',type=lambda x:int(x,0),nargs='?',default=256)
p.add_argument('--offset',type=lambda x:int(x,0),default=0)
p.add_argument('--module',default='dmm.ko')
a=p.parse_args()
with (Path('/opt/sony-a7iv/menu-a7m4/runtime/analysis/menu-root/usr/kmod')/a.module).open('rb') as f:
    e=ELFFile(f);symbols=e.get_section_by_name('.symtab')
    symbol=symbols.get_symbol_by_name(a.symbol)[0];section=e.get_section(symbol['st_shndx'])
    annotations={}
    for reloc in e.iter_sections():
        if reloc['sh_type']=='SHT_RELA' and reloc['sh_info']==symbol['st_shndx']:
            for r in reloc.iter_relocations():
                target=symbols.get_symbol(r['r_info_sym'])
                annotations[r['r_offset']]=f"{target.name}+{r['r_addend']:#x}"
    offset=symbol['st_value']+a.offset;raw=section.data()
    print(a.symbol,'section',section.name,'offset',hex(offset),'size',symbol['st_size'])
    for i in Cs(CS_ARCH_ARM64,0).disasm(raw[offset:offset+a.length],offset):
        note=annotations.get(i.address,'')
        literal=re.search(r', #0x([0-9a-f]+)$',i.op_str) if i.mnemonic=='ldr' else None
        if literal:note=annotations.get(int(literal[1],16),note)
        print(f"{i.address:08x}: {i.mnemonic:9} {i.op_str}"+(' ; '+note if note else ''))
