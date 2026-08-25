"""Run RQ2 temporal ablation with an RTS-GMLC CFE-deficit green-call profile."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import tempfile
from pathlib import Path

import yaml

from experiments import run_rq2_h2_temporal_holdout as temporal_runner
from experiments import run_rq2_h2_temporal_source_ablation as legacy_runner
from src.grid import (
    RTS_GMLC_COMMIT,
    RTS_GMLC_MANIFEST_SHA256,
    RTS_GMLC_RELEASE,
    RTS_GMLC_REPOSITORY,
)
from src.scenarios.rts_gmlc_cfe_deficit import (
    CFE_DEFICIT_FORMULA,
    CFE_DEFICIT_PARAMETER_STATUS,
    load_rts_gmlc_cfe_deficit_profile,
)

_ROOT = Path(__file__).resolve().parents[1]
_PROFILE_SCHEMA = "rts_gmlc_hourly_cfe_deficit_v1"


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


def _validate_cfe_source(config: dict) -> tuple[dict, dict]:
    generator = _mapping(config.get("generator"), "generator")
    shape = _mapping(
        generator.get("green_workload_shape"),
        "generator.green_workload_shape",
    )
    metadata = _mapping(
        generator.get("green_cfe_metadata"),
        "generator.green_cfe_metadata",
    )
    demand = float(generator.get("data_center_demand_mw"))
    scale = float(generator.get("green_call_scale_mw"))
    if shape.get("column") != "green_call_fraction":
        raise ValueError("CFE adapter requires green_call_fraction")
    if float(shape.get("external_peak")) != 1.0:
        raise ValueError("CFE adapter requires the frozen external peak 1.0")
    if scale != demand:
        raise ValueError("CFE adapter requires green_call_scale_mw = D_DC")

    profile_path = _path(shape.get("path"), "generator.green_workload_shape.path")
    expected_profile_sha = metadata.get("profile_sha256")
    if _sha256(profile_path) != expected_profile_sha:
        raise ValueError("CFE deficit profile SHA-256 drifted")
    profile = load_rts_gmlc_cfe_deficit_profile(
        profile_path,
        expected_sha256=expected_profile_sha,
        source="validated_rts_gmlc_cfe_profile",
    )
    summary_path = _path(
        metadata.get("summary_path"), "generator.green_cfe_metadata.summary_path"
    )
    if _sha256(summary_path) != metadata.get("summary_sha256"):
        raise ValueError("CFE deficit summary SHA-256 drifted")
    summary = _mapping(
        json.loads(summary_path.read_text(encoding="utf-8")),
        "CFE deficit summary",
    )
    expected = {
        "schema": _PROFILE_SCHEMA,
        "hours": 8784,
        "dc_demand_mw": demand,
        "hourly_cfe_target": float(metadata.get("hourly_cfe_target")),
        "formula": CFE_DEFICIT_FORMULA,
        "parameter_status": CFE_DEFICIT_PARAMETER_STATUS,
        "security_certified": False,
        "procurement_or_delivery_claimed": False,
        "source": {
            "repository": RTS_GMLC_REPOSITORY,
            "release": RTS_GMLC_RELEASE,
            "commit": RTS_GMLC_COMMIT,
            "manifest_sha256": RTS_GMLC_MANIFEST_SHA256,
        },
    }
    if any(summary.get(key) != value for key, value in expected.items()):
        raise ValueError("CFE deficit summary contract drifted")
    values = profile.values
    if summary.get("green_call_mw") != {
        "minimum": min(values),
        "maximum": max(values),
        "mean": sum(values) / len(values),
    }:
        raise ValueError("CFE deficit summary statistics drifted")
    return generator, summary


def _correct_provenance(provenance: dict, summary: dict) -> dict:
    corrected = copy.deepcopy(provenance)
    corrected["sources"]["green_semantics"] = (
        "rts_gmlc_renewable_scarcity_derived_benchmark"
    )
    corrected["normalization"]["green"] = {
        "mode": "absolute_mw_recovered_from_green_call_fraction",
        "external_peak": 1.0,
        "scale_equals_dc_demand_mw": True,
        "hourly_cfe_target": summary["hourly_cfe_target"],
        "formula": summary["formula"],
    }
    corrected["green_call_source_mode"] = "rts_gmlc_renewable_scarcity_absolute_mw"
    corrected["trace_pairing"] = (
        "independent_marginal_windows_between_google_stress_and_rts_gmlc_cfe"
    )
    return corrected


def run(config_path: Path) -> dict[str, object]:
    config_bytes = config_path.read_bytes()
    config = _mapping(yaml.safe_load(config_bytes), "config")
    _, cfe_summary = _validate_cfe_source(config)
    output = _mapping(config.get("output"), "output")
    output_dir = _path(output.get("directory"), "output.directory")

    with tempfile.TemporaryDirectory(prefix="rq2-cfe-source-ablation-") as temp:
        temp_root = Path(temp)
        delegated_config = copy.deepcopy(config)
        delegated_config["output"] = {"directory": str(temp_root / "legacy")}
        delegated_path = temp_root / "config.yaml"
        delegated_path.write_text(
            yaml.safe_dump(delegated_config, sort_keys=False),
            encoding="utf-8",
        )
        summary = legacy_runner.run(delegated_path)
        generated = temporal_runner._generated_temporal_scenarios(
            config.get("generator")
        )
        corrected_provenance = _correct_provenance(generated.provenance, cfe_summary)
        holdout = [
            temporal_runner._scenario_to_raw(scenario)
            for scenario in generated.holdout_scenarios
        ]
        training = [
            temporal_runner._scenario_to_raw(scenario)
            for scenario in generated.training_scenarios
        ]
        summary["shared_holdout_sha256"] = legacy_runner._canonical_sha256(holdout)
        summary["generated_draw_sha256"] = legacy_runner._canonical_sha256(
            {
                "training": training,
                "holdout": holdout,
                "provenance": corrected_provenance,
            }
        )
        for arm in ("generated", "reduced"):
            summary["arm_results"][arm]["scenario_source_provenance"]["generator"] = (
                corrected_provenance
            )
        summary["config_sha256"] = hashlib.sha256(config_bytes).hexdigest()
        summary["effective_config"] = config
        summary["output_directory"] = str(output_dir)
        summary["adapter"] = {
            "schema": "rq2_h2_temporal_cfe_source_adapter_v1",
            "implementation_sha256": _sha256(Path(__file__)),
            "legacy_runner_sha256": _sha256(Path(legacy_runner.__file__)),
            "temporal_runner_sha256": _sha256(Path(temporal_runner.__file__)),
            "profile_sha256": _sha256(
                _path(
                    config["generator"]["green_workload_shape"]["path"],
                    "green profile",
                )
            ),
            "numerical_path_changed": False,
        }
        summary["certification_blockers"] = [
            "network_event_timing_is_a_trace_threshold_not_observed_outage",
            "google_stress_and_rts_gmlc_cfe_are_independent_benchmark_marginals",
            "cfe_attribution_is_proportional_system_mix_not_procurement_or_delivery",
            "recovery_headroom_and_envelope_parameters_are_synthetic",
            "selected_n1_dc_not_full_n1_or_ac_security",
        ]
        summary["interpretation"] = (
            "temporal_h2_with_rts_gmlc_renewable_scarcity_cfe_calls"
        )
        summary = json.loads(
            json.dumps(summary, ensure_ascii=False, allow_nan=False, sort_keys=True)
        )

        with (temp_root / "legacy" / "arms.csv").open(
            encoding="utf-8", newline=""
        ) as handle:
            arm_rows = list(csv.DictReader(handle))
        with (temp_root / "legacy" / "leaves.csv").open(
            encoding="utf-8", newline=""
        ) as handle:
            leaf_rows = list(csv.DictReader(handle))
        legacy_runner._publish(
            output_dir,
            arm_rows=arm_rows,
            leaf_rows=leaf_rows,
            leaf_fields=("arm", *temporal_runner._LEAF_FIELDS),
            summary=summary,
        )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/rq2_h2_temporal_cfe_source_ablation_rts24_v1.yaml"),
    )
    args = parser.parse_args()
    summary = run(args.config)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not summary["gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
