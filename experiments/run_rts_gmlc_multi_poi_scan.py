"""Run the pre-registered native RTS-GMLC multi-POI scan."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import json
import platform
import tempfile
from dataclasses import asdict, dataclass, replace
from pathlib import Path
from typing import Any, Mapping

import yaml

from experiments.process_google_power_workload_day0 import (
    _publish_directory,
    _verify_manifest as _verify_output_manifest,
)
from experiments.run_rts_gmlc_day0_scuc import (
    INCIDENT_FIELDS,
    _CSV_FIELDS,
    _artifact_rows,
    _build_request,
    _format_value,
    _load_business,
    _read_config as _read_base_config,
    _sha256,
    _stable_json,
    _write_csv,
)
from src.evaluation import EvidenceSource, load_incident_chronology_csv
from src.grid import (
    build_rts_gmlc_pre_registered_contingencies,
    load_rts_gmlc_chronological_data,
    prescreen_rts_gmlc_critical_contingencies,
    select_rts_gmlc_critical_contingencies,
    solve_rts_gmlc_scuc,
    validate_chronological_dispatch,
    verify_sha256_manifest,
)
from src.scenarios.common_input_signature import common_input_signature_sha256

_PREREGISTRATION = {
    "id": "rts_gmlc_google_day0_multi_poi_selected_n1_dc_scuc_v1",
    "schema": "rts_gmlc_multi_poi_preregistration_v1",
    "status": "repository_local_frozen_before_nonreference_candidate_prescreens",
    "externally_timestamped": False,
    "all_candidates_blind": False,
    "legacy_seen_anchor_bus": 108,
    "base_benchmark_config_path": ("configs/rts_gmlc_google_day0_full24h_scuc.yaml"),
    "base_benchmark_config_sha256": (
        "e0e2a5c193ba73dc94ebfe90f334874aa8d2ec9c32693e7964b357f67a8f4887"
    ),
}
_EVIDENCE = {
    "evidence_status": "derived_benchmark",
    "result_evidence_ceiling": (
        "public_benchmark_common_selected_n_minus_one_dc_mechanism_only"
    ),
    "full_n_minus_one": False,
    "ac_security": False,
    "security_certified": False,
    "formal_vma_published": False,
}
_CANDIDATE_DESIGN = {
    "eligibility_rule": "positive_load_pq_bus_at_138_or_230_kv",
    "topology_strength_metric": "sum_incident_ac_branch_continuous_rating_mw",
    "ordering_rule": "ascending_topology_strength_then_bus_uid",
    "selection_by_voltage": {
        138: "median_zero_based_floor",
        230: "maximum",
    },
    "candidate_order": [108, 120, 208, 220, 308, 320],
    "candidate_order_rule": "ascending_area_then_138_before_230_kv",
    "weak_stratum_label": "local_138kv_median_strength",
    "strong_stratum_label": "backbone_230kv_max_strength",
    "allowed_candidate_specific_fields": [
        "candidate_id",
        "dc_bus",
        "output_directory",
    ],
}
_SECURITY_PROTOCOL = {
    "prescreen_scope": "normal_state_24h_free_boundary_for_security_selection_only",
    "branch_selection_rule": (
        "max_loaded_nonislanding_intra_area_branch_per_area_plus_"
        "max_loaded_interarea_branch"
    ),
    "common_branch_rule": "sorted_union_of_all_candidate_prescreen_branch_uids",
    "generator_selection_rule": "largest_committable_generator_per_area",
    "common_state_rule": (
        "identical_union_branch_and_generator_states_for_every_candidate"
    ),
    "branch_immediate": "fixed_dispatch_short_term_rating",
    "branch_sustained": "hourly_ramp_corrective_continuous_rating",
    "generator_sustained": "hourly_ramp_corrective_continuous_rating",
    "excluded_islanding_policy": "exclude_and_report",
    "permit_post_prescreen_state_deletion": False,
    "prescreen_generates_comparison_ranking": False,
}
_COMPARISON = {
    "required_candidate_count": 6,
    "completion_policy": "all_candidates_required_no_replacement",
    "primary_metric": "fixed_commitment_all_common_state_ed_upper_bound_usd",
    "certified_overlap_rule": (
        "candidate_lower_bound_less_than_or_equal_to_minimum_upper_bound"
    ),
    "unique_minimum_rule": (
        "winner_upper_bound_strictly_below_every_other_lower_bound"
    ),
    "certified_separation_tolerance_usd": 1.0e-6,
    "ambiguous_primary_representative_rule": (
        "first_certified_overlap_candidate_in_frozen_order"
    ),
    "stress_metric": "maximum_common_selected_state_branch_loading_fraction",
    "stress_representative_rule": "maximum_stress_metric_then_frozen_order",
    "ac_representative_rules": [
        "certified_or_ambiguous_primary_cost_representative",
        "maximum_selected_state_stress_representative",
        "legacy_seen_anchor",
    ],
    "failure_policy": "stop_and_diagnose_no_candidate_substitution",
}
_EMPTY_INCIDENT_BYTES = (",".join(INCIDENT_FIELDS) + "\n").encode("utf-8")
_EMPTY_INCIDENT_SHA256 = hashlib.sha256(_EMPTY_INCIDENT_BYTES).hexdigest()
_IMPLEMENTATION_PATHS = (
    Path("experiments/run_rts_gmlc_multi_poi_scan.py"),
    Path("experiments/run_rts_gmlc_day0_scuc.py"),
    Path("src/evaluation/chronology_inputs.py"),
    Path("src/grid/chronological_dispatch.py"),
    Path("src/grid/rts_gmlc.py"),
    Path("src/grid/rts_gmlc_scuc.py"),
    Path("src/scenarios/common_input_signature.py"),
)


@dataclass(frozen=True)
class _ScanContext:
    config_path: Path
    config: dict[str, Any]
    base_config: dict[str, Any]
    data: Any
    business: Any
    candidates: tuple[dict[str, object], ...]
    scan_config_sha256: str
    registration_contract: dict[str, object]
    registration_contract_sha256: str


def _read_scan_config(config_path: Path) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    expected_blocks = {
        "preregistration": _PREREGISTRATION,
        "evidence": _EVIDENCE,
        "candidate_design": _CANDIDATE_DESIGN,
        "security_protocol": _SECURITY_PROTOCOL,
        "comparison": _COMPARISON,
    }
    if not isinstance(config, dict) or set(config) != set(expected_blocks) | {"output"}:
        raise ValueError("RTS-GMLC multi-POI preregistration schema drifted")
    for name, expected in expected_blocks.items():
        if config.get(name) != expected:
            raise ValueError(f"RTS-GMLC multi-POI {name} contract drifted")
    output = config["output"]
    if not isinstance(output, dict) or set(output) != {"directory"}:
        raise ValueError("RTS-GMLC multi-POI output contract drifted")

    base_path = Path(_PREREGISTRATION["base_benchmark_config_path"])
    if _sha256(base_path) != _PREREGISTRATION["base_benchmark_config_sha256"]:
        raise ValueError("RTS-GMLC full-24h base config SHA-256 drifted")
    base = _read_base_config(base_path)
    if base["model"]["horizon_hours"] != 24:
        raise ValueError("RTS-GMLC multi-POI scan requires the frozen 24h backend")
    return config


def _software_versions() -> dict[str, str]:
    versions = {
        "python": platform.python_version(),
        "platform": platform.platform(),
    }
    for package in ("highspy", "numpy", "pyomo", "pyyaml"):
        versions[package] = importlib.metadata.version(package)
    return versions


def _derive_candidate_metadata(
    data: Any,
    candidate_order: tuple[int, ...],
) -> tuple[dict[str, object], ...]:
    incident = {int(bus.uid): [] for bus in data.buses}
    for branch in data.branches:
        incident[int(branch.from_bus)].append(branch)
        incident[int(branch.to_bus)].append(branch)

    eligible = [
        bus
        for bus in data.buses
        if bus.bus_type == "PQ"
        and float(bus.static_load_mw) > 0.0
        and float(bus.base_kv) in {138.0, 230.0}
    ]
    selected = []
    for area in sorted({int(bus.area) for bus in eligible}):
        for base_kv in (138.0, 230.0):
            stratum = [
                bus
                for bus in eligible
                if int(bus.area) == area and float(bus.base_kv) == base_kv
            ]
            ranked = sorted(
                stratum,
                key=lambda bus: (
                    sum(
                        float(branch.continuous_rating_mw)
                        for branch in incident[int(bus.uid)]
                    ),
                    int(bus.uid),
                ),
            )
            if not ranked:
                raise ValueError(f"Area {area} has no eligible {base_kv:g} kV POI")
            selected.append(
                ranked[len(ranked) // 2] if base_kv == 138.0 else ranked[-1]
            )

    derived_order = tuple(int(bus.uid) for bus in selected)
    if derived_order != candidate_order:
        raise ValueError(
            "RTS-GMLC multi-POI candidate rule drifted: " + str(derived_order)
        )

    metadata = []
    for order, bus in enumerate(selected):
        branches = incident[int(bus.uid)]
        ratings = [float(branch.continuous_rating_mw) for branch in branches]
        colocated = tuple(
            sorted(
                generator.uid
                for generator in data.generators
                if int(generator.bus) == int(bus.uid)
            )
        )
        metadata.append(
            {
                "candidate_order": order,
                "candidate_id": f"poi_bus_{int(bus.uid)}",
                "dc_bus": int(bus.uid),
                "bus_name": str(bus.name),
                "area": int(bus.area),
                "base_kv": float(bus.base_kv),
                "bus_type": str(bus.bus_type),
                "static_load_mw": float(bus.static_load_mw),
                "incident_ac_branch_count": len(branches),
                "incident_continuous_rating_sum_mw": sum(ratings),
                "remaining_rating_after_largest_incident_branch_mw": (
                    sum(ratings) - max(ratings)
                ),
                "stratum": (
                    _CANDIDATE_DESIGN["weak_stratum_label"]
                    if float(bus.base_kv) == 138.0
                    else _CANDIDATE_DESIGN["strong_stratum_label"]
                ),
                "colocated_generator_uids": colocated,
                "legacy_seen_anchor": int(bus.uid)
                == int(_PREREGISTRATION["legacy_seen_anchor_bus"]),
            }
        )
    return tuple(metadata)


def _chronology_signature(data: Any, business: Any) -> str:
    points = data.hourly_points[:24]
    payload = {
        "timestamps": [point.timestamp.isoformat() for point in points],
        "native_demand_by_bus_mw": [point.demand_by_bus_mw for point in points],
        "generator_min_mw": [point.generator_min_mw for point in points],
        "generator_max_mw": [point.generator_max_mw for point in points],
        "spin_up_requirement_by_area_mw": [
            point.spin_up_requirement_by_area_mw for point in points
        ],
        "data_center_requested_mw": [
            point.requested_demand_mw for point in business.points
        ],
    }
    return common_input_signature_sha256(payload)


def _registration_contract(
    config: dict[str, Any],
    base: dict[str, Any],
    data: Any,
    business: Any,
    candidates: tuple[dict[str, object], ...],
    scan_config_sha256: str,
) -> dict[str, object]:
    common_model = dict(base["model"])
    common_model.pop("dc_bus")
    return {
        "schema": "rts_gmlc_multi_poi_common_inputs_v1",
        "scan_config_sha256": scan_config_sha256,
        "base_benchmark_config_sha256": _PREREGISTRATION[
            "base_benchmark_config_sha256"
        ],
        "grid_source": base["grid_source"],
        "business_input": base["business_input"],
        "common_model_excluding_dc_bus": common_model,
        "common_security_selection_protocol": config["security_protocol"],
        "solver": base["solver"],
        "candidate_design": config["candidate_design"],
        "candidate_metadata": candidates,
        "comparison": config["comparison"],
        "chronology_signature_sha256": _chronology_signature(data, business),
        "empty_incident_chronology_sha256": _EMPTY_INCIDENT_SHA256,
        "implementation_sha256": {
            path.as_posix(): _sha256(path) for path in _IMPLEMENTATION_PATHS
        },
        "software_versions": _software_versions(),
        "evidence": config["evidence"],
    }


def _build_scan_context(config_path: Path) -> _ScanContext:
    config = _read_scan_config(config_path)
    base_path = Path(_PREREGISTRATION["base_benchmark_config_path"])
    base = _read_base_config(base_path)
    grid = base["grid_source"]
    source_root = Path(grid["path"])
    if _sha256(source_root / "SHA256SUMS") != grid["manifest_sha256"]:
        raise ValueError("RTS-GMLC source manifest SHA-256 drifted")
    if not verify_sha256_manifest(source_root):
        raise ValueError("RTS-GMLC source manifest validation failed")
    data = load_rts_gmlc_chronological_data(
        source_root,
        base_mva=float(grid["base_mva"]),
    )
    full_business = _load_business(base)
    business = replace(full_business, points=full_business.points[:24])
    scan_config_sha256 = _sha256(config_path)
    candidates = _derive_candidate_metadata(
        data,
        tuple(config["candidate_design"]["candidate_order"]),
    )
    contract = _registration_contract(
        config,
        base,
        data,
        business,
        candidates,
        scan_config_sha256,
    )
    return _ScanContext(
        config_path=config_path,
        config=config,
        base_config=base,
        data=data,
        business=business,
        candidates=candidates,
        scan_config_sha256=scan_config_sha256,
        registration_contract=contract,
        registration_contract_sha256=common_input_signature_sha256(contract),
    )


def _output_root(ctx: _ScanContext, output_directory: Path | None) -> Path:
    return output_directory or Path(ctx.config["output"]["directory"])


def _write_json(path: Path, payload: object) -> None:
    path.write_bytes(
        (
            json.dumps(
                _stable_json(payload),
                allow_nan=False,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    )


def _write_manifest(root: Path) -> None:
    paths = sorted(
        path for path in root.rglob("*") if path.is_file() and path.name != "SHA256SUMS"
    )
    (root / "SHA256SUMS").write_bytes(
        "".join(
            f"{_sha256(path)}  {path.relative_to(root).as_posix()}\n" for path in paths
        ).encode("ascii")
    )


def _load_json_artifact(root: Path, name: str) -> dict[str, Any]:
    _verify_output_manifest(root)
    payload = json.loads((root / name).read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Artifact {root / name} must contain a JSON object")
    return payload


def _publish_payload(target: Path, writer) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    prefix = f".{target.name}.processing-"
    with tempfile.TemporaryDirectory(dir=target.parent, prefix=prefix) as temp:
        staging = Path(temp)
        writer(staging)
        _write_manifest(staging)
        _publish_directory(staging, target)


def prepare_preregistration(
    config_path: Path,
    *,
    output_directory: Path | None = None,
) -> dict[str, Any]:
    ctx = _build_scan_context(config_path)
    output_root = _output_root(ctx, output_directory)
    target = output_root / "preregistration"
    payload = {
        "schema": _PREREGISTRATION["schema"],
        "preregistration_id": _PREREGISTRATION["id"],
        "status": _PREREGISTRATION["status"],
        "externally_timestamped": False,
        "all_candidates_blind": False,
        "legacy_seen_anchor_bus": _PREREGISTRATION["legacy_seen_anchor_bus"],
        "contract": ctx.registration_contract,
        "contract_sha256": ctx.registration_contract_sha256,
    }
    if target.exists():
        observed = _load_json_artifact(target, "registration.json")
        if observed != _stable_json(payload):
            raise RuntimeError("Published multi-POI preregistration drifted")
        if (target / "scan_config.yaml").read_bytes() != config_path.read_bytes():
            raise RuntimeError("Published multi-POI config snapshot drifted")
        return observed
    if output_root.exists() and any(output_root.iterdir()):
        raise RuntimeError(
            "Cannot prepare a new preregistration beside existing scan artifacts"
        )

    def writer(staging: Path) -> None:
        (staging / "scan_config.yaml").write_bytes(config_path.read_bytes())
        _write_json(staging / "registration.json", payload)

    _publish_payload(target, writer)
    return _load_json_artifact(target, "registration.json")


def _require_preregistration(ctx: _ScanContext, output_root: Path) -> dict[str, Any]:
    target = output_root / "preregistration"
    expected = {
        "schema": _PREREGISTRATION["schema"],
        "preregistration_id": _PREREGISTRATION["id"],
        "status": _PREREGISTRATION["status"],
        "externally_timestamped": False,
        "all_candidates_blind": False,
        "legacy_seen_anchor_bus": _PREREGISTRATION["legacy_seen_anchor_bus"],
        "contract": ctx.registration_contract,
        "contract_sha256": ctx.registration_contract_sha256,
    }
    observed = _load_json_artifact(target, "registration.json")
    if observed != _stable_json(expected):
        raise RuntimeError("Multi-POI preregistration no longer matches live inputs")
    if (target / "scan_config.yaml").read_bytes() != ctx.config_path.read_bytes():
        raise RuntimeError(
            "Multi-POI preregistered config no longer matches live config"
        )
    return observed


def _candidate(ctx: _ScanContext, dc_bus: int) -> dict[str, object]:
    try:
        return next(item for item in ctx.candidates if item["dc_bus"] == dc_bus)
    except StopIteration as error:
        raise ValueError(
            f"Bus {dc_bus} is not a pre-registered POI candidate"
        ) from error


def _write_empty_incidents(path: Path):
    _write_csv(path, INCIDENT_FIELDS, ())
    if _sha256(path) != _EMPTY_INCIDENT_SHA256:
        raise RuntimeError("Empty incident chronology serialization drifted")
    return load_incident_chronology_csv(
        path,
        source=EvidenceSource(
            dataset_id="rts_gmlc_multi_poi_empty_incident_window_v1",
            source_kind="synthetic_sensitivity",
            citation="empty benchmark incident window; no event frequency implied",
            version="v1",
            sha256=_EMPTY_INCIDENT_SHA256,
        ),
    )


def _request(ctx: _ScanContext, dc_bus: int, incidents: Any):
    model = dict(ctx.base_config["model"])
    model["dc_bus"] = dc_bus
    return _build_request(ctx.data, ctx.business, incidents, model)


def _solver_kwargs(ctx: _ScanContext) -> dict[str, object]:
    solver = ctx.base_config["solver"]
    return {
        "solver_name": str(solver["name"]),
        "tee": bool(solver["tee"]),
        "tolerance_mw": float(solver["tolerance_mw"]),
        "solver_threads": int(solver["threads"]),
        "mip_relative_gap": float(solver["mip_relative_gap"]),
    }


def _prescreen_summary(ctx: _ScanContext, dc_bus: int, solved: Any) -> dict[str, Any]:
    candidate = _candidate(ctx, dc_bus)
    branch_by_uid = {branch.uid: branch for branch in ctx.data.branches}
    maximum_loading = max(
        abs(float(flow)) / float(branch_by_uid[uid].continuous_rating_mw)
        for hour in solved.normal_branch_flows_mw
        for uid, flow in hour.items()
    )
    audit = asdict(solved.solver_audit)
    for field in (
        "objective_usd",
        "lower_bound_usd",
        "upper_bound_usd",
        "absolute_gap_usd",
        "gap_tolerance_usd",
    ):
        audit.pop(field)
    selection = solved.critical_selection
    return {
        "schema": "rts_gmlc_multi_poi_prescreen_v1",
        "preregistration_id": _PREREGISTRATION["id"],
        "registration_contract_sha256": ctx.registration_contract_sha256,
        "candidate": candidate,
        "hours": 24,
        "purpose": "common_security_union_only_not_candidate_ranking",
        "economic_outcomes_published": False,
        "solver_acceptance_audit": audit,
        "initial_state_status": solved.initial_state.source_scope,
        "selected_branch_uids": selection.branch_uids,
        "selected_generator_uids": selection.generator_uids,
        "excluded_islanding_branch_uids": selection.excluded_islanding_branch_uids,
        "selected_state_ids": tuple(state.state_id for state in selection.states),
        "selection_scope": selection.selection_scope,
        "maximum_normal_loading_fraction": maximum_loading,
        "empty_incident_chronology_sha256": _EMPTY_INCIDENT_SHA256,
        "prescreen_generates_comparison_ranking": False,
    }


def run_prescreen(
    config_path: Path,
    dc_bus: int,
    *,
    output_directory: Path | None = None,
) -> dict[str, Any]:
    ctx = _build_scan_context(config_path)
    output_root = _output_root(ctx, output_directory)
    _require_preregistration(ctx, output_root)
    _candidate(ctx, dc_bus)
    target = output_root / "prescreen" / f"bus_{dc_bus}"
    if target.exists():
        return _load_prescreen(ctx, output_root, dc_bus)

    def writer(staging: Path) -> None:
        incident_path = staging / "incident_chronology.csv"
        incidents = _write_empty_incidents(incident_path)
        solved = prescreen_rts_gmlc_critical_contingencies(
            ctx.data,
            _request(ctx, dc_bus, incidents),
            **_solver_kwargs(ctx),
        )
        rows = []
        branch_by_uid = {branch.uid: branch for branch in ctx.data.branches}
        for timestamp, flows in zip(
            ctx.business.points,
            solved.normal_branch_flows_mw,
        ):
            for uid in sorted(flows):
                branch = branch_by_uid[uid]
                rows.append(
                    {
                        "timestamp": timestamp.timestamp.isoformat(),
                        "branch_uid": uid,
                        "from_bus": branch.from_bus,
                        "to_bus": branch.to_bus,
                        "flow_mw": flows[uid],
                        "continuous_rating_mw": branch.continuous_rating_mw,
                        "loading_fraction": (
                            abs(float(flows[uid])) / float(branch.continuous_rating_mw)
                        ),
                    }
                )
        _write_csv(
            staging / "normal_branch_flows.csv",
            _CSV_FIELDS["normal_branch_flows.csv"],
            rows,
        )
        _write_json(staging / "summary.json", _prescreen_summary(ctx, dc_bus, solved))

    _publish_payload(target, writer)
    return _load_json_artifact(target, "summary.json")


def _prescreen_summary_from_artifact_contract(
    ctx: _ScanContext,
    dc_bus: int,
    observed: Mapping[str, Any],
) -> dict[str, Any]:
    expected = dict(observed)
    expected["schema"] = "rts_gmlc_multi_poi_prescreen_v1"
    expected["candidate"] = _candidate(ctx, dc_bus)
    expected["preregistration_id"] = _PREREGISTRATION["id"]
    expected["registration_contract_sha256"] = ctx.registration_contract_sha256
    expected["hours"] = 24
    expected["purpose"] = "common_security_union_only_not_candidate_ranking"
    expected["economic_outcomes_published"] = False
    expected["initial_state_status"] = (
        "optimization_derived_free_boundary_not_observed_chronology"
    )
    expected["prescreen_generates_comparison_ranking"] = False
    expected["empty_incident_chronology_sha256"] = _EMPTY_INCIDENT_SHA256
    return expected


def _load_prescreen(
    ctx: _ScanContext, output_root: Path, dc_bus: int
) -> dict[str, Any]:
    root = output_root / "prescreen" / f"bus_{dc_bus}"
    summary = _load_json_artifact(root, "summary.json")
    if summary != _stable_json(
        _prescreen_summary_from_artifact_contract(ctx, dc_bus, summary)
    ):
        raise RuntimeError(f"POI {dc_bus} prescreen contract drifted")
    if not summary["solver_acceptance_audit"]["accepted"]:
        raise RuntimeError(f"POI {dc_bus} normal prescreen was not accepted")
    with (root / "normal_branch_flows.csv").open(
        "r", encoding="utf-8", newline=""
    ) as source:
        rows = list(csv.DictReader(source))
    branch_uids = {branch.uid for branch in ctx.data.branches}
    if len(rows) != 24 * len(branch_uids):
        raise RuntimeError(f"POI {dc_bus} prescreen flow row count drifted")
    flows_by_timestamp: dict[str, dict[str, float]] = {}
    for row in rows:
        timestamp = row["timestamp"]
        uid = row["branch_uid"]
        if uid not in branch_uids or uid in flows_by_timestamp.setdefault(
            timestamp, {}
        ):
            raise RuntimeError(f"POI {dc_bus} prescreen flow keys drifted")
        flows_by_timestamp[timestamp][uid] = float(row["flow_mw"])
    flows = tuple(flows_by_timestamp.values())
    if len(flows) != 24 or any(set(hour) != branch_uids for hour in flows):
        raise RuntimeError(f"POI {dc_bus} prescreen hourly flow coverage drifted")
    selection = select_rts_gmlc_critical_contingencies(ctx.data, flows)
    expected_selection = {
        "selected_branch_uids": list(selection.branch_uids),
        "selected_generator_uids": list(selection.generator_uids),
        "excluded_islanding_branch_uids": list(
            selection.excluded_islanding_branch_uids
        ),
        "selected_state_ids": [state.state_id for state in selection.states],
        "selection_scope": selection.selection_scope,
    }
    if any(summary[key] != value for key, value in expected_selection.items()):
        raise RuntimeError(f"POI {dc_bus} prescreen selection was not reproducible")
    branch_by_uid = {branch.uid: branch for branch in ctx.data.branches}
    maximum_loading = max(
        abs(flow) / float(branch_by_uid[uid].continuous_rating_mw)
        for hour in flows
        for uid, flow in hour.items()
    )
    if (
        abs(maximum_loading - float(summary["maximum_normal_loading_fraction"]))
        > 1.0e-8
    ):
        raise RuntimeError(f"POI {dc_bus} prescreen loading metric drifted")
    return summary


def _common_security_payload(
    ctx: _ScanContext,
    output_root: Path,
) -> dict[str, Any]:
    per_candidate = []
    union = set()
    generator_uids: tuple[str, ...] | None = None
    for candidate in ctx.candidates:
        dc_bus = int(candidate["dc_bus"])
        summary = _load_prescreen(ctx, output_root, dc_bus)
        branches = tuple(summary["selected_branch_uids"])
        generators = tuple(summary["selected_generator_uids"])
        union.update(branches)
        if generator_uids is None:
            generator_uids = generators
        elif generators != generator_uids:
            raise RuntimeError("Candidate prescreens selected different generator sets")
        per_candidate.append(
            {
                "dc_bus": dc_bus,
                "selected_branch_uids": branches,
                "selected_generator_uids": generators,
                "prescreen_manifest_sha256": _sha256(
                    output_root / "prescreen" / f"bus_{dc_bus}" / "SHA256SUMS"
                ),
            }
        )
    if generator_uids is None:
        raise RuntimeError("No candidate prescreens were available")
    branch_uids = tuple(sorted(union))
    selection = build_rts_gmlc_pre_registered_contingencies(
        ctx.data,
        branch_uids=branch_uids,
        generator_uids=generator_uids,
    )
    security_contract = {
        "branch_uids": branch_uids,
        "generator_uids": generator_uids,
        "excluded_islanding_branch_uids": selection.excluded_islanding_branch_uids,
        "state_ids": tuple(state.state_id for state in selection.states),
        "selection_scope": selection.selection_scope,
    }
    return {
        "schema": "rts_gmlc_multi_poi_common_security_v1",
        "preregistration_id": _PREREGISTRATION["id"],
        "registration_contract_sha256": ctx.registration_contract_sha256,
        "derivation_rule": _SECURITY_PROTOCOL["common_branch_rule"],
        "candidate_prescreens": per_candidate,
        "common_security_contract": security_contract,
        "common_security_contract_sha256": common_input_signature_sha256(
            security_contract
        ),
        "all_prescreen_selected_branches_retained": len(branch_uids)
        == len({uid for item in per_candidate for uid in item["selected_branch_uids"]}),
        "post_prescreen_state_deletion_permitted": False,
    }


def freeze_common_security(
    config_path: Path,
    *,
    output_directory: Path | None = None,
) -> dict[str, Any]:
    ctx = _build_scan_context(config_path)
    output_root = _output_root(ctx, output_directory)
    _require_preregistration(ctx, output_root)
    payload = _common_security_payload(ctx, output_root)
    target = output_root / "common_security"
    if target.exists():
        observed = _load_json_artifact(target, "summary.json")
        if observed != _stable_json(payload):
            raise RuntimeError("Published common security union drifted")
        return observed

    def writer(staging: Path) -> None:
        _write_json(staging / "summary.json", payload)

    _publish_payload(target, writer)
    return _load_json_artifact(target, "summary.json")


def _require_common_security(
    ctx: _ScanContext,
    output_root: Path,
) -> dict[str, Any]:
    observed = _load_json_artifact(output_root / "common_security", "summary.json")
    expected = _stable_json(_common_security_payload(ctx, output_root))
    if observed != expected:
        raise RuntimeError("Common security union no longer matches prescreens")
    return observed


def _candidate_summary(
    ctx: _ScanContext,
    output_root: Path,
    dc_bus: int,
    solved: Any,
    rows_by_file: Mapping[str, list[dict[str, object]]],
) -> dict[str, Any]:
    candidate = _candidate(ctx, dc_bus)
    common = _require_common_security(ctx, output_root)
    normal_loading = max(
        float(row["loading_fraction"])
        for row in rows_by_file["normal_branch_flows.csv"]
    )
    selected_loading = max(
        float(row["maximum_branch_loading_fraction"])
        for row in rows_by_file["security_audit.csv"]
    )
    constraint_generation = solved.constraint_generation_audit
    return {
        "schema": "rts_gmlc_multi_poi_candidate_result_v1",
        "preregistration_id": _PREREGISTRATION["id"],
        "registration_contract_sha256": ctx.registration_contract_sha256,
        "common_security_contract_sha256": common["common_security_contract_sha256"],
        "candidate": candidate,
        "hours": 24,
        "first_timestamp": solved.dispatch_result.timestamps[0].isoformat(),
        "last_timestamp": solved.dispatch_result.timestamps[-1].isoformat(),
        "critical_branch_uids": solved.critical_selection.branch_uids,
        "critical_generator_uids": solved.critical_selection.generator_uids,
        "excluded_islanding_branch_uids": (
            solved.critical_selection.excluded_islanding_branch_uids
        ),
        "security_state_ids": tuple(
            state.state_id for state in solved.critical_selection.states
        ),
        "security_selection_scope": solved.critical_selection.selection_scope,
        "prescreen_audit": asdict(solved.prescreen_audit),
        "scuc_audit": asdict(solved.scuc_audit),
        "fixed_commitment_ed_audit": asdict(solved.sced_audit),
        "constraint_generation_audit": asdict(constraint_generation),
        "residual_audit": asdict(solved.residual_audit),
        "fixed_commitment_all_common_state_ed_upper_bound_usd": (
            constraint_generation.full_feasible_objective_usd
        ),
        "common_active_master_lower_bound_usd": (
            constraint_generation.relaxed_mip_lower_bound_usd
        ),
        "certified_absolute_gap_usd": (
            constraint_generation.certified_absolute_gap_usd
        ),
        "certified_relative_gap": constraint_generation.certified_relative_gap,
        "maximum_normal_branch_loading_fraction": normal_loading,
        "maximum_common_selected_state_branch_loading_fraction": selected_loading,
        "artifact_row_counts": {
            **{name: len(rows) for name, rows in rows_by_file.items()},
            "incident_chronology.csv": 0,
        },
        "all_common_states_verified": (
            constraint_generation.verified_state_ids
            == tuple(state.state_id for state in solved.critical_selection.states)
        ),
        "evidence_status": _EVIDENCE["evidence_status"],
        "result_evidence_ceiling": _EVIDENCE["result_evidence_ceiling"],
        "full_n_minus_one": False,
        "ac_security": False,
        "security_certified": False,
        "formal_vma_published": False,
        "absolute_power_mw_available": False,
        "flexibility_observed": False,
        "recovery_parameters_observed": False,
        "initial_state_status": solved.initial_state.source_scope,
        "real_time_sced": False,
        "incident_chronology_is_empty": True,
        "security_state_enumeration_is_event_frequency": False,
    }


def run_candidate(
    config_path: Path,
    dc_bus: int,
    *,
    output_directory: Path | None = None,
) -> dict[str, Any]:
    ctx = _build_scan_context(config_path)
    output_root = _output_root(ctx, output_directory)
    _require_preregistration(ctx, output_root)
    common = _require_common_security(ctx, output_root)
    _candidate(ctx, dc_bus)
    target = output_root / "candidates" / f"bus_{dc_bus}"
    if target.exists():
        summary = _load_json_artifact(target, "summary.json")
        if summary["registration_contract_sha256"] != ctx.registration_contract_sha256:
            raise RuntimeError(f"Published POI {dc_bus} result registration drifted")
        if (
            summary["common_security_contract_sha256"]
            != common["common_security_contract_sha256"]
        ):
            raise RuntimeError(f"Published POI {dc_bus} common security drifted")
        if summary["candidate"] != _stable_json(_candidate(ctx, dc_bus)):
            raise RuntimeError(f"Published POI {dc_bus} metadata drifted")
        return summary

    security = common["common_security_contract"]

    def writer(staging: Path) -> None:
        incident_path = staging / "incident_chronology.csv"
        incidents = _write_empty_incidents(incident_path)
        solved = solve_rts_gmlc_scuc(
            ctx.data,
            _request(ctx, dc_bus, incidents),
            pre_registered_branch_uids=tuple(security["branch_uids"]),
            pre_registered_generator_uids=tuple(security["generator_uids"]),
            **_solver_kwargs(ctx),
        )
        validate_chronological_dispatch(
            solved.dispatch_request,
            solved.dispatch_result,
            tolerance_mw=float(ctx.base_config["solver"]["tolerance_mw"]),
        )
        expected_states = tuple(security["state_ids"])
        observed_states = tuple(
            state.state_id for state in solved.critical_selection.states
        )
        if observed_states != expected_states:
            raise RuntimeError("Candidate solve did not use the common security states")
        rows_by_file = _artifact_rows(ctx.data, solved)
        for name, rows in rows_by_file.items():
            _write_csv(staging / name, _CSV_FIELDS[name], rows)
        _write_json(
            staging / "summary.json",
            _candidate_summary(ctx, output_root, dc_bus, solved, rows_by_file),
        )

    _publish_payload(target, writer)
    return _load_json_artifact(target, "summary.json")


def _load_candidate_result(
    ctx: _ScanContext,
    output_root: Path,
    dc_bus: int,
) -> dict[str, Any]:
    root = output_root / "candidates" / f"bus_{dc_bus}"
    summary = _load_json_artifact(root, "summary.json")
    if summary["candidate"] != _stable_json(_candidate(ctx, dc_bus)):
        raise RuntimeError(f"POI {dc_bus} result metadata drifted")
    if summary["registration_contract_sha256"] != ctx.registration_contract_sha256:
        raise RuntimeError(f"POI {dc_bus} result registration drifted")
    if not summary["all_common_states_verified"]:
        raise RuntimeError(f"POI {dc_bus} did not verify every common state")
    if not summary["fixed_commitment_ed_audit"]["accepted"]:
        raise RuntimeError(f"POI {dc_bus} fixed-commitment ED was not accepted")
    tolerance = float(ctx.base_config["solver"]["tolerance_mw"])
    residual_maxima = [
        float(value)
        for key, value in summary["residual_audit"].items()
        if key.startswith("maximum_")
    ]
    if max(residual_maxima) > tolerance:
        raise RuntimeError(f"POI {dc_bus} residual audit exceeds tolerance")
    return summary


def _select_representatives(
    rows: list[dict[str, object]],
    *,
    tolerance_usd: float,
    legacy_anchor_bus: int,
) -> dict[str, object]:
    ordered = sorted(rows, key=lambda row: int(row["candidate_order"]))
    minimum = min(
        ordered,
        key=lambda row: (
            float(row["upper_bound_usd"]),
            int(row["candidate_order"]),
        ),
    )
    minimum_upper = float(minimum["upper_bound_usd"])
    overlap = [
        row
        for row in ordered
        if float(row["lower_bound_usd"]) <= minimum_upper + tolerance_usd
    ]
    unique = all(
        row is minimum or minimum_upper + tolerance_usd < float(row["lower_bound_usd"])
        for row in ordered
    )
    primary = minimum if unique else overlap[0]
    stress = max(
        ordered,
        key=lambda row: (
            float(row["stress_metric"]),
            -int(row["candidate_order"]),
        ),
    )
    representative_buses = []
    reasons = []
    for row, reason in (
        (
            primary,
            (
                "unique_certified_minimum"
                if unique
                else "first_certified_overlap_candidate_in_frozen_order"
            ),
        ),
        (stress, "maximum_common_selected_state_stress"),
        (
            next(row for row in ordered if int(row["dc_bus"]) == legacy_anchor_bus),
            "legacy_seen_anchor",
        ),
    ):
        bus = int(row["dc_bus"])
        if bus not in representative_buses:
            representative_buses.append(bus)
            reasons.append({"dc_bus": bus, "reason": reason})
    return {
        "numerical_minimum_upper_bound_bus": int(minimum["dc_bus"]),
        "minimum_upper_bound_usd": minimum_upper,
        "certified_unique_minimum": unique,
        "certified_overlap_bus_ids": [int(row["dc_bus"]) for row in overlap],
        "primary_cost_representative_bus": int(primary["dc_bus"]),
        "maximum_stress_representative_bus": int(stress["dc_bus"]),
        "ac_representative_bus_ids": representative_buses,
        "representative_reasons": reasons,
    }


_AGGREGATE_FIELDS = (
    "candidate_order",
    "candidate_id",
    "dc_bus",
    "bus_name",
    "area",
    "base_kv",
    "stratum",
    "legacy_seen_anchor",
    "colocated_generator_count",
    "lower_bound_usd",
    "upper_bound_usd",
    "certified_absolute_gap_usd",
    "certified_relative_gap",
    "maximum_normal_branch_loading_fraction",
    "stress_metric",
    "common_security_state_count",
    "final_active_state_count",
    "candidate_manifest_sha256",
)


def finalize_scan(
    config_path: Path,
    *,
    output_directory: Path | None = None,
) -> dict[str, Any]:
    ctx = _build_scan_context(config_path)
    output_root = _output_root(ctx, output_directory)
    _require_preregistration(ctx, output_root)
    common = _require_common_security(ctx, output_root)
    rows = []
    for candidate in ctx.candidates:
        dc_bus = int(candidate["dc_bus"])
        summary = _load_candidate_result(ctx, output_root, dc_bus)
        rows.append(
            {
                "candidate_order": candidate["candidate_order"],
                "candidate_id": candidate["candidate_id"],
                "dc_bus": dc_bus,
                "bus_name": candidate["bus_name"],
                "area": candidate["area"],
                "base_kv": candidate["base_kv"],
                "stratum": candidate["stratum"],
                "legacy_seen_anchor": candidate["legacy_seen_anchor"],
                "colocated_generator_count": len(candidate["colocated_generator_uids"]),
                "lower_bound_usd": summary["common_active_master_lower_bound_usd"],
                "upper_bound_usd": summary[
                    "fixed_commitment_all_common_state_ed_upper_bound_usd"
                ],
                "certified_absolute_gap_usd": summary["certified_absolute_gap_usd"],
                "certified_relative_gap": summary["certified_relative_gap"],
                "maximum_normal_branch_loading_fraction": summary[
                    "maximum_normal_branch_loading_fraction"
                ],
                "stress_metric": summary[
                    "maximum_common_selected_state_branch_loading_fraction"
                ],
                "common_security_state_count": len(summary["security_state_ids"]),
                "final_active_state_count": len(
                    summary["constraint_generation_audit"]["final_active_state_ids"]
                ),
                "candidate_manifest_sha256": _sha256(
                    output_root / "candidates" / f"bus_{dc_bus}" / "SHA256SUMS"
                ),
            }
        )
    representatives = _select_representatives(
        rows,
        tolerance_usd=float(
            ctx.config["comparison"]["certified_separation_tolerance_usd"]
        ),
        legacy_anchor_bus=int(_PREREGISTRATION["legacy_seen_anchor_bus"]),
    )
    summary = {
        "schema": "rts_gmlc_multi_poi_aggregate_v1",
        "preregistration_id": _PREREGISTRATION["id"],
        "registration_contract_sha256": ctx.registration_contract_sha256,
        "common_security_contract_sha256": common["common_security_contract_sha256"],
        "candidate_count": len(rows),
        "all_candidates_completed": len(rows)
        == int(ctx.config["comparison"]["required_candidate_count"]),
        "common_security_state_count": len(
            common["common_security_contract"]["state_ids"]
        ),
        "representative_selection": representatives,
        "evidence_status": _EVIDENCE["evidence_status"],
        "result_evidence_ceiling": _EVIDENCE["result_evidence_ceiling"],
        "full_n_minus_one": False,
        "ac_security": False,
        "security_certified": False,
        "formal_vma_published": False,
        "all_candidates_blind": False,
        "legacy_seen_anchor_bus": _PREREGISTRATION["legacy_seen_anchor_bus"],
        "ac_review_status": (
            "pending_preregistered_rts_gmlc_benchmark_ac_replay_not_engineering_"
            "certification"
        ),
    }
    target = output_root / "aggregate"
    if target.exists():
        observed = _load_json_artifact(target, "summary.json")
        if observed != _stable_json(summary):
            raise RuntimeError("Published multi-POI aggregate drifted")
        observed_representatives = json.loads(
            (target / "representatives.json").read_text(encoding="utf-8")
        )
        if observed_representatives != _stable_json(representatives):
            raise RuntimeError("Published representative selection drifted")
        with (target / "candidate_results.csv").open(
            "r", encoding="utf-8", newline=""
        ) as source:
            observed_rows = list(csv.DictReader(source))
        expected_rows = [
            {field: _format_value(row[field]) for field in _AGGREGATE_FIELDS}
            for row in rows
        ]
        if observed_rows != expected_rows:
            raise RuntimeError("Published multi-POI candidate table drifted")
        return observed

    def writer(staging: Path) -> None:
        _write_csv(staging / "candidate_results.csv", _AGGREGATE_FIELDS, rows)
        _write_json(staging / "representatives.json", representatives)
        _write_json(staging / "summary.json", summary)

    _publish_payload(target, writer)
    return _load_json_artifact(target, "summary.json")


def run_all(
    config_path: Path,
    *,
    output_directory: Path | None = None,
) -> dict[str, Any]:
    prepare_preregistration(config_path, output_directory=output_directory)
    for dc_bus in _CANDIDATE_DESIGN["candidate_order"]:
        run_prescreen(config_path, int(dc_bus), output_directory=output_directory)
    freeze_common_security(config_path, output_directory=output_directory)
    for dc_bus in _CANDIDATE_DESIGN["candidate_order"]:
        run_candidate(config_path, int(dc_bus), output_directory=output_directory)
    return finalize_scan(config_path, output_directory=output_directory)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/rts_gmlc_google_day0_multi_poi_scan.yaml"),
    )
    parser.add_argument(
        "--stage",
        choices=("prepare", "prescreen", "freeze-security", "scan", "finalize", "all"),
        default="all",
    )
    parser.add_argument("--candidate-bus", type=int)
    args = parser.parse_args()
    if args.candidate_bus is not None and args.stage not in {"prescreen", "scan"}:
        parser.error("--candidate-bus is only valid for prescreen or scan")

    if args.stage == "prepare":
        result = prepare_preregistration(args.config)
    elif args.stage == "prescreen":
        buses = (
            (args.candidate_bus,)
            if args.candidate_bus is not None
            else tuple(_CANDIDATE_DESIGN["candidate_order"])
        )
        result = {}
        for bus in buses:
            result[str(bus)] = run_prescreen(args.config, int(bus))
    elif args.stage == "freeze-security":
        result = freeze_common_security(args.config)
    elif args.stage == "scan":
        buses = (
            (args.candidate_bus,)
            if args.candidate_bus is not None
            else tuple(_CANDIDATE_DESIGN["candidate_order"])
        )
        result = {}
        for bus in buses:
            result[str(bus)] = run_candidate(args.config, int(bus))
    elif args.stage == "finalize":
        result = finalize_scan(args.config)
    else:
        result = run_all(args.config)
    print(json.dumps(_stable_json(result), allow_nan=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
