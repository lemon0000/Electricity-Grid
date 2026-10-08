"""Non-authoritative canonical assignment audit; never invokes a solver.

Trusted inputs are caller supplied. Submitted model structure is diagnostic;
residuals always use a fresh canonical model. Solver bounds remain unaudited.
"""
from dataclasses import asdict, dataclass
from fractions import Fraction as Q
import hashlib
import json
from math import isfinite

from pyomo.environ import Constraint, Objective, Var, value
from pyomo.repn import generate_standard_repn

from ..rq2_joint_deliverability_v2.solver_adapter import Rq2SolverSpec, solver_spec
from .continuous_planner_bidirectional import BidirectionalPlanningInputs, build_continuous_planning_model, planner_identity
from .planner_witness import PlannerHourAction, PlannerTrackAction
from .planner_bidirectional_witness import BidirectionalWitnessCandidate, BidirectionalWitnessAudit, audit_planner_witness
from .planner_assignment import (
    NumericSnapshot, ResidualRow, _numeric, _finite, _structure, _validate_numeric_snapshot,
)


@dataclass(frozen=True)
class BidirectionalAssignmentAudit:
    inputs: BidirectionalPlanningInputs
    arm: str
    planner_id: str
    snapshot: tuple[tuple[str, NumericSnapshot], ...]
    missing_variables: tuple[str, ...]
    extra_variables: tuple[str, ...]
    canonical_structure: str
    submitted_structure: str | None
    structure_error: str | None
    variable_residuals: tuple[ResidualRow, ...]
    constraint_residuals: tuple[ResidualRow, ...]
    objective: float | None
    evaluation_error: str | None
    feasibility_tolerance: float
    integer_tolerance: float
    witness: BidirectionalWitnessAudit | None
    extraction_error: str | None

    def __post_init__(self):
        if self.planner_id != planner_identity(self.inputs, self.arm):
            raise ValueError('assignment planner identity differs')
        for tolerance in (self.feasibility_tolerance, self.integer_tolerance):
            if type(tolerance) is not float or not isfinite(tolerance) or tolerance <= 0:
                raise ValueError('finite positive audit tolerance required')
        if self.integer_tolerance >= .5:
            raise ValueError('integer audit tolerance must be below half an integer step')
        expected = _recompute(self.inputs, self.arm, self.snapshot)
        observed = (self.missing_variables, self.extra_variables, self.canonical_structure,
            self.variable_residuals, self.constraint_residuals, self.objective,
            self.evaluation_error, self.witness, self.extraction_error)
        if observed != expected:
            raise ValueError('assignment audit differs from canonical snapshot replay')

    @property
    def complete_assignment(self):
        return (not self.missing_variables and not self.extra_variables
                and all(item.error is None for _, item in self.snapshot))

    @property
    def structure_matches(self):
        return self.submitted_structure == self.canonical_structure

    @property
    def assignment_id(self):
        payload = {'contract': 'bidirectional_canonical_assignment_audit_v1', 'planner_id': self.planner_id,
            'snapshot': [(name, asdict(item)) for name, item in self.snapshot],
            'canonical_structure': self.canonical_structure, 'submitted_structure': self.submitted_structure,
            'structure_error': self.structure_error, 'feasibility_tolerance': self.feasibility_tolerance,
            'integer_tolerance': self.integer_tolerance}
        return hashlib.sha256(json.dumps(payload, sort_keys=True, allow_nan=False).encode()).hexdigest()

    @property
    def maximum_bound_violation(self):
        if not self.complete_assignment or self.evaluation_error is not None:
            return None
        return max((max(r.lower_violation, r.upper_violation) for r in self.variable_residuals), default=0.)

    @property
    def maximum_integrality_violation(self):
        if not self.complete_assignment or self.evaluation_error is not None:
            return None
        return max((r.integrality_violation for r in self.variable_residuals), default=0.)

    @property
    def maximum_constraint_violation(self):
        if not self.complete_assignment or self.evaluation_error is not None:
            return None
        return max((max(r.lower_violation, r.upper_violation) for r in self.constraint_residuals), default=0.)

    @property
    def numerical_assignment_accepted(self):
        return (self.complete_assignment and self.evaluation_error is None and self.objective is not None
                and self.maximum_bound_violation <= self.feasibility_tolerance
                and self.maximum_constraint_violation <= self.feasibility_tolerance
                and self.maximum_integrality_violation <= self.integer_tolerance)

    @property
    def exact_witness_accepted(self):
        return self.witness is not None and self.witness.accepted

    def evidence(self):
        return {'status': 'DRAFT_NONAUTHORITATIVE', 'planner_id': self.planner_id, 'assignment_id': self.assignment_id,
            'canonical_numeric_assignment_accepted': self.numerical_assignment_accepted,
            'exact_witness_accepted': self.exact_witness_accepted,
            'post_snapshot_structure_matches': self.structure_matches,
            'activity_representation': self.inputs.activity_representation,
            'solver_input_lineage_verified': False, 'solver_bound_provenance_verified': False,
            'prefix_upper_bound': None, 'complete_capacity_lower_bound': None,
            'complete_capacity_upper_bound': None, 'causal_policy_certificate': None,
            'formal_result': False, 'security_certified': False}


