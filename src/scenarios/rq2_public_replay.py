"""Scenario construction for public-marginal RQ2 fixed-policy replay."""

from __future__ import annotations

import csv
import gzip
from dataclasses import dataclass, replace
from datetime import datetime, timedelta, timezone
from math import isfinite
from pathlib import Path

from src.evaluation.flexibility_envelope import (
    ChronologicalFlexibilityEnvelope,
    ChronologicalFlexibilityTrace,
    evaluate_chronological_flexibility,
)
from src.evaluation.service_risk import ServiceLossCoefficients
from src.evaluation.temporal_economic_holdout import TemporalEconomicHoldoutInputs
from src.models.economic_temporal_stochastic import (
    TemporalEconomicInputs,
    TemporalEconomicScenario,
)


@dataclass(frozen=True)
class TemporalBlock:
    block_id: str
    split: str
    probability: float
    first_source_hour: int
    grid_need: tuple[float, ...]
    cfe_call: tuple[float, ...]
    workload: tuple[float, ...]


@dataclass(frozen=True)
class ParameterCell:
    cell_id: str
    varied_dimension: str
    flexible_fraction: float
    recovery_efficiency: float
    normalized_recovery_headroom: float
    maximum_event_duration_hours: float
    maximum_event_count: int
    normalized_energy_budget: float
    normalized_debt_limit: float


@dataclass(frozen=True)
class CausalPolicyOutcome:
    name: str
    committed_flexibility: float
    resolved: bool
    hard_grid_failure: bool
    physical_policy_failure: bool
    service_shortfall_failure: bool
    access_shortfall: float
    peak_recovery_debt: float
    terminal_recovery_debt: float
    combined_call: tuple[float, ...]
    green_served: tuple[float, ...]
    physical_violations: tuple[str, ...]


def _finite(raw: object, label: str, *, minimum: float = 0.0) -> float:
    try:
        number = float(raw)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be numeric") from error
    if not isfinite(number) or number < minimum:
        raise ValueError(f"{label} must be finite and at least {minimum}")
    return number


def _marginal(path: Path) -> dict[str, float]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != ["id", "probability"]:
            raise ValueError(f"{path} marginal schema drifted")
        rows = list(reader)
    probabilities = {
        row["id"]: _finite(row["probability"], f"{path} probability")
        for row in rows
    }
    if (
        not probabilities
        or len(probabilities) != len(rows)
        or abs(sum(probabilities.values()) - 1.0) > 1.0e-9
    ):
        raise ValueError(f"{path} marginal is invalid")
    return probabilities


