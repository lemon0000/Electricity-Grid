"""Bind final read-only audit notes and every existing packet artifact."""
import json
from capture_checks import ROOT, OUT, pin

pins = {p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in OUT.rglob('*')
    if p.is_file() and p.name != 'support_pins.json'}
(OUT/'support_pins.json').write_bytes((json.dumps(pins, sort_keys=True, indent=2)+'\n').encode())
print(json.dumps(dict(support_files=len(pins), actual_saved_F_execution=False)))
