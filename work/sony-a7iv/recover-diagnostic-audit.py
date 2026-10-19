"""Recover native115's export using only identified asynchronous transport noise."""
from pathlib import Path
import base64,hashlib,json,re,struct
from native_frame import clean_native_export
run=Path('/mnt/d/CodexWork/sony-a7iv-qemu/menu-a7m4/native-115-evf-priority')
raw=(run/'diagnostic-export.console').read_bytes();clean,removed=clean_native_export(raw)
m=re.search(rb'\nA7M4_DIAG_BEGIN\n([A-Za-z0-9+/=\n]+)A7M4_DIAG_END',clean)
assert m,'Unrecognized data remains; do not repair encoded bytes'
b=base64.b64decode(re.sub(rb'\s',b'',m[1]),validate=True)
at=0;count=0
while at<len(b):
 assert len(b)-at>=4
 size=struct.unpack_from('<I',b,at)[0];at+=4
 assert 33<=size<=4096 and size<=len(b)-at
 kind,command,category,length=struct.unpack_from('<HHII',b,at)
 assert (kind,command)==(2,0x83) and length==size-32
 at+=size;count+=1
summary=re.search(rb'DIAGNOSTIC_SNAPSHOT total=(\d+) records=(\d+) exported_records=(\d+) exported_bytes=(\d+) sha256=([0-9a-f]{64})',clean)
assert summary and int(summary[3])==count and int(summary[4])==len(b)
(run/'diagnostic-events.bin').write_bytes(b)
result={'raw_console_sha256':hashlib.sha256(raw).hexdigest(),'identified_noise_records_removed':removed,'sample_bytes':len(b),'sample_records':count,'sample_sha256':hashlib.sha256(b).hexdigest(),'full_guest_stream_bytes':int(summary[1]),'full_guest_stream_records':int(summary[2]),'full_guest_stream_sha256':summary[5].decode(),'sample_sha256_independently_reported_by_old_guest_exporter':False,'limitation':'Old exporter supplied only full-stream SHA; this recovered tail sample passes every record bound/header and the original record/byte counts. The source log and original failed result remain unchanged.'}
(run/'diagnostic-recovery.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result))
