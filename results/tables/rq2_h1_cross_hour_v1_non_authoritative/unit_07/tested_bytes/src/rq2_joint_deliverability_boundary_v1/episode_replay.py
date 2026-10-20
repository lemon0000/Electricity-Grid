"""Source-bound, solver-free episode archive diagnostics; never a resume API."""
from dataclasses import dataclass, fields
from fractions import Fraction as Q
from hashlib import sha256
import json
from pathlib import Path

from . import episode_coordinator as ep
from . import hourly_transaction as tx
from . import selector_replay as selectors
from .current_grid_step import _Owned, _owned
from .prefix_handoff import _encoded, _unique_object, _reject_constant


SCHEMA = 'rq2_source_bound_episode_replay_v1'
DEPENDENCIES = tuple(sorted(set(selectors.DEPENDENCIES) | {
    'src/rq2_joint_deliverability_boundary_v1/'+name+'.py' for name in
    ('episode_replay', 'episode_coordinator', 'hourly_transaction', 'common_request_adapter')}))


def _implementation():
    if SCHEMA != 'rq2_source_bound_episode_replay_v1':
        raise ValueError('episode replay schema drift')
    root = Path(__file__).resolve().parents[2]
    return tx._identity(SCHEMA, ep._implementation(),
        tuple((p, sha256((root/p).read_bytes()).hexdigest()) for p in DEPENDENCIES))


def episode_replay_input_identity(common, arms, hours, *, reference_selector,
                                 solver_specification, reference_budget, budget):
    if type(hours) is not tuple or any(type(h) is not ep.EpisodeHourInput for h in hours):
        raise ValueError('independent immutable typed episode hour inventory required')
    return tx._identity(common, arms, hours, reference_selector, solver_specification, reference_budget, budget)


def _envelope(snapshot, input_identity):
    return dict(schema=SCHEMA, status='DRAFT_NONAUTHORITATIVE', input_identity=input_identity,
        implementation_identity=_implementation(), snapshot=snapshot,
        native_execution_authenticated=False, formal_result=False, security_certified=False,
        resume_authorized=False)


def export_episode_archive(snapshot, *, input_identity):
    selectors.native._hash(input_identity)
    if type(snapshot) is not ep.EpisodeSnapshot or snapshot.implementation_identity != ep._implementation():
        raise ValueError('current owned episode snapshot required')
    if snapshot.status in ('attempt_in_progress', 'budget_exhausted'):
        raise ValueError('snapshot lacks the attempted invocation journal')
    return _encoded(_envelope(snapshot, input_identity))


def write_episode_archive(snapshot, path, *, input_identity):
    path = Path(path)
    if not path.name.endswith('_non_authoritative.json'):
        raise ValueError('explicit non_authoritative filename required')
    data = export_episode_archive(snapshot, input_identity=input_identity)
    with path.open('xb') as stream:
        stream.write(data)
    return sha256(data).hexdigest()


@dataclass(frozen=True, init=False)
class EpisodeReplayDiagnostic(_Owned):
    artifact_sha256: str
    input_identity: str
    implementation_identity: str
    status: str
    archived_outcome: str
    archive_reproduced: bool
    source_input_binding_verified: bool
    verified_hour_count: int
    verified_arm_result_count: int
    observed_attempt_count: int
    unverified_attempt_count: int
    selector_diagnostics: tuple
    business_power_bindings_verified: int
    reproduced_snapshot_identity: str | None
    evidence_gap: str | None
    solver_calls_by_replay_module: int
    native_execution_authenticated: bool
    training_capacity_certificate: None
    complete_service_certificate: None
    causal_certificate: None
    formal_result: bool
    security_certified: bool
    resume_authorized: bool


class _EvidenceGap(Exception):
    def __init__(self, kind, *, suffix_possible=False):
        super().__init__(kind)
        self.suffix_possible = suffix_possible


def _same(actual, saved, label):
    if _encoded(actual) != _encoded(saved):
        raise ValueError('episode archive mismatch: '+label)


def _inventory(saved, cls):
    if type(saved) is not dict or set(saved) != {f.name for f in fields(cls)}:
        raise ValueError('episode archive field inventory mismatch: '+cls.__name__)


