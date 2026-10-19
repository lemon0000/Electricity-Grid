"""Regression tests for the repair-009 Gurobi option read path.

The repair-009 ifocus attempt burned six hours because ``IntegralityFocus: 1``
was preregistered and written into ``formal_solver.solver.options`` while no
module read that key. These tests pin the read path so a declared option either
reaches ``solver.solve`` or raises.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from experiments.pilot_rts_gmlc_zero_dc_ac_aware_formulations_gurobi import (
    FROZEN_GUROBI_OPTION_KEYS,
    UnreadableSolverOptionError,
    assemble_gurobi_options,
    gurobi_runtime_options,
)


def _solver_config(**overrides: Any) -> dict[str, Any]:
    config: dict[str, Any] = {
        "name": "gurobi",
        "target_mip_relative_gap": 1.0e-4,
        "threads": 4,
        "random_seed": 0,
        "feasibility_tolerance": 1.0e-6,
        "time_limit_seconds_per_call": 7200.0,
        "mip_min_logging_interval_seconds": 5.0,
        "bound_consistency_tolerance": 1.0e-6,
    }
    config.update(overrides)
    return config


def test_absent_options_reproduce_the_frozen_defaults(tmp_path: Path) -> None:
    options = assemble_gurobi_options(
        _solver_config(), native_log=tmp_path / "call.log", objective_cutoff=None
    )
    assert options["IntFeasTol"] == pytest.approx(1.0e-6)
    assert options["Threads"] == 4
    assert options["Seed"] == 0
    assert "IntegralityFocus" not in options
    assert "Cutoff" not in options


def test_declared_option_reaches_the_option_dict(tmp_path: Path) -> None:
    options = assemble_gurobi_options(
        _solver_config(options={"IntegralityFocus": 1}),
        native_log=tmp_path / "call.log",
        objective_cutoff=None,
    )
    assert options["IntegralityFocus"] == 1


def test_integrality_tolerance_may_be_tightened_below_the_snapshot_gate(
    tmp_path: Path,
) -> None:
    options = assemble_gurobi_options(
        _solver_config(options={"IntFeasTol": 1.0e-9}),
        native_log=tmp_path / "call.log",
        objective_cutoff=None,
    )
    assert options["IntFeasTol"] == pytest.approx(1.0e-9)
    assert options["FeasibilityTol"] == pytest.approx(1.0e-6)


@pytest.mark.parametrize(
    "frozen_key, value",
    [("Threads", 8), ("Seed", 7), ("MIPGap", 1.0e-2), ("TimeLimit", 10.0)],
)
def test_frozen_pilot_selection_cannot_be_overridden(
    tmp_path: Path, frozen_key: str, value: Any
) -> None:
    with pytest.raises(UnreadableSolverOptionError) as error:
        assemble_gurobi_options(
            _solver_config(options={frozen_key: value}),
            native_log=tmp_path / "call.log",
            objective_cutoff=None,
        )
    assert frozen_key in str(error.value)


def test_cutoff_stays_frozen_even_for_the_decision_stage(tmp_path: Path) -> None:
    with pytest.raises(UnreadableSolverOptionError):
        assemble_gurobi_options(
            _solver_config(options={"Cutoff": 1.0}),
            native_log=tmp_path / "call.log",
            objective_cutoff=1_163_877.341735611,
        )


def test_intfeastol_is_retunable_but_the_other_tolerances_are_not() -> None:
    assert "IntFeasTol" not in FROZEN_GUROBI_OPTION_KEYS
    assert {"FeasibilityTol", "OptimalityTol"} <= FROZEN_GUROBI_OPTION_KEYS


def _call_config_probe(options: dict[str, Any] | None) -> dict[str, Any]:
    """Exercise the frozen adapter's config builder as the runner patches it."""
    from types import SimpleNamespace

    from src.grid.rts_gmlc_formal_cg_adapter import FormalCgModelAdapter

    import experiments.run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_009_formal  # noqa: F401

    solver = _solver_config()
    for dropped in (
        "target_mip_relative_gap",
        "time_limit_seconds_per_call",
        "mip_min_logging_interval_seconds",
    ):
        solver.pop(dropped)
    if options is not None:
        solver["options"] = options
    adapter = SimpleNamespace(
        formal_solver={
            "solver": solver,
            "progress_logging": {
                "native_solver_log_interval_seconds": 5.0,
                "heartbeat_interval_seconds": 30.0,
            },
            "expected_full_model_size": {"variables": 1, "constraints": 1},
        },
        candidate_frontier={"cost_cap_absolute_tolerance_usd": 1.0e-4},
    )
    call = SimpleNamespace(target_relative_gap=1.0e-4, time_limit_seconds=7200.0)
    return FormalCgModelAdapter._call_config(adapter, call)


def test_frozen_adapter_no_longer_drops_configured_options() -> None:
    config = _call_config_probe({"IntegralityFocus": 1})
    assert config["solver"]["options"] == {"IntegralityFocus": 1}


def test_frozen_adapter_omits_the_key_when_nothing_is_configured() -> None:
    config = _call_config_probe(None)
    assert "options" not in config["solver"]


def test_runtime_options_refuses_frozen_overrides_directly(tmp_path: Path) -> None:
    with pytest.raises(UnreadableSolverOptionError):
        gurobi_runtime_options(
            mip_relative_gap=1.0e-4,
            threads=4,
            random_seed=0,
            feasibility_tolerance=1.0e-6,
            time_limit_seconds=7200.0,
            log_file=tmp_path / "call.log",
            mip_min_logging_interval_seconds=5.0,
            extra_options={"LogFile": "elsewhere.log"},
        )
