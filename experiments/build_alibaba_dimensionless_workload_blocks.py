"""Build split-aware dimensionless workload blocks from Alibaba task overlap."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import shutil
import tempfile
from decimal import ROUND_CEILING, ROUND_FLOOR, Decimal, InvalidOperation
from pathlib import Path

import yaml

_ROOT = Path(__file__).resolve().parents[1]
_HOUR = Decimal(3600)
_SOURCE_FIELDS = frozenset(
    {"job_name", "start_time", "end_time", "requested_gpu_equivalents"}
)


def _path(raw: object, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"{label} must be a nonempty path")
    path = Path(raw)
    return path if path.is_absolute() else _ROOT / path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _integer(raw: object, label: str) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int) or raw < 1:
        raise ValueError(f"{label} must be a positive integer")
    return raw


def _decimal(raw: object, label: str) -> Decimal:
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, ValueError) as error:
        raise ValueError(f"{label} must be a finite decimal") from error
    if not value.is_finite():
        raise ValueError(f"{label} must be a finite decimal")
    return value


def _integral_second(raw: object, label: str) -> int:
    value = _decimal(raw, label)
    if value != value.to_integral_value():
        raise ValueError(f"{label} must be an integer number of seconds")
    return int(value)


def _reader(source) -> csv.DictReader:
    reader = csv.DictReader(source)
    if reader.fieldnames is None or not _SOURCE_FIELDS.issubset(reader.fieldnames):
        raise ValueError(
            "candidate task source must contain job_name, start_time, end_time, "
            "and requested_gpu_equivalents"
        )
    return reader


def _write_gzip_csv(
    path: Path,
    fieldnames: tuple[str, ...],
    rows,
) -> None:
    with (
        path.open("wb") as raw,
        gzip.GzipFile(fileobj=raw, mode="wb", mtime=0) as compressed,
        io.TextIOWrapper(compressed, encoding="utf-8", newline="") as target,
    ):
        writer = csv.DictWriter(
            target, fieldnames=fieldnames, lineterminator="\n"
        )
        writer.writeheader()
        writer.writerows(rows)


def _source_bounds(path: Path) -> tuple[int, int, int]:
    minimum = None
    maximum = None
    rows = 0
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        for row_number, row in enumerate(_reader(source), start=2):
            start = _integral_second(row["start_time"], f"row {row_number} start_time")
            end = _integral_second(row["end_time"], f"row {row_number} end_time")
            if end <= start:
                raise ValueError("candidate task must have positive duration")
            minimum = start if minimum is None else min(minimum, start)
            maximum = end if maximum is None else max(maximum, end)
            rows += 1
    if minimum is None or maximum is None:
        raise ValueError("candidate task source is empty")
    return minimum, maximum, rows


def _cross_split_jobs(path: Path, boundary_second: int) -> set[str]:
    sides: dict[str, int] = {}
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        for row_number, row in enumerate(_reader(source), start=2):
            job = row["job_name"]
            if not job:
                raise ValueError(f"row {row_number} job_name must be nonempty")
            start = _integral_second(row["start_time"], f"row {row_number} start_time")
            end = _integral_second(row["end_time"], f"row {row_number} end_time")
            if end <= start:
                raise ValueError("candidate task must have positive duration")
            side = int(start < boundary_second) | (2 * int(end > boundary_second))
            sides[job] = sides.get(job, 0) | side
    return {job for job, side in sides.items() if side == 3}


def _hourly_occupancy(
    path: Path,
    base: int,
    horizon: int,
    excluded_jobs: set[str],
) -> tuple[list[Decimal], int]:
    occupancy = [Decimal(0) for _ in range(horizon)]
    full_hour_delta = [Decimal(0) for _ in range(horizon + 1)]
    excluded_task_rows = 0
    with gzip.open(path, "rt", encoding="utf-8", newline="") as source:
        for row_number, row in enumerate(_reader(source), start=2):
            if row["job_name"] in excluded_jobs:
                excluded_task_rows += 1
                continue
            start = (
                _integral_second(row["start_time"], f"row {row_number} start_time")
                - base
            )
            end = (
                _integral_second(row["end_time"], f"row {row_number} end_time")
                - base
            )
            gpu = _decimal(
                row["requested_gpu_equivalents"],
                f"row {row_number} requested_gpu_equivalents",
            )
            if gpu <= 0:
                raise ValueError(
                    "candidate task requested_gpu_equivalents must be positive"
                )
            if start < 0 or end <= start or end > horizon * 3600:
                raise ValueError("candidate task lies outside the derived horizon")
            first = start // 3600
            last = (end - 1) // 3600
            if first == last:
                occupancy[first] += gpu * Decimal(end - start) / _HOUR
                continue
            first_end = (first + 1) * 3600
            occupancy[first] += gpu * Decimal(first_end - start) / _HOUR
            last_start = last * 3600
            occupancy[last] += gpu * Decimal(end - last_start) / _HOUR
            if first + 1 < last:
                full_hour_delta[first + 1] += gpu
                full_hour_delta[last] -= gpu
    active = Decimal(0)
    for index in range(horizon):
        active += full_hour_delta[index]
        occupancy[index] += active
    return occupancy, excluded_task_rows


def _blocks(
    values: list[Decimal],
    *,
    split: int,
    block_hours: int,
    stride: int,
    peak: Decimal,
):
    for split_name, low, high in (
        ("training", 0, split),
        ("holdout", split, len(values)),
    ):
        starts = range(low, high - block_hours + 1, stride)
        starts = tuple(starts)
        probability = Decimal(1) / Decimal(len(starts))
        for block_index, start in enumerate(starts):
            block_id = f"{split_name}_{block_index:04d}"
            for offset in range(block_hours):
                value = values[start + offset]
                yield {
                    "block_id": block_id,
                    "split": split_name,
                    "block_probability": str(probability),
                    "hour_offset": offset,
                    "source_relative_hour": start + offset,
                    "requested_gpu_occupancy": str(value),
                    "workload_fraction": str(value / peak),
                }


def _marginal_rows(block_count: int, split_name: str):
    probability = Decimal(1) / Decimal(block_count)
    return (
        {
            "id": f"{split_name}_{index:04d}",
            "probability": str(probability),
        }
        for index in range(block_count)
    )


def run(config_path: Path) -> dict[str, object]:
    config_path = config_path.resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    source = _path(config["source"]["path"], "source.path")
    if _sha256(source) != config["source"]["sha256"]:
        raise ValueError("Alibaba candidate source SHA-256 drifted")
    derivation = config["derivation"]
    if (
        derivation.get("job_split_policy")
        != "exclude_jobs_contributing_to_both_sides"
    ):
        raise ValueError(
            "job_split_policy must exclude jobs contributing to both sides"
        )
    split_fraction = _decimal(derivation["split_fraction"], "split_fraction")
    if not Decimal(0) < split_fraction < Decimal(1):
        raise ValueError("split_fraction must lie in (0, 1)")
    block_hours = _integer(derivation["block_hours"], "block_hours")
    stride = _integer(derivation["block_stride_hours"], "block_stride_hours")
    minimum, maximum, source_rows = _source_bounds(source)
    base = (minimum // 3600) * 3600
    horizon = int(
        (Decimal(maximum - base) / _HOUR).to_integral_value(
            rounding=ROUND_CEILING
        )
    )
    split = int(
        (Decimal(horizon) * split_fraction).to_integral_value(
            rounding=ROUND_FLOOR
        )
    )
    if split < block_hours or horizon - split < block_hours:
        raise ValueError("both splits must contain at least one complete block")
    split_boundary_second = base + split * 3600
    excluded_jobs = _cross_split_jobs(source, split_boundary_second)
    occupancy, excluded_task_rows = _hourly_occupancy(
        source,
        base,
        horizon,
        excluded_jobs,
    )
    training_peak = max(occupancy[:split])
    if training_peak <= 0:
        raise ValueError("training occupancy peak must be positive")
    training_count = 1 + (split - block_hours) // stride
    holdout_count = 1 + (horizon - split - block_hours) // stride

    target = _path(config["output"]["directory"], "output.directory")
    if target.exists():
        raise FileExistsError(f"refusing to overwrite output: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))
    try:
        _write_gzip_csv(
            staging / "workload_blocks.csv.gz",
            (
                "block_id",
                "split",
                "block_probability",
                "hour_offset",
                "source_relative_hour",
                "requested_gpu_occupancy",
                "workload_fraction",
            ),
            _blocks(
                occupancy,
                split=split,
                block_hours=block_hours,
                stride=stride,
                peak=training_peak,
            ),
        )
        for split_name, count in (
            ("training", training_count),
            ("holdout", holdout_count),
        ):
            _write_gzip_csv(
                staging / f"{split_name}_marginal.csv.gz",
                ("id", "probability"),
                _marginal_rows(count, split_name),
            )
        summary = {
            "schema": config["output"]["schema"],
            "config_sha256": _sha256(config_path),
            "implementation_sha256": _sha256(Path(__file__)),
            "source_sha256": _sha256(source),
            "source_task_rows": source_rows,
            "base_source_second": base,
            "hour_count": horizon,
            "split_hour": split,
            "split_boundary_source_second": split_boundary_second,
            "split_fraction": str(split_fraction),
            "split_rounding": "floor",
            "job_split_policy": "exclude_jobs_contributing_to_both_sides",
            "cross_split_jobs_excluded": len(excluded_jobs),
            "cross_split_task_rows_excluded": excluded_task_rows,
            "training_peak_requested_gpu_occupancy": str(training_peak),
            "block_hours": block_hours,
            "block_stride_hours": stride,
            "training_block_count": training_count,
            "holdout_block_count": holdout_count,
            "interval_semantics": "half_open_start_inclusive_end_exclusive",
            "workload_fraction_is_power": False,
            "flexible_fraction_inferred": False,
            "deadline_observed": False,
            "checkpoint_observed": False,
            "recoverability_observed": False,
            "parameter_status": (
                "dimensionless_requested_GPU_occupancy_blocks_from_public_trace_"
                "not_power_or_observed_flexibility"
            ),
        }
        summary_path = staging / "summary.json"
        summary_path.write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        names = (
            "holdout_marginal.csv.gz",
            "summary.json",
            "training_marginal.csv.gz",
            "workload_blocks.csv.gz",
        )
        manifest = {name: _sha256(staging / name) for name in names}
        (staging / "SHA256SUMS.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        staging.rename(target)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/alibaba_dimensionless_workload_blocks_v3.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
