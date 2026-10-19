import argparse
from pathlib import Path
import re
p=argparse.ArgumentParser()
p.add_argument('run')
p.add_argument('--tid',type=int,default=267)
a=p.parse_args()
root=Path('/mnt/d/CodexWork/sony-a7iv-qemu/menu-a7m4')
text=(root/a.run/'console.log').read_text(errors='replace')
maps=[]
for match in re.finditer(r'^([0-9a-f]+)-([0-9a-f]+) ([-rwxps]{4}) ([0-9a-f]+) \S+ \d+\s+(/\S+)',text,re.M):
    start,end,perm,off,name=match.groups()
    maps.append((int(start,16),int(end,16),int(off,16),name))
for line in text.splitlines():
    if re.search(r'(?:REGS|FRAME) tid='+str(a.tid)+r'\b',line):
        notes=[]
        for field,value in re.findall(r'\b(pc|lr)=([0-9a-f]+)',line):
            address=int(value,16)
            for start,end,offset,name in maps:
                if start<=address<end:
                    notes.append(f'{field}={name}+{address-start+offset:#x}')
                    break
        print(line+' => '+'; '.join(notes))
