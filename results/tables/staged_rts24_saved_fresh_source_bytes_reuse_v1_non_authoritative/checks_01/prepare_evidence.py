"""Freeze predecessor provenance and navigation before the one scoped edit."""
from capture_checks import ROOT, OUT, PRIOR, entry, read, save
import json

selected = entry.source_pins()
preserved = json.loads((PRIOR/'preservation_inventory.json').read_bytes())
for path in PRIOR.parent.rglob('*'):
    if path.is_file(): preserved[path.relative_to(ROOT).as_posix()] = entry.pin(path.read_bytes())
for name in json.loads((PRIOR/'document_checks.json').read_bytes())['document_pins']:
    preserved[name] = entry.pin((ROOT/name).read_bytes())
for name, expected in preserved.items(): assert entry.pin((ROOT/name).read_bytes()) == expected, name
save('preservation_inventory.json',preserved)
save('baseline_sources.json',selected)
save('navigation_before.json',{name:dict(header=(raw:=(ROOT/name).read_bytes()).partition(b'\n\n')[0].decode(),
    body=entry.pin(raw.partition(b'\n\n')[2])) for name in json.loads((PRIOR/'navigation_before.json').read_bytes())})
save('admission.json',dict(authority='DRAFT_NONAUTHORITATIVE',head='5c3e885cb3b6dd50479ad685593590d5bd0ade86',
    pytest_cap_seconds=160,static_cap_seconds=40,total_cap_seconds=200,
    initial_source_raw_bytes=sum(p['bytes'] for p in selected.values()),source_raw_cap_bytes=2*1024**2,
    mutable_sources=list(entry.NEW_SOURCES[1:3]),frozen_adapter_pin=selected[entry.NEW_SOURCES[0]],
    ordinary_only=True,actual_saved_F_execution=False,F_launch_admitted=False))
assert not entry.OUTPUT.parent.exists()
print(json.dumps(dict(preserved_paths=len(preserved),selected_sources=len(selected),
    initial_source_raw_bytes=sum(p['bytes'] for p in selected.values()),actual_saved_F_execution=False)))
