"""Disassemble verified local firmware for manual ABI/protocol review."""
import argparse
import contextlib
import importlib.util
import io
from pathlib import Path
import sys

sys.path.insert(0, '/usr/lib/python3/dist-packages')
from capstone import Cs, CS_ARCH_ARM, CS_ARCH_ARM64, CS_MODE_THUMB

p = argparse.ArgumentParser()
p.add_argument('target', choices=['app', 'oldapp', 'obj', 'cp','string','df','bus'])
p.add_argument('address', type=lambda x: int(x, 0))
p.add_argument('length', type=lambda x: int(x, 0), nargs='?', default=256)
a = p.parse_args()
plt_names={}
w = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('comparison', w/'compare-elf-addresses.py')
m = importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()):
    spec.loader.exec_module(m)
if a.target == 'cp':
    raw = (m.NEW.parent.parent/'cp/cpapp-b.bin').read_bytes()
    off = a.address
    dis = Cs(CS_ARCH_ARM, CS_MODE_THUMB)
else:
    target = {'app': m.NEW/'appFw.so', 'oldapp': m.OLD/'appFw.so', 'obj': m.NEW/'libObj.so','string':m.NEW/'appFw.so', 'df':m.NEW/'dataflowInfraFramework.so','bus':m.NEW/'libBusPower.so'}[a.target]
    elf = m.Elf(target)
    if a.target=='string':print(repr(elf.cstr(a.address)));sys.exit(0)
    plt=elf.elf.get_section_by_name('.plt');rela=elf.elf.get_section_by_name('.rela.plt')
    if plt and rela:
        symbols=elf.elf.get_section(rela['sh_link'])
        for n,rel in enumerate(rela.iter_relocations()):
            plt_names[plt['sh_addr']+32+n*16]=symbols.get_symbol(rel['r_info_sym']).name
    raw, off = elf.raw, elf.offset(a.address)
    dis = Cs(CS_ARCH_ARM64, 0)
for insn in dis.disasm(raw[off:off+a.length], a.address):
    name=''
    if insn.mnemonic in ['b','bl'] and insn.op_str.startswith('#0x'):
        name=plt_names.get(int(insn.op_str[1:],16),'')
    print(f'{insn.address:09x}: {insn.mnemonic:9} {insn.op_str}'+(' ; '+name if name else ''))