def _selector(kind, saved, info, disclosure, before, power, selector, spec, budget, policy, reports):
    if saved is None:
        raise _EvidenceGap(kind+'_selector_return_missing')
    data = _encoded(dict(schema=selectors.SCHEMA, status='DRAFT_NONAUTHORITATIVE', kind=kind,
        implementation_identity=selectors._implementation(spec, budget), result=saved,
        native_execution_authenticated=False, formal_result=False, security_certified=False,
        resume_authorized=False))
    report, result = selectors._checked_verify(kind, data, info, disclosure, before, power,
        expected_sha256=sha256(data).hexdigest(),
        expected_input_identity=selectors._input(kind, info, disclosure, before, power),
        expected_policy_identity=policy, selector=selector, solver_specification=spec, budget=budget)
    reports.append(report)
    if result is None:
        raise _EvidenceGap(kind+'_partial_native_evidence')
    return result


def _arm(before, publication, saved, reports, bindings):
    """Independently reproduce the business/power/dispatch transaction."""
    _inventory(saved, tx.ArmHourResult)
    hour = publication.mapping_result.mapped_hour
    tx._validate_next_identity(before.business.execution.tracks[0][1].physical.anchor, hour)
    physical = tx.dispatch._physical(before.grid)
    if (before.halted or physical.source_hour+1 != hour.power_source_hour
            or publication.disclosure.before != physical.disclosure
            or publication.previous_publication_identity != before.last_publication_identity
            or publication.common_origin_identity != before.common_origin_identity
            or before.business.policy_id != before.business_policy_identity):
        raise ValueError('episode arm source or policy lineage mismatch')
    candidate = power = result = None
    status, error, candidate_failure = 'input_rejected', None, None
    applicable = before.business.spec.arm_id != ep.CFE
    network_input = None
    try:
        candidate = tx.advance_capacity_policy(before.business, publication.business_current)
        record = candidate.records[-1]
        candidate_failure = record.response.grid_service_failure if record.response is not None and applicable else None
        status, error = 'business_rejected', record.error
        if record.committed:
            action = record.response.action
            expected = Q(str(hour.workload_occupancy))-action.grid_served-action.cfe_served+action.recovery
            if action.actual_service_power != expected or record.current.observation.hour != hour:
                raise ValueError('business actual power balance mismatch')
            mw = expected*Q(before.mapping.normalized_unit_mw)
            power = tx.PrescribedDcPower(hour.power_source_hour, str(mw.numerator), str(mw.denominator), 'mechanism_assumption')
            status = 'network_input_rejected'
            network_input = tx.dispatch.dispatch_input_identity(publication.info, publication.disclosure, before.grid, power)
    except (ValueError, OverflowError) as exc:
        error = str(exc)
    # Archive audit failures are outside the live transaction's exception
    # handler: malformed archives must not become ordinary service rejections.
    _same(candidate, saved['business_candidate'], 'business candidate')
    _same(power, saved['prescribed_power'], 'business actual power')
    if network_input is not None:
        bindings.append((before.business.spec.arm_id, hour.power_source_hour))
        try:
            result = _selector('actual', saved['dispatch_result'], publication.info, publication.disclosure,
                before.grid, power, before.dispatch_selector, before.solver_specification, before.budget,
                before.dispatch_policy_identity, reports)
        except _EvidenceGap as exc:
            missing = saved['dispatch_result'] is None
            partial_status = 'dispatch_execution_unresolved' if missing else 'physical_network_unresolved'
            partial_error = saved['error'] if missing else ';'.join(saved['dispatch_result']['errors']) or None
            if missing and (type(partial_error) is not str or not partial_error):
                raise ValueError('missing dispatch return requires an execution error')
            cursor = _owned(tx.ArmHourCursor, **dict(vars(before), halted=True))
            _same(dict(before_identity=before.identity, publication_identity=publication.identity,
                exposure_id=publication.exposure_id, arm_id=before.business.spec.arm_id,
                business_candidate=candidate, prescribed_power=power, dispatch_result=saved['dispatch_result'],
                cursor=cursor, published_pair=None, status=partial_status, error=partial_error,
                grid_service_applicable=applicable, candidate_grid_service_failure=candidate_failure,
                grid_service_failure=None, physical_network_check_applicable=True, capacity_certificate=None,
                causal_certificate=None, formal_result=False, security_certified=False), saved, 'partial arm fail-closed shape')
            raise _EvidenceGap(str(exc), suffix_possible=True) from exc
        status, error = 'physical_network_unresolved', ';'.join(result.errors) or None
        if result.status == 'selected_numerical_dispatch':
            if result.prescribed_power != power or result.next_dispatch_state.previous_state_identity != before.grid.identity:
                raise ValueError('replayed dispatch predecessor mismatch')
            status, error = 'committed', None
    else:
        _same(None, saved['dispatch_result'], 'unexpected dispatch after business/input rejection')
    committed = status == 'committed' and error is None
    cursor = _owned(tx.ArmHourCursor, **dict(vars(before), business=candidate if committed else before.business,
        grid=result.next_dispatch_state if committed else before.grid,
        last_publication_identity=publication.identity if committed else before.last_publication_identity,
        halted=not committed))
    result = _owned(tx.ArmHourResult, before_identity=before.identity, publication_identity=publication.identity,
        exposure_id=publication.exposure_id, arm_id=before.business.spec.arm_id, business_candidate=candidate,
        prescribed_power=power, dispatch_result=result, cursor=cursor,
        published_pair=(cursor.business, cursor.grid) if committed else None, status=status, error=error,
        grid_service_applicable=applicable, candidate_grid_service_failure=candidate_failure,
        grid_service_failure=candidate_failure if committed else None, physical_network_check_applicable=True,
        capacity_certificate=None, causal_certificate=None, formal_result=False, security_certified=False)
    _same(result, saved, 'complete arm transaction')
    return result


