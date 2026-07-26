"""Worker-only runtime options for the V4 joint AC IPOPT solve.

The caller must isolate this API in a worker process. The lock prevents two
threads in that worker from observing different temporary core option sets.
"""

from __future__ import annotations

import math
from collections.abc import Mapping, Sequence
from numbers import Real
from pathlib import Path
from threading import Lock

from src.grid import rts_gmlc_ac_aware_commitment as core
from src.grid import rts_gmlc_ac_ipopt as shared_ipopt
from src.grid.rts_gmlc_ac_ipopt import IpoptInitialStrategy
from src.grid.rts_gmlc_ac_recovery import AcRecoveryInput

_ALLOWED_RUNTIME_KEYS = frozenset(
    {
        "ipopt.max_cpu_time",
        "ipopt.output_file",
        "ipopt.file_print_level",
    }
)
_WORKER_SOLVE_LOCK = Lock()


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


def solve_ac_aware_commitment_v4_worker(
    prepared_cases: Sequence[AcRecoveryInput],
    chronology: core.AcAwareChronology,
    *,
    base_options: Mapping[str, object],
    runtime_options: Mapping[str, object],
    initial_strategy: IpoptInitialStrategy = "source",
) -> core.AcAwareCommitmentResult:
    """Run one V4 solve inside an already isolated worker process."""

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
            return core.solve_ac_aware_commitment(
                prepared_cases,
                chronology,
                initial_strategy=initial_strategy,
                solver_options=effective_options,
            )
        finally:
            core._FROZEN_IPOPT_OPTIONS = previous_core_options


__all__ = ["solve_ac_aware_commitment_v4_worker"]
