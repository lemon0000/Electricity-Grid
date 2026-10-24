"""Collect final ordinary-test identities and bind saved development evidence."""
import ast
from hashlib import sha256
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent


def pin(path):
    raw=path.read_bytes();return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def save(name,value):
    (OUT/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf-8')


if __name__=='__main__':
    labels={'units_06':47,'full_02':1,'related_01':213}
    records={label:json.loads((OUT/(label+'.exit.json')).read_bytes()) for label in labels}
    sources=records['units_06']['source_pins'];groups={}
    for label,count in labels.items():
        value=records[label]
        assert value['exit_code']==0 and value['timed_out'] is False and value['source_pins_unchanged'] is True and value['source_pins']==sources
        groups[label]=dict(passed=count,exit=pin(OUT/(label+'.exit.json')),stdout=pin(OUT/(label+'.stdout.log')))
    for name,value in sources.items():
        assert pin(ROOT/name)==value
        if name.endswith('.py'):ast.parse((ROOT/name).read_text(encoding='utf-8'),filename=name)
    names=sorted({name for value in records.values() for name in value['argv'] if name.startswith('tests/')})
    assert len(names)==6
    argv=[sys.executable,'-B','-m','pytest',*names,'--collect-only','-q','-p','no:cacheprovider']
    start=time.perf_counter();collected=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=30)
    assert collected.returncode==0 and collected.stderr==b''
    nodes=[n for n in collected.stdout.decode().splitlines() if n.startswith('tests/') and '::' in n]
    assert len(nodes)==len(set(nodes))==261
    new=[n for n in nodes if n.startswith('tests/test_staged_rts24_p2_outer_v1.py::')]
    assert len(new)==48 and len([n for n in new if 'full_319' in n])==1
    (OUT/'collection_01.stdout.log').write_bytes(collected.stdout);(OUT/'collection_01.stderr.log').write_bytes(collected.stderr)
    save('collection_01.exit.json',dict(argv=argv,exit_code=0,wall_seconds=time.perf_counter()-start,source_pins=sources,
        node_count=261,new_node_count=48,new_full_nodes=[n for n in new if 'full_319' in n],stdout=pin(OUT/'collection_01.stdout.log')))
    save('preseal_review.json',dict(authority='DRAFT_NONAUTHORITATIVE',kind='read_only_PRE_SEAL_findings',source_pins=sources,
        reviewer='sol_reviewer; no writing or subdelegation',
        closed_findings=[
            'post-parent publication bookends retain expected SHA and unknown publication outcome',
            'finish requires a prior construction attempt; no retry',
            'creator PID/thread and child owner identity continuity',
            'Binding/context/startup/publication/cleanup/failure state matrix',
            'checker startup schema verification separated from actual capture',
            'capture plus close failure retains both errors and original live cleanup capability',
            'legacy protocol oracle reaches the root allowlist using legacy launcher schema',
            'malformed/unprintable capture metadata normalized before exception construction'],
        remaining_findings=[],official_verdict=None,receipt=None,seal=None,resource_admission=False,formal_result=False))
    docs=[ROOT/'docs/plan/staged_deliverability_c_p2_outer_binding_contract_v1.md',
        ROOT/'docs/plan/continuation_handoff_20261024_outer_binding.md',OUT.parent/'validation_report.md']
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
        source_scope='selected_only',scientific_evidence_adopted=False,resource_admission=False,formal_result=False))
    print(json.dumps(dict(new_passed=48,related_passed=213,collection_distinct=261,local_links_checked=len(links),remaining_preseal_findings=[])))
