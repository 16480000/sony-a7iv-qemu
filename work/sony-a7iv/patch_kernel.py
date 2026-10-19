"""Apply QEMU-only source changes and retain the exact source diff."""
from pathlib import Path
import difflib

SRC = Path('/opt/sony-a7iv/src/linux-kernel')
OUT = Path('/mnt/d/CodexWork/sony-a7iv-qemu/patches')
OUT.mkdir(exist_ok=True)
name = 'arch/arm64/Kconfig.platforms'
p = SRC / name
original = p.read_text()
old = '\tselect AUTO_IRQ_AFFINITY if SMP\n'
new = '\tselect AUTO_IRQ_AFFINITY if SMP && !ARCH_CXD900XX_QEMU\n'
if old in original:
    if original.count(old) != 1:
        raise RuntimeError('Unexpected Kconfig source')
    changed = original.replace(old, new)
    p.write_text(changed)
    (OUT / '0001-qemu-disable-physical-gic-affinity.patch').write_text(''.join(
        difflib.unified_diff(original.splitlines(True), changed.splitlines(True),
                             fromfile='a/' + name, tofile='b/' + name)))
elif new not in original:
    raise RuntimeError('Unknown Kconfig state')
print('QEMU physical GIC affinity selection disabled')

name = 'drivers/irqchip/irq-gic.c'
p = SRC / name
original = p.read_text()
old = '#ifdef CONFIG_OSAL_UDIF\n\tif (!gic_cnt) {\n\t\tudif_map_irq(gic_data[0].domain);\n\t}\n#endif /* CONFIG_OSAL_UDIF */'
new = '#if defined(CONFIG_OSAL_UDIF) && !defined(CONFIG_ARCH_CXD900XX_QEMU)\n\tif (!gic_cnt) {\n\t\tudif_map_irq(gic_data[0].domain);\n\t}\n#endif /* CONFIG_OSAL_UDIF && !CONFIG_ARCH_CXD900XX_QEMU */'
if old in original:
    if original.count(old) != 1:
        raise RuntimeError('Unexpected GIC source')
    changed = original.replace(old, new)
    p.write_text(changed)
    (OUT / '0002-qemu-skip-sony-physical-irq-map.patch').write_text(''.join(
        difflib.unified_diff(original.splitlines(True), changed.splitlines(True),
                             fromfile='a/' + name, tofile='b/' + name)))
elif new not in original:
    raise RuntimeError('Unknown GIC state')
print('QEMU does not apply the physical Sony UDIF interrupt map')

name = 'kernel/printk/printk.c'
p = SRC / name
original = p.read_text()
old = '#ifdef CONFIG_ARCH_EJ\n\tif (console_suspended && printk_pmdebug'
new = '#if defined(CONFIG_ARCH_EJ) && defined(CONFIG_PM_SLEEP)\n\tif (console_suspended && printk_pmdebug'
if old in original:
    if original.count(old) != 1:
        raise RuntimeError('Unexpected printk source')
    changed = original.replace(old, new)
    p.write_text(changed)
    (OUT / '0003-printk-build-without-power-management.patch').write_text(''.join(
        difflib.unified_diff(original.splitlines(True), changed.splitlines(True),
                             fromfile='a/' + name, tofile='b/' + name)))
elif new not in original:
    raise RuntimeError('Unknown printk state')
print('Suspend-specific printk code only built with PM_SLEEP')

name = 'drivers/udif/mach-cxd900xx/pm_core.c'
p = SRC / name
original = p.read_text()
old = '\t/* resume vector */\n\tif (~0UL == cxd90057_resume_vector) {\n\t\tprintk("resume vector: not defined\\n");\n\t} else {\n\t\tprintk("resume vector: 0x%09lx\\n", cxd90057_resume_vector);\n\t\tprintk("resume entry:  0x%09lx\\n", (unsigned long)virt_to_phys(cxd90057_resume));\n\t\t*(unsigned long *)phys_to_virt(cxd90057_resume_vector) = virt_to_phys(cxd90057_resume);\n\t}'
new = '#if !defined(CONFIG_EJ_SIMPLE_SUSPEND)\n' + old + '\n#endif /* !CONFIG_EJ_SIMPLE_SUSPEND */'
if new in original:
    pass
elif old in original:
    if original.count(old) != 1:
        raise RuntimeError('Unexpected PM source')
    changed = original.replace(old, new)
    p.write_text(changed)
    (OUT / '0004-simple-suspend-does-not-reference-omitted-resume-code.patch').write_text(''.join(
        difflib.unified_diff(original.splitlines(True), changed.splitlines(True),
                             fromfile='a/' + name, tofile='b/' + name)))
else:
    raise RuntimeError('Unknown PM state')
print('Simple suspend does not reference the excluded hardware resume assembly')

original = p.read_text()
old = '\twarm_boot_pm_end();'
new = '#ifdef CONFIG_WARM_BOOT_IMAGE\n\twarm_boot_pm_end();\n#endif /* CONFIG_WARM_BOOT_IMAGE */'
if new in original:
    pass
elif old in original:
    if original.count(old) != 1:
        raise RuntimeError('Unexpected warm-boot call')
    changed = original.replace(old, new)
    p.write_text(changed)
    (OUT / '0005-pm-end-only-calls-enabled-warm-boot-code.patch').write_text(''.join(
        difflib.unified_diff(original.splitlines(True), changed.splitlines(True),
                             fromfile='a/' + name, tofile='b/' + name)))
else:
    raise RuntimeError('Unknown warm-boot state')
print('Warm boot callback only compiled when that feature is present')
