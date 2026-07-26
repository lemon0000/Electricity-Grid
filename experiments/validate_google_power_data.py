"""Validate the downloaded Google PowerData 2019 production traces."""

from __future__ import annotations

import argparse
import base64
import csv
import gzip
import hashlib
import json
import math
import re
from pathlib import Path

import yaml


TRACE_NAME = re.compile(r"^cell([a-j])_(pdu\d+|mvpp\d+)\.csv\.gz$")


def _verify_sha256_manifest(root: Path) -> bool:
    manifest_path = root / "SHA256SUMS"
    if not manifest_path.exists():
        return False
    expected_paths = set()
    for line in manifest_path.read_text(encoding="ascii").splitlines():
        expected, relative = line.split("  ", maxsplit=1)
        expected_paths.add(relative)
        path = root / Path(relative)
        if not path.is_file():
            return False
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected:
            return False
    actual_paths = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and path.name != "SHA256SUMS"
        and not path.name.endswith(".partial")
    }
    return expected_paths == actual_paths


def _verify_published_objects(root: Path, objects: list[dict[str, object]]) -> bool:
    for source_object in objects:
        path = root / str(source_object["name"])
        if not path.is_file() or path.stat().st_size != source_object["size"]:
            return False
        expected_md5 = base64.b64decode(str(source_object["md5_base64"])).hex()
        if hashlib.md5(path.read_bytes()).hexdigest() != expected_md5:
            return False
    return True


def _object_manifest_sha256(objects: list[dict[str, object]]) -> str:
    lines = [
        "\t".join(
            (
                str(source_object["name"]),
                str(source_object["generation"]),
                str(source_object["size"]),
                str(source_object["md5_base64"]),
            )
        )
        for source_object in sorted(objects, key=lambda item: str(item["name"]))
    ]
    return hashlib.sha256(("\n".join(lines) + "\n").encode()).hexdigest()


def _read_power_domain(
    path: Path,
    expected_columns: list[str],
) -> tuple[int, set[int], set[int], set[int]]:
    match = TRACE_NAME.fullmatch(path.name)
    if match is None:
        raise ValueError(f"Unexpected Google PowerData filename: {path.name}")
    expected_cell, expected_pdu = match.groups()
    times: set[int] = set()
    bad_measurement_times: set[int] = set()
    bad_production_times: set[int] = set()
    row_count = 0
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != expected_columns:
            raise ValueError(f"Unexpected columns in {path.name}: {reader.fieldnames}")
        for row in reader:
            row_count += 1
            if row["cell"] != expected_cell or row["pdu"] != expected_pdu:
                raise ValueError(f"Cell/PDU identity drift in {path.name}")
            timestamp = int(row["time"])
            if timestamp in times:
                raise ValueError(f"Duplicate timestamp in {path.name}: {timestamp}")
            times.add(timestamp)
            for column in ("measured_power_util", "production_power_util"):
                if not math.isfinite(float(row[column])):
                    raise ValueError(f"Non-finite {column} in {path.name}")
            flags = {
                column: row[column].lower()
                for column in ("bad_measurement_data", "bad_production_power_data")
            }
            if any(value not in {"true", "false"} for value in flags.values()):
                raise ValueError(f"Invalid quality flag in {path.name}")
            if flags["bad_measurement_data"] == "true":
                bad_measurement_times.add(timestamp)
            if flags["bad_production_power_data"] == "true":
                bad_production_times.add(timestamp)
    return row_count, times, bad_measurement_times, bad_production_times


def _read_mapping(
    path: Path,
    expected_columns: list[str],
) -> tuple[int, set[str], int, int]:
    row_count = 0
    mapping_keys: set[tuple[str, str, str]] = set()
    machine_pdus: dict[tuple[str, str], set[str]] = {}
    cells: set[str] = set()
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames != expected_columns:
            raise ValueError(f"Unexpected mapping columns: {reader.fieldnames}")
        for row in reader:
            row_count += 1
            key = (row["cell"], row["pdu"], row["machine_id"])
            if key in mapping_keys:
                raise ValueError(f"Duplicate machine mapping row: {key}")
            mapping_keys.add(key)
            machine_key = (row["cell"], row["machine_id"])
            machine_pdus.setdefault(machine_key, set()).add(row["pdu"])
            cells.add(row["cell"])
    multi_pdu_keys = sum(len(pdus) > 1 for pdus in machine_pdus.values())
    return row_count, cells, len(machine_pdus), multi_pdu_keys


def _longest_valid_run(ordered_times: list[int], invalid_times: set[int]) -> int:
    longest = 0
    current = 0
    for timestamp in ordered_times:
        if timestamp in invalid_times:
            current = 0
        else:
            current += 1
            longest = max(longest, current)
    return longest


