"""V4 successor core for full-precision candidate checkpoints.

The optimization model remains in the frozen V3 runner.  This module only
replaces candidate checkpoint persistence and the candidate-generation driver
that consumes those checkpoints.  A V4 preregistration/configuration is
intentionally out of scope until this persistence amendment is verified.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import tempfile
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from time import monotonic
from typing import Any

from experiments import run_rts_gmlc_zero_dc_ac_aware_commitment_v3 as _v3
from experiments.run_rts_gmlc_multi_poi_scan import _write_manifest

_CHECKPOINT_SCHEMA = "rts_gmlc_zero_dc_ac_aware_candidate_checkpoint_v2_full_precision"
_CHECKPOINT_FLOAT_SERIALIZATION = "python_json_roundtrip_full_precision_v1"
_CHECKPOINT_FIELDS = {
    "schema",
    "float_serialization",
    "preregistration_id",
    "input_contract_sha256",
    "ordinal",
    "candidate",
}

# Keep the V3 scientific model and frontier tabular contract unchanged.  These
# aliases are module globals so focused tests can replace expensive callbacks.
_Candidate = _v3._Candidate
_FrontierContext = _v3._FrontierContext
_CANDIDATE_FIELDS = _v3._CANDIDATE_FIELDS
_COMMITMENT_FIELDS = _v3._COMMITMENT_FIELDS
_GENERATION_FIELDS = _v3._GENERATION_FIELDS
_BRANCH_FIELDS = _v3._BRANCH_FIELDS
_DC_FLOW_FIELDS = _v3._DC_FLOW_FIELDS
_RESERVE_FIELDS = _v3._RESERVE_FIELDS
JsonlProgressWriter = _v3.JsonlProgressWriter
_baseline_candidate = _v3._baseline_candidate
_build_context = _v3._build_context
_candidate_detail_rows = _v3._candidate_detail_rows
_candidate_from_checkpoint_payload = _v3._candidate_from_checkpoint_payload
_commitment_sha256 = _v3._commitment_sha256
_deduplicate_candidates = _v3._deduplicate_candidates
_dispatch_sha256 = _v3._dispatch_sha256
_load_json = _v3._load_json
_output_root = _v3._output_root
_publish_payload = _v3._publish_payload
_requested_candidate_id = _v3._requested_candidate_id
_require_preregistration = _v3._require_preregistration
_sha256 = _v3._sha256
_solve_frontier_candidate = _v3._solve_frontier_candidate
_verify_output_manifest = _v3._verify_output_manifest
_write_csv = _v3._write_csv


def _exact_json_payload(payload: object) -> object:
    """Return the exact JSON shape without rounding finite floats."""

    return json.loads(
        json.dumps(
            payload,
            allow_nan=False,
            ensure_ascii=True,
            separators=(",", ":"),
            sort_keys=True,
        )
    )


def _write_exact_json(path: Path, payload: object) -> None:
    """Write deterministic JSON using Python's round-trip float encoding."""

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(
        (
            json.dumps(
                payload,
                allow_nan=False,
                ensure_ascii=True,
                indent=2,
                sort_keys=True,
            )
            + "\n"
        ).encode("utf-8")
    )


def _candidate_checkpoint_path(
    output_root: Path,
    ordinal: int,
    requested_candidate_id: str,
) -> Path:
    return _v3._candidate_checkpoint_path(output_root, ordinal, requested_candidate_id)


def _checkpoint_payload(
    context: _FrontierContext,
    ordinal: int,
    candidate: _Candidate,
) -> dict[str, object]:
    return {
        "schema": _CHECKPOINT_SCHEMA,
        "float_serialization": _CHECKPOINT_FLOAT_SERIALIZATION,
        "preregistration_id": context.config["preregistration"]["id"],
        "input_contract_sha256": context.input_contract_sha256,
        "ordinal": ordinal,
        "candidate": asdict(candidate),
    }


def _read_staged_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError("Candidate checkpoint staging payload is not an object")
    return payload


