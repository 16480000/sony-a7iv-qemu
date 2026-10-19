import contextlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import numpy as np

W=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('comparison',W/'compare-elf-addresses.py')
mod=importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()):spec.loader.exec_module(mod)
Elf=mod.Elf
report={}
for model,path,ctor,base,maxid in [('C2',mod.OLD/'appFw.so',0x1d15858,0x51f7810,0x4b7),('M4',mod.NEW/'appFw.so',0x1dc7504,None,0x4cf)]:
    elf=Elf(path)
    if base is None:base=elf.q(0x59e0668)
    sec=elf.elf.get_section_by_name('.text')
    a=np.frombuffer(sec.data(),dtype='<u4').astype(np.int64)
    idx=np.flatnonzero((a&0x7c000000)==0x14000000)
    imm=a[idx]&0x3ffffff
    rel=np.where(imm&(1<<25),imm-(1<<26),imm)*4
    target=sec['sh_addr']+idx*4+rel
    calls=[int(x) for x in sec['sh_addr']+idx[target==ctor]*4]
    rows=[]
    for i in range(maxid+1):
        try:
            presenter,controller=elf.q(base+i*96),elf.q(base+i*96+8)
            if any(controller<=c<controller+1024 for c in calls):
                rows.append({'mode':hex(i),'presenter':hex(presenter),'controller_factory':hex(controller),
                             'nearby_ctor_calls':[hex(c) for c in calls if controller<=c<controller+1024]})
        except ValueError:break
    report[model]={'factory_table':hex(base),'ctor':hex(ctor),'callers':[hex(c) for c in calls],'candidates':rows}
(mod.D/'menu-a7m4/menu-factory-comparison.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
