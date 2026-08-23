"""Run the manual/generated/reduced temporal H2 training-source ablation."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import shutil
import tempfile
from pathlib import Path

import yaml

from experiments import run_rq2_h2_temporal_holdout as temporal_runner

_ROOT = Path(__file__).resolve().parents[1]
_ARMS = ("manual", "generated", "reduced")
_ARM_FIELDS = (
    "arm",
    "network_method",
    "training_scenario_count",
    "holdout_scenario_count",
    "correct_committed_flexibility_mw",
    "b6_committed_flexibility_mw",
    "b6_extra_failure_probability",
    "b6_extra_expected_shortfall_mwh",
    "b6_extra_expected_terminal_debt_mwh",
    "h2_evaluated",
    "h2_b6_underdelivers_out_of_sample",
    "arm_gate_passed",
    "training_parameter_status",
    "holdout_parameter_status",
    "parameter_status",
    "security_certified",
)


def _mapping(raw: object, label: str) -> dict:
    if not isinstance(raw, dict):
        raise TypeError(f"{label} must be a mapping")
    return raw


def _path(raw: object, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"{label} must be a nonempty path")
    path = Path(raw)
    return path if path.is_absolute() else _ROOT / path


def _canonical_sha256(raw: object) -> str:
    payload = json.dumps(
        raw, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _write_csv(
    path: Path, rows: list[dict[str, object]], fields: tuple[str, ...]
) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="raise",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _publish(
    target: Path,
    *,
    arm_rows: list[dict[str, object]],
    leaf_rows: list[dict[str, object]],
    leaf_fields: tuple[str, ...],
    summary: dict[str, object],
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError(f"immutable result directory already exists: {target}")
    staging = Path(
        tempfile.mkdtemp(dir=target.parent, prefix=f".{target.name}.processing-")
    )
    try:
        _write_csv(staging / "arms.csv", arm_rows, _ARM_FIELDS)
        _write_csv(staging / "leaves.csv", leaf_rows, leaf_fields)
        (staging / "summary.json").write_text(
            json.dumps(
                summary,
                ensure_ascii=False,
                allow_nan=False,
                sort_keys=True,
            )
            + "\n",
            encoding="utf-8",
        )
        for filename, expected_rows in (
            ("arms.csv", len(arm_rows)),
            ("leaves.csv", len(leaf_rows)),
        ):
            with (staging / filename).open(
                encoding="utf-8", newline=""
            ) as handle:
                if len(list(csv.DictReader(handle))) != expected_rows:
                    raise RuntimeError(f"staged {filename} row count drifted")
        if json.loads(
            (staging / "summary.json").read_text(encoding="utf-8")
        ) != summary:
            raise RuntimeError("staged summary round-trip drifted")
        manifest = {
            filename: _sha256(staging / filename)
            for filename in ("arms.csv", "leaves.csv", "summary.json")
        }
        (staging / "SHA256SUMS.json").write_text(
            json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8"
        )
        if json.loads(
            (staging / "SHA256SUMS.json").read_text(encoding="utf-8")
        ) != manifest:
            raise RuntimeError("staged manifest round-trip drifted")
        if target.exists():
            raise FileExistsError(
                f"immutable result directory already exists: {target}"
            )
        staging.rename(target)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _arm_config(
    base: dict,
    *,
    arm: str,
    shared_holdout: list[dict[str, object]],
    shared_holdout_status: str,
    output_dir: Path,
) -> dict:
    config = copy.deepcopy(base)
    config.pop("arms", None)
    config.pop("manual_training_scenarios", None)
    config["scenario_source"] = arm
    if arm == "manual":
        config["training_scenarios"] = copy.deepcopy(
            base.get("manual_training_scenarios")
        )
        config["holdout_scenarios"] = copy.deepcopy(shared_holdout)
        config["holdout_parameter_status"] = shared_holdout_status
    config["output"] = {
        "leaves_path": str(output_dir / "leaves.csv"),
        "summary_path": str(output_dir / "summary.json"),
    }
    return config


def _source_robustness(
    *,
    methods: list[str],
    arms: list[str],
    arm_rows: list[dict[str, object]],
) -> dict[str, dict[str, object]]:
    robustness = {}
    for method in methods:
        comparable = [
            row
            for row in arm_rows
            if row["network_method"] == method and row["h2_evaluated"]
        ]
        all_evaluable = len(comparable) == len(arms)
        robustness[method] = {
            "evaluable_arm_count": len(comparable),
            "all_requested_arms_evaluable": all_evaluable,
            "h2_robust_across_sources": all_evaluable
            and all(
                row["h2_b6_underdelivers_out_of_sample"]
                for row in comparable
            ),
        }
    return robustness


def run(config_path: Path) -> dict[str, object]:
    config_bytes = config_path.read_bytes()
    config = _mapping(yaml.safe_load(config_bytes), "config")
    evaluation = _mapping(config.get("evaluation"), "evaluation")
    evaluation_id = evaluation.get("id")
    if not isinstance(evaluation_id, str) or not evaluation_id:
        raise ValueError("evaluation.id must be explicit")
    if evaluation.get("security_certified") is not False:
        raise ValueError("security_certified must remain false")
    if evaluation.get("formal_vma_published") is not False:
        raise ValueError("formal_vma_published must remain false")
    arms = config.get("arms")
    if (
        not isinstance(arms, list)
        or not arms
        or any(arm not in _ARMS for arm in arms)
        or len(arms) != len(set(arms))
    ):
        raise ValueError(
            "arms must be a nonempty unique subset of manual/generated/reduced"
        )

    generated = temporal_runner._generated_temporal_scenarios(
        config.get("generator")
    )
    shared_holdout = [
        temporal_runner._scenario_to_raw(scenario)
        for scenario in generated.holdout_scenarios
    ]
    shared_holdout_sha256 = _canonical_sha256(shared_holdout)
    generated_draw_sha256 = _canonical_sha256(
        {
            "training": [
                temporal_runner._scenario_to_raw(scenario)
                for scenario in generated.training_scenarios
            ],
            "holdout": shared_holdout,
            "provenance": generated.provenance,
        }
    )
    generator_provenance_sha256 = _canonical_sha256(generated.provenance)
    arm_rows = []
    leaf_rows = []
    arm_summaries = {}
    leaf_fields = ("arm", *temporal_runner._LEAF_FIELDS)
    gate_passed = True
    with tempfile.TemporaryDirectory(prefix="rq2-temporal-ablation-") as raw_tmp:
        temporary_root = Path(raw_tmp)
        for arm in arms:
            arm_dir = temporary_root / arm
            arm_config = _arm_config(
                config,
                arm=arm,
                shared_holdout=shared_holdout,
                shared_holdout_status=generated.parameter_status,
                output_dir=arm_dir,
            )
            arm_config_path = temporary_root / f"{arm}.yaml"
            arm_config_path.write_text(
                yaml.safe_dump(arm_config, sort_keys=False),
                encoding="utf-8",
            )
            arm_summary = temporal_runner.run(arm_config_path)
            if arm == "manual":
                observed_holdout = arm_config["holdout_scenarios"]
            else:
                observed = temporal_runner._generated_temporal_scenarios(
                    arm_config.get("generator")
                )
                observed_holdout = [
                    temporal_runner._scenario_to_raw(scenario)
                    for scenario in observed.holdout_scenarios
                ]
            if _canonical_sha256(observed_holdout) != shared_holdout_sha256:
                raise RuntimeError("shared holdout drifted across ablation arms")

            with (arm_dir / "leaves.csv").open(
                encoding="utf-8", newline=""
            ) as handle:
                for row in csv.DictReader(handle):
                    leaf_rows.append({"arm": arm, **row})
            source_provenance = arm_summary["scenario_source_provenance"]
            if arm != "manual" and _canonical_sha256(
                source_provenance["generator"]
            ) != generator_provenance_sha256:
                raise RuntimeError(
                    "generator provenance drifted across ablation arms"
                )
            training_count = (
                len(config.get("manual_training_scenarios", []))
                if arm == "manual"
                else len(generated.training_scenarios)
            )
            if arm == "reduced":
                training_count = len(
                    source_provenance["reduction"]["kept_names"]
                )
            for method, method_summary in arm_summary["methods"].items():
                arm_rows.append(
                    {
                        "arm": arm,
                        "network_method": method,
                        "training_scenario_count": training_count,
                        "holdout_scenario_count": len(shared_holdout),
                        "correct_committed_flexibility_mw": method_summary[
                            "correct"
                        ]["committed_flexibility_mw"],
                        "b6_committed_flexibility_mw": method_summary["b6"][
                            "committed_flexibility_mw"
                        ],
                        "b6_extra_failure_probability": method_summary[
                            "b6_extra_failure_probability"
                        ],
                        "b6_extra_expected_shortfall_mwh": method_summary[
                            "b6_extra_expected_shortfall_mwh"
                        ],
                        "b6_extra_expected_terminal_debt_mwh": method_summary[
                            "b6_extra_expected_terminal_debt_mwh"
                        ],
                        "h2_evaluated": method_summary["h2_evaluated"],
                        "h2_b6_underdelivers_out_of_sample": method_summary[
                            "h2_b6_underdelivers_out_of_sample"
                        ],
                        "arm_gate_passed": method_summary["gate_passed"],
                        "training_parameter_status": method_summary[
                            "training_source_parameter_status"
                        ],
                        "holdout_parameter_status": method_summary[
                            "holdout_source_parameter_status"
                        ],
                        "parameter_status": arm_summary["parameter_status"],
                        "security_certified": False,
                    }
                )
            arm_summaries[arm] = {
                "gate_passed": arm_summary["gate_passed"],
                "parameter_status": arm_summary["parameter_status"],
                "scenario_source_provenance": source_provenance,
                "methods": arm_summary["methods"],
            }
            gate_passed = gate_passed and bool(arm_summary["gate_passed"])

    robustness = _source_robustness(
        methods=config["network"]["methods"],
        arms=arms,
        arm_rows=arm_rows,
    )

    output = _mapping(config.get("output"), "output")
    output_dir = _path(output.get("directory"), "output.directory")
    summary = {
        "evaluation_id": evaluation_id,
        "arms": arms,
        "shared_holdout_scenario_count": len(shared_holdout),
        "shared_holdout_sha256": shared_holdout_sha256,
        "generated_draw_sha256": generated_draw_sha256,
        "arm_results": arm_summaries,
        "robustness_by_network_method": robustness,
        "gate_passed": gate_passed,
        "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "effective_config": config,
        "parameter_status": (
            f"{evaluation.get('parameter_status')}|temporal_training_source_"
            "ablation_shared_trace_derived_holdout_not_empirical"
        ),
        "security_certified": False,
        "formal_vma_published": False,
        "empirical_holdout_claimed": False,
        "touches_frozen_baselines": False,
        "interpretation": (
            "temporal_h2_robustness_to_manual_generated_and_reduced_training_"
            "sources_with_one_fixed_trace_derived_holdout"
        ),
        "certification_blockers": [
            "network_event_timing_is_a_trace_threshold_not_observed_outage",
            "trace_sources_are_independent_marginals_from_different_clusters",
            "recovery_headroom_and_envelope_parameters_are_synthetic",
            "selected_n1_dc_not_full_n1_or_ac_security",
        ],
        "output_directory": str(output_dir),
    }
    summary = json.loads(
        json.dumps(summary, ensure_ascii=False, allow_nan=False, sort_keys=True)
    )
    _publish(
        output_dir,
        arm_rows=arm_rows,
        leaf_rows=leaf_rows,
        leaf_fields=leaf_fields,
        summary=summary,
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/rq2_h2_temporal_source_ablation_rts24.yaml"),
    )
    args = parser.parse_args()
    summary = run(args.config)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    if not summary["gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
