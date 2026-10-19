"""Resolve the last retained original guest stack for each named probe thread."""
from pathlib import Path
import re,sys
run=Path('/mnt/d/CodexWork/sony-a7iv-qemu/menu-a7m4')/sys.argv[1]
t=(run/'console.log').read_text(errors='replace')
maps=[]
for m in re.finditer(r'^([0-9a-f]+)-([0-9a-f]+) ([-rwxps]{4}) ([0-9a-f]+) \S+ \d+\s+(/\S+)',t,re.M):
 start,end,perm,off,name=m.groups();maps.append((int(start,16),int(end,16),int(off,16),name))
def resolve(value):
 address=int(value,16)
 for start,end,off,name in maps:
  if start<=address<end:return name.rsplit('/',1)[-1]+'+'+hex(address-start+off)
 return hex(address)
names={int(tid):name for tid,name in re.findall(r'STORAGE_PROBE_THREAD /proc/\d+/task/(\d+) ([^\n]+)',t)}
stacks={}
for line in t.splitlines():
 m=re.match(r'REGS tid=(\d+) pc=([0-9a-f]+) lr=([0-9a-f]+)',line)
 if m:
  tid=int(m[1]);stacks[tid]=[resolve(m[2]),resolve(m[3])];continue
 m=re.match(r'FRAME tid=(\d+) .* lr=([0-9a-f]+)',line)
 if m and int(m[1]) in stacks:stacks[int(m[1])].append(resolve(m[2]))
for tid,stack in sorted(stacks.items()):
 if names and tid not in names:continue
 print(str(tid)+' '+names.get(tid,'?')+' | '+' -> '.join(stack))
