from __future__ import annotations

import shutil
from copy import deepcopy
from dataclasses import asdict, replace
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml

from experiments import run_rts_gmlc_zero_dc_ac_aware_commitment_v4 as runner
from experiments.run_rts_gmlc_multi_poi_scan import _write_json as _write_rounded_json
from src.grid.rts_gmlc_exact_cg import SharedSnapshot
from src.grid.rts_gmlc_exact_cg_runner import ExactCgCall


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
        Path("configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4.yaml")
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
        Path("configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4.yaml")
    )
    formal = config["formal_solver"]
    reporting = formal["optimality_reporting"]
    proxy = formal["stages"]["proxy_maximization"]
    cost = formal["stages"]["cost_normalization"]
    joint_runtime = config["joint_ac"]["runtime_control"]

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
    assert reporting["reported_interval"] == ("actual_certified_lower_and_upper_bounds")
    assert reporting["actual_interval_recomputed_for_every_completed_stage"]
    assert reporting["target_and_maximum_acceptance_frozen_before_formal_start"]
    assert not reporting["post_result_threshold_relaxation_allowed"]
    assert joint_runtime == {
        "max_cpu_time_seconds_per_call": 7200.0,
        "max_wall_time_seconds_per_call": 7500.0,
        "heartbeat_interval_seconds": 30.0,
        "parent_watchdog_interval_seconds": 5.0,
        "termination_grace_seconds": 30.0,
        "native_file_print_level": 5,
        "native_solver_logs_required": True,
        "checkpoint_each_completed_call": True,
        "retry_incomplete_call_allowed": False,
        "isolated_worker_process_required": True,
        "worker_pid_event_required": True,
        "log_directory": (
            "results/logs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4"
        ),
    }


def test_config_freezes_discrete_only_snapshot_normalization() -> None:
    config = runner._read_config(
        Path("configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4.yaml")
    )
    snapshot = config["candidate_snapshot"]

    assert snapshot["discrete_components"] == ["commitment", "startup", "shutdown"]
    assert snapshot["maximum_distance_to_nearest_binary_before_normalization"] == (
        1.0e-8
    )
    assert snapshot["continuous_values_use_full_precision"]
    assert not snapshot["continuous_rounding_or_clamping_allowed"]
    assert snapshot["normalized_snapshot_requires_new_24_state_final_audit"]
    assert snapshot["checkpoint_schema"] == runner._CHECKPOINT_SCHEMA
    assert snapshot["checkpoint_float_serialization"] == (
        runner._CHECKPOINT_FLOAT_SERIALIZATION
    )
    assert snapshot["checkpoint_prepublication_roundtrip_identity_validation"]
    assert not snapshot["checkpoint_existing_target_overwrite_allowed"]
    assert snapshot["frontier_continuous_json_uses_full_precision"]


def test_published_solver_predecessors_pass_content_and_manifest_gates() -> None:
    config = runner._read_config(
        Path("configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4.yaml")
    )

    verified = runner._verify_solver_predecessors(config)

    assert verified["v3_checkpoint_invalidation"] == {
        "manifest_sha256": (
            "30a112dc9c074533f7dbef07e0eb1508c85f6808f1af68631497b8104f1da548"
        ),
        "status": (
            "invalidated_after_one_semantically_invalid_budget_checkpoint_was_"
            "persisted_before_any_valid_budget_checkpoint_frontier_or_joint_ac_"
            "solver_call"
        ),
        "valid_budget_candidate_checkpoint_count": 0,
        "invalid_budget_candidate_checkpoint_count": 1,
        "candidate_frontier_artifact_published": False,
        "joint_ac_solver_call_count": 0,
        "v3_resume_allowed": False,
    }
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
    assert verified["initial_proxy_warm_start"] == {
        "preparation_manifest_sha256": (
            "99ed1475e9f4d69af50eb418753d09d311bba4f0d6bb81eeefbf0b2fdf93aa83"
        ),
        "result_manifest_sha256": (
            "e6b906a9038b51db08ca1f1775ac028a9cc221532d0b5c24e324d538797d23d2"
        ),
        "selected_method": "appsi_highs_full_mip_start",
        "selection_status": "selected_by_preregistered_nonobjective_runtime_rule",
        "eligible_repetitions": 2,
    }


