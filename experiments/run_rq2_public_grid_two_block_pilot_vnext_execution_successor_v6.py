"""Review-closed V6 evidence rerun for the fixed nonformal two-block pilot."""

from __future__ import annotations

import concurrent.futures
import hmac
import json
import os
import secrets
import shutil
import subprocess
import tempfile
import threading
import time
from pathlib import Path
from typing import Any

from experiments import (
    publish_rq2_public_grid_evidence_publication_successor_v3 as publisher,
)
from experiments import (
    rq2_public_grid_two_block_pilot_vnext_execution_contract_v6 as contract,
)


class HonestIncomplete(contract.ContractRejected):
    """A non-certifying execution failure stopped this one-shot session."""


class AttemptLedger:
    """Atomic one-shot 0008->0009 state; it grants no signing authority."""

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._attempted: set[int] = set()
        self._active = False
        self._accepted_predecessor: str | None = None

    def consume(self, index: int) -> str | None:
        with self._lock:
            if (
                self._active
                or index not in (1, 2)
                or index in self._attempted
                or index != len(self._attempted) + 1
                or (index == 2 and self._accepted_predecessor is None)
            ):
                raise contract.ContractRejected(
                    "concurrent/retry/resume/reorder/skip rejected"
                )
            self._attempted.add(index)
            self._active = True
            return self._accepted_predecessor

    def finish(self, index: int, accepted_digest: str | None) -> None:
        with self._lock:
            if not self._active or index != len(self._attempted):
                raise contract.ContractRejected("attempt completion state drifted")
            if index == 1 and accepted_digest is not None:
                self._accepted_predecessor = accepted_digest
            self._active = False


def _child_raw(descriptor: int) -> int:
    if os.name != "nt":
        return descriptor
    import msvcrt

    return int(msvcrt.get_osfhandle(descriptor))


def _popen(
    command: list[str],
    worker_read: int,
    worker_ack: int,
    environment: dict[str, str],
    *,
    capture_stderr: bool = False,
) -> subprocess.Popen[Any]:
    kwargs: dict[str, Any] = {
        "cwd": contract.ROOT,
        "env": dict(environment),
        "stdin": subprocess.DEVNULL,
        "stdout": subprocess.DEVNULL,
        "stderr": None if capture_stderr else subprocess.DEVNULL,
        "close_fds": True,
    }
    if os.name == "nt":
        startup = subprocess.STARTUPINFO()
        startup.lpAttributeList = {"handle_list": [worker_read, worker_ack]}
        kwargs["startupinfo"] = startup
        kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW
    else:
        kwargs["pass_fds"] = (worker_read, worker_ack)
    return subprocess.Popen(command, **kwargs)


def _pipe_setup() -> tuple[int, int, int, int, int, int]:
    controller_read, worker_ack_fd = os.pipe()
    worker_read_fd, controller_write = os.pipe()
    worker_read = _child_raw(worker_read_fd)
    worker_ack = _child_raw(worker_ack_fd)
    if os.name == "nt":
        os.set_handle_inheritable(worker_read, True)
        os.set_handle_inheritable(worker_ack, True)
    else:
        os.set_inheritable(worker_read_fd, True)
        os.set_inheritable(worker_ack_fd, True)
    return (
        controller_read,
        worker_ack_fd,
        worker_read_fd,
        controller_write,
        worker_read,
        worker_ack,
    )


def _clear_inheritance(worker_read: int, worker_ack: int, worker_read_fd: int, worker_ack_fd: int) -> None:
    if os.name == "nt":
        os.set_handle_inheritable(worker_read, False)
        os.set_handle_inheritable(worker_ack, False)
    else:
        os.set_inheritable(worker_read_fd, False)
        os.set_inheritable(worker_ack_fd, False)


def _close_descriptors(*descriptors: int) -> None:
    for descriptor in descriptors:
        if descriptor >= 0:
            try:
                os.close(descriptor)
            except OSError:
                pass


def _stop_process(process: subprocess.Popen[Any] | None) -> None:
    if process is None or process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=5)


def _sample_pair(pid: int, create_time_ns: int) -> tuple[int, int]:
    resources = contract.resource_primitives()
    observed = resources.sample_resource_pair(pid, create_time_ns)
    return (
        observed.child_private_commit_bytes,
        observed.system_commit_available_bytes,
    )


class _TerminationAuditProxy:
    """Observe which branch the sealed exact-owned termination policy takes."""

    def __init__(self, process: subprocess.Popen[Any]) -> None:
        self._process = process
        self.pid = process.pid
        self.action: str | None = None

    def poll(self) -> int | None:
        return self._process.poll()

    def terminate(self) -> None:
        self.action = "terminate_only"
        self._process.terminate()

    def kill(self) -> None:
        self.action = "terminate_then_kill"
        self._process.kill()

    def wait(self, timeout: float | None = None) -> int:
        return self._process.wait(timeout=timeout)


def _terminate_exact(
    process: subprocess.Popen[Any], **identity: int
) -> dict[str, object]:
    resources = contract.resource_primitives()
    audited = _TerminationAuditProxy(process)
    resources.terminate_exact_owned_child(audited, **identity)
    return {
        "termination_action": audited.action or "already_exited_before_signal",
        "termination_completed": True,
    }


def _persist_resource_journal(
    path: Path, journal: dict[str, Any]
) -> dict[str, Any]:
    raw = contract.exact_json_bytes(journal)
    path.parent.mkdir(parents=True, exist_ok=True)
    publisher.atomic_write(path, raw)
    if contract.read_stable(path) != raw:
        raise contract.ContractRejected(
            "monitor-owned resource journal persistence/readback drifted"
        )
    return {
        "schema": (
            "rq2_public_grid_resource_monitor_persisted_outcome_"
            "vnext_execution_v6"
        ),
        "version": 1,
        "resource_journal": journal,
        "persisted_path": str(path),
        "persisted_sha256": contract.sha256_bytes(raw),
        "readback_verified": True,
    }


def _start_resource_monitor(
    process: subprocess.Popen[Any],
    worker_identity: dict[str, int],
    persistence_path: Path,
    *,
    sample: Any = _sample_pair,
    monotonic_ns: Any = time.monotonic_ns,
    wall_time_ns: Any = time.time_ns,
    sleep: Any = time.sleep,
    terminate: Any = _terminate_exact,
) -> tuple[
    contract.ResourceMonitorState,
    concurrent.futures.ThreadPoolExecutor,
    concurrent.futures.Future[dict[str, Any]],
    int,
]:
    state = contract.ResourceMonitorState()
    deadline = time.monotonic_ns() + contract.WATCHDOG_NS
    executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    future = executor.submit(
        contract.monitor_owned_child_resources_journal,
        process,
        expected_pid=process.pid,
        expected_create_time_ns=worker_identity["create_time_ns"],
        watchdog_duration_ns=contract.WATCHDOG_NS,
        state=state,
        sample=sample,
        monotonic_ns=monotonic_ns,
        wall_time_ns=wall_time_ns,
        sleep=sleep,
        terminate=terminate,
        persist=lambda journal: _persist_resource_journal(
            persistence_path, journal
        ),
        persistence_path=str(persistence_path),
    )
    return state, executor, future, deadline


def _wait_first_sample(
    state: contract.ResourceMonitorState,
    deadline_ns: int,
    future: concurrent.futures.Future[dict[str, Any]] | None = None,
) -> None:
    timeout = max(0.0, (deadline_ns - time.monotonic_ns()) / 1_000_000_000)
    ready = state.ready.wait(timeout=timeout)
    if future is not None and future.done() and state.first_sample_success is False:
        future.result()
    if not ready or not state.first_sample_success:
        raise HonestIncomplete("first same-pair resource sample did not pass")


def _read_exit_notice_and_eof(
    controller_read: int, label: str
) -> tuple[bytes, dict[str, Any]]:
    raw, notice = contract.read_frame(controller_read, label)
    contract.require_eof(controller_read)
    return raw, notice


