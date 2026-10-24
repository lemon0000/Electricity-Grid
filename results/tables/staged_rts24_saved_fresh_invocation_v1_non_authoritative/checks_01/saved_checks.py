"""Read-only saved development evidence verification; no scientific execution."""
from hashlib import sha256
import importlib.util
import json
import math
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
GATES = ('F_launch_admitted', 'saved_P1_fresh_process_verified', 'saved_P1_parent_adoption_verified',
    'native_authorized', 'scientific_evidence_adopted', 'resource_admission', 'formal_result', 'public_P2_execution_enabled')


def canonical(value): return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('ascii')
def pin(raw): return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())
def read(name): return json.loads((OUT/name).read_bytes())
def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path); value = importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


def slot(value, marker):
    raw = canonical(value); assert 0 < len(raw) <= 4052
    return struct.pack('<I', len(raw))+raw+b'\0'*(4052-len(raw))+sha256(raw).digest()+marker


def process_oracle(value, context_sha):
    assert all(value[name] is False for name in GATES)
    assert value['owner_evidence'] == 'direct_owned_child' and value['job_quiet_confirmed'] is value['quiet_witness_consistent'] is True
    assert value['artifact_contents_read'] is value['external_constructor_and_monitor_interrupt_bound_proved'] is value['terminal_publication_bound_proved'] is False
    witness = value['quiescence_witness']; identities = {(m['pid'], m['creation_filetime']) for m in witness['member_identities']}
    assert witness['all_handles_signaled'] is witness['complete_inventory'] is True
    assert witness['active_processes'] == 0 and witness['final_pids'] == []
    assert witness['total_processes'] == witness['observed_unique_member_handles'] == len(identities) == len(witness['member_identities'])
    header, startup, spec = value['stage_header'], value['startup'], value['descriptor']
    assert header['context_sha'] == startup['context_sha'] == context_sha and header['descriptor'] == spec
    assert startup['descriptor_sha'] == sha256(canonical(spec)).hexdigest()
    assert (header['owner_pid'], header['owner_creation_filetime']) == (startup['owner_pid'], startup['owner_creation_filetime'])
    assert (header['owner_pid'], header['owner_creation_filetime']) in identities
    binding, previous, encoded = sha256(slot(header, b'GRIDHDR1')).hexdigest(), '0'*64, []
    for index, frame in enumerate(value['transcript_frames']):
        assert type(frame['sequence']) is int and frame['sequence'] == index and frame['binding_sha'] == binding and frame['previous_sha'] == previous
        assert (frame['producer_pid'], frame['producer_creation_filetime']) == (header['owner_pid'], header['owner_creation_filetime'])
        assert type(frame['stamp']) is float and math.isfinite(frame['stamp']) and frame['stamp'] > 0
        if frame['phase'] == 'error': assert index == len(value['transcript_frames'])-1 and frame['error_code']
        else: assert frame['phase'] == (spec['phases']+['terminal'])[index] and frame['error_code'] is None
        encoded.append(slot(frame, b'GRIDFRM1')); previous = sha256(canonical(frame)).hexdigest()
    assert sha256(b''.join(encoded)).hexdigest() == value['transcript_sha']
    assert value['samples'] > 0 and value['sampled_tree_peak_rss_bytes'] <= spec['rss_bytes']
    assert value['peak_job_commit_bytes'] <= spec['job_commit_bytes']
    assert value['quiesce_started_at'] <= value['quiesce_completed_at'] <= value['close_attempts_finished_at'] <= value['observation_finished_at'] <= value['total_deadline']
    assert len(value['terminal_system_helpers']) <= 1 and len(canonical(value)) <= 131072
    for helper in value['terminal_system_helpers']:
        assert (helper['pid'], helper['creation_filetime']) in identities and helper['pid'] != startup['owner_pid']
        assert Path(helper['image_path']).name.lower() == 'conhost.exe' and value['root_exit_observed_at'] <= helper['observed_at'] <= value['quiesce_started_at']
    if value['stage_process_observed_successfully']:
        assert value['exit_code'] == 0 and value['primary_stop_reason'] is None and value['stage_transcript_complete'] is True
        assert value['frames_observed'] == len(spec['phases'])+1 and value['terminal_accepted'] is not None
    return identities


