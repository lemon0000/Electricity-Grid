"""Read-only byte/transcript checks. Does not execute saved F or grant authority."""
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
ENTRY = 'experiments/staged_rts24_saved_fresh_adoption_v1.py'
TESTS = 'tests/test_staged_rts24_saved_fresh_adoption_v1.py'
FINAL = ('console_units_12', 'file_smoke_13', 'invocation_units_15', 'late_payload_16',
    'invocation_graph_17', 'invocation_edges_18', 'adapter_19')
GATES = ('F_launch_admitted', 'saved_P1_fresh_process_verified', 'saved_P1_parent_adoption_verified',
    'native_authorized', 'scientific_evidence_adopted', 'resource_admission', 'formal_result', 'public_P2_execution_enabled')


def pin(raw): return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())
def canonical(value): return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('ascii')
def read(name): return json.loads((OUT/name).read_bytes())
def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def proof(value, role, context_sha, startup, selected):
    assert value['schema'] == 'staged_saved_F_ordinary_file_bootstrap_v1'
    assert value['authority'] == 'DRAFT_NONAUTHORITATIVE' and value['scope'] == 'ordinary_file_entry_self_check_only'
    assert value['role'] == role and value['context_sha'] == context_sha
    assert all(value[k] is False for k in GATES)
    assert value['main_is_canonical_module'] is value['main_spec_is_none'] is True
    assert value['independent_OS_commandline_verified'] is value['full_runtime_closure_verified'] is False
    assert value['project_imports_before_bootstrap'] == []
    assert value['project_import_scan'] == 'module_file_paths_and_project_namespaces'
    assert value['entry_pin'] == selected[ENTRY] and Path(value['entry_path']) == ROOT/ENTRY
    assert value['sys_path'][0] == str(ROOT) and len(set(value['sys_path'])) == len(value['sys_path'])
    assert sha256(canonical(value['sys_path'])).hexdigest() == value['sys_path_sha']
    args = startup['argv']
    assert args[:6] == [r'D:\Miniconda3\envs\compute\python.exe', '-B', '-s', str(ROOT/ENTRY), '--ordinary-entry', '--'+role]
    assert value['argv_sha'] == value['orig_argv_sha'] == sha256(canonical(args)).hexdigest()
    assert value['flags'] == dict(dont_write_bytecode=True, no_user_site=True, hash_randomization=False)


