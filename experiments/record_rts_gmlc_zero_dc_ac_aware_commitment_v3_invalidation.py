from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from experiments.process_google_power_workload_day0 import (
    _verify_manifest as _verify_output_manifest,
)
from experiments.run_rts_gmlc_multi_poi_scan import _publish_payload
from src.scenarios.common_input_signature import common_input_signature_sha256

_OUTPUT_ROOT = Path(
    "results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v3"
)
_CONFIG_PATH = Path("configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v3.yaml")
_ATTEMPT_ID = "formal_20260719T061959Z"
_ATTEMPT_LOG_ROOT = (
    Path("results/logs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v3")
    / _ATTEMPT_ID
)
_CHECKPOINT_RELATIVE = Path("candidate_checkpoints/01_q_proxy_delta_0p0010")

_EXPECTED_PREREGISTRATION_MANIFEST_SHA256 = (
    "01646721d15395668bf0079cb6fe218dc0625187d1fbf108c5db74e47ae33f88"
)
_EXPECTED_INPUT_CONTRACT_SHA256 = (
    "af4a388d80c211611a8e1dad3861936decb7f3c3e2de3a422116c87c013d8aa0"
)
_EXPECTED_CONFIG_SHA256 = (
    "68c89f2e2a14143e0c5581bff86193a530b935a57cdc388abbbf2806d27b95ba"
)
_EXPECTED_RUNNER_SHA256 = (
    "f421465fbf2415fc98fd0f3b8f2022215afd923613ad315f2fb620f64d79cbfb"
)
_EXPECTED_CHECKPOINT_MANIFEST_SHA256 = (
    "e2f4e8849985cce5a72e2f9ad9ce906231c589e0d605b3f6dfbccc3df36e83bc"
)
_EXPECTED_CANDIDATE_JSON_SHA256 = (
    "b92a5920653b1565577fa4876893e7c319da24791187d6f40777872ac69c754c"
)
_EXPECTED_COMMITMENT_SHA256 = (
    "6838623399f5d760741aaa5e3cb395f92a87459576f5833e9753ab83347f982e"
)
_EXPECTED_STORED_DISPATCH_SHA256 = (
    "7dc7e40ca9a90cf09018db76c959a8a2dafcfae91b7183364fb3884021a4c6e3"
)
_EXPECTED_RECOMPUTED_DISPATCH_SHA256 = (
    "d50253747b3ba20adbb33c52eed4497465a369cd0f7a39f60c8608262bb13658"
)
_EXPECTED_KEY_LOG_SHA256 = {
    "attempt.json": "385de97021a4d42a2886bf3ca167178ee9dd347c7f5871aeb1854a5412c6889f",
    "progress.jsonl": "5f0782e0957fd22da55f5b068fe9b7e3a42988f7f95b8972e938b36775b2cfa0",
    "launcher.stdout.log": (
        "c0489f555d64ae23d7973d6a7cee7a2ecc8d7e3701de9e555862729935dd35c9"
    ),
    "launcher.stderr.log": (
        "fd282b9329e22797774d4e8ca9a0e0a29bf2b005aa5dcf0baf431299a475ef70"
    ),
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Expected a JSON object: {path}")
    return payload


def _write_exact_json(path: Path, payload: object) -> None:
    path.write_bytes(
        (json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        )
    )


def _commitment_sha256(commitment: object) -> str:
    if not isinstance(commitment, list) or not all(
        isinstance(row, dict) for row in commitment
    ):
        raise RuntimeError("Invalid persisted commitment payload")
    return common_input_signature_sha256(
        {
            "schema": "rts_gmlc_24h_commitment_identity_v1",
            "hours": [dict(sorted(row.items())) for row in commitment],
        }
    )


def _dispatch_sha256(candidate: dict[str, Any]) -> str:
    payload: dict[str, object] = {"schema": "rts_gmlc_24h_dc_dispatch_identity_v1"}
    for field in ("generation_mw", "branch_flows_mw", "dc_flows_mw"):
        rows = candidate.get(field)
        if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
            raise RuntimeError(f"Invalid persisted dispatch payload: {field}")
        payload[field] = [dict(sorted(row.items())) for row in rows]
    return common_input_signature_sha256(payload)


def _file_inventory(root: Path) -> tuple[dict[str, dict[str, object]], str]:
    files = sorted(path for path in root.rglob("*") if path.is_file())
    inventory = {
        path.relative_to(root).as_posix(): {
            "bytes": path.stat().st_size,
            "sha256": _sha256(path),
        }
        for path in files
    }
    encoded = json.dumps(
        inventory, allow_nan=False, separators=(",", ":"), sort_keys=True
    ).encode("utf-8")
    return inventory, hashlib.sha256(encoded).hexdigest()


def _validate_registration(output_root: Path) -> tuple[dict[str, Any], dict[Path, str]]:
    preregistration = output_root / "preregistration"
    _verify_output_manifest(preregistration)
    if _sha256(preregistration / "SHA256SUMS") != (
        _EXPECTED_PREREGISTRATION_MANIFEST_SHA256
    ):
        raise RuntimeError("V3 preregistration manifest drifted")
    registration = _read_json(preregistration / "registration.json")
    contract = registration.get("input_contract")
    if (
        registration.get("preregistration_id")
        != "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v3"
        or registration.get("input_contract_sha256") != _EXPECTED_INPUT_CONTRACT_SHA256
        or not isinstance(contract, dict)
        or contract.get("config_sha256") != _EXPECTED_CONFIG_SHA256
    ):
        raise RuntimeError("V3 preregistration identity drifted")
    implementation = contract.get("implementation_sha256")
    if (
        not isinstance(implementation, dict)
        or implementation.get(
            "experiments/run_rts_gmlc_zero_dc_ac_aware_commitment_v3.py"
        )
        != _EXPECTED_RUNNER_SHA256
    ):
        raise RuntimeError("V3 implementation identity drifted")

    snapshots = {_CONFIG_PATH: _EXPECTED_CONFIG_SHA256}
    snapshots.update(
        {Path(path): str(digest) for path, digest in implementation.items()}
    )
    for path, expected in snapshots.items():
        if not path.is_file() or _sha256(path) != expected:
            raise RuntimeError(f"Cannot snapshot drifted V3 input: {path}")
    return registration, snapshots


def _validate_checkpoint(output_root: Path) -> dict[str, Any]:
    checkpoint_root = output_root / _CHECKPOINT_RELATIVE
    checkpoint_parent = output_root / "candidate_checkpoints"
    observed_children = sorted(
        path.relative_to(checkpoint_parent).as_posix()
        for path in checkpoint_parent.iterdir()
    )
    if observed_children != [_CHECKPOINT_RELATIVE.name]:
        raise RuntimeError("V3 has an unexpected candidate checkpoint set")
    _verify_output_manifest(checkpoint_root)
    if (
        _sha256(checkpoint_root / "SHA256SUMS")
        != (_EXPECTED_CHECKPOINT_MANIFEST_SHA256)
        or _sha256(checkpoint_root / "candidate.json")
        != _EXPECTED_CANDIDATE_JSON_SHA256
    ):
        raise RuntimeError("V3 invalid checkpoint evidence drifted")

    envelope = _read_json(checkpoint_root / "candidate.json")
    candidate = envelope.get("candidate")
    if (
        envelope.get("schema") != "rts_gmlc_zero_dc_ac_aware_candidate_checkpoint_v1"
        or envelope.get("preregistration_id")
        != "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v3"
        or envelope.get("input_contract_sha256") != _EXPECTED_INPUT_CONTRACT_SHA256
        or envelope.get("ordinal") != 1
        or not isinstance(candidate, dict)
        or candidate.get("requested_candidate_id") != "q_proxy_delta_0p0010"
    ):
        raise RuntimeError("V3 invalid checkpoint contract drifted")

    stage_audits = candidate.get("stage_audits")
    if not isinstance(stage_audits, dict):
        raise RuntimeError("V3 invalid checkpoint stage audits drifted")
    for stage in ("proxy_maximization", "cost_normalization"):
        record = stage_audits.get(stage)
        if (
            not isinstance(record, dict)
            or record.get("eligible") is not True
            or record.get("eligibility_status") != "target_attained"
            or not isinstance(record.get("final_full_state_audit"), dict)
            or record["final_full_state_audit"].get("passed") is not True
        ):
            raise RuntimeError(f"V3 invalid checkpoint {stage} evidence drifted")
    regret = stage_audits.get("primary_proxy_regret")
    residual = candidate.get("residual_audit")
    if (
        not isinstance(regret, dict)
        or regret.get("passed") is not True
        or not isinstance(residual, dict)
        or residual.get("passed") is not True
    ):
        raise RuntimeError("V3 invalid checkpoint final gates drifted")

    commitment = _commitment_sha256(candidate.get("commitment"))
    dispatch = _dispatch_sha256(candidate)
    if (
        candidate.get("commitment_sha256") != _EXPECTED_COMMITMENT_SHA256
        or commitment != _EXPECTED_COMMITMENT_SHA256
        or candidate.get("dispatch_sha256") != _EXPECTED_STORED_DISPATCH_SHA256
        or dispatch != _EXPECTED_RECOMPUTED_DISPATCH_SHA256
        or dispatch == candidate.get("dispatch_sha256")
    ):
        raise RuntimeError("V3 checkpoint identity-failure evidence drifted")
    return candidate


def _validate_attempt(log_root: Path) -> tuple[dict[str, Any], dict[str, Any], str]:
    for relative, expected in _EXPECTED_KEY_LOG_SHA256.items():
        path = log_root / relative
        if not path.is_file() or _sha256(path) != expected:
            raise RuntimeError(f"V3 failure log drifted: {path}")
    attempt = _read_json(log_root / "attempt.json")
    if (
        attempt.get("attempt_id") != _ATTEMPT_ID
        or attempt.get("pid") != 39440
        or attempt.get("input_contract_sha256") != _EXPECTED_INPUT_CONTRACT_SHA256
    ):
        raise RuntimeError("V3 attempt identity drifted")

    lines = (log_root / "progress.jsonl").read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in lines]
    if not all(isinstance(event, dict) for event in events):
        raise RuntimeError("V3 progress event schema drifted")
    last = events[-1]
    budget_completions = [
        event
        for event in events
        if event.get("event") == "candidate_completed"
        and int(event.get("candidate_ordinal", 0)) > 0
    ]
    if (
        len(events) != 295
        or budget_completions
        or last.get("event") != "candidate_failed"
        or last.get("candidate_ordinal") != 1
        or last.get("requested_candidate_id") != "q_proxy_delta_0p0010"
        or last.get("error_type") != "RuntimeError"
        or last.get("error_message") != "Candidate checkpoint identity audit failed"
        or last.get("timestamp_utc") != "2026-07-19T07:22:26.179109+00:00"
    ):
        raise RuntimeError("V3 terminal progress evidence drifted")

    inventory, inventory_sha256 = _file_inventory(log_root)
    if (
        len(inventory) != 38
        or sum(int(item["bytes"]) for item in inventory.values()) != 613387
    ):
        raise RuntimeError("V3 attempt log inventory drifted")
    return attempt, last, inventory_sha256


