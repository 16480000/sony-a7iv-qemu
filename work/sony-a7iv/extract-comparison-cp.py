import hashlib
import io
from pathlib import Path
import sys
import tarfile
base=Path('/mnt/d/CodexWork/sony-a7iv-qemu/a7c2-reference/comparison-assets')
vendor=base.parent/'repo/report/2026-10-17-qemu-native-camera/runtime/analysis/vendor/fwtool'
sys.path.insert(0,str(vendor))
from fwtool.archive.fat import readFat
with tarfile.open(base/'firmware.tar') as tar:
    image=tar.extractfile('0700_part_image/dev/nflasha8').read()
assert hashlib.sha256(image).hexdigest()=='8700f570aed3eb32038f313590759736a06162f402637518f8078dd51b6f1541'
for entry in readFat(io.BytesIO(image)):
    if entry.path!='/cpapp-b.bin':continue
    dest=base/'cpapp-b.bin'
    with dest.open('wb') as output:
        while True:
            block=entry.contents.read(65536)
            if not block:break
            output.write(block)
    actual=hashlib.sha256(dest.read_bytes()).hexdigest()
    assert actual=='f5a477588698ef965748903b8959a39ce4f59ffd4aee4d4234ef1670f56a1428'
    print('COMPARISON_CP_VERIFIED',dest.stat().st_size,actual)
