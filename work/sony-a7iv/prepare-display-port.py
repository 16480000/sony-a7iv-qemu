"""Bind software display hooks to verified A7M4 ELF identities and relocations."""
import contextlib
import argparse
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import re
import shutil
import struct
import subprocess

W=Path(__file__).resolve().parent
parser=argparse.ArgumentParser()
parser.add_argument('--menu',action='store_true')
parser.add_argument('--window',action='store_true')
args=parser.parse_args()
spec=importlib.util.spec_from_file_location('comparison',W/'compare-elf-addresses.py')
mod=importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()):spec.loader.exec_module(mod)
Elf,D,OLD,NEW=mod.Elf,mod.D,mod.OLD,mod.NEW
A=Path('/opt/sony-a7iv/menu-a7m4/runtime/analysis')
R=A/'menu-root'
subprocess.run(['python3',str(W/'prepare-service-port.py'),'--defer-build'],check=True)
code=(A/'menu-observe.c').read_text()
code=code.replace('if (id == 0x5503e0 || family == 0x55 || family == 0x7a) return 1;', 'if (id == 0x80cf016d || id == 0x5503e0 || family == 0x55 || family == 0x7a) return 1;')
code=code.replace('static int kmsg = -2;','int kmsg = open("/dev/console", 1);')
code=code.replace('if (kmsg == -2) kmsg = open("/dev/console", 1);','')
code=code.replace('if (kmsg >= 0) { long ignored = write(kmsg, line, (unsigned long)n); (void)ignored; }','if (kmsg >= 0) { long ignored = write(kmsg, line, (unsigned long)n); (void)ignored; close(kmsg); }')
code=code.replace('"HDMI_NOTIFY_",','"DATE_CHECK_", "HDMI_NOTIFY_",',1) if '"HDMI_NOTIFY_",' in code else code
cp_raw=(R/'cp/cpapp-b.bin').read_bytes()
assert hashlib.sha256(cp_raw).hexdigest()=='7b9b137d696e5972d20db7f9119076172ed8e0730805d7f0b4c31b87689e2c2b'
pins=[]
for base,count,owner,reorder,initializer in [
    (0xe4feec,19,0x9284074a,False,'0x4f8010'),
    (0xadf43c,16,0x905a0048,True,'0x54e10a'),
    (0xabd698,13,0x90590818,True,'0x52d85a'),
    (0xc589ac,10,0x91670464,True,'0xa06834')]:
    for n in range(count):
        offset=base+n*16
        values=list(struct.unpack_from('<4I',cp_raw,offset))
        assert values[3]==owner
        if reorder:values=[values[1],values[2],values[0],values[3]]
        pins.append({'identity':values,'initial_state':1,'definition_file_offset':hex(offset),
                     'initializer':initializer,'constructor':'0x4e2006'})
# ADF4d25ee..4d2612 consumes ten12-byte {type,dir,u8 number} records,
# inserting the literal owner9058003f before invoking the same constructor.
for base,count,owner,initializer in [(0xaabeb0,10,0x9058003f,'0x4d25ee'),
                                     (0xaa1040,2,0x928d0783,'0x4950f4')]:
    for n in range(count):
        offset=base+n*12
        values=list(struct.unpack_from('<3I',cp_raw,offset))+[owner]
        assert values[2]<256
        pins.append({'identity':values,'initial_state':1,'definition_file_offset':hex(offset),
                     'initializer':initializer,'constructor':'0x4e2006'})
# HDMI5774f4..57753e builds two literal identities on its stack:
# type4 then5, direction1, number0, owner909a015a. A logical binding here
# does not alter the separately modeled HDMI RSEN/HPD-low state.
for pin_type,initializer in [(4,'0x5774f4'),(5,'0x57752e')]:
    pins.append({'identity':[pin_type,1,0,0x909a015a],'initial_state':1,
                 'literal_initializer_file_offset':initializer,'constructor':'0x4e2006'})
# GRM3d1116..3d114e builds {OSD1,INOUT3,no0,9080003b} in object+a4.
pins.append({'identity':[1,3,0,0x9080003b],'initial_state':1,
             'literal_initializer_file_offset':'0x3d1116','constructor':'0x4e2006'})
assert len({tuple(p['identity']) for p in pins})==len(pins)
pin_model=(W/'dataflow-pin-model.c').read_text().replace('/* ORIGINAL_PIN_RECORDS */',
    '\n'.join('    {{'+','.join(hex(x) for x in p['identity'])+'},1,0,0,0},' for p in pins))
sound_raw=(R/'usr/share/avsystemsound/SysSound.bin').read_bytes()
assert len(sound_raw)==77504 and hashlib.sha256(sound_raw).hexdigest()=='dae3d18d37b85a22398573f04090a4a95a97052380f4b2b4402a374516399dfb'
pin_model+='\n'+(W/'system-sound-model.c').read_text()
cfg_raw=(R/'cp/DmmCfg.bin').read_bytes()
assert hashlib.sha256(cfg_raw).hexdigest()=='7e7c09a3bb6922d5a1e5cfbddd29600b2fbc709264ac40bbde35b3f5ea2c54fd'
cfg_spec=importlib.util.spec_from_file_location('dmm_config',W/'parse-dmm-config.py')
cfg_mod=importlib.util.module_from_spec(cfg_spec);cfg_spec.loader.exec_module(cfg_mod)
cfg_profile=cfg_mod.parse(cfg_raw)
target=next(p for p in cfg_profile['units'] if p['unit_type']==0x50b58)
assert target['file_offset']==0x94fc and target['extent_ids'][0]==0xf0
assert target['first_extent_file_offset']==0x5730 and target['unit_size']==0x9600000
unit_sizes={}
for unit in cfg_profile['units']:unit_sizes.setdefault(unit['unit_type'],unit['unit_size'])
pin_model+='\n'+(W/'dmm-config-model.c').read_text().replace('/* ORIGINAL_DMM_UNITS */',
    '\n'.join('    {'+hex(key)+','+hex(size)+'},' for key,size in unit_sizes.items()))
