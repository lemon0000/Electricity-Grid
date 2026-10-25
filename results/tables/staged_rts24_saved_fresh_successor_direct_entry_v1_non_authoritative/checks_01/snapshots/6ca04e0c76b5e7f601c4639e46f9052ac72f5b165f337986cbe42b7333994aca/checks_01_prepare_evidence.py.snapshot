"""Freeze the previous epoch, all prior evidence, and navigation bodies."""
import json
from common import ROOT,OUT,PRIOR,SOURCE_PATHS,OUTPUT_PARENT,pin,selected,epoch,save

source=selected();preserved=json.loads((PRIOR/'preservation_inventory.json').read_bytes())
for path in PRIOR.parent.rglob('*'):
    if path.is_file():preserved[path.relative_to(ROOT).as_posix()]=pin(path.read_bytes())
for name in json.loads((PRIOR/'document_checks.json').read_bytes())['document_pins']:
    preserved[name]=pin((ROOT/name).read_bytes())
for name,expected in preserved.items():assert pin((ROOT/name).read_bytes())==expected,name
save('preservation_inventory.json',preserved)
save('baseline_sources.json',source)
save('navigation_before.json',{name:dict(header=(raw:=(ROOT/name).read_bytes()).partition(b'\n\n')[0].decode(),
    body=pin(raw.partition(b'\n\n')[2])) for name in json.loads((PRIOR/'navigation_before.json').read_bytes())})
save('admission.json',dict(authority='DRAFT_NONAUTHORITATIVE',head='ea2cd5e1629486158be6cfa6b8372bd43641a44a',
    previous_source_epoch=epoch(source),pytest_cap_seconds=240,static_cap_seconds=80,total_cap_seconds=320,
    mutable_sources=list(SOURCE_PATHS[1:]),ordinary_only=True,actual_saved_F_execution=False,F_launch_admitted=False))
assert not OUTPUT_PARENT.exists()
print(json.dumps(dict(preserved_paths=len(preserved),previous_epoch=epoch(source))))
