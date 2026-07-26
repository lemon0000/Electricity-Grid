from __future__ import annotations

from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from experiments import run_rts_gmlc_zero_dc_ac_aware_commitment_v3 as runner
from src.grid.rts_gmlc_exact_cg import SharedSnapshot


def _candidate(
    requested_id: str,
    *,
    commitment_sha256: str,
    cost: float,
    delta: float,
) -> runner._Candidate:
    commitment = ({"g1": True},)
    return runner._Candidate(
        requested_candidate_id=requested_id,
        source="test",
        relative_cost_budget_delta=delta,
        cost_budget_usd=200.0,
        operating_cost_usd=cost,
        reactive_proxy_fraction=0.5,
        commitment_sha256=commitment_sha256,
        dispatch_sha256=f"dispatch-{requested_id}",
        commitment=commitment,
        startup=({"g1": False},),
        shutdown=({"g1": False},),
        generation_mw=({"g1": 10.0},),
        branch_flows_mw=({"b1": 1.0},),
        dc_flows_mw=({"d1": 0.0},),
        reserve_up_mw=({"g1": 1.0},),
        stage_audits={},
        residual_audit={},
    )


def test_config_freezes_nonadaptive_official_envelope() -> None:
    config = runner._read_config(
        Path("configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v3.yaml")
    )

    assert config["candidate_frontier"]["relative_cost_budget_deltas"] == [
        0.001,
        0.0025,
        0.005,
        0.01,
        0.02,
        0.05,
    ]
    assert config["joint_ac"]["voltage_limits_pu"] == [0.95, 1.05]
    assert config["joint_ac"]["voltage_bound_expansion_pu"] == 0.0
    assert config["joint_ac"]["reactive_power_bound_expansion_mvar"] == 0.0
    assert config["joint_ac"]["branch_rate_multiplier"] == 1.0
    assert config["formal_solver"]["algorithm"] == (
        "exact_selected_state_constraint_generation"
    )
    assert config["formal_solver"]["solver"] == {
        "name": "highs",
        "threads": 4,
        "random_seed": 0,
        "feasibility_tolerance": 1.0e-6,
        "bound_consistency_tolerance": 1.0e-6,
    }
    assert not any(config["forbidden_adaptivity"].values())


def test_config_freezes_actual_gap_time_log_and_audit_contract() -> None:
    config = runner._read_config(
        Path("configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v3.yaml")
    )
    formal = config["formal_solver"]
    proxy = formal["stages"]["proxy_maximization"]
    cost = formal["stages"]["cost_normalization"]

    assert proxy["gap_measure"] == "certified_bound_interval_width"
    assert proxy["target_relative_gap"] == 1.0e-4
    assert proxy["maximum_accepted_absolute_gap"] == 1.0e-3
    assert proxy["maximum_accepted_relative_gap_to_feasible_incumbent"] == 1.0e-3
    assert cost["gap_measure"] == "certified_bound_interval_width"
    assert cost["target_relative_gap"] == 1.0e-4
    assert cost["maximum_accepted_absolute_gap"] is None
    assert cost["maximum_accepted_relative_gap_to_feasible_incumbent"] == 1.0e-3
    assert cost["restart_constraint_generation_from_frozen_seed"]
    assert formal["primary_regret"]["hard_maximum"] == pytest.approx(
        1.0e-3 + 1.0e-7 + 1.0e-6
    )
    assert formal["time_limits_seconds"] == {
        "per_candidate_total": 43200.0,
        "proxy_master_per_call": 7200.0,
        "cost_master_per_call": 7200.0,
        "inactive_state_screen_per_call": 300.0,
        "final_full_state_audit_per_call": 1800.0,
    }
    assert formal["progress_logging"]["heartbeat_interval_seconds"] == 30.0
    assert formal["progress_logging"]["native_solver_log_interval_seconds"] == 5.0
    assert formal["progress_logging"][
        "report_actual_lower_bound_upper_bound_interval_and_gap"
    ]
    assert formal["final_audit"]["selected_state_count"] == 24
    assert formal["final_audit"]["required_after_each_stage"]


