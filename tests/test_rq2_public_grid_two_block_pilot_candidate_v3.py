from __future__ import annotations

import copy
import json
import os
from pathlib import Path

import pytest

from experiments import run_rq2_public_grid_two_block_pilot_candidate_v3 as runner


def _highs_payload(block_id: str) -> dict[str, object]:
    payload = copy.deepcopy(runner._extract_gurobi_payload())
    context = runner._stage_context()
    expected = context["blocks"][block_id]
    config = context["config"]
    spec = runner.recovery.solver_spec(config["solver"])
    options = runner.recovery.solver_options(spec)
    baseline = payload["baseline_audit"]
    baseline["solver_name"] = spec.name
    baseline["solver_options"] = options
    baseline["solver_threads"] = config["solver"]["threads"]
    baseline["termination_condition"] = "optimal"
    baseline["solver_status"] = "ok"
    no_event = next(
        (copy.deepcopy(outcome), copy.deepcopy(row))
        for outcome, row in zip(payload["outcomes"], payload["rows"], strict=True)
        if not row["active_event_id"]
    )
    active = next(
        (copy.deepcopy(outcome), copy.deepcopy(row))
        for outcome, row in zip(payload["outcomes"], payload["rows"], strict=True)
        if row["active_event_id"]
    )
    rows: list[dict[str, object]] = []
    outcomes: list[dict[str, object]] = []
    for input_row in expected:
        outcome, row = copy.deepcopy(active if input_row["active_event_id"] else no_event)
        for key in runner.recovery.v4._BLOCK_FIELDS:
            row[key] = input_row[key]
        primary = outcome["primary"]
        primary["source_hour"] = int(input_row["source_hour"])
        primary["event_id"] = input_row["active_event_id"] or None
        primary["component_type"] = input_row["active_component_type"] or None
        primary["component_uid"] = input_row["active_component_uid"] or None
        outcome["solver_name"] = spec.name
        if input_row["active_event_id"]:
            outcome["solver_options"] = options
            primary["termination_condition"] = "optimal"
            primary["solver_status"] = "ok"
        else:
            outcome["solver_options"] = {}
            primary["termination_condition"] = "not_applicable_no_active_outage"
            primary["solver_status"] = "not_applicable"
        row["dispatch_termination_condition"] = primary["termination_condition"]
        row["dispatch_solver_status"] = primary["solver_status"]
        outcomes.append(outcome)
        rows.append(row)
    payload.update(
        {
            "block_id": block_id,
            "split": expected[0]["split"],
            "outcomes": outcomes,
            "rows": rows,
            "exogenous_grid_infeasibility_hour_count": 0,
            "all_hours_resolved": True,
        }
    )
    return payload


def _identity(pid: int, command: list[str]) -> dict[str, object]:
    return {
        "pid": pid,
        "creation_time": 123456789 + pid,
        "executable_path": str(Path(os.sys.executable).resolve()),
        "executable_sha256": runner.recovery._sha256(Path(os.sys.executable).resolve()),
        "command": command,
    }


def _pair(
    root: Path, block_id: str
) -> tuple[dict[str, object], Path, Path]:
    root.mkdir(parents=True, exist_ok=False)
    config = runner._load_yaml(runner.CONFIG, "candidate v3")
    python = Path(os.sys.executable).resolve()
    parent = _identity(71001, runner._expected_controller_command(python))
    worker = _identity(
        71002,
        runner._expected_worker_command(python, read_handle=41, ack_handle=42),
    )
    result_path = root / "payload.json"
    envelope = runner._build_capability_envelope(
        config,
        block_id=block_id,
        parent_identity=parent,
        worker_identity=worker,
        result_path=result_path,
        read_handle=41,
        ack_handle=42,
        environment=runner._sanitized_environment({}),
        nonce="a" * 64,
    )
    payload = _highs_payload(block_id)
    result = runner._build_worker_result(envelope, payload)
    runner.recovery._atomic_json(result_path, result)
    receipt_path = root / "receipt.json"
    runner.recovery._atomic_json(
        receipt_path, runner._build_worker_receipt(envelope, result_path)
    )
    assert runner._validate_worker_pair(
        result_path, receipt_path, envelope=envelope
    )["all_hours_resolved"] is True
    return envelope, result_path, receipt_path


