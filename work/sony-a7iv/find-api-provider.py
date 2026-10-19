from pathlib import Path
import sys
sys.path.insert(0,'/mnt/c/Users/16483/Documents/Codex/2026-10-16/new-chat/work/sony-a1m2/pydeps')
from elftools.elf.elffile import ELFFile
root=Path('/opt/sony-a7iv/menu-a7m4/runtime/analysis/menu-root/usr/lib')
for p in root.glob('*.so*'):
 if not p.is_file():continue
 try:
  with p.open('rb') as f:
   elf=ELFFile(f);sy=elf.get_section_by_name('.dynsym')
   if not sy:continue
   for s in sy.get_symbol_by_name(sys.argv[1]) or []:
    if s['st_value']:print(p.name,hex(s['st_value']),hex(s['st_size']))
 except (ValueError,OSError):pass
