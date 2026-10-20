"""Short-budget, in-process four-arm episode execution; non-authoritative."""
from dataclasses import dataclass, fields
from fractions import Fraction as Q
from hashlib import sha256
from pathlib import Path
from threading import Lock

from . import hourly_transaction as tx
from .four_arm_replay import NETWORK, CFE, JOINT, B6
from .current_grid_step import _Owned, _owned


ARMS = (NETWORK, CFE, JOINT, B6)
CONTRACT = 'draft_four_arm_episode_reserved_hour_budget_v1'


def _implementation():
    if CONTRACT != 'draft_four_arm_episode_reserved_hour_budget_v1' or ARMS != (
            NETWORK, CFE, JOINT, B6):
        raise ValueError('episode contract drift')
    return tx._identity(CONTRACT, sha256(Path(__file__).read_bytes()).hexdigest(), tx._implementation())


@dataclass(frozen=True)
class EpisodeBudget:
    planned_hours: int
    max_reserved_solver_calls: int
    max_reserved_solver_seconds: int

    def __post_init__(self):
        for name, maximum in (('planned_hours', 168), ('max_reserved_solver_calls', 120),
                              ('max_reserved_solver_seconds', 60)):
            if type(getattr(self, name)) is not int or not 0 < getattr(self, name) <= maximum:
                raise ValueError('invalid short episode budget: '+name)


@dataclass(frozen=True, init=False)
class EpisodeHourInput(_Owned):
    info: object
    disclosure: object
    source_hour: tx.ContinuationHour
    source_audit: object
    limits: tx.HourlyLimits
    due_hour: int | None
    available_flexibility: float


@dataclass(frozen=True, init=False)
class EpisodeAttempt(_Owned):
    before_identity: str
    source_hour: int
    hour_input: EpisodeHourInput
    reserved_solver_calls: int
    reserved_solver_seconds: Q
    reference_result: object
    common_attempt: object
    arm_results: tuple
    unaccepted_arm_result: object
    skipped_halted_arms: tuple
    started_arm_ids: tuple
    arms_without_complete_result: tuple
    unattempted_arms: tuple
    solver_calls: int | None
    known_solver_calls: int
    solver_call_count_complete: bool
    dispatch_call_count_unresolved_arms: tuple
    outer_committed: bool
    status: str
    error: str | None

    @property
    def committed_arm_results(self):
        return tuple(r for r in self.arm_results if r.published_pair is not None) if self.outer_committed else ()

    @property
    def published_common_hour(self):
        return self.common_attempt.publication if self.outer_committed and self.common_attempt is not None else None


@dataclass(frozen=True, init=False)
class EpisodeSnapshot(_Owned):
    origin_identity: str
    implementation_identity: str
    common: tx.CommonHourCursor
    arms: tuple
    budget: EpisodeBudget
    planned_solver_calls: int
    planned_solver_seconds: Q
    reserved_solver_calls: int
    reserved_solver_seconds: Q
    attempts: tuple
    halted: bool
    status: str
    training_capacity_certificate: None
    complete_service_certificate: None
    causal_certificate: None
    formal_result: bool
    security_certified: bool

    @property
    def identity(self):
        return tx._identity(self)

    @property
    def planned_last_hour_attempted(self):
        return len(self.attempts) == self.budget.planned_hours

    @property
    def input_window_consumed(self):
        return self.planned_last_hour_attempted and all(a.published_common_hour is not None for a in self.attempts)


def _fairness(arms):
    first = arms[0]
    base_spec = first.business.spec
    base_track = first.business.initial.tracks[0][1]
    for arm in arms:
        # Capacity and its declaration may differ; service mechanisms may not.
        for f in fields(base_spec):
            if f.name not in {'arm_id', 'committed_capacity', 'capacity_declaration_id'}:
                if getattr(arm.business.spec, f.name) != getattr(base_spec, f.name):
                    raise ValueError('unequal four-arm business mechanism: '+f.name)
        track = arm.business.initial.tracks[0][1]
        if (track.physical != base_track.physical
                or track.ledger.accounting_period_id != base_track.ledger.accounting_period_id
                or tx.dispatch._physical(arm.grid) != tx.dispatch._physical(first.grid)
                or arm.dispatch_policy_identity != first.dispatch_policy_identity):
            raise ValueError('unequal four-arm physical origin, envelope or dispatch policy')


def _requirements(count, arms, reference_spec):
    return (count+2+len(arms)*(count+1),
        (count+2)*Q(str(reference_spec.time_limit_seconds)) + sum(
            ((count+1)*Q(str(a.solver_specification.time_limit_seconds)) for a in arms), Q(0)))


