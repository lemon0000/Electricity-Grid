"""Publish the immutable repair-004 cost-gap invalidation record."""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from experiments import run_rts_gmlc_zero_dc_ac_aware_commitment_v4 as v4
from experiments import (
    run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_004_formal as repair004,
)
from experiments.process_google_power_workload_day0 import _verify_manifest

OUTPUT_ROOT = Path(
    "results/tables/" "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_004"
)
ATTEMPT_ID = "formal_repair_004_20260720T051834Z"
ATTEMPT_PID = 68116
ATTEMPT_LOG_ROOT = (
    Path(
        "results/logs/" "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_004"
    )
    / ATTEMPT_ID
)
FAILED_LEASE_ID = "eb06af41870f4dbb827f814b3326b356"
FAILED_LEASE_RELATIVE = Path("execution_lease/history") / Path(
    f"{FAILED_LEASE_ID}.failed"
)
EXPECTED_PREREGISTRATION_MANIFEST_SHA256 = (
    "925bad1b3e0da8573774cc77eb303835b2e0bf35b2074b914d1248dddf891041"
)
EXPECTED_INPUT_CONTRACT_SHA256 = (
    "4aaf38250e9a72ffcc475103ccad4f62781e8c17794425ad67986af744480e7b"
)
EXPECTED_SOURCE_SHA256 = {
    "configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_004.yaml": (
        "83770f7963ba2f9a0163da03d3301bd0753e0b8cfdd60377440aefa4b2025576"
    ),
    (
        "experiments/"
        "run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_004_formal.py"
    ): "97cea7fdd83a6af9faff371034e2103de130d832fed7f162d8f7b43d737805c2",
    (
        "experiments/" "monitor_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_004.py"
    ): "1bd4301f696edabbd79abbbd51342a635b74931d4d8adc90d0c68bd2b0c397a0",
    (
        "scripts/" "start_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_004.ps1"
    ): "66c4f8854d721811dd709f1de3567d8299fa3b275664aafb10de7e1eafad4cbe",
}
EXPECTED_ATTEMPT_FILE_SHA256 = {
    "attempt.json": "9a0ca686e9013f848d52cf3d7c3b1aed01fddf3e869acb7ce3d1164f2371c765",
    "launcher.request.json": (
        "d8add83b868eb3e2818aeb3e2e082bb30ce12169671a3fcfba3a31fc40d87399"
    ),
    "launcher.started.json": (
        "839e32e0e689ddb7907049ec7356a01f314591605ed2e625546192c4810e3384"
    ),
    "launcher.stderr.log": (
        "b4a8693ce3796cc8068242f8ee1708c86d0041620defd09b4eb66bf37c62386b"
    ),
    "launcher.stdout.log": (
        "d631838e5d8c064904b20271a6cac1632b1906e847088c848d4a8b68dacdbd18"
    ),
    "progress.jsonl": (
        "149675c2c7d4072088b2d62856b5484aa2893563dc85b4a21dbbb424b2d4c41c"
    ),
    (
        "05_q_proxy_delta_0p0200/cost_normalization/cost_normalization/"
        "cost_normalization__iteration_01__master.log"
    ): "93e176a9718695ad4480b75c0c083c2628a143caaa8850dc87858d843585f3a7",
}
EXPECTED_FAILED_LEASE_SHA256 = (
    "233528700fc3b88eb37a674248db1d496e4fc9552bf2573832da7ee6aa8b8561"
)
EXPECTED_TERMINAL_SHA256 = (
    "bc7401ca1b70f56c8a67ee8ecb7a6bbd2ed4d415079730ec09bcae480e4fa33c"
)
EXPECTED_CHECKPOINT_MANIFEST_SHA256S = (
    "2bd1d1c6843c6397248d4cd5531f1911c2f91036174b00af0877987d01b74c41",
    "98ab92e1a59f668203a66988b324cca75d764c4ed440fdf1c547d2279a00e8b2",
    "42830c97b66be3f80231757aaa0f1a1732cfa5fa4d400f0c33be3b508c764f51",
    "f929c097922937f4f85ca86c3714da2095060a10d59b1a14dfc3a51ca6d0759c",
)
EXPECTED_CANDIDATE_JSON_SHA256S = (
    "60317c6f2ead2467d6a6e3b7e23dab692d054e8cb3e8f11691144ec2f32f737e",
    "451a6cb559489f67e0b3a1d2e4f0fc02b9295238b0cf05aee06c9cc99df7c0b0",
    "913c1f46d03f506c0c04f794eab5b6c64aabd084ac15d0f7f74b25472fe33b67",
    "5efa62039ad86e3129d51d3ceba7a198311c9cfe9eb7048e3f78acf128d72448",
)


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


