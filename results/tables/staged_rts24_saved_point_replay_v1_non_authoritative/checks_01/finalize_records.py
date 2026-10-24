"""Bind final source pins, independent review, test identities and document checks."""
import ast
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent


def pin(path):
    raw=path.read_bytes();return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def save(name,value):
    (OUT/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf-8')


if __name__=='__main__':
    labels={'units_08':47,'related_02':170}
    records={label:json.loads((OUT/(label+'.exit.json')).read_bytes()) for label in labels}
    sources=records['units_08']['source_pins'];groups={}
    for label,count in labels.items():
        record=records[label]
        assert record['exit_code']==0 and record['timed_out'] is False and record['source_pins_unchanged'] is True and record['source_pins']==sources
        groups[label]=dict(passed=count,exit=pin(OUT/(label+'.exit.json')),stdout=pin(OUT/(label+'.stdout.log')))
    for name,value in sources.items():
        assert pin(ROOT/name)==value
        if name.endswith('.py'):ast.parse((ROOT/name).read_text(encoding='utf-8'),filename=name)
    names=sorted({name for record in records.values() for name in record['argv'] if name.startswith('tests/')})
    argv=[sys.executable,'-B','-m','pytest',*names,'--collect-only','-q','-p','no:cacheprovider']
    collected=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=30)
    assert collected.returncode==0 and collected.stderr==b''
    nodes=[n for n in collected.stdout.decode().splitlines() if n.startswith('tests/') and '::' in n]
    assert len(nodes)==len(set(nodes))==217
    assert sum(n.startswith('tests/test_staged_rts24_saved_point_replay_v1.py::') for n in nodes)==47
    (OUT/'collection_01.stdout.log').write_bytes(collected.stdout);(OUT/'collection_01.stderr.log').write_bytes(collected.stderr)
    save('collection_01.exit.json',dict(argv=argv,exit_code=0,node_count=217,source_pins=sources,stdout=pin(OUT/'collection_01.stdout.log')))
    save('preseal_review.json',dict(authority='DRAFT_NONAUTHORITATIVE',kind='read_only_PRE_SEAL_findings',source_pins=sources,
        reviewer='sol_reviewer; no writing, subdelegation or native execution',
        closed_findings=[
            'whole-package historical guard counters cover local necessary inventory only; full reconciliation remains false',
            'all 20 loaded src module paths and bytes bound to 23 selected files',
            'raw/observer exact field sets and primitive domains; no extra authority declarations',
            'P2 materialization requires a nonnull registration SHA',
            'historical log path canonical string with relocation allowed'],
        additional_reviewed_boundaries=['outer quiet before disk/source reads','point resource rejection before model build',
            'nonzero quiet outer only permits local diagnostic','86 source reads and 6M+16 point reads; pack5/3 verified'],
        remaining_findings=[],official_verdict=None,receipt=None,seal=None,resource_admission=False,formal_result=False))
    docs=[ROOT/'docs/plan/staged_deliverability_c_scientific_adoption_dag_v1.md',
        ROOT/'docs/plan/staged_deliverability_c_saved_point_replay_contract_v1.md',
        ROOT/'docs/plan/continuation_handoff_20261024_saved_point_replay.md',OUT.parent/'validation_report.md']
    links=[]
    for path in docs:
        text=path.read_text(encoding='utf-8');assert '\ufffd' not in text
        for target in re.findall(r'\]\(([^)]+)\)',text):
            if target.startswith(('http://','https://','#')):continue
            assert (path.parent/target.split('#')[0]).exists(),(path,target)
            links.append(dict(source=path.relative_to(ROOT).as_posix(),target=target))
    save('document_checks.json',dict(document_pins={p.relative_to(ROOT).as_posix():pin(p) for p in docs},local_links=links))
    save('ordinary_check_summary.json',dict(authority='DRAFT_NONAUTHORITATIVE',source_pins=sources,groups=groups,
        support_pins={p.relative_to(ROOT).as_posix():pin(p) for p in (OUT/'run_checks.py',OUT/'saved_checks.py',Path(__file__))},
        scientific_evidence_adopted=False,resource_admission=False,formal_result=False))
    print(json.dumps(dict(new_passed=47,related_passed=170,distinct_nodes=217,local_links_checked=len(links),remaining_preseal_findings=[])))
