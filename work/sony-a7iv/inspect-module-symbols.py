from pathlib import Path
import sys,re
sys.path.insert(0,'/mnt/c/Users/16483/Documents/Codex/2026-10-16/new-chat/work/sony-a1m2/pydeps')
from elftools.elf.elffile import ELFFile
root=Path('/opt/sony-a7iv/menu-a7m4/runtime/analysis/menu-root/usr/kmod')
with (root/sys.argv[1]).open('rb') as f:
 e=ELFFile(f)
 for s in e.get_section_by_name('.symtab').iter_symbols():
  if re.search(sys.argv[2],s.name,re.I):print(hex(s['st_value']),s['st_size'],s['st_shndx'],s.name)
