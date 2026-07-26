"""Build source-locked Alibaba GPU v2020 stage-1 processed artifacts."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import sqlite3
import tarfile
import tempfile
import time
from collections import Counter, defaultdict
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from pathlib import Path

import yaml


JOB_FIELDS = (
    "job_name",
    "inst_id",
    "user",
    "status",
    "start_time",
    "end_time",
    "duration_seconds",
    "tag_user",
    "gpu_type_spec",
    "group",
    "workload",
    "join_status",
)
TASK_FIELDS = (
    "job_name",
    "task_name",
    "inst_num",
    "status",
    "start_time",
    "end_time",
    "plan_cpu",
    "plan_mem",
    "plan_gpu",
    "gpu_type",
    "duration_seconds",
    "requested_cpu_cores",
    "requested_gpu_equivalents",
    "requested_memory_gb",
    "parent_job_status",
    "parent_job_join_status",
)
HOURLY_FIELDS = (
    "relative_hour",
    "candidate_task_starts",
    "distinct_candidate_jobs",
    "requested_instances",
    "requested_cpu_known_tasks",
    "requested_cpu_cores",
    "requested_gpu_equivalents",
    "requested_memory_known_tasks",
    "requested_memory_gb",
)
MACHINE_FIELDS = ("machine", "gpu_type", "cap_cpu", "cap_mem", "cap_gpu")
OUTPUT_FILES = (
    "jobs.csv.gz",
    "tasks.csv.gz",
    "successful_gpu_task_candidates.csv.gz",
    "relative_hourly_workload.csv.gz",
    "machine_catalog.csv.gz",
)


def _missing(value: str) -> bool:
    return value.strip() == ""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_manifest(root: Path) -> None:
    manifest_path = root / "SHA256SUMS"
    expected_paths = set()
    for line in manifest_path.read_text(encoding="ascii").splitlines():
        expected, relative = line.split("  ", maxsplit=1)
        expected_paths.add(relative)
        path = root / Path(relative)
        if not path.is_file() or _sha256(path) != expected:
            raise ValueError(f"Raw source manifest mismatch: {relative}")
    actual_paths = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file()
        and path.name != "SHA256SUMS"
        and not path.name.endswith(".partial")
    }
    if actual_paths != expected_paths:
        raise ValueError("Raw source manifest file set has drifted")


def _verify_archive(root: Path, name: str, expected: dict[str, object]) -> int:
    path = root / name
    if path.stat().st_size != int(expected["size"]):
        raise ValueError(f"Unexpected archive size: {name}")
    if _sha256(path) != expected["sha256"]:
        raise ValueError(f"Official archive SHA-256 mismatch: {name}")
    header_path = root / str(expected["header"])
    if _sha256(header_path) != expected["header_sha256"]:
        raise ValueError(f"Official header SHA-256 mismatch: {header_path.name}")
    header = next(csv.reader([header_path.read_text(encoding="utf-8").strip()]))
    if header != list(expected["columns"]):
        raise ValueError(f"Official header columns mismatch: {header_path.name}")
    with tarfile.open(path, "r:gz") as archive:
        members = [member for member in archive.getmembers() if member.isfile()]
    if [member.name for member in members] != [expected["member"]]:
        raise ValueError(f"Unexpected tar member set: {name}")
    return members[0].size


def _iter_archive_rows(
    root: Path,
    name: str,
    expected: dict[str, object],
):
    path = root / name
    expected_member = str(expected["member"])
    expected_width = len(expected["columns"])
    seen_files = []
    # The member is consumed incrementally; random-access tar mode is required
    # because TextIOWrapper queries the backing stream's seekability on Windows.
    with tarfile.open(path, "r:gz") as archive:
        for member in archive:
            if not member.isfile():
                continue
            seen_files.append(member.name)
            if member.name != expected_member:
                raise ValueError(f"Unexpected tar member in {name}: {member.name}")
            raw = archive.extractfile(member)
            if raw is None:
                raise ValueError(f"Cannot read {expected_member}")
            with io.TextIOWrapper(raw, encoding="utf-8", newline="") as text:
                for row_number, row in enumerate(csv.reader(text), start=1):
                    if len(row) != expected_width:
                        raise ValueError(
                            f"Column-count mismatch in {expected_member} "
                            f"at row {row_number}"
                        )
                    yield row
    if seen_files != [expected_member]:
        raise ValueError(f"Unexpected tar member set after streaming: {name}")


@contextmanager
def _gzip_csv(path: Path, fields: tuple[str, ...]):
    with path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed:
            with io.TextIOWrapper(
                compressed,
                encoding="utf-8",
                newline="",
            ) as text:
                writer = csv.DictWriter(
                    text,
                    fieldnames=fields,
                    lineterminator="\n",
                    extrasaction="raise",
                )
                writer.writeheader()
                yield writer


def _decimal(
    value: str,
    field: str,
    invalid_counts: Counter[str],
) -> Decimal | None:
    if _missing(value):
        return None
    try:
        number = Decimal(value)
    except InvalidOperation:
        invalid_counts[field] += 1
        return None
    if not number.is_finite():
        invalid_counts[field] += 1
        return None
    return number


def _decimal_text(value: Decimal | None) -> str:
    if value is None:
        return ""
    if value == 0:
        return "0"
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text


def _missing_counts(row: dict[str, str], counter: Counter[str]) -> None:
    for field, value in row.items():
        if _missing(value):
            counter[field] += 1


def _sorted_counter(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def _counts_for(counter: Counter[str], fields: list[str]) -> dict[str, int]:
    return {field: counter[field] for field in fields}


def _assert_expected(expected: object, actual: object, path: str = "processing") -> None:
    if isinstance(expected, dict):
        if not isinstance(actual, dict):
            raise RuntimeError(f"{path} expected a mapping")
        for key, value in expected.items():
            if key not in actual:
                raise RuntimeError(f"{path}.{key} is absent from the processing audit")
            _assert_expected(value, actual[key], f"{path}.{key}")
        return
    if actual != expected:
        raise RuntimeError(f"{path} drifted: expected={expected!r}, actual={actual!r}")


def _database(path: Path) -> sqlite3.Connection:
    connection = sqlite3.connect(path)
    connection.execute("PRAGMA journal_mode=OFF")
    connection.execute("PRAGMA synchronous=OFF")
    connection.execute("PRAGMA temp_store=FILE")
    connection.executescript(
        """
        CREATE TABLE group_tags (
            inst_id TEXT PRIMARY KEY,
            user TEXT NOT NULL,
            gpu_type_spec TEXT NOT NULL,
            group_tag TEXT NOT NULL,
            workload TEXT NOT NULL
        );
        CREATE TABLE jobs (
            row_order INTEGER PRIMARY KEY,
            job_name TEXT NOT NULL UNIQUE,
            inst_id TEXT NOT NULL UNIQUE,
            user TEXT NOT NULL,
            status TEXT NOT NULL,
            start_time TEXT NOT NULL,
            end_time TEXT NOT NULL
        );
        CREATE TABLE task_keys (
            job_name TEXT NOT NULL,
            task_name TEXT NOT NULL,
            PRIMARY KEY (job_name, task_name)
        );
        CREATE TABLE task_job_seen (job_name TEXT PRIMARY KEY);
        CREATE TABLE job_min_task_start (
            job_name TEXT PRIMARY KEY,
            min_start REAL NOT NULL
        );
        CREATE TABLE strict_jobs (job_name TEXT PRIMARY KEY);
        CREATE TABLE candidate_jobs (job_name TEXT PRIMARY KEY);
        CREATE TABLE candidate_hour_jobs (
            source_hour INTEGER NOT NULL,
            job_name TEXT NOT NULL,
            PRIMARY KEY (source_hour, job_name)
        );
        """
    )
    return connection


@contextmanager
def _staging_database(parent: Path, prefix: str):
    with tempfile.TemporaryDirectory(dir=parent, prefix=prefix) as temporary:
        connection = _database(Path(temporary) / "processing.sqlite3")
        try:
            yield Path(temporary), connection
        finally:
            connection.close()


def _source_table_name(archives: dict[str, dict[str, object]], member: str) -> str:
    for name, expected in archives.items():
        if expected["member"] == member:
            return name
    raise ValueError(f"Configured source archive is missing member {member}")


def _publish(staging: Path, output_root: Path) -> None:
    output_root.mkdir(parents=True, exist_ok=True)
    for name in (*OUTPUT_FILES, "summary.json"):
        (staging / name).replace(output_root / name)
    (staging / "SHA256SUMS").replace(output_root / "SHA256SUMS")


def run(
    config_path: Path,
    *,
    output_root: Path | None = None,
) -> dict[str, object]:
    """Process all four stage-1 tables without extracting their tar members."""

    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    root = Path(config["source"]["path"])
    processing = config["processing"]
    output_root = Path(output_root or processing["output_path"])
    if root.resolve() == output_root.resolve() or root.resolve() in output_root.resolve().parents:
        raise ValueError("Processed output must not be written inside the raw source")

    _verify_manifest(root)
    metadata = json.loads((root / "SOURCE_OBJECTS.json").read_text(encoding="utf-8-sig"))
    if metadata["profile"] != config["source"]["profile"]:
        raise ValueError("Alibaba source profile has drifted")
    if metadata["documentation_commit"] != config["source"]["documentation_commit"]:
        raise ValueError("Alibaba documentation commit has drifted")

    archives = config["expected"]["archives"]
    if {item["name"] for item in metadata["archives"]} != set(archives):
        raise ValueError("Alibaba source archive set has drifted")
    decompressed_by_archive = {
        name: _verify_archive(root, name, expected)
        for name, expected in archives.items()
    }
    archive_for = {
        member: _source_table_name(archives, member)
        for member in (
            "pai_group_tag_table.csv",
            "pai_job_table.csv",
            "pai_task_table.csv",
            "pai_machine_spec.csv",
        )
    }

    output_root.parent.mkdir(parents=True, exist_ok=True)
    with _staging_database(
        output_root.parent,
        prefix=f".{output_root.name}.processing-",
    ) as (staging, connection):
        table_rows = Counter()
        missing_by_table: dict[str, Counter[str]] = defaultdict(Counter)
        invalid_numeric_by_table: dict[str, Counter[str]] = defaultdict(Counter)
        numeric_zero_by_table: dict[str, Counter[str]] = defaultdict(Counter)
        numeric_negative_by_table: dict[str, Counter[str]] = defaultdict(Counter)
        job_status = Counter()
        task_status = Counter()

        group_name = archive_for["pai_group_tag_table.csv"]
        group_columns = list(archives[group_name]["columns"])
        for values in _iter_archive_rows(root, group_name, archives[group_name]):
            row = dict(zip(group_columns, values))
            table_rows["group_tags"] += 1
            _missing_counts(row, missing_by_table["group_tags"])
            try:
                connection.execute(
                    "INSERT INTO group_tags VALUES (?, ?, ?, ?, ?)",
                    (
                        row["inst_id"],
                        row["user"],
                        row["gpu_type_spec"],
                        row["group"],
                        row["workload"],
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise ValueError(f"Duplicate group inst_id: {row['inst_id']}") from error
        connection.commit()

        job_name = archive_for["pai_job_table.csv"]
        job_columns = list(archives[job_name]["columns"])
        for row_order, values in enumerate(
            _iter_archive_rows(root, job_name, archives[job_name]),
            start=1,
        ):
            row = dict(zip(job_columns, values))
            table_rows["jobs"] += 1
            _missing_counts(row, missing_by_table["jobs"])
            job_status[row["status"]] += 1
            for field in ("start_time", "end_time"):
                number = _decimal(
                    row[field],
                    field,
                    invalid_numeric_by_table["jobs"],
                )
                if number == 0:
                    numeric_zero_by_table["jobs"][field] += 1
                elif number is not None and number < 0:
                    numeric_negative_by_table["jobs"][field] += 1
            try:
                connection.execute(
                    "INSERT INTO jobs VALUES (?, ?, ?, ?, ?, ?, ?)",
                    (
                        row_order,
                        row["job_name"],
                        row["inst_id"],
                        row["user"],
                        row["status"],
                        row["start_time"],
                        row["end_time"],
                    ),
                )
            except sqlite3.IntegrityError as error:
                raise ValueError(
                    f"Duplicate job_name or job inst_id at row {row_order}"
                ) from error
        connection.commit()

        join_row = connection.execute(
            """
            SELECT
                SUM(CASE WHEN g.inst_id IS NOT NULL THEN 1 ELSE 0 END),
                SUM(CASE WHEN g.inst_id IS NULL THEN 1 ELSE 0 END),
                SUM(CASE WHEN g.inst_id IS NOT NULL
                          AND TRIM(j.user) <> '' AND TRIM(g.user) <> ''
                          AND j.user <> g.user THEN 1 ELSE 0 END)
            FROM jobs AS j
            LEFT JOIN group_tags AS g ON g.inst_id = j.inst_id
            """
        ).fetchone()
        matched_job_group_rows, jobs_without_group, user_conflicts = map(int, join_row)
        orphan_group_rows = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM group_tags AS g
                LEFT JOIN jobs AS j ON j.inst_id = g.inst_id
                WHERE j.inst_id IS NULL
                """
            ).fetchone()[0]
        )

        job_duration_negative = 0
        with _gzip_csv(staging / "jobs.csv.gz", JOB_FIELDS) as writer:
            for values in connection.execute(
                """
                SELECT j.job_name, j.inst_id, j.user, j.status,
                       j.start_time, j.end_time,
                       g.user, g.gpu_type_spec, g.group_tag, g.workload,
                       CASE WHEN g.inst_id IS NULL
                            THEN 'missing_group_tag' ELSE 'matched' END
                FROM jobs AS j
                LEFT JOIN group_tags AS g ON g.inst_id = j.inst_id
                ORDER BY j.row_order
                """
            ):
                (
                    current_job,
                    inst_id,
                    user,
                    status,
                    start_text,
                    end_text,
                    tag_user,
                    gpu_type_spec,
                    group_tag,
                    workload,
                    join_status,
                ) = values
                start = _decimal(start_text, "start_time", Counter())
                end = _decimal(end_text, "end_time", Counter())
                duration = end - start if start is not None and end is not None else None
                if duration is not None and duration < 0:
                    job_duration_negative += 1
                writer.writerow(
                    {
                        "job_name": current_job,
                        "inst_id": inst_id,
                        "user": user,
                        "status": status,
                        "start_time": start_text,
                        "end_time": end_text,
                        "duration_seconds": _decimal_text(duration),
                        "tag_user": tag_user or "",
                        "gpu_type_spec": gpu_type_spec or "",
                        "group": group_tag or "",
                        "workload": workload or "",
                        "join_status": join_status,
                    }
                )

        strict_tasks = 0
        gpu_candidates = 0
        candidate_missing_cpu_tasks = 0
        candidate_missing_memory_tasks = 0
        maximum_plan_gpu_percent: Decimal | None = None
        maximum_requested_gpu_equivalents: Decimal | None = None
        task_parent_missing_rows = 0
        task_end_before_start_rows = 0
        later_task_start_rows = 0
        hourly = defaultdict(
            lambda: {
                "tasks": 0,
                "instances": Decimal(0),
                "cpu_known": 0,
                "cpu": Decimal(0),
                "gpu": Decimal(0),
                "memory_known": 0,
                "memory": Decimal(0),
            }
        )
        hour_seconds = Decimal(str(processing["relative_hour_seconds"]))

        task_name = archive_for["pai_task_table.csv"]
        task_columns = list(archives[task_name]["columns"])
        with (
            _gzip_csv(staging / "tasks.csv.gz", TASK_FIELDS) as task_writer,
            _gzip_csv(
                staging / "successful_gpu_task_candidates.csv.gz",
                TASK_FIELDS,
            ) as candidate_writer,
        ):
            for row_number, values in enumerate(
                _iter_archive_rows(root, task_name, archives[task_name]),
                start=1,
            ):
                row = dict(zip(task_columns, values))
                table_rows["tasks"] += 1
                _missing_counts(row, missing_by_table["tasks"])
                task_status[row["status"]] += 1
                try:
                    connection.execute(
                        "INSERT INTO task_keys VALUES (?, ?)",
                        (row["job_name"], row["task_name"]),
                    )
                except sqlite3.IntegrityError as error:
                    raise ValueError(
                        f"Duplicate task key at row {row_number}: "
                        f"{row['job_name']}/{row['task_name']}"
                    ) from error
                connection.execute(
                    "INSERT OR IGNORE INTO task_job_seen VALUES (?)",
                    (row["job_name"],),
                )
                parent = connection.execute(
                    "SELECT status, start_time FROM jobs WHERE job_name = ?",
                    (row["job_name"],),
                ).fetchone()
                if parent is None:
                    task_parent_missing_rows += 1
                    parent_status = ""
                    parent_start = None
                    parent_join = "missing_parent_job"
                else:
                    parent_status, parent_start_text = parent
                    parent_start = _decimal(parent_start_text, "start_time", Counter())
                    parent_join = "matched_parent_job"

                numbers = {
                    field: _decimal(
                        row[field],
                        field,
                        invalid_numeric_by_table["tasks"],
                    )
                    for field in (
                        "start_time",
                        "end_time",
                        "inst_num",
                        "plan_cpu",
                        "plan_mem",
                        "plan_gpu",
                    )
                }
                for field, number in numbers.items():
                    if number == 0:
                        numeric_zero_by_table["tasks"][field] += 1
                    elif number is not None and number < 0:
                        numeric_negative_by_table["tasks"][field] += 1
                plan_gpu = numbers["plan_gpu"]
                if plan_gpu is not None and (
                    maximum_plan_gpu_percent is None
                    or plan_gpu > maximum_plan_gpu_percent
                ):
                    maximum_plan_gpu_percent = plan_gpu

                start = numbers["start_time"]
                end = numbers["end_time"]
                inst_num = numbers["inst_num"]
                duration = end - start if start is not None and end is not None else None
                if duration is not None and duration < 0:
                    task_end_before_start_rows += 1
                if start is not None and parent_start is not None and start > parent_start:
                    later_task_start_rows += 1
                if start is not None and parent is not None:
                    connection.execute(
                        """
                        INSERT INTO job_min_task_start VALUES (?, ?)
                        ON CONFLICT(job_name) DO UPDATE SET
                            min_start = MIN(min_start, excluded.min_start)
                        """,
                        (row["job_name"], float(start)),
                    )

                requested_cpu = (
                    inst_num * numbers["plan_cpu"] / Decimal(100)
                    if inst_num is not None and numbers["plan_cpu"] is not None
                    else None
                )
                requested_gpu = (
                    inst_num * numbers["plan_gpu"] / Decimal(100)
                    if inst_num is not None and numbers["plan_gpu"] is not None
                    else None
                )
                requested_memory = (
                    inst_num * numbers["plan_mem"]
                    if inst_num is not None and numbers["plan_mem"] is not None
                    else None
                )
                output_row = {
                    **row,
                    "duration_seconds": _decimal_text(duration),
                    "requested_cpu_cores": _decimal_text(requested_cpu),
                    "requested_gpu_equivalents": _decimal_text(requested_gpu),
                    "requested_memory_gb": _decimal_text(requested_memory),
                    "parent_job_status": parent_status,
                    "parent_job_join_status": parent_join,
                }
                task_writer.writerow(output_row)

                strict = (
                    parent_status == "Terminated"
                    and row["status"] == "Terminated"
                    and start is not None
                    and end is not None
                    and inst_num is not None
                    and numbers["plan_gpu"] is not None
                    and end >= start
                    and inst_num > 0
                )
                if strict:
                    strict_tasks += 1
                    connection.execute(
                        "INSERT OR IGNORE INTO strict_jobs VALUES (?)",
                        (row["job_name"],),
                    )
                candidate = strict and requested_gpu is not None and requested_gpu > 0
                if not candidate:
                    continue
                gpu_candidates += 1
                candidate_missing_cpu_tasks += requested_cpu is None
                candidate_missing_memory_tasks += requested_memory is None
                if (
                    maximum_requested_gpu_equivalents is None
                    or requested_gpu > maximum_requested_gpu_equivalents
                ):
                    maximum_requested_gpu_equivalents = requested_gpu
                candidate_writer.writerow(output_row)
                source_hour = int(
                    (start / hour_seconds).to_integral_value(rounding=ROUND_FLOOR)
                )
                connection.execute(
                    "INSERT OR IGNORE INTO candidate_jobs VALUES (?)",
                    (row["job_name"],),
                )
                connection.execute(
                    "INSERT OR IGNORE INTO candidate_hour_jobs VALUES (?, ?)",
                    (source_hour, row["job_name"]),
                )
                values_for_hour = hourly[source_hour]
                values_for_hour["tasks"] += 1
                values_for_hour["instances"] += inst_num
                values_for_hour["gpu"] += requested_gpu
                if requested_cpu is not None:
                    values_for_hour["cpu_known"] += 1
                    values_for_hour["cpu"] += requested_cpu
                if requested_memory is not None:
                    values_for_hour["memory_known"] += 1
                    values_for_hour["memory"] += requested_memory
        connection.commit()

        task_seen_jobs = int(
            connection.execute("SELECT COUNT(*) FROM task_job_seen").fetchone()[0]
        )
        job_rows = table_rows["jobs"]
        task_job_sets_equal = task_parent_missing_rows == 0 and task_seen_jobs == job_rows
        strict_jobs = int(connection.execute("SELECT COUNT(*) FROM strict_jobs").fetchone()[0])
        candidate_jobs = int(
            connection.execute("SELECT COUNT(*) FROM candidate_jobs").fetchone()[0]
        )
        candidate_workload_jobs = int(
            connection.execute(
                """
                SELECT COUNT(*) FROM candidate_jobs AS c
                JOIN jobs AS j ON j.job_name = c.job_name
                JOIN group_tags AS g ON g.inst_id = j.inst_id
                WHERE TRIM(g.workload) <> ''
                """
            ).fetchone()[0]
        )
        jobs_with_computable_min_task_start, zero_min_gap_jobs, positive_min_gap_jobs = map(
            int,
            connection.execute(
                """
                SELECT COUNT(*),
                       SUM(CASE WHEN m.min_start - CAST(j.start_time AS REAL) = 0
                                THEN 1 ELSE 0 END),
                       SUM(CASE WHEN m.min_start - CAST(j.start_time AS REAL) > 0
                                THEN 1 ELSE 0 END)
                FROM jobs AS j
                JOIN job_min_task_start AS m ON m.job_name = j.job_name
                WHERE TRIM(j.start_time) <> ''
                """
            ).fetchone(),
        )

        hourly_rows = 0
        first_source_hour = min(hourly) if hourly else None
        last_source_hour = max(hourly) if hourly else None
        with _gzip_csv(
            staging / "relative_hourly_workload.csv.gz",
            HOURLY_FIELDS,
        ) as writer:
            if first_source_hour is not None and last_source_hour is not None:
                distinct_by_hour = dict(
                    connection.execute(
                        """
                        SELECT source_hour, COUNT(*)
                        FROM candidate_hour_jobs
                        GROUP BY source_hour
                        """
                    )
                )
                for source_hour in range(first_source_hour, last_source_hour + 1):
                    values = hourly.get(source_hour)
                    if values is None:
                        values = {
                            "tasks": 0,
                            "instances": Decimal(0),
                            "cpu_known": 0,
                            "cpu": Decimal(0),
                            "gpu": Decimal(0),
                            "memory_known": 0,
                            "memory": Decimal(0),
                        }
                    writer.writerow(
                        {
                            "relative_hour": source_hour - first_source_hour,
                            "candidate_task_starts": values["tasks"],
                            "distinct_candidate_jobs": distinct_by_hour.get(
                                source_hour, 0
                            ),
                            "requested_instances": _decimal_text(values["instances"]),
                            "requested_cpu_known_tasks": values["cpu_known"],
                            "requested_cpu_cores": (
                                _decimal_text(values["cpu"])
                                if values["cpu_known"] or values["tasks"] == 0
                                else ""
                            ),
                            "requested_gpu_equivalents": _decimal_text(values["gpu"]),
                            "requested_memory_known_tasks": values["memory_known"],
                            "requested_memory_gb": (
                                _decimal_text(values["memory"])
                                if values["memory_known"] or values["tasks"] == 0
                                else ""
                            ),
                        }
                    )
                    hourly_rows += 1

        machine_name = archive_for["pai_machine_spec.csv"]
        machine_columns = list(archives[machine_name]["columns"])
        machine_keys = set()
        with _gzip_csv(staging / "machine_catalog.csv.gz", MACHINE_FIELDS) as writer:
            for values in _iter_archive_rows(root, machine_name, archives[machine_name]):
                row = dict(zip(machine_columns, values))
                table_rows["machines"] += 1
                _missing_counts(row, missing_by_table["machines"])
                if row["machine"] in machine_keys:
                    raise ValueError(f"Duplicate machine key: {row['machine']}")
                machine_keys.add(row["machine"])
                for field in ("cap_cpu", "cap_mem", "cap_gpu"):
                    number = _decimal(
                        row[field],
                        field,
                        invalid_numeric_by_table["machines"],
                    )
                    if number == 0:
                        numeric_zero_by_table["machines"][field] += 1
                    elif number is not None and number < 0:
                        numeric_negative_by_table["machines"][field] += 1
                writer.writerow(row)

        workload_present = int(
            connection.execute(
                "SELECT COUNT(*) FROM group_tags WHERE TRIM(workload) <> ''"
            ).fetchone()[0]
        )
        workload_missing = table_rows["group_tags"] - workload_present

        audit = {
            "decompressed_bytes": sum(decompressed_by_archive.values()),
            "decompressed_bytes_by_archive": {
                key: decompressed_by_archive[key] for key in sorted(decompressed_by_archive)
            },
            "table_rows": {
                key: table_rows[key]
                for key in ("jobs", "tasks", "group_tags", "machines")
            },
            "unique_keys": {
                "job_name": True,
                "job_inst_id": True,
                "task_job_name_task_name": True,
                "group_inst_id": True,
                "machine": True,
            },
            "joins": {
                "task_job_sets_equal": task_job_sets_equal,
                "matched_job_group_rows": matched_job_group_rows,
                "orphan_group_rows": orphan_group_rows,
                "jobs_without_group": jobs_without_group,
                "matched_nonempty_user_conflicts": user_conflicts,
                "task_rows_without_parent_job": task_parent_missing_rows,
            },
            "group_tags": {
                "workload_present_rows": workload_present,
                "workload_missing_rows": workload_missing,
            },
            "job_status_counts": _sorted_counter(job_status),
            "task_status_counts": _sorted_counter(task_status),
            "missing_counts": {
                "jobs": _counts_for(missing_by_table["jobs"], job_columns),
                "tasks": _counts_for(missing_by_table["tasks"], task_columns),
                "group_tags": _counts_for(
                    missing_by_table["group_tags"], group_columns
                ),
                "machines": _counts_for(
                    missing_by_table["machines"], machine_columns
                ),
            },
            "task_missing_counts": _counts_for(
                missing_by_table["tasks"], task_columns
            ),
            "invalid_nonempty_numeric_counts": {
                "jobs": _counts_for(
                    invalid_numeric_by_table["jobs"], ["start_time", "end_time"]
                ),
                "tasks": _counts_for(
                    invalid_numeric_by_table["tasks"],
                    [
                        "start_time",
                        "end_time",
                        "inst_num",
                        "plan_cpu",
                        "plan_mem",
                        "plan_gpu",
                    ],
                ),
                "machines": _counts_for(
                    invalid_numeric_by_table["machines"],
                    ["cap_cpu", "cap_mem", "cap_gpu"],
                ),
            },
            "zero_numeric_counts": {
                "jobs": _counts_for(
                    numeric_zero_by_table["jobs"], ["start_time", "end_time"]
                ),
                "tasks": _counts_for(
                    numeric_zero_by_table["tasks"],
                    [
                        "start_time",
                        "end_time",
                        "inst_num",
                        "plan_cpu",
                        "plan_mem",
                        "plan_gpu",
                    ],
                ),
                "machines": _counts_for(
                    numeric_zero_by_table["machines"],
                    ["cap_cpu", "cap_mem", "cap_gpu"],
                ),
            },
            "negative_numeric_counts": {
                "jobs": _counts_for(
                    numeric_negative_by_table["jobs"], ["start_time", "end_time"]
                ),
                "tasks": _counts_for(
                    numeric_negative_by_table["tasks"],
                    [
                        "start_time",
                        "end_time",
                        "inst_num",
                        "plan_cpu",
                        "plan_mem",
                        "plan_gpu",
                    ],
                ),
                "machines": _counts_for(
                    numeric_negative_by_table["machines"],
                    ["cap_cpu", "cap_mem", "cap_gpu"],
                ),
            },
            "time_audit": {
                "job_end_before_start_rows": job_duration_negative,
                "task_end_before_start_rows": task_end_before_start_rows,
                "task_rows_starting_after_parent_job": later_task_start_rows,
                "jobs_with_computable_earliest_task_start": (
                    jobs_with_computable_min_task_start
                ),
                "jobs_with_zero_earliest_task_start_gap": zero_min_gap_jobs,
                "jobs_with_positive_earliest_task_start_gap": positive_min_gap_jobs,
            },
            "task_resource_audit": {
                "maximum_plan_gpu_percent_per_instance": _decimal_text(
                    maximum_plan_gpu_percent
                ),
                "maximum_requested_gpu_equivalents_per_task": _decimal_text(
                    maximum_requested_gpu_equivalents
                ),
            },
            "cohorts": {
                "strict_completed_resource_complete_tasks": {
                    "tasks": strict_tasks,
                    "jobs": strict_jobs,
                },
                "successful_gpu_task_candidates": {
                    "tasks": gpu_candidates,
                    "jobs": candidate_jobs,
                    "jobs_with_workload_tag": candidate_workload_jobs,
                    "tasks_missing_requested_cpu": candidate_missing_cpu_tasks,
                    "tasks_missing_requested_memory": candidate_missing_memory_tasks,
                },
            },
            "relative_hourly_workload": {
                "rows": hourly_rows,
                "first_source_hour_index_anonymized": first_source_hour,
                "last_source_hour_index_anonymized": last_source_hour,
                "calendar_dates_real": False,
                "population": "successful_gpu_task_candidates",
            },
        }
        _assert_expected(config["processing_expected"], audit)

        output_metadata = {}
        for name in OUTPUT_FILES:
            path = staging / name
            output_metadata[name] = {
                "bytes": path.stat().st_size,
                "sha256": _sha256(path),
            }
        expected_outputs = config.get("processing_expected_outputs")
        if expected_outputs is not None:
            _assert_expected(
                {name: expected_outputs[name] for name in OUTPUT_FILES},
                output_metadata,
                "processing_expected_outputs",
            )
        summary = {
            "schema": processing["schema"],
            "dataset": config["source"]["dataset"],
            "source_profile": config["source"]["profile"],
            "documentation_commit": config["source"]["documentation_commit"],
            "calendar_status": processing["calendar_status"],
            "missing_resource_policy": processing["missing_resource_policy"],
            "derivation_rules": processing["derived_units"],
            "cohort_rules": {
                "strict_completed_resource_complete_tasks": processing[
                    "strict_completed_resource_complete_tasks"
                ],
                "successful_gpu_task_candidates": processing[
                    "successful_gpu_task_candidates"
                ],
            },
            "evidence": config["evidence"],
            "audit": audit,
            "outputs": output_metadata,
        }
        summary_path = staging / "summary.json"
        summary_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        if expected_outputs is not None and _sha256(summary_path) != expected_outputs[
            "summary_sha256"
        ]:
            raise RuntimeError("Processed Alibaba summary hash drifted")
        manifest_files = (*OUTPUT_FILES, "summary.json")
        (staging / "SHA256SUMS").write_text(
            "".join(f"{_sha256(staging / name)}  {name}\n" for name in manifest_files),
            encoding="ascii",
        )
        _publish(staging, output_root)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/alibaba_gpu_2020.yaml"),
    )
    parser.add_argument("--output-root", type=Path)
    args = parser.parse_args()
    started = time.perf_counter()
    summary = run(args.config, output_root=args.output_root)
    print(
        json.dumps(
            {
                "elapsed_seconds": time.perf_counter() - started,
                "output": str(
                    args.output_root
                    or yaml.safe_load(args.config.read_text(encoding="utf-8"))[
                        "processing"
                    ]["output_path"]
                ),
                "schema": summary["schema"],
                "cohorts": summary["audit"]["cohorts"],
            },
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
