"""Verify the RQ2 executor bundle, environment, and solver interfaces."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
import shutil
import sys
import tempfile
from pathlib import Path
from typing import Any

import yaml
from pyomo.environ import ConcreteModel, Constraint, NonNegativeReals, Objective, Var
from pyomo.opt import TerminationCondition

from src.evaluation.execution_machine import (
    execution_host_status,
    require_execution_host,
)
from src.evaluation.rq2_provenance_v3 import load_json_strict, sha256_file
from src.solvers.rq2_solver_adapter import (
    create_solver,
    model_scale,
    solver_spec,
)

_ROOT = Path(__file__).resolve().parents[1]
_CONFIG_SCHEMA = "rq2_public_executor_handoff_config_v1"
_BUNDLE_SCHEMA = "rq2_public_executor_bundle_manifest_v1"
_OPTIMAL = {
    TerminationCondition.optimal,
    TerminationCondition.globallyOptimal,
}


def _path(raw: object, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"{label} must be a nonempty path")
    path = Path(raw)
    return path if path.is_absolute() else _ROOT / path


def _verify_json_package(directory: Path, manifest_name: str) -> int:
    manifest = load_json_strict(directory / manifest_name)
    if not isinstance(manifest, dict) or not manifest:
        raise ValueError(f"invalid package manifest: {directory}")
    for name, expected in manifest.items():
        member = directory / name
        if not member.is_file() or sha256_file(member) != expected:
            raise ValueError(f"package member drifted: {member}")
    return len(manifest)


def _verify_text_package(directory: Path, manifest_name: str) -> int:
    entries = []
    for line in (directory / manifest_name).read_text(encoding="utf-8").splitlines():
        digest, separator, name = line.partition("  ")
        if len(digest) != 64 or not separator or not name:
            raise ValueError(f"invalid text manifest entry: {line}")
        member = directory / name
        if not member.is_file() or sha256_file(member) != digest:
            raise ValueError(f"package member drifted: {member}")
        entries.append(name)
    if not entries or len(entries) != len(set(entries)):
        raise ValueError(f"invalid text manifest inventory: {directory}")
    return len(entries)


def _verify_bundle(config: dict[str, Any]) -> dict[str, object]:
    manifest_path = _path(
        config["bundle"]["manifest_path"],
        "bundle.manifest_path",
    )
    manifest = load_json_strict(manifest_path)
    if (
        not isinstance(manifest, dict)
        or manifest.get("schema") != _BUNDLE_SCHEMA
        or not isinstance(manifest.get("files"), dict)
        or not manifest["files"]
    ):
        raise ValueError("executor bundle manifest is invalid")
    for name, expected in manifest["files"].items():
        path = _path(name, "bundle file")
        if not path.is_file() or sha256_file(path) != expected:
            raise ValueError(f"executor bundle file drifted: {name}")
    nested = {}
    for package in config["bundle"]["input_packages"]:
        directory = _path(package["path"], "input package")
        manifest_name = str(package["manifest"])
        manifest_file = directory / manifest_name
        if sha256_file(manifest_file) != package["manifest_sha256"]:
            raise ValueError(f"input package manifest drifted: {directory}")
        if manifest_name.endswith(".json"):
            count = _verify_json_package(directory, manifest_name)
        else:
            count = _verify_text_package(directory, manifest_name)
        nested[str(package["path"])] = count
    return {
        "bundle_manifest_path": str(manifest_path.relative_to(_ROOT)),
        "bundle_manifest_sha256": sha256_file(manifest_path),
        "bundle_file_count": len(manifest["files"]),
        "nested_package_member_counts": nested,
    }


def _environment(
    config: dict[str, Any],
    *,
    strict: bool,
) -> dict[str, object]:
    expected = config["environment"]["required_packages"]
    observed = {}
    for name in expected:
        try:
            observed[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            observed[name] = None
    drift = {
        name: {"expected": str(expected[name]), "observed": observed[name]}
        for name in expected
        if observed[name] != str(expected[name])
    }
    expected_python = str(config["environment"]["required_python_version"])
    observed_python = platform.python_version()
    matches = observed_python == expected_python and not drift
    if strict and not matches:
        raise RuntimeError(
            f"executor environment drifted: python={observed_python}; "
            f"packages={drift}"
        )
    return {
        "python_executable": str(Path(sys.executable).resolve()),
        "python_version": observed_python,
        "packages": observed,
        "matches_executor_lock": matches,
        "drift": drift,
    }


def _tiny_solver_smoke(
    solver_payload: dict[str, object],
) -> dict[str, object]:
    specification = solver_spec(solver_payload)
    model = ConcreteModel()
    model.x = Var(domain=NonNegativeReals)
    model.lower = Constraint(expr=model.x >= 1.0)
    model.objective = Objective(expr=model.x)
    scale = model_scale(model)
    solver, options = create_solver(specification)
    result = solver.solve(
        model,
        load_solutions=False,
        tee=False,
        options=options,
    )
    termination = result.solver.termination_condition
    if termination not in _OPTIMAL:
        raise RuntimeError(
            f"{specification.name} tiny solve failed: {termination}"
        )
    model.solutions.load_from(result)
    observed = float(model.x.value)
    if abs(observed - 1.0) > specification.feasibility_tolerance:
        raise RuntimeError(f"{specification.name} tiny solution audit failed")
    return {
        "solver_name": specification.name,
        "package_version": specification.expected_package_version,
        "pyomo_interface": (
            f"{type(solver).__module__}.{type(solver).__name__}"
        ),
        "termination_condition": str(termination),
        "solver_status": str(result.solver.status),
        "objective_incumbent": observed,
        "lower_bound": float(result.problem.lower_bound),
        "upper_bound": float(result.problem.upper_bound),
        "model_variables": scale.variables,
        "model_constraints": scale.constraints,
        "configured_options": options,
    }


def run(
    config_path: Path,
    *,
    verify_only: bool = False,
) -> dict[str, object]:
    config_path = config_path.resolve()
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or config.get("schema") != _CONFIG_SCHEMA:
        raise ValueError("executor handoff config schema drifted")
    bundle = _verify_bundle(config)
    environment = _environment(config, strict=not verify_only)
    report = {
        "schema": "rq2_public_executor_bundle_verification_v1",
        "config_sha256": sha256_file(config_path),
        "bundle": bundle,
        "environment": environment,
        "execution_host": execution_host_status(config["execution"]),
        "solver_smokes": [],
        "formal_execution_started": False,
    }
    if verify_only:
        return report
    require_execution_host(config["execution"])
    pilot_config = yaml.safe_load(
        _path(config["pilot"]["config_path"], "pilot.config_path").read_text(
            encoding="utf-8"
        )
    )
    report["schema"] = config["output"]["schema"]
    report["solver_smokes"] = [
        _tiny_solver_smoke(pilot_config["solvers"][name])
        for name in config["runtime_preflight"]["solvers"]
    ]
    expected_variables = int(
        config["runtime_preflight"]["tiny_model_variables"]
    )
    expected_constraints = int(
        config["runtime_preflight"]["tiny_model_constraints"]
    )
    if any(
        item["model_variables"] != expected_variables
        or item["model_constraints"] != expected_constraints
        for item in report["solver_smokes"]
    ):
        raise RuntimeError("tiny solver model scale drifted")
    target = _path(config["output"]["directory"], "output.directory")
    if target.exists():
        raise FileExistsError(f"refusing to overwrite preflight output: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.", dir=target.parent))
    try:
        shutil.copyfile(config_path, staging / "config.yaml")
        (staging / "preflight.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        names = ("config.yaml", "preflight.json")
        manifest = {name: sha256_file(staging / name) for name in names}
        (staging / "SHA256SUMS.json").write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        staging.rename(target)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return report


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("configs/rq2_public_executor_handoff_v1.yaml"),
    )
    parser.add_argument("--verify-only", action="store_true")
    args = parser.parse_args()
    print(
        json.dumps(
            run(args.config, verify_only=args.verify_only),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