def test_initial_proxy_warm_start_rejects_tampered_published_summary_hash() -> None:
    config = runner._read_config(
        Path("configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4.yaml")
    )
    provenance = config["solver_selection_provenance"]
    provenance["initial_proxy_warm_start"] = {
        **provenance["initial_proxy_warm_start"],
        "summary_sha256": "0" * 64,
    }

    with pytest.raises(RuntimeError, match="warm-start summary hash drifted"):
        runner._verify_solver_predecessors(config)


def test_initial_proxy_warm_start_is_limited_to_first_proxy_master() -> None:
    adapter = object.__new__(runner.V4InitialProxyWarmStartAdapter)
    adapter._warm_start = {
        "application_scope": "initial_proxy_maximization_master_only"
    }
    initial = ExactCgCall(
        call_id="proxy_maximization.iteration_01.master",
        kind="master",
        stage="proxy_maximization",
        iteration=1,
        active_state_ids=("normal",),
        all_state_ids=("normal",),
        time_limit_seconds=1.0,
        target_relative_gap=1.0e-4,
        proxy_floor=None,
    )

    assert adapter._is_initial_proxy_master(initial)
    assert not adapter._is_initial_proxy_master(
        replace(initial, iteration=0, call_id="proxy_maximization.iteration_00.master")
    )
    assert not adapter._is_initial_proxy_master(
        replace(initial, iteration=2, call_id="proxy_maximization.iteration_02.master")
    )
    assert not adapter._is_initial_proxy_master(
        replace(initial, kind="screen", state_id="s1")
    )
    assert not adapter._is_initial_proxy_master(replace(initial, kind="final_audit"))
    assert not adapter._is_initial_proxy_master(
        replace(initial, stage="cost_normalization", proxy_floor=0.2)
    )


def test_v3_predecessor_rejects_an_extra_checkpoint_directory(
    tmp_path: Path,
) -> None:
    config = runner._read_config(
        Path("configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4.yaml")
    )
    copied_root = tmp_path / "v3"
    shutil.copytree(Path(config["predecessor_v3"]["root"]), copied_root)
    (copied_root / "candidate_checkpoints" / "02_unregistered").mkdir()
    config["predecessor_v3"] = {
        **config["predecessor_v3"],
        "root": str(copied_root),
    }

    with pytest.raises(RuntimeError, match="checkpoint inventory drifted"):
        runner._verify_v3_predecessor(config)


def test_historical_v4_prepare_rejects_successor_implementation_drift(
    tmp_path: Path,
) -> None:
    config_path = Path(
        "configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4.yaml"
    )
    output_root = tmp_path / "v4"
    context = runner._build_context(config_path)
    parent_contract = runner._repair_parent_registration()["input_contract"]

    assert runner._json_delta_paths(parent_contract, context.input_contract) == (
        "implementation_sha256.experiments/pilot_rts_gmlc_zero_dc_ac_aware_formulations.py",
        "implementation_sha256.experiments/run_rts_gmlc_zero_dc_ac_aware_commitment_v4.py",
        "implementation_sha256.src/grid/rts_gmlc_exact_cg.py",
        "implementation_sha256.src/grid/rts_gmlc_exact_cg_runner.py",
        "implementation_sha256.src/grid/rts_gmlc_formal_cg_adapter.py",
        "implementation_sha256.src/grid/rts_gmlc_v4_initial_proxy_warmstart.py",
    )
    with pytest.raises(
        RuntimeError, match="exceeded its registered implementation scope"
    ):
        runner.prepare_preregistration(config_path, output_directory=output_root)
    assert not (output_root / "preregistration").exists()


def test_historical_v4_rejects_additional_implementation_tamper(
    tmp_path: Path,
) -> None:
    config_path = Path(
        "configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4.yaml"
    )
    context = runner._build_context(config_path)
    drifted_contract = deepcopy(context.input_contract)
    drifted_contract["implementation_sha256"][
        "experiments/monitor_rts_gmlc_zero_dc_ac_aware_commitment_v4.py"
    ] = ("0" * 64)
    drifted_context = replace(
        context,
        input_contract=drifted_contract,
        input_contract_sha256=runner.common_input_signature_sha256(drifted_contract),
    )
    with pytest.raises(
        RuntimeError, match="exceeded its registered implementation scope"
    ):
        runner._repair_amendment_payload(drifted_context, tmp_path / "other-v4")


