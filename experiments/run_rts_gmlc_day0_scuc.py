"""Run the native RTS-GMLC selected-N-1 day-0 DC-SCUC benchmark."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import tempfile
from dataclasses import asdict, replace
from datetime import timezone
from pathlib import Path
from typing import Any, Iterable, Mapping

import yaml

from experiments.process_google_power_workload_day0 import _publish_directory
from src.evaluation import (
    ChronologicalFlexibilityEnvelope,
    EvidenceSource,
    RecoveryParameters,
    load_business_chronology_csv,
    load_incident_chronology_csv,
)
from src.grid import (
    RTS_GMLC_MANIFEST_SHA256,
    build_chronological_dispatch_request,
    load_rts_gmlc_chronological_data,
    validate_rts_gmlc_source_identity,
    validate_chronological_dispatch,
    verify_sha256_manifest,
)
from src.grid.rts_gmlc_scuc import solve_rts_gmlc_scuc

INCIDENT_FIELDS = (
    "event_id",
    "start_timestamp",
    "end_timestamp",
    "kind",
    "element_id",
    "frequency_semantics",
    "frequency_value",
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _format_value(value: object) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, float):
        return f"{value:.9f}".rstrip("0").rstrip(".") or "0"
    if value is None:
        return ""
    return str(value)


def _write_csv(
    path: Path,
    fields: tuple[str, ...],
    rows: Iterable[Mapping[str, object]],
) -> None:
    with path.open("w", encoding="utf-8", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: _format_value(row[field]) for field in fields})


def _stable_json(value: object) -> object:
    if isinstance(value, float):
        return round(value, 9)
    if isinstance(value, dict):
        return {str(key): _stable_json(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_stable_json(item) for item in value]
    return value


def _read_config(config_path: Path) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    benchmark = config["benchmark"]
    benchmark_windows = {
        "rts_gmlc_google_day0_first6h_selected_n1_dc_scuc_v1": (
            6,
            "first_six_continuous_hours_of_day0_fixed_replay",
        ),
        "rts_gmlc_google_day0_full24h_selected_n1_dc_scuc_v1": (
            24,
            "complete_day0_24_continuous_hours_fixed_replay",
        ),
    }
    try:
        horizon_hours, source_window = benchmark_windows[benchmark["id"]]
    except (KeyError, TypeError) as error:
        raise ValueError(
            "RTS-GMLC day-0 benchmark evidence contract drifted"
        ) from error
    expected_benchmark = {
        "id": benchmark["id"],
        "artifact_schema": "rts_gmlc_selected_n1_dc_scuc_artifacts_v1",
        "evidence_status": "derived_benchmark",
        "result_evidence_ceiling": (
            "public_benchmark_selected_n_minus_one_dc_mechanism_only"
        ),
        "chronological_dispatch_request_built": True,
        "chronological_grid_dispatch_coupled": True,
        "security_certified": False,
        "formal_vma_published": False,
    }
    if benchmark != expected_benchmark:
        raise ValueError("RTS-GMLC day-0 benchmark evidence contract drifted")

    model = config["model"]
    expected_model = {
        "horizon_hours": horizon_hours,
        "time_step_hours": 1.0,
        "source_window": source_window,
        "dc_bus": 108,
        "dc_connected_capacity_mw": 250.0,
        "contract_call_limit_mw": 0.0,
        "network_losses": "zero_loss_dc_approximation",
        "disabled_unit_types": ["CSP", "STORAGE", "SYNC_COND"],
        "initial_state_status": (
            "optimization_derived_free_boundary_not_observed_chronology"
        ),
        "production_cost_scope": (
            "published_three_segment_heat_rate_cold_start_for_all_starts"
        ),
        "reserve_scope": "regional_spin_up_only_no_regulation_or_flex_reserve",
        "dispatch_scope": "day_ahead_not_real_time_sced",
        "commitment_security_coupling": (
            "exact_state_constraint_generation_then_fixed_commitment_" "all_state_sced"
        ),
        "selected_n_minus_one_commitment_cooptimized": True,
    }
    if model != expected_model:
        raise ValueError("RTS-GMLC day-0 model scope drifted")

    security = config["security"]
    expected_security = {
        "selection_rule": (
            "max_loaded_nonislanding_intra_area_branch_per_area_plus_"
            "max_loaded_interarea_branch_plus_largest_committable_generator_per_area"
        ),
        "branch_immediate": "fixed_dispatch_short_term_rating",
        "branch_sustained": "hourly_ramp_corrective_continuous_rating",
        "generator_sustained": "hourly_ramp_corrective_continuous_rating",
        "solution_method": "fixed_base_dispatch_state_constraint_generation",
        "full_n_minus_one": False,
        "ac_security": False,
        "security_state_enumeration_is_event_frequency": False,
    }
    if security != expected_security:
        raise ValueError("RTS-GMLC selected-N-1 security scope drifted")

    grid = config["grid_source"]
    validate_rts_gmlc_source_identity(grid)
    if grid.get("manifest_sha256") != RTS_GMLC_MANIFEST_SHA256:
        raise ValueError("RTS-GMLC source manifest identity drifted")
    return config


def _load_business(config: dict[str, Any]):
    source = config["business_input"]
    business_path = Path(source["business_path"])
    recovery_path = Path(source["recovery_path"])
    summary_path = Path(source["summary_path"])
    for path, digest, label in (
        (business_path, source["business_sha256"], "business chronology"),
        (recovery_path, source["recovery_sha256"], "recovery parameters"),
        (summary_path, source["summary_sha256"], "business summary"),
    ):
        if _sha256(path) != digest:
            raise ValueError(f"RTS-GMLC day-0 {label} SHA-256 drifted")
    source_summary = json.loads(summary_path.read_text(encoding="utf-8"))
    required_source_status = {
        "benchmark_id": "m6_google_power_workload_day0_no_flex_250mw_v1",
        "evidence_status": "derived_benchmark",
        "absolute_power_mw_available": False,
        "flexibility_observed": False,
        "full_m6_model_input_ready": False,
        "chronological_grid_dispatch_coupled": False,
        "security_certified": False,
    }
    if any(
        source_summary.get(key) != value
        for key, value in required_source_status.items()
    ):
        raise ValueError("Paired Google day-0 evidence status drifted")
    recovery_payload = json.loads(recovery_path.read_text(encoding="utf-8"))
    if recovery_payload != {
        "maximum_recovery_power_mw": 0.0,
        "recovery_efficiency": 1.0,
        "schema": "m6_recovery_parameters_v1",
    }:
        raise ValueError("Day-0 neutral recovery parameters drifted")
    recovery = RecoveryParameters(
        maximum_recovery_power_mw=0.0,
        recovery_efficiency=1.0,
        source=EvidenceSource(
            dataset_id="neutral_no_recoverable_load_baseline_v1",
            source_kind="derived_benchmark",
            citation="neutral no-recoverable-load benchmark",
            version="v1",
            sha256=source["recovery_sha256"],
        ),
        source_artifact_path=recovery_path,
    )
    return load_business_chronology_csv(
        business_path,
        time_step_hours=1.0,
        workload_source=EvidenceSource(
            dataset_id="m6_google_power_workload_day0_no_flex_250mw_v1",
            source_kind="derived_benchmark",
            citation="Google PowerData day-0 plus the locked 250 MW project mapping",
            version="v1",
            sha256=source["business_sha256"],
        ),
        recovery=recovery,
    )


def _zero_flexibility_envelope(periods: tuple[str, ...]):
    unique_periods = tuple(dict.fromkeys(periods))
    return ChronologicalFlexibilityEnvelope(
        time_step_hours=1.0,
        maximum_event_duration_hours=1.0,
        minimum_recovery_hours=0.0,
        maximum_events_by_period={period: 0 for period in unique_periods},
        maximum_curtailment_energy_mwh_by_period={
            period: 0.0 for period in unique_periods
        },
        maximum_recovery_debt_mwh=0.0,
        maximum_recovery_power_mw=0.0,
        minimum_event_power_mw=1.0,
        response_time_hours=1.0,
        curtailment_ramp_mw_per_hour=1.0,
        recovery_efficiency=1.0,
        terminal_debt_limit_mwh_by_period={period: 0.0 for period in unique_periods},
        parameter_status=(
            "neutral_no_flexibility_interface_parameters_not_empirical_contract"
        ),
    )


def _build_request(data, business, incidents, model_config: dict[str, Any]):
    hours = int(model_config["horizon_hours"])
    if len(business.points) != hours:
        raise ValueError("Business chronology does not match the configured horizon")
    points = data.hourly_points[:hours]
    for grid_point, business_point in zip(points, business.points):
        if (
            grid_point.timestamp.replace(tzinfo=timezone.utc)
            != business_point.timestamp
        ):
            raise ValueError("RTS-GMLC and business day-0 clocks do not align")
    generator_uids = tuple(generator.uid for generator in data.generators)
    availability = {
        generator.uid: bool(generator.enabled) for generator in data.generators
    }
    initial_commitment = {uid: False for uid in generator_uids}
    initial_generation = {uid: 0.0 for uid in generator_uids}
    initial_duration = {
        generator.uid: max(
            24.0,
            float(generator.minimum_down_time_hours),
            float(generator.minimum_up_time_hours),
        )
        for generator in data.generators
    }
    periods = tuple(point.period for point in business.points)
    return build_chronological_dispatch_request(
        business,
        incidents,
        system_demand_by_bus_mw=tuple(point.demand_by_bus_mw for point in points),
        generator_availability=tuple(dict(availability) for _ in points),
        dc_bus=int(model_config["dc_bus"]),
        contract_call_limit_mw=tuple(
            float(model_config["contract_call_limit_mw"]) for _ in points
        ),
        connected_capacity_mw=tuple(
            float(model_config["dc_connected_capacity_mw"]) for _ in points
        ),
        flexibility_envelope=_zero_flexibility_envelope(periods),
        flexibility_boundary_state_status="clean_boundary_with_zero_carry_in",
        completed_periods=frozenset(),
        initial_commitment=initial_commitment,
        initial_generation_mw=initial_generation,
        initial_time_in_state_hours=initial_duration,
        require_terminal_event_inactive=True,
    )


def _state_loading(state, flows, branch_by_uid):
    maximum = 0.0
    maximum_violation = 0.0
    for uid, flow in flows.items():
        branch = branch_by_uid[uid]
        rating = (
            branch.short_term_rating_mw
            if state.branch_rating == "short_term"
            else branch.continuous_rating_mw
        )
        maximum = max(maximum, abs(float(flow)) / float(rating))
        maximum_violation = max(maximum_violation, abs(float(flow)) - float(rating))
    return maximum, max(maximum_violation, 0.0)


def _artifact_rows(data, solved):
    request = solved.dispatch_request
    result = solved.dispatch_result
    points = data.hourly_points[: len(request.timestamps)]
    generator_by_uid = {generator.uid: generator for generator in data.generators}
    branch_by_uid = {branch.uid: branch for branch in data.branches}
    state_by_id = {state.state_id: state for state in solved.critical_selection.states}
    initial_rows = [
        {
            "generator_uid": uid,
            "commitment": solved.initial_state.commitment[uid],
            "generation_mw": solved.initial_state.generation_mw[uid],
            "time_in_state_hours": solved.initial_state.time_in_state_hours[uid],
            "source_scope": solved.initial_state.source_scope,
        }
        for uid in sorted(generator_by_uid)
    ]
    generator_rows = []
    hourly_rows = []
    branch_rows = []
    security_rows = []
    security_generator_rows = []
    security_branch_rows = []
    previous_commitment = solved.initial_state.commitment
    for index, (timestamp, point) in enumerate(zip(request.timestamps, points)):
        generation = result.generation_mw[index]
        commitment = result.commitment[index]
        reserve = solved.reserve_up_mw[index]
        normal_flows = solved.normal_branch_flows_mw[index]
        native_grid_demand = sum(request.system_demand_by_bus_mw[index].values())
        data_center_power = result.dc_power_mw[index]
        total_demand = native_grid_demand + data_center_power
        total_generation = sum(generation.values())
        network_losses = result.network_losses_mw[index]
        max_loading, _ = _state_loading(
            state_by_id["normal"], normal_flows, branch_by_uid
        )
        hourly_rows.append(
            {
                "timestamp": timestamp.isoformat(),
                "native_grid_demand_mw": native_grid_demand,
                "data_center_requested_mw": request.dc_requested_mw[index],
                "data_center_flexible_demand_mw": (
                    request.dc_flexible_demand_mw[index]
                ),
                "data_center_recoverable_flexible_mw": (
                    request.dc_recoverable_flexible_mw[index]
                ),
                "data_center_physical_maximum_mw": (
                    request.dc_physical_maximum_mw[index]
                ),
                "data_center_connected_capacity_mw": (
                    request.dc_connected_capacity_mw[index]
                ),
                "data_center_call_limit_mw": request.dc_call_limit_mw[index],
                "data_center_recovery_headroom_mw": (
                    request.recovery_headroom_mw[index]
                ),
                "data_center_grid_call_mw": result.grid_call_mw[index],
                "data_center_recovery_power_mw": result.recovery_power_mw[index],
                "data_center_power_mw": data_center_power,
                "total_demand_mw": total_demand,
                "network_losses_mw": network_losses,
                "total_generation_mw": total_generation,
                "generation_balance_residual_mw": (
                    total_generation - total_demand - network_losses
                ),
                "committed_thermal_units": sum(
                    commitment[uid]
                    for uid, generator in generator_by_uid.items()
                    if generator.dispatch_mode == "committable"
                ),
                "spin_requirement_mw": sum(
                    point.spin_up_requirement_by_area_mw.values()
                ),
                "spin_provided_mw": sum(reserve.values()),
                "maximum_normal_branch_loading_fraction": max_loading,
                "hvdc_dc1_flow_mw": solved.normal_dc_flows_mw[index].get("DC1", 0.0),
                "commitment_feasible": result.commitment_feasible_by_step[index],
                "ramp_feasible": result.ramp_feasible_by_step[index],
                "reserve_feasible": result.reserve_feasible_by_step[index],
                "normal_secure": result.normal_secure_by_step[index],
                "selected_contingencies_secure": (
                    result.contingency_secure_by_step[index]
                ),
            }
        )
        for uid in sorted(generator_by_uid):
            generator = generator_by_uid[uid]
            generator_rows.append(
                {
                    "timestamp": timestamp.isoformat(),
                    "generator_uid": uid,
                    "bus": generator.bus,
                    "category": generator.category,
                    "dispatch_mode": generator.dispatch_mode,
                    "commitment": commitment[uid],
                    "startup": commitment[uid] and not previous_commitment[uid],
                    "shutdown": previous_commitment[uid] and not commitment[uid],
                    "generation_mw": generation[uid],
                    "minimum_mw": point.generator_min_mw[uid],
                    "maximum_mw": point.generator_max_mw[uid],
                    "spin_up_mw": reserve.get(uid, 0.0),
                }
            )
        for uid in sorted(branch_by_uid):
            branch = branch_by_uid[uid]
            flow = normal_flows[uid]
            branch_rows.append(
                {
                    "timestamp": timestamp.isoformat(),
                    "branch_uid": uid,
                    "from_bus": branch.from_bus,
                    "to_bus": branch.to_bus,
                    "flow_mw": flow,
                    "continuous_rating_mw": branch.continuous_rating_mw,
                    "loading_fraction": abs(flow) / branch.continuous_rating_mw,
                }
            )
        for state in solved.critical_selection.states:
            state_id = state.state_id
            if state_id == "normal":
                state_generation = generation
                state_flows = normal_flows
            else:
                state_generation = solved.security_generation_mw[state_id][index]
                state_flows = solved.security_branch_flows_mw[state_id][index]
            loading, violation = _state_loading(state, state_flows, branch_by_uid)
            outaged_value = 0.0
            if state.kind == "branch":
                outaged_value = abs(state_flows[state.element_uid])
            elif state.kind == "generator":
                outaged_value = abs(state_generation[state.element_uid])
            security_rows.append(
                {
                    "timestamp": timestamp.isoformat(),
                    "state_id": state_id,
                    "kind": state.kind,
                    "element_uid": state.element_uid,
                    "response_mode": state.response_mode,
                    "branch_rating": state.branch_rating,
                    "total_generation_mw": sum(state_generation.values()),
                    "maximum_branch_loading_fraction": loading,
                    "maximum_branch_rating_violation_mw": violation,
                    "outaged_element_output_mw": outaged_value,
                }
            )
            if state_id != "normal":
                for uid in sorted(generator_by_uid):
                    security_generator_rows.append(
                        {
                            "timestamp": timestamp.isoformat(),
                            "state_id": state_id,
                            "generator_uid": uid,
                            "generation_mw": state_generation[uid],
                        }
                    )
                for uid in sorted(branch_by_uid):
                    branch = branch_by_uid[uid]
                    rating = (
                        branch.short_term_rating_mw
                        if state.branch_rating == "short_term"
                        else branch.continuous_rating_mw
                    )
                    security_branch_rows.append(
                        {
                            "timestamp": timestamp.isoformat(),
                            "state_id": state_id,
                            "branch_uid": uid,
                            "flow_mw": state_flows[uid],
                            "rating_mw": rating,
                            "loading_fraction": abs(state_flows[uid]) / rating,
                        }
                    )
        previous_commitment = commitment
    return {
        "initial_state.csv": initial_rows,
        "hourly_dispatch.csv": hourly_rows,
        "generator_dispatch.csv": generator_rows,
        "normal_branch_flows.csv": branch_rows,
        "security_audit.csv": security_rows,
        "security_generator_dispatch.csv": security_generator_rows,
        "security_branch_flows.csv": security_branch_rows,
    }


_CSV_FIELDS = {
    "initial_state.csv": (
        "generator_uid",
        "commitment",
        "generation_mw",
        "time_in_state_hours",
        "source_scope",
    ),
    "hourly_dispatch.csv": (
        "timestamp",
        "native_grid_demand_mw",
        "data_center_requested_mw",
        "data_center_flexible_demand_mw",
        "data_center_recoverable_flexible_mw",
        "data_center_physical_maximum_mw",
        "data_center_connected_capacity_mw",
        "data_center_call_limit_mw",
        "data_center_recovery_headroom_mw",
        "data_center_grid_call_mw",
        "data_center_recovery_power_mw",
        "data_center_power_mw",
        "total_demand_mw",
        "network_losses_mw",
        "total_generation_mw",
        "generation_balance_residual_mw",
        "committed_thermal_units",
        "spin_requirement_mw",
        "spin_provided_mw",
        "maximum_normal_branch_loading_fraction",
        "hvdc_dc1_flow_mw",
        "commitment_feasible",
        "ramp_feasible",
        "reserve_feasible",
        "normal_secure",
        "selected_contingencies_secure",
    ),
    "generator_dispatch.csv": (
        "timestamp",
        "generator_uid",
        "bus",
        "category",
        "dispatch_mode",
        "commitment",
        "startup",
        "shutdown",
        "generation_mw",
        "minimum_mw",
        "maximum_mw",
        "spin_up_mw",
    ),
    "normal_branch_flows.csv": (
        "timestamp",
        "branch_uid",
        "from_bus",
        "to_bus",
        "flow_mw",
        "continuous_rating_mw",
        "loading_fraction",
    ),
    "security_audit.csv": (
        "timestamp",
        "state_id",
        "kind",
        "element_uid",
        "response_mode",
        "branch_rating",
        "total_generation_mw",
        "maximum_branch_loading_fraction",
        "maximum_branch_rating_violation_mw",
        "outaged_element_output_mw",
    ),
    "security_generator_dispatch.csv": (
        "timestamp",
        "state_id",
        "generator_uid",
        "generation_mw",
    ),
    "security_branch_flows.csv": (
        "timestamp",
        "state_id",
        "branch_uid",
        "flow_mw",
        "rating_mw",
        "loading_fraction",
    ),
}


def run(
    config_path: Path,
    *,
    output_directory: Path | None = None,
) -> dict[str, object]:
    config = _read_config(config_path)
    grid = config["grid_source"]
    root = Path(grid["path"])
    manifest_path = root / "SHA256SUMS"
    if _sha256(manifest_path) != grid["manifest_sha256"]:
        raise ValueError("RTS-GMLC source manifest SHA-256 drifted")
    if not verify_sha256_manifest(root):
        raise ValueError("RTS-GMLC source manifest validation failed")
    data = load_rts_gmlc_chronological_data(root, base_mva=float(grid["base_mva"]))
    if (len(data.buses), len(data.generators), len(data.branches)) != (73, 158, 120):
        raise ValueError("RTS-GMLC native topology counts drifted")
    full_business = _load_business(config)
    hours = int(config["model"]["horizon_hours"])
    if len(full_business.points) < hours:
        raise ValueError("Business chronology is shorter than the configured window")
    business = replace(full_business, points=full_business.points[:hours])

    output_root = output_directory or Path(config["output"]["directory"])
    output_root.parent.mkdir(parents=True, exist_ok=True)
    prefix = f".{output_root.name}.processing-"
    with tempfile.TemporaryDirectory(dir=output_root.parent, prefix=prefix) as temp:
        staging = Path(temp)
        incident_path = staging / "incident_chronology.csv"
        _write_csv(incident_path, INCIDENT_FIELDS, ())
        incident_sha = _sha256(incident_path)
        incident_source = EvidenceSource(
            dataset_id="rts_gmlc_day0_empty_incident_window_v1",
            source_kind="synthetic_sensitivity",
            citation="empty benchmark incident window; no event frequency implied",
            version="v1",
            sha256=incident_sha,
        )
        incidents = load_incident_chronology_csv(
            incident_path,
            source=incident_source,
        )
        request_shell = _build_request(data, business, incidents, config["model"])
        solved = solve_rts_gmlc_scuc(
            data,
            request_shell,
            solver_name=str(config["solver"]["name"]),
            tee=bool(config["solver"]["tee"]),
            tolerance_mw=float(config["solver"]["tolerance_mw"]),
            solver_threads=int(config["solver"]["threads"]),
            mip_relative_gap=float(config["solver"]["mip_relative_gap"]),
        )
        validate_chronological_dispatch(
            solved.dispatch_request,
            solved.dispatch_result,
            tolerance_mw=float(config["solver"]["tolerance_mw"]),
        )
        selection = solved.critical_selection
        expected = config["expected"]
        if list(selection.branch_uids) != expected["critical_branch_uids"]:
            raise RuntimeError(
                f"Critical branch selection drifted: {list(selection.branch_uids)}"
            )
        if list(selection.generator_uids) != expected["critical_generator_uids"]:
            raise RuntimeError(
                f"Critical generator selection drifted: {list(selection.generator_uids)}"
            )
        if (
            list(selection.excluded_islanding_branch_uids)
            != expected["excluded_islanding_branch_uids"]
        ):
            raise RuntimeError("Excluded islanding branch set drifted")

        rows_by_file = _artifact_rows(data, solved)
        for name, rows in rows_by_file.items():
            _write_csv(staging / name, _CSV_FIELDS[name], rows)
        dispatch = solved.dispatch_result
        zero_flexibility_fields = (
            "data_center_flexible_demand_mw",
            "data_center_recoverable_flexible_mw",
            "data_center_call_limit_mw",
            "data_center_recovery_headroom_mw",
            "data_center_grid_call_mw",
            "data_center_recovery_power_mw",
        )
        all_flexibility_fields_zero = all(
            float(row[field]) == 0.0
            for row in rows_by_file["hourly_dispatch.csv"]
            for field in zero_flexibility_fields
        )
        summary = {
            "schema": config["benchmark"]["artifact_schema"],
            "benchmark_id": config["benchmark"]["id"],
            "evidence_status": config["benchmark"]["evidence_status"],
            "result_evidence_ceiling": config["benchmark"]["result_evidence_ceiling"],
            "grid_source_repository": grid["repository"],
            "grid_source_release": grid["release"],
            "grid_source_commit": grid["commit"],
            "grid_source_manifest_sha256": grid["manifest_sha256"],
            "business_chronology_sha256": config["business_input"]["business_sha256"],
            "business_recovery_parameters_sha256": config["business_input"][
                "recovery_sha256"
            ],
            "business_source_summary_sha256": config["business_input"][
                "summary_sha256"
            ],
            "empty_incident_chronology_sha256": incident_sha,
            "empty_incident_chronology_source": _stable_json(asdict(incident_source)),
            "hours": len(dispatch.timestamps),
            "source_business_hours": len(full_business.points),
            "time_step_hours": float(config["model"]["time_step_hours"]),
            "source_window": config["model"]["source_window"],
            "completed_periods": sorted(solved.dispatch_request.completed_periods),
            "artifact_row_counts": {
                **{name: len(rows) for name, rows in rows_by_file.items()},
                "incident_chronology.csv": len(incidents.incidents),
            },
            "buses": len(data.buses),
            "generators": len(data.generators),
            "ac_branches": len(data.branches),
            "dc_branches": len(data.dc_branches),
            "first_timestamp": dispatch.timestamps[0].isoformat(),
            "last_timestamp": dispatch.timestamps[-1].isoformat(),
            "minimum_data_center_demand_mw": min(dispatch.dc_power_mw),
            "maximum_data_center_demand_mw": max(dispatch.dc_power_mw),
            "critical_branch_uids": list(selection.branch_uids),
            "critical_generator_uids": list(selection.generator_uids),
            "excluded_islanding_branch_uids": list(
                selection.excluded_islanding_branch_uids
            ),
            "security_states_per_hour_including_normal": len(selection.states),
            "contingency_states_per_hour": len(selection.states) - 1,
            "dispatch_scope": solved.dispatch_scope,
            "security_scope": solved.security_scope,
            "initial_state_status": solved.initial_state.source_scope,
            "prescreen_audit": _stable_json(asdict(solved.prescreen_audit)),
            "scuc_audit": _stable_json(asdict(solved.scuc_audit)),
            "fixed_commitment_ed_audit": _stable_json(asdict(solved.sced_audit)),
            "constraint_generation_audit": _stable_json(
                asdict(solved.constraint_generation_audit)
            ),
            "residual_audit": _stable_json(asdict(solved.residual_audit)),
            "all_flexibility_fields_zero": all_flexibility_fields_zero,
            "incident_chronology_is_empty": not incidents.incidents,
            "security_state_enumeration_is_event_frequency": config["security"][
                "security_state_enumeration_is_event_frequency"
            ],
            "csp_storage_and_sync_condenser_active_power_disabled": True,
            "real_time_sced": config["model"]["dispatch_scope"]
            != "day_ahead_not_real_time_sced",
            "selected_n_minus_one_commitment_cooptimized": config["model"][
                "selected_n_minus_one_commitment_cooptimized"
            ],
            "solver_name": str(config["solver"]["name"]),
            "solver_tolerance_mw": float(config["solver"]["tolerance_mw"]),
            "configured_mip_relative_gap": float(config["solver"]["mip_relative_gap"]),
            "full_n_minus_one": config["security"]["full_n_minus_one"],
            "ac_security": config["security"]["ac_security"],
            "absolute_power_mw_available": False,
            "flexibility_observed": False,
            "recovery_parameters_observed": False,
            "contract_semantics_available": False,
            "full_m6_model_input_ready": False,
            "chronological_dispatch_request_built": config["benchmark"][
                "chronological_dispatch_request_built"
            ],
            "chronological_grid_dispatch_coupled": config["benchmark"][
                "chronological_grid_dispatch_coupled"
            ],
            "security_certified": config["benchmark"]["security_certified"],
            "formal_vma_published": config["benchmark"]["formal_vma_published"],
        }
        summary_path = staging / "summary.json"
        summary_path.write_bytes(
            (json.dumps(_stable_json(summary), indent=2, sort_keys=True) + "\n").encode(
                "utf-8"
            )
        )
        artifact_paths = {
            path.name: path
            for path in staging.iterdir()
            if path.is_file() and path.name != "SHA256SUMS"
        }
        observed_hashes = {
            name: _sha256(path) for name, path in sorted(artifact_paths.items())
        }
        if observed_hashes != expected["artifact_sha256"]:
            raise RuntimeError(
                "RTS-GMLC day-0 artifact hashes drifted: "
                + json.dumps(observed_hashes, sort_keys=True)
            )
        artifact_manifest = staging / "SHA256SUMS"
        artifact_manifest.write_bytes(
            "".join(
                f"{digest}  {name}\n"
                for name, digest in sorted(observed_hashes.items())
            ).encode("ascii")
        )
        observed_manifest_sha256 = _sha256(artifact_manifest)
        if observed_manifest_sha256 != expected["artifact_manifest_sha256"]:
            raise RuntimeError(
                "RTS-GMLC day-0 artifact manifest SHA-256 drifted: "
                + observed_manifest_sha256
            )
        _publish_directory(staging, output_root)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/rts_gmlc_google_day0_scuc.yaml"),
    )
    args = parser.parse_args()
    print(json.dumps(run(args.config), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
