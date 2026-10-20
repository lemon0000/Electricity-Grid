"""Draft in-memory common-hour publication and atomic arm state pairs."""
from dataclasses import dataclass, fields
from fractions import Fraction as Q
from hashlib import sha256
from pathlib import Path

from .boundary import BoundaryAnchor, ContinuationHour, _validate_next_identity
from .causal_policy import CurrentObservation, HourlyLimits
from .capacity_policy import CapacityPolicyCursor, CapacityObservation, advance_capacity_policy
from .four_arm_replay import CFE, JOINT
from .prefix_handoff import IMPLEMENTATION, _plain
from .continuous_grid_normal import SOURCE_DEPENDENCIES, _digest, _dependencies
from .continuous_grid_candidate import EXTRA_DEPENDENCIES
from .current_grid_step import PrescribedDcPower, _owned, _Owned
from . import common_request_adapter as mapping_api
from . import reference_grid as reference
from . import reference_selector as reference_selection
from . import actual_dispatch_selector as dispatch


CONTRACT = 'common_hour_fixed_mapping_atomic_business_actual_grid_pair_v1'


def _identity(*items):
    return _digest(_plain(items))


def _implementation():
    if type(CONTRACT) is not str or CONTRACT != 'common_hour_fixed_mapping_atomic_business_actual_grid_pair_v1':
        raise ValueError('hour transaction contract drift')
    names = set(SOURCE_DEPENDENCIES) | set(EXTRA_DEPENDENCIES) | set(IMPLEMENTATION) | {
        'src/rq2_joint_deliverability_boundary_v1/'+name+'.py' for name in (
            'hourly_transaction', 'common_request_adapter', 'reference_grid', 'reference_selector',
            'actual_dispatch_selector', 'current_grid_step', 'grid_information', 'event_disclosure')}
    root = Path(__file__).resolve().parents[2]
    return _identity(CONTRACT, tuple((n, sha256((root/n).read_bytes()).hexdigest()) for n in sorted(names)), _dependencies())


@dataclass(frozen=True, init=False)
class CommonHourCursor(_Owned):
    origin_identity: str
    implementation_identity: str
    mapping: mapping_api.CommonRequestMapping
    reference_policy_identity: str
    source_audit_origin: mapping_api.RequestSourceAudit
    reference_state: object
    source_anchor: BoundaryAnchor
    last_publication_identity: str | None
    halted: bool

    @property
    def identity(self):
        return _identity(self)


@dataclass(frozen=True, init=False)
class CommonHourPublication(_Owned):
    common_origin_identity: str
    previous_publication_identity: str | None
    implementation_identity: str
    info: object
    disclosure: object
    reference_result: reference_selection.ReferenceSelectionResult
    mapping_result: mapping_api.CommonRequestResult
    business_current: CapacityObservation
    exposure_id: str

    @property
    def identity(self):
        return _identity(self)


@dataclass(frozen=True, init=False)
class CommonHourAttempt(_Owned):
    before_identity: str
    reference_result: reference_selection.ReferenceSelectionResult
    mapping_result: mapping_api.CommonRequestResult
    publication: CommonHourPublication | None
    cursor: CommonHourCursor
    status: str
    error: str | None


def _anchor(hour):
    return BoundaryAnchor(**{f.name: getattr(hour, f.name) for f in fields(BoundaryAnchor)})


