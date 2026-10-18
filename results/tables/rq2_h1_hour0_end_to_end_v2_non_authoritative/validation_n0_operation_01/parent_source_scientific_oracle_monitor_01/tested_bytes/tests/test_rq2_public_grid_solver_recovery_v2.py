from __future__ import annotations

import json
import sys
import time
from copy import deepcopy
from pathlib import Path

import pytest
import yaml

from experiments import (
    run_rts_gmlc_public_grid_need_dispatch_v4_process_isolated_v1 as runner,
)

TEMPLATE = Path(
    "configs/rts_gmlc_public_grid_need_dispatch_v4_highs_process_isolated_v1.yaml"
)


def _block(block_id: str, *, event_hour: int | None = None) -> list[dict[str, str]]:
    return [
        {
            "block_id": block_id,
            "split": "holdout",
            "block_probability": "0.1",
            "outage_seed": "20260822",
            "hour_offset": str(hour),
            "source_hour": str(1000 + hour),
            "timestamp": f"2020-01-01T{hour:02d}:00:00",
            "system_load_mw": "1000.0",
            "cfe_call_fraction": "0.5",
            "active_event_id": "event_0001" if hour == event_hour else "",
            "active_component_type": "generator" if hour == event_hour else "",
            "active_component_uid": "101_PV_1" if hour == event_hour else "",
        }
        for hour in range(24)
    ]


def _certificate(
    *, value: float = 0.0, model_variables: int = 0, model_constraints: int = 0
) -> dict[str, object]:
    gap_tolerance = 0.0 if model_variables == 0 else max(1.0e-6, 1.0e-6 * value)
    return {
        "objective_incumbent_mw": value,
        "lower_bound_mw": value,
        "upper_bound_mw": value,
        "absolute_gap_mw": 0.0,
        "relative_gap": 0.0,
        "gap_tolerance_mw": gap_tolerance,
        "model_variables": model_variables,
        "model_constraints": model_constraints,
    }


def _infeasible_certificate() -> dict[str, object]:
    return {
        "objective_incumbent_mw": None,
        "lower_bound_mw": None,
        "upper_bound_mw": None,
        "absolute_gap_mw": None,
        "relative_gap": None,
        "gap_tolerance_mw": None,
        "model_variables": 10,
        "model_constraints": 20,
    }


def _baseline(config: dict, *, has_event: bool) -> dict[str, object]:
    if not has_event:
        return {
            "accepted": True,
            "termination_condition": "not_applicable_no_active_outage",
        }
    gap_tolerance = max(
        float(config["solver"]["tolerance_mw"]),
        max(float(config["solver"]["mip_relative_gap"]), 1.0e-8) * 100.0,
    )
    return {
        "accepted": True,
        "termination_condition": "optimal",
        "solver_status": "ok",
        "solver_message": "synthetic accepted test solve",
        "objective_usd": 100.0,
        "lower_bound_usd": 100.0,
        "upper_bound_usd": 100.0,
        "absolute_gap_usd": 0.0,
        "relative_gap": 0.0,
        "gap_tolerance_usd": gap_tolerance,
        "maximum_constraint_violation": 0.0,
        "maximum_integrality_violation": 0.0,
        "solver_threads": 4,
        "configured_mip_relative_gap": 1.0e-6,
        "model_variables": 100,
        "model_constraints": 200,
        "solver_name": "highs",
        "solver_options": runner.solver_options(runner.solver_spec(config["solver"])),
    }


