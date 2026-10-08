"""Owned, bounded H1 numerical lex chain; not a formal execution controller."""
from copy import deepcopy
from dataclasses import asdict, dataclass, fields
from hashlib import sha256
import json
from pathlib import Path

from . import normal_h1_model as model_api
from . import continuous_grid_candidate as budget_api
from .continuous_grid_candidate import GridDevelopmentBudget
from ..solvers import rq2_objective_provenance_run_v1 as capture
from ..solvers import rq2_normal_numerical_candidate_v1 as predicate
from experiments import replay_rq2_h25_native_provenance_v1 as replay


PURPOSE = 'h1_normal_numerical_lex_short_development_v1'
MAX_PAYLOAD_BYTES = 16 * 1024**2


def _pin(pin):
    if type(pin) is not str or len(pin) != 64 or any(c not in '0123456789abcdef' for c in pin):
        raise ValueError('canonical H1 chain identity required')


def implementation_identity():
    return model_api._digest(PURPOSE, capture.implementation_identity(),
        tuple((m.__name__, sha256(Path(m.__file__).read_bytes()).hexdigest())
              for m in (model_api, predicate, replay, budget_api)), sha256(Path(__file__).read_bytes()).hexdigest())


def chain_identity(inputs, specification, budget):
    capture.provenance.adapter.validate_spec(specification)
    if type(budget) is not GridDevelopmentBudget or budget.purpose != PURPOSE:
        raise ValueError('explicit H1 short development budget required')
    budget.__post_init__()
    order = model_api.stage_order(inputs)
    if (budget.max_horizon != 1 or len(order) > budget.max_solver_calls
            or specification.time_limit_seconds > budget.max_seconds_per_solve
            or specification.threads > budget.max_threads
            or len(order)*specification.time_limit_seconds > budget.max_total_solver_seconds):
        raise ValueError('complete H1 chain exceeds declared short budget')
    req = model_api.H1StageRequest(inputs)
    identity = model_api.h1_stage_identity(req)
    model = model_api.build_h1_stage_model(req, expected_identity=identity)
    scale = capture.audit.model_scale(model)
    if scale.variables > budget.max_variables or scale.constraints+len(order)-1 > budget.max_constraints:
        raise ValueError('complete H1 chain model scale exceeds budget')
    return model_api._digest(PURPOSE, identity, asdict(specification), asdict(budget), implementation_identity())


class _Owned:
    def __init__(self, *args, **kwargs):
        raise TypeError('H1 chain evidence requires owned execution')


def _owned(cls, **values):
    result = object.__new__(cls)
    for field in fields(cls):
        object.__setattr__(result, field.name, values[field.name])
    return result


@dataclass(frozen=True, init=False)
class H1StageEvidence(_Owned):
    index: int
    objective: tuple
    stage_identity: str
    prior_locks: tuple
    native_payload: bytes | None
    assignment_audit: model_api.H1AssignmentAudit | None
    numeric_predicate_payload: bytes | None
    lock_value: float | None
    accepted: bool
    errors: tuple[str, ...]


@dataclass(frozen=True, init=False)
class H1ChainEvidence(_Owned):
    chain_identity: str
    stages: tuple[H1StageEvidence, ...]
    collector_attempts: int
    solver_calls: int | None
    numerical_chain_accepted: bool
    errors: tuple[str, ...]
    exact_mathematical_certificate: bool
    formal_result: bool
    hard_process_resources_verified: bool


