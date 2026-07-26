"""Validate the pinned RTS-GMLC source data and hourly load proxy."""

from __future__ import annotations

import argparse
import hashlib
import json
from dataclasses import asdict
from pathlib import Path

import yaml

from src.grid import (
    RTS_GMLC_MANIFEST_SHA256,
    load_rts24_area1_load_multipliers,
    summarize_rts_gmlc,
    validate_rts_gmlc_source_identity,
    verify_sha256_manifest,
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run(config_path: Path) -> dict[str, object]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    source = config["source"]
    validate_rts_gmlc_source_identity(source)
    if source.get("manifest_sha256") != RTS_GMLC_MANIFEST_SHA256:
        raise ValueError("RTS-GMLC source manifest lock drifted")
    root = Path(source["path"])
    manifest_path = root / "SHA256SUMS"
    if (
        not manifest_path.is_file()
        or _sha256(manifest_path) != source["manifest_sha256"]
    ):
        raise ValueError("RTS-GMLC source manifest SHA-256 drifted")
    if not verify_sha256_manifest(root):
        raise ValueError("RTS-GMLC source manifest validation failed")
    summary = summarize_rts_gmlc(root)
    expected = config["expected"]
    checks = {
        "source_repository": summary.source_repository == source["repository"],
        "source_release": summary.source_release == source["release"],
        "source_commit": summary.source_commit == source["commit"],
        "source_manifest_sha256": (
            summary.source_manifest_sha256 == source["manifest_sha256"]
        ),
        "sha256_manifest": summary.sha256_manifest_valid,
        "buses": summary.buses == expected["buses"],
        "generators": summary.generators == expected["generators"],
        "ac_branches": summary.ac_branches == expected["ac_branches"],
        "day_ahead_hours": summary.day_ahead_hours == expected["day_ahead_hours"],
        "all_core_series_have_expected_row_count": all(
            rows == expected["day_ahead_hours"]
            for rows in summary.day_ahead_rows.values()
        ),
        "all_core_series_timestamp_continuous": all(
            summary.day_ahead_series_timestamp_continuous.values()
        ),
        "all_core_series_share_common_calendar": (
            summary.day_ahead_series_common_calendar
        ),
        "all_core_pointer_columns_complete": (
            summary.day_ahead_core_pointer_columns_complete
        ),
    }
    if not all(checks.values()):
        raise RuntimeError(f"RTS-GMLC validation failed: {checks}")

    proxy_config = config["legacy_rts24_proxy"]
    multipliers = load_rts24_area1_load_multipliers(
        root,
        static_peak_mw=float(proxy_config["static_peak_mw"]),
    )
    multiplier_values = sorted(value for _, value in multipliers)
    output = {
        **asdict(summary),
        "first_timestamp": summary.first_timestamp.isoformat(),
        "last_timestamp": summary.last_timestamp.isoformat(),
        "checks": checks,
        "rts24_load_proxy_status": proxy_config["parameter_status"],
        "generator_ramp_mapping": proxy_config["generator_ramp_mapping"],
        "rts24_load_quantile_method": "lower_order_statistic",
        "rts24_load_multiplier_min": multiplier_values[0],
        "rts24_load_multiplier_median": multiplier_values[
            int(0.5 * (len(multipliers) - 1))
        ],
        "rts24_load_multiplier_p95": multiplier_values[
            int(0.95 * (len(multipliers) - 1))
        ],
        "rts24_load_multiplier_max": multiplier_values[-1],
    }
    output_path = Path(config["output"]["path"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output, indent=2, sort_keys=True, default=str) + "\n",
        encoding="utf-8",
    )
    return output


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/rts_gmlc.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2, sort_keys=True, default=str))


if __name__ == "__main__":
    main()
