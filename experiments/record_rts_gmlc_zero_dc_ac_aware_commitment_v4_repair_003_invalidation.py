"""Publish the immutable repair-003 post-audit adapter invalidation record."""

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
    run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_003 as repair,
)
from experiments.process_google_power_workload_day0 import _verify_manifest

OUTPUT_ROOT = Path(
    "results/tables/" "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_003"
)
ATTEMPT_ID = "formal_repair_003_20260720T043940Z"
ATTEMPT_LOG_ROOT = (
    Path(
        "results/logs/" "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_003"
    )
    / ATTEMPT_ID
)
FAILED_LEASE_RELATIVE = Path(
    "execution_lease/history/" "0c7a95edbca34f7e9ceda797e2c7252d.failed"
)
EXPECTED_PREREGISTRATION_MANIFEST_SHA256 = (
    "f09c1091d61e9392b07c78e12fa07630b4a045f806715faf90ca0cd44717c7d3"
)
EXPECTED_INPUT_CONTRACT_SHA256 = (
    "98ad827b4eb9baf9afae09ae68b50054f713f5cf7db63dd99aab876e70a52066"
)
EXPECTED_SOURCE_SHA256 = {
    "configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_003.yaml": (
        "6ae11ecc01ee6a43932e46d370f86503f9946541a936e7095da5d836dab440bd"
    ),
    (
        "experiments/"
        "run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_003_formal.py"
    ): "07513a1c4cf7c92bc0e62080691827c20cc3e1c2277e103633848010830cb4a4",
    (
        "experiments/" "monitor_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_003.py"
    ): "d8d9533e20a2fc6a576c850a13e853ccba5a44ead749e41dac6f1e2c91ecefc8",
    (
        "scripts/start_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_003.ps1"
    ): "91ec7a12f7e0e8f96c124e8ca2755547bfcce22c9b98db08211c13c090f72334",
}
EXPECTED_PARENT_FILE_SHA256 = {
    "preregistration/config.yaml": EXPECTED_SOURCE_SHA256[
        "configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_003.yaml"
    ],
    "preregistration/registration.json": (
        "3f18e8c3f373459a8a8e21da5bf1859ddfa0c416f798740397f4e011bd64a15a"
    ),
    "preregistration/SHA256SUMS": EXPECTED_PREREGISTRATION_MANIFEST_SHA256,
    f"{FAILED_LEASE_RELATIVE.as_posix()}/lease.json": (
        "3c7bbd2c3de3e045b1464822e5d80097d4e6a6e8d6f39932ec8f598f410ee8ca"
    ),
    f"{FAILED_LEASE_RELATIVE.as_posix()}/terminal.json": (
        "20fc1b8cf3c810403d28d394cf5e33e8ea859e53a01cac5ba91418028187fed5"
    ),
}
EXPECTED_ATTEMPT_FILE_SHA256 = {
    "attempt.json": "8c93a32ef8638edd7339dafcea942daac8e1af5ae384b52fa705835001c68aaa",
    "launcher.request.json": (
        "4b4270c19f59935287bd4e3f9968e5b33a5ae98d47e39378d0fdda9788b25c57"
    ),
    "launcher.started.json": (
        "82ffaaabd1e4f54afdbdb311e08b930fb8b0960f6917f4c14994f981580bea87"
    ),
    "launcher.stderr.log": (
        "883d59267804bd596d68f6c4f6720b95ecdd42a58a065ca3dfe31496a1612955"
    ),
    "launcher.stdout.log": (
        "654674eb9d0240a9e02416a800be04277f19759c49530cc1f1fc9ad3200523ed"
    ),
    "progress.jsonl": (
        "9d9f605d5050e2f3d2597fa9d794b06dd463569cfea5ed13044ba891e4f29b13"
    ),
    (
        "01_q_proxy_delta_0p0010/prefix_reconstruction/"
        "level_set_cost_minimization/"
        "level_set_cost_minimization__prefix_reconstruction_01__"
        "final_full_state_fixed_shared_audit.log"
    ): "58dd96cf75eb11fc3e8c73b4caaf244c0358725491bfc7969f0df186e39eabc5",
    (
        "01_q_proxy_delta_0p0010/prefix_reconstruction/"
        "level_set_cost_minimization/"
        "level_set_cost_minimization__prefix_reconstruction_01__master.log"
    ): "444de0dbdbf904cc1646312a69206ee8cc20d5ef558ca0f7f49a2b7ffadb4490",
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


def _inventory(root: Path, *, exclude: set[str] | None = None) -> dict[str, str]:
    excluded = exclude or set()
    return {
        path.relative_to(root).as_posix(): _sha256(path)
        for path in sorted(root.rglob("*"))
        if path.is_file()
        and not any(part in excluded for part in path.relative_to(root).parts)
    }


def _verify_exact_inventory(
    root: Path,
    expected: Mapping[str, str],
    label: str,
    *,
    exclude: set[str] | None = None,
) -> None:
    observed = _inventory(root, exclude=exclude)
    if observed != dict(expected):
        raise RuntimeError(f"repair-003 {label} inventory or hash drifted")


def _validate_parent_output(output_root: Path) -> dict[str, Any]:
    if not output_root.is_dir():
        raise RuntimeError("repair-003 output root is missing")
    allowed = {"preregistration", "execution_lease", "invalidation"}
    if any(
        path.name not in allowed or path.name.startswith(".")
        for path in output_root.iterdir()
    ):
        raise RuntimeError("repair-003 gained an unexpected result artifact")
    for forbidden in ("candidate_checkpoints", "candidate_frontier", "joint_ac"):
        if (output_root / forbidden).exists():
            raise RuntimeError(f"repair-003 gained forbidden {forbidden} evidence")
    lease_root = output_root / "execution_lease"
    if (lease_root / "active").exists() or (lease_root / "lease.json").exists():
        raise RuntimeError("repair-003 still has an active execution lease")
    _verify_exact_inventory(
        output_root,
        EXPECTED_PARENT_FILE_SHA256,
        "formal root",
        exclude={"invalidation"},
    )
    preregistration = output_root / "preregistration"
    _verify_manifest(preregistration)
    registration = _read_json(preregistration / "registration.json")
    if (
        registration.get("schema")
        != "rts_gmlc_zero_dc_ac_aware_commitment_preregistration_v4_repair_003"
        or registration.get("preregistration_id")
        != "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_003"
        or registration.get("input_contract_sha256") != EXPECTED_INPUT_CONTRACT_SHA256
        or registration.get("candidate_frontier_outcomes_observed") is not False
        or registration.get("joint_ac_outcomes_observed") is not False
    ):
        raise RuntimeError("repair-003 preregistration content drifted")
    lease = _read_json(output_root / FAILED_LEASE_RELATIVE / "lease.json")
    terminal = _read_json(output_root / FAILED_LEASE_RELATIVE / "terminal.json")
    if (
        lease.get("lease_id") != "0c7a95edbca34f7e9ceda797e2c7252d"
        or lease.get("attempt_id") != ATTEMPT_ID
        or lease.get("pid") != 50844
        or lease.get("stage") != "generate_candidates"
        or terminal.get("lease_id") != lease["lease_id"]
        or terminal.get("status") != "failed"
        or terminal.get("error_type") != "RuntimeError"
        or terminal.get("error_message")
        != "repair-003 prefix residual audit is missing"
    ):
        raise RuntimeError("repair-003 failed lease content drifted")
    return registration


def _validate_attempt(attempt_log_root: Path) -> dict[str, Any]:
    _verify_exact_inventory(
        attempt_log_root, EXPECTED_ATTEMPT_FILE_SHA256, "attempt evidence"
    )
    attempt = _read_json(attempt_log_root / "attempt.json")
    if (
        attempt.get("attempt_id") != ATTEMPT_ID
        or attempt.get("pid") != 50844
        or attempt.get("input_contract_sha256") != EXPECTED_INPUT_CONTRACT_SHA256
    ):
        raise RuntimeError("repair-003 attempt identity drifted")
    events = [
        json.loads(line)
        for line in (attempt_log_root / "progress.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    if len(events) != 11 or not all(isinstance(event, dict) for event in events):
        raise RuntimeError("repair-003 progress event inventory drifted")
    solves = [event for event in events if event.get("event") == "solve_completed"]
    audit_events = [
        event
        for event in events
        if event.get("event") == "formal_full_state_audit_completed"
    ]
    completed = [
        event for event in events if event.get("event") == "candidate_completed"
    ]
    if (
        len(solves) != 2
        or any(
            event.get("termination_condition") != "optimal"
            or event.get("incumbent_usable") is not True
            or event.get("bound_valid") is not True
            for event in solves
        )
        or len(audit_events) != 1
        or completed
    ):
        raise RuntimeError("repair-003 solver/audit completion evidence drifted")
    audit = audit_events[0]
    residual = audit.get("residual_audit")
    if (
        audit.get("candidate_ordinal") != 1
        or audit.get("passed") is not True
        or not isinstance(residual, Mapping)
        or residual.get("passed") is not True
        or residual.get("maximum_balance_residual_mw") != 1.5069190340000205e-10
    ):
        raise RuntimeError("repair-003 real full-state audit evidence drifted")
    candidate_failure, attempt_failure = events[-2:]
    if (
        candidate_failure.get("event") != "candidate_failed"
        or candidate_failure.get("candidate_ordinal") != 1
        or candidate_failure.get("error_type") != "RuntimeError"
        or candidate_failure.get("error_message")
        != "repair-003 prefix residual audit is missing"
        or attempt_failure.get("event") != "attempt_failed"
        or attempt_failure.get("error_message") != candidate_failure["error_message"]
    ):
        raise RuntimeError("repair-003 terminal failure evidence drifted")
    return {
        "attempt": attempt,
        "audit": audit,
        "candidate_failure": candidate_failure,
        "attempt_failure": attempt_failure,
    }


def _validate_sources(repository_root: Path) -> dict[str, Path]:
    sources = {
        relative: repository_root / relative for relative in EXPECTED_SOURCE_SHA256
    }
    for relative, path in sources.items():
        if not path.is_file() or _sha256(path) != EXPECTED_SOURCE_SHA256[relative]:
            raise RuntimeError(f"repair-003 parent source drifted: {relative}")
    return sources


def _payload(
    registration: Mapping[str, Any], evidence: Mapping[str, Any]
) -> dict[str, Any]:
    audit = evidence["audit"]
    failure = evidence["candidate_failure"]
    return {
        "schema": "rts_gmlc_v4_repair_003_post_audit_adapter_invalidation_v1",
        "status": (
            "invalidated_after_prefix_master_and_24_state_audit_passed_but_"
            "post_audit_record_shape_adapter_failed_before_any_valid_checkpoint_"
            "frontier_or_joint_ac_call"
        ),
        "preregistration_id": registration["preregistration_id"],
        "preregistration_manifest_sha256": (EXPECTED_PREREGISTRATION_MANIFEST_SHA256),
        "input_contract_sha256": EXPECTED_INPUT_CONTRACT_SHA256,
        "formal_attempt_id": ATTEMPT_ID,
        "process_id": 50844,
        "process_is_running": False,
        "failed_lease_id": "0c7a95edbca34f7e9ceda797e2c7252d",
        "failure_phase": "prefix_post_full_state_audit_record_shape_adapter",
        "failure_exception_type": failure["error_type"],
        "failure_exception_message": failure["error_message"],
        "failure_root_cause": (
            "prefix_adapter_read_residual_audit_from_callback_record_even_though_"
            "rehydration_returns_it_at_the_full_state_audit_record_top_level"
        ),
        "prefix_master_termination_condition": "optimal",
        "prefix_master_incumbent_usable": True,
        "prefix_master_bound_valid": True,
        "repeated_24_state_full_state_audit_passed": True,
        "residual_audit_passed": True,
        "maximum_balance_residual_mw": audit["residual_audit"][
            "maximum_balance_residual_mw"
        ],
        "failure_is_infeasibility_evidence": False,
        "failure_is_solver_failure": False,
        "failure_is_post_audit_implementation_bug": True,
        "valid_candidate_checkpoint_count": 0,
        "candidate_frontier_artifact_published": False,
        "joint_ac_solver_call_count": 0,
        "repair_003_resume_allowed": False,
        "successor_must_restart_from_candidate_ordinal": 1,
        "successor_must_use_new_preregistration_id": True,
        "successor_must_use_new_output_root": True,
        "scientific_protocol_changed": False,
        "permitted_successor_correction": (
            "read_and_validate_prefix_residual_audit_at_the_top_level_in_both_"
            "prefix_candidate_construction_and_prefix_checkpoint_validation_only"
        ),
        "source_snapshot_sha256": dict(EXPECTED_SOURCE_SHA256),
        "parent_root_file_sha256": dict(EXPECTED_PARENT_FILE_SHA256),
        "attempt_file_sha256": dict(EXPECTED_ATTEMPT_FILE_SHA256),
    }


def _publish_recursive_payload(target: Path, writer: Any) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError(f"Immutable artifact already exists: {target}")
    staging = Path(
        tempfile.mkdtemp(dir=target.parent, prefix=f".{target.name}.processing-")
    )
    try:
        writer(staging)
        repair._write_recursive_manifest(staging)
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
    sources = _validate_sources(repository_root)
    payload = _payload(registration, evidence)
    target = output_root / "invalidation"
    if target.exists():
        _verify_manifest(target)
        observed = _read_json(target / "invalidation.json")
        if observed != payload:
            raise RuntimeError("repair-003 published invalidation drifted")
        return observed

    def writer(staging: Path) -> None:
        for relative, source in sources.items():
            destination = staging / "source_snapshot" / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        shutil.copytree(
            output_root / "preregistration",
            staging / "evidence_snapshot/preregistration",
        )
        shutil.copytree(
            output_root / FAILED_LEASE_RELATIVE,
            staging / "evidence_snapshot" / FAILED_LEASE_RELATIVE,
        )
        shutil.copytree(
            attempt_log_root,
            staging / "evidence_snapshot/logs" / ATTEMPT_ID,
        )
        v4._write_exact_json(staging / "invalidation.json", payload)

    _publish_recursive_payload(target, writer)
    _verify_manifest(target)
    observed = _read_json(target / "invalidation.json")
    if observed != payload:
        raise RuntimeError("repair-003 invalidation publication failed verification")
    return observed


if __name__ == "__main__":
    print(json.dumps(record_invalidation(), indent=2, sort_keys=True))
