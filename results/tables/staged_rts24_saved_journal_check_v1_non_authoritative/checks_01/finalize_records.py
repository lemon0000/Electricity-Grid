"""Bind the final ordinary integration and two disjoint regression terminals."""
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


def save(name,value):(OUT/name).write_text(json.dumps(value,indent=2,sort_keys=True)+'\n',encoding='utf-8')


if __name__=='__main__':
    labels={'chain_04':1,'bindings_02':15,'related_02a':12,'related_02b':12}
    records={n:json.loads((OUT/(n+'.exit.json')).read_bytes()) for n in labels}
    sources=records['chain_04']['source_pins'];groups={}
    for label,count in labels.items():
        record=records[label]
        assert record['exit_code']==0 and record['timed_out'] is False and record['source_pins_unchanged'] is True
        assert record['source_pins']==sources and record['timeout_seconds']==90
        assert (str(count)+' passed').encode() in (OUT/(label+'.stdout.log')).read_bytes()
        groups[label]=dict(passed=count,exit=pin(OUT/(label+'.exit.json')),stdout=pin(OUT/(label+'.stdout.log')))
    printed=[json.loads(line) for line in (OUT/'chain_04.stdout.log').read_text().splitlines() if line.startswith('{')]
    assert len(printed)==1;observation=printed[0];component=observation['source_pins'];assert len(component)==45
    for name,value in component.items():
        assert pin(ROOT/name)==value
        if name.endswith('.py'):ast.parse((ROOT/name).read_text(encoding='utf-8'),filename=name)
    assert all(component[n]==v for n,v in sources.items())
    save('component_source_pins.json',component);save('saved_journal_observation.json',observation)
    names=sorted({v.split('::')[0] for r in records.values() for v in r['argv'] if v.startswith('tests/')})
    argv=[sys.executable,'-B','-m','pytest',*names,'--collect-only','-q','-p','no:cacheprovider']
    collected=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=30)
    assert collected.returncode==0 and collected.stderr==b''
    nodes=[n for n in collected.stdout.decode().splitlines() if n.startswith('tests/') and '::' in n]
    assert len(nodes)==len(set(nodes))==40
    new=[n for n in nodes if n.startswith('tests/test_staged_rts24_saved_journal_check_v1.py::')];assert len(new)==16
    split=json.loads((OUT/'related_split_nodes.json').read_bytes())
    group_nodes={'chain_04':[n for n in new if 'exact_chain' in n],
        'bindings_02':[n for n in new if 'exact_chain' not in n],**split}
    flat=[n for group in group_nodes.values() for n in group]
    assert set(flat)==set(nodes) and len(flat)==len(set(flat))==40
    assert {n:len(v) for n,v in group_nodes.items()}==labels
    for label in split:assert [v for v in records[label]['argv'] if v.startswith('tests/')]==split[label]
    (OUT/'collection_01.stdout.log').write_bytes(collected.stdout);(OUT/'collection_01.stderr.log').write_bytes(collected.stderr)
    save('collection_01.exit.json',dict(argv=argv,exit_code=0,node_count=40,new_distinct=16,related_distinct=24,
        source_pins=sources,stdout=pin(OUT/'collection_01.stdout.log'),group_nodes=group_nodes))
    review=json.loads((OUT/'preseal_review.json').read_bytes())
    assert review['remaining_findings']==[] and review['source_pins']==sources
    docs=[ROOT/'docs/plan/staged_deliverability_c_saved_journal_check_contract_v1.md',
        ROOT/'docs/plan/continuation_handoff_20261024_saved_journal_check.md',OUT.parent/'validation_report.md']
    links=[]
    for path in docs:
        text=path.read_text(encoding='utf-8');assert '\ufffd' not in text
        for target in re.findall(r'\]\(([^)]+)\)',text):
            if target.startswith(('http://','https://','#')):continue
            assert (path.parent/target.split('#')[0]).exists(),(path,target)
            links.append(dict(source=path.relative_to(ROOT).as_posix(),target=target))
    save('document_checks.json',dict(document_pins={p.relative_to(ROOT).as_posix():pin(p) for p in docs},local_links=links))
    support=[OUT/n for n in ('run_checks.py','saved_checks.py','finalize_records.py','launch_related_split.py',
        'related_split_nodes.json','raw_log_whitespace_exceptions.json')]
    save('ordinary_check_summary.json',dict(authority='DRAFT_NONAUTHORITATIVE',source_pins=sources,groups=groups,
        component_source_pins=component,component_source_group='selected_only',
        support_pins={p.relative_to(ROOT).as_posix():pin(p) for p in support},
        scientific_evidence_adopted=False,journal_replayed=False,resource_admission=False,formal_result=False))
    print(json.dumps(dict(new_distinct_passed=16,related_distinct_passed=24,distinct_nodes=40,
        selected_sources=45,local_links_checked=len(links),remaining_preseal_findings=[])))
