"""Checkpoint and publication contract for the public RQ2 four-arm baseline.

This module is deliberately an orchestration-neutral package core.  It can
serialize already-computed planning and holdout outcomes and offers thin
wrappers around the three registered public calculation APIs.  It does not
load data, choose cells or pairs, invoke identification, or make claims.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import stat
import uuid
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import asdict, is_dataclass
from math import fsum, isfinite
from pathlib import Path, PurePosixPath
from typing import Any

from src.models.rq2_baseline_robustness import (
    FOUR_ARM_IDS,
    FOUR_ARM_SPECS,
    plan_four_arm_minimum_flexibility_with_spec,
)
from src.scenarios.rq2_baseline_robustness import (
    REGISTERED_SERVICE_RISK_SCHEMA,
    UNBOUND_DEBT_VIOLATION_PREFIXES_V1,
    UNBOUND_TERMINAL_CONDITION_VIOLATIONS_V1,
    audit_four_arm_training_support,
    execute_four_arm_causal_policy,
)

RESUME_IDENTITY_SCHEMA = "rq2_baseline_robustness_resume_identity_v1"
PLANNING_CHECKPOINT_SCHEMA = "rq2_baseline_planning_checkpoint_v1"
FINITE_PAIR_CHECKPOINT_SCHEMA = "rq2_baseline_finite_pair_checkpoint_v1"
E0_CHECKPOINT_SCHEMA = "rq2_baseline_E0_checkpoint_v1"
PACKAGE_MANIFEST_SCHEMA = "rq2_baseline_package_manifest_v1"
PACKAGE_SCHEMAS = (
    "four_arm_training_status",
    "four_arm_minimum_flexibility",
    "four_arm_pairwise_outcomes",
    "E0_outcomes",
    "checkpoint_inventory",
    "provenance",
)
FINITE_GRID_NEED = "finite_grid_need"
E0_GRID_STATE = "exogenous_grid_infeasibility"
PROBABILITY_TOLERANCE = 1.0e-9
_HEX = frozenset("0123456789abcdef")
_ENFORCE_JOINT_BUDGET_BY_ARM = {
    specification.arm_id: specification.enforce_joint_budget
    for specification in FOUR_ARM_SPECS
}
_PLANNING_CERTIFICATE_FIELDS = {
    "enforce_joint_budget",
    "feasible",
    "proven_infeasible",
    "minimum_capacity",
    "termination_condition",
    "solver_status",
    "maximum_residual",
    "lower_bound",
    "upper_bound",
    "absolute_gap",
    "relative_gap",
    "gap_tolerance",
    "model_variables",
    "model_constraints",
    "solver_name",
    "solver_options",
}
_RAW_OUTCOME_FIELDS = {
    "name",
    "committed_flexibility",
    "resolved",
    "hard_grid_failure",
    "physical_policy_failure",
    "service_shortfall_failure",
    "access_shortfall",
    "peak_recovery_debt",
    "terminal_recovery_debt",
    "combined_call",
    "green_served",
    "physical_violations",
}
_REGISTERED_OUTCOME_FIELDS = {
    "schema",
    "resolved",
    "unresolved_reason",
    "registered_failure",
    "registered_physical_failure",
    "service_shortfall_failure",
    "service_shortfall_amount",
    "registered_physical_violations",
    "excluded_debt_violations",
    "excluded_terminal_condition_violations",
    "right_censored",
    "raw_outcome",
}


def _canonical_bytes(value: object) -> bytes:
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


def _digest_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _digest_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path_is_reparse(path: Path) -> bool:
    """Return true for symlinks and Windows reparse points without following them."""

    information = os.lstat(path)
    reparse_flag = getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x0400)
    return bool(
        stat.S_ISLNK(information.st_mode)
        or getattr(information, "st_file_attributes", 0) & reparse_flag
    )


def _assert_safe_path_components(path: Path) -> None:
    """Reject every existing reparse component in an absolute lexical path."""

    absolute = Path(os.path.abspath(path))
    current = Path(absolute.anchor)
    missing_parent = False
    for component in absolute.parts[1:]:
        current /= component
        if missing_parent:
            continue
        try:
            if _path_is_reparse(current):
                raise ValueError(f"reparse path component is forbidden: {current}")
        except FileNotFoundError:
            missing_parent = True


def _walk_regular_files(directory: Path) -> list[Path]:
    """Walk a package without entering symlinks, junctions, or special files."""

    _assert_safe_path_components(directory)
    files: list[Path] = []

    def visit(parent: Path) -> None:
        with os.scandir(parent) as entries:
            for entry in entries:
                path = Path(entry.path)
                if _path_is_reparse(path):
                    raise ValueError(f"reparse package child is forbidden: {path}")
                if entry.is_dir(follow_symlinks=False):
                    visit(path)
                elif entry.is_file(follow_symlinks=False):
                    files.append(path)
                else:
                    raise ValueError(f"special package child is forbidden: {path}")

    visit(directory)
    return sorted(files)


def _require_sha256(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in _HEX for character in value)
    ):
        raise ValueError(f"{label} must be a lowercase SHA-256 digest")
    return value


def _safe_component(value: object, label: str) -> str:
    if not isinstance(value, str) or not value or value in {".", ".."}:
        raise ValueError(f"{label} must be a nonempty path-safe identifier")
    if any(character in value for character in ("/", "\\", ":", "\x00")):
        raise ValueError(f"{label} must be a single path component")
    return value


def _mapping(value: object, label: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"{label} must be a mapping")
    return value


def _sequence(value: object, label: str) -> Sequence[Any]:
    if isinstance(value, (str, bytes)) or not isinstance(value, Sequence):
        raise ValueError(f"{label} must be a sequence")
    return value


def _finite(value: object, label: str, *, minimum: float = 0.0) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be numeric") from error
    if not isfinite(number) or number < minimum:
        raise ValueError(f"{label} must be finite and at least {minimum}")
    return number


def _probability(value: object, label: str) -> float:
    probability = _finite(value, label)
    if probability > 1.0:
        raise ValueError(f"{label} must not exceed 1.0")
    return probability


def _object_mapping(value: object, label: str) -> dict[str, Any]:
    if is_dataclass(value) and not isinstance(value, type):
        converted = asdict(value)
    elif isinstance(value, Mapping):
        converted = dict(value)
    else:
        attributes = getattr(value, "__dict__", None)
        if not isinstance(attributes, dict):
            raise ValueError(f"{label} must be a dataclass or mapping")
        converted = dict(attributes)
    _canonical_bytes(converted)
    return converted


def build_resume_identity(
    *,
    run_id: str,
    successor_config_sha256: str,
    authority_sha256s: Mapping[str, str],
) -> dict[str, object]:
    """Build a deterministic identity shared by every resumable checkpoint."""

    run = _safe_component(run_id, "run_id")
    config_digest = _require_sha256(
        successor_config_sha256, "successor_config_sha256"
    )
    if not authority_sha256s:
        raise ValueError("authority_sha256s must not be empty")
    authorities = {
        _safe_component(name, "authority name"): _require_sha256(
            digest, f"authority {name}"
        )
        for name, digest in sorted(authority_sha256s.items())
    }
    identity: dict[str, object] = {
        "schema": RESUME_IDENTITY_SCHEMA,
        "run_id": run,
        "successor_config_sha256": config_digest,
        "authority_sha256s": authorities,
    }
    identity["identity_sha256"] = _digest_bytes(_canonical_bytes(identity))
    return identity


def validate_resume_identity(value: object) -> dict[str, object]:
    """Validate and normalize a resume identity without touching the filesystem."""

    identity = dict(_mapping(value, "resume_identity"))
    if set(identity) != {
        "schema",
        "run_id",
        "successor_config_sha256",
        "authority_sha256s",
        "identity_sha256",
    }:
        raise ValueError("resume identity inventory drifted")
    if identity["schema"] != RESUME_IDENTITY_SCHEMA:
        raise ValueError("resume identity schema drifted")
    expected = build_resume_identity(
        run_id=identity["run_id"],
        successor_config_sha256=identity["successor_config_sha256"],
        authority_sha256s=_mapping(
            identity["authority_sha256s"], "authority_sha256s"
        ),
    )
    if identity != expected:
        raise ValueError("resume identity digest or canonical form drifted")
    return expected


def _canonical_arm_objects(value: object, label: str) -> dict[str, object]:
    if isinstance(value, Mapping):
        by_arm = dict(value)
    else:
        items = getattr(value, "arms", value)
        by_arm = {}
        for item in _sequence(items, label):
            arm_id = getattr(item, "arm_id", None)
            if not isinstance(arm_id, str) and isinstance(item, Mapping):
                arm_id = item.get("arm_id")
            if not isinstance(arm_id, str) or arm_id in by_arm:
                raise ValueError(f"{label} has missing or duplicate arm IDs")
            by_arm[arm_id] = item
    if set(by_arm) != set(FOUR_ARM_IDS):
        raise ValueError(f"{label} four-arm inventory drifted")
    return {arm_id: by_arm[arm_id] for arm_id in FOUR_ARM_IDS}


def _planning_result(item: object) -> object:
    if isinstance(item, Mapping):
        return item.get("result", item)
    return getattr(item, "result", item)


def _planning_record(arm_id: str, item: object) -> dict[str, object]:
    result = _planning_result(item)
    certificate = _object_mapping(result, f"planning result for {arm_id}")
    if set(certificate) != _PLANNING_CERTIFICATE_FIELDS:
        raise ValueError(f"planning certificate inventory drifted for {arm_id}")
    for key in ("enforce_joint_budget", "feasible", "proven_infeasible"):
        if not isinstance(certificate[key], bool):
            raise ValueError(f"planning certificate {key} must be boolean")
    if certificate["enforce_joint_budget"] is not _ENFORCE_JOINT_BUDGET_BY_ARM[arm_id]:
        raise ValueError(f"planning certificate joint-budget semantics drifted for {arm_id}")
    for key in ("termination_condition", "solver_status", "solver_name"):
        if not isinstance(certificate[key], str) or not certificate[key]:
            raise ValueError(f"planning certificate {key} must be nonempty")
    for key in ("model_variables", "model_constraints"):
        if (
            isinstance(certificate[key], bool)
            or not isinstance(certificate[key], int)
            or certificate[key] < 0
        ):
            raise ValueError(f"planning certificate {key} must be nonnegative")
    _mapping(certificate["solver_options"], "solver_options")
    for key in (
        "maximum_residual",
        "lower_bound",
        "upper_bound",
        "absolute_gap",
        "relative_gap",
        "gap_tolerance",
    ):
        if certificate[key] is not None:
            _finite(certificate[key], f"planning certificate {key}")
    feasible = certificate.get("feasible") is True
    proven_infeasible = certificate.get("proven_infeasible") is True
    capacity = certificate.get("minimum_capacity")
    if feasible and not proven_infeasible:
        normalized_capacity = _finite(capacity, f"capacity for {arm_id}")
        status = "resolved"
        estimand_defined = True
    elif (
        proven_infeasible
        and not feasible
        and capacity is None
        and certificate["termination_condition"].casefold() == "infeasible"
    ):
        normalized_capacity = None
        status = "proven_infeasible"
        estimand_defined = False
    else:
        normalized_capacity = None
        status = "unresolved"
        estimand_defined = False
    return {
        "arm_id": arm_id,
        "status": status,
        "minimum_capacity": normalized_capacity,
        "estimand_defined": estimand_defined,
        "certificate": certificate,
    }


def _training_records(
    planning: Sequence[Mapping[str, object]],
    training_audit: object | None,
    expected_pair_ids: Sequence[str],
) -> list[dict[str, object]]:
    statuses = {str(record["status"]) for record in planning}
    if statuses == {"resolved"}:
        if training_audit is None:
            return [
                {
                    "arm_id": arm_id,
                    "status": "unresolved",
                    "pair_count": None,
                    "failed_pair_ids": [],
                    "unresolved_pair_ids": [],
                    "reason": "full_training_support_audit_missing",
                }
                for arm_id in FOUR_ARM_IDS
            ]
        audited = _canonical_arm_objects(training_audit, "training audit")
        records = []
        for arm_id, item in audited.items():
            audit = _object_mapping(item, f"training audit for {arm_id}")
            failures = list(audit.get("failed_pair_ids", ()))
            unresolved = list(audit.get("unresolved_pair_ids", ()))
            pair_count = audit.get("pair_count")
            if isinstance(pair_count, bool) or not isinstance(pair_count, int):
                raise ValueError("training pair_count must be an integer")
            if pair_count < 1:
                raise ValueError("training pair_count must be positive")
            if pair_count != len(expected_pair_ids):
                raise ValueError("training pair_count does not cover the Cartesian inventory")
            if (
                not set(failures).issubset(expected_pair_ids)
                or not set(unresolved).issubset(expected_pair_ids)
                or set(failures) & set(unresolved)
            ):
                raise ValueError("training failure/unresolved pair inventory drifted")
            records.append(
                {
                    "arm_id": arm_id,
                    "status": (
                        "passed" if not failures and not unresolved else "failed"
                    ),
                    "pair_count": pair_count,
                    "failed_pair_ids": failures,
                    "unresolved_pair_ids": unresolved,
                    "reason": None,
                }
            )
        return records
    reason = (
        "planning_estimand_undefined"
        if "proven_infeasible" in statuses and "unresolved" not in statuses
        else "planning_unresolved"
    )
    return [
        {
            "arm_id": arm_id,
            "status": "not_applicable" if reason.endswith("undefined") else "unresolved",
            "pair_count": None,
            "failed_pair_ids": [],
            "unresolved_pair_ids": [],
            "reason": reason,
        }
        for arm_id in FOUR_ARM_IDS
    ]


def _training_pair_inventory(expected_training_pair_ids: Sequence[str]) -> dict[str, object]:
    pair_ids = sorted(
        _safe_component(pair_id, "training pair ID")
        for pair_id in expected_training_pair_ids
    )
    if not pair_ids or len(pair_ids) != len(set(pair_ids)):
        raise ValueError("training pair inventory is empty or duplicated")
    return {
        "schema": "rq2_baseline_training_pair_inventory_v1",
        "pair_ids": pair_ids,
        "pair_count": len(pair_ids),
        "canonical_sha256": _digest_bytes(_canonical_bytes(pair_ids)),
    }


def build_planning_checkpoint(
    *,
    cell_id: str,
    planning: object,
    training_audit: object | None,
    expected_training_pair_ids: Sequence[str],
    resume_identity: Mapping[str, object],
    provenance: Mapping[str, object],
) -> dict[str, object]:
    """Serialize one cell's four planning certificates and support audit."""

    identity = validate_resume_identity(resume_identity)
    training_inventory = _training_pair_inventory(expected_training_pair_ids)
    by_arm = _canonical_arm_objects(planning, "planning")
    planning_records = [
        _planning_record(arm_id, by_arm[arm_id]) for arm_id in FOUR_ARM_IDS
    ]
    training_records = _training_records(
        planning_records,
        training_audit,
        training_inventory["pair_ids"],
    )
    statuses = {str(record["status"]) for record in planning_records}
    if "unresolved" in statuses or any(
        record["status"] in {"failed", "unresolved"}
        for record in training_records
    ):
        disposition = "unresolved"
    elif "proven_infeasible" in statuses:
        disposition = "training_infeasible_estimand_undefined"
    else:
        disposition = "resolved"
    checkpoint = {
        "schema": PLANNING_CHECKPOINT_SCHEMA,
        "cell_id": _safe_component(cell_id, "cell_id"),
        "resume_identity": identity,
        "disposition": disposition,
        "training_pair_inventory": training_inventory,
        "four_arm_minimum_flexibility": planning_records,
        "four_arm_training_status": training_records,
        "provenance": dict(_mapping(provenance, "provenance")),
    }
    _canonical_bytes(checkpoint)
    validate_planning_checkpoint(checkpoint)
    return checkpoint


