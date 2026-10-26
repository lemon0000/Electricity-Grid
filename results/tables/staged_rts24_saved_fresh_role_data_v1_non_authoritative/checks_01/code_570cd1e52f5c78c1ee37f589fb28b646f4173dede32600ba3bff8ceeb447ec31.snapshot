"""Pure LP/QP transport and checked numeric evidence import; never runs a solver."""
from dataclasses import dataclass
from math import isfinite

from pyomo.environ import Constraint, Var, value, maximize
from pyomo.repn import generate_standard_repn

from src import staged_rts24_development_v1 as c
from src.staged_rts24_audit_v1 import audit_economic_base, audit_point, TOL_KKT, TOL_MW
from src.staged_rts24_child_optimality_v1 import ChildLpEvidence, audit_child_lp, reduction
from src.staged_rts24_causal_v1 import PointEvidence

SCHEMA = "staged_diagonal_convex_qp_min_transport_v1"
SNAPSHOT_SCHEMA = "highs_min_row_bound_snapshot_v1"
TOL_OBJECTIVE_ECHO = 1e-6  # Separate transport echo gate, not an optimality proof.


@dataclass(frozen=True)
class NumericRow:
    name: str
    lower: float | None
    upper: float | None
    terms: tuple[tuple[int, float], ...]
    # Canonical residual = original_scale * (original Pyomo body - equality RHS).
    original_scale: float = 1.


@dataclass(frozen=True)
class EliminatedRow:
    name: str
    constant: float
    lower: float | None
    upper: float | None


@dataclass(frozen=True)
class EliminatedVariable:
    name: str
    lower: float | None
    upper: float | None
    reason: str


@dataclass(frozen=True)
class NumericProblem:
    query_sha: str
    columns: tuple[str, ...]
    lower: tuple[float | None, ...]
    upper: tuple[float | None, ...]
    fixed: tuple[tuple[str, float], ...]
    eliminated_variables: tuple[EliminatedVariable, ...]
    rows: tuple[NumericRow, ...]
    eliminated_rows: tuple[EliminatedRow, ...]
    constant: float
    linear: tuple[float, ...]
    # Polynomial coefficients c*x_i*x_j, i <= j (not Hessian entries).
    quadratic: tuple[tuple[int, int, float], ...]
    schema: str = SCHEMA

    @property
    def identity(self): return c.digest(self)


@dataclass(frozen=True)
class NumericSnapshot:
    problem_sha: str
    model_status: str
    primal_valid: bool
    dual_valid: bool
    column_value: tuple[float, ...]
    row_value: tuple[float, ...]
    column_dual: tuple[float, ...]
    row_dual: tuple[float, ...]
    objective: float
    schema: str = SNAPSHOT_SCHEMA


class UnresolvedNumeric(ValueError):
    """No consumable point; this exception does not assert infeasibility."""


def number(v):
    c.require(type(v) in (int, float) and isfinite(v), "nonfinite numeric transport")
    return float(v)


