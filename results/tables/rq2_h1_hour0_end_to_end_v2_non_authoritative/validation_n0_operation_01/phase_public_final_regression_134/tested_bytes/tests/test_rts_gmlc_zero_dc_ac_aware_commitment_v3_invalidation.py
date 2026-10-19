from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from experiments import (
    record_rts_gmlc_zero_dc_ac_aware_commitment_v3_invalidation as subject,
)
from experiments.process_google_power_workload_day0 import (
    _verify_manifest as _verify_output_manifest,
)

SOURCE_ROOT = Path("results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v3")
LOG_ROOT = Path(
    "results/logs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v3/"
    "formal_20260719T061959Z"
)


def _inputs(tmp_path: Path) -> tuple[Path, Path]:
    output = tmp_path / "v3"
    shutil.copytree(SOURCE_ROOT / "preregistration", output / "preregistration")
    shutil.copytree(
        SOURCE_ROOT / subject._CHECKPOINT_RELATIVE,
        output / subject._CHECKPOINT_RELATIVE,
    )
    logs = tmp_path / "logs" / subject._ATTEMPT_ID
    shutil.copytree(LOG_ROOT, logs)
    return output, logs


def test_record_invalidation_is_atomic_complete_and_idempotent(tmp_path: Path) -> None:
    output, logs = _inputs(tmp_path)
    checkpoint = output / subject._CHECKPOINT_RELATIVE
    original_candidate = subject._sha256(checkpoint / "candidate.json")
    original_manifest = subject._sha256(checkpoint / "SHA256SUMS")

    first = subject.record_invalidation(output_root=output, attempt_log_root=logs)
    manifest = subject._sha256(output / "invalidation" / "SHA256SUMS")
    second = subject.record_invalidation(output_root=output, attempt_log_root=logs)

    assert first == second
    assert subject._sha256(output / "invalidation" / "SHA256SUMS") == manifest
    _verify_output_manifest(output / "invalidation")
    assert first["valid_budget_candidate_checkpoint_count"] == 0
    assert first["invalid_budget_candidate_checkpoint_count"] == 1
    assert first["checkpoint_manifest_file_integrity_valid"]
    assert not first["checkpoint_reload_identity_valid"]
    assert not first["invalid_checkpoint_is_resume_eligible"]
    assert not first["candidate_frontier_artifact_published"]
    assert first["joint_ac_solver_call_count"] == 0
    assert (
        first["stored_dispatch_sha256"] != first["recomputed_persisted_dispatch_sha256"]
    )
    assert (
        output
        / "invalidation"
        / "evidence_snapshot"
        / subject._CHECKPOINT_RELATIVE
        / "candidate.json"
    ).is_file()
    assert subject._sha256(checkpoint / "candidate.json") == original_candidate
    assert subject._sha256(checkpoint / "SHA256SUMS") == original_manifest
    assert not any(path.name.startswith(".") for path in output.iterdir())


@pytest.mark.parametrize("result_name", ("candidate_frontier", "joint_ac"))
def test_record_invalidation_refuses_a_v3_result_artifact(
    tmp_path: Path, result_name: str
) -> None:
    output, logs = _inputs(tmp_path)
    (output / result_name).mkdir()

    with pytest.raises(RuntimeError, match="gained a result artifact"):
        subject.record_invalidation(output_root=output, attempt_log_root=logs)

    assert not (output / "invalidation").exists()


def test_record_invalidation_never_overwrites_a_drifted_record(tmp_path: Path) -> None:
    output, logs = _inputs(tmp_path)
    subject.record_invalidation(output_root=output, attempt_log_root=logs)
    path = output / "invalidation" / "invalidation.json"
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload["v3_resume_allowed"] = True
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")
    observed = path.read_bytes()

    with pytest.raises(RuntimeError, match="manifest"):
        subject.record_invalidation(output_root=output, attempt_log_root=logs)

    assert path.read_bytes() == observed
