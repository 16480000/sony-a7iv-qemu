import hashlib
import io
import json
import re
from pathlib import Path
import shutil
import stat
import struct
import subprocess
import sys

W=Path(__file__).resolve().parent
D=Path('/mnt/d/CodexWork/sony-a7iv-qemu')
REF=D/'a7c2-reference/repo/report/2026-10-17-qemu-native-camera/runtime/analysis'
A=Path('/opt/sony-a7iv/menu-a7m4/runtime/analysis')
R=A/'menu-root'
code=(REF/'menu-observe.c').read_text()
start=code.index('        appfw_base = (unsigned long)symbol - 0x1796918;')
end=code.index('        return observe_application_init;',start)
code=code[:start]+'        appfw_base = 0; /* A7M4: application offsets pending separate validation. */\n'+code[end:]
code=re.sub(r'static void \*(\w*continue\w*);',r'static void *\1 __attribute__((used));',code)
code=code.replace('"MENU_CONTROLLER_SEEN ",','"ENTER ", "RETURN_", "GPE_WORKER_BIND", "DMM_SERVICE_INIT", "MENU_CONTROLLER_SEEN ",',1)
(A/'menu-observe.c').write_text(code)
date=(REF/'seed-date-clock.c').read_text()
date=date.replace('if (get16(bytes(&initial) + 36) || get16(bytes(&initial) + 38) || get16(bytes(&initial) + 40))',
'''if ((get16(bytes(&initial) + 36) != 0 && get16(bytes(&initial) + 36) != 540) ||
            get16(bytes(&initial) + 38) || get16(bytes(&initial) + 40))''')
date=date.replace('return 6; /* Only the verified ALLLANG UTC default is supported. */', '''{
            printf("DATE_DEFAULT_RAW ");
            for (unsigned int i=20;i<48;++i) printf("%02x",bytes(&initial)[i]);
            printf("\\n");
            return 6; /* Inspect the M4 native timezone fields before adapting. */
        }''')
date=date.replace('long expected = seconds(&initial);',
'''/* Native M4 read operation 2 adds its retained +540-minute offset
           to the date passed through BY_BOOT (measured native-28 round trip). */
        long expected = seconds(&initial) + (long)(short)get16(bytes(&initial) + 36) * 60;''')
date=date.replace('if (elapsed < 0 || elapsed > 10) return 8;', '''
        printf("DATE_BOOT_READBACK expected=%ld actual=%ld elapsed=%ld timezone=%u\\n",expected,seconds(&current),elapsed,get16(bytes(&initial)+36));
        if (elapsed < 0 || elapsed > 10) return 8;''')
(A/'seed-date-clock.c').write_text(date)
if '--defer-build' not in sys.argv:
    subprocess.run(['bash',str(A/'build-observers.sh')],check=True)
    shutil.copyfile(A/'menu-observe.so',R/'simulation/menu-observe.so')
sys.path.insert(0,str(REF/'vendor/fwtool'))
from fwtool.archive import UnixFile
from fwtool.archive.fat import readFat,writeFat
with (D/'unpacked/firmware.fdat').open('rb') as f: header=f.read(512)
assert header[:8]==b'UDTRFIRM'
assert struct.unpack_from('<II',header,36)==(16973953,0)
assert header[32:34]==b'\x02\x06'
contents={'/DAT2':header[36:40],'/DAT3':header[40:44]}
files=[UnixFile(n,len(b),315532800,stat.S_IFREG|0o444,0,0,io.BytesIO(b)) for n,b in contents.items()]
fat=io.BytesIO()
writeFat(files,4*1024*1024,fat)
fat.seek(0)
assert {f.path:f.contents.read() for f in readFat(fat)}==contents
(R/'simulation/firmware-identity.fat').write_bytes(fat.getvalue())
(R/'simulation/firmware-version.dat4').write_bytes(header[32:34])
init=(W/'menu-init-bootstrap').read_text()
init=init.replace('for mod in stream stream2 osal_ulogio dmm grm_ma upm kikilog;', 'for mod in stream stream2 osal_ulogio dmm grm_ma;')
insertion='''
for mod in udate; do
  insmod /usr/kmod/$mod.ko; echo EXTRA_MODULE_STATUS "$mod" $?
done
mkdir -p /setting/updater /mnt
cp /simulation/firmware-version.dat4 /setting/updater/dat4
mknod /dev/ram1 b 1 1
ln -s /dev/ram1 /dev/nflasha1
dd if=/simulation/firmware-identity.fat of=/dev/ram1 bs=4096
/simulation/seed-power-on 1
echo POWER_SEED_STATUS=$?
insmod /usr/kmod/upm.ko
insmod /usr/kmod/kikilog.ko
/simulation/seed-date-clock
echo DATE_SEED_STATUS=$?
cat /proc/modules
export QEMU_NO_CP_UPDATER=1 QEMU_CAPID_SERVICE=1 QEMU_SA_ADDRESS_SERVICE=1
export QEMU_HDMI_FORMAT_SERVICE=1 QEMU_HDMI_PHOTO_SERVICE=1 QEMU_DMM_SERVICE=1
export QEMU_SOFTWARE_GPE=1 QEMU_GPE_RGBA4444=1 QEMU_DISPLAY_INFO_SERVICE=1
'''
init=init.replace('echo NATIVE_MODULES_LOADED',insertion+'\necho NATIVE_MODULES_LOADED')
init=init.replace('LD_PRELOAD=/simulation/basic-observe.so','LD_PRELOAD=/simulation/menu-observe.so')
init=init.replace('cat /tmp/loader.log','cat /tmp/menu-load.log')
(W/'menu-init-services').write_text(init)
print('A7M4_SERVICE_PORT_PREPARED (A7C2 application offsets disabled)',flush=True)
