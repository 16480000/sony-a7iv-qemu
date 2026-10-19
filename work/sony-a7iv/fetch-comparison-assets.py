"""Read-only A7C2 comparison ELF assets; never used as A7M4 firmware."""
import hashlib
import json
from pathlib import Path
import requests
import shutil
import sys
import tarfile
import time

PREVIOUS=Path('C:/Users/16483/Documents/Codex/2026-10-16/new-chat/work/sony-a1m2')
sys.path.insert(0,str(PREVIOUS/'pydeps'))
sys.path.insert(0,str(PREVIOUS/'format-research/fwtool'))
from fwtool.sony import dat,fdat
from fwtool.archive.ext2 import readExt2

out=Path('D:/CodexWork/sony-a7iv-qemu/a7c2-reference/comparison-assets')
out.mkdir(exist_ok=True)
api='https://service.sony.com.cn/casch/outDownload'
response=requests.get(api,params={'method':'findOne','path':'/etc/commerce/products/casch/pim/download/firmware/00003056'},timeout=30)
response.raise_for_status()
meta=response.json()
(out/'official-metadata.json').write_text(json.dumps(meta,indent=2),encoding='utf-8')
url=meta['returnData']['Data']['downloadPath'][0]
path=out/'BODYDATA.DAT'
if not path.exists():
    with requests.get(url,stream=True,timeout=(30,60)) as response:
        response.raise_for_status()
        with path.with_suffix('.DAT.part').open('wb') as f:
            for block in response.iter_content(1024*1024): f.write(block)
    path.with_suffix('.DAT.part').replace(path)
assert path.stat().st_size==1139929560
print('DOWNLOADED comparison ILCE-7CM2 2.01',path.stat().st_size,flush=True)
plain=out/'firmware.fdat'
if not plain.exists():
    with path.open('rb') as source:
        package=dat.readDat(source)
        method,stream=fdat.decryptFdat(package.firmwareData)
        with plain.open('wb') as f: shutil.copyfileobj(stream,f,65536)
    print('DECRYPTED',method,flush=True)
with plain.open('rb') as f:
    header=fdat.FdatHeader.unpack(f)
    contents=fdat.readFdat(f)
    assert contents.version=='2.01',contents.version
    f.seek(0)
    raw=f.read(512)
    assert hashlib.sha256(raw).hexdigest()=='ee176eb36cadf11d0f9d02f0829121352fa9d5804932a33831764618c23e8c5e'
    f.seek(header.firmwareOffset)
    tarpath=out/'firmware.tar'
    if not tarpath.exists():
        with tarpath.open('wb') as dst:
            remaining=header.firmwareSize
            while remaining:
                block=f.read(min(1024*1024,remaining));assert block
                dst.write(block);remaining-=len(block)
part=out/'nflasha15'
if not part.exists():
    with tarfile.open(tarpath) as tar, tar.extractfile('0700_part_image/dev/nflasha15') as f, part.open('wb') as dst:
        shutil.copyfileobj(f,dst,1024*1024)
expected={
    '/lib/appFw.so':'2ea02f7ecbc5bb917316fe8ef4ce5ffd87eb66efaae78ba2ce11420552df539b',
    '/lib/libObj.so':'c0897d72a40bf0a161fa7f89e9a34eef4d19e0506c7817a5c11a6f53897cdbbc',
    '/lib/libgpe.so':'80fc6236379933f80c2689aa002e0cf39483da8d45e876705d2a427cd1a2a7d1',
}
manifest={}
with part.open('rb') as f:
    for entry in readExt2(f):
        if entry.path not in expected: continue
        dst=out/Path(entry.path).name
        with dst.open('wb') as target:
            while True:
                block=entry.contents.read(65536)
                if not block: break
                target.write(block)
        actual=hashlib.sha256(dst.read_bytes()).hexdigest()
        assert actual==expected[entry.path],entry.path
        manifest[dst.name]={'sha256':actual,'bytes':dst.stat().st_size}
(out/'elf-provenance.json').write_text(json.dumps({'model':'ILCE-7CM2','version':'2.01','purpose':'static comparison only','url':url,'assets':manifest},indent=2))
print('COMPARISON_ELF_IDENTITIES_PASS',list(manifest),flush=True)
