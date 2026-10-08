from copy import copy

import pytest
from pyomo.environ import Binary, ConcreteModel, Constraint, Objective, Var

from experiments import h1_linear_export_guard_development_v1 as api
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver


class Handle:
    def __init__(self, owner, index, **attrs):
        self.owner, self.index = owner, index
        self.__dict__.update(attrs)

    def sameAs(self, other):
        return self.owner is other.owner and self.index == other.index


class Expression:
    def __init__(self, terms, constant=0.):
        self.terms, self.constant = terms, constant

    def size(self):
        return len(self.terms)

    def getVar(self, i):
        return copy(self.terms[i][0])

    def getCoeff(self, i):
        return self.terms[i][1]

    def getConstant(self):
        return self.constant


class Native:
    NumVars, NumConstrs, NumObj, ModelSense = 3, 3, 1, 1
    NumQConstrs = NumSOS = NumGenConstrs = NumQNZs = 0
    NumScenarios = NumPWLObjVars = 0

    def getVars(self):
        return [copy(x) for x in self.variables]

    def getConstrs(self):
        return [copy(x) for x in self.constraints]

    def getObjective(self):
        return self.objective

    def getRow(self, constraint):
        return self.rows[constraint.index]


def case():
    m = ConcreteModel()
    m.x = Var(bounds=(-2, 7))
    m.y = Var(domain=Binary)
    m.z = Var(initialize=2.)
    m.z.fix()
    m.obj = Objective(expr=3*m.x + m.y + m.z)
    m.eq = Constraint(expr=m.x + 2*m.y == 5)
    m.upper = Constraint(expr=2*m.x - m.y + m.z <= 8)
    m.lower = Constraint(expr=m.x >= -1)
    n = Native()
    owner, rows_owner = object(), object()
    x, y, z = n.variables = [Handle(owner, i, VType=t, LB=lo, UB=hi)
        for i, (t, lo, hi) in enumerate([('C', -2., 7.), ('B', 0., 1.), ('C', 2., 2.)])]
    n.constraints = [Handle(rows_owner, i, Sense=s, RHS=r, Lazy=0)
        for i, (s, r) in enumerate([('=', 5.), ('<', 6.), ('>', -1.)])]
    n.objective = Expression([(x, 3.), (y, 1.)], 2.)
    n.rows = [Expression([(x, 1.), (y, 2.)]), Expression([(x, 2.), (y, -1.)]), Expression([(x, 1.)])]
    vf = tuple(zip((m.x, m.y, m.z), n.variables))
    cf = tuple(zip((m.eq, m.upper, m.lower), n.constraints))
    args = dict(native_model=n, variable_forward=vf,
                variable_reverse=tuple((copy(nv), v) for v, nv in vf),
                constraint_forward=cf, constraint_reverse=tuple((copy(nc), c) for c, nc in cf))
    return m, n, args


def test_equivalent_wrappers_full_matrix_and_fixed_variable():
    m, n, args = case()
    assert n.getVars()[0] is not args['variable_forward'][0][1]
    result = api.check(m, **args)
    assert result['exact_linear_correspondence_checked']
    assert not any(result[k] for k in ('native_export_coverage', 'native_execution_authenticated',
                                     'resource_admission', 'formal_execution_ready', 'formal_result'))


@pytest.mark.parametrize('fault', ['objective', 'constant', 'row', 'rhs', 'sense', 'domain', 'lb',
    'fixed', 'extra_variable', 'missing_constraint', 'duplicate_index', 'foreign_owner',
    'reverse', 'constraint_reverse', 'duplicate_term', 'nan', 'bool_index', 'range',
    'quadratic', 'rounded_rhs', 'infinity_collision', 'lazy', 'row_constant'])