def _await_exit_notice_and_monitor(
    *,
    controller_read: int,
    process: subprocess.Popen[Any],
    resource_future: concurrent.futures.Future[dict[str, Any]],
    deadline_ns: int,
    label: str,
) -> tuple[bytes | None, dict[str, Any] | None, dict[str, Any]]:
    """Wait without making an incomplete monitor depend on exit protocol."""
    exit_executor = concurrent.futures.ThreadPoolExecutor(max_workers=1)
    exit_future = exit_executor.submit(
        _read_exit_notice_and_eof, controller_read, label
    )
    try:
        done, _ = concurrent.futures.wait(
            {exit_future, resource_future},
            timeout=max(1.0, (deadline_ns - time.monotonic_ns()) / 1e9),
            return_when=concurrent.futures.FIRST_COMPLETED,
        )
        if not done:
            raise HonestIncomplete("exit/resource futures reached watchdog")
        if resource_future in done:
            persisted = contract.validate_resource_monitor_outcome(
                resource_future.result()
            )
            journal = persisted["resource_journal"]
            if journal["status"] != "child_exited":
                return None, None, persisted
        try:
            exit_raw, exit_notice = exit_future.result(
                timeout=max(1.0, (deadline_ns - time.monotonic_ns()) / 1e9)
            )
        except Exception as exc:
            persisted = contract.validate_resource_monitor_outcome(
                resource_future.result(timeout=30)
            )
            if persisted["resource_journal"]["status"] != "child_exited":
                return None, None, persisted
            raise HonestIncomplete("worker exit protocol incomplete") from exc
        process.wait(timeout=max(1.0, (deadline_ns - time.monotonic_ns()) / 1e9))
        persisted = contract.validate_resource_monitor_outcome(
            resource_future.result(timeout=30)
        )
        return exit_raw, exit_notice, persisted
    finally:
        exit_executor.shutdown(wait=False, cancel_futures=True)


def run_review_preloader_e2e() -> dict[str, Any]:
    """Start the exact worker and stop before runtime package/science access."""
    config = contract.load_config()
    contract.verify_live_authorities()
    parent = {
        "pid": os.getpid(),
        "create_time_ns": contract.process_create_time_ns(os.getpid()),
    }
    values = list(_pipe_setup())
    controller_read, worker_ack_fd, worker_read_fd, controller_write, worker_read, worker_ack = values
    process: subprocess.Popen[Any] | None = None
    try:
        command = list(
            contract.exact_worker_command(
                mode="review-preloader",
                read_handle=worker_read,
                ack_handle=worker_ack,
                parent_pid=parent["pid"],
                parent_create_time_ns=parent["create_time_ns"],
                session_id="review-preloader",
                execution_index=0,
                block_id="review-preloader",
                predecessor_digest=None,
                nonce="review-preloader",
            )
        )
        try:
            process = _popen(
                command,
                worker_read,
                worker_ack,
                config["runtime"]["sanitized_environment"],
                capture_stderr=True,
            )
        finally:
            _clear_inheritance(worker_read, worker_ack, worker_read_fd, worker_ack_fd)
        worker_identity = {
            "pid": process.pid,
            "ppid": os.getpid(),
            "create_time_ns": contract.process_create_time_ns(process.pid),
        }
        os.close(worker_read_fd)
        worker_read_fd = -1
        os.close(worker_ack_fd)
        worker_ack_fd = -1
        hello_raw, hello = contract.read_frame(controller_read, "preloader HELLO")
        ack_raw, ack = contract.read_frame(controller_read, "preloader ACK")
        contract.require_eof(controller_read)
        os.close(controller_write)
        controller_write = -1
        if process.wait(timeout=30) != 0:
            raise contract.ContractRejected("preloader child exit rejected")
        expected = contract.build_worker_hello(
            mode="review-preloader",
            session_id="review-preloader",
            execution_index=0,
            block_id="review-preloader",
            predecessor_digest=None,
            nonce="review-preloader",
            parent_identity=parent,
            worker_identity=worker_identity,
            command=tuple(command),
            worker_read={
                "raw_identifier": worker_read,
                "type": "anonymous_pipe",
                "role": "controller_to_worker",
                "direction": "read",
                "inherited": True,
            },
            worker_ack={
                "raw_identifier": worker_ack,
                "type": "anonymous_pipe",
                "role": "worker_to_controller",
                "direction": "write",
                "inherited": True,
            },
        )
        contract.require_exact(hello, expected, label="preloader HELLO")
        expected_ack = {
            "schema": "rq2_public_grid_preloader_ack_vnext_execution_v6",
            "hello_sha256": contract.sha256_bytes(hello_raw),
            "status": "NON_ACCEPTED_PRELOADER_BOUNDARY",
            "scientific_loader_calls": 0,
            "solver_calls": 0,
            "accepted": False,
            "nonformal": True,
            "claim": False,
        }
        contract.require_exact(ack, expected_ack, label="preloader ACK")
        return {
            "status": ack["status"],
            "worker_pid": process.pid,
            "worker_exited": True,
            "hello_sha256": contract.sha256_bytes(hello_raw),
            "ack_sha256": contract.sha256_bytes(ack_raw),
            "scientific_loader_calls": 0,
            "solver_calls": 0,
            "result_writes": 0,
        }
    finally:
        _close_descriptors(controller_read, worker_ack_fd, worker_read_fd, controller_write)
        _stop_process(process)


def run_review_resource_probe_e2e() -> dict[str, Any]:
    """Prove that a fast real child cannot receive release before sample one."""
    config = contract.load_config()
    contract.verify_live_authorities()
    parent = {
        "pid": os.getpid(),
        "create_time_ns": contract.process_create_time_ns(os.getpid()),
    }
    values = list(_pipe_setup())
    controller_read, worker_ack_fd, worker_read_fd, controller_write, worker_read, worker_ack = values
    process: subprocess.Popen[Any] | None = None
    executor: concurrent.futures.ThreadPoolExecutor | None = None
    journal_directory = tempfile.TemporaryDirectory(prefix="rq2_v6_resource_probe_")
    persistence_path = Path(journal_directory.name) / "resource_journal.json"
    try:
        command = list(
            contract.exact_worker_command(
                mode="review-resource-probe",
                read_handle=worker_read,
                ack_handle=worker_ack,
                parent_pid=parent["pid"],
                parent_create_time_ns=parent["create_time_ns"],
                session_id="review-resource-probe",
                execution_index=0,
                block_id="review-resource-probe",
                predecessor_digest=None,
                nonce="review-resource-probe",
            )
        )
        try:
            process = _popen(
                command,
                worker_read,
                worker_ack,
                config["runtime"]["sanitized_environment"],
                capture_stderr=True,
            )
        finally:
            _clear_inheritance(worker_read, worker_ack, worker_read_fd, worker_ack_fd)
        worker_identity = {
            "pid": process.pid,
            "ppid": os.getpid(),
            "create_time_ns": contract.process_create_time_ns(process.pid),
        }
        os.close(worker_read_fd)
        worker_read_fd = -1
        os.close(worker_ack_fd)
        worker_ack_fd = -1
        state, executor, future, deadline = _start_resource_monitor(
            process, worker_identity, persistence_path
        )
        hello_raw, _hello = contract.read_frame(controller_read, "resource-probe HELLO")
        _wait_first_sample(state, deadline, future)
        release = {
            "schema": "rq2_public_grid_resource_probe_release_vnext_execution_v6",
            "hello_sha256": contract.sha256_bytes(hello_raw),
            "first_same_pair_resource_sample_succeeded_before_release": True,
            "nonformal": True,
            "claim": False,
        }
        release_raw = contract.write_frame(controller_write, release)
        release_sent_monotonic_ns = time.monotonic_ns()
        os.close(controller_write)
        controller_write = -1
        notice_raw, notice = contract.read_frame(
            controller_read, "resource-probe notice"
        )
        contract.require_eof(controller_read)
        process.wait(timeout=max(1.0, (deadline - time.monotonic_ns()) / 1e9))
        persisted = contract.validate_resource_monitor_outcome(
            future.result(timeout=30), expected_path=str(persistence_path)
        )
        journal = persisted["resource_journal"]
        executor.shutdown(wait=True)
        executor = None
        contract.validate_resource_journal(journal)
        if process.returncode != 0 or journal["status"] != "child_exited":
            raise contract.ContractRejected("resource-probe child outcome rejected")
        expected_notice = {
            "schema": "rq2_public_grid_resource_probe_notice_vnext_execution_v6",
            "hello_sha256": contract.sha256_bytes(hello_raw),
            "release_sha256": contract.sha256_bytes(release_raw),
            "status": "REVIEW_RESOURCE_PROBE_EXITING",
            "scientific_loader_calls": 0,
            "solver_calls": 0,
            "accepted": False,
            "nonformal": True,
            "claim": False,
        }
        contract.require_exact(notice, expected_notice, label="resource-probe notice")
        if release_sent_monotonic_ns < journal["first_sample_monotonic_ns"]:
            raise contract.ContractRejected("release preceded first resource sample")
        return {
            "status": notice["status"],
            "worker_pid": process.pid,
            "worker_exited": True,
            "release_sent_monotonic_ns": release_sent_monotonic_ns,
            "resource_journal": journal,
            "hello_sha256": contract.sha256_bytes(hello_raw),
            "notice_sha256": contract.sha256_bytes(notice_raw),
            "scientific_loader_calls": 0,
            "solver_calls": 0,
            "result_writes": 0,
        }
    finally:
        if executor is not None:
            executor.shutdown(wait=False, cancel_futures=True)
        _close_descriptors(controller_read, worker_ack_fd, worker_read_fd, controller_write)
        _stop_process(process)
        journal_directory.cleanup()


