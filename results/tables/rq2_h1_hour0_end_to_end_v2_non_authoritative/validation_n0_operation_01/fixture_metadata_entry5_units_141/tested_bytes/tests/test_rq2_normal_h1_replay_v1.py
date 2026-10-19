from hashlib import sha256
from copy import deepcopy
import json

import pytest

from tests.test_rq2_normal_h1_source_v1 import packet, run
from tests.test_rq2_normal_h1_short_solve_v1 import budget
from tests.test_rq2_objective_provenance_run_v1 import spec
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_replay as api


@pytest.fixture(scope='module')
def native_result():
    p = packet()
    result = run(p)
    assert result.current_decision_accepted, result.errors
    return p, result


@pytest.fixture(autouse=True)
def forbid_solver(monkeypatch, native_result):
    def forbidden(*args, **kwargs):
        pytest.fail('replay entered a solver')
    monkeypatch.setattr(api.native.capture, 'solve_once', forbidden)
    monkeypatch.setattr(api.native.capture.provenance.adapter, 'create_solver', forbidden)
    monkeypatch.setattr(api.current, 'solve_current', forbidden)


def reports(result):
    return tuple(s.native_payload for s in result.evidence.stages)


def replay(p, raw, key):
    return api.replay_archive(p, spec(), budget(), raw, expected_key=key,
                              expected_archive_sha256=sha256(raw).hexdigest())


def test_full_chain_archive_and_zero_solver_reconstruction(native_result):
    p, result = native_result
    raw = api.archive_current(p, spec(), budget(), result)
    restored = replay(p, raw, result.request_key)
    assert restored.projection_identity == result.decision.projection_identity
    assert restored.before_identity == result.decision.before_identity
    assert restored.canonical_locks == (20., 1., 20.)
    assert all(not s.errors for s in restored.stage_audits)
    assert restored.solver_calls_by_replay == 0 and restored.numerical_chain_recomputed
    assert not restored.native_execution_authenticated and not restored.published and not restored.formal_result
    assert not hasattr(restored, 'candidate_boundary')
    assert tuple(s.encode('ascii') for s in json.loads(raw)['reports']) == reports(result)


@pytest.mark.parametrize('kind', ['missing', 'extra', 'reverse', 'repeat', 'old_input'])
def test_complete_order_and_current_input_required(native_result, kind):
    p, result = native_result
    rows = reports(result)
    if kind == 'missing': rows = rows[:-1]
    if kind == 'extra': rows = (*rows, rows[-1])
    if kind == 'reverse': rows = tuple(reversed(rows))
    if kind == 'repeat': rows = (rows[0], rows[0], rows[2])
    if kind == 'old_input': p = packet(raw_workload='0.1')
    with pytest.raises(ValueError):
        api.replay_reports(p, spec(), budget(), rows, expected_key=result.request_key)


@pytest.mark.parametrize('field,value', [('solver_calls', True), ('variables', 999),
    ('constraints', 999), ('native_status', 999), ('normal_accepted', True),
    ('assignment', None), ('implementation_identity', '0'*64)])
def test_report_binding_tampering_rejected(native_result, field, value):
    p, result = native_result
    rows = list(reports(result))
    bad = json.loads(rows[1])
    bad[field] = value
    rows[1] = api.native.capture.encode(bad)
    with pytest.raises(ValueError):
        api.replay_reports(p, spec(), budget(), tuple(rows), expected_key=result.request_key)


def test_later_stage_numeric_bound_failure_not_hidden_by_final_assignment(native_result):
    p, result = native_result
    rows = list(reports(result))
    bad = json.loads(rows[1])
    bad['provenance']['native']['ObjBound']['hex'] = float(2).hex()
    rows[1] = api.native.capture.encode(bad)
    with pytest.raises(ValueError):
        api.replay_reports(p, spec(), budget(), tuple(rows), expected_key=result.request_key)


@pytest.mark.parametrize('field', ['projection_identity', 'projection', 'before_identity',
                                  'chain_identity', 'report_sha256', 'published', 'reports'])