def compile_problem(query):
    """Reduce an isolated original Pyomo model, retaining an exact transport map."""
    model = c.build_point_model(query)
    q, d = query.request, query.request.data
    original = {v.name: (None if v.lb is None else number(v.lb), None if v.ub is None else number(v.ub))
                for v in model.component_data_objects(Var)}
    reasons = {v.name: "original_fixed" for v in model.component_data_objects(Var) if v.fixed}
    for branch in d.branches:
        if not branch.in_service or branch.index in q.outages.branches:
            model.flow[branch.index].fix(0.)
            reasons[model.flow[branch.index].name] = "inactive_branch_zero"
    for var in model.component_data_objects(Var):
        if var.lb is not None and var.ub is not None and var.lb == var.ub:
            var.fix(var.lb)
            reasons.setdefault(var.name, "equal_bounds")
    variables = tuple(model.component_data_objects(Var))
    free = tuple(v for v in variables if not v.fixed)
    positions = {id(v): i for i, v in enumerate(free)}
    c.require(len({v.name for v in variables}) == len(variables), "duplicate transport variable")

    def polynomial(expression):
        repn = generate_standard_repn(expression, compute_values=True, quadratic=True)
        c.require(repn.nonlinear_expr is None, "unsupported nonlinear transport")
        constant = number(value(repn.constant))
        linear = {}
        for var, coef in zip(repn.linear_vars, repn.linear_coefs):
            i = positions[id(var)]
            linear[i] = linear.get(i, 0.) + number(value(coef))
        quadratic = {}
        for (a, b), coef in zip(repn.quadratic_vars, repn.quadratic_coefs):
            pair = tuple(sorted((positions[id(a)], positions[id(b)])))
            quadratic[pair] = quadratic.get(pair, 0.) + number(value(coef))
        return constant, tuple((i, number(v)) for i, v in sorted(linear.items()) if v != 0), tuple(
            (a, b, number(v)) for (a, b), v in sorted(quadratic.items()) if v != 0)

    rows, eliminated_rows = [], []
    for row in model.component_data_objects(Constraint, active=True):
        constant, terms, quadratic = polynomial(row.body)
        original_constant = constant
        c.require(not quadratic, "nonlinear constraint transport")
        lo = None if row.lower is None else number(value(row.lower)-constant)
        hi = None if row.upper is None else number(value(row.upper)-constant)
        equality = row.parent_component() in (model.power_balance, model.branch_flow)
        c.require((lo is not None and lo == hi) if equality else
                  (row.name in ("connection", "curtailment_bound") and lo is None and hi is not None),
                  "unsupported transport row form")
        scale = 1.
        if row.parent_component() is model.power_balance:
            # Pyomo may reverse `constant == expression` at buses without a
            # generator. Export the audit's explicit G-Pd-Pnet-out+in direction.
            i = row.index()
            expr = (sum(model.generation[g.index] for g in d.generators if g.bus == i)
                    - next(b.demand_mw for b in d.buses if b.index == i)
                    - (model.meter-model.curtailment if i == q.poi_bus else 0.)
                    - sum(model.flow[b.index] for b in d.branches if b.from_bus == i)
                    + sum(model.flow[b.index] for b in d.branches if b.to_bus == i))
            expected = polynomial(expr)
            original_residual = polynomial(row.body-row.lower)
            negative = (number(-original_residual[0]), tuple((j, -a) for j, a in original_residual[1]), ())
            c.require(expected == original_residual or expected == negative, "balance row direction differs")
            scale = 1. if expected == original_residual else -1.
            constant, terms, quadratic = expected
            lo = hi = number(-constant)
        if not terms:
            c.require((lo is None or lo <= 0) and (hi is None or hi >= 0), "inconsistent constant row")
            eliminated_rows.append(EliminatedRow(row.name, original_constant,
                None if row.lower is None else number(value(row.lower)),
                None if row.upper is None else number(value(row.upper))))
        else:
            rows.append(NumericRow(row.name, lo, hi, terms, scale))
    sign = -1. if model.objective.sense == maximize else 1.
    constant, terms, quadratic = polynomial(sign*model.objective.expr)
    c.require(all(i == j and a > 0 for i, j, a in quadratic), "diagonal convex objective required")
    c.require(len({r.name for r in rows}) == len(rows), "duplicate transport row")
    costs = dict(terms)
    return NumericProblem(query.identity, tuple(v.name for v in free),
        tuple(None if v.lb is None else number(v.lb) for v in free),
        tuple(None if v.ub is None else number(v.ub) for v in free),
        tuple((v.name, number(v.value)) for v in variables if v.fixed),
        tuple(EliminatedVariable(v.name, *original[v.name], reasons[v.name]) for v in variables if v.fixed),
        tuple(rows), tuple(eliminated_rows), constant,
        tuple(costs.get(i, 0.) for i in range(len(free))), quadratic)


def hessian_columns(problem):
    """Pure lower-triangle CSC for the convention 0.5*x.T@H@x + c.T@x."""
    c.require(type(problem) is NumericProblem and problem.schema == SCHEMA, "wrong numeric transport schema")
    c.require(all(i == j and 0 <= i < len(problem.columns) and a > 0 and isfinite(a)
                  for i, j, a in problem.quadratic), "diagonal convex Hessian required")
    diagonal = {i: 2*a for i, j, a in problem.quadratic}
    c.require(len(diagonal) == len(problem.quadratic), "duplicate Hessian coefficient")
    start, index, values = [0], [], []
    for i in range(len(problem.columns)):
        if i in diagonal:
            index.append(i)
            values.append(number(diagonal[i]))
        start.append(len(index))
    return tuple(start), tuple(index), tuple(values)


