"""An owned, isolated A7M4 VM with actual QEMU display/input and AP frame checks."""
import argparse
import base64
import hashlib
import importlib.util
import io
import json
import os
import re
from pathlib import Path
import select
import shutil
import signal
import socket
import struct
import subprocess
import sys
import time
import wave
from datetime import datetime,timezone,timedelta

BASE=Path('/mnt/d/CodexWork/sony-a7iv-qemu')
RUNTIME=Path('/opt/sony-a7iv/menu-a7m4/runtime/analysis')
sys.path.insert(0,str(RUNTIME))
from menu_live import key_command, FirmwareMonitor
serial_spec=importlib.util.spec_from_file_location('native_serial',Path(__file__).with_name('native-serial.py'))
serial_module=importlib.util.module_from_spec(serial_spec);serial_spec.loader.exec_module(serial_module)
serial_command=serial_module.serial_command

def write_web_photo(process,logpath,data,monitor):
    """Transfer one padded 64 KiB browser JPEG to the guest and overwrite the pre-indexed card file."""
    if len(data)!=65536:raise ValueError('web photo must be exactly 65536 bytes')
    encoded=base64.b64encode(data).decode('ascii')
    for offset in range(0,len(encoded),512):
        chunk=encoded[offset:offset+512];op='>' if offset==0 else '>>'
        serial_command(process,logpath,f"printf '%s' '{chunk}' {op} /tmp/a7m4-web-photo.b64",timeout=15,monitor=monitor)
    raw=serial_command(process,logpath,'/usr/bin/openssl base64 -d -A -in /tmp/a7m4-web-photo.b64 -out /tmp/a7m4-web-photo.jpg; /bin/busybox wc -c /tmp/a7m4-web-photo.b64 /tmp/a7m4-web-photo.jpg; /simulation/virtual-photo-capture /tmp/a7m4-web-photo.jpg; echo WEB_PHOTO_WRITE=$?',timeout=60,monitor=monitor)
    if b'WEB_PHOTO_WRITE=0' not in raw:raise RuntimeError('guest web-photo write failed')

# The AP still emits a real adf_sys_request for every camera feedback tone.
# The CP/AIP decoder is not executed, so the host renders the exact firmware
# bank entry that the descriptor points at. This is a virtual CP output path,
# not a substitute trigger: disabling Audio Signals in the guest produces no
# event. The entry header is one byte; the previous web candidates incorrectly
# skipped one byte in every 32-byte block.
FW_SOUND_RE=re.compile(r'A7M4_SOUND_PLAY kind=(\d+) option=(\d+) sound_id=(\d+) '
                       r'param=(0x[0-9a-fA-F]+|\d+) addr=(0x[0-9a-fA-F]+|\d+) '
                       r'len=(\d+) enabled=(\d+) volume=(\d+)')
FW_SOUND_NAMES={1:'快门轻响 Ka',2:'快门动作 Sha',3:'Kasha 快门音',4:'对焦锁定提示音',
                5:'录制开始',6:'录制停止',7:'Kasha 连续快门',8:'连续快门',9:'20fps KaSha',
                10:'自拍计时',11:'2 秒自拍计时',12:'开机提示音',13:'关机提示音',
                14:'视频自拍 3 秒',15:'模式切换',16:'ASRID 扫描提示音'}
def fw_read_events(logpath,offset,partial):
    """Read complete A7M4_SOUND_PLAY records appended to the serial log."""
    try:
        with logpath.open('rb') as log:
            log.seek(offset)
            chunk=log.read()
    except OSError:
        return offset,partial,[]
    if not chunk:return offset,partial,[]
    offset+=len(chunk)
    lines=(partial+chunk).split(b'\n')
    partial=lines.pop()
    if len(partial)>262144:partial=b''
    events=[]
    for line in lines:
        text=line.decode('utf-8','replace')
        if 'A7M4_SOUND_PLAY' not in text:continue
        match=FW_SOUND_RE.search(text)
        if not match:
            events.append({'parse_error':text[-512:]});continue
        kind,option,sound_id,param,address,length,enabled,volume=match.groups()
        events.append({'kind':int(kind),'option':int(option),'sound_id':int(sound_id),
                       'param':int(param,0),'addr':int(address,0),'len':int(length),
                       'enabled':int(enabled),'volume':int(volume),
                       'name':FW_SOUND_NAMES.get(int(sound_id),'Sound #'+sound_id)})
    return offset,partial,events

def fw_decode_entry(data,rate,volume):
    """Render one original bank entry as a mono 16-bit WAV.

    The bank entry begins with a one-byte header (0x17/0x07 in observed
    entries); the remainder is signed 8-bit PCM. Sample-rate selection is a
    host rendering choice until the original AIP clock is recovered.
    """
    if len(data)<=1:raise ValueError('empty sound entry')
    raw=data[1:]
    gain=min(.8,.2+.04*max(0,min(16,volume)))
    pcm=bytearray(len(raw)*2)
    for i,value in enumerate(raw):
        sample=int(round((value-256 if value>=128 else value)*gain*256))
        sample=max(-32768,min(32767,sample))
        struct.pack_into('<h',pcm,2*i,sample)
    output=io.BytesIO()
    with wave.open(output,'wb') as wav:
        wav.setnchannels(1);wav.setsampwidth(2);wav.setframerate(rate);wav.writeframes(pcm)
    return output.getvalue()