def test_config_rejects_manual_failed_hours(tmp_path: Path) -> None:
    source = Path("configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4.yaml")
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
    source = Path("configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4.yaml")
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
    source = Path("configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4.yaml")
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


def test_v3_frontier_schema_is_rejected_before_detail_loading(
    tmp_path: Path,
) -> None:
    root = tmp_path / "candidate_frontier"
    runner._publish_immutable_payload(
        root,
        lambda staging: runner._write_exact_json(
            staging / "summary.json",
            {
                "schema": "rts_gmlc_zero_dc_ac_aware_candidate_frontier_v3",
                "input_contract_sha256": "a" * 64,
            },
        ),
    )
    context = SimpleNamespace(input_contract_sha256="a" * 64)

    with pytest.raises(RuntimeError, match="candidate summary drifted"):
        runner._load_candidate_frontier(context, tmp_path)


def test_v3_joint_schema_is_rejected_before_csv_loading(tmp_path: Path) -> None:
    target = tmp_path / "joint_ac"
    runner._publish_immutable_payload(
        target,
        lambda staging: runner._write_exact_json(
            staging / "summary.json",
            {"schema": "rts_gmlc_zero_dc_ac_aware_joint_ac_results_v3"},
        ),
    )

    with pytest.raises(RuntimeError, match="joint schema drifted"):
        runner._load_joint_results(SimpleNamespace(), target, {}, (), "a" * 64, {}, {})


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
        config={"preregistration": {"id": "experiment-v4"}},
        input_contract_sha256="a" * 64,
    )

    first = runner._save_candidate_checkpoint(context, tmp_path, 1, candidate)
    second = runner._save_candidate_checkpoint(context, tmp_path, 1, candidate)
    loaded = runner._load_candidate_checkpoint(context, tmp_path, 1, "delta_1")

    assert first == candidate
    assert second == candidate
    assert loaded == candidate
    assert (tmp_path / "candidate_checkpoints" / "01_delta_1" / "SHA256SUMS").is_file()


def test_immutable_publisher_never_replaces_a_concurrently_created_target(
    tmp_path: Path,
) -> None:
    target = tmp_path / "artifact"

    def writer(staging: Path) -> None:
        runner._write_exact_json(staging / "payload.json", {"value": 1.0})
        target.mkdir()
        (target / "sentinel.txt").write_text("keep", encoding="utf-8")

    with pytest.raises(FileExistsError, match="already exists"):
        runner._publish_immutable_payload(target, writer)

    assert (target / "sentinel.txt").read_text(encoding="utf-8") == "keep"
    assert not tuple(tmp_path.glob(".artifact.processing-*"))


def test_candidate_checkpoint_preserves_full_precision_and_negative_zero(
    tmp_path: Path,
) -> None:
    candidate = _candidate(
        "delta_1",
        commitment_sha256=runner._commitment_sha256(({"g1": True},)),
        cost=100.98765432109876,
        delta=0.12345678901234568,
    )
    generation = ({"g1": 1.2345678901234567},)
    branch_flows = ({"b1": -987.6543210987654},)
    dc_flows = ({"d1": -0.0},)
    candidate = replace(
        candidate,
        generation_mw=generation,
        branch_flows_mw=branch_flows,
        dc_flows_mw=dc_flows,
        reserve_up_mw=({"g1": 2.345678901234567},),
        reactive_proxy_fraction=0.5000000001234568,
        dispatch_sha256=runner._dispatch_sha256(generation, branch_flows, dc_flows),
    )
    context = SimpleNamespace(
        config={"preregistration": {"id": "experiment-v4"}},
        input_contract_sha256="a" * 64,
    )

    runner._save_candidate_checkpoint(context, tmp_path, 1, candidate)
    loaded = runner._load_candidate_checkpoint(context, tmp_path, 1, "delta_1")

    assert loaded is not None
    assert loaded.dispatch_sha256 == candidate.dispatch_sha256
    assert loaded.generation_mw[0]["g1"].hex() == generation[0]["g1"].hex()
    assert loaded.branch_flows_mw[0]["b1"].hex() == branch_flows[0]["b1"].hex()
    assert loaded.dc_flows_mw[0]["d1"].hex() == (-0.0).hex()
    assert loaded.operating_cost_usd.hex() == candidate.operating_cost_usd.hex()
    assert loaded.reactive_proxy_fraction.hex() == (
        candidate.reactive_proxy_fraction.hex()
    )


