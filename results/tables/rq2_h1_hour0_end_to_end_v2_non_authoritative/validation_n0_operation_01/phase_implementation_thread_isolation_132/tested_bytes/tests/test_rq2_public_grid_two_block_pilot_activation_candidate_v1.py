"""Focused tests for the closed two-block pilot activation candidate."""

from __future__ import annotations

import ast
import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pytest

from experiments import (
    bootstrap_rq2_public_grid_two_block_pilot_activation_candidate_v1 as activation,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / activation.CONFIG_REL).read_text(encoding="utf-8"))


def _runtime() -> dict[str, object]:
    contract = CONFIG["bootstrap_contract"]
    return {
        "executable": contract["locked_python_executable"],
        "executable_sha256": contract["locked_python_sha256"],
        "version": contract["locked_python_version"],
        "orig_argv": [contract["locked_python_executable"], *contract["validate_only_argv_suffix"]],
        "cwd": contract["exact_cwd"],
        "hostname": contract["host"]["hostname"],
        "system": contract["host"]["system"],
        "release": contract["host"]["release"],
        "machine": contract["host"]["machine"],
        "environment": contract["exact_environment"],
        "process_age_seconds": 1.0,
        "processes": [(os.getpid(), "python.exe")],
        "available_virtual_bytes": 10 * 1024**3,
    }


def _root_map() -> dict[str, bool]:
    paths = [*CONFIG["fresh_roots"], *CONFIG["formal_invariants"]["protected_roots_clean_absent"]]
    return dict.fromkeys(paths, False)


def _attempt(
    index: int,
    *,
    classification: str = "accepted",
    pid: int | None = None,
    predecessor: str | None = None,
) -> dict[str, object]:
    character = "a" if index == 1 else "b"
    return {
        "execution_index": index,
        "block_id": CONFIG["nonformal_pilot_contract"]["execution_order"][index - 1],
        "child_pid": pid if pid is not None else 1000 + index,
        "child_create_time_ns": 100_000 + index,
        "nonce": f"nonce-{index}",
        "request_sha256": character * 64,
        "ack_sha256": character * 64,
        "attempt_receipt_sha256": character * 64,
        "payload_sha256": character * 64,
        "accepted_evidence_sha256": character * 64,
        "predecessor_accepted_evidence_sha256": predecessor,
        "proven_infeasible": False,
        "classification": classification,
    }


def _review_payload(outer_sha256: str) -> dict[str, Any]:
    return {
        "schema": "rq2_public_grid_two_block_pilot_activation_review_pass_v1",
        "version": 1,
        "reviewer_role": "independent_sol_reviewer",
        "verdict": "PASS",
        "findings": {"blocker": [], "major": [], "minor": []},
        "reviewed_activation": {"outer_path": activation.OUTER_REL, "outer_sha256": outer_sha256},
        "reviewed_chain": activation._activation_review_chain(CONFIG),
        "user_authorization_scope": CONFIG["predecessor_authority"]["user_authorization_scope"],
        "effect": {
            "activation_candidate_independent_review_passed": True,
            "activation_execution_authorized": True,
            "two_block_pilot_execution_authorized": True,
            "formal_activation_authorized": False,
            "formal_execution_ready": False,
            "user_formal_run_authorized": False,
            "formal_result_exists": False,
            "claim": False,
            "security_certified": False,
            "no_formal_execution_authority": True,
        },
    }


def test_activation_candidate_is_standard_library_only_and_closed() -> None:
    assert activation.PROJECT_IMPORTS_PERMITTED is False
    tree = ast.parse((ROOT / activation.SELF_REL).read_text(encoding="utf-8"))
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module.split(".")[0])
    assert not imported.intersection({"src", "experiments", "pyomo", "pandas"})
    assert CONFIG["status"] == "nonformal_two_block_pilot_activation_candidate_closed"
    assert CONFIG["gates"]["activation_review_present"] is False
    assert CONFIG["gates"]["activation_execution_ready"] is False
    assert CONFIG["gates"]["formal_execution_ready"] is False


def test_static_authority_and_formal_snapshot_are_live() -> None:
    config = activation._verify_static_authority()
    assert config["gates"]["successor_v2_independent_review_passed"] is True
    assert config["gates"]["activation_candidate_independent_review_passed"] is False