def fw_decode_event(qmp,out,event,seq):
    """Read the exact descriptor bytes from guest PA and render the entry.

    The one-byte bank-entry header selects the playback rate. The user
    calibrated FocusLock (header 0x17) at 48 kHz on 2026-10-21; the matching
    0x07 group is 16 kHz. This is still the host rendering of AA_RT bytes,
    not the original CP/AIP decoder, but the rate and 8-bit entry layout now
    follow the firmware header instead of a guessed global rate.
    """
    address=event.get('addr',0);length=event.get('len',0)
    if not address or not 1<=length<=32768:raise ValueError('descriptor has no backed bank range')
    dump=out/f'fw-sound-{seq}.bin'
    qmp.call('pmemsave',{'val':address,'size':length,'filename':'/out/'+dump.name})
    data=dump.read_bytes()
    if len(data)!=length:raise ValueError('short PMEM sound read')
    result=dict(event)
    result['seq']=seq
    result['encoded_sha256']=hashlib.sha256(data).hexdigest()
    result['encoded_bytes']=len(data)
    result['samples']=max(0,len(data)-1)
    header=data[0]
    auto_rate=48000 if header==0x17 else (16000 if header==0x07 else 48000)
    result['header']=header
    result['rate']=auto_rate
    for rate in (8000,16000,24000,32000,48000):
        wav=fw_decode_entry(data,rate,event.get('volume',4))
        result[f'wav{rate//1000}']=base64.b64encode(wav).decode('ascii')
        result[f'duration{rate//1000}']=round(result['samples']/rate,4)
        (out/f'fw-sound-{seq}-{rate//1000}k.wav').write_bytes(wav)
    result['wav']=result[f'wav{auto_rate//1000}']
    result['duration']=round(result['samples']/auto_rate,4)
    return result

FW_CP={'descriptors':{},'seq':0}
def fw_parse_descriptors(logpath):
    """Recover the beep table registered by the original AP at boot."""
    descriptors={}
    try:text=logpath.read_text('utf-8','replace')
    except OSError:return descriptors
    for match in re.finditer(r'BOOT_LOG_SOUND_DESCRIPTOR id=(\d+) enabled=(\d+) '
                             r'address=(0x[0-9a-fA-F]+) bytes=(\d+)',text):
        sound_id,enabled,address,length=match.groups()
        descriptors[int(sound_id)]={'enabled':int(enabled),'addr':int(address,16),
                                    'len':int(length),'volume':4}
    for match in re.finditer(r'BOOT_LOG_SOUND_VOLUME sound_id=(\d+) volume=(\d+)',text):
        sound_id,volume=match.groups()
        if int(sound_id) in descriptors:descriptors[int(sound_id)]['volume']=int(volume)
    return descriptors

def fw_emit_registered(sound_id,source='virtual-cp'):
    """Play one AP-registered beep through the host virtual CP.

    The trigger is the real native key/sequence; the descriptor table and
    SysSound bytes are read from the guest, so firmware asset/table changes
    are audible. The CP/AIP trigger logic itself is approximated.
    """
    if not panel or not qmp:return None
    descriptor=FW_CP['descriptors'].get(int(sound_id))
    if not descriptor or not descriptor.get('enabled'):return None
    FW_CP['seq']+=1;seq=FW_CP['seq']
    event={'kind':1,'option':0,'sound_id':int(sound_id),'param':0,
           'addr':descriptor['addr'],'len':descriptor['len'],
           'enabled':descriptor['enabled'],'volume':descriptor.get('volume',4),
           'name':FW_SOUND_NAMES.get(int(sound_id),'Sound #'+str(sound_id)),
           'source':source}
    try:
        decoded=fw_decode_event(qmp,out,event,seq)
    except Exception as error:
        decoded=dict(event,seq=seq,error=str(error))
    panel.add_fw_sound(decoded)
    audit={key:value for key,value in decoded.items() if key not in ('wav8','wav16')}
    results.setdefault('firmware_sounds',[]).append(audit)
    try:
        with (out/'fw-sounds.jsonl').open('a') as log:
            log.write(json.dumps(audit,ensure_ascii=False)+'\n')
    except OSError:
        pass
    return decoded

from headless_osd_capture import capture
from native_frame import clean_native_export
from PIL import Image

p=argparse.ArgumentParser()
p.add_argument('--display',choices=['none','gtk'],default='gtk')
p.add_argument('--name',default='interactive-'+time.strftime('%Y%m%d-%H%M%S'))
p.add_argument('--test',action='store_true')
p.add_argument('--seconds',type=int,default=0)
p.add_argument('--initramfs',default='menu-window.cpio')
p.add_argument('--test-home',action='store_true')
p.add_argument('--web',action='store_true')
p.add_argument('--port',type=int,default=18764)
p.add_argument('--keep-menu-awake',action='store_true')
p.add_argument('--panel-token')
p.add_argument('--verify-system-sound',action='store_true')
p.add_argument('--inspect-threads',type=int,nargs='*',default=[])
p.add_argument('--inspect-manager',action='store_true')
p.add_argument('--auto-main',action='store_true',help='Replay the verified original firstboot UI and disable native power save')
p.add_argument('--allow-unlisted-image',action='store_true',help='Allow auto-main on an explicitly named candidate firmware image')
p.add_argument('--probe-virtual-card',action='store_true')
p.add_argument('--probe-storage-controls',action='store_true')
p.add_argument('--card-main',action='store_true',help='Configure the verified virtual Slot2 profile through the original menu')
p.add_argument('--virtual-sensor',action='store_true',help='Label the panel as an experimental virtual-sensor test image')
p.add_argument('--virtual-photo',action='store_true',help='Run the guest virtual-photo capture helper on SHUTTER')
p.add_argument('--web-video',action='store_true',help='Label the panel as browser-side web-video compositing')
p.add_argument('--gdb',type=int,help='Optional loopback QEMU gdbstub port')
p.add_argument('--gdb-socket',action='store_true',help='Expose the QEMU gdbstub on /out/gdb.sock')
a=p.parse_args()
if a.probe_storage_controls and not (a.probe_virtual_card and a.auto_main):p.error('Storage control probe requires virtual card and original UI setup replay')
if a.card_main and (not a.auto_main or a.initramfs!='main-virtual-card-stable.cpio'):p.error('Card main requires the verified card image and automatic original setup')
if a.probe_virtual_card and a.initramfs not in {'main-virtual-card-cycle.cpio','main-virtual-card-info.cpio'}:p.error('Card-cycle probe requires the isolated test image')
if a.auto_main and a.initramfs not in {'main-ap-state-consumer.cpio','imager-control-test.cpio','virtual-sensor-test.cpio','virtual-photo-test.cpio','virtual-video-test.cpio','sound-feedback-test.cpio','sound-live-test.cpio','language-zh-test.cpio','language-zh-seed.cpio'} and not (a.probe_virtual_card and a.initramfs=='main-virtual-card-info.cpio') and not a.card_main and not a.allow_unlisted_image:
    p.error('Automatic setup requires the verified M4 coldboot image, an isolated imaging test image, or the explicit isolated virtual-card probe')
