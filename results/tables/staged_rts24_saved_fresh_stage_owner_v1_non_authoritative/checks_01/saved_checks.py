"""Stdlib saved component integrity; no pytest/scientific imports or F run."""
from hashlib import sha256
import json
from pathlib import Path
import struct
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent


def pin(raw): return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def read(name): return json.loads((OUT/name).read_bytes())


def slot(value, marker):
    raw = json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(',', ':'), allow_nan=False).encode('ascii')
    assert 0 < len(raw) <= 4052
    return struct.pack('<I', len(raw))+raw+b'\0'*(4052-len(raw))+sha256(raw).digest()+marker


def verify():
    preserved = read('preservation_inventory.json'); assert len(preserved) == 980
    for name, expected in preserved.items(): assert pin((ROOT/name).read_bytes()) == expected, name
    for name, expected in read('navigation_before.json').items():
        raw = (ROOT/name).read_bytes()
        assert raw.partition(b'\n\n')[0].decode('utf-8') == expected['header']
        assert pin(raw[-expected['body']['bytes']:]) == expected['body'], name
    docs = read('document_checks.json')
    for name, expected in docs['document_pins'].items(): assert pin((ROOT/name).read_bytes()) == expected, name
    for name, expected in docs['navigation_checkpoint_bodies'].items():
        assert pin((ROOT/name).read_bytes()[-expected['bytes']:]) == expected, name
    summary = read('ordinary_check_summary.json'); assert len(summary['source_pins']) == 49
    snapshots = read('affected_04.snapshot.json')['sources']
    canonical_match = True
    for name, expected in summary['source_pins'].items():
        if name in snapshots:
            assert expected == snapshots[name]['pin'] == pin((ROOT/snapshots[name]['snapshot']).read_bytes())
            canonical_match &= pin((ROOT/name).read_bytes()) == expected
        else: assert pin((ROOT/name).read_bytes()) == expected, name
    for label, expected in summary['groups'].items():
        value = read(label+'.exit.json')
        assert value['exit_code'] == expected['exit_code'] and value['timed_out'] is False
        assert value['source_pins_unchanged'] is True and value['wall_seconds'] < value['timeout_seconds']
        assert len(value['nodes']) == expected['nodes']
        assert (OUT/(label+'.stderr.log')).read_bytes() == b''
        for suffix, expected_pin in expected['pins'].items():
            assert pin((OUT/(label+'.'+suffix)).read_bytes()) == expected_pin
        frozen = read(value['snapshot_manifest'])['sources']
        for name, archived in frozen.items():
            assert archived['pin'] == value['source_pins'][name] == pin((ROOT/archived['snapshot']).read_bytes())
    assert summary['groups']['stage_01']['exit_code'] == summary['groups']['stage_guard_02']['exit_code'] == 1
    assert b'6 failed, 43 passed' in (OUT/'stage_01.stdout.log').read_bytes()
    assert b'1 failed, 67 passed' in (OUT/'stage_guard_02.stdout.log').read_bytes()
    assert b'105 passed' in (OUT/'final_03.stdout.log').read_bytes()
    assert b'87 passed' in (OUT/'affected_04.stdout.log').read_bytes()
    assert read('affected_04.exit.json')['timeout_seconds'] == 30
    assert read('collection_01.exit.json')['exit_code'] == 1
    assert b"No module named 'pygments'" in (OUT/'collection_01.stderr.log').read_bytes()
    unaffected = read('unaffected_domain_equivalence.json')
    prior_snapshots = read('final_03.snapshot.json')['sources']
    for name, domain in unaffected['domains'].items():
        old = (ROOT/prior_snapshots[name]['snapshot']).read_bytes()
        new = (ROOT/snapshots[name]['snapshot']).read_bytes()
        if domain['scope'] != 'whole_file':
            marker = domain['scope'].removeprefix('prefix_before_').encode('ascii')
            old, new = old.partition(marker)[0], new.partition(marker)[0]
        assert old == new and pin(new) == domain['pin']
    probes = read('ordinary_probe_observations.json')['records']; assert len(probes) == 11
    from_raw = [json.loads(line.partition(b'STAGE_PROBE ')[2]) for line in (OUT/'affected_04.stdout.log').read_bytes().splitlines() if b'STAGE_PROBE ' in line]
    assert probes == from_raw
    success_ids = set()
    for record in probes:
        assert record['owner_evidence'] == 'direct_owned_child' and record['job_quiet_confirmed'] is True
        assert all(record[k] is False for k in ('F_launch_admitted', 'native_authorized', 'resource_admission',
            'formal_result', 'scientific_evidence_adopted', 'public_P2_execution_enabled',
            'saved_P1_fresh_process_verified', 'saved_P1_parent_adoption_verified'))
        witness = record['quiescence_witness']; identities = witness['member_identities']
        assert witness['complete_inventory'] is witness['all_handles_signaled'] is True
        assert witness['active_processes'] == 0 and witness['final_pids'] == []
        assert witness['total_processes'] == witness['observed_unique_member_handles'] == len(identities)
        assert len({(p['pid'], p['creation_filetime']) for p in identities}) == len(identities)
        header = record['stage_header']; header_bytes = slot(header, b'GRIDHDR1')
        startup = record['startup']
        assert header['context_sha'] == startup['context_sha'] and header['descriptor'] == record['descriptor']
        assert (header['owner_pid'], header['owner_creation_filetime']) == (startup['owner_pid'], startup['owner_creation_filetime'])
        assert (header['owner_pid'], header['owner_creation_filetime']) in {(p['pid'], p['creation_filetime']) for p in identities}
        assert startup['actual_os_commandline_independently_verified'] is False
        frames = record['transcript_frames']; prior = '0'*64; slots = []
        expected_phases = record['descriptor']['phases']+['terminal']
        for index, frame in enumerate(frames):
            raw = json.dumps(frame, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')
            assert type(frame['sequence']) is int and frame['sequence'] == index and frame['previous_sha'] == prior
            assert frame['binding_sha'] == sha256(header_bytes).hexdigest()
            assert (frame['producer_pid'], frame['producer_creation_filetime']) == (header['owner_pid'], header['owner_creation_filetime'])
            assert frame['phase'] == expected_phases[index] or (frame['phase'] == 'error' and index == len(frames)-1)
            slots.append(slot(frame, b'GRIDFRM1')); prior = sha256(raw).hexdigest()
        assert sha256(b''.join(slots)).hexdigest() == record['transcript_sha']
        assert record['stage_transcript_complete'] is ([f['phase'] for f in frames] == expected_phases)
        assert record['quiesce_started_at'] <= record['quiesce_completed_at'] <= record['close_attempts_finished_at']
        if record['termination_requested']: assert record['termination_requested_at'] <= record['quiesce_started_at']
        if record['stage_process_observed_successfully']:
            success_ids.add(startup['probe_id']); assert record['exit_code'] == 0 and record['primary_stop_reason'] is None
        assert len(json.dumps(record, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')) <= 131072
    assert success_ids == {'normal', 'nested_quiet'}
    review = read('preseal_review.json')
    assert review['remaining_findings'] == [] and review['official_verdict'] is review['receipt'] is review['seal'] is None
    for name, expected in review['reviewer_source_pins'].items(): assert expected == summary['source_pins'][name]
    for name, expected in review['support_pins'].items(): assert pin((ROOT/name).read_bytes()) == expected, name
    for name, expected in read('raw_log_whitespace_exceptions.json')['pins'].items(): assert pin((ROOT/name).read_bytes()) == expected
    assert not (ROOT/'results/tables/staged_rts24_saved_fresh_adoption_v1_non_authoritative/draft_01').exists()
    prior = ROOT/'results/tables/staged_rts24_saved_fresh_adapter_v1_non_authoritative/checks_01/saved_checks.py'
    run = subprocess.run([sys.executable, '-B', str(prior)], cwd=ROOT, capture_output=True, timeout=15)
    assert run.returncode == 0 and run.stderr == b''
    previous = json.loads(run.stdout); assert previous['frozen_tested_source_snapshot_verified'] is True
    assert previous['canonical_draft_matches_tested_snapshot'] is False
    return dict(authority='DRAFT_NONAUTHORITATIVE', preservation_verified=980, P1_file_bytes_unchanged=683,
        navigation_bodies_preserved=3, frozen_tested_source_snapshot_verified=True,
        canonical_draft_matches_tested_snapshot=canonical_match, current_stage_distinct_passed=68,
        current_related_guard_distinct_passed=19, unaffected_adapter_snapshot_nodes_reused=28,
        source_scope='selected_only_49', real_ordinary_probe_records=11,
        reconstructable_transcripts_verified=True, F_launch_admitted=False,
        new_F_workflow_executed=False, saved_P1_fresh_process_verified=False,
        saved_P1_parent_adoption_verified=False, scientific_evidence_adopted=False,
        resource_admission=False, formal_result=False, new_native_calls=0)


if __name__ == '__main__': print(json.dumps(verify(), sort_keys=True, indent=2))
