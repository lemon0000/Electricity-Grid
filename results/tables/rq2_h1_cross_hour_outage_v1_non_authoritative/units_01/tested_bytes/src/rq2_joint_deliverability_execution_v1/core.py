"""Fail-closed persistence and replay primitives for RQ2 execution.

This module does not authorize or start a formal run. It provides the
platform-neutral evidence layer used by a future, separately activated runner.
"""

from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import math
import os
import re
import stat
import tempfile
import tracemalloc
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass
from importlib.metadata import version
from pathlib import Path
from typing import Any

import numpy as np
import yaml
from pyomo.environ import Constraint, Objective, Var, value
from pyomo.opt import SolverStatus, TerminationCondition

from src.rq2_joint_deliverability_v2.evaluation import (
    REGISTERED_METRICS,
    bootstrap_draw_stream,
    bootstrap_raw_draw_stream,
    canonical_certificate_payload,
    certify_scalar_transport,
    execute_holdout_policy,
    finite_conditioning,
)
from src.rq2_joint_deliverability_v2.model import (
    FOUR_ARM_IDS,
    NETWORK_ONLY_SHARED,
    ArmPlanningCertificate,
    JointDeliverabilityPlanningInputs,
    build_arm_planning_model,
)
from src.rq2_joint_deliverability_v2.scenarios import (
    PowerBlock,
    RegisteredCell,
    WorkloadBlock,
    build_pair_scenario,
    condition_finite_power,
    expand_registered_cells,
)
from src.rq2_joint_deliverability_v2.solver_adapter import (
    Rq2SolverSpec,
    create_solver,
    model_scale,
    solver_options,
    solver_spec,
)

_SAFE_COMPONENT = re.compile(r"[A-Za-z0-9_.-]+")
_HEX_DIGEST = re.compile(r"[0-9a-f]{64}")
_OPTIMAL = {
    TerminationCondition.optimal,
    TerminationCondition.globallyOptimal,
}
_PROVEN_INFEASIBLE = {TerminationCondition.infeasible}
_SOLVER_PACKAGE = {"gurobi": "gurobipy", "highs": "highspy"}
_TRANSPORT_SOLVER_STATUS = (
    "Optimization terminated successfully. (HiGHS Status 7: Optimal)"
)
_WINDOWS_GENERIC_READ = 0x80000000
_WINDOWS_GENERIC_WRITE = 0x40000000
_GRID_BLOCK_FIELDS = (
    "block_id",
    "split",
    "block_probability",
    "outage_seed",
    "hour_offset",
    "source_hour",
    "timestamp",
    "system_load_mw",
    "cfe_call_fraction",
    "active_event_id",
    "active_component_type",
    "active_component_uid",
)
_GRID_OUTPUT_FIELDS = (
    *_GRID_BLOCK_FIELDS,
    "grid_need_mw",
    "grid_need_fraction",
    "dispatch_resolved",
    "dispatch_proven_infeasible",
    "dispatch_state",
    "dispatch_objective_incumbent_mw",
    "dispatch_lower_bound_mw",
    "dispatch_upper_bound_mw",
    "dispatch_absolute_gap_mw",
    "dispatch_relative_gap",
    "dispatch_gap_tolerance_mw",
    "dispatch_model_variables",
    "dispatch_model_constraints",
    "zero_dc_confirmation_termination_condition",
    "zero_dc_confirmation_solver_status",
    "zero_dc_confirmation_lower_bound_mw",
    "zero_dc_confirmation_upper_bound_mw",
    "zero_dc_confirmation_absolute_gap_mw",
    "zero_dc_confirmation_model_variables",
    "zero_dc_confirmation_model_constraints",
    "dispatch_termination_condition",
    "dispatch_solver_status",
    "maximum_constraint_violation",
)
_GRID_CHECKPOINT_STRING_FIELDS = frozenset(
    {
        *_GRID_BLOCK_FIELDS,
        "dispatch_resolved",
        "dispatch_proven_infeasible",
        "dispatch_state",
        "zero_dc_confirmation_termination_condition",
        "zero_dc_confirmation_solver_status",
        "dispatch_termination_condition",
        "dispatch_solver_status",
    }
)
_GRID_CHECKPOINT_FLOAT_FIELDS = frozenset(
    {
        "grid_need_mw",
        "grid_need_fraction",
        "dispatch_objective_incumbent_mw",
        "dispatch_lower_bound_mw",
        "dispatch_upper_bound_mw",
        "dispatch_absolute_gap_mw",
        "dispatch_relative_gap",
        "dispatch_gap_tolerance_mw",
        "zero_dc_confirmation_lower_bound_mw",
        "zero_dc_confirmation_upper_bound_mw",
        "zero_dc_confirmation_absolute_gap_mw",
        "maximum_constraint_violation",
    }
)
_GRID_CHECKPOINT_INTEGER_FIELDS = frozenset(
    {
        "dispatch_model_variables",
        "dispatch_model_constraints",
        "zero_dc_confirmation_model_variables",
        "zero_dc_confirmation_model_constraints",
    }
)
_GRID_PACKAGE_MEMBERS = {
    "block_status.csv.gz",
    "checkpoint_inventory.json",
    "config.yaml",
    "dispatched_power_system_blocks.csv.gz",
    "holdout_marginal.csv.gz",
    "provenance.json",
    "summary.json",
    "training_marginal.csv.gz",
}
_GRID_SUMMARY_FIELDS = {
    "schema",
    "config_sha256",
    "stage_base_provenance_sha256",
    "provenance_sha256",
    "checkpoint_inventory_sha256",
    "input_manifest_sha256",
    "block_count",
    "training_block_count",
    "holdout_block_count",
    "all_blocks_resolved",
    "finite_grid_need_scope",
    "exogenous_grid_infeasibility_block_count",
    "exogenous_grid_infeasibility_hour_count",
    "exogenous_grid_infeasibility_has_finite_grid_need",
    "solver_name",
    "normal_scuc_model_scales",
    "corrective_lp_model_scales",
    "formal_execution_authorized",
    "empirical_outage_probability_claimed",
    "full_N_minus_one",
    "AC_security",
    "security_certified",
}
_GRID_NEED_SCOPE = (
    "sampled_N_minus_one_hourly_minimum_POI_curtailment_against_fixed_normal_"
    "commitment_and_dispatch_DC_not_empirical_not_AC_not_security_certification"
)
_GRID_NUMERIC_SERIALIZATION_TOLERANCE = 1.0e-12
_FINITE_GRID_NEED = "finite_grid_need"
_EXOGENOUS_GRID_INFEASIBILITY = "exogenous_grid_infeasibility"
_REGISTERED_BOOTSTRAP_CONTRACT_SHA256 = (
    "e394ff33dd8b0ce522fcd8041d9d46022c893f10f577b5073223fd7fdf81b1df"
)
_EXECUTION_CONFIG_RELATIVE = (
    "configs/rq2_joint_deliverability_execution_successor_v1.yaml"
)
_EXECUTION_OUTER_RELATIVE = (
    "configs/rq2_joint_deliverability_execution_successor_v1.OUTER.SHA256SUMS.json"
)
_EXECUTION_REVIEW_RELATIVE = (
    "configs/rq2_joint_deliverability_execution_review_pass_v1.yaml"
)
_SCIENTIFIC_CONFIG_RELATIVE = (
    "configs/rq2_joint_deliverability_preregistration_successor_v5.yaml"
)
_REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


class ExecutionEvidenceError(RuntimeError):
    """Base class for fail-closed execution evidence errors."""


class ExecutionBlocked(ExecutionEvidenceError):
    """Raised when a required external authority is not yet available."""


class EvidenceDrift(ExecutionEvidenceError):
    """Raised when immutable evidence differs from existing evidence."""


def canonical_json_bytes(payload: object) -> bytes:
    """Serialize one authoritative JSON payload."""

    return (
        json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
        )
        + "\n"
    ).encode("utf-8")


def canonical_sha256(payload: object) -> str:
    return hashlib.sha256(canonical_json_bytes(payload)).hexdigest()


def _provenance_sha256(payload: object) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _is_reparse(info: os.stat_result) -> bool:
    attributes = int(getattr(info, "st_file_attributes", 0))
    reparse_flag = int(getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400))
    return bool(attributes & reparse_flag)


def _reject_alias(path: Path) -> None:
    info = os.lstat(path)
    if stat.S_ISLNK(info.st_mode) or _is_reparse(info):
        raise ExecutionEvidenceError(f"symlink or reparse path rejected: {path}")


def require_safe_existing(path: Path, *, directory: bool) -> None:
    """Reject aliases in every existing path component."""

    absolute = path.absolute()
    current = Path(absolute.anchor)
    for component in absolute.parts[1:]:
        current = current / component
        if not os.path.lexists(current):
            raise ExecutionEvidenceError(f"required path is absent: {current}")
        _reject_alias(current)
    info = os.lstat(absolute)
    expected = stat.S_ISDIR(info.st_mode) if directory else stat.S_ISREG(info.st_mode)
    if not expected:
        kind = "directory" if directory else "regular file"
        raise ExecutionEvidenceError(f"path is not a {kind}: {absolute}")


def _read_regular_bytes(path: Path) -> bytes:
    """Read one regular file through a stable descriptor and reject path swaps."""

    require_safe_existing(path, directory=False)
    before = os.lstat(path)
    try:
        with path.open("rb") as handle:
            opened_before = os.fstat(handle.fileno())
            if not stat.S_ISREG(opened_before.st_mode) or not os.path.samestat(
                before,
                opened_before,
            ):
                raise EvidenceDrift(
                    f"regular file identity changed before read: {path}"
                )
            payload = handle.read()
            opened_after = os.fstat(handle.fileno())
    except OSError as error:
        raise ExecutionEvidenceError(f"cannot read regular file: {path}") from error
    require_safe_existing(path, directory=False)
    after = os.lstat(path)
    stable_metadata = (
        opened_before.st_size == opened_after.st_size == len(payload)
        and opened_before.st_mtime_ns == opened_after.st_mtime_ns
        and opened_before.st_ctime_ns == opened_after.st_ctime_ns
    )
    if (
        not stable_metadata
        or not stat.S_ISREG(after.st_mode)
        or _is_reparse(after)
        or not os.path.samestat(opened_after, after)
    ):
        raise EvidenceDrift(f"regular file changed during read: {path}")
    return payload


def sha256_file(path: Path) -> str:
    """Hash the bytes from one stable regular-file read."""

    return hashlib.sha256(_read_regular_bytes(path)).hexdigest()


def _safe_component(value: str, label: str) -> str:
    if not value or _SAFE_COMPONENT.fullmatch(value) is None:
        raise ValueError(f"{label} is not a safe path component")
    return value


def _json_bytes(payload_bytes: bytes, *, label: str) -> Any:
    def reject_duplicate_keys(
        pairs: list[tuple[str, object]],
    ) -> dict[str, object]:
        result: dict[str, object] = {}
        for key, value_ in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON object key: {key}")
            result[key] = value_
        return result

    def reject_nonfinite_constant(constant: str) -> None:
        raise ValueError(f"non-finite JSON number: {constant}")

    def parse_finite_float(raw: str) -> float:
        value_ = float(raw)
        if not math.isfinite(value_):
            raise ValueError(f"non-finite JSON number: {raw}")
        return value_

    try:
        return json.loads(
            payload_bytes,
            object_pairs_hook=reject_duplicate_keys,
            parse_constant=reject_nonfinite_constant,
            parse_float=parse_finite_float,
        )
    except (UnicodeError, ValueError) as error:
        raise ExecutionEvidenceError(f"invalid JSON: {label}") from error


def _json_bytes_mapping(payload_bytes: bytes, *, label: str) -> dict[str, Any]:
    payload = _json_bytes(payload_bytes, label=label)
    if not isinstance(payload, dict):
        raise ExecutionEvidenceError(f"JSON authority is not an object: {label}")
    return payload


def _json_mapping(path: Path) -> dict[str, Any]:
    return _json_bytes_mapping(_read_regular_bytes(path), label=str(path))


def _snapshot_flat_package(
    package: Path,
    *,
    manifest_name: str,
    expected_manifest_sha256: str,
    required_members: set[str] | None = None,
) -> tuple[dict[str, str], dict[str, bytes]]:
    """Read and verify one exact flat package into an immutable byte snapshot."""

    require_safe_existing(package, directory=True)
    package_before = os.lstat(package)
    manifest = package / manifest_name
    manifest_bytes = _read_regular_bytes(manifest)
    if hashlib.sha256(manifest_bytes).hexdigest() != expected_manifest_sha256:
        raise EvidenceDrift(f"package manifest SHA-256 drifted: {manifest}")
    payload = _json_bytes_mapping(
        manifest_bytes,
        label=f"package manifest: {manifest}",
    )
    if not payload or any(
        not isinstance(name, str)
        or "/" in name
        or "\\" in name
        or not isinstance(digest, str)
        or _HEX_DIGEST.fullmatch(digest) is None
        for name, digest in payload.items()
    ):
        raise ExecutionEvidenceError(f"invalid package manifest: {manifest}")
    if required_members is not None and set(payload) != required_members:
        raise EvidenceDrift(f"package manifest member set drifted: {manifest}")
    observed = set()
    for child in package.iterdir():
        _reject_alias(child)
        if not child.is_file():
            raise ExecutionEvidenceError(f"nested package member rejected: {child}")
        observed.add(child.name)
    expected = set(payload) | {manifest_name}
    if observed != expected:
        raise EvidenceDrift(f"package inventory drifted: {package}")
    snapshots: dict[str, bytes] = {}
    for name, expected_digest in payload.items():
        member = package / name
        member_bytes = _read_regular_bytes(member)
        if hashlib.sha256(member_bytes).hexdigest() != expected_digest:
            raise EvidenceDrift(f"package member SHA-256 drifted: {member}")
        snapshots[str(name)] = member_bytes
    observed_after = set()
    for child in package.iterdir():
        _reject_alias(child)
        if not child.is_file():
            raise ExecutionEvidenceError(f"nested package member rejected: {child}")
        observed_after.add(child.name)
    package_after = os.lstat(package)
    if (
        observed_after != expected
        or not os.path.samestat(package_before, package_after)
        or not stat.S_ISDIR(package_after.st_mode)
        or _is_reparse(package_after)
    ):
        raise EvidenceDrift(f"package changed during snapshot: {package}")
    return (
        {str(name): str(digest) for name, digest in payload.items()},
        snapshots,
    )


def verify_flat_manifest(
    package: Path,
    *,
    manifest_name: str,
    expected_manifest_sha256: str,
    required_members: set[str] | None = None,
) -> dict[str, str]:
    """Verify an exact flat package inventory and all member hashes."""

    members, _snapshots = _snapshot_flat_package(
        package,
        manifest_name=manifest_name,
        expected_manifest_sha256=expected_manifest_sha256,
        required_members=required_members,
    )
    return members


def verify_outer_chain(
    root: Path,
    outer_relative: str,
    *,
    expected_outer_sha256: str | None = None,
) -> dict[str, object]:
    """Verify outer, inner, and every recursively bound regular-file member."""

    outer_path = root / outer_relative
    outer_bytes = _read_regular_bytes(outer_path)
    outer_sha256 = hashlib.sha256(outer_bytes).hexdigest()
    if expected_outer_sha256 is not None and outer_sha256 != expected_outer_sha256:
        raise EvidenceDrift(f"outer manifest SHA-256 drifted: {outer_relative}")
    outer = _json_bytes_mapping(
        outer_bytes,
        label=f"outer manifest: {outer_relative}",
    )
    inner_identity = outer.get("inner")
    if (
        not isinstance(inner_identity, Mapping)
        or set(inner_identity) != {"path", "sha256"}
        or not isinstance(inner_identity["path"], str)
        or not isinstance(inner_identity["sha256"], str)
        or _HEX_DIGEST.fullmatch(inner_identity["sha256"]) is None
    ):
        raise ExecutionEvidenceError(f"outer manifest is malformed: {outer_relative}")
    inner_path = root / inner_identity["path"]
    inner_bytes = _read_regular_bytes(inner_path)
    if hashlib.sha256(inner_bytes).hexdigest() != inner_identity["sha256"]:
        raise EvidenceDrift(f"inner manifest SHA-256 drifted: {inner_path}")
    inner = _json_bytes_mapping(
        inner_bytes,
        label=f"inner manifest: {inner_path}",
    )
    members = inner.get("files")
    if not isinstance(members, Mapping) or not members:
        raise ExecutionEvidenceError(f"inner manifest is malformed: {inner_path}")
    for relative, expected in members.items():
        if (
            not isinstance(relative, str)
            or not isinstance(expected, str)
            or _HEX_DIGEST.fullmatch(expected) is None
        ):
            raise ExecutionEvidenceError(f"inner member is malformed: {inner_path}")
        member = root / relative
        member_bytes = _read_regular_bytes(member)
        if hashlib.sha256(member_bytes).hexdigest() != expected:
            raise EvidenceDrift(f"sealed member SHA-256 drifted: {relative}")
    return {
        "outer_path": outer_relative,
        "outer_sha256": outer_sha256,
        "inner_path": inner_identity["path"],
        "inner_sha256": inner_identity["sha256"],
        "member_count": len(members),
    }


def _sealed_yaml_member(
    root: Path,
    *,
    outer_relative: str,
    member_relative: str,
    expected_outer_sha256: str,
) -> dict[str, object]:
    """Parse the same member bytes whose digest is checked against a sealed outer."""

    outer_path = root / outer_relative
    outer_bytes = _read_regular_bytes(outer_path)
    if hashlib.sha256(outer_bytes).hexdigest() != expected_outer_sha256:
        raise EvidenceDrift(f"outer manifest SHA-256 drifted: {outer_relative}")
    outer = _json_bytes_mapping(
        outer_bytes,
        label=f"outer manifest: {outer_path}",
    )
    inner_identity = outer.get("inner") if isinstance(outer, Mapping) else None
    if (
        not isinstance(inner_identity, Mapping)
        or not isinstance(inner_identity.get("path"), str)
        or not isinstance(inner_identity.get("sha256"), str)
        or _HEX_DIGEST.fullmatch(inner_identity["sha256"]) is None
    ):
        raise ExecutionEvidenceError(f"outer manifest is malformed: {outer_relative}")
    inner_path = root / inner_identity["path"]
    inner_bytes = _read_regular_bytes(inner_path)
    if hashlib.sha256(inner_bytes).hexdigest() != inner_identity["sha256"]:
        raise EvidenceDrift(f"inner manifest SHA-256 drifted: {inner_path}")
    inner = _json_bytes_mapping(
        inner_bytes,
        label=f"inner manifest: {inner_path}",
    )
    members = inner.get("files") if isinstance(inner, Mapping) else None
    if not isinstance(members, Mapping) or member_relative not in members:
        raise EvidenceDrift(f"sealed member is absent: {member_relative}")
    selected: bytes | None = None
    for relative, expected_sha256 in members.items():
        if (
            not isinstance(relative, str)
            or not isinstance(expected_sha256, str)
            or _HEX_DIGEST.fullmatch(expected_sha256) is None
        ):
            raise ExecutionEvidenceError(f"inner manifest is malformed: {inner_path}")
        member_path = root / relative
        member_bytes = _read_regular_bytes(member_path)
        if hashlib.sha256(member_bytes).hexdigest() != expected_sha256:
            raise EvidenceDrift(f"sealed member SHA-256 drifted: {relative}")
        if relative == member_relative:
            selected = member_bytes
    assert selected is not None
    try:
        payload = yaml.safe_load(selected.decode("utf-8"))
    except (UnicodeError, yaml.YAMLError) as error:
        raise ExecutionEvidenceError(
            f"sealed YAML member is invalid: {member_relative}"
        ) from error
    if not isinstance(payload, dict):
        raise ExecutionEvidenceError(
            f"sealed YAML member is not a mapping: {member_relative}"
        )
    return payload


@dataclass(frozen=True)
class SplitInventory:
    training_ids: tuple[str, ...]
    holdout_ids: tuple[str, ...]
    training_source_values: tuple[int, ...]
    holdout_source_values: tuple[int, ...]


def power_block_inventory_sha256(blocks: Sequence[PowerBlock]) -> str:
    ordered = sorted(blocks, key=lambda block: block.block_id.encode())
    if len({block.block_id for block in ordered}) != len(ordered):
        raise EvidenceDrift("power block identity is duplicated")
    return canonical_sha256([asdict(block) for block in ordered])


def workload_block_inventory_sha256(blocks: Sequence[WorkloadBlock]) -> str:
    ordered = sorted(blocks, key=lambda block: block.block_id.encode())
    if len({block.block_id for block in ordered}) != len(ordered):
        raise EvidenceDrift("workload block identity is duplicated")
    return canonical_sha256([asdict(block) for block in ordered])


def _gzip_csv_rows(
    payload: bytes,
    *,
    label: str,
    exact_fields: Sequence[str] | None = None,
    required_fields: set[str] | None = None,
) -> list[dict[str, str]]:
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(payload), mode="rb") as compressed:
            text = io.TextIOWrapper(compressed, encoding="utf-8", newline="")
            reader = csv.DictReader(text)
            if (
                not reader.fieldnames
                or any(not field for field in reader.fieldnames)
                or len(set(reader.fieldnames)) != len(reader.fieldnames)
            ):
                raise EvidenceDrift(f"CSV header drifted: {label}")
            if exact_fields is not None and reader.fieldnames != list(exact_fields):
                raise EvidenceDrift(f"CSV schema drifted: {label}")
            if required_fields is not None and (
                not required_fields.issubset(reader.fieldnames)
            ):
                raise ExecutionEvidenceError(f"hourly schema drifted: {label}")
            rows: list[dict[str, str]] = []
            for row in reader:
                if None in row or any(value_ is None for value_ in row.values()):
                    raise EvidenceDrift(f"CSV row width drifted: {label}")
                rows.append({str(key): str(value_) for key, value_ in row.items()})
            return rows
    except (OSError, EOFError, UnicodeError) as error:
        raise ExecutionEvidenceError(f"invalid gzip CSV: {label}") from error


def _read_marginal_bytes(payload: bytes, *, label: str) -> tuple[str, ...]:
    rows = _gzip_csv_rows(
        payload,
        label=label,
        exact_fields=("id", "probability"),
    )
    ids = []
    probabilities = []
    for row in rows:
        block_id = row["id"]
        try:
            probability = float(row["probability"])
        except (TypeError, ValueError) as error:
            raise ExecutionEvidenceError("marginal probability is invalid") from error
        if (
            not block_id
            or block_id in ids
            or not math.isfinite(probability)
            or probability < 0.0
            or probability > 1.0
        ):
            raise ExecutionEvidenceError(f"marginal row is invalid: {label}")
        ids.append(block_id)
        probabilities.append(probability)
    if not ids or not math.isclose(
        math.fsum(probabilities),
        1.0,
        rel_tol=0.0,
        abs_tol=1.0e-9,
    ):
        raise ExecutionEvidenceError(f"marginal mass drifted: {label}")
    return tuple(ids)


def _audit_split_inventory_from_snapshot(
    files: Mapping[str, bytes],
    *,
    hourly_file: str,
    source_field: str,
    training_blocks: int,
    holdout_blocks: int,
    label: str,
) -> SplitInventory:
    try:
        hourly_bytes = files[hourly_file]
        marginal_bytes = {
            split: files[f"{split}_marginal.csv.gz"]
            for split in ("training", "holdout")
        }
    except KeyError as error:
        raise EvidenceDrift(f"split package member is absent: {label}") from error
    grouped: dict[str, list[tuple[str, int, int]]] = {}
    rows = _gzip_csv_rows(
        hourly_bytes,
        label=f"{label}/{hourly_file}",
        required_fields={"block_id", "split", "hour_offset", source_field},
    )
    for row in rows:
        block_id = row["block_id"]
        split = row["split"]
        try:
            offset = int(row["hour_offset"])
            source_value = int(row[source_field])
        except (TypeError, ValueError) as error:
            raise ExecutionEvidenceError("hourly integer field is invalid") from error
        if (
            not block_id
            or split not in {"training", "holdout"}
            or not 0 <= offset <= 23
            or source_value < 0
        ):
            raise ExecutionEvidenceError("hourly identity field is invalid")
        grouped.setdefault(block_id, []).append((split, offset, source_value))
    by_split: dict[str, set[str]] = {"training": set(), "holdout": set()}
    source_by_split: dict[str, set[int]] = {"training": set(), "holdout": set()}
    for block_id, block_rows in grouped.items():
        splits = {split for split, _, _ in block_rows}
        offsets = {offset for _, offset, _ in block_rows}
        if len(splits) != 1:
            raise EvidenceDrift("training and holdout block IDs overlap")
        if len(block_rows) != 24 or offsets != set(range(24)):
            raise ExecutionEvidenceError(f"invalid 24-hour block: {block_id}")
        split = splits.pop()
        by_split[split].add(block_id)
        source_by_split[split].update(source for _, _, source in block_rows)
    marginal_ids = {
        split: set(
            _read_marginal_bytes(
                marginal_bytes[split],
                label=f"{label}/{split}_marginal.csv.gz",
            )
        )
        for split in ("training", "holdout")
    }
    if by_split != marginal_ids:
        raise EvidenceDrift("hourly and marginal block inventories differ")
    if (
        len(by_split["training"]) != training_blocks
        or len(by_split["holdout"]) != holdout_blocks
    ):
        raise EvidenceDrift("registered block counts drifted")
    if by_split["training"] & by_split["holdout"]:
        raise EvidenceDrift("training and holdout block IDs overlap")
    if source_by_split["training"] & source_by_split["holdout"]:
        raise EvidenceDrift("training and holdout source support overlaps")
    return SplitInventory(
        training_ids=tuple(sorted(by_split["training"], key=str.encode)),
        holdout_ids=tuple(sorted(by_split["holdout"], key=str.encode)),
        training_source_values=tuple(sorted(source_by_split["training"])),
        holdout_source_values=tuple(sorted(source_by_split["holdout"])),
    )


def _read_marginal_with_probabilities(
    payload: bytes,
    *,
    label: str,
) -> tuple[tuple[str, float], ...]:
    rows = _gzip_csv_rows(
        payload,
        label=label,
        exact_fields=("id", "probability"),
    )
    result = []
    seen: set[str] = set()
    for row in rows:
        block_id = row["id"]
        try:
            probability = float(row["probability"])
        except (TypeError, ValueError) as error:
            raise ExecutionEvidenceError("marginal probability is invalid") from error
        if (
            not block_id
            or block_id in seen
            or not math.isfinite(probability)
            or not 0.0 <= probability <= 1.0
        ):
            raise ExecutionEvidenceError(f"marginal row is invalid: {label}")
        seen.add(block_id)
        result.append((block_id, probability))
    if not result or not math.isclose(
        math.fsum(probability for _, probability in result),
        1.0,
        rel_tol=0.0,
        abs_tol=1.0e-9,
    ):
        raise ExecutionEvidenceError(f"marginal mass drifted: {label}")
    return tuple(result)


def _group_hourly_rows(
    payload: bytes,
    *,
    label: str,
    required_fields: set[str],
) -> dict[str, list[dict[str, str]]]:
    rows = _gzip_csv_rows(
        payload,
        label=label,
        required_fields=required_fields | {"block_id", "split", "hour_offset"},
    )
    grouped: dict[str, list[dict[str, str]]] = {}
    for row in rows:
        block_id = row["block_id"]
        split = row["split"]
        try:
            offset = int(row["hour_offset"])
        except (TypeError, ValueError) as error:
            raise ExecutionEvidenceError("hourly offset is invalid") from error
        if (
            not block_id
            or split not in {"training", "holdout"}
            or not 0 <= offset <= 23
        ):
            raise ExecutionEvidenceError(f"hourly identity is invalid: {label}")
        grouped.setdefault(block_id, []).append(dict(row))
    for block_id, block_rows in grouped.items():
        if (
            len(block_rows) != 24
            or {int(row["hour_offset"]) for row in block_rows} != set(range(24))
            or len({row["split"] for row in block_rows}) != 1
        ):
            raise EvidenceDrift(f"invalid 24-hour block: {block_id}")
        block_rows.sort(key=lambda row: int(row["hour_offset"]))
    return grouped


def _snapshot_power_blocks(
    files: Mapping[str, bytes],
    split: str,
) -> tuple[PowerBlock, ...]:
    if split not in {"training", "holdout"}:
        raise ValueError("power split must be training or holdout")
    marginal = _read_marginal_with_probabilities(
        files[f"{split}_marginal.csv.gz"],
        label=f"{split}_marginal.csv.gz",
    )
    grouped = _group_hourly_rows(
        files["dispatched_power_system_blocks.csv.gz"],
        label="dispatched_power_system_blocks.csv.gz",
        required_fields={
            "source_hour",
            "cfe_call_fraction",
            "grid_need_fraction",
            "dispatch_state",
        },
    )
    if {
        block_id for block_id, rows in grouped.items() if rows[0]["split"] == split
    } != {block_id for block_id, _ in marginal}:
        raise EvidenceDrift("power hourly and marginal block inventories differ")
    blocks = []
    for block_id, probability in marginal:
        rows = grouped[block_id]
        states = tuple(row["dispatch_state"] for row in rows)
        if any(
            state not in {_FINITE_GRID_NEED, _EXOGENOUS_GRID_INFEASIBILITY}
            for state in states
        ):
            raise EvidenceDrift("power block state inventory drifted")
        state = (
            _EXOGENOUS_GRID_INFEASIBILITY
            if _EXOGENOUS_GRID_INFEASIBILITY in states
            else _FINITE_GRID_NEED
        )
        grid_need = []
        for row_state, row in zip(states, rows, strict=True):
            raw = row["grid_need_fraction"]
            if row_state == _EXOGENOUS_GRID_INFEASIBILITY:
                if raw != "":
                    raise EvidenceDrift("E0 hour must have an empty grid need")
                grid_need.append(None)
            else:
                grid_need.append(
                    _finite_csv_float(
                        raw,
                        "grid_need_fraction",
                        minimum=0.0,
                        maximum=1.0,
                    )
                )
        blocks.append(
            PowerBlock(
                block_id=block_id,
                split=split,
                probability=probability,
                source_hours=tuple(int(row["source_hour"]) for row in rows),
                cfe_call_fraction_at_alpha_1=tuple(
                    _finite_csv_float(
                        row["cfe_call_fraction"],
                        "cfe_call_fraction",
                        minimum=0.0,
                        maximum=1.0,
                    )
                    for row in rows
                ),
                grid_need=tuple(grid_need),
                state=state,
            )
        )
    return tuple(blocks)


def _snapshot_workload_blocks(
    files: Mapping[str, bytes],
    split: str,
) -> tuple[WorkloadBlock, ...]:
    if split not in {"training", "holdout"}:
        raise ValueError("workload split must be training or holdout")
    marginal = _read_marginal_with_probabilities(
        files[f"{split}_marginal.csv.gz"],
        label=f"{split}_marginal.csv.gz",
    )
    grouped = _group_hourly_rows(
        files["workload_blocks.csv.gz"],
        label="workload_blocks.csv.gz",
        required_fields={"source_relative_hour", "workload_fraction"},
    )
    if {
        block_id for block_id, rows in grouped.items() if rows[0]["split"] == split
    } != {block_id for block_id, _ in marginal}:
        raise EvidenceDrift("workload hourly and marginal block inventories differ")
    return tuple(
        WorkloadBlock(
            block_id=block_id,
            split=split,
            probability=probability,
            source_relative_hours=tuple(
                int(row["source_relative_hour"]) for row in grouped[block_id]
            ),
            raw_workload_fraction=tuple(
                _finite_csv_float(
                    row["workload_fraction"],
                    "workload_fraction",
                    minimum=0.0,
                )
                for row in grouped[block_id]
            ),
        )
        for block_id, probability in marginal
    )


