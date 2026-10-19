from __future__ import annotations

import ast
import importlib
import json
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def controller():
    return importlib.import_module(
        "experiments.run_rq2_public_grid_two_block_pilot_activation_transport_v4"
    )


@pytest.fixture(scope="module")
def worker():
    return importlib.import_module(
        "experiments.worker_rq2_public_grid_two_block_pilot_activation_transport_v4"
    )


def test_v4_modules_exist_and_production_is_closed() -> None:
    controller = importlib.import_module(
        "experiments.run_rq2_public_grid_two_block_pilot_activation_transport_v4"
    )
    worker = importlib.import_module(
        "experiments.worker_rq2_public_grid_two_block_pilot_activation_transport_v4"
    )
    assert controller.PRODUCTION_CLOSED is True
    assert worker.PRODUCTION_CLOSED is True


def test_v3_rework_receipt_binds_exact_outer_and_has_no_authority() -> None:
    receipt = json.loads(
        (
            ROOT
            / "configs/rq2_public_grid_two_block_pilot_activation_transport_review_rework_v3.json"
        ).read_bytes()
    )
    assert receipt["verdict"] == "REWORK"
    assert receipt["reviewed_outer"]["sha256"] == (
        "b7b5d85000091c052d257ee5ce4a6e280a6de52b6a813eaaad82d3473c92daee"
    )
    effect = receipt["review_effect"]
    assert effect["v3_execution_authorized"] is False
    assert effect["v4_closed_candidate_creation_authorized"] is True
    assert effect["production_worker_authorized"] is False
    assert effect["formal_authorized"] is False


@pytest.mark.parametrize("method", ["run_two_block_pilot", "run_production_block"])
def test_all_controller_production_methods_reject_before_any_effect(
    controller, monkeypatch: pytest.MonkeyPatch, method: str
) -> None:
    effects = {"config": 0, "pipe": 0, "popen": 0, "science_import": 0}

    def forbidden_config():
        effects["config"] += 1
        raise AssertionError

    def forbidden_pipe():
        effects["pipe"] += 1
        raise AssertionError

    class ForbiddenPopen:
        def __init__(self, *_args, **_kwargs):
            effects["popen"] += 1
            raise AssertionError

    monkeypatch.setattr(controller, "_load_config", forbidden_config)
    monkeypatch.setattr(controller.os, "pipe", forbidden_pipe)
    monkeypatch.setattr(controller.subprocess, "Popen", ForbiddenPopen)
    session = controller.ControllerSession()
    with pytest.raises(controller.ProductionClosed):
        getattr(session, method)(
            activation_review_receipt=Path("self-consistent-review.json"),
            wrapper_review_receipt=Path("self-consistent-wrapper.json"),
            dispatch_authorization_receipt=Path("self-consistent-dispatch.json"),
            parent_command="forged-parent-command",
        )
    assert effects == {"config": 0, "pipe": 0, "popen": 0, "science_import": 0}
    assert session.attempted_indices == frozenset()


def test_worker_production_flag_rejects_before_handle_or_science_import(
    worker, monkeypatch: pytest.MonkeyPatch
) -> None:
    effects = {"review": 0}

    def forbidden(*_args, **_kwargs):
        effects["review"] += 1
        raise AssertionError

    monkeypatch.setattr(worker, "_review_only_preloader_worker", forbidden)
    with pytest.raises(worker.WorkerV4Rejected, match="permanently closed"):
        worker.main(
            [
                "--internal-production-worker",
                "--read-handle",
                "123",
                "--ack-handle",
                "456",
            ]
        )
    assert effects == {"review": 0}


def test_production_methods_have_literal_fail_closed_first_statement(controller) -> None:
    tree = ast.parse(Path(controller.__file__).read_text(encoding="utf-8"))
    methods = {}
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in {
            "run_two_block_pilot",
            "run_production_block",
        }:
            methods[node.name] = node
    assert set(methods) == {"run_two_block_pilot", "run_production_block"}
    for node in methods.values():
        statements = list(node.body)
        if (
            statements
            and isinstance(statements[0], ast.Expr)
            and isinstance(statements[0].value, ast.Constant)
            and isinstance(statements[0].value.value, str)
        ):
            statements = statements[1:]
        assert isinstance(statements[0], ast.Raise)


