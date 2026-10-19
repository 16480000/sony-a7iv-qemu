import io,sys,struct
from pathlib import Path
sys.path.insert(0,'/mnt/c/Users/16483/Documents/Codex/2026-10-16/new-chat/work/sony-a1m2/pydeps')
from elftools.elf.elffile import ELFFile
p=Path('/opt/sony-a7iv/menu-a7m4/runtime/analysis/menu-root/usr/lib/appFw.so');b=p.read_bytes();e=ELFFile(io.BytesIO(b))
def va(off):
 for s in e.iter_segments():
  if s['p_type']=='PT_LOAD' and s['p_offset']<=off<s['p_offset']+s['p_filesz']:return s['p_vaddr']+off-s['p_offset']
def offset(address):
 for s in e.iter_segments():
  if s['p_type']=='PT_LOAD' and s['p_vaddr']<=address<s['p_vaddr']+s['p_filesz']:return s['p_offset']+address-s['p_vaddr']
for table in [0x37af958,0x37b1c58]:
 for address in range(table,table+0x2300,8):
  key,value=struct.unpack_from('<II',b,offset(address))
  if key in [0xf,0x10,0x1d,0x1e,0x13,0x14,0x22,0x8d,0x24,0x87,0x88] or value in [1,2,0x1ab,0x1ac]:
   print('ORIGINAL_KEY_MAP',hex(address),hex(key),hex(value))
for address in range(0x37b41a8,0x37b41a8+0x43c*12,12):
 key,event,status=struct.unpack_from('<III',b,offset(address))
 if key in [0xa7,0x1f1,0x1ab,0x1ac,1,2]:print('AP_KEY_SUBSCRIPTION',hex(address),hex(key),hex(event),hex(status))
for address in range(0x5832e58,0x5832e58+0x200,16):
 idx,code,ptr=struct.unpack_from('<IIQ',b,offset(address))
 try:
  at=offset(ptr);name=b[at:b.index(0,at)].decode()
  if name.startswith('UIBIZ_'):print('KEYTABLE',hex(address),hex(idx),hex(code),name)
 except (TypeError,ValueError,UnicodeDecodeError):pass
for name in [b'UIBIZ_KEY_RELEASE_CAP',b'UIBIZ_KEY_RELEASE_LOCK',b'UIBIZ_KEY_MENU',b'UIBIZ_KEY_DELETE']:
 off=b.find(name+b'\0')
 if off<0:continue
 address=va(off);print(name.decode(),hex(address));needle=struct.pack('<Q',address);at=0
 while True:
  at=b.find(needle,at)
  if at<0:break
  print('REF',hex(va(at)), ' '.join(f'{n:x}' for n in struct.unpack('<16I',b[at-24:at+40])));at+=8