def _finite_outcome_and_row(
    input_row: dict[str, str], config: dict
) -> tuple[dict[str, object], dict[str, object]]:
    active = bool(input_row["active_event_id"])
    value = 5.0 if active else 0.0
    certificate = _certificate(
        value=value,
        model_variables=10 if active else 0,
        model_constraints=20 if active else 0,
    )
    primary = {
        "source_hour": int(input_row["source_hour"]),
        "event_id": input_row["active_event_id"] or None,
        "component_type": input_row["active_component_type"] or None,
        "component_uid": input_row["active_component_uid"] or None,
        "resolved": True,
        "proven_infeasible": False,
        "grid_need_mw": value,
        "termination_condition": (
            "optimal" if active else "not_applicable_no_active_outage"
        ),
        "solver_status": "ok" if active else "not_applicable",
        "maximum_constraint_violation": 0.0,
    }
    outcome = {
        "state": runner.FINITE_GRID_NEED,
        "resolved_for_pipeline": True,
        "primary": primary,
        "primary_certificate": certificate,
        "zero_dc_confirmation": None,
        "zero_dc_confirmation_certificate": None,
        "solver_name": "highs",
        "solver_options": (
            runner.solver_options(runner.solver_spec(config["solver"]))
            if active
            else {}
        ),
    }
    row: dict[str, object] = {
        **input_row,
        "grid_need_mw": value,
        "grid_need_fraction": value / 250.0,
        "dispatch_resolved": "true",
        "dispatch_proven_infeasible": "false",
        "dispatch_state": runner.FINITE_GRID_NEED,
        "dispatch_objective_incumbent_mw": certificate[
            "objective_incumbent_mw"
        ],
        "dispatch_lower_bound_mw": certificate["lower_bound_mw"],
        "dispatch_upper_bound_mw": certificate["upper_bound_mw"],
        "dispatch_absolute_gap_mw": certificate["absolute_gap_mw"],
        "dispatch_relative_gap": certificate["relative_gap"],
        "dispatch_gap_tolerance_mw": certificate["gap_tolerance_mw"],
        "dispatch_model_variables": certificate["model_variables"],
        "dispatch_model_constraints": certificate["model_constraints"],
        "zero_dc_confirmation_termination_condition": "",
        "zero_dc_confirmation_solver_status": "",
        "zero_dc_confirmation_lower_bound_mw": "",
        "zero_dc_confirmation_upper_bound_mw": "",
        "zero_dc_confirmation_absolute_gap_mw": "",
        "zero_dc_confirmation_model_variables": "",
        "zero_dc_confirmation_model_constraints": "",
        "dispatch_termination_condition": primary["termination_condition"],
        "dispatch_solver_status": primary["solver_status"],
        "maximum_constraint_violation": 0.0,
    }
    return outcome, row


def _payload(
    block_id: str,
    config: dict,
    block: list[dict[str, str]],
    *,
    e0_hour: int | None = None,
) -> dict[str, object]:
    pairs = [_finite_outcome_and_row(row, config) for row in block]
    outcomes = [item[0] for item in pairs]
    rows = [item[1] for item in pairs]
    if e0_hour is not None:
        input_row = block[e0_hour]
        if not input_row["active_event_id"]:
            raise ValueError("E0 test hour must contain an active event")
        primary = {
            "source_hour": int(input_row["source_hour"]),
            "event_id": input_row["active_event_id"],
            "component_type": input_row["active_component_type"],
            "component_uid": input_row["active_component_uid"],
            "resolved": False,
            "proven_infeasible": True,
            "grid_need_mw": None,
            "termination_condition": "infeasible",
            "solver_status": "warning",
            "maximum_constraint_violation": None,
        }
        certificate = _infeasible_certificate()
        outcomes[e0_hour] = {
            "state": runner.EXOGENOUS_GRID_INFEASIBILITY,
            "resolved_for_pipeline": True,
            "primary": primary,
            "primary_certificate": certificate,
            "zero_dc_confirmation": dict(primary),
            "zero_dc_confirmation_certificate": dict(certificate),
            "solver_name": "highs",
            "solver_options": runner.solver_options(
                runner.solver_spec(config["solver"])
            ),
        }
        rows[e0_hour] = {
            **input_row,
            "grid_need_mw": "",
            "grid_need_fraction": "",
            "dispatch_resolved": "false",
            "dispatch_proven_infeasible": "true",
            "dispatch_state": runner.EXOGENOUS_GRID_INFEASIBILITY,
            "dispatch_objective_incumbent_mw": "",
            "dispatch_lower_bound_mw": "",
            "dispatch_upper_bound_mw": "",
            "dispatch_absolute_gap_mw": "",
            "dispatch_relative_gap": "",
            "dispatch_gap_tolerance_mw": "",
            "dispatch_model_variables": 10,
            "dispatch_model_constraints": 20,
            "zero_dc_confirmation_termination_condition": "infeasible",
            "zero_dc_confirmation_solver_status": "warning",
            "zero_dc_confirmation_lower_bound_mw": "",
            "zero_dc_confirmation_upper_bound_mw": "",
            "zero_dc_confirmation_absolute_gap_mw": "",
            "zero_dc_confirmation_model_variables": 10,
            "zero_dc_confirmation_model_constraints": 20,
            "dispatch_termination_condition": "infeasible",
            "dispatch_solver_status": "warning",
            "maximum_constraint_violation": "",
        }
    return {
        "block_id": block_id,
        "split": "holdout",
        "baseline_audit": _baseline(
            config, has_event=any(row["active_event_id"] for row in block)
        ),
        "all_hours_resolved": True,
        "exogenous_grid_infeasibility_hour_count": int(e0_hour is not None),
        "outcomes": outcomes,
        "rows": rows,
    }


