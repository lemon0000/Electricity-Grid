"""Focused bootstrap tests for the closed v7 execution successor."""

from __future__ import annotations

import ast
import copy
import json
import os
from pathlib import Path

import pytest

from experiments import (
    bootstrap_rq2_public_grid_two_block_pilot_execution_successor_v1 as bootstrap,
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
            *contract["exact_argv_suffix"],
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


def _roots() -> dict[str, bool]:
    formal = CONFIG["formal_invariants"]
    paths = [*CONFIG["fresh_roots"], *formal["protected_roots_clean_absent"]]
    return dict.fromkeys(paths, False)


def test_successor_bootstrap_is_standard_library_only() -> None:
    assert bootstrap.PROJECT_IMPORTS_PERMITTED is False
    tree = ast.parse((ROOT / bootstrap.SELF_REL).read_text(encoding="utf-8"))
    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
    assert not imported_roots.intersection({"src", "experiments", "pyomo", "pandas"})


def test_sealed_static_authority_is_live_and_execution_closed() -> None:
    config = bootstrap._verify_static_authority()
    assert config["status"] == "execution_successor_candidate_closed"
    assert config["gates"]["successor_independent_review_passed"] is False
    assert config["gates"]["successor_execution_ready"] is False
    assert config["gates"]["formal_execution_ready"] is False


def test_v7_or_successor_hash_drift_fails_closed(monkeypatch: pytest.MonkeyPatch) -> None:
    real_sha = bootstrap._sha256

    def drift(path: Path) -> str:
        if path == ROOT / bootstrap.V7_OUTER_REL:
            return "0" * 64
        return real_sha(path)

    monkeypatch.setattr(bootstrap, "_sha256", drift)
    with pytest.raises(bootstrap.BootstrapRejected, match="hash drift"):
        bootstrap._verify_static_authority()


def test_preimport_attack_rejected_before_static_authority(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    static_called = False

    def forbidden_static() -> dict[str, object]:
        nonlocal static_called
        static_called = True
        return CONFIG

    monkeypatch.setattr(bootstrap, "_verify_static_authority", forbidden_static)
    with pytest.raises(bootstrap.BootstrapRejected, match="preimport"):
        bootstrap.validate(preimport_modules=["src.attack"])
    assert static_called is False


def test_closed_successor_validate_only_report_has_zero_execution_or_writes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(bootstrap, "_verify_static_authority", lambda: CONFIG)
    report = bootstrap.validate(
        preimport_modules=[], runtime=_runtime(), root_appearances=_roots()
    )
    assert report["validation_passed"] is True
    assert report["status"] == "READY_FOR_INDEPENDENT_REVIEW"
    assert report["execution_ready"] is False
    assert report["project_modules_imported"] == 0
    assert report["worker_processes_started"] == 0
    assert report["scientific_loader_calls"] == 0
    assert report["solver_calls"] == 0
    assert report["result_files_written"] == 0
    assert report["formal_writes"] == 0


@pytest.mark.parametrize(
    ("field", "bad_value"),
    [
        ("executable", r"C:\Python311\python.exe"),
        ("executable_sha256", "0" * 64),
        ("version", "3.11.14"),
        ("cwd", r"D:\CUHKSZ"),
        ("hostname", "ANOTHER-HOST"),
        ("system", "Linux"),
        ("release", "11"),
        ("machine", "ARM64"),
    ],
)
def test_runtime_identity_drift_rejected(field: str, bad_value: object) -> None:
    runtime = _runtime()
    runtime[field] = bad_value
    with pytest.raises(bootstrap.BootstrapRejected, match="runtime identity"):
        bootstrap._verify_runtime(CONFIG, runtime)


def test_argv_module_or_path_drift_rejected() -> None:
    executable = CONFIG["bootstrap_contract"]["locked_python_executable"]
    for argv in (
        [executable, "-m", "experiments.bad"],
        [*_runtime()["orig_argv"], "--execute"],
    ):
        runtime = _runtime()
        runtime["orig_argv"] = argv
        with pytest.raises(bootstrap.BootstrapRejected, match="orig_argv"):
            bootstrap._verify_runtime(CONFIG, runtime)


def test_environment_allowlist_rejects_leakage_and_missing_binding() -> None:
    expected = CONFIG["bootstrap_contract"]["exact_environment"]
    for environment in (
        {**expected, "PYTHONPATH": "attack"},
        {key: value for key, value in expected.items() if key != "NO_COLOR"},
    ):
        runtime = _runtime()
        runtime["environment"] = environment
        with pytest.raises(bootstrap.BootstrapRejected, match="environment"):
            bootstrap._verify_runtime(CONFIG, runtime)


def test_stale_or_active_related_process_rejected() -> None:
    stale = _runtime()
    stale["process_age_seconds"] = 121.0
    with pytest.raises(bootstrap.BootstrapRejected, match="not fresh"):
        bootstrap._verify_runtime(CONFIG, stale)

    active = _runtime()
    active["processes"] = [(os.getpid(), "python.exe"), (os.getpid() + 1, "highs.exe")]
    with pytest.raises(bootstrap.BootstrapRejected, match="active related process"):
        bootstrap._verify_runtime(CONFIG, active)


def test_insufficient_virtual_memory_rejected() -> None:
    runtime = _runtime()
    runtime["available_virtual_bytes"] = 10 * 1024**3 - 1
    with pytest.raises(bootstrap.BootstrapRejected, match="insufficient"):
        bootstrap._verify_runtime(CONFIG, runtime)


def test_any_fresh_or_protected_root_appearance_rejected() -> None:
    for relative in _roots():
        roots = _roots()
        roots[relative] = True
        with pytest.raises(bootstrap.BootstrapRejected, match="root appearance"):
            bootstrap._verify_roots(CONFIG, roots)


def test_non_validate_cli_is_permanently_closed() -> None:
    with pytest.raises(bootstrap.BootstrapRejected, match="validate-only"):
        bootstrap.main([])


def test_validate_does_not_call_filesystem_mutators(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(bootstrap, "_verify_static_authority", lambda: CONFIG)

    def forbidden(*_args: object, **_kwargs: object) -> None:
        raise AssertionError("filesystem mutation attempted")

    for name in ("mkdir", "makedirs", "remove", "replace", "rename", "unlink"):
        if hasattr(os, name):
            monkeypatch.setattr(os, name, forbidden)
    report = bootstrap.validate(
        preimport_modules=[], runtime=copy.deepcopy(_runtime()), root_appearances=_roots()
    )
    assert report["result_files_written"] == 0
