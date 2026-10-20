"""Rebuild pinned streaming declarations before one source-bound normal call.

Synchronous development entry only; the caller must provide Job supervision.
"""
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path

from . import normal_task_inputs_stream as prepare
from . import source_normal_execution_stream_numeric as source

kernel = source.kernel
CONTRACT = 'draft_numeric_streaming_declared_normal_execution_v1'


def declared_execution_identity(request, *, expected_request_identity, expected_source_execution_identity):
    for pin in (expected_request_identity, expected_source_execution_identity):
        kernel._pin(pin)
    return kernel._digest(CONTRACT, expected_request_identity, expected_source_execution_identity,
        prepare.task_source_identity(request), sha256(Path(__file__).read_bytes()).hexdigest())


@dataclass(frozen=True, init=False)
class DeclaredNumericStreamingNormalResult(kernel._Owned):
    contract: str
    execution_identity: str
    request_identity: str
    source_result: source.NumericStreamingSourceNormalExecutionResult | None
    preparation_timings: tuple
    solver_calls: int | None
    call_count_complete: bool
    accepted: bool
    status: str
    errors: tuple[str, ...]
    mechanism_initial_state: bool
    observed_power_mapping: bool
    hard_resource_limits_enforced: bool
    durable_invocation_tracking: bool
    formal_result: bool

    @property
    def identity(self):
        return kernel._digest(self)