(D/'menu-a7m4/original-cp-dmm-profile.json').write_text(json.dumps(cfg_profile,indent=2))
(D/'menu-a7m4/original-cp-pin-profile.json').write_text(json.dumps({'pins':pins,'scope':'virtual control-plane; no data stream'},indent=2))
send_entry='int osal_snd_msg(unsigned int id, void *message) {'
assert code.count(send_entry)==1
code=code.replace(send_entry,pin_model+'\n'+send_entry+r'''
    /* Exact single-way diagnostic producer: AP3724f4c accepts 1..0xfe0
       payload bytes and allocates payload+32 (3724f74). Header is
       {u16type2,u16cmd83,u32kind,u32length}, timestamp
       at+16 via3724b24 and original payload at+24, source8f013a, send3724ff4.
       Preserve the complete wire record before receiving/freeing it. This
       does not handle sync queries, other payloads or camera completions. */
    if(getenv("QEMU_A7M4_DIAGNOSTIC_SINK") && id==0x8f013a && message &&
       real_msg_size && real_msg_size(message)>=33 && real_msg_size(message)<=4096 &&
       (unsigned long)__builtin_return_address(0)-appfw_base==0x3724ff8 &&
       real_get_source(message)==0x8f013a && ((unsigned short *)message)[0]==2 &&
       ((unsigned short *)message)[1]==0x83 &&
       ((unsigned int *)message)[2]==real_msg_size(message)-32) {
        unsigned int size=real_msg_size(message);
        unsigned char retained[4100];*(unsigned int *)retained=size;
        for(unsigned int i=0;i<size;++i)retained[i+4]=((unsigned char *)message)[i];
        static volatile unsigned int retention_lock;
        static unsigned long retained_bytes;static unsigned int generation;
        unsigned int rolling=getenv("QEMU_A7M4_DIAGNOSTIC_ROTATE8")!=0,rotated=0;
        if(rolling)while(__atomic_exchange_n(&retention_lock,1,__ATOMIC_ACQUIRE))syscall(124);
        int retention_error=0;
        if(rolling && retained_bytes+size+4>8388608) {
            extern int rename(const char *,const char *);
            if(rename("/tmp/a7m4-diagnostic-events.bin","/tmp/a7m4-diagnostic-events.previous.bin"))retention_error=1;
            else {retained_bytes=0;rotated=++generation;}
        }
        int fd=retention_error?-1:open("/tmp/a7m4-diagnostic-events.bin",0x441,0644);
        long written=-1;if(fd>=0){written=write(fd,retained,size+4);close(fd);}
        if(written==size+4 && rolling)retained_bytes+=size+4;
        if(rolling)__atomic_store_n(&retention_lock,0,__ATOMIC_RELEASE);
        if(written!=size+4)return -1024;
        if(rotated){char event[100];snprintf(event,sizeof event,"generation=%u limit=8388608 files=2; complete records retained in rolling segments",rotated);record("BOOT_LOG_DIAGNOSTIC_ROTATED ",event);}
        static unsigned int count;unsigned int n=__atomic_add_fetch(&count,1,__ATOMIC_RELAXED);
        if(n<=8 || !(n&(n-1))) {
            char text[180];snprintf(text,sizeof text,"tid=%ld count=%u bytes=%u caller=appFw+0x3724ff8; exact one-way diagnostic event retained before free",syscall(178),n,size);
            record("BOOT_LOG_DIAGNOSTIC_RETAINED ",text);
        }
        return real_free_msg(id,message);
    }
    /* Original AP183c9a0/183cac0 sends OSD model snapshots to CP9088076b.
       Successful enqueue transfers ownership. With no physical CP, forwarding
       into an unregistered endpoint leaks the original shared-message pool.
       Preserve validated snapshot bytes, then consume/free as its receiver;
       no image stream, rendered pixels or completion notification invented. */
    if(display_info_enabled && id==0x9088076b && message && real_msg_size) {
        unsigned int size=real_msg_size(message),*words=message;
        unsigned long caller=(unsigned long)__builtin_return_address(0)-appfw_base;
        if(size>=8 && size<=65536 && words[1]==size-8 &&
           (caller==0x183ca4c || (caller>=0x183cafc && caller<0x183cb80))) {
            unsigned int valid=1,count=0;
            if(!words[0]) {
                unsigned int at=8;
                while(at<size) {
                    if(size-at<8 || ++count>64){valid=0;break;}
                    unsigned int length=*(unsigned int *)((char *)message+at+4);
                    if(length>size-at-8){valid=0;break;}
                    at+=8+length;
                }
            }
            if(valid) {
                int fd=open("/tmp/a7m4-ap-model-state.bin",0x241,0644);
                if(fd>=0) {long written=write(fd,message,size);close(fd);if(written!=(long)size)return -1024;}
                else return -1024;
                static unsigned int received;unsigned int sequence=++received;
                if(sequence==1 || !(sequence&(sequence-1))) {
                    char text[180];snprintf(text,sizeof text,"received=%u bytes=%u kind=%u fields=%u; exact AP state retained; message consumed/freed; no physical CP composition",sequence,size,words[0],count);
                    record("BOOT_LOG_AP_STATE_CONSUMED ",text);
                }
                return real_free_msg(id,message);
            }
            record("BOOT_LOG_AP_STATE_INVALID ","snapshot lengths differ from original AP serializer");
        }
    }
    /* CameraBackground AP libObj ea668 ->e9be0 requests3007 before
       replying to the original app's background power-save request.
       Native CP31e67e checks already-in-state3007 via90e0ca, then
       90f0ae ->320bb4 emits12B {kind1,cmd3007,token,statusf000}.
       This profile has no running imaging pipeline; retain that idle
       background state rather than claim any sensor transition. */
    /* Opt-in control endpoint, not CP code execution or a data producer.
       Model only the two background control states with original12B completion
       contracts:3006 CP31e678/31faca ->90f086,3007 CP31e694/31fadc ->90f0ae,
       both ->320bb4. No stream, exposure, capture, DMA, encoder or JPEG is
       completed here. Call-site and source guards keep unrelated IPC untouched. */
    if(display_info_enabled && getenv("QEMU_A7M4_BACKGROUND_CONTROL") &&
       id==0x90030001 && message && real_msg_size && real_msg_size(message)==24 &&
       ((unsigned char *)message)[0]==0) {
        unsigned int command=((unsigned short *)message)[1],source=real_get_source(message);
        Dl_info info;void *caller=__builtin_return_address(0);
        if((command==0x3006 || command==0x3007) && (source&0xffff0000)==0x81020000 &&
           real_dladdr && real_dladdr(caller,&info) && info.dli_fname &&
           strstr(info.dli_fname,"libObj.so") && (unsigned long)caller-(unsigned long)info.dli_fbase==0xe9c6c) {
            static unsigned int control_state=0x3007;
            void *reply=0;int result=real_allocate_msg(source,&reply,12,1);
            if(result)return result;
            unsigned int previous=__atomic_exchange_n(&control_state,command,__ATOMIC_SEQ_CST);
            ((unsigned int *)reply)[0]=(command<<16)|1;
            ((unsigned int *)reply)[1]=((unsigned int *)message)[1];
            ((unsigned int *)reply)[2]=0xf000;
            real_set_source(reply,id);result=real_send_msg(source,reply);
            if(result){real_free_msg(source,reply);return result;}
            char text[220];snprintf(text,sizeof text,"tid=%ld previous=%#x state=%#x reply=%#x; virtual control state only, no sensor/ISP/frame/capture completion",syscall(178),previous,command,source);
            record("BOOT_LOG_BACKGROUND_CONTROL ",text);
            real_free_msg(id,message);return 0;
        }
    }
    /* Explicit failure probe, not a ready/sensor completion. Original CP
       31eb66..31eb7a emits F001 when3006 cannot transition (90deac ->-1).
       Original AP e9cdc..e9d00 consumes this as failure/return0. Restrict the
       packet to the observed CameraBackground call site and reply queue family.
       Unknown commands and301c are deliberately left to their original route. */
    if(display_info_enabled && getenv("QEMU_A7M4_BACKGROUND_FAILURE") &&
       id==0x90030001 && message && real_msg_size && real_msg_size(message)==24 &&
       ((unsigned char *)message)[0]==0 && ((unsigned short *)message)[1]==0x3006) {
        unsigned int source=real_get_source(message);Dl_info info;
        void *caller=__builtin_return_address(0);
        if((source&0xffff0000)==0x81020000 && real_dladdr && real_dladdr(caller,&info) &&
           info.dli_fname && strstr(info.dli_fname,"libObj.so") &&
           (unsigned long)caller-(unsigned long)info.dli_fbase==0xe9c6c) {
            void *reply=0;int result=real_allocate_msg(source,&reply,12,1);
            if(result)return result;
            ((unsigned int *)reply)[0]=0x30060001;
            ((unsigned int *)reply)[1]=((unsigned int *)message)[1];
            ((unsigned int *)reply)[2]=0xf001;
            real_set_source(reply,id);result=real_send_msg(source,reply);
            if(result){real_free_msg(source,reply);return result;}
            char text[180];snprintf(text,sizeof text,"tid=%ld cmd=0x3006 reply=%#x status=0xf001; original failed-transition contract, no ready state or sensor data",syscall(178),source);
            record("BOOT_LOG_BACKGROUND_FAILURE ",text);
            real_free_msg(id,message);return 0;
        }
    }
    if(display_info_enabled && !getenv("QEMU_A7M4_BACKGROUND_CONTROL") && id==0x90030001 && message && real_msg_size &&
       real_msg_size(message)==24 && ((unsigned char *)message)[0]==0 &&
       ((unsigned short *)message)[1]==0x3007) {
        unsigned int source=real_get_source(message);
        if((source&0xffff0000)==0x81020000) {
            static unsigned int background_idle=1;
            if(background_idle) {
                void *reply=0;int result=real_allocate_msg(source,&reply,12,1);
                if(result)return result;
                ((unsigned int *)reply)[0]=0x30070001;
                ((unsigned int *)reply)[1]=((unsigned int *)message)[1];
                ((unsigned int *)reply)[2]=0xf000;
                real_set_source(reply,id);result=real_send_msg(source,reply);
                if(result){real_free_msg(source,reply);return result;}
                record("BOOT_LOG_BACKGROUND_IDLE ","native3007 already-idle completion; no running imaging pipeline or sensor transition");
                real_free_msg(id,message);return 0;
            }
        }
    }
    if(message && real_msg_size && (id==0x8102021f || id==0x90030001 || id==0x90040193)) {
        unsigned int bytes=real_msg_size(message),shown=bytes<96?bytes:96;
        Dl_info caller_info;void *caller_address=__builtin_return_address(0);
        const char *caller_name="unknown";unsigned long caller_offset=(unsigned long)caller_address;
        if(real_dladdr && real_dladdr(caller_address,&caller_info) && caller_info.dli_fname) {
            caller_name=caller_info.dli_fname;caller_offset-=(unsigned long)caller_info.dli_fbase;
        }
        char text[440];int used=snprintf(text,sizeof text,"tid=%ld dest=%#x source=%#x caller=%.70s+%#lx bytes=%u payload=",syscall(178),id,real_get_source(message),caller_name,caller_offset,bytes);
        for(unsigned int i=0;i<shown && used+2<(int)sizeof(text);++i)used+=snprintf(text+used,sizeof(text)-used,"%02x",((unsigned char *)message)[i]);
        record("BOOT_LOG_IMAGING_REQUEST ",text);
    }
    if(display_info_enabled) {
        int size_handled=0;int size_result=a7m4_dmm_size_query(id,message,&size_handled);
        if(size_handled)return size_result;
    }
    /* Original digital-level controller3ee59a calls3ee620 and mirrors
       its24-byte request with result at+16. In ready state2 but feature
       disabled,3ee67c..3ee68e returns0 without sending to the sensor.
       This virtual profile deliberately has no inertial sampling. */
    if(display_info_enabled && id==0x912f0335 && message && real_msg_size &&
       real_msg_size(message)==24) {
        unsigned int *request=message,source=real_get_source(message);
        if((request[0]==3 || request[0]==4) && !request[1] && !request[2] &&
           !request[3] && !request[4] && !request[5] && source) {
            static unsigned int requested_enable;
            requested_enable=request[0]==3;
            void *reply=0;int result=real_allocate_msg(source,&reply,24,1);
            if(result)return result;
            for(unsigned int i=0;i<6;++i)((unsigned int *)reply)[i]=request[i];
            ((unsigned int *)reply)[4]=0;
            real_set_source(reply,id);result=real_send_msg(source,reply);
            if(result){real_free_msg(source,reply);return result;}
            char text[180];snprintf(text,sizeof text,"requested_enable=%u; virtual feature disabled, native no-sensor branch result0; no orientation samples",requested_enable);
            record("BOOT_LOG_DIGITAL_LEVEL ",text);real_free_msg(id,message);return 0;
        }
    }
    if((id&0xf0000000)==0x90000000 && message && real_msg_size &&
       real_msg_size(message)>=24 && ((unsigned int *)message)[1]==0xa0a0a0a0) {
        unsigned int size=real_msg_size(message);unsigned char *bytes=message;
        char hex[210]={0},text[280];unsigned int at=0;
        for(unsigned int i=0;i<size && i<96;++i)at+=snprintf(hex+at,sizeof hex-at,"%02x",bytes[i]);
        snprintf(text,sizeof text,"dest=%#x source=%#x bytes=%u payload=%s",id,real_get_source(message),size,hex);
        record("BOOT_LOG_CP_REQUEST ",text);
        int pin_handled=0;int pin_result=a7m4_pin_model(id,message,&pin_handled);
        if(pin_handled)return pin_result;
        /* Native Dataflow header: marker at4, count/size at8/10,
           first-message offset24 at12, end at16. Only the observed
           single-message VDF timecode request is implemented here. */
        if(id==0x9059000e && size==52 && ((unsigned int *)message)[1]==0xa0a0a0a0 &&
           ((unsigned short *)message)[4]==1 && ((unsigned short *)message)[5]==52 &&
           ((unsigned int *)message)[3]==24 && ((unsigned int *)message)[4]==52 &&
           ((unsigned int *)message)[5]==0) {
            unsigned short *inner=(unsigned short *)(bytes+24);
            unsigned int source=real_get_source(message);
            if(inner[0]==0x2001 && inner[1]==0x205 && inner[2]==28 && inner[3]==1 &&
               ((unsigned int *)message)[0]==source && source) {
                /* CP51ee2a validates these byte fields;51eeb8 stores/publishes
                   the 20-byte config before51ee90 replies1205/status0.
                   This virtual endpoint retains configuration only. */
                static unsigned char timecode[20];static unsigned int commits;
                unsigned char *config=bytes+32;
                unsigned int status=(!config[0] || config[1]>=2 || config[12]>=3)?1:0;
                if(!status) {
                    for(unsigned int i=0;i<20;++i)timecode[i]=config[i];
                    ++commits;
                    int fd=open("/tmp/a7m4-timecode-config.bin",1|64|512,0600);
                    if(fd>=0){write(fd,timecode,sizeof timecode);close(fd);}
                }
                void *reply=0;int result=real_allocate_msg(source,&reply,36,1);
                if(result)return result;
                unsigned char *out=reply;
                for(unsigned int i=0;i<32;++i)out[i]=bytes[i];
                ((unsigned short *)out)[5]=36;((unsigned int *)out)[4]=36;
                ((unsigned short *)out)[13]=0x1205;((unsigned short *)out)[14]=12;
                ((unsigned int *)out)[8]=status;
                real_set_source(reply,id);result=real_send_msg(source,reply);
                if(result){real_free_msg(source,reply);return result;}
                snprintf(text,sizeof text,"VDF config retained bytes=20 commit=%u status=%u reply_queue=%#x inner=2001/1205 size=12 Dataflow size=36",commits,status,source);
                record("BOOT_LOG_TIMECODE ",text);
                real_free_msg(id,message);return 0;
            }
        }
    }
''')
obj_old,obj=Elf(OLD/'libObj.so'),Elf(NEW/'libObj.so')
app_old,app=Elf(OLD/'appFw.so'),Elf(NEW/'appFw.so')
assert hashlib.sha256(app.raw).hexdigest()=='1e1b9202eaa69198f20df03dbfdab2f103b206cc4ebcd2e7bd817e6a710018a2'
assert hashlib.sha256(obj.raw).hexdigest()=='0d4957f95e73b3ab643ef584c53f37de71098d3e353de15d3088651710ca2ba6'
# Resolve the actual rep_menu_controller, not a same-shaped generated constructor.
assert mod.rtti(app_old,app,0x5b0c558)['new_vptrs']==['0x599e090']
assert app.q(0x5a300a0)+16==0x599e090
assert app.q(0x5118520+0x354*96+8)==0x1dc769c
assert struct.unpack_from('<I',app.raw,app.offset(0x1dc7518))[0]==0x52806a81 # mov w1,#0x354

