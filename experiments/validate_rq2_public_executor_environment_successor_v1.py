"""Validate the versioned RQ2 executor environment successor."""

from __future__ import annotations

import argparse
import hashlib
import importlib
import importlib.metadata
import json
import platform
import sys
from pathlib import Path
from typing import Any

import yaml

_ROOT = Path(__file__).resolve().parents[1]
_CONFIG = _ROOT / "configs/rq2_public_executor_environment_successor_v1.yaml"
_MANIFEST = (
    _ROOT
    / "configs/rq2_public_executor_environment_successor_v1.SHA256SUMS.json"
)
_SCHEMA = "rq2_public_executor_environment_successor_v1"
_STATUS = "implementation_only_environment_rebuild_contract_not_pilot_activation"
_PREDECESSOR_HASHES = {
    "environments/rq2_executor_v1.yml": (
        "00ab8f2438993385b4d7f937603b0cbe70623588078728389de9a93b9ebc4bb1"
    ),
    "requirements.txt": (
        "32d801524eb4ecb69ce7af654fbef2318344462e3ebd92f4d169ca5096cf4be2"
    ),
    "configs/rq2_public_executor_handoff_v2.yaml": (
        "e362b635dcd22c54162683d04686fd907681976c8c933e983584e19a175c34f0"
    ),
    "configs/rq2_public_executor_bundle_v2.SHA256SUMS.json": (
        "10129f473a521f37ae0c45bf89a4904c77156c92dcc55837adf91adb8d58e37e"
    ),
    "configs/rq2_public_executor_bundle_v2.OUTER.SHA256SUMS.json": (
        "32bde980733ef80b04571d1fe328c893ff78b4ecb1aee2150c318970707e4942"
    ),
    "scripts/rq2_public_executor.py": (
        "8fb1f8a57f2491f8c24f4fb91ebafdf4e3470b418bddc8f0e297c76a8ce8bf42"
    ),
}
_CONDA_PACKAGES = {
    "python": "3.11.15",
    "numpy": "1.26.4",
    "scipy": "1.17.0",
    "pyomo": "6.10.1",
    "highspy": "1.15.1",
    "pyyaml": "6.0.3",
    "pytest": "9.0.2",
}
_PIP_PACKAGES = {
    "gurobipy": "13.0.2",
    "osqp": "1.0.5",
    "pypower": "5.1.19",
    "ruff": "0.16.4",
}
_RUNTIME_PACKAGES = {
    **{name: version for name, version in _CONDA_PACKAGES.items() if name != "python"},
    **_PIP_PACKAGES,
}
_OBSERVED_FAILURE = {
    "fresh_v1_environment_entrypoint_import_failed": True,
    "missing_package_first_observed": "pypower",
    "additional_eager_import_dependency": "osqp",
    "solver_calls_before_failure": 0,
    "result_files_written_before_failure": 0,
    "mathematical_infeasibility_evidence": False,
}
_GATES = {
    "environment_successor_runtime_validated": False,
    "runtime_receipt_published": False,
    "pilot_executed": False,
    "cross_solver_confirmation_completed": False,
    "formal_execution_ready": False,
    "formal_result_exists": False,
    "security_certified": False,
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(raw: object, label: str) -> dict[str, Any]:
    if not isinstance(raw, dict):
        raise TypeError(f"{label} must be a mapping")
    return raw


def _environment_packages(path: Path) -> tuple[dict[str, str], dict[str, str]]:
    payload = _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), "environment")
    dependencies = payload.get("dependencies")
    if not isinstance(dependencies, list):
        raise TypeError("environment dependencies must be a list")
    conda: dict[str, str] = {}
    pip: dict[str, str] = {}
    for dependency in dependencies:
        if isinstance(dependency, str):
            if dependency == "pip":
                continue
            name, separator, version = dependency.partition("=")
            if not separator or not name or not version:
                raise ValueError(f"environment dependency is not exactly pinned: {dependency}")
            conda[name.lower()] = version
        elif isinstance(dependency, dict) and set(dependency) == {"pip"}:
            entries = dependency["pip"]
            if not isinstance(entries, list):
                raise TypeError("pip dependencies must be a list")
            for entry in entries:
                if not isinstance(entry, str):
                    raise TypeError("pip dependency must be a string")
                name, separator, version = entry.partition("==")
                if not separator or not name or not version:
                    raise ValueError(f"pip dependency is not exactly pinned: {entry}")
                pip[name.lower()] = version
        else:
            raise ValueError(f"unsupported environment dependency: {dependency}")
    return conda, pip


def validate_environment_spec(path: Path) -> dict[str, object]:
    conda, pip = _environment_packages(path)
    if conda != _CONDA_PACKAGES:
        raise ValueError(f"conda direct dependency inventory drifted: {conda}")
    if pip != _PIP_PACKAGES:
        raise ValueError(f"pip direct dependency inventory drifted: {pip}")
    return {
        "conda_direct_packages": conda,
        "pip_direct_packages": pip,
        "missing_v1_entry_import_packages_registered": ["osqp", "pypower"],
    }


def _import_executor_entrypoint() -> None:
    root = str(_ROOT)
    original_path = list(sys.path)
    sys.path[:] = [root, *(entry for entry in original_path if entry != root)]
    try:
        module = importlib.import_module("scripts.rq2_public_executor")
        module_file = getattr(module, "__file__", None)
        expected = (_ROOT / "scripts/rq2_public_executor.py").resolve()
        if module_file is None or Path(module_file).resolve() != expected:
            raise RuntimeError("imported executor entrypoint is not the frozen file")
    finally:
        sys.path[:] = original_path


