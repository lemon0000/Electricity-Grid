"""Create-only index of the bounded data-only checkpoint; no ENTRY imports."""
import json
import re
from common import ROOT,OUT,read,pin,selected,epoch,save

plan=read('group_admission_02.json');assert selected()==plan['source_pins']
for label,nodes in plan['groups'].items():
    receipt=read(label+'.exit.json');assert receipt['exit_code']==0 and receipt['nodes']==nodes
    assert receipt['source_epoch']==epoch(selected()) and receipt['source_pins_unchanged']
navigation={}
for name,old in read('navigation_before.json').items():
    raw=(ROOT/name).read_bytes();header,separator,body=raw.partition(b'\n\n')
    assert separator and header.decode()==old['header'] and pin(raw[-old['body']['bytes']:])==old['body']
    navigation[name]=dict(header=header.decode(),body=pin(body),full=pin(raw))
save('navigation_after.json',navigation)
documents=['docs/plan/staged_deliverability_c_saved_fresh_successor_data_validation_contract_v1.md',
    'docs/plan/continuation_handoff_20261025_saved_fresh_successor_data.md',
    OUT.parent.relative_to(ROOT).as_posix()+'/validation_report.md']
for name in documents:
    path=ROOT/name;text=path.read_text(encoding='utf-8');assert '\ufffd' not in text
    for target in re.findall(r'\]\(([^)]+)\)',text):
        if '://' in target or target.startswith('#'):continue
        assert (path.parent/target.split('#')[0]).resolve().exists(),(name,target)
save('document_checks.json',dict(document_pins={n:pin((ROOT/n).read_bytes()) for n in documents},links_resolve=True))
protected=read('preservation_inventory.json')
for name,expected in protected.items():assert pin((ROOT/name).read_bytes())==expected,name
save('support_pins.json',{p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in OUT.rglob('*') if p.is_file()})
print(json.dumps(dict(source_epoch=plan['source_epoch'],current_epoch_nodes=sum(map(len,plan['groups'].values())),
    preservation_paths=len(protected),documents=len(documents),all_gates_false=True)))