def run(config_path: Path, *, write_output: bool = True) -> dict[str, object]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    root = Path(config["source"]["path"])
    expected = config["expected"]
    trace_paths = sorted(path for path in root.glob("cell*.csv.gz"))
    metadata = json.loads((root / "SOURCE_OBJECTS.json").read_text(encoding="utf-8-sig"))

    common_times: set[int] | None = None
    row_counts = []
    quality_by_domain: dict[str, tuple[set[int], set[int]]] = {}
    for path in trace_paths:
        rows, times, bad_measurement_times, bad_production_times = _read_power_domain(
            path,
            list(expected["trace_columns"]),
        )
        row_counts.append(rows)
        quality_by_domain[path.name] = (
            bad_measurement_times,
            bad_production_times,
        )
        if common_times is None:
            common_times = times
        elif times != common_times:
            raise ValueError(f"Power-domain calendar differs in {path.name}")

    (
        mapping_rows,
        mapped_cells,
        cell_scoped_machine_keys,
        multi_pdu_cell_machine_keys,
    ) = _read_mapping(
        root / "machine_to_pdu_mapping.csv.gz",
        list(expected["mapping_columns"]),
    )
    ordered_times = sorted(common_times or ())
    time_steps = {
        later - earlier for earlier, later in zip(ordered_times, ordered_times[1:])
    }
    linkable_domains = sum(
        TRACE_NAME.fullmatch(path.name).group(1) in mapped_cells
        for path in trace_paths
    )
    power_only_domains = len(trace_paths) - linkable_domains
    checks = {
        "sha256_manifest": _verify_sha256_manifest(root),
        "published_object_size_and_md5": _verify_published_objects(
            root, metadata["objects"]
        ),
        "source_objects": len(metadata["objects"]) == expected["source_objects"],
        "pinned_object_manifest": _object_manifest_sha256(metadata["objects"])
        == config["source"]["object_manifest_sha256"],
        "total_compressed_bytes": sum(
            source_object["size"] for source_object in metadata["objects"]
        )
        == config["source"]["total_compressed_bytes"],
        "documentation_commit": metadata["documentation_commit"]
        == config["source"]["documentation_commit"],
        "power_domains": len(trace_paths) == expected["power_domains"],
        "workload_linkable_power_domains": linkable_domains
        == expected["workload_linkable_power_domains"],
        "power_only_mvpp_domains": power_only_domains
        == expected["power_only_mvpp_domains"],
        "samples_per_domain": bool(row_counts)
        and set(row_counts) == {expected["samples_per_domain"]},
        "common_five_minute_calendar": time_steps
        == {expected["time_step_microseconds"]},
        "mapping_rows": mapping_rows == expected["mapping_rows"],
        "mapping_cells": mapped_cells == set("abcdefgh"),
        "cell_scoped_machine_keys": cell_scoped_machine_keys
        == expected["cell_scoped_machine_keys"],
        "multi_pdu_mapping_anomalies_recorded": multi_pdu_cell_machine_keys
        == expected["multi_pdu_cell_machine_keys"],
    }
    if not all(checks.values()):
        raise RuntimeError(f"Google PowerData validation failed: {checks}")

    step_hours = expected["time_step_microseconds"] / 3_600_000_000
    domain_quality = []
    for path in trace_paths:
        bad_measurement_times, bad_production_times = quality_by_domain[path.name]
        match = TRACE_NAME.fullmatch(path.name)
        domain_quality.append(
            {
                "file": path.name,
                "cell": match.group(1),
                "pdu": match.group(2),
                "workload_linkable": match.group(1) in mapped_cells,
                "rows": len(ordered_times),
                "valid_measurement_rows": len(ordered_times)
                - len(bad_measurement_times),
                "valid_production_rows": len(ordered_times)
                - len(bad_production_times),
                "measurement_coverage": 1.0
                - len(bad_measurement_times) / len(ordered_times),
                "production_coverage": 1.0
                - len(bad_production_times) / len(ordered_times),
                "longest_valid_measurement_hours": _longest_valid_run(
                    ordered_times, bad_measurement_times
                )
                * step_hours,
                "longest_valid_production_hours": _longest_valid_run(
                    ordered_times, bad_production_times
                )
                * step_hours,
            }
        )
    total_power_rows = sum(row_counts)
    bad_measurement_rows = sum(
        len(quality[0]) for quality in quality_by_domain.values()
    )
    bad_production_rows = sum(
        len(quality[1]) for quality in quality_by_domain.values()
    )

    summary = {
        "dataset": config["source"]["dataset"],
        "documentation_commit": config["source"]["documentation_commit"],
        "license": config["source"]["license"],
        "checks": checks,
        "source_objects": len(metadata["objects"]),
        "object_manifest_sha256": _object_manifest_sha256(metadata["objects"]),
        "compressed_bytes": sum(
            source_object["size"] for source_object in metadata["objects"]
        ),
        "power_domains": len(trace_paths),
        "workload_linkable_power_domains": linkable_domains,
        "power_only_mvpp_domains": power_only_domains,
        "power_rows": total_power_rows,
        "samples_per_domain": sorted(set(row_counts)),
        "mapping_rows": mapping_rows,
        "cell_scoped_machine_keys": cell_scoped_machine_keys,
        "multi_pdu_cell_machine_keys": multi_pdu_cell_machine_keys,
        "mapped_cells": sorted(mapped_cells),
        "first_anonymized_time_microseconds": ordered_times[0],
        "last_anonymized_time_microseconds": ordered_times[-1],
        "time_step_microseconds": next(iter(time_steps)),
        "bad_measurement_rows": bad_measurement_rows,
        "bad_production_rows": bad_production_rows,
        "valid_measurement_rows": total_power_rows - bad_measurement_rows,
        "valid_production_rows": total_power_rows - bad_production_rows,
        "measurement_coverage": 1.0 - bad_measurement_rows / total_power_rows,
        "production_coverage": 1.0 - bad_production_rows / total_power_rows,
        "domain_quality": domain_quality,
        "evidence": config["evidence"],
    }
    if write_output:
        output_path = Path(config["output"]["summary_path"])
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/google_power_2019.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
