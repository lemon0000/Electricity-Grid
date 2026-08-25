"""Create stage-local activated configs from verified RQ2 successor evidence."""

from __future__ import annotations

import argparse
import json
import tempfile
from pathlib import Path
from typing import Any

import yaml

from src.evaluation.rq2_provenance_v3 import load_json_strict, sha256_file

_ROOT = Path(__file__).resolve().parents[1]
_ACTIVATION_SCHEMA = "rq2_public_successor_activation_v1"
_OUTPUT_ROOT = _ROOT / "results/execution_configs/rq2_public_successor_v1"


def _path(raw: object, label: str) -> Path:
    if not isinstance(raw, str) or not raw:
        raise ValueError(f"{label} must be a nonempty path")
    path = Path(raw)
    return path if path.is_absolute() else _ROOT / path


def _verified_json_package(
    directory: Path,
    *,
    payload_name: str = "summary.json",
) -> tuple[str, dict[str, Any]]:
    manifest_path = directory / "SHA256SUMS.json"
    manifest_sha = sha256_file(manifest_path)
    manifest = load_json_strict(manifest_path)
    if not isinstance(manifest, dict) or not manifest:
        raise ValueError(f"invalid package manifest: {directory}")
    for name, expected in manifest.items():
        member = directory / name
        if not member.is_file() or sha256_file(member) != expected:
            raise ValueError(f"package member drifted: {member}")
    payload = load_json_strict(directory / payload_name)
    if not isinstance(payload, dict):
        raise TypeError(f"package payload is invalid: {directory}")
    return manifest_sha, payload


def _verify_runtime_preflight(payload: dict[str, Any]) -> dict[str, Any]:
    preflight = payload["runtime_preflight"]
    if preflight["required"] is not True or preflight["passed"] is not True:
        raise RuntimeError("executor runtime preflight has not passed")
    root = _path(
        preflight["result_directory"],
        "runtime_preflight.result_directory",
    )
    manifest_sha, report = _verified_json_package(
        root,
        payload_name="preflight.json",
    )
    manifest = load_json_strict(root / "SHA256SUMS.json")
    successor = payload["successor"]
    bundle = report.get("bundle", {})
    bundle_path = _path(
        bundle.get("bundle_manifest_path"),
        "runtime_preflight.bundle_manifest_path",
    )
    smokes = report.get("solver_smokes")
    if (
        manifest_sha != preflight["result_manifest_sha256"]
        or set(manifest) != {"config.yaml", "preflight.json"}
        or report.get("schema") != "rq2_public_executor_preflight_v1"
        or report.get("config_sha256")
        != successor["executor_handoff_sha256"]
        or sha256_file(bundle_path) != bundle.get("bundle_manifest_sha256")
        or report.get("formal_execution_started") is not False
        or report.get("environment", {}).get("matches_executor_lock") is not True
        or report.get("execution_host", {}).get("hostname_allowed") is not True
        or report.get("execution_host", {}).get("environment_authorized")
        is not True
        or not isinstance(smokes, list)
        or {item.get("solver_name") for item in smokes}
        != {"highs", "gurobi"}
        or any(
            item.get("termination_condition")
            not in {"optimal", "globallyOptimal"}
            or item.get("objective_incumbent") != 1.0
            or item.get("lower_bound") != 1.0
            or item.get("upper_bound") != 1.0
            or item.get("model_variables") != 1
            or item.get("model_constraints") != 1
            for item in smokes
        )
    ):
        raise RuntimeError("executor runtime preflight evidence is invalid")
    return report


