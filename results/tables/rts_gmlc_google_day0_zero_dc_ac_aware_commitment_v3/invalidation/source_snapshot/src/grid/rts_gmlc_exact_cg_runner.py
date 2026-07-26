"""Model-agnostic orchestration for formal exact constraint generation.

The callbacks own model construction, solves, native logs, and JSONL output.  This
module only enforces the active-set protocol and assembles optimization
certificates from audited callback results.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from typing import Literal

from src.grid.rts_gmlc_exact_cg import (
    NORMAL_STATE_ID,
    SharedSnapshot,
    final_max_certificate,
    final_min_certificate,
    promotions,
    screen_plan,
)


Stage = Literal["proxy_maximization", "cost_normalization"]
CallKind = Literal["master", "screen", "final_audit"]
ScreenStatus = Literal["feasible", "certified_infeasible", "unresolved"]
EventCallback = Callable[[str, Mapping[str, object]], None]


def _discard_event(_event: str, _payload: Mapping[str, object]) -> None:
    return None


@dataclass(frozen=True)
class ExactCgTimeLimits:
    master_seconds: float
    screen_seconds: float
    final_audit_seconds: float

    def __post_init__(self) -> None:
        for name, candidate in (
            ("master_seconds", self.master_seconds),
            ("screen_seconds", self.screen_seconds),
            ("final_audit_seconds", self.final_audit_seconds),
        ):
            if not math.isfinite(float(candidate)) or float(candidate) <= 0.0:
                raise ValueError(f"{name} must be finite and positive")

    def for_kind(self, kind: CallKind) -> float:
        return float(
            {
                "master": self.master_seconds,
                "screen": self.screen_seconds,
                "final_audit": self.final_audit_seconds,
            }[kind]
        )


@dataclass(frozen=True)
class ExactCgCall:
    call_id: str
    kind: CallKind
    stage: Stage
    iteration: int
    active_state_ids: tuple[str, ...]
    all_state_ids: tuple[str, ...]
    time_limit_seconds: float
    target_relative_gap: float
    proxy_floor: float | None
    state_id: str | None = None
    shared_snapshot: SharedSnapshot | None = None


@dataclass(frozen=True)
class MasterSolveResult:
    snapshot: SharedSnapshot | None
    incumbent_usable: bool
    bound_valid: bool
    dual_bound: float | None
    residual_audit_passed: bool
    record: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class StateScreenResult:
    status: ScreenStatus
    shared_snapshot_sha256: str
    record: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class FullStateAuditResult:
    audited_state_ids: tuple[str, ...]
    shared_snapshot_sha256: str
    solution_usable: bool
    shared_snapshot_fixed: bool
    integer_variables_relaxed: bool
    residual_audit_passed: bool
    additional_audits_passed: bool
    full_feasible_objective: float | None
    record: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True)
class ExactCgCallbacks:
    solve_master: Callable[[ExactCgCall], MasterSolveResult]
    screen_state: Callable[[ExactCgCall], StateScreenResult]
    audit_full_state: Callable[[ExactCgCall], FullStateAuditResult]
    emit: EventCallback = _discard_event


@dataclass(frozen=True)
class ExactCgStageResult:
    snapshot: SharedSnapshot | None
    stage_record: dict[str, object]


def _finite_number(candidate: object) -> float | None:
    try:
        parsed = float(candidate)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _snapshot_valid(snapshot: SharedSnapshot | None) -> bool:
    return bool(
        snapshot is not None
        and snapshot.sha256
        and _finite_number(snapshot.reactive_proxy) is not None
        and _finite_number(snapshot.operating_cost_usd) is not None
    )


def _call_payload(call: ExactCgCall) -> dict[str, object]:
    return {
        "call_id": call.call_id,
        "kind": call.kind,
        "stage": call.stage,
        "iteration": call.iteration,
        "active_state_ids": list(call.active_state_ids),
        "all_state_ids": list(call.all_state_ids),
        "state_id": call.state_id,
        "shared_snapshot_sha256": (
            call.shared_snapshot.sha256 if call.shared_snapshot else None
        ),
        "time_limit_seconds": call.time_limit_seconds,
        "target_relative_gap": call.target_relative_gap,
        "proxy_floor": call.proxy_floor,
    }


def run_exact_cg_stage(
    *,
    stage: Stage,
    all_state_ids: Sequence[str],
    seed_state_ids: Sequence[str],
    target_relative_gap: float,
    maximum_accepted_relative_gap_to_feasible_incumbent: float,
    maximum_accepted_absolute_gap: float | None,
    time_limits: ExactCgTimeLimits,
    callbacks: ExactCgCallbacks,
    proxy_floor: float | None = None,
    candidate_deadline_monotonic: float | None = None,
    candidate_remaining_seconds: Callable[[], float] | None = None,
    monotonic_clock: Callable[[], float] = time.monotonic,
) -> ExactCgStageResult:
    """Run one exact-CG stage from a fresh copy of ``seed_state_ids``.

    Call this function once for proxy maximization and again for cost
    normalization.  No active-set state is retained between invocations.
    """

    all_ids = tuple(str(item) for item in all_state_ids)
    seed_ids = tuple(str(item) for item in seed_state_ids)
    _validate_inputs(
        stage=stage,
        all_state_ids=all_ids,
        seed_state_ids=seed_ids,
        target_relative_gap=target_relative_gap,
        maximum_accepted_relative_gap_to_feasible_incumbent=(
            maximum_accepted_relative_gap_to_feasible_incumbent
        ),
        maximum_accepted_absolute_gap=maximum_accepted_absolute_gap,
        proxy_floor=proxy_floor,
        candidate_deadline_monotonic=candidate_deadline_monotonic,
        candidate_remaining_seconds=candidate_remaining_seconds,
    )

    active_ids = list(seed_ids)
    master_records: list[dict[str, object]] = []
    iteration_records: list[dict[str, object]] = []
    dual_bounds: list[float] = []
    final_snapshot: SharedSnapshot | None = None
    final_audit_record: dict[str, object] | None = None
    full_feasible_objective: float | None = None
    failure_reason: str | None = None

    deadline_mode = (
        "absolute_monotonic"
        if candidate_deadline_monotonic is not None
        else "remaining_time_callback"
        if candidate_remaining_seconds is not None
        else "none"
    )
    callbacks.emit(
        "exact_cg_stage_started",
        {
            "stage": stage,
            "sense": _sense(stage),
            "initial_active_state_ids": list(seed_ids),
            "all_state_ids": list(all_ids),
            "target_relative_gap": float(target_relative_gap),
            "maximum_accepted_relative_gap_to_feasible_incumbent": float(
                maximum_accepted_relative_gap_to_feasible_incumbent
            ),
            "maximum_accepted_absolute_gap": maximum_accepted_absolute_gap,
            "proxy_floor": proxy_floor,
            "candidate_deadline_mode": deadline_mode,
        },
    )

    maximum_iterations = len(all_ids) - len(seed_ids) + 1
    for iteration in range(1, maximum_iterations + 1):
        master_call = _make_call(
            kind="master",
            stage=stage,
            iteration=iteration,
            active_state_ids=active_ids,
            all_state_ids=all_ids,
            proxy_floor=proxy_floor,
            target_relative_gap=target_relative_gap,
            time_limits=time_limits,
            candidate_deadline_monotonic=candidate_deadline_monotonic,
            candidate_remaining_seconds=candidate_remaining_seconds,
            monotonic_clock=monotonic_clock,
        )
        if master_call is None:
            failure_reason = "candidate_deadline_exhausted_before_master"
            break
        callbacks.emit("exact_cg_call_started", _call_payload(master_call))
        master = callbacks.solve_master(master_call)
        master_record = {
            **_call_payload(master_call),
            "incumbent_usable": bool(master.incumbent_usable),
            "bound_valid": bool(master.bound_valid),
            "dual_bound": _finite_number(master.dual_bound),
            "residual_audit_passed": bool(master.residual_audit_passed),
            "shared_snapshot_sha256": (
                master.snapshot.sha256 if master.snapshot is not None else None
            ),
            "callback_record": dict(master.record),
        }
        master_records.append(master_record)
        callbacks.emit("exact_cg_master_completed", master_record)

        dual_bound = _finite_number(master.dual_bound)
        if not master.incumbent_usable or not master.bound_valid or dual_bound is None:
            failure_reason = "master_lacked_audited_incumbent_or_valid_dual_bound"
            break
        if not master.residual_audit_passed or not _snapshot_valid(master.snapshot):
            failure_reason = "master_shared_snapshot_or_residual_audit_failed"
            break
        snapshot = master.snapshot
        assert snapshot is not None
        dual_bounds.append(dual_bound)

        inactive_ids = screen_plan(
            stage=stage,
            all_state_ids=all_ids,
            active_state_ids=active_ids,
        )
        screen_records: list[dict[str, object]] = []
        callbacks.emit(
            "exact_cg_screen_round_started",
            {
                "stage": stage,
                "iteration": iteration,
                "active_state_ids": list(active_ids),
                "screened_state_ids": list(inactive_ids),
                "shared_snapshot_sha256": snapshot.sha256,
            },
        )
        for ordinal, state_id in enumerate(inactive_ids, start=1):
            screen_call = _make_call(
                kind="screen",
                stage=stage,
                iteration=iteration,
                active_state_ids=active_ids,
                all_state_ids=all_ids,
                proxy_floor=proxy_floor,
                target_relative_gap=target_relative_gap,
                time_limits=time_limits,
                candidate_deadline_monotonic=candidate_deadline_monotonic,
                candidate_remaining_seconds=candidate_remaining_seconds,
                monotonic_clock=monotonic_clock,
                state_id=state_id,
                shared_snapshot=snapshot,
                ordinal=ordinal,
            )
            if screen_call is None:
                failure_reason = "candidate_deadline_exhausted_before_screen"
                break
            callbacks.emit("exact_cg_call_started", _call_payload(screen_call))
            screened = callbacks.screen_state(screen_call)
            if screened.status not in {
                "feasible",
                "certified_infeasible",
                "unresolved",
            }:
                raise ValueError(f"Unknown screen status {screened.status}")
            contract_valid = screened.shared_snapshot_sha256 == snapshot.sha256
            effective_status: ScreenStatus = (
                screened.status if contract_valid else "unresolved"
            )
            screen_record = {
                **_call_payload(screen_call),
                "status": effective_status,
                "reported_status": screened.status,
                "screen_snapshot_contract_valid": contract_valid,
                "unresolved_is_infeasibility_claim": False,
                "callback_record": dict(screened.record),
            }
            screen_records.append(screen_record)
            callbacks.emit("exact_cg_screen_completed", screen_record)

        if failure_reason is not None:
            iteration_records.append(
                {
                    "iteration": iteration,
                    "stage": stage,
                    "active_state_ids": list(active_ids),
                    "shared_snapshot_sha256": snapshot.sha256,
                    "screen_records": screen_records,
                    "screen_round_complete": False,
                    "promotions": [],
                }
            )
            break

        promoted = promotions(screen_records, all_ids)
        iteration_record = {
            "iteration": iteration,
            "stage": stage,
            "active_state_ids": list(active_ids),
            "shared_snapshot_sha256": snapshot.sha256,
            "screen_records": screen_records,
            "screen_round_complete": True,
            "promotions": list(promoted),
        }
        iteration_records.append(iteration_record)
        if promoted:
            promoted_ids = {item["state_id"] for item in promoted}
            active_ids.extend(
                state_id
                for state_id in all_ids
                if state_id in promoted_ids and state_id not in active_ids
            )
            callbacks.emit(
                "exact_cg_active_set_expanded",
                {
                    "stage": stage,
                    "iteration": iteration,
                    "promotions": list(promoted),
                    "active_state_ids": list(active_ids),
                },
            )
            continue
        final_snapshot = snapshot
        break
    else:
        failure_reason = "constraint_generation_iteration_limit_exceeded"

    if failure_reason is None and final_snapshot is not None:
        audit_call = _make_call(
            kind="final_audit",
            stage=stage,
            iteration=len(master_records),
            active_state_ids=active_ids,
            all_state_ids=all_ids,
            proxy_floor=proxy_floor,
            target_relative_gap=target_relative_gap,
            time_limits=time_limits,
            candidate_deadline_monotonic=candidate_deadline_monotonic,
            candidate_remaining_seconds=candidate_remaining_seconds,
            monotonic_clock=monotonic_clock,
            shared_snapshot=final_snapshot,
        )
        if audit_call is None:
            failure_reason = "candidate_deadline_exhausted_before_final_audit"
        else:
            callbacks.emit("exact_cg_call_started", _call_payload(audit_call))
            audited = callbacks.audit_full_state(audit_call)
            audited_objective = _finite_number(audited.full_feasible_objective)
            audit_passed = bool(
                audited.audited_state_ids == all_ids
                and audited.shared_snapshot_sha256 == final_snapshot.sha256
                and audited.solution_usable
                and audited.shared_snapshot_fixed
                and audited.integer_variables_relaxed
                and audited.residual_audit_passed
                and audited.additional_audits_passed
                and audited_objective is not None
            )
            final_audit_record = {
                **_call_payload(audit_call),
                "passed": audit_passed,
                "audited_state_ids": list(audited.audited_state_ids),
                "reported_shared_snapshot_sha256": audited.shared_snapshot_sha256,
                "solution_usable": bool(audited.solution_usable),
                "shared_snapshot_fixed": bool(audited.shared_snapshot_fixed),
                "integer_variables_relaxed": bool(audited.integer_variables_relaxed),
                "residual_audit_passed": bool(audited.residual_audit_passed),
                "additional_audits_passed": bool(audited.additional_audits_passed),
                "full_feasible_objective": audited_objective,
                "callback_record": dict(audited.record),
            }
            callbacks.emit("exact_cg_full_state_audit_completed", final_audit_record)
            if not audit_passed:
                failure_reason = "final_full_state_fixed_shared_audit_failed"
            else:
                full_feasible_objective = audited_objective

    certificate = _certificate(
        stage=stage,
        full_feasible_objective=full_feasible_objective,
        dual_bounds=dual_bounds,
        target_relative_gap=float(target_relative_gap),
    )
    if failure_reason is None and not certificate["valid"]:
        failure_reason = "final_bound_certificate_invalid"

    relative_to_feasible = _finite_number(
        certificate["relative_gap_to_feasible_incumbent"]
    )
    absolute_gap = _finite_number(certificate["absolute_gap"])
    target_attained = bool(
        certificate["valid"]
        and relative_to_feasible is not None
        and relative_to_feasible <= float(target_relative_gap)
    )
    relative_acceptance_passed = bool(
        certificate["valid"]
        and relative_to_feasible is not None
        and relative_to_feasible
        <= float(maximum_accepted_relative_gap_to_feasible_incumbent)
    )
    absolute_acceptance_passed = bool(
        certificate["valid"]
        and absolute_gap is not None
        and (
            maximum_accepted_absolute_gap is None
            or absolute_gap <= float(maximum_accepted_absolute_gap)
        )
    )
    maximum_acceptance_passed = bool(
        relative_acceptance_passed and absolute_acceptance_passed
    )
    if failure_reason is None and not maximum_acceptance_passed:
        failure_reason = "final_bound_certificate_exceeds_maximum_acceptance"

    eligible = failure_reason is None
    eligibility_status = (
        "target_attained"
        if eligible and target_attained
        else "eligible_within_maximum"
        if eligible
        else "ineligible"
    )
    acceptance = {
        "target_relative_gap_to_feasible_incumbent": float(target_relative_gap),
        "target_attained": target_attained,
        "maximum_accepted_relative_gap_to_feasible_incumbent": float(
            maximum_accepted_relative_gap_to_feasible_incumbent
        ),
        "maximum_accepted_absolute_gap": maximum_accepted_absolute_gap,
        "relative_acceptance_passed": relative_acceptance_passed,
        "absolute_acceptance_passed": absolute_acceptance_passed,
        "maximum_acceptance_passed": maximum_acceptance_passed,
    }
    stage_record: dict[str, object] = {
        "schema": "rts_gmlc_exact_cg_stage_record_v1",
        "stage": stage,
        "sense": _sense(stage),
        "eligible": eligible,
        "eligibility_status": eligibility_status,
        "failure_reason": failure_reason,
        "target_relative_gap": float(target_relative_gap),
        "target_attained": target_attained,
        "maximum_acceptance": acceptance,
        "proxy_floor": proxy_floor,
        "candidate_deadline_mode": deadline_mode,
        "initial_active_state_ids": list(seed_ids),
        "final_active_state_ids": list(active_ids),
        "master_records": master_records,
        "iteration_records": iteration_records,
        "final_shared_snapshot_sha256": (
            final_snapshot.sha256 if final_snapshot is not None else None
        ),
        "final_full_state_audit": final_audit_record,
        "certificate": certificate,
        "unresolved_promoted_is_infeasibility_claim": False,
    }
    callbacks.emit(
        "exact_cg_stage_completed",
        {
            "stage": stage,
            "eligible": eligible,
            "eligibility_status": eligibility_status,
            "failure_reason": failure_reason,
            "final_active_state_ids": list(active_ids),
            "final_shared_snapshot_sha256": stage_record[
                "final_shared_snapshot_sha256"
            ],
            "certificate": certificate,
            "maximum_acceptance": acceptance,
        },
    )
    return ExactCgStageResult(
        snapshot=final_snapshot if eligible else None,
        stage_record=stage_record,
    )


def _validate_inputs(
    *,
    stage: str,
    all_state_ids: tuple[str, ...],
    seed_state_ids: tuple[str, ...],
    target_relative_gap: float,
    maximum_accepted_relative_gap_to_feasible_incumbent: float,
    maximum_accepted_absolute_gap: float | None,
    proxy_floor: float | None,
    candidate_deadline_monotonic: float | None,
    candidate_remaining_seconds: Callable[[], float] | None,
) -> None:
    if stage not in {"proxy_maximization", "cost_normalization"}:
        raise ValueError(f"Unknown exact-CG stage {stage}")
    if not all_state_ids or len(set(all_state_ids)) != len(all_state_ids):
        raise ValueError("all_state_ids must be nonempty and unique")
    if all_state_ids[0] != NORMAL_STATE_ID:
        raise ValueError("all_state_ids must begin with normal")
    if not seed_state_ids or len(set(seed_state_ids)) != len(seed_state_ids):
        raise ValueError("seed_state_ids must be nonempty and unique")
    if seed_state_ids[0] != NORMAL_STATE_ID:
        raise ValueError("seed_state_ids must begin with normal")
    if not set(seed_state_ids) <= set(all_state_ids):
        raise ValueError("seed_state_ids must be a subset of all_state_ids")
    gap = _finite_number(target_relative_gap)
    if gap is None or gap < 0.0:
        raise ValueError("target_relative_gap must be finite and nonnegative")
    maximum_relative = _finite_number(
        maximum_accepted_relative_gap_to_feasible_incumbent
    )
    if maximum_relative is None or maximum_relative < gap:
        raise ValueError(
            "maximum accepted relative gap must be finite and no smaller than target"
        )
    maximum_absolute = _finite_number(maximum_accepted_absolute_gap)
    if stage == "proxy_maximization" and (
        maximum_absolute is None or maximum_absolute < 0.0
    ):
        raise ValueError("Proxy maximization requires a nonnegative absolute gap cap")
    if maximum_accepted_absolute_gap is not None and (
        maximum_absolute is None or maximum_absolute < 0.0
    ):
        raise ValueError("maximum accepted absolute gap must be nonnegative")
    if stage == "proxy_maximization" and proxy_floor is not None:
        raise ValueError("Proxy maximization cannot receive a proxy floor")
    if stage == "cost_normalization" and _finite_number(proxy_floor) is None:
        raise ValueError("Cost normalization requires a finite proxy floor")
    if (
        candidate_deadline_monotonic is not None
        and candidate_remaining_seconds is not None
    ):
        raise ValueError("Specify one candidate deadline mechanism, not both")
    if (
        candidate_deadline_monotonic is not None
        and _finite_number(candidate_deadline_monotonic) is None
    ):
        raise ValueError("candidate_deadline_monotonic must be finite")


def _sense(stage: Stage) -> str:
    return "maximize" if stage == "proxy_maximization" else "minimize"


def _certificate(
    *,
    stage: Stage,
    full_feasible_objective: object,
    dual_bounds: Sequence[object],
    target_relative_gap: float,
) -> dict[str, object]:
    if stage == "proxy_maximization":
        return final_max_certificate(
            full_feasible_objective=full_feasible_objective,
            master_dual_upper_bounds=dual_bounds,
            target_relative_gap=target_relative_gap,
        )
    return final_min_certificate(
        full_feasible_objective=full_feasible_objective,
        master_dual_lower_bounds=dual_bounds,
        target_relative_gap=target_relative_gap,
    )


def _make_call(
    *,
    kind: CallKind,
    stage: Stage,
    iteration: int,
    active_state_ids: Sequence[str],
    all_state_ids: tuple[str, ...],
    proxy_floor: float | None,
    target_relative_gap: float,
    time_limits: ExactCgTimeLimits,
    candidate_deadline_monotonic: float | None,
    candidate_remaining_seconds: Callable[[], float] | None,
    monotonic_clock: Callable[[], float],
    state_id: str | None = None,
    shared_snapshot: SharedSnapshot | None = None,
    ordinal: int | None = None,
) -> ExactCgCall | None:
    cap = time_limits.for_kind(kind)
    remaining: float | None = None
    if candidate_deadline_monotonic is not None:
        remaining = float(candidate_deadline_monotonic) - float(monotonic_clock())
    elif candidate_remaining_seconds is not None:
        remaining = float(candidate_remaining_seconds())
    if remaining is not None:
        if math.isnan(remaining) or remaining == -math.inf:
            raise ValueError("Candidate remaining time must not be NaN or -infinity")
        if remaining <= 0.0:
            return None
        cap = min(cap, remaining)
    call_suffix = {
        "master": "master",
        "screen": f"screen_{int(ordinal or 0):02d}",
        "final_audit": "final_full_state_fixed_shared_audit",
    }[kind]
    return ExactCgCall(
        call_id=f"{stage}.iteration_{iteration:02d}.{call_suffix}",
        kind=kind,
        stage=stage,
        iteration=iteration,
        active_state_ids=tuple(active_state_ids),
        all_state_ids=all_state_ids,
        time_limit_seconds=float(cap),
        target_relative_gap=float(target_relative_gap),
        proxy_floor=proxy_floor,
        state_id=state_id,
        shared_snapshot=shared_snapshot,
    )


__all__ = [
    "ExactCgCall",
    "ExactCgCallbacks",
    "ExactCgStageResult",
    "ExactCgTimeLimits",
    "FullStateAuditResult",
    "MasterSolveResult",
    "StateScreenResult",
    "run_exact_cg_stage",
]
