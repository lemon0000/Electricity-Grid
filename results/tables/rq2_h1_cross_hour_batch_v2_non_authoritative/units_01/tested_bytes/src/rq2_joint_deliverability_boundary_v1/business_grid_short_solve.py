"""Single-call development feasibility solve with fixed business actions.

Reuse the owned native pipeline; only the fresh joint audit determines physical
assignment availability. Raw constant-objective bounds are never conclusions.
"""
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from pyomo.opt import SolverStatus, SolutionStatus, TerminationCondition

from .business_grid import (BusinessGridInputs, BusinessGridWitness, business_grid_identity,
    build_business_grid_model, audit_business_grid_assignment)
from .continuous_grid_candidate import GridDevelopmentBudget, GridSolveEvidence, _solve, _make, _enum
from .continuous_grid_normal import _digest
from .outage_short_solve import _admit, _execution
from .outage_trajectory import _sha
from ..solvers.rq2_solver_adapter import Rq2SolverSpec


CONTRACT = 'owned_fixed_business_network_feasibility_short_v1'
PURPOSE = 'fixed_business_network_feasibility'


@dataclass(frozen=True, init=False)
class BusinessGridShortResult:
    contract: str
    input_identity: str
    execution_identity: str
    specification: Rq2SolverSpec
    budget: GridDevelopmentBudget
    raw_solve: GridSolveEvidence
    assignment_witness: BusinessGridWitness | None
    physical_assignment_witness_available: bool
    solver_lineage_checked: bool
    owned_solver_assignment_available: bool
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
        raise TypeError('business network result requires owned short execution')

    @property
    def result_id(self):
        return _digest(self)


def _identity(inputs, expected_identity, spec, budget):
    if (type(CONTRACT) is not str or CONTRACT != 'owned_fixed_business_network_feasibility_short_v1'
            or type(PURPOSE) is not str or PURPOSE != 'fixed_business_network_feasibility'):
        raise ValueError('business network execution contract drift')
    root = Path(__file__).resolve().parent
    sources = tuple((name, sha256((root / name).read_bytes()).hexdigest()) for name in
        ('business_grid_short_solve.py', 'business_grid.py', 'prefix_handoff.py'))
    return _digest(CONTRACT, PURPOSE, expected_identity, inputs.expected_business_prefix_sha256,
                   _execution(spec, budget), sources)


def run_short_business_grid(inputs, *, expected_identity, solver_specification, budget):
    if type(inputs) is not BusinessGridInputs or type(budget) is not GridDevelopmentBudget:
        raise ValueError('typed fixed-business inputs and development budget required')
    if type(budget.purpose) is not str or budget.purpose != 'fixed_business_network_feasibility':
        raise ValueError('explicit fixed_business_network_feasibility purpose required')
    _sha(expected_identity)
    spec = solver_specification
    _admit(inputs.network, spec, budget)
    if business_grid_identity(inputs) != expected_identity:
        raise ValueError('fixed business network input identity mismatch')
    execution = _identity(inputs, expected_identity, spec, budget)
    builder = lambda: build_business_grid_model(inputs, expected_identity=expected_identity)
    raw = _solve(builder, spec, budget, PURPOSE)
    if raw.calls not in (0, 1) or raw.calls > budget.max_solver_calls:
        raise ValueError('business network solver call budget exceeded')
    witness = None
    errors = list(raw.errors)
    # A load error or mismatched native/loaded inventory is not a solver-origin
    # assignment. Complete assignments with later lineage errors can still be
    # audited independently, without inheriting the solver's claims.
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
            witness = audit_business_grid_assignment(inputs, dict(raw.loaded_values), expected_identity=expected_identity)
            errors.extend(witness.errors)
        except (ValueError, OverflowError) as error:
            errors.append(f'joint_assignment_audit:{type(error).__name__}:{error}')
    elif raw.solution_count == 1 and not feasible_status:
        errors.append('native_solution_status_not_feasible')
    if (business_grid_identity(inputs) != expected_identity
            or _identity(inputs, expected_identity, spec, budget) != execution):
        raise ValueError('business network input or execution identity drifted')
    physical = witness is not None and witness.physical_network_assignment_valid
    lineage = not raw.errors and raw.assignment_valid and feasible_status and accepted_outcome
    return _make(BusinessGridShortResult, contract=CONTRACT, input_identity=expected_identity,
        execution_identity=execution, specification=spec, budget=budget, raw_solve=raw,
        assignment_witness=witness, physical_assignment_witness_available=physical,
        solver_lineage_checked=lineage, owned_solver_assignment_available=physical and lineage,
        network_feasibility_status='witnessed' if physical else 'unresolved', errors=tuple(errors),
        information_mode=inputs.network.information_mode, development_objective_interval=None,
        external_grid_need_trace=None, capacity_certificate=None, causal_grid_dispatch_certificate=None,
        infeasibility_certificate=None, formal_result=False, security_certified=False)
