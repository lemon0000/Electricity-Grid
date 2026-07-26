from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from typing import Any

from experiments.run_rts_gmlc_multi_poi_scan import _publish_payload, _write_json


_OUTPUT_ROOT = Path(
    "results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v2"
)
_CONFIG_PATH = Path(
    "configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v2.yaml"
)
_EXPECTED_INPUT_CONTRACT_SHA256 = (
    "7cb101bfbdc26994354fd77d6525bfc2de5deaf97496cc970cea805ead9857d0"
)
_EXPECTED_PREREGISTRATION_MANIFEST_SHA256 = (
    "ee71eca750a4c6e8819c8d3b3c7de803c0736efa3327b5f89aec0d91edeff708"
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_manifest(root: Path) -> None:
    manifest = root / "SHA256SUMS"
    for line in manifest.read_text(encoding="ascii").splitlines():
        expected, relative = line.split("  ", maxsplit=1)
        path = root / relative
        if not path.is_file() or _sha256(path) != expected:
            raise RuntimeError(f"Manifest drifted: {path}")


def record_termination() -> dict[str, Any]:
    preregistration = _OUTPUT_ROOT / "preregistration"
    _verify_manifest(preregistration)
    if _sha256(preregistration / "SHA256SUMS") != (
        _EXPECTED_PREREGISTRATION_MANIFEST_SHA256
    ):
        raise RuntimeError("v2 preregistration manifest drifted")
    registration = json.loads(
        (preregistration / "registration.json").read_text(encoding="utf-8")
    )
    if registration["input_contract_sha256"] != _EXPECTED_INPUT_CONTRACT_SHA256:
        raise RuntimeError("v2 input contract drifted")
    forbidden = ("candidate_frontier", "joint_ac")
    if any((_OUTPUT_ROOT / name).exists() for name in forbidden):
        raise RuntimeError("v2 gained a result artifact before termination recording")
    if any(path.name.startswith(".") for path in _OUTPUT_ROOT.iterdir()):
        raise RuntimeError("v2 has a hidden staging artifact")

    implementation_hashes = registration["input_contract"]["implementation_sha256"]
    snapshots = {_CONFIG_PATH: registration["input_contract"]["config_sha256"]}
    snapshots.update(
        {Path(path): expected for path, expected in implementation_hashes.items()}
    )
    for path, expected in snapshots.items():
        if not path.is_file() or _sha256(path) != expected:
            raise RuntimeError(f"Cannot snapshot drifted v2 input: {path}")

    stdout_log = Path(
        "results/logs/"
        "rts_gmlc_zero_dc_ac_aware_commitment_v2_candidate_frontier.stdout.log"
    )
    stderr_log = Path(
        "results/logs/"
        "rts_gmlc_zero_dc_ac_aware_commitment_v2_candidate_frontier.stderr.log"
    )
    payload = {
        "schema": "rts_gmlc_zero_dc_ac_aware_commitment_operational_termination_v1",
        "status": (
            "terminated_before_candidate_frontier_publication_and_before_any_"
            "joint_ac_solver_call"
        ),
        "preregistration_id": registration["preregistration_id"],
        "input_contract_sha256": registration["input_contract_sha256"],
        "preregistration_manifest_sha256": (
            _EXPECTED_PREREGISTRATION_MANIFEST_SHA256
        ),
        "process_id": 21468,
        "process_started_at_local": "2026-07-18T23:07:49+08:00",
        "termination_requested_at_local": "2026-07-19T12:06:34+08:00",
        "elapsed_seconds_to_termination_request": 46725,
        "candidate_generation_invocation_started": True,
        "candidate_frontier_artifact_published": False,
        "candidate_frontier_outcomes_observed": False,
        "partial_candidate_solution_persisted": False,
        "joint_ac_solver_call_count": 0,
        "joint_ac_outcomes_observed": False,
        "termination_is_infeasibility_evidence": False,
        "termination_reason": (
            "unobservable_solver_progress_and_no_finite_runtime_bound;_the_"
            "process_remained_cpu_active"
        ),
        "stdout_log": {
            "path": stdout_log.as_posix(),
            "bytes": stdout_log.stat().st_size,
            "sha256": _sha256(stdout_log),
        },
        "stderr_log": {
            "path": stderr_log.as_posix(),
            "bytes": stderr_log.stat().st_size,
            "sha256": _sha256(stderr_log),
        },
        "scientific_inputs_or_ac_outcomes_changed": False,
        "successor_must_use_new_preregistration_id": True,
        "source_snapshot_hashes": {
            path.as_posix(): expected for path, expected in snapshots.items()
        },
    }
    target = _OUTPUT_ROOT / "operational_termination"
    if target.exists():
        _verify_manifest(target)
        observed = json.loads(
            (target / "termination.json").read_text(encoding="utf-8")
        )
        if observed != payload:
            raise RuntimeError("Published v2 termination record drifted")
        return observed

    def writer(staging: Path) -> None:
        for source in snapshots:
            destination = staging / "source_snapshot" / source
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, destination)
        _write_json(staging / "termination.json", payload)

    _publish_payload(target, writer)
    return json.loads((target / "termination.json").read_text(encoding="utf-8"))


if __name__ == "__main__":
    print(json.dumps(record_termination(), indent=2, sort_keys=True))
