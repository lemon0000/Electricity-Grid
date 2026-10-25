"""Bind the completed read-only packet and prepend current navigation."""
import json
from pathlib import Path
import re
from capture_checks import ROOT, OUT, OWNER, pin


def save(name, value): (OUT/name).write_bytes((json.dumps(value, sort_keys=True, indent=2)+'\n').encode())


value = json.loads((OUT/'binding_completion_01.exit.json').read_bytes())
assert value['exit_code'] == 0 and value['wall_seconds'] == 30.625 and value['source_pins_unchanged']
old = json.loads((OWNER/'development_summary.json').read_bytes())
assert value['source_pins'] == old['source_pins'] and len(set(value['nodes']+old['final_nodeids'])) == 161
handoff = 'continuation_handoff_20261025_saved_fresh_owner_completion.md'
navigation = json.loads((OUT/'navigation_before.json').read_bytes())
for name, before in navigation.items():
    path = ROOT/name; raw = path.read_bytes()
    assert pin(raw[-before['body']['bytes']:]) == before['body']
    target = handoff if Path(name).parent.as_posix() == 'docs/plan' else '../plan/'+handoff
    prefix = ('2026-10-25 saved owner相关绑定补验完成：见[最新交接]('+target+')。源码不变的18节点30.625s终态通过，与前143同SF49/三源snapshot、互斥合计161；两批预算225.639/240s与30.625/45s分别保存，原失败/超时不计通过。实际saved F/issuer/supervise/public CLI以及科学采用、资源和正式门禁仍未开放。\n\n').encode()
    head, separator, body = raw.partition(b'\n\n')
    if prefix not in raw: path.write_bytes(head+separator+prefix+body)
documents = [ROOT/'docs/plan'/handoff,
    ROOT/'docs/plan/staged_deliverability_c_saved_fresh_owner_binding_completion_contract_v1.md',
    OUT.parent/'validation_report.md']
for path in documents:
    for target in re.findall(r'\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
        if '://' not in target: assert (path.parent/target.split('#')[0]).resolve().exists(), (path, target)
save('document_checks.json', dict(authority='DRAFT_NONAUTHORITATIVE', links_resolve=True,
    document_pins={p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in documents}))
save('unit_node_closure.json', dict(authority='DRAFT_NONAUTHORITATIVE', previous_nodes=old['final_nodeids'],
    new_nodes=value['nodes'], union_nodes=old['final_nodeids']+value['nodes'], same_SF49=True, unique_nodes=161,
    actual_saved_F_execution=False, F_launch_admitted=False, scientific_evidence_adopted=False,
    resource_admission=False, formal_result=False))
save('support_pins.json', {p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in OUT.rglob('*')
    if p.is_file() and p.name != 'support_pins.json'})
print(json.dumps(dict(unique_nodes=161, source_pins_unchanged=True, document_links_resolve=True)))