def _runtime_environment() -> dict[str, object]:
    observed = {
        name: importlib.metadata.version(name) for name in _RUNTIME_PACKAGES
    }
    drift = {
        name: {"expected": expected, "observed": observed.get(name)}
        for name, expected in _RUNTIME_PACKAGES.items()
        if observed.get(name) != expected
    }
    python_version = platform.python_version()
    executable = Path(sys.executable).resolve()
    if python_version != _CONDA_PACKAGES["python"] or drift:
        raise RuntimeError(
            f"executor runtime drifted: python={python_version}; packages={drift}"
        )
    if not executable.is_file() or executable.is_symlink():
        raise RuntimeError("executor Python must be an ordinary file")
    _import_executor_entrypoint()
    return {
        "python_executable": str(executable),
        "python_version": python_version,
        "packages": observed,
        "entrypoint_imported": True,
        "matches_environment_successor": True,
    }


def validate(
    config_path: Path = _CONFIG,
    manifest_path: Path = _MANIFEST,
    *,
    runtime: bool = False,
) -> dict[str, object]:
    config_path = config_path.resolve()
    manifest_path = manifest_path.resolve()
    config = _mapping(
        yaml.safe_load(config_path.read_text(encoding="utf-8")),
        "successor config",
    )
    if config.get("schema") != _SCHEMA:
        raise ValueError("executor environment successor schema drifted")
    if config.get("status") != _STATUS:
        raise ValueError("executor environment successor status drifted")
    if config.get("observed_failure") != _OBSERVED_FAILURE:
        raise ValueError("observed executor environment failure semantics drifted")
    predecessor = _mapping(config.get("predecessor"), "predecessor")
    if predecessor.get("immutable") is not True:
        raise ValueError("executor environment predecessor must remain immutable")
    if predecessor.get("files") != _PREDECESSOR_HASHES:
        raise ValueError("executor environment predecessor inventory drifted")
    for relative, expected in _PREDECESSOR_HASHES.items():
        if predecessor["files"].get(relative) != expected:
            raise ValueError(f"predecessor binding drifted: {relative}")
        if _sha256(_ROOT / relative) != expected:
            raise ValueError(f"predecessor bytes drifted: {relative}")

    successor = _mapping(config.get("successor"), "successor")
    spec_path = _ROOT / "environments/rq2_executor_v2.yml"
    expected_successor = {
        "environment_spec_path": "environments/rq2_executor_v2.yml",
        "environment_spec_sha256": _sha256(spec_path),
        "manifest_path": (
            "configs/rq2_public_executor_environment_successor_v1.SHA256SUMS.json"
        ),
        "validator_path": (
            "experiments/validate_rq2_public_executor_environment_successor_v1.py"
        ),
        "validator_sha256": _sha256(Path(__file__).resolve()),
        "entrypoint_path": "scripts/rq2_public_executor.py",
        "entrypoint_sha256": _PREDECESSOR_HASHES["scripts/rq2_public_executor.py"],
        "required_python_version": _CONDA_PACKAGES["python"],
        "required_packages": _RUNTIME_PACKAGES,
        "runtime_validation_requires_entrypoint_import": True,
        "runtime_validation_solver_calls": 0,
        "runtime_validation_result_writes": 0,
        "scientific_design_changed": False,
        "solver_or_algorithm_changed": False,
        "threads_seed_or_thresholds_changed": False,
        "pilot_block_changed": False,
    }
    if successor != expected_successor:
        raise ValueError("executor environment successor authority drifted")
    if config.get("gates") != _GATES:
        raise ValueError("executor environment successor gates drifted")
    environment = validate_environment_spec(spec_path)

    manifest = _mapping(
        json.loads(manifest_path.read_text(encoding="utf-8")),
        "successor manifest",
    )
    expected_manifest = dict(_PREDECESSOR_HASHES)
    expected_manifest.update(
        {
            successor["environment_spec_path"]: _sha256(spec_path),
            "configs/rq2_public_executor_environment_successor_v1.yaml": _sha256(
                config_path
            ),
            "experiments/validate_rq2_public_executor_environment_successor_v1.py": _sha256(
                Path(__file__).resolve()
            ),
        }
    )
    if manifest != expected_manifest:
        raise ValueError("executor environment successor manifest drifted")
    report: dict[str, object] = {
        "schema": "rq2_public_executor_environment_validation_v1",
        "config_sha256": _sha256(config_path),
        "manifest_sha256": _sha256(manifest_path),
        "environment_spec_sha256": _sha256(spec_path),
        "environment": environment,
        "runtime": None,
        "runtime_checked": runtime,
        "solver_calls": 0,
        "result_files_written": 0,
        "pilot_executed": False,
        "formal_execution_started": False,
        "formal_execution_ready": False,
        "security_certified": False,
        "validation_passed": True,
    }
    if runtime:
        report["runtime"] = _runtime_environment()
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=_CONFIG)
    parser.add_argument("--manifest", type=Path, default=_MANIFEST)
    parser.add_argument("--runtime", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            validate(args.config, args.manifest, runtime=args.runtime),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
