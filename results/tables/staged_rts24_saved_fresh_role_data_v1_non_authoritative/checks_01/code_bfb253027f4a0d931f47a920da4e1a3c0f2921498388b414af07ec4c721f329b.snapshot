"""Create-only data-validation indices; no implementation imports."""
import base64
from hashlib import sha256
import json
from pathlib import Path
import re
OUT=Path(__file__).resolve().parent;ROOT=OUT.parents[3]
def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')
def pin(v):return dict(bytes=len(v),sha256=sha256(v).hexdigest())
def read(p):return json.loads(p.read_bytes())
def save(name,v):
    data=raw(v);assert len(data)<=1024**2
    with (OUT/name).open('xb') as f:f.write(data)
baseline=read(OUT/'baseline.json');plan=read(OUT/'admission.json');revision=read(OUT/'admission_revision_08.json')
sources={n:pin((ROOT/n).read_bytes()) for n in baseline['sources']};assert sources==plan['source_pins']
effective={n:v for n,v in plan['groups'].items() if n not in ('role_1','role_2','role_3','role_4')}
effective.update(revision['groups']);passed=[]
for n,nodes in effective.items():
    r=read(OUT/(n+'.exit.json'));h=read(OUT/(n+'.harness.json'))
    assert r['accepted'] and r['source_pins']==sources and h['pytest_exit_code']==0
    assert len(nodes)==len(set(h['passed_call_nodes'])) and set(nodes)==set(h['passed_call_nodes'])
    assert not h['failed_phases'] and not h['skipped_phases'];passed.extend(nodes)
assert len(passed)==len(set(passed))==480
navigation={}
for n,old in baseline['navigation'].items():
    data=(ROOT/n).read_bytes();header,sep,body=data.partition(b'\n\n')
    assert sep and header==base64.b64decode(old['header_base64']) and pin(body[-old['body']['bytes']:])==old['body']
    prefix=body[:-old['body']['bytes']];assert prefix.endswith(b'\n\n')
    navigation[n]=dict(header_base64=old['header_base64'],prefix_base64=base64.b64encode(prefix).decode(),
        before_full_pin=old['full'],before_body_pin=old['body'],after_body_pin=pin(body),after_full_pin=pin(data))
documents=['docs/plan/staged_deliverability_c_saved_fresh_role_data_scope_budget_v1.md',
    'docs/plan/continuation_handoff_20261025_saved_fresh_role_data.md',OUT.parent.relative_to(ROOT).as_posix()+'/validation_report.md']
assert sum((ROOT/n).stat().st_size for n in documents)<=1024**2
links=0
for name,text in [(n,(ROOT/n).read_text(encoding='utf8')) for n in documents]+[(n,base64.b64decode(v['prefix_base64']).decode('utf8')) for n,v in navigation.items()]:
    assert '\ufffd' not in text
    for target in re.findall(r'\]\(([^)]+)\)',text):
        if '://' in target or target.startswith('#'):continue
        assert (ROOT/name).parent.joinpath(target.split('#')[0]).resolve().exists(),(name,target)
        links+=1
save('document_checks.json',dict(navigation=navigation,documents={n:pin((ROOT/n).read_bytes()) for n in documents},checked_links=links))
save('validation_summary.json',dict(authority='DRAFT_NONAUTHORITATIVE',source_pins=sources,source_epoch=plan['source_epoch'],
    passed_nodes=480,regression_nodes=282,new_nodes=198,effective_labels=list(effective),
    actual_F=False,scientific_evidence_adopted=False,resource_admission=False,formal_result=False))
print(json.dumps(dict(passed_nodes=480,regression_nodes=282,new_nodes=198,checked_links=links,actual_F=False),sort_keys=True))
