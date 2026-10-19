from fractions import Fraction
from math import nextafter, inf

import pytest
from pyomo.environ import ConcreteModel, Var, Objective, Constraint, Binary, Reals, value
from pyomo.opt import TerminationCondition, SolutionStatus, SolverStatus

from src.solvers import rq2_objective_provenance_v1 as api
from src.solvers.rq2_solver_adapter import Rq2SolverSpec


@pytest.mark.parametrize('mip', [False, True])
@pytest.mark.parametrize('offset', [0., -3., -2.])
def test_real_direct_channels_and_exact_assignment(mip, offset, monkeypatch):
    model = ConcreteModel()
    model.x = Var(bounds=(0, 1), domain=Binary if mip else Reals)
    model.required = Constraint(expr=model.x >= 1)
    model.cost = Objective(expr=2 * model.x + offset)
    spec = Rq2SolverSpec('gurobi', '13.0.2', 1, 1e-8, 1e-9, 1e-9, 1e-9, 0, 1., False)
    solver, options = api.adapter.create_solver(spec)
    try:
        results = solver.solve(model, load_solutions=False, options=options)
        model.solutions.load_from(results)
        before = value(model.x)
        def forbidden(*args, **kwargs):
            raise AssertionError('collector must not solve or load')
        monkeypatch.setattr(solver, 'solve', forbidden)
        monkeypatch.setattr(model.solutions, 'load_from', forbidden)
        report = api.capture_direct(solver, results, model)
        assert report['native_status'] == 2
        assert report['canonical_objective_hex'] == (2. + offset).hex()
        assert report['exact_objective'] == {'numerator': str(int(2 + offset)), 'denominator': '1'}
        assert report['native_exact_objective'] == report['exact_objective']
        assert report['native_exact_value_equals_canonical_exact_value']
        assert report['native_algebra_equals_canonical_algebra']
        assert report['optimal_status_channels_consistent']
        assert report['pyomo_solution_status'] == 'optimal'
        assert report['comparisons']['native_to_pyomo_lower_hex_equal']
        assert report['comparisons']['native_to_pyomo_upper_hex_equal']
        assert report['pyomo_lower_source'] == ('ObjBound' if mip else 'ObjVal')
        assert report['referenced_assignment'] == [('x', 1.0.hex())]
        assert report['solver_calls_by_collector'] == 0
        assert not report['optimality_certified'] and not report['formal_result']
        assert value(model.x) == before
        results.solution[0].status = SolutionStatus.feasible
        assert not api.capture_direct(solver, results, model)['optimal_status_channels_consistent']
        results.solution[0].status = SolutionStatus.optimal
        results.solver.status = SolverStatus.warning
        assert not api.capture_direct(solver, results, model)['optimal_status_channels_consistent']
        results.solver.status = SolverStatus.ok
        # A changed wrapper status cannot turn provenance into certification.
        results.solver.termination_condition = TerminationCondition.maxTimeLimit
        timeout = api.capture_direct(solver, results, model)
        assert timeout['pyomo_termination'] == 'maxTimeLimit'
        assert timeout['native_status'] == 2
        assert not timeout['optimality_certified']
        assert not timeout['optimal_status_channels_consistent']
        # Synthetic TIME_LIMIT native channel; this is not a timed-out real run.
        original_native = solver._solver_model
        class TimeoutView:
            Status = 9
            def __getattr__(self, name):
                return getattr(original_native, name)
        solver._solver_model = TimeoutView()
        try:
            timeout = api.capture_direct(solver, results, model)
            assert timeout['native_status'] == 9
            assert timeout['pyomo_termination'] == 'maxTimeLimit'
            assert not timeout['optimality_certified']
            assert not timeout['optimal_status_channels_consistent']
        finally:
            solver._solver_model = original_native
        # Wrapper conversion drift is recorded, not normalized.
        results.problem[0].upper_bound = nextafter(2. + offset, inf)
        assert not api.capture_direct(solver, results, model)['comparisons']['native_to_pyomo_upper_hex_equal']
        # Objective mutation after solve must remain visible in both inventories.
        model.cost.set_value(3 * model.x + offset)
        changed = api.capture_direct(solver, results, model)
        assert not changed['native_exact_value_equals_canonical_exact_value']
        assert changed['ordered_native_objective_terms'] != changed['ordered_objective_terms']
        model.cost.set_value(3 * model.x + offset - 1)
        compensated = api.capture_direct(solver, results, model)
        assert compensated['native_exact_value_equals_canonical_exact_value']
        assert not compensated['native_algebra_equals_canonical_algebra']
        model.x.set_value(.5, skip_validation=True)
        with pytest.raises(ValueError, match='assignment differs'):
            api.capture_direct(solver, results, model)
    finally:
        solver.close()


@pytest.mark.parametrize('objective', [1388837.913859345, -1., 0.])
def test_one_ulp_crossing_is_preserved(objective):
    lower = nextafter(objective, inf)
    upper = nextafter(lower, inf)
    report = api.compare_channels(native_objective=upper, native_bound=lower,
        pyomo_lower=lower, pyomo_upper=upper, canonical_objective=objective,
        exact_objective=Fraction.from_float(objective))
    assert report['native_to_pyomo_lower_hex_equal']
    assert report['native_to_pyomo_upper_hex_equal']
    assert report['lower_le_upper']
    assert not report['lower_le_canonical'] and not report['lower_le_exact']
    assert Fraction(report['exact_minus_lower']) < 0


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), -float('inf')])
def test_nonfinite_channel_rejected(bad):
    with pytest.raises(ValueError, match='finite'):
        api.compare_channels(native_objective=bad, native_bound=0.,
            pyomo_lower=0., pyomo_upper=0., canonical_objective=0.,
            exact_objective=Fraction(0))


@pytest.mark.parametrize('error', [AttributeError('absent'), api.GurobiError(api.GRB.Error.DATA_NOT_AVAILABLE, 'absent')])
def test_unavailable_native_attribute_is_explicit(error):
    class Missing:
        def __getattr__(self, name):
            raise error
    assert api._attribute(Missing(), 'ObjBoundC')['available'] is False
    assert api._attribute(Missing(), 'ObjBoundC')['hex'] is None


def test_unexpected_native_error_propagates():
    class Broken:
        def __getattr__(self, name):
            raise api.GurobiError(10001, 'unexpected')
    with pytest.raises(api.GurobiError):
        api._attribute(Broken(), 'ObjBoundC')


def test_algebra_aggregates_duplicates_and_ignores_order():
    split = [('x', 1.0.hex(), 2.0.hex()), ('y', 0.0.hex(), 3.0.hex()), ('x', 2.0.hex(), 2.0.hex())]
    assert api._algebra(0., split) == api._algebra(0., [('x', 3.0.hex(), 2.0.hex())])
