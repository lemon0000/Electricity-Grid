import json
import subprocess
import sys
from dataclasses import replace
from fractions import Fraction as Q

import pytest

from experiments import export_rq2_continuous_capacity_diagnostics_v1 as delivery
from test_rq2_continuous_capacity_policy_v1 import init, current, advance


def rational(value):
    return Q(int(value['numerator']), int(value['denominator']))


@pytest.fixture(scope='module')
def payload():
    return delivery.build_payload()


def records(payload):
    return [json.loads(line) for line in payload['records.jsonl'].splitlines()]


def summaries(payload):
    return {(r['case_id'], r['arm_id']): r for r in json.loads(payload['summary.json'])}


def test_four_arms_original_projection_and_independent_conservation(payload):
    assert len(summaries(payload)) == 36
    policies = json.loads(payload['policies.json'])
    for row in records(payload):
        assert row['policy_id'] in policies
        before = row['before_execution']['tracks']['shared']['ledger']
        after = row['committed_execution']['tracks']['shared']['ledger']
        if not row['committed']:
            assert before == after
            continue
        a = row['declared_action']
        g, c, r, p = (rational(a[k]) for k in ('grid_served', 'cfe_served', 'recovery', 'actual_service_power'))
        original = row['original_current']['observation']['hour']
        projected = row['executed_request_projection']['hour']
        assert (rational(projected['grid_request']), rational(projected['cfe_request'])) == (g, c)
        assert p == Q(str(original['workload_occupancy']))-g-c+r
        old = sum((rational(v['remaining']) for v in before['cohorts']), Q(0))
        new = sum((rational(v['remaining']) for v in after['cohorts']), Q(0))
        assert new == old+g+c-Q('.8')*r
    partial = next(r for r in records(payload) if r['case_id'] == 'capacity_cfe_partial'
                   and r['arm_id'] == delivery.prefix.JOINT and r['submission_index'] == 1)
    assert partial['original_current']['observation']['hour']['cfe_request'] == .25
    assert rational(partial['executed_request_projection']['hour']['cfe_request']) == 0


def test_candidate_shortfall_and_invalid_source_are_separate(payload):
    rows = summaries(payload)
    stopped = rows['capacity_grid_stop', delivery.prefix.JOINT]
    assert (stopped['submitted_input_count'], stopped['committed_input_count'], stopped['unsubmitted_input_count']) == (1, 0, 3)
    assert rational(stopped['evaluated_candidate_grid_shortfall_energy']) == Q('.125')
    assert rational(stopped['committed_grid_shortfall_energy']) == 0
    assert stopped['remaining_debt'] == [['shared', {'numerator': '0', 'denominator': '1'}]]
    gap = rows['capacity_source_gap', delivery.prefix.JOINT]
    assert (gap['stop_submission_index'], gap['stop_raw_source_hour'], gap['last_committed_source_hour']) == (2, 99, 1)
    assert gap['unassessed_submitted_count'] == 1 and gap['evaluated_candidate_count'] == 1
    assert gap['uncommitted_hour_and_suffix_actual_outcome'] is None


def test_small_shortfalls_accumulate_without_hourly_failure():
    cursor = init(curtailment_ramp_per_hour=1., response_time_hours=1.)
    for t in (1, 2, 3):
        cursor = advance(cursor, current(t, g=.1250005, available=.125))
        assert cursor.records[-1].committed
        assert cursor.records[-1].response.grid_service_failure is False
    summary = delivery.summarize(cursor, 3)
    assert summary['committed_grid_shortfall_energy'] == Q('0.0000015')
    assert summary['evaluated_candidate_grid_failure_count'] == 0
    assert summary['risk_probability'] is None


def test_empty_prefix_and_inapplicable_services():
    for arm in delivery.prefix.ARMS:
        s = delivery.summarize(init(arm), 5)
        assert s['unsubmitted_input_count'] == 5 and s['committed_input_count'] == 0
        assert (s['committed_grid_shortfall_energy'] is None) == (arm == delivery.prefix.CFE)
        assert (s['committed_cfe_shortfall_energy'] is None) == (arm == delivery.prefix.NETWORK)
    with pytest.raises(ValueError):
        delivery.summarize(advance(init(), current(1)), 0)


def test_censoring_unknown_miss_and_evidence_remain_distinct(payload):
    rows = summaries(payload)
    arm = delivery.prefix.JOINT
    assert {v[2] for v in rows['censored_prefix', arm]['cohort_statuses']} == {'right_censored_before_deadline'}
    assert {v[2] for v in rows['unknown_deadline', arm]['cohort_statuses']} == {'deadline_unidentified'}
    assert {v[2] for v in rows['late_recovery', arm]['cohort_statuses']} == {'deadline_missed'}
    assert all(r['full_service_outcome'] is None and r['formal_result'] is False for r in rows.values())
    evidence = json.loads(payload['evidence.json'])
    assert evidence['real_observations_used'] is False
    assert evidence['training_capacity_certificate'] is None


