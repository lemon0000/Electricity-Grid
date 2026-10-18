"""Build split-aware RTS-GMLC network, CFE, and N-1 chronology blocks."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import shutil
import tempfile
from collections.abc import Iterable, Mapping
from datetime import datetime, timezone
from decimal import ROUND_FLOOR, Decimal, InvalidOperation
from pathlib import Path

import yaml

from src.grid.rts_gmlc import (
    RTS_GMLC_MANIFEST_SHA256,
    validate_rts_gmlc_source_identity,
    verify_sha256_manifest,
)
from src.scenarios.rts_gmlc_n1_chronology import (
    N1OutageEvent,
    N1ReliabilityComponent,
    event_by_hour,
    simulate_n_minus_one_events,
)

_ROOT = Path(__file__).resolve().parents[1]
_CFE_FIELDS = {
    "timestamp",
    "system_load_mw",
    "green_call_fraction",
}


def _path(raw: object, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"{label} must be a nonempty path")
    path = Path(raw)
    return path if path.is_absolute() else _ROOT / path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _decimal(raw: object, label: str) -> Decimal:
    try:
        value = Decimal(str(raw))
    except (InvalidOperation, ValueError) as error:
        raise ValueError(f"{label} must be a finite decimal") from error
    if not value.is_finite():
        raise ValueError(f"{label} must be a finite decimal")
    return value


def _positive_integer(raw: object, label: str) -> int:
    if isinstance(raw, bool) or not isinstance(raw, int) or raw <= 0:
        raise ValueError(f"{label} must be a positive integer")
    return raw


def _verify_package(directory: Path, expected_manifest_sha256: str) -> None:
    manifest_path = directory / "SHA256SUMS.json"
    if _sha256(manifest_path) != expected_manifest_sha256:
        raise ValueError(f"package manifest SHA-256 drifted: {directory}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or not manifest:
        raise ValueError(f"package manifest is invalid: {directory}")
    for name, digest in manifest.items():
        if _sha256(directory / name) != digest:
            raise ValueError(f"package member SHA-256 drifted: {directory / name}")


def _plain_rows(path: Path, required_fields: set[str]) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as source:
        reader = csv.DictReader(source)
        if reader.fieldnames is None or not required_fields.issubset(
            reader.fieldnames
        ):
            raise ValueError(f"{path} schema drifted")
        rows = list(reader)
    if not rows:
        raise ValueError(f"{path} must be nonempty")
    return rows


def _source_csv(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as source:
        rows = list(csv.DictReader(source))
    if not rows:
        raise ValueError(f"{path} must be nonempty")
    return rows


def _connected_component_count(
    branch_rows: list[dict[str, str]],
    *,
    excluded_uid: str | None,
) -> int:
    buses = {
        int(row[field])
        for row in branch_rows
        for field in ("From Bus", "To Bus")
    }
    adjacency = {bus: set() for bus in buses}
    for row in branch_rows:
        if row["UID"] == excluded_uid:
            continue
        left = int(row["From Bus"])
        right = int(row["To Bus"])
        adjacency[left].add(right)
        adjacency[right].add(left)
    unseen = set(buses)
    components = 0
    while unseen:
        components += 1
        stack = [next(iter(unseen))]
        visited = set()
        while stack:
            bus = stack.pop()
            if bus in visited:
                continue
            visited.add(bus)
            stack.extend(adjacency[bus] - visited)
        unseen -= visited
    return components


def _components(
    root: Path,
    *,
    excluded_generator_unit_types: frozenset[str],
) -> tuple[
    tuple[N1ReliabilityComponent, ...],
    tuple[str, ...],
    tuple[str, ...],
]:
    source = root / "RTS_Data" / "SourceData"
    result = []
    excluded_generators = []
    generator_rows = _source_csv(source / "gen.csv")
    for index, row in enumerate(generator_rows, start=2):
        mean_up = _decimal(row["MTTF Hr"], f"generator row {index} MTTF")
        mean_down = _decimal(row["MTTR Hr"], f"generator row {index} MTTR")
        if mean_up == 0 and mean_down == 0 and _decimal(
            row["FOR"], f"generator row {index} FOR"
        ) == 0:
            continue
        if mean_up <= 0 or mean_down <= 0:
            raise ValueError("generator reliability means must be positive")
        if row["Unit Type"] in excluded_generator_unit_types:
            excluded_generators.append(row["GEN UID"])
            continue
        result.append(
            N1ReliabilityComponent(
                component_type="generator",
                uid=row["GEN UID"],
                failure_rate_per_hour=float(Decimal(1) / mean_up),
                mean_down_hours=float(mean_down),
            )
        )
    branch_rows = _source_csv(source / "branch.csv")
    base_components = _connected_component_count(branch_rows, excluded_uid=None)
    excluded_branches = tuple(
        sorted(
            row["UID"]
            for row in branch_rows
            if _connected_component_count(
                branch_rows,
                excluded_uid=row["UID"],
            )
            > base_components
        )
    )
    for index, row in enumerate(branch_rows, start=2):
        annual_rate = _decimal(
            row["Perm OutRate"], f"branch row {index} permanent outage rate"
        )
        mean_down = _decimal(
            row["Duration"], f"branch row {index} outage duration"
        )
        if annual_rate <= 0 or mean_down <= 0:
            raise ValueError("branch reliability fields must be positive")
        if row["UID"] in excluded_branches:
            continue
        result.append(
            N1ReliabilityComponent(
                component_type="branch",
                uid=row["UID"],
                failure_rate_per_hour=float(annual_rate / Decimal(8760)),
                mean_down_hours=float(mean_down),
            )
        )
    return tuple(result), tuple(sorted(excluded_generators)), excluded_branches


def _cfe_points(path: Path) -> tuple[dict[str, object], ...]:
    rows = _plain_rows(path, _CFE_FIELDS)
    result = []
    previous: datetime | None = None
    for index, row in enumerate(rows, start=2):
        timestamp = datetime.fromisoformat(row["timestamp"])
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        if previous is not None and (timestamp - previous).total_seconds() != 3600:
            raise ValueError("CFE chronology must be continuous hourly")
        system_load = _decimal(
            row["system_load_mw"], f"CFE row {index} system_load_mw"
        )
        cfe_call = _decimal(
            row["green_call_fraction"], f"CFE row {index} green_call_fraction"
        )
        if system_load < 0 or not Decimal(0) <= cfe_call <= Decimal(1):
            raise ValueError("CFE rows contain an invalid load or call fraction")
        result.append(
            {
                "timestamp": timestamp,
                "system_load_mw": system_load,
                "cfe_call_fraction": cfe_call,
            }
        )
        previous = timestamp
    return tuple(result)


def _write_gzip_csv(
    path: Path,
    fields: tuple[str, ...],
    rows: Iterable[Mapping[str, object]],
) -> None:
    with (
        path.open("wb") as raw,
        gzip.GzipFile(filename="", fileobj=raw, mode="wb", mtime=0) as compressed,
        io.TextIOWrapper(compressed, encoding="utf-8", newline="") as text,
    ):
        writer = csv.DictWriter(text, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def _cross_split_event_ids(
    events: tuple[N1OutageEvent, ...],
    split_hour: int,
) -> set[str]:
    return {
        event.event_id
        for event in events
        if event.start_hour < split_hour < event.end_hour_exclusive
    }


def _accepted_starts(
    active: tuple[N1OutageEvent | None, ...],
    *,
    low: int,
    high: int,
    block_hours: int,
    stride: int,
    excluded_event_ids: set[str],
) -> tuple[int, ...]:
    starts = []
    for start in range(low, high - block_hours + 1, stride):
        represented = active[start : start + block_hours]
        if any(
            event is not None and event.event_id in excluded_event_ids
            for event in represented
        ):
            continue
        starts.append(start)
    return tuple(starts)


def run(config_path: Path) -> dict[str, object]:
    config_path = config_path.resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    source = config["source"]
    validate_rts_gmlc_source_identity(source)
    if source["grid_manifest_sha256"] != RTS_GMLC_MANIFEST_SHA256:
        raise ValueError("RTS-GMLC source manifest identity drifted")
    grid_root = _path(source["grid_root"], "source.grid_root")
    if (
        _sha256(grid_root / "SHA256SUMS") != source["grid_manifest_sha256"]
        or not verify_sha256_manifest(grid_root)
    ):
        raise ValueError("RTS-GMLC source manifest verification failed")
    cfe = _path(source["cfe_package"], "source.cfe_package")
    _verify_package(cfe, source["cfe_manifest_sha256"])

    derivation = config["derivation"]
    if derivation["reliability_scope"] != (
        "enabled_generators_and_nonislanding_AC_branches_in_full_RTS_GMLC"
    ):
        raise ValueError("reliability_scope contract drifted")
    if derivation["excluded_branch_rule"] != (
        "removal_increases_AC_connected_component_count"
    ):
        raise ValueError("excluded_branch_rule contract drifted")
    excluded_unit_types = frozenset(
        str(item) for item in derivation["excluded_generator_unit_types"]
    )
    if excluded_unit_types != frozenset({"CSP", "STORAGE", "SYNC_COND"}):
        raise ValueError("excluded_generator_unit_types contract drifted")
    if derivation["outage_model"] != (
        "stationary_system_level_competing_risks_N_minus_one"
    ):
        raise ValueError("outage_model contract drifted")
    if derivation["cross_split_event_policy"] != (
        "exclude_every_block_touched_by_cross_split_event"
    ):
        raise ValueError("cross_split_event_policy contract drifted")
    seeds = tuple(int(seed) for seed in derivation["outage_seeds"])
    if not seeds or len(seeds) != len(set(seeds)):
        raise ValueError("outage_seeds must be nonempty and unique")
    split_fraction = _decimal(derivation["split_fraction"], "split_fraction")
    if not Decimal(0) < split_fraction < Decimal(1):
        raise ValueError("split_fraction must lie in (0, 1)")
    block_hours = _positive_integer(derivation["block_hours"], "block_hours")
    stride = _positive_integer(
        derivation["block_stride_hours"], "block_stride_hours"
    )

    components, excluded_generators, excluded_branches = _components(
        grid_root,
        excluded_generator_unit_types=excluded_unit_types,
    )
    cfe_points = _cfe_points(cfe / "hourly_cfe_deficit.csv")
    horizon = len(cfe_points)
    split = int(
        (Decimal(horizon) * split_fraction).to_integral_value(
            rounding=ROUND_FLOOR
        )
    )
    if split < block_hours or horizon - split < block_hours:
        raise ValueError("both splits must contain at least one complete block")

    events_by_seed = {
        seed: simulate_n_minus_one_events(
            components,
            seed=seed,
            horizon_hours=horizon,
        )
        for seed in seeds
    }
    active_by_seed = {
        seed: event_by_hour(events, horizon_hours=horizon)
        for seed, events in events_by_seed.items()
    }
    starts_by_split: dict[str, list[tuple[int, int]]] = {
        "training": [],
        "holdout": [],
    }
    excluded_by_seed = {}
    for seed in seeds:
        excluded = _cross_split_event_ids(events_by_seed[seed], split)
        excluded_by_seed[seed] = excluded
        starts_by_split["training"].extend(
            (seed, start)
            for start in _accepted_starts(
                active_by_seed[seed],
                low=0,
                high=split,
                block_hours=block_hours,
                stride=stride,
                excluded_event_ids=excluded,
            )
        )
        starts_by_split["holdout"].extend(
            (seed, start)
            for start in _accepted_starts(
                active_by_seed[seed],
                low=split,
                high=horizon,
                block_hours=block_hours,
                stride=stride,
                excluded_event_ids=excluded,
            )
        )
    if any(not starts for starts in starts_by_split.values()):
        raise ValueError("both splits must retain at least one block")

    target = _path(config["output"]["directory"], "output.directory")
    if target.exists():
        raise FileExistsError(f"refusing to overwrite output: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))
    try:
        block_rows = []
        marginal_rows: dict[str, list[dict[str, object]]] = {}
        for split_name in ("training", "holdout"):
            starts = starts_by_split[split_name]
            probability = Decimal(1) / Decimal(len(starts))
            marginal_rows[split_name] = []
            for block_index, (seed, start) in enumerate(starts):
                block_id = f"{split_name}_s{seed}_{block_index:04d}"
                marginal_rows[split_name].append(
                    {"id": block_id, "probability": str(probability)}
                )
                for offset in range(block_hours):
                    hour = start + offset
                    point = cfe_points[hour]
                    event = active_by_seed[seed][hour]
                    block_rows.append(
                        {
                            "block_id": block_id,
                            "split": split_name,
                            "block_probability": str(probability),
                            "outage_seed": seed,
                            "hour_offset": offset,
                            "source_hour": hour,
                            "timestamp": point["timestamp"].isoformat(),
                            "system_load_mw": str(point["system_load_mw"]),
                            "cfe_call_fraction": str(point["cfe_call_fraction"]),
                            "active_event_id": event.event_id if event else "",
                            "active_component_type": (
                                event.component_type if event else ""
                            ),
                            "active_component_uid": event.uid if event else "",
                        }
                    )
        _write_gzip_csv(
            staging / "power_system_blocks.csv.gz",
            (
                "block_id",
                "split",
                "block_probability",
                "outage_seed",
                "hour_offset",
                "source_hour",
                "timestamp",
                "system_load_mw",
                "cfe_call_fraction",
                "active_event_id",
                "active_component_type",
                "active_component_uid",
            ),
            block_rows,
        )
        for split_name in ("training", "holdout"):
            _write_gzip_csv(
                staging / f"{split_name}_marginal.csv.gz",
                ("id", "probability"),
                marginal_rows[split_name],
            )
        event_rows = (
            {
                "outage_seed": seed,
                "event_id": event.event_id,
                "component_type": event.component_type,
                "component_uid": event.uid,
                "start_hour": event.start_hour,
                "end_hour_exclusive": event.end_hour_exclusive,
                "duration_hours": event.duration_hours,
                "crosses_split": event.event_id in excluded_by_seed[seed],
            }
            for seed in seeds
            for event in events_by_seed[seed]
        )
        _write_gzip_csv(
            staging / "n1_outage_events.csv.gz",
            (
                "outage_seed",
                "event_id",
                "component_type",
                "component_uid",
                "start_hour",
                "end_hour_exclusive",
                "duration_hours",
                "crosses_split",
            ),
            event_rows,
        )
        summary = {
            "schema": config["output"]["schema"],
            "config_sha256": _sha256(config_path),
            "implementation_sha256": _sha256(Path(__file__)),
            "n1_chronology_module_sha256": _sha256(
                _ROOT / "src/scenarios/rts_gmlc_n1_chronology.py"
            ),
            "grid_source_manifest_sha256": source["grid_manifest_sha256"],
            "cfe_package_manifest_sha256": source["cfe_manifest_sha256"],
            "hours": horizon,
            "split_hour": split,
            "block_hours": block_hours,
            "block_stride_hours": stride,
            "outage_seeds": list(seeds),
            "reliability_components": len(components),
            "generator_reliability_components": sum(
                item.component_type == "generator" for item in components
            ),
            "branch_reliability_components": sum(
                item.component_type == "branch" for item in components
            ),
            "reliability_scope": derivation["reliability_scope"],
            "excluded_disabled_generator_uids": list(excluded_generators),
            "excluded_islanding_branch_uids": list(excluded_branches),
            "event_counts": {
                str(seed): len(events_by_seed[seed]) for seed in seeds
            },
            "cross_split_event_counts": {
                str(seed): len(excluded_by_seed[seed]) for seed in seeds
            },
            "training_block_count": len(starts_by_split["training"]),
            "holdout_block_count": len(starts_by_split["holdout"]),
            "maximum_simultaneous_outages": 1,
            "training_marginal_role": derivation["training_marginal_role"],
            "holdout_marginal_role": derivation["holdout_marginal_role"],
            "outage_frequency_semantics": derivation[
                "outage_frequency_semantics"
            ],
            "empirical_outage_probability_claimed": False,
            "grid_need_dispatch_completed": False,
            "security_certified": False,
        }
        (staging / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        names = (
            "holdout_marginal.csv.gz",
            "n1_outage_events.csv.gz",
            "power_system_blocks.csv.gz",
            "summary.json",
            "training_marginal.csv.gz",
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
        default=Path("configs/rts_gmlc_public_power_system_blocks_v4.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
