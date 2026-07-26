"""V4-only audited MIP start for the first proxy exact-CG master.

The implementation deliberately reuses the frozen benchmark's audited mapping
routine after the V4 runner has verified its immutable source and result
manifests.  It is not used for later masters, screening, or final audits.
"""

from __future__ import annotations

import hashlib
import importlib.util
import os
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from highspy import Highs
from pyomo.environ import SolverFactory, value

from experiments import pilot_rts_gmlc_zero_dc_ac_aware_formulations as pilot
from src.grid.rts_gmlc_exact_cg_runner import ExactCgCall, MasterSolveResult
from src.grid.rts_gmlc_formal_cg_adapter import (
    FormalCgModelAdapter,
    canonicalize_discrete_snapshot,
)
from src.solvers.mip_progress import ProgressHeartbeat, highs_runtime_options


def _load_frozen_benchmark_module(path: Path, expected_sha256: str) -> Any:
    if (
        not path.is_file()
        or hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha256
    ):
        raise RuntimeError("V4 initial proxy warm-start source drifted")
    spec = importlib.util.spec_from_file_location("_v4_frozen_warmstart", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("V4 initial proxy warm-start source cannot be loaded")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class V4InitialProxyWarmStartAdapter(FormalCgModelAdapter):
    """Use the selected full-column Appsi/HiGHS start on the first master."""

    def __init__(self, *, warm_start: Mapping[str, Any], **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._warm_start = dict(warm_start)

    def _is_initial_proxy_master(self, call: ExactCgCall) -> bool:
        return bool(
            call.stage == "proxy_maximization"
            and call.kind == "master"
            and call.iteration == 1
            and self._warm_start["application_scope"]
            == "initial_proxy_maximization_master_only"
        )

    def _benchmark_config(self) -> dict[str, object]:
        parent = self.problem.parent_context.config["parent_zero_control"]
        solver = self.formal_solver["solver"]
        return {
            "provenance": {
                "parent_zero_dispatch_root": str(
                    Path(parent["output_directory"]) / "dc_dispatch"
                )
            },
            "solver": {"feasibility_tolerance": float(solver["feasibility_tolerance"])},
            "warm_start": {
                "expected_proxy_objective": 0.24328147100424327,
                "expected_operating_cost_usd": float(
                    parent["baseline_full_state_cost_usd"]
                ),
                "maximum_constraint_violation": 1.0e-6,
                "maximum_integrality_violation": 1.0e-8,
                "objective_absolute_tolerance": 1.0e-6,
            },
        }

    def solve_master(self, call: ExactCgCall) -> MasterSolveResult:
        if not self._is_initial_proxy_master(call):
            return super().solve_master(call)
        if tuple(call.active_state_ids) != tuple(self.problem.initial_active_state_ids):
            raise RuntimeError(
                "V4 initial proxy warm-start active-state mapping drifted"
            )

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
        frozen = _load_frozen_benchmark_module(
            Path(self._warm_start["adapter_source_path"]),
            str(self._warm_start["adapter_source_sha256"]),
        )
        warm_audit = frozen._assign_parent_start(
            self._benchmark_config(), self.problem, handle
        )
        solver = SolverFactory(str(self._warm_start["solver_interface"]))
        if (
            not solver.available(exception_flag=False)
            or not solver.warm_start_capable()
        ):
            raise RuntimeError("V4 selected Appsi/HiGHS MIP start is unavailable")
        frozen._install_audited_appsi_warm_start(solver)
        native_log = self._native_log(call)
        options = highs_runtime_options(
            mip_relative_gap=float(config["solver"]["target_mip_relative_gap"]),
            threads=int(config["solver"]["threads"]),
            random_seed=int(config["solver"]["random_seed"]),
            feasibility_tolerance=float(config["solver"]["feasibility_tolerance"]),
            time_limit_seconds=float(config["solver"]["time_limit_seconds_per_call"]),
            log_file=native_log,
            mip_min_logging_interval_seconds=float(
                config["solver"]["mip_min_logging_interval_seconds"]
            ),
        )
        self.progress.emit(
            "formal_initial_proxy_warm_start_submitted",
            **self.event_context,
            call_id=call.call_id,
            submitted_solver_column_count=handle.formulation_variables,
            warm_start_audit=warm_audit,
        )
        Highs.resetGlobalScheduler(True)
        started = time.perf_counter()
        try:
            with ProgressHeartbeat(
                self.progress,
                interval_seconds=float(config["timing"]["heartbeat_interval_seconds"]),
                payload={"solve_label": call.call_id, "native_log": native_log.name},
            ):
                results = solver.solve(
                    handle.model,
                    load_solutions=False,
                    tee=False,
                    options=options,
                    warmstart=True,
                )
        except Exception as error:
            self._fsync(native_log)
            raise RuntimeError("V4 initial proxy warm-start solve failed") from error
        self._fsync(native_log)
        loaded = False
        try:
            handle.model.solutions.load_from(results)
            loaded = True
        except Exception:
            loaded = False
        objective = (
            pilot._optional_float(value(handle.model.reactive_proxy, exception=False))
            if loaded
            else None
        )
        constraint_violation = (
            float(pilot._constraint_violation(handle.model)) if loaded else None
        )
        integrality_violation = (
            float(pilot._integrality_violation(handle.model)) if loaded else None
        )
        tolerance = float(self.formal_solver["solver"]["feasibility_tolerance"])
        usable = pilot._incumbent_is_usable(
            termination_condition=results.solver.termination_condition,
            solution_loaded=loaded,
            incumbent_objective=objective,
            maximum_constraint_violation=constraint_violation,
            maximum_integrality_violation=integrality_violation,
            variables_finite=(
                pilot._all_variables_finite(handle.model) if loaded else False
            ),
            feasibility_tolerance=tolerance,
        )
        bounds = pilot._orient_bound_interval(
            sense=handle.sense,
            raw_lower_bound=pilot._optional_float(results.problem.lower_bound),
            raw_upper_bound=pilot._optional_float(results.problem.upper_bound),
            incumbent_objective=objective,
            consistency_tolerance=float(
                config["solver"]["bound_consistency_tolerance"]
            ),
        )
        acceptance = frozen._parse_native_log(
            native_log,
            acceptance_text="MIP start solution is feasible, objective value is",
            rejection_text="MIP start solution is infeasible",
        )
        if (
            warm_audit["passed"] is not True
            or getattr(solver, "_warmstart_submission_status", None)
            != "HighsStatus.kOk"
            or getattr(solver, "_warmstart_submitted_column_count", 0)
            != handle.formulation_variables
            or acceptance["mip_start_acceptance_line_count"] != 1
            or acceptance["mip_start_rejection_line_count"] != 0
        ):
            raise RuntimeError("V4 initial proxy warm-start acceptance evidence failed")
        snapshot = None
        residual = None
        normalization = None
        if (
            usable
            and integrality_violation is not None
            and integrality_violation
            <= float(
                self.snapshot_contract[
                    "maximum_distance_to_nearest_binary_before_normalization"
                ]
            )
        ):
            raw_snapshot = pilot._extract_shared_snapshot(handle)
            snapshot, normalization = canonicalize_discrete_snapshot(
                handle.model, raw_snapshot, self.snapshot_contract
            )
            residual = pilot._residual_audit(handle, self.problem, tolerance)
        return MasterSolveResult(
            snapshot=snapshot,
            incumbent_usable=bool(usable and snapshot is not None),
            bound_valid=bool(bounds["bound_valid"]),
            dual_bound=(
                float(bounds["certified_upper_bound"])
                if bounds["certified_upper_bound"] is not None
                else None
            ),
            residual_audit_passed=bool(residual is not None and residual["passed"]),
            record={
                "build_seconds": build_seconds,
                "solve": {
                    "solve_seconds": time.perf_counter() - started,
                    "termination_condition": str(results.solver.termination_condition),
                    "solution_loaded": loaded,
                    "incumbent_usable": usable,
                    "incumbent_objective": objective,
                    "maximum_constraint_violation": constraint_violation,
                    "maximum_integrality_violation": integrality_violation,
                    "native_log": native_log.name,
                    **bounds,
                },
                "initial_proxy_warm_start": {
                    "method": self._warm_start["selected_method"],
                    "warm_start_audit": warm_audit,
                    "set_solution_status": getattr(
                        solver, "_warmstart_submission_status", None
                    ),
                    "submitted_solver_column_count": getattr(
                        solver, "_warmstart_submitted_column_count", 0
                    ),
                    "native_log_evidence": acceptance,
                },
                "snapshot_normalization": normalization,
                "canonical_residual_audit": residual,
            },
        )

    @staticmethod
    def _fsync(path: Path) -> None:
        if path.exists():
            with path.open("ab") as output:
                output.flush()
                os.fsync(output.fileno())


__all__ = ["V4InitialProxyWarmStartAdapter"]