def test_archive_self_claims_recomputed_even_with_updated_outer_hash(native_result, field):
    p, result = native_result
    item = json.loads(api.archive_current(p, spec(), budget(), result))
    if field == 'projection': item[field]['units'][0][2] = float(21).hex()
    elif field == 'published': item[field] = True
    elif field == 'reports': item[field] = item[field][:-1]
    elif field == 'report_sha256': item[field][0] = '0'*64
    else: item[field] = '0'*64
    raw = api.native.capture.encode(item)
    with pytest.raises(ValueError):
        replay(p, raw, result.request_key)


def test_duplicate_keys_noncanonical_bytes_and_wrong_pin_rejected(native_result):
    p, result = native_result
    raw = api.archive_current(p, spec(), budget(), result)
    for changed in (b'{"schema":"bad",'+raw[1:], raw+b'\n', b'NaN', b'[]'):
        with pytest.raises(ValueError):
            replay(p, changed, result.request_key)
    with pytest.raises(ValueError, match='SHA256'):
        api.replay_archive(p, spec(), budget(), raw, expected_key=result.request_key,
                            expected_archive_sha256='0'*64)


def test_auxiliary_witness_difference_keeps_projection(native_result):
    p, result = native_result
    changed = []
    for raw in reports(result):
        report = json.loads(raw)
        assignment = dict(report['assignment'])
        assert float.fromhex(assignment['reserve_up[0,G1]']) == 0.
        assignment['reserve_up[0,G1]'] = float(1).hex()
        report['assignment'] = sorted(assignment.items())
        provenance = report['provenance']
        referenced = tuple((name, assignment[name]) for name, _ in provenance['referenced_assignment'])
        provenance['referenced_assignment'] = referenced
        provenance['assignment_sha256'] = sha256(repr(referenced).encode()).hexdigest()
        changed.append(api.native.capture.encode(report))
    original = api.replay_reports(p, spec(), budget(), reports(result), expected_key=result.request_key)
    different = api.replay_reports(p, spec(), budget(), tuple(changed), expected_key=result.request_key)
    assert original.report_sha256 != different.report_sha256
    assert original.projection_payload == different.projection_payload
    assert original.projection_identity == different.projection_identity
    assert not different.native_execution_authenticated


def test_replay_cannot_construct_an_executable_boundary(native_result):
    p, result = native_result
    restored = api.replay_reports(p, spec(), budget(), reports(result), expected_key=result.request_key)
    with pytest.raises(TypeError):
        api.H1ReplayedProjection()
    with pytest.raises(ValueError):
        packet(relative_hour=1, before=restored)


@pytest.mark.parametrize('flag', ['exact_mathematical_certificate', 'formal_result', 'hard_process_resources_verified'])
def test_owned_authority_drift_is_rejected_not_silently_erased(native_result, flag):
    p, original = native_result
    result = deepcopy(original)
    object.__setattr__(result.evidence, flag, True)
    with pytest.raises(ValueError, match='owned'):
        api.archive_current(p, spec(), budget(), result)


def test_aggregate_payload_limit_precedes_model_build(monkeypatch, native_result):
    p, result = native_result
    monkeypatch.setattr(api, 'MAX_ARCHIVE_BYTES', 10)
    monkeypatch.setattr(api.current, 'request_key', lambda *a, **k: pytest.fail('budget check came after build'))
    with pytest.raises(ValueError, match='aggregate'):
        api.replay_reports(p, spec(), budget(), (b'123456',)*3, expected_key=result.request_key)


@pytest.mark.parametrize('raw', [None, b'{}'])
def test_owned_numeric_predicate_evidence_must_match_reconstruction(native_result, raw):
    p, original = native_result
    result = deepcopy(original)
    object.__setattr__(result.evidence.stages[1], 'numeric_predicate_payload', raw)
    with pytest.raises(ValueError, match='stage metadata'):
        api.archive_current(p, spec(), budget(), result)
