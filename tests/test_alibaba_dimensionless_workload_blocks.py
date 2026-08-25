from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import shutil
from pathlib import Path

import pytest
import yaml

from experiments.build_alibaba_dimensionless_workload_blocks import run

PACKAGE = Path(
    "data/processed/model_inputs/alibaba_dimensionless_workload_blocks_v3"
)
CONFIG = Path("configs/alibaba_dimensionless_workload_blocks_v3.yaml")
IMPLEMENTATION = Path("experiments/build_alibaba_dimensionless_workload_blocks.py")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_source(path: Path, rows: list[dict[str, object]]) -> None:
    with (
        path.open("wb") as raw,
        gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed,
        io.TextIOWrapper(compressed, encoding="utf-8", newline="") as target,
    ):
        writer = csv.DictWriter(
            target,
            fieldnames=(
                "job_name",
                "start_time",
                "end_time",
                "requested_gpu_equivalents",
            ),
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def _read_gzip_csv(path: Path) -> list[dict[str, str]]:
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        return list(csv.DictReader(source))


def _config(tmp_path: Path, rows: list[dict[str, object]]) -> Path:
    source = tmp_path / "tasks.csv.gz"
    _write_source(source, rows)
    config = {
        "source": {"path": str(source), "sha256": _sha256(source)},
        "derivation": {
            "split_fraction": 0.5,
            "job_split_policy": "exclude_jobs_contributing_to_both_sides",
            "block_hours": 2,
            "block_stride_hours": 2,
        },
        "output": {
            "schema": "test_dimensionless_workload_blocks",
            "directory": str(tmp_path / "output"),
        },
    }
    path = tmp_path / "config.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=True), encoding="utf-8")
    return path


def _eight_hour_tasks() -> list[dict[str, object]]:
    return [
        {
            "job_name": "job_0",
            "start_time": 0,
            "end_time": 1800,
            "requested_gpu_equivalents": 2,
        },
        {
            "job_name": "job_1",
            "start_time": 1800,
            "end_time": 5400,
            "requested_gpu_equivalents": 1,
        },
        {
            "job_name": "job_2",
            "start_time": 3600,
            "end_time": 10800,
            "requested_gpu_equivalents": 2,
        },
        {
            "job_name": "job_3",
            "start_time": 10800,
            "end_time": 14400,
            "requested_gpu_equivalents": 1,
        },
        {
            "job_name": "job_4",
            "start_time": 14400,
            "end_time": 18000,
            "requested_gpu_equivalents": 4,
        },
        {
            "job_name": "job_5",
            "start_time": 18000,
            "end_time": 21600,
            "requested_gpu_equivalents": 2,
        },
        {
            "job_name": "job_6",
            "start_time": 21600,
            "end_time": 25200,
            "requested_gpu_equivalents": 3,
        },
        {
            "job_name": "job_7",
            "start_time": 25200,
            "end_time": 28800,
            "requested_gpu_equivalents": 1,
        },
    ]


def test_overlap_split_and_training_only_normalization(tmp_path: Path):
    config = _config(tmp_path, _eight_hour_tasks())

    summary = run(config)

    output = tmp_path / "output"
    rows = _read_gzip_csv(output / "workload_blocks.csv.gz")
    occupancy = [float(row["requested_gpu_occupancy"]) for row in rows]
    fractions = [float(row["workload_fraction"]) for row in rows]
    assert occupancy == pytest.approx([1.5, 2.5, 2, 1, 4, 2, 3, 1])
    assert fractions == pytest.approx([0.6, 1, 0.8, 0.4, 1.6, 0.8, 1.2, 0.4])
    assert [row["block_id"] for row in rows] == [
        "training_0000",
        "training_0000",
        "training_0001",
        "training_0001",
        "holdout_0000",
        "holdout_0000",
        "holdout_0001",
        "holdout_0001",
    ]
    assert summary["training_peak_requested_gpu_occupancy"] == "2.5"
    assert summary["training_block_count"] == 2
    assert summary["holdout_block_count"] == 2
    assert summary["split_rounding"] == "floor"
    assert summary["cross_split_jobs_excluded"] == 0
    assert max(fractions[4:]) > 1

    for split in ("training", "holdout"):
        marginal = _read_gzip_csv(output / f"{split}_marginal.csv.gz")
        assert sum(float(row["probability"]) for row in marginal) == pytest.approx(1)


def test_rebuild_is_byte_deterministic_and_manifest_is_complete(tmp_path: Path):
    config = _config(tmp_path, _eight_hour_tasks())

    run(config)
    output = tmp_path / "output"
    first_hashes = {
        path.name: _sha256(path)
        for path in output.iterdir()
        if path.is_file()
    }
    manifest = json.loads(
        (output / "SHA256SUMS.json").read_text(encoding="utf-8")
    )
    assert manifest == {
        name: first_hashes[name]
        for name in (
            "holdout_marginal.csv.gz",
            "summary.json",
            "training_marginal.csv.gz",
            "workload_blocks.csv.gz",
        )
    }

    shutil.rmtree(output)
    run(config)
    second_hashes = {
        path.name: _sha256(path)
        for path in output.iterdir()
        if path.is_file()
    }
    assert second_hashes == first_hashes


def test_jobs_contributing_to_both_sides_are_excluded(tmp_path: Path):
    rows = _eight_hour_tasks()
    rows.extend(
        [
            {
                "job_name": "cross_split",
                "start_time": 0,
                "end_time": 3600,
                "requested_gpu_equivalents": 100,
            },
            {
                "job_name": "cross_split",
                "start_time": 21600,
                "end_time": 25200,
                "requested_gpu_equivalents": 100,
            },
        ]
    )
    config = _config(tmp_path, rows)

    summary = run(config)
    output_rows = _read_gzip_csv(
        tmp_path / "output" / "workload_blocks.csv.gz"
    )

    assert summary["cross_split_jobs_excluded"] == 1
    assert summary["cross_split_task_rows_excluded"] == 2
    assert [float(row["requested_gpu_occupancy"]) for row in output_rows] == (
        pytest.approx([1.5, 2.5, 2, 1, 4, 2, 3, 1])
    )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("start_time", "0.5", "integer number of seconds"),
        ("requested_gpu_equivalents", "NaN", "finite decimal"),
        ("requested_gpu_equivalents", "0", "must be positive"),
    ],
)
def test_invalid_candidate_values_fail_closed(
    tmp_path: Path,
    field: str,
    value: str,
    message: str,
):
    rows = _eight_hour_tasks()
    rows[0][field] = value
    config = _config(tmp_path, rows)

    with pytest.raises(ValueError, match=message):
        run(config)