def relocation_symbols(elf):
    result={}
    for sec in elf.elf.iter_sections():
        if sec['sh_type']!='SHT_RELA':continue
        symbols=elf.elf.get_section(sec['sh_link'])
        for rel in sec.iter_relocations():
            if rel['r_info_sym']:
                result[rel['r_offset']]=(rel['r_info_type'],symbols.get_symbol(rel['r_info_sym']).name)
    return result

def got_map(old,new,addresses):
    a,b=relocation_symbols(old),relocation_symbols(new)
    result={}
    for addr in addresses:
        hits=[p for p,info in b.items() if info==a[addr]]
        assert len(hits)==1,(hex(addr),a[addr],hits)
        result[addr]=hits[0]
    return result

mapping=got_map(obj_old,obj,[0x27ec98,0x27f528,0x27e1a0,0x27f540,0x27e490,0x27f040])
appgot=got_map(app_old,app,[0x5bc2098,0x5bc2370,0x5bc2720])
date_old=[addr for addr,info in relocation_symbols(app_old).items() if info[1]=='date_time_add_seconds']
assert len(date_old)==1
date_got=got_map(app_old,app,date_old)[date_old[0]]
appgot[date_old[0]]=date_got
mapping.update({0x174dbc:obj.symbols['_ZN2ux6gfxeng14GraphicsEngine15drawFramebufferEv']['st_value'],
 0xf8e94:obj.symbols['GRM_screenGetOnBitmap']['st_value'],
 0x100d28:0xfc498,0x100cd8:0xfc448,0x100cec:0xfc45c,0x100d3c:0xfc4ac,
 0x100cb0:0xfc420,0x100eac:0xfc61c,0x100c3c:0xfc3ac,
 0x104404:0xffcb4,0x104414:0xffcc4,0x133cc8:0x12f720,
 0x130de8:0x12c840,0x130e00:0x12c858,0x100224:0xfb994,0x1027ac:0xfe05c,
 0x26d210:0x254630})
# These GOT-backed globals are anchored by corresponding original function loads.
assert obj_old.q(0x27da30)==0x2ebde0
manager=obj.q(0x264a48)
assert manager==0x2d0580
mapping[0x2ebde0]=manager

old_decode=0x277900
decoder=None
for i in range(0,96,8):
    vptr=old_decode-i
    try:
        if obj_old.q(vptr-16)!=0:continue
        report=mod.rtti(obj_old,obj,vptr)
        if 'Lz77' in report['type_name'] and len(report['new_vptrs'])==1:
            decoder={'old_vptr':vptr,'new_vptr':int(report['new_vptrs'][0],16),'slot':i,'type':report['type_name']}
            break
    except (ValueError,UnicodeError):pass
assert decoder is not None
decode_slot=decoder['new_vptr']+decoder['slot']
mapping[old_decode]=decode_slot
mapping[0x15a8b8]=obj.q(decode_slot)
mapping[0x277000]=decode_slot & ~4095
# The mapped JUMP_SLOT entries span these writable pages in each original ELF.
low=min(mapping[x] for x in (0x27ec98,0x27f528,0x27e1a0,0x27f540,0x27e490,0x27f040)) & ~4095
high=(max(mapping[x] for x in (0x27ec98,0x27f528,0x27e1a0,0x27f540,0x27e490,0x27f040))+4096)&~4095
assert high-low==8192
mapping[0x27e000]=low

def replace_body(text,signature,new_body):
    start=text.index(signature)
    brace=text.index('{',start)
    level=1;pos=brace+1
    while level:
        if text[pos]=='{':level+=1
        if text[pos]=='}':level-=1
        pos+=1
    return text[:brace+1]+'\n'+new_body+'\n'+text[pos-1:]

for old,new in sorted(mapping.items(),reverse=True):
    code=re.sub(r'0x'+format(old,'x')+r'(?![0-9a-fA-F])','0x'+format(new,'x'),code)
headless=(A/'headless-osd.c').read_text()
headless=headless.replace('0x2ebde0','0x'+format(manager,'x')).replace('0x26d210','0x254630')
(A/'headless-osd.c').write_text(headless)

code=replace_body(code,'static void *observe_application_init(void *argument)',
'''    record("ENTER ", "Application_System_Init");
    void *result=real_application_init(argument);
    record("RETURN_NONZERO ", result ? "Application_System_Init" : "Application_System_Init returned null");
    return result;''')
code=replace_body(code,'static void *observe_create_screen(void *a0,',
'''    __atomic_add_fetch(&create_screen_active,1,__ATOMIC_RELEASE);
    if(!ui_thread_id) ui_thread_id=(unsigned int)syscall(178);
    char text[160];
    snprintf(text,sizeof text,"call=%u id=%#lx count=%lu this=%p tid=%u",++create_screen_calls,(unsigned long)a1,(unsigned long)a3,a0,ui_thread_id);
    record("CREATE_SCREEN_ARGS ",text);
    void *result=real_create_screen(a0,a1,a2,a3,a4,a5,a6,a7);
    __atomic_add_fetch(&create_screen_returned,1,__ATOMIC_RELEASE);
    __atomic_sub_fetch(&create_screen_active,1,__ATOMIC_RELEASE);
    record("CREATE_SCREEN_RETURN ","original A7M4 view method returned");
    return result;''')
view=0x584e098
slot=view+16
original=app.q(slot)
code=replace_body(code,'static void install_create_screen_sentinel(unsigned long base)',f'''
    unsigned long *slot=(unsigned long *)(base+0x{slot:x}UL);
    if(*slot != base+0x{original:x}UL) {{record("CREATE_SCREEN_SENTINEL_FAILED ","A7M4 original method identity mismatch");return;}}
    if(mprotect((void *)((unsigned long)slot & ~4095UL),4096,3)) return;
    real_create_screen=(void *)*slot;
    *slot=(unsigned long)observe_create_screen;
    record("CREATE_SCREEN_SENTINEL ","A7M4 view RTTI and original method verified");''')
code=replace_body(code,'static void record_frame_call(const char *prefix,',
'''    if(count>8)return;
    char text[160];
    snprintf(text,sizeof text,"call=%u tid=%ld this=%p result=%#lx",count,syscall(178),object,result);
    record(prefix,text);''')