def test_preflight_requires_child_cap_plus_host_reserve(controller) -> None:
    required = 10 * controller.GIB
    assert (
        controller.preflight_available_commit(observe=lambda: required)
        == required
    )
    with pytest.raises(controller.TransportV4Rejected, match="below"):
        controller.preflight_available_commit(observe=lambda: required - 1)
    with pytest.raises(controller.TransportV4Rejected, match="observation"):
        controller.preflight_available_commit(
            observe=lambda: (_ for _ in ()).throw(OSError("denied"))
        )
    with pytest.raises(controller.TransportV4Rejected, match="malformed"):
        controller.preflight_available_commit(observe=lambda: -1)


class _FakeProcess:
    def __init__(self, pid: int = 44001) -> None:
        self.pid = pid
        self.alive = True
        self.terminate_calls = 0
        self.kill_calls = 0

    def poll(self):
        return None if self.alive else 0

    def terminate(self) -> None:
        self.terminate_calls += 1
        self.alive = False

    def kill(self) -> None:
        self.kill_calls += 1
        self.alive = False

    def wait(self, timeout: float):
        assert timeout == 1.0
        self.alive = False
        return 0


@pytest.mark.parametrize(
    ("sample", "expected_status"),
    [
        (lambda _pid, _created: 8 * 1024**3 + 1, "resource_stop"),
        (
            lambda _pid, _created: (_ for _ in ()).throw(OSError("sample denied")),
            "sampling_error",
        ),
        (lambda _pid, _created: -1, "sampling_error"),
    ],
)
def test_resource_monitor_fails_closed_and_never_infers_infeasible(
    controller,
    monkeypatch: pytest.MonkeyPatch,
    sample,
    expected_status: str,
) -> None:
    process = _FakeProcess()
    created = 123456
    monkeypatch.setattr(controller, "_process_creation_time_ns", lambda _pid: created)
    outcome = controller.monitor_owned_child_resources(
        process,
        expected_pid=process.pid,
        expected_create_time_ns=created,
        sample=sample,
        sleep=lambda _seconds: None,
    )
    assert outcome.status == expected_status
    assert outcome.honest_incomplete is True
    assert outcome.mathematical_infeasibility_inferred is False
    assert process.terminate_calls == 1
    assert process.alive is False


def test_resource_monitor_uses_five_second_default(controller) -> None:
    signature = controller.inspect.signature(controller.monitor_owned_child_resources)
    assert signature.parameters["sample_interval_seconds"].default == 5.0


def test_resource_timeout_is_honest_and_terminates_only_owned_identity(
    controller, monkeypatch: pytest.MonkeyPatch
) -> None:
    process = _FakeProcess()
    created = 777
    monkeypatch.setattr(controller, "_process_creation_time_ns", lambda _pid: created)
    outcome = controller.monitor_owned_child_resources(
        process,
        expected_pid=process.pid,
        expected_create_time_ns=created,
        sample=lambda _pid, _created: 1,
        clock=lambda: 10.0,
        sleep=lambda _seconds: None,
        deadline=9.0,
    )
    assert outcome.status == "timeout"
    assert outcome.mathematical_infeasibility_inferred is False
    foreign = _FakeProcess(pid=99001)
    with pytest.raises(controller.TransportV4Rejected, match="non-owned"):
        controller.terminate_exact_owned_child(
            foreign, expected_pid=99002, expected_create_time_ns=created
        )
    assert foreign.terminate_calls == 0


def test_atomic_lock_allows_exactly_one_thread_to_spawn(
    controller, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        controller,
        "_load_config",
        lambda: {
            "resource_contract": {
                "child_private_commit_limit_gib": 8,
                "minimum_host_commit_reserve_gib": 2,
            }
        },
    )
    monkeypatch.setattr(controller, "preflight_available_commit", lambda **_kwargs: 10)
    start = threading.Barrier(3)
    entered = threading.Event()
    release = threading.Event()
    spawn_calls: list[int] = []

    def review(_timeout: float):
        spawn_calls.append(1)
        entered.set()
        assert release.wait(5)
        return controller.ReviewOutcome(
            "NON_ACCEPTED_PRELOADER_BOUNDARY",
            False,
            1,
            controller.BLOCK,
            False,
            {},
        )

    monkeypatch.setattr(controller, "_run_review_transport", review)
    session = controller.ControllerSession()
    outcomes: list[object] = []

    def invoke() -> None:
        start.wait()
        try:
            outcomes.append(session.run_review_preloader_boundary(timeout_seconds=1))
        except controller.TransportV4Rejected as exc:
            outcomes.append(exc)

    threads = [threading.Thread(target=invoke) for _ in range(2)]
    for thread in threads:
        thread.start()
    start.wait()
    assert entered.wait(5)
    release.set()
    for thread in threads:
        thread.join(5)
        assert not thread.is_alive()
    assert len(spawn_calls) == 1
    assert len(outcomes) == 2
    assert sum(isinstance(value, controller.ReviewOutcome) for value in outcomes) == 1
    assert sum(isinstance(value, controller.TransportV4Rejected) for value in outcomes) == 1
    assert session.attempted_indices == frozenset({1})


