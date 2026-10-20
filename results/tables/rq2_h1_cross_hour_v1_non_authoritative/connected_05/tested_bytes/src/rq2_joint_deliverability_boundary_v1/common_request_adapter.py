"""Lossless common reference MW to the existing exact business request path."""
from dataclasses import dataclass, replace
from fractions import Fraction as Q
from hashlib import sha256
from pathlib import Path
from re import fullmatch

from . import boundary
from .boundary import ContinuationHour
from .four_arm_replay import JOINT, _effective_call
from .prefix_handoff import IMPLEMENTATION, _plain
from .continuous_grid_normal import _digest, normal_input_identity
from .grid_information import PreparedNormalInformation, current_grid_information
from .current_grid_step import _owned, _Owned
from .reference_grid import reference_input_identity
from . import reference_selector as selection


CONTRACT = 'common_reference_exact_mw_business_request_mapping_v1'


def _hash(item):
    if type(item) is not str or len(item) != 64 or any(c not in '0123456789abcdef' for c in item):
        raise ValueError('canonical lowercase SHA256 mapping identity required')


@dataclass(frozen=True, init=False)
class RequestSourceAudit(_Owned):
    normal_input_identity: str
    prepared_audit_identity: str
    current_visible_identity: str
    split: str
    outage_seed: int
    source_hour: int


def bind_request_source(inputs, prepared, info, *, expected_normal_identity, expected_prepared_identity):
    """Audit-side linkage; full source/seed never enters reference selection."""
    _hash(expected_normal_identity)
    _hash(expected_prepared_identity)
    if (type(prepared) is not PreparedNormalInformation
            or normal_input_identity(inputs) != expected_normal_identity
            or prepared.source_input_identity != expected_normal_identity
            or current_grid_information(prepared, info.current, expected_audit_identity=expected_prepared_identity) != info):
        raise ValueError('normal source/prepared/current audit linkage mismatch')
    identity = inputs.carry.identity
    return _owned(RequestSourceAudit, normal_input_identity=expected_normal_identity,
        prepared_audit_identity=expected_prepared_identity, current_visible_identity=info.visible_identity,
        split=identity.split, outage_seed=identity.outage_seed, source_hour=info.current.source_hour)


@dataclass(frozen=True)
class CommonRequestMapping:
    normalized_unit_mw: str
    workload_normalization_sha256: str
    power_mapping: str
    source_pairing: str
    parameter_role: str

    def __post_init__(self):
        _hash(self.workload_normalization_sha256)
        if (type(self.normalized_unit_mw) is not str
                or fullmatch(r'(?:0|[1-9][0-9]*)(?:\.[0-9]*[1-9])?', self.normalized_unit_mw) is None
                or Q(self.normalized_unit_mw) <= 0):
            raise ValueError('positive canonical decimal string MW unit required')
        for name, expected in (
                ('power_mapping', 'linear_workload_power_no_idle_offset_v1'),
                ('source_pairing', 'declared_power_source_and_workload_pairing_mechanism_v1'),
                ('parameter_role', 'mechanism_assumption')):
            if type(getattr(self, name)) is not str or getattr(self, name) != expected:
                raise ValueError('explicit common request mapping mechanism required: '+name)


@dataclass(frozen=True, init=False)
class CommonRequestResult(_Owned):
    contract: str
    input_identity: str
    reference_result_identity: str
    source_audit: RequestSourceAudit
    mapping: CommonRequestMapping
    original_source_hour: ContinuationHour
    raw_grid_request_mw: Q | None
    normalized_grid_request: Q | None
    normalized_float_projection: float | None
    normalized_float_hex: str | None
    binary_projection_error: Q | None
    mapped_hour: ContinuationHour | None
    status: str
    errors: tuple[str, ...]
    causal_certificate: None
    capacity_certificate: None
    formal_result: bool
    security_certified: bool

    @property
    def identity(self):
        return _digest(_plain(self))


