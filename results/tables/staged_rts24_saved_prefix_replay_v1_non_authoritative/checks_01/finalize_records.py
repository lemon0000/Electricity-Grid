"""Bind ordinary check terminals, selected sources, review and document evidence."""
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
    labels={'units_05':38,'saved_02':1,'related_02':126}
    records={label:json.loads((OUT/(label+'.exit.json')).read_bytes()) for label in labels}
    sources=records['units_05']['source_pins'];groups={}
    for label,count in labels.items():
        record=records[label]
        assert record['exit_code']==0 and record['timed_out'] is False and record['source_pins_unchanged'] is True
        assert record['source_pins']==sources
        groups[label]=dict(passed=count,exit=pin(OUT/(label+'.exit.json')),stdout=pin(OUT/(label+'.stdout.log')))
    for name,value in sources.items():assert pin(ROOT/name)==value
    def assignment(path,name):
        tree=ast.parse(path.read_text(encoding='utf-8'),filename=str(path))
        return next(node.value for node in tree.body if isinstance(node,ast.Assign)
            and any(isinstance(t,ast.Name) and t.id==name for t in node.targets))
    point=assignment(ROOT/'src/staged_rts24_saved_point_replay_v1.py','SOURCES')
    prefix=assignment(ROOT/'src/staged_rts24_saved_prefix_replay_v1.py','SOURCES')
    selected=ast.literal_eval(point)+ast.literal_eval(prefix.right)
    assert len(selected)==len(set(selected))==29
    component={n:pin(ROOT/n) for n in selected}
    for name in selected:
        if name.endswith('.py'):ast.parse((ROOT/name).read_text(encoding='utf-8'),filename=name)
    save('component_source_pins.json',component)
    names=sorted({name for record in records.values() for name in record['argv'] if name.startswith('tests/')})
    argv=[sys.executable,'-B','-m','pytest',*names,'--collect-only','-q','-p','no:cacheprovider']
    collected=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=30)
    assert collected.returncode==0 and collected.stderr==b''
    nodes=[n for n in collected.stdout.decode().splitlines() if n.startswith('tests/') and '::' in n]
    assert len(nodes)==len(set(nodes))==165
    assert sum(n.startswith('tests/test_staged_rts24_saved_prefix_replay_v1.py::') for n in nodes)==39
    (OUT/'collection_01.stdout.log').write_bytes(collected.stdout);(OUT/'collection_01.stderr.log').write_bytes(collected.stderr)
    save('collection_01.exit.json',dict(argv=argv,exit_code=0,node_count=len(nodes),source_pins=sources,
        stdout=pin(OUT/'collection_01.stdout.log'),new_distinct=39,related_distinct=126))
    printed=[json.loads(line) for line in (OUT/'saved_02.stdout.log').read_text().splitlines() if line.startswith('{')]
    assert len(printed)==1
    save('saved_prefix_observation.json',printed[0])
    review=json.loads((OUT/'preseal_review.json').read_bytes())
    assert review['remaining_findings']==[] and review['source_pins']==sources
    docs=[ROOT/'docs/plan/staged_deliverability_c_saved_prefix_replay_contract_v1.md',
        ROOT/'docs/plan/continuation_handoff_20261024_saved_prefix_replay.md',OUT.parent/'validation_report.md']
    links=[]
    for path in docs:
        text=path.read_text(encoding='utf-8');assert '\ufffd' not in text
        for target in re.findall(r'\]\(([^)]+)\)',text):
            if target.startswith(('http://','https://','#')):continue
            assert (path.parent/target.split('#')[0]).exists(),(path,target)
            links.append(dict(source=path.relative_to(ROOT).as_posix(),target=target))
    save('document_checks.json',dict(document_pins={p.relative_to(ROOT).as_posix():pin(p) for p in docs},local_links=links))
    save('ordinary_check_summary.json',dict(authority='DRAFT_NONAUTHORITATIVE',source_pins=sources,groups=groups,
        component_source_pins=component,component_source_group='selected_only',
        support_pins={p.relative_to(ROOT).as_posix():pin(p) for p in (OUT/'run_checks.py',OUT/'saved_checks.py',Path(__file__))},
        scientific_evidence_adopted=False,journal_replayed=False,resource_admission=False,formal_result=False))
    print(json.dumps(dict(new_distinct_passed=39,related_distinct_passed=126,distinct_nodes=165,
        selected_sources=len(component),local_links_checked=len(links),remaining_preseal_findings=[])))