def test_config_freezes_discrete_only_snapshot_normalization() -> None:
    config = runner._read_config(
        Path("configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v3.yaml")
    )
    snapshot = config["candidate_snapshot"]

    assert snapshot["discrete_components"] == ["commitment", "startup", "shutdown"]
    assert snapshot["maximum_distance_to_nearest_binary_before_normalization"] == (
        1.0e-8
    )
    assert snapshot["continuous_values_use_full_precision"]
    assert not snapshot["continuous_rounding_or_clamping_allowed"]
    assert snapshot["normalized_snapshot_requires_new_24_state_final_audit"]


def test_published_solver_predecessors_pass_content_and_manifest_gates() -> None:
    config = runner._read_config(
        Path("configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v3.yaml")
    )

    verified = runner._verify_solver_predecessors(config)

    assert verified["v2_operational_termination"] == {
        "manifest_sha256": (
            "e8bcef7466a1dfa44e4c0a444eb297fbf7160cf1f7596485c86a6fd9984b799b"
        ),
        "status": (
            "terminated_before_candidate_frontier_publication_and_before_any_"
            "joint_ac_solver_call"
        ),
        "candidate_frontier_artifact_published": False,
        "partial_candidate_solution_persisted": False,
        "joint_ac_solver_call_count": 0,
        "termination_is_infeasibility_evidence": False,
    }
    assert verified["solver_inventory"]["only_formally_eligible_solver"] == "highs"
    assert verified["thread_benchmark"]["selected_threads"] == 4
    assert verified["formulation_pilot"]["selected_formulation"] == (
        "exact_selected_state_constraint_generation"
    )
    assert verified["formulation_pilot"]["eligible_repetitions"] == 2


def test_config_rejects_manual_failed_hours(tmp_path: Path) -> None:
    source = Path("configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v3.yaml")
    config = yaml.safe_load(source.read_text(encoding="utf-8"))
    config["forbidden_adaptivity"]["manual_failed_hours_allowed"] = True
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="forbidden adaptivity"):
        runner._read_config(path)


@pytest.mark.parametrize(
    ("section", "nested_key", "replacement", "message"),
    (
        (
            "solver_selection_provenance",
            ("formulation_pilot", "selected_formulation"),
            "full_state_monolith",
            "solver-selection provenance",
        ),
        (
            "formal_solver",
            ("solver", "threads"),
            8,
            "formal solver contract",
        ),
        (
            "formal_solver",
            ("stages", "proxy_maximization", "maximum_accepted_absolute_gap"),
            0.01,
            "formal solver contract",
        ),
        (
            "candidate_snapshot",
            ("continuous_rounding_or_clamping_allowed",),
            True,
            "candidate snapshot contract",
        ),
    ),
)
def test_config_rejects_frozen_solver_contract_drift(
    tmp_path: Path,
    section: str,
    nested_key: tuple[str, ...],
    replacement: object,
    message: str,
) -> None:
    source = Path("configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v3.yaml")
    config = yaml.safe_load(source.read_text(encoding="utf-8"))
    target = config[section]
    for key in nested_key[:-1]:
        target = target[key]
    target[nested_key[-1]] = replacement
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match=message):
        runner._read_config(path)


def test_config_rejects_reserve_scope_drift(tmp_path: Path) -> None:
    source = Path("configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v3.yaml")
    config = yaml.safe_load(source.read_text(encoding="utf-8"))
    config["joint_ac"]["reserve_eligible_categories"] = ["Coal"]
    path = tmp_path / "invalid.yaml"
    path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")

    with pytest.raises(ValueError, match="joint AC contract"):
        runner._read_config(path)


