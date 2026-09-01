"""Pure-read validator for the observed RQ2 solver-pilot semantic amendment."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import json
import math
import tarfile
from collections import Counter
from collections.abc import Mapping, Sequence
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
CONFIG_RELATIVE = "configs/rq2_public_solver_pilot_semantic_successor_v1.yaml"
MANIFEST_RELATIVE = (
    "configs/rq2_public_solver_pilot_semantic_successor_v1.SHA256SUMS.json"
)
CONFIG = ROOT / CONFIG_RELATIVE
MANIFEST = ROOT / MANIFEST_RELATIVE
CONFIG_SHA256 = "cb0209a9a53962be8ebb6ee185d3bfbf3d004d7cd761e164b286a58e0c7887b0"
SCHEMA = "rq2_public_solver_pilot_semantic_successor_v1"
STATUS = "observed_pilot_diagnostic_amendment_confirmatory_pilot_required"

PREDECESSOR_HASHES = {
    "configs/rq2_public_executor_bundle_v1.SHA256SUMS.json": (
        "49613e3e400a31ee4888490c5939c4985efaaed3f13325baa1c4bbc28b319f04"
    ),
    "configs/rq2_public_executor_bundle_v2.SHA256SUMS.json": (
        "10129f473a521f37ae0c45bf89a4904c77156c92dcc55837adf91adb8d58e37e"
    ),
    "configs/rq2_public_executor_bundle_v2.OUTER.SHA256SUMS.json": (
        "32bde980733ef80b04571d1fe328c893ff78b4ecb1aee2150c318970707e4942"
    ),
    "configs/rq2_public_solver_pilot_v1.yaml": (
        "bcba9981628001ced20e466632bb33e4d9f44ca3ffad6b24fc8a0761f72c0ec1"
    ),
    "experiments/run_rq2_public_solver_pilot_v1.py": (
        "094f93751c92d95f379ee34f7a236bb7a86a8cb3d81f359d96c5590bcb0cf200"
    ),
    "tests/test_rq2_public_solver_pilot_v1.py": (
        "4aab6b41ab8aa2be68e0cf7cd3878239405334098767ecb772a51a93329db609"
    ),
    "results/tables/rq2_public_solver_pilot_v1/SHA256SUMS.json": (
        "08a1f2c6808aa03b9601d20252421fb15a03c2d6686540b8b7d04b1cb4c52e90"
    ),
    "results/tables/rq2_public_solver_pilot_v1/config.yaml": (
        "bcba9981628001ced20e466632bb33e4d9f44ca3ffad6b24fc8a0761f72c0ec1"
    ),
    "results/tables/rq2_public_solver_pilot_v1/summary.json": (
        "e5ee6c960ab766ba2c8ba9752974491d1aa08b4165ce600b004a41f0246e460f"
    ),
    "results/tables/rq2_public_solver_pilot_v1/comparison.json": (
        "ed1eb1f7c1dbdcf0a8140fd690a524c075b7f11b3fb0246c78b06ca2400aa267"
    ),
    "results/tables/rq2_public_solver_pilot_v1/runs.json": (
        "dfdcbcced9f5ba6362856643e44e5e0fdd979334e0165c701a0c9fe3cc80a153"
    ),
    "results/transfer/rq2_public_successor_v1_pilot.tar.gz": (
        "701159a2a4bb55cb16837f14ccdebd473e5099145650c4d56fc87c82da9c21fc"
    ),
    "results/transfer/rq2_public_successor_v1_pilot.json": (
        "be8df8e3ac0bb879fc3a4faf40707ef1bd5b618272ced799e8edf5e6e71c5b30"
    ),
    "configs/rq2_public_executor_handoff_v1.yaml": (
        "52279c15ad4d27516821956b536886081987957d88dcd7fef3d409592694c289"
    ),
    "configs/rq2_public_executor_handoff_v2.yaml": (
        "e362b635dcd22c54162683d04686fd907681976c8c933e983584e19a175c34f0"
    ),
    "configs/rq2_public_successor_activation_v1.yaml": (
        "eba653ef3e1e1131731b4f13df59136a2ea362b891be965b4e514f6d3e027856"
    ),
    "results/tables/rq2_public_executor_preflight_v1/SHA256SUMS.json": (
        "aa765cf39ac4d8bc4c279128041764397eb7dcef6a76242fc0e29327d0ed903f"
    ),
    "data/processed/model_inputs/rts_gmlc_public_power_system_blocks_v4/SHA256SUMS.json": (
        "28bc2c3c1ee3ba0ef6c940aec56f66d49587b5f2895d0e6b0b83fb0b6360cc63"
    ),
}
PACKAGE_RELATIVE = "data/processed/model_inputs/rts_gmlc_public_power_system_blocks_v4"
PACKAGE_MEMBER_HASHES = {
    "holdout_marginal.csv.gz": (
        "127f0ae8ee17986fa0e4b4f8c9833153a65846b8eff068a2c1cfed28ad0c7984"
    ),
    "n1_outage_events.csv.gz": (
        "6b18f27a090e1e0c71f8878dd77007957e7b898e8a5f99543a6e26fb0856092d"
    ),
    "power_system_blocks.csv.gz": (
        "b8b76fcfaa4dfbf63ff8c92092f357d43a7f21ffb51e76552593bb63f6a34ff1"
    ),
    "summary.json": (
        "f74d3a15520562d319cff49cf19fdca87ac04ae5687a639548f1a6dd7c36ce2a"
    ),
    "training_marginal.csv.gz": (
        "e34434955f5d6d3dde21f684dc95799fe31a799791f9a3a8ce8525ebfe528546"
    ),
}
PREFLIGHT_RELATIVE = "results/tables/rq2_public_executor_preflight_v1"
PREFLIGHT_MEMBER_HASHES = {
    "config.yaml": ("52279c15ad4d27516821956b536886081987957d88dcd7fef3d409592694c289"),
    "preflight.json": (
        "43cb4f2dc2871122208853f4c67876bac64752e155cf9c1ccb91ca368fc7b6dc"
    ),
}
RESULT_RELATIVE = "results/tables/rq2_public_solver_pilot_v1"
RESULT_MEMBER_HASHES = {
    "comparison.json": PREDECESSOR_HASHES[
        "results/tables/rq2_public_solver_pilot_v1/comparison.json"
    ],
    "config.yaml": PREDECESSOR_HASHES[
        "results/tables/rq2_public_solver_pilot_v1/config.yaml"
    ],
    "runs.json": PREDECESSOR_HASHES[
        "results/tables/rq2_public_solver_pilot_v1/runs.json"
    ],
    "summary.json": PREDECESSOR_HASHES[
        "results/tables/rq2_public_solver_pilot_v1/summary.json"
    ],
}
TRANSFER_MANIFEST_RELATIVE = "results/transfer/rq2_public_successor_v1_pilot.json"
TRANSFER_ARCHIVE_RELATIVE = "results/transfer/rq2_public_successor_v1_pilot.tar.gz"
TRANSFER_FILE_HASHES = {
    f"{PREFLIGHT_RELATIVE}/SHA256SUMS.json": PREDECESSOR_HASHES[
        f"{PREFLIGHT_RELATIVE}/SHA256SUMS.json"
    ],
    **{
        f"{PREFLIGHT_RELATIVE}/{name}": digest
        for name, digest in PREFLIGHT_MEMBER_HASHES.items()
    },
    f"{RESULT_RELATIVE}/SHA256SUMS.json": PREDECESSOR_HASHES[
        f"{RESULT_RELATIVE}/SHA256SUMS.json"
    ],
    **{
        f"{RESULT_RELATIVE}/{name}": digest
        for name, digest in RESULT_MEMBER_HASHES.items()
    },
}
EXPECTED_GATES = {
    "v1_diagnostic_semantic_consistency_observed": False,
    "confirmatory_pilot_implementation_bound": False,
    "independent_review_passed": False,
    "confirmatory_pilot_authorized": False,
    "confirmatory_pilot_executed": False,
    "cross_solver_confirmation_completed": False,
    "formal_execution_ready": False,
    "formal_result_exists": False,
    "claim": False,
    "security_certified": False,
}
EXPECTED_RUNS = {
    "highs_r1": ("highs", 1),
    "gurobi_r1": ("gurobi", 1),
    "gurobi_r2": ("gurobi", 2),
    "highs_r2": ("highs", 2),
}
EXPECTED_E0 = {
    "holdout_s20260822_0013": (),
    "holdout_s20260822_0091": (),
    "holdout_s20260822_0089": (6598,),
    "holdout_s20260822_0150": (8057, 8058, 8059),
}
EXPECTED_ROLES = {
    "holdout_s20260822_0013": "ordinary_no_outage",
    "holdout_s20260822_0091": "congested_finite_outage",
    "holdout_s20260822_0089": "generator_outage_anomaly",
    "holdout_s20260822_0150": "branch_outage_anomaly",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    return dict(value)


def _list(value: object, label: str) -> list[Any]:
    if not isinstance(value, list):
        raise TypeError(f"{label} must be a list")
    return value


def _equal(observed: object, expected: object, label: str) -> None:
    if observed != expected:
        raise ValueError(f"{label} drifted: {observed!r} != {expected!r}")


def _safe_path(relative: object, label: str) -> str:
    if not isinstance(relative, str) or not relative:
        raise ValueError(f"{label} must be a nonempty path")
    path = PurePosixPath(relative)
    if path.is_absolute() or ".." in path.parts or str(path) != relative:
        raise ValueError(f"{label} must be a canonical repository-relative path")
    return relative


def _load_json(path: Path, label: str) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ValueError(f"cannot load {label}") from error


def _verify_directory_manifest(
    directory_relative: str,
    expected_members: Mapping[str, str],
    *,
    label: str,
) -> int:
    directory = ROOT / _safe_path(directory_relative, label)
    manifest = directory / "SHA256SUMS.json"
    observed = _mapping(_load_json(manifest, f"{label} manifest"), f"{label} manifest")
    _equal(observed, dict(expected_members), f"{label} manifest members")
    expected_inventory = {*expected_members, "SHA256SUMS.json"}
    try:
        children = list(directory.iterdir())
    except OSError as error:
        raise ValueError(f"cannot inventory {label}") from error
    _equal({item.name for item in children}, expected_inventory, f"{label} inventory")
    for child in children:
        if not child.is_file() or child.is_symlink():
            raise ValueError(f"{label} contains a non-ordinary file: {child.name}")
    for name, expected in expected_members.items():
        if PurePosixPath(name).name != name or _sha256(directory / name) != expected:
            raise ValueError(f"{label} member drifted: {name}")
    return len(expected_members)


def _verify_bundle_manifest(
    manifest_relative: str,
    *,
    schema: str,
    label: str,
) -> int:
    manifest = _mapping(
        _load_json(ROOT / manifest_relative, f"{label} manifest"),
        f"{label} manifest",
    )
    _equal(set(manifest), {"schema", "files"}, f"{label} manifest fields")
    _equal(manifest.get("schema"), schema, f"{label} schema")
    files = _mapping(manifest.get("files"), f"{label} files")
    if not files:
        raise ValueError(f"{label} files must not be empty")
    for relative, expected in files.items():
        path = ROOT / _safe_path(relative, f"{label} member {relative}")
        if (
            not isinstance(expected, str)
            or len(expected) != 64
            or not path.is_file()
            or path.is_symlink()
            or _sha256(path) != expected
        ):
            raise ValueError(f"{label} member drifted: {relative}")
    return len(files)


def _verify_transfer_archive(
    archive_path: Path,
    expected_members: Mapping[str, str],
) -> int:
    try:
        with tarfile.open(archive_path, "r:gz") as archive:
            members = archive.getmembers()
            names = [member.name for member in members]
            _equal(len(names), len(set(names)), "transfer archive unique members")
            _equal(set(names), set(expected_members), "transfer archive inventory")
            for member in members:
                _safe_path(member.name, f"transfer archive member {member.name}")
                if not member.isfile() or member.issym() or member.islnk():
                    raise ValueError(
                        f"transfer archive member is not an ordinary file: {member.name}"
                    )
                source = archive.extractfile(member)
                if source is None:
                    raise ValueError(
                        f"cannot read transfer archive member: {member.name}"
                    )
                digest = hashlib.sha256()
                for chunk in iter(lambda source=source: source.read(1024 * 1024), b""):
                    digest.update(chunk)
                if digest.hexdigest() != expected_members[member.name]:
                    raise ValueError(f"transfer archive member drifted: {member.name}")
    except (OSError, tarfile.TarError) as error:
        raise ValueError("cannot validate transfer archive") from error
    return len(expected_members)


def _load_expected_hour_inventory(
    v1_config: Mapping[str, Any],
) -> dict[str, list[tuple[int, str | None, str | None, str | None]]]:
    input_contract = _mapping(v1_config.get("input"), "v1 input contract")
    _equal(
        input_contract.get("power_system_blocks_package"),
        PACKAGE_RELATIVE,
        "v1 input package path",
    )
    _equal(
        input_contract.get("power_system_blocks_manifest_sha256"),
        PREDECESSOR_HASHES[f"{PACKAGE_RELATIVE}/SHA256SUMS.json"],
        "v1 input package manifest hash",
    )
    pilot_blocks = _list(v1_config.get("pilot_blocks"), "v1 pilot blocks")
    _equal(
        [item.get("block_id") for item in pilot_blocks if isinstance(item, Mapping)],
        list(EXPECTED_E0),
        "v1 pilot block inventory",
    )
    for raw_block in pilot_blocks:
        block = _mapping(raw_block, "v1 pilot block")
        block_id = str(block["block_id"])
        _equal(block.get("role"), EXPECTED_ROLES[block_id], f"{block_id} frozen role")
        _equal(
            tuple(block.get("expected_exogenous_source_hours", [])),
            EXPECTED_E0[block_id],
            f"{block_id} frozen E0 inventory",
        )
    _verify_directory_manifest(
        PACKAGE_RELATIVE,
        PACKAGE_MEMBER_HASHES,
        label="power-system input package",
    )
    inventory = {block_id: [] for block_id in EXPECTED_E0}
    csv_path = ROOT / PACKAGE_RELATIVE / "power_system_blocks.csv.gz"
    try:
        with gzip.open(csv_path, "rt", encoding="utf-8", newline="") as source:
            for row in csv.DictReader(source):
                block_id = row.get("block_id")
                if block_id not in inventory:
                    continue
                inventory[block_id].append(
                    (
                        int(row["source_hour"]),
                        row.get("active_event_id") or None,
                        row.get("active_component_type") or None,
                        row.get("active_component_uid") or None,
                    )
                )
    except (
        OSError,
        UnicodeDecodeError,
        csv.Error,
        KeyError,
        TypeError,
        ValueError,
    ) as error:
        raise ValueError("cannot load frozen power-system hour inventory") from error
    for block_id, rows in inventory.items():
        if len(rows) != 24 or len({row[0] for row in rows}) != 24:
            raise ValueError(f"{block_id} frozen hour inventory is invalid")
    return inventory


def _finite(value: object, label: str) -> float:
    if isinstance(value, bool):
        raise TypeError(f"{label} must be finite")
    try:
        result = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be finite") from error
    if not math.isfinite(result):
        raise ValueError(f"{label} must be finite")
    return result


def _close(
    left: float,
    right: float,
    relative_tolerance: float,
    *,
    absolute_tolerance: float | None = None,
) -> bool:
    absolute = relative_tolerance if absolute_tolerance is None else absolute_tolerance
    return math.isclose(
        left,
        right,
        rel_tol=relative_tolerance,
        abs_tol=absolute,
    )


def _expected_solver_options(
    solver: str, solver_config: Mapping[str, Any]
) -> dict[str, float | int]:
    if solver == "gurobi":
        return {
            "MIPGap": solver_config["mip_relative_gap"],
            "MIPGapAbs": 0.0,
            "Seed": solver_config["random_seed"],
            "Threads": solver_config["threads"],
            "FeasibilityTol": solver_config["feasibility_tolerance"],
            "OptimalityTol": solver_config["optimality_tolerance"],
            "IntFeasTol": solver_config["integer_feasibility_tolerance"],
        }
    if solver == "highs":
        return {
            "mip_rel_gap": solver_config["mip_relative_gap"],
            "mip_abs_gap": 0.0,
            "random_seed": solver_config["random_seed"],
            "threads": solver_config["threads"],
            "primal_feasibility_tolerance": solver_config["feasibility_tolerance"],
            "dual_feasibility_tolerance": solver_config["optimality_tolerance"],
            "mip_feasibility_tolerance": solver_config["integer_feasibility_tolerance"],
        }
    raise ValueError(f"unregistered solver: {solver}")


def _raw_semantic(
    result: Mapping[str, Any],
    solver: str,
    status_mapping: Mapping[str, Any],
) -> str:
    termination = result.get("termination_condition")
    raw_status = result.get("solver_status")
    solver_mapping = _mapping(status_mapping.get(solver), f"status mapping {solver}")
    allowed = solver_mapping.get(termination)
    if not isinstance(allowed, Sequence) or isinstance(allowed, (str, bytes)):
        return "unresolved_unregistered_raw_status"
    if raw_status not in allowed:
        return "unresolved_unregistered_raw_status"
    if termination == "optimal":
        return "optimal"
    if termination == "infeasible":
        return "proven_infeasible"
    if termination == "not_applicable_no_active_outage":
        return "not_applicable_no_active_outage"
    return "unresolved_unregistered_raw_status"


def _certificate_interval(
    certificate: Mapping[str, Any],
    *,
    prefix: str,
    configured_relative_gap: float,
    model_tolerance: float,
    numeric_tolerance: float,
    incumbent_key: str,
    lower_key: str,
    upper_key: str,
    absolute_gap_key: str,
    relative_gap_key: str,
    gap_tolerance_key: str,
) -> tuple[float, float, float]:
    incumbent = _finite(certificate.get(incumbent_key), f"{prefix} incumbent")
    lower = _finite(certificate.get(lower_key), f"{prefix} lower bound")
    upper = _finite(certificate.get(upper_key), f"{prefix} upper bound")
    absolute_gap = _finite(certificate.get(absolute_gap_key), f"{prefix} absolute gap")
    relative_gap = _finite(certificate.get(relative_gap_key), f"{prefix} relative gap")
    gap_tolerance = _finite(
        certificate.get(gap_tolerance_key), f"{prefix} gap tolerance"
    )
    if lower > upper and not _close(lower, upper, numeric_tolerance):
        raise ValueError(f"{prefix} has an invalid minimization interval")
    if (
        incumbent < lower
        and not _close(incumbent, lower, numeric_tolerance)
    ) or (
        incumbent > upper
        and not _close(incumbent, upper, numeric_tolerance)
    ):
        raise ValueError(f"{prefix} incumbent is outside the certified interval")
    recomputed_gap = upper - lower if upper >= lower else 0.0
    if not _close(absolute_gap, recomputed_gap, numeric_tolerance):
        raise ValueError(f"{prefix} absolute gap is inconsistent with bounds")
    recomputed_relative = recomputed_gap / max(abs(upper), 1.0e-12)
    if not _close(relative_gap, recomputed_relative, numeric_tolerance):
        raise ValueError(f"{prefix} relative gap is inconsistent with bounds")
    expected_tolerance = max(
        model_tolerance,
        configured_relative_gap * max(abs(upper), 1.0),
    )
    if not _close(gap_tolerance, expected_tolerance, numeric_tolerance):
        raise ValueError(f"{prefix} own gap tolerance is inconsistent")
    if absolute_gap > gap_tolerance and not _close(
        absolute_gap, gap_tolerance, numeric_tolerance
    ):
        raise ValueError(f"{prefix} exceeds its own absolute gap tolerance")
    if relative_gap > configured_relative_gap and not _close(
        relative_gap, configured_relative_gap, numeric_tolerance
    ):
        raise ValueError(f"{prefix} exceeds its configured relative gap")
    return incumbent, lower, upper


def _null_infeasible_certificate(
    certificate: Mapping[str, Any], prefix: str
) -> tuple[int, int]:
    for field in (
        "objective_incumbent_mw",
        "lower_bound_mw",
        "upper_bound_mw",
        "absolute_gap_mw",
        "relative_gap",
        "gap_tolerance_mw",
    ):
        if certificate.get(field) is not None:
            raise ValueError(f"{prefix}.{field} must be null for infeasibility")
    variables = certificate.get("model_variables")
    constraints = certificate.get("model_constraints")
    if (
        isinstance(variables, bool)
        or not isinstance(variables, int)
        or variables <= 0
        or isinstance(constraints, bool)
        or not isinstance(constraints, int)
        or constraints <= 0
    ):
        raise ValueError(f"{prefix} model scale is invalid")
    return variables, constraints


def _validate_infeasible_result(
    result: Mapping[str, Any],
    *,
    solver: str,
    status_mapping: Mapping[str, Any],
    prefix: str,
) -> None:
    if _raw_semantic(result, solver, status_mapping) != "proven_infeasible":
        raise ValueError(f"{prefix} raw status is not registered as infeasible")
    if (
        result.get("proven_infeasible") is not True
        or result.get("resolved") is not False
        or result.get("grid_need_mw") is not None
        or result.get("maximum_constraint_violation") is not None
    ):
        raise ValueError(f"{prefix} infeasibility evidence is incomplete")


def _validate_baseline(
    audit: Mapping[str, Any],
    *,
    solver: str,
    solver_config: Mapping[str, Any],
    status_mapping: Mapping[str, Any],
    model_tolerance: float,
    residual_limit: float,
    numeric_tolerance: float,
    prefix: str,
) -> tuple[float, float, float, int, int, float, float]:
    if audit.get("accepted") is not True:
        raise ValueError(f"{prefix} baseline was not accepted")
    if audit.get("solver_name") != solver:
        raise ValueError(f"{prefix} solver identity drifted")
    if audit.get("solver_threads") != solver_config.get("threads"):
        raise ValueError(f"{prefix} solver thread count drifted")
    if audit.get("solver_options") != _expected_solver_options(solver, solver_config):
        raise ValueError(f"{prefix} solver options drifted")
    if _raw_semantic(audit, solver, status_mapping) != "optimal":
        raise ValueError(f"{prefix} baseline raw status is not registered as optimal")
    configured_gap = _finite(
        solver_config.get("mip_relative_gap"), f"{prefix} configured gap"
    )
    if not _close(
        _finite(audit.get("configured_mip_relative_gap"), f"{prefix} audit gap"),
        configured_gap,
        numeric_tolerance,
    ):
        raise ValueError(f"{prefix} configured relative gap drifted")
    incumbent, lower, upper = _certificate_interval(
        audit,
        prefix=prefix,
        configured_relative_gap=configured_gap,
        model_tolerance=model_tolerance,
        numeric_tolerance=numeric_tolerance,
        incumbent_key="objective_usd",
        lower_key="lower_bound_usd",
        upper_key="upper_bound_usd",
        absolute_gap_key="absolute_gap_usd",
        relative_gap_key="relative_gap",
        gap_tolerance_key="gap_tolerance_usd",
    )
    violation = _finite(
        audit.get("maximum_constraint_violation"), f"{prefix} constraint violation"
    )
    integrality = _finite(
        audit.get("maximum_integrality_violation"), f"{prefix} integrality"
    )
    if (
        violation < 0.0
        or integrality < 0.0
        or violation > residual_limit
        or integrality > residual_limit
    ):
        raise ValueError(f"{prefix} residual limit failed")
    variables = audit.get("model_variables")
    constraints = audit.get("model_constraints")
    if (
        isinstance(variables, bool)
        or not isinstance(variables, int)
        or variables <= 0
        or isinstance(constraints, bool)
        or not isinstance(constraints, int)
        or constraints <= 0
    ):
        raise ValueError(f"{prefix} model scale is invalid")
    return incumbent, lower, upper, variables, constraints, violation, integrality


def _validate_hour(
    hour: Mapping[str, Any],
    *,
    solver: str,
    configured_gap: float,
    expected_solver_options: Mapping[str, Any],
    status_mapping: Mapping[str, Any],
    model_tolerance: float,
    numeric_absolute_tolerance: float,
    residual_limit: float,
    numeric_tolerance: float,
    expected_hour: tuple[int, str | None, str | None, str | None],
    prefix: str,
) -> dict[str, Any]:
    if hour.get("solver_name") != solver:
        raise ValueError(f"{prefix} solver identity drifted")
    if hour.get("resolved_for_pipeline") is not True:
        raise ValueError(f"{prefix} unresolved hour cannot confirm semantics")
    primary = _mapping(hour.get("primary"), f"{prefix}.primary")
    certificate = _mapping(
        hour.get("primary_certificate"), f"{prefix}.primary_certificate"
    )
    state = hour.get("state")
    active_event = hour.get("active_event_id")
    expected_source_hour, expected_event, expected_component_type, expected_uid = (
        expected_hour
    )
    if (
        hour.get("source_hour") != expected_source_hour
        or active_event != expected_event
    ):
        raise ValueError(f"{prefix} frozen hour inventory drifted")
    observed_options = _mapping(hour.get("solver_options"), f"{prefix}.solver_options")
    if observed_options != ({} if active_event is None else expected_solver_options):
        raise ValueError(f"{prefix} solver options drifted")
    raw = {
        "solver": solver,
        "termination_condition": primary.get("termination_condition"),
        "solver_status": primary.get("solver_status"),
    }
    if state == "finite_grid_need":
        if (
            hour.get("zero_dc_confirmation") is not None
            or hour.get("zero_dc_confirmation_certificate") is not None
        ):
            raise ValueError(f"{prefix} finite state has a zero-DC confirmation")
        semantic = _raw_semantic(primary, solver, status_mapping)
        grid_need = _finite(primary.get("grid_need_mw"), f"{prefix} grid need")
        if semantic == "not_applicable_no_active_outage":
            if active_event is not None or not _close(
                grid_need, 0.0, numeric_tolerance
            ):
                raise ValueError(f"{prefix} no-outage semantic evidence is invalid")
        elif semantic != "optimal":
            raise ValueError(f"{prefix} finite state has unregistered raw status")
        if (
            primary.get("resolved") is not True
            or primary.get("proven_infeasible") is not False
            or primary.get("source_hour") != hour.get("source_hour")
            or primary.get("event_id") != active_event
        ):
            raise ValueError(f"{prefix} finite state resolution flags are invalid")
        violation = _finite(
            primary.get("maximum_constraint_violation"),
            f"{prefix} maximum constraint violation",
        )
        if violation < 0.0 or violation > residual_limit:
            raise ValueError(f"{prefix} finite residual limit failed")
        if semantic == "not_applicable_no_active_outage":
            interval = (0.0, 0.0, 0.0)
            if any(
                not _close(
                    _finite(certificate.get(field), f"{prefix}.{field}"),
                    0.0,
                    numeric_tolerance,
                )
                for field in (
                    "objective_incumbent_mw",
                    "lower_bound_mw",
                    "upper_bound_mw",
                    "absolute_gap_mw",
                    "relative_gap",
                    "gap_tolerance_mw",
                )
            ):
                raise ValueError(f"{prefix} no-outage certificate is not zero")
        else:
            interval = _certificate_interval(
                certificate,
                prefix=f"{prefix}.primary_certificate",
                configured_relative_gap=configured_gap,
                model_tolerance=model_tolerance,
                numeric_tolerance=numeric_tolerance,
                incumbent_key="objective_incumbent_mw",
                lower_key="lower_bound_mw",
                upper_key="upper_bound_mw",
                absolute_gap_key="absolute_gap_mw",
                relative_gap_key="relative_gap",
                gap_tolerance_key="gap_tolerance_mw",
            )
            if not _close(
                interval[0],
                grid_need,
                numeric_tolerance,
                absolute_tolerance=numeric_absolute_tolerance,
            ):
                raise ValueError(f"{prefix} grid need and incumbent differ")
        scale = (
            certificate.get("model_variables"),
            certificate.get("model_constraints"),
        )
        if any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in scale
        ):
            raise ValueError(f"{prefix} finite model scale is invalid")
        if semantic == "not_applicable_no_active_outage":
            if scale != (0, 0):
                raise ValueError(f"{prefix} no-outage model scale must be zero")
        elif any(value <= 0 for value in scale):
            raise ValueError(f"{prefix} active finite model scale must be positive")
        event_signature = (
            primary.get("event_id"),
            primary.get("component_type"),
            primary.get("component_uid"),
        )
        if event_signature != (
            expected_event,
            expected_component_type,
            expected_uid,
        ):
            raise ValueError(f"{prefix} frozen event metadata drifted")
        return {
            "state": state,
            "grid_need": grid_need,
            "interval": interval,
            "scale": scale,
            "residual": violation,
            "raw": raw,
            "event_signature": event_signature,
        }
    if state != "exogenous_grid_infeasibility":
        raise ValueError(
            f"{prefix} unresolved or unknown state cannot confirm semantics"
        )
    zero = _mapping(hour.get("zero_dc_confirmation"), f"{prefix}.zero_dc_confirmation")
    zero_certificate = _mapping(
        hour.get("zero_dc_confirmation_certificate"),
        f"{prefix}.zero_dc_confirmation_certificate",
    )
    _validate_infeasible_result(
        primary,
        solver=solver,
        status_mapping=status_mapping,
        prefix=f"{prefix}.primary",
    )
    _validate_infeasible_result(
        zero,
        solver=solver,
        status_mapping=status_mapping,
        prefix=f"{prefix}.zero_dc_confirmation",
    )
    primary_scale = _null_infeasible_certificate(
        certificate, f"{prefix}.primary_certificate"
    )
    zero_scale = _null_infeasible_certificate(
        zero_certificate, f"{prefix}.zero_dc_confirmation_certificate"
    )
    if primary_scale != zero_scale:
        raise ValueError(f"{prefix} E0 primary and zero-DC model scales differ")
    for field in ("source_hour", "event_id", "component_type", "component_uid"):
        if primary.get(field) != zero.get(field):
            raise ValueError(f"{prefix} E0 primary and zero-DC metadata differ")
    if (
        primary.get("source_hour") != hour.get("source_hour")
        or primary.get("event_id") != active_event
    ):
        raise ValueError(f"{prefix} E0 hour metadata drifted")
    event_signature = (
        primary.get("event_id"),
        primary.get("component_type"),
        primary.get("component_uid"),
    )
    if event_signature != (
        expected_event,
        expected_component_type,
        expected_uid,
    ):
        raise ValueError(f"{prefix} frozen event metadata drifted")
    return {
        "state": state,
        "grid_need": None,
        "interval": None,
        "scale": primary_scale,
        "residual": None,
        "raw": raw,
        "event_signature": event_signature,
    }


def evaluate_runs(config: Mapping[str, Any], runs: object) -> dict[str, object]:
    """Recompute diagnostic semantic consistency without changing any gate."""

    config = _mapping(config, "successor config")
    v1_config = _mapping(
        yaml.safe_load(
            (ROOT / "configs/rq2_public_solver_pilot_v1.yaml").read_text(
                encoding="utf-8"
            )
        ),
        "v1 pilot config",
    )
    expected_hour_inventory = _load_expected_hour_inventory(v1_config)
    acceptance = _mapping(config.get("semantic_acceptance"), "semantic acceptance")
    baseline_rules = _mapping(acceptance.get("baseline"), "baseline rules")
    hourly_rules = _mapping(acceptance.get("hourly"), "hourly rules")
    status_mapping = _mapping(
        acceptance.get("registered_raw_status_mapping"), "raw status mapping"
    )
    objective_tolerance = _finite(
        baseline_rules.get("maximum_cross_solver_incumbent_difference_usd"),
        "baseline objective tolerance",
    )
    grid_tolerance = _finite(
        hourly_rules.get("maximum_finite_grid_need_difference_mw"),
        "grid-need tolerance",
    )
    residual_limit = _finite(
        hourly_rules.get("maximum_constraint_violation"), "residual limit"
    )
    numeric_tolerance = _finite(
        acceptance.get("numeric_serialization_consistency_tolerance"),
        "numeric consistency tolerance",
    )
    hourly_numeric_absolute_tolerance = _finite(
        acceptance.get("hourly_solver_report_absolute_tolerance_mw"),
        "hourly solver-report absolute tolerance",
    )
    model_tolerance = _finite(v1_config["model"]["tolerance_mw"], "model tolerance")
    run_list = _list(runs, "runs")
    if [item.get("run_id") for item in run_list if isinstance(item, Mapping)] != list(
        EXPECTED_RUNS
    ):
        raise ValueError("pilot run order or inventory drifted")
    records: dict[tuple[str, str], dict[str, Any]] = {}
    raw_counter: Counter[tuple[str, str, str]] = Counter()
    baseline_records: dict[
        tuple[str, str], tuple[float, float, float, int, int, float, float]
    ] = {}
    semantic_hours: dict[tuple[str, str], dict[int, dict[str, Any]]] = {}
    for raw_run in run_list:
        run = _mapping(raw_run, "run")
        run_id = str(run["run_id"])
        solver, repetition = EXPECTED_RUNS[run_id]
        if run.get("solver_name") != solver or run.get("repetition") != repetition:
            raise ValueError(f"{run_id} solver or repetition identity drifted")
        solver_config = _mapping(v1_config["solvers"][solver], f"{solver} config")
        blocks = _list(run.get("blocks"), f"{run_id} blocks")
        if [
            item.get("block_id") for item in blocks if isinstance(item, Mapping)
        ] != list(EXPECTED_E0):
            raise ValueError(f"{run_id} block order or inventory drifted")
        for raw_block in blocks:
            block = _mapping(raw_block, f"{run_id} block")
            block_id = str(block["block_id"])
            _equal(
                block.get("role"),
                EXPECTED_ROLES[block_id],
                f"{run_id}.{block_id} role",
            )
            key = (run_id, block_id)
            records[key] = block
            baseline_records[key] = _validate_baseline(
                _mapping(block.get("baseline_audit"), f"{run_id}.{block_id} baseline"),
                solver=solver,
                solver_config=solver_config,
                status_mapping=status_mapping,
                model_tolerance=model_tolerance,
                residual_limit=residual_limit,
                numeric_tolerance=numeric_tolerance,
                prefix=f"{run_id}.{block_id}.baseline",
            )
            hours = _list(block.get("hours"), f"{run_id}.{block_id} hours")
            expected_hours = expected_hour_inventory[block_id]
            _equal(
                [
                    item.get("source_hour")
                    for item in hours
                    if isinstance(item, Mapping)
                ],
                [item[0] for item in expected_hours],
                f"{run_id}.{block_id} frozen source-hour inventory",
            )
            indexed: dict[int, dict[str, Any]] = {}
            for raw_hour, expected_hour in zip(hours, expected_hours, strict=True):
                hour = _mapping(raw_hour, f"{run_id}.{block_id} hour")
                source_hour = hour.get("source_hour")
                if isinstance(source_hour, bool) or not isinstance(source_hour, int):
                    raise TypeError(f"{run_id}.{block_id} source hour is invalid")
                if source_hour in indexed:
                    raise ValueError(f"{run_id}.{block_id} has duplicate source hours")
                semantic = _validate_hour(
                    hour,
                    solver=solver,
                    configured_gap=_finite(
                        solver_config["mip_relative_gap"], f"{solver} relative gap"
                    ),
                    expected_solver_options=_expected_solver_options(
                        solver, solver_config
                    ),
                    status_mapping=status_mapping,
                    model_tolerance=model_tolerance,
                    numeric_absolute_tolerance=hourly_numeric_absolute_tolerance,
                    residual_limit=residual_limit,
                    numeric_tolerance=numeric_tolerance,
                    expected_hour=expected_hour,
                    prefix=f"{run_id}.{block_id}.{source_hour}",
                )
                indexed[source_hour] = semantic
                raw = semantic["raw"]
                raw_counter[
                    (raw["solver"], raw["termination_condition"], raw["solver_status"])
                ] += 1
            observed_e0 = tuple(
                hour
                for hour, item in indexed.items()
                if item["state"] == "exogenous_grid_infeasibility"
            )
            if observed_e0 != EXPECTED_E0[block_id]:
                raise ValueError(f"{run_id}.{block_id} E0 hour set drifted")
            semantic_hours[key] = indexed
    run_ids = list(EXPECTED_RUNS)
    pair_count = 0
    for block_id in EXPECTED_E0:
        for left_index, left_id in enumerate(run_ids):
            for right_id in run_ids[left_index + 1 :]:
                pair_count += 1
                left = baseline_records[(left_id, block_id)]
                right = baseline_records[(right_id, block_id)]
                if left[3:5] != right[3:5]:
                    raise ValueError(f"{block_id} baseline model scale mismatch")
                if abs(left[0] - right[0]) > objective_tolerance:
                    raise ValueError(f"{block_id} baseline incumbents differ")
                interval_lower = max(left[1], right[1])
                interval_upper = min(left[2], right[2])
                if interval_lower > interval_upper and not _close(
                    interval_lower, interval_upper, numeric_tolerance
                ):
                    raise ValueError(f"{block_id} baseline MIP intervals are disjoint")
                if (
                    abs(left[5] - right[5]) > residual_limit
                    or abs(left[6] - right[6]) > residual_limit
                ):
                    raise ValueError(f"{block_id} baseline residuals differ")
                left_hours = semantic_hours[(left_id, block_id)]
                right_hours = semantic_hours[(right_id, block_id)]
                if set(left_hours) != set(right_hours):
                    raise ValueError(f"{block_id} hourly inventory differs")
                for source_hour in left_hours:
                    left_hour = left_hours[source_hour]
                    right_hour = right_hours[source_hour]
                    if left_hour["state"] != right_hour["state"]:
                        raise ValueError(
                            f"{block_id}.{source_hour} semantic state differs"
                        )
                    if left_hour["scale"] != right_hour["scale"]:
                        raise ValueError(
                            f"{block_id}.{source_hour} model scale differs"
                        )
                    if left_hour["event_signature"] != right_hour["event_signature"]:
                        raise ValueError(
                            f"{block_id}.{source_hour} event metadata differs"
                        )
                    if left_hour["state"] == "finite_grid_need" and (
                        abs(left_hour["grid_need"] - right_hour["grid_need"])
                        > grid_tolerance
                    ):
                        raise ValueError(
                            f"{block_id}.{source_hour} finite grid need differs"
                        )
                    if left_hour["state"] == "finite_grid_need":
                        left_interval = left_hour["interval"]
                        right_interval = right_hour["interval"]
                        interval_lower = max(left_interval[1], right_interval[1])
                        interval_upper = min(left_interval[2], right_interval[2])
                        if interval_lower > interval_upper and not _close(
                            interval_lower,
                            interval_upper,
                            numeric_tolerance,
                            absolute_tolerance=hourly_numeric_absolute_tolerance,
                        ):
                            raise ValueError(
                                f"{block_id}.{source_hour} hourly MIP intervals "
                                "are disjoint"
                            )
    return {
        "schema": "rq2_public_solver_pilot_semantic_diagnostic_v1",
        "run_count": len(run_list),
        "block_run_count": len(records),
        "hour_run_count": sum(len(items) for items in semantic_hours.values()),
        "pairwise_block_comparison_count": pair_count,
        "raw_status_inventory": [
            {
                "solver": solver,
                "termination_condition": termination,
                "solver_status": status,
                "count": count,
            }
            for (solver, termination, status), count in sorted(raw_counter.items())
        ],
        "diagnostic_semantic_consistency_observed": True,
        "v1_eligibility_changed": False,
        "confirmatory_pilot_required": True,
        "cross_solver_confirmation_completed": False,
    }


def _validate_v1_outcome(config: Mapping[str, Any]) -> None:
    summary = _mapping(
        _load_json(
            ROOT / "results/tables/rq2_public_solver_pilot_v1/summary.json",
            "v1 summary",
        ),
        "v1 summary",
    )
    comparison = _mapping(
        _load_json(
            ROOT / "results/tables/rq2_public_solver_pilot_v1/comparison.json",
            "v1 comparison",
        ),
        "v1 comparison",
    )
    checks = _list(comparison.get("checks"), "v1 checks")
    failures = _list(comparison.get("failed_checks"), "v1 failed checks")
    observed = _mapping(config.get("observed_v1_outcome"), "observed v1 outcome")
    failure_counts: dict[str, dict[str, int]] = {}
    for failure in failures:
        item = _mapping(failure, "v1 failed check")
        block = str(item["block_id"])
        check = str(item["check"])
        failure_counts.setdefault(block, {})[check] = (
            failure_counts.setdefault(block, {}).get(check, 0) + 1
        )
    expected = {
        "check_count": len(checks),
        "passed_check_count": sum(item.get("passed") is True for item in checks),
        "failed_check_count": len(failures),
        "gurobi_eligible_for_formal_successor": summary.get(
            "gurobi_eligible_for_formal_successor"
        ),
        "failed_check_classes": failure_counts,
        "all_other_v1_checks_passed": len(checks) - len(failures) == 268,
        "formal_grid_execution_started": summary.get("formal_grid_execution_started"),
        "security_certified": summary.get("security_certified"),
    }
    _equal(observed, expected, "observed v1 outcome")


def _validate_contract(config: Mapping[str, Any]) -> None:
    _equal(config.get("schema"), SCHEMA, "schema")
    _equal(config.get("version"), 1, "version")
    _equal(config.get("frozen_on"), "2026-08-27", "frozen date")
    _equal(config.get("status"), STATUS, "status")
    scope = _mapping(config.get("scope"), "scope")
    required_scope = {
        "task_risk": "R3",
        "purpose": "normalize_cross_solver_certificate_semantics_without_reclassifying_v1",
        "source_pilot_outcomes_observed_before_amendment": True,
        "v1_result_reassessment_is_diagnostic_only": True,
        "v1_eligibility_changed": False,
        "runs_solver_during_validation": False,
        "writes_result_during_validation": False,
        "changes_model_formulation": False,
        "changes_solver_algorithm_threads_seed_or_tolerances": False,
        "changes_pilot_blocks_or_repetitions": False,
        "changes_formal_result_or_certification": False,
    }
    _equal(scope, required_scope, "scope")
    predecessor = _mapping(config.get("predecessor_authority"), "predecessor")
    _equal(predecessor.get("immutable"), True, "predecessor immutability")
    _equal(predecessor.get("files"), PREDECESSOR_HASHES, "predecessor hashes")
    acceptance = _mapping(config.get("semantic_acceptance"), "semantic acceptance")
    _equal(acceptance.get("objective_sense"), "minimize", "objective sense")
    _equal(
        acceptance.get("threshold_provenance"),
        {
            "baseline_incumbent_difference": {
                "v1_source_field": (
                    "acceptance.maximum_baseline_objective_difference_usd"
                ),
                "frozen_value": 1.0e-4,
                "successor_use": "incumbent_objective_only",
            },
            "finite_grid_need_difference": {
                "v1_source_field": (
                    "acceptance.maximum_finite_grid_need_difference_mw"
                ),
                "frozen_value": 1.0e-5,
            },
            "constraint_violation": {
                "v1_source_field": "acceptance.maximum_constraint_violation",
                "frozen_value": 1.0e-6,
            },
            "solver_relative_gap": {
                "v1_source_field": "solvers.*.mip_relative_gap",
                "frozen_value": 1.0e-6,
            },
            "scientific_threshold_values_changed_after_observation": False,
            "hourly_solver_report_absolute_tolerance": {
                "value_mw": 1.0e-10,
                "derivation": "frozen_model_tolerance_times_1e-4",
                "frozen_model_tolerance_source": "model.tolerance_mw",
                "frozen_model_tolerance_mw": 1.0e-6,
                "fraction_of_frozen_model_tolerance": 1.0e-4,
                "fraction_of_cross_solver_finite_grid_threshold": 1.0e-5,
                "introduced_after_v1_observation": True,
                "diagnostic_only_until_fresh_confirmatory_pilot": True,
                "successor_use": (
                    "same_record_objective_and_pairwise_interval_consistency_only"
                ),
            },
        },
        "threshold provenance",
    )
    baseline = _mapping(acceptance.get("baseline"), "baseline acceptance")
    hourly = _mapping(acceptance.get("hourly"), "hourly acceptance")
    _equal(
        baseline,
        {
            "maximum_cross_solver_incumbent_difference_usd": 1.0e-4,
            "require_finite_lower_and_upper_bounds": True,
            "require_lower_bound_not_above_upper_bound": True,
            "require_incumbent_inside_interval": True,
            "require_pairwise_intervals_overlap": True,
            "compare_lower_bounds_across_solvers_for_equality": False,
            "compare_absolute_gaps_across_solvers_for_equality": False,
            "compare_gap_tolerances_across_solvers_for_equality": False,
            "require_each_solver_own_gap_within_recorded_tolerance": True,
            "require_each_solver_own_relative_gap_within_configured_limit": True,
            "interval_direction_tolerance": (
                "numeric_serialization_consistency_tolerance_only"
            ),
            "interval_overlap_tolerance": (
                "numeric_serialization_consistency_tolerance_only"
            ),
        },
        "baseline acceptance",
    )
    _equal(
        hourly,
        {
            "maximum_finite_grid_need_difference_mw": 1.0e-5,
            "maximum_constraint_violation": 1.0e-6,
            "require_identical_semantic_state": True,
            "require_identical_model_scale": True,
            "compare_raw_solver_status_across_solvers_for_equality": False,
            "preserve_raw_termination_condition_and_solver_status": True,
            "E0_requires_primary_and_zero_dc_proven_infeasible": True,
            "E0_requires_null_grid_need_and_null_incumbent_bounds": True,
            "require_nonnegative_residuals": True,
            "no_active_outage_requires_zero_model_scale": True,
            "active_finite_and_E0_require_positive_model_scale": True,
            "require_exact_frozen_block_role_source_hour_and_event_inventory": True,
            "require_same_record_grid_need_and_certificate_incumbent_consistency": (
                True
            ),
            "require_pairwise_finite_certificate_intervals_overlap": True,
            "interval_direction_tolerance": (
                "numeric_serialization_consistency_tolerance_only"
            ),
            "same_record_objective_tolerance": (
                "hourly_solver_report_numeric_envelope_only"
            ),
            "interval_overlap_tolerance": (
                "hourly_solver_report_numeric_envelope_only"
            ),
        },
        "hourly acceptance",
    )
    _equal(
        acceptance.get("registered_raw_status_mapping"),
        {
            "highs": {
                "optimal": ["ok"],
                "infeasible": ["error"],
                "not_applicable_no_active_outage": ["not_applicable"],
            },
            "gurobi": {
                "optimal": ["ok"],
                "infeasible": ["warning"],
                "not_applicable_no_active_outage": ["not_applicable"],
            },
        },
        "registered raw status mapping",
    )
    _equal(
        {
            key: acceptance.get(key)
            for key in (
                "unregistered_raw_status_or_termination",
                "timeout_is_infeasibility_evidence",
                "timeout_is_semantic_confirmation",
                "unresolved_is_infeasibility_evidence",
                "unresolved_is_semantic_confirmation",
                "missing_or_incomplete_certificate_is_confirmation",
                "numeric_serialization_consistency_tolerance",
                "hourly_solver_report_absolute_tolerance_mw",
            )
        },
        {
            "unregistered_raw_status_or_termination": "unresolved_fail_closed",
            "timeout_is_infeasibility_evidence": False,
            "timeout_is_semantic_confirmation": False,
            "unresolved_is_infeasibility_evidence": False,
            "unresolved_is_semantic_confirmation": False,
            "missing_or_incomplete_certificate_is_confirmation": False,
            "numeric_serialization_consistency_tolerance": 1.0e-12,
            "hourly_solver_report_absolute_tolerance_mw": 1.0e-10,
        },
        "fail-closed semantic acceptance",
    )
    _equal(
        set(acceptance),
        {
            "objective_sense",
            "threshold_provenance",
            "baseline",
            "hourly",
            "registered_raw_status_mapping",
            "unregistered_raw_status_or_termination",
            "timeout_is_infeasibility_evidence",
            "timeout_is_semantic_confirmation",
            "unresolved_is_infeasibility_evidence",
            "unresolved_is_semantic_confirmation",
            "missing_or_incomplete_certificate_is_confirmation",
            "numeric_serialization_consistency_tolerance",
            "hourly_solver_report_absolute_tolerance_mw",
        },
        "semantic acceptance fields",
    )
    confirmatory = _mapping(config.get("confirmatory_pilot"), "confirmatory pilot")
    if (
        confirmatory.get("required") is not True
        or confirmatory.get("fresh_solver_executions_required") is not True
        or confirmatory.get("v1_runs_or_transfer_package_may_satisfy_confirmation")
        is not False
        or confirmatory.get("runner_path") is not None
        or confirmatory.get("result_directory") is not None
        or confirmatory.get("executed") is not False
        or confirmatory.get("independent_sol_reviewer_required") is not True
        or confirmatory.get("user_authorization_required_before_execution") is not True
        or confirmatory.get("activation_authority_path") is not None
    ):
        raise ValueError("confirmatory pilot gate contract drifted")
    _equal(config.get("gates"), EXPECTED_GATES, "gates")


def validate(
    config_path: Path = CONFIG,
    manifest_path: Path = MANIFEST,
) -> dict[str, object]:
    config_path = config_path.resolve()
    manifest_path = manifest_path.resolve()
    if config_path != CONFIG.resolve() or manifest_path != MANIFEST.resolve():
        raise ValueError("only canonical config and manifest are accepted")
    if _sha256(config_path) != CONFIG_SHA256:
        raise ValueError("semantic successor config hash drifted")
    config = _mapping(
        yaml.safe_load(config_path.read_text(encoding="utf-8")), "successor config"
    )
    _validate_contract(config)
    for relative, expected in PREDECESSOR_HASHES.items():
        path = ROOT / _safe_path(relative, f"predecessor {relative}")
        if not path.is_file() or path.is_symlink() or _sha256(path) != expected:
            raise ValueError(f"predecessor artifact drifted: {relative}")
    bundle_v1_member_count = _verify_bundle_manifest(
        "configs/rq2_public_executor_bundle_v1.SHA256SUMS.json",
        schema="rq2_public_executor_bundle_manifest_v1",
        label="executor bundle v1",
    )
    bundle_v2_member_count = _verify_bundle_manifest(
        "configs/rq2_public_executor_bundle_v2.SHA256SUMS.json",
        schema="rq2_public_executor_bundle_manifest_v2",
        label="executor bundle v2",
    )
    outer = _mapping(
        _load_json(
            ROOT / "configs/rq2_public_executor_bundle_v2.OUTER.SHA256SUMS.json",
            "executor bundle v2 outer manifest",
        ),
        "executor bundle v2 outer manifest",
    )
    _equal(
        outer,
        {
            "schema": "rq2_public_executor_outer_manifest_v2",
            "files": {
                "configs/rq2_public_executor_bundle_v2.SHA256SUMS.json": (
                    PREDECESSOR_HASHES[
                        "configs/rq2_public_executor_bundle_v2.SHA256SUMS.json"
                    ]
                )
            },
        },
        "executor bundle v2 outer manifest",
    )
    package_member_count = _verify_directory_manifest(
        PACKAGE_RELATIVE,
        PACKAGE_MEMBER_HASHES,
        label="power-system input package",
    )
    preflight_member_count = _verify_directory_manifest(
        PREFLIGHT_RELATIVE,
        PREFLIGHT_MEMBER_HASHES,
        label="v1 preflight",
    )
    result_member_count = _verify_directory_manifest(
        RESULT_RELATIVE,
        RESULT_MEMBER_HASHES,
        label="v1 result",
    )
    transfer = _mapping(
        _load_json(
            ROOT / TRANSFER_MANIFEST_RELATIVE,
            "v1 transfer manifest",
        ),
        "v1 transfer manifest",
    )
    _equal(
        transfer,
        {
            "schema": "rq2_public_executor_return_package_v1",
            "scope": "pilot",
            "formal_result_claimed": False,
            "security_certified": False,
            "files": TRANSFER_FILE_HASHES,
        },
        "v1 transfer manifest",
    )
    for relative, expected in TRANSFER_FILE_HASHES.items():
        path = ROOT / _safe_path(relative, f"transfer member {relative}")
        if not path.is_file() or path.is_symlink() or _sha256(path) != expected:
            raise ValueError(f"live transfer member drifted: {relative}")
    archive_member_hashes = {
        **TRANSFER_FILE_HASHES,
        TRANSFER_MANIFEST_RELATIVE: PREDECESSOR_HASHES[TRANSFER_MANIFEST_RELATIVE],
    }
    archive_member_count = _verify_transfer_archive(
        ROOT / TRANSFER_ARCHIVE_RELATIVE,
        archive_member_hashes,
    )
    _validate_v1_outcome(config)
    runs = _load_json(
        ROOT / "results/tables/rq2_public_solver_pilot_v1/runs.json", "v1 runs"
    )
    diagnostic = evaluate_runs(config, runs)
    manifest = _mapping(_load_json(manifest_path, "successor manifest"), "manifest")
    if (
        manifest.get("schema")
        != "rq2_public_solver_pilot_semantic_successor_manifest_v1"
    ):
        raise ValueError("successor manifest schema drifted")
    expected_paths = {
        *PREDECESSOR_HASHES,
        CONFIG_RELATIVE,
        "experiments/validate_rq2_public_solver_pilot_semantic_successor_v1.py",
        "tests/test_rq2_public_solver_pilot_semantic_successor_v1.py",
    }
    files = _mapping(manifest.get("files"), "successor manifest files")
    _equal(set(files), expected_paths, "successor manifest inventory")
    for relative, expected in files.items():
        path = ROOT / _safe_path(relative, f"manifest {relative}")
        if not path.is_file() or path.is_symlink() or _sha256(path) != expected:
            raise ValueError(f"successor manifest member drifted: {relative}")
    return {
        "schema": "rq2_public_solver_pilot_semantic_successor_validation_v1",
        "config_sha256": _sha256(config_path),
        "manifest_sha256": _sha256(manifest_path),
        "v1_result_manifest_sha256": PREDECESSOR_HASHES[
            "results/tables/rq2_public_solver_pilot_v1/SHA256SUMS.json"
        ],
        "v1_transfer_archive_sha256": PREDECESSOR_HASHES[
            "results/transfer/rq2_public_successor_v1_pilot.tar.gz"
        ],
        "v1_transfer_manifest_sha256": PREDECESSOR_HASHES[TRANSFER_MANIFEST_RELATIVE],
        "executor_bundle_v1_member_count": bundle_v1_member_count,
        "executor_bundle_v2_member_count": bundle_v2_member_count,
        "input_package_member_count": package_member_count,
        "preflight_member_count": preflight_member_count,
        "pilot_result_member_count": result_member_count,
        "transfer_manifest_member_count": len(TRANSFER_FILE_HASHES),
        "transfer_archive_member_count": archive_member_count,
        "original_v1_failed_check_count": 12,
        "original_v1_eligible": False,
        "diagnostic": diagnostic,
        "solver_calls": 0,
        "result_files_written": 0,
        "confirmatory_pilot_executed": False,
        "cross_solver_confirmation_completed": False,
        "formal_execution_ready": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
        "validation_passed": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--manifest", type=Path, default=MANIFEST)
    args = parser.parse_args()
    print(json.dumps(validate(args.config, args.manifest), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