def _admit_hour(before, h):
    if before.halted:
        raise ValueError('halted episode cannot consume archived suffix')
    h.source_hour.__post_init__()
    tx._validate_next_identity(before.common.source_anchor, h.source_hour)
    origin = before.common.source_audit_origin
    if (h.source_hour.power_source_hour != h.info.current.source_hour
            or type(h.source_audit) is not tx.mapping_api.RequestSourceAudit
            or h.source_audit.current_visible_identity != h.info.visible_identity
            or h.source_audit.source_hour != h.info.current.source_hour
            or (h.source_audit.normal_input_identity, h.source_audit.prepared_audit_identity,
                h.source_audit.split, h.source_audit.outage_seed)
            != (origin.normal_input_identity, origin.prepared_audit_identity, origin.split, origin.outage_seed)
            or (h.source_hour.split, h.source_hour.power_outage_seed) != (h.source_audit.split, h.source_audit.outage_seed)
            or h.source_hour.grid_request != 0
            or Q(str(h.source_hour.workload_occupancy))*Q(before.common.mapping.normalized_unit_mw)
                != Q(str(h.info.current.dc_baseline_mw))):
        raise ValueError('episode source audit or baseline mismatch')
    if type(h.limits) is not tx.HourlyLimits:
        raise ValueError('typed hour limits required')
    h.limits.__post_init__()
    if type(h.available_flexibility) not in (int, float) or not 0 <= h.available_flexibility <= 1:
        raise ValueError('bounded available flexibility required')
    if h.due_hour is not None and (type(h.due_hour) is not int or h.due_hour < h.source_hour.power_source_hour):
        raise ValueError('invalid current deadline')
    tx.reference.reference_input_identity(h.info, h.disclosure, before.common.reference_state)


