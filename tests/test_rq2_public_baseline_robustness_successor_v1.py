from __future__ import annotations

import ast
import copy
import hashlib
import json
import os
from pathlib import Path

import pytest
import yaml

from src.evaluation import rq2_baseline_robustness_package_v1 as package
from src.models.rq2_baseline_robustness import FOUR_ARM_IDS

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_baseline_robustness_successor_v1.yaml"
MANIFEST = ROOT / "configs/rq2_public_baseline_robustness_successor_v1.SHA256SUMS.json"
VALIDATOR = (
    ROOT / "experiments/validate_rq2_public_baseline_robustness_successor_v1.py"
)


def _resume() -> dict[str, object]:
    return package.build_resume_identity(
        run_id="unit-run",
        successor_config_sha256="a" * 64,
        authority_sha256s={"baseline_preregistration": "b" * 64},
    )


def _result(
    *,
    capacity: float | None = 0.25,
    proven: bool = False,
    enforce_joint_budget: bool = True,
) -> dict:
    feasible = capacity is not None and not proven
    return {
        "enforce_joint_budget": enforce_joint_budget,
        "feasible": feasible,
        "proven_infeasible": proven,
        "minimum_capacity": capacity,
        "termination_condition": "optimal" if feasible else "unknown",
        "solver_status": "ok" if feasible else "aborted",
        "maximum_residual": 0.0 if feasible else None,
        "lower_bound": capacity,
        "upper_bound": capacity,
        "absolute_gap": 0.0 if feasible else None,
        "relative_gap": 0.0 if feasible else None,
        "gap_tolerance": 1.0e-6 if feasible else None,
        "model_variables": 10,
        "model_constraints": 20,
        "solver_name": "fake-not-executed",
        "solver_options": {"threads": 4},
    }


def _planning(*, reverse: bool = False, unknown_arm: str | None = None) -> dict:
    items = list(FOUR_ARM_IDS)
    if reverse:
        items.reverse()
    return {
        arm_id: (
            _result(
                capacity=None,
                enforce_joint_budget=arm_id != FOUR_ARM_IDS[-1],
            )
            if arm_id == unknown_arm
            else _result(enforce_joint_budget=arm_id != FOUR_ARM_IDS[-1])
        )
        for arm_id in items
    }


def _audit() -> dict:
    return {
        arm_id: {
            "arm_id": arm_id,
            "pair_count": 4,
            "failed_pair_ids": (),
            "unresolved_pair_ids": (),
        }
        for arm_id in reversed(FOUR_ARM_IDS)
    }


def _training_pair_ids() -> list[str]:
    return [
        "train-power-01__train-workload-01",
        "train-power-01__train-workload-02",
        "train-power-02__train-workload-01",
        "train-power-02__train-workload-02",
    ]


def _raw(*, resolved: bool = True, debt_only: bool = False) -> dict:
    violations = (
        ("maximum_recovery_debt_exceeded_at_step_3",) if debt_only else ()
    )
    return {
        "name": "fake-pair",
        "committed_flexibility": 0.25,
        "resolved": resolved,
        "hard_grid_failure": False,
        "physical_policy_failure": debt_only,
        "service_shortfall_failure": False,
        "access_shortfall": 0.0,
        "peak_recovery_debt": 0.1 if debt_only else 0.0,
        "terminal_recovery_debt": 0.0,
        "combined_call": (0.1, 0.2),
        "green_served": (0.0, 0.1),
        "physical_violations": violations,
    }


def _registered(raw: dict, *, debt_only: bool = False) -> dict:
    return {
        "schema": "rq2_baseline_registered_service_risk_v1",
        "resolved": raw["resolved"],
        "unresolved_reason": (
            None if raw["resolved"] else "source_causal_outcome_unresolved"
        ),
        "registered_failure": False if raw["resolved"] else None,
        "registered_physical_failure": False if raw["resolved"] else None,
        "service_shortfall_failure": False if raw["resolved"] else None,
        "service_shortfall_amount": 0.0 if raw["resolved"] else None,
        "registered_physical_violations": (),
        "excluded_debt_violations": raw["physical_violations"] if debt_only else (),
        "excluded_terminal_condition_violations": (),
        "right_censored": False,
        "raw_outcome": raw,
    }


def _execution(
    *,
    debt_only_arm: str | None = None,
    unresolved_arm: str | None = None,
    right_censored: bool = False,
):
    result = {}
    for arm_id in FOUR_ARM_IDS:
        debt_only = arm_id == debt_only_arm
        raw = _raw(resolved=arm_id != unresolved_arm, debt_only=debt_only)
        result[arm_id] = {
            "arm_id": arm_id,
            "committed_capacity": 0.25,
            "outcome": raw,
            "registered_service_risk": {
                **_registered(raw, debt_only=debt_only),
                "right_censored": right_censored,
            },
        }
    return result


