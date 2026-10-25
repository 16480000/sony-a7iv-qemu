set pagination off
set confirm off
set breakpoint pending on
target remote /opt/sony-a7iv/menu-a7m4/runs/sound-live-20261021/gdb.sock
python
import gdb, json, time
OUT = '/mnt/d/TMP/all-events.jsonl'
count = 0

class AllBreakpoint(gdb.Breakpoint):
    def stop(self):
        global count
        try:
            ident = int(gdb.parse_and_eval('$x0')) & 0xffffffff
            msg = int(gdb.parse_and_eval('$x1')) & 0xffffffffffffffff
            lr = int(gdb.parse_and_eval('$x30')) & 0xffffffffffffffff
        except Exception:
            return False
        data = ''
        header = ''
        try:
            data = bytes(gdb.selected_inferior().read_memory(msg, 64)).hex()
            header = bytes(gdb.selected_inferior().read_memory(msg - 24, 24)).hex()
        except Exception as error:
            data = 'ERR:' + str(error)
        count += 1
        if count <= 5000:
            try:
                with open(OUT, 'a') as out:
                    out.write(json.dumps({'t': time.time(), 'n': count, 'id': ident,
                                          'ptr': msg, 'lr': lr, 'header': header,
                                          'data': data}) + '\n')
                    out.flush()
            except Exception:
                pass
        return False

AllBreakpoint('*0xffffff80004c1bf8')
end
continue
