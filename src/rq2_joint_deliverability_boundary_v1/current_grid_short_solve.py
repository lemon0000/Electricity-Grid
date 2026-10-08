"""One bounded current-hour feasibility solve with audited actual carry.

The prescribed DC power is fixed. This does not define a dispatch selection
policy, a grid request, or any capacity/infeasibility/security certificate.
"""
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path

from pyomo.opt import SolverStatus, SolutionStatus, TerminationCondition

from ..solvers.rq2_solver_adapter import Rq2SolverSpec, solver_spec
from .continuous_grid_candidate import GridDevelopmentBudget, GridSolveEvidence, _solve, _make, _enum, _execution_identity
from .continuous_grid_normal import _digest
from .current_grid_step import (ActualStepCarry, CurrentGridWitness, current_step_identity,
    build_current_grid_model, audit_current_grid_assignment)


CONTRACT = 'owned_current_hour_fixed_power_network_short_solve_v1'
PURPOSE = 'current_hour_fixed_power_network_feasibility'


@dataclass(frozen=True, init=False)
class CurrentGridShortResult:
    contract: str
    input_identity: str
    execution_identity: str
    specification: Rq2SolverSpec
    budget: GridDevelopmentBudget
    raw_solve: GridSolveEvidence
    assignment_witness: CurrentGridWitness | None
    physical_assignment_witness_available: bool
    solver_lineage_checked: bool
    owned_solver_assignment_available: bool
    next_carry: ActualStepCarry | None
    network_feasibility_status: str
    errors: tuple[str, ...]
    information_mode: str
    development_objective_interval: None
    external_grid_need_trace: None
    capacity_certificate: None
    causal_grid_dispatch_certificate: None
    infeasibility_certificate: None
    formal_result: bool
    security_certified: bool

    def __init__(self, *args, **kwargs):
        raise TypeError('current network result requires owned short execution')

    @property
    def result_id(self):
        return _digest(self)


def _admit(spec, budget):
    if type(spec) is not Rq2SolverSpec or type(budget) is not GridDevelopmentBudget:
        raise ValueError('typed solver specification and short development budget required')
    budget.__post_init__()
    if budget.purpose != PURPOSE:
        raise ValueError('explicit current-hour feasibility purpose required')
    if spec != solver_spec(asdict(spec)):
        raise ValueError('canonical solver specification required')
    if any(getattr(spec, name) > 1e-6 for name in
            ('feasibility_tolerance', 'optimality_tolerance', 'integer_feasibility_tolerance')):
        raise ValueError('solver tolerance exceeds current-hour audit applicability')
    if (spec.time_limit_seconds is None or spec.time_limit_seconds > budget.max_seconds_per_solve
            or spec.time_limit_seconds > budget.max_total_solver_seconds or spec.threads > budget.max_threads):
        raise ValueError('current-hour execution exceeds short development budget')


def _identity(expected_identity, spec, budget):
    if (type(CONTRACT) is not str or CONTRACT != 'owned_current_hour_fixed_power_network_short_solve_v1'
            or type(PURPOSE) is not str or PURPOSE != 'current_hour_fixed_power_network_feasibility'):
        raise ValueError('current-hour execution contract drift')
    source = sha256(Path(__file__).read_bytes()).hexdigest()
    return _digest(CONTRACT, PURPOSE, expected_identity, _execution_identity(spec, budget), source)


def run_short_current_grid(info, disclosure, before, power, *, expected_identity, solver_specification, budget):
    spec = solver_specification
    _admit(spec, budget)
    if current_step_identity(info, disclosure, before, power) != expected_identity:
        raise ValueError('current-hour input identity mismatch')
    execution = _identity(expected_identity, spec, budget)
    builder = lambda: build_current_grid_model(info, disclosure, before, power, expected_identity=expected_identity)
    raw = _solve(builder, spec, budget, PURPOSE)
    if raw.calls not in (0, 1) or raw.calls > budget.max_solver_calls:
        raise ValueError('current-hour solver call budget exceeded')
    witness = None
    errors = list(raw.errors)
    complete = tuple(sorted((*raw.native_values, *((n, x) for n, x, _ in raw.canonical_completed_values))))
    load_failed = any(error.startswith(('load:', 'native_inventory:', 'native_result:')) for error in raw.errors)
    feasible_status = raw.solution_statuses in ((_enum(SolutionStatus.optimal),), (_enum(SolutionStatus.feasible),))
    accepted_outcome = (len(raw.solver_records) == 1
        and raw.solver_records[0][0] in tuple(_enum(s) for s in (SolverStatus.ok, SolverStatus.warning))
        and raw.solver_records[0][1] in tuple(_enum(t) for t in (
            TerminationCondition.optimal, TerminationCondition.globallyOptimal,
            TerminationCondition.feasible, TerminationCondition.maxTimeLimit,
            TerminationCondition.maxIterations, TerminationCondition.maxEvaluations,
            TerminationCondition.userInterrupt, TerminationCondition.resourceInterrupt)))
    if raw.solution_count == 1 and not accepted_outcome:
        errors.append('native_solver_outcome_inconsistent_or_unsupported')
    if raw.solution_count == 1 and raw.loaded_values and raw.loaded_values == complete and not load_failed and feasible_status:
        try:
            witness = audit_current_grid_assignment(info, disclosure, before, power,
                dict(raw.loaded_values), expected_identity=expected_identity)
            errors.extend(witness.errors)
        except (ValueError, OverflowError) as error:
            errors.append(f'current_assignment_audit:{type(error).__name__}:{error}')
    elif raw.solution_count == 1 and not feasible_status:
        errors.append('native_solution_status_not_feasible')
    if (current_step_identity(info, disclosure, before, power) != expected_identity
            or _identity(expected_identity, spec, budget) != execution):
        raise ValueError('current-hour input or execution identity drifted')
    physical = witness is not None and witness.physical_assignment_valid
    lineage = not raw.errors and raw.assignment_valid and feasible_status and accepted_outcome
    owned = physical and lineage
    return _make(CurrentGridShortResult, contract=CONTRACT, input_identity=expected_identity,
        execution_identity=execution, specification=spec, budget=budget, raw_solve=raw,
        assignment_witness=witness, physical_assignment_witness_available=physical,
        solver_lineage_checked=lineage, owned_solver_assignment_available=owned,
        next_carry=witness.next_carry if owned else None,
        network_feasibility_status='witnessed' if physical else 'unresolved', errors=tuple(errors),
        information_mode=before.protocol.information_mode, development_objective_interval=None,
        external_grid_need_trace=None, capacity_certificate=None, causal_grid_dispatch_certificate=None,
        infeasibility_certificate=None, formal_result=False, security_certified=False)
