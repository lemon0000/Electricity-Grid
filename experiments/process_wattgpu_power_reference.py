"""Build a hardware-stratified GPU power reference from pinned WattGPU data."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import shutil
import tempfile
from collections import Counter, defaultdict
from contextlib import contextmanager
from pathlib import Path

import numpy as np
import yaml

_ROOT = Path(__file__).resolve().parents[1]
_CHUNK_SIZE = 1024 * 1024
_EXPERIMENT_FIELDS = (
    "source_row_index",
    "model",
    "gpu_type",
    "gpu_architecture",
    "gpu_memory_gb",
    "gpu_tdp_w",
    "scenario",
    "arrival_rate_qps",
    "request_count",
    "source_prompt_request_count",
    "source_prompt_tokens_total",
    "prompt_generation_request_counts_match",
    "generation_tokens_total",
    "measurement_duration_s",
    "gpu_energy_j",
    "reported_mean_gpu_power_w",
    "energy_duration_mean_gpu_power_w",
    "energy_mean_relative_difference",
    "reported_minimum_gpu_power_w",
    "reported_maximum_gpu_power_w",
    "reported_standard_deviation_gpu_power_w",
    "energy_per_generation_token_j",
    "generation_throughput_tokens_per_s",
    "median_time_to_first_token_s",
    "p95_time_to_first_token_s",
    "median_request_latency_s",
    "p95_request_latency_s",
)
_GROUP_FIELDS = (
    "gpu_type",
    "gpu_architecture",
    "scenario",
    "arrival_rate_qps",
    "experiment_count",
    "model_count",
    "minimum_reported_mean_gpu_power_w",
    "median_reported_mean_gpu_power_w",
    "p95_reported_mean_gpu_power_w",
    "maximum_reported_mean_gpu_power_w",
    "median_energy_per_generation_token_j",
    "median_generation_throughput_tokens_per_s",
    "energy_mean_difference_above_1pct_count",
)
_COVERAGE_FIELDS = (
    "alibaba_gpu_type",
    "machine_count",
    "candidate_task_count",
    "candidate_job_count",
    "declared_gpu_seconds",
    "wattgpu_type",
    "mapping_status",
    "reference_experiment_count",
    "reference_model_count",
    "reference_workload_scope",
    "direct_job_power_mapping_ready",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path(value: object, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a nonempty path")
    path = Path(value)
    return path if path.is_absolute() else _ROOT / path


def _verified_input(specification: dict[str, object], label: str) -> Path:
    path = _path(specification["path"], f"{label}.path")
    if _sha256(path) != specification["sha256"]:
        raise ValueError(f"{label} identity drifted")
    return path


@contextmanager
def _gzip_csv(path: Path, fields: tuple[str, ...]):
    with (
        path.open("wb") as raw,
        gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed,
        io.TextIOWrapper(compressed, encoding="utf-8", newline="") as text,
    ):
        writer = csv.DictWriter(text, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        yield writer


def _read_feature_table(path: Path, key: str) -> dict[str, dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source, delimiter=";"))
    result = {row[key]: row for row in rows}
    if len(result) != len(rows) or "" in result:
        raise ValueError(f"Duplicate or empty key in {path}")
    return result


def _numbers(value: str, *, field: str, row_index: int) -> list[float]:
    decoded = json.loads(value)
    if not isinstance(decoded, list):
        raise TypeError(f"{field} is not a list at source row {row_index}")
    result = [float(item) for item in decoded]
    if not all(math.isfinite(item) for item in result):
        raise ValueError(f"{field} has non-finite values at source row {row_index}")
    return result


def _optional_quantile(values: list[float], probability: float) -> float | str:
    return "" if not values else float(np.quantile(values, probability))


def _scenario(lambda_value: str, *, low_qps: float, high_qps: float) -> str:
    if lambda_value == "":
        return "offline"
    arrival_rate = float(lambda_value)
    if math.isclose(arrival_rate, low_qps, rel_tol=0.0, abs_tol=1e-12):
        return "server_low_qps"
    if math.isclose(arrival_rate, high_qps, rel_tol=0.0, abs_tol=1e-12):
        return "server_high_qps"
    raise ValueError(f"Unexpected server arrival rate: {lambda_value}")


def _experiment_rows(
    source_path: Path,
    *,
    gpu_features: dict[str, dict[str, str]],
    model_features: dict[str, dict[str, str]],
    low_qps: float,
    high_qps: float,
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    with source_path.open(encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        expected_fields = (
            "",
            "model",
            "gpu_type",
            "lambda_qps",
            "generation_tokens_total",
            "measurement_duration",
            "gpu_energy",
            "gpu_0_power_draw_watts_mean",
            "gpu_0_power_draw_watts_min",
            "gpu_0_power_draw_watts_max",
            "gpu_0_power_draw_watts_std",
            "time_to_first_token_seconds_events",
            "e2e_request_latency_seconds_events",
            "request_generation_tokens",
            "request_prompt_tokens",
        )
        if tuple(reader.fieldnames or ()) != expected_fields:
            raise ValueError("Watt Counts subset schema drifted")
        previous_source_index = -1
        for row in reader:
            source_index = int(row[""])
            if source_index <= previous_source_index:
                raise ValueError("Watt Counts source row index is not increasing")
            previous_source_index = source_index
            model = row["model"]
            gpu_type = row["gpu_type"]
            if model not in model_features or gpu_type not in gpu_features:
                raise ValueError(f"Missing feature row at source row {source_index}")

            duration = float(row["measurement_duration"])
            energy = float(row["gpu_energy"])
            reported_mean = float(row["gpu_0_power_draw_watts_mean"])
            minimum = float(row["gpu_0_power_draw_watts_min"])
            maximum = float(row["gpu_0_power_draw_watts_max"])
            standard_deviation = float(row["gpu_0_power_draw_watts_std"])
            generation_total = float(row["generation_tokens_total"])
            numeric = (
                duration,
                energy,
                reported_mean,
                minimum,
                maximum,
                standard_deviation,
                generation_total,
            )
            if not all(math.isfinite(value) for value in numeric):
                raise ValueError(f"Non-finite metric at source row {source_index}")
            if not (
                duration > 0
                and energy > 0
                and generation_total > 0
                and 0 <= minimum <= reported_mean <= maximum
                and standard_deviation >= 0
            ):
                raise ValueError(f"Invalid metric bounds at source row {source_index}")

            generated = _numbers(
                row["request_generation_tokens"],
                field="request_generation_tokens",
                row_index=source_index,
            )
            prompted = _numbers(
                row["request_prompt_tokens"],
                field="request_prompt_tokens",
                row_index=source_index,
            )
            time_to_first = _numbers(
                row["time_to_first_token_seconds_events"],
                field="time_to_first_token_seconds_events",
                row_index=source_index,
            )
            request_latency = _numbers(
                row["e2e_request_latency_seconds_events"],
                field="e2e_request_latency_seconds_events",
                row_index=source_index,
            )
            if not math.isclose(
                sum(generated), generation_total, rel_tol=0.0, abs_tol=1e-9
            ):
                raise ValueError(
                    f"Generation token total mismatch at source row {source_index}"
                )
            if any(value < 0 for value in (*generated, *prompted)):
                raise ValueError(f"Negative token count at source row {source_index}")

            scenario = _scenario(
                row["lambda_qps"], low_qps=low_qps, high_qps=high_qps
            )
            if scenario == "offline":
                if time_to_first or len(request_latency) != 1:
                    raise ValueError(f"Offline event shape drifted at row {source_index}")
            elif not (
                len(time_to_first) == len(request_latency) == len(generated)
            ):
                raise ValueError(f"Server event shape drifted at row {source_index}")

            integrated_mean = energy / duration
            relative_difference = abs(integrated_mean - reported_mean) / reported_mean
            gpu = gpu_features[gpu_type]
            rows.append(
                {
                    "source_row_index": source_index,
                    "model": model,
                    "gpu_type": gpu_type,
                    "gpu_architecture": gpu["architecture"],
                    "gpu_memory_gb": float(gpu["memory_size_gb"]),
                    "gpu_tdp_w": float(gpu["thermal_design_power_w"]),
                    "scenario": scenario,
                    "arrival_rate_qps": (
                        "" if row["lambda_qps"] == "" else float(row["lambda_qps"])
                    ),
                    "request_count": len(generated),
                    "source_prompt_request_count": len(prompted),
                    "source_prompt_tokens_total": float(sum(prompted)),
                    "prompt_generation_request_counts_match": int(
                        len(prompted) == len(generated)
                    ),
                    "generation_tokens_total": generation_total,
                    "measurement_duration_s": duration,
                    "gpu_energy_j": energy,
                    "reported_mean_gpu_power_w": reported_mean,
                    "energy_duration_mean_gpu_power_w": integrated_mean,
                    "energy_mean_relative_difference": relative_difference,
                    "reported_minimum_gpu_power_w": minimum,
                    "reported_maximum_gpu_power_w": maximum,
                    "reported_standard_deviation_gpu_power_w": standard_deviation,
                    "energy_per_generation_token_j": energy / generation_total,
                    "generation_throughput_tokens_per_s": (
                        generation_total / duration
                    ),
                    "median_time_to_first_token_s": _optional_quantile(
                        time_to_first, 0.5
                    ),
                    "p95_time_to_first_token_s": _optional_quantile(
                        time_to_first, 0.95
                    ),
                    "median_request_latency_s": _optional_quantile(
                        request_latency, 0.5
                    ),
                    "p95_request_latency_s": _optional_quantile(
                        request_latency, 0.95
                    ),
                }
            )
    return rows


def _group_rows(
    experiments: list[dict[str, object]],
) -> list[dict[str, object]]:
    groups: dict[tuple[str, str, str], list[dict[str, object]]] = defaultdict(list)
    for row in experiments:
        groups[
            (
                str(row["gpu_type"]),
                str(row["gpu_architecture"]),
                str(row["scenario"]),
            )
        ].append(row)

    result = []
    for (gpu_type, architecture, scenario), members in sorted(groups.items()):
        power = np.array(
            [float(row["reported_mean_gpu_power_w"]) for row in members]
        )
        energy_per_token = np.array(
            [float(row["energy_per_generation_token_j"]) for row in members]
        )
        throughput = np.array(
            [float(row["generation_throughput_tokens_per_s"]) for row in members]
        )
        arrival_rates = {row["arrival_rate_qps"] for row in members}
        if len(arrival_rates) != 1:
            raise ValueError("Scenario group has inconsistent arrival rates")
        result.append(
            {
                "gpu_type": gpu_type,
                "gpu_architecture": architecture,
                "scenario": scenario,
                "arrival_rate_qps": next(iter(arrival_rates)),
                "experiment_count": len(members),
                "model_count": len({str(row["model"]) for row in members}),
                "minimum_reported_mean_gpu_power_w": float(np.min(power)),
                "median_reported_mean_gpu_power_w": float(np.median(power)),
                "p95_reported_mean_gpu_power_w": float(np.quantile(power, 0.95)),
                "maximum_reported_mean_gpu_power_w": float(np.max(power)),
                "median_energy_per_generation_token_j": float(
                    np.median(energy_per_token)
                ),
                "median_generation_throughput_tokens_per_s": float(
                    np.median(throughput)
                ),
                "energy_mean_difference_above_1pct_count": sum(
                    float(row["energy_mean_relative_difference"]) > 0.01
                    for row in members
                ),
            }
        )
    return result


def _alibaba_coverage_rows(
    *,
    machine_catalog: Path,
    task_candidates: Path,
    mappings: dict[str, dict[str, object]],
    experiments: list[dict[str, object]],
) -> list[dict[str, object]]:
    machine_counts: Counter[str] = Counter()
    with gzip.open(machine_catalog, "rt", encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            machine_counts[row["gpu_type"]] += 1

    task_counts: Counter[str] = Counter()
    job_ids: dict[str, set[str]] = defaultdict(set)
    gpu_seconds: Counter[str] = Counter()
    with gzip.open(task_candidates, "rt", encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            gpu_type = row["gpu_type"]
            task_counts[gpu_type] += 1
            job_ids[gpu_type].add(row["job_name"])
            gpu_seconds[gpu_type] += float(row["duration_seconds"]) * float(
                row["requested_gpu_equivalents"]
            )

    reference_counts = Counter(str(row["gpu_type"]) for row in experiments)
    reference_models: dict[str, set[str]] = defaultdict(set)
    for row in experiments:
        reference_models[str(row["gpu_type"])].add(str(row["model"]))

    observed_types = set(machine_counts) | set(task_counts)
    if observed_types != set(mappings):
        raise ValueError("Alibaba GPU mapping inventory drifted")
    result = []
    for gpu_type in sorted(observed_types):
        mapping = mappings[gpu_type]
        reference_type = mapping.get("wattgpu_type")
        result.append(
            {
                "alibaba_gpu_type": gpu_type,
                "machine_count": machine_counts[gpu_type],
                "candidate_task_count": task_counts[gpu_type],
                "candidate_job_count": len(job_ids[gpu_type]),
                "declared_gpu_seconds": float(gpu_seconds[gpu_type]),
                "wattgpu_type": reference_type or "",
                "mapping_status": mapping["status"],
                "reference_experiment_count": (
                    reference_counts[str(reference_type)] if reference_type else 0
                ),
                "reference_model_count": (
                    len(reference_models[str(reference_type)])
                    if reference_type
                    else 0
                ),
                "reference_workload_scope": (
                    "llm_inference_only" if reference_type else "unavailable"
                ),
                "direct_job_power_mapping_ready": 0,
            }
        )
    return result


def run(config_path: Path) -> dict[str, object]:
    config_bytes = config_path.read_bytes()
    config = yaml.safe_load(config_bytes)
    source = config["source"]
    source_root = _path(source["path"], "source.path")
    for relative, identity in config["objects"].items():
        path = source_root / relative
        if (
            path.stat().st_size != int(identity["size"])
            or _sha256(path) != identity["sha256"]
        ):
            raise ValueError(f"WattGPU source identity drifted: {relative}")

    gpu_features = _read_feature_table(
        source_root / "data/gpu_features.csv", "gpu_type"
    )
    model_features = _read_feature_table(
        source_root / "data/model_features.csv", "model_name"
    )
    processing = config["processing"]
    experiments = _experiment_rows(
        source_root / "data/watt_counts_subset.csv",
        gpu_features=gpu_features,
        model_features=model_features,
        low_qps=float(processing["server_qps"]["low"]),
        high_qps=float(processing["server_qps"]["high"]),
    )
    expected_scenarios = {
        str(name): int(count)
        for name, count in processing["expected_scenario_counts"].items()
    }
    scenario_counts = Counter(str(row["scenario"]) for row in experiments)
    if (
        len(experiments) != int(processing["expected_experiment_rows"])
        or len({str(row["model"]) for row in experiments})
        != int(processing["expected_model_count"])
        or len({str(row["gpu_type"]) for row in experiments})
        != int(processing["expected_measured_gpu_count"])
        or len(gpu_features) != int(processing["expected_feature_gpu_count"])
        or dict(scenario_counts) != expected_scenarios
    ):
        raise ValueError("WattGPU population contract drifted")

    groups = _group_rows(experiments)
    coverage = _alibaba_coverage_rows(
        machine_catalog=_verified_input(
            processing["alibaba_machine_catalog"],
            "processing.alibaba_machine_catalog",
        ),
        task_candidates=_verified_input(
            processing["alibaba_task_candidates"],
            "processing.alibaba_task_candidates",
        ),
        mappings=processing["alibaba_hardware_mapping"],
        experiments=experiments,
    )

    target = _path(config["output"]["directory"], "output.directory")
    if target.exists():
        raise FileExistsError(f"immutable output directory already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(dir=target.parent, prefix=f".{target.name}.processing-")
    )
    try:
        with _gzip_csv(
            staging / "experiment_power_reference.csv.gz", _EXPERIMENT_FIELDS
        ) as writer:
            writer.writerows(experiments)
        with _gzip_csv(
            staging / "gpu_scenario_statistics.csv.gz", _GROUP_FIELDS
        ) as writer:
            writer.writerows(groups)
        with _gzip_csv(
            staging / "alibaba_hardware_coverage.csv.gz", _COVERAGE_FIELDS
        ) as writer:
            writer.writerows(coverage)

        boundary = config["scientific_boundary"]
        difference_counts = {
            "above_0p1pct": sum(
                float(row["energy_mean_relative_difference"]) > 0.001
                for row in experiments
            ),
            "above_1pct": sum(
                float(row["energy_mean_relative_difference"]) > 0.01
                for row in experiments
            ),
            "above_5pct": sum(
                float(row["energy_mean_relative_difference"]) > 0.05
                for row in experiments
            ),
            "above_10pct": sum(
                float(row["energy_mean_relative_difference"]) > 0.10
                for row in experiments
            ),
        }
        prompt_count_mismatch_rows = sum(
            not bool(row["prompt_generation_request_counts_match"])
            for row in experiments
        )
        summary = {
            "schema": "wattgpu_power_reference_v1",
            "source": {
                "repository": source["repository"],
                "commit": source["commit"],
                "license": source["license"],
                "release_version": str(source["release_version"]),
                "release_date": str(source["release_date"]),
                "paper_url": source["paper_url"],
                "source_manifest_sha256": _sha256(source_root / "SHA256SUMS"),
            },
            "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
            "implementation_sha256": _sha256(Path(__file__)),
            "experiment_rows": len(experiments),
            "model_count": len({str(row["model"]) for row in experiments}),
            "measured_gpu_count": len(
                {str(row["gpu_type"]) for row in experiments}
            ),
            "gpu_scenario_group_rows": len(groups),
            "scenario_counts": dict(sorted(scenario_counts.items())),
            "energy_mean_relative_difference_counts": difference_counts,
            "prompt_generation_request_count_mismatch_rows": (
                prompt_count_mismatch_rows
            ),
            "maximum_energy_mean_relative_difference": max(
                float(row["energy_mean_relative_difference"])
                for row in experiments
            ),
            "alibaba_hardware_coverage": coverage,
            "evidence_status": {
                "measured_quantity": boundary["measured_quantity"],
                "workload_scope": boundary["workload_scope"],
                "alibaba_shared_job_identity": bool(
                    boundary["alibaba_shared_job_identity"]
                ),
                "alibaba_shared_clock": bool(boundary["alibaba_shared_clock"]),
                "t4_exact_hardware_reference_ready": bool(
                    boundary["t4_exact_hardware_reference_ready"]
                ),
                "v100_exact_hardware_reference_ready": bool(
                    boundary["v100_exact_hardware_reference_ready"]
                ),
                "p100_hardware_reference_ready": bool(
                    boundary["p100_hardware_reference_ready"]
                ),
                "direct_pai_job_to_power_mapping_ready": bool(
                    boundary["direct_pai_job_to_power_mapping_ready"]
                ),
            },
        }
        (staging / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        files = (
            "experiment_power_reference.csv.gz",
            "gpu_scenario_statistics.csv.gz",
            "alibaba_hardware_coverage.csv.gz",
            "summary.json",
        )
        manifest = {name: _sha256(staging / name) for name in files}
        (staging / "SHA256SUMS.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        staging.rename(target)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/wattgpu_power_reference_v1.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