def _context(
    tmp_path: Path,
    block_ids: tuple[str, ...] = ("block_0000",),
    *,
    event_hour: int | None = None,
) -> dict:
    config = yaml.safe_load(TEMPLATE.read_text(encoding="utf-8"))
    config["execution"]["checkpoint_directory"] = str(tmp_path / "checkpoints")
    process = config["execution"]["process_isolation"]
    process["worker_staging_directory"] = str(tmp_path / "workers")
    process["attempt_log_directory"] = str(tmp_path / "logs")
    config["output"]["directory"] = str(tmp_path / "output")
    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    blocks = {block_id: _block(block_id, event_hour=event_hour) for block_id in block_ids}
    return {
        "config": config,
        "config_path": config_path,
        "blocks": blocks,
        "stage_base_sha256": "a" * 64,
    }


def _request_result(
    tmp_path: Path,
    context: dict,
    block_id: str,
    *,
    worker_pid: int,
    parent_pid: int = 101,
    nonce: str = "b" * 64,
) -> tuple[dict, dict, Path, Path]:
    attempt = tmp_path / f"attempt-{block_id}-{nonce[:8]}"
    attempt.mkdir()
    request_path = attempt / "request.json"
    result_path = attempt / "result.json"
    dispatch_started_ns = time.time_ns() - 1_000_000
    request = {
        "schema": runner.REQUEST_SCHEMA,
        "block_id": block_id,
        "block_input_sha256": runner._block_input_sha256(context["blocks"][block_id]),
        "config_path": str(context["config_path"]),
        "config_sha256": runner._sha256(context["config_path"]),
        "stage": runner.STAGE,
        "stage_base_provenance_sha256": context["stage_base_sha256"],
        "parent_pid": parent_pid,
        "parent_dispatch_started_ns": dispatch_started_ns,
        "nonce": nonce,
        "python_executable": str(Path(sys.executable).resolve()),
        "python_executable_sha256": runner._sha256(Path(sys.executable)),
        "implementation": runner._implementation_bindings(),
        "solver": runner._solver_binding(context["config"]),
        "formal_roots": {
            "checkpoint": str((tmp_path / "checkpoints").resolve()),
            "output": str((tmp_path / "output").resolve()),
        },
        "worker_result_path": str(result_path.resolve()),
    }
    request_path.write_text(json.dumps(request), encoding="utf-8")
    block = context["blocks"][block_id]
    payload = _payload(block_id, context["config"], block)
    result = {
        "schema": runner.RESULT_SCHEMA,
        "status": "complete",
        "block_id": block_id,
        "request_sha256": runner._sha256(request_path),
        "config_sha256": request["config_sha256"],
        "stage_base_provenance_sha256": context["stage_base_sha256"],
        "parent_pid": parent_pid,
        "worker_pid": worker_pid,
        "worker_parent_pid": parent_pid,
        "worker_started_ns": time.time_ns(),
        "nonce": request["nonce"],
        "python_executable": request["python_executable"],
        "python_executable_sha256": request["python_executable_sha256"],
        "implementation": request["implementation"],
        "solver": request["solver"],
        "scientific_payload": payload,
        "scientific_payload_sha256": runner._canonical_sha256(payload),
        "all_hours_resolved": True,
        "mathematical_infeasibility_inferred_from_failure": False,
    }
    result_path.write_text(json.dumps(result), encoding="utf-8")
    return request, result, request_path, result_path