def _extract(inputs, arm, canonical):
    # repr(float) is the fixed shortest-round-trip decimal interpretation.
    def q(variable):
        raw = float(variable.value)
        text = repr(raw)
        if float(text) != raw:
            raise ValueError('numeric round trip failed')
        return Q(text)
    scenarios = []
    for scenario in inputs.scenarios:
        hours = []
        for t, current in enumerate(scenario.observations):
            g = q(canonical.grid_service[scenario.name, t])
            c = q(canonical.cfe_service[scenario.name, t])
            tracks = []
            for k in canonical._continuous_tracks:
                call = g if k == 'grid' else c if k == 'cfe' else g+c
                recovery = q(canonical.recovery[scenario.name, k, t])
                allocations = tuple((scenario.anchor.power_source_hour+b+1, amount)
                    for b in range(t+1)
                    if (amount := q(canonical.allocation[scenario.name, k, b, t])) != 0)
                power = Q(str(current.observation.hour.workload_occupancy))-call+recovery
                tracks.append((k, PlannerTrackAction(recovery, power, allocations)))
            hours.append(PlannerHourAction(g, c, tuple(tracks)))
        scenarios.append((scenario.name, tuple(hours)))
    candidate = BidirectionalWitnessCandidate(planner_identity(inputs, arm), q(canonical.capacity), tuple(scenarios))
    return audit_planner_witness(inputs, arm, candidate)


def audit_planner_assignment(inputs, arm, submitted_model, specification):
    """Read every submitted value, rebuild canonical constraints, then replay.

No solver metadata on submitted_model supplies trusted inputs or authority.
The supplied solver spec is validated; tolerances are never silently widened.
"""
    if not isinstance(specification, Rq2SolverSpec):
        raise ValueError('explicit typed solver specification required')
    specification = solver_spec(asdict(specification))
    if specification.integer_feasibility_tolerance >= .5:
        raise ValueError('integer audit tolerance must be below half an integer step')
    snapshot = tuple(sorted((v.name, _numeric(v.value))
        for v in submitted_model.component_data_objects(Var, active=None, descend_into=True)))
    structure, structure_error = None, None
    try:
        structure = _structure(submitted_model)
    except (ValueError, TypeError, OverflowError, ArithmeticError) as error:
        structure_error = str(error)
    (missing, extra, canonical_structure, variable_rows, constraint_rows, objective,
     evaluation_error, witness, extraction_error) = _recompute(inputs, arm, snapshot)
    return BidirectionalAssignmentAudit(inputs, arm, planner_identity(inputs, arm), snapshot, missing, extra, canonical_structure,
        structure, structure_error, variable_rows, constraint_rows, objective, evaluation_error,
        specification.feasibility_tolerance, specification.integer_feasibility_tolerance, witness, extraction_error)