code=replace_body(code,'static void record_frame_sync(unsigned int count)','    (void)count; /* Unneeded diagnostic globals are not ported. */')
code=replace_body(code,'static void try_apply_menu_after_frame(void)',r'''
    static unsigned int attempted;
    if(!getenv("MENU_APPLY_MENU") || attempted || !captured_manager ||
       !create_screen_returned || create_screen_active || (unsigned int)syscall(178)!=ui_thread_id) return;
    attempted=1;
    int fd=open("/proc/self/mem",0);
    if(fd<0)return;
    unsigned long words[160]={0},vt=0;
    unsigned long manager=captured_manager,controller=0,offset=0;
    unsigned int hits=0;
    if(syscall(67,fd,words,sizeof words,manager)!=(long)sizeof words || words[0]!=appfw_base+0x599dfb8UL) {
        close(fd);record("MENU_APPLY_SKIPPED ","A7M4 manager RTTI identity mismatch");return;
    }
    for(unsigned int i=0;i+4<160;++i) {
        /* A7M4's active record has a 32-byte controller/current-ID gap;
           native-17 independently read fields 0x398 and 0x3b8. */
        if(i!=0x398/8 || words[i]<4096 || ((unsigned int *)(words+i))[8]!=0x315)continue;
        if(syscall(67,fd,&vt,8,words[i])==8 && vt==appfw_base+0x599fdd0UL) {
            controller=words[i];offset=i*8;hits++;
        }
    }
    if(hits!=1) {
        char item[200];
        for(unsigned int i=96;i<150;++i) {
            unsigned long object=words[i],table=0;
            if(object>=4096 && syscall(67,fd,&table,8,object)==8 && table>appfw_base && table<appfw_base+0x6000000UL) {
                snprintf(item,sizeof item,"off=%#x object=%#lx table=appFw+%#lx after24=%#x",i*8,object,table-appfw_base,((unsigned int *)(words+i))[6]);
                record("MENU_MANAGER_POINTER ",item);
            }
        }
        for(unsigned int i=192;i<300;++i) {
            unsigned int value=((unsigned int *)words)[i];
            if(value>=0x2e0 && value<0x4d0) {
                snprintf(item,sizeof item,"off=%#x value=%#x",i*4,value);
                record("MENU_MANAGER_ID ",item);
            }
        }
    }
    close(fd);
    char text[200];
    snprintf(text,sizeof text,"manager=%#lx controller=%#lx field=%#lx matches=%u tid=%u",manager,controller,offset,hits,ui_thread_id);
    record("MENU_APPLY_CHECK ",text);
    if(hits!=1){record("MENU_APPLY_SKIPPED ","no unique live boot controller/current-mode pair");return;}
    unsigned int from=0x4cf,to=0x354,restore=0x4cf;
    typedef void (*apply_t)(void *,const unsigned int *,const unsigned int *,const unsigned int *,unsigned int,unsigned int,unsigned int,unsigned int,unsigned int);
    record("MENU_APPLY_ENTER ","original A7M4 nine-argument lifecycle; rep_menu_controller ID 0x354 verified by RTTI/GOT/factory/constructor");
    ((apply_t)(appfw_base+0x1f05350))((void *)manager,&from,&to,&restore,0,1,0,0,0);
    record("MENU_APPLY_RETURN ","original lifecycle returned");
''')
lo=min(appgot.values()) & ~4095
hi=(max(appgot.values())+4096)&~4095
code=replace_body(code,'static void install_frame_observers(unsigned long base)',f'''
    if(!getenv("MENU_FRAME_OBSERVE") || !real_notify_draw || !real_draw_framebuffer) return;
    if(mprotect((void *)(base+0x{lo:x}),0x{hi-lo:x},3)) return;
    *(unsigned long *)(base+0x{appgot[0x5bc2098]:x})=(unsigned long)observe_notify_draw;
    *(unsigned long *)(base+0x{appgot[0x5bc2370]:x})=(unsigned long)observe_draw_framebuffer;
    if(real_uxengine_init2) *(unsigned long *)(base+0x{appgot[0x5bc2720]:x})=(unsigned long)observe_uxengine_init2;
    *(unsigned long *)(base+0x{date_got:x})=(unsigned long)observe_date_add;
    record("DATE_CHECK_BIND ","verified A7M4 date_time_add_seconds import now targets private forwarding observer");
    record("FRAME_PROBES_ARMED ","A7M4 import relocations verified");''')
needle='        appfw_base = 0; /* A7M4: application offsets pending separate validation. */'
replacement='''        Dl_info info;
        if(!real_dladdr(symbol,&info)) return symbol;
        appfw_base=(unsigned long)info.dli_fbase;
        real_uxengine_init2=real_dlsym(0,"uxengine_init2");
        /* im.elf checks dlerror immediately after this interposed dlsym.
           An unavailable optional diagnostic symbol must not invalidate its valid entry. */
        if(!real_uxengine_init2) { extern char *dlerror(void); (void)dlerror(); }
        install_create_screen_sentinel(appfw_base);
        install_manager_probe(appfw_base);
        install_frame_observers(appfw_base);'''
