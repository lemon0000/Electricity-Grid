"""Freeze the old source epoch and predecessor packages before editing ENTRY/tests."""
import json
from pathlib import Path
from capture_checks import ROOT, OUT, PRIOR, entry, save

selected = entry.source_pins()
preserved = json.loads((PRIOR/'preservation_inventory.json').read_bytes())
for path in PRIOR.parent.rglob('*'):
    if path.is_file(): preserved[path.relative_to(ROOT).as_posix()] = entry.pin(path.read_bytes())
for name in json.loads((PRIOR/'document_checks.json').read_bytes())['document_pins']:
    preserved[name] = entry.pin((ROOT/name).read_bytes())
for name in (entry.NEW_SOURCES[0], 'tests/test_staged_rts24_process_guard_v1.py'):
    preserved[name] = entry.pin((ROOT/name).read_bytes())
for name, expected in preserved.items(): assert entry.pin((ROOT/name).read_bytes()) == expected, name
save('preservation_inventory.json', preserved)
navigation = {}
for name in json.loads((PRIOR/'navigation_before.json').read_bytes()):
    header, _, body = (ROOT/name).read_bytes().partition(b'\n\n')
    navigation[name] = dict(header=header.decode(), body=entry.pin(body))
save('navigation_before.json', navigation)
save('baseline_sources.json', selected)
save('admission.json', dict(authority='DRAFT_NONAUTHORITATIVE', head='41ed32c08519ccacbb932bddc2b16babb3132cb3',
    pytest_cap_seconds=160, static_cap_seconds=40, total_cap_seconds=200, ordinary_only=True,
    actual_saved_F_execution=False, F_launch_admitted=False, source_group_size=49,
    mutable_sources=list(entry.NEW_SOURCES[1:3]), frozen_adapter_pin=selected[entry.NEW_SOURCES[0]]))
assert not entry.OUTPUT.parent.exists()
print(json.dumps(dict(preserved_paths=len(preserved), selected_sources=len(selected), actual_saved_F_execution=False)))
