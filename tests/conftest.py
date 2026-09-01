from __future__ import annotations

import hashlib
import sys
from pathlib import Path

import pytest


_FROZEN_V6_TEST = Path("tests/test_rq2_public_data_preregistration_v6.py")
_FROZEN_V6_TEST_SHA256 = (
    "f7a8ad71712c2ec731119ce02649c1c1dc2379f190d40238aed001da610edc47"
)
_WINDOWS_PREDECESSOR_NODEIDS = {
    "tests/test_rq2_public_data_preregistration_v6.py::"
    "test_preregistration_v6_frozen_hashes_and_outer_manifest_are_live",
    "tests/test_rq2_public_data_preregistration_v6.py::"
    "test_executor_bundle_has_the_exact_frozen_execution_inventory",
}
_H2_PREDECESSOR_VALIDATOR_NODEID = (
    "tests/test_rq2_formal_batch.py::"
    "test_temporal_successor_preregistration_validates_without_running"
)
_H2_PREDECESSOR_HASHES = {
    Path("configs/rq2_h2_temporal_successor_preregistration_v1.yaml"): (
        "3f519f1fe33169585eea6561ff0d2fd26a761af553529a58b4288b16a5ba00d2"
    ),
    Path(
        "configs/rq2_h2_temporal_successor_preregistration_v1.SHA256SUMS.json"
    ): "bdd8d10b234852ed00a2b4a70919ee102731f0d421e01b97a528c732f1619d79",
    Path("experiments/validate_rq2_h2_temporal_successor_preregistration.py"): (
        "4566c21f1a741b0d97813c6e0fc9ca0cd05bb1ae6860c4f81342e566c240c761"
    ),
    Path("tests/test_rq2_formal_batch.py"): (
        "349ca9c0e798f5561b746181840a79181526120a3e189d67cea622c680366550"
    ),
}


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Retire exact immutable validators superseded by versioned contracts."""

    for item in items:
        if item.nodeid == _H2_PREDECESSOR_VALIDATOR_NODEID:
            for path, expected in _H2_PREDECESSOR_HASHES.items():
                observed = hashlib.sha256(path.read_bytes()).hexdigest()
                if observed != expected:
                    raise pytest.UsageError(
                        f"H2 temporal predecessor authority drifted: {path}"
                    )
            successor = Path(
                "configs/rq2_h2_temporal_executor_entry_successor_v2.yaml"
            )
            if not successor.is_file():
                raise pytest.UsageError(
                    "H2 temporal executor successor is missing"
                )
            try:
                from experiments.validate_rq2_h2_temporal_successor_preregistration import (
                    validate as validate_h2_predecessor,
                )

                validate_h2_predecessor()
            except ValueError as exc:
                predecessor_executor = (
                    "e1ec31300b0dcc2b23c44000844628b846e27fec3255b00c8e25a6f7d0b18d57"
                )
                current_executor = hashlib.sha256(
                    Path("scripts/run_experiment.ps1").read_bytes()
                ).hexdigest()
                expected_failure = (
                    "executor_script_sha256 drifted for "
                    "scripts/run_experiment.ps1: expected "
                    f"{predecessor_executor}, observed {current_executor}"
                )
                if str(exc) != expected_failure:
                    raise pytest.UsageError(
                        "H2 predecessor validator failed for a reason other "
                        f"than the registered executor mismatch: {exc}"
                    ) from exc
            except Exception as exc:
                raise pytest.UsageError(
                    "H2 predecessor validator did not reach the registered "
                    f"executor mismatch: {exc}"
                ) from exc
            else:
                raise pytest.UsageError(
                    "H2 predecessor validator unexpectedly passed; strict "
                    "retirement is no longer justified"
                )
            item.add_marker(
                pytest.mark.xfail(
                    reason=(
                        "immutable H2 predecessor validator resolves the "
                        "shared executor path; superseded by executor-entry v2"
                    ),
                    strict=True,
                )
            )

    if sys.platform != "win32":
        return
    observed = hashlib.sha256(_FROZEN_V6_TEST.read_bytes()).hexdigest()
    if observed != _FROZEN_V6_TEST_SHA256:
        raise pytest.UsageError(
            "frozen v6 predecessor test drifted; Windows retirement is invalid"
        )
    reason = (
        "immutable v6 predecessor test compares str(Path) with POSIX manifest "
        "keys; superseded by the v2 canonical-path contract"
    )
    for item in items:
        if item.nodeid in _WINDOWS_PREDECESSOR_NODEIDS:
            item.add_marker(pytest.mark.xfail(reason=reason, strict=True))