def _recompute(inputs, arm, snapshot):
    if type(snapshot) is not tuple or any(type(row) is not tuple or len(row) != 2
        or type(row[0]) is not str for row in snapshot):
        raise ValueError('immutable named snapshot required')
    names = tuple(name for name, _ in snapshot)
    if names != tuple(sorted(set(names))):
        raise ValueError('snapshot names must be unique and ordered')
    for _, item in snapshot:
        _validate_numeric_snapshot(item)
    canonical = build_continuous_planning_model(inputs, arm)
    expected = {v.name: v for v in canonical.component_data_objects(Var, active=None, descend_into=True)}
    values = dict(snapshot)
    missing, extra = tuple(sorted(expected.keys()-values.keys())), tuple(sorted(values.keys()-expected.keys()))
    canonical_structure = _structure(canonical)
    variable_rows, constraint_rows = [], []
    objective, evaluation_error, witness, extraction_error = None, None, None, None
    if not missing and not extra and all(x.error is None for x in values.values()):
        for name, variable in expected.items():
            variable.set_value(values[name].number, skip_validation=True)
        try:
            for variable in expected.values():
                x = _finite(variable)
                variable_rows.append(ResidualRow(variable.name,
                    max(0., _finite(variable.lb)-x) if variable.lb is not None else 0.,
                    max(0., x-_finite(variable.ub)) if variable.ub is not None else 0.,
                    abs(x-round(x)) if variable.is_integer() else 0.))
            for constraint in canonical.component_data_objects(Constraint, active=True, descend_into=True):
                x = _finite(constraint.body)
                constraint_rows.append(ResidualRow(constraint.name,
                    max(0., _finite(constraint.lower)-x) if constraint.lower is not None else 0.,
                    max(0., x-_finite(constraint.upper)) if constraint.upper is not None else 0.))
            objective = _finite(canonical.minimum_capacity.expr)
        except (ValueError, TypeError, OverflowError, ArithmeticError) as error:
            evaluation_error = str(error)
        try:
            witness = _extract(inputs, arm, canonical)
        except (ValueError, OverflowError) as error:
            extraction_error = str(error)
    else:
        evaluation_error = 'incomplete_or_invalid_assignment'
    return (missing, extra, canonical_structure, tuple(variable_rows), tuple(constraint_rows), objective,
            evaluation_error, witness, extraction_error)


@dataclass(frozen=True)
class BidirectionalRawOutcomeAudit:
    solver_status: str
    termination: str
    lower: NumericSnapshot
    upper: NumericSnapshot
    absolute_gap: float | None
    incumbent_relative_gap: float | None
    issues: tuple[str, ...]
    planner_id: str
    assignment_id: str

    def evidence(self):
        return {'status': 'unresolved', 'evidence_class': 'raw_solver_report_unaudited',
            'planner_id': self.planner_id, 'assignment_id': self.assignment_id,
            'reported_object': 'offline_bidirectional_relaxed_prefix',
            'solver_bound_provenance_verified': False, 'relaxed_prefix_capacity_interval': None,
            'prefix_capacity_interval': None, 'complete_capacity_lower_bound': None,
            'complete_capacity_upper_bound': None, 'formal_result': False, 'security_certified': False}


def audit_raw_solver_outcome(assignment, *, solver_status, termination, lower_bound, upper_bound):
    """Retain raw reports without turning caller strings or post-hoc audits into certificates."""
    if not isinstance(assignment, BidirectionalAssignmentAudit) or type(solver_status) is not str or type(termination) is not str:
        raise ValueError('typed assignment and explicit raw solver status required')
    lower, upper = _numeric(lower_bound), _numeric(upper_bound)
    issues = []
    if solver_status != 'ok': issues.append('solver_status_not_ok')
    if termination not in ('optimal', 'globallyOptimal'): issues.append('termination_not_optimal')
    for name, number in (('lower', lower), ('upper', upper)):
        if number.error: issues.append(name+'_'+number.error)
    if not assignment.numerical_assignment_accepted: issues.append('canonical_assignment_unaccepted')
    if not assignment.structure_matches: issues.append('submitted_structure_differs')
    if not assignment.exact_witness_accepted: issues.append('effective_witness_unavailable')
    gap = relative = None
    if lower.number is not None and upper.number is not None:
        if lower.number > upper.number:
            issues.append('inverted_bounds')
        else:
            gap = upper.number-lower.number
            if not isfinite(gap):
                gap = None
                issues.append('gap_overflow')
        if assignment.objective is not None:
            if lower.number > assignment.objective: issues.append('lower_exceeds_assignment_objective')
            if abs(upper.number-assignment.objective) > assignment.feasibility_tolerance:
                issues.append('upper_differs_from_assignment_objective')
            if gap is not None:
                relative = gap/max(abs(assignment.objective), 1e-12)
                if not isfinite(relative):
                    relative = None
                    issues.append('relative_gap_overflow')
    # Post-snapshot structure equality cannot establish what was actually solved.
    issues.append('solver_input_and_bound_lineage_unaudited')
    return BidirectionalRawOutcomeAudit(solver_status, termination, lower, upper, gap, relative,
                           tuple(issues), assignment.planner_id, assignment.assignment_id)
