"""Reusable invariants for exact selected-state constraint generation."""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Mapping, Sequence

from pyomo.core.expr.visitor import identify_variables
from pyomo.environ import Constraint, Objective, TransformationFactory, Var, value

from src.solvers.mip_progress import certified_bound_interval

NORMAL_STATE_ID = "normal"
STATE_VARIABLE_COMPONENTS = frozenset(
    {"generation", "angle_degrees", "branch_flow", "dc_flow"}
)
ALL_VARIABLE_COMPONENTS = frozenset(
    {
        "commitment",
        "startup",
        "shutdown",
        "generation",
        "angle_degrees",
        "branch_flow",
        "dc_flow",
        "reserve_up",
        "segment_power",
        "reactive_proxy",
    }
)
SHARED_COMPONENTS = frozenset(
    {
        "commitment",
        "startup",
        "shutdown",
        "segment_power",
        "reserve_up",
        "reactive_proxy",
    }
)
STAGES = frozenset(
    {
        "proxy_maximization",
        "cost_normalization",
        "level_set_cost_minimization",
        "level_set_budget_feasibility",
    }
)


@dataclass(frozen=True)
class SharedSnapshot:
    values: tuple[tuple[str, tuple[object, ...], float], ...]
    sha256: str
    reactive_proxy: float
    operating_cost_usd: float


def _stable_scalar(item: object) -> object:
    if isinstance(item, dict):
        return {
            str(key): _stable_scalar(value_) for key, value_ in sorted(item.items())
        }
    if isinstance(item, (list, tuple)):
        return [_stable_scalar(value_) for value_ in item]
    return item


