"""Independent stdlib archive audit for the dependency-import policy primitive."""
import ast
from hashlib import sha256
import json
from pathlib import Path
import sys
PACKAGE=Path(__file__).resolve().parent;BASE=PACKAGE.parent;OUT=BASE/'checks_01';ROOT=BASE.parents[2]
OLD=ROOT/'results/tables/staged_rts24_saved_fresh_wire_data_v1_non_authoritative'
OLD_POLICY=ROOT/'results/tables/staged_rts24_saved_fresh_import_policy_v1_non_authoritative'
def raw(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')
def pin(v):return dict(bytes=len(v),sha256=sha256(v).hexdigest())
def read(p):return json.loads(p.read_bytes())
def names(paths):return {p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in paths}
def snapshot(p,n=None):
    for d in (OUT,OLD_POLICY/'checks_01',OLD/'checks_02',OLD/'checks_01',ROOT/'results/tables/staged_rts24_saved_fresh_role_data_v1_non_authoritative/checks_01'):
        path=d/('code_'+p['sha256']+'.snapshot')
        if path.exists():data=path.read_bytes();assert pin(data)==p;return data
    path=ROOT/read(OLD/'checks_01/baseline.json')['source_snapshots'][n];data=path.read_bytes();assert pin(data)==p;return data

# Complete AST hashes of the manually reviewed, bounded v1-to-v2 changes.
# Every other predecessor node is compared positionally, including class metadata.
ALLOWED_AST={
    '_saved_import_inputs':'77099d324b489c0555fcac21a2d196b5ab53c621e28e8cfa223353c8ce909e57',
    'SavedSuccessorImportBoundary._entry':'d618973b68a740feffc7821a6d65027a554269bdbb8f47739da04997bdf5efd1',
    'SavedSuccessorImportBoundary.close':'44e2dd6e47d812241561d04ddb8a423e856b5bd52c0718078d6c3cd0401edcb5',
    'open_saved_successor_import_boundary':'ced1e40e9f17189180cd644b5294c0b8ffa51937fe953a225d30989e800f56af',
    'load_saved_successor_dependencies':'f55b83d21e42c5189068dc2671e32ce7df5487dcde1f1f72e8f8720c4e071c88',
    'import_policy_unit':'ce405cc0452b9cd4d665de6084b64904e885728345c013a0c5be567a0610060e',
    'test_saved_import_policy_factory_literal_and_single_attempt':'28b892566d11035c2f8ce85044fc218b9ccb16e10f582aa9808dbd573ad40316',
    'test_saved_import_policy_fixed_external_hardlink_read_scope':'0e4fe33ce34e6c8284e78a41d6e21d026a20eeeac4f91fd1a6b20f06601d3e69',
    'test_saved_import_policy_external_reader_rejects_unpinned_domain':'a532700a0448ef9f4aca6d7bc3a95373ec34238d1c2daa85aef3e21fd2b82773',
    'test_saved_import_policy_canonical_source_bookend':'e34ebcde6512db9aa6ea54ccab766992d94b29649a74c2089e0f0d85e1117423',
}
NEW_TESTS=list(ALLOWED_AST)[-3:]
def node_raw(n):return ast.dump(n,include_attributes=False).encode('utf8')
def exact_delta(baseline,plan):
    seen=set()
    for name in baseline['protected_api_nodes']:
        before=ast.parse(snapshot(baseline['sources'][name],name));after=ast.parse(snapshot(plan['source_pins'][name],name))
        compile(before,name,'exec',dont_inherit=True);compile(after,name,'exec',dont_inherit=True)
        assert before.type_ignores==after.type_ignores==[]
        extra=3 if name.startswith('tests/') else 0
        assert len(after.body)==len(before.body)+extra
        named=[n.name for n in after.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))]
        assert len(named)==len(set(named))
        for old,new in zip(before.body,after.body):
            key=getattr(old,'name',None);assert type(old) is type(new)
            assert key==getattr(new,'name',None)
            if key=='SavedSuccessorImportBoundary':
                assert len(old.body)==len(new.body)
                old_members=old.body;new_members=new.body
                old.body=[];new.body=[];assert node_raw(old)==node_raw(new)
                for left,right in zip(old_members,new_members):
                    sub=key+'.'+getattr(left,'name','')
                    if sub in ALLOWED_AST:
                        assert sha256(node_raw(right)).hexdigest()==ALLOWED_AST[sub];seen.add(sub)
                    else:assert node_raw(left)==node_raw(right)
            elif key in ALLOWED_AST:
                assert sha256(node_raw(new)).hexdigest()==ALLOWED_AST[key];seen.add(key)
            else:assert node_raw(old)==node_raw(new)
        if extra:
            assert [n.name for n in after.body[-3:]]==NEW_TESTS
            for n in after.body[-3:]:
                assert type(n) is ast.FunctionDef and sha256(node_raw(n)).hexdigest()==ALLOWED_AST[n.name];seen.add(n.name)
    assert seen==set(ALLOWED_AST)

