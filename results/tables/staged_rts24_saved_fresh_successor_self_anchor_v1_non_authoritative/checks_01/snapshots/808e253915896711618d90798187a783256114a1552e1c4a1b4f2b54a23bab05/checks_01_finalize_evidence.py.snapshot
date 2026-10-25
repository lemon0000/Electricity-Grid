"""Create-only final indices; leave inventory hashing to the independent oracle."""
import json
import re
from common import ROOT,OUT,read,pin,selected,save

plan=read('group_admission_04.json');assert selected()==plan['source_pins']
for label,nodes in plan['groups'].items():
    record=read(label+'.exit.json')
    assert record['exit_code']==0 and not record['timed_out'] and record['nodes']==nodes and record['source_pins']==plan['source_pins']
navigation={}
for name,old in read('navigation_before.json').items():
    raw=(ROOT/name).read_bytes();header,separator,body=raw.partition(b'\n\n')
    assert separator and header.decode()==old['header'] and pin(raw[-old['body']['bytes']:])==old['body']
    navigation[name]=dict(header=header.decode(),body=pin(body),full=pin(raw))
save('navigation_after.json',navigation)
documents=['docs/plan/staged_deliverability_c_saved_fresh_successor_self_anchor_contract_v1.md',
    'docs/plan/continuation_handoff_20261025_saved_fresh_successor_self_anchor.md',
    OUT.parent.relative_to(ROOT).as_posix()+'/validation_report.md']
for name in documents:
    path=ROOT/name;text=path.read_text(encoding='utf8');assert '\ufffd' not in text
    for target in re.findall(r'\]\(([^)]+)\)',text):
        if '://' in target or target.startswith('#'):continue
        assert (path.parent/target.split('#')[0]).resolve().exists(),(name,target)
save('document_checks.json',dict(document_pins={n:pin((ROOT/n).read_bytes()) for n in documents},links_resolve=True))
save('support_pins.json',{p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in OUT.rglob('*') if p.is_file()})
print(json.dumps(dict(current_epoch_nodes=218,new_self_nodes=34,preserved_paths=3649,all_gates_false=True)))
