"""Read-only CP investigation; all addresses printed as original file offsets."""
from pathlib import Path
import sys, struct, re
sys.path.insert(0, '/usr/lib/python3/dist-packages')
import numpy as np
from capstone import Cs, CS_ARCH_ARM, CS_ARCH_ARM64, CS_MODE_THUMB
b=Path('/opt/sony-a7iv/menu-a7m4/runtime/analysis/menu-root/cp/cpapp-b.bin').read_bytes()
dis=Cs(CS_ARCH_ARM,CS_MODE_THUMB)
cmd=sys.argv[1]
if cmd=='strings':
    pattern=re.compile(b'|'.join(x.encode() for x in sys.argv[2:]),re.I)
    for m in re.finditer(rb'[\x20-\x7e\t]{4,}',b):
        if pattern.search(m.group()):print(f'{m.start():09x} VA={m.start()+0x108000:09x} {m.group().decode()}')
elif cmd=='range':
    start=int(sys.argv[2],0);end=start+int(sys.argv[3],0)
    for m in re.finditer(rb'[\x20-\x7e\t]{4,}',b[start:end]):print(f'{start+m.start():09x} {m.group().decode()}')
elif cmd=='ptr':
    for arg in sys.argv[2:]:
        v=int(arg,0);needle=struct.pack('<I',v);p=0;hits=[]
        while (p:=b.find(needle,p))>=0:hits.append(p);p+=1
        print(hex(v), [hex(x) for x in hits])
elif cmd=='same':
    start=int(sys.argv[2],0);n=int(sys.argv[3],0);needle=b[start:start+n];p=0;hits=[]
    while (p:=b.find(needle,p))>=0:
        if not p%2:hits.append(p)
        p+=1
    print(needle.hex(),[hex(x) for x in hits])
elif cmd in ('imm','immctx'):
    for arg in sys.argv[2:]:
        imm=int(arg,0);positions=set()
        for register in range(16):
            needle=struct.pack('<HH',0xf240|((imm>>12)&15)|(((imm>>11)&1)<<10),(((imm>>8)&7)<<12)|(register<<8)|(imm&255))
            p=0
            while (p:=b.find(needle,p))>=0:
                if not p%2:positions.add(p)
                p+=1
        print(hex(imm),[hex(x) for x in sorted(positions)])
        if cmd=='immctx':
            for p in sorted(positions):
                print(f'IMMEDIATE {imm:#x} AT FILE+{p:#x}')
                for i in dis.disasm(b[max(0,p-24):p+48],max(0,p-24)):print(f'{i.address:09x}: {i.mnemonic:10} {i.op_str}')
elif cmd=='xref':
    a=np.frombuffer(b[:len(b)&~1],dtype='<u2').astype(np.int64)
    idx=np.flatnonzero(((a[:-1]&0xf800)==0xf000)&((a[1:]&0xd000)==0xd000));h1=a[idx];h2=a[idx+1]
    s=(h1>>10)&1;j1=(h2>>13)&1;j2=(h2>>11)&1
    rel=(s<<24)|(((~(j1^s))&1)<<23)|(((~(j2^s))&1)<<22)|((h1&1023)<<12)|((h2&2047)<<1)
    rel=np.where(s,rel-(1<<25),rel);targets=idx*2+4+rel
    for arg in sys.argv[2:]:
        target=int(arg,0);found=idx[targets==target]*2
        print(hex(target),[hex(int(x)) for x in found])
elif cmd in ('dis','dish'):
    if cmd=='dish':dis.skipdata=True
    start=int(sys.argv[2],0);length=int(sys.argv[3],0)
    for i in dis.disasm(b[start:start+length],start):print(f'{i.address:09x}: {i.mnemonic:10} {i.op_str}')
elif cmd=='pinjson':
    import json,hashlib
    records=[]
    for ix in range(19):
        off=0xe4feec+ix*16
        typ,direction,number,owner=struct.unpack_from('<IIII',b,off)
        obj=struct.unpack_from('<I',b,0xe5001c+ix*4)[0]
        records.append(dict(index=ix,type=typ,direction=direction,number=number,owner=f'0x{owner:08x}',definition_file_offset=hex(off),definition_runtime_va=hex(off+0x108000),object_runtime_va=hex(obj),object_pointer_file_offset=hex(0xe5001c+ix*4),initial_state=1,initial_state_meaning='disconnected',initial_state_source_file_offsets=['0x4e2022','0x4e2028'],constructor_call_file_offset=hex(0x4f8010 if ix==0 else 0x4f803a+(ix-1)*0x22)))
    print(json.dumps(dict(firmware='/opt/sony-a7iv/menu-a7m4/runtime/analysis/menu-root/cp/cpapp-b.bin',sha256=hashlib.sha256(b).hexdigest(),scope='Original CP constructor definitions; initial state before later runtime connections, not live topology.',pin_constructor_file_offset='0x4e2006',pins=records),indent=2))
