"""One in-process WIP archive check, original static cap; no dependency import."""
import time
STARTED=time.perf_counter()
import ast
from hashlib import sha256
import json
from pathlib import Path
import sys
OUT=Path(__file__).resolve().parent;BASE=OUT.parent;ROOT=BASE.parents[2]
V1=ROOT/'results/tables/staged_rts24_saved_fresh_import_policy_v1_non_authoritative'
V2=ROOT/'results/tables/staged_rts24_saved_fresh_import_policy_v2_non_authoritative'
WIRE=ROOT/'results/tables/staged_rts24_saved_fresh_wire_data_v1_non_authoritative'
CAP=4.4;STEP='initialization'
def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(v):return dict(bytes=len(v),sha256=sha256(v).hexdigest())
def data(p):
    if time.perf_counter()-STARTED>CAP-1.:raise TimeoutError('archive preparation budget exhausted')
    return p.read_bytes()
def read(p):return json.loads(data(p))
def names(paths):return {p.relative_to(ROOT).as_posix():pin(data(p)) for p in paths}
SNAPSHOTS={}
def snapshot(p,name=None):
    if p['sha256'] in SNAPSHOTS:return SNAPSHOTS[p['sha256']]
    for d in (OUT,V2/'checks_01',V1/'checks_01',WIRE/'checks_02',WIRE/'checks_01',ROOT/'results/tables/staged_rts24_saved_fresh_role_data_v1_non_authoritative/checks_01'):
        f=d/('code_'+p['sha256']+'.snapshot')
        if f.exists():
            result=data(f);assert pin(result)==p;SNAPSHOTS[p['sha256']]=result;return result
    if name is not None:
        original=read(WIRE/'checks_01/baseline.json')['source_snapshots']
        if name in original:
            result=data(ROOT/original[name]);assert pin(result)==p;SNAPSHOTS[p['sha256']]=result;return result
    raise AssertionError('missing frozen code snapshot')
record_paths=[p for d in (WIRE/'checks_01',WIRE/'final_package_01',WIRE/'checks_02',WIRE/'final_package_02',V1/'checks_01',V2/'checks_01',V2/'final_package_01',OUT,BASE/'final_package_01') for p in d.glob('*.exit.json')]
records={p.relative_to(ROOT).as_posix():(p,json.loads(p.read_bytes())) for p in record_paths}
spent={k:sum(r['charged_seconds'] for _,r in records.values() if r['kind']==k) for k in ('static','pytest')}
assert spent['static']+CAP<=120 and spent['pytest']<=420 and sum(spent.values())+CAP<=540
output=OUT/'wip_checkpoint.exit.json';assert not output.exists()
report=dict(schema='inprocess_WIP_archive_checkpoint_v1',authority='DRAFT_NONAUTHORITATIVE',label='wip_archive',kind='static',
    cap_seconds=CAP,previous_charged_seconds=spent,prior_record_pins=names(record_paths),official_verdict=None,production_seal=False,
    actual_F=False,run_authority=False,scientific_evidence_adopted=False,resource_admission=False,formal_result=False,
    cold_acceptance=False,saved_terminal_executed=False,whole_workflow_wall_budget_verified=False)
