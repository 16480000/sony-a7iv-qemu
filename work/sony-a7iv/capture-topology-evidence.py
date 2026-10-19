"""Summarize actual original-AP cold-boot protocol progress, never UI success."""
import argparse
import json
from pathlib import Path

p=argparse.ArgumentParser()
p.add_argument('run')
a=p.parse_args()
base=Path('/mnt/d/CodexWork/sony-a7iv-qemu/menu-a7m4')
root=base/a.run
lines=(root/'console.log').read_text(errors='replace').splitlines()
observed=[s[4:] for s in lines if s.startswith('OBS BOOT_LOG_PIN_')]
requests=[s[4:] for s in lines if s.startswith('OBS BOOT_LOG_CP_REQUEST ')]
session=json.loads((root/'session-result.json').read_text())
result={
    'run':a.run,'original_app':'ILCE-7M4 6.02 appFw.so',
    'injected_menu_entry':False,'full_camera_boot':False,
    'scope':'Control-plane local virtual endpoints; original CP code is inspected but not executed.',
    'limitations':['No sensor/ISP image stream','No camera main UI observed','Fresh logical connections only'],
    'accepted_fresh_connections':sum(s.startswith('BOOT_LOG_PIN_CONNECT ') for s in observed),
    'pin_operations':observed,'outgoing_cp_requests':requests,
    'display_observation':session.get('baseline'),
    'session_error':session.get('error'),
}
(root/'topology-evidence.json').write_text(json.dumps(result,indent=2))
print(json.dumps({'connections':result['accepted_fresh_connections'],'display':result['display_observation'],'error':result['session_error']}))
