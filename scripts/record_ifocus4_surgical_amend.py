"""Record surgical preregistration amendment audit and launch readiness check."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path

from experiments import run_rts_gmlc_zero_dc_ac_aware_commitment_v4 as v4
from experiments.process_google_power_workload_day0 import _verify_manifest
from experiments.run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_009_formal import (
    _sha256,
    _write_nested_manifest,
)

ROOT = Path(
    "results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009_ifocus4"
)
RUNNER = Path(
    "experiments/run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_009_formal.py"
)


def main() -> None:
    reg = v4._load_json(ROOT / "preregistration", "registration.json")
    frontier = v4._load_json(ROOT / "candidate_frontier", "summary.json")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    archive = ROOT / "preregistration_amendments" / (
        f"0b34bfe901d054ff_to_{reg['input_contract_sha256'][:16]}_surgical_{stamp}"
    )
    archive.mkdir(parents=False)
    v4._write_exact_json(
        archive / "amendment.json",
        {
            "schema": "rts_gmlc_v4_repair_009_preregistration_implementation_amendment_v1",
            "amended_utc": datetime.now(timezone.utc).isoformat(),
            "method": "surgical_hash_delta_without_rebuild_context",
            "scientific_protocol_changed": False,
            "joint_ac_not_yet_started": True,
            "candidate_frontier_preserved": True,
            "published_frontier_input_contract_sha256": frontier[
                "input_contract_sha256"
            ],
            "previous_input_contract_sha256": (
                "0b34bfe901d054ff8d42562ce21f336b1c6b0b34009ba2f01bc687b4ec37598d"
            ),
            "amended_input_contract_sha256": reg["input_contract_sha256"],
            "prior_incomplete_archive": (
                "0b34bfe901d054ff_to_b1c3044f339bdbdb_20260811T185447237514Z"
            ),
            "changed_fields": {
                "implementation.runner_sha256": {
                    "to": reg["input_contract"]["implementation"]["runner_sha256"]
                },
                "implementation.pilot_gurobi_module_sha256": {
                    "to": reg["input_contract"]["implementation"][
                        "pilot_gurobi_module_sha256"
                    ]
                },
                "successor_config_sha256": {
                    "to": reg["input_contract"]["successor_config_sha256"]
                },
            },
            "reason": (
                "complete_prereg_replace_after_nested_manifest_bug_blocked_full_amend"
            ),
        },
    )
    _write_nested_manifest(archive)
    _verify_manifest(archive)
    print("audit_archive", archive.name)
    print(
        "prereg_runner_match",
        reg["input_contract"]["implementation"]["runner_sha256"] == _sha256(RUNNER),
    )
    print("frontier_contract", frontier["input_contract_sha256"])
    print("prereg_contract", reg["input_contract_sha256"])


if __name__ == "__main__":
    main()