def test_failed_review_attempt_is_consumed_before_spawn(
    controller, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        controller,
        "_load_config",
        lambda: {
            "resource_contract": {
                "child_private_commit_limit_gib": 8,
                "minimum_host_commit_reserve_gib": 2,
            }
        },
    )
    monkeypatch.setattr(controller, "preflight_available_commit", lambda **_kwargs: 10)
    calls = 0

    def failed(_timeout: float):
        nonlocal calls
        calls += 1
        raise OSError("synthetic spawn failure")

    monkeypatch.setattr(controller, "_run_review_transport", failed)
    session = controller.ControllerSession()
    with pytest.raises(controller.TransportV4Rejected, match="honestly"):
        session.run_review_preloader_boundary(timeout_seconds=1)
    with pytest.raises(controller.TransportV4Rejected, match="consumed"):
        session.run_review_preloader_boundary(timeout_seconds=1)
    assert calls == 1
    assert session.attempted_indices == frozenset({1})


def test_real_review_only_preloader_boundary_remains_non_accepting(controller) -> None:
    session = controller.ControllerSession()
    outcome = session.run_review_preloader_boundary(timeout_seconds=10.0)
    assert outcome.status == "NON_ACCEPTED_PRELOADER_BOUNDARY"
    assert outcome.accepted is False
    assert outcome.execution_index == 1
    assert outcome.block_id == controller.BLOCK
    assert dict(outcome.counters) == {
        "scientific_loader_calls": 0,
        "solver_calls": 0,
        "result_writes": 0,
        "formal_writes": 0,
    }
    assert outcome.mathematical_infeasibility_inferred is False
    assert session.attempted_indices == frozenset({1})


def _valid_scientific_values():
    block = [{"source_hour": "1"}]
    certificate = {"lower_bound_mw": 0.0, "upper_bound_mw": 0.0}
    payload = {
        "all_hours_resolved": True,
        "baseline_audit": {"resolved": True},
        "outcomes": [
            {
                "resolved_for_pipeline": True,
                "primary_certificate": certificate,
                "zero_dc_confirmation_certificate": None,
            }
        ],
    }
    context = {
        "blocks": {controller_block(): block},
        "config": {
            "model": {"dc_bus": 1, "dc_reference_demand_mw": 1.0},
            "solver": {"name": "zero_solver_seam"},
        },
    }
    inventory = {
        "baseline_audit": payload["baseline_audit"],
        "hourly": [
            {
                "primary_certificate": certificate,
                "zero_dc_confirmation_certificate": None,
            }
        ],
    }
    return context, payload, inventory


def controller_block() -> str:
    return "holdout_s20260822_0008"


def _registered_seam(controller, *, mutation: str | None = None):
    context, payload, inventory = _valid_scientific_values()
    calls = {"stage": 0, "load": 0, "process": 0, "validate": 0, "solver": 0}

    def stage():
        calls["stage"] += 1
        return context

    def load(value):
        calls["load"] += 1
        assert value is context
        if mutation == "loader_exception":
            raise OSError("loader seam failure")
        return object()

    def process(_data, _block, **kwargs):
        calls["process"] += 1
        assert kwargs["solver"]["name"] == "zero_solver_seam"
        return payload

    def validate(value, **_kwargs):
        calls["validate"] += 1
        assert value is payload
        if mutation == "unresolved":
            return {**payload, "all_hours_resolved": False}
        return payload

    if mutation == "certificate_mismatch":
        inventory = {**inventory, "baseline_audit": {"resolved": False}}
    seam = controller.register_zero_solver_seam(
        stage_context=stage,
        load_worker_data=load,
        process_block=process,
        validate_payload=validate,
        certificate_inventory=inventory,
    )
    return seam, calls