def audit_split_inventory(
    package: Path,
    *,
    hourly_file: str,
    source_field: str,
    training_blocks: int,
    holdout_blocks: int,
) -> SplitInventory:
    """Audit exact 24-hour blocks and physical split disjointness."""

    files = {
        hourly_file: _read_regular_bytes(package / hourly_file),
        "training_marginal.csv.gz": _read_regular_bytes(
            package / "training_marginal.csv.gz"
        ),
        "holdout_marginal.csv.gz": _read_regular_bytes(
            package / "holdout_marginal.csv.gz"
        ),
    }
    return _audit_split_inventory_from_snapshot(
        files,
        hourly_file=hourly_file,
        source_field=source_field,
        training_blocks=training_blocks,
        holdout_blocks=holdout_blocks,
        label=str(package),
    )


def _row_identity(
    row: Mapping[str, str],
    *,
    label: str,
) -> tuple[str, str, int]:
    try:
        block_id = row["block_id"]
        split = row["split"]
        hour = int(row["hour_offset"])
    except (KeyError, TypeError, ValueError) as error:
        raise EvidenceDrift(f"{label} row identity is invalid") from error
    if not block_id or split not in {"training", "holdout"} or not 0 <= hour <= 23:
        raise EvidenceDrift(f"{label} row identity is invalid")
    return block_id, split, hour


def _indexed_rows(
    rows: Sequence[Mapping[str, str]],
    *,
    label: str,
) -> dict[tuple[str, str, int], Mapping[str, str]]:
    result: dict[tuple[str, str, int], Mapping[str, str]] = {}
    for row in rows:
        identity = _row_identity(row, label=label)
        if identity in result:
            raise EvidenceDrift(f"duplicate {label} row identity")
        result[identity] = row
    return result


