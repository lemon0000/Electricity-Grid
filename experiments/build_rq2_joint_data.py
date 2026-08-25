"""Build synchronized RTS-GMLC grid, CFE, and reliability inputs for RQ2."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import io
import json
import shutil
import tempfile
from contextlib import contextmanager
from datetime import timedelta
from pathlib import Path

import yaml

import src.scenarios.rts_gmlc_reliability as reliability_module
from src.grid import (
    RTS_GMLC_COMMIT,
    RTS_GMLC_MANIFEST_SHA256,
    RTS_GMLC_RELEASE,
    RTS_GMLC_REPOSITORY,
    load_rts_gmlc_chronological_data,
    validate_rts_gmlc_source_identity,
    verify_sha256_manifest,
)
from src.scenarios.rts_gmlc_cfe_deficit import RENEWABLE_UNIT_TYPES
from src.scenarios.rts_gmlc_reliability import (
    hourly_outage_counts,
    load_reliability_components,
    simulate_outage_events,
)

_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_FILES = (
    "reliability_components.csv.gz",
    "outage_events.csv.gz",
    "hourly_outage_counts.csv.gz",
    "hourly_bus_load.csv.gz",
    "hourly_renewable_availability.csv.gz",
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


def run(config_path: Path) -> dict[str, object]:
    config_bytes = config_path.read_bytes()
    config = yaml.safe_load(config_bytes)
    source = config["source"]
    validate_rts_gmlc_source_identity(source)
    if source["manifest_sha256"] != RTS_GMLC_MANIFEST_SHA256:
        raise ValueError("RTS-GMLC source manifest identity drifted")
    source_root = _path(source["path"], "source.path")
    if _sha256(
        source_root / "SHA256SUMS"
    ) != RTS_GMLC_MANIFEST_SHA256 or not verify_sha256_manifest(source_root):
        raise ValueError("RTS-GMLC source manifest verification failed")

    derivation = config["derivation"]
    area = int(derivation["area"])
    horizon_hours = int(derivation["horizon_hours"])
    seeds = tuple(int(seed) for seed in derivation["outage_seeds"])
    renewable_types = frozenset(derivation["renewable_unit_types"])
    if renewable_types != RENEWABLE_UNIT_TYPES:
        raise ValueError("renewable_unit_types must match the project contract")
    if len(seeds) != len(set(seeds)) or not seeds:
        raise ValueError("outage_seeds must be nonempty and unique")

    data = load_rts_gmlc_chronological_data(source_root)
    if horizon_hours != len(data.hourly_points):
        raise ValueError("horizon_hours must match the complete RTS-GMLC chronology")
    area_buses = tuple(bus for bus in data.buses if bus.area == area)
    bus_ids = {bus.uid for bus in area_buses}
    renewables = tuple(
        generator
        for generator in data.generators
        if generator.enabled
        and generator.bus in bus_ids
        and generator.unit_type in renewable_types
    )
    components = load_reliability_components(source_root, area=area)
    events_by_seed = {
        seed: simulate_outage_events(
            components,
            seed=seed,
            horizon_hours=horizon_hours,
        )
        for seed in seeds
    }

    target = _path(config["output"]["directory"], "output.directory")
    if target.exists():
        raise FileExistsError(f"immutable output directory already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(dir=target.parent, prefix=f".{target.name}.processing-")
    )
    try:
        with _gzip_csv(
            staging / "reliability_components.csv.gz",
            (
                "component_type",
                "uid",
                "from_bus",
                "to_bus",
                "rts24_from_bus",
                "rts24_to_bus",
                "mean_up_hours",
                "mean_down_hours",
                "stated_for",
                "implied_unavailability",
                "source_rate",
                "source_rate_unit",
            ),
        ) as writer:
            for component in components:
                writer.writerow(
                    {
                        "component_type": component.component_type,
                        "uid": component.uid,
                        "from_bus": component.from_bus,
                        "to_bus": component.to_bus or "",
                        "rts24_from_bus": component.from_bus % 100,
                        "rts24_to_bus": (
                            component.to_bus % 100
                            if component.to_bus is not None
                            else ""
                        ),
                        "mean_up_hours": component.mean_up_hours,
                        "mean_down_hours": component.mean_down_hours,
                        "stated_for": (
                            component.stated_for
                            if component.stated_for is not None
                            else ""
                        ),
                        "implied_unavailability": component.implied_unavailability,
                        "source_rate": component.source_rate,
                        "source_rate_unit": component.source_rate_unit,
                    }
                )

        with _gzip_csv(
            staging / "outage_events.csv.gz",
            (
                "seed",
                "component_type",
                "uid",
                "start_hour",
                "end_hour_exclusive",
                "duration_hours",
                "start_timestamp",
                "end_timestamp_exclusive",
            ),
        ) as writer:
            start = data.hourly_points[0].timestamp
            for seed in seeds:
                for event in events_by_seed[seed]:
                    writer.writerow(
                        {
                            "seed": seed,
                            "component_type": event.component_type,
                            "uid": event.uid,
                            "start_hour": event.start_hour,
                            "end_hour_exclusive": event.end_hour_exclusive,
                            "duration_hours": event.duration_hours,
                            "start_timestamp": (
                                start + timedelta(hours=event.start_hour)
                            ).isoformat(),
                            "end_timestamp_exclusive": (
                                start + timedelta(hours=event.end_hour_exclusive)
                            ).isoformat(),
                        }
                    )

        with _gzip_csv(
            staging / "hourly_outage_counts.csv.gz",
            (
                "seed",
                "source_hour",
                "timestamp",
                "generator_outages",
                "branch_outages",
            ),
        ) as writer:
            for seed in seeds:
                counts = hourly_outage_counts(
                    events_by_seed[seed],
                    horizon_hours=horizon_hours,
                )
                for index, ((generators_down, branches_down), point) in enumerate(
                    zip(counts, data.hourly_points, strict=True)
                ):
                    writer.writerow(
                        {
                            "seed": seed,
                            "source_hour": index,
                            "timestamp": point.timestamp.isoformat(),
                            "generator_outages": generators_down,
                            "branch_outages": branches_down,
                        }
                    )

        with _gzip_csv(
            staging / "hourly_bus_load.csv.gz",
            ("source_hour", "timestamp", "rts_bus_id", "rts24_bus", "load_mw"),
        ) as writer:
            for index, point in enumerate(data.hourly_points):
                for bus in area_buses:
                    writer.writerow(
                        {
                            "source_hour": index,
                            "timestamp": point.timestamp.isoformat(),
                            "rts_bus_id": bus.uid,
                            "rts24_bus": bus.uid % 100,
                            "load_mw": point.demand_by_bus_mw[bus.uid],
                        }
                    )

        with _gzip_csv(
            staging / "hourly_renewable_availability.csv.gz",
            (
                "source_hour",
                "timestamp",
                "rts_bus_id",
                "rts24_bus",
                "generator_uid",
                "unit_type",
                "available_mw",
                "contract_status",
            ),
        ) as writer:
            for index, point in enumerate(data.hourly_points):
                for generator in renewables:
                    writer.writerow(
                        {
                            "source_hour": index,
                            "timestamp": point.timestamp.isoformat(),
                            "rts_bus_id": generator.bus,
                            "rts24_bus": generator.bus % 100,
                            "generator_uid": generator.uid,
                            "unit_type": generator.unit_type,
                            "available_mw": point.generator_max_mw[generator.uid],
                            "contract_status": derivation["cfe_contract_status"],
                        }
                    )

        event_counts = {
            str(seed): {
                "events": len(events_by_seed[seed]),
                "generator_events": sum(
                    event.component_type == "generator"
                    for event in events_by_seed[seed]
                ),
                "branch_events": sum(
                    event.component_type == "branch" for event in events_by_seed[seed]
                ),
            }
            for seed in seeds
        }
        generator_for_errors = [
            abs(component.stated_for - component.implied_unavailability)
            for component in components
            if component.stated_for is not None
        ]
        summary = {
            "schema": "rq2_joint_rts_gmlc_data_v1",
            "source": {
                "repository": RTS_GMLC_REPOSITORY,
                "release": RTS_GMLC_RELEASE,
                "commit": RTS_GMLC_COMMIT,
                "manifest_sha256": RTS_GMLC_MANIFEST_SHA256,
            },
            "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
            "implementation_sha256": _sha256(Path(__file__)),
            "reliability_module_sha256": _sha256(
                Path(reliability_module.__file__).resolve()
            ),
            "area": area,
            "hours": horizon_hours,
            "first_timestamp": data.hourly_points[0].timestamp.isoformat(),
            "last_timestamp": data.hourly_points[-1].timestamp.isoformat(),
            "buses": len(area_buses),
            "renewable_generators": len(renewables),
            "reliability_components": len(components),
            "generator_reliability_components": sum(
                item.component_type == "generator" for item in components
            ),
            "branch_reliability_components": sum(
                item.component_type == "branch" for item in components
            ),
            "maximum_generator_for_identity_error": max(generator_for_errors),
            "outage_seeds": list(seeds),
            "event_counts": event_counts,
            "evidence_status": {
                "load_and_renewable": "observed_rts_gmlc_benchmark_chronology",
                "outages": "derived_sequential_reliability_benchmark",
                "cfe_contract": derivation["cfe_contract_status"],
                "empirical_outage_probability_claimed": False,
                "security_certified": False,
            },
        }
        (staging / "summary.json").write_text(
            json.dumps(summary, indent=2, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        manifest = {
            name: _sha256(staging / name) for name in (*OUTPUT_FILES, "summary.json")
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
        default=Path("configs/rq2_joint_data_v1.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
