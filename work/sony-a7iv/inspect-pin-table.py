"""Read the original AP pin name table; this is not active CP topology."""
import contextlib,importlib.util,io,json,struct
from pathlib import Path
w=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('comparison',w/'compare-elf-addresses.py')
m=importlib.util.module_from_spec(spec)
with contextlib.redirect_stdout(io.StringIO()):spec.loader.exec_module(m)
app=m.Elf(m.NEW/'appFw.so');rows=[]
for n in range(50):
    va=0x575de48+n*8
    value=app.q(va)
    row={'index':n,'entry':hex(va),'string_address':hex(value),'name':app.cstr(value)}
    rows.append(row)
out=m.D/'menu-a7m4/original-ap-pin-names.json'
out.write_text(json.dumps(rows,indent=2))
print(json.dumps(rows,indent=2));print('Saved',out)
