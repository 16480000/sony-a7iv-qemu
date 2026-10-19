import hashlib
import json
from pathlib import Path
import time

import requests

BASE = Path(__file__).resolve().parent
META = json.loads((BASE / 'download-metadata.json').read_text(encoding='utf-8'))
URL = META['returnData']['Data']['downloadPath'][0]
EXPECTED = 757480856
DEST = BASE / 'BODYDATA.DAT'
PART = BASE / 'BODYDATA.DAT.part'

if not DEST.exists():
    for attempt in range(5):
        offset = PART.stat().st_size if PART.exists() else 0
        try:
            headers = {'Range': f'bytes={offset}-'} if offset else {}
            with requests.get(URL, headers=headers, stream=True, timeout=(20, 45)) as r:
                r.raise_for_status()
                if offset and r.status_code != 206:
                    raise RuntimeError('Server did not honor resume; partial file preserved')
                print(json.dumps({'url': r.url, 'status': r.status_code,
                                  'resume_offset': offset}), flush=True)
                last = time.monotonic()
                with PART.open('ab' if offset else 'wb') as out:
                    for chunk in r.iter_content(1024 * 1024):
                        out.write(chunk)
                        offset += len(chunk)
                        if time.monotonic() - last >= 10:
                            print(f'Downloaded {offset:,}/{EXPECTED:,} ({offset/EXPECTED:.1%})', flush=True)
                            last = time.monotonic()
            if offset != EXPECTED:
                raise RuntimeError(f'Size mismatch: {offset} != {EXPECTED}')
            PART.rename(DEST)
            break
        except Exception as e:
            print(f'Attempt {attempt + 1}: {e}', flush=True)
            if attempt == 4:
                raise

if DEST.stat().st_size != EXPECTED:
    raise RuntimeError('Completed file size does not match official file size')
h = hashlib.sha256()
with DEST.open('rb') as f:
    for chunk in iter(lambda: f.read(8 * 1024 * 1024), b''):
        h.update(chunk)
manifest = dict(model='ILCE-7M4', version='6.02', release_date='2026-05-28',
                source_page='https://service.sony.com.cn/download/firm/00003010.html',
                download_url=URL, size=EXPECTED, sha256=h.hexdigest(),
                verification='HTTPS and official byte count. SHA-256 computed locally; no Sony-published digest or signature verified.')
(BASE / 'firmware_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
print(json.dumps(manifest), flush=True)