def _validate_sources(repository_root: Path) -> None:
    for relative, expected in EXPECTED_SOURCE_SHA256.items():
        path = repository_root / relative
        if not path.is_file() or _sha256(path) != expected:
            raise RuntimeError(f"repair-004 source drifted: {relative}")


def _validate_parent_output(output_root: Path) -> dict[str, Any]:
    if not output_root.is_dir():
        raise RuntimeError("repair-004 output root is missing")
    allowed = {
        "preregistration",
        "execution_lease",
        "candidate_checkpoints",
        "invalidation",
    }
    if any(
        item.name not in allowed or item.name.startswith(".")
        for item in output_root.iterdir()
    ):
        raise RuntimeError("repair-004 gained an unexpected result artifact")
    if (output_root / "candidate_frontier").exists() or (
        output_root / "joint_ac"
    ).exists():
        raise RuntimeError("repair-004 gained forbidden downstream evidence")
    lease_root = output_root / "execution_lease"
    if (lease_root / "active").exists() or (lease_root / "lease.json").exists():
        raise RuntimeError("repair-004 still has an active execution lease")
    preregistration = output_root / "preregistration"
    _verify_manifest(preregistration)
    if (
        _sha256(preregistration / "SHA256SUMS")
        != EXPECTED_PREREGISTRATION_MANIFEST_SHA256
    ):
        raise RuntimeError("repair-004 preregistration manifest drifted")
    registration = _read_json(preregistration / "registration.json")
    if (
        registration.get("preregistration_id")
        != "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_004"
        or registration.get("input_contract_sha256") != EXPECTED_INPUT_CONTRACT_SHA256
        or registration.get("candidate_frontier_outcomes_observed") is not False
        or registration.get("joint_ac_outcomes_observed") is not False
    ):
        raise RuntimeError("repair-004 preregistration content drifted")
    failed = output_root / FAILED_LEASE_RELATIVE
    if (
        _sha256(failed / "lease.json") != EXPECTED_FAILED_LEASE_SHA256
        or _sha256(failed / "terminal.json") != EXPECTED_TERMINAL_SHA256
    ):
        raise RuntimeError("repair-004 failed lease hash drifted")
    lease = _read_json(failed / "lease.json")
    terminal = _read_json(failed / "terminal.json")
    if (
        lease.get("lease_id") != FAILED_LEASE_ID
        or lease.get("attempt_id") != ATTEMPT_ID
        or lease.get("pid") != ATTEMPT_PID
        or lease.get("stage") != "generate_candidates"
        or terminal.get("lease_id") != FAILED_LEASE_ID
        or terminal.get("status") != "failed"
        or terminal.get("error_type") != "RuntimeError"
        or terminal.get("error_message")
        != (
            "repair-004 cost normalization failed: "
            "final_bound_certificate_exceeds_maximum_acceptance"
        )
    ):
        raise RuntimeError("repair-004 failed lease content drifted")
    source_context = repair004._build_context(
        Path(
            "configs/"
            "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_004.yaml"
        )
    )
    checkpoints = output_root / "candidate_checkpoints"
    directories = sorted(path for path in checkpoints.iterdir() if path.is_dir())
    if len(directories) != 4:
        raise RuntimeError("repair-004 valid checkpoint count drifted")
    for ordinal, directory in enumerate(directories, 1):
        loaded = repair004._load_candidate_checkpoint(
            source_context, output_root, ordinal
        )
        if loaded is None:
            raise RuntimeError("repair-004 source checkpoint is missing")
        if (
            _sha256(directory / "SHA256SUMS")
            != EXPECTED_CHECKPOINT_MANIFEST_SHA256S[ordinal - 1]
            or _sha256(directory / "candidate.json")
            != EXPECTED_CANDIDATE_JSON_SHA256S[ordinal - 1]
        ):
            raise RuntimeError("repair-004 source checkpoint hash drifted")
    return registration


