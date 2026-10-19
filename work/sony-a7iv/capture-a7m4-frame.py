import json
from pathlib import Path
import sys
import re
sys.path.insert(0,'/opt/sony-a7iv/menu-a7m4/runtime/analysis')
from headless_osd_capture import capture,HEADER,METADATA
from PIL import Image
from native_frame import clean_native_export

run=Path('/mnt/d/CodexWork/sony-a7iv-qemu/menu-a7m4')/sys.argv[1]
console=(run/'console.log').read_bytes().replace(b'\r\n',b'\n')
end=console.rfind(b'\nHEADLESS_OSD_END')
start=console.rfind(b'HEADLESS_OSD_BEGIN\n',0,end)
if start<0 or end<start:raise ValueError('No completed original snapshot export')
console=console[start:end+len(b'\nHEADLESS_OSD_END')]
# These forwarding diagnostics share the console with the base64 transfer.
# Remove their complete, identified records only; the original decoder still
# verifies exact container length, identity and the checksum over all bytes.
console,noise_records=clean_native_export(console)
info=capture(console,run)
info['observer_records_removed']=noise_records
pixels=(run/'headless-osd-pixels.bin').read_bytes()
rgba=bytearray(640*480*4)
colors=set()
for j in range(640*480):
    v=pixels[j*2]|pixels[j*2+1]<<8
    color=((v>>12)*17,((v>>8)&15)*17,((v>>4)&15)*17,(v&15)*17)
    colors.add(color)
    rgba[j*4:j*4+4]=bytes(color)
image=Image.frombytes('RGBA',(640,480),bytes(rgba))
image.save(run/'frame-rgba4444.png')
black=Image.new('RGBA',image.size,(0,0,0,255))
black.alpha_composite(image)
black.convert('RGB').save(run/'frame-on-black.png')
info['distinct_rgba_colors']=len(colors)
info['nonempty_raster']=len(colors)>2
(run/'validated-frame.json').write_text(json.dumps(info,indent=2))
print(json.dumps({'run':str(run),'sequence':info['sequence'],'pixel_source_seq':info['pixel_source_seq'],'distinct_rgba_colors':len(colors),'snapshot_sha256':info['sha256']},indent=2))
