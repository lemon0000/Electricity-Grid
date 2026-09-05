"""Validate the complete RQ2 joint-deliverability scientific successor v5."""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import stat
from itertools import product
from pathlib import Path
from typing import Any

import numpy as np
import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_RELATIVE = "configs/rq2_joint_deliverability_preregistration_successor_v5.yaml"
SPEC_RELATIVE = "docs/model_spec/rq2_joint_deliverability_estimands_v4.md"
PLAN_RELATIVE = "docs/plan/RQ2_联合服务可交付前沿确认性方案_v5.md"
VALIDATOR_RELATIVE = (
    "experiments/validate_rq2_joint_deliverability_preregistration_successor_v5.py"
)
TEST_RELATIVE = "tests/test_rq2_joint_deliverability_preregistration_successor_v5.py"
INNER_RELATIVE = (
    "configs/rq2_joint_deliverability_preregistration_successor_v5.SHA256SUMS.json"
)
OUTER_RELATIVE = (
    "configs/rq2_joint_deliverability_preregistration_successor_v5."
    "OUTER.SHA256SUMS.json"
)
CONFIG = ROOT / CONFIG_RELATIVE
SPEC = ROOT / SPEC_RELATIVE
PLAN = ROOT / PLAN_RELATIVE
INNER = ROOT / INNER_RELATIVE
OUTER = ROOT / OUTER_RELATIVE

V4_OUTER = (
    ROOT / "configs/rq2_joint_deliverability_preregistration_successor_v4."
    "OUTER.SHA256SUMS.json"
)
V4_OUTER_SHA256 = "101fc1bc071b06779ee779beb1bb7b5f61640af8fa4b8ccb7f44b7c019710a3e"
V4_REWORK = (
    ROOT / "configs/rq2_joint_deliverability_preregistration_review_rework_v4.yaml"
)
V4_REWORK_SHA256 = "dab9573ed70689edbf64408c2b690f7016520839c706e2592cf5177ef7bad954"

EXPECTED_SEMANTIC_SHA256 = (
    "31be646a725f9aef7498fd57b140b404828bfba4afa9c98912c20346aae4b8e4"
)
BOOTSTRAP_PROBE_SHA256 = (
    "f2a5ed36b6bb1c263b16c5888efe6a36b6072d3caf0c98d7ad50fdfca296c9d9"
)
TRANSPORT_PROBE_SHA256 = (
    "716e489913b2dff47c1299b560568d1aa1e3615ac2ac1301431ff6af1e9449d5"
)
EXPECTED_SPEC_SEMANTIC_SHA256 = (
    "779982083366b7b85918c8a6c2147566300f3e9a680c6de45d5a059e779f1f6d"
)
EXPECTED_PLAN_SEMANTIC_SHA256 = (
    "8c19e8d04d1c15c55df4e17c9a2d84b18968a8a5e2a133adc9f6e4c684784eb5"
)
EXPECTED_TOP_LEVEL = {
    "schema",
    "version",
    "created_on",
    "lifecycle",
    "authority",
    "scope",
    "research_question",
    "evidence_scope",
    "data_contract",
    "input_schema_contract",
    "cfe_contract",
    "workload_and_recovery_contract",
    "temporal_envelope",
    "arm_contract",
    "planning_formulation",
    "registered_design",
    "representative_selection",
    "zero_recovery_structural_precheck",
    "planning_contract",
    "solver_contract",
    "capacity_estimands",
    "frontier_outputs",
    "attribution_contract",
    "holdout_policy",
    "holdout_identification",
    "bootstrap_contract",
    "decision_and_claim_rules",
    "implementation_requirements",
}
EXPECTED_LIFECYCLE_KEYS = {
    "status",
    "sealed_on",
    "pre_seal_audit_complete",
    "sealed_ready_for_independent_review",
    "independent_R4_review_passed",
    "implementation_bound",
    "upstream_grid_package_ready",
    "user_formal_run_authorized",
    "formal_execution_ready",
    "formal_result",
    "paper_claim",
}
EXPECTED_FALSE_EXECUTION_GATES = {
    "independent_R4_review_passed",
    "implementation_bound",
    "upstream_grid_package_ready",
    "user_formal_run_authorized",
    "formal_execution_ready",
    "formal_result",
    "paper_claim",
}
EXPECTED_INNER_MEMBERS = {
    CONFIG_RELATIVE,
    SPEC_RELATIVE,
    PLAN_RELATIVE,
    VALIDATOR_RELATIVE,
    TEST_RELATIVE,
}
ARM_ORDER = (
    "network_only_shared",
    "cfe_only_shared",
    "joint_correct_shared",
    "joint_b6_separate_planning_shared_execution",
)
ALL_CAPACITY_LABELS = {
    "joint_extra_requirement",
    "joint_portfolio_relief",
    "joint_interaction_near_zero",
    "joint_interaction_indeterminate",
    "b6_capacity_underprovisioning",
    "b6_capacity_overprovisioning",
    "b6_capacity_near_zero",
    "b6_capacity_indeterminate",
}
OPERATIONAL_METRICS = (
    "B6_minus_correct_joint_service_failure",
    "B6_minus_correct_total_service_shortfall",
    "B6_minus_correct_cfe_shortfall",
)
SHA256_HEX_LENGTH = 64


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_bytes(value: object) -> bytes:
    _validate_canonical_json_types(value, "canonical payload")
    return (
        json.dumps(
            value,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def _canonical_sha256(value: object) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _validate_canonical_json_types(value: object, label: str) -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise TypeError(f"{label} contains a non-string mapping key")
            _validate_canonical_json_types(child, f"{label}.{key}")
    elif isinstance(value, (list, tuple)):
        for index, child in enumerate(value):
            _validate_canonical_json_types(child, f"{label}[{index}]")
    elif value is not None and not isinstance(value, (str, int, float, bool)):
        raise TypeError(f"{label} contains a non-JSON value")


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be a mapping")
    return value


def _sequence(value: object, label: str) -> list[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, list):
        raise TypeError(f"{label} must be a list")
    return value


class _UniqueKeyLoader(yaml.SafeLoader):
    """Safe YAML loader that rejects duplicate mapping keys."""


def _construct_unique_mapping(
    loader: _UniqueKeyLoader,
    node: yaml.MappingNode,
    deep: bool = False,
) -> dict[object, object]:
    loader.flatten_mapping(node)
    result: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if not isinstance(key, str):
            raise TypeError(f"YAML mapping key must be a string: {key!r}")
        if key in result:
            raise ValueError(f"duplicate YAML key: {key!r}")
        result[key] = loader.construct_object(value_node, deep=deep)
    return result


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_unique_mapping,
)


def _load_yaml_text(text: str, label: str) -> dict[str, Any]:
    return _mapping(yaml.load(text, Loader=_UniqueKeyLoader), label)


def _load_yaml(path: Path) -> dict[str, Any]:
    return _load_yaml_text(path.read_text(encoding="utf-8"), str(path))


def _reject_json_constant(value: str) -> None:
    raise ValueError(f"non-standard JSON constant: {value}")


def _unique_json_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key!r}")
        result[key] = value
    return result


def _load_json_text(text: str, label: str) -> dict[str, Any]:
    return _mapping(
        json.loads(
            text,
            object_pairs_hook=_unique_json_object,
            parse_constant=_reject_json_constant,
        ),
        label,
    )


def _load_json(path: Path) -> dict[str, Any]:
    return _load_json_text(path.read_text(encoding="utf-8"), str(path))


def _equal(observed: object, expected: object, label: str) -> None:
    if type(observed) is not type(expected) or observed != expected:
        raise ValueError(
            f"{label} drifted: expected {expected!r}, observed {observed!r}"
        )