def test_mismatch_fails_closed(fault):
    m, n, args = case()
    if fault == 'objective': n.objective.terms[0] = (n.variables[0], 4.)
    elif fault == 'constant': n.objective.constant = 3.
    elif fault == 'row': n.rows[1].terms[0] = (n.variables[0], 3.)
    elif fault == 'rhs': n.constraints[0].RHS = 6.
    elif fault == 'sense': n.constraints[0].Sense = '<'
    elif fault == 'domain': n.variables[1].VType = 'C'
    elif fault == 'lb': n.variables[0].LB = -3.
    elif fault == 'fixed': n.variables[2].UB = 3.
    elif fault == 'extra_variable': n.NumVars = 4
    elif fault == 'missing_constraint': n.constraints.pop()
    elif fault == 'duplicate_index': n.variables[1].index = 0
    elif fault == 'foreign_owner':
        alien = copy(n.variables[0]); alien.owner = object()
        n.rows[0].terms[0] = (alien, 1.)
    elif fault == 'reverse': args['variable_reverse'] = ((n.variables[0], m.y), (n.variables[1], m.x), (n.variables[2], m.z))
    elif fault == 'constraint_reverse':
        args['constraint_reverse'] = ((n.constraints[0], m.upper), (n.constraints[1], m.eq), (n.constraints[2], m.lower))
    elif fault == 'duplicate_term': n.rows[0].terms.append(n.rows[0].terms[0])
    elif fault == 'nan': n.variables[0].LB = float('nan')
    elif fault == 'bool_index': n.variables[0].index = False
    elif fault == 'range': m.lower.set_value((-1, m.x, 2))
    elif fault == 'quadratic': m.eq.set_value(m.x**2 == 5)
    elif fault == 'rounded_rhs':
        m.lower.set_value(m.x + 0.1 >= 1.)
        n.constraints[2].RHS = 1. - 0.1
    elif fault == 'lazy': n.constraints[0].Lazy = 1
    elif fault == 'row_constant': n.rows[0].constant = 1.
    else: m.x.setlb(-1e100); n.variables[0].LB = -1e100
    with pytest.raises(api.ExportUnresolved):
        api.check(m, **args)


@pytest.mark.parametrize('attribute', ['NumQConstrs', 'NumSOS', 'NumGenConstrs', 'NumQNZs',
                                      'NumScenarios', 'NumPWLObjVars', 'NumObj', 'ModelSense'])
def test_hidden_native_structure_rejected(attribute):
    m, n, args = case()
    setattr(n, attribute, 2)
    with pytest.raises(api.ExportUnresolved):
        api.check(m, **args)


def test_unbounded_continuous_and_integer_domains():
    from pyomo.environ import Integers
    m, n, args = case()
    m.x.setlb(None); m.x.setub(None)
    n.variables[0].LB, n.variables[0].UB = -1e100, 1e100
    m.y.domain = Integers
    m.y.setlb(0); m.y.setub(1)
    n.variables[1].VType = 'I'
    assert api.check(m, **args)['exact_linear_correspondence_checked']


def test_pinned_origin_and_synthetic_future_rows_fit_strict_linear_protocol(monkeypatch, no_solver):
    from experiments import h1_producer_shape_development_v1 as shape
    from src.rq2_joint_deliverability_boundary_v1 import normal_h1_full_job_v3 as job
    from collections import Counter
    from pyomo.environ import value
    model_api = job.source.h1.model_api
    original = model_api.build_h1_stage_model
    observed = []

    def inspect_model(*args, **kwargs):
        model = original(*args, **kwargs)
        variables, count, _, _ = api._canonical(model)
        senses = Counter()
        for row in model.component_data_objects(Constraint, active=True, descend_into=True):
            assert row.equality or not (row.has_lb() and row.has_ub())
            offset, terms = api._repn(row.body, variables)
            bound = row.lower if row.has_lb() else row.upper
            rhs = api._number(value(bound)) - offset
            assert api._number(float(rhs)) == rhs
            assert len(terms) <= len(variables)
            senses['eq' if row.equality else 'lower' if row.has_lb() else 'upper'] += 1
        observed.append((count, dict(senses)))
        return model

    monkeypatch.setattr(model_api, 'build_h1_stage_model', inspect_model)
    evidence = shape.audit()
    assert observed == [(980, dict(eq=339, upper=638, lower=3)),
                        (1272, dict(eq=631, upper=638, lower=3))]
    assert evidence['counterexample']['synthetic_boundary']
    assert not evidence['counterexample']['reachable_assignment_proven']