def _validate_attempt(attempt_log_root: Path) -> dict[str, Any]:
    for relative, expected in EXPECTED_ATTEMPT_FILE_SHA256.items():
        path = attempt_log_root / relative
        if not path.is_file() or _sha256(path) != expected:
            raise RuntimeError(f"repair-004 attempt evidence drifted: {relative}")
    attempt = _read_json(attempt_log_root / "attempt.json")
    if (
        attempt.get("attempt_id") != ATTEMPT_ID
        or attempt.get("pid") != ATTEMPT_PID
        or attempt.get("input_contract_sha256") != EXPECTED_INPUT_CONTRACT_SHA256
    ):
        raise RuntimeError("repair-004 attempt identity drifted")
    events = [
        json.loads(line)
        for line in (attempt_log_root / "progress.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    if not events or not all(isinstance(event, dict) for event in events):
        raise RuntimeError("repair-004 progress evidence drifted")
    completions = [
        event for event in events if event.get("event") == "candidate_completed"
    ]
    cost_completed = [
        event
        for event in events
        if event.get("event") == "exact_cg_stage_completed"
        and event.get("candidate_ordinal") == 5
        and event.get("stage") == "cost_normalization"
    ]
    full_audits = [
        event
        for event in events
        if event.get("event") == "exact_cg_full_state_audit_completed"
        and event.get("candidate_ordinal") == 5
        and event.get("stage") == "cost_normalization"
    ]
    if (
        [event.get("candidate_ordinal") for event in completions] != [1, 2, 3, 4]
        or len(cost_completed) != 1
        or len(full_audits) != 1
        or full_audits[0].get("passed") is not True
        or full_audits[0].get("residual_audit_passed") is not True
    ):
        raise RuntimeError("repair-004 checkpoint/audit event evidence drifted")
    cost = cost_completed[0]
    certificate = cost.get("certificate")
    if (
        cost.get("eligible") is not False
        or cost.get("failure_reason")
        != "final_bound_certificate_exceeds_maximum_acceptance"
        or not isinstance(certificate, Mapping)
        or certificate.get("valid") is not True
        or certificate.get("lower_bound") != 1127283.3411921486
        or certificate.get("upper_bound") != 1128705.0994006419
        or certificate.get("absolute_gap") != 1421.7582084932365
        or certificate.get("relative_gap_to_feasible_incumbent")
        != 0.0012596365598491668
    ):
        raise RuntimeError("repair-004 cost certificate evidence drifted")
    candidate_failure, attempt_failure = events[-2:]
    expected_message = (
        "repair-004 cost normalization failed: "
        "final_bound_certificate_exceeds_maximum_acceptance"
    )
    if (
        candidate_failure.get("event") != "candidate_failed"
        or candidate_failure.get("candidate_ordinal") != 5
        or candidate_failure.get("error_message") != expected_message
        or attempt_failure.get("event") != "attempt_failed"
        or attempt_failure.get("error_message") != expected_message
        or any(event.get("stage") == "joint_ac" for event in events)
    ):
        raise RuntimeError("repair-004 terminal progress evidence drifted")
    return {"cost_stage": cost, "full_audit": full_audits[0]}


def _payload(
    registration: Mapping[str, Any], evidence: Mapping[str, Any]
) -> dict[str, Any]:
    certificate = evidence["cost_stage"]["certificate"]
    return {
        "schema": "rts_gmlc_v4_repair_004_cost_gap_invalidation_v1",
        "status": (
            "invalidated_after_four_valid_checkpoints_and_candidate_5_audited_"
            "cost_incumbent_but_direct_cost_bound_gap_exceeded_frozen_maximum"
        ),
        "preregistration_id": registration["preregistration_id"],
        "preregistration_manifest_sha256": (EXPECTED_PREREGISTRATION_MANIFEST_SHA256),
        "input_contract_sha256": EXPECTED_INPUT_CONTRACT_SHA256,
        "formal_attempt_id": ATTEMPT_ID,
        "process_id": ATTEMPT_PID,
        "process_is_running": False,
        "failed_lease_id": FAILED_LEASE_ID,
        "failure_phase": "candidate_5_cost_normalization_bound_acceptance",
        "failure_exception_type": "RuntimeError",
        "failure_exception_message": (
            "repair-004 cost normalization failed: "
            "final_bound_certificate_exceeds_maximum_acceptance"
        ),
        "failure_is_infeasibility_evidence": False,
        "direct_cost_certificate_valid": True,
        "direct_cost_full_state_audit_passed": True,
        "direct_cost_residual_audit_passed": True,
        "direct_cost_lower_bound_usd": certificate["lower_bound"],
        "direct_cost_upper_bound_usd": certificate["upper_bound"],
        "direct_cost_absolute_gap_usd": certificate["absolute_gap"],
        "direct_cost_relative_gap_to_feasible_incumbent": certificate[
            "relative_gap_to_feasible_incumbent"
        ],
        "frozen_target_relative_gap": 1.0e-4,
        "frozen_maximum_relative_gap": 1.0e-3,
        "valid_candidate_checkpoint_count": 4,
        "candidate_checkpoint_manifest_sha256s": list(
            EXPECTED_CHECKPOINT_MANIFEST_SHA256S
        ),
        "candidate_json_sha256s": list(EXPECTED_CANDIDATE_JSON_SHA256S),
        "candidate_frontier_artifact_published": False,
        "joint_ac_solver_call_count": 0,
        "repair_004_resume_allowed": False,
        "successor_must_restart_from_candidate_ordinal": 5,
        "successor_must_use_new_preregistration_id": True,
        "successor_must_use_new_output_root": True,
        "successor_preregistration_id": (
            "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_005"
        ),
        "successor_output_root": (
            "results/tables/"
            "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_005"
        ),
        "scientific_protocol_changed": False,
        "permitted_successor_correction": (
            "only_after_the_direct_cost_stage_has_a_valid_audited_incumbent_and_"
            "fails_exactly_the_frozen_maximum_gap_gate_use_fail_closed_budget_"
            "capped_cost_decision_bisection_to_tighten_the_same_cost_interval"
        ),
        "source_snapshot_sha256": dict(EXPECTED_SOURCE_SHA256),
        "attempt_file_sha256": dict(EXPECTED_ATTEMPT_FILE_SHA256),
        "failed_lease_sha256": EXPECTED_FAILED_LEASE_SHA256,
        "failed_terminal_sha256": EXPECTED_TERMINAL_SHA256,
    }


def _publish_payload(target: Path, payload: Mapping[str, Any]) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(dir=target.parent, prefix=f".{target.name}.processing-")
    )
    try:
        v4._write_exact_json(staging / "invalidation.json", payload)
        repair004.repair._write_recursive_manifest(staging)
        _verify_manifest(staging)
        staging.rename(target)
        _verify_manifest(target)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def record_invalidation(
    *,
    output_root: Path = OUTPUT_ROOT,
    attempt_log_root: Path = ATTEMPT_LOG_ROOT,
    repository_root: Path = Path("."),
) -> dict[str, Any]:
    registration = _validate_parent_output(output_root)
    evidence = _validate_attempt(attempt_log_root)
    _validate_sources(repository_root)
    payload = _payload(registration, evidence)
    target = output_root / "invalidation"
    if target.exists():
        _verify_manifest(target)
        observed = _read_json(target / "invalidation.json")
        if observed != payload:
            raise RuntimeError("repair-004 published invalidation drifted")
        return observed
    _publish_payload(target, payload)
    observed = _read_json(target / "invalidation.json")
    if observed != payload:
        raise RuntimeError("repair-004 invalidation publication failed verification")
    return observed


if __name__ == "__main__":
    print(json.dumps(record_invalidation(), indent=2, sort_keys=True))