if a.keep_menu_awake and a.initramfs!='menu-window.cpio':p.error('The verified native menu power profile requires menu-window.cpio')
running_qemu=[]
for task_proc in Path('/proc').iterdir():
    if not task_proc.name.isdigit():continue
    try:
        task_comm=(task_proc/'comm').read_text().strip()
        if task_comm=='qemu' or task_comm.startswith('qemu-system-'):running_qemu.append(int(task_proc.name))
    except OSError:pass
if len(running_qemu)>=2:p.error('Two QEMU instances are already running; finish the secondary probe before starting another')
out=Path('/opt/sony-a7iv/menu-a7m4/runs')/a.name
out.mkdir(parents=True,exist_ok=False)
shutil.copyfile(BASE/'menu-a7m4/virt.dtb',out/'virt.dtb')
# The board DTB carries the fixed initrd window and ramdisk_size. Rebuild
# images change the cpio length, so set both from the actual initramfs here
# instead of relying on a DTB generated for an older image.
initramfs=BASE/'menu-a7m4'/a.initramfs
initrd_start=0x440000000
initrd_size=initramfs.stat().st_size
initrd_end=initrd_start+initrd_size
ramdisk_kib=(initrd_size+1023)//1024
dtb=out/'virt.dtb'
bootargs=subprocess.run(['fdtget','-t','s',str(dtb),'/chosen','bootargs'],
                        check=True,capture_output=True,text=True).stdout.rstrip('\n')
bootargs=re.sub(r'ramdisk_size=\d+',f'ramdisk_size={ramdisk_kib}',bootargs)
subprocess.run(['fdtput','-t','s',str(dtb),'/chosen','bootargs',bootargs],check=True)
subprocess.run(['fdtput','-t','x',str(dtb),'/chosen','linux,initrd-start',
                hex(initrd_start>>32),hex(initrd_start&0xffffffff)],check=True)
subprocess.run(['fdtput','-t','x',str(dtb),'/chosen','linux,initrd-end',
                hex(initrd_end>>32),hex(initrd_end&0xffffffff)],check=True)
command=['bwrap','--unshare-all','--die-with-parent','--new-session','--clearenv',
 '--ro-bind','/usr','/usr','--symlink','usr/lib','/lib','--symlink','usr/lib64','/lib64',
 '--proc','/proc','--dev','/dev','--tmpfs','/tmp',
 '--ro-bind','/opt/sony-a7iv/qemu-menu-build/qemu-system-aarch64','/qemu',
 '--ro-bind',str(BASE/'boot-original/vmlinux.bin'),'/kernel.img',
 '--ro-bind',str(BASE/'menu-a7m4'/a.initramfs),'/initrd.img',
 '--bind',str(out),'/out','--chdir','/','--setenv','QEMU_SONY_TIMERS','1']
if a.display=='gtk':
    x=Path('/tmp/.X11-unix/X0')
    if not x.is_socket():raise RuntimeError('Local WSLg X0 socket is unavailable')
    command+=['--dir','/tmp/.X11-unix','--ro-bind',str(x),str(x),
      '--ro-bind','/etc/fonts','/etc/fonts','--setenv','DISPLAY',':0',
      '--setenv','GDK_BACKEND','x11','--setenv','NO_AT_BRIDGE','1',
      '--setenv','XDG_CACHE_HOME','/tmp/cache','--setenv','XDG_CONFIG_HOME','/tmp/config']
command+=['/qemu','-object','memory-backend-ram,id=sony-ram,size=24G,reserve=off',
 '-machine','virt,secure=off,gic-version=2,memory-backend=sony-ram',
 '-cpu','cortex-a35,cntfrq=2000000','-smp','1','-m','24576',
 '-nodefaults','-display','gtk,gl=off' if a.display=='gtk' else 'none',
 '-device','ramfb,id=a7m4-screen','-name','Sony A7 IV 6.02 - experimental original menu',
 '-chardev','socket,id=sonykeys,path=/out/native-input.sock,server=on,wait=off',
 '-device','sony-ui-input,chardev=sonykeys,display=a7m4-screen',
 '-monitor','none','-serial','stdio','-nic','none','-sandbox','on',
 '-qmp','unix:/out/qmp.sock,server=on,wait=off',
 '-device','loader,file=/out/virt.dtb,addr=0x400002000',
 '-device','loader,file=/kernel.img,addr=0x400080000,force-raw=on',
 '-device','loader,file=/initrd.img,addr=0x440000000,force-raw=on',
 '-device','loader,addr=0x400080000,cpu-num=0','-kernel','/kernel.img','-initrd','/initrd.img']
if a.gdb:command+=['-gdb',f'tcp:127.0.0.1:{a.gdb}']
if a.gdb_socket:command+=['-gdb','unix:/out/gdb.sock,server=on,wait=off']
(out/'command.json').write_text(json.dumps(command,indent=2))
def file_digest(path):
    digest=hashlib.sha256()
    with Path(path).open('rb') as reader:
        for block in iter(lambda:reader.read(1024*1024),b''):digest.update(block)
    return digest.hexdigest()
artifacts={name:{'path':str(path),'sha256':file_digest(path)} for name,path in {
    'kernel':BASE/'boot-original/vmlinux.bin','initramfs':BASE/'menu-a7m4'/a.initramfs,
    'dtb':out/'virt.dtb','session_script':Path(__file__),
    'frame_parser':Path(__file__).with_name('native_frame.py'),
    'serial_transport':Path(__file__).with_name('native-serial.py')}.items()}
