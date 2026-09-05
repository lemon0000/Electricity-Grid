"""Validate the RQ2 execution successor without starting a formal run."""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from experiments.validate_rq2_joint_deliverability_execution_v1 import (
    validate as validate_candidate,
)
from src.rq2_joint_deliverability_execution_v1.core import (
    audit_registered_inputs,
    derive_static_authority,
    streaming_scale_projection,
)

CONFIG_RELATIVE = "configs/rq2_joint_deliverability_execution_successor_v1.yaml"
CONFIG = ROOT / CONFIG_RELATIVE


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise TypeError(f"YAML root must be a mapping: {path}")
    return payload


def validate_runtime_contract(config: Mapping[str, object]) -> None:
    if config.get("schema") != "rq2_joint_deliverability_execution_successor_v1":
        raise ValueError("execution successor schema drifted")
    scope = config.get("scope")
    gates = config.get("gates")
    if not isinstance(scope, Mapping) or not isinstance(gates, Mapping):
        raise TypeError("execution scope or gates are malformed")
    scope_false = {
        "runs_solver_during_validation",
        "writes_formal_results_during_validation",
        "formal_execution",
        "formal_result",
        "paper_claim",
        "security_certification",
    }
    gate_false = {
        "independent_R3_review_passed",
        "upstream_grid_package_ready",
        "execution_machine_runtime_ready",
        "native_solver_replay_passed",
        "registered_memory_profile_passed",
        "transport_runtime_projection_accepted",
        "user_formal_run_authorized",
        "formal_execution_ready",
        "formal_result",
        "paper_claim",
        "security_certified",
    }
    if any(scope.get(name) is not False for name in scope_false):
        raise ValueError("execution scope opened a forbidden effect")
    if any(gates.get(name) is not False for name in gate_false):
        raise ValueError("execution candidate opened a runtime or formal gate")


def run(*, validate_only: bool = True) -> dict[str, object]:
    config = _load_yaml(CONFIG)
    lifecycle = config.get("lifecycle")
    require_sealed = bool(
        isinstance(lifecycle, Mapping)
        and lifecycle.get("status") == "SEALED_READY_FOR_INDEPENDENT_REVIEW"
    )
    static = validate_candidate(config, require_sealed=require_sealed)
    validate_runtime_contract(config)
    authority = derive_static_authority(ROOT, config)
    input_audit = audit_registered_inputs(ROOT, config)
    projection = streaming_scale_projection(config)
    if not validate_only:
        raise RuntimeError(
            "formal execution requires a separately reviewed activation wrapper"
        )
    blockers = [
        "missing_dispatched_grid_package",
        "missing_execution_machine_runtime_receipt",
        "missing_gurobi_13_0_2_native_replay",
        "missing_registered_dimension_memory_profile",
        "missing_measured_transport_runtime_projection",
        "missing_fresh_process_activation_successor",
        "missing_independent_R3_execution_review",
        "missing_user_formal_run_authorization",
    ]
    return {
        "schema": "rq2_joint_deliverability_execution_validation_v1",
        "lifecycle": static["lifecycle"],
        "static_authority_sha256": authority["authority_sha256"],
        "input_audit": input_audit,
        "streaming_projection": projection,
        "formal_execution_ready": False,
        "formal_result": False,
        "paper_claim": False,
        "security_certified": False,
        "solver_calls": 0,
        "formal_result_files_written": 0,
        "blockers": blockers,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--validate-only", action="store_true")
    arguments = parser.parse_args()
    if not arguments.validate_only:
        parser.error("--validate-only is required; this candidate has no run authority")
    print(json.dumps(run(validate_only=True), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
