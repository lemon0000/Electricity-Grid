"""Four-arm minimum-flexibility planning for the RQ2 robustness design."""

from __future__ import annotations

from dataclasses import dataclass, fields, replace

from src.models.economic_temporal_stochastic import (
    TemporalEconomicInputs,
    TemporalEconomicScenario,
)
from src.models.temporal_flexibility_capacity_successor import (
    MinimumFlexibilityCapacitySuccessor,
    solve_minimum_temporal_flexibility_with_spec,
)
from src.solvers.rq2_solver_adapter import Rq2SolverSpec

NETWORK_ONLY_SHARED = "network_only_shared"
CFE_ONLY_SHARED = "cfe_only_shared"
JOINT_CORRECT_SHARED = "joint_correct_shared"
JOINT_B6_SEPARATE_PLANNING_SHARED_EXECUTION = (
    "joint_b6_separate_planning_shared_execution"
)


@dataclass(frozen=True)
class BaselineRobustnessArmSpec:
    arm_id: str
    grid_call_rule: str
    green_call_rule: str
    enforce_joint_budget: bool
    planning_envelope: str
    execution_envelope: str = "shared"


FOUR_ARM_SPECS = (
    BaselineRobustnessArmSpec(
        arm_id=NETWORK_ONLY_SHARED,
        grid_call_rule="preserve",
        green_call_rule="zero",
        enforce_joint_budget=True,
        planning_envelope="shared",
    ),
    BaselineRobustnessArmSpec(
        arm_id=CFE_ONLY_SHARED,
        grid_call_rule="zero",
        green_call_rule="preserve",
        enforce_joint_budget=True,
        planning_envelope="shared",
    ),
    BaselineRobustnessArmSpec(
        arm_id=JOINT_CORRECT_SHARED,
        grid_call_rule="preserve",
        green_call_rule="preserve",
        enforce_joint_budget=True,
        planning_envelope="shared",
    ),
    BaselineRobustnessArmSpec(
        arm_id=JOINT_B6_SEPARATE_PLANNING_SHARED_EXECUTION,
        grid_call_rule="preserve",
        green_call_rule="preserve",
        enforce_joint_budget=False,
        planning_envelope="separate_by_service_then_combined",
    ),
)
FOUR_ARM_IDS = tuple(spec.arm_id for spec in FOUR_ARM_SPECS)


@dataclass(frozen=True)
class ScenarioCallProjectionAudit:
    arm_id: str
    grid_call_rule: str
    green_call_rule: str
    changed_grid_entries: int
    changed_green_entries: int
    non_call_fields_preserved: bool


@dataclass(frozen=True)
class ProjectedTemporalScenario:
    scenario: TemporalEconomicScenario
    audit: ScenarioCallProjectionAudit


@dataclass(frozen=True)
class TrainingInputProjectionAudit:
    arm_id: str
    scenario_count: int
    enforce_joint_budget: bool
    changed_grid_entries: int
    changed_green_entries: int
    non_call_scenario_fields_preserved: bool
    non_scenario_input_fields_preserved: bool
    idempotent: bool


@dataclass(frozen=True)
class ProjectedTrainingInputs:
    inputs: TemporalEconomicInputs
    audit: TrainingInputProjectionAudit


@dataclass(frozen=True)
class ArmMinimumFlexibilityPlanning:
    arm_id: str
    result: MinimumFlexibilityCapacitySuccessor
    input_projection_audit: TrainingInputProjectionAudit


@dataclass(frozen=True)
class FourArmMinimumFlexibilityPlanning:
    arms: tuple[ArmMinimumFlexibilityPlanning, ...]

    @property
    def by_arm(self) -> dict[str, ArmMinimumFlexibilityPlanning]:
        return {arm.arm_id: arm for arm in self.arms}


def arm_spec(arm_id: str) -> BaselineRobustnessArmSpec:
    """Return one frozen arm specification or fail on inventory drift."""

    for spec in FOUR_ARM_SPECS:
        if spec.arm_id == arm_id:
            return spec
    raise ValueError(f"unknown RQ2 baseline robustness arm: {arm_id}")


