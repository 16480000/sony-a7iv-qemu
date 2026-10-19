"""Stage original ILCE-7M4 6.02 assets for the port, separate from A7C2."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import stat
import sys
import tarfile

PREV = Path('/mnt/c/Users/16483/Documents/Codex/2026-10-16/new-chat/work/sony-a1m2')
sys.path.insert(0, str(PREV/'format-research/fwtool'))
sys.path.insert(0, str(PREV/'pydeps'))
from fwtool.archive.ext2 import readExt2
from fwtool.archive.fat import readFat

DATA = Path('/mnt/d/CodexWork/sony-a7iv-qemu')
DEST = Path('/opt/sony-a7iv/menu-a7m4')
REF = DATA/'a7c2-reference/repo/report/2026-10-17-qemu-native-camera'
A = DEST/'runtime/analysis'
ROOT = A/'menu-root'
EXPECTED = {
    'nflasha7': 'a96e69d870c07266551ccd01f13b44f5c53ee1a191eebdf289761c32120d83b8',
    'nflasha15': 'b33408130538b6b34b3fe196d455bfce6f404a207a5567a0ab13e933024c8637',
    'nflasha3': '8f26ffa8792e60436d7d311e3ae089d929c13daf22c76136360e94e51e0c2862',
    'nflasha8': '62d16a76ac949e7f9ec5b9b1a46c7cdc65148b1a169b8d617c83c441d7806aee',
}

def sha(path):
    with path.open('rb') as f:
        return hashlib.file_digest(f, 'sha256').hexdigest()

def install_partition(name, destination, reader):
    source=DATA/'unpacked'/name
    assert sha(source) == EXPECTED[name], name
    destination.mkdir(parents=True, exist_ok=True)
    records=[]
    links=[]
    with source.open('rb') as image:
        for entry in reader(image):
            name=entry.path.lstrip('/')
            if not name or name == '.':
                continue
            assert '..' not in Path(name).parts and not Path(name).is_absolute(), name
            target=destination/name
            mode=entry.mode
            if stat.S_ISDIR(mode):
                target.mkdir(parents=True, exist_ok=True)
            elif stat.S_ISREG(mode):
                target.parent.mkdir(parents=True, exist_ok=True)
                assert not target.is_symlink()
                with target.open('wb') as output:
                    while True:
                        block=entry.contents.read(65536)
                        if not block: break
                        output.write(block)
                target.chmod(stat.S_IMODE(mode))
                records.append({'path':name,'size':target.stat().st_size,'sha256':sha(target)})
            elif stat.S_ISLNK(mode):
                links.append((target, entry.contents.read().decode().rstrip('\0')))
    # Delay guest absolute symlinks until every regular file has been written.
    for target, link in links:
        target.parent.mkdir(parents=True, exist_ok=True)
        if not os.path.lexists(target):
            target.symlink_to(link)
    print('EXTRACTED',source.name,len(records),'regular files',flush=True)
    return records

assert not (DEST/'prepared.json').exists(), 'Staging is already prepared; refusing to overwrite originals'
ROOT.mkdir(parents=True, exist_ok=True)
shutil.copytree(REF/'runtime/analysis', A, dirs_exist_ok=True)
manifest={'model':'ILCE-7M4','version':'6.02','source':'official update only',
          'reference_commit':'25efb56d7f0c69355f9225d1da50454207532e7f','original_partitions':EXPECTED,
          'files':{}}
manifest['files']['root']=install_partition('nflasha7',ROOT,readExt2)
manifest['files']['usr']=install_partition('nflasha15',ROOT/'usr',readExt2)
manifest['files']['system']=install_partition('nflasha3',ROOT/'system',readFat)
manifest['files']['cp']=install_partition('nflasha8',ROOT/'cp',readFat)
for name in ('system','cp','setting','log','cert','lens','tmp','proc','sys','dev','tmp_wbshd','simulation','seed-setting'):
    (ROOT/name).mkdir(exist_ok=True)
with tarfile.open(DATA/'unpacked/firmware.tar') as tar:
    for ent in tar:
        if ent.isfile() and ent.name.startswith('0800_appli/setting/'):
            assert '..' not in Path(ent.name).parts
            dest=ROOT/'seed-setting'/Path(ent.name).name
            dest.write_bytes(tar.extractfile(ent).read())
    seed='0110_backup/SYSIPSX-DSLR/LS/CH89100_ALLLANG.bin'
    data=tar.extractfile(seed).read()
    for name in ('seed-backup.bin','seed-setting/Backup.bin'):
        (ROOT/name).write_bytes(data)
    manifest['backup']={'path':seed,'sha256':hashlib.sha256(data).hexdigest()}
(ROOT/'init').write_text('#!/bin/busybox sh\n/bin/busybox mount -t devtmpfs devtmpfs /dev\nexec /bin/busybox sh </dev/ttyAMA0 >/dev/ttyAMA0 2>&1\n')
(ROOT/'init').chmod(0o755)
manifest['original_libc_matches_reference'] = sha(ROOT/'lib/libc-2.25.so') == 'f9104526eb7e5d2ea533c1a209bb0b83e69367f569e4c966895c8e106e6382c9'
(DEST/'prepared.json').write_text(json.dumps(manifest, indent=2)+'\n')
print('PREPARED A7M4 6.02',len(manifest['files']['usr']),'usr files; glibc match',manifest['original_libc_matches_reference'], flush=True)
