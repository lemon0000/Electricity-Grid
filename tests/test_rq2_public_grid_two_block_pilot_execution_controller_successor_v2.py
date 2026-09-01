from __future__ import annotations

import copy
import ctypes
import importlib
import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_grid_two_block_pilot_execution_controller_successor_v2.json"


@pytest.fixture(scope="module")
def closure():
    return importlib.import_module(
        "experiments.rq2_public_grid_execution_dependency_closure_v2"
    )


@pytest.fixture(scope="module")
def controller():
    return importlib.import_module(
        "experiments.run_rq2_public_grid_two_block_pilot_execution_controller_successor_v2"
    )


@pytest.fixture(scope="module")
def worker():
    return importlib.import_module(
        "experiments.worker_rq2_public_grid_two_block_pilot_execution_controller_successor_v2"
    )


@pytest.fixture(scope="module")
def bootstrap():
    return importlib.import_module(
        "experiments.bootstrap_rq2_public_grid_two_block_pilot_execution_controller_successor_v2"
    )


def _config() -> dict:
    return json.loads(CONFIG.read_bytes())


def _payload(*, event: bool, zero_confirmations: int = 0) -> dict:
    outcomes = []
    for index in range(24):
        zero = index < zero_confirmations
        active = event and index == 0
        outcomes.append(
            {
                "primary": {
                    "resolved": not zero,
                    "proven_infeasible": zero,
                    "termination_condition": (
                        "infeasible"
                        if zero
                        else "optimal"
                        if active
                        else "not_applicable_no_active_outage"
                    ),
                },
                "primary_certificate": {"termination_condition": "optimal"},
                "zero_dc_confirmation": (
                    {
                        "resolved": False,
                        "proven_infeasible": True,
                        "termination_condition": "infeasible",
                    }
                    if zero
                    else None
                ),
                "zero_dc_confirmation_certificate": (
                    {"termination_condition": "infeasible"} if zero else None
                ),
            }
        )
    return {
        "baseline_audit": {
            "accepted": True,
            "termination_condition": (
                "optimal" if event else "not_applicable_no_active_outage"
            ),
        },
        "outcomes": outcomes,
        "all_hours_resolved": True,
    }


def test_rework_receipt_binds_rejected_v1_outer() -> None:
    receipt = json.loads(
        (
            ROOT
            / "configs/rq2_public_grid_two_block_pilot_execution_controller_review_rework_v1.json"
        ).read_bytes()
    )
    assert receipt["verdict"] == "REWORK"
    assert receipt["reviewed_outer"]["sha256"] == (
        "c21ced8b52f5aeaa3e6720991d871ccb6ae6ff513f506adf41a5bb436e2154bd"
    )
    assert len(receipt["findings"]) == 5
    assert receipt["effect"]["no_execution_authority"] is True


def test_complete_live_dependency_closure_and_named_runner_trace(closure) -> None:
    config = _config()
    trace: list[tuple[str, str]] = []
    observed = closure.verify_dependency_closure(
        ROOT, config, trace=lambda path, digest: trace.append((path, digest))
    )
    traced = {path for path, _digest in trace}
    assert set(config["dependency_closure"]["named_runner_paths"]) <= traced
    assert len(observed) == len(traced)
    assert "experiments/run_rts_gmlc_public_grid_need_dispatch_v4_process_isolated_v1.py" in traced
    assert "experiments/run_rq2_public_grid_two_block_pilot_candidate_v7.py" in traced


def _all_dependency_paths(config: dict) -> list[str]:
    values: list[str] = []
    closure = config["dependency_closure"]
    for bundle in closure["bundles"]:
        values.extend([bundle["outer_path"], bundle["inner_path"]])
        values.extend(bundle["members"])
    for manifest in closure["flat_manifests"]:
        values.append(manifest["path"])
        values.extend(manifest["members"])
    values.extend(closure["transitive_files"])
    return list(dict.fromkeys(values))


@pytest.mark.parametrize("relative", _all_dependency_paths(_config()))
def test_each_frozen_dependency_drift_fails_closed(
    closure, controller, monkeypatch: pytest.MonkeyPatch, relative: str
) -> None:
    original = closure.read_stable_bytes
    effects = {"pipe": 0}

    def drift(path: Path) -> bytes:
        raw = original(path)
        return raw + b"DRIFT" if path == ROOT / relative else raw

    monkeypatch.setattr(closure, "read_stable_bytes", drift)
    monkeypatch.setattr(
        controller.os,
        "pipe",
        lambda: effects.__setitem__("pipe", effects["pipe"] + 1),
    )
    with pytest.raises(closure.ClosureRejected, match="hash drifted"):
        controller.review_preloader_closure_gate()
    assert effects["pipe"] == 0


