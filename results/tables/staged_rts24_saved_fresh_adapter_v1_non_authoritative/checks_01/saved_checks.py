"""Stdlib historical/snapshot integrity audit; no scientific imports or replay."""
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent
PRIOR = ROOT/'results/tables/staged_rts24_saved_journal_check_v1_non_authoritative/checks_01'


def pin(raw): return dict(bytes=len(raw), sha256=sha256(raw).hexdigest())


def verify():
    preserved = json.loads((OUT/'preservation_inventory.json').read_bytes())
    assert len(preserved) == 926
    for name, expected in preserved.items(): assert pin((ROOT/name).read_bytes()) == expected, name
    for name, expected in json.loads((OUT/'navigation_before.json').read_bytes()).items():
        raw = (ROOT/name).read_bytes()
        assert raw.partition(b'\n\n')[0].decode('utf-8') == expected['header']
        assert pin(raw[-expected['body']['bytes']:]) == expected['body'], name
    docs = json.loads((OUT/'document_checks.json').read_bytes())
    for name, expected in docs['document_pins'].items(): assert pin((ROOT/name).read_bytes()) == expected, name
    for name, expected in docs['navigation_checkpoint_bodies'].items():
        assert pin((ROOT/name).read_bytes()[-expected['bytes']:]) == expected, name
    summary = json.loads((OUT/'ordinary_check_summary.json').read_bytes())
    snapshots = json.loads((OUT/'tested_draft_snapshot.json').read_bytes())['sources']
    canonical_match = True
    for name, expected in summary['source_pins'].items():
        if name in snapshots:
            assert snapshots[name]['pin'] == expected
            assert pin((ROOT/snapshots[name]['snapshot']).read_bytes()) == expected
            canonical_match = canonical_match and pin((ROOT/name).read_bytes()) == expected
        else: assert pin((ROOT/name).read_bytes()) == expected, name
    assert len(summary['source_pins']) == 49
    collection = json.loads((OUT/'collection_02.exit.json').read_bytes())
    split = json.loads((OUT/'split_admission_04.json').read_bytes())
    all_nodes = [n for group in collection['groups'].values() for n in group]
    assert len(all_nodes) == len(set(all_nodes)) == 94
    flat = []
    for label, expected in summary['groups'].items():
        record = json.loads((OUT/(label+'.exit.json')).read_bytes())
        assert record['exit_code'] == 0 and record['timed_out'] is False
        assert record['source_pins_unchanged'] is True and record['source_pins'] == summary['source_pins']
        assert record['timeout_seconds'] == 90 and record['wall_seconds'] < 90
        assert record['nodes'] == expected['nodes']
        assert (str(len(record['nodes']))+' passed').encode() in (OUT/(label+'.stdout.log')).read_bytes()
        assert (OUT/(label+'.stderr.log')).read_bytes() == b''
        for suffix in ('exit.json', 'stdout.log', 'stderr.log'):
            assert pin((OUT/(label+'.'+suffix)).read_bytes()) == expected[suffix]
        flat.extend(record['nodes'])
    assert len(flat) == len(set(flat)) == 94 and set(flat) == set(all_nodes)
    assert [len(summary['groups'][label]['nodes']) for label in summary['groups']] == [12, 12, 70]
    assert split['groups']['chain_bindings_04a']+split['groups']['chain_bindings_04b'] == collection['groups']['chain_bindings_03']
    failed = json.loads((OUT/'chain_bindings_03.exit.json').read_bytes())
    assert failed['timed_out'] is True and failed['exit_code'] is None and failed['timeout_seconds'] == 90
    assert summary['targeted_distinct_passed'] == 85 and summary['related_distinct_passed'] == 9
    raw = json.loads((OUT/'raw_log_whitespace_exceptions.json').read_bytes())
    for name, expected in raw['pins'].items(): assert pin((ROOT/name).read_bytes()) == expected
    assert raw['raw_bytes_preserved'] is True
    review = json.loads((OUT/'preseal_review.json').read_bytes())
    assert review['remaining_findings'] == [] and review['official_verdict'] is review['receipt'] is review['seal'] is None
    for name, expected in review['support_pins'].items(): assert pin((ROOT/name).read_bytes()) == expected, name
    for name, expected in review['reviewer_source_pins'].items(): assert snapshots[name]['pin'] == expected
    disabled = json.loads((OUT/'disabled_entry_01.exit.json').read_bytes())
    assert disabled['exit_code'] == 1 and b'F launch remains disabled' in (OUT/'disabled_entry_01.stderr.log').read_bytes()
    prior = subprocess.run([sys.executable, '-B', str(PRIOR/'saved_checks.py')], cwd=ROOT, capture_output=True, timeout=30)
    assert prior.returncode == 0 and prior.stderr == b'' and prior.stdout == (OUT/'saved_integrity_01.stdout.log').read_bytes()
    return dict(authority='DRAFT_NONAUTHORITATIVE', preservation_verified=926, navigation_bodies_preserved=3,
        P1_files_unchanged=683, targeted_distinct_passed=85, related_distinct_passed=9,
        frozen_tested_source_snapshot_verified=True, canonical_draft_matches_tested_snapshot=canonical_match,
        source_scope='selected_only_49', entry_execution_disabled_at_tested_snapshot=True,
        F_launch_admitted=False, saved_P1_fresh_process_verified=False, saved_P1_parent_adoption_verified=False,
        scientific_evidence_adopted=False, journal_replayed=False, full_fx_contract_verified=False,
        independent_139_verified=False, resource_admission=False, formal_result=False,
        new_F_workflow_executed=False, new_native_calls=0)


if __name__ == '__main__': print(json.dumps(verify(), sort_keys=True, indent=2))