def _partial_inventory(before, record, common_attempt):
    """Audit returned siblings independently, without advancing the outer state."""
    active = tuple(a for a in before.arms if not a.halted)
    active_ids = tuple(a.business.spec.arm_id for a in active)
    rows = record['arm_results']
    if type(rows) is not list or len(rows) > len(active):
        raise ValueError('partial returned arm inventory mismatch')
    if (common_attempt is None or common_attempt.publication is None) and rows:
        raise ValueError('arm returns require a reconstructed common publication')
    known = record['reference_result']['solver_calls'] if record['reference_result'] is not None else 0
    unknown = []
    for arm, row in zip(active, rows):
        scratch = []
        try:
            _arm(arm, common_attempt.publication, row, scratch, [])
        except _EvidenceGap as exc:
            if not exc.suffix_possible:
                raise
        # _arm has now checked either the full returned record or its typed
        # partial fail-closed shape, including any recorded selector calls.
        if row['dispatch_result'] is not None:
            known += row['dispatch_result']['solver_calls']
        elif row['status'] == 'dispatch_execution_unresolved':
            unknown.append(arm.business.spec.arm_id)
    started = record['started_arm_ids']
    if type(started) is not list:
        raise ValueError('partial started inventory must be a list')
    _same(active_ids[:len(started)], started, 'partial started canonical prefix')
    interrupted = record['status'] == 'interrupted'
    if interrupted:
        if not len(rows) <= len(started) <= min(len(rows)+1, len(active)):
            raise ValueError('interrupted start/return inventory mismatch')
        if record['unaccepted_arm_result'] is not None and len(started) != len(rows)+1:
            raise ValueError('unaccepted arm requires one uncompleted started arm')
    else:
        expected_started = active_ids if common_attempt is not None and common_attempt.publication is not None else ()
        _same(expected_started, started, 'completed outer started arms')
        _same(len(started), len(rows), 'completed outer returned arms')
        _same(None, record['unaccepted_arm_result'], 'completed outer pending arm')
    _same(tuple(a.business.spec.arm_id for a in before.arms if a.halted), record['skipped_halted_arms'], 'partial skipped arms')
    _same(tuple(started[len(rows):]), record['arms_without_complete_result'], 'partial incomplete arms')
    _same(active_ids[len(started):], record['unattempted_arms'], 'partial unattempted arms')
    _same(tuple(unknown), record['dispatch_call_count_unresolved_arms'], 'partial unknown dispatch arms')
    _same(known, record['known_solver_calls'], 'partial known solver calls')
    complete = not interrupted and not unknown
    _same(complete, record['solver_call_count_complete'], 'partial solver call completeness')
    _same(known if complete else None, record['solver_calls'], 'partial solver calls')
    if known > record['reserved_solver_calls']:
        raise ValueError('partial known calls exceed reservation')
    cursors = {row['arm_id']: row['cursor'] for row in rows}
    return tuple(cursors.get(a.business.spec.arm_id, a) for a in before.arms)