def test_fraction_microcomponent_projection_roundtrip():
    config, inputs = delivery.load_inputs()
    config['scenarios']['cases'] = [{'id': 'micro'}]
    config['policy']['fixture'].update(minimum_event_power=.000003, curtailment_ramp_per_hour=1., response_time_hours=1.)
    row = inputs[0]
    row['case_id'] = 'micro'
    row['available_flexibility'] = .000003
    row['observation']['hour'].update(grid_request=.000002, cfe_request=.000002)
    row['observation']['due_hour'] = 5
    result, _, _ = delivery.replay(config, [row])
    joint = next(r for r in result if r['arm_id'] == delivery.prefix.JOINT)
    encoded = json.loads(delivery.prefix.encoded(joint))
    assert rational(encoded['executed_request_projection']['hour']['cfe_request']) == Q('0.000001')
    assert rational(encoded['declared_action']['cfe_served']) == Q('0.000001')


def put_package(path, payload):
    path.mkdir()
    for name, data in payload.items():
        (path/name).write_bytes(data)
    (path/'diagnostic_manifest.json').write_bytes(delivery.prefix.encoded(delivery.manifest(payload)))


@pytest.mark.parametrize('include_tests', [False, True])
def test_fresh_import_repository_dependency_closure(include_tests):
    script = '''
import json, pathlib, sys
root = pathlib.Path.cwd().resolve()
read_paths = set()
original_read_text = pathlib.Path.read_text
def tracked_read_text(path, *args, **kwargs):
    resolved = path.resolve()
    if resolved.is_relative_to(root):
        read_paths.add(resolved.relative_to(root).as_posix())
    return original_read_text(path, *args, **kwargs)
pathlib.Path.read_text = tracked_read_text
from experiments import export_rq2_continuous_capacity_diagnostics_v1 as delivery
if sys.argv[1] == 'tests':
    sys.path.insert(0, str(root/'tests'))
    import test_rq2_continuous_capacity_diagnostics_v1
delivery.load_inputs()
loaded = set()
for module in tuple(sys.modules.values()):
    name = getattr(module, '__file__', None)
    if name:
        path = pathlib.Path(name).resolve()
        if path.suffix == '.py' and path.is_relative_to(root):
            loaded.add(path.relative_to(root).as_posix())
print(json.dumps(sorted(loaded | read_paths)))
'''
    result = subprocess.run([sys.executable, '-B', '-c', script, 'tests' if include_tests else 'runtime'], cwd=delivery.ROOT,
                            capture_output=True, text=True, check=True)
    loaded = set(json.loads(result.stdout))
    assert {'experiments/__init__.py', 'src/__init__.py'} <= loaded
    assert loaded <= set(delivery.DEPENDENCIES)


def test_create_verify_and_preserve_existing(tmp_path):
    path = tmp_path/'capacity_non_authoritative'
    result = delivery.write_package(path)
    assert result['case_arm_count'] == 36 and result['replay_matches']
    before = {p.name: p.read_bytes() for p in path.iterdir()}
    with pytest.raises(FileExistsError):
        delivery.write_package(path)
    assert before == {p.name: p.read_bytes() for p in path.iterdir()}


@pytest.mark.parametrize('field', ['original_current', 'executed_request_projection', 'committed_execution'])
def test_rehashed_semantic_tampering_fails_replay(tmp_path, payload, field):
    altered = dict(payload)
    rows = records(payload)
    rows[0][field] = None
    altered['records.jsonl'] = b''.join(map(delivery.prefix.encoded, rows))
    path = tmp_path/'capacity_non_authoritative'
    put_package(path, altered)
    with pytest.raises(ValueError, match='replay mismatch'):
        delivery.verify_package(path)


@pytest.mark.parametrize('fault', ['extra', 'dependency', 'truncated'])
def test_partial_or_mismatched_package_rejected(tmp_path, payload, fault):
    path = tmp_path/'capacity_non_authoritative'
    put_package(path, payload)
    if fault == 'extra':
        (path/'extra').write_text('x')
    elif fault == 'truncated':
        (path/'records.jsonl').write_bytes(b'')
    else:
        inventory = json.loads((path/'diagnostic_manifest.json').read_bytes())
        inventory['dependencies'][delivery.CONFIG] = '0'*64
        (path/'diagnostic_manifest.json').write_bytes(delivery.prefix.encoded(inventory))
    with pytest.raises(ValueError, match='mismatch'):
        delivery.verify_package(path)
