from __future__ import annotations

import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path

import pytest
import yaml

from src.evaluation.repository_paths import (
    canonical_repository_relative_path,
)


ROOT = Path(__file__).resolve().parents[1]
HANDOFF = ROOT / "configs/rq2_public_executor_handoff_v2.yaml"
BUNDLE = ROOT / "configs/rq2_public_executor_bundle_v2.SHA256SUMS.json"
OUTER = ROOT / "configs/rq2_public_executor_bundle_v2.OUTER.SHA256SUMS.json"
OLD_HASHES = {
    "configs/rq2_public_data_robust_identification_preregistration_v6.yaml": (
        "ef25deabfcd51fbd667e48dcddcfbe4b19a2115c6d4bc40b0fc556b5c1f332f2"
    ),
    "configs/rq2_public_data_robust_identification_preregistration_v6.SHA256SUMS.json": (
        "07bb735df3cc5ad547c7d4741c5f69929b39a37df9b65c3c2ae004e74b08cdcf"
    ),
    "configs/rq2_public_executor_bundle_v1.SHA256SUMS.json": (
        "49613e3e400a31ee4888490c5939c4985efaaed3f13325baa1c4bbc28b319f04"
    ),
    "tests/test_rq2_public_data_preregistration_v6.py": (
        "f7a8ad71712c2ec731119ce02649c1c1dc2379f190d40238aed001da610edc47"
    ),
}
FORBIDDEN_COMMANDS = {
    "activate-grid",
    "grid",
    "resume-grid",
    "activate-pairwise",
    "pairwise",
    "resume-pairwise",
    "activate-identification",
    "identification",
    "package-results",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_canonical_repository_paths_are_platform_independent():
    assert canonical_repository_relative_path(
        Path("configs") / "rq2.yaml"
    ) == "configs/rq2.yaml"
    assert canonical_repository_relative_path(
        r"configs\rq2.yaml"
    ) == "configs/rq2.yaml"
    with pytest.raises(ValueError, match="relative"):
        canonical_repository_relative_path(r"D:\repo\rq2.yaml")
    with pytest.raises(ValueError, match="traversal"):
        canonical_repository_relative_path("configs/../rq2.yaml")


def test_frozen_v6_predecessor_bytes_are_unchanged():
    assert {
        name: _sha256(ROOT / name) for name in OLD_HASHES
    } == OLD_HASHES


def test_windows_successor_outer_and_bundle_are_live_and_preserve_v1_inventory():
    handoff = yaml.safe_load(HANDOFF.read_text(encoding="utf-8"))
    bundle = json.loads(BUNDLE.read_text(encoding="utf-8"))
    outer = json.loads(OUTER.read_text(encoding="utf-8"))
    predecessor = json.loads(
        (
            ROOT
            / "configs/rq2_public_executor_bundle_v1.SHA256SUMS.json"
        ).read_text(encoding="utf-8")
    )
    assert handoff["schema"] == "rq2_public_executor_windows_successor_v2"
    assert handoff["predecessor"]["immutable"] is True
    assert handoff["gates"] == {
        "pilot_executed": False,
        "cross_solver_confirmation_completed": False,
        "grid_need_dispatch_ready": False,
        "pairwise_replay_ready": False,
        "identification_ready": False,
        "formal_execution_ready": False,
        "formal_result_exists": False,
        "security_certified": False,
    }
    assert outer == {
        "files": {
            "configs/rq2_public_executor_bundle_v2.SHA256SUMS.json": (
                _sha256(BUNDLE)
            )
        },
        "schema": "rq2_public_executor_outer_manifest_v2",
    }
    assert handoff["authority_chain"]["outer_manifest_path"] == (
        "configs/rq2_public_executor_bundle_v2.OUTER.SHA256SUMS.json"
    )
    assert handoff["authority_chain"]["bundle_path"] == (
        "configs/rq2_public_executor_bundle_v2.SHA256SUMS.json"
    )
    assert handoff["authority_chain"]["handoff_records_outer_hash"] is False
    assert bundle["schema"] == "rq2_public_executor_bundle_manifest_v2"
    for name, expected in predecessor["files"].items():
        assert bundle["files"].get(name) == expected
    assert bundle["files"][
        "configs/rq2_public_executor_bundle_v1.SHA256SUMS.json"
    ] == OLD_HASHES["configs/rq2_public_executor_bundle_v1.SHA256SUMS.json"]
    for name, expected in bundle["files"].items():
        assert canonical_repository_relative_path(name) == name
        path = ROOT / name
        assert path.is_file() and not path.is_symlink()
        assert _sha256(path) == expected
    path_contract = handoff["path_contract"]
    assert _sha256(ROOT / path_contract["canonicalizer_path"]) == (
        path_contract["canonicalizer_sha256"]
    )
    entry = handoff["run_tag_entry"]
    assert _sha256(ROOT / entry["entrypoint_path"]) == (
        entry["entrypoint_sha256"]
    )


def test_default_config_stays_smoke_and_pilot_contract_is_whitelisted():
    default = yaml.safe_load(
        (ROOT / "configs/experiment.yaml").read_text(encoding="utf-8")
    )
    handoff = yaml.safe_load(HANDOFF.read_text(encoding="utf-8"))
    entry = handoff["run_tag_entry"]
    assert default["experiment"]["kind"] == "pytest-smoke"
    assert entry["kind"] == "rq2-public-pilot"
    assert entry["command_sequence"] == [
        "verify",
        "preflight",
        "pilot",
        "package-pilot",
    ]
    assert set(entry["forbidden_commands"]) == FORBIDDEN_COMMANDS
    assert entry["timeout_default_seconds"] >= 21600
    assert entry["timeout_minimum_seconds"] >= 21600
    assert entry["smoke_timeout_is_inherited"] is False


def test_h2_temporal_predecessor_is_preserved_by_entry_only_successor():
    from experiments.validate_rq2_h2_temporal_executor_entry_successor_v2 import (
        validate,
    )

    successor = yaml.safe_load(
        (
            ROOT
            / "configs/rq2_h2_temporal_executor_entry_successor_v2.yaml"
        ).read_text(encoding="utf-8")
    )
    predecessor = successor["predecessor"]
    assert _sha256(ROOT / predecessor["preregistration_path"]) == (
        predecessor["preregistration_sha256"]
    )
    assert _sha256(ROOT / predecessor["manifest_path"]) == (
        predecessor["manifest_sha256"]
    )
    manifest = json.loads(
        (ROOT / predecessor["manifest_path"]).read_text(encoding="utf-8")
    )
    successor_manifest = json.loads(
        (ROOT / successor["successor"]["manifest_path"]).read_text(
            encoding="utf-8"
        )
    )
    for name, expected in manifest.items():
        if name == "scripts/run_experiment.ps1":
            assert expected == predecessor["frozen_executor_sha256"]
            continue
        assert _sha256(ROOT / name) == expected
        assert successor_manifest[name] == expected
    amendment = successor["successor"]
    assert _sha256(ROOT / amendment["executor_path"]) == (
        amendment["executor_sha256"]
    )
    assert amendment["scientific_design_changed"] is False
    assert amendment["thresholds_changed"] is False
    assert amendment["seeds_changed"] is False
    assert amendment["sample_sizes_changed"] is False
    assert amendment["model_or_solver_semantics_changed"] is False
    assert successor_manifest[amendment["executor_path"]] == amendment[
        "executor_sha256"
    ]
    assert successor_manifest[amendment["validator_path"]] == amendment[
        "validator_sha256"
    ]
    assert successor_manifest[
        "configs/rq2_h2_temporal_executor_entry_successor_v2.yaml"
    ] == _sha256(
        ROOT / "configs/rq2_h2_temporal_executor_entry_successor_v2.yaml"
    )
    report = validate()
    assert report["job_count"] == 17
    assert report["confirmatory_cell_count"] == 24
    assert report["primary_cell_count"] == 6
    assert report["predecessor_scientific_validation_replayed"] is True
    assert report["executor_entry_successor_validated"] is True
    assert report["validation_passed"] is True
    assert successor["gates"]["formal_execution_ready"] is False
    assert successor["gates"]["solver_invoked"] is False


FAKE_EXECUTOR = r'''from __future__ import annotations
import hashlib
import json
import os
import sys
import time
from pathlib import Path

root = Path.cwd()
command = sys.argv[1]
mode = os.environ.get("FAKE_RQ2_MODE")
with (root / "invocations.txt").open("a", encoding="utf-8") as stream:
    stream.write(command + "\n")

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def write_package(relative: str, members: dict[str, object]) -> None:
    target = root / relative
    target.mkdir(parents=True, exist_ok=False)
    for name, payload in members.items():
        (target / name).write_text(
            json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8"
        )
    manifest = {name: digest(target / name) for name in sorted(members)}
    (target / "SHA256SUMS.json").write_text(
        json.dumps(manifest, sort_keys=True) + "\n", encoding="utf-8"
    )

if mode in {"timeout", "timeout-unconfirmed"} and command == "verify":
    (root / "child_pid.txt").write_text(str(os.getpid()), encoding="utf-8")
    time.sleep(2 if mode == "timeout-unconfirmed" else 60)

if mode == "complete" or mode == "missing-stderr" or mode.startswith("receipt-"):
    if command == "preflight":
        write_package(
            "results/tables/rq2_public_executor_preflight_v1",
            {"config.yaml": {"schema": "fake"}, "preflight.json": {"passed": True}},
        )
    elif command == "pilot":
        write_package(
            "results/tables/rq2_public_solver_pilot_v1",
            {
                "comparison.json": {"passed": True},
                "config.yaml": {"schema": "fake"},
                "runs.json": {"runs": []},
                "summary.json": {"gurobi_eligible_for_formal_successor": True},
            },
        )
    elif command == "package-pilot":
        transfer = root / "results/transfer"
        transfer.mkdir(parents=True, exist_ok=False)
        files = {}
        for package in (
            root / "results/tables/rq2_public_executor_preflight_v1",
            root / "results/tables/rq2_public_solver_pilot_v1",
        ):
            for path in sorted(package.iterdir()):
                files[path.relative_to(root).as_posix()] = digest(path)
        manifest_path = transfer / "rq2_public_successor_v1_pilot.json"
        manifest_path.write_text(
            json.dumps(
                {
                    "schema": "rq2_public_executor_return_package_v1",
                    "scope": "pilot",
                    "files": files,
                    "formal_result_claimed": False,
                    "security_certified": False,
                },
                sort_keys=True,
            ) + "\n",
            encoding="utf-8",
        )
        archive = transfer / "rq2_public_successor_v1_pilot.tar.gz"
        archive.write_bytes(b"synthetic archive for runner contract test\n")
        archive_receipt = str(archive.relative_to(root))
        manifest_receipt = str(manifest_path.relative_to(root))
        if mode == "receipt-absolute":
            archive_receipt = str(archive.resolve())
        elif mode == "receipt-traversal":
            manifest_receipt = str(
                Path("results/transfer/../transfer") / manifest_path.name
            )
        elif mode == "receipt-drive-relative":
            archive_receipt = "C:" + archive_receipt
        elif mode == "receipt-unc":
            archive_receipt = r"\\server\share\rq2_public_successor_v1_pilot.tar.gz"
        elif mode == "receipt-rooted":
            archive_receipt = os.sep + archive_receipt
        elif mode == "receipt-dot":
            archive_receipt = (
                "results" + os.sep + "." + os.sep + "transfer" + os.sep
                + archive.name
            )
        elif mode == "receipt-duplicate":
            archive_receipt = (
                "results" + os.sep + os.sep + "transfer" + os.sep
                + archive.name
            )
        elif mode == "receipt-case":
            archive_receipt = "Results" + archive_receipt[len("results"):]
        if mode == "missing-stderr":
            (
                Path(os.environ["RUN_DIR"])
                / "rq2-public-pilot-logs/verify.stderr.log"
            ).unlink()
        print(json.dumps({
            "schema": "rq2_public_executor_return_package_v1",
            "scope": "pilot",
            "formal_result_claimed": False,
            "security_certified": False,
            "archive": archive_receipt,
            "archive_sha256": digest(archive),
            "manifest": manifest_receipt,
            "manifest_sha256": digest(manifest_path),
        }))
        raise SystemExit(0)
print(json.dumps({"command": command, "synthetic": True}))
'''


def _runner_sandbox(
    tmp_path: Path,
    *,
    mode: str,
    pilot_timeout_seconds: int | None = None,
    force_unconfirmed: bool = False,
) -> tuple[Path, dict[str, str]]:
    for name in ("scripts", "configs"):
        (tmp_path / name).mkdir()
    shutil.copyfile(
        ROOT / "scripts/run_experiment.ps1",
        tmp_path / "scripts/run_experiment.ps1",
    )
    if pilot_timeout_seconds is not None or force_unconfirmed:
        runner_path = tmp_path / "scripts/run_experiment.ps1"
        runner = runner_path.read_text(encoding="utf-8-sig")
        if pilot_timeout_seconds is not None:
            runner = runner.replace(
                "$rq2PilotTimeoutSeconds = 21600",
                f"$rq2PilotTimeoutSeconds = {pilot_timeout_seconds}",
                1,
            ).replace(
                "$parsed -ge 21600",
                f"$parsed -ge {pilot_timeout_seconds}",
                1,
            )
        if force_unconfirmed:
            kill_marker = "$Process.Kill()"
            grace_marker = (
                "Stop-ChildProcessAndConfirm -Process $proc "
                "-GraceMilliseconds 5000"
            )
            assert runner.count(kill_marker) == 1
            assert runner.count(grace_marker) == 1
            runner = runner.replace(
                kill_marker,
                'throw "synthetic kill failure"',
                1,
            ).replace(
                grace_marker,
                "Stop-ChildProcessAndConfirm -Process $proc "
                "-GraceMilliseconds 100",
                1,
            )
        runner_path.write_text(runner, encoding="utf-8-sig")
    (tmp_path / "scripts/rq2_public_executor.py").write_text(
        FAKE_EXECUTOR, encoding="utf-8"
    )
    (tmp_path / "configs/experiment.yaml").write_text(
        "experiment:\n  id: synthetic\n  kind: rq2-public-pilot\n",
        encoding="utf-8",
    )
    inventory = {
        name: _sha256(tmp_path / name)
        for name in (
            "scripts/rq2_public_executor.py",
            "scripts/run_experiment.ps1",
        )
    }
    bundle_path = (
        tmp_path / "configs/rq2_public_executor_bundle_v2.SHA256SUMS.json"
    )
    bundle_path.write_text(
        json.dumps(
            {
                "schema": "rq2_public_executor_bundle_manifest_v2",
                "files": inventory,
            },
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    (
        tmp_path
        / "configs/rq2_public_executor_bundle_v2.OUTER.SHA256SUMS.json"
    ).write_text(
        json.dumps(
            {
                "schema": "rq2_public_executor_outer_manifest_v2",
                "files": {
                    "configs/rq2_public_executor_bundle_v2.SHA256SUMS.json": (
                        _sha256(bundle_path)
                    )
                },
            },
            sort_keys=True,
        ) + "\n",
        encoding="utf-8",
    )
    environment = os.environ.copy()
    environment.update(
        {
            "RUN_ID": "run-contract-test",
            "RUN_TAG": "run-contract-test",
            "RUN_COMMIT": "1" * 40,
            "RUN_DIR": str(tmp_path / "run"),
            "RUN_ARTIFACT_DIR": str(tmp_path / "artifacts"),
            "RQ2_EXECUTOR_PYTHON_EXE": str(Path(sys.executable).resolve()),
            "SMOKE_TIMEOUT_SECONDS": "1",
            "FAKE_RQ2_MODE": mode,
        }
    )
    environment.pop("RQ2_PILOT_TIMEOUT_SECONDS", None)
    if pilot_timeout_seconds is not None:
        environment["RQ2_PILOT_TIMEOUT_SECONDS"] = str(pilot_timeout_seconds)
    return tmp_path, environment


def _windows_process_exists(pid: int) -> bool:
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-Command",
            (
                f"if (Get-Process -Id {pid} -ErrorAction SilentlyContinue) "
                "{ exit 0 } else { exit 1 }"
            ),
        ],
        capture_output=True,
        check=False,
    )
    return completed.returncode == 0


def _assert_child_is_stopped(pid: int) -> None:
    try:
        for _ in range(20):
            if not _windows_process_exists(pid):
                return
            time.sleep(0.1)
        assert not _windows_process_exists(pid), f"child process remains: {pid}"
    finally:
        if _windows_process_exists(pid):
            subprocess.run(
                ["taskkill.exe", "/PID", str(pid), "/T", "/F"],
                capture_output=True,
                check=False,
            )


@pytest.mark.skipif(sys.platform != "win32", reason="Windows runner contract")
def test_pilot_kind_runs_only_whitelist_in_order_and_copies_complete_tree(
    tmp_path,
):
    sandbox, environment = _runner_sandbox(tmp_path, mode="complete")
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "scripts/run_experiment.ps1",
        ],
        cwd=sandbox,
        env=environment,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 0, (completed.stdout or "") + (
        completed.stderr or ""
    )
    invocations = (sandbox / "invocations.txt").read_text(
        encoding="utf-8"
    ).splitlines()
    assert invocations == ["verify", "preflight", "pilot", "package-pilot"]
    assert set(invocations).isdisjoint(FORBIDDEN_COMMANDS)
    receipt = json.loads(
        (
            sandbox
            / "run/rq2-public-pilot-logs/package-pilot.stdout.json"
        ).read_text(encoding="utf-8")
    )
    assert receipt["archive"] == str(
        Path("results/transfer/rq2_public_successor_v1_pilot.tar.gz")
    )
    assert "\\" in receipt["archive"]
    metrics = json.loads(
        (sandbox / "run/metrics.json").read_text(encoding="utf-8-sig")
    )
    assert metrics["artifact_complete"] is True
    assert metrics["timeout_seconds"] == 21600
    assert metrics["timeout_environment_variable"] == (
        "RQ2_PILOT_TIMEOUT_SECONDS"
    )
    assert metrics["formal_execution_ready"] is False
    artifacts = sandbox / "artifacts/rq2_public_pilot"
    assert (artifacts / "preflight/SHA256SUMS.json").is_file()
    assert (artifacts / "pilot/SHA256SUMS.json").is_file()
    assert (
        artifacts / "transfer/rq2_public_successor_v1_pilot.tar.gz"
    ).is_file()
    assert (
        artifacts / "transfer/rq2_public_successor_v1_pilot.json"
    ).is_file()
    for command in invocations:
        for suffix in ("stdout.json", "stderr.log"):
            assert (artifacts / f"logs/{command}.{suffix}").is_file()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows runner contract")
