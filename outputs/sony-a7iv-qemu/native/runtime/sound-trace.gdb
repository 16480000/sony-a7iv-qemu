set pagination off
set confirm off
set breakpoint pending on
target remote /opt/sony-a7iv/menu-a7m4/runs/sound-feedback-20261021m/gdb.sock
python
import gdb, json, time
OUT = '/mnt/d/TMP/bb-events.jsonl'
count = 0

class SoundBreakpoint(gdb.Breakpoint):
    def stop(self):
        global count
        try:
            ident = int(gdb.parse_and_eval('$x0')) & 0xffffffff
            msg = int(gdb.parse_and_eval('$x1')) & 0xffffffffffffffff
            lr = int(gdb.parse_and_eval('$x30')) & 0xffffffffffffffff
        except Exception:
            return False
        if (ident & 0xffff) not in {0x747, 0x8fc, 0x83f, 0x86f, 0x8f7, 0x85c, 0x738, 0x7ec, 0x964, 0x5c5}:
            return False
        data = ''
        header = ''
        try:
            data = bytes(gdb.selected_inferior().read_memory(msg, 96)).hex()
            header = bytes(gdb.selected_inferior().read_memory(msg - 32, 32)).hex()
        except Exception as error:
            data = 'ERR:' + str(error)
        count += 1
        try:
            with open(OUT, 'a') as out:
                out.write(json.dumps({'t': time.time(), 'n': count, 'id': ident,
                                      'ptr': msg, 'lr': lr, 'header': header,
                                      'data': data}) + '\n')
                out.flush()
        except Exception:
            pass
        return False

SoundBreakpoint('*0xffffff80004c1bf8')
end
continue