def validate_planning_checkpoint(value: object) -> dict[str, object]:
    """Fail closed on planning inventory or status/certificate drift."""

    checkpoint = dict(_mapping(value, "planning checkpoint"))
    if set(checkpoint) != {
        "schema",
        "cell_id",
        "resume_identity",
        "disposition",
        "training_pair_inventory",
        "four_arm_minimum_flexibility",
        "four_arm_training_status",
        "provenance",
    }:
        raise ValueError("planning checkpoint inventory drifted")
    if checkpoint["schema"] != PLANNING_CHECKPOINT_SCHEMA:
        raise ValueError("planning checkpoint schema drifted")
    _safe_component(checkpoint["cell_id"], "cell_id")
    validate_resume_identity(checkpoint["resume_identity"])
    training_inventory = _mapping(
        checkpoint["training_pair_inventory"], "training pair inventory"
    )
    if set(training_inventory) != {
        "schema",
        "pair_ids",
        "pair_count",
        "canonical_sha256",
    }:
        raise ValueError("training pair inventory schema drifted")
    rebuilt_inventory = _training_pair_inventory(training_inventory["pair_ids"])
    if training_inventory != rebuilt_inventory:
        raise ValueError("training pair inventory hash/order drifted")
    planning = _sequence(
        checkpoint["four_arm_minimum_flexibility"], "planning records"
    )
    training = _sequence(
        checkpoint["four_arm_training_status"], "training records"
    )
    if [item.get("arm_id") for item in planning] != list(FOUR_ARM_IDS):
        raise ValueError("planning records are not in canonical arm order")
    if [item.get("arm_id") for item in training] != list(FOUR_ARM_IDS):
        raise ValueError("training records are not in canonical arm order")
    rebuilt_planning = [
        _planning_record(arm_id, _mapping(item, "planning record")["certificate"])
        for arm_id, item in zip(FOUR_ARM_IDS, planning, strict=True)
    ]
    if list(planning) != rebuilt_planning:
        raise ValueError("planning status disagrees with its certificate")
    planning_statuses = {str(item["status"]) for item in planning}
    for record in training:
        item = _mapping(record, "training record")
        if set(item) != {
            "arm_id",
            "status",
            "pair_count",
            "failed_pair_ids",
            "unresolved_pair_ids",
            "reason",
        }:
            raise ValueError("training status inventory drifted")
        if item["status"] == "passed":
            if (
                not isinstance(item["pair_count"], int)
                or isinstance(item["pair_count"], bool)
                or item["pair_count"] < 1
                or item["failed_pair_ids"]
                or item["unresolved_pair_ids"]
                or item["reason"] is not None
            ):
                raise ValueError("passed training audit is inconsistent")
        if item["pair_count"] is not None:
            if item["pair_count"] != training_inventory["pair_count"]:
                raise ValueError("training pair_count does not match inventory")
            failed = set(_sequence(item["failed_pair_ids"], "failed pair IDs"))
            unresolved = set(
                _sequence(item["unresolved_pair_ids"], "unresolved pair IDs")
            )
            if (
                not failed.issubset(training_inventory["pair_ids"])
                or not unresolved.issubset(training_inventory["pair_ids"])
                or failed & unresolved
            ):
                raise ValueError("training status pair IDs drifted")
    if "unresolved" in planning_statuses or any(
        item["status"] in {"failed", "unresolved"} for item in training
    ):
        expected_disposition = "unresolved"
    elif "proven_infeasible" in planning_statuses:
        expected_disposition = "training_infeasible_estimand_undefined"
    elif all(item["status"] == "passed" for item in training):
        expected_disposition = "resolved"
    else:
        raise ValueError("planning/training disposition is incomplete")
    if checkpoint["disposition"] != expected_disposition:
        raise ValueError("planning disposition drifted")
    _mapping(checkpoint["provenance"], "provenance")
    _canonical_bytes(checkpoint)
    return checkpoint


