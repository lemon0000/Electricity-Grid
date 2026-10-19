from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from experiments import (
    record_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_003_invalidation as record,
)


def _copies(tmp_path: Path) -> tuple[Path, Path]:
    output = tmp_path / "output"
    attempt = tmp_path / "attempt"
    shutil.copytree(record.OUTPUT_ROOT, output)
    shutil.copytree(record.ATTEMPT_LOG_ROOT, attempt)
    return output, attempt


def _repository_copy(tmp_path: Path) -> Path:
    repository = tmp_path / "repository"
    for relative in record.EXPECTED_SOURCE_SHA256:
        source = Path(relative)
        destination = repository / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    return repository


def test_invalidation_temp_publication_is_recursive_and_idempotent(
    tmp_path: Path,
) -> None:
    output, attempt = _copies(tmp_path)

    first = record.record_invalidation(
        output_root=output,
        attempt_log_root=attempt,
    )
    second = record.record_invalidation(
        output_root=output,
        attempt_log_root=attempt,
    )

    assert first == second
    assert first["failure_is_infeasibility_evidence"] is False
    assert first["failure_is_post_audit_implementation_bug"] is True
    assert first["valid_candidate_checkpoint_count"] == 0
    assert first["candidate_frontier_artifact_published"] is False
    assert first["joint_ac_solver_call_count"] == 0
    assert first["repair_003_resume_allowed"] is False
    record._verify_manifest(output / "invalidation")
    assert record._sha256(output / "invalidation/SHA256SUMS") == (
        "dd35214345d5c0a516f12bbfb6c898df12ca6da6f42f6fb0deb039a82a176053"
    )


@pytest.mark.parametrize(
    ("scope", "relative"),
    [
        ("output", "preregistration/registration.json"),
        (
            "output",
            "execution_lease/history/"
            "0c7a95edbca34f7e9ceda797e2c7252d.failed/lease.json",
        ),
        (
            "output",
            "execution_lease/history/"
            "0c7a95edbca34f7e9ceda797e2c7252d.failed/terminal.json",
        ),
        ("attempt", "progress.jsonl"),
        ("attempt", "launcher.stderr.log"),
        (
            "attempt",
            "01_q_proxy_delta_0p0010/prefix_reconstruction/"
            "level_set_cost_minimization/"
            "level_set_cost_minimization__prefix_reconstruction_01__"
            "final_full_state_fixed_shared_audit.log",
        ),
    ],
)
def test_invalidation_rejects_parent_evidence_tampering(
    tmp_path: Path, scope: str, relative: str
) -> None:
    output, attempt = _copies(tmp_path)
    target = (output if scope == "output" else attempt) / relative
    target.write_bytes(target.read_bytes() + b"tamper")

    with pytest.raises(RuntimeError, match="drifted"):
        record.record_invalidation(output_root=output, attempt_log_root=attempt)


def test_invalidation_rejects_parent_source_tampering(tmp_path: Path) -> None:
    output, attempt = _copies(tmp_path)
    repository = _repository_copy(tmp_path)
    source = repository / next(iter(record.EXPECTED_SOURCE_SHA256))
    source.write_bytes(source.read_bytes() + b"tamper")

    with pytest.raises(RuntimeError, match="parent source drifted"):
        record.record_invalidation(
            output_root=output,
            attempt_log_root=attempt,
            repository_root=repository,
        )


@pytest.mark.parametrize(
    "forbidden", ["candidate_checkpoints", "candidate_frontier", "joint_ac"]
)
def test_invalidation_rejects_fabricated_result_artifacts(
    tmp_path: Path, forbidden: str
) -> None:
    output, attempt = _copies(tmp_path)
    (output / forbidden).mkdir()

    with pytest.raises(RuntimeError, match="unexpected|forbidden"):
        record.record_invalidation(output_root=output, attempt_log_root=attempt)


def test_invalidation_rejects_published_payload_tampering(tmp_path: Path) -> None:
    output, attempt = _copies(tmp_path)
    record.record_invalidation(output_root=output, attempt_log_root=attempt)
    payload = output / "invalidation/invalidation.json"
    payload.write_bytes(payload.read_bytes() + b"tamper")

    with pytest.raises(RuntimeError, match="manifest|drifted"):
        record.record_invalidation(output_root=output, attempt_log_root=attempt)