def _activation(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if (
        not isinstance(payload, dict)
        or payload.get("schema") != _ACTIVATION_SCHEMA
    ):
        raise ValueError("successor activation schema drifted")
    successor = payload["successor"]
    preregistration = _path(
        successor["preregistration_path"],
        "successor.preregistration_path",
    )
    contract = _path(
        successor["provenance_contract_path"],
        "successor.provenance_contract_path",
    )
    if (
        sha256_file(preregistration) != successor["preregistration_sha256"]
        or sha256_file(contract) != successor["provenance_contract_sha256"]
    ):
        raise ValueError("successor activation authority drifted")
    handoff = _path(
        successor["executor_handoff_path"],
        "successor.executor_handoff_path",
    )
    if sha256_file(handoff) != successor["executor_handoff_sha256"]:
        raise ValueError("executor handoff authority drifted")
    review = payload["review"]
    if review["independent_R4_review_passed"] is not True:
        raise RuntimeError("independent R4 review has not passed")
    review_path = _path(review["review_path"], "review.review_path")
    if sha256_file(review_path) != review["review_sha256"]:
        raise ValueError("independent R4 review artifact drifted")
    preflight_report = _verify_runtime_preflight(payload)
    pilot = payload["solver_pilot"]
    pilot_config = _path(pilot["config_path"], "solver_pilot.config_path")
    if sha256_file(pilot_config) != pilot["config_sha256"]:
        raise ValueError("cross-solver pilot config drifted")
    pilot_configuration = yaml.safe_load(
        pilot_config.read_text(encoding="utf-8")
    )
    implementation = pilot_configuration["implementation"]
    pilot_runner = _path(
        implementation["runner_path"],
        "solver_pilot.implementation.runner_path",
    )
    if sha256_file(pilot_runner) != implementation["runner_sha256"]:
        raise ValueError("cross-solver pilot implementation drifted")
    pilot_root = _path(pilot["result_directory"], "solver_pilot.result_directory")
    pilot_manifest_sha, pilot_summary = _verified_json_package(pilot_root)
    if (
        pilot_manifest_sha != pilot["result_manifest_sha256"]
        or pilot_summary.get("config_sha256") != pilot["config_sha256"]
        or pilot_summary.get("implementation_sha256")
        != implementation["runner_sha256"]
        or pilot_summary.get("bundle_manifest_sha256")
        != preflight_report["bundle"]["bundle_manifest_sha256"]
        or pilot_summary.get("gurobi_eligible_for_formal_successor") is not True
        or pilot["gurobi_eligible_for_formal_successor"] is not True
    ):
        raise RuntimeError("Gurobi cross-solver pilot gate is not satisfied")
    execution = payload["formal_execution"]
    if (
        execution["user_authorized_execution_machine"] is not True
        or execution["formal_execution_ready"] is not True
        or execution["activation_requires_new_checkpoint_directories"] is not True
        or execution["predecessor_HiGHS_checkpoint_reuse_allowed"] is not False
    ):
        raise RuntimeError("formal successor activation remains closed")
    return payload


def _template(
    handoff: dict[str, Any],
    key: str,
    activation: dict[str, Any],
    stage: str,
) -> tuple[Path, dict[str, Any]]:
    path = _path(handoff["formal_pipeline"][key], key)
    authority = activation["successor"]["stage_templates"][stage]
    authority_path = _path(authority["path"], f"stage_templates.{stage}.path")
    if path != authority_path or sha256_file(path) != authority["sha256"]:
        raise ValueError(f"{stage} stage template authority drifted")
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"invalid config template: {path}")
    return path, payload


def _enable_execution(config: dict[str, Any]) -> None:
    execution = config["execution"]
    execution["formal_execution_ready"] = True
    execution["independent_R4_review_passed"] = True


def _verify_template_authority(
    config: dict[str, Any],
    activation: dict[str, Any],
) -> None:
    successor = activation["successor"]
    if config["provenance"] != {
        "contract_path": successor["provenance_contract_path"],
        "contract_sha256": successor["provenance_contract_sha256"],
    }:
        raise ValueError("stage template provenance authority drifted")


def _write_activated(
    stage: str,
    config: dict[str, Any],
    evidence: dict[str, object],
) -> dict[str, object]:
    _OUTPUT_ROOT.mkdir(parents=True, exist_ok=True)
    target = _OUTPUT_ROOT / f"{stage}.yaml"
    record_target = _OUTPUT_ROOT / f"{stage}.activation.json"
    if target.exists() or record_target.exists():
        raise FileExistsError(f"activated stage config already exists: {stage}")
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=_OUTPUT_ROOT,
        prefix=f".{stage}.",
        suffix=".yaml",
        delete=False,
    ) as temporary:
        yaml.safe_dump(config, temporary, sort_keys=False)
        temporary_path = Path(temporary.name)
    temporary_path.replace(target)
    record = {
        "schema": "rq2_public_stage_activation_v1",
        "stage": stage,
        "config_path": str(target.relative_to(_ROOT)),
        "config_sha256": sha256_file(target),
        "evidence": evidence,
    }
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=_OUTPUT_ROOT,
        prefix=f".{stage}.",
        suffix=".json",
        delete=False,
    ) as temporary:
        json.dump(record, temporary, indent=2, sort_keys=True)
        temporary.write("\n")
        record_path = Path(temporary.name)
    record_path.replace(record_target)
    return record


