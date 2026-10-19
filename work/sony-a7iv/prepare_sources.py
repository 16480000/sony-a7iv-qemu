import json
from pathlib import Path
import requests
import shutil
import time

LOCAL = Path(__file__).resolve().parent
DATA = Path('D:/CodexWork/sony-a7iv-qemu')
DATA.mkdir(parents=True, exist_ok=True)
fw = LOCAL / 'BODYDATA.DAT'
if fw.exists() and not (DATA / fw.name).exists():
    shutil.move(str(fw), str(DATA / fw.name))
shutil.copy2(LOCAL / 'firmware_manifest.json', DATA / 'firmware_manifest.json')
repo = 'DavidBuchanan314/Sony-ILCE-7M4-Linux'
r = requests.get(f'https://api.github.com/repos/{repo}/commits/main', timeout=25)
r.raise_for_status()
commit = r.json()['sha']
url = f'https://codeload.github.com/{repo}/tar.gz/{commit}'
dest = DATA / 'sony-linux-source.tar.gz'
print(json.dumps({'repo': repo, 'commit': commit, 'url': url}), flush=True)
(LOCAL / 'source_manifest.json').write_text(json.dumps(dict(repo=repo, commit=commit, url=url), indent=2))
if not dest.exists():
    with requests.get(url, stream=True, timeout=(20, 60)) as r:
        r.raise_for_status()
        last = time.monotonic()
        with dest.with_suffix('.part').open('wb') as out:
            for chunk in r.iter_content(1024*1024):
                out.write(chunk)
                if time.monotonic() - last > 10:
                    print('Kernel source downloaded:', out.tell(), flush=True)
                    last = time.monotonic()
    dest.with_suffix('.part').rename(dest)
print('Kernel source archive bytes:', dest.stat().st_size, flush=True)
