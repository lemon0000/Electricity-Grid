from __future__ import annotations

import json
from pathlib import Path

import pytest

from experiments import (
    record_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_005_interruption as recorder,
)


def _write_json(path: Path, payload: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_manifest(root: Path) -> None:
    import hashlib

    files = sorted(
        path for path in root.rglob("*") if path.is_file() and path.name != "SHA256SUMS"
    )
    lines = []
    for path in files:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        lines.append(f"{digest}  {path.relative_to(root).as_posix()}\n")
    (root / "SHA256SUMS").write_text("".join(lines), encoding="ascii")


def _synthetic_evidence(tmp_path: Path) -> tuple[Path, Path]:
    output = tmp_path / "output"
    prereg = output / "preregistration"
    _write_json(
        prereg / "registration.json",
        {
            "preregistration_id": recorder.EXPECTED_PREREGISTRATION_ID,
            "input_contract_sha256": recorder.EXPECTED_INPUT_CONTRACT_SHA256,
            "candidate_frontier_outcomes_observed": False,
            "joint_ac_outcomes_observed": False,
        },
    )
    _write_manifest(prereg)
    for ordinal, name in enumerate(recorder.CHECKPOINT_NAMES, 1):
        checkpoint = output / "candidate_checkpoints" / name
        _write_json(
            checkpoint / "candidate.json",
            {
                "schema": (
                    "rts_gmlc_v4_repair_005_cost_bisection_" "candidate_checkpoint_v1"
                ),
                "preregistration_id": recorder.EXPECTED_PREREGISTRATION_ID,
                "input_contract_sha256": recorder.EXPECTED_INPUT_CONTRACT_SHA256,
                "mode": "verified_repair_004_prefix",
                "ordinal": ordinal,
                "candidate": {
                    "requested_candidate_id": name[3:],
                    "stage_audits": {"repair_005_prefix": {}},
                    "residual_audit": {"passed": True},
                },
                "evidence": {
                    "source_checkpoint_validated_by_repair_004_runner": True,
                    "source_imported_as_recomputed": False,
                },
            },
        )
        _write_manifest(checkpoint)
    lease = output / "execution_lease" / "active" / "lease.json"
    _write_json(
        lease,
        {
            "schema": "execution_lease_v1",
            "lease_id": "d99c538dbc2f43fcb55f0bf4015aa5bd",
            "hostname": "synthetic",
            "pid": recorder.ATTEMPT_PID,
            "stage": "generate_candidates",
            "attempt_id": recorder.ATTEMPT_ID,
            "started_utc": "2026-07-22T13:52:43.481691+00:00",
        },
    )

    logs = tmp_path / "logs" / recorder.ATTEMPT_ID
    _write_json(
        logs / "attempt.json",
        {
            "schema": "rts_gmlc_v4_repair_005_candidate_attempt_v1",
            "attempt_id": recorder.ATTEMPT_ID,
            "pid": recorder.ATTEMPT_PID,
            "started_utc": "2026-07-22T13:52:43.498457+00:00",
            "input_contract_sha256": recorder.EXPECTED_INPUT_CONTRACT_SHA256,
        },
    )
    events: list[dict[str, object]] = [
        {"event": "attempt_started"},
    ]
    for ordinal, candidate_id in enumerate(
        (
            "q_proxy_delta_0p0010",
            "q_proxy_delta_0p0025",
            "q_proxy_delta_0p0050",
            "q_proxy_delta_0p0100",
        ),
        1,
    ):
        events.extend(
            [
                {
                    "event": "candidate_started",
                    "candidate_ordinal": ordinal,
                    "requested_candidate_id": candidate_id,
                },
                {"event": "candidate_completed", "candidate_ordinal": ordinal},
            ]
        )
    events.extend(
        [
            {
                "event": "candidate_started",
                "candidate_ordinal": 5,
                "requested_candidate_id": "q_proxy_delta_0p0200",
            },
            {
                "event": "exact_cg_stage_started",
                "candidate_ordinal": 5,
                "stage": "cost_normalization",
            },
            {
                "event": "heartbeat",
                "timestamp_utc": "2026-07-22T16:32:15.138847+00:00",
                "stage": "cost_normalization",
                "solve_label": "cost_normalization.iteration_01.master",
            },
        ]
    )
    (logs / "progress.jsonl").write_text(
        "".join(json.dumps(event) + "\n" for event in events), encoding="utf-8"
    )
    for name in (
        "launcher.request.json",
        "launcher.started.json",
        "launcher.stdout.log",
        "launcher.stderr.log",
    ):
        (logs / name).write_text("", encoding="utf-8")
    return output, logs


def _pin_synthetic_checkpoint_hashes(monkeypatch, output: Path) -> None:
    checkpoints = output / "candidate_checkpoints"
    monkeypatch.setattr(
        recorder,
        "EXPECTED_CHECKPOINT_MANIFEST_SHA256S",
        tuple(
            recorder._sha256(checkpoints / name / "SHA256SUMS")
            for name in recorder.CHECKPOINT_NAMES
        ),
    )
    monkeypatch.setattr(
        recorder,
        "EXPECTED_CANDIDATE_JSON_SHA256S",
        tuple(
            recorder._sha256(checkpoints / name / "candidate.json")
            for name in recorder.CHECKPOINT_NAMES
        ),
    )


def test_records_interruption_without_formal_failure_and_is_idempotent(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output, logs = _synthetic_evidence(tmp_path)
    _pin_synthetic_checkpoint_hashes(monkeypatch, output)

    first = recorder.record_interruption(
        output_root=output,
        attempt_log_root=logs,
        repository_root=Path("."),
        process_probe_fn=lambda _pid: False,
        observed_at_utc="2026-07-26T00:00:00+00:00",
    )
    second = recorder.record_interruption(
        output_root=output,
        attempt_log_root=logs,
        repository_root=Path("."),
        process_probe_fn=lambda _pid: False,
        observed_at_utc="2026-07-26T00:01:00+00:00",
    )

    assert first == second
    assert first["schema"] == "rts_gmlc_v4_repair_005_operational_interruption_v1"
    assert first["valid_candidate_checkpoint_count"] == 4
    assert first["candidate_frontier_artifact_published"] is False
    assert first["joint_ac_solver_call_count"] == 0
    assert first["interruption_is_infeasibility_evidence"] is False
    assert first["interruption_is_formal_failure"] is False
    assert first["active_lease"]["retained"] is True
    assert (output / "execution_lease" / "active" / "lease.json").is_file()
    recorder._verify_manifest(output / "operational_interruption")


def test_rejects_checkpoint_content_with_rewritten_manifest(
    tmp_path: Path,
    monkeypatch,
) -> None:
    output, logs = _synthetic_evidence(tmp_path)
    _pin_synthetic_checkpoint_hashes(monkeypatch, output)
    checkpoint = output / "candidate_checkpoints" / recorder.CHECKPOINT_NAMES[0]
    _write_json(checkpoint / "candidate.json", {"tampered": True})
    _write_manifest(checkpoint)

    with pytest.raises(RuntimeError, match="checkpoint hash drifted"):
        recorder.record_interruption(
            output_root=output,
            attempt_log_root=logs,
            repository_root=Path("."),
            process_probe_fn=lambda _pid: False,
            observed_at_utc="2026-07-26T00:00:00+00:00",
        )
