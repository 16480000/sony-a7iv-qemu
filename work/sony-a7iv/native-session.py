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
from datetime import datetime,timezone,timedelta

BASE=Path('/mnt/d/CodexWork/sony-a7iv-qemu')
RUNTIME=Path('/opt/sony-a7iv/menu-a7m4/runtime/analysis')
sys.path.insert(0,str(RUNTIME))
from menu_live import key_command, FirmwareMonitor
serial_spec=importlib.util.spec_from_file_location('native_serial',Path(__file__).with_name('native-serial.py'))
serial_module=importlib.util.module_from_spec(serial_spec);serial_spec.loader.exec_module(serial_module)
serial_command=serial_module.serial_command
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
p.add_argument('--probe-virtual-card',action='store_true')
p.add_argument('--probe-storage-controls',action='store_true')
p.add_argument('--card-main',action='store_true',help='Configure the verified virtual Slot2 profile through the original menu')
a=p.parse_args()
if a.probe_storage_controls and not (a.probe_virtual_card and a.auto_main):p.error('Storage control probe requires virtual card and original UI setup replay')
if a.card_main and (not a.auto_main or a.initramfs!='main-virtual-card-stable.cpio'):p.error('Card main requires the verified card image and automatic original setup')
if a.probe_virtual_card and a.initramfs not in {'main-virtual-card-cycle.cpio','main-virtual-card-info.cpio'}:p.error('Card-cycle probe requires the isolated test image')
if a.auto_main and a.initramfs!='main-ap-state-consumer.cpio' and not (a.probe_virtual_card and a.initramfs=='main-virtual-card-info.cpio') and not a.card_main:
    p.error('Automatic setup requires the verified M4 coldboot image or the explicit isolated virtual-card probe')
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
            transition(['UP','ENTER'],0x1e3)
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
            if actual.tobytes()!=expected.tobytes():raise RuntimeError('Original power-save Off page did not match the verified UI')
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
            state={'url':panel.url,'run':str(out),'linux_pid':os.getpid()}
            state_name='live-panel.json' if a.port==18764 else f'live-panel-{a.port}.json'
            (BASE/'menu-a7m4'/state_name).write_text(json.dumps(state))
            print('A7M4_PANEL_URL '+panel.url,flush=True)
        last_refresh=0
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
        while not break_after_test and process.poll() is None:
            monitor.check()
            if a.seconds and time.monotonic()-start>a.seconds:break
            if panel:
                if time.monotonic()-last_refresh>.4:
                    qmp.call('screendump',{'filename':'/out/live.ppm'})
                    with Image.open(out/'live.ppm') as im:
                        png=io.BytesIO();im.save(png,format='PNG');panel.frame=png.getvalue()
                        black=im.convert('RGB').getextrema()==((0,0),(0,0),(0,0))
                        panel.status='当前黑屏；可重新启动恢复原厂初始化' if black else ('原厂界面运行中；虚拟卡槽 2；取景和照片保存尚未实现' if a.card_main else ('原厂界面运行中；省电已关闭；取景和照片保存尚未实现' if results.get('power_save_off') else '原厂界面运行中；取景和照片保存尚未实现'))
                    last_refresh=time.monotonic()
                if not panel.actions.empty():
                    key,event,result=panel.actions.get_nowait()
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
                            panel.frame=(out/result['restart']['label']/'qemu.png').read_bytes()
                            panel.status='原厂界面已显示；取景和照片保存尚未实现';last_refresh=0
                            continue
                        emit_key(key)
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
