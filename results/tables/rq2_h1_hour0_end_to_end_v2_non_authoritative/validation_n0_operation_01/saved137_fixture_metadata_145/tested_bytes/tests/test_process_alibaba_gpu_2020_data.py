import csv
import gzip
import hashlib
import io
import json
import tarfile
from pathlib import Path

import pytest
import yaml

from experiments.process_alibaba_gpu_2020_data import run


FORMAL_OUTPUT = Path("data/processed/alibaba_gpu_2020/v2020")


TABLES = {
    "pai_group_tag_table": {
        "columns": ["inst_id", "user", "gpu_type_spec", "group", "workload"],
        "rows": [
            ["I1", "U1", "T4", "G1", "bert"],
            ["I2", "U2", "", "G2", ""],
            ["IX", "UX", "V100", "GX", ""],
        ],
    },
    "pai_job_table": {
        "columns": ["job_name", "inst_id", "user", "status", "start_time", "end_time"],
        "rows": [
            ["J1", "I1", "U1", "Terminated", "0", "20"],
            ["J2", "I2", "U2", "Terminated", "0", "20"],
            ["J3", "I3", "U3", "Failed", "0", "20"],
        ],
    },
    "pai_task_table": {
        "columns": [
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
        ],
        "rows": [
            ["J1", "worker", "2", "Terminated", "0", "10", "100", "4", "50", "T4"],
            ["J1", "ps", "1", "Terminated", "0", "10", "100", "2", "", ""],
            ["J2", "eval", "1", "Terminated", "5", "15", "", "", "0", "T4"],
            ["J2", "zero", "0", "Terminated", "5", "15", "100", "1", "100", "T4"],
            ["J2", "negative", "-1", "Terminated", "5", "15", "100", "1", "100", "T4"],
            ["J2", "badtime", "1", "Terminated", "20", "10", "100", "1", "100", "T4"],
            ["J3", "worker", "1", "Terminated", "0", "10", "100", "1", "100", "T4"],
        ],
    },
    "pai_machine_spec": {
        "columns": ["machine", "gpu_type", "cap_cpu", "cap_mem", "cap_gpu"],
        "rows": [
            ["M1", "T4", "96", "512", "2"],
            ["M2", "MISC", "64", "256", "0"],
        ],
    },
}


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_tar(path, member, rows):
    buffer = io.StringIO(newline="")
    writer = csv.writer(buffer, lineterminator="\n")
    writer.writerows(rows)
    content = buffer.getvalue().encode()
    info = tarfile.TarInfo(member)
    info.size = len(content)
    info.mtime = 0
    with tarfile.open(path, "w:gz") as archive:
        archive.addfile(info, io.BytesIO(content))


def _fixture_config(tmp_path, *, duplicate_task=False):
    root = tmp_path / "raw"
    root.mkdir()
    archives = {}
    source_entries = []
    for table_name, table in TABLES.items():
        rows = [list(row) for row in table["rows"]]
        if duplicate_task and table_name == "pai_task_table":
            rows.append(list(rows[0]))
        archive_name = f"{table_name}.tar.gz"
        member_name = f"{table_name}.csv"
        header_name = f"{table_name}.header"
        archive_path = root / archive_name
        header_path = root / header_name
        _write_tar(archive_path, member_name, rows)
        header_path.write_text(",".join(table["columns"]) + "\n", encoding="utf-8")
        archives[archive_name] = {
            "size": archive_path.stat().st_size,
            "sha256": _sha256(archive_path),
            "member": member_name,
            "header": header_name,
            "header_sha256": _sha256(header_path),
            "columns": table["columns"],
        }
        source_entries.append({"name": archive_name})
    (root / "SOURCE_OBJECTS.json").write_text(
        json.dumps(
            {
                "profile": "stage1_core",
                "documentation_commit": "fixture-commit",
                "archives": source_entries,
            }
        ),
        encoding="utf-8",
    )
    manifest_paths = sorted(path for path in root.iterdir() if path.is_file())
    (root / "SHA256SUMS").write_text(
        "".join(f"{_sha256(path)}  {path.name}\n" for path in manifest_paths),
        encoding="ascii",
    )
    config = {
        "source": {
            "dataset": "Alibaba fixture",
            "documentation_commit": "fixture-commit",
            "path": str(root),
            "profile": "stage1_core",
        },
        "expected": {"archives": archives},
        "evidence": {
            "status": "observed_ai_workload_trace",
            "calendar_dates_real": False,
        },
        "processing": {
            "schema": "alibaba_gpu_2020_stage1_processed_v1",
            "output_path": str(tmp_path / "processed"),
            "relative_hour_seconds": 3600,
            "calendar_status": "anonymized_relative_seconds_not_real_dates",
            "missing_resource_policy": "preserve_null_never_fill_zero",
            "derived_units": {
                "duration_seconds": "end_time - start_time",
                "requested_cpu_cores": "inst_num * plan_cpu / 100",
                "requested_gpu_equivalents": "inst_num * plan_gpu / 100",
                "requested_memory_gb": "inst_num * plan_mem",
            },
            "strict_completed_resource_complete_tasks": {
                "parent_job_status": "Terminated",
                "task_status": "Terminated",
                "required_numeric_fields": [
                    "start_time",
                    "end_time",
                    "inst_num",
                    "plan_gpu",
                ],
                "require_end_not_before_start": True,
                "require_positive_inst_num": True,
            },
            "successful_gpu_task_candidates": {
                "base": "strict_completed_resource_complete_tasks",
                "require_positive_requested_gpu_equivalents": True,
            },
        },
        "processing_expected": {
            "table_rows": {
                "jobs": 3,
                "tasks": 8 if duplicate_task else 7,
                "group_tags": 3,
                "machines": 2,
            },
            "joins": {
                "matched_job_group_rows": 2,
                "orphan_group_rows": 1,
                "jobs_without_group": 1,
                "matched_nonempty_user_conflicts": 0,
            },
            "group_tags": {
                "workload_present_rows": 1,
                "workload_missing_rows": 2,
            },
        },
    }
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    return config_path


