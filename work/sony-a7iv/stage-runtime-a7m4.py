import ctypes
import argparse
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import struct
import subprocess
import sys

def virtual_photo_layout(volume,partition_start):
    """Return the image_mmca offset and size of the seeded DSC00001.JPG data run."""
    data=volume.read_bytes()
    bps=struct.unpack_from('<H',data,11)[0]
    spc=data[13]
    reserved=struct.unpack_from('<H',data,14)[0]
    nfats=data[16]
    fatsz=struct.unpack_from('<I',data,36)[0]
    root=struct.unpack_from('<I',data,44)[0]
    cluster=bps*spc
    fat=reserved*bps
    area=(reserved+nfats*fatsz)*bps
    def chain(start):
        out=[];c=start
        while 2<=c<0x0ffffff8 and len(out)<100000:
            out.append(c)
            c=struct.unpack_from('<I',data,fat+c*4)[0]&0x0fffffff
        return out
    def read_dir(start):
        raw=bytearray()
        for c in chain(start):raw+=data[area+(c-2)*cluster:area+(c-1)*cluster]
        entries=[]
        for i in range(0,len(raw),32):
            e=raw[i:i+32]
            if e[0]==0:break
            if e[0]==0xe5 or e[11] in (0x08,0x0f):continue
            c=(struct.unpack_from('<H',e,20)[0]<<16)|struct.unpack_from('<H',e,26)[0]
            entries.append((bytes(e[0:11]),e[11],c,struct.unpack_from('<I',e,28)[0]))
        return entries
    def find(entries,name):
        for n,attr,c,size in entries:
            if n==name:return c,size,attr
        raise AssertionError(name)
    c,_,attr=find(read_dir(root),b'DCIM       ');assert attr&0x10
    c,_,attr=find(read_dir(c),b'100MSDCF   ');assert attr&0x10
    c,size,attr=find(read_dir(c),b'DSC00001JPG');assert not attr&0x10
    clusters=chain(c);assert clusters and size<=len(clusters)*cluster
    assert all(clusters[i+1]==clusters[i]+1 for i in range(len(clusters)-1)),'photo file is not contiguous'
    return partition_start*512+area+(c-2)*cluster,size

PREV=Path('/mnt/c/Users/16483/Documents/Codex/2026-10-16/new-chat/work/sony-a1m2')
sys.path.insert(0,str(PREV/'pydeps'))
from elftools.elf.elffile import ELFFile

W=Path('/mnt/c/Users/16483/Documents/Codex/2026-10-17/new-chat/work/sony-a7iv')
DATA=Path('/mnt/d/CodexWork/sony-a7iv-qemu')
DEST=Path('/opt/sony-a7iv/menu-a7m4')
A=DEST/'runtime/analysis'
ROOT=A/'menu-root'
assert (DEST/'prepared.json').exists()
parser=argparse.ArgumentParser()
parser.add_argument('--init',default='menu-init-bootstrap')
parser.add_argument('--image',default='bootstrap.cpio')
parser.add_argument('--window',action='store_true')
parser.add_argument('--system-sound',action='store_true')
parser.add_argument('--file-media',action='store_true')
parser.add_argument('--native-media-driver',action='store_true')
parser.add_argument('--virtual-card',action='store_true')
parser.add_argument('--background-failure',action='store_true')
parser.add_argument('--background-control',action='store_true')
parser.add_argument('--diagnostic-sink',action='store_true')
parser.add_argument('--rolling-diagnostics',action='store_true')
parser.add_argument('--imager-control',action='store_true')
parser.add_argument('--virtual-sensor',action='store_true')
parser.add_argument('--virtual-photo',action='store_true')
parser.add_argument('--virtual-video',action='store_true')
parser.add_argument('--sound-sink',action='store_true')
parser.add_argument('--sound-hook',action='store_true')
parser.add_argument('--enable-service',action='append',default=[])
args=parser.parse_args()
if args.virtual_card:assert args.file_media and args.native_media_driver,'Virtual card requires native notification driver and original file backend'
if args.background_failure:assert args.virtual_card,'Documented background failure probe is restricted to the isolated card profile'
if args.background_control:assert args.virtual_card and not args.background_failure,'Virtual background control requires the isolated card profile and excludes the failure probe'
if args.diagnostic_sink:assert args.virtual_card,'Diagnostic record receiver is restricted to the isolated card profile'
if args.rolling_diagnostics:assert args.diagnostic_sink,'Rolling retention requires the precise diagnostic receiver'
if args.imager_control:assert args.virtual_card and args.init=='menu-init-display','Imager control sink is restricted to the isolated display profile'
if args.virtual_sensor:assert args.virtual_card and args.init=='menu-init-display','Virtual sensor base layer is restricted to the isolated display profile'
if args.virtual_photo:assert args.virtual_card,'Virtual photo seeding requires the isolated virtual card profile'
if args.virtual_video:assert args.virtual_sensor and args.virtual_card,'Virtual video input requires the isolated virtual-sensor card profile'
if args.diagnostic_sink:
    subprocess.run(['clang','--target=aarch64-linux-gnu','-fuse-ld=lld','-nostdlib','-O2','-mno-outline-atomics','-Wl,-e,_start','-Wl,--dynamic-linker=/lib/ld-linux-aarch64.so.1',str(W/'kernel-log-read.c'),'-Wl,--no-as-needed',*[str(ROOT/'lib'/name) for name in ['libc-2.25.so','ld-2.25.so']],'-Wl,--allow-shlib-undefined','-o',str(ROOT/'simulation/kernel-log-read')],check=True)
    subprocess.run(['clang','--target=aarch64-linux-gnu','-fuse-ld=lld','-nostdlib','-O2','-mno-outline-atomics','-Wl,-e,_start','-Wl,--dynamic-linker=/lib/ld-linux-aarch64.so.1',str(W/'diagnostic-export.c'),'-Wl,--no-as-needed',str(ROOT/'usr/lib/libcrypto.so'),*[str(ROOT/'lib'/name) for name in ['libc-2.25.so','libdl-2.25.so','libpthread-2.25.so','ld-2.25.so']],'-Wl,--allow-shlib-undefined','-o',str(ROOT/'simulation/diagnostic-export')],check=True)