def _planning_checkpoint(
    *, cell_id: str = "cell-01", provenance: dict | None = None
) -> dict[str, object]:
    return package.build_planning_checkpoint(
        cell_id=cell_id,
        planning=_planning(reverse=True),
        training_audit=_audit(),
        expected_training_pair_ids=list(reversed(_training_pair_ids())),
        resume_identity=_resume(),
        provenance=provenance or {"source": "synthetic-unit-test"},
    )


def _finite_checkpoint(
    *,
    cell_id: str = "cell-01",
    provenance: dict | None = None,
    right_censored: bool = False,
    boundary_state_status: str = "fully_observed",
    terminal_period_completed: bool = True,
    require_terminal_event_inactive: bool = True,
    **kwargs,
) -> dict[str, object]:
    return package.build_finite_pair_checkpoint(
        cell_id=cell_id,
        power_block_id="power-01",
        workload_block_id="workload-01",
        power_probability=0.25,
        workload_probability=1.0,
        right_censored=right_censored,
        boundary_state_status=boundary_state_status,
        terminal_period_completed=terminal_period_completed,
        require_terminal_event_inactive=require_terminal_event_inactive,
        execution=_execution(right_censored=right_censored, **kwargs),
        resume_identity=_resume(),
        provenance=provenance or {"source": "synthetic-unit-test"},
    )


def _E0_checkpoint(
    *,
    cell_id: str = "cell-01",
    provenance: dict | None = None,
    resolved: bool = True,
) -> dict[str, object]:
    return package.build_E0_pair_checkpoint(
        cell_id=cell_id,
        power_block_id="power-E0",
        workload_block_id="workload-01",
        power_probability=0.75,
        workload_probability=1.0,
        right_censored=False,
        boundary_state_status="fully_observed",
        terminal_period_completed=True,
        require_terminal_event_inactive=True,
        resolved=resolved,
        unresolved_reason=None if resolved else "grid_state_unresolved",
        resume_identity=_resume(),
        provenance=provenance or {"source": "synthetic-unit-test"},
    )


def _write(path: Path, value: dict[str, object]) -> Path:
    package.write_checkpoint_idempotent(path, value)
    return path


def _rewrite_json(path: Path, value: object) -> None:
    path.write_bytes(package._canonical_bytes(value))


def _rehash_package(target: Path) -> None:
    files = {
        path.relative_to(target).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(target.rglob("*"))
        if path.is_file() and path.name != "SHA256SUMS.json"
    }
    _rewrite_json(
        target / "SHA256SUMS.json",
        {"schema": package.PACKAGE_MANIFEST_SCHEMA, "files": files},
    )


def _publish_one_cell(tmp_path: Path) -> Path:
    planning = _write(tmp_path / "planning.json", _planning_checkpoint())
    pairs = [
        _write(tmp_path / "finite.json", _finite_checkpoint()),
        _write(tmp_path / "E0.json", _E0_checkpoint()),
    ]
    target = tmp_path / "package"
    package.publish_final_package(
        target=target,
        planning_checkpoint_paths=[planning],
        pair_checkpoint_paths=pairs,
        expected_cell_ids=["cell-01"],
        expected_pairs=_expected_pairs(),
        resume_identity=_resume(),
        provenance={"source": "synthetic-unit-test"},
    )
    return target


def _expected_pairs(*cells: str) -> list[dict[str, object]]:
    cells = cells or ("cell-01",)
    return [
        record
        for cell_id in cells
        for record in (
            {
                "cell_id": cell_id,
                "power_block_id": "power-01",
                "workload_block_id": "workload-01",
                "grid_state": package.FINITE_GRID_NEED,
                "power_probability": 0.25,
                "workload_probability": 1.0,
                "right_censored": False,
                "boundary_state_status": "fully_observed",
                "terminal_period_completed": True,
                "require_terminal_event_inactive": True,
            },
            {
                "cell_id": cell_id,
                "power_block_id": "power-E0",
                "workload_block_id": "workload-01",
                "grid_state": package.E0_GRID_STATE,
                "power_probability": 0.75,
                "workload_probability": 1.0,
                "right_censored": False,
                "boundary_state_status": "fully_observed",
                "terminal_period_completed": True,
                "require_terminal_event_inactive": True,
            },
        )
    ]


def test_planning_checkpoint_canonicalizes_reverse_capacity_order() -> None:
    checkpoint = _planning_checkpoint()
    assert checkpoint["disposition"] == "resolved"
    assert [
        item["arm_id"] for item in checkpoint["four_arm_minimum_flexibility"]
    ] == list(FOUR_ARM_IDS)
    assert [
        item["arm_id"] for item in checkpoint["four_arm_training_status"]
    ] == list(FOUR_ARM_IDS)
    assert [
        item["certificate"]["enforce_joint_budget"]
        for item in checkpoint["four_arm_minimum_flexibility"]
    ] == [True, True, True, False]


