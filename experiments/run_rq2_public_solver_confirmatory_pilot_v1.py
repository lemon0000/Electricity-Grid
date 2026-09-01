"""Run the fresh-process RQ2 cross-solver confirmatory pilot."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from experiments.validate_rq2_public_solver_pilot_semantic_successor_v1 import (
    evaluate_runs,
)
from src.evaluation.execution_machine import require_execution_host

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_solver_confirmatory_pilot_v1.yaml"
SEMANTIC_CONFIG = (
    ROOT / "configs/rq2_public_solver_pilot_semantic_successor_v1.yaml"
)
MODULE = "experiments.run_rq2_public_solver_confirmatory_pilot_v1"
CONFIG_SCHEMA = "rq2_public_solver_confirmatory_pilot_config_v1"
WORKER_SCHEMA = "rq2_public_solver_confirmatory_worker_payload_v1"
WORKER_RECEIPT_SCHEMA = "rq2_public_solver_confirmatory_worker_receipt_v1"
RESULT_SCHEMA = "rq2_public_solver_confirmatory_pilot_v1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    return dict(value)


def _load_json_strict_text(payload: str, label: str) -> Any:
    def no_duplicates(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"{label} contains duplicate key: {key}")
            result[key] = value
        return result

    try:
        return json.loads(payload, object_pairs_hook=no_duplicates)
    except json.JSONDecodeError as error:
        raise ValueError(f"cannot parse {label}") from error


def _load_json_strict(path: Path, label: str) -> Any:
    try:
        payload = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as error:
        raise ValueError(f"cannot read {label}") from error
    return _load_json_strict_text(payload, label)


def _load_config(config_path: Path) -> dict[str, Any]:
    if config_path.resolve() != CONFIG.resolve():
        raise ValueError("only the canonical confirmatory config is accepted")
    payload = _mapping(
        yaml.safe_load(config_path.read_text(encoding="utf-8")),
        "confirmatory config",
    )
    if payload.get("schema") != CONFIG_SCHEMA:
        raise ValueError("confirmatory config schema drifted")
    implementation = _mapping(payload.get("implementation"), "implementation")
    runner = ROOT / str(implementation.get("runner_path"))
    if (
        runner.resolve() != Path(__file__).resolve()
        or not runner.is_file()
        or runner.is_symlink()
        or _sha256(runner) != implementation.get("runner_sha256")
    ):
        raise ValueError("confirmatory runner bytes drifted")
    return payload


def _run_identity(config: Mapping[str, Any], run_id: str) -> tuple[str, int]:
    expected = {
        str(item): (
            str(item).rsplit("_r", maxsplit=1)[0],
            int(str(item).rsplit("_r", maxsplit=1)[1]),
        )
        for item in config["execution"]["execution_order"]
    }
    if run_id not in expected:
        raise ValueError(f"unregistered confirmatory run_id: {run_id}")
    return expected[run_id]


def _require_execution_gate(config: Mapping[str, Any]) -> None:
    gates = _mapping(config.get("gates"), "confirmatory gates")
    if gates.get("independent_confirmatory_implementation_review_passed") is not True:
        raise RuntimeError(
            "confirmatory implementation awaits independent review; solver execution "
            "is not enabled by this pre-execution bundle"
        )


def _require_empty_worker_root(worker_root: Path) -> None:
    if (
        not worker_root.is_absolute()
        or not worker_root.is_dir()
        or worker_root.is_symlink()
    ):
        raise ValueError("worker output root must be a registered ordinary directory")
    if list(worker_root.iterdir()):
        raise ValueError("worker output root must be empty")


def _execute_worker(
    config_path: Path,
    *,
    run_id: str,
    worker_root: Path,
    expected_parent_pid: int,
) -> dict[str, object]:
    # Imports that can reach solver code are intentionally worker-local.
    from experiments.run_rq2_public_solver_pilot_v1 import (
        _preflight as _v1_preflight,
    )
    from experiments.run_rq2_public_solver_pilot_v1 import _run_block
    from experiments.validate_rq2_public_solver_confirmatory_pilot_v1 import (
        validate,
    )
    from src.grid.rts_gmlc import load_rts_gmlc_chronological_data

    validate()
    config = _load_config(config_path)
    _require_execution_gate(config)
    require_execution_host(config["execution"])
    if os.getppid() != expected_parent_pid:
        raise RuntimeError("worker parent PID does not match the registered controller")
    _require_empty_worker_root(worker_root)
    solver_name, repetition = _run_identity(config, run_id)
    config_sha256 = _sha256(config_path)
    implementation_sha256 = _sha256(Path(__file__).resolve())
    parent_contract_sha256 = str(
        config["semantic_authority"]["manifest_sha256"]
    )

    _, context = _v1_preflight(
        ROOT / "configs/rq2_public_solver_pilot_v1.yaml"
    )
    data = load_rts_gmlc_chronological_data(
        context["grid_root"],
        base_mva=float(config["input"]["base_mva"]),
    )
    blocks = []
    for pilot in config["pilot_blocks"]:
        result = _run_block(
            data,
            context["blocks"][pilot["block_id"]],
            solver_payload=config["solvers"][solver_name],
            dc_bus=int(config["model"]["dc_bus"]),
            dc_demand_mw=float(config["model"]["dc_reference_demand_mw"]),
            tolerance_mw=float(config["model"]["tolerance_mw"]),
        )
        result["role"] = pilot["role"]
        blocks.append(result)
    if (
        _sha256(config_path) != config_sha256
        or _sha256(Path(__file__).resolve()) != implementation_sha256
    ):
        raise ValueError("confirmatory authority drifted during worker execution")

    run = {
        "run_id": run_id,
        "solver_name": solver_name,
        "repetition": repetition,
        "blocks": blocks,
    }
    payload = {
        "schema": WORKER_SCHEMA,
        "run_id": run_id,
        "solver_name": solver_name,
        "repetition": repetition,
        "worker_pid": os.getpid(),
        "worker_parent_pid": os.getppid(),
        "parent_contract_sha256": parent_contract_sha256,
        "config_sha256": config_sha256,
        "implementation_sha256": implementation_sha256,
        "run": run,
    }
    temporary = worker_root / ".run.json.tmp"
    published = worker_root / "run.json"
    temporary.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    temporary.replace(published)
    return {
        "schema": WORKER_RECEIPT_SCHEMA,
        "run_id": run_id,
        "worker_pid": os.getpid(),
        "worker_parent_pid": os.getppid(),
        "parent_contract_sha256": parent_contract_sha256,
        "payload_sha256": _sha256(published),
    }


def _validate_worker_payload(
    worker_root: Path,
    receipt_raw: object,
    *,
    expected_run_id: str,
    expected_solver: str,
    expected_repetition: int,
    expected_worker_pid: int,
    expected_parent_pid: int,
    expected_parent_contract_sha256: str,
    expected_config_sha256: str,
    expected_implementation_sha256: str,
    seen_run_ids: set[str],
    seen_worker_pids: set[int],
) -> dict[str, object]:
    if worker_root.is_symlink() or not worker_root.is_dir():
        raise ValueError("registered worker root is not an ordinary directory")
    children = list(worker_root.iterdir())
    if {item.name for item in children} != {"run.json"} or len(children) != 1:
        raise ValueError("worker output inventory drifted")
    payload_path = children[0]
    if not payload_path.is_file() or payload_path.is_symlink():
        raise ValueError("worker payload must be an ordinary non-symlink file")

    receipt = _mapping(receipt_raw, "worker receipt")
    if set(receipt) != {
        "schema",
        "run_id",
        "worker_pid",
        "worker_parent_pid",
        "parent_contract_sha256",
        "payload_sha256",
    }:
        raise ValueError("worker receipt schema drifted")
    if receipt.get("schema") != WORKER_RECEIPT_SCHEMA:
        raise ValueError("worker receipt schema drifted")
    if receipt.get("payload_sha256") != _sha256(payload_path):
        raise ValueError("worker payload hash drifted")

    payload = _mapping(_load_json_strict(payload_path, "worker payload"), "worker payload")
    if set(payload) != {
        "schema",
        "run_id",
        "solver_name",
        "repetition",
        "worker_pid",
        "worker_parent_pid",
        "parent_contract_sha256",
        "config_sha256",
        "implementation_sha256",
        "run",
    }:
        raise ValueError("worker payload schema drifted")
    expected = {
        "schema": WORKER_SCHEMA,
        "run_id": expected_run_id,
        "solver_name": expected_solver,
        "repetition": expected_repetition,
        "worker_pid": expected_worker_pid,
        "worker_parent_pid": expected_parent_pid,
        "parent_contract_sha256": expected_parent_contract_sha256,
        "config_sha256": expected_config_sha256,
        "implementation_sha256": expected_implementation_sha256,
    }
    for field, value in expected.items():
        if payload.get(field) != value:
            raise ValueError(f"worker payload {field} drifted")
    for field in (
        "run_id",
        "worker_pid",
        "worker_parent_pid",
        "parent_contract_sha256",
    ):
        if receipt.get(field) != payload.get(field):
            raise ValueError(f"worker receipt {field} drifted")
    if expected_run_id in seen_run_ids or expected_worker_pid in seen_worker_pids:
        raise ValueError("duplicate run identity or worker process observed")
    seen_run_ids.add(expected_run_id)
    seen_worker_pids.add(expected_worker_pid)

    run = _mapping(payload.get("run"), "worker run")
    if set(run) != {"run_id", "solver_name", "repetition", "blocks"}:
        raise ValueError("worker run schema drifted")
    for field in ("run_id", "solver_name", "repetition"):
        if run.get(field) != payload.get(field):
            raise ValueError(f"worker run {field} drifted")
    return run


def _dispatch_worker(
    config_path: Path,
    *,
    run_id: str,
    worker_root: Path,
    python_executable: Path,
    watchdog_seconds: int,
    expected_config_sha256: str,
    expected_implementation_sha256: str,
    seen_run_ids: set[str],
    seen_worker_pids: set[int],
) -> dict[str, object]:
    config = _load_config(config_path)
    solver, repetition = _run_identity(config, run_id)
    controller_pid = os.getpid()
    command = [
        str(python_executable),
        "-m",
        MODULE,
        "--config",
        str(config_path),
        "--worker",
        "--run-id",
        run_id,
        "--worker-output",
        str(worker_root),
        "--expected-parent-pid",
        str(controller_pid),
    ]
    process = subprocess.Popen(
        command,
        cwd=ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
    )
    try:
        stdout, stderr = process.communicate(timeout=watchdog_seconds)
    except subprocess.TimeoutExpired as error:
        process.kill()
        try:
            process.communicate(timeout=5)
        except subprocess.TimeoutExpired as termination_error:
            raise RuntimeError(
                "worker timeout termination is unconfirmed; no result may publish"
            ) from termination_error
        raise TimeoutError(
            f"worker {run_id} exceeded the external watchdog; this is not "
            "infeasibility evidence"
        ) from error
    if process.returncode != 0:
        raise RuntimeError(
            f"worker {run_id} failed with exit code {process.returncode}; "
            f"stderr={stderr!r}"
        )
    receipt = _load_json_strict_text(stdout, f"worker {run_id} receipt")
    return _validate_worker_payload(
        worker_root,
        receipt,
        expected_run_id=run_id,
        expected_solver=solver,
        expected_repetition=repetition,
        expected_worker_pid=process.pid,
        expected_parent_pid=controller_pid,
        expected_parent_contract_sha256=str(
            config["semantic_authority"]["manifest_sha256"]
        ),
        expected_config_sha256=expected_config_sha256,
        expected_implementation_sha256=expected_implementation_sha256,
        seen_run_ids=seen_run_ids,
        seen_worker_pids=seen_worker_pids,
    )


def _python_authority(config: Mapping[str, Any]) -> Path:
    contract = _mapping(config["execution"]["python_authority"], "Python authority")
    variable = str(contract["environment_variable"])
    raw = os.environ.get(variable)
    if not raw:
        raise RuntimeError(f"{variable} must identify the executor Python")
    path = Path(raw)
    if (
        not path.is_absolute()
        or not path.is_file()
        or path.is_symlink()
        or path.resolve() != Path(sys.executable).resolve()
    ):
        raise RuntimeError("executor Python authority is not the current ordinary file")
    return path.resolve()


def _write_result(
    staging: Path,
    config_path: Path,
    config: Mapping[str, Any],
    runs: list[dict[str, object]],
    worker_pids: set[int],
) -> dict[str, object]:
    semantic_config = _mapping(
        yaml.safe_load(SEMANTIC_CONFIG.read_text(encoding="utf-8")),
        "semantic successor config",
    )
    evaluator_report = evaluate_runs(semantic_config, runs)
    semantic_validation = {
        "schema": "rq2_public_solver_confirmatory_semantic_validation_v1",
        "semantic_successor_config_sha256": _sha256(SEMANTIC_CONFIG),
        "evaluator_report": evaluator_report,
        "fresh_execution_run_ids": [run["run_id"] for run in runs],
        "fresh_worker_pids": sorted(worker_pids),
        "fresh_process_isolation_verified": True,
        "semantic_contract_passed": True,
        "cross_solver_confirmation_completed": True,
        "formal_grid_execution_started": False,
        "security_certified": False,
    }
    summary = {
        "schema": RESULT_SCHEMA,
        "config_sha256": _sha256(config_path),
        "implementation_sha256": config["implementation"]["runner_sha256"],
        "fresh_execution_status": "passed",
        "fresh_execution_passed": True,
        "fresh_execution_failed": False,
        "run_count": len(runs),
        "unique_worker_process_count": len(worker_pids),
        "semantic_contract_passed": True,
        "cross_solver_confirmation_completed": True,
        "formal_grid_execution_started": False,
        "formal_result_exists": False,
        "claim": False,
        "security_certified": False,
    }
    shutil.copyfile(config_path, staging / "config.yaml")
    (staging / "runs.json").write_text(
        json.dumps(runs, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (staging / "semantic_validation.json").write_text(
        json.dumps(semantic_validation, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (staging / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    names = ("config.yaml", "runs.json", "semantic_validation.json", "summary.json")
    manifest = {name: _sha256(staging / name) for name in names}
    (staging / "SHA256SUMS.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if {item.name for item in staging.iterdir()} != {*names, "SHA256SUMS.json"}:
        raise ValueError("confirmatory result staging inventory drifted")
    return summary


def run(
    config_path: Path = CONFIG,
    *,
    validate_only: bool = False,
) -> dict[str, object]:
    from experiments.validate_rq2_public_solver_confirmatory_pilot_v1 import (
        validate,
    )

    preflight = validate(config_path)
    if validate_only:
        return preflight
    config_path = config_path.resolve()
    config = _load_config(config_path)
    target = ROOT / str(config["output"]["directory"])
    if target.exists():
        raise FileExistsError(f"refusing to overwrite confirmatory output: {target}")
    _require_execution_gate(config)
    require_execution_host(config["execution"])
    python_executable = _python_authority(config)
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(prefix=f".{target.name}.staging.", dir=target.parent)
    )
    workers = staging / "workers"
    workers.mkdir()
    config_sha256 = _sha256(config_path)
    implementation_sha256 = _sha256(Path(__file__).resolve())
    seen_run_ids: set[str] = set()
    seen_worker_pids: set[int] = set()
    runs: list[dict[str, object]] = []
    try:
        for run_id in config["execution"]["execution_order"]:
            worker_root = Path(
                tempfile.mkdtemp(prefix=f"{run_id}.", dir=workers)
            ).resolve()
            run_record = _dispatch_worker(
                config_path,
                run_id=str(run_id),
                worker_root=worker_root,
                python_executable=python_executable,
                watchdog_seconds=int(config["execution"]["external_watchdog_seconds"]),
                expected_config_sha256=config_sha256,
                expected_implementation_sha256=implementation_sha256,
                seen_run_ids=seen_run_ids,
                seen_worker_pids=seen_worker_pids,
            )
            runs.append(run_record)
            shutil.rmtree(worker_root)
        if list(workers.iterdir()):
            raise ValueError("worker staging roots were not fully consumed")
        workers.rmdir()
        if (
            _sha256(config_path) != config_sha256
            or _sha256(Path(__file__).resolve()) != implementation_sha256
        ):
            raise ValueError("confirmatory authority drifted during execution")
        summary = _write_result(staging, config_path, config, runs, seen_worker_pids)
        if target.exists():
            raise FileExistsError("confirmatory output appeared before publication")
        staging.rename(target)
    except Exception:
        shutil.rmtree(staging, ignore_errors=True)
        raise
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=CONFIG)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--worker", action="store_true", help=argparse.SUPPRESS)
    parser.add_argument("--run-id", help=argparse.SUPPRESS)
    parser.add_argument("--worker-output", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--expected-parent-pid", type=int, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.worker:
        if (
            not args.run_id
            or args.worker_output is None
            or args.expected_parent_pid is None
            or args.validate_only
        ):
            parser.error("worker mode requires its registered controller arguments")
        report = _execute_worker(
            args.config.resolve(),
            run_id=args.run_id,
            worker_root=args.worker_output.resolve(),
            expected_parent_pid=args.expected_parent_pid,
        )
    else:
        if args.run_id or args.worker_output is not None or args.expected_parent_pid:
            parser.error("worker-only arguments require --worker")
        report = run(args.config, validate_only=args.validate_only)
    print(json.dumps(report, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
