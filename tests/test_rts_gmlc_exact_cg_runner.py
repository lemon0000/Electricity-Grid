from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.grid.rts_gmlc_exact_cg import SharedSnapshot
from src.grid.rts_gmlc_exact_cg_runner import (
    ExactCgCall,
    ExactCgCallbacks,
    ExactCgTimeLimits,
    FullStateAuditResult,
    MasterSolveResult,
    StateScreenResult,
    run_exact_cg_stage,
)
from src.solvers.mip_progress import JsonlProgressWriter

ALL_STATES = ("normal", "s1", "s2", "s3")
SEED_STATES = ("normal", "s1")
LIMITS = ExactCgTimeLimits(
    master_seconds=30.0,
    screen_seconds=10.0,
    final_audit_seconds=20.0,
)
MAX_RELATIVE_GAP = 0.02
MAX_PROXY_ABSOLUTE_GAP = 0.02


def _snapshot(label: str, *, proxy: float, cost: float) -> SharedSnapshot:
    return SharedSnapshot(
        values=(("commitment", (0, "g1"), 1.0),),
        sha256=(label * 64)[:64],
        reactive_proxy=proxy,
        operating_cost_usd=cost,
    )


def _passed_audit(call: ExactCgCall) -> FullStateAuditResult:
    assert call.shared_snapshot is not None
    return FullStateAuditResult(
        audited_state_ids=call.all_state_ids,
        shared_snapshot_sha256=call.shared_snapshot.sha256,
        solution_usable=True,
        shared_snapshot_fixed=True,
        integer_variables_relaxed=True,
        residual_audit_passed=True,
        additional_audits_passed=True,
        full_feasible_objective=(
            call.shared_snapshot.reactive_proxy
            if call.stage == "proxy_maximization"
            else call.shared_snapshot.operating_cost_usd
        ),
        record={"native_log_selected_by_callback": call.call_id + ".log"},
    )


def test_proxy_rescreens_every_inactive_state_and_promotes_unresolved() -> None:
    first = _snapshot("a", proxy=0.81, cost=101.0)
    second = _snapshot("b", proxy=0.82, cost=102.0)
    master_calls: list[ExactCgCall] = []
    screen_calls: list[ExactCgCall] = []
    events: list[str] = []

    def solve_master(call: ExactCgCall) -> MasterSolveResult:
        master_calls.append(call)
        snapshot, upper = (first, 0.90) if call.iteration == 1 else (second, 0.83)
        return MasterSolveResult(
            snapshot=snapshot,
            incumbent_usable=True,
            bound_valid=True,
            dual_bound=upper,
            residual_audit_passed=True,
        )

    def screen_state(call: ExactCgCall) -> StateScreenResult:
        screen_calls.append(call)
        assert call.shared_snapshot is not None
        status = (
            "unresolved"
            if call.iteration == 1 and call.state_id == "s3"
            else "feasible"
        )
        return StateScreenResult(
            status=status,
            shared_snapshot_sha256=call.shared_snapshot.sha256,
        )

    result = run_exact_cg_stage(
        stage="proxy_maximization",
        all_state_ids=ALL_STATES,
        seed_state_ids=SEED_STATES,
        target_relative_gap=0.02,
        maximum_accepted_relative_gap_to_feasible_incumbent=MAX_RELATIVE_GAP,
        maximum_accepted_absolute_gap=MAX_PROXY_ABSOLUTE_GAP,
        time_limits=LIMITS,
        callbacks=ExactCgCallbacks(
            solve_master=solve_master,
            screen_state=screen_state,
            audit_full_state=_passed_audit,
            emit=lambda event, _payload: events.append(event),
        ),
    )

    assert [call.active_state_ids for call in master_calls] == [
        SEED_STATES,
        ("normal", "s1", "s3"),
    ]
    assert [(call.iteration, call.state_id) for call in screen_calls] == [
        (1, "s2"),
        (1, "s3"),
        (2, "s2"),
    ]
    assert result.snapshot == second
    assert result.stage_record["eligible"]
    assert result.stage_record["iteration_records"][0]["promotions"] == [
        {"state_id": "s3", "reason": "unresolved_promoted"}
    ]
    assert result.stage_record["certificate"]["lower_bound"] == 0.82
    assert result.stage_record["certificate"]["upper_bound"] == 0.83
    assert not result.stage_record["unresolved_promoted_is_infeasibility_claim"]
    assert events[-1] == "exact_cg_stage_completed"