def _validate(info, disclosure, before, result, source_hour, mapping, source_audit):
    if type(CONTRACT) is not str or CONTRACT != 'common_reference_exact_mw_business_request_mapping_v1':
        raise ValueError('common request mapping contract drift')
    if type(boundary.SERVICE_TOLERANCE) is not float or boundary.SERVICE_TOLERANCE != 1e-6:
        raise ValueError('business activity threshold drift')
    if type(mapping) is not CommonRequestMapping or type(source_hour) is not ContinuationHour:
        raise ValueError('typed mapping and common business source hour required')
    mapping.__post_init__()
    source_hour.__post_init__()
    if (type(source_audit) is not RequestSourceAudit or source_audit.current_visible_identity != info.visible_identity
            or source_audit.source_hour != info.current.source_hour):
        raise ValueError('owned current source audit binding required')
    if (source_hour.split, source_hour.power_outage_seed) != (source_audit.split, source_audit.outage_seed):
        raise ValueError('business/reference split or outage seed mismatch')
    if (source_hour.arm_id, source_hour.track_id) != (JOINT, 'shared'):
        raise ValueError('common JOINT/shared source container required')
    if source_hour.grid_request != 0:
        raise ValueError('explicit empty grid request slot required; existing request cannot be overwritten')
    if source_hour.power_source_hour != info.current.source_hour:
        raise ValueError('common business and reference source-hour mismatch')
    if source_hour.workload_normalization_sha256 != mapping.workload_normalization_sha256:
        raise ValueError('business normalization differs from declared MW unit source')
    if Q(str(source_hour.workload_occupancy))*Q(mapping.normalized_unit_mw) != Q(str(info.current.dc_baseline_mw)):
        raise ValueError('reference baseline differs from exact mapped business baseline')
    if type(result) is not selection.ReferenceSelectionResult:
        raise ValueError('owned reference selector result required')
    if result.input_identity != reference_input_identity(info, disclosure, before):
        raise ValueError('reference selection belongs to different current inputs')
    selection._admit(result.selector, result.specification, result.budget, len(info.network.units)+2)
    if (result.contract != selection.CONTRACT
            or result.selector_policy_identity != selection._policy_identity(result.selector, result.specification, result.budget)):
        raise ValueError('reference selection policy or implementation drift')


def common_request_input_identity(info, disclosure, before, result, source_hour, mapping, source_audit):
    _validate(info, disclosure, before, result, source_hour, mapping, source_audit)
    root = Path(__file__).resolve().parents[2]
    sources = tuple((name, sha256((root/name).read_bytes()).hexdigest()) for name in
        (*IMPLEMENTATION, 'src/rq2_joint_deliverability_boundary_v1/common_request_adapter.py',
            'src/rq2_joint_deliverability_boundary_v1/continuous_grid_normal.py'))
    return _digest(CONTRACT, reference_input_identity(info, disclosure, before), result.identity,
        _plain(source_hour), mapping, source_audit, boundary.SERVICE_TOLERANCE, sources)


def adapt_common_request(info, disclosure, before, result, source_hour, mapping, source_audit, *, expected_identity):
    _hash(expected_identity)
    if common_request_input_identity(info, disclosure, before, result, source_hour, mapping, source_audit) != expected_identity:
        raise ValueError('common request mapping input identity mismatch')
    errors, raw, normalized, mapped, projected, projection_error = [], None, None, None, None, None
    if result.status != 'selected_numerical_reference':
        errors.append('reference_selection_unresolved')
    else:
        count = len(info.network.units)+2
        state = result.next_reference_state
        if (result.errors or len(result.stages) != count or result.planned_solver_calls != count
                or result.solver_calls != count or state is None
                or any(not s.accepted or s.errors or not s.raw_solve.optimal for s in result.stages)):
            raise ValueError('incomplete reference selection cannot provide a common request')
        final = result.stages[-1].assignment_witness
        if (final is None or not final.physical_assignment_valid
                or final.candidate_grid_request_exact != result.selected_request_exact
                or final.physical_witness.next_carry != state.physical_carry
                or state.previous_state_identity != before.identity
                or state.selector_policy_identity != result.selector_policy_identity
                or state.selection_identity != _digest(selection.CONTRACT, result.selector_policy_identity,
                    result.input_identity, result.stages)):
            raise ValueError('reference selected request or state evidence mismatch')
        raw = Q(int(result.selected_request_exact[0]), int(result.selected_request_exact[1]))
        if raw < 0 or raw > Q(str(info.current.dc_baseline_mw)):
            raise ValueError('selected request outside reference baseline domain')
        normalized = raw/Q(mapping.normalized_unit_mw)
        projected = float(normalized)
        projection_error = abs(Q.from_float(projected)-normalized)
        # Preserve the exact rational through the already rational-capable
        # business path. The legacy activity decision still needs a check.
        if raw > 0 and (normalized <= Q(str(boundary.SERVICE_TOLERANCE))
                or _effective_call(normalized, 0.) != normalized):
            errors.append('positive_grid_request_below_business_resolution')
        elif (_effective_call(normalized, 0.)+_effective_call(0., source_hour.cfe_request)
                != _effective_call(normalized, source_hour.cfe_request)):
            errors.append('separate_and_shared_request_activity_mismatch')
        else:
            mapped = replace(source_hour, grid_request=normalized)
    if common_request_input_identity(info, disclosure, before, result, source_hour, mapping, source_audit) != expected_identity:
        raise ValueError('common request mapping inputs changed during adaptation')
    return _owned(CommonRequestResult, contract=CONTRACT, input_identity=expected_identity,
        reference_result_identity=result.identity, source_audit=source_audit, mapping=mapping, original_source_hour=source_hour,
        raw_grid_request_mw=raw, normalized_grid_request=normalized, mapped_hour=mapped,
        normalized_float_projection=projected, normalized_float_hex=None if projected is None else projected.hex(),
        binary_projection_error=projection_error,
        status='mapped_exact_common_request' if mapped is not None else 'unresolved', errors=tuple(errors),
        causal_certificate=None, capacity_certificate=None, formal_result=False, security_certified=False)
