"""Build an auditable hourly CFE-deficit profile from pinned RTS-GMLC data."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import yaml

import src.scenarios.rts_gmlc_cfe_deficit as cfe_deficit_module
from src.grid import (
    RTS_GMLC_COMMIT,
    RTS_GMLC_MANIFEST_SHA256,
    RTS_GMLC_RELEASE,
    RTS_GMLC_REPOSITORY,
    load_rts_gmlc_chronological_data,
    validate_rts_gmlc_source_identity,
    verify_sha256_manifest,
)
from src.scenarios.rts_gmlc_cfe_deficit import (
    CFE_DEFICIT_COLUMNS,
    RENEWABLE_UNIT_TYPES,
    derive_rts_gmlc_cfe_deficit,
)

_ROOT = Path(__file__).resolve().parents[1]


def _mapping(raw: object, label: str) -> dict:
    if not isinstance(raw, dict):
        raise TypeError(f"{label} must be a mapping")
    return raw


def _path(raw: object, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"{label} must be a nonempty path")
    path = Path(raw)
    return path if path.is_absolute() else _ROOT / path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write_csv(path: Path, profile) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle, fieldnames=CFE_DEFICIT_COLUMNS, lineterminator="\n"
        )
        writer.writeheader()
        for point in profile.points:
            writer.writerow(
                {
                    "timestamp": point.timestamp.isoformat(),
                    "system_load_mw": point.system_load_mw,
                    "renewable_available_mw": point.renewable_available_mw,
                    "renewable_share": point.renewable_share,
                    "dc_demand_mw": point.dc_demand_mw,
                    "hourly_cfe_target": point.hourly_cfe_target,
                    "attributed_cfe_mw": point.attributed_cfe_mw,
                    "cfe_deficit_mw": point.cfe_deficit_mw,
                    "green_call_mw": point.green_call_mw,
                    "green_call_fraction": (point.green_call_mw / point.dc_demand_mw),
                }
            )


def run(config_path: Path) -> dict[str, object]:
    config_bytes = config_path.read_bytes()
    config = _mapping(yaml.safe_load(config_bytes), "config")
    source = _mapping(config.get("source"), "source")
    validate_rts_gmlc_source_identity(source)
    if source.get("manifest_sha256") != RTS_GMLC_MANIFEST_SHA256:
        raise ValueError("RTS-GMLC source manifest identity drifted")
    source_root = _path(source.get("path"), "source.path")
    if _sha256(source_root / "SHA256SUMS") != RTS_GMLC_MANIFEST_SHA256:
        raise ValueError("RTS-GMLC source manifest content drifted")
    if not verify_sha256_manifest(source_root):
        raise ValueError("RTS-GMLC source files failed SHA-256 verification")

    derivation = _mapping(config.get("derivation"), "derivation")
    renewable_types = frozenset(derivation.get("renewable_unit_types", ()))
    if renewable_types != RENEWABLE_UNIT_TYPES:
        raise ValueError("renewable_unit_types must match the frozen set")
    profile = derive_rts_gmlc_cfe_deficit(
        load_rts_gmlc_chronological_data(source_root),
        dc_demand_mw=float(derivation["dc_demand_mw"]),
        hourly_cfe_target=float(derivation["hourly_cfe_target"]),
        renewable_unit_types=renewable_types,
        source=(
            f"{RTS_GMLC_REPOSITORY}@{RTS_GMLC_COMMIT}"
            f"::manifest={RTS_GMLC_MANIFEST_SHA256}"
        ),
    )

    output = _mapping(config.get("output"), "output")
    schema = output.get("schema", "rts_gmlc_hourly_cfe_deficit_v1")
    if not isinstance(schema, str) or not schema:
        raise ValueError("output.schema must be a nonempty string")
    predecessor = config.get("predecessor")
    predecessor_record = None
    if predecessor is not None:
        predecessor = _mapping(predecessor, "predecessor")
        predecessor_manifest = _path(
            predecessor.get("manifest_path"), "predecessor.manifest_path"
        )
        predecessor_profile = _path(
            predecessor.get("profile_path"), "predecessor.profile_path"
        )
        expected_manifest_sha256 = predecessor.get("manifest_sha256")
        expected_profile_sha256 = predecessor.get("profile_sha256")
        if _sha256(predecessor_manifest) != expected_manifest_sha256:
            raise ValueError("predecessor manifest identity drifted")
        if _sha256(predecessor_profile) != expected_profile_sha256:
            raise ValueError("predecessor profile identity drifted")
        predecessor_record = {
            "schema": predecessor.get("schema"),
            "manifest_path": str(predecessor_manifest.relative_to(_ROOT)),
            "manifest_sha256": expected_manifest_sha256,
            "profile_path": str(predecessor_profile.relative_to(_ROOT)),
            "profile_sha256": expected_profile_sha256,
            "status": predecessor.get("status"),
        }
    target = _path(output.get("directory"), "output.directory")
    if target.exists():
        raise FileExistsError(f"immutable output directory already exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(dir=target.parent, prefix=f".{target.name}.processing-")
    )
    try:
        csv_path = staging / "hourly_cfe_deficit.csv"
        _write_csv(csv_path, profile)
        values = profile.values
        summary = {
            "schema": schema,
            "source": {
                "repository": RTS_GMLC_REPOSITORY,
                "release": RTS_GMLC_RELEASE,
                "commit": RTS_GMLC_COMMIT,
                "manifest_sha256": RTS_GMLC_MANIFEST_SHA256,
            },
            "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
            "implementation_sha256": _sha256(Path(__file__)),
            "derivation_module_sha256": _sha256(Path(cfe_deficit_module.__file__)),
            "hours": len(profile.points),
            "first_timestamp": profile.points[0].timestamp.isoformat(),
            "last_timestamp": profile.points[-1].timestamp.isoformat(),
            "dc_demand_mw": profile.points[0].dc_demand_mw,
            "hourly_cfe_target": profile.points[0].hourly_cfe_target,
            "renewable_unit_types": sorted(renewable_types),
            "formula": profile.formula,
            "parameter_status": profile.parameter_status,
            "green_call_mw": {
                "minimum": min(values),
                "maximum": max(values),
                "mean": sum(values) / len(values),
            },
            "security_certified": False,
            "procurement_or_delivery_claimed": False,
        }
        if predecessor_record is not None:
            summary["predecessor"] = predecessor_record
        (staging / "summary.json").write_text(
            json.dumps(summary, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        manifest = {
            name: _sha256(staging / name)
            for name in ("hourly_cfe_deficit.csv", "summary.json")
        }
        (staging / "SHA256SUMS.json").write_text(
            json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8"
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
        default=Path("configs/rts_gmlc_cfe_deficit.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2))


if __name__ == "__main__":
    main()