def _serialize_execution(execution: object) -> list[dict[str, object]]:
    by_arm = _canonical_arm_objects(execution, "four-arm execution")
    records = []
    for arm_id, item in by_arm.items():
        source = _object_mapping(item, f"execution for {arm_id}")
        raw = source.get("outcome")
        registered = source.get("registered_service_risk")
        if raw is None or registered is None:
            raise ValueError(f"execution for {arm_id} lacks raw or registered outcome")
        raw_record = _object_mapping(raw, f"raw outcome for {arm_id}")
        registered_record = _object_mapping(
            registered, f"registered outcome for {arm_id}"
        )
        nested_raw = registered_record.get("raw_outcome")
        if nested_raw is not None and nested_raw != raw_record:
            raise ValueError("registered outcome does not bind the raw outcome")
        records.append(
            {
                "arm_id": arm_id,
                "committed_capacity": _finite(
                    source.get("committed_capacity"),
                    f"committed capacity for {arm_id}",
                ),
                "raw_causal_policy_outcome": raw_record,
                "registered_service_risk_outcome": registered_record,
            }
        )
    return records


def _boundary_fields(
    *,
    right_censored: bool,
    boundary_state_status: str,
    terminal_period_completed: bool,
    require_terminal_event_inactive: bool,
) -> dict[str, object]:
    for label, value in (
        ("right_censored", right_censored),
        ("terminal_period_completed", terminal_period_completed),
        ("require_terminal_event_inactive", require_terminal_event_inactive),
    ):
        if not isinstance(value, bool):
            raise ValueError(f"{label} must be boolean")
    if not isinstance(boundary_state_status, str) or not boundary_state_status:
        raise ValueError("boundary_state_status must be nonempty")
    derived_right_censored = bool(
        not terminal_period_completed or not require_terminal_event_inactive
    )
    if right_censored is not derived_right_censored:
        raise ValueError("right_censored disagrees with explicit terminal boundary fields")
    return {
        "right_censored": right_censored,
        "boundary_state_status": boundary_state_status,
        "terminal_period_completed": terminal_period_completed,
        "require_terminal_event_inactive": require_terminal_event_inactive,
    }


def _rebuild_registered_service_risk(
    raw: Mapping[str, object], *, right_censored: bool
) -> dict[str, object]:
    """Rebuild the complete registered v1 layer from raw public diagnostics."""

    physical_violations = _sequence(raw.get("physical_violations"), "violations")
    collection = tuple if isinstance(physical_violations, tuple) else list
    debt_violations = collection(
        code
        for code in physical_violations
        if code.startswith(UNBOUND_DEBT_VIOLATION_PREFIXES_V1)
    )
    terminal_violations = collection(
        code
        for code in physical_violations
        if code in UNBOUND_TERMINAL_CONDITION_VIOLATIONS_V1
    )
    excluded = {*debt_violations, *terminal_violations}
    registered_violations = collection(
        code for code in physical_violations if code not in excluded
    )
    raw_physical_failure = bool(
        raw["hard_grid_failure"] or raw["physical_policy_failure"]
    )
    diagnostics_consistent = raw_physical_failure == bool(physical_violations)
    resolved = bool(raw["resolved"] and diagnostics_consistent)
    unresolved_reason = None
    if not raw["resolved"]:
        unresolved_reason = "source_causal_outcome_unresolved"
    elif not diagnostics_consistent:
        unresolved_reason = "raw_physical_failure_and_violation_inventory_disagree"
    registered_physical_failure = bool(registered_violations) if resolved else None
    shortfall_failure = bool(raw["service_shortfall_failure"]) if resolved else None
    return {
        "schema": REGISTERED_SERVICE_RISK_SCHEMA,
        "resolved": resolved,
        "unresolved_reason": unresolved_reason,
        "registered_failure": (
            bool(registered_physical_failure or shortfall_failure)
            if resolved
            else None
        ),
        "registered_physical_failure": registered_physical_failure,
        "service_shortfall_failure": shortfall_failure,
        "service_shortfall_amount": raw["access_shortfall"] if resolved else None,
        "registered_physical_violations": registered_violations,
        "excluded_debt_violations": debt_violations,
        "excluded_terminal_condition_violations": terminal_violations,
        "right_censored": right_censored,
        "raw_outcome": dict(raw),
    }


def build_finite_pair_checkpoint(
    *,
    cell_id: str,
    power_block_id: str,
    workload_block_id: str,
    power_probability: object,
    workload_probability: object,
    right_censored: bool,
    boundary_state_status: str,
    terminal_period_completed: bool,
    require_terminal_event_inactive: bool,
    execution: object,
    resume_identity: Mapping[str, object],
    provenance: Mapping[str, object],
) -> dict[str, object]:
    """Serialize all four raw and registered outcomes for one finite pair."""

    power = _probability(power_probability, "power_probability")
    workload = _probability(workload_probability, "workload_probability")
    checkpoint = {
        "schema": FINITE_PAIR_CHECKPOINT_SCHEMA,
        "cell_id": _safe_component(cell_id, "cell_id"),
        "power_block_id": _safe_component(power_block_id, "power_block_id"),
        "workload_block_id": _safe_component(
            workload_block_id, "workload_block_id"
        ),
        "grid_state": FINITE_GRID_NEED,
        "power_probability": power,
        "workload_probability": workload,
        "unconditional_pair_probability": power * workload,
        **_boundary_fields(
            right_censored=right_censored,
            boundary_state_status=boundary_state_status,
            terminal_period_completed=terminal_period_completed,
            require_terminal_event_inactive=require_terminal_event_inactive,
        ),
        "resume_identity": validate_resume_identity(resume_identity),
        "arms": _serialize_execution(execution),
        "provenance": dict(_mapping(provenance, "provenance")),
    }
    _canonical_bytes(checkpoint)
    validate_finite_pair_checkpoint(checkpoint)
    return checkpoint


