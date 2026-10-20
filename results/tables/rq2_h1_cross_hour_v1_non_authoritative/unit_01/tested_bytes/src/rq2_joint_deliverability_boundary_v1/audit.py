"""Zero-solver necessary-condition audit for the RQ2 boundary draft."""

from __future__ import annotations

import csv
import gzip
import hashlib
import json
from collections import defaultdict
from copy import deepcopy
from dataclasses import asdict, dataclass
from functools import lru_cache
from itertools import product
from math import ceil, floor, fsum, isfinite
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
ARM_IDS = (
    "network_only_shared",
    "cfe_only_shared",
    "joint_correct_shared",
    "joint_b6_separate_planning_shared_execution",
)
NECESSARY_CONDITION_CLASSES = (
    "terminal_inactivity",
    "available_flexibility",
    "energy_budget",
    "maximum_event_duration",
    "maximum_event_count_lower_bound",
    "total_recovery_energy_lower_bound",
    "causal_debt_limit",
    "causal_terminal_debt",
)


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _construct_mapping(
    loader: _UniqueKeyLoader,
    node: yaml.nodes.MappingNode,
    deep: bool = False,
) -> dict[object, object]:
    mapping: dict[object, object] = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in mapping:
            raise ValueError(f"duplicate YAML key: {key}")
        mapping[key] = loader.construct_object(value_node, deep=deep)
    return mapping


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,
    _construct_mapping,
)


@dataclass(frozen=True)
class _Cell:
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
class _PowerBlock:
    block_id: str
    cfe_call_fraction_at_alpha_1: tuple[float, ...]


@dataclass(frozen=True)
class _WorkloadBlock:
    block_id: str
    occupancy: tuple[float, ...]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _path(raw: object, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"{label} must be a nonempty path")
    path = Path(raw)
    return path if path.is_absolute() else ROOT / path


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict) or not all(isinstance(key, str) for key in value):
        raise ValueError(f"{label} must be a string-keyed mapping")
    return value


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.load(path.read_text(encoding="utf-8"), Loader=_UniqueKeyLoader)
    return _mapping(payload, str(path))


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    return _mapping(payload, str(path))


def _check_hash(path: Path, expected: object, label: str) -> None:
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError(f"{label} expected SHA-256 is invalid")
    if _sha256(path) != expected:
        raise ValueError(f"{label} SHA-256 drifted")


def _verify_package(binding: dict[str, Any], label: str) -> None:
    manifest_path = _path(binding["manifest_path"], f"{label}.manifest_path")
    _check_hash(manifest_path, binding["manifest_sha256"], f"{label} manifest")
    manifest = _load_json(manifest_path)
    package = _path(binding["package"], f"{label}.package")
    for name, digest in manifest.items():
        if not isinstance(name, str) or Path(name).name != name:
            raise ValueError(f"{label} manifest member path is invalid")
        member = package / name
        if not member.is_file():
            raise ValueError(f"{label} manifest member is absent: {name}")
        _check_hash(member, digest, f"{label} manifest member {name}")
    for role in ("hourly", "summary"):
        path = _path(binding[f"{role}_path"], f"{label}.{role}_path")
        _check_hash(path, binding[f"{role}_sha256"], f"{label} {role}")
        if manifest.get(path.name) != binding[f"{role}_sha256"]:
            raise ValueError(f"{label} {role} is not bound by its package manifest")