def _exact_keys(value: dict[str, Any], expected: set[str], label: str) -> None:
    if set(value) != expected:
        raise ValueError(f"{label} exact keyset drifted")


def _sha256_digest(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != SHA256_HEX_LENGTH
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _path_appears(path: Path) -> bool:
    return os.path.lexists(path)


def _require_regular_file(path: Path, label: str) -> None:
    absolute = Path(os.path.abspath(path))
    for ancestor in reversed(absolute.parents):
        try:
            mode = os.lstat(ancestor).st_mode
        except OSError as error:
            raise ValueError(f"{label} ancestor is inaccessible") from error
        if stat.S_ISLNK(mode) or not stat.S_ISDIR(mode):
            raise ValueError(f"{label} has an unsafe ancestor")
    try:
        mode = os.lstat(absolute).st_mode
    except OSError as error:
        raise ValueError(f"{label} is missing or unsafe") from error
    if stat.S_ISLNK(mode) or not stat.S_ISREG(mode):
        raise ValueError(f"{label} is missing or unsafe")


def _semantic_payload(design: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in design.items() if key != "lifecycle"}


def _validate_authority(design: dict[str, Any]) -> None:
    authority = _mapping(design["authority"], "authority")
    _equal(authority["mode"], "complete_self_contained_replacement", "authority mode")
    _equal(
        authority["predecessor_scientific_fields_inherited_by_omission"],
        False,
        "omitted predecessor inheritance",
    )
    _equal(
        authority["prior_versions_may_define_current_semantics"],
        False,
        "prior-version authority",
    )
    for path, digest, label in (
        (V4_OUTER, V4_OUTER_SHA256, "v4 outer"),
        (V4_REWORK, V4_REWORK_SHA256, "v4 REWORK receipt"),
    ):
        _require_regular_file(path, label)
        _equal(_sha256(path), digest, f"{label} hash")
    receipt = _load_yaml(V4_REWORK)
    _equal(receipt.get("verdict"), "REWORK", "v4 review verdict")
    _equal(len(_sequence(receipt.get("findings"), "v4 findings")), 1, "v4 Major count")


def expand_registered_cells(design: dict[str, Any]) -> list[dict[str, object]]:
    """Build the exact 36-factorial plus 10-OAT inventory without a solver."""

    registered = _mapping(design["registered_design"], "registered design")
    primary = _mapping(registered["primary_factorial"], "primary factorial")
    factors = _mapping(primary["factors"], "primary factors")
    fixed = _mapping(design["temporal_envelope"], "temporal envelope")[
        "fixed_parameters"
    ]
    fixed = _mapping(fixed, "fixed parameters")
    cells: list[dict[str, object]] = []
    for alpha, flexible, headroom in product(
        factors["hourly_cfe_target"],
        factors["flexible_fraction"],
        factors["normalized_recovery_headroom"],
    ):
        values = {
            "hourly_cfe_target": alpha,
            "flexible_fraction": flexible,
            "normalized_recovery_headroom": headroom,
            **fixed,
        }
        cells.append(
            {
                "cell_id": (
                    f"primary_a{round(alpha * 100):03d}"
                    f"_f{round(flexible * 100):03d}"
                    f"_h{round(headroom * 100):03d}"
                ),
                "family": "primary_factorial",
                "values": values,
            }
        )
    secondary = _mapping(registered["secondary_oat"], "secondary OAT")
    anchor = _mapping(secondary["anchor"], "OAT anchor")
    levels = _mapping(
        _mapping(design["temporal_envelope"], "temporal envelope")["oat_levels"],
        "OAT levels",
    )
    for dimension in secondary["varied_dimensions"]:
        values = _sequence(levels[dimension], f"{dimension} levels")
        if anchor[dimension] not in values:
            raise ValueError(f"OAT anchor is absent from {dimension}")
        added_index = 0
        for value in values:
            if value == anchor[dimension]:
                continue
            payload = dict(anchor)
            payload[dimension] = value
            cells.append(
                {
                    "cell_id": f"oat_{dimension}_{added_index:02d}",
                    "family": "secondary_oat",
                    "values": payload,
                }
            )
            added_index += 1
    return cells


def contrast_intervals(
    bounds: dict[str, tuple[float, float]],
) -> dict[str, tuple[float, float]]:
    """Propagate certified arm intervals into all registered contrasts."""

    if set(bounds) != {"D_N", "D_C", "D_J", "D_B"}:
        raise ValueError("capacity bound inventory drifted")
    normalized: dict[str, tuple[float, float]] = {}
    for arm, pair in bounds.items():
        lower, upper = map(float, pair)
        if not math.isfinite(lower) or not math.isfinite(upper) or lower > upper:
            raise ValueError(f"invalid capacity interval for {arm}")
        normalized[arm] = (lower, upper)
    ln, un = normalized["D_N"]
    lc, uc = normalized["D_C"]
    lj, uj = normalized["D_J"]
    lb, ub = normalized["D_B"]
    single_lower = max(ln, lc)
    single_upper = max(un, uc)
    return {
        "D_single": (single_lower, single_upper),
        "I_joint": (lj - single_upper, uj - single_lower),
        "I_sep": (lb - single_upper, ub - single_lower),
        "A_B6": (lj - ub, uj - lb),
    }


def classify_interval(
    interval: tuple[float, float],
    *,
    tolerance: float = 1.0e-6,
) -> str:
    """Classify a complete certified interval, never an incumbent alone."""

    lower, upper = map(float, interval)
    if not math.isfinite(lower) or not math.isfinite(upper) or lower > upper:
        raise ValueError("invalid contrast interval")
    if lower > tolerance:
        return "robust_positive"
    if upper < -tolerance:
        return "robust_negative"
    if lower >= -tolerance and upper <= tolerance:
        return "certified_near_zero"
    return "numerically_indeterminate"


def operational_labels_from_transport_intervals(
    intervals: dict[str, tuple[float, float]],
    *,
    tolerance: float = 1.0e-6,
) -> dict[str, bool]:
    """Apply the registered exists-metric, for-all-couplings quantifier."""

    if set(intervals) != set(OPERATIONAL_METRICS):
        raise ValueError("operational metric interval inventory drifted")
    validated: list[tuple[float, float]] = []
    for metric in OPERATIONAL_METRICS:
        lower, upper = map(float, intervals[metric])
        if not math.isfinite(lower) or not math.isfinite(upper) or lower > upper:
            raise ValueError(f"invalid operational interval: {metric}")
        validated.append((lower, upper))
    return {
        "b6_operational_penalty": any(lower > tolerance for lower, _ in validated),
        "b6_operational_relief": any(upper < -tolerance for _, upper in validated),
    }


def zero_recovery_structural_trigger(
    required_call: list[float] | tuple[float, ...],
    recovery_headroom: list[float] | tuple[float, ...],
    *,
    maximum_recovery_power: float,
    recovery_efficiency: float,
    initial_recovery_debt: float,
    terminal_recovery_debt_limit: float,
    time_step_hours: float,
    service_tolerance: float,
    tolerance: float,
) -> bool:
    """Apply the registered recovery-energy lower bound to one arm-track-pair."""

    if not required_call or len(required_call) != len(recovery_headroom):
        raise ValueError("structural precheck trajectory inventory drifted")
    values = (
        *required_call,
        *recovery_headroom,
        maximum_recovery_power,
        recovery_efficiency,
        initial_recovery_debt,
        terminal_recovery_debt_limit,
        time_step_hours,
        service_tolerance,
        tolerance,
    )
    if any(not math.isfinite(float(value)) or float(value) < 0.0 for value in values):
        raise ValueError("structural precheck values must be finite and nonnegative")
    if not 0.0 < recovery_efficiency <= 1.0 or time_step_hours <= 0.0:
        raise ValueError("precheck efficiency and time step must be positive")
    effective_required_call = [
        0.0 if call <= service_tolerance else float(call) for call in required_call
    ]
    eligible_recovery = (
        min(maximum_recovery_power, headroom) if call == 0.0 else 0.0
        for call, headroom in zip(
            effective_required_call,
            recovery_headroom,
            strict=True,
        )
    )
    terminal_lower_bound = (
        initial_recovery_debt
        + math.fsum(effective_required_call) * time_step_hours
        - recovery_efficiency * math.fsum(eligible_recovery) * time_step_hours
    )
    return terminal_lower_bound > terminal_recovery_debt_limit + tolerance


def lift_power_block_state(
    hourly_states: list[str] | tuple[str, ...],
) -> str:
    """Lift the 24 hourly dispatch states to the registered block state."""

    if len(hourly_states) != 24:
        raise ValueError("power block must contain exactly 24 hourly states")
    allowed = {"finite_grid_need", "exogenous_grid_infeasibility"}
    if any(type(state) is not str or state not in allowed for state in hourly_states):
        raise ValueError("power block contains an unregistered hourly state")
    if "exogenous_grid_infeasibility" in hourly_states:
        return "exogenous_grid_infeasibility"
    return "finite_grid_need"


def e0_mass_by_unique_block(
    marginal_rows: list[tuple[str, float]],
    state_by_block: dict[str, str],
) -> float:
    """Compute unconditional E0 mass once per unique power block."""

    seen: set[str] = set()
    mass_terms: list[float] = []
    for block_id, probability in marginal_rows:
        if type(block_id) is not str or not block_id:
            raise ValueError("power marginal block ID must be a nonempty string")
        if block_id in seen:
            raise ValueError("power marginal contains a duplicate block ID")
        seen.add(block_id)
        value = float(probability)
        if not math.isfinite(value) or value < 0.0 or value > 1.0:
            raise ValueError("power marginal probability is invalid")
        state = state_by_block.get(block_id)
        if state not in {"finite_grid_need", "exogenous_grid_infeasibility"}:
            raise ValueError("power marginal block state is missing or invalid")
        if state == "exogenous_grid_infeasibility":
            mass_terms.append(value)
    if seen != set(state_by_block):
        raise ValueError("power marginal and block-state inventories differ")
    total = math.fsum(float(value) for _, value in marginal_rows)
    if not math.isclose(total, 1.0, rel_tol=0.0, abs_tol=1.0e-9):
        raise ValueError("power marginal probability mass drifted")
    return math.fsum(mass_terms)


def finite_conditioning_denominator(
    e0_mass: float,
    *,
    tolerance: float = 1.0e-9,
) -> float | None:
    """Return the finite-support mass, or None when that support is empty."""

    mass = float(e0_mass)
    if (
        not math.isfinite(mass)
        or mass < -tolerance
        or mass > 1.0 + tolerance
        or tolerance < 0.0
    ):
        raise ValueError("E0 mass or tolerance is invalid")
    if mass >= 1.0 - tolerance:
        return None
    return 1.0 - mass


def _numeric_vector(
    values: list[float] | tuple[float, ...],
    *,
    label: str,
    length: int,
) -> list[float]:
    if len(values) != length:
        raise ValueError(f"{label} length drifted")
    result = [float(value) for value in values]
    if any(not math.isfinite(value) or value < 0.0 for value in result):
        raise ValueError(f"{label} must be finite and nonnegative")
    return result


def execute_holdout_policy(
    *,
    committed_capacity: float,
    grid_request: list[float] | tuple[float, ...],
    cfe_request: list[float] | tuple[float, ...],
    available_flexibility: list[float] | tuple[float, ...],
    connected_demand: list[float] | tuple[float, ...],
    current_recovery_headroom: list[float] | tuple[float, ...],
    maximum_recovery_power: float,
    recovery_efficiency: float,
    maximum_event_duration_hours: float,
    maximum_event_count: int,
    minimum_recovery_hours: float,
    normalized_energy_budget: float,
    normalized_debt_limit: float,
    terminal_recovery_debt_limit: float,
    time_step_hours: float,
    minimum_event_power: float,
    curtailment_ramp_per_hour: float,
    response_time_hours: float,
    service_shortfall_tolerance: float,
) -> dict[str, object]:
    """Execute the frozen current-state-only shared-envelope policy."""

    length = len(grid_request)
    if length == 0:
        raise ValueError("holdout trajectory must be nonempty")
    grid = _numeric_vector(grid_request, label="grid request", length=length)
    cfe = _numeric_vector(cfe_request, label="CFE request", length=length)
    available = _numeric_vector(
        available_flexibility,
        label="available flexibility",
        length=length,
    )
    connected = _numeric_vector(
        connected_demand,
        label="connected demand",
        length=length,
    )
    recovery_headroom = _numeric_vector(
        current_recovery_headroom,
        label="recovery headroom",
        length=length,
    )
    scalar_values = (
        committed_capacity,
        maximum_recovery_power,
        recovery_efficiency,
        maximum_event_duration_hours,
        minimum_recovery_hours,
        normalized_energy_budget,
        normalized_debt_limit,
        terminal_recovery_debt_limit,
        time_step_hours,
        minimum_event_power,
        curtailment_ramp_per_hour,
        response_time_hours,
        service_shortfall_tolerance,
    )
    if any(
        not math.isfinite(float(value)) or float(value) < 0.0 for value in scalar_values
    ):
        raise ValueError("holdout scalar inputs must be finite and nonnegative")
    if not 0.0 < recovery_efficiency <= 1.0:
        raise ValueError("holdout recovery efficiency must be in (0, 1]")
    if (
        type(maximum_event_count) is not int
        or time_step_hours <= 0.0
        or maximum_event_count < 0
    ):
        raise ValueError("holdout time step and event count are invalid")
    grid = [
        0.0 if request <= service_shortfall_tolerance else request for request in grid
    ]
    cfe = [
        0.0 if request <= service_shortfall_tolerance else request for request in cfe
    ]

    previous_call = 0.0
    previous_active = False
    active_duration = 0.0
    event_count = 0
    interevent_rest: float | None = None
    cumulative_energy = 0.0
    recovery_debt = 0.0
    has_prior_event = False
    trajectory: list[dict[str, object]] = []

    for hour in range(length):
        terminal = hour == length - 1
        can_continue = (
            previous_active
            and active_duration + time_step_hours <= maximum_event_duration_hours
        )
        can_start = (
            not previous_active
            and event_count < maximum_event_count
            and (
                not has_prior_event
                or (
                    interevent_rest is not None
                    and interevent_rest >= minimum_recovery_hours
                )
            )
        )
        active_permitted = not terminal and (can_continue or can_start)
        remaining_energy_power = max(
            0.0,
            (normalized_energy_budget - cumulative_energy) / time_step_hours,
        )
        remaining_debt_power = max(
            0.0,
            (normalized_debt_limit - recovery_debt) / time_step_hours,
        )
        upward_cap = previous_call + min(
            curtailment_ramp_per_hour * time_step_hours,
            curtailment_ramp_per_hour * response_time_hours,
        )
        call_cap = min(
            committed_capacity,
            available[hour],
            connected[hour],
            remaining_energy_power,
            remaining_debt_power,
            upward_cap,
        )
        requested = grid[hour] + cfe[hour]
        candidate_call = min(requested, max(0.0, call_cap))
        active = active_permitted and candidate_call >= minimum_event_power
        if active:
            grid_served = min(grid[hour], candidate_call)
            cfe_served = min(cfe[hour], candidate_call - grid_served)
        else:
            grid_served = 0.0
            cfe_served = 0.0
        total_call = grid_served + cfe_served
        event_start = active and not previous_active
        event_stop = previous_active and not active
        debt_before_recovery = recovery_debt + total_call * time_step_hours
        if active:
            recovery = 0.0
        else:
            recovery = min(
                maximum_recovery_power,
                recovery_headroom[hour],
                debt_before_recovery / (recovery_efficiency * time_step_hours),
            )
        debt_after_recovery = (
            debt_before_recovery - recovery_efficiency * recovery * time_step_hours
        )
        if debt_after_recovery > normalized_debt_limit + 1.0e-12:
            raise ValueError("holdout policy exceeded maximum recovery debt")

        next_duration = (
            active_duration + time_step_hours
            if active and previous_active
            else (time_step_hours if active else 0.0)
        )
        next_event_count = event_count + int(event_start)
        if active:
            next_rest = None
        elif previous_active:
            next_rest = time_step_hours
        elif has_prior_event:
            if interevent_rest is None:
                raise ValueError("holdout rest state is internally inconsistent")
            next_rest = interevent_rest + time_step_hours
        else:
            next_rest = None
        next_energy = cumulative_energy + total_call * time_step_hours
        next_has_prior_event = has_prior_event or event_start
        trajectory.append(
            {
                "hour": hour,
                "grid_served": grid_served,
                "cfe_served": cfe_served,
                "total_call": total_call,
                "active": active,
                "event_start": event_start,
                "event_stop": event_stop,
                "recovery": recovery,
                "recovery_debt": debt_after_recovery,
                "active_event_duration": next_duration,
                "event_count": next_event_count,
                "interevent_rest": next_rest,
                "cumulative_call_energy": next_energy,
                "has_prior_event": next_has_prior_event,
            }
        )
        previous_call = total_call
        previous_active = active
        active_duration = next_duration
        event_count = next_event_count
        interevent_rest = next_rest
        cumulative_energy = next_energy
        recovery_debt = debt_after_recovery
        has_prior_event = next_has_prior_event

    grid_shortfall = (
        math.fsum(
            max(request - float(row["grid_served"]), 0.0)
            for request, row in zip(grid, trajectory, strict=True)
        )
        * time_step_hours
    )
    cfe_shortfall = (
        math.fsum(
            max(request - float(row["cfe_served"]), 0.0)
            for request, row in zip(cfe, trajectory, strict=True)
        )
        * time_step_hours
    )
    recovery_failure = (
        recovery_debt > terminal_recovery_debt_limit + service_shortfall_tolerance
    )
    return {
        "trajectory": trajectory,
        "metrics": {
            "grid_shortfall": grid_shortfall,
            "cfe_shortfall": cfe_shortfall,
            "total_service_shortfall": grid_shortfall + cfe_shortfall,
            "hard_grid_failure": (grid_shortfall > service_shortfall_tolerance),
            "cfe_service_failure": (cfe_shortfall > service_shortfall_tolerance),
            "recovery_completion_failure": recovery_failure,
            "joint_service_failure": (
                grid_shortfall > service_shortfall_tolerance
                or cfe_shortfall > service_shortfall_tolerance
                or recovery_failure
            ),
        },
    }


def _hexify_floats(value: object) -> object:
    if isinstance(value, bool) or value is None or isinstance(value, (str, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError("canonical certificate contains a nonfinite float")
        return value.hex()
    if isinstance(value, dict):
        return {str(key): _hexify_floats(child) for key, child in value.items()}
    if isinstance(value, (list, tuple)):
        return [_hexify_floats(child) for child in value]
    raise TypeError("canonical certificate contains an unsupported value")


def holdout_probe_sha256(design: dict[str, Any]) -> str:
    """Execute and hash the registered deterministic holdout trajectory."""

    policy = _mapping(design["holdout_policy"], "holdout policy")
    probe = _mapping(policy["deterministic_probe"], "holdout deterministic probe")
    temporal = _mapping(design["temporal_envelope"], "temporal envelope")
    payload = execute_holdout_policy(
        committed_capacity=float(probe["committed_capacity"]),
        grid_request=probe["grid_request"],
        cfe_request=probe["cfe_request"],
        available_flexibility=probe["available_flexibility"],
        connected_demand=probe["connected_demand"],
        current_recovery_headroom=probe["current_recovery_headroom"],
        maximum_recovery_power=float(probe["maximum_recovery_power"]),
        recovery_efficiency=float(probe["recovery_efficiency"]),
        maximum_event_duration_hours=float(probe["maximum_event_duration_hours"]),
        maximum_event_count=int(probe["maximum_event_count"]),
        minimum_recovery_hours=float(probe["minimum_recovery_hours"]),
        normalized_energy_budget=float(probe["normalized_energy_budget"]),
        normalized_debt_limit=float(probe["normalized_debt_limit"]),
        terminal_recovery_debt_limit=float(temporal["terminal_recovery_debt_limit"]),
        time_step_hours=float(design["data_contract"]["time_step_hours"]),
        minimum_event_power=float(temporal["minimum_event_power"]),
        curtailment_ramp_per_hour=float(temporal["curtailment_ramp_per_hour"]),
        response_time_hours=float(temporal["response_time_hours"]),
        service_shortfall_tolerance=float(temporal["service_shortfall_tolerance"]),
    )
    return _canonical_sha256(_hexify_floats(payload))


def _transport_equalities(
    rows: np.ndarray,
    columns: np.ndarray,
) -> tuple[np.ndarray, np.ndarray]:
    row_count = rows.size
    column_count = columns.size
    variable_count = row_count * column_count
    matrix = np.zeros((row_count + column_count - 1, variable_count))
    for row in range(row_count):
        matrix[row, row * column_count : (row + 1) * column_count] = 1.0
    for column in range(column_count - 1):
        matrix[row_count + column, column::column_count] = 1.0
    return matrix, np.concatenate((rows, columns[:-1]))


def _transport_probe_endpoint(
    objective: np.ndarray,
    equality_matrix: np.ndarray,
    equality_rhs: np.ndarray,
    coupling_values: list[float],
    dual_values: list[float],
    *,
    extremum: str,
) -> dict[str, object]:
    primal_vector = np.asarray(coupling_values, dtype=np.float64)
    dual_vector = np.asarray(dual_values, dtype=np.float64)
    if (
        primal_vector.shape != objective.shape
        or dual_vector.shape != equality_rhs.shape
        or not np.all(np.isfinite(primal_vector))
        or not np.all(np.isfinite(dual_vector))
        or np.any(primal_vector < 0.0)
    ):
        raise ValueError(f"transport {extremum} analytic witness is invalid")
    primal_objective = float(objective @ primal_vector)
    dual_objective = float(equality_rhs @ dual_vector)
    marginal_residual = float(
        np.max(np.abs(equality_matrix @ primal_vector - equality_rhs))
    )
    dual_residual = max(
        0.0,
        float(np.max(equality_matrix.T @ dual_vector - objective)),
    )
    primal_dual_gap = abs(primal_objective - dual_objective)
    if marginal_residual > 1.0e-8 or dual_residual > 1.0e-8 or primal_dual_gap > 1.0e-8:
        raise ValueError(f"transport {extremum} probe certificate failed")
    endpoint_value = primal_objective if extremum == "lower" else -primal_objective
    return {
        "extremum": extremum,
        "endpoint_value": endpoint_value,
        "primal_objective_min_form": primal_objective,
        "dual_objective_min_form": dual_objective,
        "primal_dual_gap": primal_dual_gap,
        "marginal_residual": marginal_residual,
        "dual_feasibility_residual": dual_residual,
        "coupling_row_major": primal_vector.tolist(),
        "dual_equality_variables": dual_vector.tolist(),
        "primal_status": "analytic_feasible",
        "dual_status": "analytic_feasible",
    }


def transport_probe_payload(design: dict[str, Any]) -> dict[str, object]:
    """Verify and serialize the registered analytic transport certificate."""

    transport = _mapping(
        _mapping(design["holdout_identification"], "holdout identification")[
            "transport"
        ],
        "transport",
    )
    software = _mapping(transport["software"], "transport software")
    _equal(
        software,
        {
            "python": "3.11.15",
            "numpy": "1.26.4",
            "scipy": "1.17.0",
            "scipy_bundled_highs": "1.8.0",
        },
        "transport software",
    )
    _equal(np.__version__, software["numpy"], "transport NumPy runtime")
    solver = _mapping(transport["scalar_endpoint_solver"], "transport solver")
    _equal(solver["api"], "scipy.optimize.linprog", "transport solver API")
    _equal(solver["method"], "highs-ds", "transport solver method")
    options = _mapping(solver["options"], "transport solver options")
    _equal(
        options,
        {
            "presolve": True,
            "dual_feasibility_tolerance": 1.0e-9,
            "primal_feasibility_tolerance": 1.0e-9,
        },
        "transport solver options",
    )
    _equal(
        solver["environment"],
        {"OMP_NUM_THREADS": "1"},
        "transport solver environment",
    )
    probe = _mapping(transport["deterministic_probe"], "transport probe")
    rows = np.asarray(probe["row_probabilities"], dtype=np.float64)
    columns = np.asarray(probe["column_probabilities"], dtype=np.float64)
    metric = np.asarray(probe["metric_row_major"], dtype=np.float64)
    if metric.shape != (rows.size, columns.size):
        raise ValueError("transport probe metric shape drifted")
    equality_matrix, equality_rhs = _transport_equalities(rows, columns)
    payload = {
        "schema": "rq2_joint_deliverability_transport_probe_v5",
        "row_probabilities": rows.tolist(),
        "column_probabilities": columns.tolist(),
        "metric_row_major": metric.ravel().tolist(),
        "equality_matrix_row_major": equality_matrix.ravel().tolist(),
        "equality_rhs": equality_rhs.tolist(),
        "lower": _transport_probe_endpoint(
            metric.ravel(),
            equality_matrix,
            equality_rhs,
            list(probe["analytic_lower_coupling_row_major"]),
            list(probe["analytic_lower_dual_equality_variables"]),
            extremum="lower",
        ),
        "upper": _transport_probe_endpoint(
            -metric.ravel(),
            equality_matrix,
            equality_rhs,
            list(probe["analytic_upper_coupling_row_major"]),
            list(probe["analytic_upper_dual_equality_variables"]),
            extremum="upper",
        ),
    }
    expected_lower = float(probe["expected_lower"])
    expected_upper = float(probe["expected_upper"])
    if not math.isclose(
        float(_mapping(payload["lower"], "lower endpoint")["endpoint_value"]),
        expected_lower,
        rel_tol=0.0,
        abs_tol=1.0e-12,
    ):
        raise ValueError("transport probe lower endpoint drifted")
    if not math.isclose(
        float(_mapping(payload["upper"], "upper endpoint")["endpoint_value"]),
        expected_upper,
        rel_tol=0.0,
        abs_tol=1.0e-12,
    ):
        raise ValueError("transport probe upper endpoint drifted")
    return _mapping(_hexify_floats(payload), "hex transport probe")


def transport_probe_sha256(design: dict[str, Any]) -> str:
    return _canonical_sha256(transport_probe_payload(design))


def bootstrap_probe_sha256(design: dict[str, Any]) -> str:
    """Execute the frozen small RNG probe without reading project data."""

    contract = _mapping(design["bootstrap_contract"], "bootstrap contract")
    software = _mapping(contract["software"], "bootstrap software")
    _equal(np.__version__, software["numpy"], "NumPy runtime version")
    generator = _mapping(contract["pseudorandom_generator"], "pseudorandom generator")
    _equal(generator["api"], "numpy.random.Generator", "RNG API")
    _equal(generator["bit_generator"], "numpy.random.PCG64DXSM", "bit generator")
    probe = _mapping(contract["deterministic_probe"], "deterministic probe")

    power_ids = np.asarray(probe["power_IDs"])
    power_raw = [float(value) for value in probe["power_probabilities"]]
    power_probability = np.asarray(
        [value / math.fsum(power_raw) for value in power_raw],
        dtype=np.float64,
    )
    workload_ids = np.asarray(probe["workload_IDs"])
    workload_raw = [float(value) for value in probe["workload_probabilities"]]
    workload_probability = np.asarray(
        [value / math.fsum(workload_raw) for value in workload_raw],
        dtype=np.float64,
    )
    rng = np.random.Generator(np.random.PCG64DXSM(int(generator["seed"])))
    payload = []
    for replicate in range(int(probe["replicates"])):
        payload.append(
            {
                "replicate": replicate,
                "power": rng.choice(
                    power_ids,
                    size=int(probe["power_draw_count"]),
                    replace=True,
                    p=power_probability,
                ).tolist(),
                "workload": rng.choice(
                    workload_ids,
                    size=int(probe["workload_draw_count"]),
                    replace=True,
                    p=workload_probability,
                ).tolist(),
            }
        )
    return _canonical_sha256(payload)


def _validate_scientific_invariants(design: dict[str, Any]) -> None:
    _validate_authority(design)
    scope = _mapping(design["scope"], "scope")
    _equal(scope["registered_arm_count"], 4, "registered arm count")
    _equal(scope["registered_cell_count"], 46, "registered cell count")
    for field in ("runs_solver", "publishes_result", "formal_result", "claim"):
        _equal(scope[field], False, f"scope {field}")

    input_schema = _mapping(design["input_schema_contract"], "input schema")
    _equal(
        input_schema["power_hourly_file"],
        "dispatched_power_system_blocks.csv.gz",
        "power hourly file",
    )
    _equal(
        input_schema["power_marginal_columns_exact"],
        ["id", "probability"],
        "power marginal columns",
    )
    _equal(
        _mapping(input_schema["power_field_mapping"], "power field mapping")[
            "cfe_call_fraction_at_alpha_1"
        ],
        {
            "source_column": "cfe_call_fraction",
            "parse": "finite_float64_closed_0_1",
        },
        "CFE source field",
    )
    _equal(
        _mapping(input_schema["power_field_mapping"], "power field mapping")[
            "grid_need"
        ],
        {
            "source_column": "grid_need_fraction",
            "parse_for_finite_block": "finite_float64_closed_0_1",
            "parse_for_E0_hour": "exact_empty_string",
        },
        "grid-need source field",
    )
    _equal(
        input_schema["workload_hourly_file"],
        "workload_blocks.csv.gz",
        "workload hourly file",
    )
    _equal(
        _mapping(input_schema["workload_field_mapping"], "workload field mapping")[
            "raw_workload_fraction"
        ],
        {
            "source_column": "workload_fraction",
            "parse": "finite_float64_nonnegative",
        },
        "workload source field",
    )
    _equal(
        lift_power_block_state(["finite_grid_need"] * 24),
        "finite_grid_need",
        "finite block lifting",
    )
    _equal(
        lift_power_block_state(
            ["finite_grid_need"] * 23 + ["exogenous_grid_infeasibility"]
        ),
        "exogenous_grid_infeasibility",
        "E0 block lifting",
    )

    cfe = _mapping(design["cfe_contract"], "CFE contract")
    _equal(cfe["registered_levels"], [0.50, 0.70, 0.85, 1.00], "CFE levels")
    _equal(
        cfe["effective_call_expression"],
        "0 if raw_call <= service_shortfall_tolerance, else raw_call",
        "effective CFE request",
    )
    _equal(cfe["raw_call_truncated_to_available_flexibility"], False, "CFE call")
    _equal(cfe["interpolation_between_registered_levels"], False, "interpolation")

    arms = _mapping(design["arm_contract"], "arm contract")
    _equal(tuple(arms["canonical_order"]), ARM_ORDER, "arm order")
    definitions = _mapping(arms["definitions"], "arm definitions")
    _equal(set(definitions), set(ARM_ORDER), "arm definition inventory")
    network = _mapping(definitions["network_only_shared"], "network-only")
    _equal(network["cfe_call"], "zero", "network-only CFE call")
    _equal(
        network["planning_recovery_by_track"],
        {"shared": "business_recovery_headroom"},
        "network-only planning recovery",
    )
    _equal(
        network["canonical_capacity_key_excludes"],
        ["hourly_cfe_target"],
        "network-only alpha invariant key",
    )
    b6 = _mapping(definitions["joint_b6_separate_planning_shared_execution"], "B6")
    _equal(b6["planning_tracks"], ["grid", "cfe"], "B6 planning tracks")
    _equal(
        b6["planning_recovery_by_track"],
        {
            "grid": "business_recovery_headroom",
            "cfe": "cfe_service_recovery_headroom",
        },
        "B6 planning recovery",
    )
    _equal(b6["execution_tracks"], ["shared"], "B6 execution tracks")

    formulation = _mapping(design["planning_formulation"], "planning formulation")
    _equal(
        formulation["objective"],
        "minimize_D",
        "planning objective",
    )
    _equal(
        _mapping(
            formulation["effective_service_requests"],
            "effective service requests",
        ),
        {
            "grid": (
                "0 if grid_request <= service_shortfall_tolerance, else grid_request"
            ),
            "cfe": (
                "0 if raw_cfe_request <= service_shortfall_tolerance, else "
                "raw_cfe_request"
            ),
            "raw_requests_retained_for_audit": True,
        },
        "effective service requests",
    )
    _equal(
        _mapping(formulation["service_constraints"], "service constraints")[
            "cfe_active"
        ],
        "x_cfe_equal_to_effective_cfe_request",
        "planning effective CFE service",
    )
    _equal(
        _mapping(formulation["track_call_mapping"], "track call mapping"),
        {
            "shared": "q_equals_x_grid_plus_x_cfe",
            "grid": "q_equals_x_grid",
            "cfe": "q_equals_x_cfe",
        },
        "planning track-call mapping",
    )
    _equal(
        _mapping(formulation["physical_caps"], "physical caps")[
            "every_arm_connected_demand"
        ],
        "x_grid_plus_x_cfe_less_than_or_equal_to_connected_demand",
        "planning connected-demand cap",
    )
    _equal(
        _mapping(formulation["terminal_constraints"], "terminal constraints"),
        {
            "terminal_on": "on_at_hour_23_equals_zero",
            "terminal_debt": "debt_at_hour_23_less_than_or_equal_to_zero",
        },
        "planning terminal constraints",
    )
    _equal(
        _mapping(
            formulation["B6_simultaneous_track_semantics"],
            "B6 simultaneous-track semantics",
        )["one_track_may_recover_while_other_track_calls"],
        True,
        "B6 simultaneous recovery/call semantics",
    )

    cells = expand_registered_cells(design)
    ids = [str(cell["cell_id"]) for cell in cells]
    tuples = [
        tuple(sorted(_mapping(cell["values"], "cell values").items())) for cell in cells
    ]
    _equal(len(cells), 46, "expanded cell count")
    _equal(len(set(ids)), 46, "unique cell ID count")
    _equal(len(set(tuples)), 46, "unique parameter tuple count")
    _equal(
        sum(cell["family"] == "primary_factorial" for cell in cells),
        36,
        "primary cell count",
    )
    _equal(
        sum(cell["family"] == "secondary_oat" for cell in cells),
        10,
        "OAT cell count",
    )

    precheck = _mapping(
        design["zero_recovery_structural_precheck"], "zero-recovery precheck"
    )
    _equal(
        precheck["scope"],
        "every_arm_track_cell_over_full_evaluable_training_cartesian_support",
        "global precheck scope",
    )
    _equal(
        _mapping(precheck["track_required_call"], "precheck tracks"),
        {
            "network_only_shared": {"shared": "effective_grid_call"},
            "cfe_only_shared": {"shared": "effective_cfe_call"},
            "joint_correct_shared": {
                "shared": "effective_grid_call_plus_effective_cfe_call"
            },
            "joint_b6_separate_planning_shared_execution": {
                "grid": "effective_grid_call",
                "cfe": "effective_cfe_call",
            },
        },
        "precheck effective track calls",
    )
    for field in (
        "solver_call_when_triggered",
        "numeric_capacity_imputation",
        "holdout_execution_when_triggered",
        "capacity_contrast_when_any_required_arm_undefined",
    ):
        _equal(precheck[field], False, f"precheck {field}")
    _equal(
        precheck["alpha_1_role"],
        "sufficient_input_route_not_exclusive_scope",
        "alpha=1 precheck role",
    )
    if "effective_required_call_t = 0" not in str(
        precheck["eligible_recovery_power_expression"]
    ):
        raise ValueError("structural precheck inactive-hour rule drifted")

    capacity = _mapping(design["capacity_estimands"], "capacity estimands")
    _equal(
        capacity["contrasts"],
        {
            "I_joint": {
                "point": "D_J - max(D_N, D_C)",
                "interval": "[L_J-max(U_N,U_C), U_J-max(L_N,L_C)]",
            },
            "I_sep": {
                "point": "D_B - max(D_N, D_C)",
                "interval": "[L_B-max(U_N,U_C), U_B-max(L_N,L_C)]",
            },
            "A_B6": {
                "point": "D_J - D_B",
                "interval": "[L_J-U_B, U_J-L_B]",
            },
        },
        "capacity contrasts",
    )
    _equal(capacity["point_sign_used_for_label_or_claim"], False, "point sign gate")
    frontier = _mapping(design["frontier_outputs"], "frontier outputs")
    if "certified I_joint interval" not in str(
        frontier["first_registered_robust_positive_joint_interaction"]
    ):
        raise ValueError("frontier positive crossing is not interval-supported")
    attribution = _mapping(design["attribution_contract"], "attribution")
    _equal(
        attribution["type"],
        "nonexclusive_interval_supported_bottleneck_vector",
        "attribution type",
    )
    labels = _mapping(attribution["labels"], "attribution labels")
    if not ALL_CAPACITY_LABELS.issubset(labels):
        raise ValueError("interval-supported attribution label inventory drifted")
    for name in ALL_CAPACITY_LABELS:
        if "certified_" not in str(_mapping(labels[name], name)["condition"]):
            raise ValueError(f"capacity label is not interval-supported: {name}")
    _equal(
        _mapping(labels["b6_operational_penalty"], "operational penalty"),
        {
            "condition": (
                "there exists at least one registered B6-minus-correct service "
                "metric whose certified scalar transport lower bound is greater "
                "than 1e-6."
            ),
            "requires_holdout_and_transport_resolved": True,
        },
        "operational penalty",
    )
    _equal(
        _mapping(labels["b6_operational_relief"], "operational relief"),
        {
            "condition": (
                "there exists at least one registered B6-minus-correct service "
                "metric whose certified scalar transport upper bound is less "
                "than -1e-6."
            ),
            "requires_holdout_and_transport_resolved": True,
        },
        "operational relief",
    )
    _equal(
        attribution["evaluation_order"],
        [
            "status_based_single_service_labels",
            "signed_capacity_labels_if_all_four_arms_resolved",
            "operational_labels_if_holdout_and_transport_resolved",
        ],
        "attribution evaluation order",
    )
    _equal(
        attribution["status_based_single_service_labels_require_all_four_resolved"],
        False,
        "status-based attribution precondition",
    )
    _equal(
        attribution["signed_capacity_labels_require_all_four_resolved"],
        True,
        "signed attribution precondition",
    )
    truth_table = _mapping(attribution["truth_table"], "attribution truth table")
    _equal(
        _mapping(
            truth_table["D_N_structural_or_cap_infeasible"],
            "network structural truth-table row",
        ),
        {
            "network_single_service_binding": True,
            "signed_capacity_labels": "not_evaluable",
            "operational_labels": "not_evaluable",
        },
        "network structural truth-table row",
    )
    _equal(
        _mapping(
            truth_table["all_four_resolved_holdout_not_resolved"],
            "resolved-without-holdout truth-table row",
        )["status_based_single_service_labels"],
        "not_evaluable",
        "resolved-without-holdout single-service labels",
    )

    holdout = _mapping(design["holdout_policy"], "holdout policy")
    _equal(holdout["future_calls_or_states_used"], False, "holdout information")
    _equal(
        holdout["request_preprocessing"],
        {
            "grid": (
                "0 if current_grid_request <= service_shortfall_tolerance, "
                "else current_grid_request"
            ),
            "cfe": (
                "0 if current_cfe_request <= service_shortfall_tolerance, "
                "else current_cfe_request"
            ),
            "raw_requests_retained_for_audit": True,
        },
        "holdout request preprocessing",
    )
    required_current_constraints = {
        "committed_capacity",
        "available_flexibility",
        "connected_demand",
        "response_and_ramp",
        "minimum_event_power",
        "maximum_event_duration",
        "maximum_event_count",
        "minimum_recovery_hours",
        "cumulative_energy_budget",
        "maximum_recovery_debt",
        "current_recovery_headroom",
        "terminal_inactivity_when_hour_offset_is_23",
    }
    _equal(
        set(holdout["current_shared_feasible_action_set_includes"]),
        required_current_constraints,
        "holdout current feasible set",
    )
    _equal(
        holdout["activity_rule"],
        {
            "tolerance": 1.0e-6,
            "active": "total_call_greater_than_or_equal_to_minimum_event_power",
            "inactive": "total_call_equal_to_zero",
            "active_minimum_power": (
                "total_call_greater_than_or_equal_to_minimum_event_power"
            ),
        },
        "holdout activity rule",
    )
    _equal(
        holdout["state_transition_order"],
        [
            "determine_served_grid_and_cfe",
            "derive_active_start_and_stop",
            "compute_debt_before_recovery",
            "choose_recovery_if_inactive",
            "compute_debt_after_recovery",
            "update_duration_event_count_rest_energy_and_prior_event",
        ],
        "holdout state-transition order",
    )
    metrics = _mapping(holdout["metric_definitions"], "holdout metrics")
    if "recovery_completion_failure" not in metrics["joint_service_failure"]:
        raise ValueError("joint service failure omits recovery completion")
    _equal(
        holdout_probe_sha256(design),
        _mapping(holdout["deterministic_probe"], "holdout deterministic probe")[
            "canonical_trajectory_payload_sha256"
        ],
        "holdout deterministic probe",
    )

    identification = _mapping(
        design["holdout_identification"], "holdout identification"
    )
    e0 = _mapping(identification["E0"], "E0")
    _equal(e0["excluded_from_finite_service_numerator"], True, "E0 numerator")
    _equal(e0["excluded_from_finite_service_denominator"], True, "E0 denominator")
    _equal(
        _mapping(identification["empty_finite_support"], "empty finite support"),
        {
            "condition": "E0_mass_greater_than_or_equal_to_1_minus_1e-9",
            "status": "finite_service_identification_unresolved",
            "transport_solver_called": False,
            "pairwise_service_metrics_defined": False,
            "E0_mass_still_reported_unconditionally": True,
        },
        "empty finite support",
    )
    _equal(
        finite_conditioning_denominator(1.0),
        None,
        "all-E0 finite denominator",
    )
    transport = _mapping(identification["transport"], "transport")
    if "all nonnegative finite matrices pi" not in transport["ambiguity_set"]:
        raise ValueError("transport ambiguity set drifted")
    quantifiers = _mapping(
        transport["operational_label_quantifiers"],
        "operational label quantifiers",
    )
    _equal(
        quantifiers,
        {
            "quantifier_order": ("exists_registered_metric_then_for_all_admissible_pi"),
            "existential_common_pi_witness_used": False,
            "registered_statements": {
                "b6_operational_penalty": {
                    "logic": ("any_metric_certified_over_complete_transport_polytope"),
                    "endpoint_test": ("certified_lower_bound_greater_than_1e-6"),
                    "metrics": list(OPERATIONAL_METRICS),
                },
                "b6_operational_relief": {
                    "logic": ("any_metric_certified_over_complete_transport_polytope"),
                    "endpoint_test": ("certified_upper_bound_less_than_negative_1e-6"),
                    "metrics": list(OPERATIONAL_METRICS),
                },
            },
        },
        "operational label quantifiers",
    )
    crossing_zero = {metric: (-0.2, 0.3) for metric in OPERATIONAL_METRICS}
    _equal(
        operational_labels_from_transport_intervals(crossing_zero),
        {
            "b6_operational_penalty": False,
            "b6_operational_relief": False,
        },
        "existential coupling is insufficient for robust operational labels",
    )
    mixed_robust = {
        OPERATIONAL_METRICS[0]: (0.1, 0.2),
        OPERATIONAL_METRICS[1]: (-0.3, -0.2),
        OPERATIONAL_METRICS[2]: (-0.1, 0.1),
    }
    _equal(
        operational_labels_from_transport_intervals(mixed_robust),
        {
            "b6_operational_penalty": True,
            "b6_operational_relief": True,
        },
        "nonexclusive robust operational labels",
    )
    transport_probe = _mapping(
        transport["deterministic_probe"], "transport deterministic probe"
    )
    _equal(
        transport_probe["canonical_certificate_payload_sha256"],
        TRANSPORT_PROBE_SHA256,
        "registered transport probe digest",
    )
    _equal(
        transport_probe_sha256(design),
        TRANSPORT_PROBE_SHA256,
        "transport deterministic probe",
    )

    bootstrap = _mapping(design["bootstrap_contract"], "bootstrap")
    _equal(
        _mapping(bootstrap["software"], "bootstrap software")["numpy"],
        "1.26.4",
        "bootstrap NumPy",
    )
    _equal(
        _mapping(bootstrap["pseudorandom_generator"], "bootstrap RNG")["bit_generator"],
        "numpy.random.PCG64DXSM",
        "bootstrap bit generator",
    )
    _equal(bootstrap["replicate_count"], 200, "bootstrap replicate count")
    _equal(
        bootstrap["percentile"],
        {
            "api": "numpy.quantile",
            "q": [0.025, 0.975],
            "axis": 0,
            "method": "linear",
            "input_dtype": "float64",
        },
        "bootstrap percentile",
    )
    if "every bootstrap endpoint" not in bootstrap["empty_finite_support_rule"]:
        raise ValueError("bootstrap unresolved propagation drifted")
    _equal(
        bootstrap_probe_sha256(design),
        BOOTSTRAP_PROBE_SHA256,
        "bootstrap deterministic probe",
    )

    synthetic = contrast_intervals(
        {
            "D_N": (0.1, 0.2),
            "D_C": (0.3, 0.4),
            "D_J": (0.5, 0.6),
            "D_B": (0.45, 0.55),
        }
    )
    expected_intervals = {
        "D_single": (0.3, 0.4),
        "I_joint": (0.1, 0.3),
        "I_sep": (0.05, 0.25),
        "A_B6": (-0.05, 0.15),
    }
    for name, expected in expected_intervals.items():
        if not all(
            math.isclose(left, right, abs_tol=1.0e-12)
            for left, right in zip(synthetic[name], expected, strict=True)
        ):
            raise ValueError(f"{name} interval propagation drifted")


def validate_design(
    design: dict[str, Any],
    *,
    require_sealed: bool,
) -> dict[str, Any]:
    _exact_keys(design, EXPECTED_TOP_LEVEL, "top-level design")
    _equal(
        design["schema"],
        "rq2_joint_deliverability_preregistration_successor_v5",
        "schema",
    )
    _equal(design["version"], 5, "version")
    _equal(design["created_on"], "2026-09-05", "created_on")
    lifecycle = _mapping(design["lifecycle"], "lifecycle")
    _exact_keys(lifecycle, EXPECTED_LIFECYCLE_KEYS, "lifecycle")
    for field in EXPECTED_FALSE_EXECUTION_GATES:
        _equal(lifecycle[field], False, f"lifecycle {field}")
    if require_sealed:
        _equal(
            lifecycle["status"],
            "SEALED_READY_FOR_INDEPENDENT_REVIEW",
            "sealed status",
        )
        _equal(lifecycle["sealed_on"], "2026-09-05", "sealed_on")
        _equal(lifecycle["pre_seal_audit_complete"], True, "pre-seal gate")
        _equal(
            lifecycle["sealed_ready_for_independent_review"],
            True,
            "sealed review gate",
        )
    else:
        _equal(lifecycle["status"], "DRAFT_NONAUTHORITATIVE", "draft status")
        _equal(lifecycle["sealed_on"], None, "draft sealed_on")
        _equal(lifecycle["pre_seal_audit_complete"], False, "draft pre-seal gate")
        _equal(
            lifecycle["sealed_ready_for_independent_review"],
            False,
            "draft review gate",
        )
    observed_semantic_sha256 = _canonical_sha256(_semantic_payload(design))
    _equal(
        observed_semantic_sha256,
        EXPECTED_SEMANTIC_SHA256,
        "complete semantic payload digest",
    )
    _validate_scientific_invariants(design)
    return {
        "design_valid": True,
        "complete_self_contained_authority": True,
        "semantic_payload_sha256": observed_semantic_sha256,
        "registered_cell_count": 46,
        "arm_count": 4,
        "holdout_probe_sha256": holdout_probe_sha256(design),
        "transport_probe_sha256": transport_probe_sha256(design),
        "bootstrap_probe_sha256": bootstrap_probe_sha256(design),
        "solver_calls": 0,
        "result_files_written": 0,
    }


def _document_semantic_sha256(
    text: str,
    *,
    expected_status: str,
    label: str,
) -> str:
    marker_prefix = "> 状态：`"
    marker = f"{marker_prefix}{expected_status}`"
    if text.count(marker_prefix) != 1 or marker not in text:
        raise ValueError(f"{label} lifecycle status drifted")
    normalized = text.replace(
        marker,
        f"{marker_prefix}<LIFECYCLE_STATUS>`",
        1,
    )
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _validate_document_texts(
    spec: str,
    plan: str,
    *,
    require_sealed: bool,
) -> dict[str, str]:
    expected_status = (
        "SEALED_READY_FOR_INDEPENDENT_REVIEW"
        if require_sealed
        else "DRAFT_NONAUTHORITATIVE"
    )
    required_terms = (
        "完整、自包含",
        "structural_recovery_infeasible_estimand_undefined",
        "numerically_indeterminate",
        "PCG64DXSM",
        "unsigned UTF-8",
    )
    combined = spec + "\n" + plan
    for term in required_terms:
        if term not in combined:
            raise ValueError(f"successor documents omit required term: {term}")
    spec_digest = _document_semantic_sha256(
        spec,
        expected_status=expected_status,
        label="specification",
    )
    plan_digest = _document_semantic_sha256(
        plan,
        expected_status=expected_status,
        label="plan",
    )
    _equal(
        spec_digest,
        EXPECTED_SPEC_SEMANTIC_SHA256,
        "specification semantic digest",
    )
    _equal(
        plan_digest,
        EXPECTED_PLAN_SEMANTIC_SHA256,
        "plan semantic digest",
    )
    return {
        "spec_semantic_sha256": spec_digest,
        "plan_semantic_sha256": plan_digest,
    }


def _validate_documents(*, require_sealed: bool) -> dict[str, str]:
    _require_regular_file(SPEC, "specification")
    _require_regular_file(PLAN, "plan")
    return _validate_document_texts(
        SPEC.read_text(encoding="utf-8"),
        PLAN.read_text(encoding="utf-8"),
        require_sealed=require_sealed,
    )


def _validate_manifest_shapes(
    inner: dict[str, Any],
    outer: dict[str, Any],
    *,
    inner_sha256: str,
) -> dict[str, str]:
    _exact_keys(inner, {"schema", "files"}, "inner manifest")
    _equal(
        inner["schema"],
        "rq2_joint_deliverability_preregistration_successor_manifest_v5",
        "inner schema",
    )
    files = _mapping(inner["files"], "inner files")
    _equal(set(files), EXPECTED_INNER_MEMBERS, "inner member inventory")
    for relative, digest in files.items():
        if type(relative) is not str:
            raise TypeError("inner manifest path must be a string")
        _sha256_digest(digest, f"inner member digest {relative}")
    _exact_keys(outer, {"schema", "version", "inner"}, "outer manifest")
    _equal(
        outer["schema"],
        "rq2_joint_deliverability_preregistration_successor_outer_v5",
        "outer schema",
    )
    _equal(outer["version"], 5, "outer version")
    outer_inner = _mapping(outer["inner"], "outer inner")
    _exact_keys(outer_inner, {"path", "sha256"}, "outer inner")
    _equal(outer_inner["path"], INNER_RELATIVE, "outer inner path")
    _equal(
        outer_inner["sha256"],
        _sha256_digest(inner_sha256, "observed inner manifest digest"),
        "outer inner hash",
    )
    return files


def _validate_manifests() -> dict[str, Any]:
    _require_regular_file(INNER, "inner manifest")
    _require_regular_file(OUTER, "outer manifest")
    inner = _load_json(INNER)
    outer = _load_json(OUTER)
    files = _validate_manifest_shapes(
        inner,
        outer,
        inner_sha256=_sha256(INNER),
    )
    for relative, expected in files.items():
        path = ROOT / relative
        _require_regular_file(path, f"sealed member {relative}")
        _equal(_sha256(path), expected, f"sealed member hash {relative}")
    return {
        "inner_manifest_sha256": _sha256(INNER),
        "outer_manifest_sha256": _sha256(OUTER),
        "sealed_file_count": len(files),
    }


def validate() -> dict[str, Any]:
    design = _load_yaml(CONFIG)
    require_sealed = (
        _mapping(design["lifecycle"], "lifecycle")["status"]
        == "SEALED_READY_FOR_INDEPENDENT_REVIEW"
    )
    report = validate_design(design, require_sealed=require_sealed)
    report.update(_validate_documents(require_sealed=require_sealed))
    if require_sealed:
        report.update(_validate_manifests())
    else:
        if _path_appears(INNER) or _path_appears(OUTER):
            raise ValueError("draft candidate must not have production manifests")
        report.update(
            {
                "inner_manifest_sha256": None,
                "outer_manifest_sha256": None,
                "sealed_file_count": 0,
            }
        )
    lifecycle = _mapping(design["lifecycle"], "lifecycle")
    report.update(
        {
            "validation_passed": True,
            "status": lifecycle["status"],
            "pre_seal_audit_complete": lifecycle["pre_seal_audit_complete"],
            "independent_R4_review_passed": False,
            "implementation_bound": False,
            "formal_execution_ready": False,
            "formal_result": False,
        }
    )
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.parse_args()
    print(json.dumps(validate(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
