"""Record observed basic controls and bounded storage probe results."""
from pathlib import Path
import hashlib,json

work=Path(__file__).resolve().parent
outputs=work.parent.parent/'outputs/sony-a7iv-qemu/native'
data=Path('/mnt/d/CodexWork/sony-a7iv-qemu/menu-a7m4')
primary=Path('/opt/sony-a7iv/menu-a7m4/runs/native-87-basic-stable')
actions=[json.loads(line) for line in (primary/'actions.jsonl').read_text().splitlines()]
report={
 'date':'2026-10-19','model':'ILCE-7M4','firmware':'6.02',
 'primary_run':primary.name,
 'primary_image':'main-ap-state-consumer.cpio',
 'primary_image_sha256':hashlib.sha256((data/'main-ap-state-consumer.cpio').read_bytes()).hexdigest(),
 'completed_actions':actions,
 'restart_success':any(a['key']=='RESTART' and 'restart' in a['result'] and 'error' not in a['result'] for a in actions),
 'settings_persistence':'UI setup replay only; personal settings are not persisted',
 'photo_capture_implemented':False,'sensor_liveview_implemented':False,
}
assert report['restart_success']
(outputs/'evidence/basic-controls-native87.json').write_text(json.dumps(report,indent=2))
storage={'date':'2026-10-19','physical_storage_used':False,'probes':[],'photo_capture_implemented':False}
for name in ['native-93-single-virtual-card','native-94-card-header','native-95-card-port2','native-96-card-native-status','native-97-card-error-trace','native-98-card-root-error','native-99-card-pci-contract','native-100-slot2-sd','native-101-slot2-main','native-103-slot2-controls','native-104-slot2-controls']:
 run=data/name;log=(run/'console.log').read_bytes()
 lines=[]
 for line in log.decode(errors='replace').splitlines():
  if 'BOOT_LOG_MEDIA_' in line and not line.startswith('OBS ') and line not in lines:lines.append(line)
 storage['probes'].append({'run':name,'console_sha256':hashlib.sha256(log).hexdigest(),'result':json.loads((run/'session-result.json').read_text()),'native_media_log':lines})
storage['interpretation']={
 'slot2':'Native /nondev/rm2 -> /dev/mmca; 64 MiB MBR/FAT32 mounted and drive/free-space queries succeeded. Native100 stayed on original language page without card-error view330. Native101 completed original setup and reached main view0.',
 'slot1':'Native hybrid /nondev/rm3 fails. Native98 traced root error source0xd line0xb23 to missing /proc/bus/pci configuration. Native99 metadata experiment advanced to line0xb39, missing hybrid submodule. That experiment was removed from current observer.',
 'port_header':'libInfraMediaDetect ParseInternalMessage at0x10a9c requires byte0=2. Kernel-only acceptance of type0 did not establish upper-layer handling.',
 'notification_state':'0/1 also encode initial subscription notifications; they must not be interpreted as raw inserted/removed flags.',
 'verification_limit':'Native101 main snapshot RGB comparison was false during asynchronous drawing. This report does not claim exact AP/QMP equality for that snapshot. Native100 language and native101 power-setting snapshot comparisons passed.',
 'recording_target':'Native104 original Rec. Media Settings photo target changed from Slot1 to Slot2 via native menu; actual QMP screenshot slot2-recording-media.png. Main showed boxed2 and no NO CARD text in checked frame.',
 'playback_limit':'Native104 PLAY created views352 and8f but actual AP/QMP output stayed on main. Last traced request includes CP3006, while CameraBackground stack also waits in libObj e9ca8 via ea918 (301c path). No completion contract was added or fabricated.',
 'audit_limit':'Guest BusyBox has no sha256sum applet. The attempted read-only card hash audit did not produce a hash; no storage-write or JPEG-file claim is supported.',
 'remaining':'Storage writes, working playback, photography, JPEG encoding and sensor/ISP/AF still require validation or implementation.'
}
(outputs/'evidence/virtual-card-probes.json').write_text(json.dumps(storage,indent=2))
for name in ['native-session.py','native-serial.py','native_frame.py','panel-server.py']:
 (outputs/'runtime'/name).write_bytes((work/name).read_bytes())
print('BASIC_PROGRESS_RECORDED',len(storage['probes']))
