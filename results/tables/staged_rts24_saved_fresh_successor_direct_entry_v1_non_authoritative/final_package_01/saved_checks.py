"""Independent frozen execution/package oracle; never import current ENTRY/helpers."""
import ast
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[4];OUT=Path(__file__).resolve().parent;MAIN=OUT.parent/'checks_01'
PRIOR=ROOT/'results/tables/staged_rts24_saved_fresh_successor_self_anchor_v1_non_authoritative/checks_01'
SOURCES=('src/staged_rts24_saved_fresh_adoption_v1.py','experiments/staged_rts24_saved_fresh_adoption_v1.py',
    'tests/test_staged_rts24_saved_fresh_adoption_v1.py')
MUTABLE=set(SOURCES[1:])
CASES=('normal','argv','alias','path','environment','helper','commit','oversize')
GATES=('native_authorized','resource_admission','formal_result','scientific_evidence_adopted','public_P2_execution_enabled')

def pin(raw):return dict(bytes=len(raw),sha256=sha256(raw).hexdigest())
def canonical(value):return json.dumps(value,ensure_ascii=True,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
def read(path):return json.loads(path.read_bytes())
def epoch(source):return sha256(canonical({n:source[n] for n in SOURCES})).hexdigest()
def definitions(raw):return {n.name:ast.dump(n,include_attributes=False) for n in ast.parse(raw).body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
def false_flags(value):
    for key in (*GATES,'role_binding','external_Job_owner','full_runtime_closure_verified','full_P1_content_verified','run_authority','F_launch_admitted'):
        if key in value:assert value[key] is False


def verify(require_current_sources=False,require_current_navigation=False):
    freeze=read(OUT/'execution_freeze.json')
    actual={p.relative_to(ROOT).as_posix():pin(p.read_bytes()) for p in MAIN.rglob('*') if p.is_file()}
    assert actual==freeze['files'] and len(actual)==freeze['count']<=224
    assert sum(p['bytes'] for p in actual.values())==freeze['bytes']<=16*1024**2
    assert sha256(canonical(actual)).hexdigest()==freeze['inventory_root_sha256']
    support=read(OUT/'support_pins.json');support_pin=pin((OUT/'support_pins.json').read_bytes())
    finalizer=read(OUT/'finalizer_20.exit.json');assert finalizer['support_pin']==support_pin
    assert read(OUT/'finalizer_20.stdout.log')['support_pin']==support_pin
    helper_names=('package_capture.py','finalize_evidence.py','saved_checks.py')
    expected_support={p.relative_to(ROOT).as_posix() for p in (OUT/n for n in helper_names)}
    expected_support|={(OUT/('helper_'+pin((OUT/n).read_bytes())['sha256']+'.snapshot')).relative_to(ROOT).as_posix() for n in helper_names}
    expected_support|={(OUT/n).relative_to(ROOT).as_posix() for n in ('execution_freeze.json','finalizer_20.snapshot.json','navigation_after.json','document_checks.json')}
    assert set(support)==expected_support
    for name,item in support.items():assert pin((ROOT/name).read_bytes())==item,name
    package_manifests={p.name.removesuffix('.snapshot.json'):read(p) for p in OUT.glob('*.snapshot.json')}
    for label,manifest in package_manifests.items():
        assert manifest['support_pin']==(None if label=='finalizer_20' else support_pin)
        previous_labels=[] if label=='finalizer_20' else ['finalizer_20'] if label=='saved_21' else ['finalizer_20','saved_21']
        wanted={(OUT/(previous+'.'+suffix)).relative_to(ROOT).as_posix()
            for previous in previous_labels for suffix in ('snapshot.json','stdout.log','stderr.log','exit.json')}
        assert set(manifest['prior_mechanical_pins'])==wanted
        for name,item in manifest['prior_mechanical_pins'].items():assert pin((ROOT/name).read_bytes())==item,name
    plan=read(MAIN/'group_admission_03.json');baseline=read(MAIN/'baseline_sources.json');source=plan['source_pins']
    proposals={1:read(MAIN/'group_admission.json'),2:read(MAIN/'group_admission_02.json'),3:plan}
    assert len(source)==49 and set(source)==set(baseline)
    assert len({epoch(baseline),*(p['source_epoch'] for p in proposals.values())})==4
    for p in proposals.values():assert p['source_epoch']==epoch(p['source_pins'])
    current=True
    for name,item in source.items():
        match=pin((ROOT/name).read_bytes())==item
        if name not in MUTABLE:assert match and item==baseline[name],name
        current &= match
    if require_current_sources:assert current,'current mutable sources differ from tested epoch'
    preserved=read(MAIN/'preservation_inventory.json');assert len(preserved)==3815
    for name,item in preserved.items():assert pin((ROOT/name).read_bytes())==item,name
    first={'collection_03','admission_04'};second={'collection_07','admission_08','direct_compare_05'}
    base={'baseline_01','prepare_02'}
    probe_labels=dict(zip(CASES,('probe_normal_12','probe_argv_13','probe_alias_14','probe_path_15',
        'probe_environment_16','probe_helper_17','probe_commit_18','probe_oversize_19')))
    records={p.name.removesuffix('.exit.json'):read(p) for p in MAIN.glob('*.exit.json')}
    assert set(records)==base|first|second|{'collection_10','admission_11'}|set(plan['groups'])|set(probe_labels.values())
    totals={'static':0.,'pytest':0.};probe_seconds=0.
    for label,value in records.items():
        assert value['exit_code']==0 and value['timed_out'] is False and value['authority']=='DRAFT_NONAUTHORITATIVE'
        assert 0<=value['wall_seconds']<=value['timeout_seconds']<=40
        totals[value['kind']]+=value['wall_seconds']
        expected=baseline if label in base else proposals[1]['source_pins'] if label in first else proposals[2]['source_pins'] if label in second else source
        assert value['source_pins']==expected and value['source_epoch']==epoch(expected)
        assert value['source_pins_unchanged'] is value['helper_pins_unchanged'] is True
        assert value['actual_saved_F_execution'] is value['F_launch_admitted'] is False
        manifest=read(MAIN/value['snapshot_manifest'])
        assert set(manifest['sources'])==set(SOURCES) and set(manifest['helpers'])==set(value['helper_pins'])
        for kind,items in manifest.items():
            for name,item in items.items():
                wanted=(expected if kind=='sources' else value['helper_pins'])[name]
                assert pin((ROOT/item['snapshot']).read_bytes())==item['pin']==wanted
        assert (MAIN/(label+'.stderr.log')).read_bytes()==b''
        if value['kind']=='pytest':
            group_plan=proposals[2] if label=='direct_compare_05' else plan
            assert value['nodes']==group_plan['groups'][label] and value['timeout_seconds']==group_plan['caps'][label]
            assert re.search(rb'\b'+str(len(value['nodes'])).encode()+rb' passed in ',(MAIN/(label+'.stdout.log')).read_bytes())
            harness=read(MAIN/(label+'.harness.json'))
            assert harness['counts']==dict(optional_Popen_attempts=1,blocked_lscpu=1,unexpected_process_attempts=0,
                native_owner_attempts=0,P1_write_attempts=0,actual_F_write_attempts=0)
            assert harness['native_constructor_guard_installed'] is harness['native_constructor_original_restored'] is True
            assert harness['production_policy_decided'] is harness['arbitrary_native_effects_proved_absent'] is False
        if value.get('requested_kind')=='probe':probe_seconds+=value['wall_seconds']
    assert probe_seconds<=24
    flat=[n for nodes in plan['groups'].values() for n in nodes]
    assert len(flat)==len(set(flat))==282 and sum('::test_saved_direct_entry_' in n for n in flat)==64
    assert len(records['direct_compare_05']['nodes'])==59
    assert sum(plan['caps'].values())==212 and records['direct_compare_05']['wall_seconds']+212<=220
    old=read(PRIOR/'group_admission_04.json')['groups']
    pairs=(('self_smoke_06','self_smoke_19'),('self_rest_07','self_rest_20'),('data_smoke_08','data_smoke_07'),
        ('data_a_09','data_a_08'),('data_b_10','data_b_09'),('source_expectation_11','source_expectation_10'),
        ('expectation_a_12','expectation_a_11'),('expectation_b_13','expectation_b_12'),('binding_14','binding_13'))
    for here,there in pairs:assert plan['groups'][here]==old[there]
    frozen=read(MAIN/'direct_compare_09.snapshot.json')['sources']
    for name,item in read(MAIN/'baseline_01.snapshot.json')['sources'].items():
        before=definitions((ROOT/item['snapshot']).read_bytes());after=definitions((ROOT/frozen[name]['snapshot']).read_bytes())
        assert all(after.get(k)==v for k,v in before.items()),name
    case_specs={
        'argv':('direct entry control changed',['final_bookend']),
        'alias':('direct entry control changed',['final_bookend','alias_restore','restore_witness']),
        'path':('direct entry control changed',['final_bookend','path_restore','restore_witness']),
        'environment':('direct Python-visible environment differs',['final_bookend']),
        'helper':('direct observation dependency changed',['final_bookend']),
        'commit':('creating immutable direct observation required',['final_bookend'])}
    for case,label in probe_labels.items():
        result=read(MAIN/('probe_'+case+'.result.json'));started=read(MAIN/('probe_'+case+'.started.json'))
        expected_raw=(MAIN/('probe_'+case+'.expected.json')).read_bytes();expected=json.loads(expected_raw)
        stdout=(MAIN/('probe_'+case+'.child.stdout.log')).read_bytes();stderr=(MAIN/('probe_'+case+'.child.stderr.log')).read_bytes()
        assert canonical(expected)==expected_raw and pin(expected_raw)==result['expected_pin']==started['expected_pin']
        assert result['primary'] is None and result['cleanup']==[] and result['source_pins']==source and result['ordinary_probe'] is True
        assert result['child_identity']==started['child_identity'] and started['terminal'] is False
        assert result['child_process_handle_closed'] is True and result['actual_saved_F_execution'] is result['F_launch_admitted'] is result['Job_quiet_proved'] is False
        assert result['audit_counts']==dict(allowed_Popen=1,unexpected_process_attempts=0,P1_open_attempts=0)
        assert pin(stdout)==result['stdout_pin'] and pin(stderr)==result['stderr_pin'] and stderr==b''
        drain=result['bounded_drain']
        assert drain['cleanup']==[] and drain['pipes_closed'] is drain['reader_threads_terminal'] is True
        assert (drain['stdout_capacity'],drain['stderr_capacity'],drain['chunk_bytes'])==(131073,4096,4096)
        assert str(Path(result['child_identity'][2]).absolute()).casefold()==str(Path(expected['argv'][0]).absolute()).casefold()
        if case=='oversize':
            assert len(stdout)==131073 and drain['stop_reason']=='stdout_limit' and drain['kill_requested'] is True
            assert result['child_exit'] is not None and result['result']['bounded_stdout_overflow_rejected'] is True
            continue
        assert drain['stop_reason'] is None and drain['kill_requested'] is False and stdout.endswith(b'\n')
        record=json.loads(stdout);assert canonical(record)+b'\n'==stdout;false_flags(record)
        assert record['self_handles_closed'] is record['ordinary_probe'] is True and record['audit_hook_active_at_end'] is False
        assert record['audit_counts']==dict(process_attempts=0,P1_open_attempts=0,actual_F_open_attempts=0,write_attempts=0)
        if case=='normal':
            assert result['child_exit']==0 and record['status']=='completed' and record['primary'] is None and record['secondary']==[]
            assert result['result']['independent_parent_expected_compared'] is result['result']['child_identity_compared'] is True
            observation=record['observation'];control=observation['control'];false_flags(observation)
            assert observation['ordinary_probe'] is observation['module_code_matches_disk'] is True
            assert observation['initial_sys_path']==expected['initial_paths'] and control['sys_path']==expected['installed_paths']
            assert canonical(observation['files'])==canonical(expected['files']) and len(observation['files'])==50
            assert control['argv']==expected['argv'][3:] and control['orig_argv']==expected['argv']
            assert canonical(control['environment'])==canonical(expected['environment']) and control['python']==expected['python']
            assert control['cwd']==expected['cwd'] and control['main_name']=='__main__' and control['main_spec_is_none'] is control['canonical_alias_is_main'] is True
            assert canonical(control['flags'])==canonical(dict(dont_write_bytecode=True,no_user_site=True,hash_randomization=False,optimize=0))
            kernel=observation['self_observation'];false_flags(kernel);own=kernel['observation']
            assert [own['pid'],own['process_creation_filetime']]==result['child_identity'][:2]
            assert str(Path(own['image_path']).absolute()).casefold()==str(Path(result['child_identity'][2]).absolute()).casefold()
            assert own['command_line']==subprocess.list2cmdline(expected['argv'])
        else:
            assert result['child_exit']==1 and record['status']=='failed' and record['observation'] is None
            message,layers=case_specs[case]
            assert record['primary']==dict(type='ValueError',message=message,primary=None,secondary=[],truncated=False)
            assert result['result']['case']==case and result['result']['layers']==layers and result['result']['layered_errors_validated'] is True
            assert len(record['secondary'])==1 and [v['layer'] for v in record['secondary'][0]['secondary']]==layers
            assert record['secondary'][0]['secondary'][0]['error']==record['primary']
    package_records={p.name.removesuffix('.exit.json'):read(p) for p in OUT.glob('*.exit.json')}
    assert {'finalizer_20'}<=set(package_records)<={'finalizer_20','saved_21','terminal_22'}
    for label,value in package_records.items():
        assert value['exit_code']==0 and not value['timed_out'] and 0<=value['measured_action_seconds']<=value['timeout_seconds']<=12
        assert value['tail_reserve_seconds']==.5 and value['wall_seconds']==value['measured_action_seconds']+.5
        assert value['support_pin']==support_pin
        assert value['source_pins']==source and value['source_pins_unchanged'] is value['execution_inventory_unchanged'] is value['helper_pins_unchanged'] is True
        manifest=read(OUT/value['snapshot_manifest']);assert manifest['source_pins']==source
        assert manifest['execution_inventory_root_sha256']==freeze['inventory_root_sha256']
        for name,item in manifest['helpers'].items():assert pin((ROOT/item['snapshot']).read_bytes())==item['pin']
        assert (OUT/(label+'.stderr.log')).read_bytes()==b''
        totals['static']+=value['wall_seconds']
    assert totals['pytest']<=240 and totals['static']<=80 and sum(totals.values())<=320
    navigation_current=True
    for name,item in read(OUT/'navigation_after.json').items():
        raw=(ROOT/name).read_bytes();header,separator,body=raw.partition(b'\n\n')
        assert separator and header.decode()==item['header'] and pin(body[-item['body']['bytes']:])==item['body']
        previous=read(MAIN/'navigation_before.json')[name];assert pin(raw[-previous['body']['bytes']:])==previous['body']
        navigation_current &= pin(raw)==item['full']
    if require_current_navigation:assert navigation_current
    docs=read(OUT/'document_checks.json');assert docs['links_resolve'] is True
    for name,item in docs['document_pins'].items():assert pin((ROOT/name).read_bytes())==item,name
    # This published predecessor is fixed by the 3815-file preservation map;
    # its entire verifier chain is stdlib-only and imports no current ENTRY.
    loader=importlib.util.spec_from_file_location('previous_self_anchor_direct_entry_archive',PRIOR/'saved_checks.py')
    previous=importlib.util.module_from_spec(loader);loader.loader.exec_module(previous);prior=previous.verify()
    assert prior['P1_unchanged_files']==683 and prior['frozen_epoch_test_nodes']==218 and prior['scientific_ENTRY_imported_by_oracle'] is False
    if require_current_sources:assert prior['current_epoch_test_nodes']==0
    assert not (ROOT/'results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative').exists()
    package=[p for p in OUT.rglob('*') if p.is_file()];package_bytes=sum(p.stat().st_size for p in package)
    assert len(package)<=32 and package_bytes<=2*1024**2 and len(actual)+len(package)<=256 and freeze['bytes']+package_bytes<=18*1024**2
    return dict(authority='DRAFT_NONAUTHORITATIVE',source_epoch=plan['source_epoch'],current_sources_match_frozen_epoch=bool(current),
        frozen_epoch_test_nodes=282,current_epoch_test_nodes=282 if current else 0,new_comparator_nodes=64,regression_nodes=218,
        historical_other_epoch_passed_nodes=59,ordinary_cold_process_probes=8,normal_cold_parent_comparison=True,
        case_specific_RAM_faults=6,real_bounded_stdout_kill_cleanup=True,real_OS_timeout_verified=False,
        all_attempt_pytest_seconds=totals['pytest'],observed_completed_static_seconds=totals['static'],probe_seconds=probe_seconds,
        observed_completed_check_seconds=sum(totals.values()),current_process_excluded_until_external_exit_record=True,
        execution_ledger_is_target_subprocess_wall=True,package_ledger_includes_pre_post_hashing=True,whole_workflow_wall_budget_verified=False,
        pytest_cap_seconds=240,static_cap_seconds=80,total_cap_seconds=320,preservation_paths=3815,P1_unchanged_files=683,
        frozen_execution_files=freeze['count'],frozen_execution_bytes=freeze['bytes'],package_files=len(package),package_bytes=package_bytes,
        ordinary_probe=True,role_binding=False,external_Job_owner=False,full_runtime_closure_verified=False,full_P1_content_verified=False,
        actual_saved_F_execution=False,F_launch_admitted=False,native_authorized=False,scientific_evidence_adopted=False,
        resource_admission=False,formal_result=False,public_P2_execution_enabled=False,scientific_ENTRY_imported_by_oracle=False,
        navigation_current_whole_pins_match=bool(navigation_current))


if __name__=='__main__':
    sys.stdout.buffer.write((json.dumps(verify(require_current_sources=True,require_current_navigation=True),sort_keys=True,indent=2)+'\n').encode())