original=ROOT/'usr/lib/libIMDB.so'
saved=original.with_name('libIMDB.original.so')
if not saved.exists(): shutil.copyfile(original,saved)
data=bytearray(saved.read_bytes())
with saved.open('rb') as f:
    elf=ELFFile(f)
    raw=elf.get_section_by_name('.dynsym').get_symbol_by_name('imdb_raw')[0]
    def offset(va):
        for p in elf.iter_segments():
            if p['p_type']=='PT_LOAD' and p['p_vaddr']<=va<p['p_vaddr']+p['p_filesz']:
                return p['p_offset']+va-p['p_vaddr']
        raise ValueError(hex(va))
    skip={'libUsbBusPower.so','libInfraUsbCmn.so','libsensapi.so','libUsbControl.so','libBusPower.so','libHotplug.so','libInfraCrypt.so','libInfraMediaPwrMgr.so','libNetServiceTethering.so','libTetheringResource.so'}
    assert set(args.enable_service)<=skip,args.enable_service
    skip.difference_update(args.enable_service)
    changes=[]
    # IMDB_get_entries returns imdb_raw+0x100 (verified original instructions).
    for va in range(raw['st_value']+0x100,raw['st_value']+raw['st_size'],72):
        off=offset(va)
        if struct.unpack_from('<I',data,off)[0]==40: break
        ptr=struct.unpack_from('<Q',data,off+16)[0]
        if not ptr: continue
        pos=offset(ptr)
        name=data[pos:data.index(0,pos)].decode('ascii')
        if name in skip:
            old=struct.unpack_from('<I',data,off+8)[0]
            struct.pack_into('<I',data,off+8,old & ~7)
            changes.append({'service':name,'mask_before':old,'mask_after':old & ~7,'offset':hex(off+8)})
    assert 5<=len(changes)<=10, changes
for path in (original,A/'libIMDB-menu.so',ROOT/'simulation/libIMDB.so'):
    if path.exists(): path.chmod(0o755)
    path.write_bytes(data)
    path.chmod(0o555)
(DEST/'imdb-changes.json').write_text(json.dumps({'input_sha256':hashlib.sha256(saved.read_bytes()).hexdigest(),'output_sha256':hashlib.sha256(data).hexdigest(),'changes':changes},indent=2))
init_text=(W/args.init).read_text()
if args.background_failure:
    init_text=init_text.replace('echo NATIVE_MODULES_LOADED','export QEMU_A7M4_BACKGROUND_FAILURE=1\necho NATIVE_MODULES_LOADED')
if args.background_control:
    init_text=init_text.replace('echo NATIVE_MODULES_LOADED','export QEMU_A7M4_BACKGROUND_CONTROL=1\necho NATIVE_MODULES_LOADED')
