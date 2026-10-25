"""Create-only indices over the immutable execution inventory; no ENTRY imports."""
from hashlib import sha256
import json
from pathlib import Path
import re

ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent;MAIN=OUT.parent/'checks_01'
def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def read(path):return json.loads(path.read_bytes())
def save(name,value):
    path=OUT/name;assert not path.exists();path.write_bytes((json.dumps(value,sort_keys=True,indent=2)+'\n').encode())
freeze=read(OUT/'execution_freeze.json')
assert {p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in MAIN.rglob('*') if p.is_file()}==freeze['files']
navigation={}
for name,old in read(MAIN/'navigation_before.json').items():
    raw=(ROOT/name).read_bytes();header,separator,body=raw.partition(b'\n\n')
    assert separator and header.decode()==old['header'] and pin(raw[-old['body']['bytes']:])==old['body']
    navigation[name]=dict(header=header.decode(),body=pin(body),full=pin(raw))
save('navigation_after.json',navigation)
documents=['docs/plan/staged_deliverability_c_saved_fresh_successor_direct_entry_contract_v1.md',
    'docs/plan/staged_deliverability_c_saved_fresh_successor_direct_entry_package_contract_v1.md',
    'docs/plan/continuation_handoff_20261025_saved_fresh_successor_direct_entry.md',
    OUT.parent.relative_to(ROOT).as_posix()+'/validation_report.md']
for name in documents:
    path=ROOT/name;text=path.read_text(encoding='utf8');assert '\ufffd' not in text
    for target in re.findall(r'\]\(([^)]+)\)',text):
        if '://' in target or target.startswith('#'):continue
        assert (path.parent/target.split('#')[0]).resolve().exists(),(name,target)
save('document_checks.json',dict(document_pins={n:pin((ROOT/n).read_bytes()) for n in documents},links_resolve=True))
save('support_pins.json',{p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in OUT.rglob('*') if p.is_file()})
print(json.dumps(dict(execution_files=freeze['count'],execution_bytes=freeze['bytes'],frozen_execution_unchanged=True,
    support_pin=pin((OUT/'support_pins.json').read_bytes()),all_gates_false=True)))
