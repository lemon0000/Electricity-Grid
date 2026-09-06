"""Imported validation endpoint for the RQ2 fresh-process boundary."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from src.rq2_joint_deliverability_execution_v3 import core

ROOT = Path(__file__).resolve().parents[1]


class ActivationRejected(RuntimeError):
    """The imported activation boundary could not prove an invariant."""


def _digest(value: object, label: str) -> str:
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise ActivationRejected(f"{label} digest is invalid")
    return value


def validate_imported_runtime(
    context: Mapping[str, object],
    *,
    repository_root: Path = ROOT,
) -> dict[str, object]:
    """Recheck reviewed execution v3 without opening its closed stage surface."""

    execution_config, execution_authority = core._load_reviewed_execution_config(
        repository_root
    )
    expected_outer = _digest(
        context.get("execution_outer_sha256"),
        "execution outer",
    )
    expected_review = _digest(
        context.get("execution_review_sha256"),
        "execution review",
    )
    expected_static = _digest(
        context.get("static_authority_sha256"),
        "execution static authority",
    )
    if execution_authority != {
        "execution_outer_sha256": expected_outer,
        "execution_review_sha256": expected_review,
    }:
        raise ActivationRejected("imported execution authority drifted")
    static_authority = core.derive_static_authority(repository_root, execution_config)
    if static_authority.get("authority_sha256") != expected_static:
        raise ActivationRejected("imported static authority drifted")
    audit = core.audit_registered_inputs(repository_root, execution_config)
    if audit.get("registered_inputs_ready") is not False:
        raise ActivationRejected(
            "validation unexpectedly reached execution-ready inputs"
        )
    return {
        "schema": "rq2_joint_deliverability_activation_import_validation_v1",
        "execution_outer_sha256": expected_outer,
        "execution_review_sha256": expected_review,
        "static_authority_sha256": expected_static,
        "registered_inputs_ready": False,
        "public_stage_surface": "closed",
        "solver_calls": 0,
        "formal_result_files_written": 0,
    }