def test_existing_output_is_not_overwritten(tmp_path: Path):
    config = _config(tmp_path, _eight_hour_tasks())
    run(config)

    with pytest.raises(FileExistsError, match="refusing to overwrite"):
        run(config)


def test_published_package_integrity_and_split_boundary():
    manifest = json.loads((PACKAGE / "SHA256SUMS.json").read_text(encoding="utf-8"))
    summary = json.loads((PACKAGE / "summary.json").read_text(encoding="utf-8"))
    assert all(_sha256(PACKAGE / name) == digest for name, digest in manifest.items())
    assert summary["config_sha256"] == _sha256(CONFIG)
    assert summary["implementation_sha256"] == _sha256(IMPLEMENTATION)
    assert summary["source_task_rows"] == 732318
    assert summary["training_block_count"] == 34
    assert summary["holdout_block_count"] == 34
    assert summary["block_hours"] == 24
    assert summary["cross_split_jobs_excluded"] == 908
    assert summary["cross_split_task_rows_excluded"] == 916
    assert summary["job_split_policy"] == (
        "exclude_jobs_contributing_to_both_sides"
    )
    assert not summary["workload_fraction_is_power"]
    assert not summary["flexible_fraction_inferred"]

    rows = _read_gzip_csv(PACKAGE / "workload_blocks.csv.gz")
    training_hours = {
        int(row["source_relative_hour"])
        for row in rows
        if row["split"] == "training"
    }
    holdout_hours = {
        int(row["source_relative_hour"])
        for row in rows
        if row["split"] == "holdout"
    }
    assert len(rows) == 68 * 24
    assert len({row["block_id"] for row in rows}) == 68
    assert max(training_hours) < min(holdout_hours)
    assert max(
        float(row["workload_fraction"])
        for row in rows
        if row["split"] == "training"
    ) == pytest.approx(1)
    assert max(
        float(row["workload_fraction"])
        for row in rows
        if row["split"] == "holdout"
    ) > 1
