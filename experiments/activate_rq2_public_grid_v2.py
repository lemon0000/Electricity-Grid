"""Materialize the reviewed, versioned RQ2 grid activation."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

import yaml

from experiments.run_rts_gmlc_public_grid_need_dispatch_v4 import run as run_grid
from experiments.validate_rq2_public_grid_activation_v2 import CONFIG as ACTIVATION
from experiments.validate_rq2_public_grid_activation_v2 import validate

ROOT = Path(__file__).resolve().parents[1]
ACTIVATED_ROOT = ROOT / "results/execution_configs/rq2_public_successor_v2"


def _sha256(path: Path) -> str:
    import hashlib

    return hashlib.sha256(path.read_bytes()).hexdigest()


def _path(raw: object, label: str) -> Path:
    if not isinstance(raw, str) or not raw or Path(raw).is_absolute() or ".." in Path(raw).parts:
        raise ValueError(f"{label} must be repository-relative")
    return ROOT / Path(raw)


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise TypeError(f"{label} must be a mapping")
    return dict(value)


def _write_atomic(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=path.parent, prefix=f".{path.name}.", suffix=".tmp", delete=False
    ) as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def _verify_materialized_config(
    *,
    target: Path,
    activation: dict[str, Any],
    grid: dict[str, Any],
    validation: dict[str, object],
    runner_validation: dict[str, object],
) -> None:
    if not target.is_file() or target.is_symlink():
        raise ValueError("activated grid config is not an ordinary file")
    activated = _mapping(
        yaml.safe_load(target.read_text(encoding="utf-8")),
        "activated grid config",
    )
    execution = _mapping(activated.get("execution"), "activated grid execution")
    for key in (
        "formal_execution_ready",
        "independent_R4_review_passed",
        "user_formal_run_authorized",
    ):
        if execution.get(key) is not True:
            raise ValueError(f"activated grid execution gate is closed: {key}")
    template = _mapping(
        yaml.safe_load(
            _path(grid["template_path"], "grid template").read_text(encoding="utf-8")
        ),
        "grid template",
    )
    for key in ("input", "grid_source", "model", "solver", "provenance", "output"):
        if activated.get(key) != template.get(key):
            raise ValueError(f"activated grid {key} drifted")
    if execution.get("predecessor_HiGHS_checkpoint_reuse_allowed") is not False:
        raise ValueError("activated grid predecessor reuse gate drifted")
    if execution.get("require_all_blocks_resolved") is not True:
        raise ValueError("activated grid resolution gate drifted")
    if execution.get("required_environment_value") != "EXECUTION_MACHINE_CONFIRMED":
        raise ValueError("activated grid environment gate drifted")
    if execution.get("forbidden_hostnames") != ["GQPD263XH9"]:
        raise ValueError("activated grid host gate drifted")
    authority = _mapping(
        activated.get("activation_authority"),
        "activated grid activation authority",
    )
    expected_authority = {
        "activation_path": "configs/rq2_public_grid_need_activation_v2.yaml",
        "activation_sha256": _sha256(ACTIVATION),
        "post_result_review_path": activation["pilot_post_result_review"]["receipt_path"],
        "post_result_review_sha256": activation["pilot_post_result_review"]["receipt_sha256"],
        "pilot_result_manifest_sha256": activation["pilot_evidence"]["result_manifest_sha256"],
        "grid_activation_review_path": activation["grid_activation_review"]["receipt_path"],
        "grid_activation_review_sha256": activation["grid_activation_review"]["receipt_sha256"],
    }
    if authority != expected_authority:
        raise ValueError("activated grid authority binding drifted")
    if runner_validation.get("config_sha256") != _sha256(target):
        raise ValueError("activated grid runner config hash drifted")
    if runner_validation.get("formal_execution_ready") is not True:
        raise ValueError("activated grid runner did not observe execution readiness")
    if runner_validation.get("independent_R4_review_passed") is not True:
        raise ValueError("activated grid runner did not observe review readiness")
    if runner_validation.get("user_formal_run_authorized") is not True:
        raise ValueError("activated grid runner did not observe user authorization")
    if runner_validation.get("power_system_block_count") != grid["expected_block_count"]:
        raise ValueError("activated grid runner block count drifted")
    if validation.get("activation_subject_sha256") is None:
        raise ValueError("activation subject digest is missing")


def activate(activation_path: Path = ACTIVATION) -> dict[str, object]:
    if activation_path.resolve() != ACTIVATION.resolve():
        raise ValueError("only canonical grid activation v2 is accepted")
    validation = validate()
    activation = _mapping(yaml.safe_load(ACTIVATION.read_text(encoding="utf-8")), "activation")
    grid = _mapping(activation["grid_stage"], "grid_stage")
    template_path = _path(grid["template_path"], "grid template")
    template = _mapping(yaml.safe_load(template_path.read_text(encoding="utf-8")), "grid template")
    execution = _mapping(template["execution"], "grid template execution")
    if execution.get("formal_execution_ready") is not False or execution.get("independent_R4_review_passed") is not False:
        raise ValueError("frozen grid template is already activated")
    checkpoint = _path(grid["checkpoint_directory"], "checkpoint directory")
    output = _path(grid["output_directory"], "output directory")
    if checkpoint.exists() or output.exists():
        raise FileExistsError("grid checkpoint/output directory must not preexist")
    target = _path(grid["activated_config_path"], "activated grid config")
    record_target = _path(grid["activation_record_path"], "grid activation record")
    if target.parent != ACTIVATED_ROOT or record_target.parent != ACTIVATED_ROOT:
        raise ValueError("activated grid targets must remain in the canonical successor root")
    if ACTIVATED_ROOT.exists():
        raise FileExistsError("activated successor root must not preexist")
    if target.exists() or record_target.exists():
        raise FileExistsError("activated grid config already exists")
    execution["formal_execution_ready"] = True
    execution["independent_R4_review_passed"] = True
    execution["user_formal_run_authorized"] = True
    execution["predecessor_HiGHS_checkpoint_reuse_allowed"] = False
    template["execution"] = execution
    template["activation_authority"] = {
        "activation_path": "configs/rq2_public_grid_need_activation_v2.yaml",
        "activation_sha256": _sha256(ACTIVATION),
        "post_result_review_path": activation["pilot_post_result_review"]["receipt_path"],
        "post_result_review_sha256": activation["pilot_post_result_review"]["receipt_sha256"],
        "pilot_result_manifest_sha256": activation["pilot_evidence"]["result_manifest_sha256"],
        "grid_activation_review_path": activation["grid_activation_review"]["receipt_path"],
        "grid_activation_review_sha256": activation["grid_activation_review"]["receipt_sha256"],
    }
    ACTIVATED_ROOT.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", dir=ACTIVATED_ROOT, prefix=".grid.", suffix=".yaml", delete=False
    ) as handle:
        yaml.safe_dump(template, handle, sort_keys=False)
        temporary = Path(handle.name)
    try:
        temporary.replace(target)
        runner_validation = run_grid(target, validate_only=True)
        _verify_materialized_config(
            target=target,
            activation=activation,
            grid=grid,
            validation=validation,
            runner_validation=runner_validation,
        )
        record = {
            "schema": "rq2_public_grid_stage_activation_v2",
            "stage": "grid_need_dispatch_v4",
            "activation_path": "configs/rq2_public_grid_need_activation_v2.yaml",
            "activation_sha256": _sha256(ACTIVATION),
            "grid_activation_review_path": activation["grid_activation_review"]["receipt_path"],
            "grid_activation_review_sha256": activation["grid_activation_review"]["receipt_sha256"],
            "activation_subject_sha256": validation["activation_subject_sha256"],
            "activated_config_path": grid["activated_config_path"],
            "activation_record_path": grid["activation_record_path"],
            "activated_config_sha256": _sha256(target),
            "template_path": grid["template_path"],
            "template_sha256": grid["template_sha256"],
            "pilot_result_manifest_sha256": activation["pilot_evidence"]["result_manifest_sha256"],
            "formal_execution_ready": True,
            "pairwise_replay_ready": False,
            "identification_ready": False,
            "security_certified": False,
            "runner_validate_only": runner_validation,
            "validation": validation,
        }
        _write_atomic(record_target, record)
    except Exception:
        target.unlink(missing_ok=True)
        record_target.unlink(missing_ok=True)
        raise
    written_record = _mapping(
        json.loads(record_target.read_text(encoding="utf-8")),
        "grid activation record",
    )
    if written_record != record:
        target.unlink(missing_ok=True)
        record_target.unlink(missing_ok=True)
        raise ValueError("grid activation record changed after publication")
    return record


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--activation", type=Path, default=ACTIVATION)
    args = parser.parse_args()
    print(json.dumps(activate(args.activation), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
