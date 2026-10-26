"""Independent saved data-only oracle; stdlib and pinned predecessor archive only."""
import ast
import base64
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import re
import sys
PACKAGE=Path(__file__).resolve().parent;MAIN=PACKAGE.parent/'checks_01';ROOT=MAIN.parents[3]
OLD=ROOT/'results/tables/staged_rts24_saved_fresh_upstream_archive_v1_non_authoritative/checks_01/saved_checks.py'
MUTABLE={'experiments/staged_rts24_saved_fresh_adoption_v1.py','tests/test_staged_rts24_saved_fresh_adoption_v1.py'}
FAILURES={'collection_02','admission_03','role_1'}
def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(v):return dict(bytes=len(v),sha256=sha256(v).hexdigest())
def read(p):return json.loads(p.read_bytes())
def names(paths):return {p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in paths}
def snapshot(p):
    data=(MAIN/('code_'+p['sha256']+'.snapshot')).read_bytes();assert pin(data)==p;return data
def nodes(data):return [sha256(ast.dump(n,include_attributes=False).encode()).hexdigest() for n in ast.parse(data).body]
def verify(require_current_sources=False,require_current_navigation=False):
    baseline=read(MAIN/'baseline.json');plan=read(MAIN/'admission.json');revision=read(MAIN/'admission_revision_08.json')
    assert len(baseline['preserved'])==4123 and names(ROOT/n for n in baseline['preserved'])==baseline['preserved']
    assert len(plan['source_pins'])==49 and set(plan['source_pins'])==set(baseline['sources'])
    assert all(p==baseline['sources'][n] for n,p in plan['source_pins'].items() if n not in MUTABLE)
    assert plan['source_epoch']==sha256(raw(plan['source_pins'])).hexdigest()
    current=names(ROOT/n for n in plan['source_pins'])==plan['source_pins']
    if require_current_sources:assert current
    for n,p in plan['source_pins'].items():
        after=nodes(snapshot(p)) if n in baseline['old_nodes'] else None
        if after is None:continue
        before=baseline['old_nodes'][n]
        assert (after[:len(before)-1]==before[:-1] and after[-1]==before[-1]) if n.startswith('experiments/') else after[:len(before)]==before
        if n.startswith('src/'):assert after==before
    original=[n for group in plan['groups'].values() for n in group]
    assert len(original)==len(set(original))==480 and sum('::test_saved_role_data_' in n for n in original)==198
    assert plan['new_nodes']==198 and plan['regression_nodes']==282 and sum(plan['caps'].values())==319
    assert revision['original_admission_pin']==pin((MAIN/'admission.json').read_bytes())
    assert revision['historical_timeout_pin']==pin((MAIN/'role_1.exit.json').read_bytes())
    assert revision['source_pins']==plan['source_pins'] and revision['source_epoch']==plan['source_epoch']
    assert set(revision['groups'])=={'role_1_retry','role_2','role_3','role_4'} and set(revision['caps'].values())=={35}
    for label,group in revision['groups'].items():assert group==plan['groups']['role_1' if label=='role_1_retry' else label]
    completed={n:v for n,v in plan['groups'].items() if n not in ('role_1','role_2','role_3','role_4')}
    left=[n for v in completed.values() for n in v];right=[n for v in revision['groups'].values() for n in v]
    assert len(left)==len(set(left))==291 and len(right)==len(set(right))==189
    assert not set(left)&set(right) and set(left)|set(right)==set(original)
    assert set(revision['completed_labels'])==set(completed)
    effective={**completed,**revision['groups']}
    records={p.name.removesuffix('.exit.json'):(p,read(p)) for d in (MAIN,PACKAGE) for p in d.glob('*.exit.json')}
    required={'baseline_01','collection_02','collection_retry_04','admission_03','admission_retry_07','revision_08','finalizer_04','role_1',*effective}
    assert required<=set(records)<=required|{'saved_05','terminal_06'}
    spent=dict(static=0.,pytest=0.);ordered=sorted(records,key=lambda n:len(records[n][1]['prior_record_pins']))
    fixed=pin(raw(baseline['preserved']))
    for index,label in enumerate(ordered):
        path,r=records[label];assert r['label']==label and r['authority']=='DRAFT_NONAUTHORITATIVE'
        prior={records[n][0].relative_to(ROOT).as_posix():pin(records[n][0].read_bytes()) for n in ordered[:index]}
        assert r['prior_record_pins']==prior and all(abs(r['previous_charged_seconds'][k]-spent[k])<1e-8 for k in spent)
        assert r['fixed_before']==r['fixed_after']==fixed and r['package_postcheck_verified']
        assert r['source_epoch']==sha256(raw(r['source_pins'])).hexdigest()
        assert r['source_pins']==(baseline['sources'] if label=='baseline_01' else plan['source_pins'])
        for n,p in {**r['source_pins'],**r['helper_pins']}.items():snapshot(p)
        target=Path(r['argv'][2]).relative_to(ROOT).as_posix();assert target in r['helper_pins']
        assert r['stdout_pin']==pin(path.with_name(label+'.stdout.log').read_bytes())
        assert r['stderr_pin']==pin(path.with_name(label+'.stderr.log').read_bytes())==pin(b'')
        assert r['tail_reserve_seconds']==.5 and r['charged_seconds']==r['observed_capture_seconds']+.5
        assert r['kind']==('pytest' if label in {*effective,'role_1'} else 'static')
        if label in FAILURES:
            assert r['returncode']==1 and r['accepted'] is False and r['error']=='timeout'
            assert not (MAIN/(label+'.harness.json')).exists()
        else:assert r['returncode']==0 and r['accepted'] and r['error'] is None and r['charged_seconds']<=r['cap_seconds']<=45
        assert all(r[n] is False for n in ('actual_F','scientific_evidence_adopted','resource_admission','formal_result','whole_workflow_wall_budget_verified'))
        if label!='baseline_01':
            d=r['bounded_drain'];assert d['child_created'] and d['pipes_closed'] and d['reader_threads_terminal'] and d['cleanup']==[]
            assert not d['stdout_truncated'] and not d['stderr_truncated'] and not d['reader_errors']
        if label in effective:
            group=effective[label];h=read(MAIN/(label+'.harness.json'))
            assert h['pytest_exit_code']==0 and h['failed_phases']==h['skipped_phases']==[]
            for field in ('requested_nodes','collected_nodes','passed_call_nodes'):
                assert len(h[field])==len(set(h[field]))==len(group) and set(h[field])==set(group)
            assert h['counts']==dict(P1_write_attempts=0,actual_F_write_attempts=0,blocked_lscpu=1,native_owner_attempts=0,optional_Popen_attempts=1,unexpected_process_attempts=0)
            assert all(h[n] for n in ('guards_installed_before_repository_import','native_constructor_guard_installed','native_constructor_original_restored','audit_hook_installed_until_process_exit'))
            assert all(h[n] is False for n in ('actual_saved_F_execution','arbitrary_native_effects_proved_absent','production_policy_decided'))
            for name in ('fixture_builder.py','pytest_harness.py','run.py'):
                n=(MAIN/name).relative_to(ROOT).as_posix();assert r['helper_pins'][n]==plan['helper_pins'][n]
        if label in ('collection_retry_04','admission_retry_07'):
            failed_label='collection_02' if label=='collection_retry_04' else 'admission_03'
            p=records[failed_label][0];assert r['retry_of']==dict(path=p.relative_to(ROOT).as_posix(),pin=pin(p.read_bytes()))
        spent[r['kind']]+=r['charged_seconds']
    assert spent['pytest']<=360 and spent['static']<=120 and sum(spent.values())<=480
    collection=read(MAIN/'collection_retry_04.harness.json')
    assert set(collection['collected_nodes'])==set(original) and len(collection['collected_nodes'])==480
    assert collection['unexpected_new_collection_nodes']==[] and collection['passed_call_nodes']==[]
    docs=read(MAIN/'document_checks.json');navigation=True
    for n,v in docs['navigation'].items():
        data=(ROOT/n).read_bytes();header,sep,body=data.partition(b'\n\n')
        assert sep and header==base64.b64decode(v['header_base64'])
        suffix=body[-v['after_body_pin']['bytes']:];prefix=base64.b64decode(v['prefix_base64'])
        assert pin(suffix)==v['after_body_pin'] and suffix.startswith(prefix)
        old=suffix[len(prefix):];assert pin(old)==v['before_body_pin']
        assert pin(header+b'\n\n'+old)==v['before_full_pin']
        navigation &= pin(data)==v['after_full_pin']
    if require_current_navigation:assert navigation
    for n,p in docs['documents'].items():assert pin((ROOT/n).read_bytes())==p
    assert sum(p['bytes'] for p in docs['documents'].values())<=1024**2
    freeze=read(PACKAGE/'execution_freeze.json')
    actual=names(p for p in MAIN.rglob('*') if p.is_file())
    assert actual==freeze['files'] and len(actual)==freeze['count']<=160
    assert sum(v['bytes'] for v in actual.values())==freeze['bytes']<=12*1024**2 and pin(raw(actual))==freeze['root']
    support=read(PACKAGE/'support_pins.json')
    assert support==names((PACKAGE/n for n in ('saved_checks.py','execution_freeze.json')))
    for label in ('saved_05','terminal_06'):
        if label not in records:continue
        r=records[label][1];assert r['support_pin']==pin((PACKAGE/'support_pins.json').read_bytes())
        assert r['execution_freeze_pin']==pin((PACKAGE/'execution_freeze.json').read_bytes())
    assert pin(OLD.read_bytes())==baseline['preserved'][OLD.relative_to(ROOT).as_posix()]
    spec=importlib.util.spec_from_file_location('pinned_predecessor_archive',OLD);prior=importlib.util.module_from_spec(spec);spec.loader.exec_module(prior)
    old_result=prior.verify()
    assert old_result['frozen_epoch_test_nodes']==282 and old_result['current_epoch_test_nodes']==0
    assert old_result['P1_unchanged_files']==683 and old_result['full_ancestor_archive_verified']
    assert old_result['historical_failure_records']==2 and old_result['scientific_ENTRY_imported'] is False
    assert not (ROOT/'results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative').exists()
    files=[p for p in PACKAGE.rglob('*') if p.is_file()]
    expected={'saved_checks.py','execution_freeze.json','support_pins.json'}|{label+'.'+suffix for label in ('saved_05','terminal_06') if label in records for suffix in ('stdout.log','stderr.log','exit.json')}
    assert {p.name for p in files}==expected and len(files)<=24 and sum(p.stat().st_size for p in files)<=2*1024**2
    summary=read(MAIN/'validation_summary.json');assert summary['passed_nodes']==480 and summary['source_epoch']==plan['source_epoch']
    return dict(authority='DRAFT_NONAUTHORITATIVE',scope='role_entry_data_only',frozen_epoch_test_nodes=480,
        current_epoch_test_nodes=480 if current else 0,regression_nodes=282,new_nodes=198,completed_accepted_groups=len(effective),
        preserved_paths=4123,P1_unchanged_files=683,ancestor_archive_verified=True,retained_current_failed_attempts=3,
        ancestor_failures_retained=2,current_sources_match=current,current_navigation_match=bool(navigation),
        source_epoch=plan['source_epoch'],completed_capture_records=len(records),charged_seconds=spent,
        current_capture_excluded_until_external_exit=True,execution_files=len(actual),execution_bytes=freeze['bytes'],
        helper_execution_snapshots_verified=True,scientific_ENTRY_imported=False,new_simulated_hours=0,
        producer_capability_verified=False,full_projection_semantics_verified=False,role_bootstrap=False,
        actual_F=False,scientific_evidence_adopted=False,resource_admission=False,formal_result=False)
def guard(event,args):
    if event=='subprocess.Popen' or event=='os.system' or event.startswith('os.spawn'):raise AssertionError('saved oracle process launch')
    if event=='import' and args and str(args[0]).split('.')[0] in ('src','experiments','numpy','scipy','pyomo','highspy'):
        raise AssertionError('saved oracle scientific import')
if __name__=='__main__':
    assert not sys.argv[1:];sys.addaudithook(guard)
    print(json.dumps(verify(require_current_sources=True,require_current_navigation=True),sort_keys=True))