def _load_config(config_path: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    config_path = config_path.resolve()
    config = _load_yaml(config_path)
    if config.get("schema") != "rq2_joint_deliverability_boundary_successor_v1_draft":
        raise ValueError("boundary diagnostic config schema drifted")
    lifecycle = _mapping(config.get("lifecycle"), "lifecycle")
    if lifecycle != {
        "status": "DRAFT_NONAUTHORITATIVE",
        "pre_seal_audit_complete": False,
        "sealed_ready_for_independent_review": False,
        "independent_review_passed": False,
        "formal_execution_ready": False,
        "formal_result": False,
        "paper_claim": False,
        "security_certified": False,
    }:
        raise ValueError("boundary diagnostic lifecycle gates drifted")
    authority = _mapping(config.get("authority"), "authority")
    if (
        authority.get("replaces_or_modifies_v5") is not False
        or authority.get("may_open_any_execution_gate") is not False
        or authority.get("sealed_implementation_v2_may_be_modified") is not False
        or authority.get("sealed_execution_v3_may_be_modified") is not False
    ):
        raise ValueError("draft authority boundary drifted")
    sealed = _mapping(authority.get("sealed_v5"), "authority.sealed_v5")
    v5_path = _path(sealed["config_path"], "sealed_v5.config_path")
    _check_hash(v5_path, sealed["config_sha256"], "sealed V5 config")
    v5 = _load_yaml(v5_path)
    _check_hash(
        _path(sealed["outer_path"], "sealed_v5.outer_path"),
        sealed["outer_sha256"],
        "sealed V5 outer",
    )
    inputs = _mapping(config.get("input_bindings"), "input_bindings")
    for label in ("power", "workload"):
        _verify_package(_mapping(inputs.get(label), f"input_bindings.{label}"), label)
    audit = _mapping(config.get("audit_contract"), "audit_contract")
    if audit.get("solver_calls_allowed") is not False:
        raise ValueError("zero-solver audit gate is open")
    if tuple(audit.get("registered_arm_ids", ())) != ARM_IDS:
        raise ValueError("registered arm inventory drifted")
    if tuple(audit.get("necessary_condition_classes", ())) != NECESSARY_CONDITION_CLASSES:
        raise ValueError("necessary-condition inventory drifted")
    v5_temporal = _mapping(v5.get("temporal_envelope"), "V5 temporal_envelope")
    v5_precheck = _mapping(
        v5.get("zero_recovery_structural_precheck"),
        "V5 zero_recovery_structural_precheck",
    )
    if float(audit.get("service_shortfall_tolerance")) != float(
        v5_temporal.get("service_shortfall_tolerance")
    ):
        raise ValueError("diagnostic service tolerance differs from sealed V5")
    if float(audit.get("arithmetic_tolerance")) != float(v5_precheck.get("tolerance")):
        raise ValueError("diagnostic arithmetic tolerance differs from sealed V5")
    if audit.get("model_scope") != "legacy_sealed_v5_single_24h_completed_period":
        raise ValueError("diagnostic model scope drifted")
    if (
        audit.get("terminal_conditions_apply_to_selected_continuous_draft") is not False
        or audit.get("full_physical_training_support_audited") is not False
        or audit.get("absence_of_necessary_condition_means_feasible") is not False
        or audit.get("result_contingent_parameter_change_allowed") is not False
    ):
        raise ValueError("diagnostic evidence boundary drifted")
    boundary = _mapping(config.get("boundary_contract"), "boundary_contract")
    if (
        boundary.get("selected_primary_mode")
        != "continuous_multi_day_state_carry"
        or boundary.get("hour_23_service_retained") is not True
        or boundary.get("force_inactive_at_observation_end") is not False
        or boundary.get("force_zero_debt_at_observation_end") is not False
        or boundary.get("cross_split_continuation_allowed") is not False
        or boundary.get("silent_zero_tail_obligations_allowed") is not False
        or boundary.get("debt_reset_at_boundary_allowed") is not False
        or boundary.get("accounting_period_change_or_reset_supported") is not False
    ):
        raise ValueError("continuous boundary contract drifted")
    output = _mapping(config.get("output"), "output")
    if output.get("overwrite_allowed") is not False or "non_authoritative" not in str(
        output.get("directory", "")
    ):
        raise ValueError("diagnostic output safety boundary drifted")
    return config, v5


def _finite(raw: object, label: str, *, maximum: float | None = None) -> float:
    if isinstance(raw, bool):
        raise TypeError(f"{label} must be a finite number")
    try:
        value = float(raw)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} must be a finite number") from exc
    if not isfinite(value) or value < 0.0 or (maximum is not None and value > maximum):
        raise ValueError(f"{label} is outside its registered domain")
    return value


def _load_marginal_ids(package: Path, split: str) -> tuple[str, ...]:
    path = package / f"{split}_marginal.csv.gz"
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["id", "probability"]:
            raise ValueError(f"{split} marginal schema drifted")
        ids = []
        for row in reader:
            block_id = row["id"]
            if not block_id or block_id in ids:
                raise ValueError(f"{split} marginal IDs are invalid")
            _finite(row["probability"], f"{split} marginal probability")
            ids.append(block_id)
    return tuple(ids)