def test_B6_joint_budget_flag_drift_fails_closed() -> None:
    all_true = {arm_id: _result() for arm_id in FOUR_ARM_IDS}
    with pytest.raises(ValueError, match="joint-budget semantics drifted"):
        package.build_planning_checkpoint(
            cell_id="cell-01",
            planning=all_true,
            training_audit=_audit(),
            expected_training_pair_ids=_training_pair_ids(),
            resume_identity=_resume(),
            provenance={"source": "synthetic-unit-test"},
        )


def test_unknown_planning_is_unresolved_not_infeasible() -> None:
    checkpoint = package.build_planning_checkpoint(
        cell_id="cell-01",
        planning=_planning(unknown_arm=FOUR_ARM_IDS[0]),
        training_audit=None,
        expected_training_pair_ids=_training_pair_ids(),
        resume_identity=_resume(),
        provenance={},
    )
    arm = checkpoint["four_arm_minimum_flexibility"][0]
    assert arm["status"] == "unresolved"
    assert arm["status"] != "proven_infeasible"
    assert checkpoint["disposition"] == "unresolved"


def test_unknown_termination_cannot_be_forged_into_proven_infeasible() -> None:
    planning = _planning()
    planning[FOUR_ARM_IDS[0]] = _result(capacity=None, proven=True)
    checkpoint = package.build_planning_checkpoint(
        cell_id="cell-01",
        planning=planning,
        training_audit=None,
        expected_training_pair_ids=_training_pair_ids(),
        resume_identity=_resume(),
        provenance={},
    )
    assert checkpoint["four_arm_minimum_flexibility"][0]["status"] == "unresolved"
    assert checkpoint["disposition"] == "unresolved"


def test_checkpoint_write_is_idempotent_and_rejects_drift(tmp_path: Path) -> None:
    target = tmp_path / "planning.json"
    checkpoint = _planning_checkpoint()
    first = package.write_checkpoint_idempotent(target, checkpoint)
    second = package.write_checkpoint_idempotent(target, checkpoint)
    assert first == second == hashlib.sha256(target.read_bytes()).hexdigest()
    drifted = copy.deepcopy(checkpoint)
    drifted["provenance"]["drift"] = True
    with pytest.raises(FileExistsError, match="checkpoint drift"):
        package.write_checkpoint_idempotent(target, drifted)


def test_debt_only_raw_failure_does_not_become_registered_failure() -> None:
    checkpoint = _finite_checkpoint(debt_only_arm=FOUR_ARM_IDS[0])
    arm = checkpoint["arms"][0]
    assert arm["raw_causal_policy_outcome"]["physical_policy_failure"] is True
    registered = arm["registered_service_risk_outcome"]
    assert registered["registered_failure"] is False
    assert registered["registered_physical_failure"] is False
    assert registered["excluded_debt_violations"]


def test_missing_or_extra_arm_inventory_fails_closed() -> None:
    execution = _execution()
    execution.pop(FOUR_ARM_IDS[-1])
    with pytest.raises(ValueError, match="four-arm inventory"):
        package.build_finite_pair_checkpoint(
            cell_id="cell-01",
            power_block_id="power-01",
            workload_block_id="workload-01",
            power_probability=1.0,
            workload_probability=1.0,
            right_censored=False,
            boundary_state_status="fully_observed",
            terminal_period_completed=True,
            require_terminal_event_inactive=True,
            execution=execution,
            resume_identity=_resume(),
            provenance={"source": "synthetic-unit-test"},
        )


@pytest.mark.parametrize("unresolved", ["finite", "E0"])
def test_unresolved_pair_blocks_final_publish(tmp_path: Path, unresolved: str) -> None:
    planning = _write(tmp_path / "planning.json", _planning_checkpoint())
    finite = _finite_checkpoint(
        unresolved_arm=FOUR_ARM_IDS[0] if unresolved == "finite" else None
    )
    e0 = _E0_checkpoint(resolved=unresolved != "E0")
    pair_paths = [
        _write(tmp_path / "finite.json", finite),
        _write(tmp_path / "E0.json", e0),
    ]
    with pytest.raises(ValueError, match="unresolved"):
        package.publish_final_package(
            target=tmp_path / "package",
            planning_checkpoint_paths=[planning],
            pair_checkpoint_paths=pair_paths,
            expected_cell_ids=["cell-01"],
            expected_pairs=_expected_pairs(),
            resume_identity=_resume(),
            provenance={"source": "synthetic-unit-test"},
        )
    assert not (tmp_path / "package").exists()


