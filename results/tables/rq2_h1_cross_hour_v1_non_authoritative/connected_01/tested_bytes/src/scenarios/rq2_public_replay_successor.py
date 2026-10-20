"""Successor utilities for E0-aware RQ2 replay and training coverage."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from math import isfinite
from pathlib import Path

from src.evaluation.flexibility_envelope import (
    ChronologicalFlexibilityEnvelope,
    evaluate_chronological_flexibility,
)
from src.grid.rts_gmlc_grid_need_successor import (
    EXOGENOUS_GRID_INFEASIBILITY,
    FINITE_GRID_NEED,
)
from src.scenarios.rq2_public_replay import (
    ParameterCell,
    TemporalBlock,
    _finite,
    _group_rows,
    _marginal,
    _trace,
    envelope_for_cell,
    pair_scenario,
)


@dataclass(frozen=True)
class ConditionalPowerMarginal:
    evaluable_blocks: tuple[TemporalBlock, ...]
    exogenous_block_ids: tuple[str, ...]
    exogenous_probability_mass: float
    conditioning_probability_mass: float


@dataclass(frozen=True)
class LoadedPowerMarginal:
    blocks: tuple[TemporalBlock, ...]
    state_by_block: dict[str, str]


@dataclass(frozen=True)
class TrainingSupportAudit:
    variant: str
    pair_count: int
    failed_pair_ids: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.failed_pair_ids


def load_power_blocks_with_state(
    package: Path,
    split: str,
) -> LoadedPowerMarginal:
    """Load finite and E0 power blocks without inventing a finite grid need."""

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
            "dispatch_state",
        },
    )
    blocks = []
    states = {}
    for block_id, probability in probabilities.items():
        if block_id not in grouped:
            raise ValueError(f"power marginal block is missing: {block_id}")
        rows = grouped[block_id]
        if any(row["split"] != split for row in rows):
            raise ValueError(f"power block is mislabeled: {block_id}")
        row_states = {row["dispatch_state"] for row in rows}
        if not row_states.issubset(
            {FINITE_GRID_NEED, EXOGENOUS_GRID_INFEASIBILITY}
        ):
            raise ValueError(f"power block contains unresolved state: {block_id}")
        state = (
            EXOGENOUS_GRID_INFEASIBILITY
            if EXOGENOUS_GRID_INFEASIBILITY in row_states
            else FINITE_GRID_NEED
        )
        if state == FINITE_GRID_NEED:
            grid_need = tuple(
                _finite(row["grid_need_fraction"], "grid_need_fraction")
                for row in rows
            )
        else:
            if any(
                row["grid_need_fraction"]
                for row in rows
                if row["dispatch_state"] == EXOGENOUS_GRID_INFEASIBILITY
            ):
                raise ValueError("E0 hour cannot contain a finite grid need")
            grid_need = tuple(
                (
                    0.0
                    if row["dispatch_state"] == EXOGENOUS_GRID_INFEASIBILITY
                    else _finite(
                        row["grid_need_fraction"],
                        "grid_need_fraction",
                    )
                )
                for row in rows
            )
        blocks.append(
            TemporalBlock(
                block_id=block_id,
                split=split,
                probability=probability,
                first_source_hour=int(rows[0]["source_hour"]),
                grid_need=grid_need,
                cfe_call=tuple(
                    _finite(row["cfe_call_fraction"], "cfe_call_fraction")
                    for row in rows
                ),
                workload=(),
            )
        )
        states[block_id] = state
    return LoadedPowerMarginal(blocks=tuple(blocks), state_by_block=states)


def condition_on_grid_evaluable(
    blocks: tuple[TemporalBlock, ...],
    state_by_block: Mapping[str, str],
) -> ConditionalPowerMarginal:
    """Preserve E0 mass while renormalizing the contract-risk support."""

    if not blocks:
        raise ValueError("power marginal must contain blocks")
    if set(state_by_block) != {block.block_id for block in blocks}:
        raise ValueError("power block state inventory drifted")
    total = sum(block.probability for block in blocks)
    if not isfinite(total) or abs(total - 1.0) > 1.0e-9:
        raise ValueError("power marginal probabilities must sum to one")
    invalid_states = set(state_by_block.values()) - {
        FINITE_GRID_NEED,
        EXOGENOUS_GRID_INFEASIBILITY,
    }
    if invalid_states:
        raise ValueError(f"unresolved power states cannot be conditioned: {invalid_states}")
    exogenous_ids = tuple(
        block.block_id
        for block in blocks
        if state_by_block[block.block_id] == EXOGENOUS_GRID_INFEASIBILITY
    )
    exogenous_mass = sum(
        block.probability for block in blocks if block.block_id in exogenous_ids
    )
    conditioning_mass = 1.0 - exogenous_mass
    if conditioning_mass <= 0.0:
        raise ValueError("no grid-evaluable probability mass remains")
    evaluable = tuple(
        replace(block, probability=block.probability / conditioning_mass)
        for block in blocks
        if state_by_block[block.block_id] == FINITE_GRID_NEED
    )
    return ConditionalPowerMarginal(
        evaluable_blocks=evaluable,
        exogenous_block_ids=exogenous_ids,
        exogenous_probability_mass=exogenous_mass,
        conditioning_probability_mass=conditioning_mass,
    )


def _trace_passes(
    scenario: object,
    envelope: ChronologicalFlexibilityEnvelope,
    call: tuple[float, ...],
    capacity: float,
) -> bool:
    available = (
        scenario.available_flexibility_mw
        if scenario.available_flexibility_mw is not None
        else scenario.connected_demand_mw
    )
    call_limit = tuple(
        min(capacity, flexible, connected)
        for flexible, connected in zip(
            available,
            scenario.connected_demand_mw,
            strict=True,
        )
    )
    return evaluate_chronological_flexibility(
        _trace(scenario, call, call_limit),
        envelope,
    ).feasible


def audit_training_support(
    power_blocks: tuple[TemporalBlock, ...],
    workload_blocks: tuple[TemporalBlock, ...],
    cell: ParameterCell,
    *,
    correct_capacity: float,
    b6_capacity: float,
    fixed_policy: Mapping[str, object],
) -> tuple[TrainingSupportAudit, TrainingSupportAudit]:
    """Audit representative-trained policies on every evaluable training pair.

    Correct uses one physical envelope. B6 is checked under its registered
    separate-envelope planning semantics. Holdout evaluation still uses the
    shared physical envelope for both policies.
    """

    if not power_blocks or not workload_blocks:
        raise ValueError("full-support audit requires both training marginals")
    envelope = envelope_for_cell(cell, policy=dict(fixed_policy))
    correct_failures = []
    b6_failures = []
    pair_count = 0
    for power in power_blocks:
        for workload in workload_blocks:
            scenario = pair_scenario(
                power,
                workload,
                cell,
                name=f"training_audit__{power.block_id}__{workload.block_id}",
            )
            pair_id = f"{power.block_id}__{workload.block_id}"
            pair_count += 1
            combined_call = tuple(
                grid + green
                for grid, green in zip(
                    scenario.grid_need_mw,
                    scenario.green_call_mw,
                    strict=True,
                )
            )
            if not _trace_passes(
                scenario,
                envelope,
                combined_call,
                correct_capacity,
            ):
                correct_failures.append(pair_id)
            b6_grid_passes = _trace_passes(
                scenario,
                envelope,
                scenario.grid_need_mw,
                b6_capacity,
            )
            b6_green_passes = _trace_passes(
                scenario,
                envelope,
                scenario.green_call_mw,
                b6_capacity,
            )
            if not (b6_grid_passes and b6_green_passes):
                b6_failures.append(pair_id)
    return (
        TrainingSupportAudit(
            variant="correct",
            pair_count=pair_count,
            failed_pair_ids=tuple(correct_failures),
        ),
        TrainingSupportAudit(
            variant="b6",
            pair_count=pair_count,
            failed_pair_ids=tuple(b6_failures),
        ),
    )
