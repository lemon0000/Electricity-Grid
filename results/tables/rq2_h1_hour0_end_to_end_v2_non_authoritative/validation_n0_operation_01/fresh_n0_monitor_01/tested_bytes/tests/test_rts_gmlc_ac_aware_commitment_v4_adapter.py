from __future__ import annotations

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest
from pypower.api import case9, ppoption, runopf
from pypower.idx_brch import RATE_A
from pypower.idx_bus import VA, VM, VMAX, VMIN
from pypower.idx_gen import GEN_STATUS, PG, PMAX, QG, VG

from src.grid import rts_gmlc_ac_aware_commitment as core
from src.grid import rts_gmlc_ac_ipopt as shared_ipopt
from src.grid.rts_gmlc_ac_aware_commitment import (
    AcAwareChronology,
    AcAwareCommitmentUnit,
)
from src.grid.rts_gmlc_ac_aware_commitment_v4_adapter import (
    solve_ac_aware_commitment_v4_worker,
)
from src.grid.rts_gmlc_ac_recovery import prepare_ac_recovery_case


def _base_options() -> dict[str, object]:
    return dict(shared_ipopt._FROZEN_IPOPT_OPTIONS)


def _small_case() -> tuple[tuple[object, ...], AcAwareChronology]:
    source = case9()
    source["bus"][:, VMIN] = 0.95
    source["bus"][:, VMAX] = 1.05
    source["branch"][:, RATE_A] = np.maximum(source["branch"][:, RATE_A], 250.0)
    baseline = runopf(
        deepcopy(source),
        ppoption(VERBOSE=0, OUT_ALL=0, OPF_ALG=560),
    )
    assert baseline["success"]
    source["bus"][:, (VM, VA)] = baseline["bus"][:, (VM, VA)]
    source["gen"][:, (PG, QG, VG)] = baseline["gen"][:, (PG, QG, VG)]
    targets = tuple(float(value) for value in baseline["gen"][:, PG])
    active_rows = tuple(np.flatnonzero(source["gen"][:, GEN_STATUS] > 0.0))
    prepared = prepare_ac_recovery_case(
        source,
        target_generation_mw_by_row=targets,
        generator_uid_by_row=("g1", "g2", "g3"),
        branch_uid_by_row=tuple(f"b{row}" for row in range(len(source["branch"]))),
        mode="distributed_committable",
        adjustable_generator_rows=active_rows,
        reference_generator_row=0,
        reference_generator_uid="g1",
        reference_bus=int(source["gen"][0, 0]),
    )
    units = tuple(
        AcAwareCommitmentUnit(
            generator_uid=uid,
            area=1,
            p_max_mw=float(source["gen"][row, PMAX]),
            ramp_mw_per_hour=1000.0,
            ramp_mw_per_minute=100.0,
            reserve_eligible=True,
            initial_generation_mw=targets[row],
            initial_commitment=True,
            commitment_by_hour=(True,),
            startup_by_hour=(False,),
            shutdown_by_hour=(False,),
        )
        for row, uid in enumerate(prepared.generator_uid_by_row)
    )
    chronology = AcAwareChronology(
        timestamps=(datetime(2020, 1, 1, tzinfo=UTC),),
        time_step_hours=1.0,
        units=units,
        spin_up_requirement_by_hour_area_mw=({1: 0.0},),
    )
    return (prepared,), chronology


def test_worker_adapter_writes_native_ipopt_log(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    cases, chronology = _small_case()
    original = core._FROZEN_IPOPT_OPTIONS
    monkeypatch.chdir(tmp_path)

    result = solve_ac_aware_commitment_v4_worker(
        cases,
        chronology,
        base_options=_base_options(),
        runtime_options={
            "ipopt.max_cpu_time": 30.0,
            "ipopt.output_file": "native_ipopt.log",
            "ipopt.file_print_level": 5,
        },
    )

    log_path = tmp_path / "native_ipopt.log"
    assert result.evaluated
    assert log_path.is_file()
    log_text = log_path.read_text(encoding="utf-8", errors="replace")
    assert "Ipopt" in log_text
    assert "EXIT:" in log_text
    assert core._FROZEN_IPOPT_OPTIONS is original


def test_base_options_require_type_strict_shared_equality() -> None:
    drifted = _base_options()
    drifted["print_time"] = 0

    with pytest.raises(ValueError, match="base IPOPT options drifted"):
        solve_ac_aware_commitment_v4_worker(
            (),
            object(),
            base_options=drifted,
            runtime_options={},
        )


def test_unknown_runtime_option_is_rejected() -> None:
    with pytest.raises(ValueError, match="Unknown V4 IPOPT runtime options"):
        solve_ac_aware_commitment_v4_worker(
            (),
            object(),
            base_options=_base_options(),
            runtime_options={"ipopt.linear_solver": "mumps"},
        )


@pytest.mark.parametrize(
    ("runtime_options", "message"),
    (
        ({"ipopt.max_cpu_time": 0.0}, "positive finite number"),
        ({"ipopt.max_cpu_time": float("inf")}, "positive finite number"),
        ({"ipopt.output_file": "IPOPT.LOG"}, "lowercase"),
        ({"ipopt.output_file": ""}, "nonempty lowercase string"),
        ({"ipopt.file_print_level": 1.0}, "must be an integer"),
        ({"ipopt.file_print_level": True}, "must be an integer"),
    ),
)
def test_runtime_option_values_are_validated(
    runtime_options: dict[str, object], message: str
) -> None:
    with pytest.raises(ValueError, match=message):
        solve_ac_aware_commitment_v4_worker(
            (),
            object(),
            base_options=_base_options(),
            runtime_options=runtime_options,
        )


def test_core_options_are_restored_after_solver_exception(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = core._FROZEN_IPOPT_OPTIONS
    original_snapshot = dict(original)

    def fail(*_args: object, **kwargs: object) -> object:
        assert core._FROZEN_IPOPT_OPTIONS is kwargs["solver_options"]
        assert core._FROZEN_IPOPT_OPTIONS["ipopt.output_file"] == "failure.log"
        raise RuntimeError("solver failed")

    monkeypatch.setattr(core, "solve_ac_aware_commitment", fail)

    with pytest.raises(RuntimeError, match="solver failed"):
        solve_ac_aware_commitment_v4_worker(
            (),
            object(),
            base_options=_base_options(),
            runtime_options={"ipopt.output_file": "failure.log"},
        )

    assert core._FROZEN_IPOPT_OPTIONS is original
    assert core._FROZEN_IPOPT_OPTIONS == original_snapshot
    assert shared_ipopt._FROZEN_IPOPT_OPTIONS is original


def test_worker_lock_serializes_concurrent_calls(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = core._FROZEN_IPOPT_OPTIONS
    state_lock = threading.Lock()
    active = 0
    maximum_active = 0

    def solve(*_args: object, **_kwargs: object) -> str:
        nonlocal active, maximum_active
        with state_lock:
            active += 1
            maximum_active = max(maximum_active, active)
        try:
            time.sleep(0.05)
            return str(core._FROZEN_IPOPT_OPTIONS["ipopt.output_file"])
        finally:
            with state_lock:
                active -= 1

    monkeypatch.setattr(core, "solve_ac_aware_commitment", solve)

    def run(filename: str) -> str:
        return solve_ac_aware_commitment_v4_worker(
            (),
            object(),
            base_options=_base_options(),
            runtime_options={"ipopt.output_file": filename},
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(run, ("first.log", "second.log")))

    assert results == ["first.log", "second.log"]
    assert maximum_active == 1
    assert core._FROZEN_IPOPT_OPTIONS is original
