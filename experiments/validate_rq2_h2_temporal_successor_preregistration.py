"""Validate the RQ2 temporal successor preregistration without running it."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_PREREGISTRATION = (
    _ROOT / "configs" / "rq2_h2_temporal_successor_preregistration_v1.yaml"
)
_DEFAULT_MANIFEST = (
    _ROOT / "configs" / "rq2_h2_temporal_successor_preregistration_v1.SHA256SUMS.json"
)
_HASH_PATHS = {
    "base_config_sha256": "configs/rq2_h2_temporal_successor_formal_v1.yaml",
    "batch_config_sha256": "configs/rq2_h2_temporal_successor_batch_v1.yaml",
    "google_trace_sha256": (
        "data/processed/google_power_2019/v1/hourly_shape.csv"
    ),
    "alibaba_trace_sha256": (
        "data/processed/alibaba_gpu_2020/v2020/relative_hourly_workload.csv.gz"
    ),
    "temporal_ablation_runner_sha256": (
        "experiments/run_rq2_h2_temporal_source_ablation.py"
    ),
    "temporal_holdout_runner_sha256": (
        "experiments/run_rq2_h2_temporal_holdout.py"
    ),
    "temporal_generator_sha256": (
        "src/scenarios/temporal_trace_scenario_generator.py"
    ),
    "temporal_reducer_sha256": (
        "src/scenarios/temporal_scenario_reduction.py"
    ),
    "batch_driver_sha256": "experiments/run_rq2_formal_batch.py",
    "executor_script_sha256": "scripts/run_experiment.ps1",
    "prior_v3_summary_sha256": (
        "results/tables/rq2_h2_temporal_source_ablation_rts24_v3/summary.json"
    ),
    "prior_v3_manifest_sha256": (
        "results/tables/rq2_h2_temporal_source_ablation_rts24_v3/SHA256SUMS.json"
    ),
}
_CONFIRMATORY_QUANTILES = {
    "q80": (0.80, 0.9708612624236891, 75),
    "q90": (0.90, 0.9805009394329972, 38),
    "q95": (0.95, 0.9855289118330433, 19),
    "q99": (0.99, 0.9921054212765977, 4),
}
_SEEDS = (20260822, 20260823, 20260824)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(raw: object, label: str) -> dict:
    if not isinstance(raw, dict):
        raise TypeError(f"{label} must be a mapping")
    return raw


def _load_yaml(path: Path, label: str) -> dict:
    return _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), label)


def _quantile_type_7(sorted_values: list[float], probability: float) -> float:
    position = (len(sorted_values) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return sorted_values[lower]
    weight = position - lower
    return (
        sorted_values[lower] * (1.0 - weight)
        + sorted_values[upper] * weight
    )


def _training_values(contract: dict) -> tuple[list[float], float]:
    source = _ROOT / contract["source_path"]
    with source.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    values = [float(row[contract["source_column"]]) for row in rows]
    split = round(len(values) * float(contract["split_fraction"]))
    training = values[:split]
    peak = max(training)
    return sorted(value / peak for value in training), peak


def _expected_jobs(base_path: str, base_sha256: str) -> dict[str, dict]:
    jobs = {}
    ordinal = 1
    for label, (_, threshold, _) in _CONFIRMATORY_QUANTILES.items():
        for seed in _SEEDS:
            job_id = f"T{ordinal:02d}_{label}_seed_{seed}"
            jobs[job_id] = {
                "runner": "experiments.run_rq2_h2_temporal_source_ablation",
                "base_config": base_path,
                "base_config_sha256": base_sha256,
                "overrides": {
                    "generator.network_activation_threshold": threshold,
                    "generator.seed": seed,
                },
            }
            ordinal += 1
    for seed in _SEEDS:
        job_id = f"T{ordinal:02d}_boundary_1p0_seed_{seed}"
        jobs[job_id] = {
            "runner": "experiments.run_rq2_h2_temporal_source_ablation",
            "base_config": base_path,
            "base_config_sha256": base_sha256,
            "overrides": {
                "generator.network_activation_threshold": 1.0,
                "generator.seed": seed,
            },
        }
        ordinal += 1
    for ordinal, target in enumerate((25, 100), start=1):
        job_id = f"R{ordinal:02d}_q90_seed_20260822_reduce_{target}"
        jobs[job_id] = {
            "runner": "experiments.run_rq2_h2_temporal_source_ablation",
            "base_config": base_path,
            "base_config_sha256": base_sha256,
            "overrides": {
                "generator.network_activation_threshold": (
                    _CONFIRMATORY_QUANTILES["q90"][1]
                ),
                "generator.seed": 20260822,
                "reduction.target_count": target,
            },
        }
    return jobs


def validate(
    preregistration_path: Path = _DEFAULT_PREREGISTRATION,
    manifest_path: Path = _DEFAULT_MANIFEST,
) -> dict[str, object]:
    """Validate hashes and frozen design without importing any experiment runner."""

    preregistration_path = preregistration_path.resolve()
    manifest_path = manifest_path.resolve()
    config = _load_yaml(preregistration_path, "preregistration")
    prereg = _mapping(config.get("preregistration"), "preregistration")
    if prereg.get("formal_execution_ready") is not False:
        raise ValueError("formal_execution_ready must remain false before authorization")
    if prereg.get("formal_successor_solver_outcomes_observed") is not False:
        raise ValueError("formal successor outcomes must remain unobserved")
    controls = _mapping(config.get("execution_control"), "execution_control")
    if controls.get("formal_runner_invoked_by_this_task") is not False:
        raise ValueError("preregistration task must not invoke the formal runner")
    if controls.get("solver_invoked_by_this_task") is not False:
        raise ValueError("preregistration task must not invoke a solver")

    frozen = _mapping(config.get("frozen_inputs"), "frozen_inputs")
    for key, relative_path in _HASH_PATHS.items():
        expected = frozen.get(key)
        observed = _sha256(_ROOT / relative_path)
        if expected != observed:
            raise ValueError(
                f"{key} drifted for {relative_path}: expected {expected}, "
                f"observed {observed}"
            )

    threshold_contract = _mapping(
        config.get("training_only_threshold_derivation"),
        "training_only_threshold_derivation",
    )
    normalized, peak = _training_values(threshold_contract)
    if len(normalized) != threshold_contract.get("training_hours"):
        raise ValueError("training-hour count drifted")
    if not math.isclose(
        peak,
        float(threshold_contract.get("training_peak_raw")),
        rel_tol=0.0,
        abs_tol=1.0e-15,
    ):
        raise ValueError("training peak drifted")
    declared_thresholds = _mapping(
        threshold_contract.get("thresholds"), "thresholds"
    )
    for label, (probability, expected_threshold, expected_count) in (
        _CONFIRMATORY_QUANTILES.items()
    ):
        declared = _mapping(declared_thresholds.get(label), f"thresholds.{label}")
        observed_threshold = _quantile_type_7(normalized, probability)
        observed_count = sum(
            value >= observed_threshold for value in normalized
        )
        if not math.isclose(
            observed_threshold,
            expected_threshold,
            rel_tol=0.0,
            abs_tol=1.0e-15,
        ):
            raise ValueError(f"{label} threshold drifted")
        if declared.get("normalized_threshold") != expected_threshold:
            raise ValueError(f"{label} declared threshold drifted")
        if declared.get("training_hours_at_or_above") != expected_count:
            raise ValueError(f"{label} exceedance count drifted")
        if observed_count != expected_count:
            raise ValueError(f"{label} observed exceedance count drifted")

    design = _mapping(config.get("frozen_design"), "frozen_design")
    base_path = str(design.get("base_config"))
    batch_path = str(design.get("batch_config"))
    base = _load_yaml(_ROOT / base_path, "base config")
    batch = _load_yaml(_ROOT / batch_path, "batch config")
    generator = _mapping(base.get("generator"), "base.generator")
    reduction = _mapping(base.get("reduction"), "base.reduction")
    if generator.get("n_train") != 200 or generator.get("n_holdout") != 60:
        raise ValueError("formal sample sizes drifted")
    if generator.get("core_window_hours") != 8:
        raise ValueError("core_window_hours drifted")
    if generator.get("recovery_tail_hours") != 4:
        raise ValueError("recovery_tail_hours drifted")
    if generator.get("network_activation_threshold") != (
        _CONFIRMATORY_QUANTILES["q90"][1]
    ):
        raise ValueError("primary q90 threshold drifted")
    if reduction.get("target_count") != 50:
        raise ValueError("primary reduction target drifted")
    if base["evaluation"].get("security_certified") is not False:
        raise ValueError("base config must remain uncertified")

    batch_meta = _mapping(batch.get("batch"), "batch.batch")
    if batch_meta.get("formal_execution_ready") is not False:
        raise ValueError("batch must remain non-execution-ready")
    if batch_meta.get("successor_outcomes_observed") is not False:
        raise ValueError("batch successor outcomes must remain unobserved")
    jobs = batch.get("jobs")
    if not isinstance(jobs, list):
        raise TypeError("batch.jobs must be a list")
    observed_jobs = {
        job["id"]: {key: value for key, value in job.items() if key != "id"}
        for job in jobs
    }
    expected_jobs = _expected_jobs(base_path, frozen["base_config_sha256"])
    if observed_jobs != expected_jobs:
        raise ValueError("frozen 17-job matrix drifted")

    experiment = _load_yaml(_ROOT / "configs/experiment.yaml", "experiment config")
    if experiment.get("experiment", {}).get("kind") != "pytest-smoke":
        raise ValueError("configs/experiment.yaml must remain pytest-smoke")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for relative_path, expected_hash in manifest.items():
        observed_hash = _sha256(_ROOT / relative_path)
        if observed_hash != expected_hash:
            raise ValueError(
                f"manifest hash drifted for {relative_path}: expected "
                f"{expected_hash}, observed {observed_hash}"
            )

    return {
        "preregistration_id": prereg["id"],
        "job_count": len(jobs),
        "confirmatory_cell_count": 24,
        "primary_cell_count": 6,
        "manifest_file_count": len(manifest),
        "formal_execution_ready": False,
        "formal_runner_invoked": False,
        "solver_invoked": False,
        "validation_passed": True,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--preregistration",
        type=Path,
        default=_DEFAULT_PREREGISTRATION,
    )
    parser.add_argument("--manifest", type=Path, default=_DEFAULT_MANIFEST)
    args = parser.parse_args()
    print(
        json.dumps(
            validate(args.preregistration, args.manifest),
            sort_keys=True,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
