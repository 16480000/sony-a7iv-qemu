"""Find relocation-normalized AArch64 instruction matches for manual review."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import struct
import sys
import numpy as np

W=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('comparison',W/'compare-elf-addresses.py')
module=importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()):spec.loader.exec_module(module)
Elf,D,OLD,NEW=module.Elf,module.D,module.OLD,module.NEW

def mask(word):
    if word & 0x7c000000==0x14000000:return 0xfc000000
    if word & 0x7e000000==0x34000000:return 0xff00001f
    if word & 0x7e000000==0x36000000:return 0xfff8001f
    if word & 0xff000010==0x54000000:return 0xff00001f
    if word & 0x1f000000==0x10000000:return 0x9f00001f
    if word & 0x3b000000==0x18000000:return 0xff00001f
    if word & 0x7f000000==0x11000000:return 0xffc003ff
    if word & 0x3b000000==0x39000000:return 0xffc003ff
    return 0xffffffff

def match(old,new,addresses):
    section=new.elf.get_section_by_name('.text')
    words=np.frombuffer(section.data(),dtype='<u4')
    rows=[]
    for address in addresses:
        oldoff=old.offset(address)
        oldwords=struct.unpack_from('<64I',old.raw,oldoff)
        candidates=np.flatnonzero((words & mask(oldwords[0]))==(oldwords[0]&mask(oldwords[0])))
        candidates=candidates[candidates+64<len(words)]
        last=candidates
        chosen=1
        for j in range(1,64):
            candidates=candidates[(words[candidates+j]&mask(oldwords[j]))==(oldwords[j]&mask(oldwords[j]))]
            if not len(candidates):break
            chosen=j+1;last=candidates
        scores=[]
        for i in last[:10000]:
            score=sum((int(words[i+j])&mask(w))==(w&mask(w)) for j,w in enumerate(oldwords))
            scores.append((score,int(i)))
        scores.sort(reverse=True)
        rows.append({'old':hex(address),'prefix_words':chosen,'matches':len(last),
                     'best':[{'new':hex(section['sh_addr']+index*4),'matched_of_64':score,
                              'first16_identical':old.raw[oldoff:oldoff+16]==section.data()[index*4:index*4+16]}
                             for score,index in scores[:5]]})
    return rows

report={}
requested=[(sys.argv[1],[int(x,0) for x in sys.argv[2:]])] if len(sys.argv)>2 else [
    ('libObj.so',[0x100d28,0x104404,0x133cc8,0x130de8,0x130e00,0x100224,0x1027ac]),
    ('appFw.so',[0x1e770e4,0x1e78870,0x1d15858,0x1ac61f8,0x17cdb00])]
for filename,addresses in requested:
    report[filename]=match(Elf(OLD/filename),Elf(NEW/filename),addresses)
(D/('menu-a7m4/function-match-selected.json' if len(sys.argv)>2 else 'menu-a7m4/function-match-candidates.json')).write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