def test_candidate_checkpoint_normalizes_nested_audit_tuples(
    tmp_path: Path,
) -> None:
    candidate = _valid_candidate("delta_1", 0.1)
    candidate = replace(
        candidate,
        stage_audits={"nested": {"state_ids": ("normal", "branch_A11")}},
        residual_audit={"commitment_feasible_by_step": (True,)},
    )
    context = SimpleNamespace(
        config={"preregistration": {"id": "experiment-v4"}},
        input_contract_sha256="a" * 64,
    )

    saved = runner._save_candidate_checkpoint(context, tmp_path, 1, candidate)
    loaded = runner._load_candidate_checkpoint(context, tmp_path, 1, "delta_1")

    assert saved == loaded
    assert saved != candidate
    assert saved.stage_audits["nested"]["state_ids"] == ["normal", "branch_A11"]
    assert saved.residual_audit["commitment_feasible_by_step"] == [True]


def test_existing_different_checkpoint_is_rejected_without_rewrite(
    tmp_path: Path,
) -> None:
    candidate = _valid_candidate("delta_1", 0.1)
    context = SimpleNamespace(
        config={"preregistration": {"id": "experiment-v4"}},
        input_contract_sha256="a" * 64,
    )
    runner._save_candidate_checkpoint(context, tmp_path, 1, candidate)
    target = runner._candidate_checkpoint_path(tmp_path, 1, "delta_1")
    before = {
        path.relative_to(target).as_posix(): path.read_bytes()
        for path in target.rglob("*")
        if path.is_file()
    }

    with pytest.raises(RuntimeError, match="Existing candidate checkpoint drifted"):
        runner._save_candidate_checkpoint(
            context,
            tmp_path,
            1,
            replace(
                candidate,
                operating_cost_usd=candidate.operating_cost_usd + 1.0e-12,
            ),
        )

    after = {
        path.relative_to(target).as_posix(): path.read_bytes()
        for path in target.rglob("*")
        if path.is_file()
    }
    assert after == before


def test_rounded_checkpoint_writer_fails_before_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    candidate = _candidate(
        "delta_1",
        commitment_sha256=runner._commitment_sha256(({"g1": True},)),
        cost=100.98765432109876,
        delta=0.12345678901234568,
    )
    generation = ({"g1": 1.2345678901234567},)
    candidate = replace(
        candidate,
        generation_mw=generation,
        dispatch_sha256=runner._dispatch_sha256(
            generation, candidate.branch_flows_mw, candidate.dc_flows_mw
        ),
    )
    context = SimpleNamespace(
        config={"preregistration": {"id": "experiment-v4"}},
        input_contract_sha256="a" * 64,
    )
    target = runner._candidate_checkpoint_path(tmp_path, 1, "delta_1")
    monkeypatch.setattr(runner, "_write_exact_json", _write_rounded_json)

    with pytest.raises(RuntimeError, match="staging round-trip drifted"):
        runner._save_candidate_checkpoint(context, tmp_path, 1, candidate)

    assert not target.exists()


def test_v3_checkpoint_schema_is_not_resume_eligible(tmp_path: Path) -> None:
    candidate = _valid_candidate("delta_1", 0.1)
    context = SimpleNamespace(
        config={"preregistration": {"id": "experiment-v4"}},
        input_contract_sha256="a" * 64,
    )
    target = runner._candidate_checkpoint_path(tmp_path, 1, "delta_1")
    runner._publish_immutable_payload(
        target,
        lambda staging: runner._write_exact_json(
            staging / "candidate.json",
            {
                "schema": "rts_gmlc_zero_dc_ac_aware_candidate_checkpoint_v1",
                "preregistration_id": "experiment-v4",
                "input_contract_sha256": "a" * 64,
                "ordinal": 1,
                "candidate": asdict(candidate),
            },
        ),
    )

    with pytest.raises(RuntimeError, match="serialization contract drifted"):
        runner._load_candidate_checkpoint(context, tmp_path, 1, "delta_1")


@pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
def test_nonfinite_checkpoint_value_is_rejected_before_publication(
    tmp_path: Path, value: float
) -> None:
    candidate = replace(_valid_candidate("delta_1", 0.1), operating_cost_usd=value)
    context = SimpleNamespace(
        config={"preregistration": {"id": "experiment-v4"}},
        input_contract_sha256="a" * 64,
    )

    with pytest.raises(ValueError, match="Out of range float values"):
        runner._save_candidate_checkpoint(context, tmp_path, 1, candidate)

    assert not runner._candidate_checkpoint_path(tmp_path, 1, "delta_1").exists()


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
            runner._exact_json_payload(asdict(candidate))
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
            "solver_selection_provenance": {
                "initial_proxy_warm_start": {
                    "application_scope": ("initial_proxy_maximization_master_only")
                }
            },
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
    monkeypatch.setattr(runner, "V4InitialProxyWarmStartAdapter", FakeAdapter)
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
            "preregistration": {"id": "experiment-v4"},
            "formal_solver": {
                "algorithm": "exact_selected_state_constraint_generation",
                "solver": {"name": "highs", "threads": 4},
                "progress_logging": {"log_directory": str(log_root)},
                "time_limits_seconds": {"per_candidate_total": 10.0},
            },
            "candidate_frontier": {
                "relative_cost_budget_deltas": list(deltas),
            },
            "joint_ac": {"expected_hours": 1},
            "evidence": {"formal_candidate_result": False},
        },
        output_root=output_root,
        input_contract_sha256="a" * 64,
        request=SimpleNamespace(
            timestamps=(datetime(2020, 1, 1, tzinfo=timezone.utc),)
        ),
        zero=SimpleNamespace(
            scan=SimpleNamespace(
                data=SimpleNamespace(
                    generators=(SimpleNamespace(uid="g1"),),
                    branches=(SimpleNamespace(uid="b1"),),
                    dc_branches=(SimpleNamespace(uid="d1"),),
                )
            )
        ),
        initial_state=SimpleNamespace(commitment={"g1": True}),
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
    monkeypatch.setattr(
        runner,
        "_validate_formal_candidate_contract",
        lambda _candidate, _context, _ordinal: None,
    )

    with pytest.raises(RuntimeError, match="simulated interruption"):
        runner.generate_candidate_frontier(
            Path("test-config.yaml"), attempt_id="attempt-1"
        )

    first_id = runner._requested_candidate_id(deltas[0])
    first_checkpoint = runner._candidate_checkpoint_path(output_root, 1, first_id)
    assert (first_checkpoint / "SHA256SUMS").is_file()
    assert not (output_root / "candidate_frontier").exists()
    first_progress = (log_root / "attempt-1" / "progress.jsonl").read_text(
        encoding="utf-8"
    )
    assert '"event":"candidate_failed"' in first_progress
    assert '"event":"attempt_failed"' in first_progress

    summary = runner.generate_candidate_frontier(
        Path("test-config.yaml"), attempt_id="attempt-2"
    )

    assert solved_deltas == [0.1, 0.2, 0.2]
    assert summary["requested_candidate_count"] == 3
    assert len(summary["candidate_checkpoint_manifest_sha256s"]) == 2
    loaded, manifest_sha256 = runner._load_candidate_frontier(context, output_root)
    assert len(loaded) == summary["unique_candidate_count"]
    assert manifest_sha256 == runner._sha256(
        output_root / "candidate_frontier" / "SHA256SUMS"
    )
    progress_rows = (log_root / "attempt-2" / "progress.jsonl").read_text(
        encoding="utf-8"
    )
    assert "candidate_checkpoint_loaded" in progress_rows
    assert "frontier_published" in progress_rows
    lease_history = output_root / "execution_lease" / "history"
    assert len(tuple(lease_history.glob("*.failed"))) == 1
    assert len(tuple(lease_history.glob("*.released"))) == 1