def test_partial_maximum_pairs_returns_progress_without_publish(tmp_path: Path) -> None:
    planning = _write(tmp_path / "planning.json", _planning_checkpoint())
    finite = _write(tmp_path / "finite.json", _finite_checkpoint())
    target = tmp_path / "package"
    progress = package.publish_final_package(
        target=target,
        planning_checkpoint_paths=[planning],
        pair_checkpoint_paths=[finite],
        expected_cell_ids=["cell-01"],
        expected_pairs=_expected_pairs(),
        resume_identity=_resume(),
        provenance={"source": "synthetic-unit-test"},
        maximum_pairs=1,
    )
    assert progress["published"] is False
    assert progress["completed_pairs"] == 1
    assert not target.exists()


def test_extra_pair_checkpoint_fails_closed(tmp_path: Path) -> None:
    planning = _write(tmp_path / "planning.json", _planning_checkpoint())
    extra = _finite_checkpoint()
    extra["power_block_id"] = "power-extra"
    pair = _write(tmp_path / "extra.json", extra)
    with pytest.raises(ValueError, match="extra pair"):
        package.publish_final_package(
            target=tmp_path / "package",
            planning_checkpoint_paths=[planning],
            pair_checkpoint_paths=[pair],
            expected_cell_ids=["cell-01"],
            expected_pairs=_expected_pairs(),
            resume_identity=_resume(),
            provenance={"source": "synthetic-unit-test"},
            maximum_pairs=1,
        )


def test_missing_E0_checkpoint_fails_closed_at_full_publish(tmp_path: Path) -> None:
    planning = _write(tmp_path / "planning.json", _planning_checkpoint())
    finite = _write(tmp_path / "finite.json", _finite_checkpoint())
    with pytest.raises(ValueError, match="missing or extra"):
        package.publish_final_package(
            target=tmp_path / "package",
            planning_checkpoint_paths=[planning],
            pair_checkpoint_paths=[finite],
            expected_cell_ids=["cell-01"],
            expected_pairs=_expected_pairs(),
            resume_identity=_resume(),
            provenance={"source": "synthetic-unit-test"},
        )
    assert not (tmp_path / "package").exists()


def test_staging_failure_leaves_no_formal_looking_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    planning = _write(tmp_path / "planning.json", _planning_checkpoint())
    pairs = [
        _write(tmp_path / "finite.json", _finite_checkpoint()),
        _write(tmp_path / "E0.json", _E0_checkpoint()),
    ]
    target = tmp_path / "package"
    original = package._write_json
    calls = 0

    def fail_during_staging(path: Path, value: object) -> None:
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("synthetic staging failure")
        original(path, value)

    monkeypatch.setattr(package, "_write_json", fail_during_staging)
    with pytest.raises(OSError, match="synthetic staging failure"):
        package.publish_final_package(
            target=target,
            planning_checkpoint_paths=[planning],
            pair_checkpoint_paths=pairs,
            expected_cell_ids=["cell-01"],
            expected_pairs=_expected_pairs(),
            resume_identity=_resume(),
            provenance={"source": "synthetic-unit-test"},
        )
    assert not target.exists()
    assert not list(tmp_path.glob(".package.*"))


def test_complete_package_has_exact_inventory_and_cannot_overwrite(
    tmp_path: Path,
) -> None:
    planning = _write(tmp_path / "planning.json", _planning_checkpoint())
    pairs = [
        _write(tmp_path / "finite.json", _finite_checkpoint()),
        _write(tmp_path / "E0.json", _E0_checkpoint()),
    ]
    target = tmp_path / "package"
    receipt = package.publish_final_package(
        target=target,
        planning_checkpoint_paths=[planning],
        pair_checkpoint_paths=pairs,
        expected_cell_ids=["cell-01"],
        expected_pairs=_expected_pairs(),
        resume_identity=_resume(),
        provenance={"source": "synthetic-unit-test"},
    )
    assert receipt["published"] is True
    assert package.validate_final_package(target)["validation_passed"] is True
    manifest = json.loads((target / "SHA256SUMS.json").read_text("utf-8"))
    observed = {
        path.relative_to(target).as_posix()
        for path in target.rglob("*")
        if path.is_file() and path.name != "SHA256SUMS.json"
    }
    assert set(manifest["files"]) == observed
    with pytest.raises(FileExistsError, match="already exists"):
        package.publish_final_package(
            target=target,
            planning_checkpoint_paths=[planning],
            pair_checkpoint_paths=pairs,
            expected_cell_ids=["cell-01"],
            expected_pairs=_expected_pairs(),
            resume_identity=_resume(),
            provenance={"source": "synthetic-unit-test"},
        )


def test_publish_rejects_checkpoint_and_final_provenance_mismatch(
    tmp_path: Path,
) -> None:
    planning = _write(tmp_path / "planning.json", _planning_checkpoint())
    pairs = [
        _write(tmp_path / "finite.json", _finite_checkpoint()),
        _write(tmp_path / "E0.json", _E0_checkpoint()),
    ]
    with pytest.raises(ValueError, match="provenance drifted"):
        package.publish_final_package(
            target=tmp_path / "package",
            planning_checkpoint_paths=[planning],
            pair_checkpoint_paths=pairs,
            expected_cell_ids=["cell-01"],
            expected_pairs=_expected_pairs(),
            resume_identity=_resume(),
            provenance={"source": "different-final-provenance"},
        )