def build_E0_pair_checkpoint(
    *,
    cell_id: str,
    power_block_id: str,
    workload_block_id: str,
    power_probability: object,
    workload_probability: object,
    right_censored: bool,
    boundary_state_status: str,
    terminal_period_completed: bool,
    require_terminal_event_inactive: bool,
    resolved: bool,
    unresolved_reason: str | None,
    resume_identity: Mapping[str, object],
    provenance: Mapping[str, object],
) -> dict[str, object]:
    """Preserve one exogenous-grid-infeasibility pair's unconditional mass."""

    if not isinstance(resolved, bool):
        raise ValueError("E0 resolved must be boolean")
    if resolved and unresolved_reason is not None:
        raise ValueError("resolved E0 checkpoint cannot have an unresolved reason")
    if not resolved and not unresolved_reason:
        raise ValueError("unresolved E0 checkpoint requires a reason")
    power = _probability(power_probability, "power_probability")
    workload = _probability(workload_probability, "workload_probability")
    checkpoint = {
        "schema": E0_CHECKPOINT_SCHEMA,
        "cell_id": _safe_component(cell_id, "cell_id"),
        "power_block_id": _safe_component(power_block_id, "power_block_id"),
        "workload_block_id": _safe_component(
            workload_block_id, "workload_block_id"
        ),
        "grid_state": E0_GRID_STATE,
        "resolved": resolved,
        "unresolved_reason": unresolved_reason,
        "power_probability": power,
        "workload_probability": workload,
        "unconditional_pair_probability": power * workload,
        **_boundary_fields(
            right_censored=right_censored,
            boundary_state_status=boundary_state_status,
            terminal_period_completed=terminal_period_completed,
            require_terminal_event_inactive=require_terminal_event_inactive,
        ),
        "service_metrics_defined": False,
        "resume_identity": validate_resume_identity(resume_identity),
        "provenance": dict(_mapping(provenance, "provenance")),
    }
    _canonical_bytes(checkpoint)
    validate_E0_pair_checkpoint(checkpoint)
    return checkpoint


def _validate_pair_common(checkpoint: Mapping[str, object]) -> None:
    _safe_component(checkpoint.get("cell_id"), "cell_id")
    _safe_component(checkpoint.get("power_block_id"), "power_block_id")
    _safe_component(checkpoint.get("workload_block_id"), "workload_block_id")
    power = _probability(checkpoint.get("power_probability"), "power_probability")
    workload = _probability(
        checkpoint.get("workload_probability"), "workload_probability"
    )
    product = _finite(
        checkpoint.get("unconditional_pair_probability"),
        "unconditional_pair_probability",
    )
    if abs(product - power * workload) > PROBABILITY_TOLERANCE:
        raise ValueError("unconditional pair probability drifted")
    _boundary_fields(
        right_censored=checkpoint.get("right_censored"),
        boundary_state_status=checkpoint.get("boundary_state_status"),
        terminal_period_completed=checkpoint.get("terminal_period_completed"),
        require_terminal_event_inactive=checkpoint.get(
            "require_terminal_event_inactive"
        ),
    )
    validate_resume_identity(checkpoint.get("resume_identity"))
    _mapping(checkpoint.get("provenance"), "provenance")


def validate_finite_pair_checkpoint(value: object) -> dict[str, object]:
    checkpoint = dict(_mapping(value, "finite pair checkpoint"))
    if set(checkpoint) != {
        "schema",
        "cell_id",
        "power_block_id",
        "workload_block_id",
        "grid_state",
        "power_probability",
        "workload_probability",
        "unconditional_pair_probability",
        "right_censored",
        "boundary_state_status",
        "terminal_period_completed",
        "require_terminal_event_inactive",
        "resume_identity",
        "arms",
        "provenance",
    }:
        raise ValueError("finite pair checkpoint inventory drifted")
    if (
        checkpoint["schema"] != FINITE_PAIR_CHECKPOINT_SCHEMA
        or checkpoint["grid_state"] != FINITE_GRID_NEED
    ):
        raise ValueError("finite pair checkpoint schema/state drifted")
    _validate_pair_common(checkpoint)
    arms = _sequence(checkpoint["arms"], "finite pair arms")
    if [item.get("arm_id") for item in arms] != list(FOUR_ARM_IDS):
        raise ValueError("finite pair arms are missing, extra, or out of order")
    for arm in arms:
        record = _mapping(arm, "finite arm record")
        if set(record) != {
            "arm_id",
            "committed_capacity",
            "raw_causal_policy_outcome",
            "registered_service_risk_outcome",
        }:
            raise ValueError("finite arm inventory drifted")
        _finite(record["committed_capacity"], "committed_capacity")
        raw = _mapping(record["raw_causal_policy_outcome"], "raw outcome")
        registered = _mapping(
            record["registered_service_risk_outcome"], "registered outcome"
        )
        if set(raw) != _RAW_OUTCOME_FIELDS:
            raise ValueError("raw causal policy outcome inventory drifted")
        if set(registered) != _REGISTERED_OUTCOME_FIELDS:
            raise ValueError("registered service-risk outcome inventory drifted")
        if not isinstance(raw.get("resolved"), bool) or not isinstance(
            registered.get("resolved"), bool
        ):
            raise ValueError("finite pair resolved fields must be boolean")
        if not isinstance(raw.get("name"), str) or not raw["name"]:
            raise ValueError("raw outcome name must be nonempty")
        for key in (
            "hard_grid_failure",
            "physical_policy_failure",
            "service_shortfall_failure",
        ):
            if not isinstance(raw.get(key), bool):
                raise ValueError(f"raw outcome {key} must be boolean")
        for key in (
            "committed_flexibility",
            "access_shortfall",
            "peak_recovery_debt",
            "terminal_recovery_debt",
        ):
            _finite(raw.get(key), f"raw outcome {key}")
        for key in ("combined_call", "green_served"):
            for index, item in enumerate(_sequence(raw.get(key), key)):
                _finite(item, f"{key}[{index}]")
        if len(raw["combined_call"]) != len(raw["green_served"]):
            raise ValueError("raw outcome trajectory lengths drifted")
        if any(
            not isinstance(item, str)
            for item in _sequence(raw.get("physical_violations"), "physical violations")
        ):
            raise ValueError("raw physical violations must contain strings")
        if registered.get("schema") != REGISTERED_SERVICE_RISK_SCHEMA:
            raise ValueError("registered service-risk schema drifted")
        if not isinstance(registered.get("right_censored"), bool):
            raise ValueError("registered right_censored must be boolean")
        for key in (
            "registered_physical_violations",
            "excluded_debt_violations",
            "excluded_terminal_condition_violations",
        ):
            if any(not isinstance(item, str) for item in _sequence(registered.get(key), key)):
                raise ValueError(f"registered outcome {key} must contain strings")
        if registered.get("resolved") is True:
            for key in (
                "registered_failure",
                "registered_physical_failure",
                "service_shortfall_failure",
            ):
                if not isinstance(registered.get(key), bool):
                    raise ValueError(f"registered outcome {key} must be boolean")
            _finite(
                registered.get("service_shortfall_amount"),
                "registered service_shortfall_amount",
            )
            if registered.get("unresolved_reason") is not None:
                raise ValueError("resolved registered outcome has a reason")
            expected_failure = bool(
                registered["registered_physical_failure"]
                or registered["service_shortfall_failure"]
            )
            if registered["registered_failure"] is not expected_failure:
                raise ValueError("registered failure channels disagree")
            if registered["service_shortfall_amount"] != raw["access_shortfall"]:
                raise ValueError("registered shortfall does not preserve raw shortfall")
        elif registered.get("unresolved_reason") in {None, ""}:
            raise ValueError("unresolved registered outcome requires a reason")
        if registered.get("raw_outcome") != raw:
            raise ValueError("registered outcome does not preserve the raw outcome")
        rebuilt_registered = _rebuild_registered_service_risk(
            raw, right_censored=checkpoint["right_censored"]
        )
        if registered != rebuilt_registered:
            raise ValueError("registered service-risk layer disagrees with raw diagnostics")
    _canonical_bytes(checkpoint)
    return checkpoint