def verify():
    assert Path(sys.executable).absolute() == Path(r'D:\Miniconda3\envs\compute\python.exe')
    baseline = read('baseline_snapshot.json'); preserved = read('preservation_inventory.json')
    assert len(preserved) == baseline['preserved_count'] == 1724
    for name, expected in preserved.items(): assert pin((ROOT/name).read_bytes()) == expected, name
    for name, expected in read('navigation_before.json').items():
        raw = (ROOT/name).read_bytes()
        assert raw.partition(b'\n\n')[0].decode() == expected['header']
        assert pin(raw[-expected['body']['bytes']:]) == expected['body']
    for name, item in read('baseline_source.json').items():
        assert pin((ROOT/item['snapshot']).read_bytes()) == item['pin']
    assert read('baseline_saved_01.exit.json')['exit_code'] == 0
    old_check = read('baseline_saved_01.stdout.log')
    assert old_check['canonical_draft_matches_final_snapshot'] is old_check['frozen_source_snapshots_verified'] is True
    selected = read('component_source_pins.json'); assert len(selected) == 49
    for name, expected in selected.items(): assert pin((ROOT/name).read_bytes()) == expected, name
    summary = read('ordinary_check_summary.json'); assert summary['source_pins'] == selected
    total, final_nodes = 0., []
    for label, archived in summary['all_pytest_attempts'].items():
        value = read(label+'.exit.json'); total += value['wall_seconds']
        assert value['source_pins_unchanged'] is True
        for suffix, expected in archived['pins'].items():
            assert pin((OUT/(label+'.'+suffix)).read_bytes()) == expected
        for name, item in read(value['snapshot_manifest'])['sources'].items():
            assert pin((ROOT/item['snapshot']).read_bytes()) == item['pin'] == value['source_pins'][name]
        if label in FINAL:
            assert value['source_pins'] == selected and value['exit_code'] == 0 and value['timed_out'] is False
            assert value['wall_seconds'] <= value['timeout_seconds']
            assert (OUT/(label+'.stderr.log')).read_bytes() == b''
            assert (str(len(value['nodes']))+' passed').encode() in (OUT/(label+'.stdout.log')).read_bytes()
            final_nodes.extend(value['nodes'])
    assert len(final_nodes) == len(set(final_nodes)) == 72 and set(final_nodes) == set(summary['final_nodeids'])
    assert abs(total-summary['pytest_actual_seconds']) < 1e-8 and total <= 240
    assert read('role_graph_07.exit.json')['exit_code'] == 1
    assert read('role_graph_14.exit.json')['timed_out'] is True
    assert read('role_graph_14.exit.json')['exit_code'] is None
    assert all(label not in FINAL for label in ('role_graph_07', 'role_graph_14', 'file_units_04', 'role_units_06'))
    assert summary['earlier_epoch_not_counted_as_current'] == dict(file_units_04=54, role_units_06=26)
    derivation = module('entry_derivation', OUT/'verify_invocation_derivation.py').verify()
    assert derivation == read('derivation_01.stdout.log')
    old_path = ROOT/'results/tables/staged_rts24_saved_fresh_invocation_v1_non_authoritative/checks_01/saved_checks.py'
    old = module('entry_history_process', old_path)
    graphs = read('invocation_graph_snapshots.json')
    normal = next(row for row in graphs if row['label'] == 'file_smoke_13')
    result = json.loads((ROOT/normal['result']).read_bytes())
    assert result['ordinary_external_invocation_completed'] is True and all(result[k] is False for k in GATES)
    outer = result['broker_process']; returned = result['broker_return']; controller = returned['controller_process']
    context_sha = result['held_context_pin']['sha256']
    artifact = lambda name: json.loads((ROOT/normal['files'][name]['archive']).read_bytes())
    parent, fresh = artifact('worker/launcher.json'), artifact('worker/fresh/launcher.json')
    ids = [old.process_oracle(outer, result['request_sha'])]
    ids += [old.process_oracle(value, context_sha) for value in (controller, parent, fresh)]
    assert ids[3] < ids[2] < ids[1] < ids[0] and list(map(len, ids)) == [8, 6, 4, 2]
    assert len(normal['files']) == 16
    assert result['whole_F_180_seconds_proved'] is result['host_hard_resource_enforcement_proved'] is False
    proof(returned['controller_return']['entry_bootstrap'], 'supervise', context_sha, controller['startup'], selected)
    for role, record, name in [('parent', parent, 'worker/events.jsonl'), ('fresh', fresh, 'worker/fresh/events.jsonl')]:
        data = (ROOT/normal['files'][name]['archive']).read_bytes().splitlines()
        proof(json.loads(data[0])['entry_bootstrap'], role, context_sha, record['startup'], selected)
    for name, item in returned['controller_return']['result']['output_inventory'].items():
        assert item['pin'] == normal['files'][name]['original_pin']
    current_faults = [row for row in graphs if row['label'] == 'invocation_graph_17']
    assert len(current_faults) == 5
    for row in current_faults:
        value = json.loads((ROOT/row['result']).read_bytes())
        assert value['ordinary_external_invocation_completed'] is False
        old.process_oracle(value['broker_process'], value['broker_process']['startup']['context_sha'])
    events = read('final_auxiliary_events.json')
    for event in events:
        raw = (ROOT/event['source_log']).read_bytes(); assert pin(raw) == event['source_log_pin']
        data = raw.splitlines()[event['line']-1].partition(event['marker'].encode())[2]
        assert pin(data) == event['pin'] and json.loads(data) == event['value']
    native = next(e['value'] for e in events if e['marker'] == 'CONSOLE_CACHE_NATIVE ')
    assert native['stage_success_claimed'] is False and native['F_launch_admitted'] is False
    witness = native['witness']; assert witness['all_handles_signaled'] is witness['complete_inventory'] is True
    assert witness['active_processes'] == 0 and witness['final_pids'] == []
    negative = next(e['value'] for e in events if e['marker'] == 'CONSOLE_CACHE_DESCENDANT ')
    assert negative['primary_stop_reason'] == 'root_exited_with_descendants'
    assert negative['job_quiet_confirmed'] is True and negative['stage_process_observed_successfully'] is False
    resources = [e['value'] for e in events if e['marker'] == 'INVOCATION_RESOURCE_FAILURE ']
    assert len(resources) == 2
    for value in resources:
        assert value['primary'] == value['process']['monitor_error']
        assert value['primary']['message'] == 'combined host and owned Job resource limit'
    reuse = module('entry_stage_history', OUT/'stage_reuse_oracle.py').verify()
    assert reuse == read('stage_reuse_02.stdout.log')
    prior = module('entry_history_p1', ROOT/'results/tables/staged_rts24_saved_fresh_roles_v1_non_authoritative/checks_01/saved_checks.py')
    assert prior.saved_P1_bytes() == 683
    for name, expected in read('document_checks.json')['document_pins'].items():
        assert pin((ROOT/name).read_bytes()) == expected
    review = read('preseal_review.json')
    assert review['remaining_required_code_findings'] == []
    assert review['official_verdict'] is review['receipt'] is review['seal'] is None
    assert review['source_pins'] == {n: selected[n] for n in (ENTRY, TESTS, 'src/staged_rts24_saved_fresh_adoption_v1.py')}
    assert read('disabled_entry_01.exit.json')['exit_code'] == 1
    assert b'F launch remains disabled' in (OUT/'disabled_entry_01.stderr.log').read_bytes()
    assert not (ROOT/'results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative/draft_01').exists()
    for name, expected in read('support_pins.json').items(): assert pin((ROOT/name).read_bytes()) == expected, name
    return dict(authority='DRAFT_NONAUTHORITATIVE', scope='ordinary direct-file entry and saved integrity only',
        preserved_old_paths=1724, P1_file_bytes_unchanged=683, navigation_bodies_preserved=3,
        current_source_terminal_pass_nodes=72, prior_epoch54_and26_counted_as_current=False,
        historical_generic_stage_guard_nodes=87, historical_stage_counted_as_current=False,
        pytest_actual_seconds=total, raw_derivation=derivation,
        role_group_timeout_remains_nonpassing=True, forced_terminal_helper_window_proved=False,
        saved_F_workflow_executed=False, new_native_solver_calls=0, **{k: False for k in GATES})


if __name__ == '__main__': sys.stdout.buffer.write((json.dumps(verify(), sort_keys=True, indent=2)+'\n').encode())