def _group_rows(
    path: Path,
    required: set[str],
) -> dict[str, list[dict[str, str]]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None or not required.issubset(reader.fieldnames):
            raise ValueError(f"{path} block schema drifted")
        rows = list(reader)
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        grouped.setdefault(row["block_id"], []).append(row)
    if not grouped:
        raise ValueError(f"{path} must contain blocks")
    for block_id, block in grouped.items():
        offsets = tuple(int(row["hour_offset"]) for row in block)
        if offsets != tuple(range(len(block))):
            raise ValueError(f"{block_id} hour offsets are not contiguous")
        if len({row["split"] for row in block}) != 1:
            raise ValueError(f"{block_id} has mixed split labels")
    return grouped


def load_power_blocks(package: Path, split: str) -> tuple[TemporalBlock, ...]:
    probabilities = _marginal(package / f"{split}_marginal.csv.gz")
    grouped = _group_rows(
        package / "dispatched_power_system_blocks.csv.gz",
        {
            "block_id",
            "split",
            "hour_offset",
            "source_hour",
            "cfe_call_fraction",
            "grid_need_fraction",
            "dispatch_resolved",
        },
    )
    blocks = []
    for block_id, probability in probabilities.items():
        if block_id not in grouped:
            raise ValueError(f"power marginal block is missing: {block_id}")
        rows = grouped[block_id]
        if any(
            row["split"] != split or row["dispatch_resolved"] != "true"
            for row in rows
        ):
            raise ValueError(f"power block is unresolved or mislabeled: {block_id}")
        blocks.append(
            TemporalBlock(
                block_id=block_id,
                split=split,
                probability=probability,
                first_source_hour=int(rows[0]["source_hour"]),
                grid_need=tuple(
                    _finite(row["grid_need_fraction"], "grid_need_fraction")
                    for row in rows
                ),
                cfe_call=tuple(
                    _finite(row["cfe_call_fraction"], "cfe_call_fraction")
                    for row in rows
                ),
                workload=(),
            )
        )
    return tuple(blocks)


def load_workload_blocks(package: Path, split: str) -> tuple[TemporalBlock, ...]:
    probabilities = _marginal(package / f"{split}_marginal.csv.gz")
    grouped = _group_rows(
        package / "workload_blocks.csv.gz",
        {
            "block_id",
            "split",
            "hour_offset",
            "source_relative_hour",
            "workload_fraction",
        },
    )
    blocks = []
    for block_id, probability in probabilities.items():
        if block_id not in grouped:
            raise ValueError(f"workload marginal block is missing: {block_id}")
        rows = grouped[block_id]
        if any(row["split"] != split for row in rows):
            raise ValueError(f"workload block is mislabeled: {block_id}")
        blocks.append(
            TemporalBlock(
                block_id=block_id,
                split=split,
                probability=probability,
                first_source_hour=int(rows[0]["source_relative_hour"]),
                grid_need=(),
                cfe_call=(),
                workload=tuple(
                    _finite(row["workload_fraction"], "workload_fraction")
                    for row in rows
                ),
            )
        )
    return tuple(blocks)


def _score(block: TemporalBlock, role: str) -> float:
    if role == "power":
        return max(
            grid + cfe
            for grid, cfe in zip(block.grid_need, block.cfe_call, strict=True)
        )
    if role == "workload":
        return max(block.workload)
    raise ValueError(f"unknown block role: {role}")


def select_weighted_quantile_representatives(
    blocks: tuple[TemporalBlock, ...],
    count: int,
    *,
    role: str,
) -> tuple[TemporalBlock, ...]:
    """Select weighted stress quantiles and reassign all marginal mass."""

    if isinstance(count, bool) or count <= 0:
        raise ValueError("representative count must be positive")
    if not blocks:
        raise ValueError("representative selection requires blocks")
    if count > len(blocks):
        raise ValueError("representative count exceeds available blocks")
    if abs(sum(block.probability for block in blocks) - 1.0) > 1.0e-9:
        raise ValueError("representative input probabilities must sum to one")
    ordered = sorted(blocks, key=lambda item: (_score(item, role), item.block_id))
    targets = tuple((index + 0.5) / count for index in range(count))
    selected = []
    cumulative = 0.0
    target_index = 0
    for block in ordered:
        cumulative += block.probability
        while target_index < len(targets) and cumulative >= targets[target_index]:
            selected.append(block)
            target_index += 1
    selected_ids = tuple(dict.fromkeys(item.block_id for item in selected))
    if len(selected_ids) != count:
        remaining = [
            item.block_id for item in ordered if item.block_id not in selected_ids
        ]
        selected_ids = (*selected_ids, *remaining[: count - len(selected_ids)])
    selected_by_id = {item.block_id: item for item in ordered if item.block_id in selected_ids}
    assigned = {block_id: 0.0 for block_id in selected_ids}
    for block in ordered:
        representative_id = min(
            selected_ids,
            key=lambda block_id: (
                abs(_score(block, role) - _score(selected_by_id[block_id], role)),
                block_id,
            ),
        )
        assigned[representative_id] += block.probability
    return tuple(
        replace(
            selected_by_id[block_id],
            probability=assigned[block_id],
        )
        for block_id in selected_ids
    )


def expand_parameter_cells(config: dict) -> tuple[ParameterCell, ...]:
    registered = config["registered_cells"]
    base = dict(registered["base"])
    levels = registered["levels"]
    if set(levels) != set(base):
        raise ValueError("parameter levels must match every base dimension")
    cells = [("base", "base", base)]
    for dimension in sorted(levels):
        values = levels[dimension]
        if base[dimension] not in values:
            raise ValueError(f"base value is absent from levels: {dimension}")
        for index, value in enumerate(values):
            if value == base[dimension]:
                continue
            payload = dict(base)
            payload[dimension] = value
            cells.append(
                (
                    f"{dimension}_{index:02d}",
                    dimension,
                    payload,
                )
            )
    result = []
    for cell_id, varied, payload in cells:
        event_count = payload["maximum_event_count"]
        if isinstance(event_count, bool) or int(event_count) != event_count:
            raise ValueError("maximum_event_count must be an integer")
        result.append(
            ParameterCell(
                cell_id=cell_id,
                varied_dimension=varied,
                flexible_fraction=_finite(
                    payload["flexible_fraction"], "flexible_fraction"
                ),
                recovery_efficiency=_finite(
                    payload["recovery_efficiency"],
                    "recovery_efficiency",
                ),
                normalized_recovery_headroom=_finite(
                    payload["normalized_recovery_headroom"],
                    "normalized_recovery_headroom",
                ),
                maximum_event_duration_hours=_finite(
                    payload["maximum_event_duration_hours"],
                    "maximum_event_duration_hours",
                ),
                maximum_event_count=int(event_count),
                normalized_energy_budget=_finite(
                    payload["normalized_energy_budget"],
                    "normalized_energy_budget",
                ),
                normalized_debt_limit=_finite(
                    payload["normalized_debt_limit"],
                    "normalized_debt_limit",
                ),
            )
        )
    if len({cell.cell_id for cell in result}) != len(result):
        raise ValueError("parameter cell IDs must be unique")
    return tuple(result)


def envelope_for_cell(
    cell: ParameterCell,
    *,
    policy: dict,
) -> ChronologicalFlexibilityEnvelope:
    return ChronologicalFlexibilityEnvelope(
        time_step_hours=1.0,
        maximum_event_duration_hours=cell.maximum_event_duration_hours,
        minimum_recovery_hours=float(policy["minimum_recovery_hours"]),
        maximum_events_by_period={"block": cell.maximum_event_count},
        maximum_curtailment_energy_mwh_by_period={
            "block": cell.normalized_energy_budget
        },
        maximum_recovery_debt_mwh=cell.normalized_debt_limit,
        maximum_recovery_power_mw=cell.normalized_recovery_headroom,
        minimum_event_power_mw=float(policy["minimum_event_power"]),
        response_time_hours=float(policy["response_time_hours"]),
        curtailment_ramp_mw_per_hour=float(
            policy["curtailment_ramp_per_hour"]
        ),
        recovery_efficiency=cell.recovery_efficiency,
        terminal_debt_limit_mwh_by_period={"block": 0.0},
        parameter_status=(
            f"public_threshold_cell_{cell.cell_id}_not_observed_contract"
        ),
    )


def pair_scenario(
    power: TemporalBlock,
    workload: TemporalBlock,
    cell: ParameterCell,
    *,
    name: str,
) -> TemporalEconomicScenario:
    if len(power.grid_need) != len(workload.workload):
        raise ValueError("power and workload blocks must have equal length")
    if len(power.cfe_call) != len(workload.workload):
        raise ValueError("CFE and workload blocks must have equal length")
    if power.split != workload.split:
        raise ValueError("power and workload blocks must use the same split")
    occupancy = tuple(min(value, 1.0) for value in workload.workload)
    available = tuple(cell.flexible_fraction * value for value in occupancy)
    green_call = tuple(
        min(deficit, flexible)
        for deficit, flexible in zip(
            power.cfe_call,
            available,
            strict=True,
        )
    )
    recovery = tuple(
        cell.normalized_recovery_headroom * max(1.0 - value, 0.0)
        for value in occupancy
    )
    return TemporalEconomicScenario(
        name=name,
        probability=power.probability * workload.probability,
        periods=("block",) * len(occupancy),
        grid_need_mw=power.grid_need,
        green_call_mw=green_call,
        connected_demand_mw=(1.0,) * len(occupancy),
        recovery_headroom_mw=recovery,
        completed_periods=frozenset({"block"}),
        require_terminal_event_inactive=True,
        boundary_state_status="clean_boundary_with_zero_carry_in",
        available_flexibility_mw=available,
    )


def training_model_inputs(
    power_blocks: tuple[TemporalBlock, ...],
    workload_blocks: tuple[TemporalBlock, ...],
    cell: ParameterCell,
    config: dict,
) -> TemporalEconomicInputs:
    if not power_blocks or not workload_blocks:
        raise ValueError("training blocks must be nonempty")
    if any(block.split != "training" for block in (*power_blocks, *workload_blocks)):
        raise ValueError("training inputs cannot contain holdout blocks")
    scenarios = tuple(
        pair_scenario(
            power,
            workload,
            cell,
            name=f"train__{power.block_id}__{workload.block_id}",
        )
        for power in power_blocks
        for workload in workload_blocks
    )
    probability = sum(item.probability for item in scenarios)
    if probability <= 0.0:
        raise ValueError("training scenario probability must be positive")
    scenarios = tuple(
        replace(item, probability=item.probability / probability)
        for item in scenarios
    )
    coefficients = ServiceLossCoefficients(
        kappa_access=1.0,
        kappa_grid=0.0,
        kappa_green=0.0,
        kappa_drop=0.0,
        kappa_breach_firm=0.0,
        kappa_breach_conditional=0.0,
        parameter_status="capacity_identification_no_economic_weights",
    )
    return TemporalEconomicInputs(
        scenarios=scenarios,
        envelope=envelope_for_cell(cell, policy=config["fixed_policy"]),
        coefficients=coefficients,
        provisioning_cost_per_mw=0.0,
        max_flexibility_budget_mw=float(
            config["fixed_policy"]["maximum_flexibility_budget"]
        ),
        lambda_risk=0.0,
        beta=0.5,
        enforce_joint_budget=True,
        parameter_status="public_marginal_minimum_capacity_planning",
    )


def holdout_inputs(
    training_inputs: TemporalEconomicInputs,
    *,
    service_shortfall_tolerance: float,
) -> TemporalEconomicHoldoutInputs:
    return TemporalEconomicHoldoutInputs(
        training_scenarios=training_inputs.scenarios,
        holdout_scenarios=(),
        envelope=training_inputs.envelope,
        coefficients=training_inputs.coefficients,
        provisioning_cost_per_mw=0.0,
        max_flexibility_budget_mw=training_inputs.max_flexibility_budget_mw,
        lambda_risk=0.0,
        beta=0.5,
        parameter_status="public_marginal_fixed_policy_pairwise_execution",
        service_shortfall_tolerance_mwh=service_shortfall_tolerance,
    )


def _trace(
    scenario: TemporalEconomicScenario,
    call: tuple[float, ...],
    call_limit: tuple[float, ...],
) -> ChronologicalFlexibilityTrace:
    start = datetime(2000, 1, 1, tzinfo=timezone.utc)
    return ChronologicalFlexibilityTrace(
        name=scenario.name,
        timestamps=tuple(
            start + timedelta(hours=index) for index in range(len(call))
        ),
        periods=scenario.periods,
        grid_call_mw=call,
        call_limit_mw=call_limit,
        recovery_headroom_mw=scenario.recovery_headroom_mw,
        boundary_state_status=scenario.boundary_state_status,
        completed_periods=scenario.completed_periods,
        initial_has_prior_event=False,
        require_terminal_event_inactive=scenario.require_terminal_event_inactive,
    )


def execute_causal_grid_first_policy(
    scenario: TemporalEconomicScenario,
    envelope: ChronologicalFlexibilityEnvelope,
    committed_flexibility: float,
    *,
    service_shortfall_tolerance: float,
) -> CausalPolicyOutcome:
    """Replay a fixed, myopic grid-first policy without future information."""

    committed = _finite(
        committed_flexibility,
        "committed_flexibility",
    )
    tolerance = _finite(
        service_shortfall_tolerance,
        "service_shortfall_tolerance",
    )
    available = (
        scenario.available_flexibility_mw
        if scenario.available_flexibility_mw is not None
        else scenario.connected_demand_mw
    )
    if len(available) != len(scenario.periods):
        raise ValueError("available flexibility length drifted")
    call_limit = tuple(
        min(committed, flexible, connected)
        for flexible, connected in zip(
            available,
            scenario.connected_demand_mw,
            strict=True,
        )
    )
    mandatory = evaluate_chronological_flexibility(
        _trace(scenario, scenario.grid_need_mw, call_limit),
        envelope,
    )

    dt = envelope.time_step_hours
    ramp_increment = min(
        envelope.curtailment_ramp_mw_per_hour * dt,
        envelope.curtailment_ramp_mw_per_hour * envelope.response_time_hours,
    )
    event_count = {period: 0 for period in dict.fromkeys(scenario.periods)}
    energy = {period: 0.0 for period in event_count}
    previous_call = 0.0
    active_duration = 0.0
    interevent_rest: float | None = None
    debt = 0.0
    green_served = []
    combined_call = []
    for index, period in enumerate(scenario.periods):
        grid = scenario.grid_need_mw[index]
        requested = scenario.green_call_mw[index]
        upper = max(min(requested, call_limit[index] - grid), 0.0)
        previously_active = previous_call > tolerance
        starts_event = not previously_active and grid + upper > tolerance
        if starts_event and (
            event_count[period] >= envelope.maximum_events_by_period[period]
            or (
                interevent_rest is not None
                and interevent_rest + tolerance
                < envelope.minimum_recovery_hours
            )
        ):
            upper = 0.0
        duration = active_duration + dt if previously_active else dt
        if grid + upper > tolerance and (
            duration > envelope.maximum_event_duration_hours + tolerance
        ):
            upper = 0.0
        upper = min(
            upper,
            max(previous_call + ramp_increment - grid, 0.0),
            max(
                (
                    envelope.maximum_curtailment_energy_mwh_by_period[period]
                    - energy[period]
                )
                / dt
                - grid,
                0.0,
            ),
            max(
                (envelope.maximum_recovery_debt_mwh - debt) / dt - grid,
                0.0,
            ),
        )
        call = grid + upper
        if (
            grid <= tolerance
            and call > tolerance
            and call + tolerance < envelope.minimum_event_power_mw
        ):
            upper = 0.0
            call = 0.0
        active = call > tolerance
        starts_event = active and not previously_active
        if starts_event:
            event_count[period] += 1
            interevent_rest = None
        if active:
            active_duration = active_duration + dt if previously_active else dt
        else:
            active_duration = 0.0
            if previously_active:
                interevent_rest = dt
            elif interevent_rest is not None:
                interevent_rest += dt
        energy[period] += call * dt
        debt += call * dt
        if not active:
            recovery = min(
                envelope.maximum_recovery_power_mw,
                scenario.recovery_headroom_mw[index],
                debt / (envelope.recovery_efficiency * dt),
            )
            debt = max(
                debt - envelope.recovery_efficiency * recovery * dt,
                0.0,
            )
        green_served.append(upper)
        combined_call.append(call)
        previous_call = call

    combined = tuple(combined_call)
    physical = evaluate_chronological_flexibility(
        _trace(scenario, combined, call_limit),
        envelope,
    )
    mandatory_terminal_failure = bool(
        scenario.require_terminal_event_inactive
        and mandatory.terminal_has_prior_event
        and (
            mandatory.terminal_interevent_rest_hours is None
            or mandatory.terminal_interevent_rest_hours + tolerance
            < envelope.minimum_recovery_hours
        )
    )
    physical_terminal_failure = bool(
        scenario.require_terminal_event_inactive
        and physical.terminal_has_prior_event
        and (
            physical.terminal_interevent_rest_hours is None
            or physical.terminal_interevent_rest_hours + tolerance
            < envelope.minimum_recovery_hours
        )
    )
    shortfall = sum(
        requested - served
        for requested, served in zip(
            scenario.green_call_mw,
            green_served,
            strict=True,
        )
    ) * envelope.time_step_hours
    violations = tuple(
        dict.fromkeys(
            (
                *mandatory.violations,
                *(
                    ("mandatory_grid_terminal_recovery_incomplete",)
                    if mandatory_terminal_failure
                    else ()
                ),
                *physical.violations,
                *(
                    ("policy_terminal_recovery_incomplete",)
                    if physical_terminal_failure
                    else ()
                ),
            )
        )
    )
    return CausalPolicyOutcome(
        name=scenario.name,
        committed_flexibility=committed,
        resolved=True,
        hard_grid_failure=not mandatory.feasible or mandatory_terminal_failure,
        physical_policy_failure=(
            not physical.feasible or physical_terminal_failure
        ),
        service_shortfall_failure=shortfall > tolerance,
        access_shortfall=shortfall,
        peak_recovery_debt=physical.peak_recovery_debt_mwh,
        terminal_recovery_debt=physical.terminal_recovery_debt_mwh,
        combined_call=combined,
        green_served=tuple(green_served),
        physical_violations=violations,
    )