def test_final_validator_rejects_rehashed_checkpoint_provenance_attack(
    tmp_path: Path,
) -> None:
    target = _publish_one_cell(tmp_path)
    checkpoint_path = target / "checkpoints/planning/cell-01.json"
    checkpoint = json.loads(checkpoint_path.read_text("utf-8"))
    checkpoint["provenance"] = {"source": "attacker-B"}
    _rewrite_json(checkpoint_path, checkpoint)
    inventory_path = target / "checkpoint_inventory.json"
    inventory = json.loads(inventory_path.read_text("utf-8"))
    inventory["planning"][0]["sha256"] = hashlib.sha256(
        checkpoint_path.read_bytes()
    ).hexdigest()
    _rewrite_json(inventory_path, inventory)
    _rehash_package(target)
    with pytest.raises(ValueError, match="provenance"):
        package.validate_final_package(target)


def test_final_validator_rejects_rehashed_non_debt_failure_downgrade(
    tmp_path: Path,
) -> None:
    target = _publish_one_cell(tmp_path)
    checkpoint_path = target / "checkpoints/pairs/cell-01__power-01__workload-01.json"
    checkpoint = json.loads(checkpoint_path.read_text("utf-8"))
    arm = checkpoint["arms"][0]
    raw = arm["raw_causal_policy_outcome"]
    raw["physical_policy_failure"] = True
    raw["physical_violations"] = ["future_non_debt_physical_violation"]
    arm["registered_service_risk_outcome"]["raw_outcome"] = copy.deepcopy(raw)
    _rewrite_json(checkpoint_path, checkpoint)
    summary_path = target / "four_arm_pairwise_outcomes.json"
    summary = json.loads(summary_path.read_text("utf-8"))
    summary["pairs"][0] = checkpoint
    _rewrite_json(summary_path, summary)
    inventory_path = target / "checkpoint_inventory.json"
    inventory = json.loads(inventory_path.read_text("utf-8"))
    inventory["pairs"][0]["sha256"] = hashlib.sha256(
        checkpoint_path.read_bytes()
    ).hexdigest()
    _rewrite_json(inventory_path, inventory)
    _rehash_package(target)
    with pytest.raises(ValueError, match="registered service-risk layer"):
        package.validate_final_package(target)


@pytest.mark.parametrize(
    ("case", "registered_failure", "registered_physical_failure"),
    [
        ("unknown_non_debt", True, True),
        ("shortfall", True, False),
        ("debt_only", False, False),
        ("terminal_right_censored", False, False),
    ],
)
def test_registered_layer_exact_rebuild_cases(
    case: str,
    registered_failure: bool,
    registered_physical_failure: bool,
) -> None:
    right_censored = case == "terminal_right_censored"
    checkpoint = _finite_checkpoint(
        right_censored=right_censored,
        terminal_period_completed=not right_censored,
        debt_only_arm=FOUR_ARM_IDS[0] if case == "debt_only" else None,
    )
    arm = checkpoint["arms"][0]
    raw = arm["raw_causal_policy_outcome"]
    if case == "unknown_non_debt":
        raw["physical_policy_failure"] = True
        raw["physical_violations"] = ("future_unknown_physical_violation",)
    elif case == "shortfall":
        raw["service_shortfall_failure"] = True
        raw["access_shortfall"] = 0.2
    elif case == "terminal_right_censored":
        raw["physical_policy_failure"] = True
        raw["physical_violations"] = ("trace_ends_during_active_event",)
    arm["registered_service_risk_outcome"] = package._rebuild_registered_service_risk(
        raw, right_censored=right_censored
    )
    validated = package.validate_finite_pair_checkpoint(checkpoint)
    registered = validated["arms"][0]["registered_service_risk_outcome"]
    assert registered["registered_failure"] is registered_failure
    assert registered["registered_physical_failure"] is registered_physical_failure
    assert registered["right_censored"] is right_censored


