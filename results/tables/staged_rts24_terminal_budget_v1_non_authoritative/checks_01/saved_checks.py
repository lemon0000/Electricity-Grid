"""Stdlib evidence/preservation bookends; never import scientific code."""
import ast
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[4]
OUT=Path(__file__).resolve().parent
PRIOR=ROOT/'results/tables/staged_rts24_p2_package_check_v1_non_authoritative'
NAV=('docs/plan/staged_deliverability_c_scope_and_budget_plan_v1.md',
    'docs/plan/科研项目执行步骤.md','docs/model_spec/blocker_register.md')


def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())


def run_saved(label,script,expected=None,source_pins=None):
    prefix=OUT/label
    assert not prefix.with_suffix('.exit.json').exists()
    start=time.perf_counter()
    argv=[sys.executable,'-B',str(script)]
    result=subprocess.run(argv,cwd=ROOT,capture_output=True,timeout=45)
    prefix.with_suffix('.stdout.json').write_bytes(result.stdout)
    prefix.with_suffix('.stderr.log').write_bytes(result.stderr)
    record=dict(argv=argv,exit_code=result.returncode,wall_seconds=time.perf_counter()-start,script=pin(script.read_bytes()),
        stdout=pin(result.stdout),stderr=pin(result.stderr),timeout_seconds=45)
    if source_pins is not None:record['source_pins']=source_pins
    if expected is not None:record['exact_prior_stdout']=result.stdout==expected.read_bytes()
    prefix.with_suffix('.exit.json').write_text(json.dumps(record,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    assert result.returncode==0 and result.stderr==b''
    if expected is not None:assert record['exact_prior_stdout']


def bootstrap():
    # All paths in the published checkpoint, plus its 440 preserved predecessors.
    paths=set(json.loads((PRIOR/'postcheck_01/prior_preservation_inventory.json').read_bytes()))
    changed=subprocess.check_output(['git','diff-tree','--no-commit-id','--name-only','-r','-z','HEAD'],cwd=ROOT)
    paths.update(n.decode('utf-8') for n in changed.split(b'\0') if n)
    preserved={}
    navigation={}
    for name in sorted(paths):
        raw=(ROOT/name).read_bytes()
        blob=subprocess.check_output(['git','show','HEAD:'+name],cwd=ROOT)
        assert raw==blob,('prior path changed before bootstrap',name)
        if name in NAV:navigation[name]=pin(raw)
        else:preserved[name]=pin(raw)
    (OUT/'preservation_inventory.json').write_text(json.dumps(preserved,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    (OUT/'navigation_original_bytes.json').write_text(json.dumps(navigation,sort_keys=True,indent=2)+'\n',encoding='utf-8')
    run_saved('prior_01',PRIOR/'postcheck_01/postcheck.py',PRIOR/'postcheck_01/saved_01.stdout.json')
    run_saved('length_01',OUT/'length_budget.py')
    print(json.dumps(dict(preserved_paths=len(preserved),navigation_tails=len(navigation),prior_stdout_reproduced=True)))


def verify():
    preserved=json.loads((OUT/'preservation_inventory.json').read_bytes())
    for name,value in preserved.items():assert pin((ROOT/name).read_bytes())==value,('preservation drift',name)
    tails=json.loads((OUT/'navigation_original_bytes.json').read_bytes())
    bodies=json.loads((OUT/'navigation_tail_inventory.json').read_bytes())
    for name,value in tails.items():
        raw=(ROOT/name).read_bytes();body=bodies[name]['body'];old_body=raw[-body['bytes']:]
        assert raw.split(b'\n\n',1)[0].decode('utf-8')==bodies[name]['header'],('navigation header drift',name)
        assert pin(old_body)==body and pin(bodies[name]['header'].encode('utf-8')+b'\n\n'+old_body)==value,('navigation tail drift',name)
    selected=json.loads((OUT/'ordinary_check_summary.json').read_bytes())
    for name,value in selected['source_pins'].items():
        assert pin((ROOT/name).read_bytes())==value,('current source drift',name)
        if name.endswith('.py'):ast.parse((ROOT/name).read_text(encoding='utf-8-sig'),filename=name)
    for label,expected in selected['groups'].items():
        record=json.loads((OUT/(label+'.exit.json')).read_bytes())
        assert record['exit_code']==0 and record['timed_out'] is False and record['source_pins_unchanged'] is True
        assert record['source_pins']==selected['source_pins']
        assert (str(expected['passed'])+' passed').encode() in (OUT/(label+'.stdout.log')).read_bytes()
        assert pin((OUT/(label+'.exit.json')).read_bytes())==expected['exit']
        assert pin((OUT/(label+'.stdout.log')).read_bytes())==expected['stdout']
    for label in ('units_01','units_02'):
        failure=json.loads((OUT/(label+'.exit.json')).read_bytes());assert failure['exit_code']==1 and failure['timed_out'] is False
    for label in ('prior_01','prior_projection_01','length_01','length_02',selected['length_label']):
        record=json.loads((OUT/(label+'.exit.json')).read_bytes());assert record['exit_code']==0
        assert pin((OUT/(label+'.stdout.json')).read_bytes())==record['stdout']
        assert (OUT/(label+'.stderr.log')).read_bytes()==b''
    assert (OUT/'prior_01.stdout.json').read_bytes()==(PRIOR/'postcheck_01/saved_01.stdout.json').read_bytes()
    assert (OUT/'prior_projection_01.stdout.json').read_bytes()==(PRIOR/'postcheck_01/saved_01.stdout.json').read_bytes()
    projected=json.loads((OUT/'prior_projection_01.exit.json').read_bytes())
    assert projected['script']==pin((OUT/'reproduce_navigation_view.py').read_bytes())
    historical=json.loads((OUT/'prior_after_01.exit.json').read_bytes())
    assert historical['exit_code']==1 and b'document or AST drift' in (OUT/'prior_after_01.stderr.log').read_bytes()
    budget=json.loads((OUT/(selected['length_label']+'.stdout.json')).read_bytes())
    assert budget['process_encoding_upper_bound']==92033 and budget['parent_encoding_upper_bound']==101080
    length=json.loads((OUT/(selected['length_label']+'.exit.json')).read_bytes())
    assert length['source_pins']==selected['source_pins'] and length['script']==pin((OUT/'length_budget.py').read_bytes())
    assert length['argv']==[sys.executable,'-B',str(OUT/'length_budget.py')]
    for name,value in selected['support_pins'].items():assert pin((ROOT/name).read_bytes())==value
    collection=json.loads((OUT/'collection_01.exit.json').read_bytes())
    assert pin((OUT/'collection_01.exit.json').read_bytes())==selected['collection']
    assert collection['exit_code']==0 and collection['source_pins']==selected['source_pins']
    assert pin((OUT/'collection_01.stdout.log').read_bytes())==collection['stdout']
    nodes=[n for n in (OUT/'collection_01.stdout.log').read_text().splitlines() if n.startswith('tests/') and '::' in n]
    assert len(nodes)==len(set(nodes))==collection['node_count']==213
    assert (OUT/'collection_01.stderr.log').read_bytes()==b''
    review=json.loads((OUT/'preseal_review.json').read_bytes())
    assert review['source_pins']==selected['source_pins'] and review['remaining_findings']==[]
    assert review['official_verdict'] is review['receipt'] is review['seal'] is None
    documents=json.loads((OUT/'document_checks.json').read_bytes())
    assert all(pin((ROOT/name).read_bytes())==value for name,value in documents['document_pins'].items())
    native=ROOT/'results/tables/staged_rts24_p2_native_v1_non_authoritative'
    assert not (native/'p2_01').exists() and not (native/'registration_v1.json').exists()
    assert not list(OUT.parent.rglob('parent_observation.json'))
    return dict(authority='DRAFT_NONAUTHORITATIVE',preserved_paths_unchanged=len(preserved),navigation_tails_preserved=len(tails),
        targeted_passed=selected['groups'][selected['targeted_label']]['passed'],related_passed=selected['groups'][selected['related_label']]['passed'],
        process_encoding_upper_bound=92033,parent_encoding_upper_bound=101080,prior_stdout_exact=True,
        public_P2_registered=False,public_P2_executed=False,native_calls=0,scientific_evidence_adopted=False,
        resource_admission=False,formal_result=False,full_outer_time_budget_closed=False)


if __name__=='__main__':
    if sys.argv[1:]==['bootstrap']:bootstrap()
    else:print(json.dumps(verify(),indent=2,sort_keys=True))
