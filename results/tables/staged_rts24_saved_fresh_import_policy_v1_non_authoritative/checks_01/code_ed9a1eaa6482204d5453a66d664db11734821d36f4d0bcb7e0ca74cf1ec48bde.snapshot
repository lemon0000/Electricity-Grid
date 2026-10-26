"""Independent stdlib archive audit for the dependency-import policy primitive."""
import ast
from hashlib import sha256
import json
from pathlib import Path
import sys
PACKAGE=Path(__file__).resolve().parent;BASE=PACKAGE.parent;OUT=BASE/'checks_01';ROOT=BASE.parents[2]
OLD=ROOT/'results/tables/staged_rts24_saved_fresh_wire_data_v1_non_authoritative'
def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(v):return dict(bytes=len(v),sha256=sha256(v).hexdigest())
def read(p):return json.loads(p.read_bytes())
def names(paths):return {p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in paths}
def snapshot(p,n=None):
    for d in (OUT,OLD/'checks_02',OLD/'checks_01',ROOT/'results/tables/staged_rts24_saved_fresh_role_data_v1_non_authoritative/checks_01'):
        path=d/('code_'+p['sha256']+'.snapshot')
        if path.exists():data=path.read_bytes();assert pin(data)==p;return data
    path=ROOT/read(OLD/'checks_01/baseline.json')['source_snapshots'][n];data=path.read_bytes();assert pin(data)==p;return data
