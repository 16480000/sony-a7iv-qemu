from pathlib import Path
import importlib.util,contextlib,io,sys,re
sys.path.insert(0,'/usr/lib/python3/dist-packages')
from capstone import Cs,CS_ARCH_ARM64
w=Path(__file__).resolve().parent
s=importlib.util.spec_from_file_location('elf',w/'compare-elf-addresses.py');m=importlib.util.module_from_spec(s)
with contextlib.redirect_stdout(io.StringIO()):s.loader.exec_module(m)
r=m.NEW
if len(sys.argv)>1 and sys.argv[1]=='table':
 e=m.Elf(r/sys.argv[2]);a=int(sys.argv[3],0);rows=int(sys.argv[4],0);stride=int(sys.argv[5],0)
 names={sym['st_value']:sym.name for sym in e.elf.get_section_by_name('.dynsym').iter_symbols() if sym['st_value']}
 relocations={}
 for section in e.elf.iter_sections():
  if section['sh_type']!='SHT_RELA':continue
  symbols=e.elf.get_section(section['sh_link'])
  for rel in section.iter_relocations():
   if rel['r_info_sym']:relocations[rel['r_offset']]=symbols.get_symbol(rel['r_info_sym']).name
 for row in range(rows):
  values=[]
  for col in range(0,stride,8):
   v=e.q(a+row*stride+col);label=names.get(v,'')
   if v>0x40000:
    try:label=repr(e.cstr(v))
    except Exception:pass
   values.append((hex(v),relocations.get(a+row*stride+col,label)))
  print(hex(a+row*stride),values)
elif len(sys.argv)>1 and sys.argv[1]=='q':
 e=m.Elf(r/sys.argv[2])
 for text in sys.argv[3:]:
  a=int(text,0);v=e.q(a);print(hex(a),hex(v))
  try:print('STRING',e.cstr(v))
  except Exception:pass
  try:print('RTTI',e.cstr(e.q(e.q(v+8)+8)))
  except Exception:pass
elif len(sys.argv)>1 and sys.argv[1]=='mode':
 e=m.Elf(r/'appFw.so')
 for text in sys.argv[2:]:
  mode=int(text,0);a=0x5118520+mode*96
  print(text,[(hex(a+i),hex(e.q(a+i))) for i in range(0,96,8)])
elif len(sys.argv)>1 and sys.argv[1]=='endpoint':
 import struct
 for p in r.glob('*.so'):
  e=m.Elf(p)
  for seg in e.loads:
   if not(seg['p_flags']&1):continue
   b=e.raw[seg['p_offset']:seg['p_offset']+seg['p_filesz']]
   for i in range(0,len(b)-36,4):
    ins=struct.unpack_from('<I',b,i)[0]
    if ins&0x7f800000!=0x52800000 or (ins>>5)&65535!=0x21f:continue
    reg=ins&31
    for k in range(i+4,i+36,4):
     nxt=struct.unpack_from('<I',b,k)[0]
     if nxt&0x7f800000==0x72800000 and nxt&31==reg and (nxt>>5)&65535==0x8102:
      print('ENDPOINT_BUILDER',p.name,hex(seg['p_vaddr']+i),hex(seg['p_vaddr']+k))
elif len(sys.argv)>1 and sys.argv[1] in ('strings','strings-lib'):
 shift=1 if sys.argv[1]=='strings-lib' else 0
 e=m.Elf(r/(sys.argv[2] if shift else 'appFw.so'));a=int(sys.argv[2+shift],0);n=int(sys.argv[3+shift],0)
 raw=e.raw[e.offset(a):e.offset(a)+n]
 for x in re.finditer(rb'[ -~]{5,}',raw):print(hex(a+x.start()),x.group().decode())
elif len(sys.argv)>1 and sys.argv[1]=='symbols':
 e=m.Elf(r/sys.argv[2]);pattern=sys.argv[3]
 for sym in e.elf.get_section_by_name('.dynsym').iter_symbols():
  if re.search(pattern,sym.name,re.I):print(hex(sym['st_value']),hex(sym['st_size']),sym.name)
elif len(sys.argv)>2:
 e=m.Elf(r/sys.argv[1]);a=int(sys.argv[2],0);n=int(sys.argv[3],0) if len(sys.argv)>3 else 256
 plt=e.elf.get_section_by_name('.plt');rel=e.elf.get_section_by_name('.rela.plt');names={}
 if rel:
  sy=e.elf.get_section(rel['sh_link'])
  names={plt['sh_addr']+32+i*16:sy.get_symbol(x['r_info_sym']).name for i,x in enumerate(rel.iter_relocations())}
 for ins in Cs(CS_ARCH_ARM64,0).disasm(e.raw[e.offset(a):e.offset(a)+n],a):
  dest=int(ins.op_str[1:],16) if ins.mnemonic in ('b','bl') and ins.op_str.startswith('#0x') else 0
  print(f'{ins.address:09x}: {ins.mnemonic:9} {ins.op_str} ; {names.get(dest,"")}')
else:
 for p in r.glob('*.so'):
  b=p.read_bytes();needle=bytes.fromhex('1f020281');off=b.find(needle)
  if off>=0: print('ENDPOINT',p.name,hex(off))
 for n in ['libInfraMediaDetect.so','libInfraMediaCommon.so']:
  e=m.Elf(r/n);print('LIBRARY',n)
  for sym in e.elf.get_section_by_name('.dynsym').iter_symbols():
   if sym['st_value'] or re.search('open|ioctl|read|detect',sym.name,re.I):print(hex(sym['st_value']),hex(sym['st_size']),sym.name)
  for x in re.findall(rb'[ -~]{5,}',e.raw):
   if re.search(rb'/dev|error|fail|detect|insert|slot|card',x,re.I):print(x.decode())