def import_snapshot(query, problem, snapshot):
    """Check raw min-form activities/duals, then require the existing independent audit."""
    expected = compile_problem(query)
    c.require(type(problem) is NumericProblem and problem == expected and problem.identity == expected.identity,
              "numeric problem binding differs")
    c.require(type(snapshot) is NumericSnapshot and snapshot.schema == SNAPSHOT_SCHEMA
              and snapshot.problem_sha == problem.identity, "numeric snapshot binding differs")
    if snapshot.model_status != "kOptimal" or snapshot.primal_valid is not True:
        raise UnresolvedNumeric("native termination or primal unresolved; infeasibility not inferred")
    needs_dual = query.request.anchor_id is None or query.request.objective != "economic"
    if needs_dual and snapshot.dual_valid is not True:
        raise UnresolvedNumeric("native dual unresolved; no numeric optimality evidence")
    c.require(type(snapshot.dual_valid) is bool, "malformed native dual validity")
    has_dual = snapshot.dual_valid
    if not has_dual:
        c.require(snapshot.column_dual == snapshot.row_dual == ()
                  and type(snapshot.column_dual) is type(snapshot.row_dual) is tuple,
                  "invalid primal-only dual payload")
    n, m = len(problem.columns), len(problem.rows)
    arrays = ((snapshot.column_value, n), (snapshot.row_value, m))
    if has_dual: arrays += ((snapshot.column_dual, n), (snapshot.row_dual, m))
    for array, size in arrays:
        c.require(type(array) is tuple and len(array) == size, "numeric snapshot dimensions differ")
        for v in array: number(v)
    values = dict(problem.fixed)
    values.update(zip(problem.columns, snapshot.column_value))
    x = tuple(number(v) for v in snapshot.column_value)
    values.update(zip(problem.columns, x))
    objective = problem.constant + sum(a*v for a, v in zip(problem.linear, x)) + sum(
        a*x[i]*x[j] for i, j, a in problem.quadratic)
    c.require(isfinite(objective) and abs(number(snapshot.objective)-objective) <= TOL_OBJECTIVE_ECHO, "numeric objective echo differs")
    for i, row in enumerate(problem.rows):
        activity = sum(a*x[j] for j, a in row.terms)
        c.require(isfinite(activity) and abs(activity-snapshot.row_value[i]) <= TOL_MW, "numeric row activity differs")
    if has_dual:
        # Check every original free column, including unbounded angles whose
        # reduced costs do not otherwise enter the independent box certificates.
        gradient = list(problem.linear)
        for i, j, a in problem.quadratic:
            gradient[i] += a*x[j]
            gradient[j] += a*x[i]
        for row, dual in zip(problem.rows, snapshot.row_dual):
            for j, a in row.terms: gradient[j] -= a*dual
        c.require(all(isfinite(rc) and abs(rc-reported) <= TOL_KKT for rc, reported in
                      zip(gradient, snapshot.column_dual)), "numeric reduced-cost echo differs")
    q, d = query.request, query.request.data
    point = c.PointWitness(query.identity, values["meter"], values["curtailment"],
        tuple((g.index, values[f"generation[{g.index}]"]) for g in d.generators),
        tuple((b.index, values[f"angle[{b.index}]"]) for b in d.buses),
        tuple((b.index, values[f"flow[{b.index}]"]) for b in d.branches))
    if not needs_dual:
        c.require(audit_point(query, point)["point_constraints_satisfied"], "numeric point audit failed")
        return PointEvidence(query, point)

    rows = {row.name: -v for row, v in zip(problem.rows, snapshot.row_dual)}
    reduced = dict(zip(problem.columns, snapshot.column_dual))
    lam = tuple((b.index, rows[f"power_balance[{b.index}]"]) for b in d.buses)
    lam_by_bus = dict(lam)
    is_root = q.anchor_id is None

    def boxes(name):
        rc = reduced.get(name, 0.)
        return max(rc, 0.), max(-rc, 0.)

    gen_bounds = {}
    for g in d.generators:
        name = f"generation[{g.index}]"
        if is_root and name in dict(problem.fixed):
            output = values[name]
            gradient = (2*(g.cost_quadratic+float(q.economic_regularization_quadratic))*output+g.cost_linear) if g.in_service else 0.
            rc = gradient+lam_by_bus[g.bus]
            gen_bounds[g.index] = (max(rc, 0.), max(-rc, 0.))
        else:
            gen_bounds[g.index] = boxes(name)
    mu = []
    for b in d.branches:
        active = b.in_service and b.index not in q.outages.branches
        multiplier = rows[f"branch_flow[{b.index}]"] if active else (
            lam_by_bus[b.from_bus]-lam_by_bus[b.to_bus] if is_root else 0.)
        mu.append((b.index, multiplier))
    arrays = (lam, tuple(mu), tuple((g.index, gen_bounds[g.index][0]) for g in d.generators),
              tuple((g.index, gen_bounds[g.index][1]) for g in d.generators),
              tuple((b.index, boxes(f"flow[{b.index}]")[0]) for b in d.branches),
              tuple((b.index, boxes(f"flow[{b.index}]")[1]) for b in d.branches))
    if is_root:
        evidence = c.EconomicEvidence(query.identity, c.digest(point), *arrays)
        c.require(audit_economic_base(query, point, evidence)["economic_kkt_satisfied"], "numeric economic audit failed")
        return PointEvidence(query, point, economic=evidence)
    ml, mh = boxes("meter")
    cl, ch = boxes("curtailment")
    evidence = ChildLpEvidence(query.identity, c.digest(point), c.digest(reduction(query)), *arrays,
        ml, mh, cl, ch, rows.get("connection", 0.), rows.get("curtailment_bound", 0.))
    c.require(audit_child_lp(query, point, evidence)["lp_optimality_conditions_satisfied"], "numeric child LP audit failed")
    return PointEvidence(query, point, child_lp=evidence)