def test_scientific_dependency_closure_and_signatures_are_live(controller) -> None:
    signatures = controller.verify_scientific_dependency_closure()
    assert set(signatures) == {"stage", "load", "process", "validate"}


def test_registered_zero_solver_seam_exercises_complete_bridge(controller) -> None:
    seam, calls = _registered_seam(controller)
    audit = controller.audit_registered_zero_solver_seam(seam)
    assert audit.status == "ZERO_SOLVER_SEAM_VALIDATED"
    assert audit.accepted is False
    assert dict(audit.counters) == {
        "stage_calls": 1,
        "loader_calls": 1,
        "process_calls": 1,
        "validator_calls": 1,
        "solver_calls": 0,
        "writes": 0,
    }
    assert calls == {"stage": 1, "load": 1, "process": 1, "validate": 1, "solver": 0}
    assert audit.mathematical_infeasibility_inferred is False


@pytest.mark.parametrize(
    ("mutation", "pattern"),
    [
        ("unresolved", "unresolved"),
        ("certificate_mismatch", "certificate inventory mismatch"),
        ("loader_exception", "honest incomplete"),
    ],
)
def test_scientific_bridge_failures_are_honest_and_non_accepting(
    controller, mutation: str, pattern: str
) -> None:
    seam, calls = _registered_seam(controller, mutation=mutation)
    with pytest.raises(controller.ScientificBridgeRejected, match=pattern):
        controller.audit_registered_zero_solver_seam(seam)
    assert calls["solver"] == 0


def test_unregistered_or_replayed_seam_is_rejected(controller) -> None:
    seam, _calls = _registered_seam(controller)
    controller.audit_registered_zero_solver_seam(seam)
    with pytest.raises(controller.ScientificBridgeRejected, match="not registered"):
        controller.audit_registered_zero_solver_seam(seam)


def test_future_contract_requires_new_successor_and_grants_nothing(controller) -> None:
    contract = dict(controller.future_wrapper_contract())
    assert contract["current_candidate_can_be_opened_in_place"] is False
    assert contract["new_versioned_controller_successor_required"] is True
    assert contract["new_versioned_worker_successor_required"] is True
    assert contract["must_bind_exact_v4_outer"] is True
    assert contract["must_bind_independent_v4_pass_receipt"] is True
    assert contract["caller_supplied_paths_or_self_consistent_json_are_not_trust_roots"] is True
    assert contract["wrapper_generated_in_this_candidate"] is False
    assert contract["execution_authorized_by_this_contract"] is False


def test_runner_validate_only_and_all_other_cli_modes_closed(controller, capsys) -> None:
    assert controller.main(["--validate-only"]) == 0
    value = json.loads(capsys.readouterr().out)
    assert value["validation_passed"] is True
    assert value["production_closed"] is True
    assert value["execution_ready"] is False
    assert value["production_workers"] == 0
    assert value["loader_calls"] == 0
    assert value["solver_calls"] == 0
    assert value["result_writes"] == 0
    assert value["formal_writes"] == 0
    with pytest.raises(controller.ProductionClosed):
        controller.main([])


def test_bootstrap_execute_rejects_before_project_import() -> None:
    bootstrap = importlib.import_module(
        "experiments.bootstrap_rq2_public_grid_two_block_pilot_activation_transport_v4"
    )
    with pytest.raises(bootstrap.BootstrapRejected, match="permanently closed"):
        bootstrap.main(["--execute"])


def test_bootstrap_validate_only_is_sealed_and_zero_effect() -> None:
    bootstrap = importlib.import_module(
        "experiments.bootstrap_rq2_public_grid_two_block_pilot_activation_transport_v4"
    )
    value = bootstrap.validate_only()
    assert value["validation_passed"] is True
    assert value["bundle_members"] == 6
    assert value["activation_v4_independent_review_passed"] is False
    assert value["execution_ready"] is False
    assert value["project_imports"] == 0
    assert value["production_workers"] == 0
    assert value["scientific_loader_calls"] == 0
    assert value["solver_calls"] == 0
    assert value["result_writes"] == 0
    assert value["formal_writes"] == 0
