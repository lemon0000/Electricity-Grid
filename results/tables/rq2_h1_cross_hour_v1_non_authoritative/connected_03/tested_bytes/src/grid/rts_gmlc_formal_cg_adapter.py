"""Formal RTS-GMLC model callbacks for the exact-CG state machine."""

from __future__ import annotations

import math
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from pyomo.contrib.solver.common.results import (
    TerminationCondition as V2TerminationCondition,
)
from pyomo.environ import value

from experiments import pilot_rts_gmlc_zero_dc_ac_aware_formulations as pilot
from src.grid.rts_gmlc_exact_cg import (
    SharedSnapshot,
    apply_shared_snapshot,
    relax_fixed_integer_variables,
    shared_snapshot_violation,
    structured_sha256,
)
from src.grid.rts_gmlc_exact_cg_runner import (
    ExactCgCall,
    ExactCgCallbacks,
    FullStateAuditResult,
    MasterSolveResult,
    StateScreenResult,
)
from src.solvers.mip_progress import JsonlProgressWriter


def _snapshot_hash(
    values: tuple[tuple[str, tuple[object, ...], float], ...],
) -> str:
    return structured_sha256(
        [
            {
                "component": component,
                "index": list(index),
                "value_float_hex": float(number).hex(),
            }
            for component, index, number in values
        ]
    )


def canonicalize_discrete_snapshot(
    model: Any,
    snapshot: SharedSnapshot,
    contract: Mapping[str, object],
) -> tuple[SharedSnapshot, dict[str, object]]:
    discrete = {str(item) for item in contract["discrete_components"]}  # type: ignore[index]
    continuous = {str(item) for item in contract["continuous_components"]}  # type: ignore[index]
    continuous.discard("operating_cost")
    maximum_distance = float(
        contract["maximum_distance_to_nearest_binary_before_normalization"]
    )
    normalized_values = {float(item) for item in contract["normalized_values"]}  # type: ignore[index]
    if normalized_values != {0.0, 1.0}:
        raise RuntimeError("Candidate snapshot binary values drifted")

    observed_discrete: set[str] = set()
    normalized_count = 0
    largest_distance = 0.0
    values = []
    for component, index, number in snapshot.values:
        candidate = float(number)
        if not math.isfinite(candidate):
            raise RuntimeError("Candidate snapshot contains a non-finite value")
        if component in discrete:
            observed_discrete.add(component)
            nearest = float(round(candidate))
            distance = abs(candidate - nearest)
            largest_distance = max(largest_distance, distance)
            if nearest not in normalized_values or distance > maximum_distance:
                raise RuntimeError(
                    f"Discrete snapshot value is not within tolerance: {component}{index}"
                )
            candidate = nearest
            normalized_count += 1
        elif component not in continuous:
            raise RuntimeError(f"Unexpected shared snapshot component: {component}")
        values.append((component, index, candidate))
    if observed_discrete != discrete:
        raise RuntimeError("Candidate snapshot discrete component coverage drifted")

    normalized = SharedSnapshot(
        values=tuple(values),
        sha256=_snapshot_hash(tuple(values)),
        reactive_proxy=float(snapshot.reactive_proxy),
        operating_cost_usd=float(snapshot.operating_cost_usd),
    )
    apply_shared_snapshot(model, normalized)
    proxy = float(value(model.reactive_proxy))
    operating_cost = float(value(model.operating_cost))
    if not math.isfinite(proxy) or not math.isfinite(operating_cost):
        raise RuntimeError("Normalized snapshot objectives are not finite")
    normalized = SharedSnapshot(
        values=normalized.values,
        sha256=normalized.sha256,
        reactive_proxy=proxy,
        operating_cost_usd=operating_cost,
    )
    return normalized, {
        "schema": "exact_shared_snapshot_binary_normalization_v1",
        "raw_snapshot_sha256": snapshot.sha256,
        "normalized_snapshot_sha256": normalized.sha256,
        "normalized_value_count": normalized_count,
        "maximum_distance_to_nearest_binary": largest_distance,
        "maximum_allowed_distance": maximum_distance,
        "continuous_values_changed": False,
    }


