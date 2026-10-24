"""Stdlib saved ordinary-role integrity oracle; no scientific imports or run."""
from hashlib import sha256
import importlib.util
import json
import math
import os
from pathlib import Path
import stat
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
GATES = ('F_launch_admitted', 'saved_P1_fresh_process_verified', 'saved_P1_parent_adoption_verified',
    'native_authorized', 'scientific_evidence_adopted', 'resource_admission', 'formal_result', 'public_P2_execution_enabled')


def canonical(value): return json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('ascii')
def pin(raw): return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())
def read(name): return json.loads((OUT/name).read_bytes())


def slot(value, marker):
    raw = canonical(value); assert 0 < len(raw) <= 4052
    return struct.pack('<I', len(raw))+raw+b'\0'*(4052-len(raw))+sha256(raw).digest()+marker


def saved_P1_bytes():
    base = ROOT/'results/tables/staged_rts24_native_v1_non_authoritative'
    anchor = (base/'p1_execution_review_01/postcheck_03.stdout.json').read_bytes()
    assert sha256(anchor).hexdigest() == 'c6a25cd96c8a4a2cf293d41fe51bc7905db63fbc35253076f97e9239a4f22473'
    expected = json.loads(anchor)['p1_files']; assert len(expected) == 683 and sum(v['bytes'] for v in expected.values()) == 2950863
    p1 = base/'p1_01'; found = {}; stamps = {}; entries = 0
    def inspect(path, depth):
        nonlocal entries
        assert depth <= 12
        info = path.lstat(); assert not stat.S_ISLNK(info.st_mode) and not getattr(info, 'st_file_attributes', 0)&0x400
        stamps[path] = info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns
        if stat.S_ISDIR(info.st_mode):
            with os.scandir(path) as stream:
                for child in stream:
                    entries += 1; assert entries <= 16384
                    inspect(Path(child.path), depth+1)
        else:
            name = path.relative_to(p1).as_posix()
            assert name in expected and stat.S_ISREG(info.st_mode) and info.st_nlink == 1 and info.st_size == expected[name]['bytes']
            found[name] = pin(path.read_bytes()); assert found[name] == expected[name]
    inspect(p1, 0); assert found == expected
    for path, expected_stamp in stamps.items():
        info = path.lstat(); assert (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns) == expected_stamp
    return len(found)


def record_oracle(record, context_pin, projection):
    assert all(record[name] is False for name in GATES)
    assert record['owner_evidence'] == 'direct_owned_child' and record['job_quiet_confirmed'] is True
    assert record['artifact_contents_read'] is record['external_constructor_and_monitor_interrupt_bound_proved'] is record['terminal_publication_bound_proved'] is False
    witness = record['quiescence_witness']; members = witness['member_identities']
    identities = {(m['pid'], m['creation_filetime']) for m in members}
    assert witness['all_handles_signaled'] is witness['complete_inventory'] is True
    assert witness['active_processes'] == 0 and witness['final_pids'] == []
    assert witness['total_processes'] == witness['observed_unique_member_handles'] == len(members) == len(identities)
    header, startup, spec = record['stage_header'], record['startup'], record['descriptor']
    assert header['context_sha'] == startup['context_sha'] == context_pin['sha256']
    assert header['descriptor'] == spec and header['slots'] == 16 and header['slot_bytes'] == 4096
    assert startup['environment_sha'] == projection['environment_sha'] and startup['actual_os_commandline_independently_verified'] is False
    assert (header['owner_pid'], header['owner_creation_filetime']) == (startup['owner_pid'], startup['owner_creation_filetime'])
    assert (header['owner_pid'], header['owner_creation_filetime']) in identities
    assert spec['preset'] == 'role_graph' and spec['total_seconds'] == (7.5 if spec['role'] == 'parent' else 2.9)
    binding, previous, encoded = sha256(slot(header, b'GRIDHDR1')).hexdigest(), '0'*64, []
    for index, frame in enumerate(record['transcript_frames']):
        assert type(frame['sequence']) is int and frame['sequence'] == index
        assert frame['binding_sha'] == binding and frame['previous_sha'] == previous
        assert (frame['producer_pid'], frame['producer_creation_filetime']) == (header['owner_pid'], header['owner_creation_filetime'])
        assert type(frame['stamp']) is float and math.isfinite(frame['stamp']) and frame['stamp'] > 0
        if frame['phase'] == 'error':
            assert index == len(record['transcript_frames'])-1 and type(frame['error_code']) is str and 0 < len(frame['error_code']) <= 64
        else:
            assert frame['phase'] == (spec['phases']+['terminal'])[index] and frame['error_code'] is None
        raw = canonical(frame); encoded.append(slot(frame, b'GRIDFRM1')); previous = sha256(raw).hexdigest()
    assert sha256(b''.join(encoded)).hexdigest() == record['transcript_sha']
    assert record['quiesce_started_at'] <= record['quiesce_completed_at'] <= record['close_attempts_finished_at'] <= record['observation_finished_at'] <= record['total_deadline']
    assert record['remaining_total_seconds'] == record['total_deadline']-record['observation_finished_at']
    if record['termination_requested']: assert record['termination_requested_at'] <= record['quiesce_started_at']
    assert len(canonical(record)) <= 131072
    return identities