def activate(
    stage: str,
    *,
    handoff_path: Path,
    activation_path: Path,
) -> dict[str, object]:
    activation = _activation(activation_path.resolve())
    handoff_authority = _path(
        activation["successor"]["executor_handoff_path"],
        "successor.executor_handoff_path",
    )
    if (
        handoff_path.resolve() != handoff_authority
        or sha256_file(handoff_path.resolve())
        != activation["successor"]["executor_handoff_sha256"]
    ):
        raise ValueError("executor handoff argument drifted")
    handoff = yaml.safe_load(handoff_path.resolve().read_text(encoding="utf-8"))
    if (
        not isinstance(handoff, dict)
        or handoff.get("schema") != "rq2_public_executor_handoff_config_v1"
    ):
        raise ValueError("executor handoff config schema drifted")
    formal = activation["formal_execution"]
    if stage == "grid":
        if formal["grid_need_dispatch_ready"] is not True:
            raise RuntimeError("grid activation gate remains closed")
        template_path, config = _template(
            handoff,
            "grid_config_template",
            activation,
            stage,
        )
        _verify_template_authority(config, activation)
        _enable_execution(config)
        checkpoint = _path(
            config["execution"]["checkpoint_directory"],
            "grid checkpoint directory",
        )
        if checkpoint.exists():
            raise FileExistsError(
                "new Gurobi grid checkpoint directory must not preexist"
            )
        return _write_activated(
            stage,
            config,
            {
                "template_path": str(template_path.relative_to(_ROOT)),
                "template_sha256": sha256_file(template_path),
                "pilot_manifest_sha256": activation["solver_pilot"][
                    "result_manifest_sha256"
                ],
            },
        )
    if stage == "pairwise":
        if formal["pairwise_replay_ready"] is not True:
            raise RuntimeError("pairwise activation gate remains closed")
        grid_root = _path(
            handoff["formal_pipeline"]["grid_result_directory"],
            "grid_result_directory",
        )
        grid_manifest_sha, grid_summary = _verified_json_package(grid_root)
        if grid_summary.get("all_blocks_resolved") is not True:
            raise RuntimeError("grid package is not fully resolved")
        template_path, config = _template(
            handoff,
            "pairwise_config_template",
            activation,
            stage,
        )
        _verify_template_authority(config, activation)
        config["input"]["grid_need_dispatch_ready"] = True
        config["input"]["power_system_dispatch_manifest_sha256"] = (
            grid_manifest_sha
        )
        config["input"]["power_system_dispatch_config_sha256"] = (
            grid_summary["config_sha256"]
        )
        _enable_execution(config)
        return _write_activated(
            stage,
            config,
            {
                "template_path": str(template_path.relative_to(_ROOT)),
                "template_sha256": sha256_file(template_path),
                "grid_manifest_sha256": grid_manifest_sha,
                "grid_provenance_sha256": grid_summary["provenance_sha256"],
            },
        )
    if stage == "identification":
        if formal["identification_ready"] is not True:
            raise RuntimeError("identification activation gate remains closed")
        pairwise_root = _path(
            handoff["formal_pipeline"]["pairwise_result_directory"],
            "pairwise_result_directory",
        )
        pairwise_manifest_sha, pairwise_summary = _verified_json_package(
            pairwise_root
        )
        if (
            pairwise_summary.get("all_eligible_pairwise_outcomes_resolved")
            is not True
        ):
            raise RuntimeError("pairwise package is not fully resolved")
        template_path, config = _template(
            handoff,
            "identification_config_template",
            activation,
            stage,
        )
        _verify_template_authority(config, activation)
        config["input"]["pairwise_replay_ready"] = True
        config["input"]["pairwise_replay_manifest_sha256"] = (
            pairwise_manifest_sha
        )
        config["input"]["expected_pairwise_config_sha256"] = pairwise_summary[
            "config_sha256"
        ]
        config["input"]["expected_power_system_dispatch_manifest_sha256"] = (
            pairwise_summary["power_system_dispatch_manifest_sha256"]
        )
        config["input"]["expected_power_system_dispatch_provenance_sha256"] = (
            pairwise_summary["power_system_dispatch_provenance_sha256"]
        )
        _enable_execution(config)
        return _write_activated(
            stage,
            config,
            {
                "template_path": str(template_path.relative_to(_ROOT)),
                "template_sha256": sha256_file(template_path),
                "pairwise_manifest_sha256": pairwise_manifest_sha,
                "pairwise_provenance_sha256": pairwise_summary[
                    "provenance_sha256"
                ],
            },
        )
    raise ValueError("stage must be grid, pairwise, or identification")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("grid", "pairwise", "identification"))
    parser.add_argument(
        "--handoff",
        type=Path,
        default=Path("configs/rq2_public_executor_handoff_v1.yaml"),
    )
    parser.add_argument(
        "--activation",
        type=Path,
        default=Path("configs/rq2_public_successor_activation_v1.yaml"),
    )
    args = parser.parse_args()
    print(
        json.dumps(
            activate(
                args.stage,
                handoff_path=args.handoff,
                activation_path=args.activation,
            ),
            indent=2,
            sort_keys=True,
        )
    )


if __name__ == "__main__":
    main()