def verify():
    assert Path(sys.executable).absolute() == Path('D:/Miniconda3/envs/compute/python.exe'), 'bound compute interpreter required'
    preserved = read('preservation_inventory.json'); assert len(preserved) == 1315
    for name, expected in preserved.items(): assert pin((ROOT/name).read_bytes()) == expected, name
    for name, expected in read('navigation_before.json').items():
        raw = (ROOT/name).read_bytes(); assert raw.partition(b'\n\n')[0].decode() == expected['header']
        assert pin(raw[-expected['body']['bytes']:]) == expected['body']
    docs = read('document_checks.json')
    for name, expected in docs['document_pins'].items(): assert pin((ROOT/name).read_bytes()) == expected, name
    for name, expected in docs['navigation_checkpoint_bodies'].items(): assert pin((ROOT/name).read_bytes()[-expected['bytes']:]) == expected, name
    summary = read('ordinary_check_summary.json'); selected = read('component_source_pins.json'); assert selected == summary['source_pins'] and len(selected) == 49
    canonical_match = True
    for name, expected in selected.items(): canonical_match &= pin((ROOT/name).read_bytes()) == expected
    final = ('invocation_units_20', 'invocation_graph_21', 'invocation_edges_22', 'stages_23', 'bootstrap_24')
    final_nodes = []; total = 0.
    for label, archived in summary['all_pytest_attempts'].items():
        value = read(label+'.exit.json'); total += value['wall_seconds']; assert value['source_pins_unchanged'] is True
        for suffix, expected in archived['pins'].items(): assert pin((OUT/(label+'.'+suffix)).read_bytes()) == expected
        for name, item in read(value['snapshot_manifest'])['sources'].items():
            assert pin((ROOT/item['snapshot']).read_bytes()) == item['pin'] == value['source_pins'][name]
        if label in final:
            assert value['source_pins'] == selected and value['exit_code'] == 0 and value['timed_out'] is False
            assert value['wall_seconds'] <= value['timeout_seconds'] and (OUT/(label+'.stderr.log')).read_bytes() == b''
            assert (str(len(value['nodes']))+' passed').encode() in (OUT/(label+'.stdout.log')).read_bytes()
            final_nodes.extend(value['nodes'])
    assert len(final_nodes) == len(set(final_nodes)) == 127 and set(final_nodes) == set(summary['final_nodeids'])
    assert abs(total-summary['pytest_actual_seconds']) < 1e-8 and total <= 240
    for label in ('invocation_graph_02', 'affected_diagnostic_03', 'invocation_graph_05', 'invocation_graph_08', 'invocation_graph_11'):
        assert read(label+'.exit.json')['exit_code'] == 1
    derivation = module('saved_invocation_derivation', OUT/'verify_invocation_derivation.py').verify()
    assert derivation == read('derivation_01.stdout.log')
    graphs = read('invocation_graph_snapshots.json'); current = {row['case']: row for row in graphs if row['label'] == 'invocation_graph_21'}
    assert set(current) == {'normal', 'prepare_wait', 'constructor_wait', 'publication_wait', 'wrong_ack_nonce', 'wrong_ack_receipt_sha'}
    for case, graph in current.items():
        result = json.loads((ROOT/graph['result']).read_bytes()); assert all(result[name] is False for name in GATES)
        assert result['ordinary_external_invocation_completed'] is (case == 'normal')
        outer_ids = process_oracle(result['broker_process'], result.get('request_sha', result['broker_process']['startup']['context_sha']))
        if case == 'normal':
            assert len(graph['files']) == 16 and len(outer_ids) == 8
            controller = result['broker_return']['controller_process']; controller_ids = process_oracle(controller, result['held_context_pin']['sha256'])
            artifact = lambda name: json.loads((ROOT/graph['files'][name]['archive']).read_bytes())
            parent, fresh = artifact('worker/launcher.json'), artifact('worker/fresh/launcher.json')
            parent_ids = process_oracle(parent, result['held_context_pin']['sha256']); fresh_ids = process_oracle(fresh, result['held_context_pin']['sha256'])
            assert fresh_ids < parent_ids < controller_ids < outer_ids and list(map(len, (controller_ids, parent_ids, fresh_ids))) == [6, 4, 2]
            assert controller['descriptor']['invocation_ack_sha'] == result['ack_sha']
            assert result['sampled_combined_peak_rss_bytes'] <= 1024**3 and result['conservative_combined_peak_commit_bytes'] <= 2*1024**3
            assert result['broker_job_counted_once'] is True and result['host_hard_resource_enforcement_proved'] is result['whole_F_180_seconds_proved'] is False
            assert result['final_host_observation']['after_payload_encoding'] is result['final_host_observation']['after_mailbox_close'] is True
            assert result['final_host_observation']['protocol_progress_permitted'] is False
            returned = result['broker_return']['controller_return']['result']
            assert set(returned['output_inventory']) == set(graph['files']) and [r['stage'] for r in returned['input_bookends']] == ['G0', 'G2', 'G3']
            for name, item in returned['output_inventory'].items(): assert item['pin'] == graph['files'][name]['original_pin']
        elif case == 'constructor_wait':
            assert result['ack_sha'] and result['controller_binding_pin'] is None and result['constructor_probe']['phase'] == 'controller_constructor_native_wait'
            assert result['broker_process']['primary_stop_reason'] == 'phase_limit' and len(graph['files']) == 1
        elif case == 'prepare_wait': assert graph['files'] == {} and result['broker_process']['primary_stop_reason'] == 'phase_limit'
        elif case == 'publication_wait':
            assert result['result_kind'] == 'retained_unresolved_capability' and result['primary']['kind'] == 'abandoned'
            assert 'parent/parent_observation.json.pending' in graph['files'] and 'parent/parent_observation.json' not in graph['files']
        else:
            assert result['controller_binding_pin'] is None and result['broker_diagnostic']['phase'] == 'ack'
            assert result['broker_diagnostic']['primary']['message'] == 'host exact context ACK missing or differs'
    failure = read('final_failure_events.json'); raw = (OUT/failure['source_log']).read_bytes(); assert pin(raw) == failure['source_log_pin']
    for row in failure['resource']:
        line = raw.splitlines()[row['line']-1].partition(b'INVOCATION_RESOURCE_FAILURE ')[2]
        assert pin(line) == row['pin'] and json.loads(line) == row['value']
        value = row['value']; assert value['primary'] == value['process']['monitor_error'] == dict(type='ValueError', message='combined host and owned Job resource limit')
        assert value['process']['primary_stop_reason'] == 'monitor_or_channel_error' and value['process']['job_quiet_confirmed'] is True
    assert len(failure['resource']) == 2 and failure['unknown_quiet'][0]['value']['process']['job_quiet_confirmed'] is False
    reused = module('saved_invocation_reuse', OUT/'reuse_oracle.py').verify()
    original_reuse = read('historical_reuse.json')
    assert all(original_reuse[key] == value for key, value in reused.items()) and reused['counted_as_final_source_epoch_nodes'] is False
    for name, expected in read('raw_log_whitespace_exceptions.json')['pins'].items(): assert pin((ROOT/name).read_bytes()) == expected
    review = read('preseal_review.json'); assert review['remaining_code_findings'] == [] and review['official_verdict'] is review['receipt'] is review['seal'] is None
    for name, expected in review['source_pins'].items(): assert selected[name] == expected
    for name, expected in review['support_pins'].items(): assert pin((ROOT/name).read_bytes()) == expected
    assert read('disabled_entry_01.exit.json')['exit_code'] == 1 and b'F launch remains disabled' in (OUT/'disabled_entry_01.stderr.log').read_bytes()
    assert not (ROOT/'results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative/draft_01').exists()
    prior = module('saved_role_history', ROOT/'results/tables/staged_rts24_saved_fresh_roles_v1_non_authoritative/checks_01/saved_checks.py').verify()
    assert prior['frozen_tested_source_snapshot_verified'] is True and prior['P1_file_bytes_unchanged'] == 683
    return dict(authority='DRAFT_NONAUTHORITATIVE', preservation_verified=1315, P1_file_bytes_unchanged=683,
        navigation_bodies_preserved=3, final_source_epoch_unique_nodes=127, canonical_draft_matches_final_snapshot=canonical_match,
        frozen_source_snapshots_verified=True, historical_adapter17_and_role26_reuse_verified=True,
        raw_derivation=derivation, resource_original_primary_verified=True, original_context_reconstructed=False,
        saved_F_workflow_executed=False, new_native_solver_calls=0, F_launch_admitted=False,
        saved_P1_fresh_process_verified=False, saved_P1_parent_adoption_verified=False,
        scientific_evidence_adopted=False, resource_admission=False, formal_result=False)


if __name__ == '__main__': sys.stdout.buffer.write((json.dumps(verify(), sort_keys=True, indent=2)+'\n').encode())
