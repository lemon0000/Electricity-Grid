"""Compute sharp fixed-policy RQ2 bounds over unknown marginal couplings."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import yaml

from src.evaluation.rq2_identification_bounds import (
    IdentificationInputs,
    Interval,
    classify_identification_bounds,
)
from src.scenarios.block_coupling import bound_transport_expectation

_ROOT = Path(__file__).resolve().parents[1]
_PAIR_METRICS = (
    "correct_failure",
    "b6_failure",
    "correct_shortfall",
    "b6_shortfall",
)


def _path(raw: object, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"{label} must be a nonempty path")
    path = Path(raw)
    return path if path.is_absolute() else _ROOT / path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _read_marginal(path: Path) -> tuple[tuple[str, ...], tuple[float, ...]]:
    with path.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    if not rows or set(rows[0]) != {"id", "probability"}:
        raise ValueError("marginal CSV must contain exactly id,probability")
    ids = tuple(row["id"] for row in rows)
    if any(not item for item in ids) or len(ids) != len(set(ids)):
        raise ValueError("marginal IDs must be nonempty and unique")
    probabilities = tuple(float(row["probability"]) for row in rows)
    return ids, probabilities


def _read_pairwise(
    path: Path,
    row_ids: tuple[str, ...],
    column_ids: tuple[str, ...],
) -> dict[str, tuple[tuple[float, ...], ...]]:
    with path.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    expected_fields = {"row_id", "column_id", *_PAIR_METRICS}
    if not rows or set(rows[0]) != expected_fields:
        raise ValueError("pairwise CSV schema drifted")
    lookup = {}
    for row in rows:
        key = (row["row_id"], row["column_id"])
        if key in lookup:
            raise ValueError("pairwise CSV contains a duplicate pair")
        lookup[key] = row
    expected_pairs = {(row, column) for row in row_ids for column in column_ids}
    if set(lookup) != expected_pairs:
        raise ValueError("pairwise CSV must contain the complete Cartesian product")
    return {
        metric: tuple(
            tuple(float(lookup[(row, column)][metric]) for column in column_ids)
            for row in row_ids
        )
        for metric in _PAIR_METRICS
    }


def _bound(
    row_probabilities: tuple[float, ...],
    column_probabilities: tuple[float, ...],
    matrix: tuple[tuple[float, ...], ...],
) -> dict[str, object]:
    result = bound_transport_expectation(
        row_probabilities,
        column_probabilities,
        matrix,
    )
    return {
        "lower": result.minimum,
        "upper": result.maximum,
        "minimizing_coupling": result.minimizing_coupling,
        "maximizing_coupling": result.maximizing_coupling,
    }


def _difference(
    left: tuple[tuple[float, ...], ...],
    right: tuple[tuple[float, ...], ...],
) -> tuple[tuple[float, ...], ...]:
    return tuple(
        tuple(right_value - left_value for left_value, right_value in zip(a, b))
        for a, b in zip(left, right)
    )


def run(config_path: Path) -> dict[str, object]:
    config_path = config_path.resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if config["execution"]["formal_execution_ready"] is not True:
        raise ValueError("formal_execution_ready must be true before execution")
    inputs = config["inputs"]
    row_path = _path(
        inputs["power_system_marginal"]["path"],
        "power_system_marginal.path",
    )
    column_path = _path(
        inputs["workload_marginal"]["path"], "workload_marginal.path"
    )
    pairwise_path = _path(inputs["pairwise_outcomes"]["path"], "pairwise.path")
    for item, path in (
        (inputs["power_system_marginal"], row_path),
        (inputs["workload_marginal"], column_path),
        (inputs["pairwise_outcomes"], pairwise_path),
    ):
        if _sha256(path) != item["sha256"]:
            raise ValueError(f"input SHA-256 drifted: {path}")
    row_ids, row_probability = _read_marginal(row_path)
    column_ids, column_probability = _read_marginal(column_path)
    matrices = _read_pairwise(pairwise_path, row_ids, column_ids)

    delta_failure = _bound(
        row_probability,
        column_probability,
        _difference(matrices["correct_failure"], matrices["b6_failure"]),
    )
    delta_shortfall = _bound(
        row_probability,
        column_probability,
        _difference(matrices["correct_shortfall"], matrices["b6_shortfall"]),
    )
    correct_failure = _bound(
        row_probability, column_probability, matrices["correct_failure"]
    )
    correct_shortfall = _bound(
        row_probability, column_probability, matrices["correct_shortfall"]
    )
    capacity = config["fixed_policy"]["flexibility_underprovisioning"]
    identification = classify_identification_bounds(
        IdentificationInputs(
            delta_failure_probability=Interval(
                delta_failure["lower"], delta_failure["upper"]
            ),
            delta_expected_shortfall=Interval(
                delta_shortfall["lower"], delta_shortfall["upper"]
            ),
            flexibility_underprovisioning=Interval(
                float(capacity["lower"]), float(capacity["upper"])
            ),
            correct_failure_probability=Interval(
                correct_failure["lower"], correct_failure["upper"]
            ),
            correct_expected_shortfall=Interval(
                correct_shortfall["lower"], correct_shortfall["upper"]
            ),
            all_optimization_resolved=True,
        ),
        probability_tolerance=float(config["classification"]["probability_tolerance"]),
        outcome_tolerance=float(config["classification"]["outcome_tolerance"]),
    )
    report = {
        "schema": "rq2_public_data_identification_v1",
        "evaluation_id": config["evaluation"]["id"],
        "config_sha256": _sha256(config_path),
        "implementation_sha256": _sha256(Path(__file__)),
        "input_sha256": {
            "power_system_marginal": _sha256(row_path),
            "workload_marginal": _sha256(column_path),
            "pairwise_outcomes": _sha256(pairwise_path),
        },
        "marginal_sizes": {
            "power_system": len(row_ids),
            "workload": len(column_ids),
        },
        "bounds": {
            "delta_failure_probability": delta_failure,
            "delta_expected_shortfall": delta_shortfall,
            "correct_failure_probability": correct_failure,
            "correct_expected_shortfall": correct_shortfall,
            "flexibility_underprovisioning": capacity,
        },
        "identification": {
            "classification": identification.classification,
            "identified": identification.identified,
            "compatible_regions": identification.compatible_regions,
            "reason": identification.reason,
        },
        "claim_scope": (
            "sharp_transport_bounds_for_fixed_policies_over_all_couplings_of_"
            "the_supplied_public_marginals"
        ),
        "empirical_joint_distribution_claimed": False,
        "empirical_probability_claimed": False,
        "security_certified": False,
        "formal_experiment_authorized": False,
    }
    target = _path(config["output"]["directory"], "output.directory")
    if target.exists():
        raise FileExistsError(f"refusing to overwrite output: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))
    try:
        report_path = staging / "identification_bounds.json"
        report_path.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        manifest = {"identification_bounds.json": _sha256(report_path)}
        (staging / "SHA256SUMS.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        staging.rename(target)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