def test_proxy_and_cost_stages_each_restart_from_the_same_seed() -> None:
    seen_first_active: dict[str, tuple[str, ...]] = {}

    def callbacks_for(stage: str) -> ExactCgCallbacks:
        snapshot = (
            _snapshot("c", proxy=0.80, cost=104.0)
            if stage == "proxy_maximization"
            else _snapshot("d", proxy=0.80, cost=100.0)
        )

        def solve_master(call: ExactCgCall) -> MasterSolveResult:
            seen_first_active.setdefault(stage, call.active_state_ids)
            bound = 0.81 if stage == "proxy_maximization" else 99.0
            return MasterSolveResult(
                snapshot=snapshot,
                incumbent_usable=True,
                bound_valid=True,
                dual_bound=bound,
                residual_audit_passed=True,
            )

        def screen_state(call: ExactCgCall) -> StateScreenResult:
            assert call.shared_snapshot is not None
            return StateScreenResult(
                status="feasible",
                shared_snapshot_sha256=call.shared_snapshot.sha256,
            )

        return ExactCgCallbacks(solve_master, screen_state, _passed_audit)

    proxy = run_exact_cg_stage(
        stage="proxy_maximization",
        all_state_ids=ALL_STATES,
        seed_state_ids=SEED_STATES,
        target_relative_gap=0.02,
        maximum_accepted_relative_gap_to_feasible_incumbent=MAX_RELATIVE_GAP,
        maximum_accepted_absolute_gap=MAX_PROXY_ABSOLUTE_GAP,
        time_limits=LIMITS,
        callbacks=callbacks_for("proxy_maximization"),
    )
    cost = run_exact_cg_stage(
        stage="cost_normalization",
        all_state_ids=ALL_STATES,
        seed_state_ids=SEED_STATES,
        target_relative_gap=0.02,
        maximum_accepted_relative_gap_to_feasible_incumbent=MAX_RELATIVE_GAP,
        maximum_accepted_absolute_gap=None,
        time_limits=LIMITS,
        callbacks=callbacks_for("cost_normalization"),
        proxy_floor=0.7999999,
    )

    assert seen_first_active == {
        "proxy_maximization": SEED_STATES,
        "cost_normalization": SEED_STATES,
    }
    assert proxy.stage_record["certificate"]["upper_bound"] == 0.81
    assert cost.stage_record["certificate"]["lower_bound"] == 99.0
    assert cost.stage_record["certificate"]["upper_bound"] == 100.0
    assert cost.snapshot is not None
    assert cost.stage_record["proxy_floor"] == 0.7999999


