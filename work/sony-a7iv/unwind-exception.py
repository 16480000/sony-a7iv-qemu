"""Unwind only bytes actually printed by Sony's guest exception monitor."""
from pathlib import Path
import re,sys
root=Path('/mnt/d/CodexWork/sony-a7iv-qemu/menu-a7m4')
text=(root/sys.argv[1]/'console.log').read_text(errors='replace')
if '[register dump]' not in text:raise SystemExit('No captured exception registers')
text=text[text.index('[register dump]'):]
fp=int(re.search(r'\bfp:\s*0x([0-9a-f]+)',text).group(1),16)
memory={}
for match in re.finditer(r'^0x([0-9a-f]+):\|?\s*0x([0-9a-f]+)\s+0x([0-9a-f]+)',text,re.M):
    addr,a,b=[int(x,16) for x in match.groups()];memory[addr]=a;memory[addr+8]=b
maps=[]
for match in re.finditer(r'^([0-9a-f]+)-([0-9a-f]+) ([-rwx]{3}) 0x([0-9a-f]+)\s*(\S*)',text,re.M):
    start,end,perm,offset,name=match.groups()
    if name:maps.append((int(start,16),int(end,16),int(offset,16),name))
for i in range(64):
    if fp not in memory or fp+8 not in memory:break
    nxt,lr=memory[fp],memory[fp+8];desc='unmapped'
    for start,end,offset,name in maps:
        if start<=lr<end:desc=f'{name}+{lr-start+offset:#x}';break
    print(f'frame{i:02} fp={fp:#x} lr={lr:#x} => {desc}')
    if nxt<=fp or nxt-fp>1048576 or nxt%16:break
    fp=nxt
