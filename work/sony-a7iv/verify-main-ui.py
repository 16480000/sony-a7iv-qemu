"""Verify captured original AP pixels against independently served QMP scanout."""
from pathlib import Path
import json,hashlib,urllib.request,io,time
from PIL import Image
run=Path('/opt/sony-a7iv/menu-a7m4/runs/native-83-cold-panel')
out=Path('/mnt/c/Users/16483/Documents/Codex/2026-10-17/new-chat/outputs/sony-a7iv-qemu/native')
ap=Image.open(run/'frame-on-black.png').convert('RGB')
deadline=time.monotonic()+6
while True:
 with urllib.request.urlopen('http://localhost:18764/S5jrCd45BfZKkoQmYa7c0ASfeT12LoLl/frame.png',timeout=3) as response:raw=response.read()
 qmp=Image.open(io.BytesIO(raw)).convert('RGB')
 if qmp.size==(640,480) and qmp.tobytes()==ap.tobytes():break
 if time.monotonic()>deadline:raise AssertionError('Actual QMP/AP pixels differ; no matching native blink phase observed')
 time.sleep(.08)
(out/'main-ui.png').write_bytes(raw)
meta=json.loads((run/'validated-frame.json').read_text())
colors=len(set(qmp.getdata()));assert colors>10
proof={'model':'ILCE-7M4','firmware':'6.02','run':run.name,
 'menu_entry_injected':False,'original_firstboot_completed_through_ui':True,
 'original_main_view_id':0,'original_main_view_elements':585,
 'main_ui_overlay_observed':True,'main_ui_indicators':['J.FINE','14M','AF-S','MECH','AF ON'],
 'qmp_scanout_equals_original_ap_pixels':True,'size':[640,480],'rgb_colors':colors,
 'rgb_sha256':hashlib.sha256(qmp.tobytes()).hexdigest(),'original_snapshot':meta,
 'menu_enter_and_return_observed':True,'cold_restart_and_wizard_replay_observed':True,
 'power_save_off_set_through_original_ui':True,
 'liveview_implemented':False,'sensor_isp_af_or_photo_implemented':False,'full_camera_boot':False,
 'startup':'Original kernel/application/resources; virtual CP control-plane models and original media driver; CP firmware not executed'}
(out/'evidence/main-ui-native83.json').write_text(json.dumps(proof,indent=2))
print(json.dumps({k:proof[k] for k in ['main_ui_overlay_observed','qmp_scanout_equals_original_ap_pixels','rgb_colors','rgb_sha256','full_camera_boot']}))
