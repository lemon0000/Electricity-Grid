from __future__ import annotations

import copy
import json
import os
from pathlib import Path

import pytest

from experiments import run_rq2_public_grid_two_block_pilot_candidate_v2 as runner


def _highs_0008() -> dict[str, object]:
    payload = copy.deepcopy(runner._extract_gurobi_payload())
    config = runner._load_yaml(runner.BASE_CONFIG, "base config")
    spec = runner.recovery.solver_spec(config["solver"])
    options = runner.recovery.solver_options(spec)
    baseline = payload["baseline_audit"]
    baseline["solver_name"] = spec.name
    baseline["solver_options"] = options
    baseline["solver_threads"] = config["solver"]["threads"]
    baseline["termination_condition"] = "optimal"
    baseline["solver_status"] = "ok"
    for outcome, row in zip(payload["outcomes"], payload["rows"], strict=True):
        outcome["solver_name"] = spec.name
        outcome["solver_options"] = options if row["active_event_id"] else {}
        primary = outcome["primary"]
        if row["active_event_id"]:
            primary["termination_condition"] = "optimal"
            primary["solver_status"] = "ok"
        else:
            primary["termination_condition"] = "not_applicable_no_active_outage"
            primary["solver_status"] = "not_applicable"
        row["dispatch_termination_condition"] = primary["termination_condition"]
        row["dispatch_solver_status"] = primary["solver_status"]
    return payload


def _first_active(payload: dict[str, object]) -> tuple[dict[str, object], dict[str, object]]:
    index = next(
        index for index, row in enumerate(payload["rows"]) if row["active_event_id"]
    )
    return payload["outcomes"][index], payload["rows"][index]


def test_registered_raw_status_accepts_only_semantic_v1_pairs() -> None:
    assert runner._registered_raw_semantic("highs", "optimal", "ok") == "optimal"
    assert (
        runner._registered_raw_semantic(
            "highs", "not_applicable_no_active_outage", "not_applicable"
        )
        == "not_applicable_no_active_outage"
    )
    assert runner._registered_raw_semantic("gurobi", "infeasible", "warning") == "infeasible"
    for solver, termination, status in (
        ("highs", "globallyOptimal", "ok"),
        ("highs", "infeasible", "warning"),
        ("gurobi", "optimal", "warning"),
    ):
        with pytest.raises((TypeError, ValueError), match="unregistered raw"):
            runner._registered_raw_semantic(solver, termination, status)


def test_globally_optimal_is_fail_closed_at_named_outage_comparison() -> None:
    highs = _highs_0008()
    outcome, row = _first_active(highs)
    outcome["primary"]["termination_condition"] = "globallyOptimal"
    row["dispatch_termination_condition"] = "globallyOptimal"
    report = runner.compare_named_outage_0008(highs, runner._extract_gurobi_payload())
    assert report["comparison_passed"] is False
    assert "unregistered raw" in report["reason"]
    assert report["mathematical_infeasibility_inferred"] is False


def test_unregistered_baseline_raw_status_is_fail_closed() -> None:
    highs = _highs_0008()
    highs["baseline_audit"]["termination_condition"] = "globallyOptimal"
    report = runner.compare_named_outage_0008(highs, runner._extract_gurobi_payload())
    assert report["comparison_passed"] is False
    assert "unregistered raw" in report["reason"]
    assert report["mathematical_infeasibility_inferred"] is False


def test_e0_primary_and_zero_confirmation_both_use_registered_raw_mapping() -> None:
    highs = _highs_0008()
    outcome, _ = _first_active(highs)
    outcome["state"] = "E0_infeasible_at_zero_dc"
    outcome["primary"]["termination_condition"] = "infeasible"
    outcome["primary"]["solver_status"] = "error"
    outcome["zero_dc_confirmation"] = {
        "termination_condition": "infeasible",
        "solver_status": "error",
    }
    runner._normalize_payload_raw_evidence(highs, "highs")
    outcome["zero_dc_confirmation"]["solver_status"] = "warning"
    with pytest.raises(ValueError, match="unregistered raw"):
        runner._normalize_payload_raw_evidence(highs, "highs")


@pytest.mark.parametrize("field", ["event_id", "component_type", "component_uid"])
def test_named_outage_identity_mutation_fails_closed(field: str) -> None:
    highs = _highs_0008()
    outcome, row = _first_active(highs)
    outcome["primary"][field] = f"mutated-{field}"
    row_key = {
        "event_id": "active_event_id",
        "component_type": "active_component_type",
        "component_uid": "active_component_uid",
    }[field]
    row[row_key] = outcome["primary"][field]
    report = runner.compare_named_outage_0008(highs, runner._extract_gurobi_payload())
    assert report["comparison_passed"] is False
    assert report["mathematical_infeasibility_inferred"] is False


def test_named_outage_state_mutation_fails_closed() -> None:
    highs = _highs_0008()
    outcome, row = _first_active(highs)
    outcome["state"] = "E0_infeasible_at_zero_dc"
    row["state"] = "E0_infeasible_at_zero_dc"
    report = runner.compare_named_outage_0008(highs, runner._extract_gurobi_payload())
    assert report["comparison_passed"] is False
    assert report["mathematical_infeasibility_inferred"] is False


