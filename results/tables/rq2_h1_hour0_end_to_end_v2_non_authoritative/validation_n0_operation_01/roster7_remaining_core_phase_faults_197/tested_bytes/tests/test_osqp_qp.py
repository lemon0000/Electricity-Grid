import osqp
import pyomo.environ as pyo
import pytest

from src.solvers import (
    OsqpQpWorkspace,
    linear_expression_after_fixing_quadratics,
    solve_separable_convex_qp,
)


def test_osqp_adapter_solves_and_loads_a_bounded_convex_qp():
    model = pyo.ConcreteModel()
    model.x = pyo.Var(bounds=(0.0, 10.0))
    model.y = pyo.Var(bounds=(0.0, 10.0))
    model.fixed = pyo.Var(initialize=2.0)
    model.fixed.fix(2.0)
    model.balance = pyo.Constraint(expr=model.x + model.y + model.fixed == 5.0)
    model.band = pyo.Constraint(expr=(-1.0, model.x - model.y, 2.0))
    model.objective = pyo.Objective(
        expr=(
            model.x**2
            + 2.0 * model.y**2
            - 2.0 * model.x
            - 8.0 * model.y
            + 7.0 * model.fixed
        )
    )

    result = solve_separable_convex_qp(model)

    assert result.solved
    assert result.status == "solved"
    assert result.max_constraint_violation <= 1.0e-6
    assert result.primal_residual <= 1.0e-6
    assert pyo.value(model.x) == pytest.approx(1.0, abs=1.0e-7)
    assert pyo.value(model.y) == pytest.approx(2.0, abs=1.0e-7)
    assert result.objective_value == pytest.approx(5.0)


def test_osqp_adapter_reports_an_infeasible_linear_system():
    model = pyo.ConcreteModel()
    model.x = pyo.Var(bounds=(0.0, 1.0))
    model.impossible = pyo.Constraint(expr=model.x >= 2.0)
    model.objective = pyo.Objective(expr=model.x**2)

    result = solve_separable_convex_qp(model)

    assert not result.solved
    assert "infeasible" in result.status
    assert result.objective_value is None


def test_osqp_adapter_rejects_a_nonfinite_objective_constant():
    model = pyo.ConcreteModel()
    model.x = pyo.Var(bounds=(0.0, 1.0))
    model.objective = pyo.Objective(expr=model.x**2 + float("inf"))

    with pytest.raises(ValueError, match="finite objective constant"):
        solve_separable_convex_qp(model)


@pytest.mark.parametrize(
    "expression, message",
    (
        (lambda variable: float("inf") * variable, "linear objective"),
        (lambda variable: float("inf") * variable**2, "quadratic objective"),
    ),
)
def test_osqp_adapter_rejects_nonfinite_objective_coefficients(
    expression,
    message,
):
    model = pyo.ConcreteModel()
    model.x = pyo.Var(bounds=(0.0, 1.0))
    model.objective = pyo.Objective(expr=expression(model.x))

    with pytest.raises(ValueError, match=message):
        solve_separable_convex_qp(model)


def test_osqp_workspace_reuses_bounds_and_matches_a_fresh_solve():
    model = _reusable_qp_model()
    workspace = OsqpQpWorkspace()

    first = workspace.solve(model)
    model.fixed.set_value(1.0)
    reused = workspace.solve(model)
    reused_values = (pyo.value(model.x), pyo.value(model.y))
    fresh = solve_separable_convex_qp(model)

    assert first.solved
    assert not first.workspace_reused
    assert not first.warm_started
    assert reused.solved
    assert reused.workspace_reused
    assert reused.warm_started
    assert fresh.solved
    assert reused.objective_value == pytest.approx(fresh.objective_value)
    assert reused_values == pytest.approx((pyo.value(model.x), pyo.value(model.y)))


@pytest.mark.parametrize(
    "mutation, changed_component",
    (
        (lambda model: model.x.setub(9.0), "variable bounds"),
        (lambda model: _change_hessian(model), "P"),
        (lambda model: _change_linear_cost(model), "q"),
        (lambda model: _change_constraint_matrix(model), "A"),
        (lambda model: _add_variable(model), "variables"),
        (lambda model: _replace_objective(model), "objective"),
    ),
)
def test_osqp_workspace_rejects_structural_changes(
    mutation,
    changed_component,
):
    model = _reusable_qp_model()
    workspace = OsqpQpWorkspace()
    assert workspace.solve(model).solved

    mutation(model)

    with pytest.raises(
        ValueError,
        match=rf"structure changed: {changed_component}",
    ):
        workspace.solve(model)


def test_osqp_workspace_does_not_warm_start_from_an_infeasibility_certificate():
    model = _reusable_qp_model()
    workspace = OsqpQpWorkspace(max_iter=1_000)
    assert workspace.solve(model).solved

    model.fixed.set_value(20.0)
    infeasible = workspace.solve(model)
    model.fixed.set_value(2.0)
    recovered = workspace.solve(model)

    assert not infeasible.solved
    assert "infeasible" in infeasible.status
    assert recovered.solved
    assert recovered.workspace_reused
    assert not recovered.warm_started


