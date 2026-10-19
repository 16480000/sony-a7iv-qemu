import hashlib
import json
import pathlib
import time
import urllib.request

base = pathlib.Path(r'D:\CodexWork\sony-a7iv-qemu')
path = base / 'qemu-11.1.2.tar.xz'
expected = '731b5681e4bb18be313231579b8efd0296c5b015fa36dc533874b639ba838016'
url = 'https://download.qemu.org/qemu-11.1.2.tar.xz'
if not path.exists():
    part = path.with_suffix('.xz.part')
    with urllib.request.urlopen(url, timeout=60) as response, part.open('wb') as output:
        while True:
            data = response.read(1024 * 1024)
            if not data:
                break
            output.write(data)
    part.replace(path)
actual = hashlib.sha256(path.read_bytes()).hexdigest()
if actual != expected:
    raise RuntimeError('QEMU source identity mismatch: ' + actual)
(base / 'qemu-reference-source.json').write_text(json.dumps({
    'url': url, 'sha256': actual, 'bytes': path.stat().st_size,
    'reference_commit': '25efb56d7f0c69355f9225d1da50454207532e7f',
    'checked_at_unix': time.time(),
}, indent=2))
print('Verified', path.stat().st_size, actual, flush=True)
