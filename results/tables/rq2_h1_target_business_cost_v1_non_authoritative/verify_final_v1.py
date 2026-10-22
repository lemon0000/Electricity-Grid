"""Recheck component artifacts and the preserved full preparation checkpoint."""
from hashlib import sha256
import json
from pathlib import Path

import psutil

from postcheck_v1 import HERE,REPO,pin,load


def main():
    core_path=HERE/'development_acceptance_v1.json'
    core=load(core_path)
    assert all(pin(name)==expected for name,expected in core['bindings'].items())
    root=HERE/'cost_01';request=load(root/'request.json');terminal=load(root/'terminal.json')
    assert terminal['exit_code']==0 and terminal['reason'] is None and not terminal.get('error')
    assert terminal['changed_sources']==terminal['observed_processes_remaining']==[]
    assert terminal['junit']==dict(tests=1,failures=0,errors=0,skipped=0,accepted=True)
    assert all(pin(name)==expected for name,expected in request['sources_sha256'].items())
    tested={}
    for path in (root/'tested_bytes').rglob('*'):
        if path.is_file():
            original=REPO/path.relative_to(root/'tested_bytes')
            assert pin(path)==request['sources_sha256'][str(original)]
            tested[str(path)]=pin(path)
    assert len(tested)==14
    for name,value in terminal['retained_base_json'].items():
        assert Path(name).read_bytes()==Path(value['copy']).read_bytes()
        assert pin(value['copy'])==value['sha256']
    overlay=load(HERE/'parameter_overlay_verification_v1.json')
    assert all(pin(name)==expected for name,expected in overlay['bindings'].items())
    assert overlay['initial_zero_business_state_verified'] is True
    snapshot=HERE/'preseal_before_contract_fix'
    for row in load(snapshot/'snapshot_bindings.json')['files']:
        assert pin(row['preserved_path'])==row['sha256']
    old_final=load(snapshot/'final_verification.json')
    assert pin(snapshot/'final_verification.json')=='77ff060d9fc81d1bb8a0c43ea20fe516b15c75beebaad99467bb70f151722c8e'
    for name,value in old_final['bindings'].items():
        path=Path(name);choices=[path]
        try:choices.append(snapshot/path.relative_to(HERE))
        except ValueError:pass
        assert any(p.is_file() and pin(p)==value for p in choices),name
    previous=HERE.parent/'rq2_h1_constructor_window_fault_v1_non_authoritative/final_verification.json'
    assert pin(previous)=='925f9370ad00f72d8cb0a3af7abdca26dcb8eb168f346ba9ac24b763232fcb20'
    prior=load(previous)
    assert len(prior['bindings'])==208 and all(pin(name)==expected for name,expected in prior['bindings'].items())
    state=load(previous.parent/'formal_preparation_state_v4.json')
    assert len(state['gates'])==16 and all(g['complete'] is False for g in state['gates'])
    case=Path('D:/h1_outage_connected_03_non_authoritative/test_three_hour_connected_outa0')
    expected=load(REPO/'results/tables/rq2_h1_cross_hour_outage_v1_non_authoritative/connected_03_postcheck.json')['diagnostic_case_files_sha256']
    assert {str(p):pin(p) for p in case.rglob('*') if p.is_file()}==expected
    owned=load(case/'external_preclose_checkpoint.json')['saved_files_sha256']
    assert len(expected)==465 and len(owned)==444 and all(pin(name)==value for name,value in owned.items())
    remaining=[]
    for pid,created in terminal['observed_processes'].items():
        try:
            process=psutil.Process(int(pid))
            if process.create_time()==created and process.is_running():remaining.append(int(pid))
        except psutil.NoSuchProcess:pass
    assert not remaining
    bindings=dict(core['bindings']);bindings[str(core_path)]=pin(core_path)
    result=dict(status='DRAFT_NONAUTHORITATIVE',latest_core=str(core_path),latest_core_sha256=pin(core_path),
        core_bindings_verified=len(core['bindings']),bindings=bindings,
        request_live_pins_verified=len(request['sources_sha256']),explicit_tested_snapshot_sha256=tested,
        prior_constructor_final_bindings_current_verified=208,
        retained_base_original_and_copy_bytes_equal=True,
        actual_parameter_overlay_and_bound_tolerance_source_verified=True,
        actual_initial_zero_state_and_ledger_verified=True,
        preserved_superseded_draft_final_sha256=pin(snapshot/'final_verification.json'),
        preserved_superseded_draft_bindings_resolved=len(old_final['bindings']),
        source_authenticated_boundary_anchor=False,saved_case_files=465,saved_owned_files=444,
        saved_case_and_owned_sha256_unchanged=True,owned_observed_processes_remaining=remaining,
        complete_unobserved_process_tree_proof=False,open_preparation_gates=16,objective_complete=False,
        overall_performance_review_complete=False,resource_admission=False,native_execution_authorized=False,
        formal_execution_ready=False,full_192_hour_execution_verified=False,sealed=False,
        independent_official_review_performed=False,new_normal_jobs=0,real_native_calls=0,formal_result=False)
    target=HERE/'final_verification.json'
    expected_bytes=(json.dumps(result,indent=2)+'\n').encode('utf-8')
    if target.exists() and target.read_bytes()!=expected_bytes:
        assert target.read_bytes()==(snapshot/target.name).read_bytes()
    target.write_bytes(expected_bytes)
    print(json.dumps(dict(core_bindings=len(core['bindings']),final_bindings=len(bindings),
        source_pins=len(request['sources_sha256']),tested_snapshots=len(tested),old_final=208,
        case=465,owned=444,remaining=remaining,final_sha256=pin(HERE/'final_verification.json'))))


if __name__=='__main__':main()
