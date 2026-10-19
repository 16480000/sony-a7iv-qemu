"""Repackage original Sony rootfs files plus explicit virtual-board boot glue."""
import gzip
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
import sys
import tarfile

LOCAL = Path(__file__).resolve().parent
PREV = Path('C:/Users/16483/Documents/Codex/2026-10-16/new-chat/work/sony-a1m2')
sys.path.insert(0, str(PREV / 'format-research/fwtool'))
from fwtool.archive import ext2

BASE = Path('D:/CodexWork/sony-a7iv-qemu')
entries = {}
original_files = []
with (BASE / 'unpacked/nflasha7').open('rb') as image:
    for f in ext2.readExt2(image):
        name = f.path.lstrip('/') or '.'
        data = f.contents.read() if stat.S_ISREG(f.mode) or stat.S_ISLNK(f.mode) else b''
        entries[name] = dict(data=data, mode=f.mode, uid=f.uid, gid=f.gid,
                             mtime=f.mtime, rdevmajor=0, rdevminor=0)
        if stat.S_ISREG(f.mode):
            original_files.append(dict(path=f.path, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))

for name in ['proc', 'sys', 'run', 'tmp', 'usr', 'system', 'cp', 'setting', 'log', 'cert', 'lens', 'dev']:
    entries.setdefault(name, dict(data=b'', mode=stat.S_IFDIR|0o755, uid=0, gid=0,
                                  mtime=0, rdevmajor=0, rdevminor=0))
for name, major, minor in [('dev/console', 5, 1), ('dev/null', 1, 3)]:
    entries[name] = dict(data=b'', mode=stat.S_IFCHR|0o600, uid=0, gid=0,
                         mtime=0, rdevmajor=major, rdevminor=minor)
with tarfile.open(BASE / 'unpacked/firmware.tar') as tar:
    for f in tar:
        if f.isfile() and f.name.startswith('0800_appli/setting/'):
            name = f.name.removeprefix('0800_appli/') if hasattr(str, 'removeprefix') else f.name[len('0800_appli/'):]
            if '..' in PurePosixPath(name).parts:
                raise RuntimeError('Unexpected unsafe archive path')
            data = tar.extractfile(f).read()
            entries[name] = dict(data=data, mode=stat.S_IFREG|0o644, uid=0, gid=0,
                                 mtime=0, rdevmajor=0, rdevminor=0)
entries['init'] = dict(data=(LOCAL/'qemu-init').read_bytes().replace(b'\r\n', b'\n'),
                       mode=stat.S_IFREG|0o755, uid=0, gid=0, mtime=0, rdevmajor=0, rdevminor=0)
entries['sbin/qemu-load-ipc'] = dict(data=(LOCAL/'qemu-load-ipc').read_bytes().replace(b'\r\n', b'\n'),
                                   mode=stat.S_IFREG|0o755, uid=0, gid=0, mtime=0, rdevmajor=0, rdevminor=0)

def write_cpio_entry(out, name, e, ino):
    name_b = name.encode('utf-8') + b'\0'
    data = e['data']
    vals = [ino, e['mode'], e['uid'], e['gid'], 1, e['mtime'], len(data),
            0, 0, e['rdevmajor'], e['rdevminor'], len(name_b), 0]
    head = b'070701' + b''.join(f'{v & 0xffffffff:08x}'.encode('ascii') for v in vals)
    out.write(head + name_b)
    out.write(b'\0' * (-(len(head)+len(name_b)) % 4))
    out.write(data)
    out.write(b'\0' * (-len(data) % 4))

dest = BASE / 'qemu-initramfs.cpio.gz'
with dest.open('wb') as raw:
    with gzip.GzipFile(filename='', fileobj=raw, mode='wb', mtime=0) as out:
        for ino, (name, e) in enumerate(entries.items(), 1):
            write_cpio_entry(out, name, e, ino)
        write_cpio_entry(out, 'TRAILER!!!', dict(data=b'',mode=0,uid=0,gid=0,mtime=0,rdevmajor=0,rdevminor=0),len(entries)+1)
manifest = dict(original_rootfs_files=original_files,
                original_regular_files_unchanged=True,
                added_boot_scripts=['/init', '/sbin/qemu-load-ipc'], added_setting_files_from='0800_appli/setting in same official update',
                entry_count=len(entries), bytes=dest.stat().st_size,
                sha256=hashlib.sha256(dest.read_bytes()).hexdigest(),
                note='Derived initramfs. Original Sony /sbin/init is retained but not used as PID 1.')
(BASE/'initramfs-manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps({k:v for k,v in manifest.items() if k!='original_rootfs_files'},indent=2))