try:
    STEP='historical_preservation'
    baseline=read(OUT/'baseline.json');ancestor=read(V2/'checks_01/baseline.json')
    assert names(ROOT/n for n in baseline['preserved'])==baseline['preserved']
    assert names(ROOT/n for n in ancestor['preserved'])==ancestor['preserved']
    assert len(set(baseline['preserved'])|set(ancestor['preserved']))==4616
    STEP='current_source_and_regression'
    plan=read(OUT/'regression_admission.json');reg=read(OUT/'pytest_regression.exit.json');harness=read(OUT/'pytest_regression.harness.json')
    current=names(ROOT/n for n in plan['source_pins']);assert len(current)==49 and current==plan['source_pins']==reg['source_pins']==reg['after_source_pins']
    assert reg['accepted'] and reg['returncode']==harness['pytest_exit_code']==0 and reg['postcheck_pins_match']
    nodes=plan['groups']['pytest_regression'];assert len(nodes)==len(set(nodes))==len(harness['passed_call_nodes'])==42
    assert harness['requested_nodes']==nodes and set(nodes)==set(harness['collected_nodes'])==set(harness['passed_call_nodes'])
    assert not harness['failed_phases'] and not harness['skipped_phases']
    assert harness['counts']==dict(optional_Popen_attempts=1,blocked_lscpu=1,unexpected_process_attempts=0,native_owner_attempts=0,P1_write_attempts=0,actual_F_write_attempts=0)
    epoch=sha256(raw(current)).hexdigest();assert epoch==plan['source_epoch']==reg['source_epoch']
    report.update(source_pins=current,source_epoch=epoch,current_logical_nodes=42)
    STEP='exact_source_delta'
    old=read(V2/'checks_01/admission_final.json')['source_pins']
    mutable=('experiments/staged_rts24_saved_fresh_adoption_v1.py','tests/test_staged_rts24_saved_fresh_adoption_v1.py')
    assert all(p==old[n] for n,p in current.items() if n not in mutable)
    for name in mutable:
        before=ast.parse(snapshot(old[name],name));after=ast.parse(data(ROOT/name));compile(after,name,'exec',dont_inherit=True)
        if name.startswith('experiments/'):
            target=next(n for n in before.body if getattr(n,'name',None)=='load_saved_successor_dependencies')
            matches=[]
            for n in ast.walk(target):
                if isinstance(n,ast.Try):
                    for i,s in enumerate(n.body):
                        if ast.dump(s)==ast.dump(ast.parse("object.__setattr__(guard,'_adapter_bindings',tuple(bindings))").body[0]):matches.append((n,i))
            assert len(matches)==1;block,i=matches[0];block.body.insert(i+1,ast.parse('guard._set()').body[0])
            assert ast.dump(before)==ast.dump(after)
        else:
            assert len(after.body)==len(before.body)+1 and [ast.dump(n) for n in before.body]==[ast.dump(n) for n in after.body[:-1]]
            assert after.body[-1].name=='test_saved_import_policy_adapter_commit_precedes_source_open'
    STEP='ledger_and_diagnostics'
    manual=[n for n,(_,r) in records.items() if r.get('schema')=='external_wall_upper_bound_budget_failure'];assert len(manual)==1
    manual_name=manual[0];m=records[manual_name][1]
    assert not m['accepted'] and not m['child_launched'] and not m['raw_stdout_and_stderr_captured']
    assert m['charged_seconds']==6.9871657 and m['external_tool_wall_seconds']==6.4871657 and m['cap_seconds']==4
    ordered=sorted((n for n in records if n!=manual_name),key=lambda n:len(records[n][1]['prior_record_pins']))
    insertion=min(len(records[n][1]['prior_record_pins']) for n in ordered if manual_name in records[n][1]['prior_record_pins'])-1
    ordered.insert(insertion,manual_name);running=dict(static=0.,pytest=0.)
    for i,n in enumerate(ordered):
        path,r=records[n]
        if n!=manual_name:
            assert r['prior_record_pins']=={k:pin(data(records[k][0])) for k in ordered[:i]}
            assert all(abs(r['previous_charged_seconds'][k]-running[k])<1e-7 for k in running)
            assert r['charged_seconds']<=r['cap_seconds']
            for suffix in ('stdout','stderr'):assert pin(data(path.with_name(r['label']+'.'+suffix+'.log')))==r[suffix+'_pin']
            for name,p in {**r['source_pins'],**r['helper_pins']}.items():snapshot(p,name)
        running[r['kind']]+=r['charged_seconds']
    assert all(abs(running[k]-spent[k])<1e-7 for k in spent)
    failures=[n for n,(_,r) in records.items() if not r['accepted']];assert len(failures)==8
    for label in ('diagnostic_normal_02','diagnostic_normal_03'):
        r=read(OUT/(label+'.exit.json'));component=read(OUT/(label+'.stdout.log'))
        assert r['accepted'] and r['returncode']==1 and r['component_acceptance'] is False
        assert r['source_pins']==r['after_source_pins']==old and r['source_epoch']==sha256(raw(old)).hexdigest()
        assert component['loader_returned'] is False and component['boundary']['phase']=='FAULTED' and component['boundary']['fault_kind']=='classification_error'
        assert component['boundary']['hook_active'] is False and component['boundary']['optional_Popen_attempts']==component['boundary']['blocked_optional_attempts']==1
        assert component['boundary']['internal_introspection_events']==6 and component['boundary']['forced_numpy_SVE_false']
        assert all(component['counts'][k]==0 for k in ('P1_open','actual_F_open','write_attempts','unexpected_process'))
    details=read(OUT/'diagnostic_normal_03.stdout.log')['failure_details']
    assert any(r['label']=='audit_primary' and r['error_type']=='ValueError' and ['_audit_entry',6149] in r['entry_frames'] for r in details)
    report.update(failed_records=failures,conservative_preparation_charge_preserved=True,diagnostic_component_acceptance=False)
    STEP='navigation_and_review'
    review=read(OUT/'pre_seal_review.json');assert review['source_epoch']==epoch and review['official_verdict'] is None and review['production_seal'] is False
    assert review['remaining_must_fix_findings'] and len(review['navigation'])==4
    for name,row in review['navigation'].items():
        nav=data(ROOT/row['checkpoint_snapshot']);assert pin(nav)==row['checkpoint_pin'] and pin(data(ROOT/name))==row['checkpoint_pin']
        header,body=nav.split(b'\n\n',1);prefix=row['prefix'].encode();assert body.startswith(prefix)
        assert pin(header+b'\n\n'+body[len(prefix):])==row['original_pin']
    STEP='resource_caps_and_binding'
    def usage(root):
        files=[p for p in root.rglob('*') if p.is_file()];return dict(files=len(files),bytes=sum(p.stat().st_size for p in files))
    uses=[usage(p) for p in (V1,V2,BASE)];assert uses[0]['files']==38 and uses[1]['files']==39
    assert uses[2]['files']+1<=64 and uses[2]['bytes']+200000<=4*1024**2
    assert sum(r['files'] for r in uses)+1<=128 and sum(r['bytes'] for r in uses)+200000<=8*1024**2
    wire=usage(WIRE);assert wire['files']<=204 and wire['bytes']<=16*1024**2
    documents=[ROOT/'docs/plan'/name for name in ('continuation_handoff_20261026_saved_fresh_import_policy_cold_v1.md','staged_deliverability_c_saved_fresh_import_policy_wip_archive_v1.md','staged_deliverability_c_saved_fresh_import_policy_cold_scope_budget_v1.md')]
    bound=names([p for p in BASE.rglob('*') if p.is_file()]+documents)
    report.update(bound_files=bound,preserved_paths=4616,policy_usage_before_checkpoint=uses,wire_usage=wire,verification_completed=True)
except BaseException as error:
    report.update(verification_completed=False,error_type=type(error).__name__,failed_check=STEP)
report['charged_seconds']=time.perf_counter()-STARTED+.5;report['tail_reserve_seconds']=.5
report['accepted']=report.get('verification_completed',False) and report['charged_seconds']<=CAP
report['cumulative_charged_seconds']={k:spent[k]+(report['charged_seconds'] if k=='static' else 0) for k in spent}
with output.open('xb') as stream:stream.write(raw(report))
print(json.dumps(dict(accepted=report['accepted'],failed_check=report.get('failed_check'),charged_seconds=report['charged_seconds'],cumulative_charged_seconds=report['cumulative_charged_seconds']),sort_keys=True))
if not report['accepted']:raise SystemExit(1)
