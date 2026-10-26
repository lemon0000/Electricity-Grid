"""Pre-edit byte/AST preservation for bounded wire data development."""
import ast
import base64
from hashlib import sha256
import json
from pathlib import Path
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
OLD=ROOT/'results/tables/staged_rts24_saved_fresh_wire_contract_v1_non_authoritative'
def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')
def pin(v):return dict(bytes=len(v),sha256=sha256(v).hexdigest())
def read(p):return json.loads(p.read_bytes())
def names(paths):return {p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in paths}
previous=read(OLD/'checks_01/baseline.json');preserved=dict(previous['preserved'])
preserved.update(names(p for p in OLD.rglob('*') if p.is_file()))
preserved.update({n:p for n,p in read(OLD/'checks_01/document_checks.json')['documents'].items() if n.startswith('docs/')})
assert len(preserved)==4333 and names(ROOT/n for n in preserved)==preserved
sources=names(ROOT/n for n in previous['sources']);assert sources==previous['sources']
selected=('experiments/staged_rts24_saved_fresh_adoption_v1.py','tests/test_staged_rts24_saved_fresh_adoption_v1.py','src/staged_rts24_saved_fresh_adoption_v1.py')
old_nodes={n:[sha256(ast.dump(v,include_attributes=False).encode()).hexdigest() for v in ast.parse((ROOT/n).read_bytes()).body] for n in selected}
snapshots={}
for n,p in sources.items():
    path=ROOT/'results/tables/staged_rts24_saved_fresh_role_data_v1_non_authoritative/checks_01'/('code_'+p['sha256']+'.snapshot')
    assert pin(path.read_bytes())==p;snapshots[n]=path.relative_to(ROOT).as_posix()
navigation={}
for n in previous['navigation']:
    data=(ROOT/n).read_bytes();header,sep,body=data.partition(b'\n\n');assert sep
    navigation[n]=dict(header_base64=base64.b64encode(header).decode(),body=pin(body),full=pin(data))
value=dict(authority='DRAFT_NONAUTHORITATIVE',base_head='cdcc931c9fee0939ec004e2f6de4aa380f663f80',sources=sources,
    preserved=preserved,old_nodes=old_nodes,source_snapshots=snapshots,navigation=navigation)
with (OUT/'baseline.json').open('xb') as f:f.write(raw(value))
print(json.dumps(dict(preserved_paths=4333,source_names=49,reused_source_snapshots=49,actual_F=False),sort_keys=True))
