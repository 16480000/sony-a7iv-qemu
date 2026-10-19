"""Retain the original EVF enum contract and actual before/after UI evidence."""
from pathlib import Path
import hashlib,json,shutil
w=Path(__file__).resolve().parent
b=Path('/mnt/d/CodexWork/sony-a7iv-qemu/menu-a7m4')
o=w.parent.parent/'outputs/sony-a7iv-qemu/native'
run=b/'native-115-evf-priority';r=json.loads((run/'session-result.json').read_text())
assert all(r['storage_controls_checks'].values()) and not r['original_assertion_seen']
frames={}
for label in ['slot2-main','fn-before-shutter','main-before-shutter','after-shutter','after-play','play-return','fn-after-play','main-after-fn']:
 frames[label]=json.loads((run/label/'validation.json').read_text())
 assert frames[label]['ramfb_matches_ap_pixels']
root=Path('/opt/sony-a7iv/menu-a7m4/runtime/analysis/menu-root')
report={'model':'ILCE-7M4','firmware':'6.02','original_artifacts':{n:hashlib.sha256((root/n).read_bytes()).hexdigest() for n in ['usr/lib/appFw.so','cp/cpapp-b.bin']},
 'wire_contract':{'frame':'200d','command':'0118','bytes':22,'evf_priority_offset':20,'allowed_values':[0,1,2],'cp_parser_file_offsets':['0xa814a','0xa814c'],'cp_context_offset':'0x624','cp_validation_file_offsets':['0xa18ce','0xa18d4','0xa18d6','0xa18f6'],'validation':'unsigned cmp priority,3 followed by branch below3; field name from original string at runtime0xdd9ab5','completion_file_offset':'0xaded8','completion':'12-byte200d/1118 status0 preserving registered source'},
 'before':{'run':'native-114-abort-origin','failure':'Exact shape guard rejected playback EVF priority2; original AP35b8340 send failure triggers assertion at35b8358/source line876. Original stderr names send_no_wait_with_main_thread_i; kernel snapshot confirms coredump before ptrace.'},
 'after':{'run':run.name,'checks':r['storage_controls_checks'],'original_assertion_seen':r['original_assertion_seen'],'frames':frames,'diagnostic_export':json.loads((run/'diagnostic-recovery.json').read_text())},
 'photography':{'card_changed_after_shutter':r['card_changed_after_shutter'],'card_audits':r['card_audits'],'sensor_isp_jpeg_implemented':False},
 'scope':'Virtual display control state and original UI only; no CP firmware execution, synthetic images or fabricated capture completion.'}
(o/'evidence/evf-priority-playback-fix.json').write_text(json.dumps(report,indent=2))
shutil.copyfile(run/'after-play/qemu.png',o/'slot2-playback-empty.png')
print('EVF_PRIORITY_FIX_RECORDED; six original control checks and eight complete AP/QMP frame checks passed')