def test_osqp_adapter_rejects_a_bound_projection_above_tolerance(monkeypatch):
    original_solve = osqp.OSQP.solve

    def solve_with_large_bound_projection(solver, *args, **kwargs):
        raw_result = original_solve(solver, *args, **kwargs)
        raw_result.x[0] = -1.0e-3
        return raw_result

    monkeypatch.setattr(osqp.OSQP, "solve", solve_with_large_bound_projection)
    model = pyo.ConcreteModel()
    model.x = pyo.Var(bounds=(0.0, 10.0))
    model.objective = pyo.Objective(expr=model.x**2)

    result = solve_separable_convex_qp(
        model,
        feasibility_tolerance=1.0e-5,
    )

    assert result.status == "solved"
    assert not result.solved
    assert result.objective_value is None
    assert result.max_constraint_violation == pytest.approx(0.0)
    assert result.bound_projection_count == 1
    assert result.max_bound_projection == pytest.approx(1.0e-3)


def test_osqp_adapter_wraps_native_solver_exceptions(monkeypatch):
    def raise_native_exception(*args, **kwargs):
        raise osqp.OSQPException("forced solve failure")

    monkeypatch.setattr(osqp.OSQP, "solve", raise_native_exception)
    model = pyo.ConcreteModel()
    model.x = pyo.Var(bounds=(0.0, 1.0))
    model.objective = pyo.Objective(expr=model.x**2)

    with pytest.raises(RuntimeError, match="workspace solve failed"):
        solve_separable_convex_qp(model)


def test_linear_expression_is_available_after_quadratic_coordinates_are_fixed():
    model = pyo.ConcreteModel()
    model.x = pyo.Var(initialize=2.0)
    model.y = pyo.Var(initialize=3.0)
    expression = model.x**2 + 4.0 * model.y + 1.0

    model.x.fix(2.0)
    linear = linear_expression_after_fixing_quadratics(expression)

    model.y.set_value(5.0)
    assert pyo.value(linear) == pytest.approx(25.0)


@pytest.mark.parametrize(
    "build_model, message",
    (
        (
            lambda: _integer_model(),
            "continuous variables",
        ),
        (
            lambda: _cross_quadratic_model(),
            "separable quadratic objectives",
        ),
        (
            lambda: _concave_model(),
            "convex quadratic objective",
        ),
        (
            lambda: _quadratic_constraint_model(),
            "linear constraints",
        ),
    ),
)
def test_osqp_adapter_rejects_models_outside_its_supported_scope(
    build_model,
    message,
):
    with pytest.raises(ValueError, match=message):
        solve_separable_convex_qp(build_model())


def _integer_model():
    model = pyo.ConcreteModel()
    model.x = pyo.Var(domain=pyo.Integers)
    model.objective = pyo.Objective(expr=model.x**2)
    return model


def _cross_quadratic_model():
    model = pyo.ConcreteModel()
    model.x = pyo.Var()
    model.y = pyo.Var()
    model.objective = pyo.Objective(expr=model.x**2 + model.x * model.y + model.y**2)
    return model


def _concave_model():
    model = pyo.ConcreteModel()
    model.x = pyo.Var()
    model.objective = pyo.Objective(expr=-(model.x**2))
    return model


def _quadratic_constraint_model():
    model = pyo.ConcreteModel()
    model.x = pyo.Var()
    model.limit = pyo.Constraint(expr=model.x**2 <= 1.0)
    model.objective = pyo.Objective(expr=model.x**2)
    return model


def _reusable_qp_model():
    model = pyo.ConcreteModel()
    model.x = pyo.Var(bounds=(0.0, 10.0))
    model.y = pyo.Var(bounds=(0.0, 10.0))
    model.fixed = pyo.Var(initialize=2.0)
    model.fixed.fix(2.0)
    model.balance = pyo.Constraint(expr=model.x + model.y + model.fixed == 5.0)
    model.band = pyo.Constraint(expr=(-1.0, model.x - model.y, 2.0))
    model.objective = pyo.Objective(
        expr=(
            model.x**2
            + 2.0 * model.y**2
            - 2.0 * model.x
            - 8.0 * model.y
            + 7.0 * model.fixed
        )
    )
    return model


def _change_hessian(model):
    model.objective.set_value(
        1.5 * model.x**2
        + 2.0 * model.y**2
        - 2.0 * model.x
        - 8.0 * model.y
        + 7.0 * model.fixed
    )


def _change_linear_cost(model):
    model.objective.set_value(
        model.x**2
        + 2.0 * model.y**2
        - 3.0 * model.x
        - 8.0 * model.y
        + 7.0 * model.fixed
    )


def _change_constraint_matrix(model):
    model.balance.set_value(model.x + 2.0 * model.y + model.fixed == 5.0)


def _add_variable(model):
    model.extra = pyo.Var()


def _replace_objective(model):
    expression = model.objective.expr
    model.objective.deactivate()
    model.replacement_objective = pyo.Objective(expr=expression)