def _read_csv(path):
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def test_processor_preserves_nulls_separates_strict_and_positive_gpu(tmp_path):
    config_path = _fixture_config(tmp_path)
    output_root = tmp_path / "processed"

    summary = run(config_path, output_root=output_root)

    audit = summary["audit"]
    assert audit["cohorts"]["strict_completed_resource_complete_tasks"] == {
        "tasks": 2,
        "jobs": 2,
    }
    assert audit["cohorts"]["successful_gpu_task_candidates"] == {
        "tasks": 1,
        "jobs": 1,
        "jobs_with_workload_tag": 1,
        "tasks_missing_requested_cpu": 0,
        "tasks_missing_requested_memory": 0,
    }
    assert audit["zero_numeric_counts"]["tasks"]["inst_num"] == 1
    assert audit["negative_numeric_counts"]["tasks"]["inst_num"] == 1
    assert audit["time_audit"]["task_end_before_start_rows"] == 1

    tasks = _read_csv(output_root / "tasks.csv.gz")
    missing_gpu = next(row for row in tasks if row["task_name"] == "ps")
    assert missing_gpu["plan_gpu"] == ""
    assert missing_gpu["requested_gpu_equivalents"] == ""
    zero_gpu = next(row for row in tasks if row["task_name"] == "eval")
    assert zero_gpu["requested_gpu_equivalents"] == "0"
    assert zero_gpu["requested_cpu_cores"] == ""
    assert zero_gpu["requested_memory_gb"] == ""

    candidates = _read_csv(output_root / "successful_gpu_task_candidates.csv.gz")
    assert [(row["job_name"], row["task_name"]) for row in candidates] == [
        ("J1", "worker")
    ]
    hourly = _read_csv(output_root / "relative_hourly_workload.csv.gz")
    assert hourly == [
        {
            "relative_hour": "0",
            "candidate_task_starts": "1",
            "distinct_candidate_jobs": "1",
            "requested_instances": "2",
            "requested_cpu_known_tasks": "1",
            "requested_cpu_cores": "2",
            "requested_gpu_equivalents": "1",
            "requested_memory_known_tasks": "1",
            "requested_memory_gb": "8",
        }
    ]

    first_manifest = (output_root / "SHA256SUMS").read_bytes()
    first_hashes = {
        path.name: _sha256(path)
        for path in output_root.iterdir()
        if path.is_file()
    }
    run(config_path, output_root=output_root)
    assert (output_root / "SHA256SUMS").read_bytes() == first_manifest
    assert {
        path.name: _sha256(path)
        for path in output_root.iterdir()
        if path.is_file()
    } == first_hashes

    invalid_config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    invalid_config["processing_expected_outputs"] = {
        **summary["outputs"],
        "summary_sha256": "0" * 64,
    }
    invalid_path = tmp_path / "invalid-output-hash.yaml"
    invalid_path.write_text(
        yaml.safe_dump(invalid_config, sort_keys=False),
        encoding="utf-8",
    )
    with pytest.raises(RuntimeError, match="summary hash drifted"):
        run(invalid_path, output_root=output_root)
    assert {
        path.name: _sha256(path)
        for path in output_root.iterdir()
        if path.is_file()
    } == first_hashes
    assert not list(tmp_path.glob(".processed.processing-*"))


def test_processor_fails_closed_on_duplicate_task_key(tmp_path):
    config_path = _fixture_config(tmp_path, duplicate_task=True)

    with pytest.raises(ValueError, match="Duplicate task key"):
        run(config_path, output_root=tmp_path / "processed")

    assert not (tmp_path / "processed" / "SHA256SUMS").exists()


@pytest.mark.skipif(
    not (FORMAL_OUTPUT / "summary.json").exists(),
    reason="Build the formal Alibaba processed artifacts first",
)
def test_formal_alibaba_outputs_match_frozen_hashes_and_manifest():
    config = yaml.safe_load(
        Path("configs/alibaba_gpu_2020.yaml").read_text(encoding="utf-8")
    )
    expected_outputs = config["processing_expected_outputs"]
    for name, expected in expected_outputs.items():
        if name == "summary_sha256":
            continue
        path = FORMAL_OUTPUT / name
        assert path.stat().st_size == expected["bytes"]
        assert _sha256(path) == expected["sha256"]
    assert _sha256(FORMAL_OUTPUT / "summary.json") == expected_outputs[
        "summary_sha256"
    ]
    for line in (FORMAL_OUTPUT / "SHA256SUMS").read_text(
        encoding="ascii"
    ).splitlines():
        expected, relative = line.split("  ", maxsplit=1)
        assert _sha256(FORMAL_OUTPUT / relative) == expected