def test_project_preimport_fails_before_static_authority(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    def forbidden() -> dict[str, Any]:
        nonlocal called
        called = True
        return CONFIG

    monkeypatch.setattr(activation, "_verify_static_authority", forbidden)
    with pytest.raises(activation.BootstrapRejected, match="preimport"):
        activation.validate(preimport_modules=["src.attack"])
    assert called is False


def test_validate_only_is_zero_import_worker_solver_and_write(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(activation, "_verify_static_authority", lambda: CONFIG)
    monkeypatch.setattr(activation, "_verify_locked_python", lambda _contract: None)
    report = activation.validate(preimport_modules=[], runtime=_runtime(), root_appearances=_root_map())
    assert report["validation_passed"] is True
    assert report["status"] == "READY_FOR_INDEPENDENT_REVIEW"
    assert report["activation_review_present"] is False
    assert report["execution_ready"] is False
    for key in (
        "project_modules_imported", "worker_processes_started", "scientific_loader_calls",
        "solver_calls", "result_files_written", "formal_writes",
    ):
        assert report[key] == 0


def test_future_plan_is_exact_nonformal_two_block_sealed_path() -> None:
    plan = activation._future_execution_plan(CONFIG)
    assert plan["blocks"] == ("holdout_s20260822_0008", "holdout_s20260822_0009")
    assert plan["fresh_worker_per_block"] is True
    assert plan["dispatch_callable"] == "v7.v4._dispatch_one"
    assert plan["worker_callable"] == "v7.v4._worker_from_capability"
    assert plan["publication_callable"] == "v7._publish_result"
    assert plan["recovery_callable"] == "v7.load_verified_success_commit"
    assert plan["formal_entrypoints_reachable"] is False
    assert plan["gurobi_entrypoints_reachable"] is False
    assert plan["recovery_activation_entrypoints_reachable"] is False
    with pytest.raises(TypeError):
        plan["blocks"] = ()  # type: ignore[index]


def test_ledger_accepts_only_0008_then_0009_with_fresh_pid() -> None:
    first = _attempt(1)
    ledger = activation._append_attempt((), first, CONFIG)
    second = _attempt(2, predecessor=str(first["accepted_evidence_sha256"]))
    ledger = activation._append_attempt(ledger, second, CONFIG)
    assert [row["block_id"] for row in ledger] == [
        "holdout_s20260822_0008", "holdout_s20260822_0009"
    ]
    assert ledger[0]["child_pid"] != ledger[1]["child_pid"]
    with pytest.raises(TypeError):
        ledger[0]["child_pid"] = 7  # type: ignore[index]


@pytest.mark.parametrize(
    "mutation,match",
    [
        ({"execution_index": 2, "block_id": "holdout_s20260822_0009"}, "order"),
        ({"block_id": "holdout_s20260822_0009"}, "order"),
        ({"proven_infeasible": True}, "value"),
    ],
)
def test_0009_first_skip_or_infeasibility_claim_rejected(mutation: dict[str, object], match: str) -> None:
    row = _attempt(1)
    row.update(mutation)
    with pytest.raises(activation.BootstrapRejected, match=match):
        activation._append_attempt((), row, CONFIG)


def test_second_block_requires_accepted_predecessor_and_fresh_pid() -> None:
    incomplete = _attempt(1, classification="honest_incomplete")
    ledger = activation._append_attempt((), incomplete, CONFIG)
    second = _attempt(2, predecessor=str(incomplete["accepted_evidence_sha256"]))
    with pytest.raises(activation.BootstrapRejected, match="accepted first"):
        activation._append_attempt(ledger, second, CONFIG)
    first = _attempt(1)
    ledger = activation._append_attempt((), first, CONFIG)
    with pytest.raises(activation.BootstrapRejected, match="predecessor"):
        activation._append_attempt(ledger, _attempt(2, predecessor="c" * 64), CONFIG)
    with pytest.raises(activation.BootstrapRejected, match="fresh worker"):
        activation._append_attempt(
            ledger,
            _attempt(2, pid=int(first["child_pid"]), predecessor=str(first["accepted_evidence_sha256"])),
            CONFIG,
        )


def test_retry_and_extra_attempt_are_rejected() -> None:
    first = _attempt(1)
    ledger = activation._append_attempt((), first, CONFIG)
    with pytest.raises(activation.BootstrapRejected, match="order"):
        activation._append_attempt(ledger, _attempt(1), CONFIG)
    second = _attempt(2, predecessor=str(first["accepted_evidence_sha256"]))
    ledger = activation._append_attempt(ledger, second, CONFIG)
    with pytest.raises(activation.BootstrapRejected, match="extra attempt"):
        activation._append_attempt(ledger, second, CONFIG)


@pytest.mark.parametrize(
    "reason,expected",
    [
        ("timeout", "honest_incomplete"), ("resource_stop", "honest_incomplete"),
        ("nonzero_exit", "honest_incomplete"), ("missing_incumbent", "honest_incomplete"),
        ("unresolved", "honest_incomplete"),
        ("invalid_or_raced_publication", "commit_indeterminate"),
    ],
)
def test_failure_semantics_never_infer_infeasible(reason: str, expected: str) -> None:
    assert activation._classify_failure(reason, CONFIG) == expected
    assert expected != "infeasible"


def test_only_exact_owned_child_may_be_terminated() -> None:
    expected = {
        "child_pid": 123, "child_create_time_ns": 456, "nonce": "n", "request_sha256": "a" * 64,
    }
    assert activation._owned_child_matches(expected, dict(expected), CONFIG) is True
    for field in tuple(expected):
        observed = dict(expected)
        observed[field] = "wrong" if field not in {"child_pid", "child_create_time_ns"} else 999
        assert activation._owned_child_matches(expected, observed, CONFIG) is False


def test_valid_future_review_contract_and_wrong_chain_rejected() -> None:
    outer = "d" * 64
    payload = _review_payload(outer)
    activation._validate_external_activation_review(payload, expected_outer_sha256=outer, config=CONFIG)
    wrong = json.loads(json.dumps(payload))
    wrong["reviewed_chain"][activation.USER_AUTH_REL] = "e" * 64
    with pytest.raises(activation.BootstrapRejected, match="receipt mismatch"):
        activation._validate_external_activation_review(wrong, expected_outer_sha256=outer, config=CONFIG)


@pytest.mark.parametrize("field", ["verdict", "reviewer_role", "effect", "findings"])
def test_fake_future_review_receipt_rejected(field: str) -> None:
    outer = "d" * 64
    payload = _review_payload(outer)
    payload[field] = "forged"
    with pytest.raises(activation.BootstrapRejected, match="receipt mismatch"):
        activation._validate_external_activation_review(payload, expected_outer_sha256=outer, config=CONFIG)


def test_external_review_double_read_rejects_post_check_drift(tmp_path: Path) -> None:
    outer = "d" * 64
    receipt = tmp_path / "review.json"
    raw = json.dumps(_review_payload(outer), sort_keys=True).encode()
    receipt.write_bytes(raw)

    def mutate() -> None:
        receipt.write_bytes(raw + b" ")

    with pytest.raises(activation.BootstrapRejected, match="changed"):
        activation._load_external_activation_review_twice(
            receipt, expected_receipt_sha256=hashlib.sha256(raw).hexdigest(),
            expected_outer_sha256=outer, config=CONFIG, post_first_read=mutate,
        )


def test_external_review_path_alias_seam_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    outer = "d" * 64
    receipt = tmp_path / "alias.json"
    raw = json.dumps(_review_payload(outer), sort_keys=True).encode()
    receipt.write_bytes(raw)
    real = activation._strict_existing

    def reject_alias(path: Path, *, regular_file: bool) -> None:
        if path == receipt:
            raise activation.BootstrapRejected("authority path alias/reparse rejected")
        real(path, regular_file=regular_file)

    monkeypatch.setattr(activation, "_strict_existing", reject_alias)
    with pytest.raises(activation.BootstrapRejected, match="alias/reparse"):
        activation._load_external_activation_review_twice(
            receipt, expected_receipt_sha256=hashlib.sha256(raw).hexdigest(),
            expected_outer_sha256=outer, config=CONFIG,
        )


@pytest.mark.parametrize(
    "argv",
    [["--execute"], ["--execute", "--activation-review-receipt", "missing.json"],
     ["--execute", "--activation-review-receipt", "fake.json"]],
)
def test_execute_missing_or_fake_receipt_fails_before_project_import(
    argv: list[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(activation, "_PREIMPORT_PROJECT_MODULES", ())
    monkeypatch.setattr(activation, "_verify_static_authority", lambda: CONFIG)
    read_called = False

    def forbidden(*_args: object, **_kwargs: object) -> dict[str, Any]:
        nonlocal read_called
        read_called = True
        raise AssertionError("receipt must not be read without wrapper binding")

    monkeypatch.setattr(activation, "_load_external_activation_review_twice", forbidden)
    with pytest.raises(activation.BootstrapRejected, match="immutable execution wrapper"):
        activation.main(argv)
    assert read_called is False


def test_no_flag_and_validate_receipt_are_rejected() -> None:
    with pytest.raises(SystemExit):
        activation.main([])
    with pytest.raises(activation.BootstrapRejected, match="validate-only rejects"):
        activation.main(["--validate-only", "--activation-review-receipt", "forged.json"])