if args.diagnostic_sink:
    init_text=init_text.replace('echo NATIVE_MODULES_LOADED','export QEMU_A7M4_DIAGNOSTIC_SINK=1\necho NATIVE_MODULES_LOADED')
if args.rolling_diagnostics:
    init_text=init_text.replace('echo NATIVE_MODULES_LOADED','export QEMU_A7M4_DIAGNOSTIC_ROTATE8=1\necho NATIVE_MODULES_LOADED')
if args.imager_control:
    init_text=init_text.replace('echo NATIVE_MODULES_LOADED','export QEMU_A7M4_IMAGER_CONTROL=1\necho NATIVE_MODULES_LOADED')
if args.virtual_sensor:
    init_text=init_text.replace('echo NATIVE_MODULES_LOADED','export QEMU_A7M4_VIRTUAL_SENSOR=auto\necho NATIVE_MODULES_LOADED')
if args.native_media_driver:
    assert args.init=='menu-init-display'
    init_text=init_text.replace('insmod /usr/kmod/upm.ko','insmod /usr/kmod/upm.ko\ninsmod /usr/kmod/mcmn_drv.ko\necho NATIVE_MEDIA_DRIVER_STATUS=$?')
if args.file_media:
    assert args.init=='menu-init-display'
    assert hashlib.sha256((ROOT/'usr/lib/libInfraMediaCommon.so').read_bytes()).hexdigest()=='ec454c50b13aa78621fd8f0a6a9a8899b5194e446ed1b5fcefb34996b3f73a39'
    import io
    sys.path.insert(0,str(DATA/'a7c2-reference/repo/report/2026-10-17-qemu-native-camera/runtime/analysis/vendor/fwtool'))
    from fwtool.archive.fat import writeFat,readFat
    fixture=io.BytesIO();writeFat([],4*1024*1024,fixture)
    fixture.seek(43);fixture.write(b'NO NAME    ');fixture.seek(0)
    assert list(readFat(fixture))==[]
    for name in ('image_mmca','image_mmcb'):(ROOT/name).write_bytes(fixture.getvalue())
    if args.virtual_card:
        # Camera media needs a normal partitioned FAT32 disk. fwtool's archive
        # writer always emits FAT12 and is appropriate only for identity images.
        scratch=DATA/'menu-a7m4/work';scratch.mkdir(exist_ok=True)
        volume=scratch/'virtual-sd1-fat32.bin'
        sector_count=64*1024*1024//512;partition_start=2048
        with volume.open('wb') as f:f.truncate((sector_count-partition_start)*512)
        subprocess.run(['mkfs.fat','--invariant','-F','32','-s','1','-h',str(partition_start),'-n','SONYQEMU',str(volume)],check=True)
        subprocess.run(['mmd','-i',str(volume),'::/DCIM','::/DCIM/100MSDCF'],check=True)
        if args.virtual_video:
            video_raw=W/'virtual-video.rgb4444'
            video_meta=W/'virtual-video.meta'
            assert video_raw.exists() and video_meta.exists(),'virtual video assets are missing'
            shutil.copyfile(video_raw, ROOT/'simulation/virtual-video.rgb4444')
            shutil.copyfile(video_meta, ROOT/'simulation/virtual-video.meta')
        if args.virtual_photo:
            photo=W/'virtual-photo.jpg'
            raw_photo=W/'virtual-photo.rgb4444'
            next_photo=W/'virtual-photo-next.jpg'
            next_raw=W/'virtual-photo-next.rgb4444'
            assert photo.exists(),'virtual-photo.jpg is missing'
            assert raw_photo.exists(),'virtual-photo.rgb4444 is missing'
            assert next_photo.exists(),'virtual-photo-next.jpg is missing'
            assert next_raw.exists(),'virtual-photo-next.rgb4444 is missing'
            shutil.copyfile(raw_photo, ROOT/'simulation/virtual-photo.rgb4444')
            shutil.copyfile(next_photo, ROOT/'simulation/virtual-photo-next.jpg')
            shutil.copyfile(next_raw, ROOT/'simulation/virtual-photo-next.rgb4444')
            subprocess.run(['mcopy','-o','-i',str(volume),str(photo),'::/DCIM/100MSDCF/DSC00001.JPG'],check=True)
            offset,size=virtual_photo_layout(volume,partition_start)
            assert size==65536,size
            (ROOT/'simulation/virtual-photo-layout').write_bytes(struct.pack('<QI',offset,size))
            subprocess.run(['clang','--target=aarch64-linux-gnu','-fuse-ld=lld','-nostdlib','-O2','-mno-outline-atomics','-Wl,-e,_start','-Wl,--dynamic-linker=/lib/ld-linux-aarch64.so.1',str(W/'virtual-photo-capture.c'),'-Wl,--no-as-needed',*[str(ROOT/'lib'/name) for name in ['libc-2.25.so','libdl-2.25.so','libpthread-2.25.so','ld-2.25.so']],'-Wl,--allow-shlib-undefined','-o',str(ROOT/'simulation/virtual-photo-capture')],check=True)
        subprocess.run(['fsck.fat','-n',str(volume)],check=True)
        mbr=bytearray(512)
        struct.pack_into('<I',mbr,440,0x41374d34)
        struct.pack_into('<B3sB3sII',mbr,446,0,b'\xfe\xff\xff',0x0c,b'\xfe\xff\xff',partition_start,sector_count-partition_start)
        mbr[510:512]=b'\x55\xaa'
        image_path=ROOT/'image_mmca'
        with image_path.open('wb') as f,volume.open('rb') as v:
            f.write(mbr);f.seek(partition_start*512);shutil.copyfileobj(v,f)
        assert image_path.stat().st_size==64*1024*1024
        (scratch/'virtual-sd1-profile.json').write_text(json.dumps({'virtual_file':str(image_path),'bytes':image_path.stat().st_size,'sha256':hashlib.sha256(image_path.read_bytes()).hexdigest(),'partition_type':'FAT32 LBA','partition_start_lba':partition_start,'partition_sectors':sector_count-partition_start,'fsck_read_only_passed':True,'physical_devices_used':False},indent=2))
    init_text=init_text.replace('echo NATIVE_MODULES_LOADED','export QEMU_A7M4_FILE_MEDIA=1\necho NATIVE_MODULES_LOADED')
