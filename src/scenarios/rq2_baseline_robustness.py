"""Finite-grid training and holdout helpers for the RQ2 four-arm design."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from math import isfinite
from numbers import Real

from src.evaluation.flexibility_envelope import (
    ChronologicalFlexibilityEnvelope,
    ChronologicalFlexibilityResult,
    ChronologicalFlexibilityTrace,
    evaluate_chronological_flexibility,
)
from src.grid.rts_gmlc_grid_need_successor import FINITE_GRID_NEED
from src.models.economic_temporal_stochastic import TemporalEconomicScenario
from src.models.rq2_baseline_robustness import (
    FOUR_ARM_IDS,
    FOUR_ARM_SPECS,
    JOINT_B6_SEPARATE_PLANNING_SHARED_EXECUTION,
    ProjectedTemporalScenario,
    project_temporal_scenario_for_arm,
)
from src.scenarios.rq2_public_replay import (
    CausalPolicyOutcome,
    ParameterCell,
    TemporalBlock,
    envelope_for_cell,
    execute_causal_grid_first_policy,
    pair_scenario,
)

REGISTERED_SERVICE_RISK_SCHEMA = "rq2_baseline_registered_service_risk_v1"
UNBOUND_DEBT_VIOLATION_PREFIXES_V1 = (
    "initial_recovery_debt_exceeds_maximum",
    "maximum_recovery_debt_exceeded_at_step_",
    "terminal_debt_exceeded_for_period_",
)
UNBOUND_TERMINAL_CONDITION_VIOLATIONS_V1 = frozenset(
    {
        "mandatory_grid_terminal_recovery_incomplete",
        "policy_terminal_recovery_incomplete",
        "trace_ends_during_active_event",
    }
)


@dataclass(frozen=True)
class RegisteredServiceRiskOutcome:
    schema: str
    resolved: bool
    unresolved_reason: str | None
    registered_failure: bool | None
    registered_physical_failure: bool | None
    service_shortfall_failure: bool | None
    service_shortfall_amount: float | None
    registered_physical_violations: tuple[str, ...]
    excluded_debt_violations: tuple[str, ...]
    excluded_terminal_condition_violations: tuple[str, ...]
    right_censored: bool
    raw_outcome: CausalPolicyOutcome


@dataclass(frozen=True)
class ArmCausalPolicyExecution:
    arm_id: str
    committed_capacity: float
    projected_scenario: TemporalEconomicScenario
    outcome: CausalPolicyOutcome
    registered_service_risk: RegisteredServiceRiskOutcome
    debt_metrics_role: str = "descriptive_only_not_category_deciding"


@dataclass(frozen=True)
class FourArmCausalPolicyExecution:
    arms: tuple[ArmCausalPolicyExecution, ...]

    @property
    def by_arm(self) -> dict[str, ArmCausalPolicyExecution]:
        return {arm.arm_id: arm for arm in self.arms}


@dataclass(frozen=True)
class ArmTrainingSupportAudit:
    arm_id: str
    pair_count: int
    failed_pair_ids: tuple[str, ...]
    unresolved_pair_ids: tuple[str, ...] = ()

    @property
    def passed(self) -> bool:
        return not self.failed_pair_ids and not self.unresolved_pair_ids


@dataclass(frozen=True)
class FourArmTrainingSupportAudit:
    arms: tuple[ArmTrainingSupportAudit, ...]

    @property
    def by_arm(self) -> dict[str, ArmTrainingSupportAudit]:
        return {arm.arm_id: arm for arm in self.arms}


def _validated_capacities(
    capacity_by_arm: Mapping[str, object],
) -> dict[str, float]:
    if set(capacity_by_arm) != set(FOUR_ARM_IDS):
        raise ValueError("four-arm capacity inventory drifted")
    capacities = {}
    for arm_id in FOUR_ARM_IDS:
        raw = capacity_by_arm[arm_id]
        if isinstance(raw, bool) or not isinstance(raw, Real):
            raise ValueError(f"capacity for {arm_id} must be a finite number")
        value = float(raw)
        if not isfinite(value) or value < 0.0:
            raise ValueError(
                f"capacity for {arm_id} must be finite and nonnegative"
            )
        capacities[arm_id] = value
    return capacities


def registered_service_risk_outcome(
    scenario: TemporalEconomicScenario,
    outcome: CausalPolicyOutcome,
) -> RegisteredServiceRiskOutcome:
    """Derive the frozen v1 service-risk fields without discarding raw diagnostics."""

    if not scenario.periods:
        raise ValueError("registered service risk requires a nonempty scenario")
    right_censored = bool(
        scenario.periods[-1] not in scenario.completed_periods
        or not scenario.require_terminal_event_inactive
    )
    debt_violations = tuple(
        code
        for code in outcome.physical_violations
        if code.startswith(UNBOUND_DEBT_VIOLATION_PREFIXES_V1)
    )
    terminal_condition_violations = tuple(
        code
        for code in outcome.physical_violations
        if code in UNBOUND_TERMINAL_CONDITION_VIOLATIONS_V1
    )
    excluded = {*debt_violations, *terminal_condition_violations}
    registered_violations = tuple(
        code for code in outcome.physical_violations if code not in excluded
    )
    raw_physical_failure = bool(
        outcome.hard_grid_failure or outcome.physical_policy_failure
    )
    diagnostics_consistent = raw_physical_failure == bool(
        outcome.physical_violations
    )
    resolved = bool(outcome.resolved and diagnostics_consistent)
    unresolved_reason = None
    if not outcome.resolved:
        unresolved_reason = "source_causal_outcome_unresolved"
    elif not diagnostics_consistent:
        unresolved_reason = "raw_physical_failure_and_violation_inventory_disagree"
    registered_physical_failure = (
        bool(registered_violations) if resolved else None
    )
    shortfall_failure = (
        bool(outcome.service_shortfall_failure) if resolved else None
    )
    return RegisteredServiceRiskOutcome(
        schema=REGISTERED_SERVICE_RISK_SCHEMA,
        resolved=resolved,
        unresolved_reason=unresolved_reason,
        registered_failure=(
            bool(registered_physical_failure or shortfall_failure)
            if resolved
            else None
        ),
        registered_physical_failure=registered_physical_failure,
        service_shortfall_failure=shortfall_failure,
        service_shortfall_amount=(outcome.access_shortfall if resolved else None),
        registered_physical_violations=registered_violations,
        excluded_debt_violations=debt_violations,
        excluded_terminal_condition_violations=terminal_condition_violations,
        right_censored=right_censored,
        raw_outcome=outcome,
    )


def project_finite_scenario_for_arm(
    scenario: TemporalEconomicScenario,
    arm_id: str,
    *,
    grid_state: str,
) -> ProjectedTemporalScenario:
    """Project one scenario only after an explicit finite-grid assertion."""

    if grid_state != FINITE_GRID_NEED:
        raise ValueError("four-arm replay requires explicit finite_grid_need state")
    return project_temporal_scenario_for_arm(scenario, arm_id)


def execute_four_arm_causal_policy(
    scenario: TemporalEconomicScenario,
    envelope: ChronologicalFlexibilityEnvelope,
    capacity_by_arm: Mapping[str, object],
    *,
    grid_state: str,
    service_shortfall_tolerance: float,
) -> FourArmCausalPolicyExecution:
    """Replay all four fixed capacities through the same shared envelope."""

    if grid_state != FINITE_GRID_NEED:
        raise ValueError("four-arm replay requires explicit finite_grid_need state")
    capacities = _validated_capacities(capacity_by_arm)
    executions = []
    for arm_id in FOUR_ARM_IDS:
        projected = project_finite_scenario_for_arm(
            scenario,
            arm_id,
            grid_state=grid_state,
        )
        outcome = execute_causal_grid_first_policy(
            projected.scenario,
            envelope,
            capacities[arm_id],
            service_shortfall_tolerance=service_shortfall_tolerance,
        )
        executions.append(
            ArmCausalPolicyExecution(
                arm_id=arm_id,
                committed_capacity=capacities[arm_id],
                projected_scenario=projected.scenario,
                outcome=outcome,
                registered_service_risk=registered_service_risk_outcome(
                    projected.scenario,
                    outcome,
                ),
            )
        )
    return FourArmCausalPolicyExecution(arms=tuple(executions))


def evaluate_training_trace_support(
    scenario: TemporalEconomicScenario,
    envelope: ChronologicalFlexibilityEnvelope,
    call: tuple[float, ...],
    capacity: float,
) -> ChronologicalFlexibilityResult:
    """Audit one registered planning trace through the public causal envelope."""

    if isinstance(capacity, bool) or not isinstance(capacity, Real):
        raise ValueError("training capacity must be a finite number")
    committed = float(capacity)
    if not isfinite(committed) or committed < 0.0:
        raise ValueError("training capacity must be finite and nonnegative")
    available = (
        scenario.available_flexibility_mw
        if scenario.available_flexibility_mw is not None
        else scenario.connected_demand_mw
    )
    call_limit = tuple(
        min(committed, flexible, connected)
        for flexible, connected in zip(
            available,
            scenario.connected_demand_mw,
            strict=True,
        )
    )
    start = datetime(2000, 1, 1, tzinfo=timezone.utc)
    trace = ChronologicalFlexibilityTrace(
        name=scenario.name,
        timestamps=tuple(
            start + timedelta(hours=envelope.time_step_hours * index)
            for index in range(len(call))
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
    return evaluate_chronological_flexibility(trace, envelope)


def audit_four_arm_training_support(
    power_blocks: tuple[TemporalBlock, ...],
    workload_blocks: tuple[TemporalBlock, ...],
    cell: ParameterCell,
    *,
    capacity_by_arm: Mapping[str, object],
    fixed_policy: Mapping[str, object],
    grid_state_by_power_block: Mapping[str, str],
) -> FourArmTrainingSupportAudit:
    """Audit all finite training pairs under each arm's planning semantics."""

    if not power_blocks or not workload_blocks:
        raise ValueError("full-support audit requires both training marginals")
    if any(
        block.split != "training" for block in (*power_blocks, *workload_blocks)
    ):
        raise ValueError("training support audit cannot contain holdout blocks")
    power_ids = tuple(block.block_id for block in power_blocks)
    workload_ids = tuple(block.block_id for block in workload_blocks)
    if len(set(power_ids)) != len(power_ids):
        raise ValueError("power block IDs must be unique")
    if len(set(workload_ids)) != len(workload_ids):
        raise ValueError("workload block IDs must be unique")
    if set(grid_state_by_power_block) != set(power_ids):
        raise ValueError("power block state inventory drifted")
    if any(
        grid_state_by_power_block[block_id] != FINITE_GRID_NEED
        for block_id in power_ids
    ):
        raise ValueError("training support audit accepts finite_grid_need only")
    capacities = _validated_capacities(capacity_by_arm)
    envelope = envelope_for_cell(cell, policy=dict(fixed_policy))
    failures = {arm_id: [] for arm_id in FOUR_ARM_IDS}
    pair_count = 0
    for power in power_blocks:
        for workload in workload_blocks:
            pair_id = f"{power.block_id}__{workload.block_id}"
            scenario = pair_scenario(
                power,
                workload,
                cell,
                name=f"training_audit__{pair_id}",
            )
            pair_count += 1
            for spec in FOUR_ARM_SPECS:
                projected = project_finite_scenario_for_arm(
                    scenario,
                    spec.arm_id,
                    grid_state=grid_state_by_power_block[power.block_id],
                ).scenario
                if spec.arm_id == JOINT_B6_SEPARATE_PLANNING_SHARED_EXECUTION:
                    grid_audit = evaluate_training_trace_support(
                        projected,
                        envelope,
                        projected.grid_need_mw,
                        capacities[spec.arm_id],
                    )
                    green_audit = evaluate_training_trace_support(
                        projected,
                        envelope,
                        projected.green_call_mw,
                        capacities[spec.arm_id],
                    )
                    passes = grid_audit.feasible and green_audit.feasible
                else:
                    combined = tuple(
                        grid + green
                        for grid, green in zip(
                            projected.grid_need_mw,
                            projected.green_call_mw,
                            strict=True,
                        )
                    )
                    passes = evaluate_training_trace_support(
                        projected,
                        envelope,
                        combined,
                        capacities[spec.arm_id],
                    ).feasible
                if not passes:
                    failures[spec.arm_id].append(pair_id)
    return FourArmTrainingSupportAudit(
        arms=tuple(
            ArmTrainingSupportAudit(
                arm_id=arm_id,
                pair_count=pair_count,
                failed_pair_ids=tuple(failures[arm_id]),
            )
            for arm_id in FOUR_ARM_IDS
        )
    )
