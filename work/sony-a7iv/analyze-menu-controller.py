import contextlib
import importlib.util
import io
import json
from pathlib import Path
import sys
sys.path.insert(0,'/usr/lib/python3/dist-packages')
from capstone import Cs,CS_ARCH_ARM64
w=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('c',w/'compare-elf-addresses.py')
m=importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()):spec.loader.exec_module(m)
old,new=m.Elf(m.OLD/'appFw.so'),m.Elf(m.NEW/'appFw.so')
report=m.rtti(old,new,0x5b0c558)
for key,elf,va in [('old',old,0x5b0c558),('new',new,int(report['new_vptrs'][0],16))]:
    report[key]=[hex(elf.q(va+i*8)) for i in range(20)]
    address=elf.q(va+32)
    off=elf.offset(address)
    dis=Cs(CS_ARCH_ARM64,0)
    lines=[f'{x.address:09x}: {x.mnemonic:9} {x.op_str}' for x in dis.disasm(elf.raw[off:off+2000],address)]
    (m.D/f'menu-a7m4/{key}-menu-controller-init.asm').write_text('\n'.join(lines))
print(json.dumps(report,indent=2))