def test_screen_snapshot_mismatch_is_conservatively_unresolved_and_promoted() -> None:
    snapshots = iter(
        (
            _snapshot("e", proxy=0.80, cost=100.0),
            _snapshot("f", proxy=0.80, cost=100.0),
        )
    )

    def solve_master(_call: ExactCgCall) -> MasterSolveResult:
        return MasterSolveResult(
            snapshot=next(snapshots),
            incumbent_usable=True,
            bound_valid=True,
            dual_bound=0.80,
            residual_audit_passed=True,
        )

    def screen_state(call: ExactCgCall) -> StateScreenResult:
        assert call.shared_snapshot is not None
        return StateScreenResult(
            status="feasible",
            shared_snapshot_sha256=(
                "wrong"
                if call.iteration == 1 and call.state_id == "s2"
                else call.shared_snapshot.sha256
            ),
        )

    result = run_exact_cg_stage(
        stage="proxy_maximization",
        all_state_ids=("normal", "s1", "s2"),
        seed_state_ids=SEED_STATES,
        target_relative_gap=0.0,
        maximum_accepted_relative_gap_to_feasible_incumbent=MAX_RELATIVE_GAP,
        maximum_accepted_absolute_gap=MAX_PROXY_ABSOLUTE_GAP,
        time_limits=LIMITS,
        callbacks=ExactCgCallbacks(solve_master, screen_state, _passed_audit),
    )

    first_screen = result.stage_record["iteration_records"][0]["screen_records"][0]
    assert first_screen["reported_status"] == "feasible"
    assert first_screen["status"] == "unresolved"
    assert not first_screen["screen_snapshot_contract_valid"]
    assert result.stage_record["final_active_state_ids"] == [
        "normal",
        "s1",
        "s2",
    ]
    assert result.snapshot is not None


@pytest.mark.parametrize(
    ("audit_change", "field_value"),
    (
        ("audited_state_ids", ("normal", "s1")),
        ("shared_snapshot_sha256", "wrong"),
        ("solution_usable", False),
        ("shared_snapshot_fixed", False),
        ("integer_variables_relaxed", False),
        ("residual_audit_passed", False),
        ("additional_audits_passed", False),
        ("full_feasible_objective", None),
    ),
)
def test_final_full_state_fixed_shared_lp_and_all_audits_are_mandatory(
    audit_change: str, field_value: object
) -> None:
    snapshot = _snapshot("1", proxy=0.8, cost=100.0)

    def solve_master(_call: ExactCgCall) -> MasterSolveResult:
        return MasterSolveResult(snapshot, True, True, 0.8, True)

    def screen_state(call: ExactCgCall) -> StateScreenResult:
        return StateScreenResult("feasible", snapshot.sha256)

    def audit(call: ExactCgCall) -> FullStateAuditResult:
        values: dict[str, object] = {
            "audited_state_ids": call.all_state_ids,
            "shared_snapshot_sha256": snapshot.sha256,
            "solution_usable": True,
            "shared_snapshot_fixed": True,
            "integer_variables_relaxed": True,
            "residual_audit_passed": True,
            "additional_audits_passed": True,
            "full_feasible_objective": snapshot.reactive_proxy,
        }
        values[audit_change] = field_value
        return FullStateAuditResult(**values)  # type: ignore[arg-type]

    result = run_exact_cg_stage(
        stage="proxy_maximization",
        all_state_ids=ALL_STATES,
        seed_state_ids=SEED_STATES,
        target_relative_gap=0.0,
        maximum_accepted_relative_gap_to_feasible_incumbent=MAX_RELATIVE_GAP,
        maximum_accepted_absolute_gap=MAX_PROXY_ABSOLUTE_GAP,
        time_limits=LIMITS,
        callbacks=ExactCgCallbacks(solve_master, screen_state, audit),
    )

    assert result.snapshot is None
    assert not result.stage_record["eligible"]
    assert result.stage_record["failure_reason"] == (
        "final_full_state_fixed_shared_audit_failed"
    )
    assert not result.stage_record["final_full_state_audit"]["passed"]


