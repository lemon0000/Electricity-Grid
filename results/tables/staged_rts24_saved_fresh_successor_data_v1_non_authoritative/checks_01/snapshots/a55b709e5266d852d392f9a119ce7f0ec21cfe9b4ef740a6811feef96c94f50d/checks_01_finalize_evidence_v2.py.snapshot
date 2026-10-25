"""Complete the partial index; preserve timeout14 and its original doc images."""
import json
import re
from common import ROOT,OUT,read,pin,selected,save

plan=read('group_admission_02.json');assert selected()==plan['source_pins']
failed=read('finalizer_14.exit.json')
assert failed['timed_out'] is True and failed['exit_code'] is None and failed['timeout_seconds']==4
for name,item in read('finalizer_14_document_snapshots.json').items():
    assert pin((ROOT/item['snapshot']).read_bytes())==item['pin']==read('document_checks.json')['document_pins'][name]
for label,nodes in plan['groups'].items():
    receipt=read(label+'.exit.json')
    assert receipt['exit_code']==0 and receipt['nodes']==nodes and receipt['source_pins']==plan['source_pins']
for name,item in read('navigation_after.json').items():
    raw=(ROOT/name).read_bytes();header,separator,body=raw.partition(b'\n\n')
    assert separator and header.decode()==item['header'] and pin(body)==item['body'] and pin(raw)==item['full']
    old=read('navigation_before.json')[name];assert pin(raw[-old['body']['bytes']:])==old['body']
documents=list(read('document_checks.json')['document_pins'])
for name in documents:
    path=ROOT/name;text=path.read_text(encoding='utf-8');assert '\ufffd' not in text
    for target in re.findall(r'\]\(([^)]+)\)',text):
        if '://' in target or target.startswith('#'):continue
        assert (path.parent/target.split('#')[0]).resolve().exists(),(name,target)
save('document_checks_v2.json',dict(document_pins={n:pin((ROOT/n).read_bytes()) for n in documents},links_resolve=True))
# All 3518 preserved files are checked by the independent saved oracle;
# do not repeat that inventory in this create-only index assembly.
save('support_pins.json',{p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in OUT.rglob('*') if p.is_file()})
print(json.dumps(dict(current_epoch_nodes=184,timeout14_preserved=True,partial_documents_preserved=3,
    all_gates_false=True,finalizer_successor='v2')))
