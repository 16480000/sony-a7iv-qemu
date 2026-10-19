import csv
import hashlib
import io
import json
from pathlib import Path
import tarfile
import zlib

BASE = Path('D:/CodexWork/sony-a7iv-qemu')
UNPACKED = BASE / 'unpacked'
with tarfile.open(UNPACKED / 'firmware.tar', 'r:') as tar:
    rows = list(csv.reader(io.StringIO(tar.extractfile('0701_part_image_sum/part_image.sum').read().decode('ascii'))))
checks = []
for row in rows:
    if row[0] != '0':
        continue
    name = Path(row[10]).name
    path = UNPACKED / name
    crc = 0
    sha = hashlib.sha256()
    with path.open('rb') as f:
        for chunk in iter(lambda: f.read(8*1024*1024), b''):
            crc = zlib.crc32(chunk, crc)
            sha.update(chunk)
    expected_crc = int(row[1], 16)
    expected_bytes = int(row[2], 16)
    ok = crc == expected_crc and path.stat().st_size == expected_bytes
    checks.append(dict(file=name, bytes=path.stat().st_size, expected_bytes=expected_bytes,
                       crc32=f'{crc:08x}', expected_crc32=f'{expected_crc:08x}',
                       sha256=sha.hexdigest(), passed=ok))
    if not ok:
        raise RuntimeError('Partition checksum or length mismatch: ' + name)
(BASE / 'partition-verification.json').write_text(json.dumps(checks, indent=2))
print(json.dumps(checks, indent=2))