def validate_E0_pair_checkpoint(value: object) -> dict[str, object]:
    checkpoint = dict(_mapping(value, "E0 checkpoint"))
    if set(checkpoint) != {
        "schema",
        "cell_id",
        "power_block_id",
        "workload_block_id",
        "grid_state",
        "resolved",
        "unresolved_reason",
        "power_probability",
        "workload_probability",
        "unconditional_pair_probability",
        "right_censored",
        "boundary_state_status",
        "terminal_period_completed",
        "require_terminal_event_inactive",
        "service_metrics_defined",
        "resume_identity",
        "provenance",
    }:
        raise ValueError("E0 checkpoint inventory drifted")
    if (
        checkpoint["schema"] != E0_CHECKPOINT_SCHEMA
        or checkpoint["grid_state"] != E0_GRID_STATE
        or checkpoint["service_metrics_defined"] is not False
    ):
        raise ValueError("E0 checkpoint schema/state drifted")
    _validate_pair_common(checkpoint)
    if not isinstance(checkpoint["resolved"], bool):
        raise ValueError("E0 resolved field must be boolean")
    if checkpoint["resolved"] and checkpoint["unresolved_reason"] is not None:
        raise ValueError("resolved E0 checkpoint has an unresolved reason")
    if not checkpoint["resolved"] and not checkpoint["unresolved_reason"]:
        raise ValueError("unresolved E0 checkpoint lacks a reason")
    _canonical_bytes(checkpoint)
    return checkpoint


def compute_planning_checkpoint(
    *,
    cell_id: str,
    training_inputs: object,
    solver_specification: object,
    power_blocks: tuple[object, ...],
    workload_blocks: tuple[object, ...],
    cell: object,
    fixed_policy: Mapping[str, object],
    grid_state_by_power_block: Mapping[str, str],
    resume_identity: Mapping[str, object],
    provenance: Mapping[str, object],
) -> dict[str, object]:
    """Call only the registered planning and full-support public APIs."""

    planning = plan_four_arm_minimum_flexibility_with_spec(
        training_inputs, solver_specification=solver_specification
    )
    power_ids = [
        _safe_component(
            block.get("block_id") if isinstance(block, Mapping) else block.block_id,
            "training power block ID",
        )
        for block in power_blocks
    ]
    workload_ids = [
        _safe_component(
            block.get("block_id") if isinstance(block, Mapping) else block.block_id,
            "training workload block ID",
        )
        for block in workload_blocks
    ]
    expected_training_pair_ids = [
        f"{power_id}__{workload_id}"
        for power_id in power_ids
        for workload_id in workload_ids
    ]
    records = [
        _planning_record(arm_id, item)
        for arm_id, item in _canonical_arm_objects(planning, "planning").items()
    ]
    audit = None
    if all(record["status"] == "resolved" for record in records):
        capacities = {
            str(record["arm_id"]): record["minimum_capacity"] for record in records
        }
        audit = audit_four_arm_training_support(
            power_blocks,
            workload_blocks,
            cell,
            capacity_by_arm=capacities,
            fixed_policy=fixed_policy,
            grid_state_by_power_block=grid_state_by_power_block,
        )
    return build_planning_checkpoint(
        cell_id=cell_id,
        planning=planning,
        training_audit=audit,
        expected_training_pair_ids=expected_training_pair_ids,
        resume_identity=resume_identity,
        provenance=provenance,
    )


def compute_finite_pair_checkpoint(
    *,
    cell_id: str,
    power_block_id: str,
    workload_block_id: str,
    power_probability: object,
    workload_probability: object,
    scenario: object,
    envelope: object,
    capacity_by_arm: Mapping[str, object],
    service_shortfall_tolerance: float,
    resume_identity: Mapping[str, object],
    provenance: Mapping[str, object],
) -> dict[str, object]:
    """Call only the registered public four-arm causal replay API."""

    execution = execute_four_arm_causal_policy(
        scenario,
        envelope,
        capacity_by_arm,
        grid_state=FINITE_GRID_NEED,
        service_shortfall_tolerance=service_shortfall_tolerance,
    )
    if not scenario.periods:
        raise ValueError("finite pair scenario must have at least one period")
    terminal_period_completed = scenario.periods[-1] in scenario.completed_periods
    right_censored = bool(
        not terminal_period_completed or not scenario.require_terminal_event_inactive
    )
    return build_finite_pair_checkpoint(
        cell_id=cell_id,
        power_block_id=power_block_id,
        workload_block_id=workload_block_id,
        power_probability=power_probability,
        workload_probability=workload_probability,
        right_censored=right_censored,
        boundary_state_status=scenario.boundary_state_status,
        terminal_period_completed=terminal_period_completed,
        require_terminal_event_inactive=scenario.require_terminal_event_inactive,
        execution=execution,
        resume_identity=resume_identity,
        provenance=provenance,
    )


def write_checkpoint_idempotent(path: Path, checkpoint: Mapping[str, object]) -> str:
    """Create one checkpoint atomically; accept only byte-identical replay."""

    payload = _canonical_bytes(checkpoint)
    _assert_safe_path_components(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    _assert_safe_path_components(path.parent)
    if path.exists():
        if not path.is_file() or path.read_bytes() != payload:
            raise FileExistsError(f"checkpoint drift at {path}")
        return _digest_bytes(payload)
    temporary = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex}")
    try:
        temporary.write_bytes(payload)
        try:
            os.link(temporary, path)
        except FileExistsError:
            if not path.is_file() or path.read_bytes() != payload:
                raise FileExistsError(f"checkpoint drift at {path}") from None
        return _digest_bytes(payload)
    finally:
        temporary.unlink(missing_ok=True)


def _load_checkpoint(path: Path) -> dict[str, object]:
    _assert_safe_path_components(path)
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"checkpoint must be a regular file: {path}")
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"invalid checkpoint: {path}") from error
    return dict(_mapping(loaded, f"checkpoint {path}"))


def _pair_key(value: Mapping[str, object]) -> tuple[str, str, str]:
    return (
        str(value["cell_id"]),
        str(value["power_block_id"]),
        str(value["workload_block_id"]),
    )


def _expected_pair(
    value: object,
) -> tuple[tuple[str, str, str], dict[str, object]]:
    item = _mapping(value, "expected pair")
    if set(item) != {
        "cell_id",
        "power_block_id",
        "workload_block_id",
        "grid_state",
        "power_probability",
        "workload_probability",
        "right_censored",
        "boundary_state_status",
        "terminal_period_completed",
        "require_terminal_event_inactive",
    }:
        raise ValueError("expected pair inventory drifted")
    key = (
        _safe_component(item["cell_id"], "cell_id"),
        _safe_component(item["power_block_id"], "power_block_id"),
        _safe_component(item["workload_block_id"], "workload_block_id"),
    )
    state = item["grid_state"]
    if state not in {FINITE_GRID_NEED, E0_GRID_STATE}:
        raise ValueError("expected pair has unresolved or unknown grid state")
    boundary = _boundary_fields(
        right_censored=item["right_censored"],
        boundary_state_status=item["boundary_state_status"],
        terminal_period_completed=item["terminal_period_completed"],
        require_terminal_event_inactive=item["require_terminal_event_inactive"],
    )
    return key, {
        "cell_id": key[0],
        "power_block_id": key[1],
        "workload_block_id": key[2],
        "grid_state": str(state),
        "power_probability": _probability(
            item["power_probability"], "expected power_probability"
        ),
        "workload_probability": _probability(
            item["workload_probability"], "expected workload_probability"
        ),
        **boundary,
    }


