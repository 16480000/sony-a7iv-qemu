"""Owned VM serial commands, retaining logs across long runs and cold restarts."""
import re,secrets,time
from menu_live import FirmwareMonitor,clean_console

def serial_command(proc,console,command,timeout=90,monitor=None):
    monitor=monitor or FirmwareMonitor(console)
    monitor.check()
    marker='A7M4_COMMAND_DONE_'+secrets.token_hex(12)
    with console.open('rb') as reader:
        reader.seek(0,2)
        proc.stdin.write((command+"; rc=$?; printf '\\n"+marker+":%s\\n' \"$rc\"\n").encode())
        proc.stdin.flush()
        data=bytearray();deadline=time.monotonic()+timeout
        while time.monotonic()<deadline:
            monitor.check();data.extend(reader.read(65536))
            if len(data)>8*1024*1024:raise RuntimeError('单次串口输出超过限制')
            clean=clean_console(bytes(data))
            if b'Exception>' in clean:raise RuntimeError('固件进入异常监视器')
            match=re.search(rb'\n'+marker.encode()+rb':([0-9]+)\n',clean)
            if match:
                if int(match[1]):raise RuntimeError('guest 命令失败，返回码 '+match[1].decode())
                return bytes(data)
            if proc.poll() is not None:raise RuntimeError('VM 进程提前退出')
            time.sleep(.05)
    raise TimeoutError('串口命令缺少完成标记')
