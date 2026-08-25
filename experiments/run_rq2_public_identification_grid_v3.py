"""Sharp transport identification over every registered RQ2 parameter cell."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import shutil
import tempfile
from collections import defaultdict
from collections.abc import Iterable, Mapping
from math import isfinite
from pathlib import Path
from typing import Any

import yaml

from src.evaluation.rq2_identification_bounds import (
    UNRESOLVED,
    IdentificationInputs,
    Interval,
    classify_identification_bounds,
)
from src.evaluation.rq2_provenance_v2 import (
    canonical_sha256,
    load_contract,
    load_json_strict,
    sha256_file,
    stage_base_provenance,
    verify_checkpoint_inventory_bundle,
    write_json,
)
from src.scenarios.block_coupling import (
    bound_transport_expectation,
    quantile_coupling,
)

_ROOT = Path(__file__).resolve().parents[1]
_STAGE = "identification_grid_v3"
_PAIRWISE_STAGE = "pairwise_replay_v3"
_BASE_METRICS = (
    "correct_failure",
    "b6_failure",
    "correct_shortfall",
    "b6_shortfall",
    "correct_peak_debt",
    "b6_peak_debt",
    "correct_terminal_debt",
    "b6_terminal_debt",
    "capacity_underprovisioning",
)
_BOUND_METRICS = (
    "delta_failure_probability",
    "delta_expected_shortfall",
    "flexibility_underprovisioning",
    "correct_failure_probability",
    "correct_expected_shortfall",
    "delta_peak_recovery_debt",
    "delta_terminal_recovery_debt",
    "correct_peak_recovery_debt",
    "correct_terminal_recovery_debt",
)
_BOUND_FIELDS = (
    "cell_id",
    "varied_dimension",
    "metric",
    "lower",
    "upper",
    "independent_product",
    "comonotone",
    "countermonotone",
    "minimum_solver_status",
    "maximum_solver_status",
)
_COUPLING_FIELDS = (
    "cell_id",
    "metric",
    "extremum",
    "row_id",
    "column_id",
    "mass",
)
_PAIR_FIELDS = (
    "cell_id",
    "row_id",
    "column_id",
    "outcome_resolved",
    "correct_capacity",
    "b6_capacity",
    "capacity_underprovisioning",
    "correct_failure",
    "b6_failure",
    "correct_shortfall",
    "b6_shortfall",
    "correct_peak_debt",
    "b6_peak_debt",
    "correct_terminal_debt",
    "b6_terminal_debt",
    "correct_hard_temporal_failure",
    "b6_hard_temporal_failure",
    "correct_physical_policy_failure",
    "b6_physical_policy_failure",
    "correct_service_failure",
    "b6_service_failure",
    "correct_solver_unresolved",
    "b6_solver_unresolved",
)
_CELL_STATUS_FIELDS = (
    "cell_id",
    "varied_dimension",
    "training_resolved",
    "correct_training_feasible",
    "correct_training_proven_infeasible",
    "b6_training_feasible",
    "b6_training_proven_infeasible",
    "pairwise_eligible",
    "pair_count_expected",
    "pair_count_completed",
    "all_pairwise_outcomes_resolved",
)
_POLICY_FIELDS = (
    "cell_id",
    "varied_dimension",
    "variant",
    "resolved",
    "feasible",
    "proven_infeasible",
    "minimum_capacity",
    "termination_condition",
    "solver_status",
    "maximum_residual",
)
_PACKAGE_MEMBERS = {
    "cell_status.csv.gz",
    "checkpoint_inventory.json",
    "pairwise_outcomes.csv.gz",
    "policy_table.csv.gz",
    "power_system_holdout_marginal.csv.gz",
    "provenance.json",
    "summary.json",
    "workload_holdout_marginal.csv.gz",
}


def _path(raw: object, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"{label} must be a nonempty path")
    path = Path(raw)
    return path if path.is_absolute() else _ROOT / path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_json_manifest(directory: Path, expected_sha256: str) -> None:
    manifest_path = directory / "SHA256SUMS.json"
    if not manifest_path.is_file() or _sha256(manifest_path) != expected_sha256:
        raise ValueError("pairwise replay manifest SHA-256 drifted")
    manifest = load_json_strict(manifest_path)
    if not isinstance(manifest, dict) or not manifest:
        raise ValueError("pairwise replay manifest is invalid")
    if set(manifest) != _PACKAGE_MEMBERS:
        raise ValueError("pairwise replay manifest member set drifted")
    for name, digest in manifest.items():
        member = directory / name
        if not member.is_file() or _sha256(member) != digest:
            raise ValueError(f"pairwise replay member drifted: {name}")


def _read_gzip_rows(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None:
            raise ValueError(f"CSV schema is absent: {path}")
        return reader.fieldnames, list(reader)


def _write_gzip_csv(
    path: Path,
    fields: tuple[str, ...],
    rows: Iterable[Mapping[str, object]],
) -> None:
    with (
        path.open("wb") as raw,
        gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed,
        io.TextIOWrapper(compressed, encoding="utf-8", newline="") as text,
    ):
        writer = csv.DictWriter(text, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _number(raw: object, label: str) -> float:
    try:
        value = float(raw)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be numeric") from error
    if not isfinite(value):
        raise ValueError(f"{label} must be finite")
    return value


def _boolean(raw: object, label: str) -> bool:
    if isinstance(raw, bool):
        return raw
    if raw == "True" or raw == "true" or raw == "1":
        return True
    if raw == "False" or raw == "false" or raw == "0":
        return False
    raise ValueError(f"{label} must be boolean")


def _marginal(
    path: Path,
) -> tuple[tuple[str, ...], tuple[float, ...], tuple[float, ...]]:
    fields, rows = _read_gzip_rows(path)
    if fields != ["id", "probability", "stress_score"] or not rows:
        raise ValueError(f"marginal schema drifted: {path}")
    identifiers = tuple(row["id"] for row in rows)
    if any(not item for item in identifiers) or len(set(identifiers)) != len(rows):
        raise ValueError(f"marginal IDs are invalid: {path}")
    probabilities = tuple(
        _number(row["probability"], f"{path} probability") for row in rows
    )
    if any(value < 0.0 for value in probabilities) or abs(sum(probabilities) - 1.0) > 1.0e-9:
        raise ValueError(f"marginal probabilities are invalid: {path}")
    scores = tuple(
        _number(row["stress_score"], f"{path} stress_score") for row in rows
    )
    return identifiers, probabilities, scores


def _expected_pairwise_checkpoint_keys(
    package: Path,
    *,
    expected_parameter_cells: int,
    expected_power_holdout_blocks: int,
    expected_workload_holdout_blocks: int,
) -> tuple[set[str], int]:
    row_ids, _, _ = _marginal(
        package / "power_system_holdout_marginal.csv.gz"
    )
    column_ids, _, _ = _marginal(
        package / "workload_holdout_marginal.csv.gz"
    )
    if (
        len(row_ids) != expected_power_holdout_blocks
        or len(column_ids) != expected_workload_holdout_blocks
    ):
        raise ValueError("pairwise marginal checkpoint dimensions drifted")
    status_fields, status_rows = _read_gzip_rows(
        package / "cell_status.csv.gz"
    )
    if (
        status_fields != list(_CELL_STATUS_FIELDS)
        or len(status_rows) != expected_parameter_cells
        or len({row["cell_id"] for row in status_rows}) != len(status_rows)
    ):
        raise ValueError("pairwise cell checkpoint inventory drifted")
    policy_fields, policy_rows = _read_gzip_rows(
        package / "policy_table.csv.gz"
    )
    if policy_fields != list(_POLICY_FIELDS):
        raise ValueError("pairwise policy checkpoint schema drifted")
    expected_policy_rows = {
        (row["cell_id"], variant)
        for row in status_rows
        for variant in ("correct", "b6")
    }
    observed_policy_rows = {
        (row["cell_id"], row["variant"]) for row in policy_rows
    }
    if (
        observed_policy_rows != expected_policy_rows
        or len(policy_rows) != len(expected_policy_rows)
    ):
        raise ValueError("pairwise policy checkpoint inventory drifted")
    policies = {
        (row["cell_id"], row["variant"]): row for row in policy_rows
    }
    expected_keys = {
        f"policies/{row['cell_id']}.json" for row in status_rows
    }
    eligible_cells = set()
    pair_count = len(row_ids) * len(column_ids)
    for status in status_rows:
        cell_id = status["cell_id"]
        feasible = []
        for variant in ("correct", "b6"):
            policy = policies[(cell_id, variant)]
            policy_feasible = _boolean(
                policy["feasible"],
                f"{variant}.feasible",
            )
            policy_infeasible = _boolean(
                policy["proven_infeasible"],
                f"{variant}.proven_infeasible",
            )
            policy_resolved = _boolean(
                policy["resolved"],
                f"{variant}.resolved",
            )
            if (
                policy_feasible and policy_infeasible
                or policy_resolved is not (
                    policy_feasible or policy_infeasible
                )
            ):
                raise ValueError("pairwise policy checkpoint status drifted")
            feasible.append(policy_feasible)
        eligible = all(feasible)
        if (
            _boolean(status["pairwise_eligible"], "pairwise_eligible")
            is not eligible
            or int(status["pair_count_expected"])
            != (pair_count if eligible else 0)
        ):
            raise ValueError("pairwise checkpoint eligibility drifted")
        if eligible:
            eligible_cells.add(cell_id)
    expected_keys.update(
        f"pairs/{cell_id}/{row_id}__{column_id}.json"
        for cell_id in eligible_cells
        for row_id in row_ids
        for column_id in column_ids
    )
    return expected_keys, len(eligible_cells)


def _expected(
    coupling: tuple[tuple[float, ...], ...],
    matrix: tuple[tuple[float, ...], ...],
) -> float:
    return sum(
        mass * value
        for coupling_row, metric_row in zip(coupling, matrix, strict=True)
        for mass, value in zip(coupling_row, metric_row, strict=True)
    )


def _difference(
    correct: tuple[tuple[float, ...], ...],
    b6: tuple[tuple[float, ...], ...],
) -> tuple[tuple[float, ...], ...]:
    return tuple(
        tuple(
            b6_value - correct_value
            for correct_value, b6_value in zip(
                correct_row,
                b6_row,
                strict=True,
            )
        )
        for correct_row, b6_row in zip(correct, b6, strict=True)
    )


def _matrices(
    rows: list[dict[str, str]],
    row_ids: tuple[str, ...],
    column_ids: tuple[str, ...],
) -> dict[str, tuple[tuple[float, ...], ...]]:
    lookup = {}
    for row in rows:
        key = (row["row_id"], row["column_id"])
        if key in lookup:
            raise ValueError("pairwise outcomes contain a duplicate pair")
        lookup[key] = row
    expected = {(row, column) for row in row_ids for column in column_ids}
    if set(lookup) != expected:
        raise ValueError("pairwise outcomes do not cover the complete Cartesian product")
    if any(
        not _boolean(row["outcome_resolved"], "outcome_resolved")
        for row in rows
    ):
        raise ValueError("pairwise outcomes contain unresolved rows")
    base = {
        metric: tuple(
            tuple(
                _number(lookup[(row, column)][metric], metric)
                for column in column_ids
            )
            for row in row_ids
        )
        for metric in _BASE_METRICS
    }
    return {
        "delta_failure_probability": _difference(
            base["correct_failure"],
            base["b6_failure"],
        ),
        "delta_expected_shortfall": _difference(
            base["correct_shortfall"],
            base["b6_shortfall"],
        ),
        "flexibility_underprovisioning": base[
            "capacity_underprovisioning"
        ],
        "correct_failure_probability": base["correct_failure"],
        "correct_expected_shortfall": base["correct_shortfall"],
        "delta_peak_recovery_debt": _difference(
            base["correct_peak_debt"],
            base["b6_peak_debt"],
        ),
        "delta_terminal_recovery_debt": _difference(
            base["correct_terminal_debt"],
            base["b6_terminal_debt"],
        ),
        "correct_peak_recovery_debt": base["correct_peak_debt"],
        "correct_terminal_recovery_debt": base["correct_terminal_debt"],
    }


def _sparse_coupling_rows(
    *,
    cell_id: str,
    metric: str,
    extremum: str,
    coupling: tuple[tuple[float, ...], ...],
    row_ids: tuple[str, ...],
    column_ids: tuple[str, ...],
) -> list[dict[str, object]]:
    return [
        {
            "cell_id": cell_id,
            "metric": metric,
            "extremum": extremum,
            "row_id": row_ids[row_index],
            "column_id": column_ids[column_index],
            "mass": mass,
        }
        for row_index, coupling_row in enumerate(coupling)
        for column_index, mass in enumerate(coupling_row)
        if mass > 1.0e-12
    ]


def _ambiguity_reduction(
    bounds_by_cell: dict[str, dict[str, tuple[float, float]]],
    varied_dimension: dict[str, str],
) -> dict[str, object]:
    result = {}
    dimensions = sorted(
        {value for value in varied_dimension.values() if value != "base"}
    )
    for dimension in dimensions:
        registered_cell_ids = [
            cell_id
            for cell_id, varied in varied_dimension.items()
            if varied in {"base", dimension}
        ]
        missing_cell_ids = [
            cell_id
            for cell_id in registered_cell_ids
            if cell_id not in bounds_by_cell
        ]
        if missing_cell_ids:
            result[dimension] = {
                "status": "unresolved",
                "registered_cell_count": len(registered_cell_ids),
                "missing_cell_ids": missing_cell_ids,
                "metrics": {},
            }
            continue
        metrics = {}
        for metric in _BOUND_METRICS:
            intervals = [
                bounds_by_cell[cell_id][metric]
                for cell_id in registered_cell_ids
            ]
            pooled_lower = min(lower for lower, _ in intervals)
            pooled_upper = max(upper for _, upper in intervals)
            pooled_width = pooled_upper - pooled_lower
            conditional_widths = [upper - lower for lower, upper in intervals]
            metrics[metric] = {
                "cell_count": len(registered_cell_ids),
                "pooled_lower": pooled_lower,
                "pooled_upper": pooled_upper,
                "pooled_width": pooled_width,
                "minimum_width_reduction_if_level_known": (
                    pooled_width - max(conditional_widths)
                ),
                "maximum_width_reduction_if_level_known": (
                    pooled_width - min(conditional_widths)
                ),
            }
        result[dimension] = {
            "status": "resolved",
            "registered_cell_count": len(registered_cell_ids),
            "missing_cell_ids": [],
            "metrics": metrics,
        }
    return {
        "definition": (
            "set_identification_width_reduction_without_a_probability_"
            "distribution_over_parameter_levels"
        ),
        "joint_parameter_robustness_claimed": False,
        "dimensions": result,
    }


def _preflight(config_path: Path) -> tuple[dict[str, Any], dict[str, object]]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    contract_path = _path(
        config["provenance"]["contract_path"],
        "provenance.contract_path",
    )
    contract_sha256 = str(config["provenance"]["contract_sha256"])
    contract_identity = load_contract(
        _ROOT,
        path=contract_path,
        expected_sha256=contract_sha256,
        stage=_STAGE,
    )
    if tuple(config["registered_metrics"]) != _BOUND_METRICS:
        raise ValueError("registered metric contract drifted")
    if config["ambiguity_set"] != {
        "type": "complete_discrete_transport_polytope",
        "support": "unrestricted_complete_Cartesian_product",
        "within_block_hour_order_preserved": True,
        "empirical_joint_distribution_claimed": False,
        "canonical_diagnostics": [
            "independent_product",
            "comonotone_by_registered_stress_score",
            "countermonotone_by_registered_stress_score",
            "minimum_metric_transport",
            "maximum_metric_transport",
        ],
    }:
        raise ValueError("transport ambiguity-set contract drifted")
    ready = config["input"]["pairwise_replay_ready"] is True
    package = _path(
        config["input"]["pairwise_replay_package"],
        "pairwise_replay_package",
    )
    summary = None
    pairwise_provenance_sha256 = None
    if ready:
        digest = config["input"]["pairwise_replay_manifest_sha256"]
        if not isinstance(digest, str) or len(digest) != 64:
            raise ValueError("pairwise replay manifest must be frozen")
        _verify_json_manifest(package, digest)
        summary = load_json_strict(package / "summary.json")
        pairwise_provenance_path = package / "provenance.json"
        pairwise_provenance_sha256 = sha256_file(
            pairwise_provenance_path
        )
        expected_checkpoint_keys, eligible_cell_count = (
            _expected_pairwise_checkpoint_keys(
                package,
                expected_parameter_cells=int(
                    config["input"]["expected_parameter_cells"]
                ),
                expected_power_holdout_blocks=int(
                    config["input"]["expected_power_holdout_blocks"]
                ),
                expected_workload_holdout_blocks=int(
                    config["input"]["expected_workload_holdout_blocks"]
                ),
            )
        )
        expected_summary = {
            "schema": config["input"]["expected_pairwise_schema"],
            "parameter_cell_count": int(
                config["input"]["expected_parameter_cells"]
            ),
            "holdout_power_block_count": int(
                config["input"]["expected_power_holdout_blocks"]
            ),
            "holdout_workload_block_count": int(
                config["input"]["expected_workload_holdout_blocks"]
            ),
            "pairwise_eligible_cell_count": eligible_cell_count,
            "holdout_provision_reoptimized": False,
            "holdout_recourse_reoptimized": False,
            "operational_policy": (
                "causal_myopic_grid_first_then_CFE_with_current_state_only"
            ),
            "physical_execution_envelope": "correct_shared_envelope",
            "empirical_joint_distribution_claimed": False,
            "empirical_probability_claimed": False,
            "security_certified": False,
            "config_sha256": config["input"][
                "expected_pairwise_config_sha256"
            ],
            "provenance_sha256": pairwise_provenance_sha256,
        }
        if not isinstance(summary, dict) or any(
            summary.get(key) != value
            for key, value in expected_summary.items()
        ):
            raise ValueError("pairwise replay summary contract drifted")
        if not isinstance(
            summary.get("all_eligible_pairwise_outcomes_resolved"),
            bool,
        ):
            raise ValueError("pairwise replay resolution status drifted")
        pairwise_contract = load_contract(
            _ROOT,
            path=contract_path,
            expected_sha256=contract_sha256,
            stage=_PAIRWISE_STAGE,
        )
        pairwise_provenance = load_json_strict(pairwise_provenance_path)
        checkpoint_inventory = load_json_strict(
            package / "checkpoint_inventory.json"
        )
        verify_checkpoint_inventory_bundle(
            pairwise_provenance,
            checkpoint_inventory,
            summary,
            stage=_PAIRWISE_STAGE,
            expected_config_sha256=str(
                config["input"]["expected_pairwise_config_sha256"]
            ),
            contract_identity=pairwise_contract,
            expected_inputs={
                "power_system_dispatch_manifest_sha256": config["input"][
                    "expected_power_system_dispatch_manifest_sha256"
                ],
                "power_system_dispatch_provenance_sha256": config["input"][
                    "expected_power_system_dispatch_provenance_sha256"
                ],
                "workload_manifest_sha256": config["input"][
                    "expected_workload_manifest_sha256"
                ],
                "workload_config_sha256": config["input"][
                    "expected_workload_config_sha256"
                ],
                "workload_implementation_sha256": config["input"][
                    "expected_workload_implementation_sha256"
                ],
                "workload_source_sha256": config["input"][
                    "expected_workload_source_sha256"
                ],
            },
            expected_checkpoint_keys=expected_checkpoint_keys,
        )
    report = {
        "schema": "rq2_public_identification_grid_preflight_v3",
        "config_sha256": _sha256(config_path),
        "pairwise_replay_ready": ready,
        "pairwise_summary_loaded": summary is not None,
        "formal_execution_ready": config["execution"][
            "formal_execution_ready"
        ],
        "independent_R4_review_passed": config["execution"][
            "independent_R4_review_passed"
        ],
        "user_formal_run_authorized": config["execution"][
            "user_formal_run_authorized"
        ],
        "provenance_contract_sha256": contract_sha256,
    }
    return config, {
        "package": package,
        "report": report,
        "summary": summary,
        "contract_identity": contract_identity,
        "pairwise_provenance_sha256": pairwise_provenance_sha256,
    }


def run(
    config_path: Path,
    *,
    validate_only: bool = False,
) -> dict[str, object]:
    config_path = config_path.resolve()
    config, context = _preflight(config_path)
    if validate_only:
        return context["report"]
    execution = config["execution"]
    if (
        config["input"]["pairwise_replay_ready"] is not True
        or execution["formal_execution_ready"] is not True
        or execution["independent_R4_review_passed"] is not True
        or execution["user_formal_run_authorized"] is not True
    ):
        raise ValueError(
            "pairwise_replay_ready, formal_execution_ready, "
            "independent_R4_review_passed, and user_formal_run_authorized "
            "must all be true before identification"
        )

    package = context["package"]
    row_ids, row_probability, row_scores = _marginal(
        package / "power_system_holdout_marginal.csv.gz"
    )
    column_ids, column_probability, column_scores = _marginal(
        package / "workload_holdout_marginal.csv.gz"
    )
    status_fields, status_rows = _read_gzip_rows(
        package / "cell_status.csv.gz"
    )
    if status_fields != list(_CELL_STATUS_FIELDS):
        raise ValueError("cell status schema drifted")
    if (
        len(status_rows) != int(config["input"]["expected_parameter_cells"])
        or len({row["cell_id"] for row in status_rows}) != len(status_rows)
    ):
        raise ValueError("cell status inventory drifted")
    observed_all_resolved = all(
        not _boolean(row["pairwise_eligible"], "pairwise_eligible")
        or _boolean(
            row["all_pairwise_outcomes_resolved"],
            "all_pairwise_outcomes_resolved",
        )
        for row in status_rows
    )
    if (
        context["summary"]["all_eligible_pairwise_outcomes_resolved"]
        is not observed_all_resolved
    ):
        raise ValueError("pairwise summary and cell status disagree")
    policy_fields, policy_rows = _read_gzip_rows(
        package / "policy_table.csv.gz"
    )
    if policy_fields != list(_POLICY_FIELDS):
        raise ValueError("policy table schema drifted")
    expected_policy_keys = {
        (row["cell_id"], variant)
        for row in status_rows
        for variant in ("correct", "b6")
    }
    if {
        (row["cell_id"], row["variant"]) for row in policy_rows
    } != expected_policy_keys:
        raise ValueError("policy table inventory drifted")
    policy_by_key = {
        (row["cell_id"], row["variant"]): row for row in policy_rows
    }
    policy_capacity: dict[tuple[str, str], float] = {}
    for status in status_rows:
        status_training_resolved = _boolean(
            status["training_resolved"],
            "training_resolved",
        )
        status_pairwise_eligible = _boolean(
            status["pairwise_eligible"],
            "pairwise_eligible",
        )
        policy_resolved = []
        policy_feasible = []
        for variant in ("correct", "b6"):
            policy = policy_by_key[(status["cell_id"], variant)]
            feasible = _boolean(policy["feasible"], "policy.feasible")
            proven_infeasible = _boolean(
                policy["proven_infeasible"],
                "policy.proven_infeasible",
            )
            resolved = _boolean(policy["resolved"], "policy.resolved")
            if (
                policy["varied_dimension"] != status["varied_dimension"]
                or feasible and proven_infeasible
                or resolved is not (feasible or proven_infeasible)
            ):
                raise ValueError("policy table contains an invalid status")
            if feasible:
                capacity = _number(
                    policy["minimum_capacity"],
                    "policy.minimum_capacity",
                )
                if capacity < 0.0:
                    raise ValueError("policy capacity must be nonnegative")
                policy_capacity[(status["cell_id"], variant)] = capacity
            elif policy["minimum_capacity"] != "":
                raise ValueError("nonfeasible policy cannot report capacity")
            policy_resolved.append(resolved)
            policy_feasible.append(feasible)
            if (
                feasible is not _boolean(
                    status[f"{variant}_training_feasible"],
                    f"{variant}_training_feasible",
                )
                or proven_infeasible is not _boolean(
                    status[f"{variant}_training_proven_infeasible"],
                    f"{variant}_training_proven_infeasible",
                )
            ):
                raise ValueError("policy table and cell status disagree")
        if (
            status_training_resolved is not all(policy_resolved)
            or status_pairwise_eligible is not all(policy_feasible)
        ):
            raise ValueError("cell status is inconsistent with policy status")
    pair_fields, pair_rows = _read_gzip_rows(
        package / "pairwise_outcomes.csv.gz"
    )
    if pair_fields != list(_PAIR_FIELDS):
        raise ValueError("pairwise outcome schema drifted")
    known_cells = {row["cell_id"] for row in status_rows}
    if any(row["cell_id"] not in known_cells for row in pair_rows):
        raise ValueError("pairwise outcomes contain an unknown cell")
    pairs_by_cell: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in pair_rows:
        pairs_by_cell[row["cell_id"]].append(row)
    known_pairs = {(row_id, column_id) for row_id in row_ids for column_id in column_ids}
    for status in status_rows:
        cell_id = status["cell_id"]
        expected_count = int(status["pair_count_expected"])
        completed_count = int(status["pair_count_completed"])
        cell_pairs = pairs_by_cell[cell_id]
        observed_count = len(cell_pairs)
        eligible = _boolean(status["pairwise_eligible"], "pairwise_eligible")
        required_count = len(row_ids) * len(column_ids) if eligible else 0
        observed_keys = {
            (row["row_id"], row["column_id"]) for row in cell_pairs
        }
        if (
            expected_count != required_count
            or completed_count != observed_count
            or observed_count != len(observed_keys)
            or not observed_keys.issubset(known_pairs)
        ):
            raise ValueError("pairwise count audit failed")
        if not eligible and observed_count:
            raise ValueError("ineligible cell cannot contain pairwise outcomes")
        all_rows_resolved = True
        for row in cell_pairs:
            outcome_resolved = _boolean(
                row["outcome_resolved"],
                "outcome_resolved",
            )
            solver_resolved = not (
                _boolean(
                    row["correct_solver_unresolved"],
                    "correct_solver_unresolved",
                )
                or _boolean(
                    row["b6_solver_unresolved"],
                    "b6_solver_unresolved",
                )
            )
            if outcome_resolved is not solver_resolved:
                raise ValueError("pairwise resolution flags disagree")
            all_rows_resolved = all_rows_resolved and outcome_resolved
            if not outcome_resolved:
                continue
            for variant in ("correct", "b6"):
                failure = _boolean(
                    row[f"{variant}_failure"],
                    f"{variant}_failure",
                )
                component_failure = any(
                    _boolean(row[field], field)
                    for field in (
                        f"{variant}_hard_temporal_failure",
                        f"{variant}_physical_policy_failure",
                        f"{variant}_service_failure",
                    )
                )
                if failure is not component_failure:
                    raise ValueError("pairwise failure flags disagree")
                capacity = _number(
                    row[f"{variant}_capacity"],
                    f"{variant}_capacity",
                )
                if abs(capacity - policy_capacity[(cell_id, variant)]) > 1.0e-12:
                    raise ValueError("pairwise policy capacity drifted")
                for metric in (
                    f"{variant}_shortfall",
                    f"{variant}_peak_debt",
                    f"{variant}_terminal_debt",
                ):
                    if _number(row[metric], metric) < 0.0:
                        raise ValueError("pairwise metric must be nonnegative")
            underprovisioning = _number(
                row["capacity_underprovisioning"],
                "capacity_underprovisioning",
            )
            expected_underprovisioning = (
                policy_capacity[(cell_id, "correct")]
                - policy_capacity[(cell_id, "b6")]
            )
            if abs(underprovisioning - expected_underprovisioning) > 1.0e-12:
                raise ValueError("pairwise capacity difference drifted")
        reported_resolved = _boolean(
            status["all_pairwise_outcomes_resolved"],
            "all_pairwise_outcomes_resolved",
        )
        expected_resolved = (
            eligible
            and observed_count == required_count
            and all_rows_resolved
        )
        if reported_resolved is not expected_resolved:
            raise ValueError("pairwise resolution status drifted")
    independent = tuple(
        tuple(row_mass * column_mass for column_mass in column_probability)
        for row_mass in row_probability
    )
    comonotone = quantile_coupling(
        row_probability,
        column_probability,
        row_scores,
        column_scores,
    )
    countermonotone = quantile_coupling(
        row_probability,
        column_probability,
        row_scores,
        column_scores,
        reverse_columns=True,
    )
    probability_tolerance = float(
        config["classification"]["probability_tolerance"]
    )
    outcome_tolerance = float(config["classification"]["outcome_tolerance"])
    bound_rows = []
    coupling_rows = []
    identifications = []
    bounds_by_cell = {}
    varied_dimension = {
        row["cell_id"]: row["varied_dimension"] for row in status_rows
    }
    for status in status_rows:
        cell_id = status["cell_id"]
        eligible = _boolean(status["pairwise_eligible"], "pairwise_eligible")
        complete = _boolean(
            status["all_pairwise_outcomes_resolved"],
            "all_pairwise_outcomes_resolved",
        )
        if not eligible or not complete:
            training_resolved = _boolean(
                status["training_resolved"],
                "training_resolved",
            )
            correct_infeasible = _boolean(
                status["correct_training_proven_infeasible"],
                "correct_training_proven_infeasible",
            )
            b6_infeasible = _boolean(
                status["b6_training_proven_infeasible"],
                "b6_training_proven_infeasible",
            )
            if not training_resolved:
                reason = "training_policy_optimization_unresolved"
            elif correct_infeasible or b6_infeasible:
                reason = (
                    "fixed_policy_estimand_undefined_due_to_proven_training_"
                    f"infeasibility_correct_{str(correct_infeasible).lower()}_"
                    f"b6_{str(b6_infeasible).lower()}"
                )
            else:
                reason = "pairwise_execution_incomplete_or_unresolved"
            identifications.append(
                {
                    "cell_id": cell_id,
                    "varied_dimension": status["varied_dimension"],
                    "classification": UNRESOLVED,
                    "identified": False,
                    "compatible_regions": [],
                    "reason": reason,
                }
            )
            continue
        matrices = _matrices(pairs_by_cell[cell_id], row_ids, column_ids)
        cell_bounds = {}
        for metric in _BOUND_METRICS:
            matrix = matrices[metric]
            bound = bound_transport_expectation(
                row_probability,
                column_probability,
                matrix,
            )
            cell_bounds[metric] = (bound.minimum, bound.maximum)
            bound_rows.append(
                {
                    "cell_id": cell_id,
                    "varied_dimension": status["varied_dimension"],
                    "metric": metric,
                    "lower": bound.minimum,
                    "upper": bound.maximum,
                    "independent_product": _expected(independent, matrix),
                    "comonotone": _expected(comonotone, matrix),
                    "countermonotone": _expected(countermonotone, matrix),
                    "minimum_solver_status": bound.minimum_status,
                    "maximum_solver_status": bound.maximum_status,
                }
            )
            coupling_rows.extend(
                _sparse_coupling_rows(
                    cell_id=cell_id,
                    metric=metric,
                    extremum="minimum",
                    coupling=bound.minimizing_coupling,
                    row_ids=row_ids,
                    column_ids=column_ids,
                )
            )
            coupling_rows.extend(
                _sparse_coupling_rows(
                    cell_id=cell_id,
                    metric=metric,
                    extremum="maximum",
                    coupling=bound.maximizing_coupling,
                    row_ids=row_ids,
                    column_ids=column_ids,
                )
            )
        bounds_by_cell[cell_id] = cell_bounds
        classification = classify_identification_bounds(
            IdentificationInputs(
                delta_failure_probability=Interval(
                    *cell_bounds["delta_failure_probability"]
                ),
                delta_expected_shortfall=Interval(
                    *cell_bounds["delta_expected_shortfall"]
                ),
                flexibility_underprovisioning=Interval(
                    *cell_bounds["flexibility_underprovisioning"]
                ),
                correct_failure_probability=Interval(
                    *cell_bounds["correct_failure_probability"]
                ),
                correct_expected_shortfall=Interval(
                    *cell_bounds["correct_expected_shortfall"]
                ),
                all_optimization_resolved=True,
                delta_peak_recovery_debt=Interval(
                    *cell_bounds["delta_peak_recovery_debt"]
                ),
                delta_terminal_recovery_debt=Interval(
                    *cell_bounds["delta_terminal_recovery_debt"]
                ),
            ),
            probability_tolerance=probability_tolerance,
            outcome_tolerance=outcome_tolerance,
        )
        identifications.append(
            {
                "cell_id": cell_id,
                "varied_dimension": status["varied_dimension"],
                "classification": classification.classification,
                "identified": classification.identified,
                "compatible_regions": classification.compatible_regions,
                "reason": classification.reason,
            }
        )

    target = _path(config["output"]["directory"], "output.directory")
    if target.exists():
        raise FileExistsError(f"refusing to overwrite output: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))
    try:
        _write_gzip_csv(
            staging / "cell_bounds.csv.gz",
            _BOUND_FIELDS,
            bound_rows,
        )
        _write_gzip_csv(
            staging / "optimizing_couplings.csv.gz",
            _COUPLING_FIELDS,
            coupling_rows,
        )
        (staging / "cell_identification.json").write_text(
            json.dumps(identifications, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        ambiguity = _ambiguity_reduction(
            bounds_by_cell,
            varied_dimension,
        )
        (staging / "ambiguity_reduction.json").write_text(
            json.dumps(ambiguity, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        counts: dict[str, int] = defaultdict(int)
        for item in identifications:
            counts[item["classification"]] += 1
        stage_base = stage_base_provenance(
            stage=_STAGE,
            config_path=config_path,
            contract_identity=context["contract_identity"],
            inputs={
                "pairwise_replay_manifest_sha256": config["input"][
                    "pairwise_replay_manifest_sha256"
                ],
                "pairwise_replay_provenance_sha256": context[
                    "pairwise_provenance_sha256"
                ],
            },
        )
        provenance_payload = {
            "base": stage_base,
            "stage_base_provenance_sha256": canonical_sha256(stage_base),
        }
        write_json(staging / "provenance.json", provenance_payload)
        summary = {
            "schema": config["output"]["schema"],
            "config_sha256": _sha256(config_path),
            "stage_base_provenance_sha256": canonical_sha256(stage_base),
            "provenance_sha256": sha256_file(staging / "provenance.json"),
            "pairwise_replay_manifest_sha256": config["input"][
                "pairwise_replay_manifest_sha256"
            ],
            "parameter_cell_count": len(status_rows),
            "transport_identified_cell_count": len(bounds_by_cell),
            "unresolved_cell_count": len(status_rows) - len(bounds_by_cell),
            "classification_counts": dict(sorted(counts.items())),
            "all_transport_objectives_reported": (
                len(bounds_by_cell) == len(status_rows)
            ),
            "optimizing_couplings_reported": (
                len(bounds_by_cell) == len(status_rows)
            ),
            "joint_parameter_robustness_claimed": False,
            "empirical_joint_distribution_claimed": False,
            "empirical_probability_claimed": False,
            "security_certified": False,
        }
        (staging / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        names = (
            "ambiguity_reduction.json",
            "cell_bounds.csv.gz",
            "cell_identification.json",
            "optimizing_couplings.csv.gz",
            "provenance.json",
            "summary.json",
        )
        manifest = {name: _sha256(staging / name) for name in names}
        (staging / "SHA256SUMS.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        staging.rename(target)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/rq2_public_identification_grid_v3.yaml"),
    )
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            run(args.config, validate_only=args.validate_only),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
