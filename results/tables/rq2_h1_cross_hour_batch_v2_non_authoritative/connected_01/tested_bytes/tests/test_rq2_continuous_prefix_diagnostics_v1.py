import json
from fractions import Fraction

import pytest

from experiments import export_rq2_continuous_prefix_diagnostics_v1 as delivery


@pytest.fixture(scope='module')
def payload():
    return delivery.build_payload()


def unpack(payload, name):
    return json.loads(payload[name])


def debt(snapshot):
    cohorts = snapshot['tracks']['shared']['ledger']['cohorts']
    return sum((Fraction(int(c['remaining']['numerator']), int(c['remaining']['denominator']))
                for c in cohorts), Fraction(0))


def test_analytic_scenarios_and_honest_exposure(payload):
    summary = {(r['case_id'], r['arm_id']): r for r in unpack(payload, 'summary.json')}
    assert len(summary) == 24
    normal = summary['normal_recovery', delivery.JOINT]
    assert normal['accepted_hours'] == 48 and normal['deadline_missed_count'] == 0
    poor = summary['insufficient_recovery', delivery.JOINT]
    assert poor['accepted_hours'] == 48 and poor['deadline_missed_count'] == 3
    assert poor['remaining_debt'] == [['shared', {'numerator': '3', 'denominator': '8'}]]
    late = summary['late_recovery', delivery.JOINT]
    assert late['deadline_missed_count'] == 3
    assert late['remaining_debt'] == [['shared', {'numerator': '0', 'denominator': '1'}]]
    unknown = summary['unknown_deadline', delivery.JOINT]
    assert unknown['deadline_unidentified_count'] == 3 and unknown['deadline_missed_count'] == 0
    censored = summary['censored_prefix', delivery.JOINT]
    assert censored['accepted_hours'] == 25 and censored['right_censored_count'] == 3
    rejected = summary['b6_shared_rejection', delivery.B6]
    assert (rejected['configured_hours'], rejected['submitted_hours'], rejected['accepted_hours'],
            rejected['unsubmitted_hours'], rejected['last_committed_power_hour']) == (48, 26, 25, 22, 25)
    assert rejected['rejection_stage'] == 'shared_execution'
    assert rejected['actual_rejected_hour_and_later_outcome'] is None
    assert all(r['formal_result'] is False and r['completion_claim_allowed'] is False for r in summary.values())


def test_hourly_exact_debt_cross_day_and_uncommitted_candidate(payload):
    records = [json.loads(line) for line in payload['records.jsonl'].splitlines()]
    assert len(records) == 1038
    rows = [r for r in records if r['case_id'] == 'normal_recovery' and r['arm_id'] == delivery.JOINT]
    hour24 = rows[23]['committed_execution']
    assert debt(hour24) == Fraction(1, 4)
    assert hour24['tracks']['shared']['physical']['state']['active_duration_hours'] == 2
    assert debt(rows[24]['committed_execution']) == Fraction(3, 8)
    assert debt(rows[25]['committed_execution']) == Fraction(1, 8)
    assert debt(rows[26]['committed_execution']) == 0
    b6 = [r for r in records if r['case_id'] == 'b6_shared_rejection' and r['arm_id'] == delivery.B6]
    last = b6[-1]
    assert last['status'] == 'rejected_uncommitted' and last['planned_candidate'] is not None
    assert last['committed_execution'] == last['before_execution'] == b6[-2]['committed_execution']
    assert last['committed_planning'] == last['before_planning']
    assert debt(last['committed_execution']) == Fraction(3, 4)
    assert last['observation']['hour']['power_source_hour'] == 26
    assert last['accepted_physical_actions'] is None
    assert last['attempted_actions_scope'] == 'separate_planning'
    assert b6[-2]['accepted_physical_actions']['shared']['physical']['actual_service_power'] == .75


def test_evidence_marks_every_input_and_preserves_null_deadlines(payload):
    rows = [json.loads(line) for line in payload['inputs.jsonl'].splitlines()]
    assert len(rows) == 265
    assert all(r['evidence_class'] == 'mechanism_assumption' for r in rows)
    assert all(r['observation']['due_hour'] is None for r in rows if r['case_id'] == 'unknown_deadline')
    assert unpack(payload, 'evidence.json')['real_observations_used'] is False


def put_package(path, payload):
    path.mkdir()
    for name, data in payload.items():
        (path/name).write_bytes(data)
    (path/'diagnostic_manifest.json').write_bytes(delivery.encoded(delivery.manifest(payload)))


def test_generation_verification_and_no_overwrite(tmp_path):
    path = tmp_path/'test_non_authoritative'
    result = delivery.write_package(path)
    assert result['replay_matches'] and result['record_count'] == 1038
    before = {p.name: p.read_bytes() for p in path.iterdir()}
    with pytest.raises(FileExistsError):
        delivery.write_package(path)
    assert before == {p.name: p.read_bytes() for p in path.iterdir()}
    assert delivery.verify_package(path) == result


@pytest.mark.parametrize('mutation', ['missing', 'extra', 'hash', 'rehashed_summary', 'rehashed_input', 'rehashed_record', 'dependency'])
def test_verifier_rejects_corruption_even_when_manifest_is_rehashed(tmp_path, payload, mutation):
    path = tmp_path/'test_non_authoritative'
    changed = dict(payload)
    if mutation == 'rehashed_summary':
        rows = unpack(payload, 'summary.json')
        rows[0]['accepted_hours'] = 999
        changed['summary.json'] = delivery.encoded(rows)
    if mutation == 'rehashed_input':
        rows = [json.loads(line) for line in payload['inputs.jsonl'].splitlines()]
        rows[0]['observation']['limits']['call_limit'] = .123
        changed['inputs.jsonl'] = b''.join(map(delivery.encoded, rows))
    if mutation == 'rehashed_record':
        rows = [json.loads(line) for line in payload['records.jsonl'].splitlines()]
        rows[0]['committed_execution']['tracks']['shared']['physical']['state']['event_count'] = 999
        changed['records.jsonl'] = b''.join(map(delivery.encoded, rows))
    put_package(path, changed)
    if mutation == 'missing':
        (path/'summary.json').unlink()
    if mutation == 'extra':
        (path/'extra.json').write_text('{}')
    if mutation == 'hash':
        (path/'summary.json').write_text('[]')
    if mutation == 'dependency':
        m = json.loads((path/'diagnostic_manifest.json').read_bytes())
        m['dependencies'][delivery.CONFIG] = '0'*64
        (path/'diagnostic_manifest.json').write_bytes(delivery.encoded(m))
    with pytest.raises(ValueError, match='inventory|mismatch'):
        delivery.verify_package(path)


def test_verifier_requires_manifest_last_and_regular_files(tmp_path, payload):
    path = tmp_path/'test_non_authoritative'
    put_package(path, payload)
    (path/'diagnostic_manifest.json').unlink()
    with pytest.raises(ValueError, match='inventory'):
        delivery.verify_package(path)
    (path/'diagnostic_manifest.json').mkdir()
    with pytest.raises(ValueError, match='regular'):
        delivery.verify_package(path)
