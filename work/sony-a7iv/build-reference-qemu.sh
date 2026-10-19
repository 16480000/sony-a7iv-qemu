#!/bin/bash
set -euo pipefail
base=/opt/sony-a7iv
data=/mnt/d/CodexWork/sony-a7iv-qemu
ref=$data/a7c2-reference/repo/report/2026-10-17-qemu-native-camera
src=$base/qemu-11.1.2
build=$base/qemu-menu-build
python3 - "$data/qemu-11.1.2.tar.xz" "$base" <<'PY'
import pathlib, sys, tarfile
archive, output = pathlib.Path(sys.argv[1]), pathlib.Path(sys.argv[2])
if not (output/'qemu-11.1.2').exists():
    with tarfile.open(archive) as tar:
        members = [m for m in tar if not (m.issym() and m.linkname == '/opt/X11/include')]
        tar.extractall(output, members=members, filter='data')
PY
if [ ! -f "$src/.sony-menu-patched" ]; then
    patch --batch -p1 -d "$src" < "$ref/source/qemu-sony-native.patch"
    touch "$src/.sony-menu-patched"
fi
python3 - "$ref/source/manifest.json" "$src" <<'PY'
import hashlib, json, pathlib, sys
manifest=json.loads(pathlib.Path(sys.argv[1]).read_text())
for name, record in manifest['source_files'].items():
    assert hashlib.sha256((pathlib.Path(sys.argv[2])/name).read_bytes()).hexdigest() == record['after'], name
print('PATCHED_SOURCE_IDENTITIES_PASS', flush=True)
PY
mkdir -p "$build"
cd "$build"
"$src/configure" --target-list=aarch64-softmmu,aarch64-linux-user \
    --without-default-features --enable-tcg --enable-gtk --enable-sdl --enable-pixman \
    --enable-seccomp --enable-fdt=system --disable-opengl --disable-download \
    --disable-docs --disable-containers --disable-werror --disable-tools
ninja -j8 qemu-system-aarch64 qemu-aarch64
"$build/qemu-system-aarch64" --version
"$build/qemu-system-aarch64" -display help
python3 - "$ref/runtime/analysis/test-qemu-native-input.py" "$build/test-qemu-input-ubuntu.py" <<'PY'
from pathlib import Path
import sys
text=Path(sys.argv[1]).read_text()
old="'--symlink', 'usr/lib', '/lib64'"
assert text.count(old)==1
Path(sys.argv[2]).write_text(text.replace(old,"'--symlink', 'usr/lib64', '/lib64'"))
PY
PYTHONPATH="$ref/runtime/analysis" QEMU_TEST_BINARY="$build/qemu-system-aarch64" python3 -B "$build/test-qemu-input-ubuntu.py"
sha256sum qemu-system-aarch64 qemu-aarch64 > "$data/qemu-menu-programs.sha256"