def _validate_expected_pairs(
    expected_pairs: Sequence[Mapping[str, object]], cells: Sequence[str]
) -> dict[tuple[str, str, str], dict[str, object]]:
    expected = dict(_expected_pair(item) for item in expected_pairs)
    if len(expected) != len(expected_pairs):
        raise ValueError("expected pair inventory contains duplicates")
    if set(key[0] for key in expected) != set(cells):
        raise ValueError("expected pair cells do not match the registered inventory")
    by_cell = {
        cell_id: {
            (power_id, workload_id): expected[(cell_id, power_id, workload_id)]
            for candidate_cell, power_id, workload_id in expected
            if candidate_cell == cell_id
        }
        for cell_id in cells
    }
    reference_pairs = set(by_cell[cells[0]])
    power_ids = sorted({key[0] for key in reference_pairs})
    workload_ids = sorted({key[1] for key in reference_pairs})
    cartesian = {
        (power_id, workload_id)
        for power_id in power_ids
        for workload_id in workload_ids
    }
    if not power_ids or not workload_ids or reference_pairs != cartesian:
        raise ValueError("expected pairs are not a complete Cartesian inventory")
    reference = by_cell[cells[0]]
    for cell_id in cells:
        if set(by_cell[cell_id]) != cartesian:
            raise ValueError("cells do not share one complete Cartesian inventory")
        for pair_id in cartesian:
            left = {
                key: value
                for key, value in reference[pair_id].items()
                if key != "cell_id"
            }
            right = {
                key: value
                for key, value in by_cell[cell_id][pair_id].items()
                if key != "cell_id"
            }
            if left != right:
                raise ValueError("pair probability/state/boundary drifted across cells")
    power_probabilities = {
        power_id: reference[(power_id, workload_ids[0])]["power_probability"]
        for power_id in power_ids
    }
    workload_probabilities = {
        workload_id: reference[(power_ids[0], workload_id)][
            "workload_probability"
        ]
        for workload_id in workload_ids
    }
    for pair_id, item in reference.items():
        if item["power_probability"] != power_probabilities[pair_id[0]]:
            raise ValueError("power probability drifted across workload pairs")
        if item["workload_probability"] != workload_probabilities[pair_id[1]]:
            raise ValueError("workload probability drifted across power pairs")
    if abs(fsum(power_probabilities.values()) - 1.0) > PROBABILITY_TOLERANCE:
        raise ValueError("power marginal does not normalize to one")
    if abs(fsum(workload_probabilities.values()) - 1.0) > PROBABILITY_TOLERANCE:
        raise ValueError("workload marginal does not normalize to one")
    state_by_power: dict[str, str] = {}
    for item in expected.values():
        power_id = str(item["power_block_id"])
        state = str(item["grid_state"])
        if power_id in state_by_power and state_by_power[power_id] != state:
            raise ValueError("grid state drifted for one power block")
        state_by_power[power_id] = state
    return expected


def _write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(_canonical_bytes(value))


def _exact_manifest(directory: Path) -> dict[str, str]:
    files = {}
    for path in _walk_regular_files(directory):
        relative = path.relative_to(directory).as_posix()
        files[relative] = _digest_file(path)
    return files