def test_certificate_uses_full_state_audit_objective_and_separates_acceptance() -> None:
    snapshot = _snapshot("4", proxy=0.80, cost=100.0)

    def solve_master(_call: ExactCgCall) -> MasterSolveResult:
        return MasterSolveResult(snapshot, True, True, 0.81, True)

    def screen_state(_call: ExactCgCall) -> StateScreenResult:
        return StateScreenResult("feasible", snapshot.sha256)

    def audit(call: ExactCgCall) -> FullStateAuditResult:
        passed = _passed_audit(call)
        return FullStateAuditResult(
            audited_state_ids=passed.audited_state_ids,
            shared_snapshot_sha256=passed.shared_snapshot_sha256,
            solution_usable=True,
            shared_snapshot_fixed=True,
            integer_variables_relaxed=True,
            residual_audit_passed=True,
            additional_audits_passed=True,
            full_feasible_objective=0.79,
        )

    result = run_exact_cg_stage(
        stage="proxy_maximization",
        all_state_ids=("normal",),
        seed_state_ids=("normal",),
        target_relative_gap=0.01,
        maximum_accepted_relative_gap_to_feasible_incumbent=0.03,
        maximum_accepted_absolute_gap=0.021,
        time_limits=LIMITS,
        callbacks=ExactCgCallbacks(solve_master, pytest.fail, audit),
    )

    certificate = result.stage_record["certificate"]
    assert certificate["lower_bound"] == 0.79
    assert certificate["upper_bound"] == 0.81
    assert not result.stage_record["target_attained"]
    assert result.stage_record["eligibility_status"] == "eligible_within_maximum"
    assert result.stage_record["maximum_acceptance"]["maximum_acceptance_passed"]
    assert result.snapshot == snapshot


def test_proxy_acceptance_requires_both_relative_and_absolute_gap_caps() -> None:
    snapshot = _snapshot("5", proxy=0.80, cost=100.0)

    result = run_exact_cg_stage(
        stage="proxy_maximization",
        all_state_ids=("normal",),
        seed_state_ids=("normal",),
        target_relative_gap=0.001,
        maximum_accepted_relative_gap_to_feasible_incumbent=0.1,
        maximum_accepted_absolute_gap=0.005,
        time_limits=LIMITS,
        callbacks=ExactCgCallbacks(
            lambda _call: MasterSolveResult(snapshot, True, True, 0.81, True),
            pytest.fail,
            _passed_audit,
        ),
    )

    acceptance = result.stage_record["maximum_acceptance"]
    assert acceptance["relative_acceptance_passed"]
    assert not acceptance["absolute_acceptance_passed"]
    assert result.snapshot is None
    assert result.stage_record["failure_reason"] == (
        "final_bound_certificate_exceeds_maximum_acceptance"
    )


def test_cost_certificate_uses_audited_cost_and_allows_no_absolute_cap() -> None:
    snapshot = _snapshot("6", proxy=0.80, cost=100.0)

    def audit(call: ExactCgCall) -> FullStateAuditResult:
        passed = _passed_audit(call)
        return FullStateAuditResult(
            audited_state_ids=passed.audited_state_ids,
            shared_snapshot_sha256=passed.shared_snapshot_sha256,
            solution_usable=True,
            shared_snapshot_fixed=True,
            integer_variables_relaxed=True,
            residual_audit_passed=True,
            additional_audits_passed=True,
            full_feasible_objective=101.0,
        )

    result = run_exact_cg_stage(
        stage="cost_normalization",
        all_state_ids=("normal",),
        seed_state_ids=("normal",),
        target_relative_gap=0.005,
        maximum_accepted_relative_gap_to_feasible_incumbent=0.02,
        maximum_accepted_absolute_gap=None,
        time_limits=LIMITS,
        callbacks=ExactCgCallbacks(
            lambda _call: MasterSolveResult(snapshot, True, True, 99.0, True),
            pytest.fail,
            audit,
        ),
        proxy_floor=0.7999999,
    )

    certificate = result.stage_record["certificate"]
    assert certificate["lower_bound"] == 99.0
    assert certificate["upper_bound"] == 101.0
    assert result.stage_record["eligibility_status"] == "eligible_within_maximum"
    assert result.snapshot == snapshot