replacement=replacement.replace('install_frame_observers(appfw_base);','install_frame_observers(appfw_base);\n        install_date_math_probe(appfw_base);\n        install_boot_log_probe(appfw_base);')
assert code.count(needle)==1
code=code.replace(needle,replacement)
code=code.replace('0x1e770e4','0x1f04414')
verify='''    unsigned int *original=(unsigned int *)(base+0x1f04414UL);
    if(original[0]!=0xa9b87bfd || original[1]!=0x910003fd || original[2]!=0xa9025bf5 || original[3]!=0xaa0003f6) {
        record("MANAGER_PROBE_FAILED ","A7M4 original prologue identity mismatch");return;
    }
'''
old_sig='static void install_manager_probe(unsigned long base) {'
assert code.count(old_sig)==1
code=code.replace(old_sig,old_sig+'\n'+verify)
code=code.replace('static int hdmi_photo_enabled;', 'static int hdmi_photo_enabled;\nstatic volatile unsigned int a7m4_hdmi_notify_queue;')
marker='        if (hdmi_photo_enabled && head[0] == 0x2500 && head[1] == 0x102)'
handler='''        /* A7M4 original startup registers its IWrapperHDMI destination with 0x127.
           The virtual HDMI endpoint retains that actual queue; cable state stays disconnected. */
        if(display_info_enabled && head[0]==0x2500 && head[1]==0x127 &&
           real_msg_size(message)==12 && head[2]==12 && head[3]==1) {
            unsigned int callback=((const unsigned int *)message)[2];
            int (*statq)(unsigned int,unsigned int *)=real_dlsym((void *)-1,"osal_stat_msgq");
            unsigned int state[4]={0};
            unsigned int source=real_get_source(message);
            if(!source || !statq || statq(callback,state)) return -1024;
            void *reply=0;
            int result=real_allocate_msg(source,&reply,12,1);
            if(result)return result;
            unsigned short *out=reply;
            out[0]=0x2500;out[1]=0x8127;out[2]=12;out[3]=1;
            ((unsigned int *)reply)[2]=0;
            real_set_source(reply,id);
            result=real_send_msg(source,reply);
            if(result){real_free_msg(source,reply);return result;}
            a7m4_hdmi_notify_queue=callback;
            real_free_msg(id,message);
            record("HDMI_NOTIFY_REGISTER ","stored original IWrapperHDMI queue; 0x8127 registration completion delivered");
            return 0;
        }
        if(display_info_enabled && head[0]==0x2500 && real_msg_size(message)<=64) {
            unsigned char *b=message;unsigned int size=real_msg_size(message),at=0;
            char body[140]={0};for(unsigned int i=0;i<size;++i)at+=snprintf(body+at,sizeof body-at,"%02x",b[i]);
            record("HDMI_NOTIFY_REQUEST_BODY ",body);
        }
        /* AP calls hdmi_set_definition_hd(0)/qfhd(2). Original CP5797ae
           stores this desired setting and replies1 in RSEN_Lo;57bd48
           also replies1 if unchanged. AP35b7ab8 accepts0/1. Keep the
           virtual cable disconnected and change no link/output flags. */
        if(display_info_enabled && head[0]==0x2500 && head[1]==0x10a &&
           real_msg_size(message)==12 && head[2]==12 && head[3]==1) {
            unsigned char *b=message;
            if((b[8]==0 || b[8]==2) && !b[9] && !b[10] && !b[11]) {
                static volatile unsigned int desired_definition;
                unsigned int source=real_get_source(message);if(!source)return -1024;
                desired_definition=b[8];
                void *reply=0;int result=real_allocate_msg(source,&reply,12,1);
                if(result)return result;
                unsigned short *out=reply;out[0]=0x2500;out[1]=0x810a;out[2]=12;out[3]=1;
                ((unsigned int *)reply)[2]=1;
                real_set_source(reply,id);result=real_send_msg(source,reply);
                if(result){real_free_msg(source,reply);return result;}
                real_free_msg(id,message);
                char text[140];snprintf(text,sizeof text,"desired_definition=%u cable=disconnected; native810a status1 retained-setting completion",desired_definition);
                record("HDMI_NOTIFY_DEFINITION ",text);return 0;
            }
        }
        /* hdmi_init_resolution's original five byte slots are
           HD/SD/QFHD/UHD/RAW (CP10f4c8). In RSEN_Lo, CP579314 stores
           them without activating the link, replies8101/status0.
           Restrict this model to the actually observed factory packet. */
        if(display_info_enabled && head[0]==0x2500 && head[1]==0x101 &&
           real_msg_size(message)==16 && head[2]==16 && head[3]==1) {
            unsigned char *b=message;
            if(!b[8] && !b[9] && !b[10] && !b[11] && b[12]==6 && !b[13] && !b[14] && !b[15]) {
                static unsigned char resolution[5];
                unsigned int source=real_get_source(message);if(!source)return -1024;
                for(unsigned int i=0;i<5;++i)resolution[i]=b[8+i];
                int fd=open("/tmp/a7m4-hdmi-resolution.bin",1|64|512,0600);
                if(fd>=0){write(fd,resolution,sizeof resolution);close(fd);}
                void *reply=0;int result=real_allocate_msg(source,&reply,12,1);
                if(result)return result;
                unsigned short *out=reply;out[0]=0x2500;out[1]=0x8101;out[2]=12;out[3]=1;
                ((unsigned int *)reply)[2]=0;
                real_set_source(reply,id);result=real_send_msg(source,reply);
                if(result){real_free_msg(source,reply);return result;}
                real_free_msg(id,message);
                record("HDMI_NOTIFY_RESOLUTION ","stored original HD/SD/QFHD/UHD/RAW slots=0/0/0/0/6; cable remains disconnected; native8101/status0 delivered");return 0;
            }
        }
        /* CP1113bc, RSEN_Lo: handle_set_output_frame_rate retains one
           byte per HDMI definition0..4 in SharedData9e..a2, replies
           8117/status0 without a state change. The M4 path ignores the
           two DP bytes. No cable or video-output event is generated. */
        if(display_info_enabled && head[0]==0x2500 && head[1]==0x117 &&
           real_msg_size(message)==12 && head[2]==12 && head[3]==1 &&
           ((unsigned char *)message)[8]<5) {
            static unsigned char rates[5];unsigned char *b=message;
            unsigned int source=real_get_source(message);if(!source)return -1024;
            unsigned int definition=b[8],rate=b[9];rates[definition]=rate;
            int fd=open("/tmp/a7m4-hdmi-rates.bin",1|64|512,0600);
            if(fd>=0){write(fd,rates,sizeof rates);close(fd);}
            void *reply=0;int result=real_allocate_msg(source,&reply,12,1);
            if(result)return result;
            unsigned short *out=reply;out[0]=0x2500;out[1]=0x8117;out[2]=12;out[3]=1;
            ((unsigned int *)reply)[2]=0;
            real_set_source(reply,id);result=real_send_msg(source,reply);
            if(result){real_free_msg(source,reply);return result;}
            real_free_msg(id,message);
            char text[140];snprintf(text,sizeof text,"definition=%u desired_frame_rate=%u; native8117/status0 delivered; cable remains disconnected",definition,rate);
            record("HDMI_NOTIFY_RATE ",text);return 0;
        }
'''
assert code.count(marker)==1
code=code.replace(marker,handler+marker)
code=code.replace('"ENTER ", "RETURN_",','"HDMI_NOTIFY_", "ENTER ", "RETURN_",',1)
# M4 CP file+b1750 maps 0x32d to legacy 0x2004/0x304 (HDMI audio
# format, enum 0/1); +4f2cda builds the 0x200d/0x132d status completion.
# C2 uses 0x32f for that same legacy operation, so port the opcode exactly.
code=code.replace('head[1] == 0x32f','head[1] == 0x32d')
code=code.replace('head[1] == 0x16a','head[1] == 0x169')
code=code.replace('head[1] == 0x14c','head[1] == 0x14b')
code=code.replace('head[1] == 0x13d','head[1] == 0x13c')
code=code.replace('head[1] == 0x147','head[1] == 0x146')
code=code.replace('head[1] == 0x161','head[1] == 0x160')
# The original A7M4 receiver at 35b897c consumes its output-ready event
# from the actual registered queue at 8a9338c. Preserve the real event path;
# no direct writes to its promise, mode or key-state globals.
code=replace_body(code,'static void bb_output_ready_event(void)',r'''
    static unsigned int delivered;
    if(delivered || !appfw_base || !real_allocate_msg || !real_send_msg || !real_set_source || !real_free_msg)return;
    unsigned int queue=*(volatile unsigned int *)(appfw_base+0x8a9338cUL);
    int (*statq)(unsigned int,unsigned int *)=real_dlsym((void *)-1,"osal_stat_msgq");
    unsigned int state[4]={0};
    if(!queue || !statq || statq(queue,state)) {record("BB_OUTPUT_READY ","A7M4 output-event queue unavailable");return;}
    void *msg=0;
    if(real_allocate_msg(queue,&msg,48,1))return;
    unsigned char *b=msg;
    for(unsigned int i=0;i<48;++i)b[i]=0;
    b[0]=3;b[1]=0x20;b[2]=1;b[3]=0x82;b[4]=48;b[10]=3;
    real_set_source(msg,0x92840747);
    int result=real_send_msg(queue,msg);
    if(result){real_free_msg(queue,msg);return;}
    delivered=1;
    char text[140];snprintf(text,sizeof text,"A7M4 virtual output committed; 0x2003/0x8201 sent to registered queue %#x",queue);
    record("BB_OUTPUT_READY ",text);
''')
needle='        record("BB_CONFIG_REQUEST ", text);'
assert code.count(needle)==1
code=code.replace(needle,needle+r'''
        { unsigned int n=real_msg_size(message);if(n>64)n=64;
          char body[160];unsigned int at=0;
          for(unsigned int i=0;i<n;++i)at+=snprintf(body+at,sizeof body-at,"%02x",((unsigned char *)message)[i]);
          record("BB_CONFIG_BODY ",body); }
        if(display_info_enabled) {
            int sound_handled=0;int sound_result=a7m4_audio_config(id,message,&sound_handled);
            if(sound_handled)return sound_result;
        }
''')
needle='        if (display_info_enabled && head[0] == 0x200d && head[1] == 0x169)'
assert code.count(needle)==1
handler=r'''
        /* CPb3130: BB0119 maps to VDF2001/0101 (hrev,vrev,osdRev,
           rotation mode/value). Current native packet sets h/v reverse,
           keeps OSD unreversed and rotation0. AE01c returns1119/12.
           Only retain this observed virtual image-transform profile;
           there is no image stream, and the OSD pixels remain unchanged. */
        if(display_info_enabled && head[0]==0x200d && head[1]==0x119) {
            static unsigned char reverse_profile[20];
            static const unsigned char shape[28]={0x0d,0x20,0x19,1,28,0,1,0x80,1,1};
            if(real_msg_size(message)!=28)return -1024;
            unsigned char *request=message;
            for(unsigned int i=0;i<28;++i)if(request[i]!=shape[i])return -1024;
            unsigned int source=real_get_source(message);if(!source)return -1024;
            for(unsigned int i=0;i<20;++i)reverse_profile[i]=request[8+i];
            int fd=open("/tmp/a7m4-display-reverse.bin",1|64|512,0600);
            if(fd>=0){write(fd,reverse_profile,20);close(fd);}
            void *reply=0;int result=real_allocate_msg(source,&reply,12,1);if(result)return result;
            unsigned short *out=reply;out[0]=0x200d;out[1]=0x1119;out[2]=12;out[3]=0x8001;
            ((unsigned int *)reply)[2]=0;
            real_set_source(reply,id);result=real_send_msg(source,reply);
            if(result){real_free_msg(source,reply);return result;}
            record("BOOT_LOG_DISPLAY_REVERSE ","retained hrev1/vrev1/osdRev0/rotation0; virtual image path only; native1119 delivered");
            real_free_msg(id,message);return 0;
        }
        /* Native M4 display-switch request captured from SeqQueueDispSwi.
           CP aded8 builds its 12-byte 1118 result; preserve its original
           IWrapperBB completion queue and keep the accepted mode as state.
           Byte20 is EVF priority: a814a/a814c retains it in context+624,
           a18ce..a18f6 accepts0..2. Playback uses2, shooting uses1. */
        if(display_info_enabled && head[0]==0x200d && head[1]==0x118) {
            static unsigned char display_switch[22];
            static const unsigned char shape[22]={0x0d,0x20,0x18,1,22,0,1,0x80,3,1,0,0,0,0,0,0,0,0,0,0,1,0};
            if(real_msg_size(message)!=22)return -1024;
            for(unsigned int i=0;i<22;++i) {
                unsigned char value=((unsigned char *)message)[i];
                if(i==20){if(value>2)return -1024;}
                else if(value!=shape[i])return -1024;
            }
            unsigned int source=real_get_source(message);
            if(!source)return -1024;
            for(unsigned int i=0;i<22;++i)display_switch[i]=((unsigned char *)message)[i];
            void *reply=0;int result=real_allocate_msg(source,&reply,12,1);
            if(result)return result;
            unsigned char *out=reply;
            for(unsigned int i=0;i<12;++i)out[i]=0;
            out[0]=0x0d;out[1]=0x20;out[2]=0x18;out[3]=0x11;out[4]=12;out[6]=1;out[7]=0x80;
            real_set_source(reply,id);result=real_send_msg(source,reply);
            if(result){real_free_msg(source,reply);return result;}
            real_free_msg(id,message);
            char state[140];snprintf(state,sizeof state,"stored native display switch mode=%u evf_priority=%u; 0x1118 delivered to %#x",display_switch[8],display_switch[20],source);
            record("DISPLAY_SWITCH_SERVICE ",state);return 0;
        }
'''
code=code.replace(needle,handler+needle)
needle='    if (capid_enabled && (id == 0x9004015e || id == 0x92850750))'
assert code.count(needle)==1
handler=r'''
    /* A7M4 Camera::ReleaseLock::RelLockS2 mask: builder35f0938,
       CP8d0506 uses OR/BIC helpers8d02d2/8d02da. Idle virtual release
       state can ACK immediately (CP8d05d6 ->8d32b2), preserving mask
       and token. Same module8d0e28 selects f000 when blocked bits=0. */
    if(display_info_enabled && id==0x90040193 && message && real_msg_size &&
       real_msg_size(message)>=4 && ((unsigned short *)message)[1]==0x403d) {
        unsigned int size=real_msg_size(message);
        unsigned char *b=message;char text[180];unsigned int at=0;
        for(unsigned int i=0;i<size && i<32;++i)at+=snprintf(text+at,sizeof text-at,"%02x",b[i]);
        record("RESOURCE_SWITCH_REQUEST ",text);
        unsigned int source=real_get_source(message);
        unsigned int *words=message;
        if(size!=16 || b[0]!=5 || b[1] || ((unsigned short *)b)[1]!=0x403d ||
           (words[2]!=0x8000 && words[2]!=0x200000) || b[12]>1 || b[13] || b[14] || b[15] || source!=0x80020002)return -1024;
        static volatile unsigned int leases;
        if(appfw_base) {
            unsigned long *date_slot=(unsigned long *)(appfw_base+A7M4_DATE_GOT);
            snprintf(text,sizeof text,"slot=%#lx original=%#lx diagnostic=%#lx",(unsigned long)date_slot,*date_slot,(unsigned long)observe_date_add);
            record("DATE_CHECK_SLOT ",text);
            *date_slot=(unsigned long)observe_date_add;
        }
        if(b[12])leases|=words[2];else leases&=~words[2];
        void *reply=0;int result=real_allocate_msg(source,&reply,12,1);
        if(result)return result;
        unsigned int *out=reply;out[0]=0x403d0001;out[1]=words[1];out[2]=0xf000;
        real_set_source(reply,id);result=real_send_msg(source,reply);
        if(result){real_free_msg(source,reply);return result;}
        snprintf(text,sizeof text,"token=%#x resource=%#x enable=%u leases=%#x status=0xf000",words[1],words[2],b[12],leases);
        record("RESOURCE_SWITCH_COMPLETE ",text);real_free_msg(id,message);return 0;
    }
'''
code=code.replace(needle,handler+needle)
handler=r'''
        /* CP a1b8c validates request byte8 as display on/off 0/1 and maps
           it to legacy 2001/0321; 4f2476 creates the 1145 completion.
           The virtual display keeps this actual requested enable state. */
        if(display_info_enabled && head[0]==0x200d && head[1]==0x145) {
            static volatile unsigned int display_enabled;
            unsigned char *request=message;
            if(real_msg_size(message)!=10 || head[2]!=10 || head[3]!=0x8001 || request[8]>1 || request[9])return -1024;
            unsigned int source=real_get_source(message);if(!source)return -1024;
            display_enabled=request[8];
            void *reply=0;int result=real_allocate_msg(source,&reply,12,1);if(result)return result;
            unsigned char *body=reply;for(unsigned int i=0;i<12;++i)body[i]=0;
            body[0]=0x0d;body[1]=0x20;body[2]=0x45;body[3]=0x11;body[4]=12;body[6]=1;body[7]=0x80;
            real_set_source(reply,id);result=real_send_msg(source,reply);
            if(result){real_free_msg(source,reply);return result;}
            real_free_msg(id,message);
            char text[100];snprintf(text,sizeof text,"virtual display onoff=%u; native 0x1145 completion delivered",display_enabled);
            record("DISPLAY_ENABLE_SERVICE ",text);return 0;
        }
        /* Audio ADF availability query. CP b2764 ->2004/0128,
           reply8128 ->afd3c ->200d/1325 length28. No virtual audio
           input or processing features exist: each of16 native feature
           slots is0x80 (unavailable), not0 (available). Query result0
           means the feature profile itself was obtained successfully. */
        if(display_info_enabled && head[0]==0x200d && head[1]==0x325 &&
           real_msg_size(message)==8 && head[2]==8 && head[3]==0x8001) {
            unsigned int source=real_get_source(message);if(!source)return -1024;
            void *reply=0;int result=real_allocate_msg(source,&reply,28,1);
            if(result)return result;
            unsigned char *body=reply;for(unsigned int i=0;i<28;++i)body[i]=i>=12?0x80:0;
            body[0]=0x0d;body[1]=0x20;body[2]=0x25;body[3]=0x13;body[4]=28;body[6]=1;body[7]=0x80;
            real_set_source(reply,id);result=real_send_msg(source,reply);
            if(result){real_free_msg(source,reply);return result;}
            real_free_msg(id,message);
            record("BOOT_LOG_AUDIO_CAPABILITIES ","native1325 profile: all16 audio features unavailable(80), query result0; no audio-input implementation");return 0;
        }
        /* CP b4e10: display resolution_size. Current original request is
           selector2/resolution0, forwarded there to VDF2001/0118.
           CP4f27aa forms200d/1164/12-byte completion. Retain only this
           observed selector's valid (<3) virtual resolution policy. */
        if(display_info_enabled && head[0]==0x200d && head[1]==0x164 &&
           real_msg_size(message)==10 && head[2]==10 && head[3]==0x8001 &&
           ((unsigned char *)message)[8]==2 && ((unsigned char *)message)[9]<3) {
            static volatile unsigned int resolution;
            unsigned char *request=message;unsigned int source=real_get_source(message);
            if(!source)return -1024;
            resolution=request[9];
            void *reply=0;int result=real_allocate_msg(source,&reply,12,1);
            if(result)return result;
            unsigned char *body=reply;for(unsigned int i=0;i<12;++i)body[i]=0;
            body[0]=0x0d;body[1]=0x20;body[2]=0x64;body[3]=0x11;body[4]=12;body[6]=1;body[7]=0x80;
            real_set_source(reply,id);result=real_send_msg(source,reply);
            if(result){real_free_msg(source,reply);return result;}
            real_free_msg(id,message);
            char text[120];snprintf(text,sizeof text,"selector=2 resolution_size=%u; native1164 completion delivered",resolution);
            record("DISPLAY_RESOLUTION_SERVICE ",text);return 0;
        }
'''
needle='        if (display_info_enabled && head[0] == 0x200d && head[1] == 0x169)'
assert code.count(needle)==1
code=code.replace(needle,handler+needle)
# A7M4 CP b5254 consumes eighteen 32-byte output records, versus C2's
# different record layout. Keep the native table as the virtual output state.
# Do not copy C2's unrelated application-global "ready" writes.
code=replace_body(code,'static int plane_config_send(void *request)',r'''
    extern void *memcpy(void *,const void *,unsigned long);
    static unsigned char output_table[584];
    static unsigned int commits;
    if(!real_allocate_msg || !real_msg_size || !real_get_source || !real_set_source || !real_free_msg) return -1021;
    unsigned int source=real_get_source(request);
    unsigned char checked[12];
    if(!source || plane_config_reply(request,real_msg_size(request),checked)) return -1024;
    memcpy(output_table,request,sizeof output_table);
    ++commits;
    int statefd=open("/tmp/a7m4-output-table.bin",1|64|512,0600);
    if(statefd>=0) { write(statefd,output_table,sizeof output_table);close(statefd); }
    for(unsigned int phase=0;phase<2;++phase) {
        void *reply=0;
        int result=real_allocate_msg(source,&reply,12,1);
        if(result)return result;
        memcpy(reply,checked,12);
        real_set_source(reply,0x92840747);
        result=real_send_msg(source,reply);
        if(result){real_free_msg(source,reply);return result;}
    }
    char text[140];
    snprintf(text,sizeof text,"A7M4 0x146 stored %u-byte native output table; commit=%u, 0x1146 sync/async delivered",(unsigned int)sizeof output_table,commits);
    record("PLANE_CONFIG_SERVICE ",text);
    bb_output_ready_event();
    real_free_msg(0x92840747,request);
    return 0;
''')
reference=D/'a7c2-reference/repo/report/2026-10-17-qemu-native-camera/runtime/analysis'
audio=(reference/'hdmi-format-service.c').read_text()
audio=audio.replace('halfword(request + 2) != 0x32f','halfword(request + 2) != 0x32d')
audio=audio.replace('{0x0d, 0x20, 0x2f, 0x13, 12, 0, 1, 0x80}','{0x0d, 0x20, 0x2d, 0x13, 12, 0, 1, 0x80}')
audio=audio.replace('halfword(request + 2) != 0x16a','halfword(request + 2) != 0x169')
audio=audio.replace('{0x0d, 0x20, 0x6a, 0x11, 18, 0, 1, 0x80}','{0x0d, 0x20, 0x69, 0x11, 18, 0, 1, 0x80}')
audio=audio.replace('halfword(request + 2) != 0x14c','halfword(request + 2) != 0x14b')
audio=audio.replace('{0x0d, 0x20, 0x4c, 0x11, 12, 0, 1, 0x80}','{0x0d, 0x20, 0x4b, 0x11, 12, 0, 1, 0x80}')
audio=audio.replace('halfword(request + 2) != 0x13d','halfword(request + 2) != 0x13c')
audio=audio.replace('{0x0d, 0x20, 0x3d, 0x11, 12, 0, 1, 0x80}','{0x0d, 0x20, 0x3c, 0x11, 12, 0, 1, 0x80}')
audio=audio.replace('halfword(request + 2) != 0x147','halfword(request + 2) != 0x146')
audio=audio.replace('size < 680','size != 584').replace('halfword(request + 4) != 680','halfword(request + 4) != 584')
audio=audio.replace('{0x0d, 0x20, 0x47, 0x11, 12, 0, 1, 0x80}','{0x0d, 0x20, 0x46, 0x11, 12, 0, 1, 0x80}')
audio=audio.replace('halfword(request + 2) != 0x161','halfword(request + 2) != 0x160')
audio=audio.replace('{0x0d, 0x20, 0x61, 0x11, 12, 0, 1, 0x80}','{0x0d, 0x20, 0x60, 0x11, 12, 0, 1, 0x80}')
# Logs must identify the actual ported M4 command numbers.
for old,new in [('0x132f','0x132d'),('0x13d','0x13c'),('0x113d','0x113c'),('0x114c','0x114b'),('0x1161','0x1160'),('0x161','0x160')]:
    code=code.replace(old,new)