def run_h1_chain(inputs, specification, budget, *, expected_identity):
    """No caller-supplied locks, retries, persistence, or automatic state advance.

    Whole-process limits and publication remain the future controller's job.
    If a collector raises, the call count is unknown and the chain stops.
    """
    _pin(expected_identity)
    inputs = deepcopy(inputs)
    if chain_identity(inputs, specification, budget) != expected_identity:
        raise ValueError('H1 chain declaration mismatch')
    runner_pin = capture.implementation_identity()
    collector_pin = sha256(Path(capture.provenance.__file__).read_bytes()).hexdigest()
    adapter_pin = capture.provenance.adapter.implementation_identity()
    order = model_api.stage_order(inputs)
    stages, locks, errors = [], (), []
    attempts, calls = 0, 0
    for index, objective in enumerate(order):
        req = model_api.H1StageRequest(inputs, locks)
        stage_pin = model_api.h1_stage_identity(req)
        builder = lambda req=req, pin=stage_pin: model_api.build_h1_stage_model(req, expected_identity=pin)
        raw = audit = numeric_raw = lock = None
        stage_errors = []
        report_count_bound = False
        collector_entered = False
        try:
            stage_model = builder()
            structure = capture.audit._structure(stage_model)
            scale = capture.audit.model_scale(stage_model)
            attempts += 1
            collector_entered = True
            try:
                raw = capture.solve_once(builder, specification, expected_structure=structure,
                    max_variables=budget.max_variables, max_constraints=budget.max_constraints,
                    max_payload_bytes=MAX_PAYLOAD_BYTES, expected_implementation=runner_pin)
            except Exception:
                calls = None
                raise
            if type(raw) is not bytes:
                returned_type = type(raw).__name__
                raw = None
                raise ValueError('native payload must be bytes; got '+returned_type)
            if len(raw) > MAX_PAYLOAD_BYTES:
                raw = None
                raise ValueError('native payload exceeds byte limit')
            report = json.loads(raw)
            if (report['schema'] != 'rq2_objective_provenance_owned_solve_v1'
                    or type(report['solver_calls']) is not int or report['solver_calls'] != 1
                    or type(report['variables']) is not int or report['variables'] != scale.variables
                    or type(report['constraints']) is not int or report['constraints'] != scale.constraints
                    or report['implementation_identity'] != runner_pin
                    or report['model_structure_identity'] != structure
                    or report['solver_options'] != capture.audit.solver_options(specification)
                    or any(report[k] is not False for k in ('formal_result','normal_accepted','optimality_certified'))):
                raise ValueError('owned H1 native report binding mismatch')
            report_count_bound = True
            calls += 1
            if report['provenance'] is None or report['assignment'] is None:
                raise ValueError('missing H1 native incumbent/provenance')
            for name in ('native_status', 'native_solution_count', 'pyomo_status', 'pyomo_termination'):
                if (type(report[name]) is not type(report['provenance'][name])
                        or report[name] != report['provenance'][name]):
                    raise ValueError('H1 native status channels mismatch')
            replay.verify_numerical(builder(), report)
            numeric = predicate.evaluate(report, expected_implementation=runner_pin,
                expected_collector=collector_pin, expected_adapter=adapter_pin)
            numeric_raw = capture.encode(numeric)
            assignment = {name: float.fromhex(number) for name, number in report['assignment']}
            audit = model_api.audit_h1_assignment(req, assignment, expected_identity=stage_pin)
            if audit.canonical_objective.hex() != report['provenance']['canonical_objective_hex']:
                raise ValueError('independent H1 canonical objective mismatch')
            if not numeric['candidate_numeric_predicate_passed'] or audit.errors:
                raise ValueError('H1 numerical/assignment acceptance failed')
            lock = audit.canonical_objective
            if objective[0] == 'commitment':
                lock = float(round(lock))
                if lock not in (0., 1.) or abs(lock-audit.canonical_objective) > 1e-9:
                    raise ValueError('H1 commitment lock is not audited binary')
            if index+1 < len(order):
                model_api.H1StageRequest(inputs, (*locks, lock))
            if chain_identity(inputs, specification, budget) != expected_identity:
                raise ValueError('H1 chain implementation/input drift')
        except Exception as error:
            if collector_entered and not report_count_bound:
                calls = None
            stage_errors.append(f'{type(error).__name__}:{error}')
        accepted = not stage_errors
        stages.append(_owned(H1StageEvidence, index=index, objective=objective, stage_identity=stage_pin,
            prior_locks=locks, native_payload=raw, assignment_audit=audit,
            numeric_predicate_payload=numeric_raw, lock_value=lock if accepted else None,
            accepted=accepted, errors=tuple(stage_errors)))
        if not accepted:
            errors.extend(stage_errors)
            break
        locks = (*locks, lock)
    return _owned(H1ChainEvidence, chain_identity=expected_identity, stages=tuple(stages),
        collector_attempts=attempts, solver_calls=calls,
        numerical_chain_accepted=not errors and len(stages)==len(order), errors=tuple(errors),
        exact_mathematical_certificate=False, formal_result=False, hard_process_resources_verified=False)
