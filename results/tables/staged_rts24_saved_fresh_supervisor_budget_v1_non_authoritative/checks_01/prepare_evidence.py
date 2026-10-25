"""Capture unchanged dependencies and old evidence before admission arithmetic."""
import json
from pathlib import Path
from capture_static import ROOT, OUT, PRIOR, pin, save

selected = json.loads((PRIOR/'admission.json').read_bytes())['source_pins']
assert len(selected) == 49
preserved = json.loads((PRIOR/'preservation_inventory.json').read_bytes())
for path in PRIOR.parent.rglob('*'):
    if path.is_file(): preserved[path.relative_to(ROOT).as_posix()] = pin(path.read_bytes())
for name in json.loads((PRIOR/'document_checks.json').read_bytes())['document_pins']:
    preserved[name] = pin((ROOT/name).read_bytes())
for name, expected in preserved.items(): assert pin((ROOT/name).read_bytes()) == expected, name
save('preservation_inventory.json', preserved)
navigation = {}
for name in json.loads((PRIOR/'navigation_before.json').read_bytes()):
    header, _, body = (ROOT/name).read_bytes().partition(b'\n\n')
    navigation[name] = dict(header=header.decode(), body=pin(body))
save('navigation_before.json', navigation)
save('admission.json', dict(authority='DRAFT_NONAUTHORITATIVE', head='e6871551f58c9872402d54e5da81d973f6c14abd',
    source_pins=selected, check_cap_seconds=90, check_attempt_cap_seconds=15, output_bytes=8*1024**2, output_files=128,
    source_changes_allowed=False, actual_saved_F_execution=False, native_calls=0, scientific_replays=0,
    F_launch_admitted=False, scientific_evidence_adopted=False, resource_admission=False, formal_result=False))
assert not (ROOT/'results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative').exists()
print(json.dumps(dict(selected_sources=49, preserved_paths=len(preserved), actual_saved_F_execution=False)))
