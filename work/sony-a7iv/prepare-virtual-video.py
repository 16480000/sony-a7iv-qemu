"""Extract a bounded, loopable RGBA4444 virtual-sensor video and two photo assets.

Virtual emulator input only. The frames are decoded/rescaled on the host and
included in the isolated test image; this is not the original ISP path.
Usage: python prepare-virtual-video.py <video> [--seconds 6] [--fps 10]
"""
import argparse
import json
import struct
import subprocess
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

W = Path(__file__).resolve().parent
ap = argparse.ArgumentParser()
ap.add_argument('video')
ap.add_argument('--seconds', type=float, default=6.0)
ap.add_argument('--fps', type=int, default=10)
a = ap.parse_args()
video = Path(a.video)
assert video.exists(), video
frames_wanted = max(2, int(a.seconds * a.fps))

vf = (f"scale=640:480:force_original_aspect_ratio=decrease,"
      f"pad=640:480:(ow-iw)/2:(oh-ih)/2:black,fps={a.fps}")
cmd = ['ffmpeg', '-v', 'error', '-i', str(video), '-an', '-vf', vf,
       '-frames:v', str(frames_wanted), '-f', 'rawvideo', '-pix_fmt', 'rgba', '-']
raw = subprocess.check_output(cmd)
frame_bytes = 640 * 480 * 4
count = len(raw) // frame_bytes
if count < 2:
    raise SystemExit(f'decoded only {count} frames')
raw = raw[:count * frame_bytes]
rgba = np.frombuffer(raw, dtype=np.uint8).reshape(count, 480, 640, 4)

def to4444(rgb, alpha=True):
    r = (rgb[..., 0] >> 4).astype(np.uint16)
    g = (rgb[..., 1] >> 4).astype(np.uint16)
    b = (rgb[..., 2] >> 4).astype(np.uint16)
    v = (b << 12) | (g << 8) | (r << 4) | 15
    return v.astype('<u2').tobytes()

video_raw = to4444(rgba[:, :, :, :3])
(W / 'virtual-video.rgb4444').write_bytes(video_raw)
(W / 'virtual-video.meta').write_bytes(struct.pack('<II', count, a.fps))
(W / 'virtual-video.json').write_text(json.dumps({
    'source': str(video), 'decoded_frames': count, 'fps': a.fps,
    'width': 640, 'height': 480, 'pixel_format': 'RGBA4444 little-endian, alpha 15',
    'bytes': len(video_raw), 'sha256': __import__('hashlib').sha256(video_raw).hexdigest(),
    'scope': 'virtual sensor input only; not original ISP or hardware capture'
}, indent=2) + '\n')

indices = [0, count // 2]
names = [('virtual-photo.jpg', 'virtual-photo.rgb4444', 1),
         ('virtual-photo-next.jpg', 'virtual-photo-next.rgb4444', 2)]
for idx, (jpg_name, raw_name, variant) in zip(indices, names):
    frame = rgba[idx, :, :, :3]
    im = Image.fromarray(frame, 'RGB')
    d = ImageDraw.Draw(im)
    d.rectangle([0, 200, 640, 280], fill=(20, 20, 20))
    d.text((190, 220), f'VIRTUAL VIDEO PHOTO {variant}', fill=(255, 255, 255))
    d.text((190, 245), 'QEMU - not original ISP', fill=(255, 180, 80))
    d.rectangle([0, 470, 639, 479], outline=(255, 255, 255))
    jpg = BytesIO()
    im.save(jpg, 'JPEG', quality=90)
    data = jpg.getvalue()
    assert len(data) <= 65536, len(data)
    (W / jpg_name).write_bytes(data + b'\x00' * (65536 - len(data)))
    photo_rgb = np.asarray(im)
    (W / raw_name).write_bytes(to4444(photo_rgb))
    print(jpg_name, 'source_frame', idx, 'jpeg_bytes', len(data))
print('video frames', count, 'raw bytes', len(video_raw), 'fps', a.fps)