def archive_and_resources(baseline,records):
    initial={k:sum(r['charged_seconds'] for p,r in records.values() if r['kind']==k and (OLD_POLICY in p.parents or OLD in p.parents)) for k in ('static','pytest')}
    assert all(abs(initial[k]-baseline['starting_charged_seconds'][k])<1e-7 for k in initial)
    for label,fragment in (('pytest_a',b'TypeError: Object of type bytes is not JSON serializable'),('pytest_retry',b'1 failed, 31 passed')):
        record=read(OLD_POLICY/'checks_01'/(label+'.exit.json'))
        output=(OLD_POLICY/'checks_01'/(label+'.stdout.log')).read_bytes()
        assert record['accepted'] is False and record['returncode']==1 and record['postcheck_pins_match'] and fragment in output
        assert record['source_pins']==record['after_source_pins'] and record['helper_pins']==record['after_helper_pins']
        admission=read(OLD_POLICY/'checks_01'/('admission.json' if label=='pytest_a' else 'admission_revision.json'))
        assert record['source_pins']==admission['source_pins'] and record['source_epoch']==admission['source_epoch']
        if label=='pytest_retry':
            assert b'SavedSuccessorImportUnresolved' in output and b'external_bookend' in output
            assert b'test_saved_import_policy_closed_local_result_never_opens_authority' in output
    assert not list((OLD_POLICY/'checks_01').glob('cold_*'))
    policy=read(OUT/'import_policy.json');proposal=read(OUT/'runtime_profile_v3_proposal.json')
    assert proposal['preserved_v1_policy_pin']==pin((OLD_POLICY/'checks_01/import_policy.json').read_bytes())
    for n,row in baseline['external_metadata_at_v2_preparation'].items():
        expected_nlink=1 if n.endswith('utils.py') else 2
        assert row['st_nlink']==expected_nlink and row['would_fail_v1_single_link_predicate']==(expected_nlink!=1)
    assert baseline['metadata_limits']=='current inspection, not a reconstructed v1 runtime observation; hardlink alias authentication false'
    assert policy['external_file_read_policy']==dict(regular_files_only=True,reject_reparse_paths=True,hardlinks='allowed_for_fixed_pinned_external_sources_only',identity_and_parent_bookends=True,filesystem_alias_authentication=False)
    def usage(root):
        files=[p for p in root.rglob('*') if p.is_file()];return dict(files=len(files),bytes=sum(p.stat().st_size for p in files))
    old=usage(OLD);v1=usage(OLD_POLICY);v2=usage(BASE)
    assert old['files']<=204 and old['bytes']<=16*1024**2
    assert v1['files']==38 and v1['bytes']<=4*1024**2
    assert v2['files']<=64 and v2['bytes']<=4*1024**2
    assert v1['files']+v2['files']<=128 and v1['bytes']+v2['bytes']<=8*1024**2
    return dict(wire=old,import_policy_v1=v1,import_policy_v2=v2)
