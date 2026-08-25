"""Run the preregistered RQ2 three-region phase-map benchmark."""

from __future__ import annotations

import argparse
import csv
import hashlib
import importlib.metadata
import itertools
import json
import platform
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import yaml

from experiments.run_rq2_l5_economic_temporal_network import (
    _coefficients,
    _envelope,
    _integer_tuple,
    _mapping,
    _number,
    _validate_network_selection,
)
from src.evaluation.rq2_phase_regions import (
    PHASE_REGIONS,
    PhaseRegionInputs,
    classify_phase_region,
)
from src.evaluation.temporal_economic_holdout import (
    TemporalEconomicHoldoutInputs,
    TemporalPolicyPlan,
    execute_temporal_economic_holdout,
)
from src.grid import load_rts24
from src.grid.network_grid_need import (
    NETWORK_GRID_NEED_METHODS,
    NetworkGridNeedInputs,
    derive_network_grid_need,
)
from src.models.economic_temporal_stochastic import (
    TemporalEconomicInputs,
    TemporalEconomicScenario,
    solve_temporal_economic_stochastic,
)
from src.scenarios.rq2_phase_map import (
    PHASE_MAP_SCENARIO_STATUS,
    PhaseMapScenarioConfig,
    generate_phase_map_scenarios,
)
from src.scenarios.rts_gmlc_cfe_deficit import (
    load_rts_gmlc_cfe_deficit_profile,
)
from src.scenarios.trace_scenario_generator import (
    load_peak_normalized_shape_from_csv,
)

_ROOT = Path(__file__).resolve().parents[1]
_CELL_FIELDS = (
    "cell_id",
    "families",
    "poi_bus",
    "network_method",
    "hourly_cfe_target",
    "threshold_label",
    "network_activation_threshold",
    "business_recovery_headroom_mw",
    "max_flexibility_budget_mw",
    "seed",
    "training_network_activation_rate",
    "training_green_call_rate",
    "training_joint_overlap_rate",
    "holdout_network_activation_rate",
    "holdout_green_call_rate",
    "holdout_joint_overlap_rate",
    "mean_effective_recovery_headroom_mw",
    "grid_need_mw",
    "correct_training_feasible",
    "b6_training_feasible",
    "correct_training_termination_condition",
    "b6_training_termination_condition",
    "correct_training_proven_infeasible",
    "b6_training_proven_infeasible",
    "correct_committed_flexibility_mw",
    "b6_committed_flexibility_mw",
    "correct_failure_probability",
    "b6_failure_probability",
    "correct_expected_shortfall_mwh",
    "b6_expected_shortfall_mwh",
    "delta_failure_probability",
    "delta_expected_shortfall_mwh",
    "flexibility_underprovisioning_mw",
    "region",
    "region_reason",
    "scientific_region",
    "gate_passed",
    "security_certified",
)
_NETWORK_FIELDS = (
    "poi_bus",
    "network_method",
    "feasible",
    "proven_infeasible",
    "grid_need_mw",
    "critical_state",
    "direct_physical_dispatch_witness",
    "termination_condition",
    "failure_details_json",
    "security_certified",
)


@dataclass(frozen=True)
class _Cell:
    families: tuple[str, ...]
    poi_bus: int
    network_method: str
    hourly_cfe_target: float
    threshold_label: str
    network_activation_threshold: float
    business_recovery_headroom_mw: float
    max_flexibility_budget_mw: float
    seed: int

    @property
    def id(self) -> str:
        return (
            f"poi{self.poi_bus}_{self.network_method}_"
            f"a{self.hourly_cfe_target:.2f}_"
            f"{self.threshold_label}_"
            f"h{self.business_recovery_headroom_mw:g}_"
            f"b{self.max_flexibility_budget_mw:g}_s{self.seed}"
        )