audio='/* A7M4 6.02 opcode port: CP +b1750/+4f2cda, legacy HDMI audio format 0x304. */\n'+audio
(A/'hdmi-format-service.c').write_text(audio)
code=f'#define A7M4_DATE_GOT 0x{date_got:x}UL\nstatic int observe_date_add(void *,const void *,long);\nstatic void install_date_math_probe(unsigned long);\nstatic void install_boot_log_probe(unsigned long);\n'+code
code=code.replace('"HDMI_NOTIFY_",','"BOOT_LOG_", "DATE_CHECK_", "HDMI_NOTIFY_",',1)
code+=r'''
/* Observe the original date library. No date/model values are modified. */
static int observe_date_add(void *out,const void *in,long seconds) {
    static int (*native)(void *,const void *,long);
    if(!native)native=real_dlsym((void *)-1,"date_time_add_seconds");
    const unsigned char *p=in;char text[180];
    snprintf(text,sizeof text,"input=%u-%u-%uT%u:%u:%u delta=%ld caller=%p",p[0]|(p[1]<<8),p[2],p[3],p[4],p[5],p[6],seconds,__builtin_return_address(0));
    record("DATE_CHECK_ENTER ",text);
    if(!native){record("DATE_CHECK_ERROR ","original date library not available");__builtin_trap();}
    int result=native(out,in,seconds);
    snprintf(text,sizeof text,"native result=%d",result);record("DATE_CHECK_RETURN ",text);
    return result;
}
int date_time_add_seconds(void *out,const void *in,long seconds) {return observe_date_add(out,in,seconds);}
static void *date_math_continue __attribute__((used));
void capture_date_math(const unsigned char *p,long seconds,void *out) {
    char text[180];
    snprintf(text,sizeof text,"original app shim input=%u-%u-%uT%u:%u:%u delta=%ld out=%p",p[0]|(p[1]<<8),p[2],p[3],p[4],p[5],p[6],seconds,out);
    record("DATE_CHECK_APP ",text);
}
__asm__(
".text\n.globl date_math_trampoline\n.type date_math_trampoline, %function\ndate_math_trampoline:\n"
PROBE_SAVE_ARGS
"bl capture_date_math\n"
PROBE_RESTORE_ARGS
"stp x29,x30,[sp,#-0x40]!\nmov x29,sp\nstr x19,[sp,#0x10]\nmov x19,x2\n"
"adrp x16,date_math_continue\nldr x16,[x16,#:lo12:date_math_continue]\nbr x16\n"
);
extern void date_math_trampoline(void);
static void install_date_math_probe(unsigned long base) {
    unsigned long target=base+0x3797480UL;
    unsigned int *p=(unsigned int *)target;
    if(p[0]!=0xa9bc7bfd || p[1]!=0x910003fd || p[2]!=0xf9000bf3 || p[3]!=0xaa0203f3) {
        record("DATE_CHECK_PROBE_ERROR ","original M4 prologue mismatch");return;
    }
    if(mprotect((void *)(target&~4095UL),4096,7))return;
    date_math_continue=(void *)(target+16);
    p[0]=0x58000050;p[1]=0xd61f0200;*(unsigned long *)(target+8)=(unsigned long)date_math_trampoline;
    clear_cache_range((void *)target,16);
    record("DATE_CHECK_APP_BOUND ","original date math entry observed; original instructions and return preserved");
}

/* Mirror only sequence_boot's own original log calls. The entry probe saves
   all ABI arguments and NZCV, then replays the verified original prologue. */
static void *boot_log_continue __attribute__((used));
void capture_boot_log(const unsigned long *args) {
    unsigned long caller=args[9]-appfw_base;
    if(caller<0x3178000UL || caller>=0x317b000UL)return;
    char text[380];
    snprintf(text,sizeof text,"caller=app+%#lx fmt=%.100s x1=%#lx x2=%#lx x3=%#lx x4=%#lx x5=%#lx x6=%#lx x7=%#lx",
             caller,(const char *)args[0],args[1],args[2],args[3],args[4],args[5],args[6],args[7]);
    record("BOOT_LOG_CALL ",text);
}
__asm__(
".text\n.globl boot_log_trampoline\n.type boot_log_trampoline, %function\nboot_log_trampoline:\n"
PROBE_SAVE_ARGS
"mov x0,sp\nbl capture_boot_log\n"
PROBE_RESTORE_ARGS
"sub sp,sp,#0x200\nstp x29,x30,[sp,#-0x20]!\nmov x29,sp\nstr x19,[sp,#0x10]\n"
"adrp x16,boot_log_continue\nldr x16,[x16,#:lo12:boot_log_continue]\nbr x16\n"
);
extern void boot_log_trampoline(void);
static void install_boot_log_probe(unsigned long base) {
    unsigned long target=base+0x37258d4UL;
    unsigned int *p=(unsigned int *)target;
    if(p[0]!=0xd10803ff || p[1]!=0xa9be7bfd || p[2]!=0x910003fd || p[3]!=0xf9000bf3) {
        record("BOOT_LOG_ERROR ","original M4 logger prologue mismatch");return;
    }
    if(mprotect((void *)(target&~4095UL),4096,7))return;
    boot_log_continue=(void *)(target+16);
    p[0]=0x58000050;p[1]=0xd61f0200;*(unsigned long *)(target+8)=(unsigned long)boot_log_trampoline;
    clear_cache_range((void *)target,16);
    record("BOOT_LOG_BOUND ","sequence_boot original log arguments observed and forwarded unchanged");
}
'''
code+=r'''
int Fsys_Mount(const char *device,unsigned int flags,char *drive,const void *params) {
    int (*original)(const char *,unsigned int,char *,const void *)=real_dlsym((void *)-1,"Fsys_Mount");
    if(!original)return -1;
    int result=original(device,flags,drive,params);
    char text[220];snprintf(text,sizeof text,"Fsys_Mount device=%.80s flags=%#x result=%#x drive=%u; original forwarded unchanged",device,flags,result,drive?(unsigned char)*drive:0);
    record("BOOT_LOG_MEDIA_MOUNT ",text);
    if(!result && drive && getenv("QEMU_A7M4_FILE_MEDIA")) {
        int (*info)(unsigned char,void *)=real_dlsym((void *)-1,"Fsys_GetDriveInfo");
        int (*free_space)(unsigned char,void *)=real_dlsym((void *)-1,"Fsys_GetFreeSpace");
        unsigned long words[512]={0};
        if(info) {
            int rc=info((unsigned char)*drive,words);
            char detail[280];snprintf(detail,sizeof detail,"drive=%u result=%#x words=%#lx,%#lx,%#lx,%#lx,%#lx,%#lx; native readonly query",(unsigned char)*drive,rc,words[0],words[1],words[2],words[3],words[4],words[5]);record("BOOT_LOG_MEDIA_DRIVE_INFO ",detail);
        }
        if(free_space) {
            for(unsigned int i=0;i<512;++i)words[i]=0;
            int rc=free_space((unsigned char)*drive,words);
            char detail[220];snprintf(detail,sizeof detail,"drive=%u result=%#x words=%#lx,%#lx,%#lx,%#lx; native readonly query",(unsigned char)*drive,rc,words[0],words[1],words[2],words[3]);record("BOOT_LOG_MEDIA_FREE_SPACE ",detail);
        }
    }
    return result;
}
int mcmn_drv_open(const char *device,unsigned int flags,void **out) {
    int (*original)(const char *,unsigned int,void **)=real_dlsym((void *)-1,"mcmn_drv_open");
    if(!original)return -1;
    int result=original(device,flags,out);
    if(getenv("QEMU_A7M4_FILE_MEDIA")) {
        char text[220];snprintf(text,sizeof text,"device=%.100s flags=%#x result=%#x handle=%p; original forwarded unchanged",device?device:"(null)",flags,result,(!result&&out)?*out:0);
        record("BOOT_LOG_MEDIA_OPEN ",text);
    }
    return result;
}
int mcmn_drv_dummy_open(void *context) {
    int (*original)(void *)=real_dlsym((void *)-1,"mcmn_drv_dummy_open");
    if(!original)return -1;
    int result=original(context);
    if(getenv("QEMU_A7M4_FILE_MEDIA") && context) {
        const char *device=*(const char **)((char *)context+0x70);
        int fd=*(int *)((char *)context+0x98);
        char text[260];snprintf(text,sizeof text,"device=%.100s result=%#x fd=%d sector_bytes=%lu sectors=%lu status=%#x; original dummy file open forwarded unchanged",device?device:"(null)",result,fd,*(unsigned long *)((char *)context+0xb0),*(unsigned long *)((char *)context+0xb8),*(unsigned int *)((char *)context+0xa4));
        record("BOOT_LOG_MEDIA_DUMMY_OPEN ",text);
    }
    return result;
}
int mcmn_drv_debug_error_rootdevctrl(int error,unsigned int source,unsigned int line,void *context) {
    int (*original)(int,unsigned int,unsigned int,void *)=real_dlsym((void *)-1,"mcmn_drv_debug_error_rootdevctrl");
    if(!original)return error;
    int result=original(error,source,line,context);
    if(getenv("QEMU_A7M4_FILE_MEDIA")) {
        char text[200];snprintf(text,sizeof text,"error=%#x source=%#x line=%#x context=%p result=%#x; original root error retained",error,source,line,context,result);
        record("BOOT_LOG_MEDIA_ROOT_ERROR ",text);
    }
    return result;
}
int mcmn_drv_debug_error_devctrl(int error,unsigned int source,unsigned int line,void *context) {
    int (*original)(int,unsigned int,unsigned int,void *)=real_dlsym((void *)-1,"mcmn_drv_debug_error_devctrl");
    if(!original)return error;
    int result=original(error,source,line,context);
    if(getenv("QEMU_A7M4_FILE_MEDIA")) {
        char text[200];snprintf(text,sizeof text,"error=%#x source=%#x line=%#x context=%p result=%#x; original error retained",error,source,line,context,result);
        record("BOOT_LOG_MEDIA_DRIVER_ERROR ",text);
    }
    return result;
}
void mcmn_param_init(void) {
    void (*original)(void)=real_dlsym((void *)-1,"mcmn_param_init");
    if(!original || original==mcmn_param_init)return;
    original();
    if(!getenv("QEMU_A7M4_FILE_MEDIA"))return;
    int (*find)(const char *)=real_dlsym((void *)-1,"mcmn_param_getidfromdesc");
    unsigned int (*get)(int)=real_dlsym((void *)-1,"mcmn_param_getul");
    void (*set)(int,unsigned int)=real_dlsym((void *)-1,"mcmn_param_setul");
    if(!find || !get || !set || find("EXISTMEDIADRIVER")!=0x69 ||
       find("DBG_DRV_DUMMY_OMIT_WRITE")!=0xf9) {
        record("BOOT_LOG_MEDIA_CONFIG_ERROR ","original named parameter identities differ");return;
    }
    unsigned int previous=get(0x69);set(0x69,0);
    char text[180];snprintf(text,sizeof text,"EXISTMEDIADRIVER=%u->%u OMIT_WRITE=%u; original firmware file backend selected, isolated guest files only",previous,get(0x69),get(0xf9));
    record("BOOT_LOG_MEDIA_FILE_BACKEND ",text);
    if(getenv("QEMU_A7M4_VIRTUAL_CARD")) {
        if(find("DBG_DRV_DUMMY_RM1_STATUS")!=0xa2 || find("DBG_DRV_DUMMY_RM2_STATUS")!=0xa3 || find("DBG_DRV_DUMMY_RM3_STATUS")!=0xa4) {
            record("BOOT_LOG_MEDIA_CONFIG_ERROR ","original virtual-port status parameter identities differ");return;
        }
        /* These parameters describe dummy driver status, not the native
         * front-end insertion record. Preserve firmware defaults here. */
        char detail[180];snprintf(detail,sizeof detail,"RM1_STATUS=%u RM2_STATUS=%u RM3_STATUS=%u; original driver status defaults, insertion comes from front-end record",get(0xa2),get(0xa3),get(0xa4));record("BOOT_LOG_MEDIA_PORT_PROFILE ",detail);
    }
}
int observe_rm_status(void *self,unsigned int device,void *out) __asm__("_ZN24InfraMediaDetectThreadRM14GetInOutStatusEjPv");
int observe_rm_status(void *self,unsigned int device,void *out) {
    static int (*original)(void *,unsigned int,void *);
    if(!original)original=real_dlsym((void *)-1,"_ZN24InfraMediaDetectThreadRM14GetInOutStatusEjPv");
    if(!original)return 6;
    int result=original(self,device,out);
    char text[200];unsigned char *b=out;
    snprintf(text,sizeof text,"RM this=%p device=%#x result=%d status=%02x%02x%02x%02x%02x%02x; original forwarded unchanged",self,device,result,b[0],b[1],b[2],b[3],b[4],b[5]);
    record("BOOT_LOG_MEDIA_STATUS ",text);return result;
}
void observe_media_event(void *self,unsigned int first,unsigned int second,signed char third,signed char fourth,unsigned char fifth,unsigned short sixth) __asm__("_ZN26InfraMediaDetectThreadBase16NotifyInOutEventEjjaaht");
void observe_media_event(void *self,unsigned int first,unsigned int second,signed char third,signed char fourth,unsigned char fifth,unsigned short sixth) {
    void (*original)(void *,unsigned int,unsigned int,signed char,signed char,unsigned char,unsigned short)=real_dlsym((void *)-1,"_ZN26InfraMediaDetectThreadBase16NotifyInOutEventEjjaaht");
    if(!original)return;
    if(getenv("QEMU_A7M4_FILE_MEDIA")) {
        char text[220];snprintf(text,sizeof text,"device=%#x second=%#x third=%d fourth=%d fifth=%u sixth=%u; original notification forwarded unchanged",first,second,third,fourth,fifth,sixth);
        record("BOOT_LOG_MEDIA_EVENT ",text);
    }
    original(self,first,second,third,fourth,fifth,sixth);
}
void observe_rm_config(void *self,void *out) __asm__("_ZN24InfraMediaDetectThreadRM15GetRMConfigInfoEP16mcmnd_rmcfg_info");
void observe_rm_config(void *self,void *out) {
    void (*original)(void *,void *)=real_dlsym((void *)-1,"_ZN24InfraMediaDetectThreadRM15GetRMConfigInfoEP16mcmnd_rmcfg_info");
    if(!original)return;
    original(self,out);
    if(getenv("QEMU_A7M4_FILE_MEDIA") && out) {
        unsigned int *p=out;char text[360];
        snprintf(text,sizeof text,"words=%08x,%08x,%08x,%08x,%08x,%08x,%08x,%08x,%08x,%08x,%08x,%08x,%08x,%08x,%08x,%08x,%08x,%08x,%08x,%08x,%08x,%08x,%08x,%08x,%08x,%08x,%08x,%08x; original readonly config",p[0],p[1],p[2],p[3],p[4],p[5],p[6],p[7],p[8],p[9],p[10],p[11],p[12],p[13],p[14],p[15],p[16],p[17],p[18],p[19],p[20],p[21],p[22],p[23],p[24],p[25],p[26],p[27]);
        record("BOOT_LOG_MEDIA_RM_CONFIG ",text);
    }
}
void observe_media_info_event(void *self,void *info,signed char state) __asm__("_ZN24InfraMediaDetectThreadRM27NotifyInOutEventByMediaInfoEPNS_9MediaInfoEa");
void observe_media_info_event(void *self,void *info,signed char state) {
    void (*original)(void *,void *,signed char)=real_dlsym((void *)-1,"_ZN24InfraMediaDetectThreadRM27NotifyInOutEventByMediaInfoEPNS_9MediaInfoEa");
    if(!original)return;
    if(getenv("QEMU_A7M4_FILE_MEDIA") && info) {
        unsigned int *w=info;unsigned char *b=info;char text[260];
        snprintf(text,sizeof text,"state=%d device=%#x mask=%#x field18=%#x field1c=%#x field20=%#x field30=%u field32=%u; original MediaInfo retained",state,w[3],w[5],w[6],w[7],w[8],b[0x30],b[0x32]);record("BOOT_LOG_MEDIA_INFO_EVENT ",text);
    }
    original(self,info,state);
}
'''
code+=r'''
/* Observation only: forward the original fatal-signal/abort path unchanged. */
static void a7m4_trace_fatal(const char *operation,int signal_number,void *caller) {
    if(!getenv("QEMU_A7M4_DIAGNOSTIC_SINK"))return;
    char text[300];Dl_info info={0};
    real_dladdr(caller,&info);
    snprintf(text,sizeof text,"tid=%ld operation=%s signal=%d caller=%s+%#lx",syscall(178),operation,signal_number,info.dli_fname?info.dli_fname:"?",(unsigned long)caller-(unsigned long)info.dli_fbase);
    record("BOOT_LOG_FATAL_SIGNAL ",text);
    int fd=open("/proc/self/mem",0);if(fd<0)return;
    unsigned long first=(unsigned long)__builtin_frame_address(0),fp=first,frame[2];
    for(unsigned int n=0;n<24 && fp>=first && fp-first<1048576 && !(fp&15);++n) {
        if(syscall(67,fd,frame,sizeof frame,fp)!=sizeof frame)break;
        Dl_info origin={0};real_dladdr((void *)frame[1],&origin);
        snprintf(text,sizeof text,"tid=%ld frame=%u lr=%#lx origin=%s+%#lx",syscall(178),n,frame[1],origin.dli_fname?origin.dli_fname:"?",frame[1]-(unsigned long)origin.dli_fbase);
        record("BOOT_LOG_FATAL_STACK ",text);
        if(frame[0]<=fp)break;fp=frame[0];
    }
    close(fd);
}
int raise(int signal_number) {
    int (*original)(int)=real_dlsym((void *)-1,"raise");
    if(signal_number==6 || signal_number==3 || signal_number==11)
        a7m4_trace_fatal("raise",signal_number,__builtin_return_address(0));
    return original?original(signal_number):-1;
}
void abort(void) {
    void (*original)(void)=real_dlsym((void *)-1,"abort");
    a7m4_trace_fatal("abort",6,__builtin_return_address(0));
    if(original)original();
    syscall(94,134);__builtin_unreachable();
}
'''
(A/'menu-observe.c').write_text(code)
subprocess.run(['bash',str(A/'build-observers.sh')],check=True)
shutil.copyfile(A/'menu-observe.so',R/'simulation/menu-observe.so')
init=(W/'menu-init-services').read_text()
init=init.replace('echo NATIVE_MODULES_LOADED','export MENU_HEADLESS_OSD=1 MENU_FRAME_OBSERVE=1 MENU_OSD_OBSERVE=1 QEMU_SOFTWARE_LZ77=1\necho NATIVE_MODULES_LOADED')
if args.menu:init=init.replace('export MENU_HEADLESS_OSD=1','export MENU_APPLY_MENU=1\nexport MENU_HEADLESS_OSD=1')
if args.window:
    init=init.replace('echo NATIVE_MODULES_LOADED','/simulation/ramfb-viewer >/tmp/ramfb-stderr.log 2>&1 &\necho NATIVE_MODULES_LOADED')
