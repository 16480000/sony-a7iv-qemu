"""Read-only diagnostics for the specifically owned virtual-card control probe."""
from pathlib import Path
import json,os,time

base=Path('/mnt/d/CodexWork/sony-a7iv-qemu/menu-a7m4')
state=json.loads((base/'live-panel-18765.json').read_text())
run=Path(state['run']);assert run.name=='native-104-slot2-controls'
parent=int(state['linux_pid'])
args=(Path('/proc')/str(parent)/'cmdline').read_bytes().split(b'\0')
assert run.name.encode() in args and b'--probe-virtual-card' in args
pending=[parent];qemu=[]
while pending:
 pid=pending.pop();p=Path('/proc')/str(pid)
 try:
  if (p/'comm').read_text().strip()=='qemu':qemu.append(pid)
  pending.extend(map(int,(p/'task'/str(pid)/'children').read_text().split()))
 except FileNotFoundError:pass
assert len(qemu)==1,qemu
log=run/'console.log';offset=log.stat().st_size
command='echo CARD_AUDIT_BEGIN; /simulation/headless-osd-export; /bin/busybox sha256sum /image_mmca; for t in /proc/$(pidof im.elf)/task/*; do case "$(cat "$t/comm")" in CameraBackgroun) echo CARD_AUDIT_THREAD "$t"; /simulation/menu-regs "${t##*/}";; esac; done; echo CARD_AUDIT_DONE\n'
fd=os.open(f'/proc/{qemu[0]}/fd/0',os.O_WRONLY|os.O_NONBLOCK)
try:assert os.write(fd,command.encode())==len(command)
finally:os.close(fd)
deadline=time.monotonic()+35
while time.monotonic()<deadline:
 with log.open('rb') as f:f.seek(offset);data=f.read()
 if b'\nCARD_AUDIT_DONE\r\n' in data:break
 time.sleep(.1)
else:raise TimeoutError('Probe read-only audit timed out')
(run/'card-audit.console').write_bytes(data)
for line in data.decode(errors='replace').splitlines():
 if '/image_mmca' in line or line.startswith(('CARD_AUDIT_','REGS','STACK','PC=')):print(line)