def _valid_review_receipt(closure, config: dict, outer_hash: str = "a" * 64) -> dict:
    return {
        "schema": config["fixed_execution_review"]["schema"],
        "version": 2,
        "reviewed_on": "2026-08-31",
        "reviewer_role": "independent_sol_reviewer",
        "verdict": "PASS",
        "reviewed_outer": {
            "path": "configs/rq2_public_grid_two_block_pilot_execution_controller_successor_v2.OUTER.SHA256SUMS.json",
            "sha256": outer_hash,
        },
        "bound_predecessor": config["predecessor"],
        "bound_dependency_closure": closure.closure_binding(config),
        "findings": [],
        "effect": config["fixed_execution_review"]["exact_effect"],
    }


@pytest.mark.parametrize(
    "mutation",
    ["missing_effect", "extra", "wrong_nonformal", "wrong_formal", "wrong_claim", "wrong_security"],
)
def test_review_receipt_exact_keyset_and_effect_fail_closed(closure, mutation: str) -> None:
    config = _config()
    receipt = _valid_review_receipt(closure, config)
    if mutation == "missing_effect":
        receipt.pop("effect")
    elif mutation == "extra":
        receipt["extra"] = False
    else:
        keys = {
            "wrong_nonformal": "two_block_nonformal_pilot_execution_authorized",
            "wrong_formal": "formal_execution_authorized",
            "wrong_claim": "claim",
            "wrong_security": "security_certified",
        }
        receipt["effect"] = dict(receipt["effect"])
        receipt["effect"][keys[mutation]] = not receipt["effect"][keys[mutation]]
    with pytest.raises(closure.ClosureRejected):
        closure.validate_review_receipt_object(
            receipt,
            config=config,
            outer_relative=receipt.get("reviewed_outer", {}).get("path", ""),
            outer_sha256="a" * 64,
        )


@pytest.mark.parametrize("entry", ["bootstrap", "controller", "worker"])
def test_exact_review_receipt_contract_is_used_at_all_three_entries(
    closure, bootstrap, controller, worker, entry: str
) -> None:
    receipt = _valid_review_receipt(closure, _config())
    target = {"bootstrap": bootstrap, "controller": controller, "worker": worker}[entry]
    kwargs = {"outer_sha256": "a" * 64}
    if entry == "bootstrap":
        kwargs["closure_module"] = closure
    target.validate_review_receipt_for_entry(receipt, **kwargs)
    receipt["effect"] = dict(receipt["effect"])
    receipt["effect"]["formal_execution_authorized"] = True
    with pytest.raises(closure.ClosureRejected):
        target.validate_review_receipt_for_entry(receipt, **kwargs)


@pytest.mark.parametrize(
    ("event", "zero", "baseline", "primary", "confirmation", "total"),
    [
        (False, 0, 0, 0, 0, 0),
        (True, 0, 1, 1, 0, 2),
        (True, 1, 1, 1, 1, 3),
        (True, 3, 1, 3, 3, 7),
    ],
)
def test_solver_accounting_is_derived_from_validated_payload(
    controller, event, zero, baseline, primary, confirmation, total
) -> None:
    observed = controller.solver_call_accounting(_payload(event=event, zero_confirmations=zero))
    assert observed == {
        "baseline_solver_calls": baseline,
        "primary_solver_calls": primary,
        "zero_dc_confirmation_solver_calls": confirmation,
        "solver_calls": total,
    }


@pytest.mark.parametrize("mutation", ["missing_primary", "half_zero_pair", "extra_outcome"])
def test_solver_accounting_rejects_malformed_or_mismatched_payload(
    controller, mutation: str
) -> None:
    payload = _payload(event=True, zero_confirmations=1)
    if mutation == "missing_primary":
        payload["outcomes"][2]["primary_certificate"] = None
    elif mutation == "half_zero_pair":
        payload["outcomes"][0]["zero_dc_confirmation_certificate"] = None
    else:
        payload["outcomes"].append(copy.deepcopy(payload["outcomes"][0]))
    with pytest.raises(controller.SuccessorV2Rejected):
        controller.solver_call_accounting(payload)