def _verify(data, common, arms, hours, *, expected_sha256, expected_input_identity,
            reference_selector, solver_specification, reference_budget, budget):
    selectors.native._hash(expected_sha256)
    selectors.native._hash(expected_input_identity)
    if type(data) is not bytes or sha256(data).hexdigest() != expected_sha256:
        raise ValueError('episode archive digest mismatch')
    config = dict(reference_selector=reference_selector, solver_specification=solver_specification,
        reference_budget=reference_budget, budget=budget)
    identity = episode_replay_input_identity(common, arms, hours, **config)
    if identity != expected_input_identity:
        raise ValueError('independent episode input identity mismatch')
    implementation = _implementation()
    initial = ep.EpisodeSession(common, arms, **config).snapshot
    payload = json.loads(data, object_pairs_hook=_unique_object, parse_constant=_reject_constant)
    _same(_envelope(payload['snapshot'], identity), payload, 'canonical envelope')
    if _encoded(payload) != data:
        raise ValueError('canonical episode archive bytes required')
    saved = payload['snapshot']
    _inventory(saved, ep.EpisodeSnapshot)
    if saved['status'] in ('attempt_in_progress', 'budget_exhausted'):
        raise ValueError('snapshot lacks the attempted invocation journal')
    if type(saved['attempts']) is not list or len(saved['attempts']) != len(hours) or len(hours) > budget.planned_hours:
        raise ValueError('independent attempted-hour inventory mismatch')
    for key in ('origin_identity', 'implementation_identity', 'budget', 'planned_solver_calls',
                'planned_solver_seconds', 'training_capacity_certificate', 'complete_service_certificate',
                'causal_certificate', 'formal_result', 'security_certified'):
        _same(getattr(initial, key), saved[key], key)
    for h, record in zip(hours, saved['attempts']):
        _inventory(record, ep.EpisodeAttempt)
        _same(h, record['hour_input'], 'independent hour input')
    before, reports, bindings = initial, [], []
    verified_arms, gap = 0, None
    for index, (h, record) in enumerate(zip(hours, saved['attempts'])):
        _inventory(record, ep.EpisodeAttempt)
        _admit_hour(before, h)
        _same(h, record['hour_input'], 'independent hour input')
        _same(before.identity, record['before_identity'], 'hour predecessor')
        _same(h.source_hour.power_source_hour, record['source_hour'], 'attempt source hour')
        active = tuple(a for a in before.arms if not a.halted)
        calls, seconds = ep._requirements(len(h.info.network.units), active, solver_specification)
        if (before.reserved_solver_calls+calls > budget.max_reserved_solver_calls
                or before.reserved_solver_seconds+seconds > budget.max_reserved_solver_seconds):
            raise ValueError('archived attempt exceeds episode budget')
        _same(calls, record['reserved_solver_calls'], 'reserved calls')
        _same(seconds, record['reserved_solver_seconds'], 'reserved seconds')
        results, started, selected, common_attempt = [], [], None, None
        try:
            selected = _selector('reference', record['reference_result'], h.info, h.disclosure,
                before.common.reference_state, None, reference_selector, solver_specification,
                reference_budget, before.common.reference_policy_identity, reports)
            common_attempt = tx.publish_common_hour(before.common, h.info, h.disclosure, selected,
                h.source_hour, h.source_audit, limits=h.limits, due_hour=h.due_hour,
                available_flexibility=h.available_flexibility)
            if record['common_attempt'] is None:
                raise _EvidenceGap('common_transaction_return_missing')
            _same(common_attempt, record['common_attempt'], 'common mapping/publication')
            next_arms = list(before.arms)
            if common_attempt.publication is not None:
                for arm_index, arm in enumerate(before.arms):
                    if arm.halted:
                        continue
                    if len(results) >= len(record['arm_results']):
                        raise _EvidenceGap('arm_transaction_return_missing')
                    started.append(arm.business.spec.arm_id)
                    result = _arm(arm, common_attempt.publication, record['arm_results'][len(results)], reports, bindings)
                    results.append(result)
                    verified_arms += 1
                    next_arms[arm_index] = result.cursor
                status = 'all_arms_halted' if all(a.halted for a in next_arms) else 'advanced'
                if status == 'advanced' and index+1 == budget.planned_hours:
                    status = 'observation_window_complete'
            else:
                status = common_attempt.status
            if record['status'] == 'interrupted':
                raise _EvidenceGap('outer_execution_interrupted')
            known = selected.solver_calls + sum(r.dispatch_result.solver_calls for r in results if r.dispatch_result is not None)
            reconstructed = _owned(ep.EpisodeAttempt, before_identity=before.identity, source_hour=h.source_hour.power_source_hour,
                hour_input=h, reserved_solver_calls=calls, reserved_solver_seconds=seconds, reference_result=selected,
                common_attempt=common_attempt, arm_results=tuple(results), unaccepted_arm_result=None,
                skipped_halted_arms=tuple(a.business.spec.arm_id for a in before.arms if a.halted),
                started_arm_ids=tuple(started), arms_without_complete_result=(),
                unattempted_arms=tuple(a.business.spec.arm_id for a in active if a.business.spec.arm_id not in started),
                solver_calls=known, known_solver_calls=known, solver_call_count_complete=True,
                dispatch_call_count_unresolved_arms=(), outer_committed=True, status=status, error=None)
            _same(reconstructed, record, 'complete outer hour transaction')
            before = _owned(ep.EpisodeSnapshot, **dict(vars(before), common=common_attempt.cursor, arms=tuple(next_arms),
                reserved_solver_calls=before.reserved_solver_calls+calls,
                reserved_solver_seconds=before.reserved_solver_seconds+seconds,
                attempts=before.attempts+(reconstructed,), halted=status != 'advanced', status=status))
        except _EvidenceGap as exc:
            # Never invent the missing exception/native record or an owned
            # successor. The digest preserves it, but it is not reproduced.
            gap = str(exc)
            if not exc.suffix_possible and index != len(hours)-1:
                raise ValueError('halted or interrupted evidence boundary cannot have a suffix')
            if gap in ('reference_selector_return_missing', 'common_transaction_return_missing',
                       'arm_transaction_return_missing', 'outer_execution_interrupted'):
                _same('interrupted', record['status'], 'missing outer return requires interruption')
            if gap == 'reference_partial_native_evidence' and record['status'] != 'interrupted':
                _same('request_unresolved', record['status'], 'partial reference halt')
                _same(True, record['outer_committed'], 'partial reference outer transaction')
                _same([], record['arm_results'], 'partial reference cannot start arms')
                _same([], record['started_arm_ids'], 'partial reference started arms')
                _same(None, record['common_attempt']['publication'], 'partial reference publication')
                stopped = _owned(tx.CommonHourCursor, **dict(vars(before.common), halted=True))
                _same(stopped, record['common_attempt']['cursor'], 'partial reference common cursor')
                _same(stopped, saved['common'], 'partial reference final common')
                _same(before.arms, saved['arms'], 'partial reference unchanged arms')
                _same(True, saved['halted'], 'partial reference final halt')
                _same('request_unresolved', saved['status'], 'partial reference final status')
            projected_arms = _partial_inventory(before, record, common_attempt)
            if record['status'] != 'interrupted':
                _same(None, record['error'], 'completed outer error')
            if exc.suffix_possible:
                _same(tuple(started), tuple(record['started_arm_ids'][:len(started)]), 'partial started arm prefix')
                if record['status'] != 'interrupted':
                    _same(True, record['outer_committed'], 'partial arm outer commit')
                    all_halted = all(a['halted'] if type(a) is dict else a.halted for a in projected_arms)
                    expected_status = 'all_arms_halted' if all_halted else (
                        'observation_window_complete' if index+1 == budget.planned_hours else 'advanced')
                    _same(expected_status, record['status'], 'partial outer status from verified arm projections')
                    if index == len(hours)-1:
                        _same(record['status'], saved['status'], 'partial final status')
                        _same(record['status'] != 'advanced', saved['halted'], 'partial final halt')
                        _same(common_attempt.cursor, saved['common'], 'partial committed common')
                        _same(projected_arms, saved['arms'], 'partial final arm projections')
                        for r in results:
                            _same(r.cursor, saved['arms'][ep.ARMS.index(r.arm_id)], 'partial verified arm commit')
                        partial_arm = record['arm_results'][len(results)]
                        _same(partial_arm['cursor'], saved['arms'][ep.ARMS.index(started[-1])], 'partial failed arm state')
                if index != len(hours)-1:
                    _same('advanced', record['status'], 'partial arm suffix requires advanced hour')
                    _same(True, record['outer_committed'], 'partial arm suffix outer commit')
            if record['status'] == 'interrupted':
                if index != len(hours)-1:
                    raise ValueError('interrupted episode cannot have a suffix')
                if type(record['error']) is not str or not record['error']:
                    raise ValueError('interrupted episode requires an error record')
                _same(False, record['outer_committed'], 'interrupted outer commit')
                _same(None, record['solver_calls'], 'interrupted unknown calls')
                _same(False, record['solver_call_count_complete'], 'interrupted call completeness')
                _same(before.common, saved['common'], 'interrupted common rollback')
                _same(before.arms, saved['arms'], 'interrupted arm rollback')
                _same(True, saved['halted'], 'interrupted halt')
                _same('interrupted', saved['status'], 'interrupted status')
            if index == len(hours)-1:
                _same(before.reserved_solver_calls+calls, saved['reserved_solver_calls'], 'partial reservation calls')
                _same(before.reserved_solver_seconds+seconds, saved['reserved_solver_seconds'], 'partial reservation seconds')
            break
    if gap is None:
        _same(before, saved, 'complete episode snapshot')
    report = _owned(EpisodeReplayDiagnostic, artifact_sha256=expected_sha256, input_identity=identity,
        implementation_identity=implementation, status='partial_episode_evidence' if gap else 'reproduced_episode',
        archived_outcome=saved['status'], archive_reproduced=gap is None, source_input_binding_verified=True,
        verified_hour_count=len(before.attempts), verified_arm_result_count=verified_arms,
        observed_attempt_count=len(hours), unverified_attempt_count=len(hours)-len(before.attempts),
        selector_diagnostics=tuple(reports), business_power_bindings_verified=len(bindings),
        reproduced_snapshot_identity=before.identity if gap is None else None, evidence_gap=gap,
        solver_calls_by_replay_module=0, native_execution_authenticated=False, training_capacity_certificate=None,
        complete_service_certificate=None, causal_certificate=None, formal_result=False, security_certified=False,
        resume_authorized=False)
    if (_implementation() != implementation
            or episode_replay_input_identity(common, arms, hours, **config) != identity):
        raise ValueError('episode replay source or implementation changed during audit')
    return report, before if gap is None else None


def replay_episode_archive(data, common, arms, hours, **expectations):
    try:
        return _verify(data, common, arms, hours, **expectations)[0]
    except (TypeError, KeyError, AttributeError, IndexError, OverflowError) as exc:
        raise ValueError('invalid episode archive structure') from exc
