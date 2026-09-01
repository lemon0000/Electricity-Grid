"""Focused tests for activation/transport successor v3."""

from __future__ import annotations

import ast
import base64
import dataclasses
import hashlib
import hmac
import inspect
import json
import os
import subprocess
from pathlib import Path
from typing import Any

import pytest

from experiments import (
    bootstrap_rq2_public_grid_two_block_pilot_activation_transport_v3 as bootstrap,
)
from experiments import (
    run_rq2_public_grid_two_block_pilot_activation_transport_v3 as controller,
)
from experiments import (
    worker_rq2_public_grid_two_block_pilot_activation_transport_v3 as worker,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG = json.loads((ROOT / bootstrap.CONFIG_REL).read_text(encoding="utf-8"))


def _runtime() -> dict[str, object]:
    contract = CONFIG["bootstrap_contract"]
    return {
        "executable": contract["locked_python_executable"],
        "executable_sha256": contract["locked_python_sha256"],
        "version": contract["locked_python_version"],
        "orig_argv": [
            contract["locked_python_executable"],
            *contract["validate_only_argv_suffix"],
        ],
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
    paths = [
        *CONFIG["fresh_roots"],
        *CONFIG["formal_invariants"]["protected_roots_clean_absent"],
    ]
    return dict.fromkeys(paths, False)


def _sealed_record(
    session: controller.ControllerSession,
    index: int,
    *,
    predecessor: str | None,
    identity_seed: str | None = None,
) -> controller.AcceptedRecord:
    seed = identity_seed or str(index)
    provisional = controller.AcceptedRecord(
        schema=controller.RECORD_SCHEMA,
        block_id=controller.BLOCKS[index - 1],
        execution_index=index,
        nonce=("a" if seed == "1" else "b") * 64,
        child_pid=20_000 + int(seed[-1]),
        child_create_time_ns=30_000 + int(seed[-1]),
        envelope_sha256=("1" if seed == "1" else "2") * 64,
        ack_sha256=("3" if seed == "1" else "4") * 64,
        source_sha256=("5" if seed == "1" else "6") * 64,
        scientific_payload_sha256=("7" if seed == "1" else "8") * 64,
        certificate_inventory_sha256=("9" if seed == "1" else "a") * 64,
        predecessor_accepted_digest=predecessor,
        controller_session_id=session._session_id,
        controller_mac="",
        accepted_record_digest="",
    )
    digest = controller._record_digest(provisional)
    mac = hmac.new(
        session._secret,
        f"{session._session_id}:{digest}".encode("ascii"),
        hashlib.sha256,
    ).hexdigest()
    return dataclasses.replace(
        provisional, controller_mac=mac, accepted_record_digest=digest
    )


def test_v3_modules_are_standard_library_only_and_no_caller_accept_api() -> None:
    assert bootstrap.PROJECT_IMPORTS_PERMITTED is False
    assert controller.PRODUCTION_DISPATCH_PERMITTED is False
    assert worker.PRODUCTION_DISPATCH_PERMITTED is False
    for relative in (
        bootstrap.CONTROLLER_REL,
        bootstrap.WORKER_REL,
        bootstrap.SELF_REL,
    ):
        tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
        imported: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name.split(".")[0] for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported.add(node.module.split(".")[0])
        assert not imported.intersection({"src", "pyomo", "pandas"})
    public = {
        name
        for name, value in inspect.getmembers(
            controller.ControllerSession, predicate=callable
        )
        if not name.startswith("_")
    }
    assert public == {"run_review_preloader_boundary", "run_two_block_pilot"}
    for name in public:
        parameters = inspect.signature(
            getattr(controller.ControllerSession, name)
        ).parameters
        assert not {
            "process",
            "popen",
            "capability",
            "ack",
            "source",
            "evidence",
        }.intersection(parameters)
    source = (ROOT / bootstrap.CONTROLLER_REL).read_text(encoding="utf-8")
    assert "accept_verified_transport" not in source
    assert "begin_transport_attempt" not in source
    assert "_dispatch_one(" not in source
    assert "_worker_from_capability(" not in source


def test_static_authority_and_v2_escalate_receipt_are_live() -> None:
    config, _helper = bootstrap._verify_static_authority()
    assert config["gates"]["activation_v2_escalate_recorded"] is True
    assert config["gates"]["activation_v3_independent_review_passed"] is False


def test_preimport_fails_before_static_authority(monkeypatch: pytest.MonkeyPatch) -> None:
    called = False

    def forbidden() -> tuple[dict[str, Any], Any]:
        nonlocal called
        called = True
        raise AssertionError

    monkeypatch.setattr(bootstrap, "_verify_static_authority", forbidden)
    with pytest.raises(bootstrap.BootstrapRejected, match="preimport"):
        bootstrap.validate(preimport_modules=["src.attack"])
    assert called is False


def test_validate_only_is_closed_and_zero_execution(monkeypatch: pytest.MonkeyPatch) -> None:
    helper = type(
        "Helper",
        (),
        {
            "_verify_runtime": staticmethod(lambda _config, _runtime: None),
            "_verify_roots": staticmethod(lambda _config, _roots: None),
        },
    )
    monkeypatch.setattr(bootstrap, "_verify_static_authority", lambda: (CONFIG, helper))
    report = bootstrap.validate(
        preimport_modules=[], runtime=_runtime(), root_appearances=_root_map()
    )
    assert report["validation_passed"] is True
    assert report["execution_ready"] is False
    for key in (
        "production_workers_started",
        "scientific_loader_calls",
        "solver_calls",
        "result_files_written",
        "formal_writes",
    ):
        assert report[key] == 0


def test_future_review_only_authorizes_wrapper_creation() -> None:
    outer = "e" * 64
    payload = {
        "schema": "rq2_public_grid_activation_transport_review_pass_v3",
        "reviewer_role": "independent_sol_reviewer",
        "verdict": "PASS",
        "reviewed_outer": {"path": bootstrap.OUTER_REL, "sha256": outer},
        "findings": {"blocker": [], "major": [], "minor": []},
        "effect": CONFIG["future_activation_review"]["expected_effect"],
    }
    bootstrap._verify_review_effect(payload, outer)
    overbroad = json.loads(json.dumps(payload))
    overbroad["effect"]["activation_execution_authorized"] = True
    with pytest.raises(bootstrap.BootstrapRejected, match="overauthorizes"):
        bootstrap._verify_review_effect(overbroad, outer)


def test_future_receipt_chain_is_noncircular_and_worker_revalidates_bindings(
    tmp_path: Path,
) -> None:
    outer_hash = hashlib.sha256((ROOT / bootstrap.OUTER_REL).read_bytes()).hexdigest()
    wrapper_path = tmp_path / "execution_wrapper.py"
    wrapper_path.write_bytes(b"# independently reviewed immutable wrapper\n")
    wrapper_hash = hashlib.sha256(wrapper_path.read_bytes()).hexdigest()
    review = {
        "schema": "rq2_public_grid_activation_transport_review_pass_v3",
        "reviewer_role": "independent_sol_reviewer",
        "verdict": "PASS",
        "reviewed_outer": {"path": bootstrap.OUTER_REL, "sha256": outer_hash},
        "findings": {"blocker": [], "major": [], "minor": []},
        "effect": CONFIG["future_activation_review"]["expected_effect"],
    }
    review_path = tmp_path / "activation_review.json"
    review_path.write_bytes(controller._canonical_bytes(review))
    review_hash = hashlib.sha256(review_path.read_bytes()).hexdigest()
    wrapper = {
        "schema": "rq2_public_grid_activation_execution_wrapper_review_pass_v1",
        "verdict": "PASS",
        "reviewed_activation_outer_sha256": outer_hash,
        "activation_review_receipt_sha256": review_hash,
        "execution_wrapper": {"path": str(wrapper_path), "sha256": wrapper_hash},
    }
    wrapper_receipt_path = tmp_path / "wrapper_review.json"
    wrapper_receipt_path.write_bytes(controller._canonical_bytes(wrapper))
    wrapper_receipt_hash = hashlib.sha256(
        wrapper_receipt_path.read_bytes()
    ).hexdigest()
    dispatch = {
        "schema": "rq2_public_grid_two_block_pilot_dispatch_authorization_v1",
        "reviewed_activation_outer_sha256": outer_hash,
        "activation_review_receipt_sha256": review_hash,
        "wrapper_review_receipt_sha256": wrapper_receipt_hash,
        "execution_wrapper_sha256": wrapper_hash,
        "user_authorization_sha256": CONFIG["predecessor_authority"][
            "user_authorization_sha256"
        ],
        "human_dispatch_review_passed": True,
        "two_block_pilot_execution_authorized": True,
        "formal_execution_authorized": False,
    }
    dispatch_path = tmp_path / "dispatch.json"
    dispatch_path.write_bytes(controller._canonical_bytes(dispatch))
    authority = controller._load_future_authority(
        activation_review_receipt=review_path,
        wrapper_review_receipt=wrapper_receipt_path,
        dispatch_authorization_receipt=dispatch_path,
        config=CONFIG,
    )
    worker._verify_future_authority(authority, CONFIG)
    forged = json.loads(json.dumps(authority))
    forged["dispatch_authorization_receipt"][
        "wrapper_review_receipt_sha256"
    ] = "0" * 64
    with pytest.raises(worker.WorkerRejected, match="dispatch authority"):
        worker._verify_future_authority(forged, CONFIG)


def test_real_production_worker_stops_preloader_and_cannot_unlock_0009() -> None:
    session = controller.ControllerSession()
    outcome = session.run_review_preloader_boundary(timeout_seconds=10.0)
    assert outcome.status == "NON_ACCEPTED_PRELOADER_BOUNDARY"
    assert outcome.accepted is False
    assert outcome.block_id == controller.BLOCKS[0]
    assert outcome.counters == {
        "scientific_loader_calls": 0,
        "solver_calls": 0,
        "result_writes": 0,
        "formal_writes": 0,
    }
    assert outcome.mathematical_infeasibility_inferred is False
    assert session.records == ()
    assert session.attempted_indices == frozenset({1})
    with pytest.raises(controller.TransportRejected, match="retry forbidden"):
        session.run_review_preloader_boundary(timeout_seconds=10.0)
    with pytest.raises(controller.TransportRejected, match="order or predecessor"):
        session._dispatch_owned(
            execution_index=2,
            mode="review_only_preloader_stop",
            future_authority=None,
            timeout_seconds=1.0,
        )
    with pytest.raises(controller.TransportRejected):
        controller._process_creation_time_ns(outcome.child_pid)


def test_exact_child_command_cwd_environment_and_fresh_pid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = controller.subprocess.Popen
    observed: list[int] = []

    def checked(command: list[str], **kwargs: Any) -> subprocess.Popen[Any]:
        assert command[:5] == CONFIG["transport_contract"]["worker_command_prefix"]
        assert kwargs["cwd"] == str(ROOT)
        assert kwargs["env"] == CONFIG["bootstrap_contract"]["exact_environment"]
        process = original(command, **kwargs)
        observed.append(process.pid)
        return process

    monkeypatch.setattr(controller.subprocess, "Popen", checked)
    outcome = controller.ControllerSession().run_review_preloader_boundary(
        timeout_seconds=10.0
    )
    assert observed == [outcome.child_pid]
    assert outcome.child_pid != os.getpid()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("worker_command", ["python", "-c", "import time;time.sleep(1)"]),
        ("working_directory", "D:\\forged"),
        ("sanitized_environment", {"FORGED": "1"}),
        ("controller_sha256", "0" * 64),
        ("worker_sha256", "0" * 64),
        ("config_sha256", "0" * 64),
        ("parent_pid", 1),
    ],
)
def test_forged_command_env_cwd_module_config_or_parent_rejected(
    monkeypatch: pytest.MonkeyPatch, field: str, value: object
) -> None:
    original = controller._build_envelope

    def forged(**kwargs: Any) -> dict[str, Any]:
        payload = original(**kwargs)
        payload[field] = value
        return payload

    monkeypatch.setattr(controller, "_build_envelope", forged)
    session = controller.ControllerSession()
    with pytest.raises(controller.TransportRejected):
        session.run_review_preloader_boundary(timeout_seconds=5.0)
    assert session.records == ()
    assert session.attempted_indices == frozenset({1})