def _envelope(
    tmp_path: Path,
    context: dict,
    block_id: str,
    worker_pid: int,
    *,
    nonce: str = "b" * 64,
) -> dict:
    request, result, request_path, result_path = _request_result(
        tmp_path, context, block_id, worker_pid=worker_pid, nonce=nonce
    )
    runner._validate_worker_result(
        request,
        result,
        request_path=request_path,
        observed_pid=worker_pid,
        observed_exit_code=0,
        prior_attempt_identities=set(),
        context=context,
    )
    return runner._checkpoint_envelope(
        request,
        result,
        request_path=request_path,
        result_path=result_path,
        observed_pid=worker_pid,
    )


def test_validate_only_is_zero_solver_and_zero_formal_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runner.subprocess,
        "Popen",
        lambda *args, **kwargs: pytest.fail("validate-only spawned a worker"),
    )
    monkeypatch.setattr(
        runner.v4,
        "_process_block",
        lambda *args, **kwargs: pytest.fail("parent called the solver path"),
    )
    report = runner.run(TEMPLATE, validate_only=True)
    assert report["solver_calls"] == 0
    assert report["formal_writes"] == 0
    assert report["formal_execution_ready"] is False
    assert report["two_block_full_process_pilot_post_result_passed"] is False
    assert report["dispatch_authority"]["user_formal_run_authorized"] is False


def test_formal_root_overlap_is_rejected(tmp_path: Path) -> None:
    context = _context(tmp_path)
    context["config"]["execution"]["process_isolation"][
        "worker_staging_directory"
    ] = str(tmp_path / "checkpoints" / "workers")
    with pytest.raises(ValueError, match="roots overlap"):
        runner._require_isolated_roots(context["config"])