def verify():
    preserved = read('preservation_inventory.json'); assert len(preserved) == 1068
    for name, expected in preserved.items(): assert pin((ROOT/name).read_bytes()) == expected, name
    assert saved_P1_bytes() == 683
    for name, expected in read('navigation_before.json').items():
        raw = (ROOT/name).read_bytes()
        assert raw.partition(b'\n\n')[0].decode('utf-8') == expected['header']
        assert pin(raw[-expected['body']['bytes']:]) == expected['body']
    docs = read('document_checks.json')
    for name, expected in docs['document_pins'].items(): assert pin((ROOT/name).read_bytes()) == expected, name
    for name, expected in docs['navigation_checkpoint_bodies'].items(): assert pin((ROOT/name).read_bytes()[-expected['bytes']:]) == expected
    summary = read('ordinary_check_summary.json'); final = ('role_graph_03', 'role_units_04', 'stages_05', 'adapter_06')
    assert len(summary['source_pins']) == 49 and summary['pytest_actual_seconds'] < 240
    current = read('role_graph_03.snapshot.json')['sources']; canonical_match = True; nodes = []
    for name, expected in summary['source_pins'].items():
        if name in current:
            assert current[name]['pin'] == expected == pin((ROOT/current[name]['snapshot']).read_bytes())
            canonical_match &= pin((ROOT/name).read_bytes()) == expected
        else: assert pin((ROOT/name).read_bytes()) == expected, name
    plan = read('group_admission_03.json')
    for label, expected in summary['groups'].items():
        value = read(label+'.exit.json')
        assert value['source_pins_unchanged'] is True
        for suffix, expected_pin in expected['pins'].items(): assert pin((OUT/(label+'.'+suffix)).read_bytes()) == expected_pin
        for name, archived in read(value['snapshot_manifest'])['sources'].items():
            assert archived['pin'] == value['source_pins'][name] == pin((ROOT/archived['snapshot']).read_bytes())
        if label in final:
            assert value['exit_code'] == 0 and value['timed_out'] is False and value['wall_seconds'] < value['timeout_seconds']
            assert value['source_pins'] == summary['source_pins'] and value['nodes'] == plan['groups'][label]
            assert (OUT/(label+'.stderr.log')).read_bytes() == b''
            assert (str(len(value['nodes']))+' passed').encode() in (OUT/(label+'.stdout.log')).read_bytes()
            nodes.extend(value['nodes'])
    assert len(nodes) == len(set(nodes)) == 140
    assert read('roles_01.exit.json')['exit_code'] == 1 and b'2 failed, 31 passed' in (OUT/'roles_01.stdout.log').read_bytes()
    timed = read('role_graph_02.exit.json'); assert timed['timed_out'] is True and timed['exit_code'] is None and timed['timeout_seconds'] == 30
    for name, expected in summary['derived_support_pins'].items(): assert pin((ROOT/name).read_bytes()) == expected
    derivation = read('graph_derivation.json')
    for key in ('source_log', 'manifest', 'verifier'):
        assert pin((ROOT/derivation[key]['path']).read_bytes()) == derivation[key]['pin']
    spec = importlib.util.spec_from_file_location('ordinary_graph_derivation', OUT/'verify_graph_derivation.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    assert module.verify() == derivation['verified_result']
    graphs = read('ordinary_graph_snapshots.json'); process_records = 0
    for scenario, graph in graphs.items():
        result = json.loads((ROOT/graph['result']).read_bytes())
        assert all(result[name] is False for name in GATES)
        assert result['ordinary_graph_completed'] is (scenario == 'normal')
        projection = json.loads((ROOT/graph['files']['context.json']['archive']).read_bytes())
        assert projection['fixture'] == dict(left=2, right=3, expected=5) and 'environment' not in projection
        context_pin = graph['files']['context.json']['original_pin']
        def artifact(name): return (ROOT/graph['files'][name]['archive']).read_bytes()
        if 'worker/launcher.json' in graph['files']:
            outer = json.loads(artifact('worker/launcher.json')); outer_ids = record_oracle(outer, context_pin, projection); process_records += 1
            if 'worker/fresh/launcher.json' in graph['files']:
                inner = json.loads(artifact('worker/fresh/launcher.json')); inner_ids = record_oracle(inner, context_pin, projection); process_records += 1
                assert inner_ids <= outer_ids and inner['startup']['creator_pid'] == outer['startup']['owner_pid']
        if scenario == 'normal':
            assert len(graph['files']) == 16
            expected = dict(schema='staged_saved_F_ordinary_algebra_payload_v1', authority='DRAFT_NONAUTHORITATIVE',
                scope='ordinary_role_algebra_only', fixture_sha=sha256(canonical(projection['fixture'])).hexdigest(), operands=[2, 3], result=5)
            assert artifact('worker/parent_metrics.json') == artifact('worker/fresh/metrics.json') == canonical(expected)
            candidate = json.loads(artifact('worker/comparison_candidate.json')); observation = json.loads(artifact('parent/parent_observation.json'))
            assert candidate['parent_payload_pin'] == candidate['fresh_payload_pin'] == pin(canonical(expected))
            assert candidate['inner_process_sha'] == sha256(artifact('worker/fresh/launcher.json')).hexdigest()
            assert candidate['inner_observation_pin'] == pin(artifact('worker/fresh_parent/parent_observation.json'))
            assert candidate['G1']['stage'] == 'G1' and [m['stage'] for m in result['input_bookends']] == ['G0', 'G2', 'G3']
            assert [m['stage'] for m in observation['input_bookends_before_publication']] == ['G0', 'G2'] and 'G3' not in observation
            assert observation['outer_process_sha'] == sha256(artifact('worker/launcher.json')).hexdigest()
            core = {name: value for name, value in result['output_inventory'].items() if name != 'parent/parent_observation.json'}
            assert observation['core_output_inventory_sha'] == sha256(canonical(core)).hexdigest()
            for name, value in result['output_inventory'].items(): assert value['pin'] == graph['files'][name]['original_pin']
        elif scenario == 'g0_error': assert 'worker/launcher.json' not in graph['files']
        elif scenario == 'outer_launcher_corruption':
            assert outer['exit_code'] == 9 and result['error']['message'] == 'saved outer process differs from live owner'
            assert result['outer_process_sha'] != sha256(artifact('worker/launcher.json')).hexdigest()
        elif scenario == 'late_payload_drift':
            assert json.loads(artifact('worker/fresh/metrics.json'))['result'] == 999 and result['observation_pin'] == pin(artifact('parent/parent_observation.json'))
            assert result['error']['message'] == 'validated role core changed after final publication'
        elif scenario == 'g3_error': assert result['observation_pin'] == pin(artifact('parent/parent_observation.json'))
    assert process_records == 16
    reused = read('unaffected_scientific_adapter.json')
    assert pin((ROOT/reused['frozen_snapshot']).read_bytes()) == reused['current_pin'] == summary['source_pins'][reused['source']]
    review = read('preseal_review.json')
    assert review['remaining_findings'] == [] and review['official_verdict'] is review['receipt'] is review['seal'] is None
    for name, expected in review['reviewer_source_pins'].items(): assert expected == summary['source_pins'][name]
    for name, expected in review['support_pins'].items(): assert pin((ROOT/name).read_bytes()) == expected
    for name, expected in read('raw_log_whitespace_exceptions.json')['pins'].items(): assert pin((ROOT/name).read_bytes()) == expected
    assert read('disabled_entry_01.exit.json')['exit_code'] == 1 and b'F launch remains disabled' in (OUT/'disabled_entry_01.stderr.log').read_bytes()
    assert not (ROOT/'results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative/draft_01').exists()
    prior = ROOT/'results/tables/staged_rts24_saved_fresh_stage_owner_v1_non_authoritative/checks_01/saved_checks.py'
    run = subprocess.run([sys.executable, '-B', str(prior)], cwd=ROOT, capture_output=True, timeout=20)
    assert run.returncode == 0 and run.stderr == b'' and json.loads(run.stdout)['frozen_tested_source_snapshot_verified'] is True
    return dict(authority='DRAFT_NONAUTHORITATIVE', preservation_verified=1068, P1_file_bytes_unchanged=683,
        navigation_bodies_preserved=3, current_unique_nodes_passed=140, frozen_tested_source_snapshot_verified=True,
        canonical_draft_matches_tested_snapshot=canonical_match, ordinary_graph_cases=9, archived_process_records=16,
        raw_graph_derivation_verified=True, original_context_reconstructed=False, source_scope='selected_only_49',
        actual_saved_role_execution=False, new_F_workflow_executed=False, new_native_calls=0,
        F_launch_admitted=False, saved_P1_fresh_process_verified=False, saved_P1_parent_adoption_verified=False,
        scientific_evidence_adopted=False, resource_admission=False, formal_result=False)


if __name__ == '__main__': print(json.dumps(verify(), sort_keys=True, indent=2))