def record_invalidation(
    *,
    output_root: Path = _OUTPUT_ROOT,
    attempt_log_root: Path = _ATTEMPT_LOG_ROOT,
) -> dict[str, Any]:
    if any(
        (output_root / name).exists() for name in ("candidate_frontier", "joint_ac")
    ):
        raise RuntimeError("V3 gained a result artifact before invalidation recording")
    allowed_top_level = {"preregistration", "candidate_checkpoints", "invalidation"}
    unexpected = {
        path.name
        for path in output_root.iterdir()
        if path.name not in allowed_top_level
    }
    if unexpected or any(path.name.startswith(".") for path in output_root.iterdir()):
        raise RuntimeError("V3 has an unexpected or hidden artifact")

    registration, snapshots = _validate_registration(output_root)
    candidate = _validate_checkpoint(output_root)
    attempt, failure, log_inventory_sha256 = _validate_attempt(attempt_log_root)
    checkpoint_root = output_root / _CHECKPOINT_RELATIVE

    payload = {
        "schema": (
            "rts_gmlc_zero_dc_ac_aware_commitment_checkpoint_serialization_"
            "invalidation_v1"
        ),
        "status": (
            "invalidated_after_one_semantically_invalid_budget_checkpoint_was_"
            "persisted_before_any_valid_budget_checkpoint_frontier_or_joint_ac_"
            "solver_call"
        ),
        "preregistration_id": registration["preregistration_id"],
        "preregistration_manifest_sha256": (_EXPECTED_PREREGISTRATION_MANIFEST_SHA256),
        "input_contract_sha256": registration["input_contract_sha256"],
        "config_sha256": _EXPECTED_CONFIG_SHA256,
        "runner_sha256": _EXPECTED_RUNNER_SHA256,
        "formal_attempt_id": _ATTEMPT_ID,
        "process_id": attempt["pid"],
        "process_started_at_utc": attempt["started_utc"],
        "failure_detected_at_utc": failure["timestamp_utc"],
        "elapsed_seconds_to_failure": failure["monotonic_elapsed_seconds"],
        "candidate_generation_invocation_started": True,
        "process_terminated_by_uncaught_exception": True,
        "failure_phase": "candidate_checkpoint_post_publish_reload_identity_audit",
        "failure_exception_type": failure["error_type"],
        "failure_exception_message": failure["error_message"],
        "failure_root_cause": (
            "checkpoint_writer_applied_nine_decimal_float_rounding_after_full_"
            "precision_dispatch_sha256_was_computed"
        ),
        "violated_candidate_snapshot_contract": {
            "continuous_values_use_full_precision": True,
            "continuous_rounding_or_clamping_allowed": False,
        },
        "first_budget_candidate_id": candidate["requested_candidate_id"],
        "first_budget_candidate_ordinal": 1,
        "first_budget_candidate_relative_cost_budget_delta": candidate[
            "relative_cost_budget_delta"
        ],
        "in_memory_candidate_passed_all_precheckpoint_gates": True,
        "proxy_stage_eligible": True,
        "cost_stage_eligible": True,
        "proxy_final_24_state_audit_passed": True,
        "cost_final_24_state_audit_passed": True,
        "primary_proxy_regret_passed": True,
        "final_candidate_residual_audit_passed": True,
        "candidate_checkpoint_directory_persisted": True,
        "partial_candidate_solution_persisted": True,
        "invalid_checkpoint_relative_path": _CHECKPOINT_RELATIVE.as_posix(),
        "invalid_checkpoint_manifest_sha256": (_EXPECTED_CHECKPOINT_MANIFEST_SHA256),
        "invalid_candidate_json_sha256": _EXPECTED_CANDIDATE_JSON_SHA256,
        "checkpoint_manifest_file_integrity_valid": True,
        "checkpoint_reload_identity_valid": False,
        "stored_commitment_sha256": _EXPECTED_COMMITMENT_SHA256,
        "recomputed_commitment_sha256": _EXPECTED_COMMITMENT_SHA256,
        "stored_dispatch_sha256": _EXPECTED_STORED_DISPATCH_SHA256,
        "recomputed_persisted_dispatch_sha256": (_EXPECTED_RECOMPUTED_DISPATCH_SHA256),
        "valid_budget_candidate_checkpoint_count": 0,
        "invalid_budget_candidate_checkpoint_count": 1,
        "budget_candidate_completed_event_count": 0,
        "candidate_frontier_artifact_published": False,
        "candidate_frontier_outcomes_observed": False,
        "joint_ac_solver_call_count": 0,
        "joint_ac_outcomes_observed": False,
        "failure_is_infeasibility_evidence": False,
        "invalid_checkpoint_is_scientific_candidate_result": False,
        "invalid_checkpoint_is_resume_eligible": False,
        "v3_resume_allowed": False,
        "successor_must_use_new_preregistration_id": True,
        "scientific_inputs_or_ac_outcomes_changed": False,
        "parent_invalid_checkpoint_payload_observed": True,
        "parent_first_budget_solver_outcomes_observed": True,
        "permitted_successor_correction": (
            "new_preregistration_id_with_exact_full_precision_checkpoint_"
            "serialization_and_prepublication_roundtrip_identity_validation_only"
        ),
        "invalid_checkpoint_handling": (
            "retain_immutable_in_v3;_never_rehash_repair_resume_migrate_or_use_as_"
            "warm_start"
        ),
        "attempt_log_file_count": 38,
        "attempt_log_total_bytes": 613387,
        "attempt_log_inventory_sha256": log_inventory_sha256,
        "key_failure_evidence": {
            relative: {
                "path": (attempt_log_root / relative).as_posix(),
                "bytes": (attempt_log_root / relative).stat().st_size,
                "sha256": digest,
            }
            for relative, digest in _EXPECTED_KEY_LOG_SHA256.items()
        },
        "source_snapshot_hashes": {
            path.as_posix(): expected for path, expected in snapshots.items()
        },
    }
    target = output_root / "invalidation"
    if target.exists():
        _verify_output_manifest(target)
        observed = _read_json(target / "invalidation.json")
        if observed != payload:
            raise RuntimeError("Published V3 invalidation record drifted")
        return observed

    def writer(staging: Path) -> None:
        for source in snapshots:
            destination = staging / "source_snapshot" / source
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        shutil.copytree(
            attempt_log_root,
            staging / "evidence_snapshot" / "logs" / _ATTEMPT_ID,
        )
        checkpoint_snapshot = staging / "evidence_snapshot" / _CHECKPOINT_RELATIVE
        checkpoint_snapshot.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(
            checkpoint_root / "candidate.json",
            checkpoint_snapshot / "candidate.json",
        )
        shutil.copyfile(
            checkpoint_root / "SHA256SUMS",
            checkpoint_snapshot / "original_SHA256SUMS.txt",
        )
        _write_exact_json(staging / "invalidation.json", payload)

    _publish_payload(target, writer)
    _verify_output_manifest(target)
    observed = _read_json(target / "invalidation.json")
    if observed != payload:
        raise RuntimeError("Published V3 invalidation record failed verification")
    return observed


if __name__ == "__main__":
    print(json.dumps(record_invalidation(), indent=2, sort_keys=True))
