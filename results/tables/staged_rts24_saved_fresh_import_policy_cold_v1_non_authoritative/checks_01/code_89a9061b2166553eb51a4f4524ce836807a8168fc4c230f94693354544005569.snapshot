"""Stdlib-only saved audit: frozen unit evidence plus corrected Windows cold driver."""
import ast
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys
PACKAGE=Path(__file__).resolve().parent;BASE=PACKAGE.parent;OUT=BASE/'checks_01';ROOT=BASE.parents[2]
V1=ROOT/'results/tables/staged_rts24_saved_fresh_import_policy_v1_non_authoritative'
V2=ROOT/'results/tables/staged_rts24_saved_fresh_import_policy_v2_non_authoritative'
WIRE=ROOT/'results/tables/staged_rts24_saved_fresh_wire_data_v1_non_authoritative'
def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(v):return dict(bytes=len(v),sha256=sha256(v).hexdigest())
def read(p):return json.loads(p.read_bytes())
def names(paths):return {p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in paths}
def verify():
    baseline=read(OUT/'baseline.json');ancestor=read(V2/'checks_01/baseline.json');plan=read(V2/'checks_01/admission_final.json')
    assert names(ROOT/n for n in baseline['preserved'])==baseline['preserved'] and len(baseline['preserved'])==40
    assert names(ROOT/n for n in ancestor['preserved'])==ancestor['preserved'] and len(ancestor['preserved'])==4576
    assert len(set(baseline['preserved'])|set(ancestor['preserved']))==baseline['preserved_paths']==4616
    assert names(ROOT/n for n in plan['source_pins'])==plan['source_pins']==baseline['source_pins'] and len(plan['source_pins'])==49
    assert plan['source_epoch']==baseline['source_epoch']==sha256(raw(plan['source_pins'])).hexdigest()
    assert baseline['phase_caps']==dict(cold_import=12,saved=6,terminal=6)
    assert baseline['cold_cases']==['normal','caught_effect','blocked_installation']
    helper_pins=names(p for d in (OUT,PACKAGE) for p in d.glob('*.py'));assert helper_pins==baseline['helper_pins'] and len(helper_pins)==3
    controls={(OUT/'baseline.json').relative_to(ROOT).as_posix():pin((OUT/'baseline.json').read_bytes())}
    old_oracle=V2/'final_package_01/oracle_revision_02.py'
    spec=importlib.util.spec_from_file_location('frozen_ast_archive_checker',old_oracle);old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
    old.exact_delta(ancestor,plan)
    for n in ancestor['protected_api_nodes']:
        before=ast.parse(old.snapshot(ancestor['protected_sources'][n],n));after=ast.parse(old.snapshot(plan['source_pins'][n],n));compile(after,n,'exec',dont_inherit=True)
        prefix=len(before.body)-(1 if n.startswith('experiments/') else 0)
        assert [ast.dump(x) for x in after.body[:prefix]]==[ast.dump(x) for x in before.body[:prefix]]
        if n.startswith('experiments/'):assert ast.dump(after.body[-1])==ast.dump(before.body[-1])
    original=read(V2/'checks_01/collection.exit.json');final=read(V2/'checks_01/collection_final.exit.json')
    assert original['accepted'] and final['accepted'] and original['source_pins']==final['source_pins']==plan['source_pins']
    for name in ('admission_final.json','collection_final.harness.json','revision_final.json'):
        path=V2/'checks_01'/name;assert final['child_artifact_pins'][path.relative_to(ROOT).as_posix()]==pin(path.read_bytes())
    revision=read(V2/'checks_01/revision_final.json');assert names(ROOT/n for n in revision['original_artifact_pins'])==revision['original_artifact_pins']
    assert revision['helper_pins']==plan['helper_pins']==names(ROOT/n for n in plan['helper_pins'])
    assert plan['controls_pins']==final['controls_pins']==names(ROOT/n for n in plan['controls_pins'])
    weak=V2/'final_package_01/oracle.py';weak_pin=pin(weak.read_bytes())
    assert original['helper_pins'][weak.relative_to(ROOT).as_posix()]==weak_pin
    assert pin((V2/'checks_01'/('code_'+weak_pin['sha256']+'.snapshot')).read_bytes())==weak_pin
    harness=read(V2/'checks_01/pytest_a.harness.json');unit=read(V2/'checks_01/pytest_a.exit.json');nodes=plan['groups']['pytest_a']
    assert unit['accepted'] and unit['returncode']==harness['pytest_exit_code']==0
    assert plan['current_targeted_nodes']==len(nodes)==len(set(nodes))==len(harness['passed_call_nodes'])==41
    assert harness['requested_nodes']==nodes and set(harness['collected_nodes'])==set(harness['passed_call_nodes'])==set(nodes)
    assert not harness['failed_phases'] and not harness['skipped_phases']
    assert harness['counts']==dict(optional_Popen_attempts=1,blocked_lscpu=1,unexpected_process_attempts=0,native_owner_attempts=0,P1_write_attempts=0,actual_F_write_attempts=0)
    failed=read(V2/'checks_01/cold_import.exit.json')
    assert failed['returncode']==1 and failed['accepted'] is False and failed['postcheck_pins_match'] is False
    assert len(failed['missing_child_artifacts'])==9 and not failed['child_artifact_pins']
    assert not list((V2/'checks_01').glob('cold_normal.*'))
    assert all(not (ROOT/n).exists() for n in failed['missing_child_artifacts'])
    assert failed['source_pins']==failed['after_source_pins']==plan['source_pins'] and failed['helper_pins']==failed['after_helper_pins']
    assert failed['controls_pins']==failed['after_controls_pins']==plan['controls_pins']
    assert b'list(args[1])==allowed[len(launches)]' in (V2/'checks_01/cold_import.stderr.log').read_bytes()
    parent=ROOT/'results/tables/staged_rts24_saved_fresh_runtime_binding_v1_non_authoritative/checks_01/runtime_binding_contract_v2.json'
    proposal=read(V2/'checks_01/runtime_profile_v3_proposal.json');policy=V2/'checks_01/import_policy.json'
    assert proposal['parent_profile_pin']==pin(parent.read_bytes()) and proposal['import_policy_pin']==pin(policy.read_bytes())
    assert read(parent)['external_import_probe_policy']=='UNDECIDED_BLOCKING' and read(parent)['admissible_for_production_execution'] is False
    assert proposal['does_not_supersede_or_open_v2'] and proposal['admissible_for_production_execution'] is False
    cold=read(OUT/'cold_import.exit.json');assert cold['accepted'] and cold['returncode']==0
    assert names(ROOT/n for n in cold['child_artifact_pins'])==cold['child_artifact_pins'] and len(cold['child_artifact_pins'])==9
    for case in baseline['cold_cases']:
        row=read(OUT/('cold_'+case+'.json'));assert row['accepted'] and row['handle_closed'] and row['error'] is None
        for suffix in ('stdout','stderr'):assert pin((OUT/('cold_'+case+'.'+suffix+'.log')).read_bytes())==row[suffix+'_pin']
        state=row['bounded_drain'];assert state['reader_threads_terminal'] and state['pipes_closed'] and not state['cleanup']
        child=row['child_record'];result=child['boundary']
        assert child['case']==case and result['phase']==('CLOSED' if case=='normal' else 'FAULTED') and not result['hook_active']
        assert child['loader_returned']==(case=='normal') and row['returncode']==(0 if case=='normal' else 1)
        if case=='normal':assert result['optional_Popen_attempts']==result['blocked_optional_attempts']==1 and result['internal_introspection_events']==6 and result['source49_bookend_equal']
        elif case=='caught_effect':assert result['violations']==1 and child['counts']['lifecycle_injections']==1
        else:assert result['installation_sentinel_observed']==result['optional_Popen_attempts']==0
        assert all(child['counts'][n]==0 for n in ('P1_open','actual_F_open','write_attempts','unexpected_process'))
        assert child['scientific_API_calls_instrumented'] is False
        assert all(child[n] is False for n in ('actual_F','run_authority','formal_result'))
        assert all(result[n] is False for n in ('independent_root_verified','source49_expected_truth_bound_by_import_boundary','cold_main_self_anchor_verified','full_runtime_binding_verified','role_bootstrap','permit_issued','actual_F','run_authority','scientific_evidence_adopted','resource_admission','formal_result'))
    records={p.relative_to(ROOT).as_posix():(p,read(p)) for d in (WIRE/'checks_01',WIRE/'final_package_01',WIRE/'checks_02',WIRE/'final_package_02',V1/'checks_01',V2/'checks_01',V2/'final_package_01',OUT,PACKAGE) for p in d.glob('*.exit.json')}
    ordered=sorted(records,key=lambda n:len(records[n][1]['prior_record_pins']));spent=dict(static=0.,pytest=0.)
    for i,n in enumerate(ordered):
        path,r=records[n];assert r['prior_record_pins']=={k:pin(records[k][0].read_bytes()) for k in ordered[:i]}
        assert all(abs(r['previous_charged_seconds'][k]-spent[k])<1e-7 for k in spent)
        assert r['fixed_before']==r['fixed_after'] and r['charged_seconds']<=r['cap_seconds']
        if path.parent in (OUT,PACKAGE):
            assert r['postcheck_pins_match'] and r['source_pins']==r['after_source_pins']==plan['source_pins'] and r['helper_pins']==r['after_helper_pins']==helper_pins
            assert r['controls_pins']==r['after_controls_pins']==controls and not r['missing_child_artifacts']
            assert names(ROOT/n for n in r['child_artifact_pins'])==r['child_artifact_pins']
        for suffix in ('stdout','stderr'):assert pin(path.with_name(r['label']+'.'+suffix+'.log').read_bytes())==r[suffix+'_pin']
        for name,p in {**r['source_pins'],**r['helper_pins']}.items():
            if p in helper_pins.values():assert pin((OUT/('code_'+p['sha256']+'.snapshot')).read_bytes())==p
            else:old.snapshot(p,name)
        state=r['bounded_drain'];assert state['reader_threads_terminal'] and state['pipes_closed'] and not state['cleanup']
        assert all(r[k] is False for k in ('actual_F','scientific_evidence_adopted','resource_admission','formal_result'))
        spent[r['kind']]+=r['charged_seconds']
    assert spent['static']<=120 and spent['pytest']<=420 and sum(spent.values())<=540
    assert {n for n,(_,r) in records.items() if not r['accepted']}==set(baseline['failed_records'])
    historical_usage=old.archive_and_resources(ancestor,records)
    def usage(root):
        files=[p for p in root.rglob('*') if p.is_file()];return dict(files=len(files),bytes=sum(p.stat().st_size for p in files))
    uses=[usage(p) for p in (V1,V2,BASE)];assert uses[0]['files']==38 and uses[1]['files']==39
    assert uses[2]['files']<=64 and uses[2]['bytes']<=4*1024**2
    assert sum(r['files'] for r in uses)<=128 and sum(r['bytes'] for r in uses)<=8*1024**2
    review=read(OUT/'pre_seal_review.json');assert review['source_epoch']==plan['source_epoch'] and not review['remaining_must_fix_findings']
    assert review['official_verdict'] is None and review['production_seal'] is False
    for n,row in review['navigation'].items():
        data=(ROOT/row['checkpoint_snapshot']).read_bytes();assert pin(data)==row['checkpoint_pin']
        assert pin((ROOT/n).read_bytes()) in (row['checkpoint_pin'],row['published_pin'])
        header,body=data.split(b'\n\n',1);prefix=row['prefix'].encode();assert body.startswith(prefix)
        assert pin(header+b'\n\n'+body[len(prefix):])==row['original_pin']
    return dict(authority='DRAFT_NONAUTHORITATIVE',source_epoch=plan['source_epoch'],reused_unit_nodes=41,cold_cases=baseline['cold_cases'],preserved_paths=4616,
        charged_before_capture=spent,policy_root_usage_at_audit=uses,historical_usage_at_audit=historical_usage,exact_v1_to_v2_AST_delta_verified=True,
        production_seal=False,independent_root_verified=False,full_runtime_binding_verified=False,actual_F=False,run_authority=False,scientific_evidence_adopted=False,resource_admission=False,formal_result=False)