def test_joint_csv_schemas_have_unique_fields() -> None:
    schemas = (
        runner._JOINT_RUN_FIELDS,
        runner._JOINT_HOUR_FIELDS,
        runner._JOINT_GENERATOR_FIELDS,
        runner._JOINT_BUS_FIELDS,
        runner._JOINT_BRANCH_FIELDS,
        runner._JOINT_RESERVE_FIELDS,
    )

    assert all(len(fields) == len(set(fields)) for fields in schemas)


def test_csv_round_trip_preserves_dispatch_hash(tmp_path: Path) -> None:
    generation = ({"g1": float.fromhex("0x1.0000000000001p+0")},)
    branches = ({"b1": float.fromhex("0x1.0000000000001p-1")},)
    dc_flows = ({"d1": float.fromhex("0x1.0000000000001p-2")},)
    expected_hash = runner._dispatch_sha256(generation, branches, dc_flows)
    timestamp = "2020-01-01T00:00:00+00:00"
    runner._write_csv(
        tmp_path / "generation.csv",
        runner._GENERATION_FIELDS,
        [
            {
                "candidate_id": "candidate_00",
                "hour_index": 0,
                "timestamp": timestamp,
                "generator_uid": "g1",
                "generation_mw": generation[0]["g1"],
            }
        ],
    )
    runner._write_csv(
        tmp_path / "branches.csv",
        runner._BRANCH_FIELDS,
        [
            {
                "candidate_id": "candidate_00",
                "hour_index": 0,
                "timestamp": timestamp,
                "branch_uid": "b1",
                "flow_mw": branches[0]["b1"],
            }
        ],
    )
    runner._write_csv(
        tmp_path / "dc.csv",
        runner._DC_FLOW_FIELDS,
        [
            {
                "candidate_id": "candidate_00",
                "hour_index": 0,
                "timestamp": timestamp,
                "dc_branch_uid": "d1",
                "flow_mw": dc_flows[0]["d1"],
            }
        ],
    )

    loaded_generation = runner._csv_rows(
        tmp_path / "generation.csv", runner._GENERATION_FIELDS
    )
    loaded_branches = runner._csv_rows(tmp_path / "branches.csv", runner._BRANCH_FIELDS)
    loaded_dc = runner._csv_rows(tmp_path / "dc.csv", runner._DC_FLOW_FIELDS)
    observed_hash = runner._dispatch_sha256(
        ({"g1": float(loaded_generation[0]["generation_mw"])},),
        ({"b1": float(loaded_branches[0]["flow_mw"])},),
        ({"d1": float(loaded_dc[0]["flow_mw"])},),
    )

    assert observed_hash == expected_hash


def test_boolean_transitions_use_one_frozen_initial_state() -> None:
    commitment = (
        {"g1": False, "g2": True},
        {"g1": True, "g2": True},
        {"g1": True, "g2": False},
    )

    startup, shutdown = runner._boolean_transitions(
        commitment, {"g1": False, "g2": False}
    )

    assert startup == (
        {"g1": False, "g2": True},
        {"g1": True, "g2": False},
        {"g1": False, "g2": False},
    )
    assert shutdown == (
        {"g1": False, "g2": False},
        {"g1": False, "g2": False},
        {"g1": False, "g2": True},
    )