def test_expected_marginals_and_cross_cell_identity_fail_closed(tmp_path: Path) -> None:
    planning = _write(tmp_path / "planning.json", _planning_checkpoint())
    bad_marginal = _expected_pairs()
    for item in bad_marginal:
        item["workload_probability"] = 0.9
    with pytest.raises(ValueError, match="workload marginal"):
        package.publish_final_package(
            target=tmp_path / "bad-marginal",
            planning_checkpoint_paths=[planning],
            pair_checkpoint_paths=[],
            expected_cell_ids=["cell-01"],
            expected_pairs=bad_marginal,
            resume_identity=_resume(),
            provenance={"source": "synthetic-unit-test"},
            maximum_pairs=0,
        )
    cross_cell = _expected_pairs("cell-01", "cell-02")
    cross_cell[2]["power_probability"] = 0.3
    planning_two = [
        planning,
        _write(
            tmp_path / "planning-02.json",
            _planning_checkpoint(cell_id="cell-02"),
        ),
    ]
    with pytest.raises(ValueError, match="drifted across cells"):
        package.publish_final_package(
            target=tmp_path / "bad-cross-cell",
            planning_checkpoint_paths=planning_two,
            pair_checkpoint_paths=[],
            expected_cell_ids=["cell-01", "cell-02"],
            expected_pairs=cross_cell,
            resume_identity=_resume(),
            provenance={"source": "synthetic-unit-test"},
            maximum_pairs=0,
        )


def test_checkpoint_probability_must_exactly_match_expected(tmp_path: Path) -> None:
    planning = _write(tmp_path / "planning.json", _planning_checkpoint())
    finite = _finite_checkpoint()
    finite["power_probability"] = 0.2
    finite["unconditional_pair_probability"] = 0.2
    finite_path = _write(tmp_path / "finite.json", finite)
    with pytest.raises(ValueError, match="expected power_probability"):
        package.publish_final_package(
            target=tmp_path / "package",
            planning_checkpoint_paths=[planning],
            pair_checkpoint_paths=[finite_path],
            expected_cell_ids=["cell-01"],
            expected_pairs=_expected_pairs(),
            resume_identity=_resume(),
            provenance={"source": "synthetic-unit-test"},
            maximum_pairs=1,
        )


def test_publish_rejects_pair_capacity_drift_from_planning(tmp_path: Path) -> None:
    planning = _write(tmp_path / "planning.json", _planning_checkpoint())
    finite = _finite_checkpoint()
    finite["arms"][0]["committed_capacity"] = 999.0
    pairs = [
        _write(tmp_path / "finite.json", finite),
        _write(tmp_path / "E0.json", _E0_checkpoint()),
    ]
    with pytest.raises(ValueError, match="committed capacity disagrees"):
        package.publish_final_package(
            target=tmp_path / "package",
            planning_checkpoint_paths=[planning],
            pair_checkpoint_paths=pairs,
            expected_cell_ids=["cell-01"],
            expected_pairs=_expected_pairs(),
            resume_identity=_resume(),
            provenance={"source": "synthetic-unit-test"},
        )


def test_final_validator_rejects_rehashed_pair_capacity_999_attack(
    tmp_path: Path,
) -> None:
    target = _publish_one_cell(tmp_path)
    checkpoint_path = target / "checkpoints/pairs/cell-01__power-01__workload-01.json"
    checkpoint = json.loads(checkpoint_path.read_text("utf-8"))
    checkpoint["arms"][0]["committed_capacity"] = 999.0
    _rewrite_json(checkpoint_path, checkpoint)
    summary_path = target / "four_arm_pairwise_outcomes.json"
    summary = json.loads(summary_path.read_text("utf-8"))
    summary["pairs"][0] = checkpoint
    _rewrite_json(summary_path, summary)
    inventory_path = target / "checkpoint_inventory.json"
    inventory = json.loads(inventory_path.read_text("utf-8"))
    inventory["pairs"][0]["sha256"] = hashlib.sha256(
        checkpoint_path.read_bytes()
    ).hexdigest()
    _rewrite_json(inventory_path, inventory)
    _rehash_package(target)
    with pytest.raises(ValueError, match="committed capacity disagrees"):
        package.validate_final_package(target)


def test_E0_mass_is_reported_once_across_two_cells(tmp_path: Path) -> None:
    cells = ("cell-01", "cell-02")
    expected = _expected_pairs(*cells)
    for item in expected:
        item["grid_state"] = package.E0_GRID_STATE
    planning_paths = [
        _write(
            tmp_path / f"planning-{cell_id}.json",
            _planning_checkpoint(cell_id=cell_id),
        )
        for cell_id in cells
    ]
    pair_paths = []
    for cell_id in cells:
        for power_id, probability in (("power-01", 0.25), ("power-E0", 0.75)):
            checkpoint = _E0_checkpoint(cell_id=cell_id)
            checkpoint["power_block_id"] = power_id
            checkpoint["power_probability"] = probability
            checkpoint["unconditional_pair_probability"] = probability
            package.validate_E0_pair_checkpoint(checkpoint)
            pair_paths.append(
                _write(tmp_path / f"{cell_id}-{power_id}.json", checkpoint)
            )
    target = tmp_path / "package"
    package.publish_final_package(
        target=target,
        planning_checkpoint_paths=planning_paths,
        pair_checkpoint_paths=pair_paths,
        expected_cell_ids=list(cells),
        expected_pairs=expected,
        resume_identity=_resume(),
        provenance={"source": "synthetic-unit-test"},
    )
    outcomes = json.loads((target / "E0_outcomes.json").read_text("utf-8"))
    assert outcomes["unconditional_probability_mass_by_cell"] == {
        "cell-01": 1.0,
        "cell-02": 1.0,
    }
    assert outcomes["public_marginal_mass_once"] == 1.0