def _request_fixture(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[dict[str, object], Path, dict[str, object]]:
    config = runner._load_yaml(runner.CONFIG, "candidate")
    context = runner._stage_context()
    worker_root = tmp_path / "worker"
    attempt = worker_root / runner.BLOCKS[0] / ("b" * 64)
    attempt.mkdir(parents=True)
    receipt_path = tmp_path / "controller_receipt.json"
    controller = runner._build_controller_receipt(
        config,
        controller_pid=os.getpid(),
        controller_creation_time_100ns=123456,
        controller_receipt_path=receipt_path,
    )
    runner.recovery._atomic_json(receipt_path, controller)
    request_path = attempt / "request.json"
    result_path = attempt / "payload.json"
    request = runner._build_request(
        context,
        block_id=runner.BLOCKS[0],
        controller=controller,
        controller_receipt_path=receipt_path,
        worker_root=worker_root,
        python=Path(os.sys.executable).resolve(),
        result_path=result_path,
        nonce="b" * 64,
    )
    request_path.write_text(json.dumps(request, sort_keys=True), encoding="utf-8")
    monkeypatch.setattr(runner, "_require_execution_authority", lambda: (config, {}))
    monkeypatch.setattr(
        runner,
        "_process_identity",
        lambda pid: {"pid": pid, "creation_time_100ns": 123456},
    )
    monkeypatch.setattr(runner.os, "getppid", lambda: os.getpid())
    monkeypatch.setattr(
        runner, "_canonical_controller_receipt_path", lambda path, config: True
    )
    monkeypatch.setattr(runner, "_canonical_worker_root", lambda path, config: True)
    return request, request_path, context


@pytest.mark.parametrize(
    "mutation",
    ["forged_receipt", "traversal", "stale_pid", "extra_path", "authority_drift"],
)
def test_hidden_request_rejects_forgery_paths_pid_and_authority(
    mutation: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request, request_path, _ = _request_fixture(tmp_path, monkeypatch)
    if mutation == "forged_receipt":
        receipt = json.loads(Path(request["controller_receipt_path"]).read_text("utf-8"))
        receipt["controller_nonce"] = "c" * 64
        Path(request["controller_receipt_path"]).write_text(
            json.dumps(receipt), encoding="utf-8"
        )
    elif mutation == "traversal":
        request["worker_result_path"] = str(request_path.parent / ".." / "payload.json")
    elif mutation == "stale_pid":
        monkeypatch.setattr(
            runner,
            "_process_identity",
            lambda pid: {"pid": pid, "creation_time_100ns": 123457},
        )
    elif mutation == "extra_path":
        (request_path.parent / "extra.txt").write_text("unexpected", encoding="utf-8")
    else:
        request["authority"] = {**request["authority"], "semantic_manifest_sha256": "d" * 64}
    request_path.write_text(json.dumps(request, sort_keys=True), encoding="utf-8")
    with pytest.raises((RuntimeError, ValueError)):
        runner._validate_request(request, request_path)


def test_authorized_canonical_hidden_request_passes_provenance_validation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request, request_path, context = _request_fixture(tmp_path, monkeypatch)
    observed = runner._validate_request(request, request_path)
    assert observed["stage_base_sha256"] == context["stage_base_sha256"]


def test_controller_receipt_path_must_be_registered_staging_shape() -> None:
    config = runner._load_yaml(runner.CONFIG, "candidate")
    target = runner._pilot_roots(config)["result"]
    valid = (
        target.parent
        / f".{target.name}.staging.0123456789abcdef"
        / "controller_receipt.json"
    )
    invalid = target.parent / "forged" / "controller_receipt.json"
    assert runner._canonical_controller_receipt_path(valid, config) is True
    assert runner._canonical_controller_receipt_path(invalid, config) is False


def test_worker_root_must_equal_registered_canonical_root(tmp_path: Path) -> None:
    config = runner._load_yaml(runner.CONFIG, "candidate")
    registered = runner._pilot_roots(config)["worker"]
    assert runner._canonical_worker_root(registered, config) is True
    assert runner._canonical_worker_root(tmp_path.resolve(), config) is False


def test_hidden_request_rejects_symlinked_worker_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request, request_path, _ = _request_fixture(tmp_path, monkeypatch)
    real = Path(request["worker_root"])
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(real, target_is_directory=True)
    except OSError:
        original = runner._is_link_or_reparse
        monkeypatch.setattr(
            runner,
            "_is_link_or_reparse",
            lambda path: path == real or original(path),
        )
    else:
        request["worker_root"] = str(alias)
    request_path.write_text(json.dumps(request, sort_keys=True), encoding="utf-8")
    with pytest.raises(ValueError):
        runner._validate_request(request, request_path)


def _valid_copied_worker_pair(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> tuple[dict[str, object], dict[str, object], Path, Path, dict[str, object]]:
    request, _, context = _request_fixture(tmp_path, monkeypatch)
    payload = _highs_0008()
    payload_path = tmp_path / "payload.json"
    receipt_path = tmp_path / "receipt.json"
    worker_identity = {"pid": os.getpid() + 1, "creation_time_100ns": 987654}
    result = {
        "schema": runner.RESULT_SCHEMA,
        "status": "complete",
        "authority": request["authority"],
        "request_sha256": runner.recovery._canonical_sha256(request),
        "block_id": request["block_id"],
        "block_input_sha256": request["block_input_sha256"],
        "parent_process_identity": request["parent_process_identity"],
        "worker_process_identity": worker_identity,
        "controller_receipt_sha256": request["controller_receipt_sha256"],
        "nonce": request["nonce"],
        "scientific_config_path": request["scientific_config_path"],
        "scientific_config_sha256": request["scientific_config_sha256"],
        "solver": request["solver"],
        "scientific_payload": payload,
        "scientific_payload_sha256": runner.recovery._canonical_sha256(payload),
        "all_hours_resolved": True,
        "mathematical_infeasibility_inferred_from_failure": False,
    }
    runner.recovery._atomic_json(payload_path, result)
    receipt = {
        "schema": runner.RECEIPT_SCHEMA,
        "authority": request["authority"],
        "request_sha256": result["request_sha256"],
        "worker_payload_sha256": runner.recovery._sha256(payload_path),
        "block_id": result["block_id"],
        "parent_process_identity": result["parent_process_identity"],
        "worker_process_identity": worker_identity,
        "controller_receipt_sha256": result["controller_receipt_sha256"],
        "all_hours_resolved": True,
        "controller_validation_passed": True,
        "published_by_controller": True,
        "mathematical_infeasibility_inferred_from_failure": False,
    }
    runner.recovery._atomic_json(receipt_path, receipt)
    return request, context, payload_path, receipt_path, result


def test_post_copy_tamper_fails_full_validation_before_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request, context, payload_path, receipt_path, result = _valid_copied_worker_pair(
        tmp_path, monkeypatch
    )
    assert runner._validate_copied_worker_pair(
        payload_path,
        receipt_path,
        expected_authority=request["authority"],
        request=request,
        context=context,
    )["all_hours_resolved"] is True
    result["scientific_payload_sha256"] = "0" * 64
    payload_path.write_text(json.dumps(result, sort_keys=True), encoding="utf-8")
    receipt = json.loads(receipt_path.read_text("utf-8"))
    receipt["worker_payload_sha256"] = runner.recovery._sha256(payload_path)
    receipt_path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
    target = tmp_path / "published"
    with pytest.raises(ValueError, match="canonical hash drifted"):
        runner._validate_copied_worker_pair(
            payload_path,
            receipt_path,
            expected_authority=request["authority"],
            request=request,
            context=context,
        )
    assert not target.exists()


def test_receipt_payload_hash_mismatch_fails_before_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request, context, payload_path, receipt_path, _ = _valid_copied_worker_pair(
        tmp_path, monkeypatch
    )
    receipt = json.loads(receipt_path.read_text("utf-8"))
    receipt["worker_payload_sha256"] = "0" * 64
    receipt_path.write_text(json.dumps(receipt, sort_keys=True), encoding="utf-8")
    with pytest.raises(ValueError, match="payload/receipt hash mismatch"):
        runner._validate_copied_worker_pair(
            payload_path,
            receipt_path,
            expected_authority=request["authority"],
            request=request,
            context=context,
        )


def test_validate_only_is_zero_solver_zero_result_and_formal_write(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runner.subprocess,
        "Popen",
        lambda *args, **kwargs: pytest.fail("worker or solver dispatch"),
    )
    report = runner.run(validate_only=True)
    assert report["validation_passed"] is True
    assert report["execution_ready"] is False
    assert report["solver_calls"] == 0
    assert report["result_files_written"] == 0
    assert report["formal_writes"] == 0


def test_controller_and_hidden_worker_fail_closed_before_preflight(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        runner,
        "_stage_context",
        lambda: pytest.fail("scientific preflight reached"),
    )
    monkeypatch.setattr(
        runner.subprocess,
        "Popen",
        lambda *args, **kwargs: pytest.fail("worker/solver dispatch reached"),
    )
    with pytest.raises(RuntimeError, match="authority is closed"):
        runner.run(validate_only=False)
    with pytest.raises(RuntimeError, match="authority is closed"):
        runner._validate_request({}, tmp_path / "request.json")


@pytest.mark.parametrize("invalid", [False, 1.0, "1"])
def test_parent_dispatch_started_ns_is_strongly_typed(
    invalid: object, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    request, request_path, _ = _request_fixture(tmp_path, monkeypatch)
    request["parent_dispatch_started_ns"] = invalid
    request_path.write_text(json.dumps(request, sort_keys=True), encoding="utf-8")
    with pytest.raises(ValueError, match="dispatch start time"):
        runner._validate_request(request, request_path)