if __name__=='__main__':
    mode=sys.argv[1];freeze=PACKAGE/'checkpoint_freeze.json'
    if mode=='saved':
        paths=[p for p in OUT.rglob('*') if p.is_file()]+list(PACKAGE.glob('*.py'))+[ROOT/'docs/plan/staged_deliverability_c_saved_fresh_import_policy_cold_scope_budget_v1.md',ROOT/'docs/plan/continuation_handoff_20261026_saved_fresh_import_policy_cold_v1.md']
        with freeze.open('xb') as stream:stream.write(raw(dict(authority='DRAFT_NONAUTHORITATIVE',production_seal=False,bound_files=names(paths))))
    else:
        assert mode=='terminal';anchor=read(PACKAGE/'saved.exit.json')['child_artifact_pins']
        assert anchor[freeze.relative_to(ROOT).as_posix()]==pin(freeze.read_bytes())
        assert anchor[(PACKAGE/'saved_report.json').relative_to(ROOT).as_posix()]==pin((PACKAGE/'saved_report.json').read_bytes())
    f=read(freeze);assert names(ROOT/n for n in f['bound_files'])==f['bound_files']
    report=verify()
    with (PACKAGE/(mode+'_report.json')).open('xb') as stream:stream.write(raw(report))
    print(json.dumps(report,sort_keys=True))
