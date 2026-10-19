import json
import re
from pathlib import Path
import socket
import sys

run=Path('/opt/sony-a7iv/menu-a7m4/runs')/sys.argv[1]
with socket.socket(socket.AF_UNIX) as sock:
    sock.settimeout(4)
    sock.connect(str(run/'qmp.sock'))
    stream=sock.makefile('rwb')
    hello=json.loads(stream.readline())
    def execute(name,arguments=None):
        cmd={'execute':name}
        if arguments:cmd['arguments']=arguments
        stream.write(json.dumps(cmd).encode()+b'\n');stream.flush()
        while True:
            reply=json.loads(stream.readline())
            if 'event' not in reply:return reply
    execute('qmp_capabilities')
    result={}
    for name,cmd in [('status',None),('registers','info registers'),('irq','info irq')]:
        result[name]=execute('query-status') if not cmd else execute('human-monitor-command',{'command-line':cmd})
    execute('stop')
    try:
        result['scu_registers']=execute('human-monitor-command',{'command-line':'xp /5wx 0xf1388f50'})
        regs=execute('human-monitor-command',{'command-line':'info registers'})
        result['stopped_registers']=regs
        value=regs.get('return','')
        match=re.search(r'X29=([0-9a-f]+)',value)
        if match:
            fp=int(match[1],16)
            address=fp & ~4095
            result['stack_base']=hex(address)
            result['stack_save']=execute('human-monitor-command',{'command-line':f'memsave 0x{address:x} 4096 "/out/cpu-stack.bin"'})
    finally: execute('cont')
    (run/'qmp-snapshot.json').write_text(json.dumps(result,indent=2))
    print(json.dumps({k:v for k,v in result.items() if k not in ('registers','stopped_registers')},indent=2))
