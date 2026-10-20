from __future__ import annotations

from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
import pytest
from pypower.api import case9, ppoption, runopf
from pypower.idx_brch import RATE_A
from pypower.idx_bus import VA, VM, VMAX, VMIN
from pypower.idx_gen import GEN_STATUS, PG, PMAX, QG, VG

from experiments import (
    run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_010_formal as formal,
)
from src.grid import rts_gmlc_ac_aware_commitment as core
from src.grid import rts_gmlc_ac_ipopt as shared_ipopt
from src.grid import rts_gmlc_ac_aware_commitment_v4_adapter as shared_adapter
from src.grid import (
    rts_gmlc_ac_aware_commitment_v4_repair_010_adapter as repair010_adapter,
)
from src.grid.rts_gmlc_ac_aware_commitment import (
    AcAwareChronology,
    AcAwareCommitmentUnit,
)
from src.grid.rts_gmlc_ac_recovery import prepare_ac_recovery_case


def _case9_input() -> tuple[tuple[object, ...], AcAwareChronology]:
    source = case9()
    source["bus"][:, VMIN] = 0.95
    source["bus"][:, VMAX] = 1.05
    source["branch"][:, RATE_A] = np.maximum(source["branch"][:, RATE_A], 250.0)
    baseline = runopf(deepcopy(source), ppoption(VERBOSE=0, OUT_ALL=0, OPF_ALG=560))
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


def test_shared_adapter_is_exact_historical_authority() -> None:
    assert formal._sha256(formal.SHARED_V4_ADAPTER_PATH) == (
        formal.SHARED_V4_ADAPTER_AUTHORITY_SHA256
    )
    assert not hasattr(shared_adapter, "calibrate_ac_aware_commitment_v4_startup")


def test_v2_preflight_loads_four_historical_checkpoint_contracts() -> None:
    config = formal._read_config()
    contract = config["startup_calibration"]

    assert contract["calibration_id"].endswith("_v2")
    assert contract["repair_004_checkpoint_authority"]["input_contract_sha256"] == (
        "4aaf38250e9a72ffcc475103ccad4f62781e8c17794425ad67986af744480e7b"
    )
    assert contract["predecessor_incomplete_evidence"]["solver_call_count"] == 0
    assert contract["predecessor_incomplete_evidence"]["resume_allowed"] is False


def test_v2_binding_records_both_adapter_authorities(tmp_path: Path) -> None:
    config = formal._read_config()
    audit = formal.FrontierSourceAudit(
        source_preregistration_manifest_sha256="1" * 64,
        source_frontier_manifest_sha256="2" * 64,
        source_preregistration_input_contract_sha256="3" * 64,
        source_frontier_input_contract_sha256="4" * 64,
        candidate_ids=tuple(f"candidate_{index:02d}" for index in range(7)),
        budget_checkpoint_manifest_sha256s=(),
        nested_round_manifest_count=22,
    )
    binding = formal.build_startup_calibration_binding(
        config_path=formal.DEFAULT_CONFIG_PATH,
        config=config,
        source_audit=audit,
        candidate_record={"commitment_sha256": "5" * 64, "dispatch_sha256": "6" * 64},
        native_log=tmp_path / "native.log",
        software_identity={"test": "tiny"},
    )

    assert binding["schema"].endswith("_v2")
    assert binding["shared_adapter_authority_sha256"] == (
        formal.SHARED_V4_ADAPTER_AUTHORITY_SHA256
    )
    assert (
        binding["repair_010_adapter_sha256"]
        == config["startup_calibration"]["repair_010_adapter_sha256"]
    )


def test_formal_input_contract_and_worker_binding_match_actual_dedicated_module(
    tmp_path: Path,
) -> None:
    config = formal._read_config()
    base = formal.v4._FrontierContext(
        config_path=tmp_path / "base.yaml",
        config={
            "formal_solver": {"progress_logging": {}},
            "joint_ac": {"runtime_control": {}},
        },
        zero=None,
        request=None,
        initial_state=None,
        selection=None,
        q_limits_by_uid={},
        output_root=tmp_path / "base",
        input_contract={"formal_successor": {}},
        input_contract_sha256="0" * 64,
    )
    context = formal._build_context_from_predecessor(
        formal.DEFAULT_CONFIG_PATH, config, base
    )
    implementation = context.input_contract["repair_010_implementation"]
    actual_dedicated_sha256 = formal._sha256(formal.REPAIR_010_ADAPTER_PATH)
    identity = formal._software_identity()
    binding = formal.build_worker_binding(
        preregistration_id="repair010",
        input_contract_sha256="1" * 64,
        frontier_manifest_sha256="2" * 64,
        call_manifest_sha256="3" * 64,
        candidate_id="candidate_00",
        commitment_sha256="4" * 64,
        dispatch_sha256="5" * 64,
        initial_strategy="source",
        prepared_inputs_sha256="6" * 64,
        ipopt_options_sha256="7" * 64,
        software_identity=identity,
    )

    assert implementation["repair_010_adapter_sha256"] == actual_dedicated_sha256
    assert identity["repair_010_adapter_sha256"] == actual_dedicated_sha256
    assert binding["software_identity"]["repair_010_adapter_sha256"] == (
        actual_dedicated_sha256
    )
    assert implementation["shared_adapter_authority_sha256"] == (
        formal.SHARED_V4_ADAPTER_AUTHORITY_SHA256
    )