def verify():
    baseline=read(OUT/'baseline.json');plan=read(OUT/'admission_final.json')
    assert len(baseline['preserved'])==4576 and names(ROOT/n for n in baseline['preserved'])==baseline['preserved']
    assert names(ROOT/n for n in plan['source_pins'])==plan['source_pins'] and len(plan['source_pins'])==49
    assert plan['source_epoch']==sha256(raw(plan['source_pins'])).hexdigest()
    controls=names(OUT/n for n in ('baseline.json','import_policy.json','runtime_profile_v3_proposal.json','revision_final.json'))
    assert plan['controls_pins']==controls
    revision=read(OUT/'revision_final.json')
    original=read(OUT/'collection.exit.json')
    weak=PACKAGE/'oracle.py';weak_snapshot=OUT/('code_'+pin(weak.read_bytes())['sha256']+'.snapshot')
    original_paths=[OUT/n for n in ('baseline.json','import_policy.json','runtime_profile_v3_proposal.json','collection.exit.json','admission.json','collection.harness.json')]+[weak,weak_snapshot]
    assert revision['original_artifact_pins']==names(original_paths)
    assert original['accepted'] and original['returncode']==0 and original['source_pins']==plan['source_pins']
    assert names(ROOT/n for n in revision['original_artifact_pins'])==revision['original_artifact_pins']
    assert plan['helper_pins']==revision['helper_pins'] and names(ROOT/n for n in plan['helper_pins'])==plan['helper_pins']
    assert plan['source_pins']==revision['source_pins']==read(OUT/'admission.json')['source_pins']
    assert plan['groups']==read(OUT/'admission.json')['groups'] and plan['current_targeted_nodes']==41
    assert revision['phase_caps']==dict(collection_final=8,pytest_a=30,cold_import=12,saved=7,terminal=7)
    anchor=read(OUT/'collection_final.exit.json')['child_artifact_pins']
    assert anchor[(OUT/'revision_final.json').relative_to(ROOT).as_posix()]==pin((OUT/'revision_final.json').read_bytes())
    assert anchor[(OUT/'collection_final.harness.json').relative_to(ROOT).as_posix()]==pin((OUT/'collection_final.harness.json').read_bytes())
    assert read(OUT/'collection_final.exit.json')['child_artifact_pins'][(OUT/'admission_final.json').relative_to(ROOT).as_posix()]==pin((OUT/'admission_final.json').read_bytes())
    mutable={'experiments/staged_rts24_saved_fresh_adoption_v1.py','tests/test_staged_rts24_saved_fresh_adoption_v1.py'}
    assert all(p==baseline['sources'][n] for n,p in plan['source_pins'].items() if n not in mutable)
    for n in baseline['protected_api_nodes']:
        before=ast.parse(snapshot(baseline['protected_sources'][n],n));data=snapshot(plan['source_pins'][n],n);after=ast.parse(data);compile(after,n,'exec',dont_inherit=True)
        prefix=len(before.body)-(1 if n.startswith('experiments/') else 0)
        assert [ast.dump(node) for node in after.body[:prefix]]==[ast.dump(node) for node in before.body[:prefix]]
        if n.startswith('experiments/'):assert ast.dump(after.body[-1])==ast.dump(before.body[-1])
    exact_delta(baseline,plan)
    policy_raw=(OUT/'import_policy.json').read_bytes();policy=read(OUT/'import_policy.json');proposal=read(OUT/'runtime_profile_v3_proposal.json')
    assert policy_raw==raw(policy) and proposal['import_policy_pin']==pin(policy_raw)
    assert proposal['does_not_supersede_or_open_v2'] and proposal['admissible_for_production_execution'] is False
    parent=ROOT/'results/tables/staged_rts24_saved_fresh_runtime_binding_v1_non_authoritative/checks_01/runtime_binding_contract_v2.json'
    assert proposal['parent_profile_pin']==pin(parent.read_bytes()) and read(parent)['external_import_probe_policy']=='UNDECIDED_BLOCKING' and read(parent)['admissible_for_production_execution'] is False
    for n,row in baseline['external_metadata_at_v2_preparation'].items():
        assert row['regular'] and not row['reparse'] and row['st_nlink']>=1 and len(row['identity'])==4
    expected_external={policy['executable_path']:policy['executable_pin'],**policy['external_sources']}
    assert {n:r['pin'] for n,r in baseline['external_metadata_at_v2_preparation'].items()}==expected_external
    assert policy['protected_open_roots']=={'P1':str(ROOT/'results/tables/staged_rts24_native_v1_non_authoritative/p1_01'),'actual_F':str(ROOT/'results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative')}
    harness=read(OUT/'pytest_a.harness.json');group=plan['groups']['pytest_a'];record=read(OUT/'pytest_a.exit.json')
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
    records={p.relative_to(ROOT).as_posix():(p,read(p)) for d in (OLD/'checks_01',OLD/'final_package_01',OLD/'checks_02',OLD/'final_package_02',OLD_POLICY/'checks_01',OUT,PACKAGE) for p in d.glob('*.exit.json')}
    ordered=sorted(records,key=lambda n:len(records[n][1]['prior_record_pins']));spent=dict(static=0.,pytest=0.)
    for i,n in enumerate(ordered):
        path,r=records[n];assert r['prior_record_pins']=={k:pin(records[k][0].read_bytes()) for k in ordered[:i]}
        assert all(abs(r['previous_charged_seconds'][k]-spent[k])<1e-7 for k in spent)
        assert r['fixed_before']==r['fixed_after'] and r['charged_seconds']<=r['cap_seconds']
        if path.parent in (OUT,PACKAGE):
            expected=plan['source_pins']
            assert r['postcheck_pins_match'] and r['source_pins']==r['after_source_pins']==expected and r['helper_pins']==r['after_helper_pins']
            expected_controls={n:p for n,p in controls.items() if not n.endswith('/revision_final.json')} if r['label']=='collection' else controls
            assert r['controls_pins']==r['after_controls_pins']==expected_controls and not r['missing_child_artifacts']
            assert names(ROOT/n for n in r['child_artifact_pins'])==r['child_artifact_pins']
            if r['label']!='collection':
                assert r['helper_pins']==plan['helper_pins']
        for suffix in ('stdout','stderr'):assert pin(path.with_name(r['label']+'.'+suffix+'.log').read_bytes())==r[suffix+'_pin']
        for name,p in {**r['source_pins'],**r['helper_pins']}.items():snapshot(p,name)
        state=r['bounded_drain'];assert state['reader_threads_terminal'] and state['pipes_closed'] and not state['cleanup']
        assert all(r[k] is False for k in ('actual_F','scientific_evidence_adopted','resource_admission','formal_result'))
        spent[r['kind']]+=r['charged_seconds']
    assert spent['static']<=120 and spent['pytest']<=420 and sum(spent.values())<=540
    resource_usage=archive_and_resources(baseline,records)
    assert {r['label'] for _,r in records.values() if not r['accepted']}=={'wip_static_02','r1_new_smoke','r3_old_expectation_a_12','pytest_a','pytest_retry'}
    failed=read(OLD_POLICY/'checks_01/pytest_a.exit.json');assert failed['returncode']==1 and not failed['accepted']
    assert b'TypeError: Object of type bytes is not JSON serializable' in (OLD_POLICY/'checks_01/pytest_a.stdout.log').read_bytes()
    assert plan['helper_pins'][Path(__file__).relative_to(ROOT).as_posix()]==pin(Path(__file__).read_bytes())
    assert not any(n.endswith('/oracle.py') for n in read(OLD_POLICY/'checks_01/collection.exit.json')['helper_pins'])
    for n,row in read(OUT/'pre_seal_review.json')['navigation'].items():
        data=(ROOT/row['checkpoint_snapshot']).read_bytes();assert pin(data)==row['checkpoint_pin']
        assert pin((ROOT/n).read_bytes()) in (row['checkpoint_pin'],row['published_pin'])
        header,body=data.split(b'\n\n',1);prefix=row['prefix'].encode();assert body.startswith(prefix)
        assert pin(header+b'\n\n'+body[len(prefix):])==row['original_pin']
    files=[p for p in BASE.rglob('*') if p.is_file()];assert len(files)<=64 and sum(p.stat().st_size for p in files)<=4*1024**2
    return dict(authority='DRAFT_NONAUTHORITATIVE',source_epoch=plan['source_epoch'],current_policy_unit_nodes=plan['current_targeted_nodes'],cold_cases=baseline['cold_cases'],preserved_paths=4576,charged_before_capture=spent,resource_usage_at_audit=resource_usage,production_seal=False,v1_initial_capture_omitted_oracle_helper=True,v2_initial_collection_bound_weak_oracle=True,final_capture_and_admission_bind_oracle=True,exact_v1_to_v2_AST_delta_verified=True,old_API_AST_and_CLI_preserved=True,old_v2_profile_preserved=True,independent_root_verified=False,full_runtime_binding_verified=False,actual_F=False,run_authority=False,scientific_evidence_adopted=False,resource_admission=False,formal_result=False)
