"""Serial diagnostics and explicit held-key test for the exact owned A7M4 VM."""
from pathlib import Path
import json,os,sys
state=json.loads(Path('/mnt/d/CodexWork/sony-a7iv-qemu/menu-a7m4/live-panel.json').read_text())
run_name=Path(state['run']).name
assert run_name in {'native-83-cold-panel','native-84-basic-controls','native-87-basic-stable'}
if sys.argv[1:] in [['--input-layout'],['--physical-input-table']]:assert run_name=='native-83-cold-panel','Diagnostic addresses belong only to old83'
parent=int(state['linux_pid']);pending=[parent];found=[]
while pending:
 pid=pending.pop();proc=Path('/proc')/str(pid)
 try:
  args=(proc/'cmdline').read_bytes()
  if pid==parent:assert b'native-session.py' in args and run_name.encode() in args
  if (proc/'comm').read_text().strip()=='qemu':found.append(pid)
  pending.extend(map(int,(proc/'task'/str(pid)/'children').read_text().split()))
 except FileNotFoundError:pass
assert len(found)==1,found
command="echo LIVE_INPUT_STACK_BEGIN; /simulation/menu-readmem /proc/$(pidof im.elf)/mem 0x7f9093d8b0 208; /simulation/menu-readmem /proc/$(pidof im.elf)/mem 0x478760 768; echo LIVE_INPUT_STACK_END\n"
if sys.argv[1:]==['--held-up']:
 command="echo HELD_UP_TEST_BEGIN; /simulation/inject-key 0x807a0020 0x92840747 3 0 1 0 1; sleep 0.3; /simulation/inject-key 0x807a0020 0x92840747 3 0 0 0 1; echo HELD_UP_TEST_END\n"
elif sys.argv[1:]==['--set-on-camera']:
 command="echo FIRSTBOOT_SET_ON_CAMERA_BEGIN; /simulation/inject-key 0x807a0020 0x92840747 0x1f8 0 1 0 1; sleep 0.05; /simulation/inject-key 0x807a0020 0x92840747 0x1f8 0 0 0 1; echo FIRSTBOOT_SET_ON_CAMERA_END\n"
elif sys.argv[1:]==['--export-frame']:
 command="echo LIVE_VERIFIED_FRAME_BEGIN; /simulation/headless-osd-export; echo LIVE_VERIFIED_FRAME_END\n"
elif sys.argv[1:]==['--capture-diagnostics']:
 command='echo CAPTURE_DIAGNOSTICS_BEGIN; for t in /proc/$(pidof im.elf)/task/*; do case "$(cat "$t/comm")" in I-InputEvent|I-InputMain|IMCMN*|IMD-*|CameraBackgroun|IWrapperImaging) echo CAPTURE_THREAD "$t"; cat "$t/comm"; /simulation/menu-regs "${t##*/}" || true;; esac; done; /bin/busybox tail -n 90 /tmp/im.log; /bin/busybox tail -n 90 /tmp/menu-load.log; ls -l /dev/mmc*; echo CAPTURE_DIAGNOSTICS_END\n'
elif sys.argv[1:]==['--input-table']:
 command='echo LIVE_INPUT_TABLE_BEGIN; for t in /proc/$(pidof im.elf)/task/*; do case "$(cat "$t/comm")" in I-InputEvent|I-InputMain) /simulation/input-table "${t##*/}";; esac; done; echo LIVE_INPUT_TABLE_END\n'
elif sys.argv[1:]==['--input-instance']:
 command='echo INPUT_INSTANCE_BEGIN; /simulation/menu-readmem /proc/$(pidof im.elf)/mem 0x2cfea0 8 libObj.so; echo INPUT_INSTANCE_END\n'
elif sys.argv[1:]==['--input-layout']:
 command='echo INPUT_LAYOUT_BEGIN; /simulation/menu-readmem /proc/$(pidof im.elf)/mem 0x474f80 80; echo INPUT_LAYOUT_END\n'
elif sys.argv[1:]==['--physical-input-table']:
 command='echo PHYSICAL_INPUT_TABLE_BEGIN; /simulation/menu-readmem /proc/$(pidof im.elf)/mem 0x478760 1536; echo PHYSICAL_INPUT_TABLE_END\n'
elif sys.argv[1:]==['--shutter']:
 # Original M4 app mapping: 37b1cd0/37b1d40. UIBIZ_CAP ->a7, LOCK ->1f1.
 command='echo NATIVE_SHUTTER_BEGIN; /simulation/inject-key 0x807a0020 0x92840747 0x1f1 0 1 0 1; sleep 0.2; /simulation/inject-key 0x807a0020 0x92840747 0xa7 0 1 0 1; sleep 0.15; /simulation/inject-key 0x807a0020 0x92840747 0xa7 0 0 0 1; /simulation/inject-key 0x807a0020 0x92840747 0x1f1 0 0 0 1; sleep 1; /bin/busybox tail -n 110 /tmp/menu-load.log; echo NATIVE_SHUTTER_END\n'
elif sys.argv[1:]==['--backup-status']:
 command='echo BACKUP_STATUS_BEGIN; ls -l /sys/module/backup/parameters; for f in /sys/module/backup/parameters/*; do echo "$f"; cat "$f"; done; ls -l /setting/Backup.bin; echo BACKUP_STATUS_END\n'
elif sys.argv[1:]==['--backup-reset-save']:
 command='echo 0 >/sys/module/backup/parameters/Backup_save; echo BACKUP_SAVE_RESET; cat /sys/module/backup/parameters/Backup_save\n'
elif sys.argv[1:]:raise ValueError('Unsupported owned guest diagnostic')
if not sys.argv[1:]:
 command='echo LIVE_INPUT_THREADS_BEGIN; for t in /proc/$(pidof im.elf)/task/*; do case "$(cat "$t/comm")" in I-InputMain|I-InputEvent|AppFw) echo INPUT_THREAD "$t"; /simulation/menu-regs "${t##*/}";; esac; done; echo LIVE_INPUT_THREADS_END\n'
fd=os.open(f'/proc/{found[0]}/fd/0',os.O_WRONLY|os.O_NONBLOCK)
try:assert os.write(fd,command.encode())==len(command)
finally:os.close(fd)
print('OWNED_GUEST_READ_REQUESTED',found[0])

