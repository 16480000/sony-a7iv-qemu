"""Keep the actual guest card audits and frame checks for the capture probes."""
from pathlib import Path
import hashlib,json,re,shutil

work=Path(__file__).resolve().parent
base=Path('/mnt/d/CodexWork/sony-a7iv-qemu/menu-a7m4')
out=work.parent.parent/'outputs/sony-a7iv-qemu/native'
names=['native-105-shutter-audit','native-106-background-failure','native-107-background-control','native-108-diagnostic-receiver','native-109-diagnostic-exact','native-110-diagnostic-wire','native-111-playback-threads','native-112-diagnostic-audit','native-113-playback-crash','native-114-abort-origin','native-115-evf-priority','native-116-card-controls']
report={'model':'ILCE-7M4','version':'6.02','physical_devices_used':False,'runs':[],
 'audit_method':'Read-only /image_mmca SHA256 using original libcrypto, then bounded FAT32 directory walk; no files created by audit helper.',
 'initial_card_contents':'Stage creates empty FAT32 with DCIM/100MSDCF only; PRIVATE metadata files are created during original firmware execution.',
 'cp_scope':'Failure probe returns original F001 only for3006. Control probe models only3006/3007 control states, not CP firmware execution, sensor, ISP or JPEG.',
 'stack_correction':'libObj ea818 sets3006 and jumps to shared ea910/ea914; ea90c also supplies301c to that call. LR ea918 alone cannot identify the command. Direct send trace confirms3006.'}
for name in names:
 run=base/name
 if not (run/'session-result.json').is_file():continue
 raw=(run/'console.log').read_bytes();result=json.loads((run/'session-result.json').read_text())
 entry={'run':name,'console_sha256':hashlib.sha256(raw).hexdigest(),'result':result,'frames':{},'control_records':[]}
 for label in ['slot2-main','fn-before-shutter','main-before-shutter','after-shutter','after-play','play-return','fn-after-play','main-after-fn']:
  path=run/label/'validation.json'
  if path.exists():entry['frames'][label]=json.loads(path.read_text())
 diagnostics=[]
 for line in raw.decode(errors='replace').splitlines():
  if line.startswith('OBS BOOT_LOG_BACKGROUND_'):entry['control_records'].append(line)
  if line.startswith('OBS BOOT_LOG_DIAGNOSTIC_RETAINED '):diagnostics.append(line)
 entry['diagnostic_observer_records']={'logged_records':len(diagnostics),'first':diagnostics[:8],'last':diagnostics[-8:]}
 retained=run/'diagnostic-events.bin'
 if retained.exists():
  target=out/'evidence'/(name+'-diagnostic-events.bin');shutil.copyfile(retained,target)
  entry['retained_diagnostics']={'file':target.name,'bytes':retained.stat().st_size,'sha256':hashlib.sha256(retained.read_bytes()).hexdigest()}
 for filename in ['kernel-stack-audit.console','kernel-before-ptrace.console','original-stderr.console','diagnostic-recovery.json']:
  path=run/filename
  if path.exists():
   target=out/'evidence'/(name+'-'+filename);shutil.copyfile(path,target)
   entry[filename]={'file':target.name,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
 for filename in ['runtime-artifacts.json','initial-card-profile.json']:
  path=run/filename
  if path.exists():entry[filename]=json.loads(path.read_text())
 entry['guest_card_file_records']=[line.decode(errors='replace') for line in raw.splitlines() if line.startswith(b'CARD_AUDIT_FILE ')]
 entry['fatal_trace']=[line.decode(errors='replace') for line in raw.splitlines() if line.startswith((b'OBS BOOT_LOG_FATAL_',b'BOOT_LOG_FATAL_'))]
 entry['diagnostic_rotation_records']=[line.decode(errors='replace') for line in raw.splitlines() if line.startswith((b'OBS BOOT_LOG_DIAGNOSTIC_ROTATED ',b'BOOT_LOG_DIAGNOSTIC_ROTATED '))]
 report['runs'].append(entry)
(out/'evidence/capture-and-card-audits.json').write_text(json.dumps(report,indent=2))
assert any(r['result'].get('card_audits') for r in report['runs'])
for label,target in [('slot2-main','slot2-main-verified.png'),('after-shutter','slot2-after-shutter.png')]:
 shutil.copyfile(base/'native-105-shutter-audit'/label/'qemu.png',out/target)
shutil.copyfile(base/'native-110-diagnostic-wire/fn-before-shutter/qemu.png',out/'slot2-fn-verified.png')
print('CAPTURE_AUDITS_RECORDED',len(report['runs']))
