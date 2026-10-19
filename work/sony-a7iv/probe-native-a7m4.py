import argparse
import json
import os
from pathlib import Path
import signal
import subprocess
import time

p=argparse.ArgumentParser()
p.add_argument('--name',default='native-01')
p.add_argument('--seconds',type=int,default=75)
p.add_argument('--initramfs',default='bootstrap.cpio')
p.add_argument('--cpu',default='cortex-a35,cntfrq=2000000')
p.add_argument('--ramfb',action='store_true')
args=p.parse_args()
base=Path('/mnt/d/CodexWork/sony-a7iv-qemu')
data=base/'menu-a7m4'
evidence_out=data/args.name
out=Path('/opt/sony-a7iv/menu-a7m4/runs')/args.name
out.parent.mkdir(exist_ok=True)
out.mkdir(exist_ok=False)
shutil_copy=__import__('shutil').copyfile
shutil_copy(data/'virt.dtb',out/'virt.dtb')
qemu=Path('/opt/sony-a7iv/qemu-menu-build/qemu-system-aarch64')
kernel=base/'boot-original/vmlinux.bin'
image=data/args.initramfs
assert qemu.is_file() and image.is_file() and kernel.is_file()
command=['bwrap','--unshare-all','--die-with-parent','--new-session','--clearenv',
 '--ro-bind','/usr','/usr','--symlink','usr/lib','/lib','--symlink','usr/lib64','/lib64',
 '--proc','/proc','--dev','/dev','--tmpfs','/tmp','--ro-bind',str(qemu),'/qemu',
 '--ro-bind',str(kernel),'/kernel.img','--ro-bind',str(image),'/initrd.img',
 '--bind',str(out),'/out','--chdir','/','--setenv','QEMU_SONY_TIMERS','1',
 '/qemu','-object','memory-backend-ram,id=sony-ram,size=24G,reserve=off',
 '-machine','virt,secure=off,gic-version=2,memory-backend=sony-ram','-cpu',args.cpu,'-smp','1','-m','24576',
 '-nodefaults','-display','none','-monitor','none','-serial','stdio','-nic','none','-no-reboot','-sandbox','on',
 '-qmp','unix:/out/qmp.sock,server=on,wait=off',
 '-device','loader,file=/out/virt.dtb,addr=0x400002000',
 '-device','loader,file=/kernel.img,addr=0x400080000,force-raw=on',
 '-device','loader,file=/initrd.img,addr=0x440000000,force-raw=on',
 '-device','loader,addr=0x400080000,cpu-num=0',
 '-kernel','/kernel.img','-initrd','/initrd.img',
 '-d','cpu_reset,guest_errors,unimp','-D','/out/boot-trace.log']
if args.ramfb:command+=['-device','ramfb,id=a7m4-screen']
(out/'command.json').write_text(json.dumps(command,indent=2))
start=time.monotonic()
with (out/'console.log').open('wb') as log:
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT)
    limited=False
    try:
        try:
            process.wait(timeout=min(args.seconds,12))
        except subprocess.TimeoutExpired:
            helper=Path(__file__).with_name('snapshot-qmp.py')
            subprocess.run(['python3',str(helper),args.name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,timeout=8)
            process.wait(timeout=max(1,args.seconds-(time.monotonic()-start)))
    except subprocess.TimeoutExpired:
        limited=True
        process.terminate()
        try: process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill(); process.wait()
text=(out/'console.log').read_text(errors='replace')
status={'elapsed_seconds':round(time.monotonic()-start,3),'bounded_observation_ended':limited,
 'returncode':process.returncode,'serial_bytes':len(text),
 'bootstrap_complete':'A7M4_BOOTSTRAP_DONE' in text,
 'backup_loaded':'BACKUP_MODULE_STATUS=0' in text,
 'app_init_entered':'APP_INIT_ENTER' in text or 'OBS ENTER Application_System_Init' in text,
 'dynamic_link_error':'symbol lookup error:' in text,
 'exception':any(marker in text for marker in ('Exception monitor:','Entering exception monitor.','[register dump]','Kernel panic'))}
(out/'result.json').write_text(json.dumps(status,indent=2))
evidence_out.mkdir(exist_ok=True)
for path in out.iterdir():
    if path.is_file(): shutil_copy(path,evidence_out/path.name)
print(json.dumps({'run':str(out),**status},indent=2),flush=True)