@pytest.mark.parametrize(
    "mode",
    [
        "receipt-absolute",
        "receipt-traversal",
        "receipt-drive-relative",
        "receipt-unc",
        "receipt-rooted",
        "receipt-dot",
        "receipt-duplicate",
        "receipt-case",
    ],
)
def test_pilot_receipt_rejects_unsafe_paths_fail_closed(tmp_path, mode):
    sandbox, environment = _runner_sandbox(tmp_path, mode=mode)
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "scripts/run_experiment.ps1",
        ],
        cwd=sandbox,
        env=environment,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 1
    assert (sandbox / "invocations.txt").read_text(
        encoding="utf-8"
    ).splitlines() == ["verify", "preflight", "pilot", "package-pilot"]
    status = json.loads(
        (sandbox / "run/status.json").read_text(encoding="utf-8-sig")
    )
    metrics = json.loads(
        (sandbox / "run/metrics.json").read_text(encoding="utf-8-sig")
    )
    assert status["status"] == "failed"
    assert "receipt" in status["error"]
    assert metrics["artifact_complete"] is False
    assert metrics["formal_execution_ready"] is False


@pytest.mark.skipif(sys.platform != "win32", reason="Windows runner contract")
def test_successful_children_with_missing_stderr_log_fail_closed(tmp_path):
    sandbox, environment = _runner_sandbox(tmp_path, mode="missing-stderr")
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "scripts/run_experiment.ps1",
        ],
        cwd=sandbox,
        env=environment,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 1
    assert (sandbox / "invocations.txt").read_text(
        encoding="utf-8"
    ).splitlines() == ["verify", "preflight", "pilot", "package-pilot"]
    metrics = json.loads(
        (sandbox / "run/metrics.json").read_text(encoding="utf-8-sig")
    )
    assert metrics["artifact_complete"] is False
    assert not (sandbox / "artifacts/rq2_public_pilot/preflight").exists()
    assert not (sandbox / "artifacts/rq2_public_pilot/pilot").exists()
    assert not (sandbox / "artifacts/rq2_public_pilot/transfer").exists()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows runner contract")