if args.virtual_card:
    subprocess.run(['clang','--target=aarch64-linux-gnu','-fuse-ld=lld','-nostdlib','-O2','-mno-outline-atomics','-Wl,-e,_start','-Wl,--dynamic-linker=/lib/ld-linux-aarch64.so.1',str(W/'card-audit.c'),'-Wl,--no-as-needed',str(ROOT/'usr/lib/libcrypto.so'),*[str(ROOT/'lib'/name) for name in ['libc-2.25.so','libdl-2.25.so','libpthread-2.25.so','ld-2.25.so']],'-Wl,--allow-shlib-undefined','-o',str(ROOT/'simulation/card-audit')],check=True)
    subprocess.run(['clang','--target=aarch64-linux-gnu','-fuse-ld=lld','-nostdlib','-O2','-mno-outline-atomics','-Wl,-e,_start','-Wl,--dynamic-linker=/lib/ld-linux-aarch64.so.1',str(W/'seed-virtual-card.c'),'-Wl,--no-as-needed',*[str(ROOT/'usr/lib'/name) for name in ['libosal_uipc.so','libosal_utm.so']],*[str(ROOT/'lib'/name) for name in ['libc-2.25.so','libdl-2.25.so','libpthread-2.25.so','ld-2.25.so']],'-Wl,--allow-shlib-undefined','-o',str(ROOT/'simulation/seed-virtual-card')],check=True)
    init_text=init_text.replace('echo NATIVE_MODULES_LOADED','export QEMU_A7M4_VIRTUAL_CARD=1\nLD_BIND_NOW=1 /simulation/seed-virtual-card\necho VIRTUAL_CARD_SEED_STATUS=$?\necho NATIVE_MODULES_LOADED')
if args.sound_hook:
    assert args.init=='menu-init-display','Sound hook is restricted to the display profile'
    subprocess.run(['make','-C','/opt/sony-a7iv/build/source','O=/opt/sony-a7iv/build','M='+str(W/'sound-hook'),'ARCH=arm64','CROSS_COMPILE=aarch64-linux-gnu-','modules'],check=True)
    shutil.copyfile(W/'sound-hook/a7m4_snd.ko', ROOT/'simulation/a7m4_snd.ko')
