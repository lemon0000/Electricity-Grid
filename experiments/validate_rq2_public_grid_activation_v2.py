"""Validate the versioned RQ2 grid activation without solver or result writes."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

from experiments.validate_rq2_public_solver_confirmatory_pilot_v4 import (
    validate as validate_pilot,
)

ROOT = Path(__file__).resolve().parents[1]
CONFIG_RELATIVE = "configs/rq2_public_grid_need_activation_v2.yaml"
CONFIG = ROOT / CONFIG_RELATIVE
REVIEW_RELATIVE = (
    "configs/rq2_public_solver_confirmatory_pilot_post_result_review_pass_v1.yaml"
)
GRID_REVIEW_RELATIVE = "configs/rq2_public_grid_activation_review_pass_v1.yaml"
TEMPLATE_RELATIVE = "configs/rts_gmlc_public_grid_need_dispatch_v4.yaml"
RUNNER_RELATIVE = "experiments/run_rts_gmlc_public_grid_need_dispatch_v4.py"
VALIDATOR_RELATIVE = "experiments/validate_rq2_public_grid_activation_v2.py"
ACTIVATOR_RELATIVE = "experiments/activate_rq2_public_grid_v2.py"
TEST_RELATIVE = "tests/test_rq2_public_grid_activation_v2.py"
CONTRACT_RELATIVE = "configs/rq2_public_pipeline_provenance_contract_v3.yaml"
INPUT_PACKAGE_RELATIVE = (
    "data/processed/model_inputs/rts_gmlc_public_power_system_blocks_v4"
)
SOURCE_MANIFEST_RELATIVE = "data/raw/rts_gmlc/v0.2.3/upstream/SHA256SUMS"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _mapping(value: object, label: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TypeError(f"{label} must be a mapping")
    return dict(value)


def _load_yaml(path: Path, label: str) -> dict[str, Any]:
    return _mapping(yaml.safe_load(path.read_text(encoding="utf-8")), label)


def _load_json(path: Path, label: str) -> dict[str, Any]:
    return _mapping(json.loads(path.read_text(encoding="utf-8")), label)


def _canonical_sha256(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _activation_subject(config: Mapping[str, Any]) -> dict[str, Any]:
    """Return the config contract covered by the independent grid review.

    The review receipt stores this digest instead of the final config hash so
    adding the receipt binding does not create a circular hash dependency.
    """

    return {
        key: config[key]
        for key in (
            "schema",
            "version",
            "status",
            "authorized_on",
            "user_authority",
            "pilot_post_result_review",
            "pilot_evidence",
            "frozen_scientific_authority",
            "grid_stage",
            "downstream",
            "execution",
            "claims",
        )
    }


def _activation_subject_sha256(config: Mapping[str, Any]) -> str:
    return _canonical_sha256(_activation_subject(config))


def _repo_path(raw: object, label: str) -> Path:
    if not isinstance(raw, str) or not raw or raw.startswith(("/", "\\")):
        raise ValueError(f"{label} must be repository-relative")
    path = Path(raw)
    if path.is_absolute() or ".." in path.parts:
        raise ValueError(f"{label} must not escape repository")
    return ROOT / path


def _require_hash(path: Path, expected: object, label: str) -> None:
    if not isinstance(expected, str) or len(expected) != 64:
        raise ValueError(f"{label} must be a SHA-256 digest")
    if not path.is_file() or path.is_symlink():
        raise ValueError(f"{label} is not an ordinary file")
    if _sha256(path) != expected:
        raise ValueError(f"{label} drifted")


def _verify_result_members(result_root: Path, expected_manifest_sha: str) -> None:
    manifest_path = result_root / "SHA256SUMS.json"
    _require_hash(manifest_path, expected_manifest_sha, "pilot result manifest")
    manifest = _load_json(manifest_path, "pilot result manifest")
    if len(manifest) != 13:
        raise ValueError("pilot result member count drifted")
    for relative, digest in manifest.items():
        member = result_root / relative
        if not member.is_file() or member.is_symlink():
            raise ValueError(f"pilot result member is not an ordinary file: {relative}")
        _require_hash(member, digest, f"pilot result member {relative}")


def _verify_review_receipt(config: Mapping[str, Any]) -> None:
    review = _mapping(config["pilot_post_result_review"], "pilot_post_result_review")
    if review["receipt_path"] != REVIEW_RELATIVE or review["verdict"] != "PASS":
        raise ValueError("post-result review authority is not PASS")
    receipt_path = _repo_path(review["receipt_path"], "review receipt path")
    _require_hash(receipt_path, review["receipt_sha256"], "review receipt")
    receipt = _load_yaml(receipt_path, "post-result review receipt")
    if receipt.get("schema") != "rq2_public_solver_confirmatory_pilot_post_result_review_v1":
        raise ValueError("post-result review receipt schema drifted")
    if receipt.get("reviewer_role") != "independent_sol_reviewer" or receipt.get("verdict") != "PASS":
        raise ValueError("post-result review receipt verdict drifted")
    reviewed = _mapping(receipt["reviewed_result"], "reviewed_result")
    expected = _mapping(config["pilot_evidence"], "pilot_evidence")
    binding_pairs = (
        ("result_directory", "result_directory"),
        ("result_manifest_path", "result_manifest_path"),
        ("result_manifest_sha256", "result_manifest_sha256"),
        ("summary_path", "summary_path"),
        ("summary_sha256", "summary_sha256"),
        ("semantic_validation_path", "semantic_validation_path"),
        ("semantic_validation_sha256", "semantic_validation_sha256"),
        ("controller_receipt_path", "controller_receipt_path"),
        ("controller_receipt_sha256", "controller_receipt_sha256"),
        ("runs_path", "runs_path"),
        ("runs_sha256", "runs_sha256"),
        ("pilot_config_path", "config_path"),
        ("pilot_config_sha256", "config_sha256"),
        ("pilot_runner_path", "runner_path"),
        ("pilot_runner_sha256", "runner_sha256"),
        ("semantic_authority_manifest_sha256", "semantic_authority_manifest_sha256"),
        ("v3_outer_sha256", "v3_outer_sha256"),
    )
    for receipt_key, config_key in binding_pairs:
        if reviewed.get(receipt_key) != expected.get(config_key):
            raise ValueError(f"post-result receipt binding drifted: {config_key}")
    assertions = _mapping(receipt["assertions"], "post-result assertions")
    for key in (
        "fresh_execution_passed",
        "durable_process_provenance_verified",
        "nested_worker_reports_reconstructed_independently",
        "runs_reconstructed_exactly_from_worker_payloads",
        "semantic_contract_passed",
        "confirmatory_pilot_executed",
        "cross_solver_confirmation_completed",
    ):
        if assertions.get(key) is not True:
            raise ValueError(f"post-result assertion is not true: {key}")
    for key in ("formal_grid_execution_started", "formal_result_exists", "claim", "security_certified"):
        if assertions.get(key) is not False:
            raise ValueError(f"post-result claim gate drifted: {key}")
    effect = _mapping(receipt["effect"], "post-result effect")
    if effect.get("pilot_result_is_confirmatory_only") is not True:
        raise ValueError("post-result effect scope drifted")
    if effect.get("opens_grid_activation_review_only") is not True:
        raise ValueError("post-result review did not open grid activation review")
    if effect.get("grid_pairwise_identification_formal_or_security_authorized") is not False:
        raise ValueError("post-result effect opened a downstream gate")


def _verify_grid_review_receipt(
    config: Mapping[str, Any],
    frozen: Mapping[str, Any],
    grid: Mapping[str, Any],
) -> None:
    review = _mapping(config["grid_activation_review"], "grid_activation_review")
    if review.get("receipt_path") != GRID_REVIEW_RELATIVE:
        raise ValueError("grid activation review receipt path drifted")
    if review.get("verdict") != "PASS" or review.get("reviewer_role") != "independent_sol_reviewer":
        raise ValueError("grid activation review authority is not PASS")
    receipt_path = _repo_path(review["receipt_path"], "grid review receipt path")
    _require_hash(receipt_path, review.get("receipt_sha256"), "grid review receipt")
    receipt = _load_yaml(receipt_path, "grid activation review receipt")
    if receipt.get("schema") != "rq2_public_grid_activation_review_v1":
        raise ValueError("grid activation review receipt schema drifted")
    if receipt.get("reviewer_role") != "independent_sol_reviewer" or receipt.get("verdict") != "PASS":
        raise ValueError("grid activation review receipt verdict drifted")

    reviewed_subject = _mapping(receipt["reviewed_subject"], "reviewed_subject")
    if reviewed_subject.get("config_path") != CONFIG_RELATIVE:
        raise ValueError("grid activation review config binding drifted")
    if reviewed_subject.get("activation_subject_sha256") != _activation_subject_sha256(config):
        raise ValueError("grid activation review subject drifted")
    materialization = _mapping(
        receipt["materialization_contract"],
        "materialization_contract",
    )
    expected_materialization = {
        "activated_config_path": grid["activated_config_path"],
        "activation_record_path": grid["activation_record_path"],
        "runner_path": grid["runner_path"],
        "runner_invocation": (
            "python -m experiments.run_rts_gmlc_public_grid_need_dispatch_v4 "
            f"--config {grid['activated_config_path']} --validate-only"
        ),
        "solver_calls": 0,
        "result_files_written": 0,
    }
    if materialization != expected_materialization:
        raise ValueError("grid activation materialization contract drifted")

    expected_artifacts = {
        "grid_template": (grid["template_path"], grid["template_sha256"]),
        "grid_runner": (grid["runner_path"], grid["runner_sha256"]),
        "grid_validator": (VALIDATOR_RELATIVE, _sha256(ROOT / VALIDATOR_RELATIVE)),
        "grid_activator": (ACTIVATOR_RELATIVE, _sha256(ROOT / ACTIVATOR_RELATIVE)),
        "activation_tests": (TEST_RELATIVE, _sha256(ROOT / TEST_RELATIVE)),
        "provenance_contract": (
            frozen["provenance_contract_path"],
            frozen["provenance_contract_sha256"],
        ),
        "preregistration": (
            frozen["preregistration_path"],
            frozen["preregistration_sha256"],
        ),
        "input_package_manifest": (
            f"{frozen['input_package_path']}/SHA256SUMS.json",
            frozen["input_package_manifest_sha256"],
        ),
        "source_manifest": (
            frozen["source_manifest_path"],
            frozen["source_manifest_sha256"],
        ),
        "pilot_result_manifest": (
            config["pilot_evidence"]["result_manifest_path"],
            config["pilot_evidence"]["result_manifest_sha256"],
        ),
    }
    artifacts = _mapping(receipt["reviewed_artifacts"], "reviewed_artifacts")
    if set(artifacts) != set(expected_artifacts):
        raise ValueError("grid activation reviewed artifact set drifted")
    for name, (expected_path, expected_sha) in expected_artifacts.items():
        item = _mapping(artifacts[name], f"reviewed_artifacts.{name}")
        if item.get("path") != expected_path or item.get("sha256") != expected_sha:
            raise ValueError(f"grid activation reviewed artifact binding drifted: {name}")
        _require_hash(_repo_path(expected_path, f"reviewed {name}"), expected_sha, f"reviewed {name}")

    assertions = _mapping(receipt["assertions"], "grid activation review assertions")
    required_true = (
        "frozen_template_execution_closed",
        "activated_config_is_materialized_by_activator",
        "activated_config_binds_review_receipt",
        "activated_root_preexistence_fail_closed",
        "checkpoint_output_preexistence_fail_closed",
        "predecessor_checkpoint_reuse_disabled",
        "require_all_blocks_resolved",
        "required_environment_and_host_contract_declared",
        "downstream_stage_order_and_upstream_gate_closed",
        "source_manifest_frozen",
        "no_solver_or_result_writes_during_activation",
    )
    for key in required_true:
        if assertions.get(key) is not True:
            raise ValueError(f"grid activation review assertion is not true: {key}")
    effect = _mapping(receipt["effect"], "grid activation review effect")
    expected_effect = {
        "opens_grid_activation_only": True,
        "does_not_execute_solver": True,
        "pairwise_identification_remain_closed": True,
        "formal_result_claim_security_remain_false": True,
    }
    if effect != expected_effect:
        raise ValueError("grid activation review effect drifted")


def validate(config_path: Path = CONFIG) -> dict[str, object]:
    if config_path.resolve() != CONFIG.resolve():
        raise ValueError("only canonical grid activation v2 is accepted")
    config = _load_yaml(CONFIG, "grid activation config")
    expected_top_level = {
        "schema",
        "version",
        "status",
        "authorized_on",
        "user_authority",
        "pilot_post_result_review",
        "pilot_evidence",
        "frozen_scientific_authority",
        "grid_stage",
        "grid_activation_review",
        "downstream",
        "execution",
        "claims",
    }
    if set(config) != expected_top_level:
        raise ValueError("grid activation top-level contract drifted")
    if config.get("schema") != "rq2_public_grid_need_activation_v2":
        raise ValueError("grid activation schema drifted")
    if config.get("status") != "reviewed_successor_grid_activation":
        raise ValueError("grid activation status drifted")
    user = _mapping(config["user_authority"], "user_authority")
    if (
        user.get("explicit_authorization_observed") is not True
        or user.get("authorization_record")
        != "我给你完整授权，把所有东西配置好然后开始实验吧"
        or user.get("authorized_scope")
        != "formal_rq2_pipeline_in_registered_stage_order"
    ):
        raise ValueError("user formal authorization is missing")
    pilot = _mapping(config["pilot_evidence"], "pilot_evidence")
    result_root = _repo_path(pilot["result_directory"], "pilot result directory")
    _verify_result_members(result_root, str(pilot["result_manifest_sha256"]))
    pilot_report = validate_pilot()
    if pilot_report.get("result_manifest_sha256") != pilot["result_manifest_sha256"]:
        raise ValueError("pilot validator manifest binding drifted")
    if pilot_report.get("confirmatory_pilot_executed") is not True or pilot_report.get("cross_solver_confirmation_completed") is not True:
        raise ValueError("pilot confirmation gate is incomplete")
    for name, path_key, hash_key in (
        ("summary", "summary_path", "summary_sha256"),
        ("semantic validation", "semantic_validation_path", "semantic_validation_sha256"),
        ("controller receipt", "controller_receipt_path", "controller_receipt_sha256"),
        ("runs", "runs_path", "runs_sha256"),
        ("pilot config", "config_path", "config_sha256"),
        ("pilot runner", "runner_path", "runner_sha256"),
    ):
        _require_hash(_repo_path(pilot[path_key], f"pilot {name} path"), pilot[hash_key], f"pilot {name}")
    _verify_review_receipt(config)

    frozen = _mapping(config["frozen_scientific_authority"], "frozen_scientific_authority")
    for key, relative in (
        ("preregistration_path", "configs/rq2_public_data_robust_identification_preregistration_v6.yaml"),
        ("provenance_contract_path", CONTRACT_RELATIVE),
        ("input_package_path", INPUT_PACKAGE_RELATIVE),
    ):
        if frozen[key] != relative:
            raise ValueError(f"frozen authority path drifted: {key}")
        path = _repo_path(relative, key)
        if key == "input_package_path":
            manifest_path = path / "SHA256SUMS.json"
            _require_hash(manifest_path, frozen["input_package_manifest_sha256"], "input package manifest")
        else:
            expected_key = "preregistration_sha256" if key == "preregistration_path" else "provenance_contract_sha256"
            _require_hash(path, frozen[expected_key], key)
    if frozen.get("source_manifest_path") != SOURCE_MANIFEST_RELATIVE:
        raise ValueError("source manifest path drifted")
    _require_hash(
        _repo_path(SOURCE_MANIFEST_RELATIVE, "source manifest"),
        frozen.get("source_manifest_sha256"),
        "source manifest",
    )
    grid = _mapping(config["grid_stage"], "grid_stage")
    if grid["stage"] != "grid_need_dispatch_v4":
        raise ValueError("grid stage name drifted")
    template = _repo_path(grid["template_path"], "grid template path")
    _require_hash(template, grid["template_sha256"], "grid template")
    _require_hash(_repo_path(grid["runner_path"], "grid runner path"), grid["runner_sha256"], "grid runner")
    _require_hash(_repo_path(grid["provenance_contract_path"], "grid provenance path"), grid["provenance_contract_sha256"], "grid provenance")
    template_config = _load_yaml(template, "grid template")
    template_execution = _mapping(template_config["execution"], "grid template execution")
    if template_execution.get("formal_execution_ready") is not False or template_execution.get("independent_R4_review_passed") is not False:
        raise ValueError("frozen grid template execution gate was opened")
    if template_execution.get("user_formal_run_authorized") is not True:
        raise ValueError("frozen grid template user authorization drifted")
    if template_execution.get("require_all_blocks_resolved") is not True:
        raise ValueError("frozen grid template resolution gate drifted")
    if template_execution.get("required_environment_value") != "EXECUTION_MACHINE_CONFIRMED":
        raise ValueError("frozen grid template environment gate drifted")
    if template_execution.get("forbidden_hostnames") != ["GQPD263XH9"]:
        raise ValueError("frozen grid template host gate drifted")
    if template_execution.get("checkpoint_directory") != grid["checkpoint_directory"]:
        raise ValueError("grid checkpoint path disagrees with template")
    if template_config.get("output", {}).get("directory") != grid["output_directory"]:
        raise ValueError("grid output path disagrees with template")
    if grid["expected_block_count"] != 1071:
        raise ValueError("grid block count drifted")
    checkpoint = _repo_path(grid["checkpoint_directory"], "grid checkpoint directory")
    output = _repo_path(grid["output_directory"], "grid output directory")
    if grid.get("checkpoint_directory_must_not_preexist") is not True or grid.get("output_directory_must_not_preexist") is not True:
        raise ValueError("grid preexistence gates drifted")
    if checkpoint.exists() or output.exists():
        raise ValueError("grid checkpoint/output directory must be absent before activation")
    activated_config = _repo_path(grid["activated_config_path"], "activated grid config path")
    activation_record = _repo_path(grid["activation_record_path"], "grid activation record path")
    if grid.get("activated_root_must_not_preexist") is not True:
        raise ValueError("activated root preexistence gate drifted")
    if activated_config.parent.exists():
        raise ValueError("activated successor root must be absent before activation")
    if activated_config.exists() or activation_record.exists():
        raise ValueError("activated grid config must not preexist before activation")
    execution = _mapping(config["execution"], "activation execution")
    for key in ("independent_R4_review_passed", "formal_execution_ready", "user_formal_run_authorized"):
        if execution.get(key) is not True:
            raise ValueError(f"activation execution gate is closed: {key}")
    if execution.get("predecessor_HiGHS_checkpoint_reuse_allowed") is not False or execution.get("require_all_blocks_resolved") is not True:
        raise ValueError("activation fail-closed execution fields drifted")
    if frozen.get("source_manifest_sha256") != "95c1294626cdf00ee029659108bf1f30d4ec176a258192b784f097462226a914":
        raise ValueError("RTS-GMLC source manifest binding drifted")
    downstream = _mapping(config["downstream"], "downstream")
    if downstream.get("pairwise_replay_ready") is not False or downstream.get("identification_ready") is not False:
        raise ValueError("downstream stage opened prematurely")
    if downstream.get("activation_requires_verified_upstream_package") is not True:
        raise ValueError("downstream upstream-package gate drifted")
    if downstream.get("stage_order") != ["grid", "pairwise", "identification"]:
        raise ValueError("downstream stage order drifted")
    claims = _mapping(config["claims"], "claims")
    expected_claim_keys = {
        "formal_result_exists",
        "empirical_outage_probability",
        "full_N_minus_one",
        "AC_security",
        "security_certified",
        "paper_claim",
    }
    if set(claims) != expected_claim_keys or any(claims.get(key) is not False for key in claims):
        raise ValueError("claim gate drifted")
    _verify_grid_review_receipt(config, frozen, grid)
    return {
        "schema": "rq2_public_grid_activation_validation_v2",
        "config_sha256": _sha256(CONFIG),
        "pilot_result_manifest_sha256": pilot["result_manifest_sha256"],
        "pilot_post_result_review_sha256": config["pilot_post_result_review"]["receipt_sha256"],
        "grid_activation_review_sha256": config["grid_activation_review"]["receipt_sha256"],
        "activation_subject_sha256": _activation_subject_sha256(config),
        "grid_template_sha256": grid["template_sha256"],
        "grid_runner_sha256": grid["runner_sha256"],
        "activated_config_path": grid["activated_config_path"],
        "activation_record_path": grid["activation_record_path"],
        "activated_root_must_not_preexist": grid["activated_root_must_not_preexist"],
        "expected_block_count": grid["expected_block_count"],
        "solver_calls": 0,
        "result_files_written": 0,
        "formal_execution_ready": True,
        "pairwise_replay_ready": False,
        "identification_ready": False,
        "security_certified": False,
        "validation_passed": True,
    }


def main() -> None:
    print(json.dumps(validate(), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