def verify():
    baseline=read(OUT/'baseline.json');initial=read(OUT/'admission.json');plan=read(OUT/'admission_revision.json')
    assert len(baseline['preserved'])==4536 and names(ROOT/n for n in baseline['preserved'])==baseline['preserved']
    assert names(ROOT/n for n in plan['source_pins'])==plan['source_pins'] and len(plan['source_pins'])==49
    assert plan['source_epoch']==sha256(raw(plan['source_pins'])).hexdigest()
    mutable={'experiments/staged_rts24_saved_fresh_adoption_v1.py','tests/test_staged_rts24_saved_fresh_adoption_v1.py'}
    assert all(p==baseline['sources'][n] for n,p in plan['source_pins'].items() if n not in mutable)
    for n in baseline['old_nodes']:
        before=ast.parse(snapshot(baseline['sources'][n],n));data=snapshot(plan['source_pins'][n],n);after=ast.parse(data);compile(after,n,'exec',dont_inherit=True)
        prefix=len(before.body)-(1 if n.startswith('experiments/') else 0)
        assert [ast.dump(node) for node in after.body[:prefix]]==[ast.dump(node) for node in before.body[:prefix]]
        if n.startswith('experiments/'):assert ast.dump(after.body[-1])==ast.dump(before.body[-1])
    policy_raw=(OUT/'import_policy.json').read_bytes();policy=read(OUT/'import_policy.json');proposal=read(OUT/'runtime_profile_v3_proposal.json')
    assert policy_raw==raw(policy) and proposal['import_policy_pin']==pin(policy_raw)
    assert proposal['does_not_supersede_or_open_v2'] and proposal['admissible_for_production_execution'] is False
    parent=ROOT/'results/tables/staged_rts24_saved_fresh_runtime_binding_v1_non_authoritative/checks_01/runtime_binding_contract_v2.json'
    assert proposal['parent_profile_pin']==pin(parent.read_bytes()) and read(parent)['external_import_probe_policy']=='UNDECIDED_BLOCKING'
    assert policy['protected_open_roots']=={'P1':str(ROOT/'results/tables/staged_rts24_native_v1_non_authoritative/p1_01'),'actual_F':str(ROOT/'results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative')}
    harness=read(OUT/'pytest_retry.harness.json');group=plan['groups']['pytest_retry'];record=read(OUT/'pytest_retry.exit.json')
    assert record['accepted'] and record['returncode']==0 and harness['pytest_exit_code']==0
    assert harness['requested_nodes']==group and set(harness['collected_nodes'])==set(harness['passed_call_nodes'])==set(group)
    assert len(harness['passed_call_nodes'])==len(set(group))==plan['current_targeted_nodes']
    assert not harness['failed_phases'] and not harness['skipped_phases']
    assert harness['counts']==dict(optional_Popen_attempts=1,blocked_lscpu=1,unexpected_process_attempts=0,native_owner_attempts=0,P1_write_attempts=0,actual_F_write_attempts=0)
    for case in baseline['cold_cases']:
        row=read(OUT/('cold_'+case+'.json'));assert row['accepted'] and row['handle_closed'] and row['error'] is None
        for suffix in ('stdout','stderr'):assert pin((OUT/('cold_'+case+'.'+suffix+'.log')).read_bytes())==row[suffix+'_pin']
        child=row['child_record'];assert child['actual_F'] is child['run_authority'] is child['formal_result'] is False
        result=child['boundary'];assert result['phase']==('CLOSED' if case=='normal' else 'FAULTED') and not result['hook_active']
        assert child['loader_returned']==(case=='normal')
        assert row['returncode']==(0 if case=='normal' else 1)
        if case=='normal':assert result['optional_Popen_attempts']==result['blocked_optional_attempts']==1 and result['internal_introspection_events']==6 and result['source49_bookend_equal']
        elif case=='caught_effect':assert result['violations']==1 and child['counts']['lifecycle_injections']==1
        else:assert result['installation_sentinel_observed']==result['optional_Popen_attempts']==0
        assert all(child['counts'][n]==0 for n in ('P1_open','actual_F_open','write_attempts','unexpected_process'))
        assert child['scientific_API_calls_instrumented'] is False
        assert all(result[n] is False for n in ('independent_root_verified','source49_expected_truth_bound_by_import_boundary','cold_main_self_anchor_verified','full_runtime_binding_verified','role_bootstrap','permit_issued','actual_F','run_authority','scientific_evidence_adopted','resource_admission','formal_result'))
    review=read(OUT/'pre_seal_review.json');assert review['source_epoch']==plan['source_epoch'] and not review['remaining_must_fix_findings']
    assert review['official_verdict'] is None and review['production_seal'] is False
    records={p.relative_to(ROOT).as_posix():(p,read(p)) for d in (OLD/'checks_01',OLD/'final_package_01',OLD/'checks_02',OLD/'final_package_02',OUT,PACKAGE) for p in d.glob('*.exit.json')}
    ordered=sorted(records,key=lambda n:len(records[n][1]['prior_record_pins']));spent=dict(static=0.,pytest=0.)
    for i,n in enumerate(ordered):
        path,r=records[n];assert r['prior_record_pins']=={k:pin(records[k][0].read_bytes()) for k in ordered[:i]}
        assert all(abs(r['previous_charged_seconds'][k]-spent[k])<1e-7 for k in spent)
        assert r['fixed_before']==r['fixed_after'] and r['charged_seconds']<=r['cap_seconds']
        if path.parent in (OUT,PACKAGE):
            expected=initial['source_pins'] if r['label'] in ('collection','pytest_a') else plan['source_pins']
            assert r['postcheck_pins_match'] and r['source_pins']==r['after_source_pins']==expected and r['helper_pins']==r['after_helper_pins']
        for suffix in ('stdout','stderr'):assert pin(path.with_name(r['label']+'.'+suffix+'.log').read_bytes())==r[suffix+'_pin']
        for name,p in {**r['source_pins'],**r['helper_pins']}.items():snapshot(p,name)
        state=r['bounded_drain'];assert state['reader_threads_terminal'] and state['pipes_closed'] and not state['cleanup']
        assert all(r[k] is False for k in ('actual_F','scientific_evidence_adopted','resource_admission','formal_result'))
        spent[r['kind']]+=r['charged_seconds']
    assert spent['static']<=120 and spent['pytest']<=420 and sum(spent.values())<=540
    assert {r['label'] for _,r in records.values() if not r['accepted']}=={'wip_static_02','r1_new_smoke','r3_old_expectation_a_12','pytest_a'}
    failed=read(OUT/'pytest_a.exit.json');assert failed['returncode']==1 and not failed['accepted']
    assert b'TypeError: Object of type bytes is not JSON serializable' in (OUT/'pytest_a.stdout.log').read_bytes()
    assert any(n.endswith('/final_package_01/oracle.py') for n in plan['helper_pins'])
    assert not any(n.endswith('/oracle.py') for n in read(OUT/'collection.exit.json')['helper_pins'])
    for n,row in read(OUT/'pre_seal_review.json')['navigation'].items():
        data=(ROOT/row['checkpoint_snapshot']).read_bytes();assert pin(data)==row['checkpoint_pin']
        assert pin((ROOT/n).read_bytes()) in (row['checkpoint_pin'],row['published_pin'])
        header,body=data.split(b'\n\n',1);prefix=row['prefix'].encode();assert body.startswith(prefix)
        assert pin(header+b'\n\n'+body[len(prefix):])==row['original_pin']
    files=[p for p in BASE.rglob('*') if p.is_file()];assert len(files)<=64 and sum(p.stat().st_size for p in files)<=4*1024**2
    return dict(authority='DRAFT_NONAUTHORITATIVE',source_epoch=plan['source_epoch'],current_policy_unit_nodes=plan['current_targeted_nodes'],cold_cases=baseline['cold_cases'],preserved_paths=4536,charged_before_capture=spent,production_seal=False,initial_capture_omitted_oracle_helper=True,final_capture_and_admission_bind_oracle=True,old_API_AST_and_CLI_preserved=True,old_v2_profile_preserved=True,independent_root_verified=False,full_runtime_binding_verified=False,actual_F=False,run_authority=False,scientific_evidence_adopted=False,resource_admission=False,formal_result=False)
if __name__=='__main__':
    mode=sys.argv[1];freeze=PACKAGE/'checkpoint_freeze.json'
    if mode=='saved':
        paths=[p for p in OUT.rglob('*') if p.is_file()]+[Path(__file__).resolve(),ROOT/'docs/plan/staged_deliverability_c_saved_fresh_import_policy_scope_budget_v1.md',ROOT/'docs/plan/continuation_handoff_20261026_saved_fresh_import_policy.md']
        with freeze.open('xb') as stream:stream.write(raw(dict(authority='DRAFT_NONAUTHORITATIVE',production_seal=False,bound_files=names(paths))))
    f=read(freeze);assert names(ROOT/n for n in f['bound_files'])==f['bound_files']
    report=verify()
    with (PACKAGE/(mode+'_report.json')).open('xb') as stream:stream.write(raw(report))
    print(json.dumps(report,sort_keys=True))