if args.sound_sink:
    assert args.init=='menu-init-display','Sound queue sink is restricted to the display profile'
    subprocess.run(['clang','--target=aarch64-linux-gnu','-fuse-ld=lld','-nostdlib','-O2','-mno-outline-atomics','-Wl,-e,_start','-Wl,--dynamic-linker=/lib/ld-linux-aarch64.so.1',str(W/'sound-queue-sink.c'),'-Wl,--no-as-needed',str(ROOT/'usr/lib/libosal_uipc.so'),str(ROOT/'usr/lib/libosal_utm.so'),*[str(ROOT/'lib'/name) for name in ['libc-2.25.so','libdl-2.25.so','libpthread-2.25.so','ld-2.25.so']],'-Wl,--allow-shlib-undefined','-o',str(ROOT/'simulation/sound-queue-sink')],check=True)
    init_text=init_text.replace('echo NATIVE_MODULES_LOADED','/simulation/sound-queue-sink 0x8fc >/dev/console 2>&1 &\necho SOUND_SINK_STATUS=$?\necho NATIVE_MODULES_LOADED')
if args.system_sound:
    assert args.init=='menu-init-display','Sound backing is restricted to the cold-boot probe'
    init_text=init_text.replace('echo NATIVE_MODULES_LOADED','export QEMU_SYSTEM_SOUND_BUFFER=1\necho NATIVE_MODULES_LOADED')
(ROOT/'init').write_text(init_text)
(ROOT/'init').chmod(0o755)
lib=ROOT/'lib'
subprocess.run(['clang','--target=aarch64-linux-gnu','-fuse-ld=lld','-nostdlib','-O2','-mno-outline-atomics','-shared','-fPIC','-Wl,--no-undefined',str(W/'basic-observe.c'),*[str(lib/n) for n in ('libc-2.25.so','libdl-2.25.so','libpthread-2.25.so','ld-2.25.so')],'-o',str(ROOT/'simulation/basic-observe.so')],check=True)
output=DATA/'menu-a7m4'
output.mkdir(exist_ok=True)
image=output/args.image
with image.open('wb') as out:
    subprocess.run(['bash','-c','find . -path ./usr/share/screenreader -prune -o -print0 | cpio --null -o -H newc -C 1048576 --quiet'],cwd=ROOT,stdout=out,check=True)
# Reuse the reference's DTB preparation, while keeping A7M4 data independent.
unpacked=A/'unpacked/firmware.tar_unpacked'
for target,source in ((unpacked/'0700_part_image/dev/nflasha3_unpacked',ROOT/'system'),(unpacked/'0800_appli/setting',ROOT/'seed-setting')):
    target.parent.mkdir(parents=True,exist_ok=True)
    if not os.path.lexists(target): target.symlink_to(source)
tool=DEST/'runtime/sources/qemu-tools/usr/lib/libfdt.so.1'
tool.parent.mkdir(parents=True,exist_ok=True)
if not os.path.lexists(tool): tool.symlink_to('/usr/lib/x86_64-linux-gnu/libfdt.so.1')
dtb=output/'virt-packed.dtb'
subprocess.run(['dtc','-q','-I','dts','-O','dtb','-o',str(dtb),str(A/'qemu-virt-board/virt-packed.dts')],check=True)
env=dict(os.environ,QEMU_PREPARE_ONLY='1',QEMU_OUTPUT_DIR=str(output),SONY_TIMER_MODEL='1',SONY_DMM_SERVICE='1')
if args.system_sound:env['QEMU_EXTRA_CMDLINE']='memrsv=0x00020000@0x41ea00000:uc'
if args.window:env['MENU_NATIVE_WINDOW']='1'
subprocess.run(['bash',str(A/'qemu-kernel-probe.sh'),'4096',str(dtb),'1','1',str(image)],env=env,check=True)
if args.system_sound:
    command_line=subprocess.check_output(['fdtget',str(output/'virt.dtb'),'/chosen','bootargs'],text=True)
    reservation='memrsv=0x00020000@0x41ea00000:uc'
    assert command_line.split().count(reservation)==1
    for length,start in re.findall(r'memrsv=(0x[0-9a-fA-F]+)@(0x[0-9a-fA-F]+)',command_line):
        length,start=int(length,16),int(start,16)
        if (start,length)==(0x41ea00000,0x20000):continue
        assert not(start<0x41ea20000 and start+length>0x41ea00000),'Sound backing overlaps another reservation'
(output/'port-profile.json').write_text(json.dumps({'model':'ILCE-7M4','version':'6.02','reference_commit':'25efb56d7f0c69355f9225d1da50454207532e7f','initramfs_sha256':hashlib.sha256(image.read_bytes()).hexdigest(),'status':'prepared for runtime validation','app_offsets_from_a7c2_installed':False},indent=2))
print('STAGED A7M4 runtime, filtered services',len(changes),flush=True)
