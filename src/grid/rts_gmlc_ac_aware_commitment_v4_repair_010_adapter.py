"""Worker-only runtime options for the V4 joint AC IPOPT solve.

The caller must isolate this API in a worker process. The lock prevents two
threads in that worker from observing different temporary core option sets.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Callable, Mapping, Sequence
from numbers import Real
from pathlib import Path
from threading import Lock

import casadi as ca
import numpy as np

from src.grid import rts_gmlc_ac_aware_commitment as core
from src.grid import rts_gmlc_ac_ipopt as shared_ipopt
from src.grid.rts_gmlc_ac_ipopt import IpoptInitialStrategy
from src.grid.rts_gmlc_ac_recovery import AcRecoveryInput
from src.solvers.joint_ac_phase_contract import (
    expression_fingerprint_sha256,
    solver_input_fingerprint_sha256,
)

_ALLOWED_RUNTIME_KEYS = frozenset(
    {
        "ipopt.max_cpu_time",
        "ipopt.output_file",
        "ipopt.file_print_level",
    }
)
_WORKER_SOLVE_LOCK = Lock()


class CalibrationStopBeforeSolverEvaluation(RuntimeError):
    """Expected calibration stop after full solver inputs exist, before evaluation."""

    def __init__(self, fingerprint: Mapping[str, object]) -> None:
        self.fingerprint = dict(fingerprint)
        super().__init__("repair-010 calibration stopped before solver evaluation")


def _canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _array_sha256(value: object) -> str:
    array = np.asarray(value, dtype="<f8")
    shape = json.dumps(list(array.shape), separators=(",", ":")).encode("ascii")
    return hashlib.sha256(shape + b"\0" + array.tobytes(order="C")).hexdigest()


def _prepared_inputs_payload(
    prepared_cases: Sequence[AcRecoveryInput],
    chronology: core.AcAwareChronology,
) -> dict[str, object]:
    return {
        "cases": [
            {
                "mode": prepared.mode,
                "fixed_inputs_preserved": prepared.fixed_inputs_preserved,
                "active_power_envelope": prepared.active_power_envelope,
                "source_case_sha256": prepared.source_case_sha256,
                "recovery_case_sha256": prepared.recovery_case_sha256,
                "bus_sha256": _array_sha256(prepared.case["bus"]),
                "gen_sha256": _array_sha256(prepared.case["gen"]),
                "branch_sha256": _array_sha256(prepared.case["branch"]),
                "gencost_sha256": _array_sha256(prepared.case["gencost"]),
                "target_generation_mw_by_row": list(
                    prepared.target_generation_mw_by_row
                ),
                "generator_uid_by_row": list(prepared.generator_uid_by_row),
                "branch_uid_by_row": list(prepared.branch_uid_by_row),
                "adjustable_generator_rows": list(prepared.adjustable_generator_rows),
                "fixed_generator_rows": list(prepared.fixed_generator_rows),
                "reference_generator_row": prepared.reference_generator_row,
                "reference_generator_uid": prepared.reference_generator_uid,
                "reference_bus": prepared.reference_bus,
                "source_controller_vg_by_bus": [
                    [bus, value] for bus, value in prepared.source_controller_vg_by_bus
                ],
            }
            for prepared in prepared_cases
        ],
        "chronology": {
            "timestamps": [value.isoformat() for value in chronology.timestamps],
            "time_step_hours": chronology.time_step_hours,
            "units": [
                {
                    "generator_uid": unit.generator_uid,
                    "area": unit.area,
                    "p_max_mw": unit.p_max_mw,
                    "ramp_mw_per_hour": unit.ramp_mw_per_hour,
                    "ramp_mw_per_minute": unit.ramp_mw_per_minute,
                    "reserve_eligible": unit.reserve_eligible,
                    "initial_generation_mw": unit.initial_generation_mw,
                    "initial_commitment": unit.initial_commitment,
                    "commitment_by_hour": list(unit.commitment_by_hour),
                    "startup_by_hour": list(unit.startup_by_hour),
                    "shutdown_by_hour": list(unit.shutdown_by_hour),
                }
                for unit in chronology.units
            ],
            "spin_up_requirement_by_hour_area_mw": [
                [[area, value] for area, value in sorted(requirements.items())]
                for requirements in chronology.spin_up_requirement_by_hour_area_mw
            ],
        },
    }


def _expression_fingerprint(
    problem: Mapping[str, object],
    options: Mapping[str, object],
    prepared_inputs_sha256: str,
) -> dict[str, object]:
    variables = problem["x"]
    objective = problem["f"]
    constraints = problem["g"]
    variable_function = ca.Function(
        "repair010_variable_order_fingerprint", [variables], [variables]
    )
    objective_function = ca.Function(
        "repair010_objective_fingerprint", [variables], [objective]
    )
    constraint_function = ca.Function(
        "repair010_constraint_order_fingerprint", [variables], [constraints]
    )
    payload: dict[str, object] = {
        "schema": "rts_gmlc_ac_aware_nlp_expression_fingerprint_v1",
        "variable_count": int(variables.numel()),
        "constraint_count": int(constraints.numel()),
        "variable_order_sha256": hashlib.sha256(
            variable_function.serialize().encode("utf-8")
        ).hexdigest(),
        "objective_expression_sha256": hashlib.sha256(
            objective_function.serialize().encode("utf-8")
        ).hexdigest(),
        "constraint_order_and_expression_sha256": hashlib.sha256(
            constraint_function.serialize().encode("utf-8")
        ).hexdigest(),
        "ipopt_options_sha256": _canonical_sha256(dict(options)),
        "prepared_inputs_sha256": prepared_inputs_sha256,
    }
    payload["expression_fingerprint_sha256"] = expression_fingerprint_sha256(payload)
    return payload


class _ObservedSolver:
    def __init__(
        self,
        solver: object,
        observer: Callable[[str, Mapping[str, object]], None],
        expression_fingerprint: Mapping[str, object],
        *,
        stop_before_solver_evaluation: bool = False,
    ) -> None:
        self._solver = solver
        self._observer = observer
        self._expression_fingerprint = dict(expression_fingerprint)
        self._stop_before_solver_evaluation = stop_before_solver_evaluation

    def __call__(self, *args: object, **kwargs: object) -> object:
        if args:
            raise RuntimeError(
                "Observed V4 IPOPT call unexpectedly used positional inputs"
            )
        payload = {
            **self._expression_fingerprint,
            "initial_point_sha256": _array_sha256(kwargs["x0"]),
            "variable_lower_sha256": _array_sha256(kwargs["lbx"]),
            "variable_upper_sha256": _array_sha256(kwargs["ubx"]),
            "constraint_lower_sha256": _array_sha256(kwargs["lbg"]),
            "constraint_upper_sha256": _array_sha256(kwargs["ubg"]),
        }
        payload["solver_input_fingerprint_sha256"] = solver_input_fingerprint_sha256(
            payload
        )
        if self._stop_before_solver_evaluation:
            self._observer("calibration_pre_solver_stop", payload)
            raise CalibrationStopBeforeSolverEvaluation(payload)
        self._observer("solver_started", payload)
        try:
            result = self._solver(**kwargs)
        except BaseException as error:
            self._observer(
                "solver_finished",
                {
                    **payload,
                    "termination": "raised",
                    "error_type": type(error).__name__,
                },
            )
            raise
        stats = self._solver.stats()
        self._observer(
            "solver_finished",
            {
                **payload,
                "termination": "returned",
                "solver_success": bool(stats.get("success", False)),
                "return_status": str(stats.get("return_status", "")),
            },
        )
        return result

    def stats(self) -> object:
        return self._solver.stats()


class _ObservedNlpsolFactory:
    def __init__(
        self,
        factory: Callable[..., object],
        observer: Callable[[str, Mapping[str, object]], None],
        prepared_inputs_sha256: str,
        *,
        stop_before_solver_evaluation: bool = False,
    ) -> None:
        self._factory = factory
        self._observer = observer
        self._prepared_inputs_sha256 = prepared_inputs_sha256
        self._stop_before_solver_evaluation = stop_before_solver_evaluation

    def __call__(
        self,
        name: str,
        plugin: str,
        problem: Mapping[str, object],
        options: Mapping[str, object],
    ) -> _ObservedSolver:
        expression_fingerprint = _expression_fingerprint(
            problem, options, self._prepared_inputs_sha256
        )
        solver = self._factory(name, plugin, problem, options)
        self._observer("nlp_build_completed", expression_fingerprint)
        return _ObservedSolver(
            solver,
            self._observer,
            expression_fingerprint,
            stop_before_solver_evaluation=self._stop_before_solver_evaluation,
        )


def _strict_options_equal(
    observed: Mapping[str, object], expected: Mapping[str, object]
) -> bool:
    return set(observed) == set(expected) and all(
        type(observed[key]) is type(expected[key]) and observed[key] == expected[key]
        for key in expected
    )


def _validated_runtime_options(
    runtime_options: Mapping[str, object],
) -> dict[str, object]:
    if not isinstance(runtime_options, Mapping):
        raise TypeError("V4 IPOPT runtime options must be a mapping")
    unknown = set(runtime_options) - _ALLOWED_RUNTIME_KEYS
    if unknown:
        raise ValueError(
            "Unknown V4 IPOPT runtime options: " + ", ".join(sorted(unknown))
        )

    validated: dict[str, object] = {}
    if "ipopt.max_cpu_time" in runtime_options:
        candidate = runtime_options["ipopt.max_cpu_time"]
        if isinstance(candidate, bool) or not isinstance(candidate, Real):
            raise ValueError("ipopt.max_cpu_time must be a positive finite number")
        value = float(candidate)
        if not math.isfinite(value) or value <= 0.0:
            raise ValueError("ipopt.max_cpu_time must be a positive finite number")
        validated["ipopt.max_cpu_time"] = value

    if "ipopt.output_file" in runtime_options:
        candidate = runtime_options["ipopt.output_file"]
        if not isinstance(candidate, str) or not candidate:
            raise ValueError("ipopt.output_file must be a nonempty lowercase string")
        if Path(candidate).name != Path(candidate).name.lower():
            raise ValueError("ipopt.output filename must be lowercase")
        validated["ipopt.output_file"] = candidate

    if "ipopt.file_print_level" in runtime_options:
        candidate = runtime_options["ipopt.file_print_level"]
        if (
            isinstance(candidate, bool)
            or not isinstance(candidate, int)
            or not 0 <= candidate <= 12
        ):
            raise ValueError("ipopt.file_print_level must be an integer in [0, 12]")
        validated["ipopt.file_print_level"] = candidate
    return validated


def prepared_inputs_sha256(
    prepared_cases: Sequence[AcRecoveryInput], chronology: core.AcAwareChronology
) -> str:
    return _canonical_sha256(_prepared_inputs_payload(prepared_cases, chronology))


def effective_ipopt_options_sha256(
    *,
    base_options: Mapping[str, object],
    runtime_options: Mapping[str, object],
) -> str:
    if not isinstance(base_options, Mapping) or not _strict_options_equal(
        base_options, shared_ipopt._FROZEN_IPOPT_OPTIONS
    ):
        raise ValueError("V4 base IPOPT options drifted from the shared frozen set")
    effective = dict(shared_ipopt._FROZEN_IPOPT_OPTIONS)
    effective.update(_validated_runtime_options(runtime_options))
    return _canonical_sha256(effective)


def solve_ac_aware_commitment_v4_worker(
    prepared_cases: Sequence[AcRecoveryInput],
    chronology: core.AcAwareChronology,
    *,
    base_options: Mapping[str, object],
    runtime_options: Mapping[str, object],
    initial_strategy: IpoptInitialStrategy = "source",
    phase_observer: Callable[[str, Mapping[str, object]], None] | None = None,
    stop_before_solver_evaluation: bool = False,
) -> core.AcAwareCommitmentResult:
    """Run one V4 solve inside an already isolated worker process."""

    if stop_before_solver_evaluation and phase_observer is None:
        raise ValueError("Calibration stop requires a phase observer")
    runtime = _validated_runtime_options(runtime_options)
    with _WORKER_SOLVE_LOCK:
        shared_frozen = shared_ipopt._FROZEN_IPOPT_OPTIONS
        if not isinstance(base_options, Mapping) or not _strict_options_equal(
            base_options, shared_frozen
        ):
            raise ValueError("V4 base IPOPT options drifted from the shared frozen set")

        previous_core_options = core._FROZEN_IPOPT_OPTIONS
        if not _strict_options_equal(previous_core_options, shared_frozen):
            raise RuntimeError(
                "Shared AC-aware core IPOPT options are already modified"
            )

        effective_options = dict(shared_frozen)
        effective_options.update(runtime)
        core._FROZEN_IPOPT_OPTIONS = effective_options
        try:
            if phase_observer is None:
                return core.solve_ac_aware_commitment(
                    prepared_cases,
                    chronology,
                    initial_strategy=initial_strategy,
                    solver_options=effective_options,
                )
            prepared_hash = prepared_inputs_sha256(prepared_cases, chronology)
            phase_observer(
                "nlp_build_started",
                {
                    "prepared_inputs_sha256": prepared_hash,
                    "ipopt_options_sha256": _canonical_sha256(effective_options),
                },
            )
            original_nlpsol = core.ca.nlpsol
            core.ca.nlpsol = _ObservedNlpsolFactory(
                original_nlpsol,
                phase_observer,
                prepared_hash,
                stop_before_solver_evaluation=stop_before_solver_evaluation,
            )
            try:
                return core.solve_ac_aware_commitment(
                    prepared_cases,
                    chronology,
                    initial_strategy=initial_strategy,
                    solver_options=effective_options,
                )
            finally:
                core.ca.nlpsol = original_nlpsol
        finally:
            core._FROZEN_IPOPT_OPTIONS = previous_core_options


def calibrate_ac_aware_commitment_v4_startup(
    prepared_cases: Sequence[AcRecoveryInput],
    chronology: core.AcAwareChronology,
    *,
    base_options: Mapping[str, object],
    runtime_options: Mapping[str, object],
    initial_strategy: IpoptInitialStrategy = "source",
    phase_observer: Callable[[str, Mapping[str, object]], None],
) -> dict[str, object]:
    """Construct the real NLP/solver and stop at the pre-evaluation call boundary."""

    try:
        solve_ac_aware_commitment_v4_worker(
            prepared_cases,
            chronology,
            base_options=base_options,
            runtime_options=runtime_options,
            initial_strategy=initial_strategy,
            phase_observer=phase_observer,
            stop_before_solver_evaluation=True,
        )
    except CalibrationStopBeforeSolverEvaluation as stop:
        return stop.fingerprint
    raise RuntimeError(
        "repair-010 calibration core returned before the pre-solver stop boundary"
    )


__all__ = [
    "CalibrationStopBeforeSolverEvaluation",
    "calibrate_ac_aware_commitment_v4_startup",
    "effective_ipopt_options_sha256",
    "prepared_inputs_sha256",
    "solve_ac_aware_commitment_v4_worker",
]