def _finite_csv_float(
    raw: str,
    label: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float:
    try:
        value_ = float(raw)
    except (TypeError, ValueError) as error:
        raise EvidenceDrift(f"{label} is invalid") from error
    if (
        not math.isfinite(value_)
        or (minimum is not None and value_ < minimum)
        or (maximum is not None and value_ > maximum)
    ):
        raise EvidenceDrift(f"{label} is outside its registered domain")
    return value_


def _optional_csv_float(
    raw: str,
    label: str,
    *,
    minimum: float | None = None,
    maximum: float | None = None,
) -> float | None:
    return (
        None
        if raw == ""
        else _finite_csv_float(raw, label, minimum=minimum, maximum=maximum)
    )


def _csv_nonnegative_int(raw: str, label: str) -> int:
    if re.fullmatch(r"[0-9]+", raw) is None:
        raise EvidenceDrift(f"{label} is invalid")
    return int(raw)


def _validate_bound_fields(
    row: Mapping[str, str],
    *,
    prefix: str,
    include_relative_and_tolerance: bool,
) -> tuple[float | None, float | None, float | None]:
    lower = _optional_csv_float(
        row[f"{prefix}_lower_bound_mw"],
        f"{prefix} lower",
        minimum=0.0,
    )
    upper = _optional_csv_float(
        row[f"{prefix}_upper_bound_mw"],
        f"{prefix} upper",
        minimum=0.0,
    )
    gap = _optional_csv_float(
        row[f"{prefix}_absolute_gap_mw"],
        f"{prefix} gap",
        minimum=0.0,
    )
    populated_bound_fields = sum(value is not None for value in (lower, upper, gap))
    if populated_bound_fields not in {0, 3}:
        raise EvidenceDrift(f"{prefix} bound certificate drifted")
    if populated_bound_fields == 3:
        assert lower is not None
        assert upper is not None
        assert gap is not None
        if lower > upper or not math.isclose(
            gap,
            abs(upper - lower),
            rel_tol=0.0,
            abs_tol=1.0e-12,
        ):
            raise EvidenceDrift(f"{prefix} bound certificate drifted")
    if include_relative_and_tolerance:
        relative = _optional_csv_float(
            row["dispatch_relative_gap"],
            "dispatch relative gap",
        )
        tolerance = _optional_csv_float(
            row["dispatch_gap_tolerance_mw"],
            "dispatch gap tolerance",
        )
        if upper is not None and gap is not None:
            expected_relative = gap / max(abs(upper), 1.0e-12)
            if (
                relative is None
                or tolerance is None
                or not math.isclose(
                    relative,
                    expected_relative,
                    rel_tol=0.0,
                    abs_tol=1.0e-12,
                )
            ):
                raise EvidenceDrift("dispatch relative-gap certificate drifted")
        elif relative is not None or tolerance is not None:
            raise EvidenceDrift("dispatch relative-gap certificate drifted")
    return lower, upper, gap


def _checkpoint_row_value_matches_csv(
    field: str,
    raw: str,
    value_: object,
) -> bool:
    """Match the exact built-in type and text emitted by csv.DictWriter."""

    if field in _GRID_CHECKPOINT_STRING_FIELDS:
        return isinstance(value_, str) and raw == value_
    if field in _GRID_CHECKPOINT_FLOAT_FIELDS:
        return (
            value_ == ""
            and isinstance(value_, str)
            and raw == ""
            or type(value_) is float
            and math.isfinite(value_)
            and raw == str(value_)
        )
    if field in _GRID_CHECKPOINT_INTEGER_FIELDS:
        return (
            value_ == ""
            and isinstance(value_, str)
            and raw == ""
            or type(value_) is int
            and raw == str(value_)
        )
    return False


def _json_value_matches_csv(field: str, raw: str, value_: object) -> bool:
    if value_ is None:
        return raw == ""
    return _checkpoint_row_value_matches_csv(field, raw, value_)


def _strict_nonnegative_json_float(value_: object, label: str) -> float:
    if type(value_) is not float or not math.isfinite(value_) or value_ < 0.0:
        raise EvidenceDrift(f"{label} is invalid")
    return value_


def _grid_numeric_close(left: float, right: float) -> bool:
    return math.isclose(
        left,
        right,
        rel_tol=_GRID_NUMERIC_SERIALIZATION_TOLERANCE,
        abs_tol=_GRID_NUMERIC_SERIALIZATION_TOLERANCE,
    )


def _validate_grid_minimization_certificate(
    *,
    incumbent: float,
    lower: float,
    upper: float,
    absolute_gap: float,
    relative_gap: float,
    reported_gap_tolerance: float,
    model_tolerance: float,
    configured_relative_gap: float,
    label: str,
) -> None:
    if lower > upper and not _grid_numeric_close(lower, upper):
        raise EvidenceDrift(f"{label} bound order drifted")
    if (
        incumbent < lower
        and not _grid_numeric_close(incumbent, lower)
        or incumbent > upper
        and not _grid_numeric_close(incumbent, upper)
    ):
        raise EvidenceDrift(f"{label} incumbent is outside bounds")
    recomputed_gap = upper - lower if upper >= lower else 0.0
    recomputed_relative = recomputed_gap / max(abs(upper), 1.0e-12)
    expected_gap_tolerance = max(
        model_tolerance,
        configured_relative_gap * max(abs(upper), 1.0),
    )
    if (
        not _grid_numeric_close(absolute_gap, recomputed_gap)
        or not _grid_numeric_close(relative_gap, recomputed_relative)
        or not _grid_numeric_close(
            reported_gap_tolerance,
            expected_gap_tolerance,
        )
    ):
        raise EvidenceDrift(f"{label} derived gap fields drifted")
    if (
        absolute_gap > reported_gap_tolerance
        and not _grid_numeric_close(absolute_gap, reported_gap_tolerance)
        or relative_gap > configured_relative_gap
        and not _grid_numeric_close(relative_gap, configured_relative_gap)
    ):
        raise EvidenceDrift(f"{label} exceeds its registered gap limit")


def _validate_no_event_grid_values(values: Mapping[str, float]) -> None:
    if any(value_ != 0.0 for value_ in values.values()):
        raise EvidenceDrift("no-outage dispatched-grid values must be zero")


def _validate_grid_checkpoint_baseline(
    raw: object,
    *,
    has_event: bool,
    grid_solver: Mapping[str, object],
    expected_solver_options: Mapping[str, float | int],
) -> tuple[int, int] | None:
    if not isinstance(raw, Mapping):
        raise EvidenceDrift("grid checkpoint baseline fields drifted")
    if not has_event:
        if (
            set(raw) != {"accepted", "termination_condition"}
            or raw.get("accepted") is not True
            or raw.get("termination_condition") != "not_applicable_no_active_outage"
        ):
            raise EvidenceDrift("grid checkpoint no-event baseline drifted")
        return None
    fields = {
        "accepted",
        "termination_condition",
        "solver_status",
        "solver_message",
        "objective_usd",
        "lower_bound_usd",
        "upper_bound_usd",
        "absolute_gap_usd",
        "relative_gap",
        "gap_tolerance_usd",
        "maximum_constraint_violation",
        "maximum_integrality_violation",
        "solver_threads",
        "configured_mip_relative_gap",
        "model_variables",
        "model_constraints",
        "solver_name",
        "solver_options",
    }
    threads = raw.get("solver_threads")
    variables = raw.get("model_variables")
    constraints = raw.get("model_constraints")
    options = raw.get("solver_options")
    if (
        set(raw) != fields
        or raw.get("accepted") is not True
        or raw.get("termination_condition") != "optimal"
        or raw.get("solver_status") != "ok"
        or not isinstance(raw.get("solver_message"), str)
        or not raw["solver_message"]
        or raw.get("solver_name") != grid_solver.get("name")
        or not isinstance(options, Mapping)
        or canonical_json_bytes(options)
        != canonical_json_bytes(expected_solver_options)
        or type(threads) is not int
        or threads != grid_solver.get("threads")
        or type(variables) is not int
        or variables <= 0
        or type(constraints) is not int
        or constraints <= 0
    ):
        raise EvidenceDrift("grid checkpoint baseline authority drifted")
    configured_gap = _strict_nonnegative_json_float(
        raw["configured_mip_relative_gap"],
        "grid checkpoint baseline configured gap",
    )
    frozen_gap = float(grid_solver["mip_relative_gap"])
    if configured_gap != frozen_gap:
        raise EvidenceDrift("grid checkpoint baseline configured gap drifted")
    objective = _strict_nonnegative_json_float(
        raw["objective_usd"],
        "grid checkpoint baseline objective",
    )
    lower = _strict_nonnegative_json_float(
        raw["lower_bound_usd"],
        "grid checkpoint baseline lower bound",
    )
    upper = _strict_nonnegative_json_float(
        raw["upper_bound_usd"],
        "grid checkpoint baseline upper bound",
    )
    observed_gap = _strict_nonnegative_json_float(
        raw["absolute_gap_usd"],
        "grid checkpoint baseline absolute gap",
    )
    observed_relative = _strict_nonnegative_json_float(
        raw["relative_gap"],
        "grid checkpoint baseline relative gap",
    )
    observed_tolerance = _strict_nonnegative_json_float(
        raw["gap_tolerance_usd"],
        "grid checkpoint baseline gap tolerance",
    )
    _validate_grid_minimization_certificate(
        incumbent=objective,
        lower=lower,
        upper=upper,
        absolute_gap=observed_gap,
        relative_gap=observed_relative,
        reported_gap_tolerance=observed_tolerance,
        model_tolerance=float(grid_solver["tolerance_mw"]),
        configured_relative_gap=frozen_gap,
        label="grid checkpoint baseline",
    )
    constraint_violation = _strict_nonnegative_json_float(
        raw["maximum_constraint_violation"],
        "grid checkpoint baseline constraint residual",
    )
    integrality_violation = _strict_nonnegative_json_float(
        raw["maximum_integrality_violation"],
        "grid checkpoint baseline integrality residual",
    )
    if constraint_violation > float(
        grid_solver["tolerance_mw"]
    ) or integrality_violation > float(grid_solver["integer_feasibility_tolerance"]):
        raise EvidenceDrift("grid checkpoint baseline residual drifted")
    return variables, constraints


def _e0_checkpoint_certificate_scale(
    raw: object,
    *,
    label: str,
) -> tuple[int, int]:
    fields = {
        "objective_incumbent_mw",
        "lower_bound_mw",
        "upper_bound_mw",
        "absolute_gap_mw",
        "relative_gap",
        "gap_tolerance_mw",
        "model_variables",
        "model_constraints",
    }
    if not isinstance(raw, Mapping) or set(raw) != fields:
        raise EvidenceDrift(f"{label} fields drifted")
    if any(
        raw[field] is not None
        for field in fields
        if field not in {"model_variables", "model_constraints"}
    ):
        raise EvidenceDrift(f"{label} must contain null incumbent and bounds")
    variables = raw["model_variables"]
    constraints = raw["model_constraints"]
    if (
        isinstance(variables, bool)
        or not isinstance(variables, int)
        or variables <= 0
        or isinstance(constraints, bool)
        or not isinstance(constraints, int)
        or constraints <= 0
    ):
        raise EvidenceDrift(f"{label} model scale drifted")
    return variables, constraints


def _validate_grid_checkpoint_hour(
    outcome: object,
    checkpoint_row: object,
    *,
    base_row: Mapping[str, str],
    dispatched_row: Mapping[str, str],
    expected_solver_options: Mapping[str, float | int],
) -> str:
    outcome_fields = {
        "state",
        "resolved_for_pipeline",
        "primary",
        "primary_certificate",
        "zero_dc_confirmation",
        "zero_dc_confirmation_certificate",
        "solver_name",
        "solver_options",
    }
    result_fields = {
        "source_hour",
        "event_id",
        "component_type",
        "component_uid",
        "resolved",
        "proven_infeasible",
        "grid_need_mw",
        "termination_condition",
        "solver_status",
        "maximum_constraint_violation",
    }
    certificate_fields = {
        "objective_incumbent_mw",
        "lower_bound_mw",
        "upper_bound_mw",
        "absolute_gap_mw",
        "relative_gap",
        "gap_tolerance_mw",
        "model_variables",
        "model_constraints",
    }
    if not isinstance(outcome, Mapping) or set(outcome) != outcome_fields:
        raise EvidenceDrift("grid checkpoint hourly outcome fields drifted")
    if (
        not isinstance(checkpoint_row, Mapping)
        or set(checkpoint_row) != set(_GRID_OUTPUT_FIELDS)
        or any(
            not _checkpoint_row_value_matches_csv(
                field,
                dispatched_row[field],
                checkpoint_row[field],
            )
            for field in _GRID_OUTPUT_FIELDS
        )
    ):
        raise EvidenceDrift("grid checkpoint row projection drifted")
    has_event = bool(base_row["active_event_id"])
    expected_options: Mapping[str, float | int] = (
        expected_solver_options if has_event else {}
    )
    if (
        outcome.get("state") != dispatched_row["dispatch_state"]
        or outcome.get("resolved_for_pipeline") is not True
        or outcome.get("solver_name") != "gurobi"
        or canonical_json_bytes(outcome.get("solver_options"))
        != canonical_json_bytes(expected_options)
    ):
        raise EvidenceDrift("grid checkpoint hourly authority drifted")
    primary = outcome["primary"]
    certificate = outcome["primary_certificate"]
    if (
        not isinstance(primary, Mapping)
        or set(primary) != result_fields
        or not isinstance(certificate, Mapping)
        or set(certificate) != certificate_fields
    ):
        raise EvidenceDrift("grid checkpoint primary evidence fields drifted")
    expected_metadata = {
        "source_hour": int(base_row["source_hour"]),
        "event_id": base_row["active_event_id"] or None,
        "component_type": base_row["active_component_type"] or None,
        "component_uid": base_row["active_component_uid"] or None,
    }
    observed_metadata = {field: primary.get(field) for field in expected_metadata}
    if canonical_json_bytes(observed_metadata) != canonical_json_bytes(
        expected_metadata
    ):
        raise EvidenceDrift("grid checkpoint primary metadata drifted")
    if (
        type(primary["resolved"]) is not bool
        or type(primary["proven_infeasible"]) is not bool
    ):
        raise EvidenceDrift("grid checkpoint primary outcome projection drifted")
    primary_row_fields = {
        "resolved": "dispatch_resolved",
        "proven_infeasible": "dispatch_proven_infeasible",
        "grid_need_mw": "grid_need_mw",
        "termination_condition": "dispatch_termination_condition",
        "solver_status": "dispatch_solver_status",
        "maximum_constraint_violation": "maximum_constraint_violation",
    }
    if any(
        not _json_value_matches_csv(
            row_field,
            dispatched_row[row_field],
            (
                str(primary[field]).lower()
                if field in {"resolved", "proven_infeasible"}
                else primary[field]
            ),
        )
        for field, row_field in primary_row_fields.items()
    ):
        raise EvidenceDrift("grid checkpoint primary outcome projection drifted")
    certificate_row_fields = {
        "objective_incumbent_mw": "dispatch_objective_incumbent_mw",
        "lower_bound_mw": "dispatch_lower_bound_mw",
        "upper_bound_mw": "dispatch_upper_bound_mw",
        "absolute_gap_mw": "dispatch_absolute_gap_mw",
        "relative_gap": "dispatch_relative_gap",
        "gap_tolerance_mw": "dispatch_gap_tolerance_mw",
        "model_variables": "dispatch_model_variables",
        "model_constraints": "dispatch_model_constraints",
    }
    if any(
        not _json_value_matches_csv(
            row_field,
            dispatched_row[row_field],
            certificate[field],
        )
        for field, row_field in certificate_row_fields.items()
    ):
        raise EvidenceDrift("grid checkpoint primary certificate projection drifted")
    state = str(outcome["state"])
    if state == _FINITE_GRID_NEED:
        if (
            outcome["zero_dc_confirmation"] is not None
            or outcome["zero_dc_confirmation_certificate"] is not None
        ):
            raise EvidenceDrift("finite grid checkpoint carries zero-DC evidence")
        return state
    if state != _EXOGENOUS_GRID_INFEASIBILITY:
        raise EvidenceDrift("grid checkpoint contains an unregistered state")
    if (
        primary["resolved"] is not False
        or primary["proven_infeasible"] is not True
        or primary["grid_need_mw"] is not None
        or primary["termination_condition"] != "infeasible"
        or primary["solver_status"] != "warning"
        or primary["maximum_constraint_violation"] is not None
    ):
        raise EvidenceDrift("primary E0 checkpoint outcome drifted")
    primary_scale = _e0_checkpoint_certificate_scale(
        certificate,
        label="primary E0 certificate",
    )
    zero = outcome["zero_dc_confirmation"]
    if not isinstance(zero, Mapping) or set(zero) != result_fields:
        raise EvidenceDrift("zero-DC E0 outcome fields drifted")
    zero_metadata = {field: zero.get(field) for field in expected_metadata}
    if canonical_json_bytes(zero_metadata) != canonical_json_bytes(expected_metadata):
        raise EvidenceDrift("zero-DC E0 metadata drifted")
    if (
        zero["resolved"] is not False
        or zero["proven_infeasible"] is not True
        or zero["grid_need_mw"] is not None
        or zero["termination_condition"] != "infeasible"
        or zero["solver_status"] != "warning"
        or zero["maximum_constraint_violation"] is not None
    ):
        raise EvidenceDrift("zero-DC E0 outcome drifted")
    zero_scale = _e0_checkpoint_certificate_scale(
        outcome["zero_dc_confirmation_certificate"],
        label="zero-DC E0 certificate",
    )
    if primary_scale != zero_scale:
        raise EvidenceDrift("E0 checkpoint primary and zero-DC model scale drifted")
    return state


def _audit_dispatched_grid_checkpoints(
    root: Path,
    *,
    checkpoint_directory: object,
    checkpoint_inventory: Mapping[str, object],
    base_by_id: Mapping[tuple[str, str, int], Mapping[str, str]],
    dispatched_by_id: Mapping[tuple[str, str, int], Mapping[str, str]],
    expected_stage_base_sha256: str,
    grid_solver: Mapping[str, object],
) -> tuple[tuple[int, int], ...]:
    if not isinstance(checkpoint_directory, str) or not checkpoint_directory:
        raise EvidenceDrift("dispatched grid checkpoint directory is invalid")
    relative = Path(checkpoint_directory)
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise EvidenceDrift("dispatched grid checkpoint directory escaped repository")
    directory = root / relative
    require_safe_existing(directory, directory=True)
    directory_before = os.lstat(directory)
    expected_files = {}
    for block_id in checkpoint_inventory:
        if not isinstance(block_id, str) or not block_id.replace("_", "").isalnum():
            raise EvidenceDrift("dispatched grid checkpoint block ID is unsafe")
        expected_files[f"{block_id}.json"] = block_id

    def observed_files() -> dict[str, Path]:
        observed: dict[str, Path] = {}
        for child in directory.iterdir():
            _reject_alias(child)
            if not child.is_file():
                raise EvidenceDrift("dispatched grid checkpoint directory is not flat")
            observed[child.name] = child
        return observed

    observed = observed_files()
    if set(observed) != set(expected_files):
        raise EvidenceDrift("dispatched grid checkpoint file inventory drifted")
    expected_solver_options = {
        "MIPGap": float(grid_solver["mip_relative_gap"]),
        "MIPGapAbs": 0.0,
        "Seed": int(grid_solver["random_seed"]),
        "Threads": int(grid_solver["threads"]),
        "FeasibilityTol": float(grid_solver["feasibility_tolerance"]),
        "OptimalityTol": float(grid_solver["optimality_tolerance"]),
        "IntFeasTol": float(grid_solver["integer_feasibility_tolerance"]),
    }
    if grid_solver.get("time_limit_seconds") is not None:
        expected_solver_options["TimeLimit"] = float(grid_solver["time_limit_seconds"])
    checkpoint_fields = {
        "schema",
        "stage_base_provenance_sha256",
        "block_id",
        "split",
        "baseline_audit",
        "all_hours_resolved",
        "exogenous_grid_infeasibility_hour_count",
        "outcomes",
        "rows",
    }
    normal_scuc_scales: set[tuple[int, int]] = set()
    for filename in sorted(expected_files, key=str.encode):
        block_id = expected_files[filename]
        checkpoint_bytes = _read_regular_bytes(observed[filename])
        if (
            hashlib.sha256(checkpoint_bytes).hexdigest()
            != checkpoint_inventory[block_id]
        ):
            raise EvidenceDrift("dispatched grid checkpoint digest drifted")
        checkpoint = _json_bytes_mapping(
            checkpoint_bytes,
            label=str(observed[filename]),
        )
        identities = sorted(
            (identity for identity in base_by_id if identity[0] == block_id),
            key=lambda identity: identity[2],
        )
        if len(identities) != 24 or any(
            identity not in dispatched_by_id for identity in identities
        ):
            raise EvidenceDrift("dispatched grid checkpoint block inventory drifted")
        expected_split = identities[0][1]
        baseline = checkpoint.get("baseline_audit")
        outcomes = checkpoint.get("outcomes")
        rows = checkpoint.get("rows")
        if (
            set(checkpoint) != checkpoint_fields
            or checkpoint.get("schema")
            != "rts_gmlc_public_grid_need_block_checkpoint_v4"
            or checkpoint.get("stage_base_provenance_sha256")
            != expected_stage_base_sha256
            or checkpoint.get("block_id") != block_id
            or checkpoint.get("split") != expected_split
            or not isinstance(baseline, Mapping)
            or checkpoint.get("all_hours_resolved") is not True
            or not isinstance(outcomes, list)
            or not isinstance(rows, list)
            or len(outcomes) != 24
            or len(rows) != 24
        ):
            raise EvidenceDrift("dispatched grid checkpoint authority drifted")
        baseline_scale = _validate_grid_checkpoint_baseline(
            baseline,
            has_event=any(
                bool(base_by_id[identity]["active_event_id"]) for identity in identities
            ),
            grid_solver=grid_solver,
            expected_solver_options=expected_solver_options,
        )
        if baseline_scale is not None:
            normal_scuc_scales.add(baseline_scale)
        states = [
            _validate_grid_checkpoint_hour(
                outcome,
                checkpoint_row,
                base_row=base_by_id[identity],
                dispatched_row=dispatched_by_id[identity],
                expected_solver_options=expected_solver_options,
            )
            for outcome, checkpoint_row, identity in zip(
                outcomes,
                rows,
                identities,
                strict=True,
            )
        ]
        observed_e0 = checkpoint.get("exogenous_grid_infeasibility_hour_count")
        if (
            isinstance(observed_e0, bool)
            or not isinstance(observed_e0, int)
            or observed_e0
            != sum(state == _EXOGENOUS_GRID_INFEASIBILITY for state in states)
        ):
            raise EvidenceDrift("dispatched grid checkpoint E0 count drifted")
    if set(observed_files()) != set(expected_files):
        raise EvidenceDrift("dispatched grid checkpoint file inventory drifted")
    for filename, block_id in expected_files.items():
        if (
            hashlib.sha256(_read_regular_bytes(directory / filename)).hexdigest()
            != checkpoint_inventory[block_id]
        ):
            raise EvidenceDrift("dispatched grid checkpoint changed during audit")
    directory_after = os.lstat(directory)
    if not os.path.samestat(directory_before, directory_after):
        raise EvidenceDrift("dispatched grid checkpoint directory changed during audit")
    return tuple(sorted(normal_scuc_scales))


def audit_dispatched_grid_inventory(
    root: Path,
    package: Path,
    *,
    base_package: Path,
    hourly_file: str,
    base_hourly_file: str,
    base_manifest_sha256: str,
    expected_grid_config_sha256: str,
    expected_dc_reference_demand_mw: float,
    training_blocks: int,
    holdout_blocks: int,
    package_files: Mapping[str, bytes] | None = None,
    base_files: Mapping[str, bytes] | None = None,
) -> SplitInventory:
    """Verify the exact v4 dispatch schema and its row mapping to the base package."""

    if hourly_file != "dispatched_power_system_blocks.csv.gz":
        raise EvidenceDrift("dispatched grid hourly filename drifted")
    if package_files is None:
        package_files = {
            name: _read_regular_bytes(package / name) for name in _GRID_PACKAGE_MEMBERS
        }
    if base_files is None:
        base_files = {
            base_hourly_file: _read_regular_bytes(base_package / base_hourly_file),
            "training_marginal.csv.gz": _read_regular_bytes(
                base_package / "training_marginal.csv.gz"
            ),
            "holdout_marginal.csv.gz": _read_regular_bytes(
                base_package / "holdout_marginal.csv.gz"
            ),
        }
    config_bytes = package_files.get("config.yaml")
    if (
        not isinstance(config_bytes, bytes)
        or hashlib.sha256(config_bytes).hexdigest() != expected_grid_config_sha256
    ):
        raise EvidenceDrift("dispatched grid producer config drifted")
    try:
        grid_config = yaml.safe_load(config_bytes.decode("utf-8"))
    except (UnicodeError, yaml.YAMLError) as error:
        raise ExecutionEvidenceError("invalid dispatched grid config") from error
    if not isinstance(grid_config, Mapping):
        raise ExecutionEvidenceError("dispatched grid config is not a mapping")
    if set(grid_config) != {
        "input",
        "grid_source",
        "model",
        "solver",
        "provenance",
        "execution",
        "output",
        "activation_authority",
    }:
        raise EvidenceDrift("dispatched grid config schema drifted")
    grid_input = grid_config.get("input")
    grid_model = grid_config.get("model")
    grid_execution = grid_config.get("execution")
    grid_output = grid_config.get("output")
    if (
        not isinstance(grid_input, Mapping)
        or grid_input.get("power_system_blocks_manifest_sha256") != base_manifest_sha256
        or not isinstance(grid_model, Mapping)
        or set(grid_model)
        != {
            "dc_bus",
            "dc_reference_demand_mw",
            "time_step_hours",
            "normal_baseline",
            "outage_response",
            "branch_rating",
            "generator_response_limit",
            "load_shedding_allowed",
            "full_N_minus_one",
            "AC_security",
        }
        or float(grid_model.get("dc_reference_demand_mw", float("nan")))
        != expected_dc_reference_demand_mw
        or grid_model.get("load_shedding_allowed") is not False
        or grid_model.get("full_N_minus_one") is not False
        or grid_model.get("AC_security") is not False
        or not isinstance(grid_execution, Mapping)
        or grid_execution.get("formal_execution_ready") is not True
        or grid_execution.get("independent_R4_review_passed") is not True
        or grid_execution.get("user_formal_run_authorized") is not True
        or grid_execution.get("require_all_blocks_resolved") is not True
        or grid_execution.get("predecessor_HiGHS_checkpoint_reuse_allowed") is not False
        or not isinstance(grid_output, Mapping)
        or grid_output.get("schema") != "rts_gmlc_public_grid_need_dispatch_v4"
    ):
        raise EvidenceDrift("dispatched grid config contract drifted")
    dc_reference_demand_mw = _finite_csv_float(
        str(grid_model["dc_reference_demand_mw"]),
        "dc_reference_demand_mw",
        minimum=1.0e-12,
    )
    grid_solver = grid_config.get("solver")
    grid_activation = grid_config.get("activation_authority")
    if (
        not isinstance(grid_solver, Mapping)
        or grid_solver.get("name") != "gurobi"
        or grid_solver.get("expected_package_version") != "13.0.2"
        or grid_solver.get("threads") != 4
        or not isinstance(grid_activation, Mapping)
        or set(grid_activation)
        != {
            "activation_path",
            "activation_sha256",
            "post_result_review_path",
            "post_result_review_sha256",
            "pilot_result_manifest_sha256",
            "grid_activation_review_path",
            "grid_activation_review_sha256",
        }
        or any(
            _HEX_DIGEST.fullmatch(str(value)) is None
            for key, value in grid_activation.items()
            if key.endswith("_sha256")
        )
    ):
        raise EvidenceDrift("dispatched grid solver contract drifted")
    solver_tolerance_mw = _finite_csv_float(
        str(grid_solver.get("tolerance_mw")),
        "solver tolerance_mw",
        minimum=0.0,
    )
    solver_relative_gap = _finite_csv_float(
        str(grid_solver.get("mip_relative_gap")),
        "solver mip_relative_gap",
        minimum=0.0,
    )
    base_rows = _gzip_csv_rows(
        base_files[base_hourly_file],
        label=str(base_package / base_hourly_file),
        exact_fields=_GRID_BLOCK_FIELDS,
    )
    dispatched_rows = _gzip_csv_rows(
        package_files[hourly_file],
        label=str(package / hourly_file),
        exact_fields=_GRID_OUTPUT_FIELDS,
    )
    base_by_id = _indexed_rows(base_rows, label="base power")
    dispatched_by_id = _indexed_rows(dispatched_rows, label="dispatched grid")
    if set(base_by_id) != set(dispatched_by_id):
        raise EvidenceDrift("dispatched grid block/hour mapping drifted")

    for identity, base_row in base_by_id.items():
        row = dispatched_by_id[identity]
        if any(row[field] != base_row[field] for field in _GRID_BLOCK_FIELDS):
            raise EvidenceDrift("dispatched grid source-row mapping drifted")
        state = row["dispatch_state"]
        resolved = row["dispatch_resolved"]
        proven_infeasible = row["dispatch_proven_infeasible"]
        has_event = bool(row["active_event_id"])
        primary_variables = _csv_nonnegative_int(
            row["dispatch_model_variables"],
            "dispatch model variables",
        )
        primary_constraints = _csv_nonnegative_int(
            row["dispatch_model_constraints"],
            "dispatch model constraints",
        )
        if state == _FINITE_GRID_NEED:
            if resolved != "true" or proven_infeasible != "false":
                raise EvidenceDrift("finite dispatched-grid state is inconsistent")
            grid_mw = _finite_csv_float(
                row["grid_need_mw"],
                "grid_need_mw",
                minimum=0.0,
            )
            grid_fraction = _finite_csv_float(
                row["grid_need_fraction"],
                "grid_need_fraction",
                minimum=0.0,
                maximum=1.0,
            )
            if not math.isclose(
                grid_mw / dc_reference_demand_mw,
                grid_fraction,
                rel_tol=0.0,
                abs_tol=1.0e-12,
            ):
                raise EvidenceDrift("dispatched grid MW/fraction mapping drifted")
            incumbent = _finite_csv_float(
                row["dispatch_objective_incumbent_mw"],
                "dispatch objective incumbent",
                minimum=0.0,
            )
            lower, upper, gap = _validate_bound_fields(
                row,
                prefix="dispatch",
                include_relative_and_tolerance=True,
            )
            residual = _finite_csv_float(
                row["maximum_constraint_violation"],
                "dispatch maximum constraint violation",
                minimum=0.0,
            )
            reported_gap_tolerance = _finite_csv_float(
                row["dispatch_gap_tolerance_mw"],
                "dispatch gap tolerance",
                minimum=0.0,
            )
            relative_gap = _finite_csv_float(
                row["dispatch_relative_gap"],
                "dispatch relative gap",
                minimum=0.0,
            )
            if lower is None or upper is None or gap is None:
                raise EvidenceDrift("finite dispatched-grid certificate is incomplete")
            _validate_grid_minimization_certificate(
                incumbent=incumbent,
                lower=lower,
                upper=upper,
                absolute_gap=gap,
                relative_gap=relative_gap,
                reported_gap_tolerance=reported_gap_tolerance,
                model_tolerance=solver_tolerance_mw if has_event else 0.0,
                configured_relative_gap=solver_relative_gap if has_event else 0.0,
                label="finite dispatched-grid certificate",
            )
            if (
                not math.isclose(
                    max(incumbent, 0.0),
                    grid_mw,
                    rel_tol=0.0,
                    abs_tol=1.0e-12,
                )
                or residual > solver_tolerance_mw
            ):
                raise EvidenceDrift("finite dispatched-grid certificate drifted")
            if has_event:
                if (
                    row["dispatch_termination_condition"] != "optimal"
                    or row["dispatch_solver_status"] != "ok"
                    or primary_variables <= 0
                    or primary_constraints <= 0
                ):
                    raise EvidenceDrift("finite dispatched-grid solver state drifted")
            else:
                _validate_no_event_grid_values(
                    {
                        "grid_need_mw": grid_mw,
                        "grid_need_fraction": grid_fraction,
                        "objective_incumbent_mw": incumbent,
                        "lower_bound_mw": lower,
                        "upper_bound_mw": upper,
                        "absolute_gap_mw": gap,
                        "relative_gap": relative_gap,
                        "gap_tolerance_mw": reported_gap_tolerance,
                        "maximum_constraint_violation": residual,
                    }
                )
                if (
                    row["dispatch_termination_condition"]
                    != "not_applicable_no_active_outage"
                    or row["dispatch_solver_status"] != "not_applicable"
                    or primary_variables != 0
                    or primary_constraints != 0
                ):
                    raise EvidenceDrift("no-outage dispatched-grid certificate drifted")
            if any(
                row[field] != ""
                for field in _GRID_OUTPUT_FIELDS
                if field.startswith("zero_dc_confirmation_")
            ):
                raise EvidenceDrift("finite dispatched-grid zero-DC evidence drifted")
        elif state == _EXOGENOUS_GRID_INFEASIBILITY:
            if (
                resolved != "false"
                or proven_infeasible != "true"
                or row["grid_need_mw"] != ""
                or row["grid_need_fraction"] != ""
                or not has_event
                or row["dispatch_objective_incumbent_mw"] != ""
                or row["dispatch_termination_condition"] != "infeasible"
                or row["dispatch_solver_status"] != "warning"
                or row["maximum_constraint_violation"] != ""
                or primary_variables <= 0
                or primary_constraints <= 0
            ):
                raise EvidenceDrift("E0 dispatched-grid state is inconsistent")
            primary_bounds = _validate_bound_fields(
                row,
                prefix="dispatch",
                include_relative_and_tolerance=True,
            )
            if any(value is not None for value in primary_bounds):
                raise EvidenceDrift("E0 dispatch bound certificate must be empty")
            zero_variables = _csv_nonnegative_int(
                row["zero_dc_confirmation_model_variables"],
                "zero-DC model variables",
            )
            zero_constraints = _csv_nonnegative_int(
                row["zero_dc_confirmation_model_constraints"],
                "zero-DC model constraints",
            )
            if (
                row["zero_dc_confirmation_termination_condition"] != "infeasible"
                or row["zero_dc_confirmation_solver_status"] != "warning"
                or zero_variables <= 0
                or zero_constraints <= 0
            ):
                raise EvidenceDrift("E0 zero-DC confirmation drifted")
            zero_bounds = _validate_bound_fields(
                row,
                prefix="zero_dc_confirmation",
                include_relative_and_tolerance=False,
            )
            if any(value is not None for value in zero_bounds):
                raise EvidenceDrift(
                    "E0 zero_dc_confirmation bound certificate must be empty"
                )
            if (primary_variables, primary_constraints) != (
                zero_variables,
                zero_constraints,
            ):
                raise EvidenceDrift("E0 primary and zero-DC model scale drifted")
        else:
            raise EvidenceDrift("dispatched grid contains an unregistered state")

    for split in ("training", "holdout"):
        base_marginal = _gzip_csv_rows(
            base_files[f"{split}_marginal.csv.gz"],
            label=str(base_package / f"{split}_marginal.csv.gz"),
            exact_fields=("id", "probability"),
        )
        dispatched_marginal = _gzip_csv_rows(
            package_files[f"{split}_marginal.csv.gz"],
            label=str(package / f"{split}_marginal.csv.gz"),
            exact_fields=("id", "probability"),
        )
        if dispatched_marginal != base_marginal:
            raise EvidenceDrift("dispatched grid marginal mapping drifted")

    status_rows = _gzip_csv_rows(
        package_files["block_status.csv.gz"],
        label=str(package / "block_status.csv.gz"),
        exact_fields=(
            "block_id",
            "split",
            "all_hours_resolved",
            "baseline_accepted",
            "exogenous_grid_infeasibility_hour_count",
        ),
    )
    status_by_id: dict[str, Mapping[str, str]] = {}
    for row in status_rows:
        block_id = row["block_id"]
        if not block_id or block_id in status_by_id:
            raise EvidenceDrift("dispatched grid block-status inventory drifted")
        matching_rows = [
            dispatched_by_id[identity]
            for identity in dispatched_by_id
            if identity[0] == block_id
        ]
        if (
            len(matching_rows) != 24
            or row["split"] not in {"training", "holdout"}
            or any(item["split"] != row["split"] for item in matching_rows)
            or row["all_hours_resolved"] != "True"
            or row["baseline_accepted"] != "True"
        ):
            raise EvidenceDrift("dispatched grid block is not fully resolved")
        try:
            e0_count = int(row["exogenous_grid_infeasibility_hour_count"])
        except (TypeError, ValueError) as error:
            raise EvidenceDrift("dispatched grid block-status count drifted") from error
        if e0_count != sum(
            item["dispatch_state"] == _EXOGENOUS_GRID_INFEASIBILITY
            for item in matching_rows
        ):
            raise EvidenceDrift("dispatched grid block-status count drifted")
        status_by_id[block_id] = row
    expected_block_ids = {identity[0] for identity in base_by_id}
    if set(status_by_id) != expected_block_ids:
        raise EvidenceDrift("dispatched grid block-status IDs drifted")

    checkpoint_inventory = _json_bytes_mapping(
        package_files["checkpoint_inventory.json"],
        label="dispatched grid checkpoint inventory",
    )
    if set(checkpoint_inventory) != expected_block_ids or any(
        not isinstance(digest, str) or _HEX_DIGEST.fullmatch(digest) is None
        for digest in checkpoint_inventory.values()
    ):
        raise EvidenceDrift("dispatched grid checkpoint inventory drifted")
    provenance = _json_bytes_mapping(
        package_files["provenance.json"],
        label="dispatched grid provenance",
    )
    provenance_config = grid_config.get("provenance")
    grid_source = grid_config.get("grid_source")
    if (
        not isinstance(provenance_config, Mapping)
        or set(provenance_config) != {"contract_path", "contract_sha256"}
        or not isinstance(grid_source, Mapping)
        or not isinstance(grid_source.get("manifest_sha256"), str)
    ):
        raise EvidenceDrift("dispatched grid provenance config drifted")
    contract_relative = Path(str(provenance_config["contract_path"]))
    if contract_relative.is_absolute() or ".." in contract_relative.parts:
        raise EvidenceDrift("dispatched grid provenance path escaped repository")
    contract_path = root / contract_relative
    contract_bytes = _read_regular_bytes(contract_path)
    if (
        hashlib.sha256(contract_bytes).hexdigest()
        != provenance_config["contract_sha256"]
    ):
        raise EvidenceDrift("dispatched grid provenance contract drifted")
    try:
        contract = yaml.safe_load(contract_bytes.decode("utf-8"))
    except (UnicodeError, yaml.YAMLError) as error:
        raise ExecutionEvidenceError(
            "invalid dispatched grid provenance contract"
        ) from error
    if not isinstance(contract, Mapping):
        raise EvidenceDrift("dispatched grid provenance contract schema drifted")
    stages = contract.get("stages")
    stage_contract = (
        stages.get("grid_need_dispatch_v4") if isinstance(stages, Mapping) else None
    )
    if (
        contract.get("schema") != "rq2_public_pipeline_provenance_contract_v3"
        or not isinstance(stage_contract, Mapping)
        or set(stage_contract) != {"runner", "modules", "software"}
        or not isinstance(stage_contract["runner"], Mapping)
        or not isinstance(stage_contract["modules"], Mapping)
        or not isinstance(stage_contract["software"], Mapping)
    ):
        raise EvidenceDrift("dispatched grid provenance contract schema drifted")

    def bound_source_sha256(item: object) -> str:
        if not isinstance(item, Mapping) or set(item) != {"path", "sha256"}:
            raise EvidenceDrift("grid producer source identity drifted")
        relative = Path(str(item["path"]))
        digest = item["sha256"]
        if (
            relative.is_absolute()
            or ".." in relative.parts
            or not isinstance(digest, str)
            or _HEX_DIGEST.fullmatch(digest) is None
            or hashlib.sha256(_read_regular_bytes(root / relative)).hexdigest()
            != digest
        ):
            raise EvidenceDrift("grid producer source identity drifted")
        return digest

    stage_base = {
        "schema": "rq2_public_stage_provenance_v3",
        "stage": "grid_need_dispatch_v4",
        "config_sha256": expected_grid_config_sha256,
        "contract_path": contract_relative.as_posix(),
        "contract_sha256": provenance_config["contract_sha256"],
        "implementation": {
            "runner_sha256": bound_source_sha256(stage_contract["runner"]),
            "module_sha256": {
                str(name): bound_source_sha256(item)
                for name, item in sorted(stage_contract["modules"].items())
            },
        },
        "software": {
            str(name): str(expected)
            for name, expected in sorted(stage_contract["software"].items())
        },
        "inputs": {
            "power_system_blocks_manifest_sha256": base_manifest_sha256,
            "rts_gmlc_source_manifest_sha256": grid_source["manifest_sha256"],
        },
    }
    if (
        set(provenance)
        != {"base", "checkpoint_inventory", "checkpoint_inventory_sha256"}
        or provenance["base"] != stage_base
        or provenance["checkpoint_inventory"] != checkpoint_inventory
        or provenance["checkpoint_inventory_sha256"]
        != canonical_sha256(checkpoint_inventory)
    ):
        raise EvidenceDrift("dispatched grid provenance drifted")
    normal_scuc_scales = _audit_dispatched_grid_checkpoints(
        root,
        checkpoint_directory=grid_execution.get("checkpoint_directory"),
        checkpoint_inventory=checkpoint_inventory,
        base_by_id=base_by_id,
        dispatched_by_id=dispatched_by_id,
        expected_stage_base_sha256=_provenance_sha256(stage_base),
        grid_solver=grid_solver,
    )
    summary = _json_bytes_mapping(
        package_files["summary.json"],
        label="dispatched grid summary",
    )
    corrective_scales = sorted(
        {
            (
                _csv_nonnegative_int(
                    row["dispatch_model_variables"],
                    "dispatch model variables",
                ),
                _csv_nonnegative_int(
                    row["dispatch_model_constraints"],
                    "dispatch model constraints",
                ),
            )
            for row in dispatched_rows
            if row["dispatch_model_variables"] != "0"
        }
    )
    if (
        set(summary) != _GRID_SUMMARY_FIELDS
        or summary.get("schema") != "rts_gmlc_public_grid_need_dispatch_v4"
        or summary.get("config_sha256")
        != hashlib.sha256(package_files["config.yaml"]).hexdigest()
        or summary.get("stage_base_provenance_sha256") != _provenance_sha256(stage_base)
        or summary.get("input_manifest_sha256") != base_manifest_sha256
        or summary.get("provenance_sha256")
        != hashlib.sha256(package_files["provenance.json"]).hexdigest()
        or summary.get("checkpoint_inventory_sha256")
        != canonical_sha256(checkpoint_inventory)
        or summary.get("block_count") != training_blocks + holdout_blocks
        or summary.get("training_block_count") != training_blocks
        or summary.get("holdout_block_count") != holdout_blocks
        or summary.get("all_blocks_resolved") is not True
        or summary.get("finite_grid_need_scope") != _GRID_NEED_SCOPE
        or summary.get("exogenous_grid_infeasibility_block_count")
        != sum(
            int(row["exogenous_grid_infeasibility_hour_count"]) > 0
            for row in status_rows
        )
        or summary.get("exogenous_grid_infeasibility_hour_count")
        != sum(
            int(row["exogenous_grid_infeasibility_hour_count"]) for row in status_rows
        )
        or summary.get("exogenous_grid_infeasibility_has_finite_grid_need") is not False
        or summary.get("solver_name") != grid_config["solver"].get("name")
        or summary.get("normal_scuc_model_scales")
        != [list(item) for item in normal_scuc_scales]
        or summary.get("corrective_lp_model_scales")
        != [list(item) for item in corrective_scales]
        or summary.get("formal_execution_authorized") is not True
        or summary.get("empirical_outage_probability_claimed") is not False
        or summary.get("full_N_minus_one") is not False
        or summary.get("AC_security") is not False
        or summary.get("security_certified") is not False
    ):
        raise EvidenceDrift("dispatched grid summary contract drifted")

    return _audit_split_inventory_from_snapshot(
        package_files,
        hourly_file=hourly_file,
        source_field="source_hour",
        training_blocks=training_blocks,
        holdout_blocks=holdout_blocks,
        label=str(package),
    )


def derive_static_authority(
    root: Path,
    config: Mapping[str, object],
) -> dict[str, object]:
    """Derive the trust root from live sealed authorities and input manifests."""

    authority = config.get("authority")
    inputs = config.get("registered_inputs")
    if not isinstance(authority, Mapping) or not isinstance(inputs, Mapping):
        raise ExecutionEvidenceError("execution authority is malformed")
    files: dict[str, str] = {}
    recursive_chains: dict[str, object] = {}
    for label, item in authority.items():
        if (
            not isinstance(label, str)
            or not isinstance(item, Mapping)
            or set(item) != {"path", "sha256"}
        ):
            raise ExecutionEvidenceError("execution authority entry is malformed")
        relative = item["path"]
        expected = item["sha256"]
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise ExecutionEvidenceError("execution authority identity is malformed")
        path = root / relative
        if label in {"scientific_outer", "implementation_outer"}:
            recursive_chains[label] = verify_outer_chain(
                root,
                relative,
                expected_outer_sha256=expected,
            )
        else:
            authority_bytes = _read_regular_bytes(path)
            if hashlib.sha256(authority_bytes).hexdigest() != expected:
                raise EvidenceDrift(f"execution authority drifted: {relative}")
        files[relative] = expected
        if label in {"scientific_review", "implementation_review"}:
            try:
                receipt = (
                    _json_bytes_mapping(
                        authority_bytes,
                        label=f"review receipt: {relative}",
                    )
                    if path.suffix == ".json"
                    else yaml.safe_load(authority_bytes.decode("utf-8"))
                )
            except (UnicodeError, yaml.YAMLError) as error:
                raise ExecutionEvidenceError(
                    f"invalid review receipt: {relative}"
                ) from error
            if not isinstance(receipt, Mapping):
                raise ExecutionEvidenceError(f"invalid review receipt: {relative}")
            if receipt.get("verdict") != "PASS":
                raise EvidenceDrift(f"review receipt is not PASS: {relative}")
            outer_label = (
                "scientific_outer"
                if label == "scientific_review"
                else "implementation_outer"
            )
            reviewed = receipt.get("reviewed_subject")
            effect = receipt.get("effect")
            if (
                not isinstance(reviewed, Mapping)
                or reviewed.get("outer_path") != authority[outer_label]["path"]
                or reviewed.get("outer_sha256") != authority[outer_label]["sha256"]
                or not isinstance(effect, Mapping)
                or effect.get("formal_execution_authorized") is not False
                or effect.get("formal_result_exists") is not False
                or effect.get("paper_claim") is not False
                or effect.get("security_certified") is not False
            ):
                raise EvidenceDrift(f"review receipt scope drifted: {relative}")
    for name in ("power_base", "workload"):
        item = inputs.get(name)
        if not isinstance(item, Mapping):
            raise ExecutionEvidenceError(f"registered input is malformed: {name}")
        relative = item.get("manifest_path")
        expected = item.get("manifest_sha256")
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise ExecutionEvidenceError(f"input manifest is malformed: {name}")
        path = root / relative
        if hashlib.sha256(_read_regular_bytes(path)).hexdigest() != expected:
            raise EvidenceDrift(f"input manifest drifted: {relative}")
        files[relative] = expected
    grid = inputs.get("dispatched_grid")
    if not isinstance(grid, Mapping):
        raise ExecutionEvidenceError("registered grid input is malformed")
    grid_authority_bytes: dict[str, bytes] = {}
    for path_key, digest_key in (
        ("template_config_path", "template_config_sha256"),
        ("config_path", "config_sha256"),
        ("activation_record_path", "activation_record_sha256"),
    ):
        relative = grid.get(path_key)
        expected = grid.get(digest_key)
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise ExecutionEvidenceError(f"grid authority is malformed: {path_key}")
        path = root / relative
        payload_bytes = _read_regular_bytes(path)
        if hashlib.sha256(payload_bytes).hexdigest() != expected:
            raise EvidenceDrift(f"grid authority drifted: {relative}")
        files[relative] = expected
        grid_authority_bytes[path_key] = payload_bytes
    activation_record = _json_bytes_mapping(
        grid_authority_bytes["activation_record_path"],
        label="grid activation authority",
    )
    if (
        activation_record.get("schema") != "rq2_public_grid_stage_activation_v2"
        or activation_record.get("activated_config_path") != grid["config_path"]
        or activation_record.get("activated_config_sha256") != grid["config_sha256"]
        or activation_record.get("template_path") != grid["template_config_path"]
        or activation_record.get("template_sha256") != grid["template_config_sha256"]
        or activation_record.get("formal_execution_ready") is not True
    ):
        raise EvidenceDrift("grid activation authority drifted")
    payload = {
        "schema": "rq2_joint_deliverability_static_authority_v1",
        "files": dict(sorted(files.items())),
        "recursive_chains": dict(sorted(recursive_chains.items())),
    }
    return {**payload, "authority_sha256": canonical_sha256(payload)}


def _audit_registered_input_snapshot(
    root: Path,
    config: Mapping[str, object],
    *,
    activated_grid_manifest_sha256: str | None = None,
) -> tuple[
    dict[str, object],
    tuple[PowerBlock, ...] | None,
    tuple[PowerBlock, ...] | None,
    tuple[WorkloadBlock, ...],
    tuple[WorkloadBlock, ...],
]:
    """Audit and parse each registered package from one verified byte snapshot."""

    inputs = config.get("registered_inputs")
    if not isinstance(inputs, Mapping):
        raise ExecutionEvidenceError("registered input contract is malformed")
    reports: dict[str, object] = {}
    inventories: dict[str, SplitInventory] = {}
    package_snapshots: dict[str, Mapping[str, bytes]] = {}
    for name, source_field in (
        ("power_base", "source_hour"),
        ("workload", "source_relative_hour"),
    ):
        item = inputs[name]
        if not isinstance(item, Mapping):
            raise ExecutionEvidenceError(f"registered input is malformed: {name}")
        package = root / str(item["package"])
        manifest = Path(str(item["manifest_path"]))
        if manifest.parent != Path(str(item["package"])):
            raise ExecutionEvidenceError(f"manifest path escaped package: {name}")
        members, snapshots = _snapshot_flat_package(
            package,
            manifest_name=manifest.name,
            expected_manifest_sha256=str(item["manifest_sha256"]),
        )
        package_snapshots[name] = snapshots
        inventory = _audit_split_inventory_from_snapshot(
            snapshots,
            hourly_file=str(item["hourly_file"]),
            source_field=source_field,
            training_blocks=int(item["training_blocks"]),
            holdout_blocks=int(item["holdout_blocks"]),
            label=str(package),
        )
        inventories[name] = inventory
        reports[name] = {
            "status": "verified",
            "manifest_path": str(item["manifest_path"]),
            "manifest_sha256": str(item["manifest_sha256"]),
            "manifest_member_count": len(members),
            "training_blocks": len(inventory.training_ids),
            "holdout_blocks": len(inventory.holdout_ids),
            "training_block_inventory_sha256": (
                workload_block_inventory_sha256(
                    _snapshot_workload_blocks(snapshots, "training")
                )
                if name == "workload"
                else None
            ),
            "holdout_block_inventory_sha256": (
                workload_block_inventory_sha256(
                    _snapshot_workload_blocks(snapshots, "holdout")
                )
                if name == "workload"
                else None
            ),
            "cross_split_block_id_overlap": 0,
            "cross_split_source_overlap": 0,
        }
    grid = inputs.get("dispatched_grid")
    if not isinstance(grid, Mapping):
        raise ExecutionEvidenceError("dispatched grid contract is malformed")
    grid_package = root / str(grid["package"])
    registered_grid_manifest = grid.get("manifest_sha256")
    if (
        registered_grid_manifest is not None
        and activated_grid_manifest_sha256 is not None
        and registered_grid_manifest != activated_grid_manifest_sha256
    ):
        raise EvidenceDrift("activated grid manifest conflicts with registration")
    expected_grid_manifest = registered_grid_manifest
    if expected_grid_manifest is not None and (
        not isinstance(expected_grid_manifest, str)
        or _HEX_DIGEST.fullmatch(expected_grid_manifest) is None
    ):
        raise ExecutionEvidenceError("activated grid manifest digest is invalid")
    if not os.path.lexists(grid_package):
        grid_report = {
            "status": "blocked_missing_dispatched_grid_package",
            "ready": False,
        }
    elif expected_grid_manifest is None:
        require_safe_existing(grid_package, directory=True)
        grid_report = {
            "status": "blocked_unbound_dispatched_grid_manifest",
            "ready": False,
        }
    else:
        manifest_relative = Path(str(grid["manifest_path"]))
        if manifest_relative.parent != Path(str(grid["package"])):
            raise ExecutionEvidenceError("dispatched grid manifest escaped package")
        members, grid_snapshots = _snapshot_flat_package(
            grid_package,
            manifest_name=manifest_relative.name,
            expected_manifest_sha256=str(expected_grid_manifest),
            required_members=_GRID_PACKAGE_MEMBERS,
        )
        base = inputs["power_base"]
        if not isinstance(base, Mapping):
            raise ExecutionEvidenceError("power base contract is malformed")
        inventory = audit_dispatched_grid_inventory(
            root,
            grid_package,
            base_package=root / str(base["package"]),
            hourly_file=str(grid["hourly_file"]),
            base_hourly_file=str(base["hourly_file"]),
            base_manifest_sha256=str(base["manifest_sha256"]),
            expected_grid_config_sha256=str(grid["config_sha256"]),
            expected_dc_reference_demand_mw=float(grid["dc_reference_demand_mw"]),
            training_blocks=int(base["training_blocks"]),
            holdout_blocks=int(base["holdout_blocks"]),
            package_files=grid_snapshots,
            base_files=package_snapshots["power_base"],
        )
        base_inventory = inventories["power_base"]
        if (
            inventory.training_ids != base_inventory.training_ids
            or inventory.holdout_ids != base_inventory.holdout_ids
            or inventory.training_source_values != base_inventory.training_source_values
            or inventory.holdout_source_values != base_inventory.holdout_source_values
        ):
            raise EvidenceDrift(
                "dispatched grid inventory does not match the registered power base"
            )
        grid_report = {
            "status": "verified",
            "ready": True,
            "manifest_path": str(grid["manifest_path"]),
            "manifest_sha256": str(expected_grid_manifest),
            "authority": "registered",
            "manifest_member_count": len(members),
            "training_blocks": len(inventory.training_ids),
            "holdout_blocks": len(inventory.holdout_ids),
            "training_block_inventory_sha256": power_block_inventory_sha256(
                _snapshot_power_blocks(grid_snapshots, "training")
            ),
            "holdout_block_inventory_sha256": power_block_inventory_sha256(
                _snapshot_power_blocks(grid_snapshots, "holdout")
            ),
        }
    reports["dispatched_grid"] = grid_report
    audit = {
        "schema": "rq2_joint_deliverability_input_audit_v1",
        "registered_input_contract_sha256": canonical_sha256(dict(inputs)),
        "registered_inputs_ready": bool(grid_report["ready"]),
        "packages": reports,
    }
    workload_snapshot = package_snapshots["workload"]
    if grid_report["ready"] is True:
        return (
            audit,
            _snapshot_power_blocks(grid_snapshots, "training"),
            _snapshot_power_blocks(grid_snapshots, "holdout"),
            _snapshot_workload_blocks(workload_snapshot, "training"),
            _snapshot_workload_blocks(workload_snapshot, "holdout"),
        )
    return (
        audit,
        None,
        None,
        _snapshot_workload_blocks(workload_snapshot, "training"),
        _snapshot_workload_blocks(workload_snapshot, "holdout"),
    )


def audit_registered_inputs(
    root: Path,
    config: Mapping[str, object],
    *,
    activated_grid_manifest_sha256: str | None = None,
) -> dict[str, object]:
    """Audit available registered inputs without treating absence as infeasibility."""

    audit, _training_power, _holdout_power, _training_workload, _holdout_workload = (
        _audit_registered_input_snapshot(
            root,
            config,
            activated_grid_manifest_sha256=activated_grid_manifest_sha256,
        )
    )
    return audit


def _load_reviewed_execution_config(
    root: Path,
) -> tuple[dict[str, object], dict[str, str]]:
    """Load the fixed execution outer only through its independent PASS receipt."""

    review_path = root / _EXECUTION_REVIEW_RELATIVE
    review_bytes = _read_regular_bytes(review_path)
    try:
        receipt = yaml.safe_load(review_bytes.decode("utf-8"))
    except (UnicodeError, yaml.YAMLError) as error:
        raise ExecutionEvidenceError("invalid execution review receipt") from error
    if not isinstance(receipt, Mapping):
        raise ExecutionEvidenceError("execution review receipt is not a mapping")
    reviewed = receipt.get("reviewed_subject")
    conclusion = receipt.get("review_conclusion")
    effect = receipt.get("effect")
    if (
        receipt.get("schema") != "rq2_joint_deliverability_execution_review_pass_v1"
        or receipt.get("review_scope")
        != "rq2_joint_deliverability_execution_successor_v1_exact_outer"
        or receipt.get("reviewer_role") != "independent_sol_reviewer"
        or receipt.get("verdict") != "PASS"
        or not isinstance(reviewed, Mapping)
        or reviewed.get("outer_path") != _EXECUTION_OUTER_RELATIVE
        or not isinstance(reviewed.get("outer_sha256"), str)
        or _HEX_DIGEST.fullmatch(reviewed["outer_sha256"]) is None
        or not isinstance(reviewed.get("inner_sha256"), str)
        or _HEX_DIGEST.fullmatch(reviewed["inner_sha256"]) is None
        or not isinstance(reviewed.get("sealed_member_count"), int)
        or reviewed["sealed_member_count"] <= 0
        or not isinstance(conclusion, Mapping)
        or conclusion.get("blocker_findings") != []
        or conclusion.get("major_findings") != []
        or conclusion.get("minor_findings") != []
        or not isinstance(effect, Mapping)
        or effect.get("independent_v1_R3_review_passed") is not True
        or effect.get("independent_review_gate_closed") is not True
        or effect.get("formal_execution_authorized") is not False
        or effect.get("formal_result_exists") is not False
        or effect.get("paper_claim") is not False
        or effect.get("security_certified") is not False
    ):
        raise EvidenceDrift("execution review authority drifted")
    outer_sha256 = str(reviewed["outer_sha256"])
    chain = verify_outer_chain(
        root,
        _EXECUTION_OUTER_RELATIVE,
        expected_outer_sha256=outer_sha256,
    )
    if (
        chain["inner_sha256"] != reviewed["inner_sha256"]
        or chain["member_count"] != reviewed["sealed_member_count"]
    ):
        raise EvidenceDrift("execution review subject drifted")
    config = _sealed_yaml_member(
        root,
        outer_relative=_EXECUTION_OUTER_RELATIVE,
        member_relative=_EXECUTION_CONFIG_RELATIVE,
        expected_outer_sha256=outer_sha256,
    )
    if config.get("execution_review_authority") != {
        "path": _EXECUTION_REVIEW_RELATIVE,
        "schema": "rq2_joint_deliverability_execution_review_pass_v1",
        "review_scope": ("rq2_joint_deliverability_execution_successor_v1_exact_outer"),
        "reviewer_role": "independent_sol_reviewer",
        "required_verdict": "PASS",
        "required_effect": {
            "independent_v1_R3_review_passed": True,
            "independent_review_gate_closed": True,
            "formal_execution_authorized": False,
            "formal_result_exists": False,
            "paper_claim": False,
            "security_certified": False,
        },
    }:
        raise EvidenceDrift("sealed execution review contract drifted")
    implementation = config.get("implementation")
    core_identity = (
        implementation.get("core") if isinstance(implementation, Mapping) else None
    )
    if (
        not isinstance(core_identity, Mapping)
        or set(core_identity) != {"path"}
        or not isinstance(core_identity.get("path"), str)
    ):
        raise EvidenceDrift("sealed execution core identity drifted")
    expected_core = root / str(core_identity["path"])
    require_safe_existing(expected_core, directory=False)
    loaded_core = Path(__file__).absolute()
    require_safe_existing(loaded_core, directory=False)
    if not os.path.samefile(expected_core, loaded_core):
        raise EvidenceDrift("loaded execution module is outside the sealed repository")
    return (
        config,
        {
            "execution_outer_sha256": outer_sha256,
            "execution_review_sha256": hashlib.sha256(review_bytes).hexdigest(),
        },
    )


def _load_bound_stage_authority(
    root: Path,
    config: Mapping[str, object],
    *,
    section: str,
    label: str,
) -> tuple[dict[str, object], str]:
    item = config.get(section)
    if (
        not isinstance(item, Mapping)
        or set(item) != {"path", "schema", "sha256", "ready"}
        or not isinstance(item.get("path"), str)
        or not isinstance(item.get("schema"), str)
        or item.get("ready") is not True
        or not isinstance(item.get("sha256"), str)
        or _HEX_DIGEST.fullmatch(item["sha256"]) is None
    ):
        raise ExecutionBlocked(
            f"{label} is not bound by the sealed execution candidate"
        )
    relative = str(item["path"])
    relative_path = Path(relative)
    if relative_path.is_absolute() or ".." in relative_path.parts:
        raise EvidenceDrift(f"{label} path escaped the sealed repository")
    path = root / relative_path
    payload_bytes = _read_regular_bytes(path)
    digest = hashlib.sha256(payload_bytes).hexdigest()
    if digest != item["sha256"]:
        raise EvidenceDrift(f"{label} SHA-256 drifted")
    try:
        payload = (
            _json_bytes_mapping(payload_bytes, label=label)
            if path.suffix == ".json"
            else yaml.safe_load(payload_bytes.decode("utf-8"))
        )
    except (UnicodeError, yaml.YAMLError) as error:
        raise ExecutionEvidenceError(f"invalid {label}") from error
    if not isinstance(payload, dict) or payload.get("schema") != item["schema"]:
        raise EvidenceDrift(f"{label} schema drifted")
    return payload, digest


def _require_store_run_identity(
    store: EvidenceStore,
    registered_input_audit: Mapping[str, object],
) -> None:
    expected = registered_input_audit.get("run_identity_sha256")
    evidence_root_relative = registered_input_audit.get("evidence_root_relative")
    if (
        not isinstance(evidence_root_relative, str)
        or Path(evidence_root_relative).is_absolute()
        or ".." in Path(evidence_root_relative).parts
        or store.root.absolute()
        != (_REPOSITORY_ROOT / evidence_root_relative).absolute()
    ):
        raise EvidenceDrift("evidence store root drifted")
    if (
        not isinstance(expected, str)
        or _HEX_DIGEST.fullmatch(expected) is None
        or store.run_identity_sha256 != expected
    ):
        raise EvidenceDrift("evidence store run identity drifted")


def _load_live_registered_inputs(
    root: Path = _REPOSITORY_ROOT,
) -> tuple[
    dict[str, object],
    tuple[PowerBlock, ...],
    tuple[PowerBlock, ...],
    tuple[WorkloadBlock, ...],
    tuple[WorkloadBlock, ...],
    dict[str, object],
]:
    """Load registered blocks only after verifying this sealed execution candidate."""

    repository = root.absolute()
    if not os.path.samefile(repository, _REPOSITORY_ROOT):
        raise EvidenceDrift("execution repository root is not the loaded module root")
    config, execution_authority = _load_reviewed_execution_config(repository)
    lifecycle = config.get("lifecycle")
    if (
        not isinstance(lifecycle, Mapping)
        or lifecycle.get("status") != "SEALED_READY_FOR_INDEPENDENT_REVIEW"
        or lifecycle.get("sealed_ready_for_independent_review") is not True
    ):
        raise ExecutionBlocked("execution candidate is not sealed")
    static_authority = derive_static_authority(repository, config)
    authority = config.get("authority")
    scientific_outer = (
        authority.get("scientific_outer") if isinstance(authority, Mapping) else None
    )
    if not isinstance(scientific_outer, Mapping):
        raise ExecutionEvidenceError("scientific authority is malformed")
    design = _sealed_yaml_member(
        repository,
        outer_relative=str(scientific_outer.get("path")),
        member_relative=_SCIENTIFIC_CONFIG_RELATIVE,
        expected_outer_sha256=str(scientific_outer.get("sha256")),
    )
    inputs = config.get("registered_inputs")
    grid = inputs.get("dispatched_grid") if isinstance(inputs, Mapping) else None
    registered_grid_manifest = (
        grid.get("manifest_sha256") if isinstance(grid, Mapping) else None
    )
    if registered_grid_manifest is None:
        raise ExecutionBlocked(
            "dispatched grid manifest is not bound by the sealed execution candidate"
        )
    if (
        not isinstance(registered_grid_manifest, str)
        or _HEX_DIGEST.fullmatch(registered_grid_manifest) is None
    ):
        raise EvidenceDrift("sealed dispatched grid manifest is invalid")
    runtime_receipt, runtime_receipt_sha256 = _load_bound_stage_authority(
        repository,
        config,
        section="execution_runtime_authority",
        label="execution runtime authority",
    )
    activation_receipt, activation_sha256 = _load_bound_stage_authority(
        repository,
        config,
        section="execution_activation_authority",
        label="execution activation authority",
    )
    authority = config.get("authority")
    environment = (
        authority.get("executor_environment")
        if isinstance(authority, Mapping)
        else None
    )
    if (
        not isinstance(environment, Mapping)
        or runtime_receipt.get("execution_outer_sha256")
        != execution_authority["execution_outer_sha256"]
        or runtime_receipt.get("grid_manifest_sha256") != registered_grid_manifest
        or runtime_receipt.get("executor_environment_sha256")
        != environment.get("sha256")
        or runtime_receipt.get("platform") != "windows_x86_64"
        or runtime_receipt.get("python_version") != "3.11.15"
        or runtime_receipt.get("gurobipy_version") != "13.0.2"
        or runtime_receipt.get("solver_threads") != 4
        or runtime_receipt.get("native_solver_replay_passed") is not True
        or runtime_receipt.get("registered_dimension_memory_profile_passed") is not True
        or runtime_receipt.get("transport_runtime_projection_accepted") is not True
    ):
        raise EvidenceDrift("execution runtime authority scope drifted")
    if (
        activation_receipt.get("execution_outer_sha256")
        != execution_authority["execution_outer_sha256"]
        or activation_receipt.get("execution_review_sha256")
        != execution_authority["execution_review_sha256"]
        or activation_receipt.get("grid_manifest_sha256") != registered_grid_manifest
        or activation_receipt.get("runtime_receipt_sha256") != runtime_receipt_sha256
        or activation_receipt.get("independent_R3_execution_review_passed") is not True
        or activation_receipt.get("user_formal_run_authorized") is not True
        or activation_receipt.get("formal_execution_authorized") is not True
        or activation_receipt.get("formal_result_exists") is not False
        or activation_receipt.get("paper_claim") is not False
        or activation_receipt.get("security_certified") is not False
    ):
        raise EvidenceDrift("execution activation authority scope drifted")
    evidence_root_relative = activation_receipt.get("evidence_root_relative")
    if (
        not isinstance(evidence_root_relative, str)
        or Path(evidence_root_relative).is_absolute()
        or ".." in Path(evidence_root_relative).parts
        or not evidence_root_relative.startswith(
            "results/execution_evidence/rq2_joint_deliverability/"
        )
    ):
        raise EvidenceDrift("execution activation evidence root drifted")
    expected_run_identity = run_identity(
        static_authority_sha256=str(static_authority["authority_sha256"]),
        execution_outer_sha256=execution_authority["execution_outer_sha256"],
        execution_review_sha256=execution_authority["execution_review_sha256"],
        grid_manifest_sha256=registered_grid_manifest,
        runtime_receipt_sha256=runtime_receipt_sha256,
        activation_sha256=activation_sha256,
    )
    (
        observed_audit,
        training_power,
        holdout_power,
        training_workload,
        holdout_workload,
    ) = _audit_registered_input_snapshot(
        repository,
        config,
        activated_grid_manifest_sha256=registered_grid_manifest,
    )
    audit = {
        **observed_audit,
        **execution_authority,
        "activated_grid_manifest_sha256": registered_grid_manifest,
        "runtime_receipt_sha256": runtime_receipt_sha256,
        "activation_sha256": activation_sha256,
        "run_identity_sha256": expected_run_identity,
        "evidence_root_relative": evidence_root_relative,
    }
    if audit.get("registered_inputs_ready") is not True:
        raise ExecutionBlocked("registered input package is not execution-ready")
    if training_power is None or holdout_power is None:
        raise ExecutionBlocked("registered power blocks are unavailable")
    return (
        audit,
        training_power,
        holdout_power,
        training_workload,
        holdout_workload,
        design,
    )


def _fsync_directory(path: Path) -> None:
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel32.CreateFileW.argtypes = (
            wintypes.LPCWSTR,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.LPVOID,
            wintypes.DWORD,
            wintypes.DWORD,
            wintypes.HANDLE,
        )
        kernel32.CreateFileW.restype = wintypes.HANDLE
        kernel32.FlushFileBuffers.argtypes = (wintypes.HANDLE,)
        kernel32.FlushFileBuffers.restype = wintypes.BOOL
        kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)
        kernel32.CloseHandle.restype = wintypes.BOOL
        handle = kernel32.CreateFileW(
            str(path),
            _WINDOWS_GENERIC_READ | _WINDOWS_GENERIC_WRITE,
            0x00000001 | 0x00000002 | 0x00000004,
            None,
            3,
            0x02000000,
            None,
        )
        invalid = ctypes.c_void_p(-1).value
        if handle == invalid:
            raise OSError(ctypes.get_last_error(), f"open directory failed: {path}")
        try:
            if not kernel32.FlushFileBuffers(handle):
                raise OSError(
                    ctypes.get_last_error(),
                    f"directory flush failed: {path}",
                )
        finally:
            kernel32.CloseHandle(handle)
        return
    descriptor = os.open(path, os.O_RDONLY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _durable_mkdir(path: Path, *, boundary: Path | None = None) -> None:
    """Create a directory tree without traversing aliases and persist each entry."""

    absolute = path.absolute()
    boundary_absolute = None if boundary is None else boundary.absolute()
    if boundary_absolute is not None and not absolute.is_relative_to(boundary_absolute):
        raise ExecutionEvidenceError("evidence directory escaped its root")
    if os.path.lexists(absolute):
        require_safe_existing(absolute, directory=True)
        _fsync_directory(absolute)
        if absolute != boundary_absolute:
            _fsync_directory(absolute.parent)
        return
    parent = absolute.parent
    if parent == absolute:
        raise ExecutionEvidenceError(f"directory root is absent: {absolute}")
    _durable_mkdir(parent, boundary=boundary_absolute)
    try:
        os.mkdir(absolute)
    except FileExistsError:
        require_safe_existing(absolute, directory=True)
        _fsync_directory(absolute)
        _fsync_directory(parent)
        return
    require_safe_existing(absolute, directory=True)
    _fsync_directory(absolute)
    _fsync_directory(parent)


def _atomic_immutable_write(
    path: Path,
    payload: bytes,
    *,
    boundary: Path,
) -> None:
    _durable_mkdir(path.parent, boundary=boundary)
    lock = path.with_name(f".{path.name}.lock")
    if os.path.lexists(lock):
        raise ExecutionEvidenceError(f"evidence write lock exists: {lock}")
    if os.path.lexists(path):
        require_safe_existing(path, directory=False)
        if _read_regular_bytes(path) == payload:
            return
        raise EvidenceDrift(f"immutable evidence drifted: {path}")
    try:
        descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as error:
        raise ExecutionEvidenceError(f"evidence write lock exists: {lock}") from error
    temporary = path.with_name(f".{path.name}.tmp-{uuid.uuid4().hex}")
    target_appeared = False
    parent_fsynced = False
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(b"locked\n")
            handle.flush()
            os.fsync(handle.fileno())
        with temporary.open("xb") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        target_appeared = True
        _fsync_directory(path.parent)
        parent_fsynced = True
    except BaseException as error:
        if target_appeared and not parent_fsynced:
            raise ExecutionEvidenceError(
                f"immutable evidence commit is indeterminate: {path}"
            ) from error
        raise
    finally:
        if temporary.exists():
            temporary.unlink()
        if lock.exists() and (not target_appeared or parent_fsynced):
            lock.unlink()
            _fsync_directory(path.parent)


class EvidenceStore:
    """Immutable content-addressed objects plus identity-bound pointers."""

    def __init__(self, root: Path, *, run_identity_sha256: str) -> None:
        if _HEX_DIGEST.fullmatch(run_identity_sha256) is None:
            raise ValueError("run identity must be a SHA-256 digest")
        self.root = root.absolute()
        self.run_identity_sha256 = run_identity_sha256
        _durable_mkdir(self.root)

    def put_object(self, namespace: str, payload: object) -> str:
        namespace = _safe_component(namespace, "object namespace")
        encoded = canonical_json_bytes(payload)
        digest = hashlib.sha256(encoded).hexdigest()
        target = self.root / "objects" / namespace / digest[:2] / f"{digest}.json"
        _atomic_immutable_write(target, encoded, boundary=self.root)
        return digest

    def put_blob(self, namespace: str, payload: bytes) -> str:
        namespace = _safe_component(namespace, "blob namespace")
        digest = hashlib.sha256(payload).hexdigest()
        target = self.root / "blobs" / namespace / digest[:2] / f"{digest}.bin"
        _atomic_immutable_write(target, payload, boundary=self.root)
        return digest

    def load_blob(self, namespace: str, digest: str) -> bytes:
        namespace = _safe_component(namespace, "blob namespace")
        if _HEX_DIGEST.fullmatch(digest) is None:
            raise ValueError("blob digest is invalid")
        path = self.root / "blobs" / namespace / digest[:2] / f"{digest}.bin"
        payload = _read_regular_bytes(path)
        if hashlib.sha256(payload).hexdigest() != digest:
            raise EvidenceDrift(f"content-addressed blob drifted: {path}")
        return payload

    def object_path(self, namespace: str, digest: str) -> Path:
        namespace = _safe_component(namespace, "object namespace")
        if _HEX_DIGEST.fullmatch(digest) is None:
            raise ValueError("object digest is invalid")
        return self.root / "objects" / namespace / digest[:2] / f"{digest}.json"

    def load_object(self, namespace: str, digest: str) -> dict[str, Any]:
        path = self.object_path(namespace, digest)
        payload_bytes = _read_regular_bytes(path)
        if hashlib.sha256(payload_bytes).hexdigest() != digest:
            raise EvidenceDrift(f"content-addressed object drifted: {path}")
        return _json_bytes_mapping(payload_bytes, label=str(path))

    def commit(
        self,
        stage: str,
        key: str,
        payload: object,
    ) -> dict[str, object]:
        stage = _safe_component(stage, "checkpoint stage")
        key = _safe_component(key, "checkpoint key")
        digest = self.put_object(stage, payload)
        pointer = {
            "schema": "rq2_joint_deliverability_checkpoint_pointer_v1",
            "run_identity_sha256": self.run_identity_sha256,
            "stage": stage,
            "key": key,
            "object_sha256": digest,
        }
        target = self.root / "checkpoints" / stage / f"{key}.json"
        _atomic_immutable_write(
            target,
            canonical_json_bytes(pointer),
            boundary=self.root,
        )
        return pointer

    def load(self, stage: str, key: str) -> dict[str, Any]:
        stage = _safe_component(stage, "checkpoint stage")
        key = _safe_component(key, "checkpoint key")
        pointer = _json_mapping(self.root / "checkpoints" / stage / f"{key}.json")
        expected = {
            "schema": "rq2_joint_deliverability_checkpoint_pointer_v1",
            "run_identity_sha256": self.run_identity_sha256,
            "stage": stage,
            "key": key,
            "object_sha256": pointer.get("object_sha256"),
        }
        if pointer != expected or not isinstance(pointer["object_sha256"], str):
            raise EvidenceDrift("checkpoint identity drifted")
        return self.load_object(stage, pointer["object_sha256"])

    def keys(self, stage: str) -> tuple[str, ...]:
        stage = _safe_component(stage, "checkpoint stage")
        directory = self.root / "checkpoints" / stage
        if not os.path.lexists(directory):
            return ()
        require_safe_existing(directory, directory=True)
        result = []
        for path in directory.iterdir():
            _reject_alias(path)
            if not path.is_file() or path.suffix != ".json":
                raise EvidenceDrift(f"checkpoint inventory drifted: {path}")
            result.append(path.stem)
        return tuple(sorted(result, key=str.encode))

    def inventory(self) -> dict[str, object]:
        files: dict[str, str] = {}
        file_bytes: dict[str, bytes] = {}
        directories: set[str] = set()
        objects: dict[tuple[str, str], Path] = {}
        blobs: dict[tuple[str, str], Path] = {}
        pointers: dict[tuple[str, str], Path] = {}
        for path in sorted(self.root.rglob("*")):
            _reject_alias(path)
            if path.is_dir():
                directories.add(path.relative_to(self.root).as_posix())
                continue
            if (
                not path.is_file()
                or path.name.endswith(".lock")
                or ".tmp-" in path.name
            ):
                raise EvidenceDrift(f"evidence tree is not sealed-ready: {path}")
            relative_path = path.relative_to(self.root)
            relative = relative_path.as_posix()
            payload_bytes = _read_regular_bytes(path)
            file_bytes[relative] = payload_bytes
            files[relative] = hashlib.sha256(payload_bytes).hexdigest()
            parts = relative_path.parts
            if parts[0] == "objects" and len(parts) == 4:
                namespace, prefix, filename = parts[1:]
                digest = Path(filename).stem
                if (
                    Path(filename).suffix != ".json"
                    or _SAFE_COMPONENT.fullmatch(namespace) is None
                    or _HEX_DIGEST.fullmatch(digest) is None
                    or prefix != digest[:2]
                    or files[relative] != digest
                ):
                    raise EvidenceDrift("content-addressed object path drifted")
                objects[(namespace, digest)] = path
            elif parts[0] == "blobs" and len(parts) == 4:
                namespace, prefix, filename = parts[1:]
                digest = Path(filename).stem
                if (
                    Path(filename).suffix != ".bin"
                    or _SAFE_COMPONENT.fullmatch(namespace) is None
                    or _HEX_DIGEST.fullmatch(digest) is None
                    or prefix != digest[:2]
                    or files[relative] != digest
                ):
                    raise EvidenceDrift("content-addressed blob path drifted")
                blobs[(namespace, digest)] = path
            elif parts[0] == "checkpoints" and len(parts) == 3:
                stage, filename = parts[1:]
                key = Path(filename).stem
                if (
                    Path(filename).suffix != ".json"
                    or _SAFE_COMPONENT.fullmatch(stage) is None
                    or _SAFE_COMPONENT.fullmatch(key) is None
                ):
                    raise EvidenceDrift("checkpoint pointer path drifted")
                pointers[(stage, key)] = path
            else:
                raise EvidenceDrift(f"unregistered evidence path: {relative}")

        expected_directories: set[str] = set()
        for relative in files:
            parent = Path(relative).parent
            while parent != Path("."):
                expected_directories.add(parent.as_posix())
                parent = parent.parent
        if directories != expected_directories:
            raise EvidenceDrift("unregistered or empty evidence directory")

        referenced_objects: set[tuple[str, str]] = set()
        referenced_blobs: set[tuple[str, str]] = set()
        for (stage, key), path in pointers.items():
            relative = path.relative_to(self.root).as_posix()
            pointer = _json_bytes_mapping(file_bytes[relative], label=str(path))
            digest = pointer.get("object_sha256")
            if (
                not isinstance(digest, str)
                or _HEX_DIGEST.fullmatch(digest) is None
                or pointer
                != {
                    "schema": "rq2_joint_deliverability_checkpoint_pointer_v1",
                    "run_identity_sha256": self.run_identity_sha256,
                    "stage": stage,
                    "key": key,
                    "object_sha256": digest,
                }
            ):
                raise EvidenceDrift("checkpoint pointer closure drifted")
            object_identity = (stage, digest)
            object_path = objects.get(object_identity)
            if object_path is None:
                raise EvidenceDrift("checkpoint object is missing")
            referenced_objects.add(object_identity)
            object_relative = object_path.relative_to(self.root).as_posix()
            object_payload = _json_bytes_mapping(
                file_bytes[object_relative],
                label=str(object_path),
            )
            native_log_sha256 = object_payload.get("native_log_sha256")
            if native_log_sha256 is not None:
                if (
                    not isinstance(native_log_sha256, str)
                    or _HEX_DIGEST.fullmatch(native_log_sha256) is None
                ):
                    raise EvidenceDrift("native solver log reference drifted")
                referenced_blobs.add(("solver_log", native_log_sha256))
            values_blob_sha256 = object_payload.get("values_blob_sha256")
            if values_blob_sha256 is not None:
                if (
                    stage != "metric_matrix"
                    or not isinstance(values_blob_sha256, str)
                    or _HEX_DIGEST.fullmatch(values_blob_sha256) is None
                ):
                    raise EvidenceDrift("metric-matrix blob reference drifted")
                referenced_blobs.add(("metric_matrix_values", values_blob_sha256))

        if not referenced_objects.issubset(set(objects)):
            raise EvidenceDrift("referenced content-addressed object is missing")
        if not referenced_blobs.issubset(set(blobs)):
            raise EvidenceDrift("referenced content-addressed blob is missing")
        inert_objects = sorted(
            (
                objects[identity].relative_to(self.root).as_posix()
                for identity in set(objects) - referenced_objects
            ),
            key=str.encode,
        )
        inert_blobs = sorted(
            (
                blobs[identity].relative_to(self.root).as_posix()
                for identity in set(blobs) - referenced_blobs
            ),
            key=str.encode,
        )
        payload = {
            "schema": "rq2_joint_deliverability_evidence_inventory_v2",
            "run_identity_sha256": self.run_identity_sha256,
            "files": files,
            "inert_content_addressed_objects": inert_objects,
            "inert_content_addressed_blobs": inert_blobs,
        }
        return {**payload, "inventory_sha256": canonical_sha256(payload)}


_PLANNING_EVIDENCE_STAGES = {
    "input_audit",
    "solve",
    "solve_order",
    "primal",
    "primal_replay",
    "capacity_frontier",
    "planning_index",
}
_HOLDOUT_EVIDENCE_STAGES = _PLANNING_EVIDENCE_STAGES | {
    "holdout",
    "holdout_summary",
}
_BOOTSTRAP_EVIDENCE_STAGES = _HOLDOUT_EVIDENCE_STAGES | {
    "metric_matrix",
    "bootstrap",
}


def _validate_stage_store(
    store: EvidenceStore,
    *,
    allowed_stages: set[str],
    allowed_blob_namespaces: set[str],
) -> dict[str, object]:
    """Require full CAS closure and reject evidence from unrelated stages."""

    inventory = store.inventory()
    files = inventory.get("files")
    if not isinstance(files, Mapping):
        raise EvidenceDrift("evidence inventory is malformed")
    for relative in files:
        parts = Path(str(relative)).parts
        if (
            len(parts) >= 2
            and parts[0] in {"objects", "checkpoints"}
            and parts[1] not in allowed_stages
        ):
            raise EvidenceDrift("evidence store contains an unrelated stage")
        if (
            len(parts) >= 2
            and parts[0] == "blobs"
            and parts[1] not in allowed_blob_namespaces
        ):
            raise EvidenceDrift("evidence store contains an unrelated blob namespace")
    return inventory


def _validate_planning_store_prestate(store: EvidenceStore) -> dict[str, object]:
    """Planning has no implicit resume path; it must start from an empty store."""

    inventory = _validate_stage_store(
        store,
        allowed_stages=_PLANNING_EVIDENCE_STAGES,
        allowed_blob_namespaces={"solver_log"},
    )
    if inventory["files"]:
        raise EvidenceDrift("planning evidence store is not empty")
    return inventory


def metrics_from_trajectory(
    trajectory: Sequence[Mapping[str, object]],
    *,
    time_step_hours: float,
    tolerance: float,
    terminal_recovery_debt_limit: float,
) -> dict[str, object]:
    """Independently rebuild all holdout metrics from an hourly trajectory."""

    if len(trajectory) != 24:
        raise EvidenceDrift("holdout trajectory must contain 24 hours")
    grid_shortfalls = []
    cfe_shortfalls = []
    peak_debt = 0.0
    terminal_debt = 0.0
    for expected_hour, row in enumerate(trajectory):
        if row.get("hour") != expected_hour:
            raise EvidenceDrift("holdout trajectory hour order drifted")
        try:
            grid_request = float(row["effective_grid_request"])
            cfe_request = float(row["effective_cfe_request"])
            grid_served = float(row["grid_served"])
            cfe_served = float(row["cfe_served"])
            debt = float(row["recovery_debt"])
        except (KeyError, TypeError, ValueError) as error:
            raise EvidenceDrift("holdout trajectory scalar is invalid") from error
        if not all(
            math.isfinite(item)
            for item in (
                grid_request,
                cfe_request,
                grid_served,
                cfe_served,
                debt,
            )
        ):
            raise EvidenceDrift("holdout trajectory contains a nonfinite scalar")
        if grid_served < -tolerance or cfe_served < -tolerance or debt < -tolerance:
            raise EvidenceDrift("holdout trajectory contains a negative state")
        grid_shortfalls.append(max(grid_request - grid_served, 0.0) * time_step_hours)
        cfe_shortfalls.append(max(cfe_request - cfe_served, 0.0) * time_step_hours)
        peak_debt = max(peak_debt, debt)
        terminal_debt = debt
    grid_shortfall = math.fsum(grid_shortfalls)
    cfe_shortfall = math.fsum(cfe_shortfalls)
    recovery_failure = terminal_debt > terminal_recovery_debt_limit + tolerance
    hard_grid_failure = grid_shortfall > tolerance
    cfe_service_failure = cfe_shortfall > tolerance
    return {
        "grid_shortfall": grid_shortfall,
        "cfe_shortfall": cfe_shortfall,
        "total_service_shortfall": grid_shortfall + cfe_shortfall,
        "hard_grid_failure": hard_grid_failure,
        "cfe_service_failure": cfe_service_failure,
        "recovery_completion_failure": recovery_failure,
        "joint_service_failure": bool(
            hard_grid_failure or cfe_service_failure or recovery_failure
        ),
        "peak_recovery_debt": peak_debt,
        "terminal_recovery_debt": terminal_debt,
    }


def commit_holdout_chunk(
    store: EvidenceStore,
    payload: Mapping[str, object],
    *,
    time_step_hours: float,
    tolerance: float,
    terminal_recovery_debt_limit: float,
) -> dict[str, object]:
    """Validate and commit one cell/power chunk with all workload-arm traces."""

    if (
        set(payload)
        != {
            "schema",
            "cell_id",
            "power_block_id",
            "conditioned_power_probability",
            "policy_parameters",
            "workloads",
        }
        or payload["schema"] != "rq2_joint_deliverability_holdout_chunk_v1"
    ):
        raise EvidenceDrift("holdout chunk schema drifted")
    cell_id = _safe_component(str(payload["cell_id"]), "cell ID")
    power_id = _safe_component(str(payload["power_block_id"]), "power block ID")
    power_probability = float(payload["conditioned_power_probability"])
    if not math.isfinite(power_probability) or power_probability < 0.0:
        raise EvidenceDrift("conditioned power probability is invalid")
    policy = payload["policy_parameters"]
    if not isinstance(policy, Mapping) or set(policy) != {
        "maximum_recovery_power",
        "recovery_efficiency",
        "maximum_event_duration_hours",
        "maximum_event_count",
        "minimum_recovery_hours",
        "normalized_energy_budget",
        "normalized_debt_limit",
        "terminal_recovery_debt_limit",
        "time_step_hours",
        "minimum_event_power",
        "curtailment_ramp_per_hour",
        "response_time_hours",
        "service_shortfall_tolerance",
    }:
        raise EvidenceDrift("holdout policy parameter schema drifted")
    if (
        float(policy["time_step_hours"]) != time_step_hours
        or float(policy["service_shortfall_tolerance"]) != tolerance
        or float(policy["terminal_recovery_debt_limit"]) != terminal_recovery_debt_limit
    ):
        raise EvidenceDrift("holdout replay parameter binding drifted")
    workloads = payload["workloads"]
    if (
        not isinstance(workloads, Sequence)
        or isinstance(workloads, (str, bytes))
        or not workloads
    ):
        raise EvidenceDrift("holdout chunk workload inventory is empty")
    seen: set[str] = set()
    workload_probability_sum = 0.0
    for item in workloads:
        if not isinstance(item, Mapping) or set(item) != {
            "workload_block_id",
            "workload_probability",
            "available_flexibility",
            "connected_demand",
            "arms",
        }:
            raise EvidenceDrift("holdout workload record schema drifted")
        workload_id = str(item["workload_block_id"])
        if workload_id in seen:
            raise EvidenceDrift("duplicate workload in holdout chunk")
        seen.add(workload_id)
        workload_probability = float(item["workload_probability"])
        if not math.isfinite(workload_probability) or workload_probability < 0.0:
            raise EvidenceDrift("workload probability is invalid")
        workload_probability_sum += workload_probability
        available = item["available_flexibility"]
        connected = item["connected_demand"]
        if (
            not isinstance(available, Sequence)
            or isinstance(available, (str, bytes))
            or not isinstance(connected, Sequence)
            or isinstance(connected, (str, bytes))
            or len(available) != 24
            or len(connected) != 24
        ):
            raise EvidenceDrift("holdout shared input vector drifted")
        arms = item["arms"]
        if not isinstance(arms, Mapping) or set(arms) != set(FOUR_ARM_IDS):
            raise EvidenceDrift("holdout chunk arm inventory drifted")
        for arm_id in FOUR_ARM_IDS:
            arm = arms[arm_id]
            if (
                not isinstance(arm, Mapping)
                or set(arm)
                != {
                    "capacity",
                    "raw_grid_request",
                    "raw_cfe_request",
                    "recovery_headroom",
                    "trajectory",
                    "metrics",
                }
                or not isinstance(arm["trajectory"], Sequence)
                or not isinstance(arm["metrics"], Mapping)
            ):
                raise EvidenceDrift("holdout arm evidence schema drifted")
            replayed = execute_holdout_policy(
                committed_capacity=float(arm["capacity"]),
                grid_request=arm["raw_grid_request"],
                cfe_request=arm["raw_cfe_request"],
                available_flexibility=available,
                connected_demand=connected,
                current_recovery_headroom=arm["recovery_headroom"],
                maximum_recovery_power=float(policy["maximum_recovery_power"]),
                recovery_efficiency=float(policy["recovery_efficiency"]),
                maximum_event_duration_hours=float(
                    policy["maximum_event_duration_hours"]
                ),
                maximum_event_count=int(policy["maximum_event_count"]),
                minimum_recovery_hours=float(policy["minimum_recovery_hours"]),
                normalized_energy_budget=float(policy["normalized_energy_budget"]),
                normalized_debt_limit=float(policy["normalized_debt_limit"]),
                terminal_recovery_debt_limit=float(
                    policy["terminal_recovery_debt_limit"]
                ),
                time_step_hours=float(policy["time_step_hours"]),
                minimum_event_power=float(policy["minimum_event_power"]),
                curtailment_ramp_per_hour=float(policy["curtailment_ramp_per_hour"]),
                response_time_hours=float(policy["response_time_hours"]),
                service_shortfall_tolerance=float(
                    policy["service_shortfall_tolerance"]
                ),
            )
            if canonical_json_bytes(replayed["trajectory"]) != canonical_json_bytes(
                arm["trajectory"]
            ):
                raise EvidenceDrift("holdout policy trajectory replay drifted")
            if canonical_json_bytes(replayed["metrics"]) != canonical_json_bytes(
                arm["metrics"]
            ):
                raise EvidenceDrift("holdout metrics do not replay from trajectory")
            independently_replayed_metrics = metrics_from_trajectory(
                replayed["trajectory"],
                time_step_hours=time_step_hours,
                tolerance=tolerance,
                terminal_recovery_debt_limit=terminal_recovery_debt_limit,
            )
            if canonical_json_bytes(
                independently_replayed_metrics
            ) != canonical_json_bytes(arm["metrics"]):
                raise EvidenceDrift(
                    "holdout metrics do not independently replay from trajectory"
                )
    canonical_workloads = sorted(seen, key=str.encode)
    if [str(item["workload_block_id"]) for item in workloads] != canonical_workloads:
        raise EvidenceDrift("holdout workload order drifted")
    if not math.isclose(
        workload_probability_sum,
        1.0,
        rel_tol=0.0,
        abs_tol=1.0e-9,
    ):
        raise EvidenceDrift("holdout workload probability mass drifted")
    return store.commit("holdout", f"{cell_id}__{power_id}", dict(payload))


def _arm_holdout_vectors(
    scenario: object,
    arm_id: str,
) -> tuple[Sequence[float], Sequence[float], Sequence[float]]:
    zeros = (0.0,) * len(scenario.raw_grid_request)
    grid = (
        scenario.raw_grid_request
        if arm_id
        in {
            "network_only_shared",
            "joint_correct_shared",
            "joint_b6_separate_planning_shared_execution",
        }
        else zeros
    )
    cfe = (
        scenario.raw_cfe_request
        if arm_id
        in {
            "cfe_only_shared",
            "joint_correct_shared",
            "joint_b6_separate_planning_shared_execution",
        }
        else zeros
    )
    recovery = (
        scenario.business_recovery_headroom
        if arm_id == NETWORK_ONLY_SHARED
        else scenario.cfe_service_recovery_headroom
    )
    return grid, cfe, recovery


def _holdout_cell_is_evaluable(raw_arms: object) -> bool:
    return bool(
        isinstance(raw_arms, Mapping)
        and set(raw_arms) == set(FOUR_ARM_IDS)
        and all(
            isinstance(raw_arms[arm_id], Mapping)
            and raw_arms[arm_id].get("status") == "resolved"
            and raw_arms[arm_id].get("reported_point") is not None
            and isinstance(raw_arms[arm_id].get("full_support_audit"), Mapping)
            and raw_arms[arm_id]["full_support_audit"].get("status") == "passed"
            for arm_id in FOUR_ARM_IDS
        )
    )


def _holdout_chunk_payload(
    design: Mapping[str, object],
    *,
    cell: RegisteredCell,
    raw_arms: Mapping[str, object],
    power: PowerBlock,
    workloads: Sequence[WorkloadBlock],
) -> dict[str, object]:
    temporal = design["temporal_envelope"]
    dt = float(design["data_contract"]["time_step_hours"])
    tolerance = float(temporal["service_shortfall_tolerance"])
    terminal_limit = float(temporal["terminal_recovery_debt_limit"])
    workload_rows = []
    for workload in workloads:
        scenario = build_pair_scenario(
            power,
            workload,
            cell,
            service_shortfall_tolerance=tolerance,
        )
        arm_rows = {}
        for arm_id in FOUR_ARM_IDS:
            arm = raw_arms[arm_id]
            if not isinstance(arm, Mapping):
                raise EvidenceDrift("capacity arm inventory drifted")
            grid, cfe, recovery = _arm_holdout_vectors(scenario, arm_id)
            outcome = execute_holdout_policy(
                committed_capacity=float(arm["reported_point"]),
                grid_request=grid,
                cfe_request=cfe,
                available_flexibility=scenario.available_flexibility,
                connected_demand=scenario.connected_demand,
                current_recovery_headroom=recovery,
                maximum_recovery_power=cell.normalized_recovery_headroom,
                recovery_efficiency=cell.recovery_efficiency,
                maximum_event_duration_hours=cell.maximum_event_duration_hours,
                maximum_event_count=cell.maximum_event_count,
                minimum_recovery_hours=float(temporal["minimum_recovery_hours"]),
                normalized_energy_budget=cell.normalized_energy_budget,
                normalized_debt_limit=cell.normalized_debt_limit,
                terminal_recovery_debt_limit=terminal_limit,
                time_step_hours=dt,
                minimum_event_power=float(temporal["minimum_event_power"]),
                curtailment_ramp_per_hour=float(temporal["curtailment_ramp_per_hour"]),
                response_time_hours=float(temporal["response_time_hours"]),
                service_shortfall_tolerance=tolerance,
            )
            arm_rows[arm_id] = {
                "capacity": float(arm["reported_point"]),
                "raw_grid_request": list(grid),
                "raw_cfe_request": list(cfe),
                "recovery_headroom": list(recovery),
                "trajectory": outcome["trajectory"],
                "metrics": outcome["metrics"],
            }
        workload_rows.append(
            {
                "workload_block_id": workload.block_id,
                "workload_probability": workload.probability,
                "available_flexibility": list(scenario.available_flexibility),
                "connected_demand": list(scenario.connected_demand),
                "arms": arm_rows,
            }
        )
    return {
        "schema": "rq2_joint_deliverability_holdout_chunk_v1",
        "cell_id": cell.cell_id,
        "power_block_id": power.block_id,
        "conditioned_power_probability": power.probability,
        "policy_parameters": {
            "maximum_recovery_power": cell.normalized_recovery_headroom,
            "recovery_efficiency": cell.recovery_efficiency,
            "maximum_event_duration_hours": cell.maximum_event_duration_hours,
            "maximum_event_count": cell.maximum_event_count,
            "minimum_recovery_hours": float(temporal["minimum_recovery_hours"]),
            "normalized_energy_budget": cell.normalized_energy_budget,
            "normalized_debt_limit": cell.normalized_debt_limit,
            "terminal_recovery_debt_limit": terminal_limit,
            "time_step_hours": dt,
            "minimum_event_power": float(temporal["minimum_event_power"]),
            "curtailment_ramp_per_hour": float(temporal["curtailment_ramp_per_hour"]),
            "response_time_hours": float(temporal["response_time_hours"]),
            "service_shortfall_tolerance": tolerance,
        },
        "workloads": workload_rows,
    }


def _stream_holdout_stage(
    design: Mapping[str, object],
    *,
    capacity_frontier: Mapping[str, object],
    holdout_power_blocks: tuple[PowerBlock, ...],
    holdout_workload_blocks: tuple[WorkloadBlock, ...],
    store: EvidenceStore,
    commit: bool,
) -> dict[str, object]:
    """Execute and persist holdout one cell/power chunk at a time."""

    capacity_rows = capacity_frontier.get("cells")
    expected_cells = expand_registered_cells(dict(design))
    expected_ids = [cell.cell_id for cell in expected_cells]
    if (
        capacity_frontier.get("schema")
        != "rq2_joint_deliverability_capacity_frontier_v3"
        or not isinstance(capacity_rows, Sequence)
        or isinstance(capacity_rows, (str, bytes))
        or [str(row["cell_id"]) for row in capacity_rows] != expected_ids
    ):
        raise EvidenceDrift("capacity frontier inventory drifted")
    if any(block.split != "holdout" for block in holdout_power_blocks):
        raise EvidenceDrift("holdout power split drifted")
    if any(block.split != "holdout" for block in holdout_workload_blocks):
        raise EvidenceDrift("holdout workload split drifted")
    finite_power, e0_mass = condition_finite_power(holdout_power_blocks)
    finite_power = tuple(sorted(finite_power, key=lambda item: item.block_id.encode()))
    workloads = tuple(
        sorted(holdout_workload_blocks, key=lambda item: item.block_id.encode())
    )
    temporal = design["temporal_envelope"]
    dt = float(design["data_contract"]["time_step_hours"])
    tolerance = float(temporal["service_shortfall_tolerance"])
    terminal_limit = float(temporal["terminal_recovery_debt_limit"])
    expected_keys = {
        f"{cell.cell_id}__{power.block_id}"
        for row, cell in zip(capacity_rows, expected_cells, strict=True)
        if _holdout_cell_is_evaluable(row.get("arms"))
        for power in finite_power
    }
    existing_keys = set(store.keys("holdout"))
    if not existing_keys.issubset(expected_keys):
        raise EvidenceDrift("holdout checkpoint inventory contains an extra key")
    missing_seen = False
    cell_summaries = []
    digest_stream = hashlib.sha256()
    chunk_count = 0
    for row, cell in zip(capacity_rows, expected_cells, strict=True):
        raw_arms = row.get("arms")
        if not isinstance(raw_arms, Mapping) or set(raw_arms) != set(FOUR_ARM_IDS):
            raise EvidenceDrift("capacity arm inventory drifted")
        if not _holdout_cell_is_evaluable(raw_arms):
            cell_summaries.append(
                {
                    "cell_id": cell.cell_id,
                    "status": "not_evaluable_capacity_unresolved",
                    "chunk_count": 0,
                }
            )
            continue
        cell_chunk_count = 0
        for power in finite_power:
            key = f"{cell.cell_id}__{power.block_id}"
            chunk = _holdout_chunk_payload(
                design,
                cell=cell,
                raw_arms=raw_arms,
                power=power,
                workloads=workloads,
            )
            if key in existing_keys:
                if missing_seen:
                    raise EvidenceDrift("holdout checkpoint inventory is not a prefix")
                if canonical_json_bytes(store.load("holdout", key)) != (
                    canonical_json_bytes(chunk)
                ):
                    raise EvidenceDrift("existing holdout checkpoint drifted")
            else:
                missing_seen = True
            object_sha256 = canonical_sha256(chunk)
            if commit:
                pointer = commit_holdout_chunk(
                    store,
                    chunk,
                    time_step_hours=dt,
                    tolerance=tolerance,
                    terminal_recovery_debt_limit=terminal_limit,
                )
                object_sha256 = str(pointer["object_sha256"])
            digest_stream.update(
                (f"{cell.cell_id}/{power.block_id}\0{object_sha256}\n").encode()
            )
            chunk_count += 1
            cell_chunk_count += 1
        cell_summaries.append(
            {
                "cell_id": cell.cell_id,
                "status": (
                    "resolved"
                    if finite_power
                    else "finite_service_identification_unresolved"
                ),
                "chunk_count": cell_chunk_count,
            }
        )
    return {
        "schema": "rq2_joint_deliverability_holdout_stream_v1",
        "E0_mass": e0_mass,
        "E0_power_block_ids": sorted(
            (
                block.block_id
                for block in holdout_power_blocks
                if block.state == "exogenous_grid_infeasibility"
            ),
            key=str.encode,
        ),
        "finite_power_block_ids": [block.block_id for block in finite_power],
        "workload_block_ids": [block.block_id for block in workloads],
        "trajectory_chunk_count": chunk_count,
        "trajectory_chunk_stream_sha256": digest_stream.hexdigest(),
        "cells": cell_summaries,
    }


def _registered_holdout_support(
    registered_input_audit: Mapping[str, object],
    holdout_power_blocks: Sequence[PowerBlock],
    holdout_workload_blocks: Sequence[WorkloadBlock],
) -> tuple[tuple[PowerBlock, ...], tuple[WorkloadBlock, ...]]:
    packages = registered_input_audit.get("packages")
    if (
        registered_input_audit.get("schema")
        != "rq2_joint_deliverability_input_audit_v1"
        or registered_input_audit.get("registered_inputs_ready") is not True
        or not isinstance(packages, Mapping)
        or not isinstance(packages.get("dispatched_grid"), Mapping)
        or not isinstance(packages.get("workload"), Mapping)
        or packages["dispatched_grid"].get("status") != "verified"
        or packages["workload"].get("status") != "verified"
        or packages["dispatched_grid"].get("holdout_block_inventory_sha256")
        != power_block_inventory_sha256(holdout_power_blocks)
        or packages["workload"].get("holdout_block_inventory_sha256")
        != workload_block_inventory_sha256(holdout_workload_blocks)
    ):
        raise EvidenceDrift("holdout blocks do not match audited input authority")
    power = tuple(
        sorted(holdout_power_blocks, key=lambda block: block.block_id.encode())
    )
    workload = tuple(
        sorted(holdout_workload_blocks, key=lambda block: block.block_id.encode())
    )
    if (
        len(power) != 530
        or len(workload) != 34
        or any(block.split != "holdout" for block in power)
        or any(block.split != "holdout" for block in workload)
        or not math.isclose(
            math.fsum(block.probability for block in power),
            1.0,
            rel_tol=0.0,
            abs_tol=1.0e-9,
        )
        or not math.isclose(
            math.fsum(block.probability for block in workload),
            1.0,
            rel_tol=0.0,
            abs_tol=1.0e-9,
        )
    ):
        raise EvidenceDrift("registered holdout block inventory drifted")
    return power, workload


def _commit_registered_input_audit(
    store: EvidenceStore,
    registered_input_audit: Mapping[str, object],
) -> dict[str, object]:
    if (
        registered_input_audit.get("schema")
        != "rq2_joint_deliverability_input_audit_v1"
        or registered_input_audit.get("registered_inputs_ready") is not True
    ):
        raise EvidenceDrift("registered input audit is not execution-ready")
    return store.commit("input_audit", "registered", dict(registered_input_audit))


def _expected_planning_calls(
    capacity_frontier: Mapping[str, object],
) -> list[dict[str, object]]:
    cells = capacity_frontier.get("cells")
    if (
        capacity_frontier.get("schema")
        != "rq2_joint_deliverability_capacity_frontier_v3"
        or capacity_frontier.get("cell_count") != 46
        or capacity_frontier.get("arm_output_count") != 184
        or not isinstance(cells, Sequence)
        or isinstance(cells, (str, bytes))
        or len(cells) != 46
    ):
        raise EvidenceDrift("capacity frontier planning inventory drifted")
    representative: dict[tuple[str, str], dict[str, object]] = {}
    expected_calls: list[dict[str, object]] = []
    for cell in cells:
        cell_id = str(cell.get("cell_id"))
        arms = cell.get("arms")
        if (
            _SAFE_COMPONENT.fullmatch(cell_id) is None
            or not isinstance(arms, Mapping)
            or set(arms) != set(FOUR_ARM_IDS)
        ):
            raise EvidenceDrift("capacity frontier arm inventory drifted")
        for arm_id in FOUR_ARM_IDS:
            arm = arms[arm_id]
            if not isinstance(arm, Mapping):
                raise EvidenceDrift("capacity frontier arm output drifted")
            planning_hash = arm.get("planning_input_sha256")
            if (
                not isinstance(planning_hash, str)
                or _HEX_DIGEST.fullmatch(planning_hash) is None
            ):
                raise EvidenceDrift("capacity frontier planning hash drifted")
            certificate = arm.get("solver_certificate")
            if arm.get("status") == "resolved" and certificate is None:
                raise EvidenceDrift("resolved capacity arm lacks solver evidence")
            entry = None
            if certificate is not None:
                if not isinstance(certificate, Mapping):
                    raise EvidenceDrift("capacity solver certificate drifted")
                key = (
                    (arm_id, planning_hash)
                    if arm_id == NETWORK_ONLY_SHARED
                    else (cell_id, arm_id)
                )
                if key not in representative:
                    representative[key] = {
                        "certificate_sha256": canonical_sha256(dict(certificate)),
                        "output_indices": [],
                    }
                    expected_calls.append(
                        {
                            "arm_id": arm_id,
                            "planning_input_sha256": planning_hash,
                            "certificate_sha256": canonical_sha256(dict(certificate)),
                            "solve_role": "representative",
                            "output_indices": representative[key]["output_indices"],
                        }
                    )
                entry = representative[key]
                if entry["certificate_sha256"] != canonical_sha256(dict(certificate)):
                    raise EvidenceDrift("reused planning evidence changed certificate")
                entry["output_indices"].append({"cell_id": cell_id, "arm_id": arm_id})
            audit = arm.get("full_support_audit")
            if not isinstance(audit, Mapping):
                raise EvidenceDrift("full-support evidence inventory drifted")
            fallback_certificates = audit.get("fallback_certificates")
            if not isinstance(fallback_certificates, Sequence) or isinstance(
                fallback_certificates,
                (str, bytes),
            ):
                raise EvidenceDrift("fallback certificate inventory drifted")
            if certificate is None and fallback_certificates:
                raise EvidenceDrift("fallback exists without representative solve")
            if certificate is not None and entry is not None:
                if len(entry["output_indices"]) == 1:
                    for ordinal, fallback_certificate in enumerate(
                        fallback_certificates
                    ):
                        if not isinstance(fallback_certificate, Mapping):
                            raise EvidenceDrift("fallback certificate schema drifted")
                        expected_calls.append(
                            {
                                "arm_id": arm_id,
                                "planning_input_sha256": None,
                                "certificate_sha256": canonical_sha256(
                                    dict(fallback_certificate)
                                ),
                                "solve_role": "full_support_fallback",
                                "output_indices": [
                                    {
                                        "cell_id": cell_id,
                                        "arm_id": arm_id,
                                        "fallback_ordinal": ordinal,
                                    }
                                ],
                            }
                        )
                else:
                    previous_fallback = [
                        item
                        for item in expected_calls
                        if item["solve_role"] == "full_support_fallback"
                        and item["arm_id"] == arm_id
                        and item["output_indices"][0]["cell_id"]
                        == entry["output_indices"][0]["cell_id"]
                    ]
                    if [item["certificate_sha256"] for item in previous_fallback] != [
                        canonical_sha256(dict(item)) for item in fallback_certificates
                    ]:
                        raise EvidenceDrift("reused fallback evidence drifted")
    if (
        capacity_frontier.get("representative_solver_calls")
        != sum(item["solve_role"] == "representative" for item in expected_calls)
        or capacity_frontier.get("full_support_fallback_solver_calls")
        != sum(item["solve_role"] == "full_support_fallback" for item in expected_calls)
        or capacity_frontier.get("total_solver_calls") != len(expected_calls)
    ):
        raise EvidenceDrift("capacity solver-call accounting drifted")
    return expected_calls


def _registered_planning_evidence(
    store: EvidenceStore,
    *,
    design: Mapping[str, object],
    registered_input_audit: Mapping[str, object],
    training_power_blocks: Sequence[PowerBlock],
    training_workload_blocks: Sequence[WorkloadBlock],
    capacity_frontier_sha256: str,
) -> dict[str, str]:
    if store.keys("planning_index") != ("capacity_frontier",):
        raise EvidenceDrift("planning evidence authority is absent or ambiguous")
    if store.keys("capacity_frontier") != ("registered",):
        raise EvidenceDrift("capacity frontier evidence is absent or ambiguous")
    planning_index = store.load("planning_index", "capacity_frontier")
    capacity_frontier = store.load("capacity_frontier", "registered")
    capacity_frontier_object_sha256 = canonical_sha256(capacity_frontier)
    training_power, training_workload = _registered_training_support(
        registered_input_audit,
        training_power_blocks,
        training_workload_blocks,
    )
    raw_solver_contract = design.get("solver_contract")
    if not isinstance(raw_solver_contract, Mapping):
        raise EvidenceDrift("sealed planning solver contract is absent")
    solver_specification = solver_spec(raw_solver_contract)
    expected_cells = expand_registered_cells(dict(design))
    capacity_rows = capacity_frontier.get("cells")
    if (
        not isinstance(capacity_rows, Sequence)
        or isinstance(capacity_rows, (str, bytes))
        or len(capacity_rows) != len(expected_cells)
        or any(
            row.get("cell_id") != cell.cell_id
            or row.get("family") != cell.family
            or canonical_json_bytes(row.get("parameters"))
            != canonical_json_bytes(asdict(cell))
            for row, cell in zip(capacity_rows, expected_cells, strict=True)
        )
    ):
        raise EvidenceDrift("capacity frontier design authority drifted")
    input_audit_sha256 = canonical_sha256(dict(registered_input_audit))
    packages = registered_input_audit.get("packages")
    if not isinstance(packages, Mapping):
        raise EvidenceDrift("registered input audit package inventory drifted")
    grid = packages.get("dispatched_grid")
    workload = packages.get("workload")
    expected_fields = {
        "schema",
        "capacity_frontier_sha256",
        "capacity_frontier_object_sha256",
        "scientific_design_sha256",
        "registered_input_audit_sha256",
        "input_audit_object_sha256",
        "training_power_inventory_sha256",
        "training_workload_inventory_sha256",
        "solve_record_count",
        "records",
    }
    if (
        set(planning_index) != expected_fields
        or planning_index.get("schema")
        != "rq2_joint_deliverability_planning_evidence_index_v1"
        or planning_index.get("capacity_frontier_sha256") != capacity_frontier_sha256
        or planning_index.get("registered_input_audit_sha256") != input_audit_sha256
        or planning_index.get("capacity_frontier_object_sha256")
        != capacity_frontier_object_sha256
        or capacity_frontier_object_sha256 != capacity_frontier_sha256
        or planning_index.get("scientific_design_sha256")
        != canonical_sha256(dict(design))
        or planning_index.get("registered_input_audit_sha256") != input_audit_sha256
        or planning_index.get("input_audit_object_sha256") != input_audit_sha256
        or not isinstance(grid, Mapping)
        or not isinstance(workload, Mapping)
        or not isinstance(grid.get("training_block_inventory_sha256"), str)
        or _HEX_DIGEST.fullmatch(grid["training_block_inventory_sha256"]) is None
        or not isinstance(workload.get("training_block_inventory_sha256"), str)
        or _HEX_DIGEST.fullmatch(workload["training_block_inventory_sha256"]) is None
        or planning_index.get("training_power_inventory_sha256")
        != grid.get("training_block_inventory_sha256")
        or planning_index.get("training_workload_inventory_sha256")
        != workload.get("training_block_inventory_sha256")
        or not isinstance(planning_index.get("records"), Sequence)
        or isinstance(planning_index["records"], (str, bytes))
        or planning_index.get("solve_record_count") != len(planning_index["records"])
        or not planning_index["records"]
    ):
        raise EvidenceDrift("planning evidence authority drifted")
    if store.keys("input_audit") != ("registered",) or store.load(
        "input_audit", "registered"
    ) != dict(registered_input_audit):
        raise EvidenceDrift("planning input-audit object drifted")
    indexed_records = planning_index["records"]
    replay_ordinal = 0

    def replay_callback(
        inputs: JointDeliverabilityPlanningInputs,
        arm_id: str,
        specification: Rq2SolverSpec,
    ) -> Mapping[str, object]:
        nonlocal replay_ordinal
        if replay_ordinal >= len(indexed_records):
            raise EvidenceDrift("downstream planning replay is incomplete")
        record = indexed_records[replay_ordinal]
        planning_hash = planning_input_sha256(inputs, arm_id, specification)
        if (
            specification != solver_specification
            or not isinstance(record, Mapping)
            or record.get("invocation_ordinal") != replay_ordinal
            or record.get("arm_id") != arm_id
            or record.get("planning_input_sha256") != planning_hash
        ):
            raise EvidenceDrift("downstream planning invocation drifted")
        solve_payload = store.load("solve", planning_hash)
        certificate = solve_payload.get("certificate")
        if not isinstance(certificate, Mapping) or canonical_sha256(
            dict(certificate)
        ) != record.get("certificate_sha256"):
            raise EvidenceDrift("downstream planning certificate drifted")
        incumbent_present = certificate.get("incumbent_capacity") is not None
        if incumbent_present:
            primal = store.load("primal", planning_hash)
            native_log_sha256 = solve_payload.get("native_log_sha256")
            if not isinstance(native_log_sha256, str):
                raise EvidenceDrift("downstream planning native log drifted")
            native_log = store.load_blob("solver_log", native_log_sha256)
            replayed = replay_primal_evidence(
                lambda: build_arm_planning_model(inputs, arm_id),
                primal,
                expected_arm_id=arm_id,
                certificate=certificate,
                native_log=native_log,
                feasibility_tolerance=specification.feasibility_tolerance,
            )
            persisted_replay = store.load("primal_replay", planning_hash)
            if canonical_json_bytes(replayed) != canonical_json_bytes(persisted_replay):
                raise EvidenceDrift("downstream fresh-model primal replay drifted")
        replay_ordinal += 1
        return certificate

    from experiments import (
        run_rq2_joint_deliverability_implementation_v2 as reference_runner,
    )

    replayed_frontier = reference_runner.execute_capacity_stage(
        dict(design),
        training_power_blocks=training_power,
        training_workload_blocks=training_workload,
        solver_specification=solver_specification,
        solve_callback=replay_callback,
    )
    if replay_ordinal != len(indexed_records) or canonical_json_bytes(
        replayed_frontier
    ) != canonical_json_bytes(capacity_frontier):
        raise EvidenceDrift("downstream capacity frontier replay drifted")
    expected_calls = _expected_planning_calls(capacity_frontier)
    if len(indexed_records) != len(expected_calls):
        raise EvidenceDrift("planning evidence authority drifted")
    for ordinal, (record, expected) in enumerate(
        zip(indexed_records, expected_calls, strict=True)
    ):
        expected_hash = expected["planning_input_sha256"]
        if (
            not isinstance(record, Mapping)
            or set(record)
            != {
                "planning_input_sha256",
                "arm_id",
                "invocation_ordinal",
                "solve_role",
                "certificate_sha256",
                "solve_object_sha256",
                "output_indices",
            }
            or record.get("invocation_ordinal") != ordinal
            or record.get("arm_id") != expected["arm_id"]
            or record.get("solve_role") != expected["solve_role"]
            or record.get("certificate_sha256") != expected["certificate_sha256"]
            or record.get("output_indices") != expected["output_indices"]
            or not isinstance(record.get("planning_input_sha256"), str)
            or _HEX_DIGEST.fullmatch(record["planning_input_sha256"]) is None
            or (
                expected_hash is not None
                and record["planning_input_sha256"] != expected_hash
            )
        ):
            raise EvidenceDrift("planning index record drifted")
        planning_hash = record["planning_input_sha256"]
        solve_payload = store.load("solve", planning_hash)
        certificate = solve_payload.get("certificate")
        if (
            set(solve_payload)
            != {
                "schema",
                "planning_input_sha256",
                "arm_id",
                "certificate",
                "native_log_sha256",
                "primal_pointer",
                "replay_pointer",
            }
            or solve_payload.get("schema")
            != "rq2_joint_deliverability_native_solve_record_v1"
            or solve_payload.get("planning_input_sha256") != planning_hash
            or solve_payload.get("arm_id") != record["arm_id"]
            or not isinstance(certificate, Mapping)
            or canonical_sha256(dict(certificate)) != record["certificate_sha256"]
            or canonical_sha256(solve_payload) != record["solve_object_sha256"]
        ):
            raise EvidenceDrift("planning solve object drifted")
        native_log_sha256 = solve_payload.get("native_log_sha256")
        if (
            not isinstance(native_log_sha256, str)
            or _HEX_DIGEST.fullmatch(native_log_sha256) is None
        ):
            raise EvidenceDrift("planning native log binding drifted")
        store.load_blob("solver_log", native_log_sha256)
        order_payload = store.load("solve_order", f"s{ordinal:06d}")
        if order_payload != {
            "schema": "rq2_joint_deliverability_solve_order_v1",
            "invocation_ordinal": ordinal,
            "planning_input_sha256": planning_hash,
            "arm_id": record["arm_id"],
            "certificate_sha256": record["certificate_sha256"],
            "solve_object_sha256": record["solve_object_sha256"],
        }:
            raise EvidenceDrift("planning solve-order object drifted")
        incumbent_present = certificate.get("incumbent_capacity") is not None
        primal_pointer = solve_payload.get("primal_pointer")
        replay_pointer = solve_payload.get("replay_pointer")
        if incumbent_present != (
            primal_pointer is not None and replay_pointer is not None
        ):
            raise EvidenceDrift("planning primal/replay closure drifted")
        for stage, pointer in (
            ("primal", primal_pointer),
            ("primal_replay", replay_pointer),
        ):
            if pointer is None:
                continue
            if (
                not isinstance(pointer, Mapping)
                or pointer.get("schema")
                != "rq2_joint_deliverability_checkpoint_pointer_v1"
                or pointer.get("run_identity_sha256") != store.run_identity_sha256
                or pointer.get("stage") != stage
                or pointer.get("key") != planning_hash
                or not isinstance(pointer.get("object_sha256"), str)
                or _HEX_DIGEST.fullmatch(pointer["object_sha256"]) is None
            ):
                raise EvidenceDrift("planning nested pointer drifted")
            nested = store.load(stage, planning_hash)
            if canonical_sha256(nested) != pointer["object_sha256"]:
                raise EvidenceDrift("planning nested object drifted")
            if (
                nested.get("arm_id") != record["arm_id"]
                or nested.get("certificate_sha256") != record["certificate_sha256"]
                or nested.get("native_log_sha256") != native_log_sha256
                or (stage == "primal_replay" and nested.get("passed") is not True)
            ):
                raise EvidenceDrift("planning nested evidence binding drifted")
    expected_solve_keys = tuple(
        sorted(
            {str(record["planning_input_sha256"]) for record in indexed_records},
            key=str.encode,
        )
    )
    expected_order_keys = tuple(
        f"s{ordinal:06d}" for ordinal in range(len(indexed_records))
    )
    expected_primal_keys = tuple(
        sorted(
            {
                str(record["planning_input_sha256"])
                for record in indexed_records
                if store.load("solve", str(record["planning_input_sha256"]))[
                    "certificate"
                ].get("incumbent_capacity")
                is not None
            },
            key=str.encode,
        )
    )
    if (
        store.keys("input_audit") != ("registered",)
        or store.keys("solve") != expected_solve_keys
        or store.keys("solve_order") != expected_order_keys
        or store.keys("primal") != expected_primal_keys
        or store.keys("primal_replay") != expected_primal_keys
    ):
        raise EvidenceDrift("planning evidence key inventory drifted")
    return {
        "input_audit_object_sha256": input_audit_sha256,
        "planning_index_object_sha256": canonical_sha256(planning_index),
    }


def _registered_training_support(
    registered_input_audit: Mapping[str, object],
    training_power_blocks: Sequence[PowerBlock],
    training_workload_blocks: Sequence[WorkloadBlock],
) -> tuple[tuple[PowerBlock, ...], tuple[WorkloadBlock, ...]]:
    packages = registered_input_audit.get("packages")
    if (
        registered_input_audit.get("schema")
        != "rq2_joint_deliverability_input_audit_v1"
        or registered_input_audit.get("registered_inputs_ready") is not True
        or not isinstance(packages, Mapping)
        or not isinstance(packages.get("dispatched_grid"), Mapping)
        or not isinstance(packages.get("workload"), Mapping)
        or packages["dispatched_grid"].get("status") != "verified"
        or packages["workload"].get("status") != "verified"
        or packages["dispatched_grid"].get("training_block_inventory_sha256")
        != power_block_inventory_sha256(training_power_blocks)
        or packages["workload"].get("training_block_inventory_sha256")
        != workload_block_inventory_sha256(training_workload_blocks)
    ):
        raise EvidenceDrift("training blocks do not match audited input authority")
    power = tuple(
        sorted(training_power_blocks, key=lambda block: block.block_id.encode())
    )
    workload = tuple(
        sorted(training_workload_blocks, key=lambda block: block.block_id.encode())
    )
    if (
        len(power) != 541
        or len(workload) != 34
        or any(block.split != "training" for block in power)
        or any(block.split != "training" for block in workload)
        or not math.isclose(
            math.fsum(block.probability for block in power),
            1.0,
            rel_tol=0.0,
            abs_tol=1.0e-9,
        )
        or not math.isclose(
            math.fsum(block.probability for block in workload),
            1.0,
            rel_tol=0.0,
            abs_tol=1.0e-9,
        )
    ):
        raise EvidenceDrift("registered training block inventory drifted")
    return power, workload


def _stream_holdout_stage_from_audit(
    design: Mapping[str, object],
    *,
    capacity_frontier: Mapping[str, object],
    registered_input_audit: Mapping[str, object],
    training_power_blocks: tuple[PowerBlock, ...],
    holdout_power_blocks: tuple[PowerBlock, ...],
    training_workload_blocks: tuple[WorkloadBlock, ...],
    holdout_workload_blocks: tuple[WorkloadBlock, ...],
    store: EvidenceStore,
) -> dict[str, object]:
    """Validate the complete V5 holdout inventory, then stream its chunks."""

    _validate_stage_store(
        store,
        allowed_stages=_HOLDOUT_EVIDENCE_STAGES,
        allowed_blob_namespaces={"solver_log"},
    )
    power, workload = _registered_holdout_support(
        registered_input_audit,
        holdout_power_blocks,
        holdout_workload_blocks,
    )
    if store.keys("holdout_summary") not in {(), ("registered",)}:
        raise EvidenceDrift("holdout summary inventory contains an extra key")
    expected_cells = expand_registered_cells(dict(design))
    capacity_rows = capacity_frontier.get("cells")
    if (
        capacity_frontier.get("schema")
        != "rq2_joint_deliverability_capacity_frontier_v3"
        or capacity_frontier.get("cell_count") != 46
        or capacity_frontier.get("arm_output_count") != 184
        or not isinstance(capacity_rows, Sequence)
        or isinstance(capacity_rows, (str, bytes))
        or len(capacity_rows) != len(expected_cells)
    ):
        raise EvidenceDrift("capacity frontier formal inventory drifted")
    for row, cell in zip(capacity_rows, expected_cells, strict=True):
        arms = row.get("arms")
        if (
            row.get("cell_id") != cell.cell_id
            or row.get("family") != cell.family
            or canonical_json_bytes(row.get("parameters"))
            != canonical_json_bytes(asdict(cell))
            or not isinstance(arms, Mapping)
            or set(arms) != set(FOUR_ARM_IDS)
            or any(
                not isinstance(arms[arm_id], Mapping)
                or arms[arm_id].get("arm_id") != arm_id
                for arm_id in FOUR_ARM_IDS
            )
        ):
            raise EvidenceDrift("capacity frontier row/arm identity drifted")
    planning_authority = _registered_planning_evidence(
        store,
        design=design,
        registered_input_audit=registered_input_audit,
        training_power_blocks=training_power_blocks,
        training_workload_blocks=training_workload_blocks,
        capacity_frontier_sha256=canonical_sha256(dict(capacity_frontier)),
    )
    input_audit_pointer = _commit_registered_input_audit(
        store,
        registered_input_audit,
    )
    summary = _stream_holdout_stage(
        design,
        capacity_frontier=capacity_frontier,
        holdout_power_blocks=power,
        holdout_workload_blocks=workload,
        store=store,
        commit=False,
    )
    payload = {
        **summary,
        "registered_input_audit_sha256": canonical_sha256(dict(registered_input_audit)),
        "scientific_design_sha256": canonical_sha256(dict(design)),
        "capacity_frontier_sha256": canonical_sha256(dict(capacity_frontier)),
        "input_audit_object_sha256": input_audit_pointer["object_sha256"],
        "planning_index_object_sha256": planning_authority[
            "planning_index_object_sha256"
        ],
    }
    if store.keys("holdout_summary") == ("registered",):
        if len(store.keys("holdout")) != summary[
            "trajectory_chunk_count"
        ] or canonical_json_bytes(
            store.load("holdout_summary", "registered")
        ) != canonical_json_bytes(payload):
            raise EvidenceDrift("existing holdout summary is incomplete or drifted")
        _validate_stage_store(
            store,
            allowed_stages=_HOLDOUT_EVIDENCE_STAGES,
            allowed_blob_namespaces={"solver_log"},
        )
        return payload
    committed_summary = _stream_holdout_stage(
        design,
        capacity_frontier=capacity_frontier,
        holdout_power_blocks=power,
        holdout_workload_blocks=workload,
        store=store,
        commit=True,
    )
    if canonical_json_bytes(committed_summary) != canonical_json_bytes(summary):
        raise EvidenceDrift("holdout prevalidation and commit summaries differ")
    store.commit("holdout_summary", "registered", payload)
    _validate_stage_store(
        store,
        allowed_stages=_HOLDOUT_EVIDENCE_STAGES,
        allowed_blob_namespaces={"solver_log"},
    )
    return payload


def stream_holdout_stage(
    *,
    capacity_frontier: Mapping[str, object],
    store: EvidenceStore,
) -> dict[str, object]:
    """Reject execution until a fresh-process activation successor exists."""

    del capacity_frontier, store
    raise ExecutionBlocked(
        "execution successor v1 public stage is closed pending fresh-process activation"
    )


def _registered_bootstrap_cells(
    store: EvidenceStore,
    *,
    design: Mapping[str, object],
    registered_input_audit: Mapping[str, object],
    training_power_blocks: Sequence[PowerBlock],
    power_blocks: Sequence[PowerBlock],
    training_workload_blocks: Sequence[WorkloadBlock],
    workload_blocks: Sequence[WorkloadBlock],
) -> tuple[tuple[str, ...], dict[str, str], dict[str, str]]:
    if store.keys("holdout_summary") != ("registered",):
        raise EvidenceDrift("holdout summary authority is absent or ambiguous")
    summary = store.load("holdout_summary", "registered")
    persisted_input_audit = store.load("input_audit", "registered")
    persisted_input_audit_sha256 = canonical_sha256(persisted_input_audit)
    registered_cells = expand_registered_cells(dict(design))
    expected_cells = tuple(cell.cell_id for cell in registered_cells)
    finite_power, _ = condition_finite_power(power_blocks)
    finite_ids = sorted((block.block_id for block in finite_power), key=str.encode)
    e0_ids = sorted(
        (
            block.block_id
            for block in power_blocks
            if block.state == "exogenous_grid_infeasibility"
        ),
        key=str.encode,
    )
    e0_mass = math.fsum(
        block.probability
        for block in power_blocks
        if block.state == "exogenous_grid_infeasibility"
    )
    workload_ids = sorted(
        (block.block_id for block in workload_blocks),
        key=str.encode,
    )
    rows = summary.get("cells")
    planning_authority = _registered_planning_evidence(
        store,
        design=design,
        registered_input_audit=registered_input_audit,
        training_power_blocks=training_power_blocks,
        training_workload_blocks=training_workload_blocks,
        capacity_frontier_sha256=str(summary.get("capacity_frontier_sha256")),
    )
    if (
        summary.get("schema") != "rq2_joint_deliverability_holdout_stream_v1"
        or persisted_input_audit != dict(registered_input_audit)
        or summary.get("input_audit_object_sha256") != persisted_input_audit_sha256
        or summary.get("planning_index_object_sha256")
        != planning_authority["planning_index_object_sha256"]
        or summary.get("scientific_design_sha256") != canonical_sha256(dict(design))
        or summary.get("registered_input_audit_sha256")
        != canonical_sha256(dict(registered_input_audit))
        or not isinstance(summary.get("capacity_frontier_sha256"), str)
        or _HEX_DIGEST.fullmatch(summary["capacity_frontier_sha256"]) is None
        or summary.get("finite_power_block_ids") != finite_ids
        or summary.get("E0_power_block_ids") != e0_ids
        or summary.get("workload_block_ids") != workload_ids
        or not math.isclose(
            float(summary.get("E0_mass", float("nan"))),
            e0_mass,
            rel_tol=0.0,
            abs_tol=1.0e-12,
        )
        or not isinstance(summary.get("trajectory_chunk_stream_sha256"), str)
        or _HEX_DIGEST.fullmatch(summary["trajectory_chunk_stream_sha256"]) is None
        or not isinstance(rows, Sequence)
        or isinstance(rows, (str, bytes))
        or [str(row["cell_id"]) for row in rows] != list(expected_cells)
    ):
        raise EvidenceDrift("bootstrap holdout-summary authority drifted")
    capacity_frontier = store.load("capacity_frontier", "registered")
    capacity_rows = capacity_frontier.get("cells")
    if (
        not isinstance(capacity_rows, Sequence)
        or isinstance(capacity_rows, (str, bytes))
        or len(capacity_rows) != len(registered_cells)
    ):
        raise EvidenceDrift("bootstrap capacity frontier inventory drifted")
    finite_power = tuple(sorted(finite_power, key=lambda item: item.block_id.encode()))
    workloads = tuple(sorted(workload_blocks, key=lambda item: item.block_id.encode()))
    expected_rows = []
    expected_holdout_keys: set[str] = set()
    digest_stream = hashlib.sha256()
    for capacity_row, cell in zip(
        capacity_rows,
        registered_cells,
        strict=True,
    ):
        raw_arms = capacity_row.get("arms")
        eligible = _holdout_cell_is_evaluable(raw_arms)
        status = (
            "not_evaluable_capacity_unresolved"
            if not eligible
            else (
                "resolved"
                if finite_power
                else "finite_service_identification_unresolved"
            )
        )
        expected_rows.append(
            {
                "cell_id": cell.cell_id,
                "status": status,
                "chunk_count": len(finite_power) if status == "resolved" else 0,
            }
        )
        if status != "resolved":
            continue
        assert isinstance(raw_arms, Mapping)
        for power in finite_power:
            key = f"{cell.cell_id}__{power.block_id}"
            expected_holdout_keys.add(key)
            expected_chunk = _holdout_chunk_payload(
                design,
                cell=cell,
                raw_arms=raw_arms,
                power=power,
                workloads=workloads,
            )
            observed_chunk = store.load("holdout", key)
            if canonical_json_bytes(observed_chunk) != canonical_json_bytes(
                expected_chunk
            ):
                raise EvidenceDrift("holdout chunk drifted from sealed live inputs")
            digest_stream.update(
                (
                    f"{cell.cell_id}/{power.block_id}\0"
                    f"{canonical_sha256(observed_chunk)}\n"
                ).encode()
            )
    if set(store.keys("holdout")) != expected_holdout_keys:
        raise EvidenceDrift("holdout checkpoint inventory drifted")
    statuses = {str(row["cell_id"]): str(row["status"]) for row in expected_rows}
    if (
        list(rows) != expected_rows
        or summary.get("trajectory_chunk_count") != len(expected_holdout_keys)
        or summary.get("trajectory_chunk_stream_sha256") != digest_stream.hexdigest()
    ):
        raise EvidenceDrift("bootstrap holdout summary/chunk closure drifted")
    return (
        tuple(cell_id for cell_id in expected_cells if statuses[cell_id] == "resolved"),
        statuses,
        planning_authority,
    )


def _registered_metrics_from_arms(
    arms: Mapping[str, object],
) -> dict[str, float]:
    prefixes = {
        "network_only_shared": "network_only",
        "cfe_only_shared": "cfe_only",
        "joint_correct_shared": "joint_correct",
        "joint_b6_separate_planning_shared_execution": "joint_b6",
    }
    result: dict[str, float] = {}
    metrics_by_arm: dict[str, Mapping[str, object]] = {}
    for arm_id, prefix in prefixes.items():
        arm = arms.get(arm_id)
        if not isinstance(arm, Mapping):
            raise EvidenceDrift("holdout replay arm inventory drifted")
        metrics = arm.get("metrics")
        if not isinstance(metrics, Mapping):
            raise EvidenceDrift("holdout replay metrics are absent")
        metrics_by_arm[arm_id] = metrics
        for source, suffix in (
            ("joint_service_failure", "joint_service_failure"),
            ("hard_grid_failure", "hard_grid_failure"),
            ("cfe_service_failure", "cfe_service_failure"),
            ("total_service_shortfall", "total_service_shortfall"),
            ("cfe_shortfall", "cfe_shortfall"),
        ):
            result[f"{prefix}_{suffix}"] = float(metrics[source])
    correct = metrics_by_arm["joint_correct_shared"]
    b6 = metrics_by_arm["joint_b6_separate_planning_shared_execution"]
    result.update(
        {
            "B6_minus_correct_joint_service_failure": float(b6["joint_service_failure"])
            - float(correct["joint_service_failure"]),
            "B6_minus_correct_total_service_shortfall": float(
                b6["total_service_shortfall"]
            )
            - float(correct["total_service_shortfall"]),
            "B6_minus_correct_cfe_shortfall": float(b6["cfe_shortfall"])
            - float(correct["cfe_shortfall"]),
        }
    )
    if set(result) != set(REGISTERED_METRICS):
        raise EvidenceDrift("registered metric replay inventory drifted")
    return result


def replay_holdout_metric_matrices(
    store: EvidenceStore,
    *,
    cell_id: str,
    power_ids: Sequence[str],
    workload_ids: Sequence[str],
    time_step_hours: float,
    tolerance: float,
    terminal_recovery_debt_limit: float,
) -> dict[str, dict[tuple[str, str], float]]:
    """Rebuild one cell's metric matrices only from persisted trajectories."""

    matrices = {metric: {} for metric in REGISTERED_METRICS}
    ordered_power = sorted(power_ids, key=str.encode)
    ordered_workload = sorted(workload_ids, key=str.encode)
    for power_id in ordered_power:
        chunk = store.load("holdout", f"{cell_id}__{power_id}")
        if chunk.get("cell_id") != cell_id or chunk.get("power_block_id") != power_id:
            raise EvidenceDrift("holdout chunk identity drifted")
        workloads = chunk.get("workloads")
        if (
            not isinstance(workloads, Sequence)
            or [str(item["workload_block_id"]) for item in workloads]
            != ordered_workload
        ):
            raise EvidenceDrift("holdout chunk workload inventory drifted")
        policy = chunk.get("policy_parameters")
        if (
            not isinstance(policy, Mapping)
            or float(policy.get("time_step_hours", float("nan"))) != time_step_hours
            or float(policy.get("service_shortfall_tolerance", float("nan")))
            != tolerance
            or float(policy.get("terminal_recovery_debt_limit", float("nan")))
            != terminal_recovery_debt_limit
        ):
            raise EvidenceDrift("holdout replay policy binding drifted")
        independently_replayed_arms: dict[str, dict[str, object]] = {}
        for item in workloads:
            workload_id = str(item["workload_block_id"])
            arms = item["arms"]
            independently_replayed_arms = {}
            for arm_id in FOUR_ARM_IDS:
                arm = arms[arm_id]
                replayed = execute_holdout_policy(
                    committed_capacity=float(arm["capacity"]),
                    grid_request=arm["raw_grid_request"],
                    cfe_request=arm["raw_cfe_request"],
                    available_flexibility=item["available_flexibility"],
                    connected_demand=item["connected_demand"],
                    current_recovery_headroom=arm["recovery_headroom"],
                    maximum_recovery_power=float(policy["maximum_recovery_power"]),
                    recovery_efficiency=float(policy["recovery_efficiency"]),
                    maximum_event_duration_hours=float(
                        policy["maximum_event_duration_hours"]
                    ),
                    maximum_event_count=int(policy["maximum_event_count"]),
                    minimum_recovery_hours=float(policy["minimum_recovery_hours"]),
                    normalized_energy_budget=float(policy["normalized_energy_budget"]),
                    normalized_debt_limit=float(policy["normalized_debt_limit"]),
                    terminal_recovery_debt_limit=float(
                        policy["terminal_recovery_debt_limit"]
                    ),
                    time_step_hours=float(policy["time_step_hours"]),
                    minimum_event_power=float(policy["minimum_event_power"]),
                    curtailment_ramp_per_hour=float(
                        policy["curtailment_ramp_per_hour"]
                    ),
                    response_time_hours=float(policy["response_time_hours"]),
                    service_shortfall_tolerance=float(
                        policy["service_shortfall_tolerance"]
                    ),
                )
                if canonical_json_bytes(replayed["trajectory"]) != canonical_json_bytes(
                    arm["trajectory"]
                ):
                    raise EvidenceDrift("holdout policy replay drifted")
                if canonical_json_bytes(replayed["metrics"]) != canonical_json_bytes(
                    arm["metrics"]
                ):
                    raise EvidenceDrift("holdout metrics replay drifted")
                independent_metrics = metrics_from_trajectory(
                    replayed["trajectory"],
                    time_step_hours=time_step_hours,
                    tolerance=tolerance,
                    terminal_recovery_debt_limit=terminal_recovery_debt_limit,
                )
                if canonical_json_bytes(independent_metrics) != canonical_json_bytes(
                    arm["metrics"]
                ):
                    raise EvidenceDrift(
                        "holdout metrics do not independently replay from trajectory"
                    )
                independently_replayed_arms[arm_id] = {"metrics": independent_metrics}
            metrics = _registered_metrics_from_arms(independently_replayed_arms)
            for metric, metric_value in metrics.items():
                matrices[metric][(power_id, workload_id)] = metric_value
    expected_pairs = {
        (power_id, workload_id)
        for power_id in ordered_power
        for workload_id in ordered_workload
    }
    if any(set(values) != expected_pairs for values in matrices.values()):
        raise EvidenceDrift("holdout metric matrix is incomplete")
    return matrices


def _holdout_chunk_stream_sha256(
    store: EvidenceStore,
    *,
    cell_id: str,
    power_ids: Sequence[str],
) -> str:
    digest = hashlib.sha256()
    for power_id in sorted(power_ids, key=str.encode):
        chunk = store.load("holdout", f"{cell_id}__{power_id}")
        if chunk.get("cell_id") != cell_id or chunk.get("power_block_id") != power_id:
            raise EvidenceDrift("metric-matrix holdout source identity drifted")
        digest.update((f"{cell_id}/{power_id}\0{canonical_sha256(chunk)}\n").encode())
    return digest.hexdigest()


def commit_holdout_metric_matrices(
    store: EvidenceStore,
    *,
    cell_id: str,
    power_ids: Sequence[str],
    workload_ids: Sequence[str],
    matrices: Mapping[str, Mapping[tuple[str, str], float]],
) -> dict[str, object]:
    """Persist one cell's complete metric tensor as canonical float64 evidence."""

    cell = _safe_component(cell_id, "cell ID")
    ordered_power = tuple(sorted(power_ids, key=str.encode))
    ordered_workload = tuple(sorted(workload_ids, key=str.encode))
    if (
        len(set(ordered_power)) != len(ordered_power)
        or len(set(ordered_workload)) != len(ordered_workload)
        or set(matrices) != set(REGISTERED_METRICS)
    ):
        raise EvidenceDrift("holdout metric-matrix inventory drifted")
    values = np.empty(
        (len(REGISTERED_METRICS), len(ordered_power), len(ordered_workload)),
        dtype="<f8",
    )
    expected_pairs = {
        (power_id, workload_id)
        for power_id in ordered_power
        for workload_id in ordered_workload
    }
    for metric_index, metric in enumerate(REGISTERED_METRICS):
        metric_values = matrices[metric]
        if set(metric_values) != expected_pairs:
            raise EvidenceDrift("holdout metric matrix is incomplete")
        for power_index, power_id in enumerate(ordered_power):
            for workload_index, workload_id in enumerate(ordered_workload):
                value_ = float(metric_values[(power_id, workload_id)])
                if not math.isfinite(value_):
                    raise EvidenceDrift("holdout metric matrix is nonfinite")
                values[metric_index, power_index, workload_index] = value_
    holdout_chunk_stream_sha256 = _holdout_chunk_stream_sha256(
        store,
        cell_id=cell,
        power_ids=ordered_power,
    )
    blob_sha256 = store.put_blob("metric_matrix_values", values.tobytes(order="C"))
    payload = {
        "schema": "rq2_joint_deliverability_metric_matrix_v1",
        "cell_id": cell,
        "registered_metrics": list(REGISTERED_METRICS),
        "power_ids": list(ordered_power),
        "workload_ids": list(ordered_workload),
        "dtype": "float64_little_endian",
        "shape": list(values.shape),
        "holdout_chunk_stream_sha256": holdout_chunk_stream_sha256,
        "values_blob_sha256": blob_sha256,
    }
    return store.commit("metric_matrix", cell, payload)


def load_holdout_metric_matrices(
    store: EvidenceStore,
    *,
    cell_id: str,
    power_ids: Sequence[str],
    workload_ids: Sequence[str],
) -> tuple[dict[str, dict[tuple[str, str], float]], str]:
    """Load and verify one persisted metric tensor and return its object digest."""

    cell = _safe_component(cell_id, "cell ID")
    ordered_power = tuple(sorted(power_ids, key=str.encode))
    ordered_workload = tuple(sorted(workload_ids, key=str.encode))
    payload = store.load("metric_matrix", cell)
    expected_shape = (
        len(REGISTERED_METRICS),
        len(ordered_power),
        len(ordered_workload),
    )
    blob_sha256 = payload.get("values_blob_sha256")
    if (
        payload.get("schema") != "rq2_joint_deliverability_metric_matrix_v1"
        or payload.get("cell_id") != cell
        or payload.get("registered_metrics") != list(REGISTERED_METRICS)
        or payload.get("power_ids") != list(ordered_power)
        or payload.get("workload_ids") != list(ordered_workload)
        or payload.get("dtype") != "float64_little_endian"
        or payload.get("shape") != list(expected_shape)
        or payload.get("holdout_chunk_stream_sha256")
        != _holdout_chunk_stream_sha256(
            store,
            cell_id=cell,
            power_ids=ordered_power,
        )
        or not isinstance(blob_sha256, str)
        or _HEX_DIGEST.fullmatch(blob_sha256) is None
    ):
        raise EvidenceDrift("persisted metric-matrix identity drifted")
    raw = store.load_blob("metric_matrix_values", blob_sha256)
    if len(raw) != math.prod(expected_shape) * 8:
        raise EvidenceDrift("persisted metric-matrix byte length drifted")
    values = np.frombuffer(raw, dtype="<f8").reshape(expected_shape)
    if not bool(np.isfinite(values).all()):
        raise EvidenceDrift("persisted metric matrix is nonfinite")
    matrices = {
        metric: {
            (power_id, workload_id): float(
                values[metric_index, power_index, workload_index]
            )
            for power_index, power_id in enumerate(ordered_power)
            for workload_index, workload_id in enumerate(ordered_workload)
        }
        for metric_index, metric in enumerate(REGISTERED_METRICS)
    }
    return matrices, canonical_sha256(payload)


def replay_and_commit_holdout_metric_matrices(
    store: EvidenceStore,
    *,
    cell_id: str,
    power_ids: Sequence[str],
    workload_ids: Sequence[str],
    time_step_hours: float,
    tolerance: float,
    terminal_recovery_debt_limit: float,
) -> tuple[dict[str, dict[tuple[str, str], float]], str]:
    """Recompute from holdout chunks before accepting any persisted matrix."""

    matrices = replay_holdout_metric_matrices(
        store,
        cell_id=cell_id,
        power_ids=power_ids,
        workload_ids=workload_ids,
        time_step_hours=time_step_hours,
        tolerance=tolerance,
        terminal_recovery_debt_limit=terminal_recovery_debt_limit,
    )
    pointer = commit_holdout_metric_matrices(
        store,
        cell_id=cell_id,
        power_ids=power_ids,
        workload_ids=workload_ids,
        matrices=matrices,
    )
    persisted, object_sha256 = load_holdout_metric_matrices(
        store,
        cell_id=cell_id,
        power_ids=power_ids,
        workload_ids=workload_ids,
    )
    if object_sha256 != pointer["object_sha256"] or persisted != matrices:
        raise EvidenceDrift("metric-matrix persistence replay drifted")
    return persisted, object_sha256


def bootstrap_draw_stream_sha256(draws: Sequence[Mapping[str, object]]) -> str:
    """Bind exact bootstrap draw order and collapsed marginal values."""

    for expected, draw in enumerate(draws):
        if draw.get("replicate") != expected:
            raise EvidenceDrift("bootstrap draw order drifted")
    return canonical_sha256(list(draws))


def _registered_bootstrap_draws(
    bootstrap_contract: Mapping[str, object],
    *,
    power_ids: Sequence[str],
    power_probabilities: Sequence[float],
    workload_ids: Sequence[str],
    workload_probabilities: Sequence[float],
) -> tuple[tuple[dict[str, object], ...], str]:
    if canonical_sha256(dict(bootstrap_contract)) != (
        _REGISTERED_BOOTSTRAP_CONTRACT_SHA256
    ):
        raise EvidenceDrift("bootstrap contract drifted from sealed V5 authority")
    probe = bootstrap_contract.get("deterministic_probe")
    generator = bootstrap_contract.get("pseudorandom_generator")
    if not isinstance(probe, Mapping) or not isinstance(generator, Mapping):
        raise EvidenceDrift("bootstrap RNG contract is malformed")
    probe_raw = bootstrap_raw_draw_stream(
        probe["power_IDs"],
        probe["power_probabilities"],
        probe["workload_IDs"],
        probe["workload_probabilities"],
        power_draw_count=int(probe["power_draw_count"]),
        workload_draw_count=int(probe["workload_draw_count"]),
        replicates=int(probe["replicates"]),
        seed=int(generator["seed"]),
    )
    if bootstrap_draw_stream_sha256(probe_raw) != probe.get(
        "canonical_draw_payload_sha256"
    ):
        raise EvidenceDrift("bootstrap deterministic RNG probe drifted")
    replicates = int(bootstrap_contract["replicate_count"])
    seed = int(generator["seed"])
    raw_draws = bootstrap_raw_draw_stream(
        power_ids,
        power_probabilities,
        workload_ids,
        workload_probabilities,
        power_draw_count=530,
        workload_draw_count=34,
        replicates=replicates,
        seed=seed,
    )
    collapsed_draws = bootstrap_draw_stream(
        power_ids,
        power_probabilities,
        workload_ids,
        workload_probabilities,
        power_draw_count=530,
        workload_draw_count=34,
        replicates=replicates,
        seed=seed,
    )
    if len(raw_draws) != replicates or len(collapsed_draws) != replicates:
        raise EvidenceDrift("bootstrap draw count drifted")
    return collapsed_draws, bootstrap_draw_stream_sha256(raw_draws)


def commit_bootstrap_cell(
    store: EvidenceStore,
    *,
    replicate: int,
    cell_id: str,
    endpoint_invocation_start_ordinal: int,
    draw_stream_sha256: str,
    input_audit_object_sha256: str,
    planning_index_object_sha256: str,
    metric_matrix_sha256: str,
    endpoints: Mapping[str, Mapping[str, object]],
) -> dict[str, object]:
    """Commit one resumable replicate/cell endpoint checkpoint."""

    if (
        isinstance(replicate, bool)
        or not isinstance(replicate, int)
        or replicate < 0
        or isinstance(endpoint_invocation_start_ordinal, bool)
        or not isinstance(endpoint_invocation_start_ordinal, int)
        or endpoint_invocation_start_ordinal < 0
        or endpoint_invocation_start_ordinal % (len(REGISTERED_METRICS) * 2) != 0
        or _HEX_DIGEST.fullmatch(draw_stream_sha256) is None
        or _HEX_DIGEST.fullmatch(input_audit_object_sha256) is None
        or _HEX_DIGEST.fullmatch(planning_index_object_sha256) is None
        or _HEX_DIGEST.fullmatch(metric_matrix_sha256) is None
    ):
        raise ValueError("bootstrap checkpoint identity is invalid")
    if set(endpoints) != set(REGISTERED_METRICS):
        raise EvidenceDrift("bootstrap metric inventory drifted")
    normalized: dict[str, dict[str, object]] = {}
    for metric in REGISTERED_METRICS:
        interval = endpoints[metric]
        if not isinstance(interval, Mapping) or set(interval) != {
            "lower",
            "upper",
            "certificate",
        }:
            raise EvidenceDrift("bootstrap endpoint schema drifted")
        lower = float(interval["lower"])
        upper = float(interval["upper"])
        if not math.isfinite(lower) or not math.isfinite(upper) or lower > upper:
            raise EvidenceDrift("bootstrap endpoint interval is invalid")
        certificate = interval["certificate"]
        if (
            not isinstance(certificate, Mapping)
            or certificate.get("schema")
            != "rq2_joint_deliverability_transport_certificate_v3"
            or certificate.get("metric") != metric
            or certificate.get("resolved") is not True
            or not isinstance(certificate.get("lower"), Mapping)
            or not isinstance(certificate.get("upper"), Mapping)
            or certificate["lower"].get("value") != lower.hex()
            or certificate["upper"].get("value") != upper.hex()
        ):
            raise EvidenceDrift("bootstrap transport certificate drifted")
        normalized[metric] = {
            "lower": lower,
            "upper": upper,
            "certificate": dict(certificate),
        }
    cell = _safe_component(cell_id, "cell ID")
    invocation_count = len(REGISTERED_METRICS) * 2
    payload = {
        "schema": "rq2_joint_deliverability_bootstrap_cell_v2",
        "replicate": replicate,
        "cell_id": cell,
        "endpoint_invocation_start_ordinal": endpoint_invocation_start_ordinal,
        "endpoint_invocation_count": invocation_count,
        "endpoint_invocation_end_ordinal_exclusive": (
            endpoint_invocation_start_ordinal + invocation_count
        ),
        "endpoint_iteration_order": ("registered_metric_order_then_lower_then_upper"),
        "draw_stream_sha256": draw_stream_sha256,
        "input_audit_object_sha256": input_audit_object_sha256,
        "planning_index_object_sha256": planning_index_object_sha256,
        "metric_matrix_sha256": metric_matrix_sha256,
        "endpoints": normalized,
    }
    return store.commit("bootstrap", f"r{replicate:03d}__{cell}", payload)


def _hex_float(raw: object, label: str) -> float:
    if not isinstance(raw, str):
        raise EvidenceDrift(f"{label} is not float.hex text")
    try:
        result = float.fromhex(raw)
    except ValueError as error:
        raise EvidenceDrift(f"{label} is invalid") from error
    if not math.isfinite(result):
        raise EvidenceDrift(f"{label} is nonfinite")
    return result


def _validate_transport_evidence(
    certificate: Mapping[str, object],
    *,
    metric_name: str,
    row_probabilities: Sequence[float],
    column_probabilities: Sequence[float],
    metric_matrix: Sequence[Sequence[float]],
) -> tuple[float, float]:
    rows = len(row_probabilities)
    columns = len(column_probabilities)
    if (
        rows == 0
        or columns == 0
        or len(metric_matrix) != rows
        or any(len(row) != columns for row in metric_matrix)
    ):
        raise EvidenceDrift("transport replay dimensions drifted")
    if (
        certificate.get("schema") != "rq2_joint_deliverability_transport_certificate_v3"
        or certificate.get("metric") != metric_name
        or certificate.get("resolved") is not True
        or certificate.get("sharp") is not True
        or certificate.get("unresolved_reason") is not None
    ):
        raise EvidenceDrift("transport certificate identity drifted")
    values = []
    for extremum in ("lower", "upper"):
        endpoint = certificate.get(extremum)
        if not isinstance(endpoint, Mapping) or set(endpoint) != {
            "coupling_row_major",
            "dual_equality_variables",
            "dual_feasibility_residual",
            "dual_objective_min_form",
            "extremum",
            "marginal_residual",
            "primal_dual_gap",
            "primal_objective_min_form",
            "solver_status",
            "value",
        }:
            raise EvidenceDrift("transport endpoint evidence schema drifted")
        if endpoint["extremum"] != extremum:
            raise EvidenceDrift("transport endpoint label drifted")
        if endpoint["solver_status"] != _TRANSPORT_SOLVER_STATUS:
            raise EvidenceDrift("transport solver status drifted")
        coupling = [
            _hex_float(item, "transport coupling")
            for item in endpoint["coupling_row_major"]
        ]
        dual = [
            _hex_float(item, "transport dual")
            for item in endpoint["dual_equality_variables"]
        ]
        if len(coupling) != rows * columns or len(dual) != rows + columns - 1:
            raise EvidenceDrift("transport evidence vector length drifted")
        if min(coupling) < -1.0e-10:
            raise EvidenceDrift("transport coupling is negative")
        row_residual = max(
            abs(
                math.fsum(coupling[row * columns + column] for column in range(columns))
                - float(row_probabilities[row])
            )
            for row in range(rows)
        )
        column_residual = max(
            abs(
                math.fsum(coupling[row * columns + column] for row in range(rows))
                - float(column_probabilities[column])
            )
            for column in range(columns)
        )
        marginal_residual = max(row_residual, column_residual)
        objective_coefficients = [
            (1.0 if extremum == "lower" else -1.0) * float(metric_matrix[row][column])
            for row in range(rows)
            for column in range(columns)
        ]
        primal = math.fsum(
            coefficient * coupling_value
            for coefficient, coupling_value in zip(
                objective_coefficients,
                coupling,
                strict=True,
            )
        )
        dual_objective = math.fsum(
            float(row_probabilities[row]) * dual[row] for row in range(rows)
        ) + math.fsum(
            float(column_probabilities[column]) * dual[rows + column]
            for column in range(columns - 1)
        )
        dual_residual = max(
            max(
                dual[row]
                + (dual[rows + column] if column < columns - 1 else 0.0)
                - objective_coefficients[row * columns + column],
                0.0,
            )
            for row in range(rows)
            for column in range(columns)
        )
        reported_primal = _hex_float(
            endpoint["primal_objective_min_form"],
            "transport primal objective",
        )
        reported_dual = _hex_float(
            endpoint["dual_objective_min_form"],
            "transport dual objective",
        )
        reported_value = _hex_float(endpoint["value"], "transport endpoint value")
        expected_value = primal if extremum == "lower" else -primal
        primal_dual_gap = abs(primal - dual_objective)
        if (
            abs(primal - reported_primal) > 1.0e-10
            or abs(dual_objective - reported_dual) > 1.0e-10
            or abs(expected_value - reported_value) > 1.0e-10
            or primal_dual_gap > 1.0e-8
            or marginal_residual > 1.0e-8
            or dual_residual > 1.0e-8
            or abs(
                marginal_residual
                - _hex_float(
                    endpoint["marginal_residual"],
                    "transport marginal residual",
                )
            )
            > 1.0e-10
            or abs(
                dual_residual
                - _hex_float(
                    endpoint["dual_feasibility_residual"],
                    "transport dual residual",
                )
            )
            > 1.0e-10
            or abs(
                primal_dual_gap
                - _hex_float(
                    endpoint["primal_dual_gap"],
                    "transport primal-dual gap",
                )
            )
            > 1.0e-10
        ):
            raise EvidenceDrift("transport certificate does not replay")
        values.append(reported_value)
    if values[0] > values[1] + 1.0e-10:
        raise EvidenceDrift("transport interval is reversed")
    return values[0], values[1]


def _bootstrap_replay_context(
    draw: Mapping[str, object],
    *,
    expected_replicate: int,
    state_by_power_id: Mapping[str, str],
) -> tuple[list[str], list[float], list[str], list[float]]:
    if draw.get("replicate") != expected_replicate:
        raise EvidenceDrift("bootstrap replicate order drifted")
    power = draw.get("power")
    workload = draw.get("workload")
    if not isinstance(power, Mapping) or not isinstance(workload, Mapping):
        raise EvidenceDrift("bootstrap draw marginal is malformed")
    conditioning = finite_conditioning(
        list(power),
        [float(power[key]) for key in power],
        state_by_power_id,
    )
    if conditioning["status"] != "resolved":
        raise EvidenceDrift("bootstrap aggregate contains empty finite support")
    finite_ids = [str(item) for item in conditioning["finite_row_ids"]]
    row_probabilities = [
        float(item) for item in conditioning["finite_row_probabilities"]
    ]
    workload_ids = [
        str(block_id)
        for block_id, probability in workload.items()
        if float(probability) > 0.0
    ]
    raw_column_probabilities = [float(workload[block_id]) for block_id in workload_ids]
    column_total = math.fsum(raw_column_probabilities)
    if column_total <= 0.0:
        raise EvidenceDrift("bootstrap workload support is empty")
    column_probabilities = [
        probability / column_total for probability in raw_column_probabilities
    ]
    return finite_ids, row_probabilities, workload_ids, column_probabilities


def _validate_bootstrap_checkpoint(
    store: EvidenceStore,
    *,
    key: str,
    replicate: int,
    cell_id: str,
    endpoint_invocation_start_ordinal: int,
    draw_stream_sha256: str,
    input_audit_object_sha256: str,
    planning_index_object_sha256: str,
    metric_matrix_sha256: str,
    matrices: Mapping[str, Mapping[tuple[str, str], float]],
    replay_context: tuple[list[str], list[float], list[str], list[float]],
) -> Mapping[str, object]:
    payload = store.load("bootstrap", key)
    if (
        set(payload)
        != {
            "schema",
            "replicate",
            "cell_id",
            "endpoint_invocation_start_ordinal",
            "endpoint_invocation_count",
            "endpoint_invocation_end_ordinal_exclusive",
            "endpoint_iteration_order",
            "draw_stream_sha256",
            "input_audit_object_sha256",
            "planning_index_object_sha256",
            "metric_matrix_sha256",
            "endpoints",
        }
        or payload.get("schema") != "rq2_joint_deliverability_bootstrap_cell_v2"
        or payload.get("replicate") != replicate
        or payload.get("cell_id") != cell_id
        or payload.get("endpoint_invocation_start_ordinal")
        != endpoint_invocation_start_ordinal
        or payload.get("endpoint_invocation_count") != len(REGISTERED_METRICS) * 2
        or payload.get("endpoint_invocation_end_ordinal_exclusive")
        != endpoint_invocation_start_ordinal + len(REGISTERED_METRICS) * 2
        or payload.get("endpoint_iteration_order")
        != "registered_metric_order_then_lower_then_upper"
        or payload.get("draw_stream_sha256") != draw_stream_sha256
        or payload.get("input_audit_object_sha256") != input_audit_object_sha256
        or payload.get("planning_index_object_sha256") != planning_index_object_sha256
        or payload.get("metric_matrix_sha256") != metric_matrix_sha256
    ):
        raise EvidenceDrift("bootstrap checkpoint identity drifted")
    endpoints = payload.get("endpoints")
    if not isinstance(endpoints, Mapping) or set(endpoints) != set(REGISTERED_METRICS):
        raise EvidenceDrift("bootstrap checkpoint metrics drifted")
    finite_ids, row_probabilities, workload_ids, column_probabilities = replay_context
    for metric in REGISTERED_METRICS:
        pair_values = matrices[metric]
        try:
            matrix = [
                [
                    float(pair_values[(power_id, workload_id)])
                    for workload_id in workload_ids
                ]
                for power_id in finite_ids
            ]
        except (KeyError, TypeError, ValueError) as error:
            raise EvidenceDrift("bootstrap checkpoint metric matrix drifted") from error
        interval = endpoints[metric]
        if not isinstance(interval, Mapping):
            raise EvidenceDrift("bootstrap checkpoint endpoint drifted")
        lower, upper = _validate_transport_evidence(
            interval["certificate"],
            metric_name=metric,
            row_probabilities=row_probabilities,
            column_probabilities=column_probabilities,
            metric_matrix=matrix,
        )
        if float(interval["lower"]) != lower or float(interval["upper"]) != upper:
            raise EvidenceDrift("bootstrap checkpoint interval drifted")
    return endpoints


def _aggregate_bootstrap_checkpoints(
    store: EvidenceStore,
    *,
    draws: Sequence[Mapping[str, object]],
    state_by_power_id: Mapping[str, str],
    cell_ids: Sequence[str],
    draw_stream_sha256: str,
    input_audit_object_sha256: str,
    planning_index_object_sha256: str,
    metric_loader: Callable[
        [str],
        tuple[Mapping[str, Mapping[tuple[str, str], float]], str],
    ],
) -> dict[str, object]:
    """Replay every certificate before rebuilding confidence intervals."""

    ordered_cells = tuple(sorted(cell_ids, key=str.encode))
    cell_index = {cell_id: index for index, cell_id in enumerate(ordered_cells)}
    endpoint_count = len(REGISTERED_METRICS) * 2
    replicates = len(draws)
    replay_contexts = []
    first_empty_replicate: int | None = None
    for replicate, draw in enumerate(draws):
        try:
            replay_contexts.append(
                _bootstrap_replay_context(
                    draw,
                    expected_replicate=replicate,
                    state_by_power_id=state_by_power_id,
                )
            )
        except EvidenceDrift as error:
            if str(error) != "bootstrap aggregate contains empty finite support":
                raise
            first_empty_replicate = replicate
            break
    expected_keys = tuple(
        f"r{replicate:03d}__{cell_id}"
        for replicate in range(len(replay_contexts))
        for cell_id in ordered_cells
    )
    if store.keys("bootstrap") != tuple(sorted(expected_keys, key=str.encode)):
        raise EvidenceDrift("bootstrap checkpoint inventory is incomplete")
    matrix_keys = store.keys("metric_matrix")
    if not set(matrix_keys).issubset(set(ordered_cells)):
        raise EvidenceDrift("bootstrap metric-matrix inventory is incomplete")
    if first_empty_replicate is None and matrix_keys != tuple(
        sorted(ordered_cells, key=str.encode)
    ):
        raise EvidenceDrift("bootstrap metric-matrix inventory is incomplete")
    checkpoint_cells = {key.split("__", maxsplit=1)[1] for key in expected_keys}
    if not checkpoint_cells.issubset(set(matrix_keys)):
        raise EvidenceDrift("bootstrap checkpoint lacks its metric matrix")
    intervals: dict[str, dict[str, dict[str, list[float]]]] = {}
    cells_to_validate = (
        ordered_cells
        if first_empty_replicate is None
        else tuple(sorted(matrix_keys, key=str.encode))
    )
    for cell_id in cells_to_validate:
        cell_samples = {
            metric: {"lower": [], "upper": []} for metric in REGISTERED_METRICS
        }
        matrices, metric_matrix_sha256 = metric_loader(cell_id)
        if (
            set(matrices) != set(REGISTERED_METRICS)
            or _HEX_DIGEST.fullmatch(metric_matrix_sha256) is None
        ):
            raise EvidenceDrift("bootstrap aggregate metric inventory drifted")
        for replicate, context in enumerate(replay_contexts):
            key = f"r{replicate:03d}__{cell_id}"
            if key not in expected_keys:
                continue
            endpoints = _validate_bootstrap_checkpoint(
                store,
                key=key,
                replicate=replicate,
                cell_id=cell_id,
                endpoint_invocation_start_ordinal=(
                    (replicate * len(ordered_cells) + cell_index[cell_id])
                    * endpoint_count
                ),
                draw_stream_sha256=draw_stream_sha256,
                input_audit_object_sha256=input_audit_object_sha256,
                planning_index_object_sha256=planning_index_object_sha256,
                metric_matrix_sha256=metric_matrix_sha256,
                matrices=matrices,
                replay_context=context,
            )
            for metric in REGISTERED_METRICS:
                interval = endpoints[metric]
                cell_samples[metric]["lower"].append(float(interval["lower"]))
                cell_samples[metric]["upper"].append(float(interval["upper"]))
        if first_empty_replicate is None:
            intervals[cell_id] = {
                metric: {
                    endpoint: [
                        float(item)
                        for item in np.quantile(
                            np.asarray(values, dtype=np.float64),
                            q=[0.025, 0.975],
                            axis=0,
                            method="linear",
                        )
                    ]
                    for endpoint, values in by_endpoint.items()
                }
                for metric, by_endpoint in cell_samples.items()
            }
    if first_empty_replicate is not None:
        return {
            "schema": "rq2_joint_deliverability_bootstrap_aggregate_v1",
            "status": "unresolved",
            "reason": "finite_service_identification_unresolved",
            "replicates": replicates,
            "completed_replicates": len(replay_contexts),
            "first_empty_finite_replicate": first_empty_replicate,
            "cell_ids": list(ordered_cells),
            "draw_stream_sha256": draw_stream_sha256,
            "input_audit_object_sha256": input_audit_object_sha256,
            "planning_index_object_sha256": planning_index_object_sha256,
            "intervals": {},
        }
    return {
        "schema": "rq2_joint_deliverability_bootstrap_aggregate_v1",
        "replicates": replicates,
        "cell_ids": list(ordered_cells),
        "draw_stream_sha256": draw_stream_sha256,
        "input_audit_object_sha256": input_audit_object_sha256,
        "planning_index_object_sha256": planning_index_object_sha256,
        "intervals": intervals,
    }


def _aggregate_bootstrap_checkpoints_from_audit(
    store: EvidenceStore,
    *,
    design: Mapping[str, object],
    registered_input_audit: Mapping[str, object],
    training_power_blocks: Sequence[PowerBlock],
    holdout_power_blocks: Sequence[PowerBlock],
    training_workload_blocks: Sequence[WorkloadBlock],
    holdout_workload_blocks: Sequence[WorkloadBlock],
) -> dict[str, object]:
    """Regenerate sealed V5 draws and replay checkpoints into confidence intervals."""

    _validate_stage_store(
        store,
        allowed_stages=_BOOTSTRAP_EVIDENCE_STAGES,
        allowed_blob_namespaces={"solver_log", "metric_matrix_values"},
    )
    power, workload = _registered_holdout_support(
        registered_input_audit,
        holdout_power_blocks,
        holdout_workload_blocks,
    )
    cell_ids, cell_statuses, planning_authority = _registered_bootstrap_cells(
        store,
        design=design,
        registered_input_audit=registered_input_audit,
        training_power_blocks=training_power_blocks,
        power_blocks=power,
        training_workload_blocks=training_workload_blocks,
        workload_blocks=workload,
    )
    power_ids = [block.block_id for block in power]
    power_probabilities = [block.probability for block in power]
    workload_ids = [block.block_id for block in workload]
    workload_probabilities = [block.probability for block in workload]
    state_by_power_id = {block.block_id: block.state for block in power}
    bootstrap_contract = design.get("bootstrap_contract")
    if not isinstance(bootstrap_contract, Mapping):
        raise EvidenceDrift("registered bootstrap contract is absent")
    draws, draw_sha = _registered_bootstrap_draws(
        bootstrap_contract,
        power_ids=power_ids,
        power_probabilities=power_probabilities,
        workload_ids=workload_ids,
        workload_probabilities=workload_probabilities,
    )
    non_evaluable = sorted(
        (cell_id for cell_id, status in cell_statuses.items() if status != "resolved"),
        key=str.encode,
    )
    finite_power, _ = condition_finite_power(power)
    finite_power_ids = [block.block_id for block in finite_power]
    temporal = design.get("temporal_envelope")
    data_contract = design.get("data_contract")
    if not isinstance(temporal, Mapping) or not isinstance(data_contract, Mapping):
        raise EvidenceDrift("holdout replay contract is absent")
    if set(store.keys("metric_matrix")) != set(cell_ids):
        raise EvidenceDrift("unregistered metric-matrix checkpoint exists")

    def metric_loader(
        cell_id: str,
    ) -> tuple[Mapping[str, Mapping[tuple[str, str], float]], str]:
        replayed = replay_holdout_metric_matrices(
            store,
            cell_id=cell_id,
            power_ids=finite_power_ids,
            workload_ids=workload_ids,
            time_step_hours=float(data_contract["time_step_hours"]),
            tolerance=float(temporal["service_shortfall_tolerance"]),
            terminal_recovery_debt_limit=float(
                temporal["terminal_recovery_debt_limit"]
            ),
        )
        persisted, matrix_sha256 = load_holdout_metric_matrices(
            store,
            cell_id=cell_id,
            power_ids=finite_power_ids,
            workload_ids=workload_ids,
        )
        if replayed != persisted:
            raise EvidenceDrift("bootstrap aggregate metric matrix drifted")
        return persisted, matrix_sha256

    aggregate = _aggregate_bootstrap_checkpoints(
        store,
        draws=draws,
        state_by_power_id=state_by_power_id,
        cell_ids=cell_ids,
        draw_stream_sha256=draw_sha,
        input_audit_object_sha256=planning_authority["input_audit_object_sha256"],
        planning_index_object_sha256=planning_authority["planning_index_object_sha256"],
        metric_loader=metric_loader,
    )
    aggregate_unresolved = aggregate.get("status") == "unresolved"
    result = {
        **aggregate,
        "status": (
            "unresolved" if aggregate_unresolved or non_evaluable else "resolved"
        ),
        "reason": (
            aggregate.get("reason")
            if aggregate_unresolved
            else (None if not non_evaluable else "non_evaluable_holdout_cells")
        ),
        "cell_statuses": cell_statuses,
        "non_evaluable_cell_ids": non_evaluable,
    }
    _validate_stage_store(
        store,
        allowed_stages=_BOOTSTRAP_EVIDENCE_STAGES,
        allowed_blob_namespaces={"solver_log", "metric_matrix_values"},
    )
    return result


def aggregate_bootstrap_checkpoints(
    store: EvidenceStore,
) -> dict[str, object]:
    """Reject execution until a fresh-process activation successor exists."""

    del store
    raise ExecutionBlocked(
        "execution successor v1 public stage is closed pending fresh-process activation"
    )


def _execute_bootstrap_draws(
    *,
    draws: Sequence[Mapping[str, object]],
    draw_stream_sha256: str,
    state_by_power_id: Mapping[str, str],
    cell_ids: Sequence[str],
    input_audit_object_sha256: str,
    planning_index_object_sha256: str,
    metric_loader: Callable[
        [str],
        tuple[Mapping[str, Mapping[tuple[str, str], float]], str],
    ],
    metric_prevalidator: Callable[
        [str],
        tuple[Mapping[str, Mapping[tuple[str, str], float]], str],
    ],
    store: EvidenceStore,
    endpoint_solver: Callable[..., object] = certify_scalar_transport,
) -> dict[str, object]:
    """Execute an already internally generated bootstrap stream."""

    if (
        _HEX_DIGEST.fullmatch(draw_stream_sha256) is None
        or _HEX_DIGEST.fullmatch(input_audit_object_sha256) is None
        or _HEX_DIGEST.fullmatch(planning_index_object_sha256) is None
    ):
        raise EvidenceDrift("bootstrap draw-stream authority is invalid")
    draw_sha = draw_stream_sha256
    ordered_cells = tuple(sorted(cell_ids, key=str.encode))
    cell_index = {cell_id: index for index, cell_id in enumerate(ordered_cells)}
    endpoint_count = len(REGISTERED_METRICS) * 2
    solver_calls = 0
    resumed = 0
    committed = 0
    existing_bootstrap_keys = set(store.keys("bootstrap"))
    possible_bootstrap_keys = tuple(
        f"r{replicate:03d}__{cell_id}"
        for replicate in range(len(draws))
        for cell_id in ordered_cells
    )
    if not existing_bootstrap_keys.issubset(set(possible_bootstrap_keys)):
        raise EvidenceDrift("bootstrap checkpoint inventory contains an extra key")
    existing_metric_keys = set(store.keys("metric_matrix"))
    if not existing_metric_keys.issubset(set(ordered_cells)):
        raise EvidenceDrift("metric-matrix inventory contains an extra key")
    replay_contexts = []
    first_empty_replicate: int | None = None
    for expected_replicate, draw in enumerate(draws):
        try:
            replay_contexts.append(
                _bootstrap_replay_context(
                    draw,
                    expected_replicate=expected_replicate,
                    state_by_power_id=state_by_power_id,
                )
            )
        except EvidenceDrift as error:
            if str(error) != "bootstrap aggregate contains empty finite support":
                raise
            first_empty_replicate = expected_replicate
            break
    allowed_existing_keys = tuple(
        f"r{replicate:03d}__{cell_id}"
        for replicate in range(len(replay_contexts))
        for cell_id in ordered_cells
    )
    if not existing_bootstrap_keys.issubset(set(allowed_existing_keys)):
        raise EvidenceDrift("bootstrap checkpoint exists after empty finite support")
    checkpoint_cells = {
        key.split("__", maxsplit=1)[1] for key in existing_bootstrap_keys
    }
    if not checkpoint_cells.issubset(existing_metric_keys):
        raise EvidenceDrift("bootstrap checkpoint lacks its metric matrix")
    for cell_id in sorted(existing_metric_keys, key=str.encode):
        matrices, metric_matrix_sha256 = metric_prevalidator(cell_id)
        if (
            set(matrices) != set(REGISTERED_METRICS)
            or _HEX_DIGEST.fullmatch(metric_matrix_sha256) is None
        ):
            raise EvidenceDrift("bootstrap prevalidation metric inventory drifted")
        existing_for_cell = [
            replicate
            for replicate in range(len(replay_contexts))
            if f"r{replicate:03d}__{cell_id}" in existing_bootstrap_keys
        ]
        for replicate in existing_for_cell:
            _validate_bootstrap_checkpoint(
                store,
                key=f"r{replicate:03d}__{cell_id}",
                replicate=replicate,
                cell_id=cell_id,
                endpoint_invocation_start_ordinal=(
                    (replicate * len(ordered_cells) + cell_index[cell_id])
                    * endpoint_count
                ),
                draw_stream_sha256=draw_sha,
                input_audit_object_sha256=input_audit_object_sha256,
                planning_index_object_sha256=planning_index_object_sha256,
                metric_matrix_sha256=metric_matrix_sha256,
                matrices=matrices,
                replay_context=replay_contexts[replicate],
            )
    expected_prefix = set(allowed_existing_keys[: len(existing_bootstrap_keys)])
    if existing_bootstrap_keys != expected_prefix:
        raise EvidenceDrift("bootstrap checkpoint inventory is not a prefix")
    resumed = len(existing_bootstrap_keys)
    if first_empty_replicate is not None:
        return {
            "schema": "rq2_joint_deliverability_bootstrap_resume_v1",
            "status": "unresolved",
            "reason": "finite_service_identification_unresolved",
            "replicate": first_empty_replicate,
            "draw_stream_sha256": draw_sha,
            "input_audit_object_sha256": input_audit_object_sha256,
            "planning_index_object_sha256": planning_index_object_sha256,
            "endpoint_solver_calls": solver_calls,
            "resumed_checkpoints": resumed,
            "committed_checkpoints": committed,
            "aggregate": None,
        }
    for expected_replicate, (
        finite_ids,
        row_probabilities,
        workload_ids,
        column_probabilities,
    ) in enumerate(replay_contexts):
        for cell_id in ordered_cells:
            key = f"r{expected_replicate:03d}__{cell_id}"
            if key in existing_bootstrap_keys:
                continue
            matrices, metric_matrix_sha256 = metric_loader(cell_id)
            if (
                set(matrices) != set(REGISTERED_METRICS)
                or _HEX_DIGEST.fullmatch(metric_matrix_sha256) is None
            ):
                raise EvidenceDrift("bootstrap metric loader inventory drifted")
            endpoint_invocation_start_ordinal = (
                expected_replicate * len(ordered_cells) + cell_index[cell_id]
            ) * endpoint_count
            endpoints = {}
            for metric_index, metric in enumerate(REGISTERED_METRICS):
                pair_values = matrices[metric]
                matrix = [
                    [
                        float(pair_values[(power_id, workload_id)])
                        for workload_id in workload_ids
                    ]
                    for power_id in finite_ids
                ]
                certificate = endpoint_solver(
                    row_probabilities,
                    column_probabilities,
                    matrix,
                    metric_name=metric,
                )
                solver_calls += 2
                if (
                    not certificate.resolved
                    or certificate.lower is None
                    or certificate.upper is None
                ):
                    return {
                        "schema": "rq2_joint_deliverability_bootstrap_resume_v1",
                        "status": "unresolved",
                        "reason": "transport_endpoint_unresolved",
                        "replicate": expected_replicate,
                        "cell_id": cell_id,
                        "metric": metric,
                        "endpoint_invocation_ordinal": (
                            endpoint_invocation_start_ordinal + metric_index * 2
                        ),
                        "draw_stream_sha256": draw_sha,
                        "input_audit_object_sha256": input_audit_object_sha256,
                        "planning_index_object_sha256": planning_index_object_sha256,
                        "endpoint_solver_calls": solver_calls,
                        "resumed_checkpoints": resumed,
                        "committed_checkpoints": committed,
                        "aggregate": None,
                    }
                certificate_payload = _json_bytes_mapping(
                    canonical_certificate_payload(certificate),
                    label="generated transport certificate",
                )
                lower, upper = _validate_transport_evidence(
                    certificate_payload,
                    metric_name=metric,
                    row_probabilities=row_probabilities,
                    column_probabilities=column_probabilities,
                    metric_matrix=matrix,
                )
                endpoints[metric] = {
                    "lower": lower,
                    "upper": upper,
                    "certificate": certificate_payload,
                }
            commit_bootstrap_cell(
                store,
                replicate=expected_replicate,
                cell_id=cell_id,
                endpoint_invocation_start_ordinal=(endpoint_invocation_start_ordinal),
                draw_stream_sha256=draw_sha,
                input_audit_object_sha256=input_audit_object_sha256,
                planning_index_object_sha256=planning_index_object_sha256,
                metric_matrix_sha256=metric_matrix_sha256,
                endpoints=endpoints,
            )
            committed += 1
            existing_bootstrap_keys.add(key)
    aggregate = _aggregate_bootstrap_checkpoints(
        store,
        draws=draws,
        state_by_power_id=state_by_power_id,
        cell_ids=ordered_cells,
        draw_stream_sha256=draw_sha,
        input_audit_object_sha256=input_audit_object_sha256,
        planning_index_object_sha256=planning_index_object_sha256,
        metric_loader=metric_loader,
    )
    return {
        "schema": "rq2_joint_deliverability_bootstrap_resume_v1",
        "status": "resolved",
        "draw_stream_sha256": draw_sha,
        "input_audit_object_sha256": input_audit_object_sha256,
        "planning_index_object_sha256": planning_index_object_sha256,
        "endpoint_solver_calls": solver_calls,
        "resumed_checkpoints": resumed,
        "committed_checkpoints": committed,
        "aggregate": aggregate,
    }


def _execute_bootstrap_resumable_from_audit(
    *,
    design: Mapping[str, object],
    registered_input_audit: Mapping[str, object],
    training_power_blocks: Sequence[PowerBlock],
    holdout_power_blocks: Sequence[PowerBlock],
    training_workload_blocks: Sequence[WorkloadBlock],
    holdout_workload_blocks: Sequence[WorkloadBlock],
    store: EvidenceStore,
    endpoint_solver: Callable[..., object] = certify_scalar_transport,
) -> dict[str, object]:
    """Generate the sealed V5 draw stream and resume exact checkpoints."""

    _validate_stage_store(
        store,
        allowed_stages=_BOOTSTRAP_EVIDENCE_STAGES,
        allowed_blob_namespaces={"solver_log", "metric_matrix_values"},
    )
    power, workload = _registered_holdout_support(
        registered_input_audit,
        holdout_power_blocks,
        holdout_workload_blocks,
    )
    cell_ids, cell_statuses, planning_authority = _registered_bootstrap_cells(
        store,
        design=design,
        registered_input_audit=registered_input_audit,
        training_power_blocks=training_power_blocks,
        power_blocks=power,
        training_workload_blocks=training_workload_blocks,
        workload_blocks=workload,
    )
    power_ids = [block.block_id for block in power]
    power_probabilities = [block.probability for block in power]
    workload_ids = [block.block_id for block in workload]
    workload_probabilities = [block.probability for block in workload]
    state_by_power_id = {block.block_id: block.state for block in power}
    bootstrap_contract = design.get("bootstrap_contract")
    if not isinstance(bootstrap_contract, Mapping):
        raise EvidenceDrift("registered bootstrap contract is absent")
    draws, draw_sha = _registered_bootstrap_draws(
        bootstrap_contract,
        power_ids=power_ids,
        power_probabilities=power_probabilities,
        workload_ids=workload_ids,
        workload_probabilities=workload_probabilities,
    )
    finite_power, _ = condition_finite_power(power)
    finite_power_ids = [block.block_id for block in finite_power]
    temporal = design.get("temporal_envelope")
    data_contract = design.get("data_contract")
    if not isinstance(temporal, Mapping) or not isinstance(data_contract, Mapping):
        raise EvidenceDrift("holdout replay contract is absent")
    if not set(store.keys("metric_matrix")).issubset(set(cell_ids)):
        raise EvidenceDrift("unregistered metric-matrix checkpoint exists")

    def metric_loader(
        cell_id: str,
    ) -> tuple[Mapping[str, Mapping[tuple[str, str], float]], str]:
        if cell_id in set(store.keys("metric_matrix")):
            return load_holdout_metric_matrices(
                store,
                cell_id=cell_id,
                power_ids=finite_power_ids,
                workload_ids=workload_ids,
            )
        return replay_and_commit_holdout_metric_matrices(
            store,
            cell_id=cell_id,
            power_ids=finite_power_ids,
            workload_ids=workload_ids,
            time_step_hours=float(data_contract["time_step_hours"]),
            tolerance=float(temporal["service_shortfall_tolerance"]),
            terminal_recovery_debt_limit=float(
                temporal["terminal_recovery_debt_limit"]
            ),
        )

    def metric_prevalidator(
        cell_id: str,
    ) -> tuple[Mapping[str, Mapping[tuple[str, str], float]], str]:
        replayed = replay_holdout_metric_matrices(
            store,
            cell_id=cell_id,
            power_ids=finite_power_ids,
            workload_ids=workload_ids,
            time_step_hours=float(data_contract["time_step_hours"]),
            tolerance=float(temporal["service_shortfall_tolerance"]),
            terminal_recovery_debt_limit=float(
                temporal["terminal_recovery_debt_limit"]
            ),
        )
        persisted, matrix_sha256 = load_holdout_metric_matrices(
            store,
            cell_id=cell_id,
            power_ids=finite_power_ids,
            workload_ids=workload_ids,
        )
        if replayed != persisted:
            raise EvidenceDrift("bootstrap prevalidation metric matrix drifted")
        return persisted, matrix_sha256

    result = _execute_bootstrap_draws(
        draws=draws,
        draw_stream_sha256=draw_sha,
        state_by_power_id=state_by_power_id,
        cell_ids=cell_ids,
        input_audit_object_sha256=planning_authority["input_audit_object_sha256"],
        planning_index_object_sha256=planning_authority["planning_index_object_sha256"],
        metric_loader=metric_loader,
        metric_prevalidator=metric_prevalidator,
        store=store,
        endpoint_solver=endpoint_solver,
    )
    non_evaluable = sorted(
        (cell_id for cell_id, status in cell_statuses.items() if status != "resolved"),
        key=str.encode,
    )
    payload = {
        **result,
        "cell_statuses": cell_statuses,
        "non_evaluable_cell_ids": non_evaluable,
    }
    if non_evaluable and result.get("status") == "resolved":
        payload["status"] = "unresolved"
        payload["reason"] = "non_evaluable_holdout_cells"
    _validate_stage_store(
        store,
        allowed_stages=_BOOTSTRAP_EVIDENCE_STAGES,
        allowed_blob_namespaces={"solver_log", "metric_matrix_values"},
    )
    return payload


def execute_bootstrap_resumable(
    *,
    store: EvidenceStore,
) -> dict[str, object]:
    """Reject execution until a fresh-process activation successor exists."""

    del store
    raise ExecutionBlocked(
        "execution successor v1 public stage is closed pending fresh-process activation"
    )


def _model_residual(model: object) -> float:
    residual = 0.0
    for constraint in model.component_data_objects(Constraint, active=True):
        body = float(value(constraint.body))
        if not math.isfinite(body):
            return float("inf")
        if constraint.lower is not None:
            residual = max(residual, float(value(constraint.lower)) - body)
        if constraint.upper is not None:
            residual = max(residual, body - float(value(constraint.upper)))
    for variable in model.component_data_objects(Var, active=True):
        raw = float(value(variable))
        if not math.isfinite(raw):
            return float("inf")
        if variable.is_integer():
            residual = max(residual, abs(raw - round(raw)))
        if variable.lb is not None:
            residual = max(residual, float(variable.lb) - raw)
        if variable.ub is not None:
            residual = max(residual, raw - float(variable.ub))
    return max(residual, 0.0)


def _active_objective(model: object) -> float:
    objectives = list(model.component_data_objects(Objective, active=True))
    if len(objectives) != 1:
        raise EvidenceDrift("model must have exactly one active objective")
    result = float(value(objectives[0]))
    if not math.isfinite(result):
        raise EvidenceDrift("model objective is nonfinite")
    return result


def capture_primal_evidence(
    model: object,
    *,
    arm_id: str,
    certificate: Mapping[str, object],
    native_log_path: Path,
    native_log: bytes | None = None,
) -> dict[str, object]:
    """Capture every scalar variable and bind it to native solver evidence."""

    log_bytes = (
        _read_regular_bytes(native_log_path) if native_log is None else native_log
    )
    if not log_bytes:
        raise EvidenceDrift("native solver log is empty")
    variables = {
        variable.name: float(value(variable)).hex()
        for variable in model.component_data_objects(Var, active=True)
    }
    constraints = [
        constraint.name
        for constraint in model.component_data_objects(Constraint, active=True)
    ]
    payload = {
        "schema": "rq2_joint_deliverability_primal_evidence_v1",
        "arm_id": arm_id,
        "objective_hex": _active_objective(model).hex(),
        "maximum_constraint_residual_hex": _model_residual(model).hex(),
        "variables": dict(sorted(variables.items())),
        "constraint_names": sorted(constraints),
        "certificate_sha256": canonical_sha256(dict(certificate)),
        "native_log_sha256": hashlib.sha256(log_bytes).hexdigest(),
        "native_log_bytes": len(log_bytes),
    }
    return payload


def replay_primal_evidence(
    model_factory: Callable[[], object],
    evidence: Mapping[str, object],
    *,
    expected_arm_id: str,
    certificate: Mapping[str, object],
    native_log: bytes,
    feasibility_tolerance: float,
) -> dict[str, object]:
    """Rebuild a fresh model and independently replay the persisted primal."""

    if (
        set(evidence)
        != {
            "schema",
            "arm_id",
            "objective_hex",
            "maximum_constraint_residual_hex",
            "variables",
            "constraint_names",
            "certificate_sha256",
            "native_log_sha256",
            "native_log_bytes",
        }
        or evidence.get("schema") != "rq2_joint_deliverability_primal_evidence_v1"
        or evidence.get("arm_id") != expected_arm_id
        or certificate.get("arm_id") != expected_arm_id
        or evidence.get("certificate_sha256") != canonical_sha256(dict(certificate))
    ):
        raise EvidenceDrift("primal evidence certificate binding drifted")
    if hashlib.sha256(native_log).hexdigest() != evidence.get(
        "native_log_sha256"
    ) or len(native_log) != evidence.get("native_log_bytes"):
        raise EvidenceDrift("native solver log binding drifted")
    model = model_factory()
    variables = {
        variable.name: variable
        for variable in model.component_data_objects(Var, active=True)
    }
    encoded = evidence.get("variables")
    if not isinstance(encoded, Mapping) or set(encoded) != set(variables):
        raise EvidenceDrift("primal variable inventory drifted")
    for name, variable in variables.items():
        raw = encoded[name]
        if not isinstance(raw, str):
            raise EvidenceDrift("primal variable encoding drifted")
        try:
            variable.set_value(float.fromhex(raw), skip_validation=True)
        except (TypeError, ValueError) as error:
            raise EvidenceDrift("primal variable value is invalid") from error
    constraint_names = sorted(
        constraint.name
        for constraint in model.component_data_objects(Constraint, active=True)
    )
    if list(evidence.get("constraint_names", [])) != constraint_names:
        raise EvidenceDrift("primal constraint inventory drifted")
    objective = _active_objective(model)
    if objective.hex() != evidence.get("objective_hex"):
        raise EvidenceDrift("primal objective replay drifted")
    residual = _model_residual(model)
    if residual > feasibility_tolerance:
        raise EvidenceDrift("primal replay violates model constraints")
    recorded_residual = evidence.get("maximum_constraint_residual_hex")
    if not isinstance(recorded_residual, str):
        raise EvidenceDrift("recorded primal residual is invalid")
    if abs(residual - float.fromhex(recorded_residual)) > 1.0e-12:
        raise EvidenceDrift("primal residual replay drifted")
    return {
        "schema": "rq2_joint_deliverability_primal_replay_v1",
        "arm_id": expected_arm_id,
        "certificate_sha256": canonical_sha256(dict(certificate)),
        "native_log_sha256": hashlib.sha256(native_log).hexdigest(),
        "objective": objective,
        "maximum_constraint_residual": residual,
        "variable_count": len(variables),
        "constraint_count": len(constraint_names),
        "passed": True,
    }


def _optional_finite(raw: object | None) -> float | None:
    if raw is None:
        return None
    number = float(raw)
    return number if math.isfinite(number) else None


def planning_input_sha256(
    inputs: JointDeliverabilityPlanningInputs,
    arm_id: str,
    solver_specification: Rq2SolverSpec,
) -> str:
    """Reproduce the sealed implementation-v2 planning-input identity."""

    scenarios = []
    for scenario in inputs.scenarios:
        payload = {
            "name": scenario.name,
            "power_block_id": scenario.power_block_id,
            "workload_block_id": scenario.workload_block_id,
            "probability": scenario.probability,
            "raw_grid_request": scenario.raw_grid_request,
            "effective_grid_request": scenario.effective_grid_request,
            "available_flexibility": scenario.available_flexibility,
            "connected_demand": scenario.connected_demand,
            "business_recovery_headroom": scenario.business_recovery_headroom,
        }
        if arm_id != NETWORK_ONLY_SHARED:
            payload.update(
                {
                    "raw_cfe_request": scenario.raw_cfe_request,
                    "effective_cfe_request": scenario.effective_cfe_request,
                    "cfe_service_recovery_headroom": (
                        scenario.cfe_service_recovery_headroom
                    ),
                }
            )
        scenarios.append(payload)
    scalar_inputs = {
        key: value for key, value in asdict(inputs).items() if key != "scenarios"
    }
    return canonical_sha256(
        {
            "arm_id": arm_id,
            "scenarios": scenarios,
            "planning_parameters": scalar_inputs,
            "solver_specification": asdict(solver_specification),
        }
    )


def _solve_arm_with_native_evidence(
    inputs: JointDeliverabilityPlanningInputs,
    arm_id: str,
    solver_specification: Rq2SolverSpec,
    *,
    store: EvidenceStore,
    solve_driver: Callable[
        [object, Rq2SolverSpec, Mapping[str, float | int], Path],
        tuple[object, str],
    ]
    | None = None,
    model_factory: Callable[
        [JointDeliverabilityPlanningInputs, str],
        object,
    ] = build_arm_planning_model,
) -> dict[str, object]:
    """Solve one arm and atomically persist native log, primal, and replay."""

    model = model_factory(inputs, arm_id)
    scale = model_scale(model)
    options = solver_options(solver_specification)
    evidence_key = planning_input_sha256(
        inputs,
        arm_id,
        solver_specification,
    )
    with tempfile.TemporaryDirectory(dir=store.root) as temporary:
        native_log_path = Path(temporary) / "native_solver.log"
        if solve_driver is None:
            solver, observed_options = create_solver(solver_specification)
            if observed_options != options:
                raise EvidenceDrift("solver option construction drifted")
            result = solver.solve(
                model,
                tee=solver_specification.tee,
                load_solutions=False,
                options=options,
                logfile=str(native_log_path),
            )
            observed_version = version(_SOLVER_PACKAGE[solver_specification.name])
        else:
            result, observed_version = solve_driver(
                model,
                solver_specification,
                options,
                native_log_path,
            )
        if observed_version != solver_specification.expected_package_version:
            raise EvidenceDrift("native solver package version drifted")
        log_bytes = _read_regular_bytes(native_log_path)
        if not log_bytes:
            raise EvidenceDrift("native solver log is empty")
        log_sha256 = store.put_blob("solver_log", log_bytes)
        termination = result.solver.termination_condition
        lower = _optional_finite(result.problem.lower_bound)
        upper = _optional_finite(result.problem.upper_bound)
        result_has_solution = len(result.solution) > 0
        if result_has_solution:
            model.solutions.load_from(result)
        has_solution = result_has_solution or solve_driver is not None
        incumbent = _optional_finite(value(model.capacity)) if has_solution else None
        residual = _model_residual(model) if has_solution else None
        absolute_gap = (
            upper - lower if upper is not None and lower is not None else None
        )
        relative_gap = (
            absolute_gap / max(abs(incumbent), 1.0e-12)
            if absolute_gap is not None and incumbent is not None
            else None
        )
        incumbent_feasible = bool(
            incumbent is not None
            and result.solver.status in {SolverStatus.ok, SolverStatus.warning}
            and incumbent
            <= inputs.maximum_flexibility_budget
            + solver_specification.feasibility_tolerance
            and residual is not None
            and residual <= solver_specification.feasibility_tolerance
            and (lower is None or lower <= incumbent)
            and (
                upper is None
                or abs(upper - incumbent) <= solver_specification.feasibility_tolerance
            )
        )
        resolved = bool(
            termination in _OPTIMAL
            and incumbent_feasible
            and lower is not None
            and upper is not None
            and result.solver.status == SolverStatus.ok
            and lower <= upper
            and absolute_gap is not None
            and absolute_gap >= 0.0
            and relative_gap is not None
            and relative_gap <= solver_specification.mip_relative_gap + 1.0e-12
        )
        proven_infeasible = bool(
            not has_solution
            and termination in _PROVEN_INFEASIBLE
            and result.solver.status in {SolverStatus.ok, SolverStatus.warning}
        )
        certificate = ArmPlanningCertificate(
            arm_id=arm_id,
            status=(
                "candidate_resolved"
                if resolved
                else (
                    "proven_infeasible_at_registered_cap_estimand_undefined"
                    if proven_infeasible
                    else "unresolved"
                )
            ),
            incumbent_capacity=incumbent if incumbent_feasible else None,
            objective_lower_bound=None if proven_infeasible else lower,
            objective_upper_bound=None if proven_infeasible else upper,
            absolute_gap=None if proven_infeasible else absolute_gap,
            incumbent_relative_gap=(
                relative_gap if incumbent_feasible and not proven_infeasible else None
            ),
            maximum_constraint_residual=residual,
            termination_condition=(
                str(termination)
                if resolved or termination not in _OPTIMAL
                else "solution_audit_failed"
            ),
            solver_status=str(result.solver.status),
            model_variables=scale.variables,
            model_constraints=scale.constraints,
            solver_name=solver_specification.name,
            solver_version=observed_version,
            solver_options=options,
        )
        certificate_payload = asdict(certificate)
        primal_pointer = None
        replay_pointer = None
        if incumbent_feasible:
            primal = capture_primal_evidence(
                model,
                arm_id=arm_id,
                certificate=certificate_payload,
                native_log_path=native_log_path,
                native_log=log_bytes,
            )
            primal_pointer = store.commit("primal", evidence_key, primal)
            replay = replay_primal_evidence(
                lambda: model_factory(inputs, arm_id),
                primal,
                expected_arm_id=arm_id,
                certificate=certificate_payload,
                native_log=log_bytes,
                feasibility_tolerance=solver_specification.feasibility_tolerance,
            )
            replay_pointer = store.commit("primal_replay", evidence_key, replay)
        solve_payload = {
            "schema": "rq2_joint_deliverability_native_solve_record_v1",
            "planning_input_sha256": evidence_key,
            "arm_id": arm_id,
            "certificate": certificate_payload,
            "native_log_sha256": log_sha256,
            "primal_pointer": primal_pointer,
            "replay_pointer": replay_pointer,
        }
        solve_pointer = store.commit("solve", evidence_key, solve_payload)
        return {
            "certificate": certificate,
            "planning_evidence_key": evidence_key,
            "native_log_sha256": log_sha256,
            "primal_pointer": primal_pointer,
            "replay_pointer": replay_pointer,
            "solve_pointer": solve_pointer,
        }


def _commit_planning_evidence_index_from_audit(
    design: Mapping[str, object],
    *,
    capacity_frontier: Mapping[str, object],
    solve_records: Sequence[Mapping[str, object]],
    registered_input_audit: Mapping[str, object],
    training_power_blocks: tuple[PowerBlock, ...],
    training_workload_blocks: tuple[WorkloadBlock, ...],
    solver_specification: Rq2SolverSpec,
    store: EvidenceStore,
) -> dict[str, object]:
    """Bind every native solve record to its implementation-v2 output index."""

    training_power, training_workload = _registered_training_support(
        registered_input_audit,
        training_power_blocks,
        training_workload_blocks,
    )
    input_audit_pointer = _commit_registered_input_audit(
        store,
        registered_input_audit,
    )
    expected_cell_ids = [cell.cell_id for cell in expand_registered_cells(dict(design))]
    cells = capacity_frontier.get("cells")
    if (
        capacity_frontier.get("schema")
        != "rq2_joint_deliverability_capacity_frontier_v3"
        or capacity_frontier.get("cell_count") != 46
        or capacity_frontier.get("arm_output_count") != 184
        or not isinstance(cells, Sequence)
        or isinstance(cells, (str, bytes))
        or [str(cell["cell_id"]) for cell in cells] != expected_cell_ids
    ):
        raise EvidenceDrift("capacity frontier output inventory drifted")

    ordered_records = sorted(
        solve_records,
        key=lambda record: int(record.get("invocation_ordinal", -1)),
    )
    derived_invocations: list[dict[str, str]] = []
    replay_ordinal = 0

    def replay_callback(
        inputs: JointDeliverabilityPlanningInputs,
        arm_id: str,
        specification: Rq2SolverSpec,
    ) -> Mapping[str, object]:
        nonlocal replay_ordinal
        if replay_ordinal >= len(ordered_records):
            raise EvidenceDrift("capacity invocation replay is incomplete")
        record = ordered_records[replay_ordinal]
        if record.get("invocation_ordinal") != replay_ordinal:
            raise EvidenceDrift("native solve record order drifted")
        certificate = record.get("certificate")
        if hasattr(certificate, "__dataclass_fields__"):
            certificate_payload = asdict(certificate)
        elif isinstance(certificate, Mapping):
            certificate_payload = dict(certificate)
        else:
            raise EvidenceDrift("native solve certificate schema drifted")
        input_sha256 = planning_input_sha256(inputs, arm_id, specification)
        if (
            record.get("planning_evidence_key") != input_sha256
            or certificate_payload.get("arm_id") != arm_id
        ):
            raise EvidenceDrift("native solve invocation input binding drifted")
        incumbent_present = certificate_payload.get("incumbent_capacity") is not None
        primal_pointer = record.get("primal_pointer")
        replay_pointer = record.get("replay_pointer")
        if incumbent_present:
            if not isinstance(primal_pointer, Mapping) or not isinstance(
                replay_pointer,
                Mapping,
            ):
                raise EvidenceDrift("native solve primal/replay closure drifted")
            primal = store.load("primal", input_sha256)
            native_log_sha256 = record.get("native_log_sha256")
            if not isinstance(native_log_sha256, str):
                raise EvidenceDrift("native solve log binding drifted")
            native_log = store.load_blob("solver_log", native_log_sha256)
            replayed = replay_primal_evidence(
                lambda: build_arm_planning_model(inputs, arm_id),
                primal,
                expected_arm_id=arm_id,
                certificate=certificate_payload,
                native_log=native_log,
                feasibility_tolerance=specification.feasibility_tolerance,
            )
            persisted_replay = store.load("primal_replay", input_sha256)
            if canonical_json_bytes(replayed) != canonical_json_bytes(persisted_replay):
                raise EvidenceDrift("native solve fresh-model replay drifted")
        elif primal_pointer is not None or replay_pointer is not None:
            raise EvidenceDrift("native solve primal/replay closure drifted")
        derived_invocations.append(
            {
                "arm_id": arm_id,
                "planning_input_sha256": input_sha256,
                "certificate_sha256": canonical_sha256(certificate_payload),
            }
        )
        replay_ordinal += 1
        return certificate_payload

    from experiments import (
        run_rq2_joint_deliverability_implementation_v2 as reference_runner,
    )

    replayed_frontier = reference_runner.execute_capacity_stage(
        dict(design),
        training_power_blocks=training_power,
        training_workload_blocks=training_workload,
        solver_specification=solver_specification,
        solve_callback=replay_callback,
    )
    if replay_ordinal != len(ordered_records) or canonical_json_bytes(
        replayed_frontier
    ) != canonical_json_bytes(capacity_frontier):
        raise EvidenceDrift("capacity frontier invocation replay drifted")

    expected_calls = _expected_planning_calls(capacity_frontier)
    if len(solve_records) != len(expected_calls):
        raise EvidenceDrift("capacity solver-call accounting drifted")

    if len(derived_invocations) != len(expected_calls):
        raise EvidenceDrift("capacity invocation replay count drifted")
    for derived, expected_call in zip(
        derived_invocations,
        expected_calls,
        strict=True,
    ):
        if (
            derived["arm_id"] != expected_call["arm_id"]
            or derived["certificate_sha256"] != expected_call["certificate_sha256"]
        ):
            raise EvidenceDrift("capacity invocation replay order drifted")
        expected_call["planning_input_sha256"] = derived["planning_input_sha256"]

    indexed_records = []
    for expected_ordinal, (record, expected_call) in enumerate(
        zip(ordered_records, expected_calls, strict=True)
    ):
        if (
            set(record)
            != {
                "certificate",
                "planning_evidence_key",
                "native_log_sha256",
                "primal_pointer",
                "replay_pointer",
                "solve_pointer",
                "invocation_ordinal",
                "order_pointer",
            }
            or record["invocation_ordinal"] != expected_ordinal
        ):
            raise EvidenceDrift("native solve record order drifted")
        certificate = record["certificate"]
        if hasattr(certificate, "__dataclass_fields__"):
            certificate_payload = asdict(certificate)
        elif isinstance(certificate, Mapping):
            certificate_payload = dict(certificate)
        else:
            raise EvidenceDrift("native solve certificate schema drifted")
        arm_id = str(certificate_payload.get("arm_id"))
        planning_hash = str(record["planning_evidence_key"])
        if (
            arm_id not in FOUR_ARM_IDS
            or _HEX_DIGEST.fullmatch(planning_hash) is None
            or not isinstance(record["native_log_sha256"], str)
            or _HEX_DIGEST.fullmatch(record["native_log_sha256"]) is None
            or arm_id != expected_call["arm_id"]
            or canonical_sha256(certificate_payload)
            != expected_call["certificate_sha256"]
            or planning_hash != expected_call["planning_input_sha256"]
        ):
            raise EvidenceDrift("native solve record identity drifted")
        order_payload = store.load("solve_order", f"s{expected_ordinal:06d}")
        expected_order_payload = {
            "schema": "rq2_joint_deliverability_solve_order_v1",
            "invocation_ordinal": expected_ordinal,
            "planning_input_sha256": planning_hash,
            "arm_id": arm_id,
            "certificate_sha256": canonical_sha256(certificate_payload),
            "solve_object_sha256": record["solve_pointer"]["object_sha256"],
        }
        if order_payload != expected_order_payload:
            raise EvidenceDrift("native solve order evidence drifted")
        if record["order_pointer"] != {
            "schema": "rq2_joint_deliverability_checkpoint_pointer_v1",
            "run_identity_sha256": store.run_identity_sha256,
            "stage": "solve_order",
            "key": f"s{expected_ordinal:06d}",
            "object_sha256": canonical_sha256(order_payload),
        }:
            raise EvidenceDrift("native solve order pointer drifted")
        solve_payload = store.load("solve", planning_hash)
        if solve_payload != {
            "schema": "rq2_joint_deliverability_native_solve_record_v1",
            "planning_input_sha256": planning_hash,
            "arm_id": arm_id,
            "certificate": certificate_payload,
            "native_log_sha256": record["native_log_sha256"],
            "primal_pointer": record["primal_pointer"],
            "replay_pointer": record["replay_pointer"],
        }:
            raise EvidenceDrift("persisted native solve record drifted")
        expected_solve_pointer = {
            "schema": "rq2_joint_deliverability_checkpoint_pointer_v1",
            "run_identity_sha256": store.run_identity_sha256,
            "stage": "solve",
            "key": planning_hash,
            "object_sha256": canonical_sha256(solve_payload),
        }
        if record["solve_pointer"] != expected_solve_pointer:
            raise EvidenceDrift("native solve pointer drifted")
        store.load_blob("solver_log", str(record["native_log_sha256"]))
        incumbent_present = certificate_payload.get("incumbent_capacity") is not None
        if incumbent_present != (
            record["primal_pointer"] is not None
            and record["replay_pointer"] is not None
        ):
            raise EvidenceDrift("native solve primal/replay closure drifted")
        for stage, pointer in (
            ("primal", record["primal_pointer"]),
            ("primal_replay", record["replay_pointer"]),
        ):
            if pointer is None:
                continue
            if (
                not isinstance(pointer, Mapping)
                or pointer
                != {
                    "schema": "rq2_joint_deliverability_checkpoint_pointer_v1",
                    "run_identity_sha256": store.run_identity_sha256,
                    "stage": stage,
                    "key": planning_hash,
                    "object_sha256": pointer.get("object_sha256"),
                }
                or not isinstance(pointer.get("object_sha256"), str)
                or _HEX_DIGEST.fullmatch(pointer["object_sha256"]) is None
            ):
                raise EvidenceDrift("native solve nested pointer drifted")
            nested_payload = store.load(stage, planning_hash)
            if canonical_sha256(nested_payload) != pointer["object_sha256"]:
                raise EvidenceDrift("native solve nested object drifted")
            if stage == "primal" and (
                nested_payload.get("arm_id") != arm_id
                or nested_payload.get("certificate_sha256")
                != canonical_sha256(certificate_payload)
                or nested_payload.get("native_log_sha256")
                != record["native_log_sha256"]
            ):
                raise EvidenceDrift("native solve primal binding drifted")
            if stage == "primal_replay" and (
                set(nested_payload)
                != {
                    "schema",
                    "arm_id",
                    "certificate_sha256",
                    "native_log_sha256",
                    "objective",
                    "maximum_constraint_residual",
                    "variable_count",
                    "constraint_count",
                    "passed",
                }
                or nested_payload.get("schema")
                != "rq2_joint_deliverability_primal_replay_v1"
                or nested_payload.get("arm_id") != arm_id
                or nested_payload.get("certificate_sha256")
                != canonical_sha256(certificate_payload)
                or nested_payload.get("native_log_sha256")
                != record["native_log_sha256"]
                or nested_payload.get("passed") is not True
            ):
                raise EvidenceDrift("native solve replay binding drifted")
        certificate_sha = canonical_sha256(certificate_payload)
        indexed_records.append(
            {
                "planning_input_sha256": planning_hash,
                "arm_id": arm_id,
                "invocation_ordinal": expected_ordinal,
                "solve_role": expected_call["solve_role"],
                "certificate_sha256": certificate_sha,
                "solve_object_sha256": record["solve_pointer"]["object_sha256"],
                "output_indices": expected_call["output_indices"],
            }
        )
    capacity_frontier_pointer = store.commit(
        "capacity_frontier",
        "registered",
        dict(capacity_frontier),
    )
    payload = {
        "schema": "rq2_joint_deliverability_planning_evidence_index_v1",
        "capacity_frontier_sha256": canonical_sha256(dict(capacity_frontier)),
        "capacity_frontier_object_sha256": capacity_frontier_pointer["object_sha256"],
        "scientific_design_sha256": canonical_sha256(dict(design)),
        "registered_input_audit_sha256": canonical_sha256(dict(registered_input_audit)),
        "input_audit_object_sha256": input_audit_pointer["object_sha256"],
        "training_power_inventory_sha256": power_block_inventory_sha256(training_power),
        "training_workload_inventory_sha256": workload_block_inventory_sha256(
            training_workload
        ),
        "solve_record_count": len(indexed_records),
        "records": indexed_records,
    }
    return store.commit("planning_index", "capacity_frontier", payload)


class _EvidenceSolvingCallback:
    """Capacity-stage callback that records every native solve and replay."""

    def __init__(self, store: EvidenceStore) -> None:
        self.store = store
        self.records: list[dict[str, object]] = []

    def __call__(
        self,
        inputs: JointDeliverabilityPlanningInputs,
        arm_id: str,
        solver_specification: Rq2SolverSpec,
    ) -> ArmPlanningCertificate:
        record = _solve_arm_with_native_evidence(
            inputs,
            arm_id,
            solver_specification,
            store=self.store,
        )
        ordinal = len(self.records)
        certificate_payload = asdict(record["certificate"])
        order_payload = {
            "schema": "rq2_joint_deliverability_solve_order_v1",
            "invocation_ordinal": ordinal,
            "planning_input_sha256": record["planning_evidence_key"],
            "arm_id": arm_id,
            "certificate_sha256": canonical_sha256(certificate_payload),
            "solve_object_sha256": record["solve_pointer"]["object_sha256"],
        }
        record["invocation_ordinal"] = ordinal
        record["order_pointer"] = self.store.commit(
            "solve_order",
            f"s{ordinal:06d}",
            order_payload,
        )
        self.records.append(record)
        return record["certificate"]


def _execute_planning_stage_with_evidence_from_audit(
    *,
    design: Mapping[str, object],
    registered_input_audit: Mapping[str, object],
    training_power_blocks: Sequence[PowerBlock],
    training_workload_blocks: Sequence[WorkloadBlock],
    store: EvidenceStore,
) -> dict[str, object]:
    """Run the fixed planning pipeline after activation has derived live inputs."""

    _validate_planning_store_prestate(store)
    training_power, training_workload = _registered_training_support(
        registered_input_audit,
        training_power_blocks,
        training_workload_blocks,
    )
    raw_solver_contract = design.get("solver_contract")
    if not isinstance(raw_solver_contract, Mapping):
        raise EvidenceDrift("sealed planning solver contract is absent")
    solver_specification = solver_spec(raw_solver_contract)
    callback = _EvidenceSolvingCallback(store)

    from experiments import (
        run_rq2_joint_deliverability_implementation_v2 as reference_runner,
    )

    capacity_frontier = reference_runner.execute_capacity_stage(
        dict(design),
        training_power_blocks=training_power,
        training_workload_blocks=training_workload,
        solver_specification=solver_specification,
        solve_callback=callback,
    )
    capacity_frontier_sha256 = canonical_sha256(capacity_frontier)
    planning_index_pointer = _commit_planning_evidence_index_from_audit(
        design,
        capacity_frontier=capacity_frontier,
        solve_records=callback.records,
        registered_input_audit=registered_input_audit,
        training_power_blocks=training_power,
        training_workload_blocks=training_workload,
        solver_specification=solver_specification,
        store=store,
    )
    _validate_stage_store(
        store,
        allowed_stages=_PLANNING_EVIDENCE_STAGES,
        allowed_blob_namespaces={"solver_log"},
    )
    planning_authority = _registered_planning_evidence(
        store,
        design=design,
        registered_input_audit=registered_input_audit,
        training_power_blocks=training_power,
        training_workload_blocks=training_workload,
        capacity_frontier_sha256=capacity_frontier_sha256,
    )
    if (
        planning_index_pointer.get("object_sha256")
        != planning_authority["planning_index_object_sha256"]
    ):
        raise EvidenceDrift("planning index publication drifted")
    return {
        "schema": "rq2_joint_deliverability_planning_stage_v1",
        "capacity_frontier": capacity_frontier,
        "capacity_frontier_sha256": capacity_frontier_sha256,
        "planning_index_pointer": planning_index_pointer,
        **planning_authority,
    }


def execute_planning_stage_with_evidence(
    *,
    store: EvidenceStore,
) -> dict[str, object]:
    """Reject execution until a fresh-process activation successor exists."""

    del store
    raise ExecutionBlocked(
        "execution successor v1 public stage is closed pending fresh-process activation"
    )


def run_identity(
    *,
    static_authority_sha256: str,
    execution_outer_sha256: str,
    execution_review_sha256: str,
    grid_manifest_sha256: str,
    runtime_receipt_sha256: str,
    activation_sha256: str,
) -> str:
    """Derive a run identity without accepting a caller-defined trust root."""

    values = {
        "static_authority_sha256": static_authority_sha256,
        "execution_outer_sha256": execution_outer_sha256,
        "execution_review_sha256": execution_review_sha256,
        "grid_manifest_sha256": grid_manifest_sha256,
        "runtime_receipt_sha256": runtime_receipt_sha256,
        "activation_sha256": activation_sha256,
    }
    if any(_HEX_DIGEST.fullmatch(value) is None for value in values.values()):
        raise ValueError("run identity authority contains an invalid digest")
    return canonical_sha256(
        {
            "schema": "rq2_joint_deliverability_run_identity_v2",
            **values,
        }
    )


def streaming_scale_projection(config: Mapping[str, object]) -> dict[str, object]:
    """Report every registered live-set component before runtime measurement."""

    scale = config.get("formal_scale")
    if not isinstance(scale, Mapping):
        raise ExecutionEvidenceError("formal scale contract is malformed")
    workloads = int(scale["workload_holdout_blocks"])
    power_blocks = int(scale["power_holdout_blocks"])
    bootstrap_replicates = int(scale["bootstrap_replicate_cell_checkpoints"]) // int(
        scale["registered_cells"]
    )
    arms = len(FOUR_ARM_IDS)
    metrics = len(REGISTERED_METRICS)
    hours = 24
    trajectory_scalars_per_hour = 16
    trajectory_slots = workloads * arms * hours * trajectory_scalars_per_hour
    metric_matrix_slots = metrics * power_blocks * workloads
    bootstrap_endpoint_slots = metrics * 2 * bootstrap_replicates
    aggregate_interval_slots = int(scale["registered_cells"]) * metrics * 2 * 2
    bootstrap_draw_index_slots = bootstrap_replicates * (power_blocks + workloads)
    numeric_payloads = {
        "trajectory_chunk": trajectory_slots * 8,
        "single_cell_metric_matrices": metric_matrix_slots * 8,
        "single_cell_bootstrap_endpoint_samples": bootstrap_endpoint_slots * 8,
        "aggregate_interval_output": aggregate_interval_slots * 8,
        "complete_bootstrap_draw_indices": bootstrap_draw_index_slots * 8,
    }
    return {
        "schema": "rq2_joint_deliverability_streaming_projection_v1",
        "chunk_axis": "one_cell_one_power_block",
        "maximum_pairs_in_memory": workloads,
        "maximum_trajectories_in_memory": workloads * arms,
        "registered_metric_count": metrics,
        "bootstrap_replicates": bootstrap_replicates,
        "numeric_payload_bytes_by_component": numeric_payloads,
        "minimum_concurrent_numeric_payload_bytes": sum(numeric_payloads.values()),
        "python_object_overhead": {
            "included_in_static_numeric_lower_bound": False,
            "included_in_required_tracemalloc_measurement": True,
            "required_live_objects": [
                "trajectory_chunk_python_graph",
                "canonical_JSON_serialization_buffer",
                "single_cell_metric_matrix_dicts_and_tuple_keys",
                "collapsed_bootstrap_draw_stream",
                "single_cell_bootstrap_endpoint_sample_lists",
            ],
        },
        "independent_of_registered_cell_count": False,
        "independent_of_power_holdout_count": False,
        "registered_dimension_measurement_required": True,
        "static_projection_is_acceptance_evidence": False,
    }