@dataclass
class FormalCgModelAdapter:
    problem: Any
    formal_solver: Mapping[str, Any]
    candidate_frontier: Mapping[str, Any]
    snapshot_contract: Mapping[str, Any]
    progress: JsonlProgressWriter
    log_root: Path
    event_context: Mapping[str, object] = field(default_factory=dict)
    final_handles: dict[str, Any] = field(default_factory=dict, init=False)

    def callbacks(self) -> ExactCgCallbacks:
        return ExactCgCallbacks(
            solve_master=self.solve_master,
            screen_state=self.screen_state,
            audit_full_state=self.audit_full_state,
            emit=lambda event, payload: self.progress.emit(
                event, **self.event_context, **dict(payload)
            ),
        )

    def _call_config(self, call: ExactCgCall) -> dict[str, object]:
        solver = self.formal_solver["solver"]
        logging = self.formal_solver["progress_logging"]
        return {
            "budget": {
                "cost_cap_absolute_tolerance_usd": float(
                    self.candidate_frontier["cost_cap_absolute_tolerance_usd"]
                )
            },
            "solver": {
                "name": str(solver["name"]),
                "threads": int(solver["threads"]),
                "random_seed": int(solver["random_seed"]),
                "feasibility_tolerance": float(solver["feasibility_tolerance"]),
                "bound_consistency_tolerance": float(
                    solver["bound_consistency_tolerance"]
                ),
                "target_mip_relative_gap": float(call.target_relative_gap),
                "time_limit_seconds_per_call": float(call.time_limit_seconds),
                "mip_min_logging_interval_seconds": float(
                    logging["native_solver_log_interval_seconds"]
                ),
            },
            "timing": {
                "heartbeat_interval_seconds": float(
                    logging["heartbeat_interval_seconds"]
                )
            },
            "expected_full_model_size": dict(
                self.formal_solver["expected_full_model_size"]
            ),
        }

    def _native_log(self, call: ExactCgCall) -> Path:
        safe_id = call.call_id.replace(".", "__")
        path = self.log_root / call.stage / f"{safe_id}.log"
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def solve_master(self, call: ExactCgCall) -> MasterSolveResult:
        config = self._call_config(call)
        build_started = time.perf_counter()
        handle = pilot._build_model_handle(
            self.problem,
            config,
            call.active_state_ids,
            stage=call.stage,
            proxy_floor=call.proxy_floor,
        )
        build_seconds = time.perf_counter() - build_started
        self.progress.emit(
            "formal_master_built",
            **self.event_context,
            call_id=call.call_id,
            stage=call.stage,
            iteration=call.iteration,
            active_state_ids=list(call.active_state_ids),
            variables=handle.formulation_variables,
            constraints=handle.formulation_constraints,
            build_seconds=build_seconds,
        )
        solved = pilot._solve_handle(
            handle,
            config,
            native_log=self._native_log(call),
            progress=self.progress,
            solve_label=call.call_id,
        )
        tolerance = float(self.formal_solver["solver"]["feasibility_tolerance"])
        discrete_tolerance = float(
            self.snapshot_contract[
                "maximum_distance_to_nearest_binary_before_normalization"
            ]
        )
        snapshot = None
        residual = None
        normalization = None
        normalization_error = None
        usable = bool(
            solved["incumbent_usable"]
            and solved["maximum_integrality_violation"] is not None
            and float(solved["maximum_integrality_violation"]) <= discrete_tolerance
        )
        if usable:
            try:
                raw_snapshot = pilot._extract_shared_snapshot(handle)
                snapshot, normalization = canonicalize_discrete_snapshot(
                    handle.model, raw_snapshot, self.snapshot_contract
                )
                residual = pilot._residual_audit(handle, self.problem, tolerance)
            except Exception as error:
                snapshot = None
                normalization_error = f"{type(error).__name__}: {error}"
        residual_passed = bool(residual is not None and residual["passed"])
        decision_budget_cap = (
            self.problem.cost_budget_usd
            + float(self.candidate_frontier["cost_cap_absolute_tolerance_usd"])
            if call.stage == "level_set_budget_feasibility"
            else None
        )
        globally_infeasible = bool(
            call.stage == "level_set_budget_feasibility"
            and solved.get("solver_api") == "pyomo.contrib.solver.highs_v2"
            and solved.get("termination_condition")
            == str(V2TerminationCondition.provenInfeasible)
            and solved.get("global_infeasibility_certified") is True
        )
        if call.stage == "level_set_cost_minimization":
            raw_lower_bound = solved.get("raw_lower_bound")
            try:
                level_dual = float(raw_lower_bound)
            except (TypeError, ValueError):
                level_dual = None
            if level_dual is not None and not math.isfinite(level_dual):
                level_dual = None
            bound_valid = level_dual is not None
        elif call.stage == "level_set_budget_feasibility":
            level_dual = None
            bound_valid = False
        else:
            level_dual = None
            bound_valid = bool(solved["bound_valid"])
        return MasterSolveResult(
            snapshot=snapshot,
            incumbent_usable=usable and snapshot is not None,
            bound_valid=bound_valid,
            dual_bound=(
                level_dual
                if call.stage == "level_set_cost_minimization"
                else (
                    float(solved["dual_bound"])
                    if solved["dual_bound"] is not None
                    else None
                )
            ),
            residual_audit_passed=residual_passed,
            record={
                "build_seconds": build_seconds,
                "solve": solved,
                "snapshot_normalization": normalization,
                "snapshot_normalization_error": normalization_error,
                "canonical_residual_audit": residual,
                "decision_mip": (
                    {
                        "schema": "rts_gmlc_level_set_budget_decision_mip_v2",
                        "budget_cap_usd": decision_budget_cap,
                        "objective_target_usd": solved.get(
                            "decision_objective_target_usd"
                        ),
                        "solver_api": solved.get("solver_api"),
                        "solver_api_termination_condition": solved.get(
                            "termination_condition"
                        ),
                        "solver_api_solution_status": solved.get(
                            "solver_api_solution_status"
                        ),
                        "solver_status_raw": solved.get("solver_status"),
                        "termination_is_global_infeasible": globally_infeasible,
                        "objective_limit_is_feasible_only": (
                            solved.get("termination_condition")
                            == str(V2TerminationCondition.objectiveLimit)
                        ),
                        "objective_limit_is_optimality_certificate": False,
                    }
                    if call.stage == "level_set_budget_feasibility"
                    else None
                ),
            },
            globally_infeasible=globally_infeasible,
            decision_budget_cap_usd=decision_budget_cap,
        )

    def screen_state(self, call: ExactCgCall) -> StateScreenResult:
        if call.shared_snapshot is None or call.state_id is None:
            raise ValueError("State screen requires a state and shared snapshot")
        record = pilot._screen_state(
            self.problem,
            self._call_config(call),
            call.shared_snapshot,
            call.state_id,
            stage=call.stage,
            proxy_floor=call.proxy_floor,
            native_log=self._native_log(call),
            progress=self.progress,
            solve_label=call.call_id,
        )
        return StateScreenResult(
            status=str(record["status"]),  # type: ignore[arg-type]
            shared_snapshot_sha256=call.shared_snapshot.sha256,
            record=record,
        )

    def audit_full_state(self, call: ExactCgCall) -> FullStateAuditResult:
        if call.shared_snapshot is None:
            raise ValueError("Full-state audit requires a shared snapshot")
        snapshot = call.shared_snapshot
        config = self._call_config(call)
        build_started = time.perf_counter()
        handle = pilot._build_model_handle(
            self.problem,
            config,
            call.all_state_ids,
            stage=call.stage,
            proxy_floor=call.proxy_floor,
        )
        apply_shared_snapshot(handle.model, snapshot)
        relax_fixed_integer_variables(handle.model)
        build_seconds = time.perf_counter() - build_started
        solved = pilot._solve_handle(
            handle,
            config,
            native_log=self._native_log(call),
            progress=self.progress,
            solve_label=call.call_id,
        )
        tolerance = float(self.formal_solver["solver"]["feasibility_tolerance"])
        shared_violation = (
            shared_snapshot_violation(handle.model, snapshot)
            if solved["solution_loaded"]
            else None
        )
        residual = None
        if solved["incumbent_usable"] and shared_violation is not None:
            try:
                residual = pilot._residual_audit(handle, self.problem, tolerance)
            except Exception:
                residual = None
        commitment_proxy = pilot._commitment_proxy_from_snapshot(
            self.problem, snapshot, tolerance
        )
        actual_proxy = (
            float(value(handle.model.reactive_proxy))
            if solved["solution_loaded"]
            else None
        )
        actual_cost = (
            float(value(handle.model.operating_cost))
            if solved["solution_loaded"]
            else None
        )
        objective = actual_proxy if call.stage == "proxy_maximization" else actual_cost
        cost_tolerance = float(
            self.candidate_frontier["cost_cap_absolute_tolerance_usd"]
        )
        shared_fixed = bool(
            shared_violation is not None and shared_violation <= tolerance
        )
        proxy_consistent = bool(
            actual_proxy is not None
            and actual_proxy <= commitment_proxy + tolerance
            and (
                call.proxy_floor is None
                or actual_proxy + tolerance >= float(call.proxy_floor)
            )
        )
        cost_consistent = bool(
            actual_cost is not None
            and actual_cost <= self.problem.cost_budget_usd + cost_tolerance
            and abs(actual_cost - snapshot.operating_cost_usd) <= cost_tolerance
        )
        snapshot_proxy_consistent = bool(
            actual_proxy is not None
            and abs(actual_proxy - snapshot.reactive_proxy) <= tolerance
        )
        additional = bool(
            proxy_consistent and cost_consistent and snapshot_proxy_consistent
        )
        residual_passed = bool(residual is not None and residual["passed"])
        solution_usable = bool(solved["incumbent_usable"] and objective is not None)
        passed = bool(
            solution_usable and shared_fixed and residual_passed and additional
        )
        if passed:
            self.final_handles[call.stage] = handle
        record = {
            "build_seconds": build_seconds,
            "solve": solved,
            "maximum_shared_value_violation": shared_violation,
            "residual_audit": residual,
            "commitment_capability_proxy_fraction": commitment_proxy,
            "actual_proxy_fraction": actual_proxy,
            "actual_operating_cost_usd": actual_cost,
            "proxy_consistent": proxy_consistent,
            "cost_consistent": cost_consistent,
            "snapshot_proxy_consistent": snapshot_proxy_consistent,
            "passed": passed,
        }
        self.progress.emit(
            "formal_full_state_audit_completed",
            **self.event_context,
            call_id=call.call_id,
            stage=call.stage,
            **record,
        )
        return FullStateAuditResult(
            audited_state_ids=call.all_state_ids,
            shared_snapshot_sha256=snapshot.sha256,
            solution_usable=solution_usable,
            shared_snapshot_fixed=shared_fixed,
            integer_variables_relaxed=True,
            residual_audit_passed=residual_passed,
            additional_audits_passed=additional,
            full_feasible_objective=objective,
            record=record,
        )


__all__ = ["FormalCgModelAdapter", "canonicalize_discrete_snapshot"]
