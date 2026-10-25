"""Keep predecessor evidence and exact navigation before adding new context."""
import json
from common import ROOT,OUT,PRIOR,OUTPUT_PARENT,pin,selected,save,FROZEN_EPOCH

source=selected();preserved=json.loads((PRIOR/'preservation_inventory.json').read_bytes())
for path in PRIOR.parent.rglob('*'):
    if path.is_file(): preserved[path.relative_to(ROOT).as_posix()]=pin(path.read_bytes())
for name in json.loads((PRIOR/'document_checks.json').read_bytes())['document_pins']:
    preserved[name]=pin((ROOT/name).read_bytes())
for name,expected in preserved.items(): assert pin((ROOT/name).read_bytes())==expected,name
save('preservation_inventory.json',preserved)
save('navigation_before.json',{name:dict(header=(raw:=(ROOT/name).read_bytes()).partition(b'\n\n')[0].decode(),
    body=pin(raw.partition(b'\n\n')[2])) for name in json.loads((PRIOR/'navigation_before.json').read_bytes())})
save('admission.json',dict(authority='DRAFT_NONAUTHORITATIVE',head='860864eb8a6ae3926dda6b70781b9dac3aa4e058',
    source_pins=source,source_epoch=FROZEN_EPOCH,total_cap_seconds=90,source_edits_allowed=False,
    witness_cases=5,witness_cap_seconds=12,output_cap_bytes=8*1024**2,output_cap_files=128,
    actual_saved_F_execution=False,F_launch_admitted=False))
assert not OUTPUT_PARENT.exists()
print(json.dumps(dict(preserved_paths=len(preserved),selected_sources=49,source_epoch=FROZEN_EPOCH)))
