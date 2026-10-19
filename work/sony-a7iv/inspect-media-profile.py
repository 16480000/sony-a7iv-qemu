import importlib.util,contextlib,io,struct
from pathlib import Path
w=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('elf',w/'compare-elf-addresses.py');m=importlib.util.module_from_spec(s)
with contextlib.redirect_stdout(io.StringIO()):s.loader.exec_module(m)
e=m.Elf(m.NEW/'libInfraMediaCommon.so')
for index in range(0x110):
 a=0x6c638+index*32
 name=e.cstr(e.q(a))
 if 'DUMMY' in name or index in [0x69,0xa2,0xa3,0xa4,0xd2,0xf5,0xf6]:
  print('PARAMETER',hex(index),name,[hex(e.q(a+n)) for n in [8,16,24]])
for n in range(300):
 a=0x69de8+n*32
 try:
  name=e.cstr(e.q(a));image=e.cstr(e.q(a+8))
 except (ValueError,UnicodeDecodeError):break
 if 'rm' in name or n<2:print('DUMMY_DEVICE',hex(a),name,image,hex(e.q(a+16)),hex(e.q(a+24)))
 if not name:break
for needle in [b'/nondev/rm1\0',b'/nondev/rm2\0',b'/nondev/rm3\0']:
 pos=e.raw.find(needle)
 if pos>=0:
  address=e.va(pos);print('NATIVE_DEVICE',needle.decode(),hex(address))
  for x in e.references(address):print('DEVICE_REF',hex(x),[hex(e.q(x+k)) for k in range(-8,40,8)])