@pytest.mark.parametrize(
    ("force_unconfirmed", "expected_status", "expected_exit"),
    [(False, "timeout", 124), (True, "failed", 125)],
)
def test_pilot_timeout_terminates_child_and_blocks_success_artifacts(
    tmp_path,
    force_unconfirmed,
    expected_status,
    expected_exit,
):
    sandbox, environment = _runner_sandbox(
        tmp_path,
        mode="timeout-unconfirmed" if force_unconfirmed else "timeout",
        pilot_timeout_seconds=1,
        force_unconfirmed=force_unconfirmed,
    )
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "scripts/run_experiment.ps1",
        ],
        cwd=sandbox,
        env=environment,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=30,
        check=False,
    )
    assert completed.returncode == expected_exit
    pid = int((sandbox / "child_pid.txt").read_text(encoding="utf-8"))
    _assert_child_is_stopped(pid)
    status = json.loads(
        (sandbox / "run/status.json").read_text(encoding="utf-8-sig")
    )
    metrics = json.loads(
        (sandbox / "run/metrics.json").read_text(encoding="utf-8-sig")
    )
    assert status["status"] == expected_status
    assert metrics["termination_confirmed"] is (not force_unconfirmed)
    assert metrics["timeout_stage"] == "verify"
    assert metrics["completed_command_sequence"] == []
    assert metrics["artifact_complete"] is False
    assert metrics["timeout_is_infeasibility_evidence"] is False
    if force_unconfirmed:
        assert "termination_unconfirmed" in status["error"]
    artifacts = sandbox / "artifacts/rq2_public_pilot"
    if not force_unconfirmed:
        assert (artifacts / "logs/verify.stdout.json").is_file()
        assert (artifacts / "logs/verify.stderr.log").is_file()
    assert not (artifacts / "preflight").exists()
    assert not (artifacts / "pilot").exists()
    assert not (artifacts / "transfer").exists()