def project_temporal_scenario_for_arm(
    scenario: TemporalEconomicScenario,
    arm_id: str,
) -> ProjectedTemporalScenario:
    """Project only the registered service calls for one arm."""

    spec = arm_spec(arm_id)
    grid_call = (
        (0.0,) * len(scenario.grid_need_mw)
        if spec.grid_call_rule == "zero"
        else scenario.grid_need_mw
    )
    green_call = (
        (0.0,) * len(scenario.green_call_mw)
        if spec.green_call_rule == "zero"
        else scenario.green_call_mw
    )
    projected = replace(
        scenario,
        grid_need_mw=grid_call,
        green_call_mw=green_call,
    )
    excluded = {"grid_need_mw", "green_call_mw"}
    non_call_preserved = all(
        getattr(projected, field.name) == getattr(scenario, field.name)
        for field in fields(scenario)
        if field.name not in excluded
    )
    return ProjectedTemporalScenario(
        scenario=projected,
        audit=ScenarioCallProjectionAudit(
            arm_id=arm_id,
            grid_call_rule=spec.grid_call_rule,
            green_call_rule=spec.green_call_rule,
            changed_grid_entries=sum(
                source != target
                for source, target in zip(
                    scenario.grid_need_mw,
                    grid_call,
                    strict=True,
                )
            ),
            changed_green_entries=sum(
                source != target
                for source, target in zip(
                    scenario.green_call_mw,
                    green_call,
                    strict=True,
                )
            ),
            non_call_fields_preserved=non_call_preserved,
        ),
    )


def project_training_inputs_for_arm(
    inputs: TemporalEconomicInputs,
    arm_id: str,
) -> ProjectedTrainingInputs:
    """Return a non-mutating four-arm training-input projection."""

    spec = arm_spec(arm_id)
    scenarios = tuple(
        project_temporal_scenario_for_arm(scenario, arm_id)
        for scenario in inputs.scenarios
    )
    projected = replace(
        inputs,
        scenarios=tuple(item.scenario for item in scenarios),
        enforce_joint_budget=spec.enforce_joint_budget,
    )
    excluded = {"scenarios", "enforce_joint_budget"}
    non_scenario_inputs_preserved = all(
        getattr(projected, field.name) == getattr(inputs, field.name)
        for field in fields(inputs)
        if field.name not in excluded
    )
    repeated = tuple(
        project_temporal_scenario_for_arm(item.scenario, arm_id).scenario
        for item in scenarios
    )
    return ProjectedTrainingInputs(
        inputs=projected,
        audit=TrainingInputProjectionAudit(
            arm_id=arm_id,
            scenario_count=len(scenarios),
            enforce_joint_budget=spec.enforce_joint_budget,
            changed_grid_entries=sum(
                item.audit.changed_grid_entries for item in scenarios
            ),
            changed_green_entries=sum(
                item.audit.changed_green_entries for item in scenarios
            ),
            non_call_scenario_fields_preserved=all(
                item.audit.non_call_fields_preserved for item in scenarios
            ),
            non_scenario_input_fields_preserved=non_scenario_inputs_preserved,
            idempotent=(
                repeated == tuple(item.scenario for item in scenarios)
            ),
        ),
    )


def plan_four_arm_minimum_flexibility_with_spec(
    inputs: TemporalEconomicInputs,
    *,
    solver_specification: Rq2SolverSpec,
) -> FourArmMinimumFlexibilityPlanning:
    """Solve the exact four-arm inventory under one solver specification."""

    planned = []
    for spec in FOUR_ARM_SPECS:
        projection = project_training_inputs_for_arm(inputs, spec.arm_id)
        result = solve_minimum_temporal_flexibility_with_spec(
            projection.inputs,
            enforce_joint_budget=spec.enforce_joint_budget,
            solver_specification=solver_specification,
        )
        planned.append(
            ArmMinimumFlexibilityPlanning(
                arm_id=spec.arm_id,
                result=result,
                input_projection_audit=projection.audit,
            )
        )
    return FourArmMinimumFlexibilityPlanning(arms=tuple(planned))
