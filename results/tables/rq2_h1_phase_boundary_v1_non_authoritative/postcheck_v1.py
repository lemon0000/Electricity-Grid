"""Read-only terminal, exact-fact, retention and binding verification."""
import ast
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[2]
sys.path.insert(0, str(REPO))
from experiments.h1_phase_boundary_budget_development_v1 import verify_map


def load(name):
    return json.loads((HERE / name).read_bytes())


def pin(path):
    return sha256(path.read_bytes()).hexdigest()


def q(value):
    return Fraction(int(value['numerator']), int(value['denominator']))


def main():
    terminal = load('unit_04/terminal.json')
    request = load('unit_04/request.json')
    assert terminal['exit_code'] == 0 and terminal['reason'] is None
    assert terminal['junit'] == dict(tests=15, failures=0, errors=0, skipped=0, accepted=True)
    assert terminal['outer_seconds'] < 180
    assert terminal['peak_sampled_tree_rss_bytes'] < 1024 ** 3
    assert terminal['peak_logical_bytes'] < 128 * 1024 ** 2
    assert not terminal['observed_processes_remaining'] and not terminal['changed_sources']
    assert terminal['new_normal_jobs'] == terminal['real_native_calls'] == 0
    unit_pins = verify_map(request['sources_sha256'])
    assert unit_pins['count'] == 1305 and not unit_pins['mismatches']
    cases = ET.parse(HERE / 'unit_04/junit.xml').getroot().findall('.//testcase')
    assert len(cases) == 15 and not any(c.find(x) is not None for c in cases for x in ('failure', 'error', 'skipped'))
    facts = {}
    for source, row in terminal['facts'].items():
        original, retained = Path(source), Path(row['retained_copy'])
        assert pin(original) == pin(retained) == row['sha256']
        fact = json.loads(retained.read_bytes())
        assert fact['phase_events_written'] == fact['real_native_calls'] == 0
        assert fact['source_prefix_authenticated'] is fact['paired_owner_authenticated'] is fact['formal_result'] is False
        facts[retained.stem] = fact
    assert set(facts) == {'no_requests_167', 'no_requests_168', 'pending_168', 'pending_169',
                          'pending_191', 'pending_192', 'recover_primary_170', 'late_recovery_170', 'exact_due_192'}
    def business(name):
        return facts[name]['assessment']['lanes'][0]['business']
    assert business('no_requests_167')['next_phase'] == 'enrollment'
    assert q(business('no_requests_167')['retained_total_debt']) == 0
    assert not facts['no_requests_168']['assessment']['needs_next_hour']
    for name in ('pending_168', 'pending_169', 'pending_191'):
        fact = business(name)
        assert fact['pending_primary_births'] == [168] and fact['last_primary_due'] == 192
        assert fact['next_phase'] == 'followup' and fact['primary_recovery_status'] == 'U'
    assert business('pending_169')['followup_cohorts'][0]['due_hour'] == 193
    due_failure = business('pending_192')
    assert due_failure['primary_recovery_status'] == 'F'
    assert q(due_failure['primary_cohorts'][0]['missed_at_deadline']) == Fraction(17, 200)
    assert q(due_failure['retained_total_debt']) == Fraction(17, 100)
    early = business('recover_primary_170')
    assert q(early['primary_cohorts'][0]['remaining']) == 0
    assert q(early['retained_total_debt']) == Fraction(17, 200)
    assert early['primary_recovery_status'] == 'S' and not early['needs_next_hour']
    assert business('late_recovery_170')['primary_recovery_status'] == 'F'
    exact = facts['exact_due_192']
    assert exact['original_validate_calls'] == 194 and exact['validate_history_length_sum'] == 18720
    assert q(exact['final_recovery']) == Fraction(1, 10) and q(exact['deadline_snapshot']) == q(exact['debt']) == 0
    assert business('exact_due_192')['primary_cohorts'][0]['status'] == 'success_by_due'
    budget = load('budget_audit_v1.json')
    assert not budget['overall_performance_review_complete'] and not budget['long_connected_launch_admitted']
    assert not verify_map(budget['bindings'])['mismatches']
    prior = HERE.parent / 'rq2_h1_cross_hour_outage_v1_non_authoritative'
    old_post = json.loads((prior / 'connected_03_postcheck.json').read_bytes())
    for field, count in (('inherited_source_sha256', 1279), ('diagnostic_case_files_sha256', 465)):
        checked = verify_map(old_post[field])
        assert checked['count'] == count and not checked['mismatches']
    old_request = json.loads((prior / 'connected_03/request.json').read_bytes())
    case = Path(old_request['base']) / 'test_three_hour_connected_outa0'
    old_result = json.loads((case / 'outage_chain_result.json').read_bytes())
    saved = verify_map(old_result['saved_files_sha256'])
    assert saved['count'] == 444 and not saved['mismatches']
    updates = load('canonical_doc_updates.json')['updates']
    before_map = {}
    for row in updates:
        before, after = Path(row['before_snapshot']).read_bytes(), Path(row['path']).read_bytes()
        assert sha256(before).hexdigest() == row['before_sha256']
        assert sha256(after).hexdigest() == row['after_sha256']
        offset, length = row['insertion_offset'], row['insertion_length']
        assert after[:offset] + after[offset + length:] == before
        before_map[row['path']] = row['before_snapshot']
    old_final = json.loads((prior / 'final_verification_03.json').read_bytes())
    for name, expected in old_final['bindings'].items():
        path = Path(before_map.get(name, name))
        assert pin(path) == expected
    syntax = []
    for path in [REPO / 'experiments/h1_phase_boundary_budget_development_v1.py',
                 *sorted((REPO / 'tests').glob('test_h1_phase_boundary_*_development_v1.py')),
                 *sorted(HERE.glob('*.py'))]:
        ast.parse(path.read_text(encoding='utf-8'), filename=str(path))
        syntax.append(str(path))
    links = []
    for path in HERE.glob('*.md'):
        for target in re.findall(r'\[[^\]]+\]\(([^)]+)\)', path.read_text(encoding='utf-8')):
            if not target.startswith(('http:', 'https:', '#')):
                linked = (path.parent / target.split('#')[0]).resolve()
                assert linked.exists(), (path, target)
                links.append(dict(source=str(path), target=str(linked)))
    assert not (REPO / 'synthetic_metadata_only_non_authoritative').exists()
    bound = [p for p in HERE.rglob('*') if p.is_file()]
    bound += [Path(p) for p in syntax] + [Path(r['path']) for r in updates]
    bound += [prior / 'connected_03_postcheck.json', case / 'outage_chain_result.json']
    report = dict(status='DRAFT_NONAUTHORITATIVE',
        scope='detached_real_business_history_phase_body_and_budget_audit',
        unit_exit_code=0, passed=15, pytest_seconds=84.34,
        outer_seconds=terminal['outer_seconds'], exact_facts_verified=9,
        original_due_validate_calls=194, original_due_validate_history_length_sum=18720,
        current_unit_source_pins=unit_pins, inherited_source_pins=1279,
        reused_owned_files=444, reused_case_files=465,
        peak_sampled_tree_rss_bytes=terminal['peak_sampled_tree_rss_bytes'],
        peak_logical_bytes=terminal['peak_logical_bytes'],
        canonical_old_bytes_recoverable=True, canonical_old_report_bindings_via_snapshot=True,
        local_links_verified=len(links), syntax_parsed=syntax,
        failed_unit_attempts_preserved=['unit_01', 'unit_02', 'unit_03'],
        overall_performance_review_complete=False, long_connected_launch_admitted=False,
        full_192_hour_execution_verified=False, connected_phase_terminal_verified=False,
        typed_followup_right_censor_terminal_verified=False,
        native_execution_authorized=False, resource_admission=False,
        formal_execution_ready=False, new_normal_jobs=0, real_native_calls=0, formal_result=False,
        bindings={str(p): pin(p) for p in sorted(set(bound))})
    destination = HERE / sys.argv[1]
    with destination.open('x', encoding='utf-8') as stream:
        json.dump(report, stream, indent=2)
        stream.write('\n')
    print(json.dumps(dict(output=str(destination), passed=15, facts=9,
        inherited_source_pins=1279, reused_owned_files=444, local_links_verified=len(links),
        long_connected_launch_admitted=False)))


if __name__ == '__main__':
    main()