if __name__=='__main__':
    mode=sys.argv[1];freeze=PACKAGE/'checkpoint_freeze.json'
    if mode=='saved':
        paths=[p for p in OUT.rglob('*') if p.is_file()]+list(PACKAGE.glob('*.py'))+[ROOT/'docs/plan/staged_deliverability_c_saved_fresh_import_policy_scope_budget_v2.md',ROOT/'docs/plan/continuation_handoff_20261026_saved_fresh_import_policy_v2.md']
        with freeze.open('xb') as stream:stream.write(raw(dict(authority='DRAFT_NONAUTHORITATIVE',production_seal=False,bound_files=names(paths))))
    else:
        assert mode=='terminal'
        anchor=read(PACKAGE/'saved.exit.json')['child_artifact_pins']
        assert anchor[freeze.relative_to(ROOT).as_posix()]==pin(freeze.read_bytes())
        assert anchor[(PACKAGE/'saved_report.json').relative_to(ROOT).as_posix()]==pin((PACKAGE/'saved_report.json').read_bytes())
    f=read(freeze);assert names(ROOT/n for n in f['bound_files'])==f['bound_files']
    report=verify()
    with (PACKAGE/(mode+'_report.json')).open('xb') as stream:stream.write(raw(report))
    print(json.dumps(report,sort_keys=True))