init=init.replace('echo APPLICATION_LOG_BEGIN','/simulation/headless-osd-export; echo HEADLESS_OSD_EXPORT_STATUS=$?\necho APPLICATION_LOG_BEGIN')
init=init.replace('echo A7M4_BOOTSTRAP_DONE','''
for t in /proc/$(pidof im.elf)/task/*; do
  echo TASK_STATUS "$t"
  cat "$t/comm" "$t/wchan"
  case "$(cat "$t/comm")" in CameraBackgroun|IMCMN-DRV-RM|IMD-*|IWrapperImaging|AppFw|IWrapperHDMI|IWrapperBB|IWrapperBBSub|SeqQueueCommon|SeqQueueDispSwi|SeqQueueSetYuvO|SeqThreadPool*) /simulation/menu-regs "${t##*/}";; esac
done
cat /proc/$(pidof im.elf)/maps
cat /tmp/ramfb-viewer.status
echo A7M4_BOOTSTRAP_DONE''')
(W/('menu-init-menu' if args.menu else 'menu-init-display')).write_text(init)
report={'model':'ILCE-7M4','version':'6.02','libObj_addresses':{hex(k):hex(v) for k,v in mapping.items()},
 'app_imports':{hex(k):hex(v) for k,v in appgot.items()},'view_create_slot':hex(slot),'view_create_function':hex(original),
 'lz77_decoder':decoder,'menu_transition_enabled':args.menu,'framebuffer_global_evidence':'GRM_screenGetOnBitmap -> f37b0 loads GOT264a48 -> 2d0580'}
report['hdmi_audio']={'request':'0x32d','completion':'0x132d','enum':[0,1],'cp_request_to_legacy':'file+b1750 -> frame0x2004/cmd0x304','cp_completion':'file+4f2cda -> frame0x200d/cmd0x132d/status'}
report['display_info']={'request':'0x169','completion':'0x1169','bytes':18,'cp_evidence':'file+afbfc -> 1121 legacy dimensions at +8,+10,+12,+14 and aspects +16,+17'}
report['menu_controller']={'type':'19rep_menu_controller','vptr':'0x599e090','constructor':'0x1dc7504','mode':'0x354','factory':'0x1dc769c','vtable_got':'0x5a300a0','old_mode_0x346':'dlt24_controller; rejected for menu'}
(D/'menu-a7m4/display-address-profile.json').write_text(json.dumps(report,indent=2))
print('DISPLAY_PORT_PREPARED; view method',hex(original),'decoder',decoder,flush=True)
