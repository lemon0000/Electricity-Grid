from __future__ import annotations

import json
import multiprocessing
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

import pytest

from src.solvers import execution_lease as lease_module
from src.solvers.execution_lease import (
    ExecutionLease,
    ExecutionLeaseOwnershipError,
    ExecutionLeaseUnavailable,
    ParentProcessWatchdog,
    probe_process,
)

NOW = datetime(2026, 7, 19, 8, 0, tzinfo=timezone.utc)


def _json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _spawned_acquirer(
    root: str,
    start: multiprocessing.synchronize.Event,
    release: multiprocessing.synchronize.Event,
    results: multiprocessing.queues.Queue,
) -> None:
    if not start.wait(timeout=15.0):
        results.put(("error", os.getpid(), "start timeout"))
        return
    try:
        acquired = ExecutionLease.acquire(
            Path(root),
            stage="candidate",
            attempt_id=f"worker-{os.getpid()}",
        )
    except ExecutionLeaseUnavailable:
        results.put(("unavailable", os.getpid(), None))
        return
    except BaseException as error:
        results.put(("error", os.getpid(), repr(error)))
        return
    results.put(("acquired", os.getpid(), None))
    release.wait(timeout=15.0)
    acquired.release()


def test_context_manager_persists_active_identity_and_released_history(
    tmp_path: Path,
) -> None:
    with ExecutionLease.acquire(
        tmp_path,
        stage="candidate",
        attempt_id="formal-1",
        pid=4321,
        hostname="HOST-A",
        now=lambda: NOW,
    ) as acquired:
        active = _json(tmp_path / "active" / "lease.json")
        assert active == acquired.active_payload
        assert active["schema"] == "execution_lease_v1"
        assert active["pid"] == 4321
        assert active["hostname"] == "HOST-A"
        assert active["stage"] == "candidate"
        assert active["attempt_id"] == "formal-1"
        assert active["started_utc"] == NOW.isoformat()

    assert not (tmp_path / "active").exists()
    assert acquired.history_path is not None
    assert _json(acquired.history_path / "lease.json") == active
    terminal = _json(acquired.history_path / "terminal.json")
    assert terminal["status"] == "released"
    assert terminal["ended_utc"] == NOW.isoformat()
    assert terminal["error_type"] is None
    assert acquired.release() == acquired.history_path


def test_context_manager_archives_exception_terminal(tmp_path: Path) -> None:
    acquired: ExecutionLease | None = None

    with pytest.raises(ValueError, match="simulated failure"):
        with ExecutionLease.acquire(
            tmp_path,
            stage="joint_ac",
            attempt_id="joint-1",
            pid=4321,
            hostname="host-a",
            now=lambda: NOW,
        ) as acquired:
            raise ValueError("simulated failure")

    assert acquired is not None
    assert not (tmp_path / "active").exists()
    assert acquired.history_path is not None
    terminal = _json(acquired.history_path / "terminal.json")
    assert terminal["status"] == "failed"
    assert terminal["error_type"] == "ValueError"
    assert terminal["error_message"] == "simulated failure"


@pytest.mark.parametrize(
    ("probe", "message"),
    (
        (lambda _pid: True, "still running"),
        (lambda _pid: None, "cannot be determined"),
    ),
)
def test_live_or_unknown_same_host_lease_fails_closed(
    tmp_path: Path,
    probe: lease_module.ProcessProbe,
    message: str,
) -> None:
    owner = ExecutionLease.acquire(
        tmp_path,
        stage="candidate",
        attempt_id="owner",
        pid=111,
        hostname="host-a",
        now=lambda: NOW,
    )
    before = (tmp_path / "active" / "lease.json").read_bytes()

    with pytest.raises(ExecutionLeaseUnavailable, match=message):
        ExecutionLease.acquire(
            tmp_path,
            stage="candidate",
            attempt_id="contender",
            pid=222,
            hostname="HOST-A",
            process_probe=probe,
            now=lambda: NOW,
        )

    assert (tmp_path / "active" / "lease.json").read_bytes() == before
    assert not tuple((tmp_path / "history").iterdir())
    owner.release()


def test_process_probe_error_fails_closed(tmp_path: Path) -> None:
    owner = ExecutionLease.acquire(
        tmp_path,
        stage="candidate",
        attempt_id="owner",
        pid=111,
        hostname="host-a",
        now=lambda: NOW,
    )

    def failed_probe(_pid: int) -> bool | None:
        raise PermissionError("access denied")

    with pytest.raises(ExecutionLeaseUnavailable, match="cannot be determined"):
        ExecutionLease.acquire(
            tmp_path,
            stage="candidate",
            attempt_id="contender",
            pid=222,
            hostname="host-a",
            process_probe=failed_probe,
            now=lambda: NOW,
        )

    assert _json(tmp_path / "active" / "lease.json") == owner.active_payload
    owner.release()


def test_foreign_host_fails_closed_without_probing_pid(tmp_path: Path) -> None:
    owner = ExecutionLease.acquire(
        tmp_path,
        stage="candidate",
        attempt_id="owner",
        pid=111,
        hostname="host-a",
        now=lambda: NOW,
    )

    def forbidden_probe(_pid: int) -> bool | None:
        pytest.fail("foreign-host PID must not be probed")

    with pytest.raises(ExecutionLeaseUnavailable, match="another host"):
        ExecutionLease.acquire(
            tmp_path,
            stage="candidate",
            attempt_id="contender",
            pid=222,
            hostname="host-b",
            process_probe=forbidden_probe,
            now=lambda: NOW,
        )

    assert _json(tmp_path / "active" / "lease.json") == owner.active_payload
    owner.release()


