from pathlib import Path
import io, json, re, time
import urllib.request
from PIL import Image

w = Path(__file__).resolve().parent
o = w.parent.parent / 'outputs/sony-a7iv-qemu/native'
e = o / 'evidence'
checked = 0
for name in ['项目进展报告.zh-CN.md', 'README.zh-CN.md', 'MAIN-UI.zh-CN.md', 'BASIC-FUNCTIONS.zh-CN.md']:
    source = o / name
    content = source.read_text(encoding='utf-8')
    assert '\ufffd' not in content, name
    for target in re.findall(r'\]\(([^)]+)\)', content):
        if '://' in target or target.startswith('#'):
            continue
        assert (source.parent / target.split('#')[0]).exists(), (name, target)
        checked += 1

url = json.loads((e / 'live117-after-restart-audit.json').read_text())['url']
def pixels(data):
    return Image.open(io.BytesIO(data)).convert('RGB').tobytes()
frame = urllib.request.urlopen(url + 'frame.png', timeout=5).read()
main = (e / 'live117-after-restart-main.png').read_bytes()
empty = (e / 'live117-after-restart-5-play.png').read_bytes()
if pixels(frame) == pixels(empty):
    request = urllib.request.Request(url + 'action', data=b'{"key":"PLAY"}', headers={'Content-Type': 'application/json'}, method='POST')
    response = json.loads(urllib.request.urlopen(request, timeout=30).read())
    assert response.get('ok'), response
    time.sleep(0.75)
    frame = urllib.request.urlopen(url + 'frame.png', timeout=5).read()
assert pixels(frame) == pixels(main), 'Unexpected current frame; left user UI unchanged'
(e / 'live117-final-main.png').write_bytes(frame)
result = {'local_document_links_checked': checked, 'current_web_frame_matches_verified_main_rgb': True, 'run': 'native-117-card-main'}
(e / 'progress-document-validation.json').write_text(json.dumps(result, indent=2))
checkpoint = w / 'CURRENT.md'
old = checkpoint.read_text(encoding='utf-8')
checkpoint.write_text('''# CURRENT 2026-10-19 — DOCUMENTATION COMPLETE; NATIVE117 ACTIVE

Latest user request: 把当前进展整理到文档. Completed consolidated output
outputs/sony-a7iv-qemu/native/项目进展报告.zh-CN.md with current capabilities,
actual storage/playback/restart evidence, limitations, reproducibility, next acceptance criteria.
README/BASIC/MAIN/STATUS synchronized. Local document links validated.

PRIMARY native-117-card-main ACTIVE at SAME S5 URL port18764; final web frame is main.
Cold start and actual RESTART passed (~103.97s); QEMU269067 ->270922.
Before and after restart AP/HTTP entire RGB equality true, all6 afterrestart
action screenshots match native116 refs. Card metadata files present; logrotation bounded.
card-profile-promotion.json primary_activated:true. Only117 VM, no secondary.
Stable image ef7ed4046bcd3ccc0ea42f03550a958459272fb134ac61fac6f7a734f2a304d4.
Start-Camera sameargs coldstart+restart verified; launcherfile not independently coldinvoked.

NO SENSOR/LIVEVIEW/ISP/AF/JPEG/CAPTURE. Shutter audits cardSHA unchanged.
Original AP menus/Fn/Slot2 FAT32 metadata writes/empty playback work. FullCP not executed.
Virtual card and settings reset on restart. Do not claim full camera functionality.

Historical checkpoints below are superseded by current state above.

''' + old, encoding='utf-8')
print(json.dumps(result, indent=2))
