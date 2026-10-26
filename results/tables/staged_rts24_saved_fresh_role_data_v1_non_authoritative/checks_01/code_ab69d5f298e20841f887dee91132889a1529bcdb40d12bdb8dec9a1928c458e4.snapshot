"""Pre-edit ordinary byte/AST inventory; no project implementation import."""
import ast
from hashlib import sha256
import json
from pathlib import Path

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
OLD=ROOT/'results/tables/staged_rts24_saved_fresh_upstream_archive_v1_non_authoritative'
def raw(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')
def pin(data):return dict(bytes=len(data),sha256=sha256(data).hexdigest())
def read(path):return json.loads(path.read_bytes())
def names(paths):return {p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in paths}
def nodes(data):return [sha256(ast.dump(n,include_attributes=False).encode()).hexdigest() for n in ast.parse(data).body]

previous=read(OLD/'checks_01/baseline.json')
preserved=dict(previous['preserved']);preserved.update(names(p for p in OLD.rglob('*') if p.is_file()))
assert len(preserved)==4123
assert all(pin((ROOT/n).read_bytes())==expected for n,expected in preserved.items())
sources=names(ROOT/n for n in previous['sources']);assert sources==previous['sources'] and len(sources)==49
selected=('experiments/staged_rts24_saved_fresh_adoption_v1.py','tests/test_staged_rts24_saved_fresh_adoption_v1.py','src/staged_rts24_saved_fresh_adoption_v1.py')
navigation={}
for n in read(OLD/'checks_01/navigation_migration.json'):
    data=(ROOT/n).read_bytes();header,separator,body=data.partition(b'\n\n');assert separator
    navigation[n]=dict(header_base64=__import__('base64').b64encode(header).decode(),body=pin(body),full=pin(data))
baseline=dict(authority='DRAFT_NONAUTHORITATIVE',base_head='e4e02343ffceb3605fe839dbe6646ea7fba9cbd1',
    preserved=preserved,sources=sources,old_nodes={n:nodes((ROOT/n).read_bytes()) for n in selected},navigation=navigation,
    actual_F=False,scientific_evidence_adopted=False,resource_admission=False,formal_result=False)
with (OUT/'baseline.json').open('xb') as stream:stream.write(raw(baseline))
print(json.dumps(dict(preserved_paths=len(preserved),source_names=len(sources),old_nodes={n:len(v) for n,v in baseline['old_nodes'].items()},actual_F=False),sort_keys=True))