def test_worker_result_path_cannot_escape_to_formal_root(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    context = _context(tmp_path)
    request, _, request_path, _ = _request_result(
        tmp_path, context, "block_0000", worker_pid=303
    )
    request["worker_result_path"] = str(
        (tmp_path / "checkpoints" / "forbidden.json").resolve()
    )
    request_path.write_text(json.dumps(request), encoding="utf-8")
    monkeypatch.setattr(runner.os, "getppid", lambda: request["parent_pid"])
    monkeypatch.setattr(
        runner, "_require_dispatch_authority", lambda *args, **kwargs: {}
    )
    with pytest.raises(ValueError, match="escaped its isolated request directory"):
        runner._validate_request(request, request_path)


def test_closed_hidden_worker_fails_before_scientific_preflight_or_solver(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    context = runner._stage_context(TEMPLATE)
    request_path = tmp_path / "attempt" / "request.json"
    request_path.parent.mkdir()
    request = runner._build_request(
        context,
        block_id=min(context["blocks"]),
        parent_pid=12345,
        parent_dispatch_started_ns=time.time_ns() - 1_000_000,
        nonce="d" * 64,
        python_executable=Path(sys.executable).resolve(),
        worker_result_path=request_path.parent / "result.json",
    )
    request_path.write_text(json.dumps(request), encoding="utf-8")
    monkeypatch.setattr(runner.os, "getppid", lambda: 12345)
    monkeypatch.setattr(
        runner,
        "_stage_context",
        lambda *args, **kwargs: pytest.fail("closed worker loaded scientific inputs"),
    )
    monkeypatch.setattr(
        runner,
        "load_rts_gmlc_chronological_data",
        lambda *args, **kwargs: pytest.fail("closed worker loaded grid data"),
    )
    monkeypatch.setattr(
        runner.v4,
        "_process_block",
        lambda *args, **kwargs: pytest.fail("closed worker called solver path"),
    )
    with pytest.raises(ValueError, match="dispatch authority is closed"):
        runner._worker(request_path)


def test_worker_result_rejects_identity_and_duplicate_attempt(tmp_path: Path) -> None:
    context = _context(tmp_path)
    request, result, request_path, _ = _request_result(
        tmp_path, context, "block_0000", worker_pid=303
    )
    drifted = deepcopy(result)
    drifted["nonce"] = "c" * 64
    with pytest.raises(ValueError, match="identity, exit, or authority"):
        runner._validate_worker_result(
            request,
            drifted,
            request_path=request_path,
            observed_pid=303,
            observed_exit_code=0,
            prior_attempt_identities=set(),
            context=context,
        )
    identity = (request["nonce"], runner._sha256(request_path))
    with pytest.raises(ValueError, match="already consumed"):
        runner._validate_worker_result(
            request,
            result,
            request_path=request_path,
            observed_pid=303,
            observed_exit_code=0,
            prior_attempt_identities={identity},
            context=context,
        )


@pytest.mark.parametrize("mutation", ["empty", "missing", "extra", "corrupt"])
def test_empty_missing_extra_or_corrupt_certificate_is_rejected(
    tmp_path: Path, mutation: str
) -> None:
    context = _context(tmp_path)
    payload = _payload(
        "block_0000", context["config"], context["blocks"]["block_0000"]
    )
    certificate = payload["outcomes"][0]["primary_certificate"]
    if mutation == "empty":
        payload["outcomes"][0]["primary_certificate"] = {}
    elif mutation == "missing":
        del certificate["upper_bound_mw"]
    elif mutation == "extra":
        certificate["extra"] = 0.0
    else:
        certificate["objective_incumbent_mw"] = "0.0"
    with pytest.raises((TypeError, ValueError), match="certificate"):
        runner._validate_scientific_payload(
            payload,
            block_id="block_0000",
            expected_block=context["blocks"]["block_0000"],
            config=context["config"],
        )


def test_reversed_hourly_bounds_fail_before_checkpoint_publication(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path, event_hour=3)
    request, result, request_path, _ = _request_result(
        tmp_path, context, "block_0000", worker_pid=303
    )
    outcome = result["scientific_payload"]["outcomes"][3]
    certificate = outcome["primary_certificate"]
    certificate.update(
        {
            "objective_incumbent_mw": 0.0,
            "lower_bound_mw": 5.0e-7,
            "upper_bound_mw": 0.0,
            "absolute_gap_mw": 5.0e-7,
            "relative_gap": 5.0e5,
            "gap_tolerance_mw": 1.0e-6,
        }
    )
    outcome["primary"]["grid_need_mw"] = 0.0
    row = result["scientific_payload"]["rows"][3]
    row.update(
        {
            "grid_need_mw": 0.0,
            "grid_need_fraction": 0.0,
            "dispatch_objective_incumbent_mw": 0.0,
            "dispatch_lower_bound_mw": 5.0e-7,
            "dispatch_upper_bound_mw": 0.0,
            "dispatch_absolute_gap_mw": 5.0e-7,
            "dispatch_relative_gap": 5.0e5,
            "dispatch_gap_tolerance_mw": 1.0e-6,
        }
    )
    result["scientific_payload_sha256"] = runner._canonical_sha256(
        result["scientific_payload"]
    )
    with pytest.raises(ValueError, match="bound order"):
        runner._validate_worker_result(
            request,
            result,
            request_path=request_path,
            observed_pid=303,
            observed_exit_code=0,
            prior_attempt_identities=set(),
            context=context,
        )
    checkpoint = Path(context["config"]["execution"]["checkpoint_directory"])
    assert not (checkpoint / "block_0000.json").exists()


def test_reversed_baseline_bounds_fail_before_checkpoint_publication(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path, event_hour=3)
    request, result, request_path, _ = _request_result(
        tmp_path, context, "block_0000", worker_pid=303
    )
    baseline = result["scientific_payload"]["baseline_audit"]
    baseline.update(
        {
            "objective_usd": 0.0,
            "lower_bound_usd": 5.0e-7,
            "upper_bound_usd": 0.0,
            "absolute_gap_usd": 5.0e-7,
            "relative_gap": 5.0e5,
            "gap_tolerance_usd": 1.0e-6,
        }
    )
    result["scientific_payload_sha256"] = runner._canonical_sha256(
        result["scientific_payload"]
    )
    with pytest.raises(ValueError, match="bound order"):
        runner._validate_worker_result(
            request,
            result,
            request_path=request_path,
            observed_pid=303,
            observed_exit_code=0,
            prior_attempt_identities=set(),
            context=context,
        )
    checkpoint = Path(context["config"]["execution"]["checkpoint_directory"])
    assert not (checkpoint / "block_0000.json").exists()


@pytest.mark.parametrize(
    ("certificate_field", "row_field"),
    [
        ("absolute_gap_mw", "dispatch_absolute_gap_mw"),
        ("relative_gap", "dispatch_relative_gap"),
        ("gap_tolerance_mw", "dispatch_gap_tolerance_mw"),
    ],
)
def test_hourly_derived_field_drift_fails_before_checkpoint_publication(
    tmp_path: Path,
    certificate_field: str,
    row_field: str,
) -> None:
    context = _context(tmp_path, event_hour=3)
    request, result, request_path, _ = _request_result(
        tmp_path, context, "block_0000", worker_pid=303
    )
    certificate = result["scientific_payload"]["outcomes"][3][
        "primary_certificate"
    ]
    observed = certificate[certificate_field]
    drifted = (
        float(observed) + 5.0e-10
        if certificate_field == "gap_tolerance_mw"
        else -1.0e-30
    )
    certificate[certificate_field] = drifted
    result["scientific_payload"]["rows"][3][row_field] = drifted
    result["scientific_payload_sha256"] = runner._canonical_sha256(
        result["scientific_payload"]
    )
    with pytest.raises(ValueError):
        runner._validate_worker_result(
            request,
            result,
            request_path=request_path,
            observed_pid=303,
            observed_exit_code=0,
            prior_attempt_identities=set(),
            context=context,
        )
    checkpoint = Path(context["config"]["execution"]["checkpoint_directory"])
    assert not (checkpoint / "block_0000.json").exists()


@pytest.mark.parametrize(
    "baseline_field",
    [
        "absolute_gap_usd",
        "relative_gap",
        "gap_tolerance_usd",
        "configured_mip_relative_gap",
    ],
)
def test_baseline_derived_or_authority_field_drift_fails_before_publication(
    tmp_path: Path,
    baseline_field: str,
) -> None:
    context = _context(tmp_path, event_hour=3)
    request, result, request_path, _ = _request_result(
        tmp_path, context, "block_0000", worker_pid=303
    )
    baseline = result["scientific_payload"]["baseline_audit"]
    observed = baseline[baseline_field]
    drifted = (
        -1.0e-30
        if baseline_field in {"absolute_gap_usd", "relative_gap"}
        else float(observed) + 5.0e-10
    )
    baseline[baseline_field] = drifted
    result["scientific_payload_sha256"] = runner._canonical_sha256(
        result["scientific_payload"]
    )
    with pytest.raises(ValueError):
        runner._validate_worker_result(
            request,
            result,
            request_path=request_path,
            observed_pid=303,
            observed_exit_code=0,
            prior_attempt_identities=set(),
            context=context,
        )
    checkpoint = Path(context["config"]["execution"]["checkpoint_directory"])
    assert not (checkpoint / "block_0000.json").exists()


def test_forward_hourly_bounds_with_forged_signed_gap_are_rejected(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path, event_hour=3)
    block = context["blocks"]["block_0000"]
    payload = _payload("block_0000", context["config"], block)
    outcome = payload["outcomes"][3]
    certificate = outcome["primary_certificate"]
    certificate.update(
        {
            "objective_incumbent_mw": 5.0000005,
            "lower_bound_mw": 5.0,
            "upper_bound_mw": 5.0000005,
            "absolute_gap_mw": -5.0e-7,
            "relative_gap": -5.0e-7 / 5.0000005,
            "gap_tolerance_mw": 5.0000005e-6,
        }
    )
    outcome["primary"]["grid_need_mw"] = 5.0000005
    row = payload["rows"][3]
    row.update(
        {
            "grid_need_mw": 5.0000005,
            "grid_need_fraction": 5.0000005 / 250.0,
            "dispatch_objective_incumbent_mw": 5.0000005,
            "dispatch_lower_bound_mw": 5.0,
            "dispatch_upper_bound_mw": 5.0000005,
            "dispatch_absolute_gap_mw": -5.0e-7,
            "dispatch_relative_gap": -5.0e-7 / 5.0000005,
            "dispatch_gap_tolerance_mw": 5.0000005e-6,
        }
    )
    with pytest.raises(ValueError, match="absolute_gap"):
        runner._validate_scientific_payload(
            payload,
            block_id="block_0000",
            expected_block=block,
            config=context["config"],
        )


def test_forward_baseline_bounds_with_forged_signed_gap_are_rejected(
    tmp_path: Path,
) -> None:
    context = _context(tmp_path, event_hour=3)
    block = context["blocks"]["block_0000"]
    payload = _payload("block_0000", context["config"], block)
    payload["baseline_audit"].update(
        {
            "objective_usd": 100.0000005,
            "lower_bound_usd": 100.0,
            "upper_bound_usd": 100.0000005,
            "absolute_gap_usd": -5.0e-7,
            "relative_gap": -5.0e-7 / 100.0000005,
            "gap_tolerance_usd": 1.000000005e-4,
        }
    )
    with pytest.raises(ValueError, match="absolute_gap"):
        runner._validate_scientific_payload(
            payload,
            block_id="block_0000",
            expected_block=block,
            config=context["config"],
        )


@pytest.mark.parametrize("mutation", ["source_hour", "order", "block", "length"])
def test_24h_source_order_and_block_identity_are_exact(
    tmp_path: Path, mutation: str
) -> None:
    context = _context(tmp_path)
    payload = _payload(
        "block_0000", context["config"], context["blocks"]["block_0000"]
    )
    if mutation == "source_hour":
        payload["outcomes"][0]["primary"]["source_hour"] += 1
    elif mutation == "order":
        payload["rows"][0], payload["rows"][1] = (
            payload["rows"][1],
            payload["rows"][0],
        )
    elif mutation == "block":
        payload["block_id"] = "block_9999"
    else:
        payload["outcomes"].pop()
        payload["rows"].pop()
    with pytest.raises(ValueError):
        runner._validate_scientific_payload(
            payload,
            block_id="block_0000",
            expected_block=context["blocks"]["block_0000"],
            config=context["config"],
        )


def test_solver_options_and_e0_consistency_are_exact(tmp_path: Path) -> None:
    context = _context(tmp_path, event_hour=3)
    block = context["blocks"]["block_0000"]
    finite = _payload("block_0000", context["config"], block)
    finite["outcomes"][3]["solver_options"]["threads"] = 99
    with pytest.raises(ValueError, match="solver, state, or resolution"):
        runner._validate_scientific_payload(
            finite,
            block_id="block_0000",
            expected_block=block,
            config=context["config"],
        )
    e0 = _payload("block_0000", context["config"], block, e0_hour=3)
    runner._validate_scientific_payload(
        e0,
        block_id="block_0000",
        expected_block=block,
        config=context["config"],
    )
    e0["outcomes"][3]["zero_dc_confirmation"] = None
    with pytest.raises((TypeError, ValueError), match="zero-DC"):
        runner._validate_scientific_payload(
            e0,
            block_id="block_0000",
            expected_block=block,
            config=context["config"],
        )


def test_atomic_checkpoint_publication_and_no_overwrite(tmp_path: Path) -> None:
    context = _context(tmp_path)
    envelope = _envelope(tmp_path, context, "block_0000", 303)
    target = tmp_path / "published" / "block_0000.json"
    runner._publish_checkpoint_atomic(target, envelope)
    assert json.loads(target.read_text(encoding="utf-8")) == envelope
    assert not list(target.parent.glob("*.tmp"))
    with pytest.raises(FileExistsError, match="overwrite"):
        runner._publish_checkpoint_atomic(target, envelope)


def test_resume_accepts_pid_reuse_and_rejects_hole_extra_and_old_schema(
    tmp_path: Path,
) -> None:
    block_ids = ("block_0000", "block_0001", "block_0002")
    context = _context(tmp_path, block_ids)
    root = tmp_path / "checkpoints"
    root.mkdir()
    (root / "block_0000.json").write_text(
        json.dumps(_envelope(tmp_path, context, "block_0000", 303)),
        encoding="utf-8",
    )
    (root / "block_0001.json").write_text(
        json.dumps(
            _envelope(tmp_path, context, "block_0001", 303, nonce="c" * 64)
        ),
        encoding="utf-8",
    )
    payloads, identities = runner._resume_prefix(root, block_ids, context)
    assert len(payloads) == 2
    assert len(identities) == 2
    (root / "block_0001.json").unlink()
    (root / "block_0002.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="continuous prefix"):
        runner._resume_prefix(root, block_ids, context)
    (root / "block_0002.json").unlink()
    (root / "extra.txt").write_text("extra", encoding="utf-8")
    with pytest.raises(ValueError, match="extra or non-ordinary"):
        runner._resume_prefix(root, block_ids, context)
    (root / "extra.txt").unlink()
    (root / "block_0000.json").write_text(
        json.dumps({"schema": "rts_gmlc_public_grid_need_block_checkpoint_v4"}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="checkpoint identity drifted"):
        runner._resume_prefix(root, block_ids, context)


def test_exact_inventory_and_unresolved_state_block_finalization(tmp_path: Path) -> None:
    block_ids = tuple(f"block_{index:04d}" for index in range(1071))
    context = _context(tmp_path, block_ids)
    resolved = [{"all_hours_resolved": True} for _ in block_ids]
    with pytest.raises(RuntimeError, match="complete 1071-block inventory"):
        runner._finalize(context, resolved[:-1], tmp_path / "checkpoints")
    resolved[10] = {"all_hours_resolved": False}
    with pytest.raises(RuntimeError, match="unresolved block"):
        runner._finalize(context, resolved, tmp_path / "checkpoints")


def test_closed_controller_fails_before_scientific_preflight_or_solver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runner,
        "_stage_context",
        lambda *args, **kwargs: pytest.fail("closed controller loaded scientific inputs"),
    )
    monkeypatch.setattr(
        runner.v4,
        "_process_block",
        lambda *args, **kwargs: pytest.fail("parent called the solver path"),
    )
    with pytest.raises(ValueError, match="dispatch authority is closed"):
        runner.run(TEMPLATE)


def test_timeout_writes_no_completed_checkpoint_and_never_infers_infeasibility(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    context = _context(tmp_path)
    roots = runner._require_isolated_roots(context["config"])

    class FakeChild:
        pid = 303
        returncode = -9

    monkeypatch.setattr(runner.subprocess, "Popen", lambda *args, **kwargs: FakeChild())
    monkeypatch.setattr(
        runner,
        "_wait_worker",
        lambda *args, **kwargs: {
            "status": "timeout",
            "reason": "external_watchdog_reached",
            "exit_code": -9,
            "resource_sample_count": 1,
            "mathematical_infeasibility_inferred": False,
        },
    )
    with pytest.raises(RuntimeError, match="unresolved, not infeasible"):
        runner._dispatch_one(
            context,
            block_id="block_0000",
            python_executable=Path(sys.executable).resolve(),
            roots=roots,
            prior_attempt_identities=set(),
        )
    assert not (roots["checkpoint"] / "block_0000.json").exists()


def test_resource_stop_never_infers_infeasibility() -> None:
    process = yaml.safe_load(TEMPLATE.read_text(encoding="utf-8"))["execution"][
        "process_isolation"
    ]
    assert (
        runner._resource_stop_reason(
            {
                "sampling_available": True,
                "private_bytes": 9 * 1024**3,
                "system_commit_available_bytes": 10 * 1024**3,
            },
            process,
        )
        == "private_commit_limit_reached"
    )
    assert process["two_block_full_process_pilot_post_result_passed"] is False