def test_training_cartesian_inventory_hash_and_status_ids_fail_closed() -> None:
    checkpoint = _planning_checkpoint()
    inventory = checkpoint["training_pair_inventory"]
    assert inventory["pair_ids"] == sorted(_training_pair_ids())
    assert inventory["canonical_sha256"] == hashlib.sha256(
        package._canonical_bytes(sorted(_training_pair_ids()))
    ).hexdigest()
    drifted = copy.deepcopy(checkpoint)
    drifted["four_arm_training_status"][0]["failed_pair_ids"] = ["outside-pair"]
    drifted["four_arm_training_status"][0]["status"] = "failed"
    drifted["disposition"] = "unresolved"
    with pytest.raises(ValueError, match="pair IDs drifted"):
        package.validate_planning_checkpoint(drifted)
    drifted = copy.deepcopy(checkpoint)
    shared_pair = _training_pair_ids()[0]
    drifted["four_arm_training_status"][0]["failed_pair_ids"] = [shared_pair]
    drifted["four_arm_training_status"][0]["unresolved_pair_ids"] = [shared_pair]
    drifted["four_arm_training_status"][0]["status"] = "failed"
    drifted["disposition"] = "unresolved"
    with pytest.raises(ValueError, match="pair IDs drifted"):
        package.validate_planning_checkpoint(drifted)
    drifted = copy.deepcopy(checkpoint)
    drifted["four_arm_training_status"][0]["pair_count"] = 3
    with pytest.raises(ValueError, match="pair_count"):
        package.validate_planning_checkpoint(drifted)
    drifted = copy.deepcopy(checkpoint)
    drifted["training_pair_inventory"]["canonical_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="hash/order drifted"):
        package.validate_planning_checkpoint(drifted)


def test_compute_wrapper_derives_full_training_cartesian_ids(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        package,
        "plan_four_arm_minimum_flexibility_with_spec",
        lambda *args, **kwargs: _planning(),
    )
    monkeypatch.setattr(
        package,
        "audit_four_arm_training_support",
        lambda *args, **kwargs: _audit(),
    )
    checkpoint = package.compute_planning_checkpoint(
        cell_id="cell-01",
        training_inputs=object(),
        solver_specification=object(),
        power_blocks=(
            {"block_id": "train-power-02"},
            {"block_id": "train-power-01"},
        ),
        workload_blocks=(
            {"block_id": "train-workload-02"},
            {"block_id": "train-workload-01"},
        ),
        cell=object(),
        fixed_policy={},
        grid_state_by_power_block={},
        resume_identity=_resume(),
        provenance={"source": "synthetic-unit-test"},
    )
    assert checkpoint["training_pair_inventory"]["pair_ids"] == sorted(
        _training_pair_ids()
    )


def test_final_rejects_training_cartesian_drift_across_cells(tmp_path: Path) -> None:
    first = _write(tmp_path / "planning-01.json", _planning_checkpoint())
    second_checkpoint = package.build_planning_checkpoint(
        cell_id="cell-02",
        planning=_planning(),
        training_audit=_audit(),
        expected_training_pair_ids=[
            "different-power-01__train-workload-01",
            "different-power-01__train-workload-02",
            "different-power-02__train-workload-01",
            "different-power-02__train-workload-02",
        ],
        resume_identity=_resume(),
        provenance={"source": "synthetic-unit-test"},
    )
    second = _write(tmp_path / "planning-02.json", second_checkpoint)
    with pytest.raises(ValueError, match="training Cartesian inventory"):
        package.publish_final_package(
            target=tmp_path / "package",
            planning_checkpoint_paths=[first, second],
            pair_checkpoint_paths=[],
            expected_cell_ids=["cell-01", "cell-02"],
            expected_pairs=_expected_pairs("cell-01", "cell-02"),
            resume_identity=_resume(),
            provenance={"source": "synthetic-unit-test"},
            maximum_pairs=0,
        )


def _mark_one_path_as_reparse(monkeypatch: pytest.MonkeyPatch, blocked: Path) -> None:
    original = package._path_is_reparse
    blocked_name = os.path.normcase(os.path.abspath(blocked))

    def is_reparse(path: Path) -> bool:
        if os.path.normcase(os.path.abspath(path)) == blocked_name:
            return True
        return original(path)

    monkeypatch.setattr(package, "_path_is_reparse", is_reparse)


def test_checkpoint_parent_and_leaf_reparse_paths_are_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    blocked_parent = tmp_path / "blocked-parent"
    blocked_parent.mkdir()
    _mark_one_path_as_reparse(monkeypatch, blocked_parent)
    with pytest.raises(ValueError, match="reparse path component"):
        package.write_checkpoint_idempotent(
            blocked_parent / "checkpoint.json", _planning_checkpoint()
        )
    monkeypatch.undo()
    leaf = _write(tmp_path / "leaf.json", _planning_checkpoint())
    _mark_one_path_as_reparse(monkeypatch, leaf)
    with pytest.raises(ValueError, match="reparse path component"):
        package.write_checkpoint_idempotent(leaf, _planning_checkpoint())


def test_target_parent_and_final_child_reparse_paths_are_rejected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    planning = _write(tmp_path / "planning.json", _planning_checkpoint())
    pairs = [
        _write(tmp_path / "finite.json", _finite_checkpoint()),
        _write(tmp_path / "E0.json", _E0_checkpoint()),
    ]
    blocked_parent = tmp_path / "blocked-target-parent"
    blocked_parent.mkdir()
    _mark_one_path_as_reparse(monkeypatch, blocked_parent)
    with pytest.raises(ValueError, match="reparse path component"):
        package.publish_final_package(
            target=blocked_parent / "package",
            planning_checkpoint_paths=[planning],
            pair_checkpoint_paths=pairs,
            expected_cell_ids=["cell-01"],
            expected_pairs=_expected_pairs(),
            resume_identity=_resume(),
            provenance={"source": "synthetic-unit-test"},
        )
    monkeypatch.undo()
    target = _publish_one_cell(tmp_path / "valid")
    child = target / "checkpoints"
    _mark_one_path_as_reparse(monkeypatch, child)
    with pytest.raises(ValueError, match="reparse package child"):
        package.validate_final_package(target)


def test_package_core_calculation_surface_uses_only_registered_public_APIs() -> None:
    tree = ast.parse(
        (ROOT / "src/evaluation/rq2_baseline_robustness_package_v1.py").read_text(
            encoding="utf-8"
        )
    )
    call_names = {
        node.func.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
    }
    assert {
        "plan_four_arm_minimum_flexibility_with_spec",
        "audit_four_arm_training_support",
        "execute_four_arm_causal_policy",
    } <= call_names
    assert "_failure" not in call_names


def _validator_namespace() -> dict[str, object]:
    source = VALIDATOR.read_text(encoding="utf-8")
    namespace: dict[str, object] = {
        "__name__": "successor_validator_test",
        "__file__": str(VALIDATOR),
    }
    exec(compile(source, str(VALIDATOR), "exec"), namespace)
    return namespace


@pytest.mark.parametrize("mutation", ["delete", "replace", "add"])
def test_validator_rejects_recomputed_authority_inventory_mutation(
    tmp_path: Path, mutation: str
) -> None:
    config = yaml.safe_load(CONFIG.read_text(encoding="utf-8"))
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    authorities = config["frozen_scientific_authority"]
    pairwise_path = authorities["pairwise_v4"]["path"]
    if mutation == "delete":
        authorities.pop("pairwise_v4")
        manifest["files"].pop(pairwise_path)
    elif mutation == "replace":
        authorities["pairwise_v4"] = copy.deepcopy(authorities["identification_v4"])
        manifest["files"].pop(pairwise_path)
    else:
        authorities["extra_pairwise_alias"] = copy.deepcopy(
            authorities["pairwise_v4"]
        )
    config_path = tmp_path / "mutated.yaml"
    config_path.write_text(
        yaml.safe_dump(config, allow_unicode=True, sort_keys=False),
        encoding="utf-8",
    )
    for relative in list(manifest["files"]):
        path = config_path if relative == CONFIG.relative_to(ROOT).as_posix() else ROOT / relative
        manifest["files"][relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    manifest_path = tmp_path / "mutated.SHA256SUMS.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    namespace = _validator_namespace()
    with pytest.raises(ValueError, match="exact authority inventory"):
        namespace["validate"](config_path, manifest_path)


def test_successor_validator_is_read_only_and_does_not_import_runtime_core(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    if not VALIDATOR.exists():
        pytest.skip("successor validator is added with the authority manifest")
    source = VALIDATOR.read_text(encoding="utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    } | {
        node.module or ""
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    }
    assert not any(name.startswith("src") for name in imports)
    namespace = _validator_namespace()
    monkeypatch.setattr(Path, "write_text", lambda *args, **kwargs: pytest.fail("write"))
    monkeypatch.setattr(Path, "write_bytes", lambda *args, **kwargs: pytest.fail("write"))
    result = namespace["validate"](CONFIG, MANIFEST)
    assert result["validation_passed"] is True
    assert result["solver_calls"] == 0
    assert result["result_files_written"] == 0
