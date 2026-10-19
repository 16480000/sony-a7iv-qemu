"""Decrypt and inventory the official local update; no target code is executed."""
import hashlib
import json
from pathlib import Path
import shutil
import sys
import tarfile
import time

PREVIOUS = Path('C:/Users/16483/Documents/Codex/2026-10-16/new-chat/work/sony-a1m2')
sys.path.insert(0, str(PREVIOUS / 'pydeps'))
sys.path.insert(0, str(PREVIOUS / 'format-research/fwtool'))
from fwtool.sony import dat, fdat

BASE = Path('D:/CodexWork/sony-a7iv-qemu')
OUT = BASE / 'unpacked'
OUT.mkdir(exist_ok=True)

def save(name, obj):
    (OUT / name).write_text(json.dumps(obj, indent=2), encoding='utf-8')

with (BASE / 'BODYDATA.DAT').open('rb') as src:
    package = dat.readDat(src)
    name, plain = fdat.decryptFdat(package.firmwareData)
    print('Outer CRC32 passed; decrypter:', name, flush=True)
    dst = OUT / 'firmware.fdat'
    if not dst.exists():
        with dst.with_suffix('.partial').open('wb') as out:
            last = time.monotonic()
            while True:
                b = plain.read(65536)
                if not b:
                    break
                out.write(b)
                if time.monotonic() - last > 10:
                    print('Decrypted bytes:', out.tell(), flush=True)
                    last = time.monotonic()
        dst.with_suffix('.partial').rename(dst)
    save('decryption.json', dict(decrypter=name, outer_crc32=True,
                                decrypted_bytes=dst.stat().st_size,
                                source_fwtool_commit='3955d7890fc38daf942bb52827599bfe35de4a14'))

with (OUT / 'firmware.fdat').open('rb') as src:
    hdr = fdat.FdatHeader.unpack(src)
    data = fdat.readFdat(src)
    save('fdat-header.json', dict(model=data.model, region=data.region, version=data.version,
                                header_crc32=True, firmware_offset=hdr.firmwareOffset,
                                firmware_size=hdr.firmwareSize, filesystems=hdr.numFileSystems))
    print('FDAT:', data.model, data.region, data.version, flush=True)
    dst = OUT / 'firmware.tar'
    if not dst.exists():
        src.seek(hdr.firmwareOffset)
        with dst.open('xb') as out:
            remaining = hdr.firmwareSize
            while remaining:
                b = src.read(min(8*1024*1024, remaining))
                if not b:
                    raise EOFError('Truncated FDAT')
                out.write(b)
                remaining -= len(b)

inventory = []
with tarfile.open(OUT / 'firmware.tar', 'r:') as tar:
    for member in tar:
        inventory.append(dict(name=member.name, size=member.size, offset=member.offset_data))
        print(member.name, member.size, flush=True)
        if member.isfile() and member.name.startswith('0700_part_image/dev/'):
            dst = OUT / Path(member.name).name
            if not dst.exists():
                with tar.extractfile(member) as f, dst.open('xb') as out:
                    shutil.copyfileobj(f, out, 1024*1024)
save('tar-inventory.json', inventory)