def initialize_common_hours(info, disclosure, reference_origin, source_hour, mapping, source_audit, *,
                            reference_selector, solver_specification, budget):
    if type(reference_origin) is not reference.ReferenceGridOrigin:
        raise ValueError('common episode requires declared reference origin')
    if type(source_hour) is not ContinuationHour or type(source_audit) is not mapping_api.RequestSourceAudit:
        raise ValueError('typed common source hour and owned audit binding required')
    if type(mapping) is not mapping_api.CommonRequestMapping:
        raise ValueError('typed common mapping required')
    mapping.__post_init__()
    source_hour.__post_init__()
    reference.reference_input_identity(info, disclosure, reference_origin)
    if (source_audit.current_visible_identity != info.visible_identity
            or source_audit.source_hour != info.current.source_hour
            or (source_hour.split, source_hour.power_outage_seed) != (source_audit.split, source_audit.outage_seed)
            or source_hour.power_source_hour != info.current.source_hour
            or source_hour.workload_normalization_sha256 != mapping.workload_normalization_sha256
            or source_hour.grid_request != 0 or (source_hour.arm_id, source_hour.track_id) != (JOINT, 'shared')
            or Q(str(source_hour.workload_occupancy))*Q(mapping.normalized_unit_mw) != Q(str(info.current.dc_baseline_mw))):
        raise ValueError('common episode source/mapping mismatch')
    if source_hour.workload_source_hour < 1:
        raise ValueError('explicit previous workload source hour required')
    reference_selection._admit(reference_selector, solver_specification, budget, len(info.network.units)+2)
    policy = reference_selection._policy_identity(reference_selector, solver_specification, budget)
    previous = BoundaryAnchor(**dict(vars(_anchor(source_hour)),
        power_source_hour=source_hour.power_source_hour-1, workload_source_hour=source_hour.workload_source_hour-1))
    implementation = _implementation()
    origin = _identity(implementation, reference_origin, previous, mapping, policy, source_audit)
    return _owned(CommonHourCursor, origin_identity=origin, implementation_identity=implementation,
        mapping=mapping, reference_policy_identity=policy, source_audit_origin=source_audit,
        reference_state=reference_origin, source_anchor=previous, last_publication_identity=None, halted=False)


def publish_common_hour(before, info, disclosure, selected, source_hour, source_audit, *, limits, due_hour, available_flexibility):
    if type(before) is not CommonHourCursor or before.halted:
        raise ValueError('active owned common-hour cursor required')
    if before.implementation_identity != _implementation():
        raise ValueError('common-hour implementation drift')
    _validate_next_identity(before.source_anchor, source_hour)
    audit_origin = before.source_audit_origin
    if (type(source_audit) is not mapping_api.RequestSourceAudit
            or (source_audit.normal_input_identity, source_audit.prepared_audit_identity, source_audit.split, source_audit.outage_seed)
            != (audit_origin.normal_input_identity, audit_origin.prepared_audit_identity, audit_origin.split, audit_origin.outage_seed)):
        raise ValueError('common-hour source audit changed within episode')
    if type(selected) is not reference_selection.ReferenceSelectionResult or selected.selector_policy_identity != before.reference_policy_identity:
        raise ValueError('common-hour reference policy changed')
    identity = mapping_api.common_request_input_identity(info, disclosure, before.reference_state,
        selected, source_hour, before.mapping, source_audit)
    mapped = mapping_api.adapt_common_request(info, disclosure, before.reference_state,
        selected, source_hour, before.mapping, source_audit, expected_identity=identity)
    publication = None
    current = None
    status, error = 'request_unresolved', ';'.join(mapped.errors) or None
    if mapped.mapped_hour is not None:
        status = 'common_input_rejected'
        try:
            if type(limits) is not HourlyLimits:
                raise ValueError('typed current business limits required')
            limits.__post_init__()
            current = CapacityObservation(CurrentObservation(mapped.mapped_hour, limits, due_hour), available_flexibility)
        except (ValueError, OverflowError) as exc:
            error = str(exc)
    if before.implementation_identity != _implementation():
        raise ValueError('common-hour implementation changed during attempt')
    if current is not None:
        exposure = _identity(before.origin_identity, before.last_publication_identity, info.current.source_hour, mapped.identity, current)
        publication = _owned(CommonHourPublication, common_origin_identity=before.origin_identity,
            previous_publication_identity=before.last_publication_identity, implementation_identity=before.implementation_identity,
            info=info, disclosure=disclosure, reference_result=selected, mapping_result=mapped, business_current=current, exposure_id=exposure)
        status, error = 'published', None
    cursor = _owned(CommonHourCursor, origin_identity=before.origin_identity,
        implementation_identity=before.implementation_identity, mapping=before.mapping,
        reference_policy_identity=before.reference_policy_identity, source_audit_origin=audit_origin,
        reference_state=selected.next_reference_state if publication is not None else before.reference_state,
        source_anchor=_anchor(source_hour) if publication is not None else before.source_anchor,
        last_publication_identity=publication.identity if publication is not None else before.last_publication_identity,
        halted=publication is None)
    return _owned(CommonHourAttempt, before_identity=before.identity, reference_result=selected,
        mapping_result=mapped, publication=publication, cursor=cursor, status=status, error=error)


