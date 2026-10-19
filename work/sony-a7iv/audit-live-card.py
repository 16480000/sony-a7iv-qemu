"""Read-only card, retention and AP/HTTP display audit of the exact live primary."""
from pathlib import Path
import argparse,hashlib,io,json,os,re,secrets,sys,time,urllib.request
sys.path.insert(0,'/opt/sony-a7iv/menu-a7m4/runtime/analysis')
from headless_osd_capture import capture
from native_frame import clean_native_export
from PIL import Image
p=argparse.ArgumentParser();p.add_argument('label',choices=['before-restart','after-restart']);a=p.parse_args()
b=Path('/mnt/d/CodexWork/sony-a7iv-qemu/menu-a7m4')
state=json.loads((b/'live-panel.json').read_text());run=Path(state['run'])
assert run.name=='native-117-card-main' and state['url']=='http://localhost:18764/S5jrCd45BfZKkoQmYa7c0ASfeT12LoLl/'
parent=int(state['linux_pid']);argv=(Path('/proc')/str(parent)/'cmdline').read_bytes().split(b'\0')
assert run.name.encode() in argv and b'--card-main' in argv and any(x.endswith(b'/native-session.py') for x in argv)
pending=[parent];qemu=[]
while pending:
 pid=pending.pop();proc=Path('/proc')/str(pid)
 try:
  if (proc/'comm').read_text().strip()=='qemu':qemu.append(pid)
  pending.extend(map(int,(proc/'task'/str(pid)/'children').read_text().split()))
 except FileNotFoundError:pass
assert len(qemu)==1,qemu
marker='LIVE_CARD_AUDIT_DONE_'+secrets.token_hex(12)
command='LD_BIND_NOW=1 /simulation/card-audit; echo CARD_HEALTH_RC=$?; ls -ln /tmp/a7m4-diagnostic-events*.bin; for t in /proc/$(pidof im.elf)/task/*; do case "$(cat "$t/comm")" in AppFw|SeqQueueDispSwi) echo LIVE_HEALTH_THREAD "$t" "$(cat "$t/comm")"; cat "$t/wchan";; esac; done; /simulation/headless-osd-export; echo '+marker+'\n'
log=run/'console.log';offset=log.stat().st_size
fd=os.open(f'/proc/{qemu[0]}/fd/0',os.O_WRONLY|os.O_NONBLOCK)
try:assert os.write(fd,command.encode())==len(command)
finally:os.close(fd)
deadline=time.monotonic()+60
while time.monotonic()<deadline:
 with log.open('rb') as reader:reader.seek(offset);raw=reader.read()
 if b'\n'+marker.encode()+b'\r\n' in raw or b'\n'+marker.encode()+b'\n' in raw:break
 time.sleep(.1)
else:raise TimeoutError('Owned live read-only audit did not finish')
out=run/('live-audit-'+a.label);out.mkdir(exist_ok=False)
(out/'console.log').write_bytes(raw)
clean,noise=clean_native_export(raw)
assert b'CARD_HEALTH_RC=0' in clean and b'CARD_AUDIT_DONE result=0' in clean
assert b'do_coredump' not in clean and b'stop_all_threads_timeout' not in clean
info=capture(clean,out)
pixels=(out/'headless-osd-pixels.bin').read_bytes();rgb=bytearray(640*480*3)
for i in range(640*480):
 v=pixels[2*i]|pixels[2*i+1]<<8;alpha=v&15
 rgb[3*i:3*i+3]=bytes([((v>>12)*17*alpha+7)//15,(((v>>8)&15)*17*alpha+7)//15,(((v>>4)&15)*17*alpha+7)//15])
png=urllib.request.urlopen(state['url']+'frame.png',timeout=5).read()
actual=Image.open(io.BytesIO(png)).convert('RGB');(out/'http-frame.png').write_bytes(png)
assert actual.size==(640,480) and actual.tobytes()==rgb,'Current HTTP/QMP pixels differ from verified AP snapshot'
digest=re.search(rb'CARD_AUDIT_SHA256 bytes=67108864 digest=([0-9a-f]{64})',clean);assert digest
segments=[{'bytes':int(n),'path':name.decode()} for n,name in re.findall(rb'^[-rwx]{10}\s+\d+\s+\d+\s+\d+\s+(\d+)\s+[^\n]+? (/tmp/a7m4-diagnostic-events[^ \r\n]*\.bin)\r?$',clean,re.M)]
assert 1<=len(segments)<=2 and all(x['bytes']<=8388608 for x in segments),segments
result={'run':run.name,'phase':a.label,'url':state['url'],'qemu_pid':qemu[0],'card_sha256':digest[1].decode(),'card_file_records':[x.decode() for x in clean.splitlines() if x.startswith(b'CARD_AUDIT_FILE ')],'diagnostic_segments':segments,'http_frame_matches_original_ap_rgb':True,'frame_pixel_sha256':hashlib.sha256(rgb).hexdigest(),'original_ap_snapshot':info,'identified_async_records_removed':noise,'audit_console_sha256':hashlib.sha256(raw).hexdigest(),'photography_implemented':False}
(out/'audit.json').write_text(json.dumps(result,indent=2))
dest=Path(__file__).resolve().parent.parent.parent/'outputs/sony-a7iv-qemu/native/evidence'
(dest/('live117-'+a.label+'-audit.json')).write_text(json.dumps(result,indent=2))
(dest/('live117-'+a.label+'-verified.png')).write_bytes(png)
print(json.dumps(result,ensure_ascii=False))