elif cmd=='hex':
    start=int(sys.argv[2],0);length=int(sys.argv[3],0)
    print(b[start:start+length].hex(' '))
elif cmd=='hdmifield':
    from capstone.arm import ARM_OP_MEM
    dis.detail=True
    code=list(dis.disasm(b[0x570000:0x57f000],0x570000))
    for ix,i in enumerate(code):
        if any(op.type==ARM_OP_MEM and op.mem.disp==0xdc for op in i.operands):
            print('FIELD REFERENCE')
            for j in code[max(0,ix-5):ix+7]:print(f'{j.address:09x}: {j.mnemonic:10} {j.op_str}')
elif cmd=='u32':
    start=int(sys.argv[2],0);length=int(sys.argv[3],0)
    for p in range(start,start+length,4):
        v=struct.unpack_from('<I',b,p)[0];s=''
        if 0x108000<=v<0x108000+len(b):
            q=v-0x108000
            s=repr(b[q:b.find(b'\0',q)].decode('ascii','replace')[:140])
        print(f'{p:09x}: {v:08x} {s}')
elif cmd in ('appdis','appstr','appfind','apphex','appimm'):
    sys.path.insert(0,'/mnt/c/Users/16483/Documents/Codex/2026-10-16/new-chat/work/sony-a1m2/pydeps')
    import io
    from elftools.elf.elffile import ELFFile
    raw=Path('/opt/sony-a7iv/menu-a7m4/runtime/analysis/menu-root/usr/lib/appFw.so').read_bytes()
    elf=ELFFile(io.BytesIO(raw))
    if cmd=='appimm':
        for arg in sys.argv[2:]:
            imm=int(arg,0);hits=[]
            for seg in elf.iter_segments():
                if seg['p_type']!='PT_LOAD' or not (seg['p_flags']&1):continue
                s=seg['p_offset'];a=np.frombuffer(raw[s:s+seg['p_filesz']-(seg['p_filesz']%4)],dtype='<u4')
                idx=np.flatnonzero(((a&0x7f800000)==0x52800000)&(((a>>5)&65535)==imm))
                hits.extend(hex(int(x)*4+seg['p_vaddr']) for x in idx)
            print(hex(imm),hits)
        sys.exit(0)
    if cmd=='appfind':
        for arg in sys.argv[2:]:
            needle=arg.encode() if not arg.startswith('0x') else int(arg,0).to_bytes(8,'little')
            p=0;hits=[]
            while (p:=raw.find(needle,p))>=0:
                seg=next((x for x in elf.iter_segments() if x['p_type']=='PT_LOAD' and x['p_offset']<=p<x['p_offset']+x['p_filesz']),None)
                va=p-seg['p_offset']+seg['p_vaddr'] if seg else p
                hits.append((hex(p),hex(va)));p+=1
            print(arg,hits)
        sys.exit(0)
    start=int(sys.argv[2],0);length=int(sys.argv[3],0)
    seg=next(x for x in elf.iter_segments() if x['p_type']=='PT_LOAD' and x['p_vaddr']<=start<x['p_vaddr']+x['p_filesz'])
    off=start-seg['p_vaddr']+seg['p_offset'];ad=Cs(CS_ARCH_ARM64,0);plt_names={}
    if cmd=='apphex':
        print(raw[off:off+length].hex(' '));sys.exit(0)
    if cmd=='appstr':
        print(repr(raw[off:raw.find(b'\0',off)].decode('utf-8','replace')));sys.exit(0)
    plt=elf.get_section_by_name('.plt');rela=elf.get_section_by_name('.rela.plt')
    if plt and rela:
        symbols=elf.get_section(rela['sh_link'])
        for n,rel in enumerate(rela.iter_relocations()):plt_names[plt['sh_addr']+32+n*16]=symbols.get_symbol(rel['r_info_sym']).name
    for i in ad.disasm(raw[off:off+length],start):
        name=plt_names.get(int(i.op_str[1:],16),'') if i.mnemonic in ('b','bl') and i.op_str.startswith('#0x') else ''
        print(f'{i.address:09x}: {i.mnemonic:10} {i.op_str}'+(' ; '+name if name else ''))
