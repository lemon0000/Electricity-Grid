"""Input mapping and scenario construction for the RQ2 V5 design."""

from __future__ import annotations

import csv
import gzip
import re
from dataclasses import dataclass, replace
from itertools import product
from math import fsum, isclose, isfinite
from pathlib import Path
from typing import Any

from .model import (
    CFE_ONLY_SHARED,
    JOINT_B6_SEPARATE_PLANNING_SHARED_EXECUTION,
    JOINT_CORRECT_SHARED,
    NETWORK_ONLY_SHARED,
    JointDeliverabilityPlanningInputs,
    JointDeliverabilityScenario,
    effective_request,
)

FINITE_GRID_NEED = "finite_grid_need"
EXOGENOUS_GRID_INFEASIBILITY = "exogenous_grid_infeasibility"
_GRID_STATES = {FINITE_GRID_NEED, EXOGENOUS_GRID_INFEASIBILITY}


@dataclass(frozen=True)
class RegisteredCell:
    cell_id: str
    family: str
    hourly_cfe_target: float
    flexible_fraction: float
    normalized_recovery_headroom: float
    recovery_efficiency: float
    maximum_event_duration_hours: float
    maximum_event_count: int
    normalized_energy_budget: float
    normalized_debt_limit: float


@dataclass(frozen=True)
class PowerBlock:
    block_id: str
    split: str
    probability: float
    source_hours: tuple[int, ...]
    cfe_call_fraction_at_alpha_1: tuple[float, ...]
    grid_need: tuple[float | None, ...]
    state: str


@dataclass(frozen=True)
class WorkloadBlock:
    block_id: str
    split: str
    probability: float
    source_relative_hours: tuple[int, ...]
    raw_workload_fraction: tuple[float, ...]


def _finite_float(
    raw: object,
    label: str,
    *,
    minimum: float = 0.0,
    maximum: float | None = None,
) -> float:
    if isinstance(raw, bool):
        raise TypeError(f"{label} must be numeric")
    try:
        result = float(raw)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be numeric") from error
    if (
        not isfinite(result)
        or result < minimum
        or (maximum is not None and result > maximum)
    ):
        raise ValueError(f"{label} is outside its registered domain")
    return result


def _integer(
    raw: object,
    label: str,
    *,
    minimum: int = 0,
    maximum: int | None = None,
) -> int:
    if isinstance(raw, bool):
        raise TypeError(f"{label} must be an integer")
    text = str(raw).strip()
    if re.fullmatch(r"[+]?[0-9]+", text) is None:
        raise ValueError(f"{label} must use canonical integer syntax")
    result = int(text)
    if result < minimum or (maximum is not None and result > maximum):
        raise ValueError(f"{label} is outside its registered domain")
    return result


def _marginal(path: Path) -> tuple[tuple[str, float], ...]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != ["id", "probability"]:
            raise ValueError(f"{path} marginal schema drifted")
        rows = list(reader)
    result: list[tuple[str, float]] = []
    seen: set[str] = set()
    for row in rows:
        block_id = row["id"]
        if not block_id or block_id in seen:
            raise ValueError(f"{path} contains an empty or duplicate block ID")
        seen.add(block_id)
        result.append(
            (
                block_id,
                _finite_float(
                    row["probability"],
                    f"{path} probability",
                    maximum=1.0,
                ),
            )
        )
    if not result or not isclose(
        fsum(probability for _, probability in result),
        1.0,
        rel_tol=0.0,
        abs_tol=1.0e-9,
    ):
        raise ValueError(f"{path} marginal probability mass drifted")
    return tuple(result)


