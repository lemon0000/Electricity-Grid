"""Aggregate Alibaba PAI instance telemetry into job-by-GPU evidence."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import math
import shutil
import sqlite3
import tarfile
import tempfile
from collections import Counter
from contextlib import contextmanager
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[1]
_CHUNK_SIZE = 1024 * 1024
_NUMERIC_FIELDS = (
    "cpu_usage",
    "gpu_wrk_util",
    "avg_mem",
    "max_mem",
    "avg_gpu_wrk_mem",
    "max_gpu_wrk_mem",
    "read",
    "write",
    "read_count",
    "write_count",
)
_OUTPUT_FIELDS = (
    "job_name",
    "gpu_type",
    "group_tag",
    "workload_tag",
    "observed_release_time_s",
    "observed_completion_time_s",
    "observed_execution_span_s",
    "sensor_rows",
    "gpu_work_utilization_observed_rows",
    "mean_gpu_work_utilization_percent_units",
    "mean_gpu_work_utilization_equivalents",
    "minimum_gpu_work_utilization_percent_units",
    "maximum_gpu_work_utilization_percent_units",
    "zero_gpu_work_utilization_rows",
    "cpu_usage_observed_rows",
    "mean_cpu_usage_cores",
    "mean_gpu_memory_observed_rows",
    "mean_gpu_memory_gb",
    "maximum_gpu_memory_gb",
    "mean_main_memory_observed_rows",
    "mean_main_memory_gb",
    "maximum_main_memory_gb",
    "network_read_observed_rows",
    "mean_network_read_bytes",
    "network_write_observed_rows",
    "mean_network_write_bytes",
    "hardware_reference_status",
    "direct_job_power_mapping_ready",
)
_SUMMARY_FIELDS = (
    "gpu_type",
    "machine_count",
    "source_sensor_rows",
    "candidate_sensor_rows",
    "candidate_job_gpu_rows",
    "candidate_job_count",
    "mean_candidate_gpu_work_utilization_percent_units",
    "mean_candidate_gpu_work_utilization_equivalents",
    "zero_candidate_gpu_work_utilization_rows",
    "hardware_reference_status",
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


def _verify_source(
    root: Path, archive: dict[str, object]
) -> tuple[Path, tuple[str, ...]]:
    archive_path = root / str(archive["name"])
    header_path = root / str(archive["header"])
    if (
        archive_path.stat().st_size != int(archive["size"])
        or _sha256(archive_path) != archive["sha256"]
    ):
        raise ValueError("Alibaba sensor archive identity drifted")
    if _sha256(header_path) != archive["header_sha256"]:
        raise ValueError("Alibaba sensor header identity drifted")
    columns = tuple(
        next(csv.reader([header_path.read_text(encoding="utf-8").strip()]))
    )
    if columns != tuple(archive["columns"]):
        raise ValueError("Alibaba sensor header schema drifted")

    digest = hashlib.sha256()
    decompressed_bytes = 0
    rows = 0
    with tarfile.open(archive_path, "r:gz") as source:
        members = [member for member in source.getmembers() if member.isfile()]
        if [member.name for member in members] != [archive["member"]]:
            raise ValueError("Alibaba sensor tar member inventory drifted")
        if members[0].size != int(archive["decompressed_size_bytes"]):
            raise ValueError("Alibaba sensor decompressed size drifted")
        extracted = source.extractfile(members[0])
        if extracted is None:
            raise ValueError("Cannot read Alibaba sensor table")
        for chunk in iter(lambda: extracted.read(8 * _CHUNK_SIZE), b""):
            digest.update(chunk)
            decompressed_bytes += len(chunk)
            rows += chunk.count(b"\n")
    if (
        decompressed_bytes != int(archive["decompressed_size_bytes"])
        or rows != int(archive["rows"])
        or digest.hexdigest() != archive["decompressed_sha256"]
    ):
        raise ValueError("Alibaba sensor decompressed identity drifted")
    return archive_path, columns


def _machine_catalog(path: Path) -> tuple[dict[str, str], Counter[str]]:
    machines: dict[str, str] = {}
    counts: Counter[str] = Counter()
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            if row["machine"] in machines:
                raise ValueError("Duplicate machine in Alibaba machine catalog")
            machines[row["machine"]] = row["gpu_type"]
            counts[row["gpu_type"]] += 1
    return machines, counts


def _hardware_references(path: Path) -> dict[str, str]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        rows = list(csv.DictReader(source))
    result = {row["alibaba_gpu_type"]: row["mapping_status"] for row in rows}
    if len(result) != len(rows):
        raise ValueError("Duplicate Alibaba GPU type in hardware coverage")
    return result


def _database(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=OFF")
    connection.execute("PRAGMA synchronous=OFF")
    connection.execute("PRAGMA temp_store=FILE")
    connection.executescript(
        """
        CREATE TABLE jobs (
            job_name TEXT PRIMARY KEY,
            group_tag TEXT NOT NULL,
            workload_tag TEXT NOT NULL,
            release_time REAL NOT NULL,
            completion_time REAL NOT NULL,
            execution_span REAL NOT NULL
        );
        CREATE TABLE telemetry (
            job_name TEXT NOT NULL,
            gpu_type TEXT NOT NULL,
            sensor_rows INTEGER NOT NULL,
            gpu_util_count INTEGER NOT NULL,
            gpu_util_sum REAL NOT NULL,
            gpu_util_min REAL,
            gpu_util_max REAL,
            gpu_util_zero_rows INTEGER NOT NULL,
            cpu_usage_count INTEGER NOT NULL,
            cpu_usage_sum REAL NOT NULL,
            gpu_memory_count INTEGER NOT NULL,
            gpu_memory_sum REAL NOT NULL,
            gpu_memory_max REAL,
            main_memory_count INTEGER NOT NULL,
            main_memory_sum REAL NOT NULL,
            main_memory_max REAL,
            network_read_count INTEGER NOT NULL,
            network_read_sum REAL NOT NULL,
            network_write_count INTEGER NOT NULL,
            network_write_sum REAL NOT NULL,
            PRIMARY KEY (job_name, gpu_type)
        );
        """
    )
    return connection


def _load_jobs(connection: sqlite3.Connection, path: Path) -> int:
    inserted = 0
    batch: list[tuple[object, ...]] = []
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            batch.append(
                (
                    row["job_name"],
                    row["group_tag"],
                    row["workload_tag"],
                    float(row["observed_release_time_s"]),
                    float(row["observed_completion_time_s"]),
                    float(row["observed_execution_span_s"]),
                )
            )
            if len(batch) == 10000:
                connection.executemany(
                    "INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?)", batch
                )
                inserted += len(batch)
                batch.clear()
    if batch:
        connection.executemany("INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?)", batch)
        inserted += len(batch)
    connection.commit()
    return inserted


def _numeric(row: dict[str, str], field: str, row_number: int) -> float | None:
    value = row[field]
    if value == "":
        return None
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise ValueError(f"Invalid {field} at sensor row {row_number}")
    return number


def _sensor_rows(
    archive_path: Path,
    *,
    member: str,
    columns: tuple[str, ...],
):
    with tarfile.open(archive_path, "r:gz") as source:
        extracted = source.extractfile(member)
        if extracted is None:
            raise ValueError("Cannot stream Alibaba sensor table")
        with io.TextIOWrapper(extracted, encoding="utf-8", newline="") as text:
            for row_number, values in enumerate(csv.reader(text), start=1):
                if len(values) != len(columns):
                    raise ValueError(
                        f"Sensor column count drifted at row {row_number}"
                    )
                yield row_number, dict(zip(columns, values))


def _aggregate_telemetry(
    connection: sqlite3.Connection,
    *,
    archive_path: Path,
    member: str,
    columns: tuple[str, ...],
    machine_types: dict[str, str],
) -> tuple[int, Counter[str], Counter[str]]:
    sql = """
        INSERT INTO telemetry VALUES (
            ?, ?, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
        )
        ON CONFLICT(job_name, gpu_type) DO UPDATE SET
            sensor_rows = sensor_rows + 1,
            gpu_util_count = gpu_util_count + excluded.gpu_util_count,
            gpu_util_sum = gpu_util_sum + excluded.gpu_util_sum,
            gpu_util_min = COALESCE(
                MIN(gpu_util_min, excluded.gpu_util_min),
                gpu_util_min,
                excluded.gpu_util_min
            ),
            gpu_util_max = COALESCE(
                MAX(gpu_util_max, excluded.gpu_util_max),
                gpu_util_max,
                excluded.gpu_util_max
            ),
            gpu_util_zero_rows =
                gpu_util_zero_rows + excluded.gpu_util_zero_rows,
            cpu_usage_count = cpu_usage_count + excluded.cpu_usage_count,
            cpu_usage_sum = cpu_usage_sum + excluded.cpu_usage_sum,
            gpu_memory_count = gpu_memory_count + excluded.gpu_memory_count,
            gpu_memory_sum = gpu_memory_sum + excluded.gpu_memory_sum,
            gpu_memory_max = COALESCE(
                MAX(gpu_memory_max, excluded.gpu_memory_max),
                gpu_memory_max,
                excluded.gpu_memory_max
            ),
            main_memory_count = main_memory_count + excluded.main_memory_count,
            main_memory_sum = main_memory_sum + excluded.main_memory_sum,
            main_memory_max = COALESCE(
                MAX(main_memory_max, excluded.main_memory_max),
                main_memory_max,
                excluded.main_memory_max
            ),
            network_read_count =
                network_read_count + excluded.network_read_count,
            network_read_sum = network_read_sum + excluded.network_read_sum,
            network_write_count =
                network_write_count + excluded.network_write_count,
            network_write_sum = network_write_sum + excluded.network_write_sum
    """
    batch: list[tuple[object, ...]] = []
    source_counts: Counter[str] = Counter()
    missing_counts: Counter[str] = Counter()
    row_count = 0
    for row_number, row in _sensor_rows(
        archive_path, member=member, columns=columns
    ):
        if not all(row[field] for field in (*columns[:6],)):
            raise ValueError(f"Missing sensor identity at row {row_number}")
        machine = row["machine"]
        gpu_type = machine_types.get(machine, "UNMAPPED")
        values = {
            field: _numeric(row, field, row_number) for field in _NUMERIC_FIELDS
        }
        for field, value in values.items():
            if value is None:
                missing_counts[field] += 1
        if (
            (
                values["avg_mem"] is not None
                and values["max_mem"] is not None
                and values["avg_mem"] > values["max_mem"]
            )
            or (
                values["avg_gpu_wrk_mem"] is not None
                and values["max_gpu_wrk_mem"] is not None
                and values["avg_gpu_wrk_mem"] > values["max_gpu_wrk_mem"]
            )
        ):
            raise ValueError(f"Invalid sensor bounds at row {row_number}")
        gpu_util = values["gpu_wrk_util"]
        cpu_usage = values["cpu_usage"]
        gpu_memory = values["avg_gpu_wrk_mem"]
        gpu_memory_max = values["max_gpu_wrk_mem"]
        main_memory = values["avg_mem"]
        main_memory_max = values["max_mem"]
        network_read = values["read"]
        network_write = values["write"]
        batch.append(
            (
                row["job_name"],
                gpu_type,
                int(gpu_util is not None),
                gpu_util or 0.0,
                gpu_util,
                gpu_util,
                int(gpu_util == 0),
                int(cpu_usage is not None),
                0.0 if cpu_usage is None else cpu_usage / 100.0,
                int(gpu_memory is not None),
                gpu_memory or 0.0,
                gpu_memory_max,
                int(main_memory is not None),
                main_memory or 0.0,
                main_memory_max,
                int(network_read is not None),
                network_read or 0.0,
                int(network_write is not None),
                network_write or 0.0,
            )
        )
        source_counts[gpu_type] += 1
        row_count += 1
        if len(batch) == 10000:
            connection.executemany(sql, batch)
            connection.commit()
            batch.clear()
    if batch:
        connection.executemany(sql, batch)
        connection.commit()
    return row_count, source_counts, missing_counts


def _publish_outputs(
    connection: sqlite3.Connection,
    *,
    staging: Path,
    machine_counts: Counter[str],
    source_counts: Counter[str],
    references: dict[str, str],
) -> tuple[int, int, list[dict[str, object]]]:
    output_rows = 0
    candidate_sensor_rows = 0
    with _gzip_csv(staging / "job_gpu_telemetry.csv.gz", _OUTPUT_FIELDS) as writer:
        cursor = connection.execute(
            """
            SELECT
                t.job_name, t.gpu_type, j.group_tag, j.workload_tag,
                j.release_time, j.completion_time, j.execution_span,
                t.sensor_rows, t.gpu_util_count,
                CASE WHEN t.gpu_util_count > 0
                     THEN t.gpu_util_sum / t.gpu_util_count END,
                CASE WHEN t.gpu_util_count > 0
                     THEN t.gpu_util_sum / t.gpu_util_count / 100.0 END,
                t.gpu_util_min, t.gpu_util_max, t.gpu_util_zero_rows,
                t.cpu_usage_count,
                CASE WHEN t.cpu_usage_count > 0
                     THEN t.cpu_usage_sum / t.cpu_usage_count END,
                t.gpu_memory_count,
                CASE WHEN t.gpu_memory_count > 0
                     THEN t.gpu_memory_sum / t.gpu_memory_count END,
                t.gpu_memory_max,
                t.main_memory_count,
                CASE WHEN t.main_memory_count > 0
                     THEN t.main_memory_sum / t.main_memory_count END,
                t.main_memory_max,
                t.network_read_count,
                CASE WHEN t.network_read_count > 0
                     THEN t.network_read_sum / t.network_read_count END,
                t.network_write_count,
                CASE WHEN t.network_write_count > 0
                     THEN t.network_write_sum / t.network_write_count END
            FROM telemetry AS t
            JOIN jobs AS j ON j.job_name = t.job_name
            ORDER BY t.job_name, t.gpu_type
            """
        )
        for values in cursor:
            gpu_type = str(values[1])
            writer.writerow(
                dict(
                    zip(
                        _OUTPUT_FIELDS,
                        (
                            *values,
                            references[gpu_type],
                            0,
                        ),
                    )
                )
            )
            output_rows += 1
            candidate_sensor_rows += int(values[7])

    summary_rows: list[dict[str, object]] = []
    cursor = connection.execute(
        """
        SELECT
            t.gpu_type,
            SUM(t.sensor_rows),
            COUNT(*),
            COUNT(DISTINCT t.job_name),
            SUM(t.gpu_util_sum) / SUM(t.gpu_util_count),
            SUM(t.gpu_util_sum) / SUM(t.gpu_util_count) / 100.0,
            SUM(t.gpu_util_zero_rows)
        FROM telemetry AS t
        JOIN jobs AS j ON j.job_name = t.job_name
        GROUP BY t.gpu_type
        ORDER BY t.gpu_type
        """
    )
    for (
        gpu_type,
        matched_sensor_rows,
        job_gpu_rows,
        job_count,
        mean_utilization,
        mean_utilization_equivalents,
        zero_rows,
    ) in cursor:
        summary_rows.append(
            {
                "gpu_type": gpu_type,
                "machine_count": machine_counts[gpu_type],
                "source_sensor_rows": source_counts[gpu_type],
                "candidate_sensor_rows": matched_sensor_rows,
                "candidate_job_gpu_rows": job_gpu_rows,
                "candidate_job_count": job_count,
                "mean_candidate_gpu_work_utilization_percent_units": (
                    mean_utilization
                ),
                "mean_candidate_gpu_work_utilization_equivalents": (
                    mean_utilization_equivalents
                ),
                "zero_candidate_gpu_work_utilization_rows": zero_rows,
                "hardware_reference_status": references[gpu_type],
                "direct_job_power_mapping_ready": 0,
            }
        )
    with _gzip_csv(
        staging / "gpu_type_telemetry_summary.csv.gz", _SUMMARY_FIELDS
    ) as writer:
        writer.writerows(summary_rows)
    return output_rows, candidate_sensor_rows, summary_rows


def run(config_path: Path) -> dict[str, object]:
    config_bytes = config_path.read_bytes()
    config = yaml.safe_load(config_bytes)
    source = config["source"]
    processing = config["processing"]
    source_root = _path(source["path"], "source.path")
    archive_path, columns = _verify_source(source_root, config["archive"])
    machine_types, machine_counts = _machine_catalog(
        _verified_input(
            processing["machine_catalog"], "processing.machine_catalog"
        )
    )
    references = _hardware_references(
        _verified_input(
            processing["wattgpu_hardware_coverage"],
            "processing.wattgpu_hardware_coverage",
        )
    )
    if set(machine_counts) != set(references):
        raise ValueError("Machine and hardware-reference inventories differ")
    machine_counts["UNMAPPED"] = 0
    references["UNMAPPED"] = "missing_machine_spec"

    target = _path(processing["output_directory"], "processing.output_directory")
    if target.exists():
        raise FileExistsError(f"immutable output directory already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(dir=target.parent, prefix=f".{target.name}.processing-")
    )
    try:
        connection = _database(staging / "telemetry.sqlite3")
        try:
            candidate_jobs = _load_jobs(
                connection,
                _verified_input(
                    processing["job_envelopes"], "processing.job_envelopes"
                ),
            )
            sensor_rows, source_counts, missing_counts = _aggregate_telemetry(
                connection,
                archive_path=archive_path,
                member=str(config["archive"]["member"]),
                columns=columns,
                machine_types=machine_types,
            )
            job_gpu_rows, matched_sensor_rows, summary_rows = _publish_outputs(
                connection,
                staging=staging,
                machine_counts=machine_counts,
                source_counts=source_counts,
                references=references,
            )
        finally:
            connection.close()
        if sensor_rows != int(config["archive"]["rows"]):
            raise RuntimeError("Alibaba sensor row count drifted during processing")

        evidence = processing["evidence"]
        summary = {
            "schema": "alibaba_gpu_telemetry_v1",
            "source": {
                "dataset": source["dataset"],
                "documentation_commit": source["documentation_commit"],
                "license": source["license"],
                "archive_sha256": config["archive"]["sha256"],
                "decompressed_sha256": config["archive"]["decompressed_sha256"],
                "source_manifest_sha256": _sha256(source_root / "SHA256SUMS"),
            },
            "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
            "implementation_sha256": _sha256(Path(__file__)),
            "source_sensor_rows": sensor_rows,
            "candidate_job_population": candidate_jobs,
            "candidate_job_gpu_rows": job_gpu_rows,
            "candidate_sensor_rows": matched_sensor_rows,
            "unmatched_sensor_rows": sensor_rows - matched_sensor_rows,
            "source_sensor_rows_by_gpu_type": {
                gpu_type: source_counts[gpu_type]
                for gpu_type in sorted(source_counts)
            },
            "source_unmapped_machine_rows": source_counts["UNMAPPED"],
            "source_missing_numeric_counts": {
                field: missing_counts[field] for field in _NUMERIC_FIELDS
            },
            "gpu_type_summary": summary_rows,
            "evidence_status": {
                key: value for key, value in evidence.items()
            },
        }
        (staging / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        (staging / "telemetry.sqlite3").unlink()
        files = (
            "job_gpu_telemetry.csv.gz",
            "gpu_type_telemetry_summary.csv.gz",
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
        default=Path("configs/alibaba_gpu_2020_telemetry_v1.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