@dataclass(frozen=True, init=False)
class ArmHourCursor(_Owned):
    origin_identity: str
    implementation_identity: str
    common_origin_identity: str
    mapping: mapping_api.CommonRequestMapping
    business_policy_identity: str
    dispatch_selector: dispatch.ActualDispatchSpec
    solver_specification: object
    budget: object
    dispatch_policy_identity: str
    business: CapacityPolicyCursor
    grid: object
    last_publication_identity: str | None
    halted: bool

    @property
    def identity(self):
        return _identity(self)


@dataclass(frozen=True, init=False)
class ArmHourResult(_Owned):
    before_identity: str
    publication_identity: str
    exposure_id: str
    arm_id: str
    business_candidate: CapacityPolicyCursor | None
    prescribed_power: PrescribedDcPower | None
    dispatch_result: dispatch.ActualDispatchResult | None
    cursor: ArmHourCursor
    published_pair: tuple | None
    status: str
    error: str | None
    grid_service_applicable: bool
    candidate_grid_service_failure: bool | None
    grid_service_failure: bool | None
    physical_network_check_applicable: bool
    capacity_certificate: None
    causal_certificate: None
    formal_result: bool
    security_certified: bool

    @property
    def identity(self):
        return _identity(self)


def initialize_arm_hours(common, business, grid_origin, *, selector, solver_specification, budget):
    if type(common) is not CommonHourCursor or common.halted or common.last_publication_identity is not None:
        raise ValueError('unconsumed common episode origin required')
    if type(business) is not CapacityPolicyCursor or business.records:
        raise ValueError('canonical zero-history business origin required')
    business.__post_init__()
    if type(grid_origin) is not dispatch.ActualDispatchOrigin:
        raise ValueError('owned actual dispatch origin required')
    physical = dispatch._physical(grid_origin)
    reference_physical = reference._physical(common.reference_state)
    anchor = business.execution.tracks[0][1].physical.anchor
    if (anchor != common.source_anchor or physical.source_hour != anchor.power_source_hour
            or physical.network_identity != reference_physical.network_identity
            or physical.allowed_plan_identity != reference_physical.allowed_plan_identity
            or physical.disclosure != reference_physical.disclosure):
        raise ValueError('business/actual/reference origin source or network mismatch')
    dispatch._admit(selector, solver_specification, budget, len(physical.generation_mw)+1)
    policy = dispatch._policy_identity(selector, solver_specification, budget)
    if grid_origin.selector_policy_identity != policy or common.implementation_identity != _implementation():
        raise ValueError('initial transaction dispatch policy or implementation mismatch')
    origin = _identity(common.origin_identity, business, grid_origin, policy)
    return _owned(ArmHourCursor, origin_identity=origin, implementation_identity=common.implementation_identity,
        common_origin_identity=common.origin_identity, mapping=common.mapping, business_policy_identity=business.policy_id,
        dispatch_selector=selector, solver_specification=solver_specification, budget=budget,
        dispatch_policy_identity=policy, business=business, grid=grid_origin, last_publication_identity=None, halted=False)