def test_v2_preflight_rejects_adapter_or_checkpoint_authority_drift() -> None:
    config = formal._read_config()
    adapter_drift = deepcopy(config)
    adapter_drift["startup_calibration"]["shared_adapter_authority_sha256"] = "0" * 64
    with pytest.raises(RuntimeError, match="adapter authority drifted"):
        formal._verify_startup_calibration_v2_authority(adapter_drift)

    checkpoint_drift = deepcopy(config)
    checkpoint_drift["startup_calibration"]["repair_004_checkpoint_authority"][
        "input_contract_sha256"
    ] = ("0" * 64)
    with pytest.raises(RuntimeError, match="checkpoint authority drifted"):
        formal._verify_startup_calibration_v2_authority(checkpoint_drift)


def test_repair010_default_path_is_equivalent_to_shared_adapter(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[object, object, object, object]] = []
    sentinel = object()

    def fake_solve(
        cases: object,
        chronology: object,
        *,
        initial_strategy: object,
        solver_options: object,
    ) -> object:
        calls.append((cases, chronology, initial_strategy, solver_options))
        return sentinel

    monkeypatch.setattr(core, "solve_ac_aware_commitment", fake_solve)
    cases = (object(),)
    chronology = object()
    kwargs = {
        "base_options": shared_ipopt._FROZEN_IPOPT_OPTIONS,
        "runtime_options": {"ipopt.max_cpu_time": 7.0},
        "initial_strategy": "source",
    }
    shared_result = shared_adapter.solve_ac_aware_commitment_v4_worker(
        cases, chronology, **kwargs
    )
    dedicated_result = repair010_adapter.solve_ac_aware_commitment_v4_worker(
        cases, chronology, **kwargs
    )

    assert shared_result is dedicated_result is sentinel
    assert calls[0][:3] == calls[1][:3]
    assert calls[0][3] == calls[1][3]


def test_real_case9_calibration_constructs_factory_without_calling_solver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cases, chronology = _case9_input()
    calls = {"factory": 0, "callable": 0}

    class SpySolver:
        def __call__(self, **_kwargs: object) -> object:
            calls["callable"] += 1
            raise AssertionError("solver callable must remain unreachable")

        def stats(self) -> dict[str, object]:
            raise AssertionError("solver stats must remain unreachable")

    def spy_factory(
        name: str,
        plugin: str,
        problem: object,
        options: object,
    ) -> SpySolver:
        calls["factory"] += 1
        assert name == "ac_aware_commitment"
        assert plugin == "ipopt"
        assert problem is not None
        assert options is not None
        return SpySolver()

    monkeypatch.setattr(core.ca, "nlpsol", spy_factory)
    events: list[str] = []
    fingerprint = repair010_adapter.calibrate_ac_aware_commitment_v4_startup(
        cases,
        chronology,
        base_options=shared_ipopt._FROZEN_IPOPT_OPTIONS,
        runtime_options={},
        phase_observer=lambda event, _payload: events.append(event),
    )

    assert calls == {"factory": 1, "callable": 0}
    assert events == [
        "nlp_build_started",
        "nlp_build_completed",
        "calibration_pre_solver_stop",
    ]
    assert len(fingerprint["solver_input_fingerprint_sha256"]) == 64


def test_v2_roots_are_new_absent_and_v1_evidence_remains_present() -> None:
    contract = formal._read_config()["startup_calibration"]
    predecessor = contract["predecessor_incomplete_evidence"]

    assert Path(predecessor["output_directory"]).is_dir()
    assert Path(predecessor["logging_directory"]).is_dir()
    assert Path(predecessor["launcher_directory"]).is_dir()
    assert not Path(contract["output_directory"]).exists()
    assert not Path(contract["logging_directory"]).exists()
    assert not Path(contract["launcher_directory"]).exists()


def test_v1_config_and_launcher_root_cannot_authorize_v2() -> None:
    old_config = Path(
        "configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_010.yaml"
    )
    with pytest.raises(ValueError, match="frozen contract drifted"):
        formal._read_config(old_config)

    config = formal._read_config()
    old_launcher = Path(
        config["startup_calibration"]["predecessor_incomplete_evidence"][
            "launcher_directory"
        ]
    )
    with pytest.raises(
        formal.StartupCalibrationNoResumeError,
        match="launcher directory drifted",
    ):
        formal._verify_startup_calibration_launcher_authorization(
            launcher_directory=old_launcher,
            config_path=formal.DEFAULT_CONFIG_PATH,
            config=config,
        )
