"""Publish the immutable repair-005 operational-interruption record.

This recorder is deliberately read-only with respect to the execution lease.  It
records an attempt whose process stopped without emitting a terminal progress
event; it must not classify that observation as solver failure or infeasibility.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import tempfile
from collections.abc import Callable, Mapping
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from src.solvers.execution_lease import probe_process

OUTPUT_ROOT = Path(
    "results/tables/" "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_005"
)
ATTEMPT_ID = "formal_repair_005_20260722T135158Z"
ATTEMPT_PID = 3744
ATTEMPT_LOG_ROOT = (
    Path("results/logs/")
    / "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_005"
    / ATTEMPT_ID
)
ACTIVE_LEASE_RELATIVE = Path("execution_lease/active/lease.json")
EXPECTED_INPUT_CONTRACT_SHA256 = (
    "a32e2c6539387e7c5c07255c106debdc0e718b9e0fe0a121bea34da858ed9e0a"
)
EXPECTED_PREREGISTRATION_ID = (
    "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_005"
)
EXPECTED_CONFIG_SHA256 = (
    "c0aa26f4bfa6b4e9c0bcb8a59c8ca17d9ea0fc91078a00fce63fc5b97385359a"
)
EXPECTED_SOURCE_SHA256 = {
    "configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_005.yaml": (
        EXPECTED_CONFIG_SHA256
    ),
    (
        "experiments/"
        "run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_005_formal.py"
    ): "989ef4fb376bcc97ae43b8fb2ca8dd33f159028fee523bed646bc958fd59fe08",
    (
        "experiments/" "monitor_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_005.py"
    ): "6cfe8383ec54d74b41e9e213fddae52f36ed014fafa4c9e1ef468ca482751a85",
    (
        "scripts/" "start_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_005.ps1"
    ): "0db926b4d82ad169199cc90ae7ba373e6c8edc45f17e89d2be6cdd1ec628d99b",
}
CHECKPOINT_NAMES = (
    "01_q_proxy_delta_0p0010",
    "02_q_proxy_delta_0p0025",
    "03_q_proxy_delta_0p0050",
    "04_q_proxy_delta_0p0100",
)
EXPECTED_CHECKPOINT_MANIFEST_SHA256S = (
    "6916ce521927a63212d0921a7cc8fa07918f5cf21d6c878f5375f5f70fbb11a8",
    "1dca2d1a9f0695acbb6607a9f505a49a065b756f4c890d4437a8566f329c45e7",
    "2b4c96ea502264fc2a668ec1db8d50872cfe4aaa529056984abf3b8f3343039f",
    "2c1a517c8842e3bbd17d898dd8a8b0599f356af99e0e5603600db4ee59f6ab0f",
)
EXPECTED_CANDIDATE_JSON_SHA256S = (
    "920c9cac94fe8b851a3e2fe5378212afcca5cd606d9cfb5e7d3844e6c54b25a8",
    "9a54314c0f52c80e1efb4c944333bcb36d9c4e50f8d04b23bd302adba1d3e4d4",
    "2523535ab00fbd1f25e9f433e1c40cdc1fe00f32116e80ec3edfda7b7ee7dcf9",
    "da088eedbb9c48b15069d67af7ebb9e50e38b0af22abbde300bb553ffff5c84e",
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"Expected a JSON object: {path}")
    return payload


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        (json.dumps(payload, allow_nan=False, indent=2, sort_keys=True) + "\n").encode(
            "utf-8"
        )
    )


def _write_manifest(root: Path) -> None:
    files = sorted(
        path for path in root.rglob("*") if path.is_file() and path.name != "SHA256SUMS"
    )
    (root / "SHA256SUMS").write_bytes(
        "".join(
            f"{_sha256(path)}  {path.relative_to(root).as_posix()}\n" for path in files
        ).encode("ascii")
    )


def _verify_manifest(root: Path) -> None:
    manifest = root / "SHA256SUMS"
    if not manifest.is_file():
        raise RuntimeError(f"Missing manifest: {manifest}")
    expected: dict[str, str] = {}
    for line in manifest.read_text(encoding="ascii").splitlines():
        try:
            digest, relative = line.split("  ", maxsplit=1)
        except ValueError as error:
            raise RuntimeError(f"Malformed manifest: {manifest}") from error
        if relative in expected:
            raise RuntimeError(f"Duplicate manifest entry: {relative}")
        expected[relative] = digest
    actual = {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and path != manifest
    }
    if actual != set(expected):
        raise RuntimeError(f"Manifest file set drifted: {manifest}")
    for relative, digest in expected.items():
        if _sha256(root / relative) != digest:
            raise RuntimeError(f"Manifest hash drifted: {relative}")


def _file_inventory(root: Path, *, relative_files: tuple[str, ...]) -> dict[str, str]:
    inventory: dict[str, str] = {}
    for relative in relative_files:
        path = root / relative
        if not path.is_file():
            raise RuntimeError(f"Missing attempt evidence: {path}")
        inventory[relative] = _sha256(path)
    return inventory


def _validate_sources(repository_root: Path) -> dict[str, Path]:
    sources: dict[str, Path] = {}
    for relative, expected in EXPECTED_SOURCE_SHA256.items():
        path = repository_root / relative
        if not path.is_file() or _sha256(path) != expected:
            raise RuntimeError(f"repair-005 source drifted: {relative}")
        sources[relative] = path
    return sources


def _validate_preregistration(
    output_root: Path,
) -> tuple[dict[str, Any], str]:
    preregistration = output_root / "preregistration"
    _verify_manifest(preregistration)
    registration = _read_json(preregistration / "registration.json")
    if (
        registration.get("preregistration_id") != EXPECTED_PREREGISTRATION_ID
        or registration.get("input_contract_sha256") != EXPECTED_INPUT_CONTRACT_SHA256
        or registration.get("candidate_frontier_outcomes_observed") is not False
        or registration.get("joint_ac_outcomes_observed") is not False
    ):
        raise RuntimeError("repair-005 preregistration content drifted")
    return registration, _sha256(preregistration / "SHA256SUMS")


def _validate_lease(
    output_root: Path,
    *,
    process_probe: Callable[[int], bool | None],
) -> tuple[dict[str, Any], bool]:
    active = output_root / "execution_lease" / "active"
    lease_path = active / "lease.json"
    if not active.is_dir() or not lease_path.is_file():
        raise RuntimeError("repair-005 active lease is missing")
    if {path.name for path in active.iterdir()} != {"lease.json"}:
        raise RuntimeError("repair-005 active lease inventory drifted")
    lease = _read_json(lease_path)
    if (
        lease.get("schema") != "execution_lease_v1"
        or lease.get("attempt_id") != ATTEMPT_ID
        or lease.get("pid") != ATTEMPT_PID
        or lease.get("stage") != "generate_candidates"
        or not isinstance(lease.get("lease_id"), str)
    ):
        raise RuntimeError("repair-005 active lease identity drifted")
    liveness = process_probe(ATTEMPT_PID)
    if liveness is not False:
        raise RuntimeError(
            "repair-005 process must be confirmed stopped before interruption recording"
        )
    return lease, True


def _validate_output_root(
    output_root: Path,
    *,
    process_probe: Callable[[int], bool | None],
) -> tuple[dict[str, Any], bool, list[str]]:
    if not output_root.is_dir():
        raise RuntimeError("repair-005 output root is missing")
    allowed = {
        "preregistration",
        "execution_lease",
        "candidate_checkpoints",
        "operational_interruption",
    }
    unexpected = {
        item.name
        for item in output_root.iterdir()
        if item.name not in allowed or item.name.startswith(".")
    }
    if unexpected:
        raise RuntimeError(
            f"repair-005 unexpected result artifacts: {sorted(unexpected)}"
        )
    for forbidden in ("candidate_frontier", "joint_ac"):
        if (output_root / forbidden).exists():
            raise RuntimeError(f"repair-005 gained forbidden {forbidden} evidence")
    checkpoints = output_root / "candidate_checkpoints"
    if not checkpoints.is_dir():
        raise RuntimeError("repair-005 candidate checkpoint root is missing")
    observed = sorted(path.name for path in checkpoints.iterdir())
    if observed != list(CHECKPOINT_NAMES) or not all(
        (checkpoints / name).is_dir() for name in observed
    ):
        raise RuntimeError("repair-005 valid checkpoint prefix drifted")
    for ordinal, name in enumerate(CHECKPOINT_NAMES, 1):
        checkpoint = checkpoints / name
        _verify_manifest(checkpoint)
        candidate_path = checkpoint / "candidate.json"
        if (
            _sha256(checkpoint / "SHA256SUMS")
            != EXPECTED_CHECKPOINT_MANIFEST_SHA256S[ordinal - 1]
            or _sha256(candidate_path) != EXPECTED_CANDIDATE_JSON_SHA256S[ordinal - 1]
        ):
            raise RuntimeError("repair-005 checkpoint hash drifted")
        envelope = _read_json(candidate_path)
        candidate = envelope.get("candidate")
        evidence = envelope.get("evidence")
        if (
            envelope.get("schema")
            != "rts_gmlc_v4_repair_005_cost_bisection_candidate_checkpoint_v1"
            or envelope.get("preregistration_id") != EXPECTED_PREREGISTRATION_ID
            or envelope.get("input_contract_sha256") != EXPECTED_INPUT_CONTRACT_SHA256
            or envelope.get("mode") != "verified_repair_004_prefix"
            or envelope.get("ordinal") != ordinal
            or not isinstance(candidate, Mapping)
            or candidate.get("requested_candidate_id") != name[3:]
            or not isinstance(candidate.get("stage_audits"), Mapping)
            or not isinstance(
                candidate["stage_audits"].get("repair_005_prefix"), Mapping
            )
            or not isinstance(candidate.get("residual_audit"), Mapping)
            or candidate["residual_audit"].get("passed") is not True
            or not isinstance(evidence, Mapping)
            or evidence.get("source_checkpoint_validated_by_repair_004_runner")
            is not True
            or evidence.get("source_imported_as_recomputed") is not False
        ):
            raise RuntimeError("repair-005 checkpoint content drifted")
    registration, prereg_manifest = _validate_preregistration(output_root)
    lease, process_stopped = _validate_lease(output_root, process_probe=process_probe)
    return (
        {
            "registration": registration,
            "preregistration_manifest_sha256": prereg_manifest,
            "lease": lease,
            "lease_sha256": _sha256(output_root / ACTIVE_LEASE_RELATIVE),
        },
        process_stopped,
        observed,
    )


def _validate_attempt(attempt_log_root: Path) -> dict[str, Any]:
    attempt = _read_json(attempt_log_root / "attempt.json")
    if (
        attempt.get("schema") != "rts_gmlc_v4_repair_005_candidate_attempt_v1"
        or attempt.get("attempt_id") != ATTEMPT_ID
        or attempt.get("pid") != ATTEMPT_PID
        or attempt.get("input_contract_sha256") != EXPECTED_INPUT_CONTRACT_SHA256
    ):
        raise RuntimeError("repair-005 attempt identity drifted")
    progress_path = attempt_log_root / "progress.jsonl"
    lines = progress_path.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise RuntimeError("repair-005 progress log is empty")
    try:
        events = [json.loads(line) for line in lines]
    except json.JSONDecodeError as error:
        raise RuntimeError("repair-005 progress log is not valid JSONL") from error
    if not all(isinstance(event, dict) for event in events):
        raise RuntimeError("repair-005 progress event schema drifted")
    terminal_events = {
        "attempt_failed",
        "attempt_completed",
        "candidate_failed",
        "frontier_published",
    }
    if any(event.get("event") in terminal_events for event in events):
        raise RuntimeError("repair-005 has a formal terminal event")
    if any(
        event.get("stage") == "joint_ac"
        or str(event.get("event", "")).startswith("joint_")
        for event in events
    ):
        raise RuntimeError("repair-005 joint AC progress was observed")
    completed = [
        event for event in events if event.get("event") == "candidate_completed"
    ]
    if [event.get("candidate_ordinal") for event in completed] != [1, 2, 3, 4]:
        raise RuntimeError("repair-005 completed checkpoint prefix drifted")
    started = [event for event in events if event.get("event") == "candidate_started"]
    if not any(
        event.get("candidate_ordinal") == 5
        and event.get("requested_candidate_id") == "q_proxy_delta_0p0200"
        for event in started
    ) or any(int(event.get("candidate_ordinal", 0)) > 5 for event in started):
        raise RuntimeError("repair-005 interruption candidate position drifted")
    if not any(
        event.get("event") == "exact_cg_stage_started"
        and event.get("candidate_ordinal") == 5
        and event.get("stage") == "cost_normalization"
        for event in events
    ):
        raise RuntimeError("repair-005 cost phase was not reached")
    last = events[-1]
    if last.get("event") != "heartbeat":
        raise RuntimeError("repair-005 progress did not end on an observable heartbeat")
    return {
        "attempt": attempt,
        "events": events,
        "last_event": last,
        "completed_budget_candidate_count": len(completed),
        "progress_sha256": _sha256(progress_path),
        "attempt_file_sha256": _file_inventory(
            attempt_log_root,
            relative_files=(
                "attempt.json",
                "launcher.request.json",
                "launcher.started.json",
                "launcher.stdout.log",
                "launcher.stderr.log",
                "progress.jsonl",
            ),
        ),
    }


def _payload(
    *,
    output_evidence: Mapping[str, Any],
    attempt_evidence: Mapping[str, Any],
    checkpoint_names: list[str],
    source_hashes: Mapping[str, str],
    observed_at_utc: str,
) -> dict[str, Any]:
    registration = output_evidence["registration"]
    lease = output_evidence["lease"]
    last = attempt_evidence["last_event"]
    return {
        "schema": "rts_gmlc_v4_repair_005_operational_interruption_v1",
        "status": (
            "operationally_interrupted_after_four_valid_checkpoints_and_"
            "during_candidate_5_cost_normalization_before_frontier_or_joint_ac"
        ),
        "preregistration_id": registration["preregistration_id"],
        "preregistration_manifest_sha256": output_evidence[
            "preregistration_manifest_sha256"
        ],
        "input_contract_sha256": EXPECTED_INPUT_CONTRACT_SHA256,
        "formal_attempt_id": ATTEMPT_ID,
        "process_id": ATTEMPT_PID,
        "process_is_running": False,
        "observed_at_utc": observed_at_utc,
        "process_started_at_utc": attempt_evidence["attempt"]["started_utc"],
        "interruption_reason": (
            "process_not_running_after_progress_stopped_without_a_terminal_event;_"
            "cause_is_not_observable_from_registered_artifacts"
        ),
        "last_progress_event": {
            key: last.get(key)
            for key in (
                "event",
                "timestamp_utc",
                "monotonic_elapsed_seconds",
                "stage",
                "solve_label",
                "native_log",
                "candidate_ordinal",
                "requested_candidate_id",
            )
            if key in last
        },
        "terminal_progress_event_present": False,
        "attempt_failed_event_present": False,
        "candidate_failed_event_present": False,
        "candidate_frontier_artifact_published": False,
        "joint_ac_solver_call_count": 0,
        "valid_candidate_checkpoint_count": len(checkpoint_names),
        "candidate_checkpoint_names": checkpoint_names,
        "active_lease": {
            "relative_path": ACTIVE_LEASE_RELATIVE.as_posix(),
            "lease_id": lease["lease_id"],
            "sha256": output_evidence["lease_sha256"],
            "retained": True,
            "terminal_record_present": False,
            "takeover_or_release_performed_by_recorder": False,
        },
        "interruption_is_infeasibility_evidence": False,
        "interruption_is_formal_failure": False,
        "mathematical_infeasibility_certified": False,
        "solver_failure": False,
        "scientific_protocol_changed": False,
        "repair_005_resume_allowed": False,
        "successor_must_use_new_attempt_id": True,
        "successor_must_use_new_output_root": True,
        "source_snapshot_sha256": dict(source_hashes),
        "attempt_file_sha256": attempt_evidence["attempt_file_sha256"],
        "progress_sha256": attempt_evidence["progress_sha256"],
    }


def _publish_payload(
    target: Path, payload: Mapping[str, Any], *, copies: Mapping[str, Path]
) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        _verify_manifest(target)
        observed = _read_json(target / "interruption.json")
        if observed != dict(payload):
            raise RuntimeError("repair-005 published interruption record drifted")
        return
    staging = Path(
        tempfile.mkdtemp(dir=target.parent, prefix=f".{target.name}.processing-")
    )
    try:
        for relative, source in copies.items():
            destination = staging / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        _write_json(staging / "interruption.json", payload)
        _write_manifest(staging)
        _verify_manifest(staging)
        staging.rename(target)
        _verify_manifest(target)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def record_interruption(
    *,
    output_root: Path = OUTPUT_ROOT,
    attempt_log_root: Path = ATTEMPT_LOG_ROOT,
    repository_root: Path = Path("."),
    process_probe_fn: Callable[[int], bool | None] = probe_process,
    observed_at_utc: str | None = None,
) -> dict[str, Any]:
    output_evidence, _stopped, checkpoint_names = _validate_output_root(
        output_root, process_probe=process_probe_fn
    )
    attempt_evidence = _validate_attempt(attempt_log_root)
    sources = _validate_sources(repository_root)
    source_hashes = {relative: _sha256(path) for relative, path in sources.items()}
    target = output_root / "operational_interruption"
    existing_observed_at: str | None = None
    if target.exists():
        existing_observed_at = _read_json(target / "interruption.json").get(
            "observed_at_utc"
        )
        if not isinstance(existing_observed_at, str):
            raise RuntimeError("repair-005 published interruption timestamp drifted")
    payload = _payload(
        output_evidence=output_evidence,
        attempt_evidence=attempt_evidence,
        checkpoint_names=checkpoint_names,
        source_hashes=source_hashes,
        observed_at_utc=existing_observed_at
        or observed_at_utc
        or datetime.now(timezone.utc).isoformat(),
    )
    copies: dict[str, Path] = {
        "evidence_snapshot/execution_lease/active/lease.json": output_root
        / ACTIVE_LEASE_RELATIVE,
    }
    for relative in attempt_evidence["attempt_file_sha256"]:
        copies[f"evidence_snapshot/logs/{ATTEMPT_ID}/{relative}"] = (
            attempt_log_root / relative
        )
    for relative, source in sources.items():
        copies[f"source_snapshot/{relative}"] = source
    _publish_payload(target, payload, copies=copies)
    return _read_json(target / "interruption.json")


if __name__ == "__main__":
    print(json.dumps(record_interruption(), indent=2, sort_keys=True))


__all__ = [
    "ATTEMPT_ID",
    "ATTEMPT_LOG_ROOT",
    "ATTEMPT_PID",
    "CHECKPOINT_NAMES",
    "EXPECTED_INPUT_CONTRACT_SHA256",
    "EXPECTED_SOURCE_SHA256",
    "OUTPUT_ROOT",
    "record_interruption",
]