def _validate_checkpoint_document(
    observed: dict[str, Any],
    context: _FrontierContext,
    ordinal: int,
    requested_candidate_id: str,
) -> _Candidate:
    if set(observed) != _CHECKPOINT_FIELDS:
        raise RuntimeError("Candidate checkpoint serialization contract drifted")
    if (
        observed.get("schema") != _CHECKPOINT_SCHEMA
        or observed.get("float_serialization") != _CHECKPOINT_FLOAT_SERIALIZATION
    ):
        raise RuntimeError("Candidate checkpoint serialization contract drifted")
    if (
        observed.get("preregistration_id") != context.config["preregistration"]["id"]
        or observed.get("input_contract_sha256") != context.input_contract_sha256
        or observed.get("ordinal") != ordinal
        or not isinstance(observed.get("candidate"), dict)
    ):
        raise RuntimeError("Candidate checkpoint contract drifted")
    candidate = _candidate_from_checkpoint_payload(observed["candidate"])
    if candidate.requested_candidate_id != requested_candidate_id:
        raise RuntimeError("Candidate checkpoint requested ID drifted")
    return candidate


def _publish_checkpoint_without_overwrite(target: Path, writer) -> None:
    """Publish one immutable checkpoint after its staging audit passes."""

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError(f"Candidate checkpoint already exists: {target}")
    staging = Path(
        tempfile.mkdtemp(dir=target.parent, prefix=f".{target.name}.processing-")
    )
    try:
        writer(staging)
        _write_manifest(staging)
        if target.exists():
            raise FileExistsError(f"Candidate checkpoint already exists: {target}")
        staging.rename(target)
        _verify_output_manifest(target)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def _save_candidate_checkpoint(
    context: _FrontierContext,
    output_root: Path,
    ordinal: int,
    candidate: _Candidate,
) -> _Candidate:
    # Audit records may contain tuples from dataclass serialization. Normalize the
    # in-memory object to the immutable JSON representation before identity checks.
    canonical_candidate_payload = _exact_json_payload(asdict(candidate))
    if not isinstance(canonical_candidate_payload, dict):
        raise RuntimeError("Candidate checkpoint canonicalization drifted")
    candidate = _candidate_from_checkpoint_payload(canonical_candidate_payload)
    target = _candidate_checkpoint_path(
        output_root, ordinal, candidate.requested_candidate_id
    )
    payload = _checkpoint_payload(context, ordinal, candidate)
    expected = _exact_json_payload(payload)
    if not isinstance(expected, dict):
        raise RuntimeError("Candidate checkpoint exact JSON payload drifted")

    if target.exists():
        observed = _load_json(target, "candidate.json")
        loaded = _validate_checkpoint_document(
            observed,
            context,
            ordinal,
            candidate.requested_candidate_id,
        )
        if observed != expected or loaded != candidate:
            raise RuntimeError("Existing candidate checkpoint drifted")
        return loaded

    def writer(staging: Path) -> None:
        path = staging / "candidate.json"
        _write_exact_json(path, payload)
        observed = _read_staged_json(path)
        if observed != expected:
            raise RuntimeError("Candidate checkpoint staging round-trip drifted")
        loaded = _validate_checkpoint_document(
            observed,
            context,
            ordinal,
            candidate.requested_candidate_id,
        )
        if loaded != candidate:
            raise RuntimeError("Candidate checkpoint staging identity drifted")

    _publish_checkpoint_without_overwrite(target, writer)
    observed = _load_json(target, "candidate.json")
    loaded = _validate_checkpoint_document(
        observed,
        context,
        ordinal,
        candidate.requested_candidate_id,
    )
    if observed != expected or loaded != candidate:
        raise RuntimeError("Published candidate checkpoint drifted")
    return loaded


def _load_candidate_checkpoint(
    context: _FrontierContext,
    output_root: Path,
    ordinal: int,
    requested_candidate_id: str,
) -> _Candidate | None:
    target = _candidate_checkpoint_path(output_root, ordinal, requested_candidate_id)
    if not target.exists():
        return None
    observed = _load_json(target, "candidate.json")
    return _validate_checkpoint_document(
        observed, context, ordinal, requested_candidate_id
    )


