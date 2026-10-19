"""Read-only original firmware capture/input/storage evidence queries."""
import sys,io,re,struct
from pathlib import Path
sys.path.insert(0,'/mnt/c/Users/16483/Documents/Codex/2026-10-16/new-chat/work/sony-a1m2/pydeps')
from elftools.elf.elffile import ELFFile
root=Path('/opt/sony-a7iv/menu-a7m4/runtime/analysis/menu-root/usr/lib')
for name,pattern in [('libObj.so',r'InfraInput.*(C[12]|Init|KeyCode|Convert)|Key.*Code'),('appFw.so',r'NO_MATCH'),('libInfraMediaCommon.so',r'mcmnd_|mcmn_drv_rm_'),('libInfraMediaDetect.so',r'NO_MATCH')]:
 p=root/name;raw=p.read_bytes();elf=ELFFile(io.BytesIO(raw));print('LIB',name)
 for s in elf.get_section_by_name('.dynsym').iter_symbols():
  if s['st_value'] and re.search(pattern,s.name,re.I):print(hex(s['st_value']),hex(s['st_size']),s.name)
 for x in re.finditer(rb'[ -~]{5,}',raw):
  if re.search(rb'convert.*key|key.*convert|get.*key.*code|input.*key.*code|key_tact_(cap|lock)',x[0],re.I):
   if len(x[0])<180:print('STR',hex(x.start()),x[0].decode())