def run_declared_normal(request, *, expected_request_identity, expected_declared_execution_identity,
        expected_assembly_identity, expected_binding_identity, expected_source_implementation_identity,
        expected_binding_implementation_identity, expected_normal_execution_identity,
        expected_source_execution_identity, specification, budget, before_source=None):
    """All expected identities are external; no pin is inferred from prepare output."""
    if before_source is not None and not callable(before_source):
        raise TypeError('before_source must be a callable runtime check')
    for pin in (expected_request_identity, expected_declared_execution_identity,
            expected_assembly_identity, expected_binding_identity, expected_source_implementation_identity,
            expected_binding_implementation_identity, expected_normal_execution_identity,
            expected_source_execution_identity):
        kernel._pin(pin)

    def implementation():
        if (prepare.task_source_identity(request) != expected_request_identity
                or declared_execution_identity(request, expected_request_identity=expected_request_identity,
                    expected_source_execution_identity=expected_source_execution_identity)
                != expected_declared_execution_identity):
            raise ValueError('declared execution or preparation identity drift')

    def declarations():
        return tuple(prepare._read_pinned(path, pin, maximum) for path, pin, maximum in (
            (request.normal_record_path, request.expected_normal_record_sha256, request.max_normal_record_bytes),
            (request.pair_declaration_path, request.expected_pair_declaration_sha256, request.max_pair_declaration_bytes),
            (request.config_path, request.expected_config_sha256, request.max_config_bytes)))

    implementation()
    kernel._validate(specification, budget, request.expected_scale)
    before = declarations()
    prepared = prepare.prepare_task_inputs(request, expected_request_identity=expected_request_identity)
    if (type(prepared) is not prepare.PreparedStreamingNormalTaskInputs
            or prepared.request_identity != expected_request_identity
            or type(prepared.assembly) is not source.StreamingSourceNormalAssembly
            or type(prepared.binding) is not source.binding.StreamingPairBinding
            or prepared.assembly.assembly_identity != expected_assembly_identity
            or prepared.assembly.implementation_identity != expected_source_implementation_identity
            or prepared.assembly.normal_identity != request.expected_input_identity
            or prepared.binding.binding_identity != expected_binding_identity
            or prepared.binding.implementation_identity != expected_binding_implementation_identity
            or prepared.binding.legacy_content_binding_identity != request.expected_binding_identity
            or type(prepared.solver_calls) is not int or prepared.solver_calls != 0
            or prepared.mechanism_initial_state is not True
            or any(getattr(prepared, name) is not False for name in
                ('observed_power_mapping', 'normal_assignment_verified', 'formal_result'))):
        raise ValueError('prepared streaming inputs differ from independent pins or role')
    def execution_lineage():
        if (source.binding.source.implementation_identity() != expected_source_implementation_identity
                or source.binding.implementation_identity() != expected_binding_implementation_identity
                or kernel.normal_execution_identity(request.expected_input_identity, request.expected_scale,
                    specification, budget) != expected_normal_execution_identity
                or source.source_execution_identity(expected_binding_identity, expected_normal_execution_identity,
                    prepared.declaration, expected_assembly_identity=expected_assembly_identity,
                    expected_pair_identity=request.expected_pair_identity,
                    expected_source_implementation_identity=expected_source_implementation_identity,
                    expected_binding_implementation_identity=expected_binding_implementation_identity)
                    != expected_source_execution_identity):
            raise ValueError('declared source/kernel execution lineage drift')

    implementation()
    execution_lineage()
    if declarations() != before:
        raise ValueError('declarations changed before source execution')
    # Caller-owned runtime check, deliberately outside source-return handling.
    # Failure leaves a reserved journal intent, with no native invocation.
    # This check is not serialized or represented as authenticated evidence.
    if before_source is not None:
        before_source()
    result = None
    errors = []
    interrupted = False
    try:
        returned = source.run_source_normal(prepared.assembly, request.upstream_root, prepared.declaration,
            expected_assembly_identity=expected_assembly_identity,
            expected_pair_identity=request.expected_pair_identity,
            expected_binding_identity=expected_binding_identity,
            expected_input_identity=request.expected_input_identity,
            expected_source_implementation_identity=expected_source_implementation_identity,
            expected_binding_implementation_identity=expected_binding_implementation_identity,
            expected_normal_execution_identity=expected_normal_execution_identity,
            expected_source_execution_identity=expected_source_execution_identity,
            expected_scale=request.expected_scale, specification=specification, budget=budget,
            config_path=request.config_path)
        if type(returned) is not source.NumericStreamingSourceNormalExecutionResult:
            raise ValueError('owned streaming source result required')
        result = returned
        if (result.execution_identity != expected_source_execution_identity
                or result.expected_binding_identity != expected_binding_identity
                or result.contract != source.CONTRACT):
            errors.append('source_result_binding_mismatch')
        normal = result.normal_result
        if normal is not None and (type(normal) is not kernel.NumericStreamingNormalExecutionResult
                or normal.input_identity != request.expected_input_identity
                or normal.execution_identity != expected_normal_execution_identity
                or normal.scale != request.expected_scale or normal.specification != specification
                or normal.budget != budget):
            errors.append('normal_result_binding_mismatch')
        if result.source_bound_normal_accepted is not False and not (
                result.source_bound_normal_accepted is True and result.source_correspondence_verified is True
                and result.status == 'accepted_source_bound_normal' and result.errors == ()
                and result.binding_before_json == result.binding_after_json == source._json(asdict(prepared.binding))
                and type(result.normal_result) is kernel.NumericStreamingNormalExecutionResult
                and source._consistent_acceptance(result.normal_result)
                and type(result.solver_calls) is int and result.solver_calls == 1
                and result.call_count_complete is True
                and all(getattr(result, name) is False for name in ('hard_resource_limits_enforced',
                    'durable_invocation_tracking', 'registered_coupling', 'observed_power_mapping',
                    'formal_result', 'security_certified'))):
            errors.append('source_result_acceptance_inconsistent')
    except BaseException as error:
        interrupted = not isinstance(error, Exception)
        errors.append('source_return:'+type(error).__name__+':'+str(error))
    try:
        implementation()
        execution_lineage()
        if declarations() != before:
            raise ValueError('declarations changed after source execution')
    except BaseException as error:
        interrupted = interrupted or not isinstance(error, Exception)
        errors.append('post_declaration:'+type(error).__name__+':'+str(error))
    accepted = not errors and result is not None and result.source_bound_normal_accepted is True
    return kernel.native._make(DeclaredNumericStreamingNormalResult, contract=CONTRACT,
        execution_identity=expected_declared_execution_identity, request_identity=expected_request_identity,
        source_result=result, preparation_timings=prepared.timings,
        solver_calls=None if result is None else result.solver_calls,
        call_count_complete=result is not None and result.call_count_complete, accepted=accepted,
        status='accepted_declared_normal' if accepted else ('interrupted_declared_normal' if interrupted
            or (result is not None and result.status == 'interrupted_source_bound_normal')
            else 'unresolved_declared_normal'), errors=tuple(errors), mechanism_initial_state=True,
        observed_power_mapping=False, hard_resource_limits_enforced=False,
        durable_invocation_tracking=False, formal_result=False)
