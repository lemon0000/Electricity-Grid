"""Explicit solver configuration for the RQ2 public-data successor."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from importlib.metadata import PackageNotFoundError, version
from math import isfinite
from typing import Any

from pyomo.environ import Constraint, SolverFactory, Var


@dataclass(frozen=True)
class Rq2SolverSpec:
    name: str
    expected_package_version: str
    threads: int
    mip_relative_gap: float
    feasibility_tolerance: float
    optimality_tolerance: float
    integer_feasibility_tolerance: float
    random_seed: int
    time_limit_seconds: float | None
    tee: bool


@dataclass(frozen=True)
class Rq2ModelScale:
    variables: int
    constraints: int


_PACKAGE_BY_SOLVER = {
    "gurobi": "gurobipy",
    "highs": "highspy",
}


def solver_spec(payload: Mapping[str, object]) -> Rq2SolverSpec:
    """Parse and validate the complete solver contract."""

    name = str(payload.get("name", "")).lower()
    if name not in _PACKAGE_BY_SOLVER:
        raise ValueError("RQ2 solver must be 'gurobi' or 'highs'")
    expected_version = payload.get("expected_package_version")
    if not isinstance(expected_version, str) or not expected_version:
        raise ValueError("expected_package_version must be explicit")
    threads = payload.get("threads")
    seed = payload.get("random_seed")
    if isinstance(threads, bool) or not isinstance(threads, int) or threads <= 0:
        raise ValueError("threads must be a positive integer")
    if isinstance(seed, bool) or not isinstance(seed, int) or seed < 0:
        raise ValueError("random_seed must be a nonnegative integer")

    def finite_number(key: str, *, minimum: float = 0.0) -> float:
        raw = payload.get(key)
        if isinstance(raw, bool):
            raise TypeError(f"{key} must be numeric")
        try:
            result = float(raw)
        except (TypeError, ValueError) as error:
            raise ValueError(f"{key} must be numeric") from error
        if not isfinite(result) or result < minimum:
            raise ValueError(f"{key} must be finite and at least {minimum}")
        return result

    mip_gap = finite_number("mip_relative_gap")
    feasibility = finite_number("feasibility_tolerance")
    optimality = finite_number("optimality_tolerance")
    integer = finite_number("integer_feasibility_tolerance")
    if mip_gap > 1.0e-3:
        raise ValueError("mip_relative_gap cannot exceed 1e-3")
    if min(feasibility, optimality, integer) <= 0.0:
        raise ValueError("solver tolerances must be positive")
    raw_limit = payload.get("time_limit_seconds")
    time_limit = None
    if raw_limit is not None:
        time_limit = finite_number("time_limit_seconds")
        if time_limit <= 0.0:
            raise ValueError("time_limit_seconds must be positive when set")
    tee = payload.get("tee")
    if not isinstance(tee, bool):
        raise TypeError("tee must be boolean")
    return Rq2SolverSpec(
        name=name,
        expected_package_version=expected_version,
        threads=threads,
        mip_relative_gap=mip_gap,
        feasibility_tolerance=feasibility,
        optimality_tolerance=optimality,
        integer_feasibility_tolerance=integer,
        random_seed=seed,
        time_limit_seconds=time_limit,
        tee=tee,
    )


def solver_options(spec: Rq2SolverSpec) -> dict[str, float | int]:
    """Return the exact options passed to Pyomo's solver interface."""

    if spec.name == "gurobi":
        options: dict[str, float | int] = {
            "MIPGap": spec.mip_relative_gap,
            "MIPGapAbs": 0.0,
            "Seed": spec.random_seed,
            "Threads": spec.threads,
            "FeasibilityTol": spec.feasibility_tolerance,
            "OptimalityTol": spec.optimality_tolerance,
            "IntFeasTol": spec.integer_feasibility_tolerance,
        }
        if spec.time_limit_seconds is not None:
            options["TimeLimit"] = spec.time_limit_seconds
        return options
    options = {
        "mip_rel_gap": spec.mip_relative_gap,
        "mip_abs_gap": 0.0,
        "random_seed": spec.random_seed,
        "threads": spec.threads,
        "primal_feasibility_tolerance": spec.feasibility_tolerance,
        "dual_feasibility_tolerance": spec.optimality_tolerance,
        "mip_feasibility_tolerance": spec.integer_feasibility_tolerance,
    }
    if spec.time_limit_seconds is not None:
        options["time_limit"] = spec.time_limit_seconds
    return options


def create_solver(spec: Rq2SolverSpec) -> tuple[Any, dict[str, float | int]]:
    """Create a version-checked Pyomo solver and its explicit option map."""

    package = _PACKAGE_BY_SOLVER[spec.name]
    try:
        observed_version = version(package)
    except PackageNotFoundError as error:
        raise RuntimeError(
            f"required solver package is unavailable: {package}"
        ) from error
    if observed_version != spec.expected_package_version:
        raise RuntimeError(
            f"{package} version drifted: expected {spec.expected_package_version}, "
            f"observed {observed_version}"
        )
    solver = SolverFactory(spec.name)
    if not solver.available(exception_flag=False):
        raise RuntimeError(f"Pyomo solver interface is unavailable: {spec.name}")
    return solver, solver_options(spec)


def model_scale(model: Any) -> Rq2ModelScale:
    """Count active scalar variables and constraints in a built Pyomo model."""

    return Rq2ModelScale(
        variables=sum(
            1
            for _ in model.component_data_objects(
                Var,
                active=True,
                descend_into=True,
            )
        ),
        constraints=sum(
            1
            for _ in model.component_data_objects(
                Constraint,
                active=True,
                descend_into=True,
            )
        ),
    )
