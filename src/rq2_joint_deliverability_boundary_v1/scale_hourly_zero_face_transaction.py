"""Versioned business/grid transactions consuming source-bound mixed selector records."""
from dataclasses import dataclass, replace
from fractions import Fraction as Q
from hashlib import sha256
from pathlib import Path

from . import scale_selector_zero_face_archive as replay, hourly_transaction as legacy
from . import scale_selector_zero_face as scale, scale_selector_zero_face_store as store
from . import common_request_adapter as mapping_api
from .four_arm_replay import NETWORK, CFE, JOINT, B6
from .boundary import ContinuationHour, _validate_next_identity
from .current_grid_step import _Owned, _owned, PrescribedDcPower

ARMS = (NETWORK, CFE, JOINT, B6)
SCHEMA = 'draft_replayed_mixed_hour_transaction_v1'


def _implementation():
    return legacy._identity(SCHEMA, legacy._implementation(),
        tuple((m.__name__, sha256(Path(m.__file__).read_bytes()).hexdigest())
              for m in (replay, scale, store)), replay.implementation_identity(),
        sha256(Path(__file__).read_bytes()).hexdigest())


@dataclass(frozen=True, init=False)
class CommonPublication(_Owned):
    implementation: str
    previous_identity: str | None
    reference_request: object
    reference_result: object
    record_sha256: str
    store_binding_identity: str
    source_hour: object
    source_audit: object
    mapping: object
    current: object

    @property
    def identity(self): return legacy._identity(self)


def publish_common_record(data, request, source_hour, mapping, source_audit, *,
                          expected_sha256, expected_binding_identity, expected_replay_identity, max_record_bytes,
                          limits, due_hour, available_flexibility, previous=None):
    impl = _implementation()
    if type(request) is not store.MixedSelectorRequest or request.budget.role != 'reference':
        raise ValueError('reference role required')
    report, selected = replay._verify(data, request, expected_sha256=expected_sha256,
        expected_binding_identity=expected_binding_identity,
        expected_implementation_identity=expected_replay_identity, max_record_bytes=max_record_bytes)
    if not report['selection_accepted'] or selected is None:
        raise ValueError('replayed complete reference required')
    info = request.info
    if type(mapping) is not mapping_api.CommonRequestMapping or type(source_hour) is not ContinuationHour:
        raise ValueError('typed common source/mapping required')
    mapping.__post_init__()
    source_hour.__post_init__()
    if (type(source_audit) is not mapping_api.RequestSourceAudit
            or source_audit.current_visible_identity != info.visible_identity
            or source_audit.source_hour != info.current.source_hour
            or (source_hour.split, source_hour.power_outage_seed) != (source_audit.split, source_audit.outage_seed)
            or (source_hour.arm_id, source_hour.track_id) != (JOINT, 'shared')
            or source_hour.grid_request != 0 or source_hour.power_source_hour != info.current.source_hour
            or source_hour.workload_normalization_sha256 != mapping.workload_normalization_sha256
            or Q(str(source_hour.workload_occupancy))*Q(mapping.normalized_unit_mw) != Q(str(info.current.dc_baseline_mw))):
        raise ValueError('source/audit/mapping mismatch')
    if previous is not None:
        if type(previous) is not CommonPublication or previous.implementation != impl:
            raise ValueError('owned previous common publication required')
        _validate_next_identity(legacy._anchor(previous.source_hour), source_hour)
        old = previous.source_audit
        if (request.before != previous.reference_result.next_state or mapping != previous.mapping
                or selected.policy_identity != previous.reference_result.policy_identity
                or (source_audit.normal_input_identity, source_audit.prepared_audit_identity,
                    source_audit.split, source_audit.outage_seed)
                   != (old.normal_input_identity, old.prepared_audit_identity, old.split, old.outage_seed)):
            raise ValueError('common predecessor/source policy mismatch')
    elif type(request.before) is not scale.reference.ReferenceGridOrigin:
        raise ValueError('initial common publication requires reference origin')
    raw = Q(*map(int, selected.selected_request_exact))
    if not 0 <= raw <= Q(str(info.current.dc_baseline_mw)):
        raise ValueError('reference request outside baseline')
    normalized = raw/Q(mapping.normalized_unit_mw)
    if raw > 0 and (normalized <= Q(str(mapping_api.boundary.SERVICE_TOLERANCE))
            or mapping_api._effective_call(normalized, 0.) != normalized):
        raise ValueError('positive request below business resolution')
    if (mapping_api._effective_call(normalized, 0.)+mapping_api._effective_call(0., source_hour.cfe_request)
            != mapping_api._effective_call(normalized, source_hour.cfe_request)):
        raise ValueError('separate/shared activity mismatch')
    current = legacy.CapacityObservation(legacy.CurrentObservation(
        replace(source_hour, grid_request=normalized), limits, due_hour), available_flexibility)
    if _implementation() != impl:
        raise ValueError('transaction implementation drift')
    return _owned(CommonPublication, implementation=impl,
        previous_identity=None if previous is None else previous.identity,
        reference_request=request, reference_result=selected, record_sha256=expected_sha256,
        store_binding_identity=expected_binding_identity,
        source_hour=source_hour, source_audit=source_audit, mapping=mapping, current=current)


@dataclass(frozen=True, init=False)
class ArmCursor(_Owned):
    implementation: str
    origin_identity: str
    business_policy_identity: str
    business: object
    grid: object
    mapping: object
    last_publication_identity: str | None
    halted: bool

    @property
    def identity(self): return legacy._identity(self)