def test_worker_accounting_cross_check_rejects_mismatch(worker) -> None:
    accounting = {
        "baseline_solver_calls": 1,
        "primary_solver_calls": 1,
        "zero_dc_confirmation_solver_calls": 1,
        "solver_calls": 3,
    }
    worker.validate_solver_accounting(_payload(event=True, zero_confirmations=1), accounting)
    wrong = dict(accounting)
    wrong["solver_calls"] = 2
    with pytest.raises(worker.SuccessorV2WorkerRejected):
        worker.validate_solver_accounting(_payload(event=True, zero_confirmations=1), wrong)


def test_registered_live_science_publication_seam(controller) -> None:
    publications: list[tuple[dict, ...]] = []
    validated: list[str] = []

    def validate(payload: dict, block_id: str) -> dict:
        validated.append(block_id)
        return payload

    seam = controller.register_zero_solver_live_orchestration_seam(
        payloads=lambda: (
            _payload(event=False),
            _payload(event=True, zero_confirmations=1),
        ),
        validate_payload=validate,
        publish=lambda records: publications.append(tuple(records))
        or {"publisher": "sealed_v7", "writes": 0},
    )
    report = controller.audit_zero_solver_live_orchestration(seam)
    assert report["closure_verified"] is True
    assert report["solver_calls_executed"] == 0
    assert report["accounted_solver_calls"] == [0, 3]
    assert report["publication_calls"] == 1
    assert len(publications) == 1
    assert validated == list(controller.BLOCKS)


def test_registered_scientific_validation_failure_cannot_publish(controller) -> None:
    effects = {"publish": 0}
    seam = controller.register_zero_solver_live_orchestration_seam(
        payloads=lambda: (_payload(event=False), _payload(event=True)),
        validate_payload=lambda _payload, _block_id: (_ for _ in ()).throw(
            ValueError("scientific validation rejected")
        ),
        publish=lambda _records: effects.__setitem__("publish", 1),
    )
    with pytest.raises(ValueError, match="scientific validation rejected"):
        controller.audit_zero_solver_live_orchestration(seam)
    assert effects["publish"] == 0


def test_closure_failure_precedes_controller_pipe_and_worker_loader(
    controller, worker, monkeypatch: pytest.MonkeyPatch
) -> None:
    effects = {"pipe": 0, "loader": 0}

    def rejected(*_args, **_kwargs):
        raise RuntimeError("closure drift")

    monkeypatch.setattr(controller, "verify_live_closure", rejected)
    monkeypatch.setattr(controller.os, "pipe", lambda: effects.__setitem__("pipe", 1))
    with pytest.raises(RuntimeError, match="closure drift"):
        controller.review_preloader_closure_gate()
    monkeypatch.setattr(worker, "verify_live_closure", rejected)
    with pytest.raises(RuntimeError, match="closure drift"):
        worker.production_preloader_closure_gate(lambda: effects.__setitem__("loader", 1))
    assert effects == {"pipe": 0, "loader": 0}


def test_review_preloader_direct_module_cli_is_json_safe_and_reaps_child() -> None:
    config = _config()
    completed = subprocess.run(
        [
            config["runtime"]["locked_python_executable"],
            "-B",
            "-m",
            config["successor_identity"]["controller_module"],
            "--review-preloader",
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        timeout=30.0,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    report = json.loads(completed.stdout)
    assert report == {
        "accepted": False,
        "child_pid": report["child_pid"],
        "counters": {
            "formal_writes": 0,
            "loader_calls": 0,
            "result_writes": 0,
            "solver_calls": 0,
        },
        "mathematical_infeasibility_inferred": False,
        "status": "NON_ACCEPTED_PRELOADER_BOUNDARY",
    }
    if os.name == "nt":
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.restype = ctypes.c_void_p
        handle = kernel.OpenProcess(0x00100000, False, report["child_pid"])
        if handle:
            try:
                assert kernel.WaitForSingleObject(handle, 0) == 0
            finally:
                kernel.CloseHandle(handle)


def test_review_preloader_cli_error_path_remains_fail_closed(
    controller, monkeypatch: pytest.MonkeyPatch
) -> None:
    def rejected(*_args, **_kwargs):
        raise controller.SuccessorV2Rejected("review boundary rejected")

    monkeypatch.setattr(
        controller.ControllerSession, "run_review_preloader_boundary", rejected
    )
    with pytest.raises(controller.SuccessorV2Rejected, match="review boundary rejected"):
        controller.main(["--review-preloader"])


def test_v2_roots_and_fixed_review_receipt_absent() -> None:
    config = _config()
    assert not (ROOT / config["fixed_execution_review"]["path"]).exists()
    for relative in config["paths"].values():
        assert not os.path.lexists(ROOT / relative)