def structured_sha256(payload: object) -> str:
    encoded = json.dumps(
        _stable_scalar(payload),
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def normalized_index(index: object) -> tuple[object, ...]:
    if index is None:
        return ()
    return index if isinstance(index, tuple) else (index,)


def variable_state(variable: Any) -> str | None:
    component = variable.parent_component().local_name
    if component not in STATE_VARIABLE_COMPONENTS:
        return None
    index = normalized_index(variable.index())
    if not index:
        raise RuntimeError(f"State variable {variable.name} has no state index")
    return str(index[0])


def assert_conditionally_independent_recourse(model: Any) -> None:
    components = {
        variable.parent_component().local_name
        for variable in model.component_data_objects(Var, active=True)
    }
    if components != ALL_VARIABLE_COMPONENTS:
        raise RuntimeError(
            "Variable contract drifted; recourse independence cannot be proven"
        )
    for constraint in model.component_data_objects(
        Constraint, active=True, descend_into=True
    ):
        nonnormal = {
            state
            for variable in identify_variables(constraint.body, include_fixed=True)
            if (state := variable_state(variable)) not in (None, NORMAL_STATE_ID)
        }
        if len(nonnormal) > 1:
            raise RuntimeError(
                "Cross-contingency shared recourse detected in constraint "
                f"{constraint.name}: {sorted(nonnormal)}"
            )
    for objective in model.component_data_objects(
        Objective, active=True, descend_into=True
    ):
        nonnormal = {
            state
            for variable in identify_variables(objective.expr, include_fixed=True)
            if (state := variable_state(variable)) not in (None, NORMAL_STATE_ID)
        }
        if nonnormal:
            raise RuntimeError(
                f"Objective {objective.name} depends on contingency recourse"
            )


def shared_variable_items(
    model: Any,
) -> tuple[tuple[str, tuple[object, ...], Any], ...]:
    items = []
    for component_name in sorted(ALL_VARIABLE_COMPONENTS):
        component = getattr(model, component_name)
        for variable in component.values():
            index = normalized_index(variable.index())
            if component_name in STATE_VARIABLE_COMPONENTS:
                if not index or str(index[0]) != NORMAL_STATE_ID:
                    continue
            elif component_name not in SHARED_COMPONENTS:
                continue
            items.append((component_name, index, variable))
    return tuple(items)


def _snapshot_payload(
    values: Sequence[tuple[str, tuple[object, ...], float]],
) -> list[dict[str, object]]:
    return [
        {
            "component": component,
            "index": list(index),
            "value_float_hex": float(number).hex(),
        }
        for component, index, number in values
    ]


def extract_shared_snapshot(model: Any) -> SharedSnapshot:
    values = []
    for component, index, variable in shared_variable_items(model):
        candidate = value(variable, exception=False)
        if candidate is None or not math.isfinite(float(candidate)):
            raise RuntimeError(f"Shared variable {variable.name} is not finite")
        values.append((component, index, float(candidate)))
    proxy = float(value(model.reactive_proxy))
    operating_cost = float(value(model.operating_cost))
    if not math.isfinite(proxy) or not math.isfinite(operating_cost):
        raise RuntimeError("Shared objective values are not finite")
    return SharedSnapshot(
        values=tuple(values),
        sha256=structured_sha256(_snapshot_payload(values)),
        reactive_proxy=proxy,
        operating_cost_usd=operating_cost,
    )


def apply_shared_snapshot(model: Any, snapshot: SharedSnapshot) -> None:
    target = {
        (component, index): variable
        for component, index, variable in shared_variable_items(model)
    }
    source = {
        (component, index): number for component, index, number in snapshot.values
    }
    if set(target) != set(source):
        missing = sorted(set(source) - set(target), key=repr)
        extra = sorted(set(target) - set(source), key=repr)
        raise RuntimeError(
            f"Shared variable contract drifted; missing={missing}, extra={extra}"
        )
    for key, variable in target.items():
        variable.fix(source[key])


def shared_snapshot_violation(model: Any, snapshot: SharedSnapshot) -> float:
    target = {
        (component, index): variable
        for component, index, variable in shared_variable_items(model)
    }
    if set(target) != {
        (component, index) for component, index, _number in snapshot.values
    }:
        return math.inf
    maximum = 0.0
    for component, index, expected in snapshot.values:
        observed = value(target[(component, index)], exception=False)
        if observed is None or not math.isfinite(float(observed)):
            return math.inf
        maximum = max(maximum, abs(float(observed) - expected))
    return maximum


def relax_fixed_integer_variables(model: Any) -> None:
    unfixed = [
        variable.name
        for variable in model.component_data_objects(Var, active=True)
        if not variable.is_continuous() and not variable.fixed
    ]
    if unfixed:
        raise RuntimeError(
            "Fixed-shared verification contains unfixed integer variables: "
            + ", ".join(unfixed[:5])
        )
    TransformationFactory("core.relax_integer_vars").apply_to(model)


def orient_bound_interval(
    *,
    sense: str,
    raw_lower_bound: object,
    raw_upper_bound: object,
    incumbent_objective: object,
    consistency_tolerance: float,
) -> dict[str, object]:
    def optional_float(item: object) -> float | None:
        try:
            candidate = float(item)
        except (TypeError, ValueError):
            return None
        return candidate if math.isfinite(candidate) else None

    lower = optional_float(raw_lower_bound)
    upper = optional_float(raw_upper_bound)
    incumbent = optional_float(incumbent_objective)
    if sense not in {"maximize", "minimize"}:
        raise ValueError(f"Unknown objective sense {sense}")
    if lower is None or upper is None or incumbent is None:
        return {
            "bound_valid": False,
            "dual_bound": None,
            "certified_lower_bound": None,
            "certified_upper_bound": None,
            "absolute_gap": None,
            "relative_gap": None,
            "relative_gap_to_incumbent": None,
            "raw_primal_bound_consistent": False,
        }
    raw_primal = lower if sense == "maximize" else upper
    dual = upper if sense == "maximize" else lower
    scale = max(abs(raw_primal), abs(incumbent), 1.0)
    consistent = abs(raw_primal - incumbent) <= consistency_tolerance * scale
    try:
        interval = (
            certified_bound_interval(incumbent, dual)
            if sense == "maximize"
            else certified_bound_interval(dual, incumbent)
        )
    except ValueError:
        interval = None
    return {
        "bound_valid": bool(consistent and interval is not None),
        "dual_bound": dual,
        "certified_lower_bound": interval.lower_bound if interval else None,
        "certified_upper_bound": interval.upper_bound if interval else None,
        "absolute_gap": interval.absolute_gap if interval else None,
        "relative_gap": interval.relative_gap if interval else None,
        "relative_gap_to_incumbent": (
            interval.absolute_gap / max(abs(incumbent), 1.0e-12) if interval else None
        ),
        "raw_primal_bound_consistent": consistent,
    }


def screen_plan(
    *, stage: str, all_state_ids: Sequence[str], active_state_ids: Sequence[str]
) -> tuple[str, ...]:
    if stage not in STAGES:
        raise ValueError(f"Unknown screen stage {stage}")
    active = set(active_state_ids)
    if NORMAL_STATE_ID not in active:
        raise ValueError("Screen plan requires normal in the active set")
    return tuple(state_id for state_id in all_state_ids if state_id not in active)


def promotions(
    screen_records: Sequence[Mapping[str, object]], all_state_ids: Sequence[str]
) -> tuple[dict[str, str], ...]:
    by_state = {
        str(record["state_id"]): str(record["status"]) for record in screen_records
    }
    promoted = []
    for state_id in all_state_ids:
        status = by_state.get(state_id)
        if status == "certified_infeasible":
            promoted.append({"state_id": state_id, "reason": "certified_infeasible"})
        elif status == "unresolved":
            promoted.append({"state_id": state_id, "reason": "unresolved_promoted"})
    return tuple(promoted)


def final_max_certificate(
    *,
    full_feasible_objective: object,
    master_dual_upper_bounds: Sequence[object],
    target_relative_gap: float,
) -> dict[str, object]:
    try:
        objective = float(full_feasible_objective)
    except (TypeError, ValueError):
        objective = math.nan
    bounds = []
    for item in master_dual_upper_bounds:
        try:
            parsed = float(item)
        except (TypeError, ValueError):
            parsed = math.nan
        bounds.append(parsed)
    if (
        not math.isfinite(objective)
        or not bounds
        or any(not math.isfinite(item) for item in bounds)
    ):
        return {
            "valid": False,
            "lower_bound": objective if math.isfinite(objective) else None,
            "upper_bound": None,
            "absolute_gap": None,
            "relative_gap": None,
            "relative_gap_to_feasible_incumbent": None,
            "proxy_percentage_point_width": None,
            "target_gap_attained": False,
        }
    upper = min(bounds)
    try:
        interval = certified_bound_interval(objective, upper)
    except ValueError:
        return {
            "valid": False,
            "lower_bound": objective,
            "upper_bound": upper,
            "absolute_gap": None,
            "relative_gap": None,
            "relative_gap_to_feasible_incumbent": None,
            "proxy_percentage_point_width": None,
            "target_gap_attained": False,
        }
    return {
        "valid": True,
        "lower_bound": interval.lower_bound,
        "upper_bound": interval.upper_bound,
        "absolute_gap": interval.absolute_gap,
        "relative_gap": interval.relative_gap,
        "relative_gap_to_feasible_incumbent": interval.absolute_gap
        / max(abs(objective), 1.0e-12),
        "proxy_percentage_point_width": 100.0 * interval.absolute_gap,
        "target_gap_attained": interval.relative_gap <= float(target_relative_gap),
    }


def final_min_certificate(
    *,
    full_feasible_objective: object,
    master_dual_lower_bounds: Sequence[object],
    target_relative_gap: float,
) -> dict[str, object]:
    try:
        objective = float(full_feasible_objective)
    except (TypeError, ValueError):
        objective = math.nan
    bounds = []
    for item in master_dual_lower_bounds:
        try:
            parsed = float(item)
        except (TypeError, ValueError):
            parsed = math.nan
        bounds.append(parsed)
    if (
        not math.isfinite(objective)
        or not bounds
        or any(not math.isfinite(item) for item in bounds)
    ):
        return {
            "valid": False,
            "lower_bound": None,
            "upper_bound": objective if math.isfinite(objective) else None,
            "absolute_gap": None,
            "relative_gap": None,
            "relative_gap_to_feasible_incumbent": None,
            "target_gap_attained": False,
        }
    lower = max(bounds)
    try:
        interval = certified_bound_interval(lower, objective)
    except ValueError:
        return {
            "valid": False,
            "lower_bound": lower,
            "upper_bound": objective,
            "absolute_gap": None,
            "relative_gap": None,
            "relative_gap_to_feasible_incumbent": None,
            "target_gap_attained": False,
        }
    return {
        "valid": True,
        "lower_bound": interval.lower_bound,
        "upper_bound": interval.upper_bound,
        "absolute_gap": interval.absolute_gap,
        "relative_gap": interval.relative_gap,
        "relative_gap_to_feasible_incumbent": interval.absolute_gap
        / max(abs(objective), 1.0e-12),
        "target_gap_attained": interval.relative_gap <= float(target_relative_gap),
    }


__all__ = [
    "ALL_VARIABLE_COMPONENTS",
    "NORMAL_STATE_ID",
    "SHARED_COMPONENTS",
    "STAGES",
    "STATE_VARIABLE_COMPONENTS",
    "SharedSnapshot",
    "apply_shared_snapshot",
    "assert_conditionally_independent_recourse",
    "extract_shared_snapshot",
    "final_max_certificate",
    "final_min_certificate",
    "orient_bound_interval",
    "promotions",
    "relax_fixed_integer_variables",
    "screen_plan",
    "shared_snapshot_violation",
    "shared_variable_items",
    "structured_sha256",
]