def measure_synthetic_streaming_profile(
    *,
    item_count: int,
    payload_factory: Callable[[int], object],
) -> dict[str, object]:
    """Measure a synthetic one-item-at-a-time serialization working set."""

    if (
        isinstance(item_count, bool)
        or not isinstance(item_count, int)
        or item_count <= 0
    ):
        raise ValueError("synthetic profile item count must be positive")
    digest = hashlib.sha256()
    tracemalloc.start()
    try:
        for index in range(item_count):
            encoded = canonical_json_bytes(payload_factory(index))
            digest.update(encoded)
        current_bytes, peak_bytes = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    return {
        "schema": "rq2_joint_deliverability_synthetic_memory_profile_v1",
        "item_count": item_count,
        "current_bytes": current_bytes,
        "peak_bytes": peak_bytes,
        "stream_sha256": digest.hexdigest(),
        "includes_python_object_overhead": True,
        "includes_serialization_buffers": True,
        "registered_dimension_measurement": False,
        "acceptance_evidence": False,
    }


__all__ = [
    "EvidenceDrift",
    "EvidenceStore",
    "ExecutionBlocked",
    "ExecutionEvidenceError",
    "SplitInventory",
    "aggregate_bootstrap_checkpoints",
    "audit_dispatched_grid_inventory",
    "audit_registered_inputs",
    "audit_split_inventory",
    "bootstrap_draw_stream_sha256",
    "canonical_json_bytes",
    "canonical_sha256",
    "capture_primal_evidence",
    "commit_bootstrap_cell",
    "commit_holdout_chunk",
    "commit_holdout_metric_matrices",
    "derive_static_authority",
    "execute_bootstrap_resumable",
    "execute_planning_stage_with_evidence",
    "load_holdout_metric_matrices",
    "measure_synthetic_streaming_profile",
    "metrics_from_trajectory",
    "planning_input_sha256",
    "power_block_inventory_sha256",
    "replay_and_commit_holdout_metric_matrices",
    "replay_holdout_metric_matrices",
    "replay_primal_evidence",
    "require_safe_existing",
    "run_identity",
    "sha256_file",
    "stream_holdout_stage",
    "streaming_scale_projection",
    "verify_flat_manifest",
    "verify_outer_chain",
    "workload_block_inventory_sha256",
]
