"""Reproducible ordinary collection, link checks and development metadata."""
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
    (OUT/name).write_text(json.dumps(value,sort_keys=True,indent=2)+'\n',encoding='utf-8')


if __name__=='__main__':
    summary=json.loads((OUT/'ordinary_check_summary.json').read_bytes())
    for name,value in summary['source_pins'].items():assert pin(ROOT/name)==value
    names=[name for label in ('units_06','related_03') for name in json.loads((OUT/(label+'.exit.json')).read_bytes())['argv'] if name.startswith('tests/')]
    assert len(names)==len(set(names))==5
    argv=[sys.executable,'-B','-m','pytest',*names,'--collect-only','-q','-p','no:cacheprovider']
    start=time.perf_counter();result=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=30)
    (OUT/'collection_01.stdout.log').write_bytes(result.stdout);(OUT/'collection_01.stderr.log').write_bytes(result.stderr)
    nodes=[n for n in result.stdout.decode().splitlines() if n.startswith('tests/') and '::' in n]
    assert result.returncode==0 and result.stderr==b'' and len(nodes)==len(set(nodes))==213
    save('collection_01.exit.json',dict(argv=argv,exit_code=result.returncode,wall_seconds=time.perf_counter()-start,
        source_pins=summary['source_pins'],node_count=213,stdout=pin(OUT/'collection_01.stdout.log'),stderr=pin(OUT/'collection_01.stderr.log')))
    docs=[ROOT/'docs/plan/staged_deliverability_c_p2_terminal_budget_contract_v1.md',
        ROOT/'docs/plan/continuation_handoff_20261024_terminal_budget.md',OUT.parent/'validation_report.md']
    links=[]
    for path in docs:
        text=path.read_text(encoding='utf-8');assert '\ufffd' not in text
        for target in re.findall(r'\]\(([^)]+)\)',text):
            if target.startswith(('https://','http://','#')):continue
            assert (path.parent/target.split('#')[0]).exists(),(path,target)
            links.append(dict(source=path.relative_to(ROOT).as_posix(),target=target))
    save('document_checks.json',dict(local_links_checked=len(links),links=links,document_pins={p.relative_to(ROOT).as_posix():pin(p) for p in docs}))
    save('preseal_review.json',dict(authority='DRAFT_NONAUTHORITATIVE',review_kind='read_only_PRE_SEAL_adversarial_findings',
        reviewer='sol_reviewer; no writes or delegation',source_pins=summary['source_pins'],
        first_implementation_findings=[
            dict(severity='High',finding='file stat race in final accounting',resolution='file HANDLE/path/fstat/metadata and final inventory bookends'),
            dict(severity='High',finding='exception formatting can raise again',resolution='safe bounded error normalization and safe publication hook/unresolved'),
            dict(severity='High',finding='peak commit not sampled after quiesce',resolution='post-quiesce Job peak commit; narrow sampled RSS claim'),
            dict(severity='Medium',finding='worker identity not held across callbacks/publication',resolution='held ancestor identity and exact launcher bytes at all boundaries'),
            dict(severity='Medium',finding='guard return omitted own byte-cap assertion',resolution='record_image before return'),
            dict(severity='Medium',finding='oracle terminal and source binding absent',resolution='length_03 command/exit/script/stdout and exact current source pins'),
            dict(severity='Low',finding='context omitted parent cap and file slots',resolution='both record caps and both slots explicit')],
        second_round_low='overshot accounting wording narrowed to complete bounded inventory; otherwise unknown',
        final_reviewer_statement='Current PRE_SEAL review remaining findings empty; no official verdict, receipt, resource admission or run authority.',
        remaining_findings=[],official_verdict=None,receipt=None,seal=None,resource_admission=False,formal_result=False))
    summary['support_pins']={p.relative_to(ROOT).as_posix():pin(p) for p in (
        OUT/'run_checks.py',OUT/'saved_checks.py',OUT/'length_budget.py',Path(__file__))}
    summary['collection']=pin(OUT/'collection_01.exit.json')
    save('ordinary_check_summary.json',summary)
    print(json.dumps(dict(collection_distinct=213,local_links_checked=len(links),remaining_preseal_findings=[])))