def advance_arm_hour(before, publication):
    if type(before) is not ArmHourCursor or before.halted:
        raise ValueError('active owned arm-hour cursor required; halted arm cannot consume suffix')
    if type(publication) is not CommonHourPublication:
        raise ValueError('owned common-hour publication required')
    if (before.implementation_identity != _implementation()
            or publication.implementation_identity != before.implementation_identity
            or publication.common_origin_identity != before.common_origin_identity
            or publication.previous_publication_identity != before.last_publication_identity
            or publication.mapping_result.mapping != before.mapping
            or before.business.policy_id != before.business_policy_identity
            or before.grid.selector_policy_identity != before.dispatch_policy_identity
            or dispatch._policy_identity(before.dispatch_selector, before.solver_specification, before.budget) != before.dispatch_policy_identity):
        raise ValueError('transaction source chain, mapping, policy or implementation drift')
    hour = publication.mapping_result.mapped_hour
    _validate_next_identity(before.business.execution.tracks[0][1].physical.anchor, hour)
    physical = dispatch._physical(before.grid)
    if (physical.source_hour+1 != hour.power_source_hour or publication.disclosure.before != physical.disclosure
            or publication.info.current.source_hour != hour.power_source_hour):
        raise ValueError('transaction actual grid clock/disclosure mismatch')
    candidate = power = result = None
    status, error = 'input_rejected', None
    applicable = before.business.spec.arm_id != CFE
    candidate_failure = None
    try:
        current = publication.business_current
        if type(current) is not CapacityObservation or current.observation.hour != hour:
            raise ValueError('business observation differs from common publication')
        candidate = advance_capacity_policy(before.business, current)
        record = candidate.records[-1]
        candidate_failure = record.response.grid_service_failure if record.response is not None and applicable else None
        status = 'business_rejected'
        error = record.error
        if record.committed:
            action = record.response.action
            if record.current.observation.hour != hour:
                raise ValueError('business candidate differs from common mapped hour')
            expected = Q(str(hour.workload_occupancy))-action.grid_served-action.cfe_served+action.recovery
            if action.actual_service_power != expected:
                raise ValueError('business actual power balance mismatch')
            mw = action.actual_service_power*Q(before.mapping.normalized_unit_mw)
            power = PrescribedDcPower(hour.power_source_hour, str(mw.numerator), str(mw.denominator), 'mechanism_assumption')
            status = 'network_input_rejected'
            network_input = dispatch.dispatch_input_identity(publication.info, publication.disclosure, before.grid, power)
            status = 'dispatch_execution_unresolved'
            result = dispatch.select_actual_dispatch(publication.info, publication.disclosure, before.grid, power,
                expected_identity=network_input, selector=before.dispatch_selector,
                solver_specification=before.solver_specification, budget=before.budget)
            status, error = 'physical_network_unresolved', ';'.join(result.errors) or None
            if result.status == 'selected_numerical_dispatch':
                if (result.prescribed_power != power or result.next_dispatch_state is None
                        or result.next_dispatch_state.previous_state_identity != before.grid.identity):
                    raise ValueError('selected dispatch power or predecessor mismatch')
                status, error = 'committed', None
    except (ValueError, OverflowError) as exc:
        error = str(exc)
    if before.implementation_identity != _implementation():
        raise ValueError('transaction implementation changed during attempt')
    committed = status == 'committed' and error is None
    cursor = _owned(ArmHourCursor, **dict(vars(before), business=candidate if committed else before.business,
        grid=result.next_dispatch_state if committed else before.grid,
        last_publication_identity=publication.identity if committed else before.last_publication_identity,
        halted=not committed))
    return _owned(ArmHourResult, before_identity=before.identity, publication_identity=publication.identity,
        exposure_id=publication.exposure_id, arm_id=before.business.spec.arm_id,
        business_candidate=candidate, prescribed_power=power, dispatch_result=result, cursor=cursor,
        published_pair=(cursor.business, cursor.grid) if committed else None, status=status, error=error,
        grid_service_applicable=applicable, candidate_grid_service_failure=candidate_failure,
        grid_service_failure=candidate_failure if committed else None, physical_network_check_applicable=True,
        capacity_certificate=None, causal_certificate=None, formal_result=False, security_certified=False)
