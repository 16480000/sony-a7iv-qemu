import hashlib
import json
from pathlib import Path
import shutil
import subprocess

LOCAL = Path(__file__).resolve().parent
DATA = Path('D:/CodexWork/sony-a7iv-qemu')
OUT = LOCAL.parents[1] / 'outputs/sony-a7iv-qemu'
for name in ['images', 'logs', 'evidence', 'source/patches']:
    (OUT / name).mkdir(parents=True, exist_ok=True)

pairs = [
    (DATA/'Image', OUT/'images/Image'),
    (DATA/'qemu-initramfs.cpio.gz', OUT/'images/qemu-initramfs.cpio.gz'),
    (DATA/'unpacked/nflasha7', OUT/'images/rootfs-original.ext2'),
    (DATA/'unpacked/nflasha15', OUT/'images/usr.ext2'),
    (DATA/'unpacked/nflasha3', OUT/'images/system.vfat'),
    (DATA/'unpacked/nflasha8', OUT/'images/cp.vfat'),
    (DATA/'kernel.config', OUT/'source/kernel.config'),
    (DATA/'System.map', OUT/'source/System.map'),
    (LOCAL/'qemu-init', OUT/'source/qemu-init'),
    (LOCAL/'qemu-load-ipc', OUT/'source/qemu-load-ipc'),
    (DATA/'firmware_manifest.json', OUT/'evidence/firmware_manifest.json'),
    (DATA/'partition-verification.json', OUT/'evidence/partition-verification.json'),
    (DATA/'initramfs-manifest.json', OUT/'evidence/initramfs-manifest.json'),
    (LOCAL/'source_manifest.json', OUT/'evidence/kernel-source.json'),
    (DATA/'unpacked/decryption.json', OUT/'evidence/decryption.json'),
    (DATA/'unpacked/fdat-header.json', OUT/'evidence/fdat-header.json'),
    (DATA/'kernel-build-5.log', OUT/'logs/kernel-build.log'),
    (DATA/'boot-03-4cpu-drives.log', OUT/'logs/raw-rootfs-boot.log'),
    (DATA/'boot-05-original-app.log', OUT/'logs/userspace-and-openssl.log'),
    (DATA/'boot-07-uipc-enabled.log', OUT/'logs/ipc-driver-and-app-attempt.log'),
    (DATA/'boot-08-software-init.log', OUT/'logs/backup-driver-attempt.log'),
    (DATA/'boot-09-original-drivers.log', OUT/'logs/original-driver-hardware-fault.log'),
    (DATA/'boot-10-2mhz.log', OUT/'logs/app-attempt-2mhz.log'),
    (DATA/'boot-11-final-smoke.log', OUT/'logs/final-smoke.log'),
    (DATA/'boot-12-hardware-2mhz.log', OUT/'logs/hardware-driver-2mhz.log'),
]
kernel_copy = Path('//wsl.localhost/Codex-Z8-Qemu/opt/sony-a7iv/src/linux-kernel/COPYING')
if kernel_copy.exists():
    pairs.append((kernel_copy, OUT/'source/COPYING.kernel'))
for path in sorted((DATA/'patches').glob('*.patch')):
    pairs.append((path, OUT/'source/patches'/path.name))
for src, dst in pairs:
    shutil.copy2(src, dst)

def sha(path):
    h=hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda:f.read(8*1024*1024),b''):
            h.update(b)
    return h.hexdigest()
items=[]
for file in sorted((OUT/'images').iterdir()):
    items.append(dict(path=file.relative_to(OUT).as_posix(), bytes=file.stat().st_size, sha256=sha(file)))
qemu=Path('D:/soft/qemu/qemu-system-aarch64.exe')
manifest=dict(model='ILCE-7M4',firmware_version='6.02',
              result='Original user-space runs; full camera boot and menus are not working.',
              original_firmware_kernel_used=False,
              kernel='4.9.337-scel, Sony GPL Ver.6.00 mirror plus recorded patches',
              board='QEMU virt, generated DTB, four Cortex-A35 CPUs, 2 MHz architectural counter, 1024 MiB RAM',
              qemu_version=subprocess.check_output([str(qemu),'--version']).decode(errors='replace').splitlines()[0],
              qemu_sha256=sha(qemu), images=items,
              successful_checks=['Original BusyBox 1.34.1 shell and glibc 2.25',
                                 'Four Cortex-A35 guest CPUs',
                                 'Original /usr, /system, /cp partitions mounted read-only',
                                 'Original OpenSSL 3.0.2 executes',
                                 'Original devno, osal_utm and osal_uipc kernel modules load with status zero'],
              observed_boundaries=['bootin starts im.elf, which faults in MonQueue::GetQueueRemain with a null object',
                                   'The original hardware driver phase faults in pcieatu at virtual address 0xfffffffff7300004'],
              signature_validation='Internal CRC checks passed; Sony digital signature was not independently verified.')
(OUT/'evidence/delivery-manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')
print(json.dumps(dict(output=str(OUT), files=len(pairs), image_bytes=sum(x['bytes'] for x in items), images=items),indent=2))
