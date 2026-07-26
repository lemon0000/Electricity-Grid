"""Record certified infeasible POIs and finalize mixed multi-POI outcomes."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml
from highspy import Highs
from pyomo.environ import TransformationFactory
from pyomo.opt import TerminationCondition

from experiments.process_google_power_workload_day0 import (
    _verify_manifest as _verify_output_manifest,
)
from experiments.run_rts_gmlc_day0_scuc import (
    _sha256,
    _stable_json,
    _write_csv,
)
from experiments.run_rts_gmlc_multi_poi_scan import (
    _build_scan_context,
    _candidate,
    _load_candidate_result,
    _output_root,
    _publish_payload,
    _request,
    _require_common_security,
    _require_preregistration,
    _select_representatives,
    _solver_kwargs,
    _write_empty_incidents,
    _write_json,
)
from src.grid import build_rts_gmlc_pre_registered_contingencies
from src.grid.rts_gmlc_scuc import (
    _build_context,
    _build_model,
    _solve,
    _validate_inputs,
)

_AMENDMENT = {
    "id": "rts_gmlc_multi_poi_outcome_handling_amendment_001",
    "schema": "rts_gmlc_multi_poi_outcome_amendment_v1",
    "parent_preregistration_id": (
        "rts_gmlc_google_day0_multi_poi_selected_n1_dc_scuc_v1"
    ),
    "parent_registration_contract_sha256": (
        "16d9edc57d965e802dd17106a3a0aa7a99ae93f0f493ba977d8490573ce3fb78"
    ),
    "parent_common_security_contract_sha256": (
        "7865c7544817acd2d0dd6a461766862af52f7175eb24f2c1466f52e70115aa87"
    ),
    "status": "repository_local_amendment_after_bus_208_infeasibility",
    "externally_timestamped": False,
}
_OBSERVED = {
    "feasible_candidate_buses": [108, 120],
    "failed_candidate_bus": 208,
    "failed_termination": "active_state_scuc_infeasible",
    "diagnostic_result": (
        "free_boundary_continuous_commitment_relaxation_infeasible_for_state_subset"
    ),
    "remaining_full_candidate_outcomes_unseen": [220, 308, 320],
}
_SCOPE = {
    "reason": "original_runner_only_serialized_feasible_candidate_results",
    "permitted_change": (
        "serialize_certified_model_infeasibility_and_finalize_mixed_outcomes"
    ),
    "forbidden_changes": [
        "candidate_set",
        "candidate_order",
        "common_security_states",
        "grid_or_business_inputs",
        "model_constraints",
        "solver_settings",
        "comparison_or_representative_rules",
        "candidate_substitution",
    ],
    "infeasibility_certificate_rule": (
        "first_infeasible_prefix_of_frozen_common_states_under_free_boundary_"
        "continuous_commitment_relaxation"
    ),
    "infeasible_candidate_counts_as_completed": True,
    "infeasible_candidate_is_excluded_from_feasible_cost_and_ac_representative_sets": (
        True
    ),
}


def _read_amendment_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    expected = {
        "amendment": _AMENDMENT,
        "observed_before_amendment": _OBSERVED,
        "scope": _SCOPE,
    }
    if not isinstance(config, dict) or set(config) != set(expected) | {"output"}:
        raise ValueError("Multi-POI outcome amendment schema drifted")
    for key, value in expected.items():
        if config.get(key) != value:
            raise ValueError(f"Multi-POI outcome amendment {key} drifted")
    if not isinstance(config["output"], dict) or set(config["output"]) != {"directory"}:
        raise ValueError("Multi-POI outcome amendment output drifted")
    return config


def _amendment_payload(
    amendment_path: Path,
    output_root: Path,
    ctx: Any,
) -> dict[str, Any]:
    preregistration = _require_preregistration(ctx, output_root)
    common = _require_common_security(ctx, output_root)
    if (
        preregistration["contract_sha256"]
        != _AMENDMENT["parent_registration_contract_sha256"]
    ):
        raise RuntimeError("Outcome amendment parent registration drifted")
    if (
        common["common_security_contract_sha256"]
        != _AMENDMENT["parent_common_security_contract_sha256"]
    ):
        raise RuntimeError("Outcome amendment parent common security drifted")
    observed_manifests = {}
    for dc_bus in _OBSERVED["feasible_candidate_buses"]:
        _load_candidate_result(ctx, output_root, int(dc_bus))
        observed_manifests[str(dc_bus)] = _sha256(
            output_root / "candidates" / f"bus_{dc_bus}" / "SHA256SUMS"
        )
    return {
        "schema": _AMENDMENT["schema"],
        "amendment_id": _AMENDMENT["id"],
        "status": _AMENDMENT["status"],
        "externally_timestamped": False,
        "amendment_config_sha256": _sha256(amendment_path),
        "amendment_implementation_sha256": _sha256(Path(__file__)),
        "parent_registration_contract_sha256": preregistration["contract_sha256"],
        "parent_preregistration_manifest_sha256": _sha256(
            output_root / "preregistration" / "SHA256SUMS"
        ),
        "parent_common_security_contract_sha256": common[
            "common_security_contract_sha256"
        ],
        "parent_common_security_manifest_sha256": _sha256(
            output_root / "common_security" / "SHA256SUMS"
        ),
        "observed_feasible_candidate_manifest_sha256": observed_manifests,
        "observed_before_amendment": _OBSERVED,
        "scope": _SCOPE,
    }


def prepare_amendment(
    amendment_path: Path,
    *,
    scan_config_path: Path,
    output_directory: Path | None = None,
) -> dict[str, Any]:
    _read_amendment_config(amendment_path)
    ctx = _build_scan_context(scan_config_path)
    output_root = _output_root(ctx, output_directory)
    payload = _amendment_payload(amendment_path, output_root, ctx)
    target = output_root / "amendments" / "001_infeasible_outcome_handling"
    if target.exists():
        observed = _load_json(target, "amendment.json")
        if observed != _stable_json(payload):
            raise RuntimeError("Published outcome amendment drifted")
        if (
            target / "amendment_config.yaml"
        ).read_bytes() != amendment_path.read_bytes():
            raise RuntimeError("Published outcome amendment config drifted")
        return observed

    def writer(staging: Path) -> None:
        (staging / "amendment_config.yaml").write_bytes(amendment_path.read_bytes())
        _write_json(staging / "amendment.json", payload)

    _publish_payload(target, writer)
    return _load_json(target, "amendment.json")


def _load_json(root: Path, name: str) -> dict[str, Any]:
    _verify_output_manifest(root)
    payload = json.loads((root / name).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Artifact {root / name} must be a JSON object")
    return payload


def _require_amendment(
    amendment_path: Path,
    output_root: Path,
    ctx: Any,
) -> dict[str, Any]:
    target = output_root / "amendments" / "001_infeasible_outcome_handling"
    observed = _load_json(target, "amendment.json")
    expected = _stable_json(_amendment_payload(amendment_path, output_root, ctx))
    if observed != expected:
        raise RuntimeError("Outcome amendment no longer matches its parent artifacts")
    if (target / "amendment_config.yaml").read_bytes() != amendment_path.read_bytes():
        raise RuntimeError("Outcome amendment config snapshot drifted")
    return observed


def _diagnostic_audit(audit: Any) -> dict[str, object]:
    payload = asdict(audit)
    for field in (
        "objective_usd",
        "lower_bound_usd",
        "upper_bound_usd",
        "absolute_gap_usd",
        "gap_tolerance_usd",
    ):
        payload.pop(field)
    return payload


def record_infeasible_candidate(
    amendment_path: Path,
    dc_bus: int,
    *,
    scan_config_path: Path,
    output_directory: Path | None = None,
) -> dict[str, Any]:
    _read_amendment_config(amendment_path)
    ctx = _build_scan_context(scan_config_path)
    output_root = _output_root(ctx, output_directory)
    amendment = _require_amendment(amendment_path, output_root, ctx)
    common = _require_common_security(ctx, output_root)
    candidate = _candidate(ctx, dc_bus)
    if (output_root / "candidates" / f"bus_{dc_bus}").exists():
        raise RuntimeError(f"POI {dc_bus} already has a feasible published result")
    target = output_root / "infeasible_candidates" / f"bus_{dc_bus}"
    if target.exists():
        return _load_infeasible_candidate(
            amendment_path,
            ctx,
            output_root,
            dc_bus,
        )

    security = common["common_security_contract"]
    selection = build_rts_gmlc_pre_registered_contingencies(
        ctx.data,
        branch_uids=tuple(security["branch_uids"]),
        generator_uids=tuple(security["generator_uids"]),
    )

    def writer(staging: Path) -> None:
        incidents = _write_empty_incidents(staging / "incident_chronology.csv")
        request = _request(ctx, dc_bus, incidents)
        tolerance = float(ctx.base_config["solver"]["tolerance_mw"])
        points = _validate_inputs(ctx.data, request, tolerance)
        solver_kwargs = _solver_kwargs(ctx)
        internal_solver_kwargs = {
            "solver_name": solver_kwargs["solver_name"],
            "tee": solver_kwargs["tee"],
            "tolerance": solver_kwargs["tolerance_mw"],
            "solver_threads": solver_kwargs["solver_threads"],
            "mip_relative_gap": solver_kwargs["mip_relative_gap"],
        }
        Highs.resetGlobalScheduler(True)
        prefix = [selection.states[0]]
        audits = []
        infeasible_state = None
        for state in selection.states[1:]:
            prefix.append(state)
            context = _build_context(ctx.data, request, points, tuple(prefix))
            model = _build_model(context, fixed_initial=None)
            TransformationFactory("core.relax_integer_vars").apply_to(model)
            audit = _solve(model, **internal_solver_kwargs)
            audits.append(
                {
                    "added_state_id": state.state_id,
                    "prefix_state_count": len(prefix),
                    "solver_audit": _diagnostic_audit(audit),
                }
            )
            if audit.accepted:
                continue
            if audit.termination_condition != str(TerminationCondition.infeasible):
                raise RuntimeError(
                    f"POI {dc_bus} diagnostic failed without infeasibility: "
                    f"{audit.termination_condition}"
                )
            infeasible_state = state
            break
        if infeasible_state is None:
            raise RuntimeError(
                f"POI {dc_bus} full continuous relaxation was not infeasible"
            )
        payload = {
            "schema": "rts_gmlc_multi_poi_infeasible_candidate_v1",
            "amendment_id": _AMENDMENT["id"],
            "amendment_implementation_sha256": amendment[
                "amendment_implementation_sha256"
            ],
            "parent_registration_contract_sha256": ctx.registration_contract_sha256,
            "parent_common_security_contract_sha256": common[
                "common_security_contract_sha256"
            ],
            "candidate": candidate,
            "outcome_status": "model_infeasible",
            "termination_class": (
                "free_boundary_continuous_commitment_relaxation_infeasible"
            ),
            "certificate_rule": _SCOPE["infeasibility_certificate_rule"],
            "infeasible_prefix_state_ids": [state.state_id for state in prefix],
            "first_infeasible_added_state_id": infeasible_state.state_id,
            "prefix_diagnostic_audits": audits,
            "certificate_implication": (
                "the_infeasible_lp_relaxation_is_a_superset_of_the_common_state_"
                "mixed_integer_model_so_the_candidate_mip_is_infeasible"
            ),
            "farkas_ray_exported": False,
            "fixed_initial_state_used": False,
            "commitment_integrality_relaxed": True,
            "all_other_common_model_constraints_retained": True,
            "candidate_substituted": False,
            "evidence_status": "derived_benchmark",
            "full_n_minus_one": False,
            "ac_security": False,
            "security_certified": False,
            "engineering_infeasibility_claimed": False,
        }
        _write_json(staging / "summary.json", payload)

    _publish_payload(target, writer)
    return _load_infeasible_candidate(
        amendment_path,
        ctx,
        output_root,
        dc_bus,
    )


def _load_infeasible_candidate(
    amendment_path: Path,
    ctx: Any,
    output_root: Path,
    dc_bus: int,
) -> dict[str, Any]:
    amendment = _require_amendment(amendment_path, output_root, ctx)
    root = output_root / "infeasible_candidates" / f"bus_{dc_bus}"
    summary = _load_json(root, "summary.json")
    if summary["candidate"] != _stable_json(_candidate(ctx, dc_bus)):
        raise RuntimeError(f"POI {dc_bus} infeasible outcome metadata drifted")
    if summary["amendment_id"] != _AMENDMENT["id"]:
        raise RuntimeError(f"POI {dc_bus} infeasible outcome amendment drifted")
    if (
        summary["amendment_implementation_sha256"]
        != amendment["amendment_implementation_sha256"]
    ):
        raise RuntimeError(f"POI {dc_bus} infeasible outcome implementation drifted")
    if summary["outcome_status"] != "model_infeasible":
        raise RuntimeError(f"POI {dc_bus} outcome is not model infeasible")
    audits = summary["prefix_diagnostic_audits"]
    if not audits or audits[-1]["solver_audit"]["termination_condition"] != str(
        TerminationCondition.infeasible
    ):
        raise RuntimeError(f"POI {dc_bus} lacks an infeasible LP termination")
    if any(not item["solver_audit"]["accepted"] for item in audits[:-1]):
        raise RuntimeError(f"POI {dc_bus} has an invalid diagnostic prefix")
    return summary


_OUTCOME_FIELDS = (
    "candidate_order",
    "candidate_id",
    "dc_bus",
    "bus_name",
    "area",
    "base_kv",
    "stratum",
    "legacy_seen_anchor",
    "outcome_status",
    "lower_bound_usd",
    "upper_bound_usd",
    "certified_absolute_gap_usd",
    "certified_relative_gap",
    "maximum_normal_branch_loading_fraction",
    "stress_metric",
    "first_infeasible_added_state_id",
    "outcome_manifest_sha256",
)


def finalize_mixed_outcomes(
    amendment_path: Path,
    *,
    scan_config_path: Path,
    output_directory: Path | None = None,
) -> dict[str, Any]:
    _read_amendment_config(amendment_path)
    ctx = _build_scan_context(scan_config_path)
    output_root = _output_root(ctx, output_directory)
    amendment = _require_amendment(amendment_path, output_root, ctx)
    common = _require_common_security(ctx, output_root)
    rows = []
    feasible_comparison_rows = []
    feasible_buses = []
    infeasible_buses = []
    for candidate in ctx.candidates:
        dc_bus = int(candidate["dc_bus"])
        feasible_root = output_root / "candidates" / f"bus_{dc_bus}"
        infeasible_root = output_root / "infeasible_candidates" / f"bus_{dc_bus}"
        if feasible_root.exists() and infeasible_root.exists():
            raise RuntimeError(f"POI {dc_bus} has conflicting outcome artifacts")
        if feasible_root.exists():
            result = _load_candidate_result(ctx, output_root, dc_bus)
            feasible_buses.append(dc_bus)
            row = {
                "candidate_order": candidate["candidate_order"],
                "candidate_id": candidate["candidate_id"],
                "dc_bus": dc_bus,
                "bus_name": candidate["bus_name"],
                "area": candidate["area"],
                "base_kv": candidate["base_kv"],
                "stratum": candidate["stratum"],
                "legacy_seen_anchor": candidate["legacy_seen_anchor"],
                "outcome_status": "feasible",
                "lower_bound_usd": result["common_active_master_lower_bound_usd"],
                "upper_bound_usd": result[
                    "fixed_commitment_all_common_state_ed_upper_bound_usd"
                ],
                "certified_absolute_gap_usd": result["certified_absolute_gap_usd"],
                "certified_relative_gap": result["certified_relative_gap"],
                "maximum_normal_branch_loading_fraction": result[
                    "maximum_normal_branch_loading_fraction"
                ],
                "stress_metric": result[
                    "maximum_common_selected_state_branch_loading_fraction"
                ],
                "first_infeasible_added_state_id": None,
                "outcome_manifest_sha256": _sha256(feasible_root / "SHA256SUMS"),
            }
            feasible_comparison_rows.append(row)
        elif infeasible_root.exists():
            result = _load_infeasible_candidate(
                amendment_path,
                ctx,
                output_root,
                dc_bus,
            )
            infeasible_buses.append(dc_bus)
            row = {
                "candidate_order": candidate["candidate_order"],
                "candidate_id": candidate["candidate_id"],
                "dc_bus": dc_bus,
                "bus_name": candidate["bus_name"],
                "area": candidate["area"],
                "base_kv": candidate["base_kv"],
                "stratum": candidate["stratum"],
                "legacy_seen_anchor": candidate["legacy_seen_anchor"],
                "outcome_status": "model_infeasible",
                "lower_bound_usd": None,
                "upper_bound_usd": None,
                "certified_absolute_gap_usd": None,
                "certified_relative_gap": None,
                "maximum_normal_branch_loading_fraction": None,
                "stress_metric": None,
                "first_infeasible_added_state_id": result[
                    "first_infeasible_added_state_id"
                ],
                "outcome_manifest_sha256": _sha256(infeasible_root / "SHA256SUMS"),
            }
        else:
            raise RuntimeError(f"POI {dc_bus} has no completed outcome")
        rows.append(row)
    if not feasible_comparison_rows:
        raise RuntimeError("No feasible POI remains for representative selection")
    representatives = _select_representatives(
        feasible_comparison_rows,
        tolerance_usd=float(
            ctx.config["comparison"]["certified_separation_tolerance_usd"]
        ),
        legacy_anchor_bus=int(ctx.config["preregistration"]["legacy_seen_anchor_bus"]),
    )
    summary = {
        "schema": "rts_gmlc_multi_poi_mixed_outcome_aggregate_v1",
        "amendment_id": _AMENDMENT["id"],
        "amendment_implementation_sha256": amendment["amendment_implementation_sha256"],
        "parent_registration_contract_sha256": ctx.registration_contract_sha256,
        "parent_common_security_contract_sha256": common[
            "common_security_contract_sha256"
        ],
        "candidate_count": len(rows),
        "all_candidates_completed": len(rows)
        == int(ctx.config["comparison"]["required_candidate_count"]),
        "feasible_candidate_bus_ids": feasible_buses,
        "model_infeasible_candidate_bus_ids": infeasible_buses,
        "representative_selection_among_feasible_candidates": representatives,
        "infeasible_candidates_excluded_from_cost_and_ac_representative_sets": True,
        "candidate_substitution_used": False,
        "evidence_status": "derived_benchmark",
        "full_n_minus_one": False,
        "ac_security": False,
        "security_certified": False,
        "formal_vma_published": False,
        "ac_review_status": (
            "pending_preregistered_rts_gmlc_benchmark_ac_replay_not_engineering_"
            "certification"
        ),
    }
    target = output_root / "aggregate"
    if target.exists():
        observed = _load_json(target, "summary.json")
        if observed != _stable_json(summary):
            raise RuntimeError("Published mixed-outcome aggregate drifted")
        return observed

    def writer(staging: Path) -> None:
        _write_csv(staging / "candidate_outcomes.csv", _OUTCOME_FIELDS, rows)
        _write_json(staging / "representatives.json", representatives)
        _write_json(staging / "summary.json", summary)

    _publish_payload(target, writer)
    return _load_json(target, "summary.json")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--amendment-config",
        type=Path,
        default=Path("configs/rts_gmlc_google_day0_multi_poi_outcome_amendment.yaml"),
    )
    parser.add_argument(
        "--scan-config",
        type=Path,
        default=Path("configs/rts_gmlc_google_day0_multi_poi_scan.yaml"),
    )
    parser.add_argument(
        "--stage",
        choices=("prepare-amendment", "record-infeasible", "finalize"),
        required=True,
    )
    parser.add_argument("--candidate-bus", type=int)
    args = parser.parse_args()
    if args.stage == "record-infeasible" and args.candidate_bus is None:
        parser.error("record-infeasible requires --candidate-bus")
    if args.stage != "record-infeasible" and args.candidate_bus is not None:
        parser.error("--candidate-bus is only valid for record-infeasible")

    if args.stage == "prepare-amendment":
        result = prepare_amendment(
            args.amendment_config,
            scan_config_path=args.scan_config,
        )
    elif args.stage == "record-infeasible":
        result = record_infeasible_candidate(
            args.amendment_config,
            int(args.candidate_bus),
            scan_config_path=args.scan_config,
        )
    else:
        result = finalize_mixed_outcomes(
            args.amendment_config,
            scan_config_path=args.scan_config,
        )
    print(json.dumps(_stable_json(result), allow_nan=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