def test_level_set_stage_preserves_bound_only_master_evidence() -> None:
    result = run_exact_cg_stage(
        stage="level_set_cost_minimization",
        all_state_ids=ALL_STATES,
        seed_state_ids=SEED_STATES,
        target_relative_gap=0.001,
        maximum_accepted_relative_gap_to_feasible_incumbent=0.001,
        maximum_accepted_absolute_gap=None,
        time_limits=LIMITS,
        callbacks=ExactCgCallbacks(
            lambda _call: MasterSolveResult(None, False, True, 101.0, False),
            pytest.fail,
            pytest.fail,
        ),
        proxy_floor=0.6,
    )

    assert result.snapshot is None
    assert result.audited_snapshot is None
    assert result.stage_record["failure_reason"] == (
        "level_set_master_bound_only_without_audited_incumbent"
    )
    assert result.stage_record["master_records"][0]["bound_valid"]
    assert result.stage_record["master_records"][0]["dual_bound"] == 101.0


def test_budget_decision_stage_global_infeasibility_is_explicit_early_separation(
    tmp_path: Path,
) -> None:
    events: list[str] = []
    progress = JsonlProgressWriter(
        tmp_path / "progress.jsonl",
        run_id="decision-early-separation",
        preregistration_id="synthetic-only",
        input_contract_sha256="a" * 64,
    )

    def emit(event: str, payload: dict[str, object]) -> None:
        progress.emit(event, **payload)
        events.append(event)

    result = run_exact_cg_stage(
        stage="level_set_budget_feasibility",
        all_state_ids=ALL_STATES,
        seed_state_ids=SEED_STATES,
        target_relative_gap=0.001,
        maximum_accepted_relative_gap_to_feasible_incumbent=0.001,
        maximum_accepted_absolute_gap=None,
        time_limits=LIMITS,
        callbacks=ExactCgCallbacks(
            lambda _call: MasterSolveResult(
                None,
                False,
                False,
                None,
                False,
                globally_infeasible=True,
                decision_budget_cap_usd=100.0001,
            ),
            pytest.fail,
            pytest.fail,
            emit,
        ),
        proxy_floor=0.6,
    )

    assert result.snapshot is None
    assert result.audited_snapshot is None
    assert result.stage_record["failure_reason"] is None
    assert result.stage_record["eligible"] is False
    assert result.stage_record["eligibility_status"] == ("bound_only_early_separation")
    assert result.stage_record["level_set_oracle_outcome"] == (
        "bound_only_early_separation"
    )
    separation = result.stage_record["bound_only_early_separation"]
    assert separation["valid"]
    assert separation["decision_budget_cap_usd"] == 100.0001
    assert not separation["inactive_state_screen_executed"]
    assert not separation["final_full_state_audit_executed"]
    assert "exact_cg_bound_only_early_separation" in events
    records = [
        json.loads(line)
        for line in (tmp_path / "progress.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    event = next(
        record
        for record in records
        if record["event"] == "exact_cg_bound_only_early_separation"
    )
    assert event["schema"] == "mip_progress_event_v1"
    assert event["separation_schema"] == separation["schema"]
    assert event["decision_budget_cap_usd"] == 100.0001


def test_budget_decision_stage_rejects_infeasibility_with_an_incumbent() -> None:
    snapshot = _snapshot("inconsistent", proxy=0.65, cost=99.0)
    result = run_exact_cg_stage(
        stage="level_set_budget_feasibility",
        all_state_ids=ALL_STATES,
        seed_state_ids=SEED_STATES,
        target_relative_gap=0.001,
        maximum_accepted_relative_gap_to_feasible_incumbent=0.001,
        maximum_accepted_absolute_gap=None,
        time_limits=LIMITS,
        callbacks=ExactCgCallbacks(
            lambda _call: MasterSolveResult(
                snapshot,
                True,
                False,
                None,
                True,
                globally_infeasible=True,
                decision_budget_cap_usd=100.0001,
            ),
            pytest.fail,
            pytest.fail,
        ),
        proxy_floor=0.6,
    )

    assert result.stage_record["level_set_oracle_outcome"] == "unresolved"
    assert result.stage_record["failure_reason"] == (
        "decision_mip_returned_inconsistent_infeasibility"
    )
    assert result.stage_record["bound_only_early_separation"] is None


def test_budget_decision_stage_ambiguous_termination_is_unresolved() -> None:
    result = run_exact_cg_stage(
        stage="level_set_budget_feasibility",
        all_state_ids=ALL_STATES,
        seed_state_ids=SEED_STATES,
        target_relative_gap=0.001,
        maximum_accepted_relative_gap_to_feasible_incumbent=0.001,
        maximum_accepted_absolute_gap=None,
        time_limits=LIMITS,
        callbacks=ExactCgCallbacks(
            lambda _call: MasterSolveResult(None, False, False, None, False),
            pytest.fail,
            pytest.fail,
        ),
        proxy_floor=0.6,
    )

    assert result.stage_record["level_set_oracle_outcome"] == "unresolved"
    assert result.stage_record["failure_reason"] == (
        "decision_mip_unresolved_without_feasible_incumbent"
    )
    assert result.stage_record["bound_only_early_separation"] is None


def test_budget_decision_stage_requires_screen_and_full_audit_for_a_witness() -> None:
    snapshot = _snapshot("d", proxy=0.65, cost=99.0)

    def screen(call: ExactCgCall) -> StateScreenResult:
        assert call.shared_snapshot is not None
        return StateScreenResult("feasible", call.shared_snapshot.sha256)

    result = run_exact_cg_stage(
        stage="level_set_budget_feasibility",
        all_state_ids=ALL_STATES,
        seed_state_ids=SEED_STATES,
        target_relative_gap=0.001,
        maximum_accepted_relative_gap_to_feasible_incumbent=0.001,
        maximum_accepted_absolute_gap=None,
        time_limits=LIMITS,
        callbacks=ExactCgCallbacks(
            lambda _call: MasterSolveResult(snapshot, True, False, None, True),
            screen,
            _passed_audit,
        ),
        proxy_floor=0.6,
    )

    assert result.stage_record["level_set_oracle_outcome"] == "audited_feasible"
    assert result.stage_record["eligible"]
    assert result.audited_snapshot == snapshot
    assert result.stage_record["final_full_state_audit"]["passed"]


def test_level_set_stage_returns_only_a_fully_screened_audited_witness() -> None:
    first = _snapshot("7", proxy=0.65, cost=99.0)
    second = _snapshot("8", proxy=0.66, cost=98.0)

    def solve_master(call: ExactCgCall) -> MasterSolveResult:
        snapshot = first if call.iteration == 1 else second
        return MasterSolveResult(snapshot, True, True, 97.0, True)

    def screen_state(call: ExactCgCall) -> StateScreenResult:
        assert call.shared_snapshot is not None
        status = (
            "unresolved"
            if call.iteration == 1 and call.state_id == "s3"
            else "feasible"
        )
        return StateScreenResult(status, call.shared_snapshot.sha256)

    result = run_exact_cg_stage(
        stage="level_set_cost_minimization",
        all_state_ids=ALL_STATES,
        seed_state_ids=SEED_STATES,
        target_relative_gap=0.001,
        maximum_accepted_relative_gap_to_feasible_incumbent=0.001,
        maximum_accepted_absolute_gap=None,
        time_limits=LIMITS,
        callbacks=ExactCgCallbacks(solve_master, screen_state, _passed_audit),
        proxy_floor=0.6,
    )

    assert result.snapshot == second
    assert result.audited_snapshot == second
    assert result.stage_record["eligible"]
    assert result.stage_record["eligibility_status"] == "audited_oracle_witness"
    assert result.stage_record["iteration_records"][0]["promotions"] == [
        {"state_id": "s3", "reason": "unresolved_promoted"}
    ]


def test_per_kind_limits_are_clipped_by_candidate_remaining_time_callback() -> None:
    snapshot = _snapshot("2", proxy=0.8, cost=100.0)
    remaining = iter((25.0, 9.0, 8.0))
    observed: list[tuple[str, float]] = []

    def solve_master(call: ExactCgCall) -> MasterSolveResult:
        observed.append((call.kind, call.time_limit_seconds))
        return MasterSolveResult(snapshot, True, True, 0.8, True)

    def screen_state(call: ExactCgCall) -> StateScreenResult:
        observed.append((call.kind, call.time_limit_seconds))
        return StateScreenResult("feasible", snapshot.sha256)

    def audit(call: ExactCgCall) -> FullStateAuditResult:
        observed.append((call.kind, call.time_limit_seconds))
        return _passed_audit(call)

    result = run_exact_cg_stage(
        stage="proxy_maximization",
        all_state_ids=("normal", "s1"),
        seed_state_ids=("normal",),
        target_relative_gap=0.0,
        maximum_accepted_relative_gap_to_feasible_incumbent=MAX_RELATIVE_GAP,
        maximum_accepted_absolute_gap=MAX_PROXY_ABSOLUTE_GAP,
        time_limits=LIMITS,
        callbacks=ExactCgCallbacks(solve_master, screen_state, audit),
        candidate_remaining_seconds=lambda: next(remaining),
    )

    assert observed == [("master", 25.0), ("screen", 9.0), ("final_audit", 8.0)]
    assert result.stage_record["candidate_deadline_mode"] == ("remaining_time_callback")
    assert result.snapshot is not None


def test_absolute_candidate_deadline_stops_before_the_next_solve_call() -> None:
    snapshot = _snapshot("3", proxy=0.8, cost=100.0)
    clock_values = iter((75.0, 101.0))
    screens: list[ExactCgCall] = []

    def solve_master(call: ExactCgCall) -> MasterSolveResult:
        assert call.time_limit_seconds == 25.0
        return MasterSolveResult(snapshot, True, True, 0.8, True)

    def screen_state(call: ExactCgCall) -> StateScreenResult:
        screens.append(call)
        return StateScreenResult("feasible", snapshot.sha256)

    result = run_exact_cg_stage(
        stage="proxy_maximization",
        all_state_ids=("normal", "s1"),
        seed_state_ids=("normal",),
        target_relative_gap=0.0,
        maximum_accepted_relative_gap_to_feasible_incumbent=MAX_RELATIVE_GAP,
        maximum_accepted_absolute_gap=MAX_PROXY_ABSOLUTE_GAP,
        time_limits=LIMITS,
        callbacks=ExactCgCallbacks(solve_master, screen_state, _passed_audit),
        candidate_deadline_monotonic=100.0,
        monotonic_clock=lambda: next(clock_values),
    )

    assert screens == []
    assert result.snapshot is None
    assert result.stage_record["failure_reason"] == (
        "candidate_deadline_exhausted_before_screen"
    )
    iteration = result.stage_record["iteration_records"][0]
    assert not iteration["screen_round_complete"]


@pytest.mark.parametrize(
    ("stage", "proxy_floor", "message"),
    (
        ("proxy_maximization", 0.8, "cannot receive"),
        ("cost_normalization", None, "requires a finite"),
    ),
)
def test_stage_specific_proxy_floor_contract_is_enforced(
    stage: str, proxy_floor: float | None, message: str
) -> None:
    def never(_call: ExactCgCall) -> object:
        pytest.fail("callback should not run")

    callbacks = ExactCgCallbacks(never, never, never)  # type: ignore[arg-type]

    with pytest.raises(ValueError, match=message):
        run_exact_cg_stage(
            stage=stage,  # type: ignore[arg-type]
            all_state_ids=ALL_STATES,
            seed_state_ids=SEED_STATES,
            target_relative_gap=1.0e-4,
            maximum_accepted_relative_gap_to_feasible_incumbent=MAX_RELATIVE_GAP,
            maximum_accepted_absolute_gap=(
                MAX_PROXY_ABSOLUTE_GAP if stage == "proxy_maximization" else None
            ),
            time_limits=LIMITS,
            callbacks=callbacks,
            proxy_floor=proxy_floor,
        )
