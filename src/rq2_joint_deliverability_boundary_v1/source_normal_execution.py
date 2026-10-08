"""Recheck a pinned public pair/normal binding around one development solve."""
from copy import deepcopy
from dataclasses import dataclass
from hashlib import sha256
import json
from pathlib import Path
from time import perf_counter

from . import normal_execution as kernel, pair_normal_binding as binding
from .source_normal import SourceNormalAssembly
from .source_pair import PairDeclaration
from . import source_window


CONTRACT = 'draft_source_bound_single_normal_execution_v1'
ADAPTER_DEPENDENCIES = tuple('src/rq2_joint_deliverability_boundary_v1/'+n+'.py' for n in (
    'source_normal_execution', 'source_normal', 'source_pair', 'source_window', 'continuation_audit',
    'pair_normal_binding', 'power_normal_binding', 'workload_projection', 'boundary', 'common_request_adapter',
    'actual_actions', 'aggregate_response', 'capacity_policy', 'causal_policy', 'current_grid_step',
    'debt_cohorts', 'event_disclosure', 'four_arm_replay', 'grid_information', 'multiday',
    'prefix_handoff', 'reference_grid', 'reference_selector')) + (
    'src/models/economic_temporal_stochastic.py', 'src/models/rq2_joint_deliverability.py',
    'src/scenarios/rq2_joint_deliverability.py')


def source_execution_identity(expected_binding_identity, expected_normal_execution_identity, declaration,
                              *, expected_assembly_identity, expected_pair_identity):
    """Candidate pin; binding and kernel pins must be retained independently."""
    kernel._pin(expected_binding_identity)
    kernel._pin(expected_normal_execution_identity)
    kernel._pin(expected_assembly_identity)
    kernel._pin(expected_pair_identity)
    if type(declaration) is not PairDeclaration:
        raise ValueError('typed source pair declaration required')
    declaration.__post_init__()
    if CONTRACT != 'draft_source_bound_single_normal_execution_v1':
        raise ValueError('source normal execution contract drift')
    root = Path(__file__).resolve().parents[2]
    sources = tuple((name, sha256((root/name).read_bytes()).hexdigest()) for name in ADAPTER_DEPENDENCIES)
    return kernel._digest(CONTRACT, expected_binding_identity, expected_normal_execution_identity,
        expected_assembly_identity, expected_pair_identity, declaration, sources)


@dataclass(frozen=True, init=False)
class SourceNormalExecutionResult(kernel._Owned):
    contract: str
    execution_identity: str
    expected_binding_identity: str
    binding_before_json: str
    binding_after_json: str | None
    normal_result: kernel.NormalExecutionResult | None
    solver_calls: int | None
    call_count_complete: bool
    source_correspondence_verified: bool
    source_bound_normal_accepted: bool
    status: str
    errors: tuple[str, ...]
    observed_wrapper_seconds: float
    hard_resource_limits_enforced: bool
    durable_invocation_tracking: bool
    registered_coupling: bool
    observed_power_mapping: bool
    formal_result: bool
    security_certified: bool

    @property
    def identity(self):
        return kernel._digest(self)


def _json(report):
    return json.dumps(report, sort_keys=True, separators=(',', ':'), allow_nan=False)


def _consistent_acceptance(result):
    raw, witness = result.normal, result.witness
    return (result.normal_accepted is True and result.status == 'accepted_normal' and result.errors == ()
        and type(result.solver_calls) is int and result.solver_calls == 1 and result.call_count_complete is True
        and type(raw) is kernel.native.GridSolveEvidence and raw.calls == 1
        and raw.optimal is True and raw.assignment_valid is True and raw.errors == ()
        and type(witness) is kernel.NormalAssignmentWitness and witness.errors == ()
        and witness.input_identity == result.input_identity and witness.terminal_carry is not None
        and witness.assignment_identity == kernel._digest(dict(raw.loaded_values))
        and all(getattr(result, name) is False for name in ('hard_resource_limits_enforced',
            'durable_invocation_tracking', 'public_source_binding_verified', 'formal_result', 'security_certified'))
        and result.causal_certificate is None and result.infeasibility_certificate is None)