def test_dead_same_host_owner_is_archived_before_takeover(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = ExecutionLease.acquire(
        tmp_path,
        stage="candidate",
        attempt_id="owner",
        pid=111,
        hostname="host-a",
        now=lambda: NOW,
    )
    original_retire = lease_module._retire_stale_active
    evidence_seen = False

    def checked_retire(root: Path, observed: dict[str, object]) -> None:
        nonlocal evidence_seen
        evidence = root / "history" / f"{observed['lease_id']}.stale_takeover"
        evidence_seen = evidence.is_dir()
        original_retire(root, observed)

    monkeypatch.setattr(lease_module, "_retire_stale_active", checked_retire)
    successor = ExecutionLease.acquire(
        tmp_path,
        stage="candidate",
        attempt_id="successor",
        pid=222,
        hostname="HOST-A",
        process_probe=lambda pid: False if pid == 111 else True,
        now=lambda: NOW,
    )

    assert evidence_seen
    stale = tmp_path / "history" / f"{owner.active_payload['lease_id']}.stale_takeover"
    assert _json(stale / "lease.json") == owner.active_payload
    terminal = _json(stale / "terminal.json")
    assert terminal["status"] == "stale_takeover"
    assert terminal["liveness"] == "not_running"
    assert terminal["detected_by_lease_id"] == successor.active_payload["lease_id"]
    assert _json(tmp_path / "active" / "lease.json") == successor.active_payload
    with pytest.raises(ExecutionLeaseOwnershipError, match="ownership drifted"):
        owner.release()
    successor.release()


def test_malformed_active_lease_fails_closed(tmp_path: Path) -> None:
    active = tmp_path / "active"
    active.mkdir(parents=True)
    (active / "lease.json").write_text("{not-json", encoding="utf-8")

    with pytest.raises(ExecutionLeaseUnavailable, match="identified safely"):
        ExecutionLease.acquire(
            tmp_path,
            stage="candidate",
            attempt_id="contender",
            process_probe=lambda _pid: False,
        )

    assert (active / "lease.json").read_text(encoding="utf-8") == "{not-json"
    assert not tuple((tmp_path / "history").iterdir())


def test_unknown_active_inventory_fails_closed(tmp_path: Path) -> None:
    owner = ExecutionLease.acquire(
        tmp_path,
        stage="candidate",
        attempt_id="owner",
        pid=111,
        hostname="host-a",
        now=lambda: NOW,
    )
    (tmp_path / "active" / "terminal.json").write_text("{}", encoding="utf-8")

    with pytest.raises(ExecutionLeaseUnavailable, match="identified safely"):
        ExecutionLease.acquire(
            tmp_path,
            stage="candidate",
            attempt_id="contender",
            pid=222,
            hostname="host-a",
            process_probe=lambda _pid: False,
            now=lambda: NOW,
        )

    assert _json(tmp_path / "active" / "lease.json") == owner.active_payload
    assert (tmp_path / "active" / "terminal.json").is_file()
    assert not tuple((tmp_path / "history").iterdir())


def test_release_refuses_ownership_drift(tmp_path: Path) -> None:
    acquired = ExecutionLease.acquire(
        tmp_path,
        stage="candidate",
        attempt_id="owner",
        pid=111,
        hostname="host-a",
        now=lambda: NOW,
    )
    path = tmp_path / "active" / "lease.json"
    drifted = _json(path)
    drifted["attempt_id"] = "different"
    path.write_text(json.dumps(drifted), encoding="utf-8")

    with pytest.raises(ExecutionLeaseOwnershipError, match="ownership drifted"):
        acquired.release()

    assert (tmp_path / "active").is_dir()
    assert not tuple((tmp_path / "history").iterdir())


def test_atomic_acquire_allows_only_one_spawned_process(tmp_path: Path) -> None:
    context = multiprocessing.get_context("spawn")
    start = context.Event()
    release = context.Event()
    results = context.Queue()
    processes = [
        context.Process(
            target=_spawned_acquirer,
            args=(str(tmp_path), start, release, results),
        )
        for _ in range(2)
    ]
    for process in processes:
        process.start()
    start.set()
    observed = [results.get(timeout=20.0) for _ in processes]
    release.set()
    for process in processes:
        process.join(timeout=20.0)

    assert [item[0] for item in observed].count("acquired") == 1
    assert [item[0] for item in observed].count("unavailable") == 1
    assert all(process.exitcode == 0 for process in processes)
    assert not (tmp_path / "active").exists()
    assert len(tuple((tmp_path / "history").glob("*.released"))) == 1


def test_default_probe_recognizes_current_process() -> None:
    assert probe_process(os.getpid()) is True


@pytest.mark.parametrize(
    ("lost_state", "expected_exit_code"),
    ((False, 70), (None, 71)),
)
def test_parent_watchdog_exits_when_parent_is_lost_or_unknown(
    lost_state: bool | None,
    expected_exit_code: int,
) -> None:
    states = iter((True, lost_state))
    observed_exit_codes: list[int] = []
    exit_observed = threading.Event()

    def record_exit(code: int) -> None:
        observed_exit_codes.append(code)
        exit_observed.set()

    with ParentProcessWatchdog(
        4321,
        interval_seconds=0.01,
        process_probe=lambda _pid: next(states, lost_state),
        exit_process=record_exit,
    ):
        assert exit_observed.wait(timeout=1.0)

    assert observed_exit_codes == [expected_exit_code]


@pytest.mark.parametrize("pid", [True, 0, -1, 1.5])
def test_process_probe_rejects_nonpositive_or_noninteger_pid(pid: object) -> None:
    with pytest.raises(ValueError, match="positive integer"):
        probe_process(pid)  # type: ignore[arg-type]