def _hourly_rows(
    path: Path,
    required_columns: tuple[str, ...],
) -> dict[str, list[dict[str, str]]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None or not set(required_columns).issubset(
            reader.fieldnames
        ):
            raise ValueError(f"{path} hourly schema drifted")
        rows = list(reader)
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        block_id = row["block_id"]
        if not block_id:
            raise ValueError(f"{path} contains an empty block ID")
        if row["split"] not in {"training", "holdout"}:
            raise ValueError(f"{path} contains an invalid split label")
        grouped.setdefault(block_id, []).append(row)
    if not grouped:
        raise ValueError(f"{path} contains no blocks")
    for block_id, block_rows in grouped.items():
        if len(block_rows) != 24:
            raise ValueError(f"{block_id} must contain exactly 24 rows")
        parsed = [
            (
                _integer(
                    row["hour_offset"],
                    f"{block_id} hour_offset",
                    maximum=23,
                ),
                row,
            )
            for row in block_rows
        ]
        if {offset for offset, _ in parsed} != set(range(24)):
            raise ValueError(f"{block_id} hour offsets are not exactly 0..23")
        block_rows[:] = [row for _, row in sorted(parsed, key=lambda item: item[0])]
        if len({row["split"] for row in block_rows}) != 1:
            raise ValueError(f"{block_id} has mixed split labels")
    return grouped


def lift_power_block_state(hourly_states: tuple[str, ...]) -> str:
    """Lift one registered hourly E0 state to the complete power block."""

    if len(hourly_states) != 24 or any(
        state not in _GRID_STATES for state in hourly_states
    ):
        raise ValueError("power block hourly state inventory drifted")
    if EXOGENOUS_GRID_INFEASIBILITY in hourly_states:
        return EXOGENOUS_GRID_INFEASIBILITY
    return FINITE_GRID_NEED


def load_power_blocks(package: Path, split: str) -> tuple[PowerBlock, ...]:
    """Load the exact V5 power schema and preserve E0 as a block state."""

    if split not in {"training", "holdout"}:
        raise ValueError("power split must be training or holdout")
    marginal = _marginal(package / f"{split}_marginal.csv.gz")
    grouped = _hourly_rows(
        package / "dispatched_power_system_blocks.csv.gz",
        (
            "block_id",
            "split",
            "hour_offset",
            "source_hour",
            "cfe_call_fraction",
            "grid_need_fraction",
            "dispatch_state",
        ),
    )
    split_ids = {
        block_id for block_id, rows in grouped.items() if rows[0]["split"] == split
    }
    marginal_ids = {block_id for block_id, _ in marginal}
    if split_ids != marginal_ids:
        raise ValueError("power hourly and marginal block inventories differ")
    blocks = []
    for block_id, probability in marginal:
        rows = grouped[block_id]
        states = tuple(row["dispatch_state"] for row in rows)
        state = lift_power_block_state(states)
        grid_need: list[float | None] = []
        for row_state, row in zip(states, rows, strict=True):
            raw_grid = row["grid_need_fraction"]
            if row_state == EXOGENOUS_GRID_INFEASIBILITY:
                if raw_grid != "":
                    raise ValueError("E0 hour must have an empty grid need")
                grid_need.append(None)
            else:
                grid_need.append(
                    _finite_float(
                        raw_grid,
                        "grid_need_fraction",
                        maximum=1.0,
                    )
                )
        blocks.append(
            PowerBlock(
                block_id=block_id,
                split=split,
                probability=probability,
                source_hours=tuple(
                    _integer(row["source_hour"], "source_hour") for row in rows
                ),
                cfe_call_fraction_at_alpha_1=tuple(
                    _finite_float(
                        row["cfe_call_fraction"],
                        "cfe_call_fraction",
                        maximum=1.0,
                    )
                    for row in rows
                ),
                grid_need=tuple(grid_need),
                state=state,
            )
        )
    return tuple(blocks)


def load_workload_blocks(package: Path, split: str) -> tuple[WorkloadBlock, ...]:
    """Load the exact V5 workload block and marginal schemas."""

    if split not in {"training", "holdout"}:
        raise ValueError("workload split must be training or holdout")
    marginal = _marginal(package / f"{split}_marginal.csv.gz")
    grouped = _hourly_rows(
        package / "workload_blocks.csv.gz",
        (
            "block_id",
            "split",
            "hour_offset",
            "source_relative_hour",
            "workload_fraction",
        ),
    )
    split_ids = {
        block_id for block_id, rows in grouped.items() if rows[0]["split"] == split
    }
    marginal_ids = {block_id for block_id, _ in marginal}
    if split_ids != marginal_ids:
        raise ValueError("workload hourly and marginal block inventories differ")
    return tuple(
        WorkloadBlock(
            block_id=block_id,
            split=split,
            probability=probability,
            source_relative_hours=tuple(
                _integer(row["source_relative_hour"], "source_relative_hour")
                for row in grouped[block_id]
            ),
            raw_workload_fraction=tuple(
                _finite_float(
                    row["workload_fraction"],
                    "workload_fraction",
                )
                for row in grouped[block_id]
            ),
        )
        for block_id, probability in marginal
    )


def expand_registered_cells(design: dict[str, Any]) -> tuple[RegisteredCell, ...]:
    """Build the registered 36-factorial plus 10-OAT cell inventory."""

    registered = design["registered_design"]
    factors = registered["primary_factorial"]["factors"]
    fixed = design["temporal_envelope"]["fixed_parameters"]
    payloads: list[tuple[str, str, dict[str, object]]] = []
    for alpha, flexible, headroom in product(
        factors["hourly_cfe_target"],
        factors["flexible_fraction"],
        factors["normalized_recovery_headroom"],
    ):
        payloads.append(
            (
                (
                    f"primary_a{round(float(alpha) * 100):03d}"
                    f"_f{round(float(flexible) * 100):03d}"
                    f"_h{round(float(headroom) * 100):03d}"
                ),
                "primary_factorial",
                {
                    "hourly_cfe_target": alpha,
                    "flexible_fraction": flexible,
                    "normalized_recovery_headroom": headroom,
                    **fixed,
                },
            )
        )
    secondary = registered["secondary_oat"]
    anchor = secondary["anchor"]
    levels = design["temporal_envelope"]["oat_levels"]
    for dimension in secondary["varied_dimensions"]:
        if anchor[dimension] not in levels[dimension]:
            raise ValueError(f"OAT anchor is absent from {dimension}")
        index = 0
        for level in levels[dimension]:
            if level == anchor[dimension]:
                continue
            values = dict(anchor)
            values[dimension] = level
            payloads.append(
                (
                    f"oat_{dimension}_{index:02d}",
                    "secondary_oat",
                    values,
                )
            )
            index += 1
    cells = tuple(
        RegisteredCell(
            cell_id=cell_id,
            family=family,
            hourly_cfe_target=_finite_float(
                values["hourly_cfe_target"],
                "hourly_cfe_target",
                minimum=1.0e-300,
                maximum=1.0,
            ),
            flexible_fraction=_finite_float(
                values["flexible_fraction"],
                "flexible_fraction",
                maximum=1.0,
            ),
            normalized_recovery_headroom=_finite_float(
                values["normalized_recovery_headroom"],
                "normalized_recovery_headroom",
                maximum=1.0,
            ),
            recovery_efficiency=_finite_float(
                values["recovery_efficiency"],
                "recovery_efficiency",
                minimum=1.0e-300,
                maximum=1.0,
            ),
            maximum_event_duration_hours=_finite_float(
                values["maximum_event_duration_hours"],
                "maximum_event_duration_hours",
                minimum=1.0e-300,
            ),
            maximum_event_count=_integer(
                values["maximum_event_count"],
                "maximum_event_count",
            ),
            normalized_energy_budget=_finite_float(
                values["normalized_energy_budget"],
                "normalized_energy_budget",
            ),
            normalized_debt_limit=_finite_float(
                values["normalized_debt_limit"],
                "normalized_debt_limit",
            ),
        )
        for cell_id, family, values in payloads
    )
    parameter_tuples = {
        (
            cell.hourly_cfe_target,
            cell.flexible_fraction,
            cell.normalized_recovery_headroom,
            cell.recovery_efficiency,
            cell.maximum_event_duration_hours,
            cell.maximum_event_count,
            cell.normalized_energy_budget,
            cell.normalized_debt_limit,
        )
        for cell in cells
    }
    if (
        len(cells) != 46
        or len({cell.cell_id for cell in cells}) != 46
        or len(parameter_tuples) != 46
    ):
        raise ValueError("registered 46-cell inventory drifted")
    return cells


def raw_cfe_request(
    cfe_call_fraction_at_alpha_1: float,
    hourly_cfe_target: float,
) -> float:
    """Map the alpha=1 source field to the full target-specific CFE deficit."""

    source = _finite_float(
        cfe_call_fraction_at_alpha_1,
        "cfe_call_fraction_at_alpha_1",
        maximum=1.0,
    )
    alpha = _finite_float(
        hourly_cfe_target,
        "hourly_cfe_target",
        minimum=1.0e-300,
        maximum=1.0,
    )
    renewable_share = 1.0 - source
    return max(alpha - renewable_share, 0.0) / alpha


def build_pair_scenario(
    power: PowerBlock,
    workload: WorkloadBlock,
    cell: RegisteredCell,
    *,
    service_shortfall_tolerance: float,
    name: str | None = None,
) -> JointDeliverabilityScenario:
    """Build one finite pair without truncating CFE demand to flexibility."""

    if power.state != FINITE_GRID_NEED:
        raise ValueError("pair scenario requires finite_grid_need power")
    if power.split != workload.split:
        raise ValueError("power and workload splits must match")
    lengths = {
        len(power.grid_need),
        len(power.cfe_call_fraction_at_alpha_1),
        len(workload.raw_workload_fraction),
    }
    if lengths != {24}:
        raise ValueError("pair scenario requires aligned 24-hour blocks")
    raw_grid = tuple(
        _finite_float(value, "grid need", maximum=1.0)
        for value in power.grid_need
        if value is not None
    )
    if len(raw_grid) != 24:
        raise ValueError("finite power block contains an empty grid need")
    raw_cfe = tuple(
        raw_cfe_request(value, cell.hourly_cfe_target)
        for value in power.cfe_call_fraction_at_alpha_1
    )
    occupancy = tuple(min(value, 1.0) for value in workload.raw_workload_fraction)
    available = tuple(cell.flexible_fraction * value for value in occupancy)
    business_headroom = tuple(
        cell.normalized_recovery_headroom * max(1.0 - value, 0.0) for value in occupancy
    )
    renewable_share = tuple(1.0 - value for value in power.cfe_call_fraction_at_alpha_1)
    cfe_compatible = tuple(
        max(value / cell.hourly_cfe_target - 1.0, 0.0) for value in renewable_share
    )
    cfe_headroom = tuple(
        min(business, compatible)
        for business, compatible in zip(
            business_headroom,
            cfe_compatible,
            strict=True,
        )
    )
    return JointDeliverabilityScenario(
        name=name or f"{power.block_id}__{workload.block_id}",
        power_block_id=power.block_id,
        workload_block_id=workload.block_id,
        probability=power.probability * workload.probability,
        raw_grid_request=raw_grid,
        raw_cfe_request=raw_cfe,
        effective_grid_request=tuple(
            effective_request(value, service_shortfall_tolerance) for value in raw_grid
        ),
        effective_cfe_request=tuple(
            effective_request(value, service_shortfall_tolerance) for value in raw_cfe
        ),
        available_flexibility=available,
        connected_demand=(1.0,) * 24,
        business_recovery_headroom=business_headroom,
        cfe_service_recovery_headroom=cfe_headroom,
    )


def _canonical_id_key(block_id: str) -> bytes:
    return block_id.encode("utf-8")


def _score(block: PowerBlock | WorkloadBlock, role: str) -> float:
    if role == "power" and isinstance(block, PowerBlock):
        if block.state != FINITE_GRID_NEED:
            raise ValueError("E0 power block cannot receive a finite stress score")
        return max(
            float(grid) + cfe
            for grid, cfe in zip(
                block.grid_need,
                block.cfe_call_fraction_at_alpha_1,
                strict=True,
            )
            if grid is not None
        )
    if role == "workload" and isinstance(block, WorkloadBlock):
        return max(min(value, 1.0) for value in block.raw_workload_fraction)
    raise TypeError("representative role and block type disagree")


def select_representatives(
    blocks: tuple[PowerBlock, ...] | tuple[WorkloadBlock, ...],
    *,
    role: str,
    quantile_targets: tuple[float, ...],
) -> tuple[PowerBlock, ...] | tuple[WorkloadBlock, ...]:
    """Apply the exact weighted quantile and mass-reassignment algorithm."""

    if not blocks or len(quantile_targets) > len(blocks):
        raise ValueError("representative selection inventory is invalid")
    if any(block.split != "training" for block in blocks):
        raise ValueError("representatives must use training blocks only")
    if any(
        not isfinite(block.probability) or block.probability < 0.0 for block in blocks
    ):
        raise ValueError("representative probabilities must be finite and nonnegative")
    if not isclose(
        fsum(block.probability for block in blocks),
        1.0,
        rel_tol=0.0,
        abs_tol=1.0e-9,
    ):
        raise ValueError("representative probabilities must sum to one")
    targets = tuple(float(target) for target in quantile_targets)
    if (
        not targets
        or tuple(sorted(targets)) != targets
        or len(set(targets)) != len(targets)
        or any(not 0.0 < target < 1.0 for target in targets)
    ):
        raise ValueError("quantile targets are invalid")
    ordered = tuple(
        sorted(
            blocks,
            key=lambda block: (
                _score(block, role),
                _canonical_id_key(block.block_id),
            ),
        )
    )
    selected: list[PowerBlock | WorkloadBlock] = []
    cumulative = 0.0
    target_index = 0
    for block in ordered:
        cumulative += block.probability
        while target_index < len(targets) and cumulative >= targets[target_index]:
            selected.append(block)
            target_index += 1
    if target_index != len(targets):
        raise ValueError("representative cumulative mass did not reach all targets")
    selected_ids = list(dict.fromkeys(block.block_id for block in selected))
    selected_ids.extend(
        block.block_id for block in ordered if block.block_id not in selected_ids
    )
    selected_ids = selected_ids[: len(targets)]
    selected_by_id = {
        block.block_id: block for block in ordered if block.block_id in selected_ids
    }
    assigned = {block_id: 0.0 for block_id in selected_ids}
    for block in ordered:
        nearest = min(
            selected_ids,
            key=lambda block_id: (
                abs(_score(block, role) - _score(selected_by_id[block_id], role)),
                _canonical_id_key(block_id),
            ),
        )
        assigned[nearest] += block.probability
    return tuple(
        replace(selected_by_id[block_id], probability=assigned[block_id])
        for block_id in selected_ids
    )


def condition_finite_power(
    blocks: tuple[PowerBlock, ...],
    *,
    empty_tolerance: float = 1.0e-9,
) -> tuple[tuple[PowerBlock, ...], float]:
    """Separate E0 once and renormalize the finite power marginal."""

    if not blocks or len({block.block_id for block in blocks}) != len(blocks):
        raise ValueError("power block inventory is empty or duplicated")
    if any(block.state not in _GRID_STATES for block in blocks):
        raise ValueError("power block inventory contains an unresolved state")
    if any(
        not isfinite(block.probability) or block.probability < 0.0 for block in blocks
    ):
        raise ValueError("power marginal probabilities must be finite and nonnegative")
    total = fsum(block.probability for block in blocks)
    if not isclose(total, 1.0, rel_tol=0.0, abs_tol=1.0e-9):
        raise ValueError("power marginal probability mass drifted")
    e0_mass = fsum(
        block.probability
        for block in blocks
        if block.state == EXOGENOUS_GRID_INFEASIBILITY
    )
    if e0_mass >= 1.0 - empty_tolerance:
        return (), e0_mass
    finite_mass = 1.0 - e0_mass
    return (
        tuple(
            replace(block, probability=block.probability / finite_mass)
            for block in blocks
            if block.state == FINITE_GRID_NEED
        ),
        e0_mass,
    )


def planning_inputs(
    scenarios: tuple[JointDeliverabilityScenario, ...],
    cell: RegisteredCell,
    design: dict[str, Any],
) -> JointDeliverabilityPlanningInputs:
    """Normalize representative pair mass and bind all V5 cell constants."""

    if not scenarios:
        raise ValueError("planning scenarios must be nonempty")
    total = fsum(scenario.probability for scenario in scenarios)
    if total <= 0.0:
        raise ValueError("planning scenario mass must be positive")
    normalized = tuple(
        replace(scenario, probability=scenario.probability / total)
        for scenario in scenarios
    )
    temporal = design["temporal_envelope"]
    return JointDeliverabilityPlanningInputs(
        scenarios=normalized,
        time_step_hours=float(design["data_contract"]["time_step_hours"]),
        maximum_flexibility_budget=float(temporal["maximum_flexibility_budget"]),
        minimum_event_power=float(temporal["minimum_event_power"]),
        response_time_hours=float(temporal["response_time_hours"]),
        curtailment_ramp_per_hour=float(temporal["curtailment_ramp_per_hour"]),
        minimum_recovery_hours=float(temporal["minimum_recovery_hours"]),
        recovery_efficiency=cell.recovery_efficiency,
        maximum_event_duration_hours=cell.maximum_event_duration_hours,
        maximum_event_count=cell.maximum_event_count,
        normalized_recovery_headroom=cell.normalized_recovery_headroom,
        normalized_energy_budget=cell.normalized_energy_budget,
        normalized_debt_limit=cell.normalized_debt_limit,
        terminal_recovery_debt_limit=float(temporal["terminal_recovery_debt_limit"]),
        service_shortfall_tolerance=float(temporal["service_shortfall_tolerance"]),
    )


def structural_recovery_witness(
    *,
    cell_id: str,
    arm_id: str,
    track_id: str,
    power_block_id: str,
    workload_block_id: str,
    required_call: tuple[float, ...],
    recovery_headroom: tuple[float, ...],
    maximum_recovery_power: float,
    recovery_efficiency: float,
    initial_recovery_debt: float,
    terminal_recovery_debt_limit: float,
    time_step_hours: float,
    service_tolerance: float,
    tolerance: float,
) -> dict[str, object] | None:
    """Return the registered global recovery lower-bound witness when triggered."""

    if not required_call or len(required_call) != len(recovery_headroom):
        raise ValueError("structural precheck trajectory inventory drifted")
    scalar_values = (
        maximum_recovery_power,
        recovery_efficiency,
        initial_recovery_debt,
        terminal_recovery_debt_limit,
        time_step_hours,
        service_tolerance,
        tolerance,
    )
    if any(
        not isfinite(float(value)) or float(value) < 0.0
        for value in (*required_call, *recovery_headroom, *scalar_values)
    ):
        raise ValueError("structural precheck values must be finite and nonnegative")
    if not 0.0 < recovery_efficiency <= 1.0 or time_step_hours <= 0.0:
        raise ValueError("structural precheck efficiency and time step are invalid")
    effective = tuple(
        effective_request(call, service_tolerance) for call in required_call
    )
    eligible = tuple(
        (min(maximum_recovery_power, headroom) if call == 0.0 else 0.0)
        for call, headroom in zip(effective, recovery_headroom, strict=True)
    )
    total_call_energy = fsum(effective) * time_step_hours
    maximum_recovery_energy = fsum(eligible) * time_step_hours
    terminal_lower_bound = (
        initial_recovery_debt
        + total_call_energy
        - recovery_efficiency * maximum_recovery_energy
    )
    if terminal_lower_bound <= terminal_recovery_debt_limit + tolerance:
        return None
    return {
        "cell_id": cell_id,
        "arm_id": arm_id,
        "track_id": track_id,
        "power_block_id": power_block_id,
        "workload_block_id": workload_block_id,
        "total_required_call_energy": total_call_energy,
        "eligible_recovery_power_by_hour": list(eligible),
        "maximum_eligible_recovery_energy": maximum_recovery_energy,
        "recovery_efficiency": recovery_efficiency,
        "initial_recovery_debt": initial_recovery_debt,
        "terminal_recovery_debt_limit": terminal_recovery_debt_limit,
        "terminal_debt_lower_bound": terminal_lower_bound,
        "tolerance": tolerance,
        "debt_balance_identity": (
            "initial_debt+required_call_energy-"
            "recovery_efficiency*maximum_eligible_recovery_energy"
        ),
    }


def scenario_track_requirements(
    scenario: JointDeliverabilityScenario,
    arm_id: str,
) -> tuple[tuple[str, tuple[float, ...], tuple[float, ...]], ...]:
    """Expose the exact arm/track mapping used by the structural gate."""

    grid = scenario.effective_grid_request
    cfe = scenario.effective_cfe_request
    if arm_id == NETWORK_ONLY_SHARED:
        return (("shared", grid, scenario.business_recovery_headroom),)
    if arm_id == CFE_ONLY_SHARED:
        return (("shared", cfe, scenario.cfe_service_recovery_headroom),)
    if arm_id == JOINT_CORRECT_SHARED:
        return (
            (
                "shared",
                tuple(
                    grid_value + cfe_value
                    for grid_value, cfe_value in zip(grid, cfe, strict=True)
                ),
                scenario.cfe_service_recovery_headroom,
            ),
        )
    if arm_id == JOINT_B6_SEPARATE_PLANNING_SHARED_EXECUTION:
        return (
            ("grid", grid, scenario.business_recovery_headroom),
            ("cfe", cfe, scenario.cfe_service_recovery_headroom),
        )
    raise ValueError(f"unknown RQ2 joint-deliverability arm: {arm_id}")


def network_capacity_key(cell: RegisteredCell) -> tuple[object, ...]:
    """Return the alpha-invariant key for the network-only arm."""

    return (
        cell.flexible_fraction,
        cell.normalized_recovery_headroom,
        cell.recovery_efficiency,
        cell.maximum_event_duration_hours,
        cell.maximum_event_count,
        cell.normalized_energy_budget,
        cell.normalized_debt_limit,
    )


__all__ = [
    "EXOGENOUS_GRID_INFEASIBILITY",
    "FINITE_GRID_NEED",
    "PowerBlock",
    "RegisteredCell",
    "WorkloadBlock",
    "build_pair_scenario",
    "condition_finite_power",
    "expand_registered_cells",
    "lift_power_block_state",
    "load_power_blocks",
    "load_workload_blocks",
    "network_capacity_key",
    "planning_inputs",
    "raw_cfe_request",
    "scenario_track_requirements",
    "select_representatives",
    "structural_recovery_witness",
]