def run_source_normal(assembly, upstream_root, declaration, *, expected_assembly_identity,
        expected_pair_identity, expected_binding_identity, expected_input_identity,
        expected_normal_execution_identity, expected_source_execution_identity,
        expected_scale, specification, budget, config_path=source_window.audit.DEFAULT_CONFIG):
    """No source inference, retries, durable journal, current input or publication.

    Source checks before/after execution detect ordinary drift, not hostile ABA.
    The kernel budget excludes this wrapper's source rebuild and serialization.
    """
    started = perf_counter()
    for pin in (expected_assembly_identity, expected_pair_identity, expected_binding_identity,
                expected_input_identity, expected_normal_execution_identity, expected_source_execution_identity):
        kernel._pin(pin)
    if type(assembly) is not SourceNormalAssembly:
        raise ValueError('typed complete source normal assembly required')
    owned, declared = deepcopy(assembly), deepcopy(declaration)
    if (owned.assembly_identity != expected_assembly_identity
            or owned.normal_identity != expected_input_identity):
        raise ValueError('external assembly or normal identity mismatch')
    root, config = Path(upstream_root).resolve(), Path(config_path).resolve()
    kernel._validate(specification, budget, expected_scale)

    def implementation():
        if source_execution_identity(expected_binding_identity, expected_normal_execution_identity,
                declared, expected_assembly_identity=expected_assembly_identity,
                expected_pair_identity=expected_pair_identity) != expected_source_execution_identity:
            raise ValueError('source execution identity drift')
        if kernel.normal_execution_identity(expected_input_identity, expected_scale,
                specification, budget) != expected_normal_execution_identity:
            raise ValueError('normal execution identity drift')

    def rebuild():
        implementation()
        report = binding.bind_pair_normal(owned, root, declared,
            expected_assembly_identity=expected_assembly_identity,
            expected_pair_identity=expected_pair_identity, config_path=config)
        if (report['binding_identity'] != expected_binding_identity
                or report['normal_assembly_identity'] != expected_assembly_identity
                or report['pair_identity'] != expected_pair_identity
                or report['normal_input_identity'] != expected_input_identity
                or kernel.normal_input_identity(owned.inputs) != expected_input_identity):
            raise ValueError('external binding or normal identity mismatch')
        payload = dict(report)
        payload.pop('binding_identity')
        if source_window._hash(payload) != expected_binding_identity:
            raise ValueError('binding content differs from external identity')
        implementation()
        return _json(report)

    before = rebuild()
    result = None
    errors = []
    interrupted = False
    try:
        returned = kernel.run_normal_only(owned.inputs, expected_input_identity=expected_input_identity,
            expected_execution_identity=expected_normal_execution_identity, expected_scale=expected_scale,
            specification=specification, budget=budget)
        if type(returned) is not kernel.NormalExecutionResult:
            raise ValueError('owned normal kernel result required')
        result = returned
        if (result.input_identity != expected_input_identity
                or result.execution_identity != expected_normal_execution_identity
                or result.scale != expected_scale or result.specification != specification or result.budget != budget):
            errors.append('normal_result_binding_mismatch')
        if result.normal_accepted is not False and not _consistent_acceptance(result):
            errors.append('normal_result_acceptance_inconsistent')
    except BaseException as error:
        # No complete inner result: do not infer zero calls from an exception.
        interrupted = not isinstance(error, Exception)
        errors.append(('normal_return_missing:' if result is None else 'normal_result_validation:')
            +type(error).__name__+':'+str(error))
    after = None
    try:
        after = rebuild()
        if after != before:
            errors.append('source_binding_changed')
    except BaseException as error:
        interrupted = interrupted or not isinstance(error, Exception)
        errors.append('post_source:'+type(error).__name__+':'+str(error))
    correspondence = after is not None and before == after
    accepted = correspondence and not errors and result is not None and result.normal_accepted is True
    return kernel.native._make(SourceNormalExecutionResult, contract=CONTRACT,
        execution_identity=expected_source_execution_identity, expected_binding_identity=expected_binding_identity,
        binding_before_json=before, binding_after_json=after, normal_result=result,
        solver_calls=None if result is None else result.solver_calls,
        call_count_complete=result is not None and result.call_count_complete,
        source_correspondence_verified=correspondence, source_bound_normal_accepted=accepted,
        status='accepted_source_bound_normal' if accepted else ('interrupted_source_bound_normal'
            if interrupted or (result is not None and result.status == 'interrupted_normal')
            else 'unresolved_source_bound_normal'), errors=tuple(errors),
        observed_wrapper_seconds=perf_counter()-started, hard_resource_limits_enforced=False,
        durable_invocation_tracking=False, registered_coupling=False, observed_power_mapping=False,
        formal_result=False, security_certified=False)