@pytest.mark.skipif(sys.platform != "win32", reason="Windows runner contract")
def test_successful_children_without_complete_pilot_artifacts_fail_closed(
    tmp_path,
):
    sandbox, environment = _runner_sandbox(tmp_path, mode="missing")
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "scripts/run_experiment.ps1",
        ],
        cwd=sandbox,
        env=environment,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 1
    status = json.loads(
        (sandbox / "run/status.json").read_text(encoding="utf-8-sig")
    )
    metrics = json.loads(
        (sandbox / "run/metrics.json").read_text(encoding="utf-8-sig")
    )
    assert status["status"] == "failed"
    assert metrics["artifact_complete"] is False
    assert "工件不完整" in status["error"]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows runner contract")
def test_pilot_rejects_smoke_sized_timeout_before_any_command(tmp_path):
    sandbox, environment = _runner_sandbox(tmp_path, mode="complete")
    environment["RQ2_PILOT_TIMEOUT_SECONDS"] = "7200"
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "scripts/run_experiment.ps1",
        ],
        cwd=sandbox,
        env=environment,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 1
    assert not (sandbox / "invocations.txt").exists()
    status = json.loads(
        (sandbox / "run/status.json").read_text(encoding="utf-8-sig")
    )
    assert "RQ2_PILOT_TIMEOUT_SECONDS" in status["error"]
    assert "21600" in status["error"]


@pytest.mark.skipif(sys.platform != "win32", reason="Windows runner contract")
@pytest.mark.parametrize("executor_python", [None, "python.exe"])
def test_pilot_requires_explicit_absolute_executor_python(
    tmp_path,
    executor_python,
):
    sandbox, environment = _runner_sandbox(tmp_path, mode="complete")
    if executor_python is None:
        environment.pop("RQ2_EXECUTOR_PYTHON_EXE")
    else:
        environment["RQ2_EXECUTOR_PYTHON_EXE"] = executor_python
    completed = subprocess.run(
        [
            "powershell.exe",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            "scripts/run_experiment.ps1",
        ],
        cwd=sandbox,
        env=environment,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        timeout=60,
        check=False,
    )
    assert completed.returncode == 1
    assert not (sandbox / "invocations.txt").exists()
    status = json.loads(
        (sandbox / "run/status.json").read_text(encoding="utf-8-sig")
    )
    assert "RQ2_EXECUTOR_PYTHON_EXE" in status["error"]