class EpisodeSession:
    """One mutable owner; snapshots cannot be supplied as executable cursors.

    Exclusivity is local to this object. No process lease, durable resume or
    cross-session uniqueness is claimed. Any interrupted attempt stops it.
    """
    __slots__ = ('_snapshot', '_reference_selector', '_spec', '_reference_budget', '_lock')

    def __init__(self, common, arms, *, reference_selector, solver_specification,
                 reference_budget, budget):
        if type(common) is not tx.CommonHourCursor or common.halted or common.last_publication_identity is not None:
            raise ValueError('unused owned common origin required')
        if type(arms) is not tuple or len(arms) != 4 or any(type(a) is not tx.ArmHourCursor for a in arms):
            raise ValueError('four owned arm origins required')
        if tuple(a.business.spec.arm_id for a in arms) != ARMS:
            raise ValueError('canonical four-arm inventory required')
        for arm in arms:
            reconstructed = tx.initialize_arm_hours(common, arm.business, arm.grid,
                selector=arm.dispatch_selector, solver_specification=arm.solver_specification, budget=arm.budget)
            if reconstructed != arm:
                raise ValueError('unused canonical arm origin required')
        _fairness(arms)
        count = len(tx.reference._physical(common.reference_state).generation_mw)+2
        tx.reference_selection._admit(reference_selector, solver_specification, reference_budget, count)
        if tx.reference_selection._policy_identity(reference_selector, solver_specification, reference_budget) != common.reference_policy_identity:
            raise ValueError('reference origin policy mismatch')
        if type(budget) is not EpisodeBudget:
            raise ValueError('typed episode budget required')
        budget.__post_init__()
        calls, seconds = _requirements(count-2, arms, solver_specification)
        if (calls*budget.planned_hours > budget.max_reserved_solver_calls
                or seconds*budget.planned_hours > budget.max_reserved_solver_seconds):
            raise ValueError('complete planned episode exceeds short budget')
        self._reference_selector = reference_selector
        self._spec = solver_specification
        self._reference_budget = reference_budget
        self._lock = Lock()
        implementation = _implementation()
        origin = tx._identity(implementation, common, arms, reference_selector, solver_specification, reference_budget, budget)
        self._snapshot = _owned(EpisodeSnapshot, origin_identity=origin, implementation_identity=implementation,
            common=common, arms=arms, budget=budget, reserved_solver_calls=0,
            planned_solver_calls=calls*budget.planned_hours, planned_solver_seconds=seconds*budget.planned_hours,
            reserved_solver_seconds=Q(0), attempts=(), halted=False, status='active',
            training_capacity_certificate=None, complete_service_certificate=None, causal_certificate=None,
            formal_result=False, security_certified=False)

    def __copy__(self):
        raise TypeError('episode session cannot be copied')

    def __deepcopy__(self, memo):
        raise TypeError('episode session cannot be copied')

    def __reduce_ex__(self, protocol):
        raise TypeError('episode session is not a durable checkpoint')

    @property
    def snapshot(self):
        return self._snapshot

    def advance(self, info, disclosure, source_hour, source_audit, *, limits, due_hour, available_flexibility):
        if not self._lock.acquire(blocking=False):
            raise ValueError('episode attempt already in progress')
        try:
            return self._advance(info, disclosure, source_hour, source_audit,
                limits=limits, due_hour=due_hour, available_flexibility=available_flexibility)
        finally:
            self._lock.release()

    def _advance(self, info, disclosure, source_hour, source_audit, **business):
        before = self._snapshot
        if before.halted:
            raise ValueError('halted episode cannot consume suffix')
        if before.implementation_identity != _implementation():
            raise ValueError('episode implementation drift')
        if tx.reference_selection._policy_identity(self._reference_selector, self._spec, self._reference_budget) != before.common.reference_policy_identity:
            raise ValueError('episode reference policy drift')
        if type(source_hour) is not tx.ContinuationHour:
            raise ValueError('typed current source hour required')
        source_hour.__post_init__()
        tx._validate_next_identity(before.common.source_anchor, source_hour)
        # Full mapping validation follows selection; this check rejects clock
        # mismatch before reserving resources or calling any solver.
        if source_hour.power_source_hour != info.current.source_hour:
            raise ValueError('episode current clock mismatch')
        audit_origin = before.common.source_audit_origin
        if (type(source_audit) is not tx.mapping_api.RequestSourceAudit
                or source_audit.current_visible_identity != info.visible_identity
                or source_audit.source_hour != info.current.source_hour
                or (source_audit.normal_input_identity, source_audit.prepared_audit_identity, source_audit.split, source_audit.outage_seed)
                != (audit_origin.normal_input_identity, audit_origin.prepared_audit_identity, audit_origin.split, audit_origin.outage_seed)
                or (source_hour.split, source_hour.power_outage_seed) != (source_audit.split, source_audit.outage_seed)
                or source_hour.grid_request != 0
                or Q(str(source_hour.workload_occupancy))*Q(before.common.mapping.normalized_unit_mw) != Q(str(info.current.dc_baseline_mw))):
            raise ValueError('episode common source audit or baseline mismatch')
        if type(business['limits']) is not tx.HourlyLimits:
            raise ValueError('typed current business limits required')
        business['limits'].__post_init__()
        available = business['available_flexibility']
        due = business['due_hour']
        if type(available) not in (int, float) or not 0 <= available <= 1:
            raise ValueError('bounded scalar available flexibility required')
        if due is not None and (type(due) is not int or due < source_hour.power_source_hour):
            raise ValueError('current deadline must not precede source hour')
        hour_input = _owned(EpisodeHourInput, info=info, disclosure=disclosure,
            source_hour=source_hour, source_audit=source_audit, **business)
        expected = tx.reference.reference_input_identity(info, disclosure, before.common.reference_state)
        active = tuple(a for a in before.arms if not a.halted)
        count = len(info.network.units)
        calls, seconds = _requirements(count, active, self._spec)
        fits = (len(before.attempts) < before.budget.planned_hours
            and before.reserved_solver_calls+calls <= before.budget.max_reserved_solver_calls
            and before.reserved_solver_seconds+seconds <= before.budget.max_reserved_solver_seconds)
        if not fits:
            self._snapshot = _owned(EpisodeSnapshot, **dict(vars(before), halted=True, status='budget_exhausted'))
            return self._snapshot
        # Reservation is committed before effectful work and never refunded.
        # The provisional halted state makes re-entry after exceptions fail closed.
        reserved = _owned(EpisodeSnapshot, **dict(vars(before),
            reserved_solver_calls=before.reserved_solver_calls+calls,
            reserved_solver_seconds=before.reserved_solver_seconds+seconds,
            halted=True, status='attempt_in_progress'))
        selected = common_attempt = pending_arm = None
        results, started = [], []
        common, arms = before.common, list(before.arms)
        status, error, known, complete_call_count = 'interrupted', None, 0, True
        try:
            self._snapshot = reserved
            selected = tx.reference_selection.select_reference_hour(info, disclosure, common.reference_state,
                expected_identity=expected, selector=self._reference_selector,
                solver_specification=self._spec, budget=self._reference_budget)
            if (type(selected) is not tx.reference_selection.ReferenceSelectionResult
                    or selected.input_identity != expected or selected.planned_solver_calls != count+2
                    or selected.selector_policy_identity != common.reference_policy_identity):
                raise ValueError('episode reference result lineage mismatch')
            known += selected.solver_calls
            common_attempt = tx.publish_common_hour(common, info, disclosure, selected, source_hour, source_audit, **business)
            if (type(common_attempt) is not tx.CommonHourAttempt or common_attempt.before_identity != common.identity
                    or common_attempt.reference_result != selected):
                raise ValueError('episode common attempt lineage mismatch')
            mapped = common_attempt.mapping_result
            if (mapped.original_source_hour != source_hour or mapped.source_audit != source_audit
                    or mapped.mapping != common.mapping or mapped.reference_result_identity != selected.identity):
                raise ValueError('episode common mapping differs from saved input')
            publication = common_attempt.publication
            if publication is not None:
                expected_current = tx.CapacityObservation(
                    tx.CurrentObservation(mapped.mapped_hour, business['limits'], business['due_hour']),
                    business['available_flexibility'])
                if (publication.info != info or publication.disclosure != disclosure
                        or publication.business_current != expected_current
                        or publication.mapping_result != mapped or publication.reference_result != selected
                        or publication.common_origin_identity != common.origin_identity
                        or publication.previous_publication_identity != common.last_publication_identity
                        or publication.implementation_identity != common.implementation_identity
                        or common_attempt.cursor.last_publication_identity != publication.identity):
                    raise ValueError('episode common publication differs from saved input')
            common = common_attempt.cursor
            if common_attempt.publication is None:
                status = common_attempt.status
            else:
                for index, arm in enumerate(arms):
                    if arm.halted:
                        continue
                    started.append(arm.business.spec.arm_id)
                    result = tx.advance_arm_hour(arm, common_attempt.publication)
                    pending_arm = result if type(result) is tx.ArmHourResult else None
                    publication = common_attempt.publication
                    if (type(result) is not tx.ArmHourResult or result.before_identity != arm.identity
                            or result.arm_id != arm.business.spec.arm_id
                            or result.publication_identity != publication.identity
                            or result.exposure_id != publication.exposure_id
                            or result.cursor.origin_identity != arm.origin_identity
                            or result.cursor.common_origin_identity != common.origin_identity
                            or result.cursor.mapping != common.mapping
                            or result.cursor.dispatch_policy_identity != arm.dispatch_policy_identity
                            or result.cursor.business_policy_identity != arm.business_policy_identity
                            or (result.status == 'committed') != (result.published_pair is not None)
                            or (result.published_pair is not None and result.published_pair != (result.cursor.business, result.cursor.grid))
                            or result.cursor.halted != (result.published_pair is None)):
                        raise ValueError('episode arm result lineage mismatch')
                    results.append(result)
                    pending_arm = None
                    if result.dispatch_result is not None:
                        known += result.dispatch_result.solver_calls
                    elif result.status not in {'business_rejected', 'network_input_rejected', 'input_rejected'}:
                        # The lower transaction can catch an exception raised
                        # inside dispatch after a native call but before a result.
                        complete_call_count = False
                    arms[index] = result.cursor
                status = 'all_arms_halted' if all(a.halted for a in arms) else 'advanced'
                if status == 'advanced' and len(before.attempts)+1 == before.budget.planned_hours:
                    status = 'observation_window_complete'
            if known > calls:
                raise ValueError('episode call budget exceeded during attempt')
        except BaseException as exc:
            error = type(exc).__name__+':'+str(exc)
            status = 'interrupted'
            raise
        finally:
            if status == 'interrupted':
                # Completed inner candidates remain in the attempt evidence;
                # an interrupted outer hour does not publish a partial episode.
                common, arms = before.common, before.arms
            attempted = {r.arm_id for r in results}
            skipped = tuple(a.business.spec.arm_id for a in before.arms if a.halted)
            record = _owned(EpisodeAttempt, before_identity=before.identity, source_hour=source_hour.power_source_hour,
                hour_input=hour_input,
                reserved_solver_calls=calls, reserved_solver_seconds=seconds, reference_result=selected,
                common_attempt=common_attempt, arm_results=tuple(results), skipped_halted_arms=skipped,
                unaccepted_arm_result=pending_arm, started_arm_ids=tuple(started),
                arms_without_complete_result=tuple(a for a in started if a not in attempted),
                unattempted_arms=tuple(a.business.spec.arm_id for a in active if a.business.spec.arm_id not in started),
                solver_calls=known if status != 'interrupted' and complete_call_count else None, known_solver_calls=known,
                solver_call_count_complete=status != 'interrupted' and complete_call_count,
                dispatch_call_count_unresolved_arms=tuple(r.arm_id for r in results
                    if r.dispatch_result is None and r.status == 'dispatch_execution_unresolved'),
                outer_committed=status != 'interrupted',
                status=status, error=error)
            completed = _owned(EpisodeSnapshot, **dict(vars(reserved), common=common, arms=tuple(arms),
                attempts=before.attempts+(record,), halted=status != 'advanced', status=status))
            if status != 'interrupted':
                try:
                    if (tx.reference_selection._policy_identity(self._reference_selector, self._spec, self._reference_budget)
                            != before.common.reference_policy_identity
                            or any(tx.dispatch._policy_identity(a.dispatch_selector, a.solver_specification, a.budget)
                                != a.dispatch_policy_identity for a in before.arms)
                            or before.implementation_identity != _implementation()):
                        raise ValueError('episode implementation or policy changed before commit')
                except BaseException as exc:
                    record = _owned(EpisodeAttempt, **dict(vars(record), outer_committed=False,
                        solver_call_count_complete=False, solver_calls=None, status='interrupted',
                        error=type(exc).__name__+':'+str(exc)))
                    self._snapshot = _owned(EpisodeSnapshot, **dict(vars(reserved),
                        common=before.common, arms=before.arms, attempts=before.attempts+(record,),
                        halted=True, status='interrupted'))
                    raise
            self._snapshot = completed
        return self._snapshot
