"""Build job-level execution envelopes without inventing flexibility semantics."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import shutil
import sqlite3
import tempfile
from contextlib import contextmanager
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[1]
FIELDS = (
    "job_name",
    "group_tag",
    "workload_tag",
    "observed_release_time_s",
    "observed_completion_time_s",
    "observed_execution_span_s",
    "terminated_task_count",
    "declared_instance_count_sum",
    "declared_gpu_equivalents_sum",
    "maximum_task_requested_gpu_equivalents",
    "declared_cpu_cores_sum",
    "declared_memory_gb_sum",
    "declared_gpu_time_gpu_seconds",
    "deadline_observed",
    "checkpoint_state_observed",
    "preemptibility_observed",
    "recoverable_fraction_inferred",
    "power_conversion_applied",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _path(value: object, label: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ValueError(f"{label} must be a nonempty path")
    path = Path(value)
    return path if path.is_absolute() else _ROOT / path


def _verify_processed_manifest(root: Path) -> None:
    rows = (root / "SHA256SUMS").read_text(encoding="ascii").splitlines()
    for row in rows:
        expected, relative = row.split("  ", maxsplit=1)
        if _sha256(root / relative) != expected:
            raise ValueError(f"Processed Alibaba input hash drifted: {relative}")


@contextmanager
def _gzip_csv(path: Path):
    with (
        path.open("wb") as raw,
        gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as compressed,
        io.TextIOWrapper(compressed, encoding="utf-8", newline="") as text,
    ):
        writer = csv.writer(text, lineterminator="\n")
        writer.writerow(FIELDS)
        yield writer


def _load_jobs(database: sqlite3.Connection, path: Path) -> None:
    database.execute(
        "CREATE TABLE jobs (job_name TEXT PRIMARY KEY, group_tag TEXT, workload TEXT)"
    )
    batch = []
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            batch.append((row["job_name"], row["group"], row["workload"]))
            if len(batch) == 10000:
                database.executemany("INSERT INTO jobs VALUES (?, ?, ?)", batch)
                batch.clear()
    if batch:
        database.executemany("INSERT INTO jobs VALUES (?, ?, ?)", batch)


def _load_candidates(database: sqlite3.Connection, path: Path) -> int:
    database.execute(
        """
        CREATE TABLE tasks (
            job_name TEXT NOT NULL,
            start_time REAL NOT NULL,
            end_time REAL NOT NULL,
            inst_num REAL NOT NULL,
            gpu REAL NOT NULL,
            cpu REAL NOT NULL,
            memory REAL NOT NULL
        )
        """
    )
    batch = []
    rows = 0
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        for row in csv.DictReader(source):
            batch.append(
                (
                    row["job_name"],
                    float(row["start_time"]),
                    float(row["end_time"]),
                    float(row["inst_num"]),
                    float(row["requested_gpu_equivalents"]),
                    float(row["requested_cpu_cores"]),
                    float(row["requested_memory_gb"]),
                )
            )
            rows += 1
            if len(batch) == 10000:
                database.executemany(
                    "INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?)", batch
                )
                batch.clear()
    if batch:
        database.executemany("INSERT INTO tasks VALUES (?, ?, ?, ?, ?, ?, ?)", batch)
    database.execute("CREATE INDEX tasks_job_name ON tasks(job_name)")
    return rows


def run(config_path: Path) -> dict[str, object]:
    config_bytes = config_path.read_bytes()
    config = yaml.safe_load(config_bytes)
    source = config["source"]
    source_root = _path(source["path"], "source.path")
    _verify_processed_manifest(source_root)
    jobs_path = source_root / "jobs.csv.gz"
    candidates_path = source_root / "successful_gpu_task_candidates.csv.gz"
    if _sha256(jobs_path) != source["jobs_sha256"]:
        raise ValueError("jobs.csv.gz hash drifted")
    if _sha256(candidates_path) != source["candidate_tasks_sha256"]:
        raise ValueError("candidate task hash drifted")

    target = _path(config["output"]["directory"], "output.directory")
    if target.exists():
        raise FileExistsError(f"immutable output directory already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(dir=target.parent, prefix=f".{target.name}.processing-")
    )
    try:
        database = sqlite3.connect(staging / "aggregation.sqlite")
        database.execute("PRAGMA journal_mode=OFF")
        database.execute("PRAGMA synchronous=OFF")
        database.execute("PRAGMA temp_store=FILE")
        _load_jobs(database, jobs_path)
        candidate_rows = _load_candidates(database, candidates_path)

        query = """
            SELECT
                t.job_name,
                j.group_tag,
                j.workload,
                MIN(t.start_time),
                MAX(t.end_time),
                MAX(t.end_time) - MIN(t.start_time),
                COUNT(*),
                SUM(t.inst_num),
                SUM(t.gpu),
                MAX(t.gpu),
                SUM(t.cpu),
                SUM(t.memory),
                SUM((t.end_time - t.start_time) * t.gpu)
            FROM tasks AS t
            JOIN jobs AS j ON j.job_name = t.job_name
            GROUP BY t.job_name
            ORDER BY MIN(t.start_time), t.job_name
        """
        output_path = staging / "job_execution_envelopes.csv.gz"
        job_rows = 0
        minimum_release = None
        maximum_completion = None
        with _gzip_csv(output_path) as writer:
            for row in database.execute(query):
                release = float(row[3])
                completion = float(row[4])
                if completion < release:
                    raise RuntimeError("Observed completion precedes release proxy")
                writer.writerow((*row, 0, 0, 0, 0, 0))
                job_rows += 1
                minimum_release = (
                    release
                    if minimum_release is None
                    else min(minimum_release, release)
                )
                maximum_completion = (
                    completion
                    if maximum_completion is None
                    else max(maximum_completion, completion)
                )
        database.close()
        (staging / "aggregation.sqlite").unlink()

        if job_rows != 714903 or candidate_rows != 732318:
            raise RuntimeError("Alibaba candidate population count drifted")
        summary = {
            "schema": "alibaba_job_execution_envelopes_v1",
            "source": {
                "dataset": source["dataset"],
                "profile": source["profile"],
                "jobs_sha256": source["jobs_sha256"],
                "candidate_tasks_sha256": source["candidate_tasks_sha256"],
            },
            "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
            "implementation_sha256": _sha256(Path(__file__)),
            "candidate_task_rows": candidate_rows,
            "job_rows": job_rows,
            "minimum_observed_release_time_s": minimum_release,
            "maximum_observed_completion_time_s": maximum_completion,
            "derivation": config["derivation"],
            "evidence_status": {
                "workload_trace": "observed_anonymized_relative_chronology",
                "deadline_observed": False,
                "checkpoint_state_observed": False,
                "preemptibility_observed": False,
                "recoverable_fraction_inferred": False,
                "power_conversion_applied": False,
            },
        }
        (staging / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        manifest = {
            name: _sha256(staging / name)
            for name in ("job_execution_envelopes.csv.gz", "summary.json")
        }
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
        default=Path("configs/alibaba_job_execution_envelopes_v1.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
