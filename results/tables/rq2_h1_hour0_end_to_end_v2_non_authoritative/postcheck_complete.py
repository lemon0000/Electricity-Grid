"""Validate terminal synthetic evidence and replay it in a separate process."""
import hashlib
import importlib.util
from base64 import b64decode
import json
import os
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[3]
EVIDENCE=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT))


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def load(path):return json.loads(path.read_bytes())
def write(path,value):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2,ensure_ascii=False)
        stream.write('\n')
def inventory(base):
    return {p.relative_to(base).as_posix():digest(p) for p in sorted(base.rglob('*')) if p.is_file()}
def unique(base,name):
    found=list(base.rglob(name))
    assert len(found)==1,(name,found)
    return found[0]


def main(label):
    attempt=EVIDENCE/label
    terminal=load(attempt/'terminal.json')
    assert terminal['exit_code']==0 and terminal['before']==terminal['after']
    trusted=dict(terminal['after'])
    pygments_file=Path(importlib.util.find_spec('pygments').origin).resolve()
    replay_entry=EVIDENCE/'replay_saved_with_fixture_v1.py'
    supplemental=[Path(__file__),replay_entry,EVIDENCE/'preservation_check_02.json',
        ROOT/'results/tables/rq2_v2_obligation_manifest_v1_non_authoritative/obligation_manifest_v2_final.json',
        ROOT/'tests/test_h1_hour0_persistence_faults_development_v2.py',
        ROOT/'tests/test_h1_hour0_selector_parent_routing_development_v2.py',
        *sorted(pygments_file.parent.rglob('*.py'))]
    # Bind current auxiliary test closure without claiming an earlier run anchor.
    auxiliary=load(EVIDENCE/'preservation_check_02.json')['static_tests_closure']
    supplemental += [ROOT/name for name in auxiliary]
    supplemental_pins={str(p):digest(p) for p in supplemental}
    def check_code():
        assert all(digest(ROOT/name)==pin for name,pin in trusted.items())
        assert all(digest(Path(name))==pin for name,pin in supplemental_pins.items())
    check_code()
    assert '1 passed' in (attempt/'stdout.log').read_text(encoding='utf-8')
    base_temp=Path(terminal['command'][terminal['command'].index('--basetemp')+1])
    report_path=unique(base_temp,'complete_integration_report.json')
    base=report_path.parent
    packet_path=unique(base_temp,'takeover_packet.json')
    report=load(report_path);packet=load(packet_path)
    assert report['scope']=='synthetic_hour0' and report['formal_result'] is False
    assert report['real_native_calls']==report['canonical_selector_jobs']==0
    assert report['synthetic_N0_jobs']==3
    paired=report['paired_replay']
    assert paired['completed_hours']==1 and paired['paired_lanes']==3
    assert paired['replayed_from_saved_records'] is True
    assert packet['after']==paired['state']
    lanes=sorted(row['lane_id'] for row in packet['projection']['lanes'])
    assert len(lanes)==len(set(lanes))==3
    assert all(row['status']=='paired_committed' for row in packet['projection']['lanes'])
    assert len(packet['retentions'])==len(packet['tickets'])==len(packet['holder_records'])==2
    holder=Path(packet['common']['holder_receipt']['root'])
    head=digest(holder/'header.json');holder_genesis=head
    for index,(encoded,ticket) in enumerate(zip(packet['holder_records'],packet['tickets']),1):
        raw=(holder/f'{index:06d}.json').read_bytes()
        assert raw==b64decode(encoded,validate=True)
        row=json.loads(raw)
        assert row==dict(sequence=index,previous=head,ticket=ticket)
        after=hashlib.sha256(raw).hexdigest()
        assert packet['retentions'][index-1]==[holder_genesis,head,after,index]
        head=after
    assert head==paired['holder_head']
    journal=packet_path.parent/'journal_non_authoritative'
    head=digest(journal/'header.json')
    for index in range(1,6):
        path=journal/f'{index:020d}.json'
        event=load(path)
        assert event['sequence']==index and event['previous']==head
        head=digest(path)
    assert not (journal/'00000000000000000006.json').exists()
    bookends=load(base/'identity_bookends.json')
    assert bookends['test_only_identity_cache'] is True
    assert bookends['production_overhead_measured'] is False
    assert bookends['transient_code_or_package_ABA_covered'] is False
    assert set(bookends['identities'])=={'src.solvers.rq2_gurobi_declared_normal',
        'experiments.h1_bootstrap_integration_development_v2'}
    for row in bookends['identities'].values():
        assert row['before']==row['after'] and row['calls']>0
    expected=['source_and_fixture_setup']
    for arm in range(3):
        expected += [f'arm_{arm}_open',f'arm_{arm}_N0',f'arm_{arm}_roster_attach']
        if arm<2:expected += [f'arm_{arm}_close']
    expected += ['complete_common_scientific_replay','common_genesis_and_inspect',
        'selector_harness_and_reference_snapshot','Rref_parent_run','missing_all_Actual_rejected']
    expected += ['Actual_'+lane for lane in lanes]
    expected += ['missing_Actual_rejected_'+lane for lane in lanes]
    expected += ['paired_commit_and_readback','selector_parents_and_handoff_closed','arm_2_close',
        'reopen_bootstrap_roster_common_and_close','paired_owner_reopen_replay_and_close',
        'integration_report_saved','identity_bookends_restored']
    timing=[json.loads(line) for line in (attempt/'timing.jsonl').read_text(encoding='utf-8').splitlines()]
    assert [row['label'] for row in timing]==expected
    elapsed=0.
    for row in timing:
        assert row['interval_seconds']>=0
        elapsed += row['interval_seconds']
        assert abs(elapsed-row['elapsed_seconds'])<1e-5
    residual=terminal['elapsed_seconds']-elapsed
    assert residual>=0
    observations=[]
    assert len(report['N0_records'])==len({row['controller_root'] for row in report['N0_records']})==3
    for record in report['N0_records']:
        path=Path(record['controller_root'])/'job_000_non_authoritative/observation.json'
        observation=load(path)
        assert observation['exit_code']==0 and observation['whole_job_quiescent'] is True
        terminal_path=Path(record['controller_root'])/'obligation_non_authoritative/000.terminal.json'
        assert digest(terminal_path)==record['controller_terminal_sha256']
        observations.append(dict(path=str(path),sha256=digest(path),observation=observation))
    assert len({(row['observation']['pid'],row['observation']['creation_filetime']) for row in observations})==3
    post=attempt/'postcheck'
    post.mkdir(exist_ok=False)
    write(post/'request.json',dict(chain_terminal_sha256=digest(attempt/'terminal.json'),
        chain_implementation_files_sha256=trusted,supplemental_files_sha256=supplemental_pins,
        scope='non-authoritative postcheck; supplemental files were not part of chain command',formal_result=False))
    check_code()
    write(post/'chain_postcheck.json',dict(report_path=str(report_path),report_sha256=digest(report_path),
        packet_path=str(packet_path),packet_sha256=digest(packet_path),timing=timing,
        pytest_wall_seconds=terminal['elapsed_seconds'],collection_and_remaining_teardown_seconds=residual,
        timing_conditions=dict(test_only_identity_bookends=True,production_overhead_measured=False,
            concurrent_validation_records={p.name:load(p) for p in sorted(attempt.glob('concurrent_validation*.json'))}),
        N0_observations=observations,identity_bookends=bookends,formal_result=False))
    from experiments import h1_phase_manifest_binding_development_v2 as manifest
    audit=report['common_report']['phase_manifest_candidate']['audit']
    direct=[row for row in audit['group']['siblings']
        if row['arm_id'] in ('network-only','CFE-only','joint-correct')]
    assert len(direct)==3 and {row['arm_id'] for row in direct}=={'network-only','CFE-only','joint-correct'}
    ordinals=sorted(row['ordinal'] for row in direct)
    assert len(set(ordinals))==3 and audit['ordinal'] in ordinals
    sidecars=[]
    for ordinal in ordinals:
        check_code()
        verified=manifest.verifier.prepare_group('training_ub',ordinal)
        compact=manifest._verifier_evidence(verified)
        assert compact['dependency_inventory_sha256']==audit['dependency_verifier']['dependency_inventory_sha256']
        assert compact['verifier_implementation_sha256']==audit['dependency_verifier']['verifier_implementation_sha256']
        if ordinal==audit['ordinal']:
            assert verified['predecessor_group']==audit['group']
            assert compact==audit['dependency_verifier']
        path=post/f'verifier_full_ordinal_{ordinal}.json'
        write(path,verified)
        sidecars.append(dict(path=str(path),sha256=digest(path),ordinal=ordinal,
            dependency_inventory_sha256=compact['dependency_inventory_sha256']))
        check_code()
    write(post/'dependency_sidecars.json',dict(common_audit_ordinal=audit['ordinal'],
        common_audit_sha256=manifest.io.digest(manifest.owner.encode(audit)),sidecars=sidecars,formal_result=False))
    replay=post/'fresh_process_replay'
    replay.mkdir(exist_ok=False)
    bootstrap=('import sys,runpy,importlib.util;'
        f'spec=importlib.util.spec_from_file_location("pygments",{str(pygments_file)!r},submodule_search_locations=[{str(pygments_file.parent)!r}]);'
        'module=importlib.util.module_from_spec(spec);sys.modules["pygments"]=module;spec.loader.exec_module(module);'
        f'sys.path.insert(0,{str(ROOT)!r});runpy.run_path({str(replay_entry)!r},run_name="__main__")')
    command=[sys.executable,'-I','-B','-c',bootstrap,str(base),str(packet_path),
        digest(packet_path),str(report_path),digest(report_path),str(replay/'result.json')]
    before=inventory(base_temp)
    check_code()
    code_before=dict(trusted)
    request=dict(command=command,artifact_root=str(base_temp),synthetic_source_base=str(base),artifact_files_sha256=before,
        implementation_files_sha256=code_before,wall_limit_seconds=1800,
        supplemental_files_sha256_before=supplemental_pins,
        formal_result=False,real_native_authorized=False)
    write(replay/'request.json',request)
    env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTEST_DISABLE_PLUGIN_AUTOLOAD='1')
    start=time.perf_counter()
    with (replay/'stdout.log').open('xb') as out,(replay/'stderr.log').open('xb') as err:
        process=subprocess.Popen(command,cwd=ROOT,env=env,stdout=out,stderr=err)
        write(replay/'started.json',dict(pid=process.pid))
        timed_out=False
        try:code=process.wait(timeout=request['wall_limit_seconds'])
        except subprocess.TimeoutExpired:
            timed_out=True
            # The saved-replay entry only reads holders/SQLite and forbids native;
            # it has no Job or subprocess producer. Terminate this exact handle.
            process.kill()
            code=process.wait()
    after=inventory(base_temp)
    code_after={name:digest(ROOT/name) for name in code_before}
    supplemental_after={name:digest(Path(name)) for name in supplemental_pins}
    write(replay/'terminal.json',dict(exit_code=code,pid=process.pid,timed_out=timed_out,
        elapsed_seconds=time.perf_counter()-start,
        artifact_files_sha256_after=after,implementation_files_sha256_after=code_after,
        artifact_bytes_unchanged=before==after,implementation_bytes_unchanged=code_before==code_after,
        supplemental_files_sha256_after=supplemental_after,
        supplemental_bytes_unchanged=supplemental_pins==supplemental_after,
        formal_result=False))
    assert not timed_out and code==0 and before==after and code_before==code_after and supplemental_pins==supplemental_after
    check_code()
    result=load(replay/'result.json')
    assert result['completed_hours']==1 and result['paired_lanes']==3
    assert result['phase_heads']==paired['phase_heads'] and result['holder_head']==paired['holder_head']
    assert result['carry_sha256']==paired['carry_sha256'] and result['projection_sha256']==paired['projection_sha256']
    assert result['real_native_calls']==result['Jobs']==0 and result['formal_result'] is False
    assert result['copied_reference_verifier_field_rejections']==[
        'historical_verifier_identity','historical_verifier_schema','full_numerical_hour_replays',
        'fresh_byte_context_revalidations','recomputed_on_revalidation']
    assert result['copied_reference_positive_verified'] is True and result['copied_reference_fresh_verifications']==6
    assert result['retained_contract_fault_scope']=='copied reference argument; persisted bytes unchanged'
    write(post/'completed.json',dict(complete_synthetic_hour0_chain=True,fresh_process_saved_replay=True,
        dependency_inventory_preimages_bound=True,timing_reconciled=True,formal_result=False,
        native_calibration=False,production_resource_admission=False))
    check_code()
    write(post/'postcheck_manifest.json',dict(files_sha256=inventory(post),formal_result=False,
        scope='non-authoritative evidence inventory; not a production seal',supplemental_files_sha256=supplemental_pins))
    print(json.dumps(dict(postcheck=str(post),complete_synthetic_hour0_chain=True,
        fresh_process_saved_replay=True,formal_result=False)),flush=True)


if __name__=='__main__':main(sys.argv[1])
