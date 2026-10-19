from pathlib import Path
from PIL import Image
import json
o = Path('/mnt/c/Users/16483/Documents/Codex/2026-10-17/new-chat/outputs/sony-a7iv-qemu/native')
e = o / 'evidence'
ref = Path('/mnt/d/CodexWork/sony-a7iv-qemu/menu-a7m4/native-116-card-controls')
cases = [
    ('live117-after-restart-main.png', 'slot2-main'),
    ('live117-after-restart-1-play.png', 'after-play'),
    ('live117-after-restart-2-play.png', 'play-return'),
    ('live117-after-restart-3-fn.png', 'fn-after-play'),
    ('live117-after-restart-4-menu.png', 'main-after-fn'),
    ('live117-after-restart-5-play.png', 'after-play'),
]
result = {x: Image.open(e/x).convert('RGB').tobytes() == Image.open(ref/y/'qemu.png').convert('RGB').tobytes() for x, y in cases}
assert all(result.values()), result
(e/'live117-after-restart-pixels.json').write_text(json.dumps(result, indent=2))
print(json.dumps(result, indent=2))