@pytest.mark.parametrize("mutation", ["ack", "source"])
def test_forged_ack_or_source_rejected_before_append(
    monkeypatch: pytest.MonkeyPatch, mutation: str
) -> None:
    original = controller._validate_ack

    def forged(raw: bytes, **kwargs: Any) -> Any:
        ack = json.loads(raw)
        if mutation == "ack":
            ack["status"] = "ACCEPTED_COMPLETE"
        else:
            source = json.loads(base64.b64decode(ack["source_base64"]))
            source["accepted"] = True
            source_bytes = controller._canonical_bytes(source)
            ack["source_base64"] = base64.b64encode(source_bytes).decode("ascii")
            ack["source_sha256"] = hashlib.sha256(source_bytes).hexdigest()
        return original(controller._canonical_bytes(ack), **kwargs)

    monkeypatch.setattr(controller, "_validate_ack", forged)
    session = controller.ControllerSession()
    with pytest.raises(controller.TransportRejected):
        session.run_review_preloader_boundary(timeout_seconds=5.0)
    assert session.records == ()


def test_single_active_and_failed_attempt_are_permanently_consumed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active = controller.ControllerSession()
    active._active_index = 1
    with pytest.raises(controller.TransportRejected, match="single-active"):
        active.run_review_preloader_boundary(timeout_seconds=1.0)
    active._active_index = None

    failed = controller.ControllerSession()

    def fail(_self: controller.ControllerSession, **_kwargs: Any) -> controller.AttemptOutcome:
        raise controller.TransportRejected("synthetic pre-spawn failure")

    monkeypatch.setattr(controller.ControllerSession, "_spawn_read_validate_append", fail)
    with pytest.raises(controller.TransportRejected, match="synthetic"):
        failed.run_review_preloader_boundary(timeout_seconds=1.0)
    assert failed.attempted_indices == frozenset({1})
    with pytest.raises(controller.TransportRejected, match="retry forbidden"):
        failed.run_review_preloader_boundary(timeout_seconds=1.0)