def test_proxy_is_minimum_over_hours_areas_and_both_q_directions() -> None:
    generators = (
        SimpleNamespace(
            uid="g1",
            bus=101,
            unit_type="STEAM",
            enabled=True,
            dispatch_mode="committable",
        ),
        SimpleNamespace(
            uid="s1",
            bus=102,
            unit_type="SYNC_COND",
            enabled=False,
            dispatch_mode="disabled",
        ),
        SimpleNamespace(
            uid="s2",
            bus=201,
            unit_type="SYNC_COND",
            enabled=False,
            dispatch_mode="disabled",
        ),
        SimpleNamespace(
            uid="s3",
            bus=301,
            unit_type="SYNC_COND",
            enabled=False,
            dispatch_mode="disabled",
        ),
    )
    buses = (
        SimpleNamespace(uid=101, area=1),
        SimpleNamespace(uid=102, area=1),
        SimpleNamespace(uid=201, area=2),
        SimpleNamespace(uid=301, area=3),
    )
    points = (
        SimpleNamespace(
            generator_max_mw={uid: 1.0 for uid in ("g1", "s1", "s2", "s3")}
        ),
        SimpleNamespace(
            generator_max_mw={uid: 1.0 for uid in ("g1", "s1", "s2", "s3")}
        ),
    )
    context = SimpleNamespace(
        zero=SimpleNamespace(
            scan=SimpleNamespace(
                data=SimpleNamespace(generators=generators, buses=buses)
            )
        ),
        q_limits_by_uid={
            "g1": (-20.0, 40.0),
            "s1": (-20.0, 40.0),
            "s2": (-10.0, 10.0),
            "s3": (-10.0, 10.0),
        },
        config={"candidate_frontier": {"areas": [1, 2, 3]}},
    )

    value = runner._reactive_proxy_value(
        context,
        points,
        ({"g1": True}, {"g1": False}),
    )

    # Area 1 at hour 2 retains only the synchronous condenser: 40/(40+40)
    # injection and 20/(20+20) absorption. Other area-hour-directions are 1.
    assert value == pytest.approx(0.5)


def test_commitment_dedup_keeps_lowest_cost_then_budget() -> None:
    duplicate_expensive = _candidate(
        "delta_1", commitment_sha256="same", cost=110.0, delta=0.01
    )
    duplicate_winner = _candidate(
        "delta_2", commitment_sha256="same", cost=100.0, delta=0.02
    )
    distinct = _candidate("delta_3", commitment_sha256="other", cost=120.0, delta=0.03)

    rows, selected = runner._deduplicate_candidates(
        (duplicate_expensive, duplicate_winner, distinct)
    )

    assert len(selected) == 2
    row_by_requested = {row["requested_candidate_id"]: row for row in rows}
    assert not row_by_requested["delta_1"]["selected_unique_candidate"]
    assert row_by_requested["delta_1"]["duplicate_of_candidate_id"]
    assert row_by_requested["delta_2"]["selected_unique_candidate"]
    assert row_by_requested["delta_3"]["selected_unique_candidate"]


def test_candidate_checkpoint_round_trip_is_manifested_and_idempotent(
    tmp_path: Path,
) -> None:
    candidate = _candidate(
        "delta_1",
        commitment_sha256=runner._commitment_sha256(({"g1": True},)),
        cost=100.0,
        delta=0.01,
    )
    candidate = replace(
        candidate,
        dispatch_sha256=runner._dispatch_sha256(
            candidate.generation_mw,
            candidate.branch_flows_mw,
            candidate.dc_flows_mw,
        ),
    )
    context = SimpleNamespace(
        config={"preregistration": {"id": "experiment-v3"}},
        input_contract_sha256="a" * 64,
    )

    first = runner._save_candidate_checkpoint(context, tmp_path, 1, candidate)
    second = runner._load_candidate_checkpoint(context, tmp_path, 1, "delta_1")

    assert first == candidate
    assert second == candidate
    assert (tmp_path / "candidate_checkpoints" / "01_delta_1" / "SHA256SUMS").is_file()


def _valid_candidate(requested_id: str, delta: float) -> runner._Candidate:
    candidate = _candidate(
        requested_id,
        commitment_sha256=runner._commitment_sha256(({"g1": True},)),
        cost=100.0 + delta,
        delta=delta,
    )
    return replace(
        candidate,
        dispatch_sha256=runner._dispatch_sha256(
            candidate.generation_mw,
            candidate.branch_flows_mw,
            candidate.dc_flows_mw,
        ),
    )