class _ReviewDeadlineClock:
    """Thread-safe deterministic audit clock; never used by production."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._now_ns = 1_000_000_000_000

    def monotonic_ns(self) -> int:
        with self._lock:
            return self._now_ns

    def wall_time_ns(self) -> int:
        return self.monotonic_ns() + 1_000_000_000_000

    def advance(self, nanoseconds: int) -> None:
        with self._lock:
            self._now_ns += nanoseconds

    def sleep(self, seconds: float) -> None:
        self.advance(round(seconds * 1_000_000_000))


def run_review_deadline_no_exit_probe_e2e(
    persistence_root: Path,
) -> dict[str, Any]:
    """Exercise the real controller path when a worker never sends exit_notice."""
    config = contract.load_config()
    contract.verify_live_authorities()
    persistence_path = persistence_root / "controller_resource_journal.json"
    if persistence_path.exists() or persistence_path.is_symlink():
        raise contract.ContractRejected("deadline-no-exit probe path must be absent")
    parent = {
        "pid": os.getpid(),
        "create_time_ns": contract.process_create_time_ns(os.getpid()),
    }
    values = list(_pipe_setup())
    controller_read, worker_ack_fd, worker_read_fd, controller_write, worker_read, worker_ack = values
    process: subprocess.Popen[Any] | None = None
    executor: concurrent.futures.ThreadPoolExecutor | None = None
    clock = _ReviewDeadlineClock()
    release = threading.Event()
    sample_count = 0

    def sample(pid: int, create_time_ns: int) -> tuple[int, int]:
        nonlocal sample_count
        observed = _sample_pair(pid, create_time_ns)
        sample_count += 1
        if sample_count == 2:
            if not release.wait(timeout=30):
                raise contract.ContractRejected(
                    "deadline-no-exit release synchronization failed"
                )
            clock.advance(contract.OBSERVATION_JITTER_BUDGET_NS + 1)
        return observed

    def terminate(target: subprocess.Popen[Any], **identity: int) -> dict[str, object]:
        result = _terminate_exact(target, **identity)
        clock.advance(contract.OWNED_TERMINATION_GRACE_NS)
        return result

    try:
        command = list(
            contract.exact_worker_command(
                mode="review-deadline-no-exit-probe",
                read_handle=worker_read,
                ack_handle=worker_ack,
                parent_pid=parent["pid"],
                parent_create_time_ns=parent["create_time_ns"],
                session_id="review-deadline-no-exit-probe",
                execution_index=0,
                block_id="review-deadline-no-exit-probe",
                predecessor_digest=None,
                nonce="review-deadline-no-exit-probe",
            )
        )
        try:
            process = _popen(
                command,
                worker_read,
                worker_ack,
                config["runtime"]["sanitized_environment"],
                capture_stderr=True,
            )
        finally:
            _clear_inheritance(worker_read, worker_ack, worker_read_fd, worker_ack_fd)
        worker_identity = {
            "pid": process.pid,
            "ppid": os.getpid(),
            "create_time_ns": contract.process_create_time_ns(process.pid),
        }
        os.close(worker_read_fd)
        worker_read_fd = -1
        os.close(worker_ack_fd)
        worker_ack_fd = -1
        state, executor, resource_future, deadline = _start_resource_monitor(
            process,
            worker_identity,
            persistence_path,
            sample=sample,
            monotonic_ns=clock.monotonic_ns,
            wall_time_ns=clock.wall_time_ns,
            sleep=clock.sleep,
            terminate=terminate,
        )
        hello_raw, _hello = contract.read_frame(
            controller_read, "deadline-no-exit probe HELLO"
        )
        _wait_first_sample(state, deadline, resource_future)
        envelope = {
            "schema": (
                "rq2_public_grid_deadline_no_exit_probe_envelope_"
                "vnext_execution_v6"
            ),
            "hello_sha256": contract.sha256_bytes(hello_raw),
            "first_same_pair_resource_sample_succeeded_before_release": True,
            "scientific_loader_calls": 0,
            "solver_calls": 0,
            "result_writes": 0,
            "nonformal": True,
            "claim": False,
        }
        contract.write_frame(controller_write, envelope)
        os.close(controller_write)
        controller_write = -1
        release.set()
        exit_raw, exit_notice, persisted = _await_exit_notice_and_monitor(
            controller_read=controller_read,
            process=process,
            resource_future=resource_future,
            deadline_ns=deadline,
            label="deadline-no-exit probe exit notice",
        )
        journal = persisted["resource_journal"]
        if (
            exit_raw is not None
            or exit_notice is not None
            or journal["status"] != "resource_sample_deadline_missed"
            or journal["honest_incomplete"] is not True
            or journal["mathematical_infeasibility_inferred"] is not False
            or persisted["readback_verified"] is not True
            or contract.read_stable(persistence_path)
            != contract.exact_json_bytes(journal)
        ):
            raise contract.ContractRejected(
                "deadline-no-exit integration outcome drifted"
            )
        executor.shutdown(wait=True)
        executor = None
        return {
            "classification": "HONEST_INCOMPLETE",
            "resource_journal": journal,
            "persisted_path": str(persistence_path),
            "persisted_sha256": persisted["persisted_sha256"],
            "readback_verified": True,
            "worker_exited": process.poll() is not None,
            "exit_notice_received": False,
            "scientific_loader_calls": 0,
            "solver_calls": 0,
            "result_writes": 0,
            "success_writes": 0,
        }
    finally:
        release.set()
        if executor is not None:
            executor.shutdown(wait=False, cancel_futures=True)
        _close_descriptors(controller_read, worker_ack_fd, worker_read_fd, controller_write)
        _stop_process(process)


def run_review_lease_acquire_probe(failure_point: str | None) -> dict[str, Any]:
    allowed = {
        None,
        "after_rename",
        "consumed_readback",
        "consumed_json",
        "consumed_schema",
        "consumed_derive",
        "consumed_public_mismatch",
        "unexpected_after_rename",
    }
    if failure_point not in allowed:
        raise contract.ContractRejected("review lease failure point unregistered")
    return run_two_block_nonformal(
        _review_lease_probe=True,
        _review_lease_failure=failure_point,
    )


def run_two_block_nonformal(
    *,
    _review_lease_probe: bool = False,
    _review_lease_failure: str | None = None,
) -> dict[str, Any]:
    """Execute one new evidence run only after the fixed V6 PASS receipt."""
    review_directory: tempfile.TemporaryDirectory[str] | None = None
    if _review_lease_probe:
        review_directory = tempfile.TemporaryDirectory(
            prefix="rq2_v6_lease_probe_"
        )
        review_root = Path(review_directory.name)
        fresh_lease = review_root / "test_private.lease.json"
        consumed_lease = review_root / "test_private.consumed.json"
        test_seed = bytearray(bytes.fromhex("a5" * 32))
        expected_public = contract.derive_lamport_public_key(bytes(test_seed))
        auth = {
            "key_id": expected_public["key_id"],
            "public_key_sha256": expected_public["public_key_sha256"],
        }
        test_lease = {
            "schema": "rq2_public_grid_vnext_execution_successor_v6_lamport_ots_private_lease",
            "version": 1,
            "state": "fresh",
            "key_id": auth["key_id"],
            "public_key_sha256": auth["public_key_sha256"],
            "seed_hex": bytes(test_seed).hex(),
            "one_time": True,
            "same_os_user_pre_execution_lease_exfiltration_out_of_scope": True,
            "security_certified": False,
        }
        fresh_lease.write_bytes(contract.exact_json_bytes(test_lease))
        for index in range(len(test_seed)):
            test_seed[index] = 0
        config: dict[str, Any] = {}
        authority_mapping: dict[str, str] = {}
        self_mapping: dict[str, str] = {}
        paths: dict[str, Path] = {}
        session_id = "review-lease-acquire-probe"
        session_secret = bytearray()
        session_root = review_root
        ledger = AttemptLedger()
        records: list[dict[str, Any]] = []
    else:
        contract.require_execution_review()
        config = contract.load_config()
        authority_mapping = contract.verify_live_authorities()
        self_mapping = contract.verify_self_bundle()
        paths = {
            key: contract.ROOT / value for key, value in config["paths"].items()
        }
        if any(path.exists() or path.is_symlink() for path in paths.values()):
            raise contract.ContractRejected(
                "canonical V6 execution roots must be clean absent"
            )
        resources = contract.resource_primitives()
        resources.preflight_available_commit()
        auth = config["controller_authentication"]
        expected_public = contract.load_public_key()
        fresh_lease = contract.ROOT / auth["private_lease_path"]
        consumed_lease = contract.ROOT / auth["consumed_private_lease_path"]
        if consumed_lease.exists() or consumed_lease.is_symlink():
            raise contract.ContractRejected("one-time V6 key was already consumed")
        session_id = secrets.token_hex(32)
        session_secret = bytearray(secrets.token_bytes(32))
        session_root = paths["worker_root"] / session_id
        session_root.mkdir(parents=True, exist_ok=False)
        ledger = AttemptLedger()
        records = []
    key_seed: bytearray | None = None
    key_tombstoned = False
    lease_consumed = False

    def tombstone_key(state: str = "consumed") -> None:
        nonlocal key_tombstoned, lease_consumed
        if key_tombstoned:
            return
        if fresh_lease.exists() or fresh_lease.is_symlink():
            os.replace(fresh_lease, consumed_lease)
            lease_consumed = True
        if not consumed_lease.is_file() or consumed_lease.is_symlink():
            raise contract.ContractRejected(
                "consumed lease unavailable for tombstone"
            )
        tombstone = {
            "schema": "rq2_public_grid_vnext_execution_successor_v6_lamport_ots_consumed_tombstone",
            "version": 1,
            "state": state,
            "key_id": auth["key_id"],
            "public_key_sha256": auth["public_key_sha256"],
            "seed_present": False,
            "one_time_key_reusable": False,
            "same_os_user_pre_execution_lease_exfiltration_out_of_scope": True,
            "security_certified": False,
        }
        temporary = consumed_lease.with_name(
            f".{consumed_lease.name}.tombstone.{os.getpid()}"
        )
        try:
            with temporary.open("xb") as stream:
                stream.write(contract.exact_json_bytes(tombstone))
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, consumed_lease)
        finally:
            if temporary.exists():
                temporary.unlink()
        if (
            fresh_lease.exists()
            or contract.read_stable(consumed_lease)
            != contract.exact_json_bytes(tombstone)
        ):
            raise contract.ContractRejected(
                "consumed lease tombstone readback failed"
            )
        key_tombstoned = True

    def acquire_private_lease() -> bytearray:
        """Only this gated controller closure may materialize the production seed."""
        nonlocal lease_consumed
        seed: bytearray | None = None
        consumed_seed: bytearray | None = None
        acquired = False
        raw = b""
        readback = b""
        value: dict[str, Any] = {}
        consumed_value: dict[str, Any] = {}
        try:
            if (
                not fresh_lease.is_file()
                or fresh_lease.is_symlink()
                or consumed_lease.exists()
                or consumed_lease.is_symlink()
            ):
                raise contract.ContractRejected(
                    "fresh one-time private lease unavailable"
                )
            raw = contract.read_stable(fresh_lease)
            try:
                value = json.loads(raw)
                seed = bytearray.fromhex(value["seed_hex"])
            except (json.JSONDecodeError, KeyError, ValueError) as exc:
                raise contract.ContractRejected("private lease malformed") from exc
            if (
                set(value) != contract.PRIVATE_LEASE_KEYS
                or value.get("schema")
                != "rq2_public_grid_vnext_execution_successor_v6_lamport_ots_private_lease"
                or value.get("version") != 1
                or value.get("state") != "fresh"
                or value.get("key_id") != expected_public["key_id"]
                or value.get("public_key_sha256")
                != expected_public["public_key_sha256"]
                or value.get("one_time") is not True
                or value.get(
                    "same_os_user_pre_execution_lease_exfiltration_out_of_scope"
                )
                is not True
                or value.get("security_certified") is not False
                or len(seed) != 32
                or contract.derive_lamport_public_key(bytes(seed))
                != {
                    "key_id": expected_public["key_id"],
                    "public_key_sha256": expected_public["public_key_sha256"],
                }
            ):
                raise contract.ContractRejected(
                    "private lease/public anchor mismatch"
                )
            os.replace(fresh_lease, consumed_lease)
            lease_consumed = True
            if _review_lease_failure == "after_rename":
                raise contract.ContractRejected("injected after rename")
            if _review_lease_failure == "unexpected_after_rename":
                raise RuntimeError("injected unexpected failure after rename")
            if _review_lease_failure == "consumed_readback":
                raise contract.ContractRejected("injected consumed readback failure")
            readback = contract.read_stable(consumed_lease)
            if _review_lease_failure == "consumed_json":
                raise contract.ContractRejected("injected consumed JSON failure")
            try:
                consumed_value = json.loads(readback)
                consumed_seed = bytearray.fromhex(consumed_value["seed_hex"])
            except (json.JSONDecodeError, KeyError, ValueError) as exc:
                raise contract.ContractRejected(
                    "consumed private lease malformed"
                ) from exc
            if _review_lease_failure == "consumed_schema":
                raise contract.ContractRejected("injected consumed schema failure")
            if set(consumed_value) != contract.PRIVATE_LEASE_KEYS:
                raise contract.ContractRejected("consumed private lease schema drifted")
            if _review_lease_failure == "consumed_derive":
                raise contract.ContractRejected("injected consumed derive failure")
            derived = contract.derive_lamport_public_key(bytes(consumed_seed))
            if _review_lease_failure == "consumed_public_mismatch":
                raise contract.ContractRejected(
                    "injected consumed public mismatch"
                )
            if (
                fresh_lease.exists()
                or readback != raw
                or consumed_value != value
                or derived
                != {
                    "key_id": expected_public["key_id"],
                    "public_key_sha256": expected_public["public_key_sha256"],
                }
            ):
                raise contract.ContractRejected(
                    "private lease atomic consume readback failed"
                )
            acquired = True
            return seed
        finally:
            raw = b""
            readback = b""
            value = {}
            consumed_value = {}
            if consumed_seed is not None:
                for index in range(len(consumed_seed)):
                    consumed_seed[index] = 0
            if not acquired:
                if seed is not None:
                    for index in range(len(seed)):
                        seed[index] = 0
                tombstone_key("acquire_failed")

    if _review_lease_probe:
        failure_observed = False
        signature_verified = False
        probe_seed: bytearray | None = None
        try:
            probe_seed = acquire_private_lease()
            if _review_lease_failure is not None:
                raise contract.ContractRejected(
                    "registered review failure point was not exercised"
                )
            digest = contract.sha256_bytes(b"rq2-v6-review-lease-probe")
            signature = contract.lamport_sign_digest(bytes(probe_seed), digest)
            contract.verify_lamport_signature(
                digest, signature, expected_public
            )
            signature_verified = True
        except Exception:
            if _review_lease_failure is None:
                raise
            failure_observed = True
        finally:
            if probe_seed is not None:
                tombstone_key()
                for index in range(len(probe_seed)):
                    probe_seed[index] = 0
        tombstone = json.loads(contract.read_stable(consumed_lease))
        outcome = {
            "failure_injected": failure_observed,
            "signature_verified": signature_verified,
            "fresh_raw_seed_present": fresh_lease.exists(),
            "consumed_raw_seed_present": "seed_hex" in tombstone,
            "tombstone_present": consumed_lease.is_file(),
            "tombstone_seed_present": tombstone.get("seed_present"),
            "lease_consumed_flag": lease_consumed,
            "returned_seed": False,
            "scientific_loader_calls": 0,
            "solver_calls": 0,
            "result_writes": 0,
            "security_certified": False,
        }
        if review_directory is not None:
            review_directory.cleanup()
        return outcome

    def sign_hmac(value: object) -> str:
        return hmac.new(
            bytes(session_secret), contract.exact_json_bytes(value), "sha256"
        ).hexdigest()

    def verify_record(record: dict[str, Any]) -> None:
        body = {
            key: value
            for key, value in record.items()
            if key not in {"record_digest", "controller_hmac"}
        }
        digest = contract.sha256_bytes(contract.exact_json_bytes(body))
        if (
            record.get("schema")
            != "rq2_public_grid_accepted_evidence_vnext_execution_v6"
            or record.get("record_digest") != digest
            or not hmac.compare_digest(
                record.get("controller_hmac", ""),
                sign_hmac({"body": body, "record_digest": digest}),
            )
            or record.get("live_authority_mapping") != authority_mapping
            or record.get("self_bundle_mapping") != self_mapping
            or record.get("nonformal") is not True
            or record.get("claim") is not False
            or record.get("security_certified") is not False
        ):
            raise contract.ContractRejected("accepted evidence HMAC/authority rejected")
        raw_names = (
            "hello",
            "envelope",
            "exit_notice",
            "result",
            "attempt_receipt",
            "ack",
        )
        parsed: dict[str, dict[str, Any]] = {}
        for name in raw_names:
            raw = bytes.fromhex(record[f"{name}_hex"])
            if contract.sha256_bytes(raw) != record[f"{name}_sha256"]:
                raise contract.ContractRejected(f"{name} raw hash drifted")
            parsed[name] = json.loads(raw)
            if parsed[name] != record[name]:
                raise contract.ContractRejected(f"{name} raw/parsed drifted")
        hello = parsed["hello"]
        envelope = parsed["envelope"]
        result = parsed["result"]
        notice = parsed["exit_notice"]
        receipt = parsed["attempt_receipt"]
        ack = parsed["ack"]
        expected_hello = contract.build_worker_hello(
            mode="science",
            session_id=record["session_id"],
            execution_index=record["execution_index"],
            block_id=record["block_id"],
            predecessor_digest=record["predecessor_digest"],
            nonce=record["nonce"],
            parent_identity=record["parent_identity"],
            worker_identity=record["worker_identity"],
            command=tuple(record["command"]),
            worker_read=record["pipe_authority"]["worker_read"],
            worker_ack=record["pipe_authority"]["worker_ack"],
        )
        contract.require_exact(hello, expected_hello, label="accepted HELLO")
        expected_envelope = contract.build_worker_envelope(
            hello=hello,
            hello_raw=bytes.fromhex(record["hello_hex"]),
            pipe_authority=record["pipe_authority"],
            attempt_root=str(Path(record["result_path"]).parent),
        )
        contract.require_exact(envelope, expected_envelope, label="accepted envelope")
        contract.validate_solver_runtime_evidence(
            result["solver_runtime_evidence"],
            worker_identity=record["worker_identity"],
        )
        validated, accounting = contract.validate_actual_science_payload(
            result["scientific_payload"], record["block_id"]
        )
        expected_result = contract.build_worker_result(
            hello=hello,
            hello_raw=bytes.fromhex(record["hello_hex"]),
            envelope=envelope,
            envelope_raw=bytes.fromhex(record["envelope_hex"]),
            scientific_payload=validated,
            solver_call_accounting=accounting,
            solver_runtime_evidence=result["solver_runtime_evidence"],
        )
        contract.require_exact(result, expected_result, label="accepted result")
        expected_notice = contract.build_worker_exit_notice(
            hello=hello,
            envelope=envelope,
            result=result,
            result_raw=bytes.fromhex(record["result_hex"]),
            result_path=record["result_path"],
        )
        contract.require_exact(notice, expected_notice, label="accepted exit notice")
        journal = contract.validate_resource_journal(record["resource_journal"])
        expected_receipt = contract.build_attempt_receipt(
            hello=hello,
            envelope=envelope,
            result=result,
            result_raw=bytes.fromhex(record["result_hex"]),
            exit_notice=notice,
            exit_notice_raw=bytes.fromhex(record["exit_notice_hex"]),
            result_path=record["result_path"],
            resource_journal=journal,
        )
        contract.require_exact(receipt, expected_receipt, label="accepted receipt")
        expected_ack = contract.build_controller_ack(
            hello=hello,
            envelope=envelope,
            result=result,
            result_raw=bytes.fromhex(record["result_hex"]),
            exit_notice_raw=bytes.fromhex(record["exit_notice_hex"]),
            receipt=receipt,
            receipt_raw=bytes.fromhex(record["attempt_receipt_hex"]),
            resource_journal=journal,
        )
        contract.require_exact(ack, expected_ack, label="accepted ACK")
        if (
            journal["status"] != "child_exited"
            or journal["sample_count"] < 1
            or record["resource_journal_sha256"]
            != contract.sha256_bytes(contract.exact_json_bytes(journal))
            or record["solver_runtime_evidence"]
            != result["solver_runtime_evidence"]
            or record["solver_runtime_evidence_sha256"]
            != result["solver_runtime_evidence_sha256"]
            or result["accepted_as_nonformal_result"] is not True
            or ack["accepted_as_nonformal_result"] is not True
        ):
            raise contract.ContractRejected("accepted resource/science evidence rejected")
        contract.verify_live_authorities()

    def dispatch(index: int) -> None:
        predecessor_digest = ledger.consume(index)
        accepted_digest: str | None = None
        block_id = contract.BLOCKS[index - 1]
        nonce = secrets.token_hex(32)
        attempt_root = session_root / block_id / nonce
        parent = {
            "pid": os.getpid(),
            "create_time_ns": contract.process_create_time_ns(os.getpid()),
        }
        values = list(_pipe_setup())
        controller_read, worker_ack_fd, worker_read_fd, controller_write, worker_read, worker_ack = values
        process: subprocess.Popen[Any] | None = None
        executor: concurrent.futures.ThreadPoolExecutor | None = None
        try:
            command = list(
                contract.exact_worker_command(
                    mode="science",
                    read_handle=worker_read,
                    ack_handle=worker_ack,
                    parent_pid=parent["pid"],
                    parent_create_time_ns=parent["create_time_ns"],
                    session_id=session_id,
                    execution_index=index,
                    block_id=block_id,
                    predecessor_digest=predecessor_digest,
                    nonce=nonce,
                )
            )
            try:
                contract.verify_live_authorities()
                process = _popen(
                    command,
                    worker_read,
                    worker_ack,
                    config["runtime"]["sanitized_environment"],
                )
            finally:
                _clear_inheritance(worker_read, worker_ack, worker_read_fd, worker_ack_fd)
            worker_identity = {
                "pid": process.pid,
                "ppid": os.getpid(),
                "create_time_ns": contract.process_create_time_ns(process.pid),
            }
            os.close(worker_read_fd)
            worker_read_fd = -1
            os.close(worker_ack_fd)
            worker_ack_fd = -1
            state, executor, resource_future, deadline = _start_resource_monitor(
                process,
                worker_identity,
                attempt_root / "controller_resource_journal.json",
            )
            hello_raw, hello = contract.read_frame(controller_read, "science HELLO")
            _wait_first_sample(state, deadline, resource_future)
            worker_read_observed = {
                "raw_identifier": worker_read,
                "type": "anonymous_pipe",
                "role": "controller_to_worker",
                "direction": "read",
                "inherited": True,
            }
            worker_ack_observed = {
                "raw_identifier": worker_ack,
                "type": "anonymous_pipe",
                "role": "worker_to_controller",
                "direction": "write",
                "inherited": True,
            }
            expected_hello = contract.build_worker_hello(
                mode="science",
                session_id=session_id,
                execution_index=index,
                block_id=block_id,
                predecessor_digest=predecessor_digest,
                nonce=nonce,
                parent_identity=parent,
                worker_identity=worker_identity,
                command=tuple(command),
                worker_read=worker_read_observed,
                worker_ack=worker_ack_observed,
            )
            contract.require_exact(hello, expected_hello, label="science HELLO")
            pipe_authority = {
                "worker_read": worker_read_observed,
                "worker_ack": worker_ack_observed,
                "controller_write": contract.observe_pipe_endpoint(
                    _child_raw(controller_write),
                    role="controller_to_worker",
                    direction="write",
                    inherited=False,
                ),
                "controller_read": contract.observe_pipe_endpoint(
                    _child_raw(controller_read),
                    role="worker_to_controller",
                    direction="read",
                    inherited=False,
                ),
            }
            envelope = contract.build_worker_envelope(
                hello=hello,
                hello_raw=hello_raw,
                pipe_authority=pipe_authority,
                attempt_root=str(attempt_root),
            )
            envelope_raw = contract.write_frame(controller_write, envelope)
            os.close(controller_write)
            controller_write = -1
            exit_notice_raw, exit_notice, persisted = _await_exit_notice_and_monitor(
                controller_read=controller_read,
                process=process,
                resource_future=resource_future,
                deadline_ns=deadline,
                label="science exit notice",
            )
            resource_journal = persisted["resource_journal"]
            executor.shutdown(wait=True)
            executor = None
            if (
                process.returncode != 0
                or resource_journal["status"] != "child_exited"
                or resource_journal["sample_count"] < 1
            ):
                raise HonestIncomplete(
                    f"science child/resource incomplete: {resource_journal['status']}"
                )
            if exit_notice_raw is None or exit_notice is None:
                raise HonestIncomplete("science exit notice absent")
            result_path = attempt_root / "worker_result.json"
            result_raw = contract.read_stable(result_path)
            result = json.loads(result_raw)
            runtime = contract.validate_solver_runtime_evidence(
                result["solver_runtime_evidence"], worker_identity=worker_identity
            )
            validated, accounting = contract.validate_actual_science_payload(
                result["scientific_payload"], block_id
            )
            expected_result = contract.build_worker_result(
                hello=hello,
                hello_raw=hello_raw,
                envelope=envelope,
                envelope_raw=envelope_raw,
                scientific_payload=validated,
                solver_call_accounting=accounting,
                solver_runtime_evidence=runtime,
            )
            contract.require_exact(result, expected_result, label="science result")
            expected_notice = contract.build_worker_exit_notice(
                hello=hello,
                envelope=envelope,
                result=result,
                result_raw=result_raw,
                result_path=str(result_path),
            )
            contract.require_exact(
                exit_notice, expected_notice, label="science exit notice"
            )
            receipt = contract.build_attempt_receipt(
                hello=hello,
                envelope=envelope,
                result=result,
                result_raw=result_raw,
                exit_notice=exit_notice,
                exit_notice_raw=exit_notice_raw,
                result_path=str(result_path),
                resource_journal=resource_journal,
            )
            receipt_raw = contract.exact_json_bytes(receipt)
            receipt_path = attempt_root / "attempt_receipt.json"
            publisher.atomic_write(receipt_path, receipt_raw)
            ack = contract.build_controller_ack(
                hello=hello,
                envelope=envelope,
                result=result,
                result_raw=result_raw,
                exit_notice_raw=exit_notice_raw,
                receipt=receipt,
                receipt_raw=receipt_raw,
                resource_journal=resource_journal,
            )
            ack_raw = contract.exact_json_bytes(ack)
            ack_path = attempt_root / "controller_ack.json"
            publisher.atomic_write(ack_path, ack_raw)
            contract.verify_live_authorities()
            scientific_raw = contract.exact_json_bytes(result["scientific_payload"])
            resource_raw = contract.exact_json_bytes(resource_journal)
            runtime_raw = contract.exact_json_bytes(runtime)
            body = {
                "schema": "rq2_public_grid_accepted_evidence_vnext_execution_v6",
                "session_id": session_id,
                "execution_index": index,
                "block_id": block_id,
                "predecessor_digest": predecessor_digest,
                "nonce": nonce,
                "parent_identity": parent,
                "worker_identity": worker_identity,
                "command": command,
                "cwd": str(contract.ROOT),
                "environment": config["runtime"]["sanitized_environment"],
                "self_bundle_mapping": self_mapping,
                "self_bundle_mapping_sha256": contract.closure_mapping_sha256(self_mapping),
                "live_authority_mapping": authority_mapping,
                "live_authority_mapping_sha256": contract.closure_mapping_sha256(authority_mapping),
                "pipe_authority": pipe_authority,
                "pipe_authority_digest": envelope["pipe_authority_digest"],
                "hello_hex": hello_raw.hex(),
                "hello": hello,
                "hello_sha256": contract.sha256_bytes(hello_raw),
                "envelope_hex": envelope_raw.hex(),
                "envelope": envelope,
                "envelope_sha256": contract.sha256_bytes(envelope_raw),
                "exit_notice_hex": exit_notice_raw.hex(),
                "exit_notice": exit_notice,
                "exit_notice_sha256": contract.sha256_bytes(exit_notice_raw),
                "result_path": str(result_path),
                "result_hex": result_raw.hex(),
                "result": result,
                "result_sha256": contract.sha256_bytes(result_raw),
                "attempt_receipt_path": str(receipt_path),
                "attempt_receipt_hex": receipt_raw.hex(),
                "attempt_receipt": receipt,
                "attempt_receipt_sha256": contract.sha256_bytes(receipt_raw),
                "ack_path": str(ack_path),
                "ack_hex": ack_raw.hex(),
                "ack": ack,
                "ack_sha256": contract.sha256_bytes(ack_raw),
                "scientific_hex": scientific_raw.hex(),
                "scientific_payload_sha256": result["scientific_payload_sha256"],
                "solver_call_accounting_sha256": result["solver_call_accounting_sha256"],
                "solver_runtime_evidence": runtime,
                "solver_runtime_evidence_hex": runtime_raw.hex(),
                "solver_runtime_evidence_sha256": result["solver_runtime_evidence_sha256"],
                "resource_journal": resource_journal,
                "resource_journal_hex": resource_raw.hex(),
                "resource_journal_sha256": contract.sha256_bytes(resource_raw),
                "resource_outcome_status": resource_journal["status"],
                "resource_outcome_reason": resource_journal["reason"],
                "resource_honest_incomplete": resource_journal["honest_incomplete"],
                "maximum_private_commit_bytes": resource_journal["maximum_private_commit_bytes"],
                "minimum_system_commit_available_bytes": resource_journal["minimum_system_commit_available_bytes"],
                "resource_sample_count": resource_journal["sample_count"],
                "nonformal": True,
                "claim": False,
                "mathematical_infeasibility_inferred_from_failure": False,
                "same_os_user_pre_execution_lease_exfiltration_out_of_scope": True,
                "security_certified": False,
            }
            digest = contract.sha256_bytes(contract.exact_json_bytes(body))
            record = {
                **body,
                "record_digest": digest,
                "controller_hmac": sign_hmac(
                    {"body": body, "record_digest": digest}
                ),
            }
            verify_record(record)
            if index == 2 and predecessor_digest != records[0]["record_digest"]:
                raise contract.ContractRejected("0009 predecessor evidence drifted")
            records.append(record)
            accepted_digest = digest
            if index == 1:
                predecessor_file = session_root / "accepted_0008.json"
                publisher.atomic_write(
                    predecessor_file, contract.exact_json_bytes(record)
                )
                if json.loads(contract.read_stable(predecessor_file)) != record:
                    raise contract.ContractRejected(
                        "0008 predecessor commit readback drifted"
                    )
        finally:
            ledger.finish(index, accepted_digest)
            if executor is not None:
                executor.shutdown(wait=False, cancel_futures=True)
            _close_descriptors(
                controller_read, worker_ack_fd, worker_read_fd, controller_write
            )
            _stop_process(process)

    def publish(seed: bytearray) -> dict[str, Any]:
        if len(records) != 2 or [item["block_id"] for item in records] != list(contract.BLOCKS):
            raise contract.ContractRejected("publication requires exact 0008/0009 ledger")
        for record in records:
            verify_record(record)
        if contract.verify_live_authorities() != authority_mapping:
            raise contract.ContractRejected("pre-publication authority drifted")
        resource_journals = {
            record["block_id"]: record["resource_journal"] for record in records
        }
        runtime_evidence = {
            record["block_id"]: record["solver_runtime_evidence"]
            for record in records
        }
        science_hashes = {
            record["block_id"]: record["scientific_payload_sha256"]
            for record in records
        }
        accounting_hashes = {
            record["block_id"]: record["solver_call_accounting_sha256"]
            for record in records
        }
        resource_hashes = {
            block: contract.sha256_bytes(contract.exact_json_bytes(journal))
            for block, journal in resource_journals.items()
        }
        runtime_hashes = {
            block: contract.sha256_bytes(contract.exact_json_bytes(evidence))
            for block, evidence in runtime_evidence.items()
        }
        receipt_body = {
            "schema": "rq2_public_grid_controller_receipt_vnext_execution_v6",
            "session_id": session_id,
            "record_digests": [record["record_digest"] for record in records],
            "ledger_sha256": contract.sha256_bytes(contract.exact_json_bytes(records)),
            "scientific_payload_sha256s": science_hashes,
            "solver_call_accounting_sha256s": accounting_hashes,
            "resource_journal_sha256s": resource_hashes,
            "solver_runtime_evidence_sha256s": runtime_hashes,
            "resource_journals": resource_journals,
            "solver_runtime_evidence": runtime_evidence,
            "self_bundle_mapping_sha256": contract.closure_mapping_sha256(self_mapping),
            "live_authority_mapping_sha256": contract.closure_mapping_sha256(authority_mapping),
            "same_os_user_pre_execution_lease_exfiltration_out_of_scope": True,
            "nonformal": True,
            "claim": False,
            "security_certified": False,
        }
        controller_receipt = {
            **receipt_body,
            "controller_hmac": sign_hmac(receipt_body),
        }
        summary = {
            "schema": "rq2_public_grid_nonformal_two_block_summary_vnext_execution_v6",
            "blocks": list(contract.BLOCKS),
            "record_count": 2,
            "scientific_payload_sha256s": science_hashes,
            "solver_call_accounting_sha256s": accounting_hashes,
            "resource_journal_sha256s": resource_hashes,
            "solver_runtime_evidence_sha256s": runtime_hashes,
            "resource_journals": resource_journals,
            "solver_runtime_evidence": runtime_evidence,
            "nonformal": True,
            "claim": False,
            "mathematical_infeasibility_inferred_from_failure": False,
            "security_certified": False,
        }
        result_manifest_core = {
            "schema": "rq2_public_grid_result_manifest_substantive_core_vnext_execution_v6",
            "session_id": session_id,
            "controller_receipt_sha256": contract.sha256_bytes(contract.exact_json_bytes(controller_receipt)),
            "record_digests": [record["record_digest"] for record in records],
            "scientific_payload_sha256s": science_hashes,
            "solver_call_accounting_sha256s": accounting_hashes,
            "resource_journal_sha256s": resource_hashes,
            "solver_runtime_evidence_sha256s": runtime_hashes,
            "resource_journals": resource_journals,
            "solver_runtime_evidence": runtime_evidence,
            "public_key": contract.load_public_key(),
            "same_os_user_pre_execution_lease_exfiltration_out_of_scope": True,
            "nonformal": True,
            "claim": False,
            "security_certified": False,
        }
        success_core = {
            "schema": "rq2_public_grid_success_readback_substantive_core_vnext_execution_v6",
            "session_id": session_id,
            "classification": "committed_success",
            "published": True,
            "controller_receipt_sha256": result_manifest_core["controller_receipt_sha256"],
            "scientific_payload_sha256s": science_hashes,
            "solver_call_accounting_sha256s": accounting_hashes,
            "resource_journal_sha256s": resource_hashes,
            "solver_runtime_evidence_sha256s": runtime_hashes,
            "resource_journals": resource_journals,
            "solver_runtime_evidence": runtime_evidence,
            "public_key": contract.load_public_key(),
            "same_os_user_pre_execution_lease_exfiltration_out_of_scope": True,
            "nonformal": True,
            "formal": False,
            "claim": False,
            "security_certified": False,
        }
        entries: dict[str, bytes] = {
            "controller_receipt.json": contract.exact_json_bytes(controller_receipt),
            "summary.json": contract.exact_json_bytes(summary),
            "closure_mapping.json": contract.exact_json_bytes(authority_mapping),
        }
        for record in records:
            base = f"workers/{record['block_id']}"
            entries.update(
                {
                    f"{base}/accepted_evidence.json": contract.exact_json_bytes(record),
                    f"{base}/hello.json": bytes.fromhex(record["hello_hex"]),
                    f"{base}/envelope.json": bytes.fromhex(record["envelope_hex"]),
                    f"{base}/exit_notice.json": bytes.fromhex(record["exit_notice_hex"]),
                    f"{base}/worker_result.json": bytes.fromhex(record["result_hex"]),
                    f"{base}/attempt_receipt.json": bytes.fromhex(record["attempt_receipt_hex"]),
                    f"{base}/ack.json": bytes.fromhex(record["ack_hex"]),
                    f"{base}/scientific_payload.json": bytes.fromhex(record["scientific_hex"]),
                    f"{base}/resource_journal.json": bytes.fromhex(record["resource_journal_hex"]),
                    f"{base}/solver_runtime_evidence.json": bytes.fromhex(record["solver_runtime_evidence_hex"]),
                }
            )
        payload = contract.build_attestation_payload(
            session_id=session_id,
            entries=entries,
            resource_journals=resource_journals,
            runtime_evidence=runtime_evidence,
            result_manifest_core=result_manifest_core,
            success_core=success_core,
            closure_mapping=authority_mapping,
        )
        attestation = contract.build_attestation(payload, seed)
        contract.verify_attestation(attestation)
        tombstone_key()
        result_manifest = {
            "schema": "rq2_public_grid_result_manifest_vnext_execution_v6",
            "substantive_core": result_manifest_core,
            "controller_attestation_payload_sha256": attestation["payload_sha256"],
            "controller_signature_sha256": attestation["signature_sha256"],
            "public_key": contract.load_public_key(),
            "nonformal": True,
            "claim": False,
            "security_certified": False,
        }
        success_value = {
            "schema": "rq2_public_grid_success_commit_vnext_execution_v6",
            "substantive_core": success_core,
            "controller_attestation_payload_sha256": attestation["payload_sha256"],
            "controller_signature_sha256": attestation["signature_sha256"],
            "public_key": contract.load_public_key(),
            "nonformal": True,
            "formal": False,
            "claim": False,
            "security_certified": False,
        }
        entries["controller_attestation.json"] = contract.exact_json_bytes(attestation)
        entries["result_manifest.json"] = contract.exact_json_bytes(result_manifest)
        result = paths["result_root"]
        success = paths["success_root"]
        terminal = paths["terminal_root"]
        staging = result.with_name(f".{result.name}.staging.{session_id}")
        success_staging = success.with_name(f".{success.name}.staging.{session_id}")
        appeared_result = False
        appeared_success = False

        def exact_result(root: Path) -> bool:
            try:
                if json.loads(contract.read_stable(root / "SHA256SUMS.json")) != publisher.typed_tree(root):
                    return False
                for relative, raw in entries.items():
                    if contract.read_stable(root / relative) != raw:
                        return False
                checked = contract.verify_attestation(
                    json.loads(contract.read_stable(root / "controller_attestation.json"))
                )
                for relative, identity in checked["payload"]["substantive_byte_mapping"].items():
                    raw = contract.read_stable(root / relative)
                    if identity != contract.substantive_entry(raw):
                        return False
                return True
            except Exception:  # noqa: BLE001 - publication verification fails closed
                return False

        def exact_success(root: Path) -> bool:
            try:
                return (
                    json.loads(contract.read_stable(root / "SHA256SUMS.json"))
                    == publisher.typed_tree(root)
                    and contract.read_stable(root / "success.json")
                    == contract.exact_json_bytes(success_value)
                )
            except Exception:  # noqa: BLE001
                return False

        try:
            initial = publisher.capture_presence(
                publisher.PublicationPaths(result, success, terminal)
            )
            if publisher.classify_publication(initial, result_exact=False, success_exact=False) != "honest_incomplete":
                raise contract.ContractRejected("initial publication presence rejected")
            staging.mkdir(parents=True, exist_ok=False)
            for relative, raw in entries.items():
                destination = staging / relative
                destination.parent.mkdir(parents=True, exist_ok=True)
                publisher.atomic_write(destination, raw)
            publisher.atomic_write(
                staging / "SHA256SUMS.json",
                contract.exact_json_bytes(publisher.typed_tree(staging)),
            )
            if not exact_result(staging):
                raise contract.ContractRejected("staged result exact readback rejected")
            if contract.verify_live_authorities() != authority_mapping:
                raise contract.ContractRejected("pre-result closure drifted")
            os.replace(staging, result)
            appeared_result = True
            if not exact_result(result):
                raise contract.ContractRejected("committed result readback rejected")
            if contract.verify_live_authorities() != authority_mapping:
                raise contract.ContractRejected("post-result closure drifted")
            success_staging.mkdir(parents=True, exist_ok=False)
            publisher.atomic_write(
                success_staging / "success.json",
                contract.exact_json_bytes(success_value),
            )
            publisher.atomic_write(
                success_staging / "SHA256SUMS.json",
                contract.exact_json_bytes(publisher.typed_tree(success_staging)),
            )
            if not exact_success(success_staging):
                raise contract.ContractRejected("staged success readback rejected")
            if contract.verify_live_authorities() != authority_mapping:
                raise contract.ContractRejected("pre-success closure drifted")
            os.replace(success_staging, success)
            appeared_success = True
            if contract.verify_live_authorities() != authority_mapping:
                raise contract.ContractRejected("post-success closure drifted")
            final = publisher.capture_presence(
                publisher.PublicationPaths(result, success, terminal)
            )
            classification = publisher.classify_publication(
                final,
                result_exact=exact_result(result),
                success_exact=exact_success(success),
            )
            if classification != "committed_success":
                raise contract.ContractRejected("final publication readback rejected")
            independent_readback = contract.verify_published_artifacts(
                result, success
            )
            if independent_readback.get("classification") != "committed_success":
                raise contract.ContractRejected(
                    "independent post-rename readback rejected"
                )
            return {
                "classification": classification,
                "published": True,
                "claim": False,
                "formal": False,
                "security_certified": False,
            }
        except Exception:
            if appeared_result or appeared_success:
                return {
                    "classification": "commit_indeterminate",
                    "published": False,
                    "claim": False,
                    "formal": False,
                    "security_certified": False,
                }
            for path in (staging, success_staging):
                if path.exists():
                    shutil.rmtree(path)
            raise

    try:
        key_seed = acquire_private_lease()
        dispatch(1)
        dispatch(2)
        return publish(key_seed)
    except HonestIncomplete as exc:
        return {
            "classification": "honest_incomplete",
            "published": False,
            "claim": False,
            "formal": False,
            "security_certified": False,
            "mathematical_infeasibility_inferred": False,
            "reason": str(exc),
        }
    finally:
        if key_seed is not None:
            if not key_tombstoned and consumed_lease.exists():
                tombstone_key()
            for index in range(len(key_seed)):
                key_seed[index] = 0
        for index in range(len(session_secret)):
            session_secret[index] = 0


def validate_only() -> dict[str, Any]:
    config = contract.load_config()
    mapping = contract.verify_live_authorities()
    self_mapping = contract.verify_self_bundle()
    auth = config["controller_authentication"]
    fresh = contract.ROOT / auth["private_lease_path"]
    consumed = contract.ROOT / auth["consumed_private_lease_path"]
    return {
        "validation_passed": True,
        "status": config["status"],
        "live_authority_inventory_count": len(mapping),
        "live_authority_mapping_sha256": contract.closure_mapping_sha256(mapping),
        "self_bundle_inventory_count": len(self_mapping),
        "self_bundle_mapping_sha256": contract.closure_mapping_sha256(self_mapping),
        "execution_review_present": contract.REVIEW.exists(),
        "private_lease_fresh_present": fresh.is_file() and not fresh.is_symlink(),
        "private_lease_consumed_present": consumed.exists() or consumed.is_symlink(),
        "public_key": contract.load_public_key(),
        "same_os_user_pre_execution_lease_exfiltration_out_of_scope": True,
        "execution_ready": False,
        "worker_processes_started": 0,
        "scientific_loader_calls": 0,
        "solver_calls": 0,
        "result_writes": 0,
        "pilot_executed": False,
        "formal_execution_ready": False,
        "claim": False,
        "security_certified": False,
    }


def main(argv: list[str] | None = None) -> int:
    arguments = list([] if argv is None else argv)
    if arguments == ["--validate-only"]:
        print(json.dumps(validate_only(), sort_keys=True))
        return 0
    if arguments == ["--execute"]:
        contract.require_execution_review()
        print(json.dumps(run_two_block_nonformal(), sort_keys=True))
        return 0
    raise contract.ContractRejected(
        "only --validate-only or gated --execute is registered"
    )


if __name__ == "__main__":
    raise SystemExit(main(__import__("sys").argv[1:]))