def _path(raw: object, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"{label} must be a nonempty path")
    path = Path(raw)
    return path if path.is_absolute() else _ROOT / path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _canonical_sha256(raw: object) -> str:
    return hashlib.sha256(
        json.dumps(raw, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()
    ).hexdigest()


def _validate_preregistration(
    *,
    config_path: Path,
    config: dict,
    evaluation: dict,
) -> tuple[str | None, str]:
    enforce = evaluation.get("enforce_preregistration")
    if not isinstance(enforce, bool):
        raise TypeError("evaluation.enforce_preregistration must be boolean")
    if not enforce:
        status = str(evaluation.get("parameter_status", ""))
        if "test" not in status:
            raise ValueError(
                "preregistration may be disabled only for explicit test configs"
            )
        return None, "disabled_for_test_only"
    prereg_path = _path(
        evaluation.get("preregistration_path"),
        "evaluation.preregistration_path",
    )
    prereg = _mapping(yaml.safe_load(prereg_path.read_bytes()), "preregistration")
    if prereg.get("preregistration", {}).get("status") != (
        "frozen_before_full_phase_map_execution"
    ):
        raise ValueError("phase-map preregistration is not frozen")
    manifest_path = _path(
        evaluation.get("preregistration_manifest_path"),
        "evaluation.preregistration_manifest_path",
    )
    manifest = _mapping(
        json.loads(manifest_path.read_text(encoding="utf-8")),
        "preregistration_manifest",
    )
    for relative_path, expected_sha256 in manifest.items():
        observed_path = _ROOT / relative_path
        if _sha256(observed_path) != expected_sha256:
            raise ValueError(f"preregistration manifest drifted: {relative_path}")
    frozen = _mapping(prereg.get("frozen_inputs"), "frozen_inputs")
    dependencies = {
        "config_sha256": config_path,
        "runner_sha256": Path(__file__),
        "classifier_sha256": _ROOT / "src/evaluation/rq2_phase_regions.py",
        "scenario_builder_sha256": _ROOT / "src/scenarios/rq2_phase_map.py",
        "cfe_derivation_sha256": (_ROOT / "src/scenarios/rts_gmlc_cfe_deficit.py"),
        "temporal_holdout_sha256": (
            _ROOT / "src/evaluation/temporal_economic_holdout.py"
        ),
        "temporal_model_sha256": (_ROOT / "src/models/economic_temporal_stochastic.py"),
        "network_grid_need_sha256": (_ROOT / "src/grid/network_grid_need.py"),
        "temporal_runner_helpers_sha256": (
            _ROOT / "experiments/run_rq2_l5_economic_temporal_network.py"
        ),
        "trace_loader_sha256": (_ROOT / "src/scenarios/trace_scenario_generator.py"),
        "flexibility_envelope_sha256": (
            _ROOT / "src/evaluation/flexibility_envelope.py"
        ),
        "service_risk_sha256": _ROOT / "src/evaluation/service_risk.py",
        "rts24_sha256": _ROOT / "src/grid/rts24.py",
        "dc_opf_sha256": _ROOT / "src/grid/dc_opf.py",
        "scopf_sha256": _ROOT / "src/grid/scopf.py",
    }
    for key, path in dependencies.items():
        if frozen.get(key) != _sha256(path):
            raise ValueError(f"preregistered dependency drifted: {key}")
    if (
        frozen.get("cfe_profile_sha256") != config["sources"]["cfe"]["sha256"]
        or frozen.get("google_trace_sha256") != config["sources"]["grid"]["sha256"]
    ):
        raise ValueError("preregistered source hash drifted")
    software = _mapping(prereg.get("software"), "software")
    observed_versions = {
        "python": platform.python_version(),
        "numpy": importlib.metadata.version("numpy"),
        "pyomo": importlib.metadata.version("pyomo"),
        "highspy": importlib.metadata.version("highspy"),
        "pypower": importlib.metadata.version("pypower"),
        "pyyaml": importlib.metadata.version("pyyaml"),
    }
    if observed_versions != software:
        raise ValueError("preregistered software environment drifted")
    return _sha256(prereg_path), f"enforced_manifest={_sha256(manifest_path)}"


def _list(raw: object, label: str) -> list:
    if not isinstance(raw, list) or not raw:
        raise ValueError(f"{label} must be a nonempty list")
    return raw


def _thresholds(
    design: dict,
    *,
    grid_values: tuple[float, ...],
    split_fraction: float,
) -> dict[str, float]:
    block = _mapping(design.get("thresholds"), "design.thresholds")
    training = np.asarray(
        grid_values[: round(len(grid_values) * split_fraction)],
        dtype=float,
    )
    result = {}
    for label, raw in block.items():
        item = _mapping(raw, f"design.thresholds.{label}")
        quantile = _number(item.get("training_quantile"), f"{label}.quantile")
        expected = _number(item.get("value"), f"{label}.value")
        observed = float(np.quantile(training, quantile, method="linear"))
        if abs(observed - expected) > 1.0e-12:
            raise ValueError(f"training-only threshold {label} drifted")
        result[label] = expected
    return result


def _expand_cells(design: dict, thresholds: dict[str, float]) -> tuple[_Cell, ...]:
    cells: dict[tuple, set[str]] = {}
    families = _list(design.get("families"), "design.families")
    keys = (
        "poi_buses",
        "network_methods",
        "hourly_cfe_targets",
        "threshold_labels",
        "business_recovery_headroom_mw",
        "max_flexibility_budget_mw",
        "seeds",
    )
    for index, raw_family in enumerate(families):
        family = _mapping(raw_family, f"design.families[{index}]")
        name = family.get("name")
        if not isinstance(name, str) or not name:
            raise ValueError("phase-map family name must be explicit")
        axes = [_list(family.get(key), f"{name}.{key}") for key in keys]
        for values in itertools.product(*axes):
            (
                poi,
                method,
                alpha,
                threshold_label,
                headroom,
                budget,
                seed,
            ) = values
            if method not in NETWORK_GRID_NEED_METHODS:
                raise ValueError(f"unknown network method {method}")
            if threshold_label not in thresholds:
                raise ValueError(f"unknown threshold label {threshold_label}")
            key = (
                int(poi),
                str(method),
                float(alpha),
                str(threshold_label),
                float(headroom),
                float(budget),
                int(seed),
            )
            cells.setdefault(key, set()).add(name)
    return tuple(
        _Cell(
            families=tuple(sorted(families_for_cell)),
            poi_bus=key[0],
            network_method=key[1],
            hourly_cfe_target=key[2],
            threshold_label=key[3],
            network_activation_threshold=thresholds[key[3]],
            business_recovery_headroom_mw=key[4],
            max_flexibility_budget_mw=key[5],
            seed=key[6],
        )
        for key, families_for_cell in sorted(cells.items())
    )


def _economic_scenarios(
    scenarios,
    *,
    grid_need_mw: float,
) -> tuple[TemporalEconomicScenario, ...]:
    return tuple(
        TemporalEconomicScenario(
            name=scenario.name,
            probability=scenario.probability,
            periods=scenario.periods,
            grid_need_mw=tuple(
                grid_need_mw * active for active in scenario.network_call_active
            ),
            green_call_mw=scenario.green_call_mw,
            connected_demand_mw=scenario.connected_demand_mw,
            recovery_headroom_mw=scenario.recovery_headroom_mw,
            completed_periods=scenario.completed_periods,
            require_terminal_event_inactive=(scenario.require_terminal_event_inactive),
            boundary_state_status=scenario.boundary_state_status,
        )
        for scenario in scenarios
    )


def _planning_inputs(
    inputs: TemporalEconomicHoldoutInputs,
    *,
    joint: bool,
) -> TemporalEconomicInputs:
    return TemporalEconomicInputs(
        scenarios=inputs.training_scenarios,
        envelope=inputs.envelope,
        coefficients=inputs.coefficients,
        provisioning_cost_per_mw=inputs.provisioning_cost_per_mw,
        max_flexibility_budget_mw=inputs.max_flexibility_budget_mw,
        lambda_risk=inputs.lambda_risk,
        beta=inputs.beta,
        enforce_joint_budget=joint,
        fixed_flexibility_mw=None,
        parameter_status=inputs.parameter_status,
    )


def _effective_overlap_rate(raw_rate: float, grid_need_mw: float) -> float:
    return raw_rate if grid_need_mw > 1.0e-9 else 0.0


def _network_failure_details(result) -> dict[str, object]:
    details: dict[str, object] = {}
    if result.base_termination_condition not in {
        "optimal",
        "globallyOptimal",
        "locallyOptimal",
    }:
        details["base"] = {
            "termination_condition": result.base_termination_condition,
            "solver_status": result.base_solver_status,
        }
    for name, state in result.state_results.items():
        if not state.feasible:
            details[name] = {
                "termination_condition": state.termination_condition,
                "solver_status": state.solver_status,
                "proven_infeasible": state.proven_infeasible,
            }
    return details


def _network_termination_summary(result) -> str:
    details = _network_failure_details(result)
    if not details:
        return "optimal" if result.feasible else "network_failure_unclassified"
    return "|".join(
        f"{name}:{detail['termination_condition']}"
        for name, detail in sorted(details.items())
    )


def _network_unresolved_row(_cell: _Cell, result) -> dict[str, object]:
    return {
        "cell_id": _cell.id,
        "families": "|".join(_cell.families),
        "poi_bus": _cell.poi_bus,
        "network_method": _cell.network_method,
        "hourly_cfe_target": _cell.hourly_cfe_target,
        "threshold_label": _cell.threshold_label,
        "network_activation_threshold": (_cell.network_activation_threshold),
        "business_recovery_headroom_mw": (_cell.business_recovery_headroom_mw),
        "max_flexibility_budget_mw": _cell.max_flexibility_budget_mw,
        "seed": _cell.seed,
        "training_network_activation_rate": None,
        "training_green_call_rate": None,
        "training_joint_overlap_rate": None,
        "holdout_network_activation_rate": None,
        "holdout_green_call_rate": None,
        "holdout_joint_overlap_rate": None,
        "mean_effective_recovery_headroom_mw": None,
        "grid_need_mw": result.grid_need_mw,
        "correct_training_feasible": None,
        "b6_training_feasible": None,
        "correct_training_termination_condition": None,
        "b6_training_termination_condition": None,
        "correct_training_proven_infeasible": None,
        "b6_training_proven_infeasible": None,
        "correct_committed_flexibility_mw": None,
        "b6_committed_flexibility_mw": None,
        "correct_failure_probability": None,
        "b6_failure_probability": None,
        "correct_expected_shortfall_mwh": None,
        "b6_expected_shortfall_mwh": None,
        "delta_failure_probability": None,
        "delta_expected_shortfall_mwh": None,
        "flexibility_underprovisioning_mw": None,
        "region": "unresolved",
        "region_reason": (f"network_derivation_{_network_termination_summary(result)}"),
        "scientific_region": False,
        "gate_passed": False,
        "security_certified": False,
    }


def _write_csv(path: Path, rows: list[dict], fields: tuple[str, ...]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=fields,
            extrasaction="raise",
            lineterminator="\n",
        )
        writer.writeheader()
        writer.writerows(rows)


def _publish(
    target: Path,
    *,
    cells: list[dict],
    networks: list[dict],
    summary: dict,
) -> None:
    if target.exists():
        raise FileExistsError(f"immutable result directory exists: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(dir=target.parent, prefix=f".{target.name}.processing-")
    )
    try:
        _write_csv(staging / "cells.csv", cells, _CELL_FIELDS)
        _write_csv(staging / "network_points.csv", networks, _NETWORK_FIELDS)
        (staging / "summary.json").write_text(
            json.dumps(summary, sort_keys=True, allow_nan=False) + "\n",
            encoding="utf-8",
        )
        manifest = {
            name: _sha256(staging / name)
            for name in ("cells.csv", "network_points.csv", "summary.json")
        }
        (staging / "SHA256SUMS.json").write_text(
            json.dumps(manifest, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        staging.rename(target)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def run(config_path: Path) -> dict[str, object]:
    config_bytes = config_path.read_bytes()
    config = _mapping(yaml.safe_load(config_bytes), "config")
    evaluation = _mapping(config.get("evaluation"), "evaluation")
    if evaluation.get("security_certified") is not False:
        raise ValueError("security_certified must remain false")
    if evaluation.get("formal_result") is not False:
        raise ValueError("formal_result must remain false for this benchmark")
    preregistration_sha256, preregistration_gate = _validate_preregistration(
        config_path=config_path,
        config=config,
        evaluation=evaluation,
    )

    source = _mapping(config.get("sources"), "sources")
    grid_source = _mapping(source.get("grid"), "sources.grid")
    split_fraction = _number(source.get("split_fraction"), "sources.split_fraction")
    grid_path = _path(grid_source.get("path"), "sources.grid.path")
    if _sha256(grid_path) != grid_source.get("sha256"):
        raise ValueError("grid source SHA-256 drifted")
    grid_shape = load_peak_normalized_shape_from_csv(
        grid_path,
        column=str(grid_source.get("column")),
        name="google_grid_stress",
        split_fraction=split_fraction,
        source=f"{grid_path}::sha256={_sha256(grid_path)}",
    )
    cfe_source = _mapping(source.get("cfe"), "sources.cfe")
    cfe_path = _path(cfe_source.get("path"), "sources.cfe.path")
    cfe_profile = load_rts_gmlc_cfe_deficit_profile(
        cfe_path,
        expected_sha256=str(cfe_source.get("sha256")),
        source=f"{cfe_path}::sha256={_sha256(cfe_path)}",
    )

    design = _mapping(config.get("design"), "design")
    thresholds = _thresholds(
        design,
        grid_values=grid_shape.values,
        split_fraction=split_fraction,
    )
    cells = _expand_cells(design, thresholds)
    if len(cells) != int(design.get("expected_unique_cell_count")):
        raise ValueError("expanded phase-map cell count drifted")

    network = _mapping(config.get("network"), "network")
    data = load_rts24()
    branch_indices = _integer_tuple(
        network.get("branch_indices"), "network.branch_indices"
    )
    generator_indices = _integer_tuple(
        network.get("generator_indices"), "network.generator_indices"
    )
    balancing_bus = int(network.get("balancing_bus"))
    sustained_rating = str(network.get("sustained_rating"))
    solver_name = str(config["model"]["solver_name"])
    for poi in {cell.poi_bus for cell in cells}:
        _validate_network_selection(
            data,
            poi_bus=poi,
            balancing_bus=balancing_bus,
            branch_indices=branch_indices,
            generator_indices=generator_indices,
            sustained_rating=sustained_rating,
        )

    network_cache = {}
    network_rows = []
    for poi, method in sorted({(cell.poi_bus, cell.network_method) for cell in cells}):
        result = derive_network_grid_need(
            NetworkGridNeedInputs(
                data=data,
                poi_bus=poi,
                balancing_bus=balancing_bus,
                system_load_multiplier=_number(
                    design.get("system_load_multiplier"),
                    "design.system_load_multiplier",
                ),
                data_center_demand_mw=_number(
                    design.get("data_center_demand_mw"),
                    "design.data_center_demand_mw",
                ),
                branch_indices=branch_indices,
                generator_indices=generator_indices,
                redispatch_fraction_of_pmax=_number(
                    network.get("redispatch_fraction_of_pmax"),
                    "network.redispatch_fraction_of_pmax",
                ),
                sustained_rating=sustained_rating,
                method=method,
                parameter_status=str(evaluation.get("parameter_status")),
                solver_name=solver_name,
            )
        )
        network_cache[(poi, method)] = result
        network_rows.append(
            {
                "poi_bus": poi,
                "network_method": method,
                "feasible": result.feasible,
                "proven_infeasible": result.proven_infeasible,
                "grid_need_mw": result.grid_need_mw,
                "critical_state": result.critical_state,
                "direct_physical_dispatch_witness": (
                    result.direct_physical_dispatch_witness
                ),
                "termination_condition": (_network_termination_summary(result)),
                "failure_details_json": json.dumps(
                    _network_failure_details(result),
                    sort_keys=True,
                    separators=(",", ":"),
                ),
                "security_certified": False,
            }
        )

    model = _mapping(config.get("model"), "model")
    envelope = _envelope(config.get("envelope"))
    coefficients = _coefficients(config.get("coefficients"))
    scenario_cache = {}
    cell_rows = []
    gate_passed = True
    for cell in cells:
        network_result = network_cache[(cell.poi_bus, cell.network_method)]
        scenario_key = (
            cell.hourly_cfe_target,
            cell.network_activation_threshold,
            cell.business_recovery_headroom_mw,
            cell.seed,
        )
        if scenario_key not in scenario_cache:
            scenario_cache[scenario_key] = generate_phase_map_scenarios(
                PhaseMapScenarioConfig(
                    grid_stress_shape=grid_shape,
                    cfe_profile=cfe_profile,
                    hourly_cfe_target=cell.hourly_cfe_target,
                    data_center_demand_mw=_number(
                        design.get("data_center_demand_mw"),
                        "design.data_center_demand_mw",
                    ),
                    system_load_multiplier=_number(
                        design.get("system_load_multiplier"),
                        "design.system_load_multiplier",
                    ),
                    network_activation_threshold=(cell.network_activation_threshold),
                    business_recovery_headroom_mw=(cell.business_recovery_headroom_mw),
                    core_window_hours=int(design.get("core_window_hours")),
                    recovery_tail_hours=int(design.get("recovery_tail_hours")),
                    n_train=int(design.get("n_train")),
                    n_holdout=int(design.get("n_holdout")),
                    seed=cell.seed,
                    period=str(design.get("period")),
                    split_fraction=split_fraction,
                )
            )
        generated = scenario_cache[scenario_key]
        if not network_result.feasible or network_result.grid_need_mw is None:
            gate_passed = False
            cell_rows.append(_network_unresolved_row(cell, network_result))
            continue
        grid_need = float(network_result.grid_need_mw)
        training = _economic_scenarios(
            generated.training_scenarios, grid_need_mw=grid_need
        )
        holdout = _economic_scenarios(
            generated.holdout_scenarios, grid_need_mw=grid_need
        )
        inputs = TemporalEconomicHoldoutInputs(
            training_scenarios=training,
            holdout_scenarios=holdout,
            envelope=envelope,
            coefficients=coefficients,
            provisioning_cost_per_mw=_number(
                model.get("provisioning_cost_per_mw"),
                "model.provisioning_cost_per_mw",
            ),
            max_flexibility_budget_mw=cell.max_flexibility_budget_mw,
            lambda_risk=_number(model.get("lambda_risk"), "model.lambda_risk"),
            beta=_number(model.get("beta"), "model.beta"),
            parameter_status=(
                f"{evaluation.get('parameter_status')}|{PHASE_MAP_SCENARIO_STATUS}"
            ),
            service_shortfall_tolerance_mwh=_number(
                model.get("service_shortfall_tolerance_mwh"),
                "model.service_shortfall_tolerance_mwh",
            ),
        )
        correct_plan = solve_temporal_economic_stochastic(
            _planning_inputs(inputs, joint=True),
            solver_name=solver_name,
        )
        b6_plan = solve_temporal_economic_stochastic(
            _planning_inputs(inputs, joint=False),
            solver_name=solver_name,
        )
        result = execute_temporal_economic_holdout(
            inputs,
            TemporalPolicyPlan(
                correct=(
                    correct_plan.feasible,
                    not correct_plan.feasible and not correct_plan.proven_infeasible,
                    correct_plan.provisioned_flexibility_mw,
                ),
                b6=(
                    b6_plan.feasible,
                    not b6_plan.feasible and not b6_plan.proven_infeasible,
                    b6_plan.provisioned_flexibility_mw,
                ),
            ),
            solver_name=solver_name,
        )
        phase = classify_phase_region(
            PhaseRegionInputs(
                correct_training_feasible=result.correct.training_feasible,
                b6_training_feasible=result.b6.training_feasible,
                correct_training_unresolved=(result.correct.training_solver_unresolved),
                b6_training_unresolved=result.b6.training_solver_unresolved,
                h2_evaluated=result.h2_evaluated,
                correct_failure_probability=(result.correct.total_failure_probability),
                b6_failure_probability=result.b6.total_failure_probability,
                correct_expected_shortfall_mwh=(
                    result.correct.expected_access_shortfall_mwh
                ),
                b6_expected_shortfall_mwh=(result.b6.expected_access_shortfall_mwh),
                correct_committed_flexibility_mw=(
                    result.correct.committed_flexibility_mw
                ),
                b6_committed_flexibility_mw=(result.b6.committed_flexibility_mw),
            )
        )
        training_metrics = generated.provenance["training_metrics"]
        holdout_metrics = generated.provenance["holdout_metrics"]
        cell_gate = phase.region != "unresolved"
        gate_passed = gate_passed and cell_gate
        cell_rows.append(
            {
                "cell_id": cell.id,
                "families": "|".join(cell.families),
                "poi_bus": cell.poi_bus,
                "network_method": cell.network_method,
                "hourly_cfe_target": cell.hourly_cfe_target,
                "threshold_label": cell.threshold_label,
                "network_activation_threshold": (cell.network_activation_threshold),
                "business_recovery_headroom_mw": (cell.business_recovery_headroom_mw),
                "max_flexibility_budget_mw": (cell.max_flexibility_budget_mw),
                "seed": cell.seed,
                "training_network_activation_rate": training_metrics[
                    "network_activation_rate"
                ],
                "training_green_call_rate": training_metrics["green_call_rate"],
                "training_joint_overlap_rate": _effective_overlap_rate(
                    training_metrics["joint_overlap_rate"], grid_need
                ),
                "holdout_network_activation_rate": holdout_metrics[
                    "network_activation_rate"
                ],
                "holdout_green_call_rate": holdout_metrics["green_call_rate"],
                "holdout_joint_overlap_rate": _effective_overlap_rate(
                    holdout_metrics["joint_overlap_rate"], grid_need
                ),
                "mean_effective_recovery_headroom_mw": holdout_metrics[
                    "mean_effective_recovery_headroom_mw"
                ],
                "grid_need_mw": grid_need,
                "correct_training_feasible": (result.correct.training_feasible),
                "b6_training_feasible": result.b6.training_feasible,
                "correct_training_termination_condition": (
                    correct_plan.termination_condition
                ),
                "b6_training_termination_condition": (b6_plan.termination_condition),
                "correct_training_proven_infeasible": (correct_plan.proven_infeasible),
                "b6_training_proven_infeasible": (b6_plan.proven_infeasible),
                "correct_committed_flexibility_mw": (
                    result.correct.committed_flexibility_mw
                ),
                "b6_committed_flexibility_mw": (result.b6.committed_flexibility_mw),
                "correct_failure_probability": (
                    result.correct.total_failure_probability
                ),
                "b6_failure_probability": (result.b6.total_failure_probability),
                "correct_expected_shortfall_mwh": (
                    result.correct.expected_access_shortfall_mwh
                ),
                "b6_expected_shortfall_mwh": (result.b6.expected_access_shortfall_mwh),
                "delta_failure_probability": (phase.delta_failure_probability),
                "delta_expected_shortfall_mwh": (phase.delta_expected_shortfall_mwh),
                "flexibility_underprovisioning_mw": (
                    phase.flexibility_underprovisioning_mw
                ),
                "region": phase.region,
                "region_reason": phase.reason,
                "scientific_region": phase.scientific_region,
                "gate_passed": cell_gate,
                "security_certified": False,
            }
        )

    region_counts = {
        region: sum(row["region"] == region for row in cell_rows)
        for region in (*PHASE_REGIONS, "diagnostic_mixed", "unresolved")
    }
    if len(cell_rows) != len(cells) or sum(region_counts.values()) != len(cells):
        raise RuntimeError("phase-map publication omitted or duplicated cells")
    output_dir = _path(
        _mapping(config.get("output"), "output").get("directory"),
        "output.directory",
    )
    summary = {
        "schema": "rq2_three_region_phase_map_v1",
        "evaluation_id": evaluation.get("id"),
        "gate_passed": gate_passed,
        "expected_unique_cell_count": len(cells),
        "published_cell_count": len(cell_rows),
        "region_counts": region_counts,
        "region_definitions": {
            "R1_no_conflict": "both policies succeed equivalently",
            "R2_double_commitment_risk": (
                "B6 is weakly dominated with strict capacity underprovisioning "
                "or service loss"
            ),
            "R3_common_insufficiency": (
                "both policies are infeasible or fail equivalently"
            ),
            "diagnostic_mixed": "metrics are not order-consistent",
            "unresolved": "solver or evidence is unresolved",
        },
        "config_sha256": hashlib.sha256(config_bytes).hexdigest(),
        "preregistration_sha256": preregistration_sha256,
        "preregistration_gate": preregistration_gate,
        "implementation_sha256": _sha256(Path(__file__)),
        "cell_table_sha256": _canonical_sha256(cell_rows),
        "source_hashes": {
            "grid": _sha256(grid_path),
            "cfe": _sha256(cfe_path),
        },
        "security_certified": False,
        "formal_result": False,
        "empirical_probability_claimed": False,
        "parameter_status": (
            f"{evaluation.get('parameter_status')}|{PHASE_MAP_SCENARIO_STATUS}"
        ),
        "certification_blockers": [
            "network_activation_is_training_quantile_stress_not_observed_outage",
            "google_and_rts_gmlc_are_independent_marginals",
            "business_recovery_headroom_and_envelope_limits_are_synthetic",
            "selected_n1_dc_not_full_n1_or_ac_security",
            "local_phase_map_is_benchmark_not_confirmatory_formal_result",
        ],
    }
    _publish(
        output_dir,
        cells=cell_rows,
        networks=network_rows,
        summary=summary,
    )
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/rq2_three_region_phase_map_v1.yaml"),
    )
    args = parser.parse_args()
    summary = run(args.config)
    print(json.dumps(summary, indent=2))
    if not summary["gate_passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