def validate_final_package(directory: Path) -> dict[str, object]:
    """Verify declared schemas and the exact recursive package inventory."""

    _assert_safe_path_components(directory)
    if not directory.is_dir() or _path_is_reparse(directory):
        raise ValueError("final package must be a regular directory")
    package_files = _walk_regular_files(directory)
    manifest_path = directory / "SHA256SUMS.json"
    if not manifest_path.is_file() or _path_is_reparse(manifest_path):
        raise ValueError("final package manifest is missing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if set(manifest) != {"schema", "files"}:
        raise ValueError("final package manifest inventory drifted")
    if manifest["schema"] != PACKAGE_MANIFEST_SCHEMA:
        raise ValueError("final package manifest schema drifted")
    files = dict(_mapping(manifest["files"], "manifest files"))
    if "SHA256SUMS.json" in files:
        raise ValueError("final package manifest must not contain itself")
    observed_paths = {
        path.relative_to(directory).as_posix()
        for path in package_files
        if path != manifest_path
    }
    if set(files) != observed_paths:
        raise ValueError("final package file inventory drifted")
    for relative, expected_digest in files.items():
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts:
            raise ValueError(f"unsafe package path: {relative}")
        expected = _require_sha256(expected_digest, f"hash for {relative}")
        path = directory.joinpath(*pure.parts)
        if not path.is_file() or _path_is_reparse(path) or _digest_file(path) != expected:
            raise ValueError(f"package hash mismatch: {relative}")
    for schema in PACKAGE_SCHEMAS:
        path = directory / f"{schema}.json"
        if not path.is_file() or _path_is_reparse(path):
            raise ValueError(f"package schema is missing: {schema}")
    inventory = json.loads(
        (directory / "checkpoint_inventory.json").read_text(encoding="utf-8")
    )
    if set(inventory) != {
        "schema",
        "probability_tolerance",
        "expected_pairs",
        "planning",
        "pairs",
    }:
        raise ValueError("checkpoint inventory schema drifted")
    if inventory["schema"] != "checkpoint_inventory":
        raise ValueError("checkpoint inventory label drifted")
    if inventory["probability_tolerance"] != PROBABILITY_TOLERANCE:
        raise ValueError("checkpoint probability tolerance drifted")
    declared_checkpoint_paths: set[str] = set()
    planning_checkpoints: list[dict[str, object]] = []
    finite_checkpoints: list[dict[str, object]] = []
    E0_checkpoints: list[dict[str, object]] = []
    for record in _sequence(inventory["planning"], "planning inventory"):
        item = _mapping(record, "planning inventory record")
        if set(item) != {"cell_id", "path", "sha256"}:
            raise ValueError("planning inventory record drifted")
        relative = str(item["path"])
        if not relative.startswith("checkpoints/planning/"):
            raise ValueError("planning checkpoint path drifted")
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts or str(pure) != relative:
            raise ValueError("unsafe planning checkpoint path")
        if relative in declared_checkpoint_paths:
            raise ValueError("duplicate checkpoint inventory path")
        declared_checkpoint_paths.add(relative)
        checkpoint_path = directory.joinpath(*pure.parts)
        if _digest_file(checkpoint_path) != _require_sha256(
            item["sha256"], f"checkpoint hash {relative}"
        ):
            raise ValueError("planning checkpoint inventory hash drifted")
        if files.get(relative) != item["sha256"]:
            raise ValueError("planning checkpoint hash disagrees with package manifest")
        checkpoint = validate_planning_checkpoint(_load_checkpoint(checkpoint_path))
        if checkpoint["cell_id"] != item["cell_id"]:
            raise ValueError("planning checkpoint inventory identity drifted")
        if checkpoint["disposition"] == "unresolved":
            raise ValueError("unresolved planning checkpoint in final package")
        planning_checkpoints.append(checkpoint)
    cells = tuple(str(checkpoint["cell_id"]) for checkpoint in planning_checkpoints)
    if not cells or len(cells) != len(set(cells)):
        raise ValueError("final planning cell inventory is empty or duplicated")
    planning_by_cell = {
        str(checkpoint["cell_id"]): checkpoint for checkpoint in planning_checkpoints
    }
    expected_pairs = _sequence(inventory["expected_pairs"], "expected pairs")
    expected = _validate_expected_pairs(expected_pairs, cells)
    cell_order = {cell_id: index for index, cell_id in enumerate(cells)}
    expected_order = sorted(
        expected,
        key=lambda key: (cell_order[key[0]], key[1], key[2]),
    )
    if list(expected_pairs) != [expected[key] for key in expected_order]:
        raise ValueError("expected pair inventory is not in canonical order")
    training_inventories = {
        _canonical_bytes(checkpoint["training_pair_inventory"])
        for checkpoint in planning_checkpoints
    }
    if len(training_inventories) != 1:
        raise ValueError("training Cartesian inventory drifted across cells")
    required_expected = {
        key: item
        for key, item in expected.items()
        if planning_checkpoints[cell_order[key[0]]]["disposition"] == "resolved"
    }
    for record in _sequence(inventory["pairs"], "pair inventory"):
        item = _mapping(record, "pair inventory record")
        if set(item) != {
            "cell_id",
            "power_block_id",
            "workload_block_id",
            "grid_state",
            "path",
            "sha256",
        }:
            raise ValueError("pair inventory record drifted")
        relative = str(item["path"])
        if not relative.startswith("checkpoints/pairs/"):
            raise ValueError("pair checkpoint path drifted")
        pure = PurePosixPath(relative)
        if pure.is_absolute() or ".." in pure.parts or str(pure) != relative:
            raise ValueError("unsafe pair checkpoint path")
        if relative in declared_checkpoint_paths:
            raise ValueError("duplicate checkpoint inventory path")
        declared_checkpoint_paths.add(relative)
        checkpoint_path = directory.joinpath(*pure.parts)
        if _digest_file(checkpoint_path) != _require_sha256(
            item["sha256"], f"checkpoint hash {relative}"
        ):
            raise ValueError("pair checkpoint inventory hash drifted")
        if files.get(relative) != item["sha256"]:
            raise ValueError("pair checkpoint hash disagrees with package manifest")
        checkpoint = _load_checkpoint(checkpoint_path)
        if checkpoint.get("schema") == FINITE_PAIR_CHECKPOINT_SCHEMA:
            checkpoint = validate_finite_pair_checkpoint(checkpoint)
            if any(
                arm["raw_causal_policy_outcome"]["resolved"] is not True
                or arm["registered_service_risk_outcome"]["resolved"] is not True
                for arm in checkpoint["arms"]
            ):
                raise ValueError("unresolved finite pair in final package")
            planned_capacities = {
                arm["arm_id"]: arm["minimum_capacity"]
                for arm in planning_by_cell[str(checkpoint["cell_id"])][
                    "four_arm_minimum_flexibility"
                ]
            }
            # Both values are serialized checkpoint scalars; exact equality
            # prevents a replay from silently using a re-planned capacity.
            for arm in checkpoint["arms"]:
                if arm["committed_capacity"] != planned_capacities[arm["arm_id"]]:
                    raise ValueError(
                        "finite pair committed capacity disagrees with planning"
                    )
            finite_checkpoints.append(checkpoint)
        elif checkpoint.get("schema") == E0_CHECKPOINT_SCHEMA:
            checkpoint = validate_E0_pair_checkpoint(checkpoint)
            if checkpoint["resolved"] is not True:
                raise ValueError("unresolved E0 pair in final package")
            E0_checkpoints.append(checkpoint)
        else:
            raise ValueError("unknown pair checkpoint in final package")
        if _pair_key(checkpoint) != (
            item["cell_id"],
            item["power_block_id"],
            item["workload_block_id"],
        ) or checkpoint["grid_state"] != item["grid_state"]:
            raise ValueError("pair checkpoint inventory identity drifted")
        key = _pair_key(checkpoint)
        if key not in required_expected:
            raise ValueError("pair checkpoint is extra or has an undefined estimand")
        for field in (
            "grid_state",
            "power_probability",
            "workload_probability",
            "right_censored",
            "boundary_state_status",
            "terminal_period_completed",
            "require_terminal_event_inactive",
        ):
            if checkpoint[field] != required_expected[key][field]:
                raise ValueError(f"final pair expected {field} drifted")
    required_order = [key for key in expected_order if key in required_expected]
    observed_pair_order = [
        _pair_key(checkpoint) for checkpoint in (*finite_checkpoints, *E0_checkpoints)
    ]
    if set(observed_pair_order) != set(required_order):
        raise ValueError("final pair checkpoint inventory is missing or extra")
    observed_checkpoint_paths = {
        path.relative_to(directory).as_posix()
        for path in package_files
        if path.is_relative_to(directory / "checkpoints")
    }
    if declared_checkpoint_paths != observed_checkpoint_paths:
        raise ValueError("checkpoint inventory is missing or extra")
    expected_training = {
        "schema": "four_arm_training_status",
        "cells": [
            {
                "cell_id": checkpoint["cell_id"],
                "disposition": checkpoint["disposition"],
                "arms": checkpoint["four_arm_training_status"],
            }
            for checkpoint in planning_checkpoints
        ],
    }
    expected_minimum = {
        "schema": "four_arm_minimum_flexibility",
        "cells": [
            {
                "cell_id": checkpoint["cell_id"],
                "disposition": checkpoint["disposition"],
                "arms": checkpoint["four_arm_minimum_flexibility"],
            }
            for checkpoint in planning_checkpoints
        ],
    }
    expected_finite = {
        "schema": "four_arm_pairwise_outcomes",
        "pairs": finite_checkpoints,
    }
    e0_mass_by_cell = {
        cell_id: fsum(
            float(expected[key]["power_probability"])
            * float(expected[key]["workload_probability"])
            for key in expected_order
            if key[0] == cell_id and expected[key]["grid_state"] == E0_GRID_STATE
        )
        for cell_id in cells
    }
    public_e0_mass = e0_mass_by_cell[cells[0]]
    if any(
        abs(mass - public_e0_mass) > PROBABILITY_TOLERANCE
        for mass in e0_mass_by_cell.values()
    ):
        raise ValueError("final E0 marginal mass drifted across cells")
    expected_E0 = {
        "schema": "E0_outcomes",
        "pairs": E0_checkpoints,
        "unconditional_probability_mass_by_cell": e0_mass_by_cell,
        "public_marginal_mass_once": public_e0_mass,
    }
    for name, expected_summary in (
        ("four_arm_training_status", expected_training),
        ("four_arm_minimum_flexibility", expected_minimum),
        ("four_arm_pairwise_outcomes", expected_finite),
        ("E0_outcomes", expected_E0),
    ):
        observed_summary = json.loads(
            (directory / f"{name}.json").read_text(encoding="utf-8")
        )
        if observed_summary != expected_summary:
            raise ValueError(f"{name} does not match checkpoint inventory")
    identities = {
        _canonical_bytes(checkpoint["resume_identity"])
        for checkpoint in (
            *planning_checkpoints,
            *finite_checkpoints,
            *E0_checkpoints,
        )
    }
    if len(identities) != 1:
        raise ValueError("final package contains mixed resume identities")
    package_provenance = json.loads(
        (directory / "provenance.json").read_text(encoding="utf-8")
    )
    if set(package_provenance) != {
        "schema",
        "resume_identity",
        "source_provenance",
        "formal_result",
        "claim",
    }:
        raise ValueError("package provenance inventory drifted")
    if (
        package_provenance["schema"] != "provenance"
        or package_provenance["formal_result"] is not False
        or package_provenance["claim"] is not False
        or _canonical_bytes(package_provenance["resume_identity"]) not in identities
    ):
        raise ValueError("package provenance semantics drifted")
    validate_resume_identity(package_provenance["resume_identity"])
    source_provenance = _mapping(
        package_provenance["source_provenance"], "source provenance"
    )
    source_provenance_bytes = _canonical_bytes(source_provenance)
    for checkpoint in (
        *planning_checkpoints,
        *finite_checkpoints,
        *E0_checkpoints,
    ):
        if _canonical_bytes(checkpoint["provenance"]) != source_provenance_bytes:
            raise ValueError("checkpoint provenance disagrees with package provenance")
    return {
        "schema": "rq2_baseline_package_validation_v1",
        "validation_passed": True,
        "file_count": len(files),
        "formal_result": False,
        "claim": False,
    }


def publish_final_package(
    *,
    target: Path,
    planning_checkpoint_paths: Iterable[Path],
    pair_checkpoint_paths: Iterable[Path],
    expected_cell_ids: Sequence[str],
    expected_pairs: Sequence[Mapping[str, object]],
    resume_identity: Mapping[str, object],
    provenance: Mapping[str, object],
    maximum_pairs: int | None = None,
) -> dict[str, object]:
    """Publish a complete package or return non-publishing partial progress."""

    identity = validate_resume_identity(resume_identity)
    source_provenance = dict(_mapping(provenance, "provenance"))
    provenance_bytes = _canonical_bytes(source_provenance)
    cells = tuple(_safe_component(cell, "cell_id") for cell in expected_cell_ids)
    if len(cells) != len(set(cells)) or not cells:
        raise ValueError("expected cell inventory is empty or duplicated")
    expected = _validate_expected_pairs(expected_pairs, cells)
    cell_order = {cell_id: index for index, cell_id in enumerate(cells)}
    expected_order = sorted(
        expected,
        key=lambda key: (cell_order[key[0]], key[1], key[2]),
    )
    planning_by_cell = {}
    for path in planning_checkpoint_paths:
        checkpoint = validate_planning_checkpoint(_load_checkpoint(path))
        cell_id = str(checkpoint["cell_id"])
        if cell_id in planning_by_cell:
            raise ValueError("duplicate planning checkpoint")
        if checkpoint["resume_identity"] != identity:
            raise ValueError("planning resume identity drifted")
        if _canonical_bytes(checkpoint["provenance"]) != provenance_bytes:
            raise ValueError("planning checkpoint provenance drifted")
        planning_by_cell[cell_id] = checkpoint
    if set(planning_by_cell) != set(cells):
        raise ValueError("planning checkpoint inventory is missing or extra")
    if any(item["disposition"] == "unresolved" for item in planning_by_cell.values()):
        raise ValueError("unresolved planning checkpoint blocks publication")
    training_inventories = {
        _canonical_bytes(item["training_pair_inventory"])
        for item in planning_by_cell.values()
    }
    if len(training_inventories) != 1:
        raise ValueError("training Cartesian inventory drifted across cells")
    required_expected = {
        key: item
        for key, item in expected.items()
        if planning_by_cell[key[0]]["disposition"] == "resolved"
    }
    pair_by_key = {}
    for path in pair_checkpoint_paths:
        checkpoint = _load_checkpoint(path)
        schema = checkpoint.get("schema")
        if schema == FINITE_PAIR_CHECKPOINT_SCHEMA:
            checkpoint = validate_finite_pair_checkpoint(checkpoint)
        elif schema == E0_CHECKPOINT_SCHEMA:
            checkpoint = validate_E0_pair_checkpoint(checkpoint)
        else:
            raise ValueError("unknown pair checkpoint schema")
        key = _pair_key(checkpoint)
        if key in pair_by_key:
            raise ValueError("duplicate pair checkpoint")
        if key not in required_expected:
            raise ValueError("extra pair checkpoint")
        if checkpoint["resume_identity"] != identity:
            raise ValueError("pair resume identity drifted")
        if _canonical_bytes(checkpoint["provenance"]) != provenance_bytes:
            raise ValueError("pair checkpoint provenance drifted")
        expected_item = required_expected[key]
        for field in (
            "grid_state",
            "power_probability",
            "workload_probability",
            "right_censored",
            "boundary_state_status",
            "terminal_period_completed",
            "require_terminal_event_inactive",
        ):
            if checkpoint[field] != expected_item[field]:
                raise ValueError(f"pair expected {field} drifted")
        if schema == FINITE_PAIR_CHECKPOINT_SCHEMA and any(
            arm["raw_causal_policy_outcome"].get("resolved") is not True
            or arm["registered_service_risk_outcome"].get("resolved") is not True
            for arm in checkpoint["arms"]
        ):
            raise ValueError("unresolved finite arm outcome blocks publication")
        if schema == FINITE_PAIR_CHECKPOINT_SCHEMA:
            planned_capacities = {
                arm["arm_id"]: arm["minimum_capacity"]
                for arm in planning_by_cell[key[0]]["four_arm_minimum_flexibility"]
            }
            for arm in checkpoint["arms"]:
                if arm["committed_capacity"] != planned_capacities[arm["arm_id"]]:
                    raise ValueError(
                        "finite pair committed capacity disagrees with planning"
                    )
        if schema == E0_CHECKPOINT_SCHEMA and checkpoint["resolved"] is not True:
            raise ValueError("unresolved E0 checkpoint blocks publication")
        pair_by_key[key] = checkpoint
    if maximum_pairs is not None:
        if (
            isinstance(maximum_pairs, bool)
            or not isinstance(maximum_pairs, int)
            or maximum_pairs < 0
        ):
            raise ValueError("maximum_pairs must be a nonnegative integer")
        if len(pair_by_key) > maximum_pairs:
            raise ValueError("observed pairs exceed maximum_pairs")
        if maximum_pairs < len(required_expected):
            _assert_safe_path_components(target)
            if target.exists():
                raise FileExistsError(f"partial progress cannot use target {target}")
            return {
                "schema": "rq2_baseline_package_progress_v1",
                "published": False,
                "completed_pairs": len(pair_by_key),
                "required_pairs": len(required_expected),
                "maximum_pairs": maximum_pairs,
                "formal_result": False,
                "claim": False,
            }
    if set(pair_by_key) != set(required_expected):
        raise ValueError("pair checkpoint inventory is missing or extra")
    _assert_safe_path_components(target)
    if target.exists():
        raise FileExistsError(f"final package target already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    _assert_safe_path_components(target.parent)
    staging = target.with_name(f".{target.name}.staging-{uuid.uuid4().hex}")
    lock = target.with_name(f".{target.name}.publish.lock")
    lock_descriptor: int | None = None
    try:
        _assert_safe_path_components(lock)
        _assert_safe_path_components(staging)
        lock_descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
        if target.exists():
            raise FileExistsError(f"final package target already exists: {target}")
        staging.mkdir()
        planning_order = [planning_by_cell[cell] for cell in cells]
        finite = [
            pair_by_key[key]
            for key in expected_order
            if key in required_expected
            and expected[key]["grid_state"] == FINITE_GRID_NEED
        ]
        e0 = [
            pair_by_key[key]
            for key in expected_order
            if key in required_expected and expected[key]["grid_state"] == E0_GRID_STATE
        ]
        e0_mass_by_cell = {
            cell_id: fsum(
                float(expected[key]["power_probability"])
                * float(expected[key]["workload_probability"])
                for key in expected_order
                if key[0] == cell_id
                and expected[key]["grid_state"] == E0_GRID_STATE
            )
            for cell_id in cells
        }
        public_e0_mass = e0_mass_by_cell[cells[0]]
        if any(
            abs(mass - public_e0_mass) > PROBABILITY_TOLERANCE
            for mass in e0_mass_by_cell.values()
        ):
            raise ValueError("E0 marginal mass drifted across cells")
        _write_json(
            staging / "four_arm_training_status.json",
            {
                "schema": "four_arm_training_status",
                "cells": [
                    {
                        "cell_id": item["cell_id"],
                        "disposition": item["disposition"],
                        "arms": item["four_arm_training_status"],
                    }
                    for item in planning_order
                ],
            },
        )
        _write_json(
            staging / "four_arm_minimum_flexibility.json",
            {
                "schema": "four_arm_minimum_flexibility",
                "cells": [
                    {
                        "cell_id": item["cell_id"],
                        "disposition": item["disposition"],
                        "arms": item["four_arm_minimum_flexibility"],
                    }
                    for item in planning_order
                ],
            },
        )
        _write_json(
            staging / "four_arm_pairwise_outcomes.json",
            {"schema": "four_arm_pairwise_outcomes", "pairs": finite},
        )
        _write_json(
            staging / "E0_outcomes.json",
            {
                "schema": "E0_outcomes",
                "pairs": e0,
                "unconditional_probability_mass_by_cell": e0_mass_by_cell,
                "public_marginal_mass_once": public_e0_mass,
            },
        )
        checkpoint_inventory = {
            "probability_tolerance": PROBABILITY_TOLERANCE,
            "expected_pairs": [expected[key] for key in expected_order],
            "planning": [],
            "pairs": [],
        }
        for cell_id in cells:
            relative = f"checkpoints/planning/{cell_id}.json"
            destination = staging.joinpath(*PurePosixPath(relative).parts)
            _write_json(destination, planning_by_cell[cell_id])
            checkpoint_inventory["planning"].append(
                {"cell_id": cell_id, "path": relative, "sha256": _digest_file(destination)}
            )
        for key in expected_order:
            if key not in required_expected:
                continue
            relative = "checkpoints/pairs/" + "__".join(key) + ".json"
            destination = staging.joinpath(*PurePosixPath(relative).parts)
            _write_json(destination, pair_by_key[key])
            checkpoint_inventory["pairs"].append(
                {
                    "cell_id": key[0],
                    "power_block_id": key[1],
                    "workload_block_id": key[2],
                    "grid_state": expected[key]["grid_state"],
                    "path": relative,
                    "sha256": _digest_file(destination),
                }
            )
        _write_json(
            staging / "checkpoint_inventory.json",
            {"schema": "checkpoint_inventory", **checkpoint_inventory},
        )
        _write_json(
            staging / "provenance.json",
            {
                "schema": "provenance",
                "resume_identity": identity,
                "source_provenance": source_provenance,
                "formal_result": False,
                "claim": False,
            },
        )
        _write_json(
            staging / "SHA256SUMS.json",
            {"schema": PACKAGE_MANIFEST_SCHEMA, "files": _exact_manifest(staging)},
        )
        validate_final_package(staging)
        os.rename(staging, target)
        validated = validate_final_package(target)
        return {
            "schema": "rq2_baseline_package_publication_v1",
            "published": True,
            "target": str(target),
            "completed_pairs": len(pair_by_key),
            "required_pairs": len(required_expected),
            "manifest_sha256": _digest_file(target / "SHA256SUMS.json"),
            "validation": validated,
            "formal_result": False,
            "claim": False,
        }
    finally:
        if lock_descriptor is not None:
            os.close(lock_descriptor)
            lock.unlink(missing_ok=True)
        if os.path.lexists(staging):
            if _path_is_reparse(staging):
                raise RuntimeError("staging path became a reparse point; cleanup refused")
            shutil.rmtree(staging)
