"""Read kernel wait states only from the exactly named owned secondary VM."""
from pathlib import Path
import os,time,sys
core_frames=sys.argv[1:]==['--core-frames']
assert not sys.argv[1:] or core_frames
name='native-114-abort-origin' if core_frames else 'native-112-diagnostic-audit'
run=Path('/opt/sony-a7iv/menu-a7m4/runs')/name
log=run/'console.log'
deadline=time.monotonic()+300
while time.monotonic()<deadline:
 if log.exists() and b'STORAGE_PROBE_THREAD /proc/' in log.read_bytes():break
 time.sleep(1)
else:raise TimeoutError('Secondary did not reach its thread audit')
parents=[]
for p in Path('/proc').iterdir():
 if not p.name.isdigit():continue
 try:
  argv=(p/'cmdline').read_bytes().split(b'\0')
  if name.encode() in argv and any(x.endswith(b'/native-session.py') for x in argv):parents.append(int(p.name))
 except OSError:pass
assert len(parents)==1,parents
pending=parents[:];qemu=[]
while pending:
 pid=pending.pop();p=Path('/proc')/str(pid)
 try:
  if (p/'comm').read_text().strip()=='qemu':qemu.append(pid)
  pending.extend(map(int,(p/'task'/str(pid)/'children').read_text().split()))
 except FileNotFoundError:pass
assert len(qemu)==1,qemu
command='echo PROBE_KERNEL_BEGIN; for t in /proc/$(pidof im.elf)/task/*; do case "$(cat "$t/comm")" in SeqQueueCommon|SeqQueueDispSwi|CameraBackgroun|AppFw) echo KERNEL_THREAD "$t" "$(cat "$t/comm")"; cat "$t/wchan" "$t/stack" "$t/status";; esac; done; echo PROBE_KERNEL_END\n'
if core_frames:
 command='echo PROBE_KERNEL_BEGIN; for t in /proc/$(pidof im.elf)/task/*; do case "$(cat "$t/comm")" in SeqQueueDispSwi) echo CORE_FRAME_THREAD "$t"; cat "$t/syscall"; set -- $(cat "$t/syscall"); case "$1" in -1) /simulation/menu-readmem /proc/$(pidof im.elf)/mem "$2" 8192;; esac;; esac; done; echo PROBE_KERNEL_END\n'
offset=log.stat().st_size
fd=os.open(f'/proc/{qemu[0]}/fd/0',os.O_WRONLY|os.O_NONBLOCK)
try:assert os.write(fd,command.encode())==len(command)
finally:os.close(fd)
deadline=time.monotonic()+65
while time.monotonic()<deadline:
 with log.open('rb') as reader:reader.seek(offset);raw=reader.read()
 if b'\nPROBE_KERNEL_END\r\n' in raw or b'\nPROBE_KERNEL_END\n' in raw:break
 time.sleep(.2)
else:raise TimeoutError('Read-only kernel audit did not finish')
(run/('core-frame-audit.console' if core_frames else 'kernel-stack-audit.console')).write_bytes(raw)
start=raw.find(b'\nPROBE_KERNEL_BEGIN');print(raw[start:].decode(errors='replace')[-16000:])
