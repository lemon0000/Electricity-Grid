from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
from pathlib import Path

import pytest
import yaml

from experiments.run_rq2_public_identification_grid import (
    _ambiguity_reduction,
    run,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_gzip(
    path: Path,
    fields: tuple[str, ...],
    rows: list[dict[str, object]],
) -> None:
    with (
        path.open("wb") as raw,
        gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed,
        io.TextIOWrapper(compressed, encoding="utf-8", newline="") as text,
    ):
        writer = csv.DictWriter(text, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _read_gzip(path: Path) -> tuple[tuple[str, ...], list[dict[str, str]]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        assert reader.fieldnames is not None
        return tuple(reader.fieldnames), list(reader)


def _refresh_manifest(package: Path) -> None:
    names = (
        "cell_status.csv.gz",
        "pairwise_outcomes.csv.gz",
        "policy_table.csv.gz",
        "power_system_holdout_marginal.csv.gz",
        "summary.json",
        "workload_holdout_marginal.csv.gz",
    )
    (package / "SHA256SUMS.json").write_text(
        json.dumps(
            {name: _sha256(package / name) for name in names},
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
    )


def _package(tmp_path: Path, *, complete: bool = True) -> Path:
    package = tmp_path / "pairwise"
    package.mkdir()
    _write_gzip(
        package / "power_system_holdout_marginal.csv.gz",
        ("id", "probability", "stress_score"),
        [
            {"id": "p0", "probability": 0.5, "stress_score": 0},
            {"id": "p1", "probability": 0.5, "stress_score": 1},
        ],
    )
    _write_gzip(
        package / "workload_holdout_marginal.csv.gz",
        ("id", "probability", "stress_score"),
        [
            {"id": "w0", "probability": 0.5, "stress_score": 0},
            {"id": "w1", "probability": 0.5, "stress_score": 1},
        ],
    )
    _write_gzip(
        package / "cell_status.csv.gz",
        (
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
        ),
        [
            {
                "cell_id": "base",
                "varied_dimension": "base",
                "training_resolved": True,
                "correct_training_feasible": True,
                "correct_training_proven_infeasible": False,
                "b6_training_feasible": True,
                "b6_training_proven_infeasible": False,
                "pairwise_eligible": True,
                "pair_count_expected": 4,
                "pair_count_completed": 4 if complete else 3,
                "all_pairwise_outcomes_resolved": complete,
            }
        ],
    )
    _write_gzip(
        package / "policy_table.csv.gz",
        (
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
        ),
        [
            {
                "cell_id": "base",
                "varied_dimension": "base",
                "variant": variant,
                "resolved": True,
                "feasible": True,
                "proven_infeasible": False,
                "minimum_capacity": capacity,
                "termination_condition": "optimal",
                "solver_status": "ok",
                "maximum_residual": 0,
            }
            for variant, capacity in (("correct", 0.2), ("b6", 0.1))
        ],
    )
    pairs = []
    for power in ("p0", "p1"):
        for workload in ("w0", "w1"):
            conflict = int(power[-1] != workload[-1])
            pairs.append(
                {
                    "cell_id": "base",
                    "row_id": power,
                    "column_id": workload,
                    "outcome_resolved": True,
                    "correct_capacity": 0.2,
                    "b6_capacity": 0.1,
                    "correct_failure": 0,
                    "b6_failure": conflict,
                    "correct_shortfall": 0,
                    "b6_shortfall": 2 * conflict,
                    "correct_peak_debt": 0,
                    "b6_peak_debt": conflict,
                    "correct_terminal_debt": 0,
                    "b6_terminal_debt": 0,
                    "capacity_underprovisioning": 0.1,
                    "correct_hard_temporal_failure": False,
                    "b6_hard_temporal_failure": False,
                    "correct_physical_policy_failure": False,
                    "b6_physical_policy_failure": False,
                    "correct_service_failure": False,
                    "b6_service_failure": bool(conflict),
                    "correct_solver_unresolved": False,
                    "b6_solver_unresolved": False,
                }
            )
    if not complete:
        pairs.pop()
    _write_gzip(
        package / "pairwise_outcomes.csv.gz",
        (
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
        ),
        pairs,
    )
    (package / "summary.json").write_text(
        json.dumps(
            {
                "schema": "test_pairwise_replay",
                "parameter_cell_count": 1,
                "holdout_power_block_count": 2,
                "holdout_workload_block_count": 2,
                "all_eligible_pairwise_outcomes_resolved": complete,
                "holdout_provision_reoptimized": False,
                "holdout_recourse_reoptimized": False,
                "operational_policy": (
                    "causal_myopic_grid_first_then_CFE_with_current_state_only"
                ),
                "physical_execution_envelope": "correct_shared_envelope",
                "empirical_joint_distribution_claimed": False,
                "empirical_probability_claimed": False,
                "security_certified": False,
            }
        )
        + "\n",
        encoding="utf-8",
    )
    _refresh_manifest(package)
    return package


def _config(tmp_path: Path, package: Path) -> Path:
    config = {
        "input": {
            "pairwise_replay_ready": True,
            "pairwise_replay_package": str(package),
            "pairwise_replay_manifest_sha256": _sha256(
                package / "SHA256SUMS.json"
            ),
            "expected_pairwise_schema": "test_pairwise_replay",
            "expected_parameter_cells": 1,
            "expected_power_holdout_blocks": 2,
            "expected_workload_holdout_blocks": 2,
        },
        "ambiguity_set": {
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
        },
        "registered_metrics": [
            "delta_failure_probability",
            "delta_expected_shortfall",
            "flexibility_underprovisioning",
            "correct_failure_probability",
            "correct_expected_shortfall",
            "delta_peak_recovery_debt",
            "delta_terminal_recovery_debt",
            "correct_peak_recovery_debt",
            "correct_terminal_recovery_debt",
        ],
        "classification": {
            "probability_tolerance": 1.0e-9,
            "outcome_tolerance": 1.0e-6,
        },
        "execution": {
            "formal_execution_ready": True,
            "independent_R4_review_passed": True,
            "user_formal_run_authorized": True,
        },
        "output": {
            "schema": "test_identification_grid",
            "directory": str(tmp_path / "output"),
        },
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config), encoding="utf-8")
    return path


def test_grid_runner_publishes_sharp_bounds_and_optimizing_couplings(
    tmp_path: Path,
):
    package = _package(tmp_path)
    config = _config(tmp_path, package)

    summary = run(config)

    assert summary["transport_identified_cell_count"] == 1
    assert summary["classification_counts"] == {
        "identified_R2_double_commitment_risk": 1
    }
    output = tmp_path / "output"
    with gzip.open(
        output / "cell_bounds.csv.gz",
        "rt",
        encoding="utf-8",
        newline="",
    ) as source:
        rows = list(csv.DictReader(source))
    failure = next(
        row for row in rows if row["metric"] == "delta_failure_probability"
    )
    assert float(failure["lower"]) == pytest.approx(0.0)
    assert float(failure["upper"]) == pytest.approx(1.0)
    assert float(failure["independent_product"]) == pytest.approx(0.5)
    with gzip.open(
        output / "optimizing_couplings.csv.gz",
        "rt",
        encoding="utf-8",
    ) as source:
        assert len(source.readlines()) > 1
    manifest = json.loads(
        (output / "SHA256SUMS.json").read_text(encoding="utf-8")
    )
    assert set(manifest) == {
        "ambiguity_reduction.json",
        "cell_bounds.csv.gz",
        "cell_identification.json",
        "optimizing_couplings.csv.gz",
        "summary.json",
    }


def test_incomplete_cartesian_cell_is_unresolved_not_a_region(tmp_path: Path):
    package = _package(tmp_path, complete=False)
    config = _config(tmp_path, package)

    summary = run(config)

    assert summary["transport_identified_cell_count"] == 0
    assert summary["classification_counts"] == {"unresolved": 1}
    identification = json.loads(
        (tmp_path / "output" / "cell_identification.json").read_text(
            encoding="utf-8"
        )
    )
    assert identification[0]["classification"] == "unresolved"


def test_identification_requires_all_formal_gates(tmp_path: Path):
    package = _package(tmp_path)
    config_path = _config(tmp_path, package)
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    config["execution"]["independent_R4_review_passed"] = False
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")

    with pytest.raises(ValueError, match="must all be true"):
        run(config_path)


def test_ambiguity_reduction_fails_closed_when_a_registered_level_is_missing():
    result = _ambiguity_reduction(
        {
            "base": {
                metric: (0.0, 1.0)
                for metric in (
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
            }
        },
        {"base": "base", "fraction_low": "flexible_fraction"},
    )

    dimension = result["dimensions"]["flexible_fraction"]
    assert dimension["status"] == "unresolved"
    assert dimension["missing_cell_ids"] == ["fraction_low"]
    assert dimension["metrics"] == {}


def test_pairwise_count_contract_fails_closed(tmp_path: Path):
    package = _package(tmp_path)
    path = package / "cell_status.csv.gz"
    fields, rows = _read_gzip(path)
    rows[0]["pair_count_expected"] = "3"
    _write_gzip(path, fields, rows)
    _refresh_manifest(package)

    with pytest.raises(ValueError, match="pairwise count audit failed"):
        run(_config(tmp_path, package))


def test_pairwise_capacity_must_match_frozen_policy(tmp_path: Path):
    package = _package(tmp_path)
    path = package / "pairwise_outcomes.csv.gz"
    fields, rows = _read_gzip(path)
    rows[0]["correct_capacity"] = "0.3"
    _write_gzip(path, fields, rows)
    _refresh_manifest(package)

    with pytest.raises(ValueError, match="pairwise policy capacity drifted"):
        run(_config(tmp_path, package))
