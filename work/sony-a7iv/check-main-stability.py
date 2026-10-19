"""Observe actual QMP frames across the former one-minute sleep threshold."""
import hashlib,io,json,time,urllib.request
from pathlib import Path
from PIL import Image
out=Path('/mnt/c/Users/16483/Documents/Codex/2026-10-17/new-chat/outputs/sony-a7iv-qemu/native')
url='http://localhost:18764/S5jrCd45BfZKkoQmYa7c0ASfeT12LoLl/frame.png'
expected=Image.open(out/'main-ui.png').convert('RGB').tobytes()
reference=Image.open(out/'main-ui.png').convert('RGB')
regions=[(8,70,60,120),(595,440,640,480)]
start=time.monotonic();samples=[]
print('ACTUAL_QMP_MAIN_STABILITY_STARTED',flush=True)
while True:
 with urllib.request.urlopen(url,timeout=10) as response:raw=response.read()
 frame=Image.open(io.BytesIO(raw)).convert('RGB');data=frame.tobytes()
 assert frame.size==(640,480) and len(set(frame.getdata()))>3,'Original main display went black'
 assert all(frame.crop(region).tobytes()==reference.crop(region).tobytes() for region in regions),'Original camera-mode/touch-frame markers disappeared'
 elapsed=time.monotonic()-start;samples.append({'seconds':round(elapsed,3),'rgb_sha256':hashlib.sha256(data).hexdigest()})
 if elapsed>=105:break
 time.sleep(1)
proof={'run':'native-83-cold-panel','idle_seconds':round(time.monotonic()-start,3),
 'input_sent_during_test':False,'original_main_camera_and_touch_markers_present_every_sample':True,
 'dynamic_ui':'Original NO CARD indicator blinks; some other indicators automatically hide while idle; complete-frame equality is not assumed across time',
 'samples':samples,'original_power_save_setting':'Off','full_camera_boot':False}
(out/'evidence/main-ui-stability-native83.json').write_text(json.dumps(proof,indent=2))
print(json.dumps({k:proof[k] for k in proof if k!='samples'}),flush=True)
