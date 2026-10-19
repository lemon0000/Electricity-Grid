from __future__ import annotations

import importlib
import importlib.util
import json
import os
import py_compile
from pathlib import Path

import pytest

from experiments import (
    bootstrap_rq2_joint_deliverability_activation_v2 as bootstrap,
)
from experiments import run_rq2_joint_deliverability_activation_v2 as controller
from experiments import validate_rq2_joint_deliverability_activation_v2 as validator


def _config() -> dict[str, object]:
    return json.loads(bootstrap.CONFIG.read_text(encoding="utf-8"))


def _requires_sealed(config: dict[str, object]) -> bool:
    lifecycle = config["lifecycle"]
    assert isinstance(lifecycle, dict)
    return lifecycle["status"] == "SEALED_READY_FOR_INDEPENDENT_REVIEW"


def _valid_activation_review(
    config: dict[str, object],
    *,
    outer_sha256: str,
    inner_sha256: str,
    member_count: int,
) -> dict[str, object]:
    authorities = config["external_authorities"]
    assert isinstance(authorities, dict)
    contract = authorities["activation_review"]
    assert isinstance(contract, dict)
    required_effect = contract["required_effect"]
    assert isinstance(required_effect, dict)
    return {
        "schema": contract["schema"],
        "reviewed_on": "2026-09-06",
        "review_scope": contract["review_scope"],
        "reviewer_role": "independent_sol_reviewer",
        "reviewer_model": contract["reviewer_model"],
        "verdict": "PASS",
        "reviewed_subject": {
            "outer_path": bootstrap.OUTER_RELATIVE,
            "outer_sha256": outer_sha256,
            "inner_sha256": inner_sha256,
            "sealed_member_count": member_count,
        },
        "review_conclusion": {
            "blocker_findings": [],
            "major_findings": [],
            "minor_findings": [],
        },
        "effect": dict(required_effect),
    }


def test_static_candidate_and_fresh_process_validate_only_are_closed() -> None:
    config = _config()
    static = validator.validate(config, require_sealed=_requires_sealed(config))
    runtime = bootstrap.validate_only()
    assert static["python_closure_member_count"] == 13
    assert runtime["python_closure_member_count"] == 13
    assert runtime["fresh_process"]["runtime"]["registered_inputs_ready"] is False
    assert runtime["fresh_process"]["solver_calls"] == 0
    assert runtime["fresh_process"]["bootstrap_executed_from_verified_bytes"] is True
    assert runtime["fresh_process"]["verified_source_member_count"] == 13
    assert len(runtime["fresh_process"]["executed_source_members"]) == 11
    assert runtime["fresh_process"]["project_bytecode_cache_files_consumed"] == 0
    assert runtime["solver_calls"] == 0
    assert runtime["formal_result_files_written"] == 0
    assert runtime["formal_execution_ready"] is False
    assert runtime["formal_result"] is False
    assert runtime["paper_claim"] is False
    assert runtime["security_certified"] is False


def test_python_closure_matches_independent_ast_discovery() -> None:
    config = _config()
    closure = config["python_closure"]
    assert isinstance(closure, dict)
    expected = {
        "experiments/__init__.py",
        "experiments/bootstrap_rq2_joint_deliverability_activation_v2.py",
        "experiments/run_rq2_joint_deliverability_activation_v2.py",
        "experiments/run_rq2_joint_deliverability_implementation_v2.py",
        "experiments/validate_rq2_joint_deliverability_implementation_v2.py",
        "src/__init__.py",
        "src/rq2_joint_deliverability_execution_v3/__init__.py",
        "src/rq2_joint_deliverability_execution_v3/core.py",
        "src/rq2_joint_deliverability_v2/__init__.py",
        "src/rq2_joint_deliverability_v2/evaluation.py",
        "src/rq2_joint_deliverability_v2/model.py",
        "src/rq2_joint_deliverability_v2/scenarios.py",
        "src/rq2_joint_deliverability_v2/solver_adapter.py",
    }
    assert set(closure["members"]) == expected
    assert (
        validator.discover_local_python_closure(validator.EXPECTED_CLOSURE_ROOTS)
        == expected
    )


def test_bootstrap_has_no_project_or_science_top_level_import() -> None:
    validator._validate_stdlib_first_bootstrap()