def generate_candidate_frontier(
    config_path: Path,
    *,
    output_directory: Path | None = None,
    attempt_id: str | None = None,
) -> dict[str, Any]:
    """Run V3's candidate model with immutable V4 checkpoints."""

    context = _build_context(config_path)
    output_root = _output_root(context, output_directory)
    registration = _require_preregistration(context, output_root)
    target = output_root / "candidate_frontier"
    if target.exists():
        return _load_json(target, "summary.json")
    if (output_root / "joint_ac").exists():
        raise RuntimeError("Cannot generate candidates after joint AC has started")
    if attempt_id is None:
        attempt_id = (
            datetime.now(timezone.utc).strftime("candidate_%Y%m%dT%H%M%S%fZ")
            + f"_pid{os.getpid()}"
        )
    if re.fullmatch(r"[A-Za-z0-9_.-]+", attempt_id) is None:
        raise ValueError("Invalid candidate-generation attempt ID")
    log_root = (
        Path(context.config["formal_solver"]["progress_logging"]["log_directory"])
        / attempt_id
    )
    progress = JsonlProgressWriter(
        log_root / "progress.jsonl",
        run_id=attempt_id,
        preregistration_id=str(context.config["preregistration"]["id"]),
        input_contract_sha256=context.input_contract_sha256,
    )
    started_utc = datetime.now(timezone.utc)
    _write_exact_json(
        log_root / "attempt.json",
        {
            "schema": "rts_gmlc_candidate_generation_attempt_v2",
            "attempt_id": attempt_id,
            "pid": os.getpid(),
            "started_utc": started_utc.isoformat(),
            "preregistration_id": context.config["preregistration"]["id"],
            "input_contract_sha256": context.input_contract_sha256,
            "config_path": context.config_path.as_posix(),
            "checkpoint_schema": _CHECKPOINT_SCHEMA,
        },
    )
    deltas = tuple(
        float(item)
        for item in context.config["candidate_frontier"]["relative_cost_budget_deltas"]
    )
    progress.emit(
        "attempt_started",
        candidate_count=len(deltas),
        completed_candidate_count=0,
        started_utc=started_utc.isoformat(),
        checkpoint_schema=_CHECKPOINT_SCHEMA,
    )
    candidates = [_baseline_candidate(context)]
    progress.emit(
        "candidate_completed",
        candidate_ordinal=0,
        requested_candidate_id=candidates[0].requested_candidate_id,
        source=candidates[0].source,
        completed_candidate_count=1,
    )
    checkpoint_manifests: dict[str, str] = {}
    total_limit = float(
        context.config["formal_solver"]["time_limits_seconds"]["per_candidate_total"]
    )
    for ordinal, delta in enumerate(deltas, start=1):
        requested_id = _requested_candidate_id(delta)
        checkpoint = _load_candidate_checkpoint(
            context, output_root, ordinal, requested_id
        )
        if checkpoint is not None:
            candidates.append(checkpoint)
            checkpoint_path = _candidate_checkpoint_path(
                output_root, ordinal, requested_id
            )
            checkpoint_manifests[requested_id] = _sha256(checkpoint_path / "SHA256SUMS")
            progress.emit(
                "candidate_checkpoint_loaded",
                candidate_ordinal=ordinal,
                requested_candidate_id=requested_id,
                relative_cost_budget_delta=delta,
                checkpoint_manifest_sha256=checkpoint_manifests[requested_id],
                completed_candidate_count=len(candidates),
            )
            continue
        candidate_started = datetime.now(timezone.utc)
        deadline_utc = candidate_started + timedelta(seconds=total_limit)
        deadline_monotonic = monotonic() + total_limit
        progress.emit(
            "candidate_started",
            candidate_ordinal=ordinal,
            requested_candidate_id=requested_id,
            relative_cost_budget_delta=delta,
            total_limit_seconds=total_limit,
            deadline_utc=deadline_utc.isoformat(),
            completed_candidate_count=len(candidates),
        )
        try:
            candidate = _solve_frontier_candidate(
                context,
                relative_delta=delta,
                progress=progress,
                candidate_log_root=log_root / f"{ordinal:02d}_{requested_id}",
                candidate_ordinal=ordinal,
                deadline_monotonic=deadline_monotonic,
            )
            candidate = _save_candidate_checkpoint(
                context, output_root, ordinal, candidate
            )
        except Exception as error:
            progress.emit(
                "candidate_failed",
                candidate_ordinal=ordinal,
                requested_candidate_id=requested_id,
                relative_cost_budget_delta=delta,
                error_type=type(error).__name__,
                error_message=str(error) or repr(error),
                completed_candidate_count=len(candidates),
            )
            raise
        candidates.append(candidate)
        checkpoint_path = _candidate_checkpoint_path(output_root, ordinal, requested_id)
        checkpoint_manifests[requested_id] = _sha256(checkpoint_path / "SHA256SUMS")
        progress.emit(
            "candidate_completed",
            candidate_ordinal=ordinal,
            requested_candidate_id=requested_id,
            relative_cost_budget_delta=delta,
            commitment_sha256=candidate.commitment_sha256,
            dispatch_sha256=candidate.dispatch_sha256,
            checkpoint_manifest_sha256=checkpoint_manifests[requested_id],
            completed_candidate_count=len(candidates),
        )

    rows, selected = _deduplicate_candidates(candidates)
    timestamps = tuple(
        timestamp.isoformat() for timestamp in context.request.timestamps
    )
    details = _candidate_detail_rows(selected, timestamps)
    summary = {
        "schema": "rts_gmlc_zero_dc_ac_aware_candidate_frontier_v4",
        "preregistration_id": context.config["preregistration"]["id"],
        "input_contract_sha256": registration["input_contract_sha256"],
        "requested_candidate_count": len(candidates),
        "unique_candidate_count": len(selected),
        "all_budget_candidates_completed_before_deduplication": True,
        "candidate_generation_completed_before_any_joint_ac_solve": True,
        "candidate_generation_uses_ac_outcomes": False,
        "candidate_generation_attempt_id": attempt_id,
        "algorithm": context.config["formal_solver"]["algorithm"],
        "solver": context.config["formal_solver"]["solver"],
        "checkpoint_schema": _CHECKPOINT_SCHEMA,
        "candidate_checkpoint_manifest_sha256s": checkpoint_manifests,
        "relative_cost_budget_deltas": context.config["candidate_frontier"][
            "relative_cost_budget_deltas"
        ],
        "candidate_ids": [candidate_id for candidate_id, _candidate in selected],
        "commitment_sha256s": [
            candidate.commitment_sha256 for _candidate_id, candidate in selected
        ],
        "minimum_reactive_proxy_fraction": min(
            candidate.reactive_proxy_fraction for _candidate_id, candidate in selected
        ),
        "maximum_reactive_proxy_fraction": max(
            candidate.reactive_proxy_fraction for _candidate_id, candidate in selected
        ),
        "joint_ac_solver_call_count": 0,
        **context.config["evidence"],
    }

    def writer(staging: Path) -> None:
        _write_csv(staging / "candidates.csv", _CANDIDATE_FIELDS, rows)
        _write_csv(staging / "commitment.csv", _COMMITMENT_FIELDS, details[0])
        _write_csv(staging / "normal_generation.csv", _GENERATION_FIELDS, details[1])
        _write_csv(staging / "normal_branch_flows.csv", _BRANCH_FIELDS, details[2])
        _write_csv(staging / "normal_dc_flows.csv", _DC_FLOW_FIELDS, details[3])
        _write_csv(staging / "reserve_up.csv", _RESERVE_FIELDS, details[4])
        _write_exact_json(staging / "candidate_audits.json", details[5])
        _write_exact_json(staging / "summary.json", summary)

    _publish_payload(target, writer)
    manifest_sha256 = _sha256(target / "SHA256SUMS")
    progress.emit(
        "frontier_published",
        candidate_frontier_manifest_sha256=manifest_sha256,
        completed_candidate_count=len(candidates),
    )
    progress.emit(
        "attempt_completed",
        candidate_frontier_manifest_sha256=manifest_sha256,
        completed_candidate_count=len(candidates),
    )
    return _load_json(target, "summary.json")


__all__ = [
    "generate_candidate_frontier",
]
