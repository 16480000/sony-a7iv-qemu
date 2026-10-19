/* CXD90057 virtual DFS handshake, derived from ILCE-7M4 6.02 upm.ko.
 * SPDX-License-Identifier: GPL-2.0-or-later
 *
 * The observed client clears completion bits at 0xf1388f50, writes a mode
 * at +0xf5c, triggers at +0xf58 and polls (status & 0x101) == 1.
 * This models that transaction and remembers the selected mode. TCG has no
 * Sony MP clock tree; no physical clock switching or timing fidelity claimed.
 */
#include "qemu/osdep.h"
#include "hw/core/sysbus.h"
#include "qemu/module.h"
#include "qom/object.h"

#define TYPE_SONY_SCU_DFS "sony-scu-dfs"
OBJECT_DECLARE_SIMPLE_TYPE(SonyScuDfs, SONY_SCU_DFS)
struct SonyScuDfs {
    SysBusDevice parent_obj;
    MemoryRegion mmio;
    uint32_t regs[0x2000 / 4];
    uint64_t transitions;
};
static uint64_t scu_read(void *opaque, hwaddr offset, unsigned size)
{
    SonyScuDfs *s = opaque;
    return s->regs[offset / 4];
}
static void scu_write(void *opaque, hwaddr offset, uint64_t value, unsigned size)
{
    SonyScuDfs *s = opaque;
    if (offset == 0xf50) {
        s->regs[offset / 4] &= ~(uint32_t)value; /* completion W1C */
        return;
    }
    s->regs[offset / 4] = value;
    if (offset == 0xf58 && (value & 1)) {
        uint32_t mode = s->regs[0xf5c / 4] & 0xff;
        s->regs[0xf60 / 4] = mode;
        s->regs[0xf50 / 4] = (s->regs[0xf50 / 4] & ~0x100u) | 1u;
        s->transitions++;
    }
}
static const MemoryRegionOps scu_ops = {
    .read = scu_read,
    .write = scu_write,
    .endianness = DEVICE_LITTLE_ENDIAN,
    .valid.min_access_size = 4,
    .valid.max_access_size = 4,
};
static void scu_realize(DeviceState *dev, Error **errp)
{
    SonyScuDfs *s = SONY_SCU_DFS(dev);
    memory_region_init_io(&s->mmio, OBJECT(s), &scu_ops, s,
                          TYPE_SONY_SCU_DFS, 0x2000);
    sysbus_init_mmio(SYS_BUS_DEVICE(s), &s->mmio);
}
static void scu_class_init(ObjectClass *klass, const void *data)
{
    DEVICE_CLASS(klass)->realize = scu_realize;
}
static const TypeInfo scu_info = {
    .name = TYPE_SONY_SCU_DFS,
    .parent = TYPE_SYS_BUS_DEVICE,
    .instance_size = sizeof(SonyScuDfs),
    .class_init = scu_class_init,
};
static void scu_register_types(void) { type_register_static(&scu_info); }
type_init(scu_register_types)