def test_fresh_empty_pycache_prefix_rejects_preexisting_valid_bytecode(
    tmp_path: Path,
) -> None:
    source = tmp_path / "activation_bytecode_probe.py"
    source.write_text("VALUE = 'evil'\n", encoding="utf-8")
    metadata = source.stat()
    cached = Path(importlib.util.cache_from_source(str(source)))
    cached.parent.mkdir()
    py_compile.compile(str(source), cfile=str(cached), doraise=True)
    source.write_text("VALUE = 'safe'\n", encoding="utf-8")
    os.utime(source, ns=(metadata.st_atime_ns, metadata.st_mtime_ns))
    command = (
        "import sys;"
        "sys.path.insert(0,sys.argv[1]);"
        "import activation_bytecode_probe as probe;"
        "print(probe.VALUE)"
    )
    ordinary = bootstrap.subprocess.run(
        [bootstrap.sys.executable, "-I", "-B", "-c", command, str(tmp_path)],
        check=True,
        capture_output=True,
        text=True,
    )
    assert ordinary.stdout.strip() == "evil"

    isolated_cache = tmp_path / "isolated-cache"
    isolated_cache.mkdir()
    isolated = bootstrap.subprocess.run(
        [
            bootstrap.sys.executable,
            *bootstrap._isolated_python_flags(isolated_cache),
            "-c",
            command,
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert isolated.stdout.strip() == "safe"
    assert list(isolated_cache.iterdir()) == []


def test_stage0_executes_stdin_bytes_instead_of_live_bootstrap(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    live_bootstrap = tmp_path / "bootstrap.py"
    live_bootstrap.write_text("print('live-unverified')\n", encoding="utf-8")
    verified = b"print('verified-stdin')\n"
    cache = tmp_path / "stage0-cache"
    cache.mkdir()
    monkeypatch.setattr(bootstrap, "ROOT", tmp_path)
    monkeypatch.setattr(bootstrap, "BOOTSTRAP_RELATIVE", "bootstrap.py")
    envelope = bootstrap._canonical_json_bytes(
        {
            "schema": "rq2_joint_deliverability_activation_parent_envelope_v2",
            "python_sources": {
                "bootstrap.py": {
                    "sha256": bootstrap._sha256(verified),
                    "bytes_b64": bootstrap.base64.b64encode(verified).decode("ascii"),
                }
            },
        }
    )
    completed = bootstrap.subprocess.run(
        bootstrap._fresh_probe_command(
            cache,
            envelope_sha256=bootstrap._sha256(envelope),
        ),
        input=envelope,
        check=True,
        capture_output=True,
    )
    assert completed.stdout.strip() == b"verified-stdin"


def test_verified_source_loader_wins_after_live_source_changes(
    tmp_path: Path,
) -> None:
    trusted_sources = {
        "snapshot_probe/__init__.py": b"",
        "snapshot_probe/value.py": b"VALUE = 'trusted'\n",
    }
    live_root = tmp_path / "live"
    live_module = live_root / "snapshot_probe" / "value.py"
    live_module.parent.mkdir(parents=True)
    (live_module.parent / "__init__.py").write_bytes(b"")
    live_module.write_text("VALUE = 'changed'\n", encoding="utf-8")
    executed: dict[str, str] = {}
    finder = bootstrap._VerifiedSourceFinder(trusted_sources, executed)
    bootstrap.sys.path.insert(0, str(live_root))
    bootstrap.sys.meta_path.insert(0, finder)
    try:
        imported = importlib.import_module("snapshot_probe.value")
        assert imported.VALUE == "trusted"
        assert executed == {
            "snapshot_probe": "snapshot_probe/__init__.py",
            "snapshot_probe.value": "snapshot_probe/value.py",
        }
    finally:
        bootstrap.sys.meta_path.remove(finder)
        bootstrap.sys.path.remove(str(live_root))
        bootstrap.sys.modules.pop("snapshot_probe.value", None)
        bootstrap.sys.modules.pop("snapshot_probe", None)


def test_verified_source_loader_blocks_unregistered_live_sibling_body(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    marker = tmp_path / "unregistered-executed.txt"
    package = tmp_path / "blocked_probe_pkg"
    package.mkdir()
    (package / "__init__.py").write_bytes(b"")
    (package / "extra.py").write_text(
        f"from pathlib import Path\nPath({str(marker)!r}).write_text('executed')\n",
        encoding="utf-8",
    )
    trusted_sources = {
        "blocked_probe_pkg/__init__.py": b"from . import extra\n",
    }
    executed: dict[str, str] = {}
    finder = bootstrap._VerifiedSourceFinder(trusted_sources, executed)
    monkeypatch.setattr(bootstrap, "ROOT", tmp_path)
    bootstrap.sys.path.insert(0, str(tmp_path))
    bootstrap.sys.meta_path.insert(0, finder)
    try:
        with pytest.raises(ModuleNotFoundError, match="unregistered"):
            importlib.import_module("blocked_probe_pkg")
        assert not marker.exists()
    finally:
        bootstrap.sys.meta_path.remove(finder)
        bootstrap.sys.path.remove(str(tmp_path))
        bootstrap.sys.modules.pop("blocked_probe_pkg.extra", None)
        bootstrap.sys.modules.pop("blocked_probe_pkg", None)


@pytest.mark.parametrize(
    "target",
    (
        bootstrap.BOOTSTRAP_RELATIVE,
        bootstrap.CONTROLLER_RELATIVE,
        bootstrap.EXECUTION_CORE_RELATIVE,
    ),
)
def test_python_closure_single_digest_drift_is_rejected(target: str) -> None:
    config = _config()
    closure = config["python_closure"]
    assert isinstance(closure, dict)
    members = closure["members"]
    assert isinstance(members, dict)
    members[target] = "0" * 64
    with pytest.raises(bootstrap.ActivationRejected, match="closure SHA-256"):
        bootstrap._verify_python_closure(config)


def test_postimport_unregistered_local_module_is_rejected(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config()
    closure = config["python_closure"]
    assert isinstance(closure, dict)
    members = closure["members"]
    assert isinstance(members, dict)
    expected = set(closure["postimport_probe_members"])
    monkeypatch.setattr(
        bootstrap,
        "_local_module_paths",
        lambda: {
            "__main__": bootstrap.BOOTSTRAP_RELATIVE,
            "controller": bootstrap.CONTROLLER_RELATIVE,
            "core": bootstrap.EXECUTION_CORE_RELATIVE,
            "forged": "src/forged.py",
        },
    )
    with pytest.raises(bootstrap.ActivationRejected, match="inventory drifted"):
        bootstrap._verify_postimport_modules(
            members,
            expected_probe_members=expected,
            source_bytes={},
            executed={},
        )


def test_postimport_verification_does_not_reread_live_project_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    sources = {
        bootstrap.BOOTSTRAP_RELATIVE: b"bootstrap",
        bootstrap.CONTROLLER_RELATIVE: b"controller",
        bootstrap.EXECUTION_CORE_RELATIVE: b"core",
    }
    closure = {relative: bootstrap._sha256(raw) for relative, raw in sources.items()}
    observed = {
        "__main__": bootstrap.BOOTSTRAP_RELATIVE,
        "controller": bootstrap.CONTROLLER_RELATIVE,
        "core": bootstrap.EXECUTION_CORE_RELATIVE,
    }
    executed = {
        "controller": bootstrap.CONTROLLER_RELATIVE,
        "core": bootstrap.EXECUTION_CORE_RELATIVE,
    }
    monkeypatch.setattr(bootstrap, "_local_module_paths", lambda: observed)
    monkeypatch.setattr(
        bootstrap,
        "_stable",
        lambda _path: (_ for _ in ()).throw(
            AssertionError("live project source must not be reread")
        ),
    )
    result = bootstrap._verify_postimport_modules(
        closure,
        expected_probe_members=set(sources),
        source_bytes=sources,
        executed=executed,
    )
    assert result["observed_module_count"] == 3


@pytest.mark.parametrize(
    ("error", "expected"),
    (
        (KeyboardInterrupt(), KeyboardInterrupt),
        (
            bootstrap.subprocess.TimeoutExpired(cmd="probe", timeout=60),
            bootstrap.ActivationRejected,
        ),
    ),
)
def test_fresh_probe_baseexception_or_timeout_reaps_child(
    monkeypatch: pytest.MonkeyPatch,
    error: BaseException,
    expected: type[BaseException],
) -> None:
    calls: list[str] = []
    envelope = b"verified parent envelope"

    class Probe:
        returncode: int | None = None

        def communicate(
            self,
            *,
            input: bytes,
            timeout: int,
        ) -> tuple[bytes, bytes]:
            assert input == envelope
            assert timeout == 60
            raise error

        def poll(self) -> int | None:
            return self.returncode

        def terminate(self) -> None:
            calls.append("terminate")

        def wait(self, *, timeout: int) -> int:
            assert timeout == 2
            calls.append("wait")
            self.returncode = -15
            return self.returncode

        def kill(self) -> None:
            calls.append("kill")

    monkeypatch.setattr(bootstrap.subprocess, "Popen", lambda *args, **kwargs: Probe())
    with pytest.raises(expected):
        bootstrap._run_fresh_probe(
            envelope_raw=envelope,
            expected_bundle={"member_count": 22},
            expected_execution={
                "execution_outer_sha256": "a" * 64,
                "execution_review_sha256": "b" * 64,
            },
            expected_closure={"bootstrap.py": "c" * 64},
            expected_probe_members=["bootstrap.py"],
        )
    assert calls == ["terminate", "wait"]


def test_fresh_probe_rejects_forged_child_inventory(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected_modules = [bootstrap.BOOTSTRAP_RELATIVE]
    forged = {
        "schema": "rq2_joint_deliverability_activation_fresh_probe_v2",
        "bundle_member_count": 22,
        "python_closure_member_count": 999,
        "verified_source_member_count": 999,
        "observed_module_count": 0,
        "observed_modules": [],
        "executed_source_members": [],
        "runtime": {
            "schema": "rq2_joint_deliverability_activation_import_validation_v2",
            "execution_outer_sha256": "a" * 64,
            "execution_review_sha256": "b" * 64,
            "static_authority_sha256": "d" * 64,
            "registered_inputs_ready": False,
            "public_stage_surface": "closed",
            "solver_calls": 0,
            "formal_result_files_written": 0,
        },
        "bootstrap_executed_from_verified_bytes": True,
        "project_modules_imported_from_verified_bytes": True,
        "project_bytecode_cache_files_consumed": 0,
        "solver_calls": 0,
        "formal_result_files_written": 0,
    }

    class Probe:
        returncode = 0

        def communicate(
            self,
            *,
            input: bytes,
            timeout: int,
        ) -> tuple[bytes, bytes]:
            assert input == b"parent envelope"
            assert timeout == 60
            return json.dumps(forged).encode(), b""

    monkeypatch.setattr(bootstrap.subprocess, "Popen", lambda *args, **kwargs: Probe())
    with pytest.raises(bootstrap.ActivationRejected, match="output schema drifted"):
        bootstrap._run_fresh_probe(
            envelope_raw=b"parent envelope",
            expected_bundle={"member_count": 22},
            expected_execution={
                "execution_outer_sha256": "a" * 64,
                "execution_review_sha256": "b" * 64,
                "static_authority_sha256": "d" * 64,
            },
            expected_closure={"bootstrap.py": "c" * 64},
            expected_probe_members=expected_modules,
        )


@pytest.mark.parametrize(
    ("terminate_error", "kill_error"),
    (
        (True, False),
        (False, False),
        (False, True),
    ),
)
def test_probe_cleanup_continues_after_terminate_wait_or_kill_exception(
    terminate_error: bool,
    kill_error: bool,
) -> None:
    calls: list[str] = []

    class Probe:
        returncode: int | None = None
        wait_calls = 0

        def poll(self) -> int | None:
            return self.returncode

        def terminate(self) -> None:
            calls.append("terminate")
            if terminate_error:
                raise OSError("injected terminate failure")

        def wait(self, *, timeout: int) -> int:
            assert timeout == 2
            calls.append("wait")
            self.wait_calls += 1
            if self.wait_calls == 1:
                raise bootstrap.subprocess.TimeoutExpired(cmd="probe", timeout=2)
            self.returncode = 0
            return self.returncode

        def kill(self) -> None:
            calls.append("kill")
            if kill_error:
                raise OSError("injected kill failure")
            self.returncode = -9

    bootstrap._terminate_probe(Probe())
    assert calls == ["terminate", "wait", "kill", "wait"]


def test_probe_cleanup_rejects_an_unreaped_child() -> None:
    calls: list[str] = []

    class Probe:
        def poll(self) -> None:
            return None

        def terminate(self) -> None:
            calls.append("terminate")
            raise OSError("injected terminate failure")

        def wait(self, *, timeout: int) -> int:
            assert timeout == 2
            calls.append("wait")
            raise bootstrap.subprocess.TimeoutExpired(cmd="probe", timeout=2)

        def kill(self) -> None:
            calls.append("kill")
            raise OSError("injected kill failure")

    with pytest.raises(bootstrap.ActivationRejected, match="could not be reaped"):
        bootstrap._terminate_probe(Probe())
    assert calls == ["terminate", "wait", "kill", "wait"]


@pytest.mark.parametrize(
    "field",
    ("outer_sha256", "review_sha256"),
)
def test_execution_authority_single_digest_drift_is_rejected(field: str) -> None:
    config = _config()
    authority = config["execution_authority"]
    assert isinstance(authority, dict)
    authority[field] = "0" * 64
    with pytest.raises(bootstrap.ActivationRejected, match="drifted"):
        bootstrap._verify_execution_authority(config)


@pytest.mark.parametrize("version", (1, 2))
def test_execution_predecessor_single_digest_drift_is_rejected(version: int) -> None:
    config = _config()
    authority = config["execution_authority"]
    assert isinstance(authority, dict)
    predecessors = authority["recursive_predecessors"]
    assert isinstance(predecessors, list)
    predecessor = next(item for item in predecessors if item["version"] == version)
    predecessor["outer_sha256"] = "0" * 64
    with pytest.raises(bootstrap.ActivationRejected, match="contract drifted"):
        bootstrap._verify_execution_authority(config)


@pytest.mark.parametrize("inventory", ("duplicate_v2", "missing_v2"))
def test_execution_predecessor_inventory_must_be_exact(
    inventory: str,
) -> None:
    config = _config()
    authority = config["execution_authority"]
    assert isinstance(authority, dict)
    predecessors = authority["recursive_predecessors"]
    assert isinstance(predecessors, list)
    v2 = dict(predecessors[0])
    v1 = dict(predecessors[1])
    authority["recursive_predecessors"] = (
        [v2, dict(v2)] if inventory == "duplicate_v2" else [v1]
    )
    with pytest.raises(bootstrap.ActivationRejected, match="contract drifted"):
        bootstrap._verify_execution_authority(config)


def test_manifest_chain_rejects_outer_change_during_member_replay(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    member_relative = "member.py"
    inner_relative = "inner.json"
    member = tmp_path / member_relative
    inner = tmp_path / inner_relative
    outer = tmp_path / "outer.json"
    member.write_bytes(b"trusted\n")
    inner_bytes = json.dumps(
        {
            "schema": "inner-v1",
            "version": 1,
            "files": {member_relative: bootstrap._sha256(member.read_bytes())},
        }
    ).encode()
    inner.write_bytes(inner_bytes)
    outer_payload = {
        "schema": "outer-v1",
        "version": 1,
        "inner": {
            "path": inner_relative,
            "sha256": bootstrap._sha256(inner_bytes),
        },
    }
    outer.write_text(json.dumps(outer_payload), encoding="utf-8")
    real_stable = bootstrap._stable
    swapped = False

    def stable_then_swap(path: Path) -> bytes:
        nonlocal swapped
        raw = real_stable(path)
        if path == member and not swapped:
            outer_payload["generation"] = "changed"
            outer.write_text(json.dumps(outer_payload), encoding="utf-8")
            swapped = True
        return raw

    monkeypatch.setattr(bootstrap, "ROOT", tmp_path)
    monkeypatch.setattr(bootstrap, "_stable", stable_then_swap)
    with pytest.raises(bootstrap.ActivationRejected, match="chain changed"):
        bootstrap._verify_outer_chain(
            outer,
            expected_outer_schema="outer-v1",
            expected_inner_schema="inner-v1",
            expected_version=1,
            expected_inner_path=inner_relative,
        )
    assert swapped is True


def test_execute_is_hard_closed_before_config_read_or_spawn(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls = {"config": 0, "spawn": 0}

    def spawned(*args: object, **kwargs: object) -> None:
        del args, kwargs
        calls["spawn"] += 1
        raise AssertionError("subprocess must not start")

    def loaded() -> None:
        calls["config"] += 1
        raise AssertionError("config must not be read")

    monkeypatch.setattr(bootstrap.subprocess, "run", spawned)
    monkeypatch.setattr(bootstrap, "_load_config", loaded)
    with pytest.raises(bootstrap.ActivationRejected, match="review-only"):
        bootstrap.execute()
    assert calls == {"config": 0, "spawn": 0}


def test_candidate_does_not_call_execution_v3_private_stage_helpers() -> None:
    bootstrap_source = Path(bootstrap.__file__).read_text(encoding="utf-8")
    controller_source = Path(controller.__file__).read_text(encoding="utf-8")
    forbidden = (
        "_audit_registered_input_snapshot",
        "_execute_planning_stage_with_evidence_from_audit",
        "_stream_holdout_stage_from_audit",
        "_execute_bootstrap_resumable_from_audit",
        "_aggregate_bootstrap_checkpoints_from_audit",
    )
    assert all(name not in bootstrap_source for name in forbidden)
    assert all(name not in controller_source for name in forbidden)
    assert not hasattr(controller, "execute")


def test_strict_json_rejects_duplicate_and_nonfinite_values() -> None:
    with pytest.raises(bootstrap.ActivationRejected, match="duplicate"):
        bootstrap._json_bytes(b'{"a":1,"a":2}', "duplicate")
    for raw in (b'{"a":NaN}', b'{"a":Infinity}', b'{"a":1e999}'):
        with pytest.raises(bootstrap.ActivationRejected, match="non-finite"):
            bootstrap._json_bytes(raw, "nonfinite")


def test_stable_read_rejects_path_swap_after_descriptor_open(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = tmp_path / "artifact.json"
    replacement = tmp_path / "replacement.json"
    artifact.write_bytes(b'{"identity":"original"}')
    replacement.write_bytes(b'{"identity":"replaced"}')
    real_open = bootstrap.os.open
    swapped = False

    def open_then_swap(
        path: str | bytes,
        flags: int,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal swapped
        if dir_fd is None:
            descriptor = real_open(path, flags)
        else:
            descriptor = real_open(path, flags, dir_fd=dir_fd)
        if not swapped and dir_fd is not None and path == artifact.name:
            replacement.replace(artifact)
            swapped = True
        return descriptor

    monkeypatch.setattr(bootstrap.os, "open", open_then_swap)
    with pytest.raises(bootstrap.ActivationRejected, match="stable readback drifted"):
        bootstrap._stable(artifact)
    assert swapped is True


def test_stable_read_rejects_ancestor_swap_during_anchored_traversal(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active = tmp_path / "active"
    displaced = tmp_path / "displaced"
    replacement = tmp_path / "replacement"
    active.mkdir()
    replacement.mkdir()
    artifact = active / "artifact.json"
    artifact.write_bytes(b'{"identity":"trusted"}')
    (replacement / artifact.name).write_bytes(b'{"identity":"forged"}')
    real_open = bootstrap.os.open
    swapped = False

    def open_during_ancestor_swap(
        path: str | bytes,
        flags: int,
        *,
        dir_fd: int | None = None,
    ) -> int:
        nonlocal swapped
        if not swapped and dir_fd is not None and path == artifact.name:
            active.rename(displaced)
            replacement.rename(active)
            swapped = True
        if dir_fd is None:
            return real_open(path, flags)
        return real_open(path, flags, dir_fd=dir_fd)

    monkeypatch.setattr(bootstrap.os, "open", open_during_ancestor_swap)
    with pytest.raises(bootstrap.ActivationRejected, match="stable readback drifted"):
        bootstrap._stable(artifact)
    assert swapped is True


def test_anchored_open_close_error_does_not_orphan_child_descriptor(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    artifact = tmp_path / "artifact.json"
    artifact.write_text("trusted", encoding="utf-8")
    real_open = bootstrap.os.open
    real_dup = bootstrap.os.dup
    real_close = bootstrap.os.close
    live: set[int] = set()
    injected = False

    def tracked_open(
        path: str | bytes,
        flags: int,
        *,
        dir_fd: int | None = None,
    ) -> int:
        descriptor = (
            real_open(path, flags)
            if dir_fd is None
            else real_open(path, flags, dir_fd=dir_fd)
        )
        live.add(descriptor)
        return descriptor

    def tracked_dup(descriptor: int) -> int:
        duplicate = real_dup(descriptor)
        live.add(duplicate)
        return duplicate

    def fail_first_close(descriptor: int) -> None:
        nonlocal injected
        if not injected:
            injected = True
            raise OSError(bootstrap.errno.EIO, "injected close failure")
        real_close(descriptor)
        live.discard(descriptor)

    monkeypatch.setattr(bootstrap.os, "open", tracked_open)
    monkeypatch.setattr(bootstrap.os, "dup", tracked_dup)
    monkeypatch.setattr(bootstrap.os, "close", fail_first_close)
    with pytest.raises(bootstrap.ActivationRejected, match="cleanup failed"):
        bootstrap._posix_open_anchored(artifact)
    assert injected is True
    assert live == set()


def test_closed_authority_dangling_symlink_is_not_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config()
    authorities = config["external_authorities"]
    assert isinstance(authorities, dict)
    runtime = authorities["runtime"]
    assert isinstance(runtime, dict)
    dangling = tmp_path / "runtime.json"
    dangling.symlink_to(tmp_path / "missing.json")
    runtime["path"] = dangling.relative_to(tmp_path).as_posix()
    monkeypatch.setattr(bootstrap, "ROOT", tmp_path)
    monkeypatch.setattr(validator, "ROOT", tmp_path)
    with pytest.raises(ValueError, match="unexpectedly exists"):
        validator._closed_external_authorities(config)


def test_presence_uses_anchored_alias_evidence(
    tmp_path: Path,
) -> None:
    candidate = tmp_path / "junction"
    candidate.symlink_to(tmp_path / "missing")
    assert bootstrap._path_is_present_or_aliased(candidate) is True


def test_blockers_reject_ancestor_swap_from_absent_to_present_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    active = tmp_path / "active"
    displaced = tmp_path / "displaced"
    replacement = tmp_path / "replacement"
    active.mkdir()
    replacement.mkdir()
    authority_name = "runtime.json"
    (replacement / authority_name).write_text("{}", encoding="utf-8")
    config = _config()
    authorities = config["external_authorities"]
    assert isinstance(authorities, dict)
    runtime = authorities["runtime"]
    assert isinstance(runtime, dict)
    runtime["path"] = f"active/{authority_name}"
    monkeypatch.setattr(bootstrap, "ROOT", tmp_path)
    real_stat = bootstrap.os.stat
    swapped = False

    def stat_during_ancestor_swap(
        path: str | bytes,
        *,
        dir_fd: int | None = None,
        follow_symlinks: bool = True,
    ) -> os.stat_result:
        nonlocal swapped
        if not swapped and dir_fd is not None and path == authority_name:
            active.rename(displaced)
            replacement.rename(active)
            swapped = True
        if dir_fd is None:
            return real_stat(path, follow_symlinks=follow_symlinks)
        return real_stat(
            path,
            dir_fd=dir_fd,
            follow_symlinks=follow_symlinks,
        )

    monkeypatch.setattr(bootstrap.os, "stat", stat_during_ancestor_swap)
    with pytest.raises(bootstrap.ActivationRejected, match="presence changed"):
        bootstrap._blockers(config)
    assert swapped is True


def test_windows_anchored_open_uses_relative_nt_handles() -> None:
    source = Path(bootstrap.__file__).read_text(encoding="utf-8")
    assert "NtCreateFile" in source
    assert "RootDirectory" in source
    assert "file_open_reparse_point" in source
    assert "close_handle_with_recovery" in source


def test_predecessor_outer_and_rework_receipt_are_exactly_bound() -> None:
    config = _config()
    result = bootstrap._verify_predecessor_activation(config)
    assert result == {
        "activation_v1_outer_sha256": bootstrap.PREDECESSOR_OUTER_SHA256,
        "activation_v1_rework_sha256": bootstrap.PREDECESSOR_REWORK_SHA256,
    }


@pytest.mark.parametrize(
    "name",
    (
        "dispatched_grid_manifest",
        "runtime",
        "execution_activation",
        "formal_run",
    ),
)
@pytest.mark.parametrize("dangling_symlink", (False, True))
def test_production_blockers_reject_closed_authority_presence(
    name: str,
    dangling_symlink: bool,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config()
    authorities = config["external_authorities"]
    assert isinstance(authorities, dict)
    contract = authorities[name]
    assert isinstance(contract, dict)
    contract["path"] = "unexpected-authority.json"
    authority_path = tmp_path / "unexpected-authority.json"
    if dangling_symlink:
        authority_path.symlink_to(tmp_path / "missing.json")
    else:
        authority_path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(bootstrap, "ROOT", tmp_path)
    with pytest.raises(
        bootstrap.ActivationRejected,
        match=f"unexpectedly exists: {name}",
    ):
        bootstrap._blockers(config)


@pytest.mark.skipif(os.name != "nt", reason="requires a native Windows junction")
def test_windows_dangling_junctions_fail_closed_for_authorities_and_manifests(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def dangling_junction(name: str) -> Path:
        target = tmp_path / f"{name}-target"
        junction = tmp_path / name
        target.mkdir()
        completed = bootstrap.subprocess.run(
            ["cmd.exe", "/d", "/c", "mklink", "/J", str(junction), str(target)],
            check=False,
            capture_output=True,
            text=True,
        )
        if completed.returncode != 0:
            pytest.fail(f"native junction creation failed: {completed.stderr}")
        target.rmdir()
        return junction

    config = _config()
    authorities = config["external_authorities"]
    assert isinstance(authorities, dict)
    monkeypatch.setattr(bootstrap, "ROOT", tmp_path)
    for name in (
        "dispatched_grid_manifest",
        "runtime",
        "execution_activation",
        "formal_run",
    ):
        junction = dangling_junction(f"{name}.json")
        contract = authorities[name]
        assert isinstance(contract, dict)
        contract["path"] = junction.name
        try:
            with pytest.raises(
                bootstrap.ActivationRejected, match="unexpectedly exists"
            ):
                bootstrap._blockers(config)
        finally:
            junction.rmdir()

    for manifest_name in ("outer", "inner"):
        junction = dangling_junction(f"{manifest_name}.json")
        monkeypatch.setattr(
            bootstrap,
            "OUTER",
            junction if manifest_name == "outer" else tmp_path / "absent-outer.json",
        )
        monkeypatch.setattr(
            bootstrap,
            "INNER",
            junction if manifest_name == "inner" else tmp_path / "absent-inner.json",
        )
        try:
            with pytest.raises(
                bootstrap.ActivationRejected,
                match="must not have production manifests",
            ):
                bootstrap._verify_bundle(config, require_sealed=False)
        finally:
            junction.rmdir()


def test_activation_review_absent_valid_then_tampered(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config()
    authorities = config["external_authorities"]
    bundle = config["bundle"]
    assert isinstance(authorities, dict)
    assert isinstance(bundle, dict)
    contract = authorities["activation_review"]
    assert isinstance(contract, dict)
    config["lifecycle"] = {
        "status": "SEALED_READY_FOR_INDEPENDENT_REVIEW",
        "sealed_on": "2026-09-06",
        "pre_seal_audit_complete": True,
        "sealed_ready_for_independent_review": True,
    }
    outer_sha256 = "a" * 64
    inner_sha256 = "b" * 64
    member_count = len(bundle["members"])
    chain = {
        "outer_sha256": outer_sha256,
        "inner_sha256": inner_sha256,
        "member_count": member_count,
        "members": {},
    }
    monkeypatch.setattr(bootstrap, "ROOT", tmp_path)
    monkeypatch.setattr(
        bootstrap,
        "_verify_bundle",
        lambda _config, *, require_sealed: chain,
    )

    assert "missing_activation_review_receipt" in bootstrap._blockers(config)
    receipt = _valid_activation_review(
        config,
        outer_sha256=outer_sha256,
        inner_sha256=inner_sha256,
        member_count=member_count,
    )
    receipt_path = tmp_path / bootstrap.ACTIVATION_REVIEW_RELATIVE
    receipt_path.parent.mkdir(parents=True)
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    assert "missing_activation_review_receipt" not in bootstrap._blockers(config)

    receipt["reviewer_model"] = "not-the-required-model"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(bootstrap.ActivationRejected, match="authority drifted"):
        bootstrap._blockers(config)
    receipt["reviewer_model"] = contract["reviewer_model"]

    receipt["reviewed_on"] = "2026-09-05"
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(bootstrap.ActivationRejected, match="authority drifted"):
        bootstrap._blockers(config)
    receipt["reviewed_on"] = "2026-09-06"

    effect = receipt["effect"]
    assert isinstance(effect, dict)
    effect["formal_execution_authorized"] = True
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    with pytest.raises(bootstrap.ActivationRejected, match="authority drifted"):
        bootstrap._blockers(config)


def test_activation_review_dangling_symlink_is_not_absent(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config()
    authorities = config["external_authorities"]
    assert isinstance(authorities, dict)
    contract = authorities["activation_review"]
    assert isinstance(contract, dict)
    config["lifecycle"] = {
        "status": "SEALED_READY_FOR_INDEPENDENT_REVIEW",
        "sealed_on": "2026-09-06",
        "pre_seal_audit_complete": True,
        "sealed_ready_for_independent_review": True,
    }
    receipt_path = tmp_path / bootstrap.ACTIVATION_REVIEW_RELATIVE
    receipt_path.parent.mkdir(parents=True)
    receipt_path.symlink_to(tmp_path / "missing.json")
    monkeypatch.setattr(bootstrap, "ROOT", tmp_path)
    monkeypatch.setattr(
        bootstrap,
        "_verify_bundle",
        lambda _config, *, require_sealed: {
            "outer_sha256": "a" * 64,
            "inner_sha256": "b" * 64,
            "member_count": 22,
            "members": {},
        },
    )
    with pytest.raises(bootstrap.ActivationRejected, match="path alias"):
        bootstrap._blockers(config)


def test_activation_review_rejects_mixed_generation_outer_and_inner(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config()
    config["lifecycle"] = {
        "status": "SEALED_READY_FOR_INDEPENDENT_REVIEW",
        "sealed_on": "2026-09-06",
        "pre_seal_audit_complete": True,
        "sealed_ready_for_independent_review": True,
    }
    authorities = config["external_authorities"]
    bundle = config["bundle"]
    assert isinstance(authorities, dict)
    assert isinstance(bundle, dict)
    contract = authorities["activation_review"]
    assert isinstance(contract, dict)
    member_count = len(bundle["members"])
    receipt = _valid_activation_review(
        config,
        outer_sha256="a" * 64,
        inner_sha256="b" * 64,
        member_count=member_count,
    )
    monkeypatch.setattr(
        bootstrap,
        "_verify_bundle",
        lambda _config, *, require_sealed: {
            "outer_sha256": "c" * 64,
            "inner_sha256": "b" * 64,
            "member_count": member_count,
            "members": {},
        },
    )
    monkeypatch.setattr(
        bootstrap,
        "_authority_json",
        lambda _config, _name: (
            receipt,
            json.dumps(receipt).encode(),
            contract,
        ),
    )
    with pytest.raises(bootstrap.ActivationRejected, match="authority drifted"):
        bootstrap._require_activation_review(config)


def test_activation_review_contract_cannot_be_self_defined(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config()
    config["lifecycle"] = {
        "status": "SEALED_READY_FOR_INDEPENDENT_REVIEW",
        "sealed_on": "2026-09-06",
        "pre_seal_audit_complete": True,
        "sealed_ready_for_independent_review": True,
    }
    authorities = config["external_authorities"]
    assert isinstance(authorities, dict)
    contract = authorities["activation_review"]
    assert isinstance(contract, dict)
    contract["reviewer_model"] = "gpt-5.6-terra"
    effect = contract["required_effect"]
    assert isinstance(effect, dict)
    effect["formal_execution_authorized"] = True
    receipt = _valid_activation_review(
        config,
        outer_sha256="a" * 64,
        inner_sha256="b" * 64,
        member_count=22,
    )
    monkeypatch.setattr(
        bootstrap,
        "_verify_bundle",
        lambda _config, *, require_sealed: {
            "outer_sha256": "a" * 64,
            "inner_sha256": "b" * 64,
            "member_count": 22,
            "members": {},
        },
    )
    monkeypatch.setattr(
        bootstrap,
        "_authority_json",
        lambda _config, _name: (
            receipt,
            json.dumps(receipt).encode(),
            contract,
        ),
    )
    with pytest.raises(bootstrap.ActivationRejected, match="contract drifted"):
        bootstrap._require_activation_review(config)


@pytest.mark.parametrize("sealed_on", ("2026-9-6", "2026-02-30", "not-a-date"))
def test_sealed_lifecycle_rejects_non_iso_date(
    sealed_on: str,
) -> None:
    config = _config()
    config["lifecycle"] = {
        "status": "SEALED_READY_FOR_INDEPENDENT_REVIEW",
        "sealed_on": sealed_on,
        "pre_seal_audit_complete": True,
        "sealed_ready_for_independent_review": True,
    }
    with pytest.raises(bootstrap.ActivationRejected, match="date drifted"):
        bootstrap._verify_bundle(config, require_sealed=True)


def test_sealed_lifecycle_accepts_iso_date_and_exact_keys(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    config = _config()
    bundle = config["bundle"]
    assert isinstance(bundle, dict)
    members = bundle["members"]
    assert isinstance(members, list)
    config["lifecycle"] = {
        "status": "SEALED_READY_FOR_INDEPENDENT_REVIEW",
        "sealed_on": "2026-09-06",
        "pre_seal_audit_complete": True,
        "sealed_ready_for_independent_review": True,
    }
    chain = {
        "outer_sha256": "a" * 64,
        "inner_sha256": "b" * 64,
        "member_count": len(members),
        "members": {relative: "c" * 64 for relative in members},
    }
    monkeypatch.setattr(bootstrap, "_verify_outer_chain", lambda *args, **kwargs: chain)
    assert bootstrap._verify_bundle(config, require_sealed=True) == chain

    lifecycle = config["lifecycle"]
    assert isinstance(lifecycle, dict)
    lifecycle["unexpected"] = False
    with pytest.raises(bootstrap.ActivationRejected, match="lifecycle drifted"):
        bootstrap._verify_bundle(config, require_sealed=True)


def test_controller_validate_only_rechecks_reviewed_execution_authority() -> None:
    config = _config()
    authority = config["execution_authority"]
    assert isinstance(authority, dict)
    result = controller.validate_imported_runtime(
        {
            "execution_outer_sha256": authority["outer_sha256"],
            "execution_review_sha256": authority["review_sha256"],
            "static_authority_sha256": authority["static_authority_sha256"],
        }
    )
    assert result["registered_inputs_ready"] is False
    assert result["solver_calls"] == 0
    assert result["formal_result_files_written"] == 0


def test_validate_only_does_not_create_formal_roots() -> None:
    config = _config()
    roots = [bootstrap.ROOT / relative for relative in config["formal_roots"]]
    before = [(path.exists(), path.is_symlink()) for path in roots]
    bootstrap.validate_only()
    after = [(path.exists(), path.is_symlink()) for path in roots]
    assert before == after == [(False, False), (False, False)]