@pytest.mark.parametrize(
    "case",
    ["mutation", "truncate", "reorder", "replay", "block-swap", "cross-session"],
)
def test_history_mutation_truncation_replay_reorder_swap_cross_session_rejected(
    case: str,
) -> None:
    session = controller.ControllerSession()
    first = _sealed_record(session, 1, predecessor=None)
    second = _sealed_record(session, 2, predecessor=first.accepted_record_digest)
    if case == "mutation":
        records = (dataclasses.replace(first, source_sha256="0" * 64),)
    elif case == "truncate":
        records = (second,)
    elif case == "reorder":
        records = (second, first)
    elif case == "replay":
        replay = _sealed_record(
            session,
            2,
            predecessor=first.accepted_record_digest,
            identity_seed="1",
        )
        records = (first, replay)
    elif case == "block-swap":
        records = (dataclasses.replace(first, block_id=controller.BLOCKS[1]),)
    else:
        other = controller.ControllerSession()
        other._records = (first,)
        with pytest.raises(controller.TransportRejected):
            _ = other.records
        return
    session._records = records
    with pytest.raises(controller.TransportRejected):
        _ = session.records


def test_exact_valid_history_is_immutable_tuple() -> None:
    session = controller.ControllerSession()
    first = _sealed_record(session, 1, predecessor=None)
    second = _sealed_record(session, 2, predecessor=first.accepted_record_digest)
    session._records = (first, second)
    assert session.records == (first, second)
    with pytest.raises(dataclasses.FrozenInstanceError):
        first.block_id = "forged"  # type: ignore[misc]
    with pytest.raises(AttributeError):
        session.records.append(first)  # type: ignore[attr-defined]