(out/'runtime-artifacts.json').write_text(json.dumps(artifacts,indent=2))
if a.probe_virtual_card or a.card_main:shutil.copyfile(BASE/'menu-a7m4/work/virtual-sd1-profile.json',out/'initial-card-profile.json')

class Qmp:
    def __init__(self):
        self.s=socket.socket(socket.AF_UNIX);self.s.settimeout(10)
        self.s.connect(str(out/'qmp.sock'));self.f=self.s.makefile('rwb')
        self.f.readline();self.call('qmp_capabilities')
    def call(self,name,args=None):
        self.f.write((json.dumps({'execute':name,**({'arguments':args} if args else {})})+'\n').encode());self.f.flush()
        while True:
            data=json.loads(self.f.readline())
            if 'event' in data:continue
            if 'error' in data:raise RuntimeError(data)
            return data['return']
    def close(self):self.f.close();self.s.close()

def decode_pixels(info,directory):
    raw=(directory/'headless-osd-pixels.bin').read_bytes()
    rgb=bytearray(640*480*3)
    for i in range(640*480):
        value=int.from_bytes(raw[2*i:2*i+2],'little');alpha=value&15
        rgb[3*i:3*i+3]=bytes([((value>>12)*17*alpha+7)//15,(((value>>8)&15)*17*alpha+7)//15,(((value>>4)&15)*17*alpha+7)//15])
    im=Image.frombytes('RGB',(640,480),bytes(rgb));im.save(directory/'frame.png')
    return im

logpath=out/'console.log';keys=None;qmp=None;process=None;panel=None;start=time.monotonic()
results={'model':'ILCE-7M4','firmware':'6.02','display':a.display,'menu_boot':False,'keys':[],'full_camera_boot':False,'virtual_card_profile':bool(a.probe_virtual_card or a.card_main)}
fault=None
try:
    with logpath.open('ab',buffering=0) as log:
        process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT)
        monitor=FirmwareMonitor(logpath)
        while b'A7M4_BOOTSTRAP_DONE' not in logpath.read_bytes():
            if process.poll() is not None:raise RuntimeError('QEMU exited during boot')
            if time.monotonic()-start>90:raise TimeoutError('Native bootstrap did not finish within 90 seconds')
            monitor.check();time.sleep(.2)
        print('A7M4_NATIVE_READY '+str(out),flush=True)
        qmp=Qmp();keys=socket.socket(socket.AF_UNIX);keys.settimeout(3)
        keys.connect(str(out/'native-input.sock'))
        wires={b'M':'MENU',b'E':'ENTER',b'U':'UP',b'D':'DOWN',b'L':'LEFT',b'R':'RIGHT',b'X':'DELETE',b'<':'REAR_LEFT',b'>':'REAR_RIGHT'}

        def emit_key(key):
            physical={'PLAY':0x1f7,'FN':0x7095,'DISP':0x1f9,'HALF':0x1f1}
            def tap(code):
                prefix=f'/simulation/inject-key 0x807a0020 0x92840747 {code:#x} 0'
                return f'{prefix} 1 0 1; sleep 0.15; {prefix} 0 0 1'
            if key in physical or key=='SHUTTER':
                if key=='SHUTTER':
                    cmd='/simulation/inject-key 0x807a0020 0x92840747 0x1f1 0 1 0 1; sleep 0.2; '+tap(0xa7)+'; /simulation/inject-key 0x807a0020 0x92840747 0x1f1 0 0 0 1'
                else:cmd=tap(physical[key])
                serial_command(process,logpath,cmd,timeout=20,monitor=monitor)
                if key=='HALF' and (not panel or panel.cp_config.get('focus',True)):
                    fw_emit_registered(4)
                elif key=='SHUTTER' and panel:
                    # A7 IV electronic shutter is silent by default. Mechanical
                    # Ka+Sha / Kasha auditions are explicit virtual-CP choices.
                    mode=panel.cp_config.get('shutter','silent')
                    if mode=='mechanical':
                        fw_emit_registered(1);time.sleep(.06);fw_emit_registered(2)
                    elif mode=='continuous':
                        fw_emit_registered(7)
                    elif mode=='kasha':
                        fw_emit_registered(3)
                    # silent / electronic / off: no extra prompt sound
                results['keys'].append({'key':key,'route':'original InfraInput','capture_file_generated':False})
                time.sleep(.15);return
            codes={'MENU':'m','ENTER':'ret','UP':'up','DOWN':'down','LEFT':'left','RIGHT':'right','DELETE':'delete'}
            for down in [True,False]:
                qmp.call('input-send-event',{'device':'a7m4-screen','events':[{'type':'key','data':{'down':down,'key':{'type':'qcode','data':codes[key]}}}]})
            if wires.get(keys.recv(1))!=key:raise RuntimeError('Native input route mismatch')
            serial_command(process,logpath,key_command(key),timeout=20,monitor=monitor)
            time.sleep(.25 if a.auto_main else .07)

        def snap(label):
            directory=out/label;directory.mkdir()
            for attempt in range(3):
                data=serial_command(process,logpath,'/simulation/headless-osd-export',timeout=20,monitor=monitor)
                (directory/f'export-{attempt}.console').write_bytes(data)
                cleaned,noise_records=clean_native_export(data)
                try:
                    info=capture(cleaned,directory)
                    break
                except ValueError as error:
                    results.setdefault('frame_export_retries',[]).append({'label':label,'attempt':attempt,'error':str(error)})
                    if attempt==2:raise
            im=decode_pixels(info,directory)
            # The independent RAM framebuffer must show the same committed AP pixels.
            # QEMU submits asynchronously, so allow one refresh interval.
            time.sleep(.25)
            qmp.call('screendump',{'filename':'/out/'+label+'/qemu.ppm'})
            screen=Image.open(directory/'qemu.ppm').convert('RGB')
            screen.save(directory/'qemu.png')
            same=screen.size==im.size and screen.tobytes()==im.tobytes()
            summary={'label':label,'sequence':info['sequence'],'pixel_source_seq':info['pixel_source_seq'],
                     'pixel_sha256':hashlib.sha256((directory/'headless-osd-pixels.bin').read_bytes()).hexdigest(),
                     'ramfb_matches_ap_pixels':same,'distinct_colors':len(set(im.getdata())),
                     'observer_records_removed':noise_records,'export_attempt':attempt}
            (directory/'validation.json').write_text(json.dumps(summary,indent=2))
            print(json.dumps(summary),flush=True)
            return summary

        def original_setup(label,offset=0):
            def view(expected,after):
                deadline=time.monotonic()+15
                while time.monotonic()<deadline:
                    monitor.check()
                    with logpath.open('rb') as reader:reader.seek(after);data=reader.read()
                    hits=re.findall(rb'CREATE_SCREEN_ARGS call=\d+ id=(0x[0-9a-f]+|0) count=(\d+)',data)
                    if any(int(identity,0)==expected for identity,count in hits):
                        results.setdefault('original_setup_views',[]).append(hex(expected));return
                    time.sleep(.1)
                raise TimeoutError(f'Original setup page {expected:#x} was not observed')
            def transition(keys,expected):
                after=logpath.stat().st_size
                for key in keys:emit_key(key)
                view(expected,after)
            view(0x12e,offset)
            # Seed Backup.bin language entry 0x2cf03a6 is set to model
            # language 25 (Simplified Chinese), with the additive BK4 checksum
            # at 0x20 recomputed. Boot init copies the GB18030 and Big5 fonts
            # carved from firmware.fdat into /tmp/images, which fontlist.dat
            # expects. Confirm the preselected language; do not move the
            # cursor.
            time.sleep(.3)
            results['language_selection_screen']=snap(label+'-language')
            transition(['ENTER'],0x1e3)
            transition(['ENTER'],0x1e0)
            transition(['DELETE'],0x1c8)
            transition(['ENTER'],0xd1)
            transition(['LEFT','ENTER'],0x11d)
            transition(['ENTER'],0x99)
            date=datetime.now(timezone(timedelta(hours=8)))
            assert 2021<=date.year<=2035
            route=['UP']*(date.year-2021)+['RIGHT']+['DOWN']*((13-date.month)%12)+['RIGHT']+['DOWN']*((32-date.day)%31)+['ENTER']
            transition(route,0x1de)
            transition(['DOWN','ENTER'],0x1f7)
            transition(['ENTER'],0x1e9)
            transition(['ENTER'],0)
            results['main_ui_overlay_observed']=True
            time.sleep(.6)
            # Original Main home -> Setup -> Power Setting Option -> Start Time.
            transition(['MENU'],0x2d6)
            for key in ['LEFT','LEFT','UP','UP','RIGHT']+['DOWN']*8+['RIGHT','DOWN','ENTER']+['UP']*4+['ENTER','UP','ENTER']:emit_key(key)
            power=snap(label+'-power-off')
            reference=Path('/mnt/c/Users/16483/Documents/Codex/2026-10-17/new-chat/outputs/sony-a7iv-qemu/native/main-power-save-off.png')
            actual=Image.open(out/power['label']/'qemu.png').convert('RGB')
            expected=Image.open(reference).convert('RGB')
            if actual.tobytes()!=expected.tobytes():
                # The Chinese UI changes the power-save page pixels. The
                # position-based route is still the verified original route;
                # retain the actual Chinese page and do not claim the English
                # reference comparison.
                results['power_save_reference_mismatch']={
                    'reason':'camera UI language differs from the English reference',
                    'actual_screen':power['label']}
                print('A7M4_POWER_SAVE_REFERENCE_MISMATCH '+json.dumps(results['power_save_reference_mismatch']),flush=True)
            else:
                results['power_save_off']=True
            transition(['MENU'],0)
            main=snap(label+'-main')
            results['original_setup_replayed']=True
            results['original_setup_date']=date.date().isoformat()
            print('A7M4_ORIGINAL_MAIN_READY '+json.dumps(main),flush=True)
            return main

        def configure_native_power_off(baseline,label):
            expected='c4ab293effca43eb98311b1cc393fc97dcf203524d5b5bc3feeb8144da5bffcf'
            if baseline['pixel_sha256']!=expected or not baseline['ramfb_matches_ap_pixels']:
                raise RuntimeError('Original menu baseline differs; power-setting navigation not applied')
            route=['LEFT','LEFT','UP','RIGHT']+['DOWN']*8+['RIGHT','DOWN','ENTER']+['UP']*4+['ENTER','UP','ENTER']
            for key in route:emit_key(key)
            time.sleep(.3)
            power=snap(label+'-power-off')
            expected_png='b247af07d2a9cf43798b1118b5bec182e407a7d38a807d8529335371b343d4b3'
            actual_png=hashlib.sha256((out/power['label']/'qemu.png').read_bytes()).hexdigest()
            if actual_png!=expected_png or not power['ramfb_matches_ap_pixels']:
                raise RuntimeError('Native power-off settings screen differs from verified original UI')
            for key in ['LEFT','LEFT','DOWN','RIGHT','RIGHT']:emit_key(key)
            restored=snap(label+'-menu')
            if restored['pixel_sha256']!=expected or not restored['ramfb_matches_ap_pixels']:
                raise RuntimeError('Menu did not return to original baseline after native power setting')
            results['power_save_off']=True
            results.setdefault('power_save_configuration',[]).append({'method':'QMP -> native input -> original menu -> Power Save Start Time Off -> original confirmation', 'power_screen':power,'restored_menu':restored})
            return restored

        def initialize_card():
            serial_command(process,logpath,'/simulation/seed-virtual-card --remove; sleep 1; /simulation/seed-virtual-card; sleep 2; /bin/busybox tail -n 180 /tmp/menu-load.log',timeout=20,monitor=monitor)

        def configure_slot2(label):
            route=['MENU','LEFT','LEFT']+['UP']*5+['RIGHT','DOWN','RIGHT','DOWN','ENTER','ENTER','DOWN','ENTER']
            for key in route:emit_key(key)
            target=snap(label+'-recording-media')
            expected=Image.open(Path('/mnt/c/Users/16483/Documents/Codex/2026-10-17/new-chat/outputs/sony-a7iv-qemu/native/slot2-recording-media.png')).convert('RGB')
            actual=Image.open(out/target['label']/'qemu.png').convert('RGB')
            if actual.tobytes()!=expected.tobytes():raise RuntimeError('Photo recording Slot2 menu differs from the verified original setting')
            results['recording_slot2']=True
            for key in ['MENU','MENU']:emit_key(key)
            return snap(label+'-main')

        if a.probe_virtual_card or a.card_main:initialize_card()
        baseline=snap('00-menu')
        if a.auto_main:baseline=original_setup('setup')
        if a.keep_menu_awake:baseline=configure_native_power_off(baseline,'configured')
        if a.card_main:baseline=configure_slot2('card')
        results['visible_boot']=baseline['distinct_colors']>1
        results['menu_boot']=a.initramfs=='menu-window.cpio' and baseline['distinct_colors']>10
        results['baseline']=baseline
        if a.virtual_sensor:
            serial_command(process,logpath,'touch /tmp/a7m4-virtual-sensor.on',timeout=20,monitor=monitor)
            results['virtual_sensor_enabled_after_setup']=True
        if a.probe_storage_controls:
            card_main=configure_slot2('slot2')
            emit_key('FN');time.sleep(.6);fn_before=snap('fn-before-shutter')
            emit_key('MENU');time.sleep(.6);main_before=snap('main-before-shutter')
            def card_audit(label):
                raw=serial_command(process,logpath,'LD_BIND_NOW=1 /simulation/card-audit; echo CARD_AUDIT_EXIT=$?',timeout=35,monitor=monitor)
                (out/(label+'.console')).write_bytes(raw)
                digest=re.search(rb'CARD_AUDIT_SHA256 bytes=67108864 digest=([0-9a-f]{64})',raw)
                summary=re.search(rb'CARD_AUDIT_DONE result=0 files=(\d+) directories=(\d+) readonly=1',raw)
                if not digest or not summary or b'CARD_AUDIT_EXIT=0' not in raw:raise RuntimeError('Read-only virtual-card audit did not complete')
                result={'label':label,'sha256':digest[1].decode(),'files':int(summary[1]),'directories':int(summary[2]),'file_records':[line.decode(errors='replace') for line in raw.splitlines() if line.startswith(b'CARD_AUDIT_FILE ')]}
                results.setdefault('card_audits',[]).append(result);print('A7M4_CARD_AUDIT '+json.dumps(result),flush=True)
                return result
            before=card_audit('before-shutter')
            emit_key('HALF');emit_key('SHUTTER');time.sleep(1)
            after=card_audit('after-shutter')
            results['card_changed_after_shutter']=before['sha256']!=after['sha256']
            snap('after-shutter')
            emit_key('PLAY');time.sleep(1);playback=snap('after-play')
            follow_frames={}
            for key,label in [('PLAY','play-return'),('FN','fn-after-play'),('MENU','main-after-fn')]:
                emit_key(key);time.sleep(.6);follow_frames[label]=snap(label)
            results['storage_controls_checks']={
                'fn_changes_main_before_shutter':fn_before['pixel_sha256']!=card_main['pixel_sha256'],
                'menu_returns_main_before_shutter':main_before['pixel_sha256']==card_main['pixel_sha256'],
                'playback_changes_main':playback['pixel_sha256']!=card_main['pixel_sha256'],
                'play_returns_main':follow_frames['play-return']['pixel_sha256']==card_main['pixel_sha256'],
                'fn_after_play_matches_before':follow_frames['fn-after-play']['pixel_sha256']==fn_before['pixel_sha256'],
                'menu_after_fn_returns_main':follow_frames['main-after-fn']['pixel_sha256']==card_main['pixel_sha256']}
            raw=serial_command(process,logpath,'echo PRE_PTRACE_KERNEL_BEGIN; if test -x /simulation/kernel-log-read; then LD_BIND_NOW=1 /simulation/kernel-log-read; fi; cat /proc/sys/kernel/core_pattern; for t in /proc/$(pidof im.elf)/task/*; do case "$(cat "$t/comm")" in SeqQueueCommon|SeqQueueDispSwi|CameraBackgroun|AppFw) echo KERNEL_THREAD "$t" "$(cat "$t/comm")"; cat "$t/wchan" "$t/stack" "$t/syscall" "$t/stat";; esac; done; echo PRE_PTRACE_KERNEL_END',timeout=20,monitor=monitor)
            (out/'kernel-before-ptrace.console').write_bytes(raw)
            raw=serial_command(process,logpath,'echo ORIGINAL_STDERR_BEGIN; /bin/busybox tail -n 160 /tmp/im.log; echo ORIGINAL_STDERR_END',timeout=20,monitor=monitor)
            (out/'original-stderr.console').write_bytes(raw)
            results['original_assertion_seen']=bool(re.search(rb"Assertion .*failed|assert at infra_wrapper|lib_assert.cpp",raw))
            serial_command(process,logpath,'for t in /proc/$(pidof im.elf)/task/*; do echo STORAGE_PROBE_THREAD "$t" "$(cat "$t/comm")"; /simulation/menu-regs "${t##*/}"; done; /bin/busybox tail -n 100 /tmp/menu-load.log',timeout=35,monitor=monitor)
            raw=serial_command(process,logpath,'if test -f /tmp/a7m4-diagnostic-events.bin; then LD_BIND_NOW=1 /simulation/diagnostic-export; fi',timeout=50,monitor=monitor)
            (out/'diagnostic-export.console').write_bytes(raw)
            cleaned,_=clean_native_export(raw)
            match=re.search(rb'\nA7M4_DIAG_BEGIN\r?\n([A-Za-z0-9+/=\r\n]+)A7M4_DIAG_END',cleaned)
            if match:
                retained=base64.b64decode(re.sub(rb'\s',b'',match[1]),validate=True)
                at=0;lengths={};count=0
                while at<len(retained):
                    if len(retained)-at<4:raise RuntimeError('Truncated retained diagnostic length')
                    size=struct.unpack_from('<I',retained,at)[0];at+=4
                    if not 33<=size<=4096 or size>len(retained)-at:raise RuntimeError('Invalid retained diagnostic size')
                    kind,command,category,length=struct.unpack_from('<HHII',retained,at)
                    if (kind,command)!=(2,0x83) or length!=size-32:raise RuntimeError('Retained diagnostic header differs from native producer')
                    lengths[str(length)]=lengths.get(str(length),0)+1;count+=1;at+=size
                (out/'diagnostic-events.bin').write_bytes(retained)
                results['diagnostics']={'records':count,'payload_lengths':lengths,'bytes':len(retained),'sha256':hashlib.sha256(retained).hexdigest()}
                summary=re.search(rb'DIAGNOSTIC_SNAPSHOT total=(\d+) records=(\d+) exported_records=(\d+) exported_bytes=(\d+) sha256=([0-9a-f]{64})',cleaned)
                if not summary or int(summary[3])!=count or int(summary[4])!=len(retained):raise RuntimeError('Diagnostic sample differs from full-stream audit')
                sample_digest=re.search(rb' sample_sha256=([0-9a-f]{64})',cleaned)
                if not sample_digest or sample_digest[1].decode()!=results['diagnostics']['sha256']:raise RuntimeError('Retained diagnostic sample SHA256 differs from original guest bytes')
                results['diagnostics']['full_stream']={'bytes':int(summary[1]),'records':int(summary[2]),'sha256':summary[5].decode(),'raw_export_scope':'last complete records, at most512KiB; full stream validated and hashed in guest'}
                print('A7M4_DIAGNOSTIC_AUDIT '+json.dumps(results['diagnostics']),flush=True)
            elif b'A7M4_DIAG_BEGIN' in cleaned:
                raise RuntimeError('Diagnostic export is incomplete or contains unknown interleaved data')
        for tid in a.inspect_threads:
            serial_command(process,logpath,'/simulation/menu-regs '+str(tid)+' || true',timeout=20,monitor=monitor)
        if a.inspect_manager:
            matches=re.findall(rb'MANAGER_CAPTURED manager=(0x[0-9a-f]+)',logpath.read_bytes())
            if matches:
                manager=int(matches[-1],16)
                serial_command(process,logpath,f'/simulation/menu-readmem /proc/$(pidof im.elf)/mem {manager+0x398:#x} 64',timeout=20,monitor=monitor)
        if a.verify_system_sound:
            original=(RUNTIME/'menu-root/usr/share/avsystemsound/SysSound.bin').read_bytes()
            expected='dae3d18d37b85a22398573f04090a4a95a97052380f4b2b4402a374516399dfb'
            if len(original)!=77504 or hashlib.sha256(original).hexdigest()!=expected:
                raise RuntimeError('Original system-sound asset identity differs')
            qmp.call('pmemsave',{'val':0x41ea00000,'size':0x20000,'filename':'/out/system-sound-memory.bin'})
            actual=(out/'system-sound-memory.bin').read_bytes()
            matches=actual[:len(original)]==original and not any(actual[len(original):])
            results['system_sound']={'physical_address':'0x41ea00000','reserved_bytes':len(actual),
                'original_bytes':len(original),'original_sha256':expected,
                'qemu_memory_sha256':hashlib.sha256(actual[:len(original)]).hexdigest(),
                'original_bytes_match_and_tail_zero':matches,'playback_implemented':False}
            if not matches:raise RuntimeError('QEMU physical system-sound bytes differ from original firmware')
        if a.web:
            spec=importlib.util.spec_from_file_location('panel',Path(__file__).with_name('panel-server.py'))
            module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
            panel=module.Panel(a.port,(out/baseline['label']/'qemu.png').read_bytes(),a.panel_token)
            FW_CP['descriptors']=fw_parse_descriptors(logpath)
            print('A7M4_FW_BEEP_TABLE '+json.dumps({'ids':sorted(FW_CP['descriptors']),
                  'addresses':{str(key):hex(value['addr']) for key,value in FW_CP['descriptors'].items()}}),flush=True)
            state={'url':panel.url,'run':str(out),'linux_pid':os.getpid()}
            state_name='live-panel.json' if a.port==18764 else f'live-panel-{a.port}.json'
            (BASE/'menu-a7m4'/state_name).write_text(json.dumps(state))
            print('A7M4_PANEL_URL '+panel.url,flush=True)
        last_refresh=0
        sound_offset=logpath.stat().st_size
        sound_partial=b''
        sound_seq=0
        last_sound_poll=0
        if a.test:
            previous=baseline
            cases=[('DOWN','down',b'D'),('UP','up',b'U'),('ENTER','ret',b'E'),('MENU','m',b'M')]
            if a.test_home:cases.extend([('MENU','m',b'M'),('MENU','m',b'M')])
            for n,(key,qcode,wire) in enumerate(cases,1):
                for down in [True,False]:
                    qmp.call('input-send-event',{'device':'a7m4-screen','events':[{'type':'key','data':{'down':down,'key':{'type':'qcode','data':qcode}}}]})
                if keys.recv(1)!=wire:raise RuntimeError('QEMU input bridge mismatch for '+key)
                serial_command(process,logpath,key_command(key),timeout=20,monitor=monitor)
                time.sleep(.7)
                current=snap(f'{n:02d}-{key.lower()}')
                results['keys'].append({'key':key,'qmp_device_socket':True,
                    'pixels_changed':current['pixel_sha256']!=previous['pixel_sha256'],**current})
                previous=current
            break_after_test=True
        else:
            break_after_test=False
        virtual_status=(('虚拟传感器测试图运行中（非原厂 ISP）；快门写入虚拟照片' if a.virtual_photo else '虚拟传感器测试图运行中（非原厂 ISP）；照片尚未实现') if a.virtual_sensor else None)
        web_video_status='网页视频输入运行中（客户端合成；非原厂 ISP）' if a.web_video else None
        while not break_after_test and process.poll() is None:
            monitor.check()
            if a.seconds and time.monotonic()-start>a.seconds:break
            if panel and qmp and time.monotonic()-last_sound_poll>.15:
                last_sound_poll=time.monotonic()
                sound_offset,sound_partial,records=fw_read_events(logpath,sound_offset,sound_partial)
                for record in records:
                    FW_CP['seq']+=1;seq=FW_CP['seq']
                    record['source']='ap'
                    try:
                        decoded=fw_decode_event(qmp,out,record,seq)
                    except Exception as error:
                        decoded=dict(record,seq=seq,error=str(error))
                    panel.add_fw_sound(decoded)
                    audit={key:value for key,value in decoded.items() if key not in ('wav8','wav16')}
                    results.setdefault('firmware_sounds',[]).append(audit)
                    with (out/'fw-sounds.jsonl').open('a') as f:
                        f.write(json.dumps(audit,ensure_ascii=False)+'\n')
            if panel:
                if time.monotonic()-last_refresh>.4:
                    qmp.call('screendump',{'filename':'/out/live.ppm'})
                    with Image.open(out/'live.ppm') as im:
                        png=io.BytesIO();im.save(png,format='PNG');panel.frame=png.getvalue()
                        black=im.convert('RGB').getextrema()==((0,0),(0,0),(0,0))
                        panel.status='当前黑屏；可重新启动恢复原厂初始化' if black else (web_video_status or virtual_status or ('原厂界面运行中；虚拟卡槽 2；取景和照片保存尚未实现' if a.card_main else ('原厂界面运行中；省电已关闭；取景和照片保存尚未实现' if results.get('power_save_off') else '原厂界面运行中；取景和照片保存尚未实现')))
                    last_refresh=time.monotonic()
                if not panel.actions.empty():
                    item=panel.actions.get_nowait()
                    key,event,result=item[:3]
                    payload=item[3] if len(item)>3 else None
                    try:
                        if key=='STOP':
                            panel.status='虚拟机已停止';event.set();break
                        if key=='RESTART':
                            panel.status='正在从干净内存重新启动…'
                            keys.close();keys=None;qmp.close();qmp=None
                            process.terminate()
                            try:process.wait(timeout=5)
                            except subprocess.TimeoutExpired:process.kill();process.wait()
                            for name in ('qmp.sock','native-input.sock'):
                                owned_socket=out/name
                                if owned_socket.is_socket():owned_socket.unlink()
                            offset=logpath.stat().st_size
                            monitor=FirmwareMonitor(logpath);monitor.offset=offset
                            process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT)
                            deadline=time.monotonic()+85
                            while b'A7M4_BOOTSTRAP_DONE' not in logpath.read_bytes()[offset:]:
                                if process.poll() is not None:raise RuntimeError('QEMU exited during reset')
                                if time.monotonic()>deadline:raise TimeoutError('原厂系统重新启动超时')
                                monitor.check();time.sleep(.2)
                            qmp=Qmp();keys=socket.socket(socket.AF_UNIX);keys.settimeout(3)
                            keys.connect(str(out/'native-input.sock'))
                            result['restart']=snap('restart-'+str(int(time.time())))
                            if a.probe_virtual_card or a.card_main:initialize_card()
                            if a.auto_main:result['restart']=original_setup(result['restart']['label']+'-setup',offset)
                            if a.card_main:result['restart']=configure_slot2(result['restart']['label']+'-card')
                            if a.keep_menu_awake:result['restart']=configure_native_power_off(result['restart'],result['restart']['label']+'-configured')
                            FW_CP['descriptors']=fw_parse_descriptors(logpath)
                            panel.frame=(out/result['restart']['label']/'qemu.png').read_bytes()
                            if a.virtual_sensor:
                                serial_command(process,logpath,'touch /tmp/a7m4-virtual-sensor.on',timeout=20,monitor=monitor)
                            panel.status=web_video_status or virtual_status or '原厂界面已显示；取景和照片保存尚未实现';last_refresh=0
                            continue
                        if key=='EXEC':
                            if not isinstance(payload,str) or not payload or len(payload)>4096:raise ValueError('invalid guest command')
                            raw=serial_command(process,logpath,payload,timeout=60,monitor=monitor)
                            result['output']=raw.decode('utf-8','replace')[-65536:]
                        elif key=='PHOTO':
                            if payload is None:raise ValueError('missing photo payload')
                            write_web_photo(process,logpath,payload,monitor)
                            result['photo_bytes']=len(payload)
                        else:
                            emit_key(key)
                            if key=='SHUTTER' and a.virtual_photo:
                                serial_command(process,logpath,'/simulation/virtual-photo-capture; echo VIRTUAL_PHOTO_CAPTURE_RC=$?',timeout=20,monitor=monitor)
                    except Exception as error:result['error']=str(error)
                    finally:
                        with (out/'actions.jsonl').open('a') as actions:
                            actions.write(json.dumps({'time':time.time(),'key':key,'result':result})+'\n')
                        event.set()
                    continue
            if not select.select([keys],[],[],.2)[0]:continue
            event=keys.recv(1)
            if not event:break
            if event==b'S':snap('snapshot-'+str(int(time.time())));continue
            if event in wires:
                serial_command(process,logpath,key_command(wires[event]),timeout=20,monitor=monitor)
except BaseException as error:
    fault=f'{type(error).__name__}: {error}'
    results['error']=fault
    print(fault,file=sys.stderr,flush=True)
finally:
    if panel:panel.close()
    if keys:keys.close()
    if qmp:qmp.close()
    if process and process.poll() is None:
        process.terminate()
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:process.kill();process.wait()
    results['elapsed_seconds']=round(time.monotonic()-start,3)
    (out/'session-result.json').write_text(json.dumps(results,indent=2))
    destination=BASE/'menu-a7m4'/a.name
    shutil.copytree(out,destination,ignore=shutil.ignore_patterns('*.sock'),dirs_exist_ok=True)
    print('A7M4_SESSION_ENDED '+str(destination),flush=True)
if fault:sys.exit(1)
