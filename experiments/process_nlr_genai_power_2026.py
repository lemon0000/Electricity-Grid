"""Build an auditable catalog of measured and synthetic NLR power profiles."""

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
from contextlib import contextmanager
from pathlib import Path, PurePosixPath
from zipfile import ZipFile

import numpy as np
import pyarrow.parquet as pq
import yaml

_ROOT = Path(__file__).resolve().parents[1]
_CHUNK_SIZE = 1024 * 1024
_EXPECTED_ARCHIVE_MEMBERS = 3191
_POWER_COLUMNS = ("power[W]", "timestep[s]")
_MEASURED_FIELDS = (
    "profile_id",
    "workload_class",
    "model",
    "node_count",
    "gpu_slots",
    "source_member",
    "sample_count",
    "sample_interval_s",
    "sample_rate_hz",
    "sampling_semantics",
    "published_measurement_resolution_supported",
    "duration_s",
    "minimum_compute_power_w",
    "mean_compute_power_w",
    "standard_deviation_compute_power_w",
    "p05_compute_power_w",
    "median_compute_power_w",
    "p95_compute_power_w",
    "maximum_compute_power_w",
    "peak_to_average_ratio",
    "energy_wh",
    "mean_compute_power_per_node_w",
    "mean_compute_power_per_gpu_slot_w",
    "p95_absolute_ramp_w_per_s",
    "maximum_absolute_ramp_w_per_s",
    "source_metadata_mean_power_w",
    "source_metadata_peak_power_w",
    "source_metadata_json",
)
_SYNTHETIC_FIELDS = (
    "profile_id",
    "workload_class",
    "source_member",
    "average_utilization",
    "mean_power_mw",
    "standard_deviation_power_mw",
    "median_power_mw",
    "p90_power_mw",
    "maximum_power_mw",
    "peak_to_average_ratio",
    "source_metadata_json",
)
_GROUP_FIELDS = (
    "workload_class",
    "model",
    "node_count",
    "profile_count",
    "minimum_profile_mean_compute_power_w",
    "median_profile_mean_compute_power_w",
    "maximum_profile_mean_compute_power_w",
    "minimum_profile_peak_compute_power_w",
    "median_profile_peak_compute_power_w",
    "maximum_profile_peak_compute_power_w",
    "median_mean_compute_power_per_gpu_slot_w",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(_CHUNK_SIZE), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bytes_sha256(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


def _path(value: object, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a nonempty path")
    path = Path(value)
    return path if path.is_absolute() else _ROOT / path


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


def _read_csv_member(archive: ZipFile, member: str) -> list[dict[str, str]]:
    with archive.open(member) as raw:
        text = io.TextIOWrapper(raw, encoding="utf-8", newline="")
        return list(csv.DictReader(text))


def _profile_member(prefix: str, metadata: dict[str, str]) -> str:
    source_path = metadata.get("path_save") or metadata.get("path_run")
    if not source_path:
        raise ValueError("Profile metadata does not identify a Parquet file")
    filename = PurePosixPath(source_path).name
    if not filename.endswith(".parquet"):
        raise ValueError(f"Unexpected profile path: {source_path}")
    return f"{prefix.rstrip('/')}/{filename}"


def _optional_float(metadata: dict[str, str], field: str) -> float | None:
    value = metadata.get(field, "")
    return None if value == "" else float(value)


def _profile_statistics(
    archive: ZipFile,
    member: str,
    *,
    node_count: int,
    gpu_slots_per_node: int,
) -> dict[str, float | int]:
    table = pq.read_table(io.BytesIO(archive.read(member)))
    if tuple(table.column_names) != _POWER_COLUMNS:
        raise ValueError(f"Unexpected Parquet schema in {member}: {table.column_names}")
    power = table["power[W]"].combine_chunks().to_numpy(zero_copy_only=False)
    time = table["timestep[s]"].combine_chunks().to_numpy(zero_copy_only=False)
    if len(power) < 2 or len(power) != len(time):
        raise ValueError(f"Invalid profile length in {member}")
    if not np.isfinite(power).all() or not np.isfinite(time).all():
        raise ValueError(f"Non-finite profile value in {member}")
    if (power < 0).any():
        raise ValueError(f"Negative power in {member}")
    deltas = np.diff(time)
    if (deltas <= 0).any():
        raise ValueError(f"Non-increasing time axis in {member}")
    interval = float(np.median(deltas))
    if not np.allclose(deltas, interval, rtol=1e-6, atol=1e-9):
        raise ValueError(f"Nonuniform time axis in {member}")

    mean_power = float(np.mean(power))
    peak_power = float(np.max(power))
    ramp = np.abs(np.diff(power) / deltas)
    gpu_slots = node_count * gpu_slots_per_node
    return {
        "sample_count": len(power),
        "sample_interval_s": interval,
        "sample_rate_hz": 1.0 / interval,
        "duration_s": float(time[-1] - time[0]),
        "minimum_compute_power_w": float(np.min(power)),
        "mean_compute_power_w": mean_power,
        "standard_deviation_compute_power_w": float(np.std(power)),
        "p05_compute_power_w": float(np.quantile(power, 0.05)),
        "median_compute_power_w": float(np.quantile(power, 0.50)),
        "p95_compute_power_w": float(np.quantile(power, 0.95)),
        "maximum_compute_power_w": peak_power,
        "peak_to_average_ratio": peak_power / mean_power,
        "energy_wh": float(np.trapz(power, time) / 3600.0),
        "mean_compute_power_per_node_w": mean_power / node_count,
        "mean_compute_power_per_gpu_slot_w": mean_power / gpu_slots,
        "p95_absolute_ramp_w_per_s": float(np.quantile(ramp, 0.95)),
        "maximum_absolute_ramp_w_per_s": float(np.max(ramp)),
    }


def _check_source_statistics(
    *,
    member: str,
    calculated: dict[str, float | int],
    source_mean: float | None,
    source_peak: float | None,
) -> None:
    comparisons = (
        ("mean", source_mean, float(calculated["mean_compute_power_w"])),
        ("peak", source_peak, float(calculated["maximum_compute_power_w"])),
    )
    for label, expected, observed in comparisons:
        if expected is not None and not math.isclose(
            expected, observed, rel_tol=1e-11, abs_tol=1e-8
        ):
            raise ValueError(f"Source {label} power mismatch in {member}")


def _group_statistics(
    rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    groups: dict[tuple[str, str, int], list[dict[str, object]]] = {}
    for row in rows:
        key = (
            str(row["workload_class"]),
            str(row["model"]),
            int(row["node_count"]),
        )
        groups.setdefault(key, []).append(row)

    result = []
    for (workload_class, model, node_count), members in sorted(groups.items()):
        means = np.array(
            [float(item["mean_compute_power_w"]) for item in members], dtype=float
        )
        peaks = np.array(
            [float(item["maximum_compute_power_w"]) for item in members], dtype=float
        )
        normalized = np.array(
            [float(item["mean_compute_power_per_gpu_slot_w"]) for item in members],
            dtype=float,
        )
        result.append(
            {
                "workload_class": workload_class,
                "model": model,
                "node_count": node_count,
                "profile_count": len(members),
                "minimum_profile_mean_compute_power_w": float(np.min(means)),
                "median_profile_mean_compute_power_w": float(np.median(means)),
                "maximum_profile_mean_compute_power_w": float(np.max(means)),
                "minimum_profile_peak_compute_power_w": float(np.min(peaks)),
                "median_profile_peak_compute_power_w": float(np.median(peaks)),
                "maximum_profile_peak_compute_power_w": float(np.max(peaks)),
                "median_mean_compute_power_per_gpu_slot_w": float(
                    np.median(normalized)
                ),
            }
        )
    return result


def run(config_path: Path) -> dict[str, object]:
    config_bytes = config_path.read_bytes()
    config = yaml.safe_load(config_bytes)
    source = config["source"]
    archive_path = _path(source["archive_path"], "source.archive_path")
    expected_size = int(source["archive_size_bytes"])
    expected_sha256 = str(source["archive_sha256"])
    if archive_path.stat().st_size != expected_size:
        raise ValueError("NLR archive size drifted")
    if _sha256(archive_path) != expected_sha256:
        raise ValueError("NLR archive SHA-256 drifted")

    target = _path(config["output"]["directory"], "output.directory")
    if target.exists():
        raise FileExistsError(f"immutable output directory already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(dir=target.parent, prefix=f".{target.name}.processing-")
    )
    try:
        measured_rows: list[dict[str, object]] = []
        synthetic_rows: list[dict[str, object]] = []
        source_members: dict[str, str] = {}
        gpu_slots_per_node = int(config["processing"]["gpu_slots_per_node"])
        if gpu_slots_per_node <= 0:
            raise ValueError("gpu_slots_per_node must be positive")

        with ZipFile(archive_path) as archive:
            if archive.testzip() is not None:
                raise ValueError("NLR archive CRC verification failed")
            names = archive.namelist()
            if len(names) != _EXPECTED_ARCHIVE_MEMBERS or len(names) != len(
                set(names)
            ):
                raise ValueError("NLR archive member inventory drifted")
            name_set = set(names)
            source_members["README.md"] = _bytes_sha256(archive.read("README.md"))

            for profile_group in config["processing"]["measured_profiles"]:
                workload_class = str(profile_group["workload_class"])
                metadata_member = str(profile_group["metadata_member"])
                metadata_rows = _read_csv_member(archive, metadata_member)
                expected_profiles = int(profile_group["expected_profiles"])
                if len(metadata_rows) != expected_profiles:
                    raise ValueError(
                        f"{workload_class} metadata population drifted"
                    )
                source_members[metadata_member] = _bytes_sha256(
                    archive.read(metadata_member)
                )
                seen_members: set[str] = set()
                for metadata in metadata_rows:
                    member = _profile_member(
                        str(profile_group["results_prefix"]), metadata
                    )
                    if member not in name_set or member in seen_members:
                        raise ValueError(
                            f"Missing or duplicate profile member: {member}"
                        )
                    seen_members.add(member)
                    if profile_group.get("node_count_source") == "metadata":
                        node_count = int(metadata["nodes"])
                    else:
                        node_count = int(profile_group["node_count"])
                    if node_count <= 0:
                        raise ValueError(f"Invalid node count in {member}")
                    statistics = _profile_statistics(
                        archive,
                        member,
                        node_count=node_count,
                        gpu_slots_per_node=gpu_slots_per_node,
                    )
                    expected_interval = float(
                        profile_group["expected_profile_interval_s"]
                    )
                    if not math.isclose(
                        float(statistics["sample_interval_s"]),
                        expected_interval,
                        rel_tol=1e-9,
                        abs_tol=1e-9,
                    ):
                        raise ValueError(f"Profile interval drifted in {member}")
                    sampling_semantics = str(profile_group["sampling_semantics"])
                    published_resolution_supported = (
                        sampling_semantics == "published_measurement_resolution"
                    )
                    source_mean = _optional_float(metadata, "mean_power[W]")
                    source_peak = _optional_float(metadata, "peak_power[W]")
                    _check_source_statistics(
                        member=member,
                        calculated=statistics,
                        source_mean=source_mean,
                        source_peak=source_peak,
                    )
                    model = metadata.get("model") or "llama3_70b"
                    measured_rows.append(
                        {
                            "profile_id": (
                                f"{workload_class}:{PurePosixPath(member).stem}"
                            ),
                            "workload_class": workload_class,
                            "model": model,
                            "node_count": node_count,
                            "gpu_slots": node_count * gpu_slots_per_node,
                            "source_member": member,
                            **statistics,
                            "sampling_semantics": sampling_semantics,
                            "published_measurement_resolution_supported": int(
                                published_resolution_supported
                            ),
                            "source_metadata_mean_power_w": (
                                "" if source_mean is None else source_mean
                            ),
                            "source_metadata_peak_power_w": (
                                "" if source_peak is None else source_peak
                            ),
                            "source_metadata_json": json.dumps(
                                metadata,
                                sort_keys=True,
                                separators=(",", ":"),
                            ),
                        }
                    )

            for profile_group in config["processing"]["synthetic_facility_metadata"]:
                workload_class = str(profile_group["workload_class"])
                metadata_member = str(profile_group["metadata_member"])
                metadata_rows = _read_csv_member(archive, metadata_member)
                if len(metadata_rows) != int(profile_group["expected_profiles"]):
                    raise ValueError(
                        f"{workload_class} facility profile population drifted"
                    )
                source_members[metadata_member] = _bytes_sha256(
                    archive.read(metadata_member)
                )
                for metadata in metadata_rows:
                    member = (
                        f"{str(profile_group['profile_prefix']).rstrip('/')}/"
                        f"{metadata['name']}"
                    )
                    if member not in name_set:
                        raise ValueError(f"Missing facility profile: {member}")
                    synthetic_rows.append(
                        {
                            "profile_id": f"{workload_class}:{metadata['name']}",
                            "workload_class": workload_class,
                            "source_member": member,
                            "average_utilization": float(
                                metadata["Average Utilization"]
                            ),
                            "mean_power_mw": float(metadata["Power Mean (MW)"]),
                            "standard_deviation_power_mw": float(
                                metadata["Power Std Dev (MW)"]
                            ),
                            "median_power_mw": float(metadata["Power Median (MW)"]),
                            "p90_power_mw": float(
                                metadata["Power 90th Percentile (MW)"]
                            ),
                            "maximum_power_mw": float(metadata["Power Max (MW)"]),
                            "peak_to_average_ratio": float(
                                metadata["Power Peak-to-Avg Ratio"]
                            ),
                            "source_metadata_json": json.dumps(
                                metadata,
                                sort_keys=True,
                                separators=(",", ":"),
                            ),
                        }
                    )

        if len(measured_rows) != 2467 or len(synthetic_rows) != 8:
            raise RuntimeError("NLR profile population count drifted")

        with _gzip_csv(
            staging / "measured_power_profile_catalog.csv.gz", _MEASURED_FIELDS
        ) as writer:
            writer.writerows(measured_rows)
        with _gzip_csv(
            staging / "synthetic_facility_profile_catalog.csv.gz", _SYNTHETIC_FIELDS
        ) as writer:
            writer.writerows(synthetic_rows)
        grouped_rows = _group_statistics(measured_rows)
        with _gzip_csv(
            staging / "measured_power_group_statistics.csv.gz", _GROUP_FIELDS
        ) as writer:
            writer.writerows(grouped_rows)

        boundary = config["scientific_boundary"]
        sample_intervals = {
            f"{interval:.9g}": sum(
                math.isclose(
                    float(row["sample_interval_s"]),
                    interval,
                    rel_tol=1e-9,
                    abs_tol=1e-9,
                )
                for row in measured_rows
            )
            for interval in sorted(
                {float(row["sample_interval_s"]) for row in measured_rows}
            )
        }
        unsupported_resolution_profiles = sum(
            not bool(row["published_measurement_resolution_supported"])
            for row in measured_rows
        )
        summary = {
            "schema": "nlr_genai_power_profiles_v2",
            "source": {
                "dataset": source["dataset"],
                "catalog_version": int(source["catalog_version"]),
                "catalog_last_updated": str(source["catalog_last_updated"]),
                "doi": str(source["doi"]),
                "landing_page": str(source["landing_page"]),
                "license": str(source["license"]),
                "archive_size_bytes": expected_size,
                "archive_sha256": expected_sha256,
                "archive_members": _EXPECTED_ARCHIVE_MEMBERS,
                "member_sha256": source_members,
            },
            "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
            "implementation_sha256": _sha256(Path(__file__)),
            "measured_profile_rows": len(measured_rows),
            "synthetic_facility_profile_rows": len(synthetic_rows),
            "measured_group_rows": len(grouped_rows),
            "profile_sample_intervals_s": sample_intervals,
            "profiles_below_published_measurement_resolution": (
                unsupported_resolution_profiles
            ),
            "measured_profiles_by_class": {
                profile_group["workload_class"]: int(
                    profile_group["expected_profiles"]
                )
                for profile_group in config["processing"]["measured_profiles"]
            },
            "evidence_status": {
                "measured_profiles": "observed_hpc_compute_node_power",
                "measured_hardware": boundary["measured_hardware"],
                "published_measurement_intervals_s": list(
                    boundary["published_measurement_intervals_s"]
                ),
                "measured_power_scope": boundary["measured_power_scope"],
                "source_aggregation_recomputed": bool(
                    boundary["source_aggregation_recomputed"]
                ),
                "dynamic_ramp_calibration_ready": bool(
                    boundary["dynamic_ramp_calibration_ready"]
                ),
                "facility_power_observed": bool(
                    boundary["facility_power_observed"]
                ),
                "facility_profiles": boundary["facility_profiles_status"],
                "alibaba_pairing": boundary["alibaba_pairing_status"],
                "direct_pai_gpu_to_power_mapping_ready": bool(
                    boundary["direct_pai_gpu_to_power_mapping_ready"]
                ),
                "deadline_observed": bool(boundary["deadline_observed"]),
                "checkpoint_state_observed": bool(
                    boundary["checkpoint_state_observed"]
                ),
                "recoverable_fraction_observed": bool(
                    boundary["recoverable_fraction_observed"]
                ),
            },
        }
        (staging / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        output_files = (
            "measured_power_profile_catalog.csv.gz",
            "measured_power_group_statistics.csv.gz",
            "synthetic_facility_profile_catalog.csv.gz",
            "summary.json",
        )
        manifest = {name: _sha256(staging / name) for name in output_files}
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
        default=Path("configs/nlr_genai_power_profiles_v2.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
