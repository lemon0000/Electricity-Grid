"""Bind final entry results to exact bytes, closure and actual lifecycle receipts."""
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re

import psutil


HERE=Path(__file__).resolve().parent
ROOT=HERE.parent/'validation_path_optimization_01'
ENTRY=ROOT/'entry_revision_04'
REPO=HERE.parents[3]


def read(path):return json.loads(path.read_bytes())


def verify_pins(pins):
    assert all(sha256(Path(path).read_bytes()).hexdigest()==pin for path,pin in pins.items())


def main():
    raw=(ENTRY/'package_manifest_v1.json').read_bytes();manifest_sha=sha256(raw).hexdigest()
    assert manifest_sha=='d13a08fe6db35e9c5c70b8204e3fb4d0091e43a3ef483e3951a561eac0667e43'
    members=json.loads(raw)['files_sha256']
    assert len(members)==21
    verify_pins({str(ENTRY/name):pin for name,pin in members.items()})
    assert re.search("MANIFEST_SHA='([0-9a-f]{64})'",(ENTRY/'launch_validation.py').read_text(encoding='utf-8'))[1]==manifest_sha
    predecessor=read(ENTRY/'configured_predecessor_package_manifest.json')['files_sha256']
    assert set(members)==set(predecessor)|{'configured_predecessor_package_manifest.json'}
    assert all(members[name]==h for name,h in predecessor.items() if name!='interpreter_path_policy_v1.json')
    old_policy=read(ROOT/'entry_revision_03/interpreter_path_policy_v1.json')
    new_policy=read(ENTRY/'interpreter_path_policy_v1.json')
    old_policy['configured_paths'][-2:]=reversed(old_policy['configured_paths'][-2:])
    assert old_policy==new_policy
    evidence={};boundaries={};processes={}
    for label,monitor in (('unit_checks_01','configured_entry_04_unit_monitor_01'),
                          ('routing_checks_01','configured_entry_04_routing_monitor_01')):
        request=read(ENTRY/label/'request.json');terminal=read(ENTRY/label/'terminal.json')
        outer=read(ROOT/monitor/'terminal.json');started=read(ROOT/monitor/'started.json')
        assert request['package_manifest_sha256']==manifest_sha
        verify_pins(request['candidate_sha256'])
        assert terminal['exit_code']==outer['exit_code']==0 and outer['stop_reason'] is None
        assert outer['source_unchanged']
        for key in ('candidate_bytes_unchanged','repository_code_unchanged',
                    'repository_test_closure_unchanged','interpreter_settings_restored'):
            assert terminal[key],(label,key)
        assert terminal['repository_code_file_count']==145 and terminal['repository_test_closure_file_count']==604
        for name in ('repository_code_pins_after.json','repository_pins_after.json'):
            pins=read(ENTRY/label/name);assert not pins['read_errors'];verify_pins(pins['files_sha256'])
        receipt=read(ENTRY/label/'interpreter_path_receipt.json')
        assert receipt['first_failure'] is None
        assert receipt['sdk_preimports_added'] is receipt['loaded_bytes_attested'] is False
        boundaries[label]=[row['boundary'] for row in receipt['observations']]
        assert boundaries[label][0]=='before_repository_imports' and boundaries[label][-1]=='entry_exit'
        evidence[label]=dict(terminal=terminal,monitor=outer,
            terminal_sha256=sha256((ENTRY/label/'terminal.json').read_bytes()).hexdigest(),
            origin_receipt_sha256=sha256((ENTRY/label/'interpreter_path_receipt.json').read_bytes()).hexdigest())
        try:alive=psutil.Process(started['pid']).create_time()==started['creation_time']
        except psutil.NoSuchProcess:alive=False
        assert not alive
        processes[label]=dict(pid=started['pid'],same_process_still_alive=alive)
    unit=evidence['unit_checks_01']['terminal']
    assert unit['tests_run']==78 and unit['skipped']==1 and unit['failures']==unit['errors']==0
    routing=evidence['routing_checks_01']['terminal']
    assert routing['pytest_call_outcomes']==dict(passed=12,failed=0,skipped=0)
    assert routing['pytest_tests_collected']==12 and routing['pytest_tests_failed']==0
    assert routing['pytest_plugin_autoload'] is False and routing['pytest_environment_restored']
    rows=routing['pytest_test_calls'];assert len(rows)==12
    for row in rows:
        assert row['scope_entered'] and row['scope_exited'] and not row.get('scope_error')
        for phase in ('setup','call','teardown'):
            for edge in ('entry','exit'):
                assert phase+'_'+edge+':'+row['nodeid'] in boundaries['routing_checks_01']
    for boundary in ('pytest_configure_before_collection','after_collection_before_fixtures','pytest_return'):
        assert boundary in boundaries['routing_checks_01']
    original=read(HERE.parent/'chain_07/request.json')['before']
    verify_pins(original)
    result=dict(status='DRAFT_NONAUTHORITATIVE',observed_at_utc=datetime.now(timezone.utc).isoformat(),
        package_manifest_sha256=manifest_sha,package_members_sha256=members,
        postcheck_script_sha256=sha256(Path(__file__).read_bytes()).hexdigest(),
        unit_tests=dict(total=78,passed=77,skipped=1),routing_tests=dict(total=12,passed=12),
        measurements={label:dict(seconds=value['terminal']['elapsed_seconds'],
            outer_seconds=value['monitor']['elapsed_seconds'],
            observed_peak_rss_bytes=value['monitor']['peak_observed_process_tree_rss'],
            observed_new_artifact_bytes=value['monitor']['observed_storage_bytes'],
            terminal_sha256=value['terminal_sha256'],origin_receipt_sha256=value['origin_receipt_sha256'])
            for label,value in evidence.items()},
        candidate_and_145_code_604_test_files_unchanged=True,lifecycle_bookends_verified=True,
        owned_processes=processes,original_chain_pins_unchanged=len(original),
        scientific_performance_pair='validation_operation_witness_01/path_order_comparison_01.json',
        path_lease_exercise_scope='routing suite active lease; this suite does not exercise durable episode paths',
        whole_workflow_performance_review_complete=False,long_chain_launch_admitted=False,
        full_chain_passed=False,formal_result=False,resource_admission=False,
        formal_execution_ready=False,native_execution_authorized=False)
    with (ROOT/'configured_entry_04_checks_01.json').open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