def initialize_arm(publication, business, grid_origin):
    if (type(publication) is not CommonPublication or publication.previous_identity is not None
            or publication.implementation != _implementation()
            or type(business) is not legacy.CapacityPolicyCursor or business.records
            or type(grid_origin) is not scale.actual.ActualDispatchOrigin):
        raise ValueError('unconsumed typed origins required')
    business.__post_init__()
    anchor = business.execution.tracks[0][1].physical.anchor
    _validate_next_identity(anchor, publication.source_hour)
    physical = scale.actual._physical(grid_origin)
    reference = legacy.reference._physical(publication.reference_request.before)
    if (business.spec.arm_id not in ARMS or physical.source_hour != anchor.power_source_hour
            or physical.network_identity != reference.network_identity
            or physical.allowed_plan_identity != reference.allowed_plan_identity
            or physical.disclosure != reference.disclosure):
        raise ValueError('arm origin clock/network mismatch')
    origin = legacy._identity(publication.reference_request.before.identity, business, grid_origin, publication.mapping)
    return _owned(ArmCursor, implementation=publication.implementation, origin_identity=origin,
        business_policy_identity=business.policy_id, business=business, grid=grid_origin,
        mapping=publication.mapping, last_publication_identity=None, halted=False)


@dataclass(frozen=True, init=False)
class ArmProposal(_Owned):
    before: ArmCursor
    publication: CommonPublication
    business_candidate: object
    dispatch_request: object
    status: str


def prepare_arm(before, publication, *, selector, solver_specification, budget):
    if (type(before) is not ArmCursor or before.halted or type(publication) is not CommonPublication
            or before.implementation != _implementation() or publication.implementation != before.implementation
            or before.last_publication_identity != publication.previous_identity or before.mapping != publication.mapping
            or before.business.policy_id != before.business_policy_identity):
        raise ValueError('active matching arm/publication chain required')
    arm = before.business.spec.arm_id
    if arm not in ARMS or budget.role != 'actual:'+str(ARMS.index(arm)):
        raise ValueError('actual role differs from canonical business arm')
    info, disclosure = publication.reference_request.info, publication.reference_request.disclosure
    policy = scale.policy_identity(selector, solver_specification, budget)
    if before.grid.selector_policy_identity != policy:
        raise ValueError('fixed actual policy changed')
    physical = scale.actual._physical(before.grid)
    hour = publication.current.observation.hour
    _validate_next_identity(before.business.execution.tracks[0][1].physical.anchor, hour)
    if physical.source_hour+1 != hour.power_source_hour or disclosure.before != physical.disclosure:
        raise ValueError('actual clock/disclosure mismatch')
    scale._admit(selector, solver_specification, budget, len(info.network.units)+1)
    if budget.source_hour != info.current.source_hour or budget.generator_uids != tuple(g.uid for g in info.network.units):
        raise ValueError('actual reservation hour/UID mismatch')
    candidate = legacy.advance_capacity_policy(before.business, publication.current)
    record = candidate.records[-1]
    request = None
    if record.committed:
        action = record.response.action
        expected = Q(str(hour.workload_occupancy))-action.grid_served-action.cfe_served+action.recovery
        if action.actual_service_power != expected:
            raise ValueError('business service balance mismatch')
        mw = expected*Q(before.mapping.normalized_unit_mw)
        power = PrescribedDcPower(hour.power_source_hour, str(mw.numerator), str(mw.denominator), 'mechanism_assumption')
        identity = scale.actual.dispatch_input_identity(info, disclosure, before.grid, power)
        request = store.MixedSelectorRequest(info, disclosure, before.grid, identity, selector,
            solver_specification, budget, policy, power)
    if _implementation() != before.implementation:
        raise ValueError('transaction implementation changed during preparation')
    return _owned(ArmProposal, before=before, publication=publication, business_candidate=candidate,
        dispatch_request=request, status='dispatch_required' if request else 'business_rejected')


def finish_arm(proposal, data=None, *, expected_sha256=None, expected_binding_identity=None,
               expected_replay_identity=None, max_record_bytes=None):
    if type(proposal) is not ArmProposal or proposal.before.implementation != _implementation():
        raise ValueError('owned current arm proposal required')
    before, publication = proposal.before, proposal.publication
    selected = None
    status = proposal.status
    if proposal.dispatch_request is not None:
        report, selected = replay._verify(data, proposal.dispatch_request, expected_sha256=expected_sha256,
            expected_binding_identity=expected_binding_identity,
            expected_implementation_identity=expected_replay_identity, max_record_bytes=max_record_bytes)
        status = 'committed' if report['selection_accepted'] else 'physical_network_unresolved'
    elif data is not None:
        raise ValueError('business rejection cannot consume dispatch evidence')
    committed = status == 'committed'
    cursor = _owned(ArmCursor, implementation=before.implementation, origin_identity=before.origin_identity,
        business_policy_identity=before.business_policy_identity,
        business=proposal.business_candidate if committed else before.business,
        grid=selected.next_state if committed else before.grid, mapping=before.mapping,
        last_publication_identity=publication.identity if committed else before.last_publication_identity,
        halted=not committed)
    if _implementation() != before.implementation:
        raise ValueError('transaction implementation changed')
    applicable = before.business.spec.arm_id != CFE
    response = proposal.business_candidate.records[-1].response
    candidate_failure = response.grid_service_failure if response is not None and applicable else None
    return dict(status=status, cursor=cursor, published_pair=(cursor.business, cursor.grid) if committed else None,
        business_candidate=proposal.business_candidate, publication_identity=publication.identity,
        grid_service_applicable=applicable, candidate_grid_service_failure=candidate_failure,
        grid_service_failure=candidate_failure if committed else None, physical_network_check_applicable=True,
        formal_result=False, security_certified=False, executable_resume_authorized=False)
