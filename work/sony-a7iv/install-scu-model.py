from pathlib import Path
import shutil

src=Path('/opt/sony-a7iv/qemu-11.1.2')
local=Path(__file__).resolve().parent
shutil.copyfile(local/'sony_scu_dfs.c',src/'hw/misc/sony_scu_dfs.c')
path=src/'hw/misc/meson.build'
text=path.read_text()
line="system_ss.add(when: 'CONFIG_ARM_VIRT', if_true: files('sony_scu_dfs.c'))\n"
if line not in text: path.write_text(line+text)
path=src/'hw/arm/virt.c'
text=path.read_text()
marker='        DeviceState *busstub = qdev_new("sony-cxd-bus-stub");'
addition='''        /* A7M4 virtual power-mode handshake; independent of the fixed timer clock. */
        DeviceState *scu = qdev_new("sony-scu-dfs");
        sysbus_realize_and_unref(SYS_BUS_DEVICE(scu), &error_fatal);
        memory_region_add_subregion_overlap(sysmem, 0xf1388000,
                sysbus_mmio_get_region(SYS_BUS_DEVICE(scu), 0), 2);
'''
if addition not in text:
    assert text.count(marker)==1
    path.write_text(text.replace(marker,addition+marker))
print('INSTALLED_SCU_DFS_MODEL')