def test_formal_candidate_checkpoint_requires_complete_stage_certificates() -> None:
    candidate = replace(
        _valid_candidate("formal", 0.1),
        source="q_proxy_exact_selected_state_constraint_generation",
    )

    with pytest.raises(RuntimeError, match="stage audit"):
        runner._candidate_from_checkpoint_payload(
            runner._stable_json(asdict(candidate))
        )


def test_formal_candidate_wiring_restarts_cost_cg_and_audits_primary_regret(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    context = SimpleNamespace(
        config={
            "candidate_frontier": {
                "cost_cap_absolute_tolerance_usd": 1.0e-4,
            },
            "formal_solver": {
                "solver": {"feasibility_tolerance": 1.0e-6},
                "stages": {
                    "proxy_maximization": {
                        "target_relative_gap": 1.0e-4,
                        "maximum_accepted_relative_gap_to_feasible_incumbent": 1.0e-3,
                        "maximum_accepted_absolute_gap": 1.0e-3,
                    },
                    "cost_normalization": {
                        "target_relative_gap": 1.0e-4,
                        "maximum_accepted_relative_gap_to_feasible_incumbent": 1.0e-3,
                        "maximum_accepted_absolute_gap": None,
                        "proxy_floor_absolute_tolerance": 1.0e-7,
                    },
                },
                "time_limits_seconds": {
                    "proxy_master_per_call": 10.0,
                    "cost_master_per_call": 10.0,
                    "inactive_state_screen_per_call": 2.0,
                    "final_full_state_audit_per_call": 3.0,
                },
                "primary_regret": {
                    "proxy_floor_tolerance": 1.0e-7,
                    "numerical_audit_allowance": 1.0e-6,
                    "hard_maximum": 0.0010011,
                },
            },
            "candidate_snapshot": {},
            "parent_zero_control": {"baseline_full_state_cost_usd": 100.0},
        },
        initial_state=SimpleNamespace(commitment={"g1": False}),
    )
    problem = SimpleNamespace(
        all_state_ids=("normal", "s1", "s2"),
        initial_active_state_ids=("normal", "s1"),
        points=(object(),),
        cost_budget_usd=110.0,
    )
    final_model = SimpleNamespace(operating_cost=100.0)
    final_handle = SimpleNamespace(model=final_model, scuc_context=object())

    class FakeAdapter:
        def __init__(self, **_kwargs: object) -> None:
            self.final_handles = {"cost_normalization": final_handle}

        def callbacks(self) -> object:
            return object()

    calls: list[dict[str, object]] = []
    proxy_snapshot = SharedSnapshot((), "a" * 64, 0.8, 101.0)
    cost_snapshot = SharedSnapshot((), "b" * 64, 0.7999999, 100.0)

    def run_stage(**kwargs: object) -> SimpleNamespace:
        calls.append(kwargs)
        if kwargs["stage"] == "proxy_maximization":
            return SimpleNamespace(
                snapshot=proxy_snapshot,
                stage_record={
                    "certificate": {
                        "valid": True,
                        "lower_bound": 0.8,
                        "upper_bound": 0.8002,
                        "absolute_gap": 0.0002,
                    }
                },
            )
        return SimpleNamespace(
            snapshot=cost_snapshot,
            stage_record={
                "certificate": {
                    "valid": True,
                    "lower_bound": 99.99,
                    "upper_bound": 100.0,
                    "absolute_gap": 0.01,
                },
                "final_full_state_audit": {
                    "callback_record": {"residual_audit": {"passed": True}}
                },
            },
        )

    monkeypatch.setattr(runner, "_formal_problem", lambda *_args, **_kwargs: problem)
    monkeypatch.setattr(runner, "FormalCgModelAdapter", FakeAdapter)
    monkeypatch.setattr(runner, "run_exact_cg_stage", run_stage)
    monkeypatch.setattr(runner, "_extract_commitment", lambda *_args: ({"g1": True},))
    monkeypatch.setattr(runner, "_extract_generation", lambda *_args: ({"g1": 10.0},))
    monkeypatch.setattr(runner, "_extract_branch_flows", lambda *_args: ({"b1": 1.0},))
    monkeypatch.setattr(runner, "_extract_dc_flows", lambda *_args: ({"d1": 0.0},))
    monkeypatch.setattr(runner, "_extract_reserve", lambda *_args: ({"g1": 1.0},))
    monkeypatch.setattr(runner, "_reactive_proxy_value", lambda *_args: 0.8)

    candidate = runner._solve_frontier_candidate(
        context,
        relative_delta=0.1,
        progress=SimpleNamespace(),
        candidate_log_root=Path("unused"),
        candidate_ordinal=1,
        deadline_monotonic=100.0,
    )

    assert [call["stage"] for call in calls] == [
        "proxy_maximization",
        "cost_normalization",
    ]
    assert calls[0]["seed_state_ids"] == calls[1]["seed_state_ids"]
    assert calls[1]["proxy_floor"] == pytest.approx(0.7999999)
    assert candidate.stage_audits["primary_proxy_regret"]["passed"]
    assert candidate.operating_cost_usd == 100.0


def test_candidate_generation_resumes_from_atomic_candidate_checkpoint(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    output_root = tmp_path / "results"
    log_root = tmp_path / "logs"
    deltas = (0.1, 0.2)
    context = SimpleNamespace(
        config_path=Path("test-config.yaml"),
        config={
            "preregistration": {"id": "experiment-v3"},
            "formal_solver": {
                "algorithm": "exact_selected_state_constraint_generation",
                "solver": {"name": "highs", "threads": 4},
                "progress_logging": {"log_directory": str(log_root)},
                "time_limits_seconds": {"per_candidate_total": 10.0},
            },
            "candidate_frontier": {
                "relative_cost_budget_deltas": list(deltas),
            },
            "evidence": {"formal_candidate_result": False},
        },
        output_root=output_root,
        input_contract_sha256="a" * 64,
        request=SimpleNamespace(
            timestamps=(datetime(2020, 1, 1, tzinfo=timezone.utc),)
        ),
    )
    baseline = _valid_candidate("parent", 0.0)
    solved_deltas: list[float] = []
    fail_second = True

    def solve_candidate(
        _context: object, *, relative_delta: float, **_kwargs: object
    ) -> runner._Candidate:
        nonlocal fail_second
        solved_deltas.append(relative_delta)
        if relative_delta == deltas[1] and fail_second:
            fail_second = False
            raise RuntimeError("simulated interruption")
        return _valid_candidate(
            runner._requested_candidate_id(relative_delta), relative_delta
        )

    monkeypatch.setattr(runner, "_build_context", lambda _path: context)
    monkeypatch.setattr(
        runner,
        "_require_preregistration",
        lambda _context, _root: {"input_contract_sha256": "a" * 64},
    )
    monkeypatch.setattr(runner, "_baseline_candidate", lambda _context: baseline)
    monkeypatch.setattr(runner, "_solve_frontier_candidate", solve_candidate)

    with pytest.raises(RuntimeError, match="simulated interruption"):
        runner.generate_candidate_frontier(
            Path("test-config.yaml"), attempt_id="attempt-1"
        )

    first_id = runner._requested_candidate_id(deltas[0])
    first_checkpoint = runner._candidate_checkpoint_path(output_root, 1, first_id)
    assert (first_checkpoint / "SHA256SUMS").is_file()
    assert not (output_root / "candidate_frontier").exists()

    summary = runner.generate_candidate_frontier(
        Path("test-config.yaml"), attempt_id="attempt-2"
    )

    assert solved_deltas == [0.1, 0.2, 0.2]
    assert summary["requested_candidate_count"] == 3
    assert len(summary["candidate_checkpoint_manifest_sha256s"]) == 2
    progress_rows = (log_root / "attempt-2" / "progress.jsonl").read_text(
        encoding="utf-8"
    )
    assert "candidate_checkpoint_loaded" in progress_rows
    assert "frontier_published" in progress_rows