def _read_training_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        fieldnames = list(reader.fieldnames or ())
        rows = [row for row in reader if row.get("split") == "training"]
    return fieldnames, rows


def _group_24h(
    rows: list[dict[str, str]],
    *,
    value_field: str,
    maximum: float | None,
) -> dict[str, tuple[float, ...]]:
    grouped: dict[str, dict[int, float]] = defaultdict(dict)
    for row in rows:
        block_id = row.get("block_id", "")
        if not block_id:
            raise ValueError("hourly block ID is empty")
        try:
            hour = int(row["hour_offset"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("hour_offset must be an integer") from exc
        if hour not in range(24) or hour in grouped[block_id]:
            raise ValueError(f"invalid hourly inventory for {block_id}")
        grouped[block_id][hour] = _finite(
            row.get(value_field),
            f"{block_id}.{value_field}[{hour}]",
            maximum=maximum,
        )
    result = {}
    for block_id, values in grouped.items():
        if set(values) != set(range(24)):
            raise ValueError(f"block does not contain hours 0 through 23: {block_id}")
        result[block_id] = tuple(values[hour] for hour in range(24))
    return result


def _load_power(binding: dict[str, Any]) -> tuple[_PowerBlock, ...]:
    package = _path(binding["package"], "power.package")
    ids = _load_marginal_ids(package, "training")
    fields, rows = _read_training_rows(_path(binding["hourly_path"], "power.hourly_path"))
    required = {"block_id", "split", "hour_offset", "cfe_call_fraction"}
    if not required.issubset(fields):
        raise ValueError("raw power hourly schema lacks the CFE audit fields")
    grouped = _group_24h(
        rows,
        value_field="cfe_call_fraction",
        maximum=1.0,
    )
    if set(grouped) != set(ids) or len(ids) != int(binding["training_blocks"]):
        raise ValueError("raw power training inventory drifted")
    return tuple(_PowerBlock(block_id, grouped[block_id]) for block_id in ids)


def _load_workload(binding: dict[str, Any]) -> tuple[_WorkloadBlock, ...]:
    package = _path(binding["package"], "workload.package")
    ids = _load_marginal_ids(package, "training")
    fields, rows = _read_training_rows(
        _path(binding["hourly_path"], "workload.hourly_path")
    )
    required = {"block_id", "split", "hour_offset", "workload_fraction"}
    if not required.issubset(fields):
        raise ValueError("raw workload hourly schema lacks the audit fields")
    grouped = _group_24h(rows, value_field="workload_fraction", maximum=None)
    if set(grouped) != set(ids) or len(ids) != int(binding["training_blocks"]):
        raise ValueError("raw workload training inventory drifted")
    return tuple(
        _WorkloadBlock(block_id, tuple(min(value, 1.0) for value in grouped[block_id]))
        for block_id in ids
    )


def _expand_cells(v5: dict[str, Any]) -> tuple[_Cell, ...]:
    registered = _mapping(v5.get("registered_design"), "V5 registered_design")
    primary = _mapping(registered.get("primary_factorial"), "V5 primary_factorial")
    factors = _mapping(primary.get("factors"), "V5 primary factors")
    temporal = _mapping(v5.get("temporal_envelope"), "V5 temporal_envelope")
    fixed = _mapping(temporal.get("fixed_parameters"), "V5 fixed parameters")
    payloads: list[tuple[str, str, dict[str, object]]] = []
    for alpha, flexible, headroom in product(
        factors["hourly_cfe_target"],
        factors["flexible_fraction"],
        factors["normalized_recovery_headroom"],
    ):
        cell_id = (
            f"primary_a{round(float(alpha) * 100):03d}"
            f"_f{round(float(flexible) * 100):03d}"
            f"_h{round(float(headroom) * 100):03d}"
        )
        payloads.append(
            (
                cell_id,
                "primary_factorial",
                {
                    "hourly_cfe_target": alpha,
                    "flexible_fraction": flexible,
                    "normalized_recovery_headroom": headroom,
                    **fixed,
                },
            )
        )
    secondary = _mapping(registered.get("secondary_oat"), "V5 secondary_oat")
    anchor = _mapping(secondary.get("anchor"), "V5 secondary_oat anchor")
    levels = _mapping(temporal.get("oat_levels"), "V5 OAT levels")
    for dimension in secondary["varied_dimensions"]:
        index = 0
        for level in levels[dimension]:
            if level == anchor[dimension]:
                continue
            values = dict(anchor)
            values[dimension] = level
            payloads.append((f"oat_{dimension}_{index:02d}", "secondary_oat", values))
            index += 1
    cells = tuple(
        _Cell(
            cell_id=cell_id,
            family=family,
            hourly_cfe_target=_finite(values["hourly_cfe_target"], "alpha", maximum=1.0),
            flexible_fraction=_finite(values["flexible_fraction"], "flexible", maximum=1.0),
            normalized_recovery_headroom=_finite(
                values["normalized_recovery_headroom"], "headroom", maximum=1.0
            ),
            recovery_efficiency=_finite(
                values["recovery_efficiency"], "efficiency", maximum=1.0
            ),
            maximum_event_duration_hours=_finite(
                values["maximum_event_duration_hours"], "duration"
            ),
            maximum_event_count=int(values["maximum_event_count"]),
            normalized_energy_budget=_finite(values["normalized_energy_budget"], "energy"),
            normalized_debt_limit=_finite(values["normalized_debt_limit"], "debt"),
        )
        for cell_id, family, values in payloads
    )
    if len(cells) != 46 or len({cell.cell_id for cell in cells}) != 46:
        raise ValueError("V5 registered 46-cell inventory drifted")
    parameter_tuples = {
        tuple(asdict(cell)[name] for name in asdict(cell) if name not in {"cell_id", "family"})
        for cell in cells
    }
    if len(parameter_tuples) != 46:
        raise ValueError("V5 registered cell parameter tuples are not unique")
    return cells


def _effective_cfe(source: float, alpha: float, tolerance: float) -> float:
    renewable = 1.0 - source
    raw = max(alpha - renewable, 0.0) / alpha
    return 0.0 if raw <= tolerance else raw


def terminal_inactivity_conflict(required_call: tuple[float, ...], tolerance: float) -> bool:
    """Return the V5 contradiction q[T]>0, q<=on, and on[T]=0."""

    if not required_call:
        raise ValueError("required call trajectory must be nonempty")
    return required_call[-1] > tolerance


def _maximum_positive_run(values: tuple[float, ...], tolerance: float) -> int:
    maximum = 0
    current = 0
    for value in values:
        current = current + 1 if value > tolerance else 0
        maximum = max(maximum, current)
    return maximum


def minimum_event_count_lower_bound(
    required_call: tuple[float, ...],
    maximum_event_duration_steps: int,
    tolerance: float,
) -> int:
    """Return the grid-agnostic lower bound, allowing zero-hour bridging."""

    if maximum_event_duration_steps <= 0:
        raise ValueError("maximum event duration steps must be positive")
    positive_hours = sum(value > tolerance for value in required_call)
    return ceil(positive_hours / maximum_event_duration_steps)


def cfe_recovery_lower_bounds(
    required_call: tuple[float, ...],
    eligible_recovery_power: tuple[float, ...],
    *,
    recovery_efficiency: float,
    time_step_hours: float = 1.0,
) -> dict[str, object]:
    """Return optimistic total and causal debt lower bounds for a fixed CFE call."""

    if not required_call or len(required_call) != len(eligible_recovery_power):
        raise ValueError("CFE call and eligible recovery inventories must align")
    efficiency = _finite(recovery_efficiency, "recovery_efficiency", maximum=1.0)
    dt = _finite(time_step_hours, "time_step_hours")
    if efficiency <= 0.0 or dt <= 0.0:
        raise ValueError("recovery efficiency and time step must be positive")
    calls = tuple(_finite(value, "required_call") for value in required_call)
    recovery = tuple(
        _finite(value, "eligible_recovery_power") for value in eligible_recovery_power
    )
    total_call_energy = fsum(calls) * dt
    maximum_recovery_energy = fsum(recovery) * dt
    total_terminal_lower = total_call_energy - efficiency * maximum_recovery_energy
    debt = 0.0
    debt_path = []
    for call, available_recovery in zip(calls, recovery, strict=True):
        debt = max(0.0, debt + call * dt - efficiency * available_recovery * dt)
        debt_path.append(debt)
    return {
        "total_call_energy": total_call_energy,
        "maximum_eligible_recovery_energy": maximum_recovery_energy,
        "total_terminal_debt_lower_bound": total_terminal_lower,
        "causal_debt_lower_bound_by_hour": debt_path,
        "causal_peak_debt_lower_bound": max(debt_path),
        "causal_terminal_debt_lower_bound": debt_path[-1],
    }


def _first_witness(
    witnesses: dict[str, dict[str, object] | None],
    key: str,
    payload: dict[str, object],
) -> None:
    if witnesses[key] is None:
        witnesses[key] = payload


def _audit_cell(
    cell: _Cell,
    power: tuple[_PowerBlock, ...],
    workload: tuple[_WorkloadBlock, ...],
    *,
    service_tolerance: float,
    arithmetic_tolerance: float,
) -> dict[str, object]:
    witnesses: dict[str, dict[str, object] | None] = {
        name: None for name in NECESSARY_CONDITION_CLASSES
    }
    counts = {f"{name}_violation_pair_count": 0 for name in NECESSARY_CONDITION_CLASSES}
    dt = 1.0
    max_duration_steps = floor(cell.maximum_event_duration_hours / dt + 1.0e-6)
    cfe_by_power: dict[str, tuple[float, ...]] = {}
    compatible_by_power: dict[str, tuple[float, ...]] = {}
    terminal_power_ids: list[str] = []
    duration_power_ids: set[str] = set()
    event_power_ids: set[str] = set()
    energy_power_ids: set[str] = set()
    maximum_compatible = 0.0
    for block in power:
        cfe = tuple(
            _effective_cfe(value, cell.hourly_cfe_target, service_tolerance)
            for value in block.cfe_call_fraction_at_alpha_1
        )
        compatible = tuple(
            max((1.0 - value) / cell.hourly_cfe_target - 1.0, 0.0)
            for value in block.cfe_call_fraction_at_alpha_1
        )
        cfe_by_power[block.block_id] = cfe
        compatible_by_power[block.block_id] = compatible
        maximum_compatible = max(maximum_compatible, *compatible)
        if terminal_inactivity_conflict(cfe, service_tolerance):
            terminal_power_ids.append(block.block_id)
        if _maximum_positive_run(cfe, service_tolerance) > max_duration_steps:
            duration_power_ids.add(block.block_id)
        event_lower_bound = minimum_event_count_lower_bound(
            cfe,
            max_duration_steps,
            service_tolerance,
        )
        if event_lower_bound > cell.maximum_event_count:
            event_power_ids.add(block.block_id)
        if fsum(cfe) * dt > cell.normalized_energy_budget + arithmetic_tolerance:
            energy_power_ids.add(block.block_id)
    for key, ids in (
        ("terminal_inactivity", set(terminal_power_ids)),
        ("maximum_event_duration", duration_power_ids),
        ("maximum_event_count_lower_bound", event_power_ids),
        ("energy_budget", energy_power_ids),
    ):
        counts[f"{key}_violation_pair_count"] = len(ids) * len(workload)
        if ids:
            _first_witness(
                witnesses,
                key,
                {
                    "power_block_id": min(ids),
                    "scope": "all_raw_workload_pairs_for_this_power_block",
                },
            )
    for power_block in power:
        cfe = cfe_by_power[power_block.block_id]
        compatible = compatible_by_power[power_block.block_id]
        for workload_block in workload:
            available = tuple(
                cell.flexible_fraction * occupancy
                for occupancy in workload_block.occupancy
            )
            if any(
                call > limit + arithmetic_tolerance
                for call, limit in zip(cfe, available, strict=True)
            ):
                key = "available_flexibility"
                counts[f"{key}_violation_pair_count"] += 1
                hour = next(
                    index
                    for index, (call, limit) in enumerate(
                        zip(cfe, available, strict=True)
                    )
                    if call > limit + arithmetic_tolerance
                )
                _first_witness(
                    witnesses,
                    key,
                    {
                        "power_block_id": power_block.block_id,
                        "workload_block_id": workload_block.block_id,
                        "hour_offset": hour,
                        "effective_cfe_request": cfe[hour],
                        "available_flexibility": available[hour],
                    },
                )
            recovery_headroom = tuple(
                min(
                    cell.normalized_recovery_headroom
                    * max(1.0 - occupancy, 0.0),
                    cfe_compatible,
                )
                for occupancy, cfe_compatible in zip(
                    workload_block.occupancy,
                    compatible,
                    strict=True,
                )
            )
            eligible = tuple(
                headroom if call <= service_tolerance else 0.0
                for call, headroom in zip(cfe, recovery_headroom, strict=True)
            )
            recovery_bounds = cfe_recovery_lower_bounds(
                cfe,
                eligible,
                recovery_efficiency=cell.recovery_efficiency,
                time_step_hours=dt,
            )
            total_lower = float(recovery_bounds["total_terminal_debt_lower_bound"])
            if total_lower > arithmetic_tolerance:
                key = "total_recovery_energy_lower_bound"
                counts[f"{key}_violation_pair_count"] += 1
                _first_witness(
                    witnesses,
                    key,
                    {
                        "power_block_id": power_block.block_id,
                        "workload_block_id": workload_block.block_id,
                        "terminal_debt_total_energy_lower_bound": total_lower,
                    },
                )
            peak_debt = float(recovery_bounds["causal_peak_debt_lower_bound"])
            debt = float(recovery_bounds["causal_terminal_debt_lower_bound"])
            if peak_debt > cell.normalized_debt_limit + arithmetic_tolerance:
                key = "causal_debt_limit"
                counts[f"{key}_violation_pair_count"] += 1
                _first_witness(
                    witnesses,
                    key,
                    {
                        "power_block_id": power_block.block_id,
                        "workload_block_id": workload_block.block_id,
                        "causal_peak_debt_lower_bound": peak_debt,
                        "registered_debt_limit": cell.normalized_debt_limit,
                    },
                )
            if debt > arithmetic_tolerance:
                key = "causal_terminal_debt"
                counts[f"{key}_violation_pair_count"] += 1
                _first_witness(
                    witnesses,
                    key,
                    {
                        "power_block_id": power_block.block_id,
                        "workload_block_id": workload_block.block_id,
                        "causal_terminal_debt_lower_bound": debt,
                    },
                )
    projection = {
        **counts,
        "model_scope": "legacy_sealed_v5_single_24h_completed_period",
        "terminal_conditions_apply_to_selected_continuous_draft": False,
        "maximum_cfe_compatible_headroom": maximum_compatible,
        "terminal_positive_cfe_power_block_count": len(terminal_power_ids),
        "raw_candidate_pair_count": len(power) * len(workload),
        "witnesses": witnesses,
        "scope": (
            "CFE-only exact track and an optimistic necessary lower bound for "
            "joint-correct/shared and joint-B6/CFE; grid need and E0 are unknown"
        ),
        "non_trigger_interpretation": "not_proven_infeasible_and_not_proven_feasible",
    }
    arm_assessments = {
        "network_only_shared": {
            "status": "unknown_grid_need_and_E0",
            "formal_arm_status": "not_assigned",
            "necessary_conflict_observed": None,
        },
        "cfe_only_shared": {
            "status": "conditional_on_finite_grid_support",
            "formal_arm_status": "not_assigned",
            "necessary_conflict_observed": any(value > 0 for value in counts.values()),
            "projection_role": "exact_CFE_only_required_call",
        },
        "joint_correct_shared": {
            "status": "conditional_on_finite_grid_support",
            "formal_arm_status": "not_assigned",
            "necessary_conflict_observed": any(value > 0 for value in counts.values()),
            "projection_role": "optimistic_CFE_lower_bound_grid_can_only_tighten",
        },
        "joint_b6_separate_planning_shared_execution": {
            "status": "conditional_on_finite_grid_support",
            "formal_arm_status": "not_assigned",
            "necessary_conflict_observed": any(value > 0 for value in counts.values()),
            "projection_role": "exact_B6_CFE_track_required_call",
        },
    }
    parameters = asdict(cell)
    parameters.pop("cell_id")
    parameters.pop("family")
    return {
        "cell_id": cell.cell_id,
        "family": cell.family,
        "model_scope": "legacy_sealed_v5_single_24h_completed_period",
        "terminal_conditions_apply_to_selected_continuous_draft": False,
        "parameters": parameters,
        "cfe_projection": projection,
        "arm_assessments": arm_assessments,
    }


def _alpha_key(alpha: float) -> str:
    return str(alpha)


@lru_cache(maxsize=8)
def _audit_raw_training_support_cached(
    config_path_text: str,
    config_sha256: str,
) -> dict[str, object]:
    """Recompute raw-support necessary conditions without dispatch or optimization."""

    config_path = Path(config_path_text)
    if _sha256(config_path) != config_sha256:
        raise ValueError("diagnostic config changed before cached audit")
    config, v5 = _load_config(config_path)
    inputs = _mapping(config["input_bindings"], "input_bindings")
    power = _load_power(_mapping(inputs["power"], "input_bindings.power"))
    workload = _load_workload(_mapping(inputs["workload"], "input_bindings.workload"))
    cells = _expand_cells(v5)
    audit = _mapping(config["audit_contract"], "audit_contract")
    service_tolerance = _finite(
        audit["service_shortfall_tolerance"],
        "service_shortfall_tolerance",
    )
    arithmetic_tolerance = _finite(
        audit["arithmetic_tolerance"],
        "arithmetic_tolerance",
    )
    cell_results = [
        _audit_cell(
            cell,
            power,
            workload,
            service_tolerance=service_tolerance,
            arithmetic_tolerance=arithmetic_tolerance,
        )
        for cell in cells
    ]
    alphas = sorted({cell.hourly_cfe_target for cell in cells})
    terminal_counts = {}
    for alpha in alphas:
        terminal_counts[_alpha_key(alpha)] = sum(
            terminal_inactivity_conflict(
                tuple(
                    _effective_cfe(value, alpha, service_tolerance)
                    for value in block.cfe_call_fraction_at_alpha_1
                ),
                service_tolerance,
            )
            for block in power
        )
    summary = {
        "schema": "rq2_joint_deliverability_boundary_diagnostic_v1_non_authoritative",
        "evidence_level": "non_authoritative_zero_solver_diagnostic",
        "model_scope": "legacy_sealed_v5_single_24h_completed_period",
        "terminal_conditions_apply_to_selected_continuous_draft": False,
        "config_sha256": _sha256(config_path),
        "audit_module_sha256": _sha256(Path(__file__)),
        "boundary_module_sha256": _sha256(Path(__file__).with_name("boundary.py")),
        "runner_sha256": _sha256(
            ROOT / "experiments/audit_rq2_joint_deliverability_boundary_v1.py"
        ),
        "sealed_v5_config_sha256": config["authority"]["sealed_v5"]["config_sha256"],
        "sealed_v5_outer_sha256": config["authority"]["sealed_v5"]["outer_sha256"],
        "power_manifest_sha256": inputs["power"]["manifest_sha256"],
        "power_hourly_sha256": inputs["power"]["hourly_sha256"],
        "workload_manifest_sha256": inputs["workload"]["manifest_sha256"],
        "workload_hourly_sha256": inputs["workload"]["hourly_sha256"],
        "training_power_block_count": len(power),
        "training_workload_block_count": len(workload),
        "raw_candidate_pair_count_per_cell": len(power) * len(workload),
        "registered_cell_count": len(cells),
        "registered_arm_count": len(ARM_IDS),
        "registered_arm_ids": list(ARM_IDS),
        "necessary_condition_classes": list(NECESSARY_CONDITION_CLASSES),
        "terminal_positive_cfe_block_count_by_alpha": terminal_counts,
        "grid_need_available": False,
        "E0_classification_available": False,
        "full_physical_training_support_audited": False,
        "absence_of_necessary_condition_means_feasible": False,
        "formal_arm_status_assigned": False,
        "solver_calls": 0,
        "formal_grid_execution_started": False,
        "formal_result": False,
        "paper_claim": False,
        "security_certified": False,
    }
    return {"summary": summary, "cells": cell_results}


def audit_raw_training_support(config_path: Path) -> dict[str, object]:
    """Return an isolated copy of the hash-keyed zero-solver audit."""

    resolved = config_path.resolve()
    return deepcopy(
        _audit_raw_training_support_cached(str(resolved), _sha256(resolved))
    )


__all__ = [
    "ARM_IDS",
    "NECESSARY_CONDITION_CLASSES",
    "audit_raw_training_support",
    "cfe_recovery_lower_bounds",
    "minimum_event_count_lower_bound",
    "terminal_inactivity_conflict",
]