def _publication_fixture(
    tmp_path: Path,
) -> tuple[
    dict[str, object],
    dict[str, tuple[dict[str, object], Path, Path]],
    Path,
    Path,
]:
    config = runner._load_yaml(runner.CONFIG, "candidate v3")
    python = Path(os.sys.executable).resolve()
    parent = _identity(71001, runner._expected_controller_command(python))
    controller = runner._build_controller_receipt(config, parent)
    sources = {
        block_id: _pair(tmp_path / "sources" / block_id, block_id)
        for block_id in runner.BLOCKS
    }
    return controller, sources, tmp_path / "staging", tmp_path / "published"


def test_candidate_stays_closed_and_authorization_is_conditional() -> None:
    config, authorization = runner._load_authority()
    assert config["status"] == "remediation_candidate_v3_execution_closed"
    assert authorization["user_authority"]["exact_quote"] == (
        "授权给你，修复好之后就开始正式实验吧"
    )
    assert authorization["effect"]["current_formal_run_authorized"] is False
    assert authorization["effect"]["conditional_authorization_effective"] is False
    for key in (
        "independent_pre_run_review_passed",
        "execution_successor_present",
        "two_block_pilot_execution_ready",
        "two_block_pilot_executed",
        "post_result_review_passed",
        "formal_execution_ready",
        "user_formal_run_authorized",
        "formal_result_exists",
        "claim",
        "security_certified",
    ):
        assert config["gates"][key] is False


