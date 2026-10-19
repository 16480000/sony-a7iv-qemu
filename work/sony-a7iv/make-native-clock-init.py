from pathlib import Path
w=Path(__file__).resolve().parent
source=(w/'menu-init-display').read_text()
lines=source.splitlines()
removed=[s for s in lines if s.startswith('/simulation/seed-date-clock') or s.startswith('echo DATE_SEED_STATUS=')]
assert len(removed)==2,removed
lines=[s for s in lines if s not in removed]
lines.insert(lines.index('echo NATIVE_MODULES_LOADED'),'echo DATE_CLOCK_NATIVE_UNINITIALIZED')
(w/'menu-init-clock-native').write_text('\n'.join(lines)+'\n')
