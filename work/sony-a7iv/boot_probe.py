"""Boot a serial-only, network-disabled virtual machine and retain real UART output."""
import argparse
import json
from pathlib import Path
import subprocess
import threading
import time

BASE = Path('D:/CodexWork/sony-a7iv-qemu')
parser = argparse.ArgumentParser()
parser.add_argument('--seconds', type=int, default=35)
parser.add_argument('--name', default='boot-probe')
parser.add_argument('--generic-dtb', action='store_true')
parser.add_argument('--cpu', default='cortex-a53')
parser.add_argument('--smp', default='1')
parser.add_argument('--drives', action='store_true')
parser.add_argument('--initramfs', action='store_true')
parser.add_argument('--commands')
args = parser.parse_args()
image = BASE / 'Image'
initrd = BASE / ('qemu-initramfs.cpio.gz' if args.initramfs else 'unpacked/nflasha7')
append = 'earlycon=pl011,0x09000000 console=ttyAMA0,115200 loglevel=7 root=/dev/ram0 rootfstype=ext2 ramdisk_size=65536 rw init=/bin/sh panic=-1'
if args.initramfs:
    append = 'earlycon=pl011,0x09000000 console=ttyAMA0,115200 loglevel=6 rdinit=/init panic=-1'
command = [r'D:\soft\qemu\qemu-system-aarch64.exe',
           '-M', 'virt,gic-version=2,highmem=off', '-cpu', args.cpu,
           '-smp', args.smp, '-m', '1024', '-kernel', str(image),
           '-initrd', str(initrd), '-append', append,
           '-display', 'none', '-serial', 'stdio', '-monitor', 'none',
           '-nic', 'none', '-no-reboot']
if not args.generic_dtb:
    command.extend(['-dtb', str(BASE / 'qemu.dtb')])
if args.drives:
    for ident, partition in [('A7IV_USR', 'nflasha15'), ('A7IV_SYSTEM', 'nflasha3'), ('A7IV_CP', 'nflasha8')]:
        command.extend(['-drive', f'if=none,id={ident},file={BASE / "unpacked" / partition},format=raw,readonly=on',
                        '-device', f'virtio-blk-device,drive={ident},serial={ident}'])
(BASE / (args.name + '-command.json')).write_text(json.dumps(command, indent=2))
log_path = BASE / (args.name + '.log')
proc = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT, bufsize=0)
chunks = []
with log_path.open('wb') as log:
    def read_output():
        while True:
            b = proc.stdout.read(1024)
            if not b:
                break
            chunks.append(b)
            log.write(b)
            log.flush()
    reader = threading.Thread(target=read_output, daemon=True)
    reader.start()
    start = time.monotonic()
    sent = False
    while proc.poll() is None and time.monotonic() - start < args.seconds:
        data = b''.join(chunks)
        if b'Entering exception monitor.' in data:
            break
        if not sent and (b'job control' in data or b'/bin/sh:' in data or b'BusyBox' in data):
            time.sleep(0.4)
            probe = Path(args.commands).read_bytes() if args.commands else b"echo A7IV_FIRMWARE_SHELL_RUNNING; /bin/busybox; mount -t proc proc /proc; cat /proc/version; cat /proc/cpuinfo; echo A7IV_PROBE_DONE\n"
            for byte in probe:
                proc.stdin.write(bytes([byte]))
                proc.stdin.flush()
                time.sleep(0.012)
            sent = True
        if b'A7IV_PROBE_DONE' in data.replace(b'\r', b'').split(b'\n') and b'Linux version' in data and sent:
            time.sleep(0.5)
            break
        time.sleep(0.1)
    if proc.poll() is None:
        proc.terminate()
    try:
        proc.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait()
    reader.join(timeout=3)
data = b''.join(chunks)
print(json.dumps(dict(command=command, log=str(log_path), bytes=len(data),
                      returncode=proc.returncode, sent_probe=sent,
                      shell_marker=b'A7IV_FIRMWARE_SHELL_RUNNING\r\n' in data)))
print(data.decode('utf-8', errors='replace')[-13000:])