def test_legacy_request_file_cli_is_absent_before_any_resolution(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    alias = tmp_path / "request-link.json"
    monkeypatch.setattr(
        runner,
        "_resolve_after_alias_check",
        lambda *_args, **_kwargs: pytest.fail("path resolution reached"),
    )
    with pytest.raises(SystemExit):
        runner.main(["--worker-request", str(alias)])


def test_closed_internal_worker_fails_before_pipe_data_or_solver(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runner,
        "_read_frame",
        lambda *_args, **_kwargs: pytest.fail("capability pipe consumed"),
    )
    monkeypatch.setattr(
        runner.recovery.v4,
        "_process_block",
        lambda *_args, **_kwargs: pytest.fail("solver reached"),
    )
    with pytest.raises(RuntimeError, match="execution authority is closed"):
        runner._worker_from_capability(-1, -1)


def test_alias_rejected_segment_by_segment_before_resolve(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = tmp_path / "real"
    root.mkdir()
    target = root / "payload.json"
    target.write_text("{}", encoding="utf-8")
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(root, target_is_directory=True)
        candidate = alias / "payload.json"
    except OSError:
        candidate = root / "payload.json"
        original = runner._is_link_or_reparse
        monkeypatch.setattr(
            runner,
            "_is_link_or_reparse",
            lambda path: path == root or original(path),
        )
    monkeypatch.setattr(
        runner,
        "_resolve_after_alias_check",
        lambda *_args, **_kwargs: pytest.fail("resolve occurred before alias rejection"),
    )
    with pytest.raises(ValueError, match="alias|reparse"):
        runner._strict_path(candidate, must_exist=True, label="worker result")


def test_full_worker_entry_rejects_envelope_alias_before_data_and_solver(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    config = runner._load_yaml(runner.CONFIG, "candidate v3")
    parent_command = runner._expected_controller_command(Path(os.sys.executable).resolve())
    worker_command = runner._expected_worker_command(
        Path(os.sys.executable).resolve(), read_handle=91, ack_handle=92
    )
    parent = _identity(os.getpid() + 1000, parent_command)
    worker = _identity(os.getpid(), worker_command)
    real = tmp_path / "real"
    real.mkdir()
    alias = tmp_path / "alias"
    try:
        alias.symlink_to(real, target_is_directory=True)
        result_path = alias / "payload.json"
    except OSError:
        result_path = real / "payload.json"
        original = runner._is_link_or_reparse
        monkeypatch.setattr(
            runner,
            "_is_link_or_reparse",
            lambda path: path == real or original(path),
        )
    envelope = runner._build_capability_envelope(
        config,
        block_id=runner.BLOCKS[0],
        parent_identity=parent,
        worker_identity=worker,
        result_path=result_path,
        read_handle=91,
        ack_handle=92,
        environment=runner._sanitized_environment({}),
        nonce="b" * 64,
    )
    monkeypatch.setattr(runner, "_require_execution_authority", lambda: config)
    monkeypatch.setattr(
        runner,
        "_query_process_identity",
        lambda pid: worker if pid == os.getpid() else parent,
    )
    monkeypatch.setattr(runner.sys, "argv", worker_command[1:])
    monkeypatch.setattr(runner.os, "getppid", lambda: int(parent["pid"]))
    monkeypatch.setattr(runner, "_read_frame", lambda *_args: envelope)
    monkeypatch.setattr(runner, "_write_frame", lambda *_args: None)
    monkeypatch.setattr(runner, "_require_anonymous_pipe", lambda *_args: None)
    monkeypatch.setattr(
        runner,
        "_sanitized_environment",
        lambda source=None: {},
    )
    monkeypatch.setattr(
        runner,
        "_load_worker_data",
        lambda *_args, **_kwargs: pytest.fail("data loading reached"),
    )
    monkeypatch.setattr(
        runner.recovery.v4,
        "_process_block",
        lambda *_args, **_kwargs: pytest.fail("solver reached"),
    )
    with pytest.raises(ValueError, match="alias|reparse"):
        runner._worker_from_capability(9, 10, read_handle=91, ack_handle=92)


def test_real_os_anonymous_pipe_synthetic_probe_binds_post_popen_identity(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runner,
        "_load_worker_data",
        lambda *_args, **_kwargs: pytest.fail("scientific loader reached"),
    )
    monkeypatch.setattr(
        runner.recovery.v4,
        "_process_block",
        lambda *_args, **_kwargs: pytest.fail("solver reached"),
    )
    monkeypatch.setattr(
        runner.recovery,
        "_atomic_json",
        lambda *_args, **_kwargs: pytest.fail("result/formal write reached"),
    )
    report = runner._synthetic_capability_probe()
    assert report["probe_passed"] is True
    assert report["anonymous_pipe_transport"] is True
    assert report["post_popen_identity_bound"] is True
    assert report["single_use_acknowledged"] is True
    assert report["scientific_loader_calls"] == 0
    assert report["solver_calls"] == 0
    assert report["result_writes"] == 0
    assert report["formal_writes"] == 0


@pytest.mark.parametrize("mode", ["ordinary_file", "wrong_direction", "replay"])
def test_real_os_capability_probe_rejects_nonpipe_direction_and_replay(
    mode: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        runner,
        "_load_worker_data",
        lambda *_args, **_kwargs: pytest.fail("scientific loader reached"),
    )
    monkeypatch.setattr(
        runner.recovery.v4,
        "_process_block",
        lambda *_args, **_kwargs: pytest.fail("solver reached"),
    )
    monkeypatch.setattr(
        runner.recovery,
        "_atomic_json",
        lambda *_args, **_kwargs: pytest.fail("result/formal write reached"),
    )
    with pytest.raises((EOFError, ValueError)):
        runner._synthetic_capability_probe(mode=mode)


def test_predecessor_runtime_authority_drift_fails_closed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    original = runner.recovery._sha256
    victim = runner.ROOT / "experiments/run_rq2_public_grid_two_block_pilot_candidate_v1.py"
    monkeypatch.setattr(
        runner.recovery,
        "_sha256",
        lambda path: "0" * 64 if Path(path) == victim else original(Path(path)),
    )
    with pytest.raises(ValueError, match="v1 member"):
        runner._verify_predecessor_authority()


def test_v3_has_no_runtime_import_of_pilot_v1_or_v2() -> None:
    source = Path(runner.__file__).read_text(encoding="utf-8")
    assert "import run_rq2_public_grid_two_block_pilot_candidate_v1" not in source
    assert "import run_rq2_public_grid_two_block_pilot_candidate_v2" not in source


def test_typed_tree_rejects_extra_empty_directory_and_reparse(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    (tmp_path / "expected").mkdir()
    (tmp_path / "expected" / "file.json").write_text("{}", encoding="utf-8")
    inventory = runner._typed_tree(tmp_path)
    assert inventory["directories"] == ["expected"]
    (tmp_path / "extra-empty").mkdir()
    inventory = runner._typed_tree(tmp_path)
    assert "extra-empty" in inventory["directories"]
    original = runner._is_link_or_reparse
    monkeypatch.setattr(
        runner,
        "_is_link_or_reparse",
        lambda path: path.name == "extra-empty" or original(path),
    )
    with pytest.raises(ValueError, match="reparse"):
        runner._typed_tree(tmp_path)


def test_publish_result_reaches_atomic_rename_with_exact_tree(tmp_path: Path) -> None:
    controller, sources, staging, target = _publication_fixture(tmp_path)
    summary = runner._publish_result(
        staging,
        target,
        config=runner._load_yaml(runner.CONFIG, "candidate v3"),
        controller=controller,
        sources=sources,
    )
    assert summary["status"] == "complete_nonformal_pilot"
    assert target.is_dir()
    assert not staging.exists()
    manifest = json.loads((target / "SHA256SUMS.json").read_text(encoding="utf-8"))
    assert manifest == runner._typed_tree(target)


@pytest.mark.parametrize(
    "mutation",
    [
        "payload",
        "receipt",
        "manifest",
        "comparison",
        "authority",
        "extra_file",
        "extra_empty_directory",
        "reparse_directory",
    ],
)
def test_publish_result_final_boundary_tamper_fails_before_rename(
    mutation: str, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    controller, sources, staging, target = _publication_fixture(tmp_path)

    def tamper(root: Path) -> None:
        if mutation == "payload":
            path = root / "workers" / runner.BLOCKS[0] / "payload.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["scientific_payload_sha256"] = "0" * 64
            path.write_text(json.dumps(data), encoding="utf-8")
        elif mutation == "receipt":
            path = root / "workers" / runner.BLOCKS[0] / "receipt.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["worker_payload_sha256"] = "0" * 64
            path.write_text(json.dumps(data), encoding="utf-8")
        elif mutation == "manifest":
            (root / "SHA256SUMS.json").write_text("{}", encoding="utf-8")
        elif mutation == "comparison":
            (root / "comparison.json").write_text("{}", encoding="utf-8")
        elif mutation == "authority":
            (root / "config.yaml").write_text("schema: drifted\n", encoding="utf-8")
        elif mutation == "extra_file":
            (root / "extra.txt").write_text("unexpected", encoding="utf-8")
        elif mutation == "extra_empty_directory":
            (root / "empty").mkdir()
        else:
            path = root / "workers" / runner.BLOCKS[0]
            original = runner._is_link_or_reparse
            monkeypatch.setattr(
                runner,
                "_is_link_or_reparse",
                lambda candidate: candidate == path or original(candidate),
            )

    with pytest.raises((RuntimeError, TypeError, ValueError)):
        runner._publish_result(
            staging,
            target,
            config=runner._load_yaml(runner.CONFIG, "candidate v3"),
            controller=controller,
            sources=sources,
            pre_rename_test_hook=tamper,
        )
    assert not target.exists()


def test_publish_result_target_preexist_fails_without_replacement(tmp_path: Path) -> None:
    controller, sources, staging, target = _publication_fixture(tmp_path)
    target.mkdir()
    marker = target / "user-data.txt"
    marker.write_text("preserve", encoding="utf-8")
    with pytest.raises(FileExistsError):
        runner._publish_result(
            staging,
            target,
            config=runner._load_yaml(runner.CONFIG, "candidate v3"),
            controller=controller,
            sources=sources,
        )
    assert marker.read_text(encoding="utf-8") == "preserve"


def test_validate_only_has_zero_process_solver_result_and_formal_writes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        runner.subprocess,
        "Popen",
        lambda *_args, **_kwargs: pytest.fail("process or solver dispatch"),
    )
    monkeypatch.setattr(
        runner.recovery,
        "_atomic_json",
        lambda *_args, **_kwargs: pytest.fail("write attempted"),
    )
    report = runner.run(validate_only=True)
    assert report["validation_passed"] is True
    assert report["execution_ready"] is False
    assert report["worker_processes_started"] == 0
    assert report["solver_calls"] == 0
    assert report["result_files_written"] == 0
    assert report["formal_writes"] == 0
