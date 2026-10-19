import hashlib
import json
from pathlib import Path
import sys
import tarfile

prev=Path('C:/Users/16483/Documents/Codex/2026-10-16/new-chat/work/sony-a1m2')
sys.path.insert(0,str(prev/'format-research/fwtool'))
from fwtool.archive import fat
base=Path('D:/CodexWork/sony-a7iv-qemu')
out=base/'boot-original'
out.mkdir(exist_ok=True)
records=[]
with (base/'unpacked/nflasha3').open('rb') as image:
    for f in fat.readFat(image):
        if f.path in ['/vmlinux.bin','/initrd.img']:
            data=f.contents.read()
            dst=out/Path(f.path).name
            dst.write_bytes(data)
            records.append(dict(file=dst.name,size=len(data),sha256=hashlib.sha256(data).hexdigest(),header=data[:64].hex()))
with tarfile.open(base/'unpacked/firmware.tar') as t:
    for name in ['0800_appli/setting/cxd90057.dtb','0800_appli/setting/kemco.txt']:
        data=t.extractfile(name).read();dst=out/Path(name).name;dst.write_bytes(data)
        records.append(dict(file=dst.name,size=len(data),sha256=hashlib.sha256(data).hexdigest()))
(out/'manifest.json').write_text(json.dumps(records,indent=2))
print(json.dumps(records,indent=2))