def test_future_interface_rejects_missing_receipts_before_spawn(tmp_path: Path) -> None:
    session = controller.ControllerSession()
    missing = tmp_path / "missing.json"
    with pytest.raises(controller.TransportRejected, match="path unreadable"):
        session.run_two_block_pilot(
            activation_review_receipt=missing,
            wrapper_review_receipt=missing,
            dispatch_authorization_receipt=missing,
        )
    assert session.attempted_indices == frozenset()
    assert session.records == ()


def test_worker_public_invocation_and_bootstrap_execute_remain_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with pytest.raises(worker.WorkerRejected, match="public worker"):
        worker.main([])
    monkeypatch.setattr(bootstrap, "_PREIMPORT_PROJECT_MODULES", ())
    monkeypatch.setattr(bootstrap, "_verify_static_authority", lambda: (CONFIG, object()))
    with pytest.raises(bootstrap.BootstrapRejected, match="authority is absent"):
        bootstrap.main(["--execute"])


def test_scientific_bridge_uses_only_registered_primitives_and_honest_counters() -> None:
    source = (ROOT / bootstrap.WORKER_REL).read_text(encoding="utf-8")
    assert "recovery.v4._process_block(" in source
    assert "recovery._validate_scientific_payload(" in source
    assert "_dispatch_one(" not in source
    assert "_worker_from_capability(" not in source
    assert CONFIG["sealed_scientific_primitive_authority"][
        "scientific_transport_publication_thresholds_changed"
    ] is False
    semantics = CONFIG["resource_contract"]["failure_semantics"]
    assert semantics["any_failure_is_mathematical_infeasibility_evidence"] is False
    assert CONFIG["threat_model"][
        "claims_resistance_to_same_privilege_parent_memory_tampering"
    ] is False
