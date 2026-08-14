"""Fail-closed repair-010 successor with phase-timed isolated joint-AC calls.

The orchestration is wired to the existing V4 registration/result/checkpoint
contracts.  The checked-in config still blocks every formal entry point because
the fresh-worker startup limit has not been calibrated and no successor
preregistration has been published.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import math
import os
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import datetime, timezone
from importlib import metadata
from pathlib import Path
from typing import Any

import casadi as ca
import yaml

from experiments import run_rts_gmlc_zero_dc_ac_aware_commitment_v4 as v4
from experiments import (
    run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_009_formal as repair009,
)
from experiments.process_google_power_workload_day0 import _verify_manifest
from src.grid import rts_gmlc_ac_ipopt as shared_ipopt
from src.grid import (
    rts_gmlc_ac_aware_commitment_v4_repair_010_adapter as v4_adapter,
)
from src.scenarios.common_input_signature import common_input_signature_sha256
from src.solvers.execution_lease import ExecutionLease
from src.solvers.joint_ac_phase_contract import (
    CALIBRATION_REQUIRED_PHASES,
    DurablePhaseJournal,
    HonestIncomplete,
    PhaseContractError,
    PhaseHeartbeat,
    PhaseTimingController,
    REQUIRED_PHASES,
    canonical_sha256,
    classify_phase_contract_failure,
    load_verified_phase_events,
    load_verified_calibration_events,
)
from src.solvers.mip_progress import JsonlProgressWriter

DEFAULT_CONFIG_PATH = Path(
    "configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_010_calibration_v2.yaml"
)
SHARED_V4_ADAPTER_PATH = Path("src/grid/rts_gmlc_ac_aware_commitment_v4_adapter.py")
REPAIR_010_ADAPTER_PATH = Path(
    "src/grid/rts_gmlc_ac_aware_commitment_v4_repair_010_adapter.py"
)
SHARED_V4_ADAPTER_AUTHORITY_SHA256 = (
    "cf5cf1e3d133b7e60f63dbb0d072952a9e78de24cd05d0bb740683e8806013b7"
)
_SUCCESSOR_MODULE = (
    "experiments.run_rts_gmlc_zero_dc_ac_aware_commitment_v4_repair_010_formal"
)
_CONFIG_KEYS = {
    "schema",
    "preregistration",
    "protocol_change",
    "predecessor_ifocus4",
    "formal_successor",
    "frontier_import",
    "startup_calibration",
    "joint_ac_successor",
    "output",
    "logging",
}


class SuccessorNotReadyError(RuntimeError):
    """A frozen fail-closed gate prevents preregistration or formal execution."""


class IsolatedWorkerIncompleteError(RuntimeError):
    """A phase-bound worker stopped without a complete, valid result."""

    def __init__(self, outcome: HonestIncomplete) -> None:
        self.outcome = outcome
        super().__init__(
            f"{outcome.reason}; solver_call_count={outcome.solver_call_count}; "
            "is_infeasibility_evidence=false; resume_allowed=false"
        )


class TerminalIncompletePersistenceError(RuntimeError):
    """A terminal call could not persist its immutable incomplete receipt."""

    def __init__(
        self, outcome: HonestIncomplete, persistence_error: BaseException
    ) -> None:
        self.outcome = outcome
        self.persistence_error = persistence_error
        super().__init__(
            "repair-010 terminal-incomplete publication failed; immutable "
            "finalization intent remains fail-closed and no success seal may be "
            "published: " + (str(persistence_error) or repr(persistence_error))
        )


class SuccessSealCommitIndeterminateError(RuntimeError):
    """A success target exists but its atomic commit cannot be proven valid."""


class StartupCalibrationIncompleteError(RuntimeError):
    """A startup calibration stopped without one complete pre-solver sample."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        self.solver_call_count = 0
        self.is_infeasibility_evidence = False
        self.resume_allowed = False
        super().__init__(
            f"{reason}; solver_call_count=0; is_infeasibility_evidence=false; "
            "resume_allowed=false"
        )


class StartupCalibrationPersistenceError(RuntimeError):
    """Calibration incompleteness could not be atomically persisted."""


class StartupCalibrationCompletionCommitIndeterminateError(RuntimeError):
    """A completion target exists but its exact atomic commit is unprovable."""


class StartupCalibrationNoResumeError(RuntimeError):
    """Immutable calibration state already exists and may not be resumed."""


class StartupCalibrationLauncherPersistenceError(RuntimeError):
    """A spawned calibration child could not be durably stopped/classified."""


class StartupCalibrationLauncherFailedError(StartupCalibrationNoResumeError):
    """The launcher stopped its own child and persisted an immutable failure."""

    def __init__(self, reason: str, *, worker_pid: int, return_code: int) -> None:
        self.reason = reason
        self.worker_pid = worker_pid
        self.return_code = return_code
        self.child_exit_confirmed = True
        super().__init__(reason)


@dataclass(frozen=True)
class IsolatedWorkerCompletion:
    worker_pid: int
    solver_call_count: int
    result: object


@dataclass(frozen=True)
class FrontierSourceAudit:
    source_preregistration_manifest_sha256: str
    source_frontier_manifest_sha256: str
    source_preregistration_input_contract_sha256: str
    source_frontier_input_contract_sha256: str
    candidate_ids: tuple[str, ...]
    budget_checkpoint_manifest_sha256s: tuple[tuple[str, str], ...]
    nested_round_manifest_count: int


@dataclass(frozen=True)
class PhaseRecoveryEvidence:
    call_manifest_sha256: str
    call_registration: Mapping[str, Any]
    worker_result: Path
    native_solver_log: Path
    phase_journal: Path
    phase_registration: Path
    phase_spawn: Path
    phase_completion: Path
    phase_finalization_intent: Path
    phase_terminal_incomplete: Path
    phase_finalization_success: Path
    checkpoint: Path
    expected_binding: Mapping[str, object]


@dataclass(frozen=True)
class StartupCalibrationCompletion:
    worker_pid: int
    observed_startup_elapsed_seconds: float
    derived_startup_limit_seconds: float
    result: object


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise RuntimeError(f"repair-010 JSON object drifted: {path}")
    return payload


def _read_config(config_path: Path = DEFAULT_CONFIG_PATH) -> dict[str, Any]:
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or set(config) != _CONFIG_KEYS:
        raise ValueError("repair-010 config schema drifted")
    preregistration = config["preregistration"]
    protocol = config["protocol_change"]
    successor = config["formal_successor"]
    frontier_import = config["frontier_import"]
    startup_calibration = config["startup_calibration"]
    joint = config["joint_ac_successor"]
    if (
        config.get("schema") != "rts_gmlc_v4_repair_010_joint_ac_successor_config_v1"
        or preregistration.get("id")
        != "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_010"
        or preregistration.get("candidate_frontier_outcomes_observed") is not True
        or preregistration.get("joint_ac_outcomes_observed") is not False
        or protocol.get("scientific_config_changed") is not True
        or protocol.get("joint_ac_protocol_changed") is not True
        or float(protocol.get("maximum_accepted_relative_gap_to_feasible_incumbent"))
        != 1.0e-3
        or protocol.get("post_result_threshold_tuning_allowed") is not False
        or float(successor.get("maximum_accepted_relative_gap_to_feasible_incumbent"))
        != 1.0e-3
        or successor.get("candidate_frontier_outcomes_observed") is not True
        or successor.get("old_frontier_is_predecessor_evidence_only") is not True
        or successor.get("timeout_or_incomplete_is_infeasibility_evidence") is not False
        or frontier_import
        != {
            "schema": "rts_gmlc_v4_repair_010_frontier_import_v1",
            "mode": "audited_immutable_copy",
            "source_preregistration_id": (
                "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_009"
            ),
            "source_preregistration_input_contract_sha256": (
                "978a8d4be15b0b82ce1df90514c3fe766f9fbff22771bf19a5ca911448c18f12"
            ),
            "source_frontier_input_contract_sha256": (
                "0b34bfe901d054ff8d42562ce21f336b1c6b0b34009ba2f01bc687b4ec37598d"
            ),
            "source_candidate_ids": [f"candidate_{index:02d}" for index in range(7)],
            "source_budget_checkpoint_count": 6,
            "source_nested_round_manifest_count": 22,
            "destination_relative_directory": "predecessor_frontier_import",
            "authority_loader": "repair_009_load_candidate_frontier",
            "source_outcomes_observed": True,
            "scientific_values_unchanged": True,
            "solver_calls_allowed": False,
            "direct_source_use_as_solver_input_allowed": False,
            "hard_links_allowed": False,
            "atomic_immutable_publication_required": True,
        }
        or startup_calibration
        != {
            "schema": "rts_gmlc_v4_repair_010_startup_calibration_contract_v2",
            "calibration_id": "rts_gmlc_v4_repair_010_startup_calibration_v2",
            "status": "frozen_before_first_v2_sample",
            "shared_adapter_authority_sha256": (SHARED_V4_ADAPTER_AUTHORITY_SHA256),
            "repair_010_adapter_sha256": (
                "6a5e66439d5b1c11f3f6820001a53b9d0de6645b78d2309b24408366f4de9220"
            ),
            "repair_004_checkpoint_authority": {
                "root": (
                    "results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_"
                    "commitment_v4_repair_004"
                ),
                "preregistration_id": (
                    "rts_gmlc_google_day0_zero_dc_ac_aware_commitment_v4_repair_004"
                ),
                "input_contract_sha256": (
                    "4aaf38250e9a72ffcc475103ccad4f62781e8c17794425ad67986af744480e7b"
                ),
                "checkpoint_schema": (
                    "rts_gmlc_v4_repair_004_hybrid_candidate_checkpoint_v1"
                ),
                "float_serialization": ("python_json_roundtrip_full_precision_v1"),
                "requested_candidate_ids": [
                    "q_proxy_delta_0p0010",
                    "q_proxy_delta_0p0025",
                    "q_proxy_delta_0p0050",
                    "q_proxy_delta_0p0100",
                ],
                "modes": [
                    "verified_predecessor_prefix",
                    "verified_predecessor_prefix",
                    "verified_predecessor_prefix",
                    "direct_then_level_set",
                ],
                "checkpoint_manifest_sha256s": [
                    "2bd1d1c6843c6397248d4cd5531f1911c2f91036174b00af0877987d01b74c41",
                    "98ab92e1a59f668203a66988b324cca75d764c4ed440fdf1c547d2279a00e8b2",
                    "42830c97b66be3f80231757aaa0f1a1732cfa5fa4d400f0c33be3b508c764f51",
                    "f929c097922937f4f85ca86c3714da2095060a10d59b1a14dfc3a51ca6d0759c",
                ],
                "candidate_json_sha256s": [
                    "60317c6f2ead2467d6a6e3b7e23dab692d054e8cb3e8f11691144ec2f32f737e",
                    "451a6cb559489f67e0b3a1d2e4f0fc02b9295238b0cf05aee06c9cc99df7c0b0",
                    "913c1f46d03f506c0c04f794eab5b6c64aabd084ac15d0f7f74b25472fe33b67",
                    "5efa62039ad86e3129d51d3ceba7a198311c9cfe9eb7048e3f78acf128d72448",
                ],
            },
            "predecessor_incomplete_evidence": {
                "schema": ("rts_gmlc_v4_repair_010_startup_calibration_predecessor_v1"),
                "calibration_id": ("rts_gmlc_v4_repair_010_startup_calibration_v1"),
                "config_path": (
                    "configs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_"
                    "v4_repair_010.yaml"
                ),
                "config_sha256": (
                    "04cc93faeb3006cbb45d03e0585ce311d6f54095a503c1cb254165ba2f4ab60f"
                ),
                "output_directory": (
                    "results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_"
                    "commitment_v4_repair_010_startup_calibration"
                ),
                "logging_directory": (
                    "results/logs/rts_gmlc_google_day0_zero_dc_ac_aware_"
                    "commitment_v4_repair_010_startup_calibration"
                ),
                "launcher_directory": (
                    "results/logs/rts_gmlc_google_day0_zero_dc_ac_aware_"
                    "commitment_v4_repair_010_startup_calibration_launcher"
                ),
                "contract_manifest_sha256": (
                    "a4ed4af3816061c42420a031f16a694827278fe94cda4e52cb8a980972eefa5f"
                ),
                "registration_manifest_sha256": (
                    "2a3c20658cea11fc5f0ccb4b0e23d87f0e634d3f53815f8dc58c23b73582ee54"
                ),
                "spawn_manifest_sha256": (
                    "c8b951e64ede31017845b8c7ccefdbaf21f4c607b4af9ffa8faf13c9006e4e68"
                ),
                "incomplete_manifest_sha256": (
                    "4f3ba6e497e388c2e9713355f7e7a035fb8387c6f60b07958b711c884244930d"
                ),
                "phase_journal_sha256": (
                    "947b823a2bcbc88f25a44269e1beded6e480ca223e9464c0ce7c0c01ed1706c3"
                ),
                "parent_pid": 18576,
                "worker_pid": 31312,
                "verified_phase_count": 2,
                "verified_phases": ["worker_started", "context_load_started"],
                "reason": "calibration_worker_exit_code:1",
                "solver_call_count": 0,
                "is_infeasibility_evidence": False,
                "resume_allowed": False,
            },
            "sample_count": 1,
            "candidate_id": "candidate_00",
            "initial_strategy": "source",
            "elapsed_start": "parent_monotonic_immediately_before_popen",
            "elapsed_stop": "parent_first_verified_calibration_pre_solver_stop",
            "elapsed_includes_process_creation": True,
            "actual_nlpsol_construction_required": True,
            "complete_solver_arguments_required": True,
            "solver_callable_invocations_allowed": 0,
            "solver_started_event_allowed": False,
            "calibration_max_wall_seconds": 21600.0,
            "parent_poll_interval_seconds": 5.0,
            "post_stop_worker_exit_limit_seconds": 300.0,
            "termination_grace_seconds": 30.0,
            "startup_limit_rule": "double_observed_then_ceil",
            "startup_limit_multiplier": 2.0,
            "startup_limit_round_up_seconds": 300.0,
            "statistical_tail_guarantee": False,
            "retry_or_resume_allowed": False,
            "result_may_modify_formal_config_automatically": False,
            "output_directory": (
                "results/tables/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_"
                "v4_repair_010_startup_calibration_v2"
            ),
            "logging_directory": (
                "results/logs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_"
                "v4_repair_010_startup_calibration_v2"
            ),
            "launcher_directory": (
                "results/logs/rts_gmlc_google_day0_zero_dc_ac_aware_commitment_"
                "v4_repair_010_startup_calibration_v2_launcher"
            ),
        }
        or joint.get("context_artifact_mode") != "disabled_unproven"
        or joint.get("context_artifact_equivalence_proven") is not False
        or joint.get("fallback_mode") != "fresh_rebuild_in_fresh_isolated_worker"
        or joint.get("fresh_isolated_worker_required") is not True
        or joint.get("required_phase_order") != list(REQUIRED_PHASES)
        or float(joint.get("solver_wall_limit_seconds_per_call")) != 7500.0
        or float(joint.get("ipopt_max_cpu_time_seconds_per_call")) != 7200.0
        or joint.get("solver_wall_starts_after_parent_verifies_solver_started")
        is not True
        or joint.get("event_missing_or_hash_drift_is_honest_incomplete") is not True
        or joint.get("pre_solver_incomplete_counts_as_solver_call") is not False
        or joint.get("retry_or_resume_incomplete_call_allowed") is not False
        or joint.get("blocking_reasons")
        != [
            "startup_limit_not_calibrated_on_fresh_isolated_worker",
            "formal_execution_ready_is_false",
            "successor_preregistration_not_published",
        ]
    ):
        raise ValueError("repair-010 frozen contract drifted")
    _verify_startup_calibration_v2_authority(config)
    _verify_predecessor_evidence(config)
    return config


def _verify_startup_calibration_v2_authority(
    config: Mapping[str, Any],
) -> None:
    """Bind V2 to the historical adapter and immutable failed V1 evidence."""

    contract = config["startup_calibration"]
    if (
        _sha256(SHARED_V4_ADAPTER_PATH) != SHARED_V4_ADAPTER_AUTHORITY_SHA256
        or contract["shared_adapter_authority_sha256"]
        != SHARED_V4_ADAPTER_AUTHORITY_SHA256
        or _sha256(REPAIR_010_ADAPTER_PATH) != contract["repair_010_adapter_sha256"]
    ):
        raise RuntimeError("repair-010 adapter authority drifted")

    checkpoint_authority = contract["repair_004_checkpoint_authority"]
    checkpoint_root = Path(checkpoint_authority["root"]) / "candidate_checkpoints"
    for index, requested_id in enumerate(
        checkpoint_authority["requested_candidate_ids"], start=1
    ):
        target = checkpoint_root / f"{index:02d}_{requested_id}"
        candidate_json = target / "candidate.json"
        manifest = target / "SHA256SUMS"
        _verify_manifest(target)
        observed = _load_json(candidate_json)
        if (
            _sha256(manifest)
            != checkpoint_authority["checkpoint_manifest_sha256s"][index - 1]
            or _sha256(candidate_json)
            != checkpoint_authority["candidate_json_sha256s"][index - 1]
            or observed.get("schema") != checkpoint_authority["checkpoint_schema"]
            or observed.get("float_serialization")
            != checkpoint_authority["float_serialization"]
            or observed.get("preregistration_id")
            != checkpoint_authority["preregistration_id"]
            or observed.get("input_contract_sha256")
            != checkpoint_authority["input_contract_sha256"]
            or observed.get("ordinal") != index
            or observed.get("mode") != checkpoint_authority["modes"][index - 1]
            or not isinstance(observed.get("candidate"), Mapping)
            or not isinstance(observed.get("evidence"), Mapping)
        ):
            raise RuntimeError("repair-004 checkpoint authority drifted")

    evidence = contract["predecessor_incomplete_evidence"]
    if (
        _sha256(Path(evidence["config_path"])) != evidence["config_sha256"]
        or Path(evidence["output_directory"]).resolve()
        == Path(contract["output_directory"]).resolve()
        or Path(evidence["logging_directory"]).resolve()
        == Path(contract["logging_directory"]).resolve()
        or Path(evidence["launcher_directory"]).resolve()
        == Path(contract["launcher_directory"]).resolve()
    ):
        raise RuntimeError("repair-010 calibration V1/V2 authority drifted")

    output_root = Path(evidence["output_directory"])
    manifest_paths = {
        "contract_manifest_sha256": output_root / "contract" / "SHA256SUMS",
        "registration_manifest_sha256": (output_root / "registration" / "SHA256SUMS"),
        "spawn_manifest_sha256": output_root / "spawn" / "SHA256SUMS",
        "incomplete_manifest_sha256": output_root / "incomplete" / "SHA256SUMS",
    }
    if any(
        not path.is_file() or _sha256(path) != evidence[key]
        for key, path in manifest_paths.items()
    ):
        raise RuntimeError("repair-010 calibration V1 manifest drifted")
    for manifest in manifest_paths.values():
        _verify_manifest(manifest.parent)

    registration = _load_json(
        output_root / "registration" / "calibration_registration.json"
    )
    spawn = _load_json(output_root / "spawn" / "calibration_spawn.json")
    incomplete = _load_json(output_root / "incomplete" / "calibration_incomplete.json")
    journal = Path(evidence["logging_directory"]) / "phase_journal.jsonl"
    records = load_verified_calibration_events(
        journal,
        expected_binding=registration["binding"],
        expected_worker_pid=int(evidence["worker_pid"]),
    )
    if (
        _sha256(journal) != evidence["phase_journal_sha256"]
        or registration.get("binding", {}).get("calibration_id")
        != evidence["calibration_id"]
        or spawn.get("binding") != registration.get("binding")
        or incomplete.get("binding") != registration.get("binding")
        or spawn.get("parent_pid") != evidence["parent_pid"]
        or spawn.get("worker_pid") != evidence["worker_pid"]
        or incomplete.get("parent_pid") != evidence["parent_pid"]
        or incomplete.get("reason") != evidence["reason"]
        or incomplete.get("solver_call_count") != evidence["solver_call_count"]
        or incomplete.get("is_infeasibility_evidence")
        is not evidence["is_infeasibility_evidence"]
        or incomplete.get("resume_allowed") is not evidence["resume_allowed"]
        or len(records) != evidence["verified_phase_count"]
        or [record["event"] for record in records] != evidence["verified_phases"]
        or (
            Path(evidence["logging_directory"]) / "native" / "calibration_ipopt.log"
        ).exists()
        or (output_root / "completion").exists()
        or (output_root / "worker_result").exists()
    ):
        raise RuntimeError("repair-010 calibration V1 incomplete evidence drifted")


def _verify_predecessor_evidence(config: Mapping[str, Any]) -> None:
    predecessor = config["predecessor_ifocus4"]
    root = Path(predecessor["root"])
    for path_key, hash_key in (
        ("config_path", "config_sha256"),
        ("runner_path", "runner_sha256"),
    ):
        path = Path(predecessor[path_key])
        if not path.is_file() or _sha256(path) != predecessor[hash_key]:
            raise RuntimeError(f"repair-010 predecessor {path_key} hash drifted")
    preregistration = root / "preregistration" / "SHA256SUMS"
    frontier = root / "candidate_frontier" / "SHA256SUMS"
    call = root / "joint_call_registry" / "candidate_00__source" / "SHA256SUMS"
    if (
        _sha256(preregistration) != predecessor["preregistration_manifest_sha256"]
        or _sha256(frontier) != predecessor["candidate_frontier_manifest_sha256"]
        or _sha256(call) != predecessor["terminal_call_manifest_sha256"]
        or (root / "joint_ac").exists()
    ):
        raise RuntimeError("repair-010 predecessor artifact drifted")
    attempt_id = predecessor["terminal_attempt_id"]
    log_root = (
        Path(config["logging"]["directory"]).parent
        / Path(config["logging"]["directory"]).name.replace(
            "repair_010", "repair_009_ifocus4"
        )
        / attempt_id
    )
    progress = [
        json.loads(line)
        for line in (log_root / "progress.jsonl")
        .read_text(encoding="utf-8")
        .splitlines()
    ]
    final = progress[-2]
    worker_log = log_root / "worker_process" / "candidate_00__source.log"
    native_log = log_root / "native" / "candidate_00__source.log"
    lease = (
        root
        / "execution_lease"
        / "history"
        / (predecessor["terminal_lease_id"] + ".failed")
    )
    terminal = _load_json(lease / "terminal.json")
    if (
        progress[0].get("expected_joint_call_count") != 21
        or final.get("event") != "joint_call_failed"
        or final.get("completed_joint_call_count") != 0
        or float(final.get("monotonic_elapsed_seconds"))
        != predecessor["terminal_elapsed_seconds"]
        or worker_log.stat().st_size != 0
        or native_log.exists()
        or terminal.get("status") != "failed"
        or terminal.get("error_type") != "TimeoutError"
        or predecessor.get("honest_incomplete") is not True
        or predecessor.get("is_infeasibility_evidence") is not False
        or predecessor.get("predecessor_resume_allowed") is not False
    ):
        raise RuntimeError("repair-010 predecessor terminal evidence drifted")


def _verify_manifest_tree(root: Path) -> int:
    manifests = sorted(root.rglob("SHA256SUMS"))
    if not manifests or root / "SHA256SUMS" not in manifests:
        raise RuntimeError(f"repair-010 source manifest tree is incomplete: {root}")
    for manifest in manifests:
        _verify_manifest(manifest.parent)
    return len(manifests)


def audit_predecessor_frontier_source(
    *,
    source_root: Path,
    predecessor_contract: Mapping[str, Any],
    import_contract: Mapping[str, Any],
    authority_loader: Callable[[Path], tuple[Sequence[object], str]] | None = None,
) -> FrontierSourceAudit:
    """Read-only full-chain audit; the authority loader must not call a solver."""

    preregistration_root = source_root / "preregistration"
    frontier_root = source_root / "candidate_frontier"
    checkpoints_root = source_root / "candidate_checkpoints"
    _verify_manifest_tree(preregistration_root)
    _verify_manifest_tree(frontier_root)
    preregistration_manifest = _sha256(preregistration_root / "SHA256SUMS")
    frontier_manifest = _sha256(frontier_root / "SHA256SUMS")
    if (
        preregistration_manifest
        != predecessor_contract["preregistration_manifest_sha256"]
        or frontier_manifest
        != predecessor_contract["candidate_frontier_manifest_sha256"]
    ):
        raise RuntimeError("repair-010 predecessor frontier root manifest drifted")

    registration = v4._load_json(preregistration_root, "registration.json")
    summary = v4._load_json(frontier_root, "summary.json")
    expected_candidate_ids = tuple(import_contract["source_candidate_ids"])
    if (
        registration.get("preregistration_id")
        != import_contract["source_preregistration_id"]
        or registration.get("input_contract_sha256")
        != import_contract["source_preregistration_input_contract_sha256"]
        or common_input_signature_sha256(registration.get("input_contract"))
        != registration.get("input_contract_sha256")
        or summary.get("preregistration_id")
        != import_contract["source_preregistration_id"]
        or summary.get("input_contract_sha256")
        != import_contract["source_frontier_input_contract_sha256"]
        or tuple(summary.get("candidate_ids", ())) != expected_candidate_ids
        or summary.get("requested_candidate_count") != len(expected_candidate_ids)
        or summary.get("unique_candidate_count") != len(expected_candidate_ids)
        or summary.get("joint_ac_solver_call_count") != 0
    ):
        raise RuntimeError("repair-010 predecessor frontier contract drifted")
    with (frontier_root / "candidates.csv").open(
        "r", encoding="utf-8", newline=""
    ) as stream:
        csv_candidate_ids = tuple(
            str(row["candidate_id"]) for row in csv.DictReader(stream)
        )
    if csv_candidate_ids != expected_candidate_ids:
        raise RuntimeError("repair-010 predecessor candidate inventory drifted")

    checkpoint_manifests = summary.get("candidate_checkpoint_manifest_sha256s")
    checkpoint_entries = sorted(checkpoints_root.iterdir())
    if any(not path.is_dir() or path.is_symlink() for path in checkpoint_entries):
        raise RuntimeError("repair-010 predecessor checkpoint inventory drifted")
    checkpoint_directories = checkpoint_entries
    if (
        not isinstance(checkpoint_manifests, dict)
        or len(checkpoint_manifests)
        != import_contract["source_budget_checkpoint_count"]
        or len(checkpoint_directories)
        != import_contract["source_budget_checkpoint_count"]
    ):
        raise RuntimeError("repair-010 predecessor checkpoint inventory drifted")
    observed_checkpoint_manifests: list[tuple[str, str]] = []
    nested_round_manifest_count = 0
    for checkpoint_root in checkpoint_directories:
        manifest_count = _verify_manifest_tree(checkpoint_root)
        nested_round_manifest_count += manifest_count - 1
        candidate_payload = v4._load_json(checkpoint_root, "candidate.json")
        candidate = candidate_payload.get("candidate")
        requested_candidate_id = (
            candidate.get("requested_candidate_id")
            if isinstance(candidate, Mapping)
            else None
        )
        manifest = _sha256(checkpoint_root / "SHA256SUMS")
        if (
            not isinstance(requested_candidate_id, str)
            or checkpoint_manifests.get(requested_candidate_id) != manifest
        ):
            raise RuntimeError("repair-010 predecessor checkpoint binding drifted")
        observed_checkpoint_manifests.append((requested_candidate_id, manifest))
    if (
        nested_round_manifest_count
        != import_contract["source_nested_round_manifest_count"]
    ):
        raise RuntimeError("repair-010 predecessor round manifest inventory drifted")

    if authority_loader is not None:
        loaded_candidates, loaded_manifest = authority_loader(source_root)
        loaded_ids = tuple(
            str(
                item.candidate_id
                if hasattr(item, "candidate_id")
                else item["candidate_id"]
            )
            for item in loaded_candidates
        )
        if loaded_manifest != frontier_manifest or loaded_ids != expected_candidate_ids:
            raise RuntimeError("repair-010 predecessor authority loader drifted")

    return FrontierSourceAudit(
        source_preregistration_manifest_sha256=preregistration_manifest,
        source_frontier_manifest_sha256=frontier_manifest,
        source_preregistration_input_contract_sha256=str(
            registration["input_contract_sha256"]
        ),
        source_frontier_input_contract_sha256=str(summary["input_contract_sha256"]),
        candidate_ids=expected_candidate_ids,
        budget_checkpoint_manifest_sha256s=tuple(observed_checkpoint_manifests),
        nested_round_manifest_count=nested_round_manifest_count,
    )


def audit_configured_predecessor_frontier_source(
    config: Mapping[str, Any],
    *,
    authority_loader: Callable[[Path], tuple[Sequence[object], str]] | None = None,
) -> FrontierSourceAudit:
    return audit_predecessor_frontier_source(
        source_root=Path(config["predecessor_ifocus4"]["root"]),
        predecessor_contract=config["predecessor_ifocus4"],
        import_contract=config["frontier_import"],
        authority_loader=authority_loader,
    )


def _assert_successor_ready(config: Mapping[str, Any]) -> None:
    joint = config["joint_ac_successor"]
    reasons = []
    startup_limit = joint.get("startup_limit_seconds")
    if startup_limit is None:
        reasons.append("startup_limit_seconds is not calibrated")
    elif (
        isinstance(startup_limit, bool)
        or not isinstance(startup_limit, (int, float))
        or not math.isfinite(float(startup_limit))
        or float(startup_limit) <= 0.0
    ):
        raise ValueError("repair-010 startup limit must be positive and finite")
    if joint.get("formal_execution_ready") is not True:
        reasons.append("formal_execution_ready is false")
    if (
        config["preregistration"].get("status")
        != "repository_local_not_externally_timestamped"
    ):
        reasons.append("successor preregistration status remains blocked")
    if reasons:
        raise SuccessorNotReadyError(
            "repair-010 is fail-closed before preregistration/formal run: "
            + "; ".join(reasons)
        )


def _assert_startup_calibration_only(config: Mapping[str, Any]) -> None:
    """Allow only the frozen calibration exception while formal gates stay closed."""

    joint = config["joint_ac_successor"]
    preregistration = config["preregistration"]
    if (
        joint.get("startup_limit_seconds") is not None
        or joint.get("formal_execution_ready") is not False
        or preregistration.get("status")
        != "blocked_before_repository_local_preregistration"
    ):
        raise SuccessorNotReadyError(
            "repair-010 startup calibration requires the formal gates to remain closed"
        )


def derive_startup_limit_seconds(
    observed_startup_elapsed_seconds: float,
    calibration_contract: Mapping[str, object],
) -> float:
    """Apply the frozen non-statistical single-sample watchdog rule."""

    observed = float(observed_startup_elapsed_seconds)
    multiplier = float(calibration_contract["startup_limit_multiplier"])
    quantum = float(calibration_contract["startup_limit_round_up_seconds"])
    if (
        not math.isfinite(observed)
        or observed <= 0.0
        or calibration_contract.get("startup_limit_rule") != "double_observed_then_ceil"
        or multiplier != 2.0
        or not math.isfinite(quantum)
        or quantum != 300.0
    ):
        raise ValueError("repair-010 startup calibration rule drifted")
    return float(math.ceil((multiplier * observed) / quantum) * quantum)


def _calibration_candidate_record(config: Mapping[str, Any]) -> dict[str, str]:
    contract = config["startup_calibration"]
    frontier = Path(config["predecessor_ifocus4"]["root"]) / "candidate_frontier"
    with (frontier / "candidates.csv").open(
        "r", encoding="utf-8", newline=""
    ) as stream:
        matches = [
            row
            for row in csv.DictReader(stream)
            if row.get("candidate_id") == contract["candidate_id"]
        ]
    if len(matches) != 1:
        raise RuntimeError("repair-010 calibration candidate identity drifted")
    record = matches[0]
    if any(
        re.fullmatch(r"[0-9a-f]{64}", str(record.get(key, ""))) is None
        for key in ("commitment_sha256", "dispatch_sha256")
    ):
        raise RuntimeError("repair-010 calibration candidate hash drifted")
    return {key: str(value) for key, value in record.items()}


def _calibration_runtime_options(
    config: Mapping[str, Any], native_log: Path
) -> dict[str, object]:
    joint = config["joint_ac_successor"]
    return {
        "ipopt.max_cpu_time": float(joint["ipopt_max_cpu_time_seconds_per_call"]),
        "ipopt.output_file": str(native_log.resolve()),
        "ipopt.file_print_level": 5,
    }


def build_startup_calibration_binding(
    *,
    config_path: Path,
    config: Mapping[str, Any],
    source_audit: FrontierSourceAudit,
    candidate_record: Mapping[str, str],
    native_log: Path,
    software_identity: Mapping[str, object] | None = None,
) -> dict[str, object]:
    contract = config["startup_calibration"]
    binding = {
        "schema": "rts_gmlc_v4_repair_010_startup_calibration_binding_v2",
        "calibration_id": contract["calibration_id"],
        "calibration_contract_sha256": canonical_sha256(contract),
        "config_sha256": _sha256(config_path),
        "runner_sha256": _sha256(Path(__file__)),
        "shared_adapter_authority_sha256": _sha256(SHARED_V4_ADAPTER_PATH),
        "repair_010_adapter_sha256": _sha256(REPAIR_010_ADAPTER_PATH),
        "core_sha256": _sha256(Path("src/grid/rts_gmlc_ac_aware_commitment.py")),
        "phase_contract_sha256": _sha256(
            Path("src/solvers/joint_ac_phase_contract.py")
        ),
        "source_preregistration_manifest_sha256": (
            source_audit.source_preregistration_manifest_sha256
        ),
        "source_frontier_manifest_sha256": (
            source_audit.source_frontier_manifest_sha256
        ),
        "source_preregistration_input_contract_sha256": (
            source_audit.source_preregistration_input_contract_sha256
        ),
        "source_frontier_input_contract_sha256": (
            source_audit.source_frontier_input_contract_sha256
        ),
        "candidate_id": contract["candidate_id"],
        "commitment_sha256": candidate_record["commitment_sha256"],
        "dispatch_sha256": candidate_record["dispatch_sha256"],
        "initial_strategy": contract["initial_strategy"],
        "ipopt_options_sha256": v4_adapter.effective_ipopt_options_sha256(
            base_options=shared_ipopt._FROZEN_IPOPT_OPTIONS,
            runtime_options=_calibration_runtime_options(config, native_log),
        ),
        "software_identity": dict(software_identity or _software_identity()),
    }
    return binding


def _publish_exact_artifact(
    target: Path, filename: str, payload: Mapping[str, object]
) -> str:
    if target.exists():
        raise FileExistsError(
            f"Immutable calibration artifact already exists: {target}"
        )

    def writer(staging: Path) -> None:
        v4._write_exact_json(staging / filename, payload)

    v4._publish_immutable_payload(target, writer)
    _load_exact_calibration_artifact(target, filename=filename, payload=payload)
    return _sha256(target / "SHA256SUMS")


def _load_exact_calibration_artifact(
    target: Path, *, filename: str, payload: Mapping[str, object]
) -> dict[str, Any]:
    v4._verify_output_manifest(target)
    observed = v4._load_json(target, filename)
    if v4._exact_json_text(observed) != v4._exact_json_text(
        v4._exact_json_payload(payload)
    ):
        raise StartupCalibrationPersistenceError(
            f"repair-010 calibration artifact drifted after publication: {target}"
        )
    return observed


def register_startup_calibration(
    registration_directory: Path,
    *,
    binding: Mapping[str, object],
    contract_directory: Path,
    phase_journal: Path,
    worker_result: Path,
    native_solver_log: Path,
    worker_process_log: Path,
    parent_pid: int,
) -> str:
    if (
        isinstance(parent_pid, bool)
        or not isinstance(parent_pid, int)
        or parent_pid <= 0
    ):
        raise ValueError("repair-010 calibration parent PID drifted")
    v4._verify_output_manifest(contract_directory)
    payload = {
        "schema": "rts_gmlc_v4_repair_010_startup_calibration_registration_v1",
        "binding": dict(binding),
        "binding_sha256": canonical_sha256(dict(binding)),
        "contract_directory": str(contract_directory.resolve()),
        "contract_manifest_sha256": _sha256(contract_directory / "SHA256SUMS"),
        "phase_journal": str(phase_journal.resolve()),
        "worker_result": str(worker_result.resolve()),
        "native_solver_log": str(native_solver_log.resolve()),
        "worker_process_log": str(worker_process_log.resolve()),
        "parent_pid": parent_pid,
        "solver_calls_allowed": False,
        "retry_or_resume_allowed": False,
    }
    return _publish_exact_artifact(
        registration_directory, "calibration_registration.json", payload
    )


def load_verified_startup_calibration_registration(
    registration_directory: Path,
    *,
    expected_binding: Mapping[str, object],
) -> dict[str, Any]:
    v4._verify_output_manifest(registration_directory)
    registration = v4._load_json(
        registration_directory, "calibration_registration.json"
    )
    contract_directory = Path(str(registration.get("contract_directory")))
    if (
        registration.get("schema")
        != "rts_gmlc_v4_repair_010_startup_calibration_registration_v1"
        or registration.get("binding") != dict(expected_binding)
        or registration.get("binding_sha256")
        != canonical_sha256(dict(expected_binding))
        or not contract_directory.is_dir()
        or registration.get("contract_manifest_sha256")
        != _sha256(contract_directory / "SHA256SUMS")
        or isinstance(registration.get("parent_pid"), bool)
        or not isinstance(registration.get("parent_pid"), int)
        or registration["parent_pid"] <= 0
        or registration.get("solver_calls_allowed") is not False
        or registration.get("retry_or_resume_allowed") is not False
    ):
        raise PhaseContractError("repair-010 calibration registration drifted")
    return registration


def register_startup_calibration_spawn(
    spawn_directory: Path,
    *,
    registration_directory: Path,
    binding: Mapping[str, object],
    worker_pid: int,
) -> str:
    registration = load_verified_startup_calibration_registration(
        registration_directory, expected_binding=binding
    )
    if (
        isinstance(worker_pid, bool)
        or not isinstance(worker_pid, int)
        or worker_pid <= 0
    ):
        raise ValueError("repair-010 calibration worker PID drifted")
    payload = {
        "schema": "rts_gmlc_v4_repair_010_startup_calibration_spawn_v1",
        "binding": dict(binding),
        "binding_sha256": canonical_sha256(dict(binding)),
        "registration_manifest_sha256": _sha256(registration_directory / "SHA256SUMS"),
        "parent_pid": registration["parent_pid"],
        "worker_pid": worker_pid,
    }
    return _publish_exact_artifact(spawn_directory, "calibration_spawn.json", payload)


def load_verified_startup_calibration_spawn(
    spawn_directory: Path,
    *,
    registration_directory: Path,
    expected_binding: Mapping[str, object],
) -> dict[str, Any]:
    registration = load_verified_startup_calibration_registration(
        registration_directory, expected_binding=expected_binding
    )
    v4._verify_output_manifest(spawn_directory)
    spawn = v4._load_json(spawn_directory, "calibration_spawn.json")
    worker_pid = spawn.get("worker_pid")
    if (
        spawn.get("schema") != "rts_gmlc_v4_repair_010_startup_calibration_spawn_v1"
        or spawn.get("binding") != dict(expected_binding)
        or spawn.get("binding_sha256") != canonical_sha256(dict(expected_binding))
        or spawn.get("registration_manifest_sha256")
        != _sha256(registration_directory / "SHA256SUMS")
        or spawn.get("parent_pid") != registration.get("parent_pid")
        or isinstance(worker_pid, bool)
        or not isinstance(worker_pid, int)
        or worker_pid <= 0
    ):
        raise PhaseContractError("repair-010 calibration spawn receipt drifted")
    return spawn


def register_startup_calibration_incomplete(
    incomplete_directory: Path,
    *,
    completion_directory: Path,
    binding: Mapping[str, object],
    registration_directory: Path,
    spawn_directory: Path,
    phase_journal: Path,
    reason: str,
) -> str:
    if completion_directory.exists():
        raise StartupCalibrationCompletionCommitIndeterminateError(
            "repair-010 calibration completion state exists; incomplete "
            "publication is forbidden"
        )
    registration = load_verified_startup_calibration_registration(
        registration_directory, expected_binding=binding
    )
    spawn_manifest = (
        _sha256(spawn_directory / "SHA256SUMS")
        if (spawn_directory / "SHA256SUMS").is_file()
        else None
    )
    journal_sha = _sha256(phase_journal) if phase_journal.is_file() else None
    payload = {
        "schema": "rts_gmlc_v4_repair_010_startup_calibration_incomplete_v1",
        "binding": dict(binding),
        "binding_sha256": canonical_sha256(dict(binding)),
        "registration_manifest_sha256": _sha256(registration_directory / "SHA256SUMS"),
        "spawn_manifest_observed_sha256": spawn_manifest,
        "phase_journal_observed_sha256": journal_sha,
        "parent_pid": registration["parent_pid"],
        "reason": reason,
        "solver_call_count": 0,
        "is_infeasibility_evidence": False,
        "resume_allowed": False,
    }
    return _publish_exact_artifact(
        incomplete_directory, "calibration_incomplete.json", payload
    )


def _startup_calibration_completion_payload(
    *,
    binding: Mapping[str, object],
    registration_directory: Path,
    spawn_directory: Path,
    phase_journal: Path,
    worker_result: Path,
    observed_startup_elapsed_seconds: float,
    calibration_contract: Mapping[str, object],
) -> dict[str, object]:
    spawn = load_verified_startup_calibration_spawn(
        spawn_directory,
        registration_directory=registration_directory,
        expected_binding=binding,
    )
    worker_pid = int(spawn["worker_pid"])
    events = load_verified_calibration_events(
        phase_journal,
        expected_binding=binding,
        expected_worker_pid=worker_pid,
    )
    phases = tuple(
        record["event"]
        for record in events
        if record["event"] in CALIBRATION_REQUIRED_PHASES
    )
    if phases != CALIBRATION_REQUIRED_PHASES or any(
        record["event"] in {"solver_started", "solver_finished", "solver_heartbeat"}
        for record in events
    ):
        raise PhaseContractError("repair-010 calibration journal is incomplete")
    v4._verify_output_manifest(worker_result)
    stop_payload = next(
        record["payload"]
        for record in events
        if record["event"] == "calibration_pre_solver_stop"
    )
    derived = derive_startup_limit_seconds(
        observed_startup_elapsed_seconds, calibration_contract
    )
    return {
        "schema": "rts_gmlc_v4_repair_010_startup_calibration_completion_v1",
        "binding": dict(binding),
        "binding_sha256": canonical_sha256(dict(binding)),
        "registration_manifest_sha256": _sha256(registration_directory / "SHA256SUMS"),
        "spawn_manifest_sha256": _sha256(spawn_directory / "SHA256SUMS"),
        "phase_journal_sha256": _sha256(phase_journal),
        "worker_result_manifest_sha256": _sha256(worker_result / "SHA256SUMS"),
        "worker_pid": worker_pid,
        "observed_startup_elapsed_seconds": float(observed_startup_elapsed_seconds),
        "derived_startup_limit_seconds": derived,
        "startup_limit_rule": calibration_contract["startup_limit_rule"],
        "startup_limit_multiplier": calibration_contract["startup_limit_multiplier"],
        "startup_limit_round_up_seconds": calibration_contract[
            "startup_limit_round_up_seconds"
        ],
        "solver_input_fingerprint_sha256": stop_payload[
            "solver_input_fingerprint_sha256"
        ],
        "actual_nlpsol_constructed": True,
        "complete_solver_arguments_verified": True,
        "solver_callable_invocation_count": 0,
        "solver_call_count": 0,
        "is_infeasibility_evidence": False,
        "resume_allowed": False,
        "formal_config_modified": False,
        "statistical_tail_guarantee": False,
    }


def register_startup_calibration_completion(
    completion_directory: Path,
    *,
    incomplete_directory: Path,
    binding: Mapping[str, object],
    registration_directory: Path,
    spawn_directory: Path,
    phase_journal: Path,
    worker_result: Path,
    observed_startup_elapsed_seconds: float,
    calibration_contract: Mapping[str, object],
) -> None:
    if incomplete_directory.exists():
        raise StartupCalibrationCompletionCommitIndeterminateError(
            "repair-010 calibration incomplete state exists; completion "
            "publication is forbidden"
        )
    payload = _startup_calibration_completion_payload(
        binding=binding,
        registration_directory=registration_directory,
        spawn_directory=spawn_directory,
        phase_journal=phase_journal,
        worker_result=worker_result,
        observed_startup_elapsed_seconds=observed_startup_elapsed_seconds,
        calibration_contract=calibration_contract,
    )
    if completion_directory.exists():
        try:
            _load_exact_calibration_artifact(
                completion_directory,
                filename="calibration_completion.json",
                payload=payload,
            )
        except BaseException as validation_error:
            raise StartupCalibrationCompletionCommitIndeterminateError(
                "repair-010 calibration completion target already exists but its "
                "exact commit cannot be proven"
            ) from validation_error
        raise StartupCalibrationNoResumeError(
            "repair-010 calibration completion already exists; duplicate forbidden"
        )

    def writer(staging: Path) -> None:
        v4._write_exact_json(staging / "calibration_completion.json", payload)

    try:
        v4._publish_immutable_payload(completion_directory, writer)
    except BaseException as publish_error:
        try:
            committed_state = completion_directory.stat()
        except FileNotFoundError:
            raise publish_error
        except BaseException as state_error:
            raise StartupCalibrationCompletionCommitIndeterminateError(
                "repair-010 calibration completion target state is unreadable "
                "after publication failure"
            ) from state_error
        if not stat.S_ISDIR(committed_state.st_mode):
            raise StartupCalibrationCompletionCommitIndeterminateError(
                "repair-010 calibration completion target exists but is not a "
                "directory"
            ) from publish_error
        try:
            _load_exact_calibration_artifact(
                completion_directory,
                filename="calibration_completion.json",
                payload=payload,
            )
        except BaseException as validation_error:
            raise StartupCalibrationCompletionCommitIndeterminateError(
                "repair-010 calibration completion target exists but its exact "
                "committed payload cannot be proven"
            ) from validation_error


def load_verified_startup_calibration_completion(
    completion_directory: Path,
    *,
    incomplete_directory: Path,
    binding: Mapping[str, object],
    registration_directory: Path,
    spawn_directory: Path,
    phase_journal: Path,
    worker_result: Path,
    calibration_contract: Mapping[str, object],
) -> dict[str, Any]:
    if incomplete_directory.exists():
        raise StartupCalibrationCompletionCommitIndeterminateError(
            "repair-010 calibration completion/incomplete states coexist"
        )
    v4._verify_output_manifest(completion_directory)
    observed = v4._load_json(completion_directory, "calibration_completion.json")
    elapsed = observed.get("observed_startup_elapsed_seconds")
    if isinstance(elapsed, bool) or not isinstance(elapsed, (int, float)):
        raise PhaseContractError("repair-010 calibration completion elapsed drifted")
    payload = _startup_calibration_completion_payload(
        binding=binding,
        registration_directory=registration_directory,
        spawn_directory=spawn_directory,
        phase_journal=phase_journal,
        worker_result=worker_result,
        observed_startup_elapsed_seconds=float(elapsed),
        calibration_contract=calibration_contract,
    )
    return _load_exact_calibration_artifact(
        completion_directory,
        filename="calibration_completion.json",
        payload=payload,
    )


def run_startup_calibration_process(
    *,
    command: Sequence[str],
    registration_directory: Path,
    spawn_directory: Path,
    phase_journal: Path,
    expected_binding: Mapping[str, object],
    worker_process_log: Path,
    result_validator: Callable[[], object],
    calibration_contract: Mapping[str, object],
    on_incomplete: Callable[[str], None],
) -> StartupCalibrationCompletion:
    """Run one fresh calibration child through the verified pre-solver stop."""

    if (
        phase_journal.exists()
        or worker_process_log.exists()
        or spawn_directory.exists()
    ):
        raise FileExistsError("repair-010 startup calibration cannot resume")
    load_verified_startup_calibration_registration(
        registration_directory, expected_binding=expected_binding
    )
    worker_process_log.parent.mkdir(parents=True, exist_ok=True)
    phase_journal.parent.mkdir(parents=True, exist_ok=True)
    maximum_wall = float(calibration_contract["calibration_max_wall_seconds"])
    post_stop_limit = float(calibration_contract["post_stop_worker_exit_limit_seconds"])
    grace = float(calibration_contract["termination_grace_seconds"])
    poll = float(calibration_contract["parent_poll_interval_seconds"])
    if any(
        not math.isfinite(value) or value <= 0.0
        for value in (maximum_wall, post_stop_limit, grace, poll)
    ):
        raise ValueError("repair-010 calibration timing contract drifted")
    environment = os.environ.copy()
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    process: subprocess.Popen[bytes] | None = None
    stop_verified_at: float | None = None
    try:
        with worker_process_log.open("xb") as output:
            # This sample and Popen must remain adjacent: the frozen elapsed
            # definition excludes parent-side log/directory preparation.
            started = time.monotonic()
            process = subprocess.Popen(
                list(command),
                cwd=Path(__file__).resolve().parents[1],
                stdout=output,
                stderr=subprocess.STDOUT,
                env=environment,
            )
            register_startup_calibration_spawn(
                spawn_directory,
                registration_directory=registration_directory,
                binding=expected_binding,
                worker_pid=process.pid,
            )
            while True:
                events = load_verified_calibration_events(
                    phase_journal,
                    expected_binding=expected_binding,
                    expected_worker_pid=process.pid,
                )
                # The stop sample is deliberately taken only after the complete
                # actual-PID/binding/fingerprint journal validation above.
                observed = time.monotonic()
                if any(
                    record["event"] == "calibration_pre_solver_stop"
                    for record in events
                ):
                    if stop_verified_at is None:
                        stop_verified_at = observed
                if observed - started >= maximum_wall:
                    raise StartupCalibrationIncompleteError(
                        "calibration_wall_timeout_before_verified_pre_solver_stop"
                    )
                if (
                    stop_verified_at is not None
                    and observed - stop_verified_at >= post_stop_limit
                ):
                    raise StartupCalibrationIncompleteError(
                        "calibration_worker_exit_timeout_after_verified_pre_solver_stop"
                    )
                return_code = process.poll()
                if return_code is not None:
                    if return_code != 0:
                        raise StartupCalibrationIncompleteError(
                            f"calibration_worker_exit_code:{return_code}"
                        )
                    phases = tuple(
                        record["event"]
                        for record in events
                        if record["event"] in CALIBRATION_REQUIRED_PHASES
                    )
                    if (
                        phases != CALIBRATION_REQUIRED_PHASES
                        or stop_verified_at is None
                    ):
                        raise StartupCalibrationIncompleteError(
                            "calibration_worker_exit_before_verified_pre_solver_stop"
                        )
                    result = result_validator()
                    elapsed = stop_verified_at - started
                    return StartupCalibrationCompletion(
                        worker_pid=process.pid,
                        observed_startup_elapsed_seconds=elapsed,
                        derived_startup_limit_seconds=derive_startup_limit_seconds(
                            elapsed, calibration_contract
                        ),
                        result=result,
                    )
                time.sleep(poll)
    except BaseException as error:
        if process is not None:
            _stop_worker(process, grace)
        reason = (
            error.reason
            if isinstance(error, StartupCalibrationIncompleteError)
            else f"calibration_phase_or_parent_failure:{type(error).__name__}:{error}"
        )
        try:
            on_incomplete(reason)
        except BaseException as persistence_error:
            raise StartupCalibrationPersistenceError(
                "repair-010 calibration incomplete receipt could not be persisted"
            ) from persistence_error
        if isinstance(error, StartupCalibrationIncompleteError):
            raise
        raise StartupCalibrationIncompleteError(reason) from error


def finalize_startup_calibration(
    *,
    completion: StartupCalibrationCompletion,
    completion_directory: Path,
    incomplete_directory: Path,
    binding: Mapping[str, object],
    registration_directory: Path,
    spawn_directory: Path,
    phase_journal: Path,
    worker_result: Path,
    calibration_contract: Mapping[str, object],
    persist_incomplete: Callable[[str], None],
) -> dict[str, Any]:
    """Commit exactly one terminal calibration truth after a valid sample."""

    try:
        register_startup_calibration_completion(
            completion_directory,
            incomplete_directory=incomplete_directory,
            binding=binding,
            registration_directory=registration_directory,
            spawn_directory=spawn_directory,
            phase_journal=phase_journal,
            worker_result=worker_result,
            observed_startup_elapsed_seconds=(
                completion.observed_startup_elapsed_seconds
            ),
            calibration_contract=calibration_contract,
        )
    except (
        StartupCalibrationCompletionCommitIndeterminateError,
        StartupCalibrationNoResumeError,
    ):
        raise
    except BaseException as error:
        reason = f"calibration_parent_completion_failure:{type(error).__name__}:{error}"
        try:
            persist_incomplete(reason)
        except BaseException as persistence_error:
            raise StartupCalibrationPersistenceError(
                "repair-010 calibration completion and incomplete publication failed"
            ) from persistence_error
        raise StartupCalibrationIncompleteError(reason) from error
    try:
        return load_verified_startup_calibration_completion(
            completion_directory,
            incomplete_directory=incomplete_directory,
            binding=binding,
            registration_directory=registration_directory,
            spawn_directory=spawn_directory,
            phase_journal=phase_journal,
            worker_result=worker_result,
            calibration_contract=calibration_contract,
        )
    except StartupCalibrationCompletionCommitIndeterminateError:
        raise
    except BaseException as validation_error:
        raise StartupCalibrationCompletionCommitIndeterminateError(
            "repair-010 committed calibration completion could not be revalidated"
        ) from validation_error


def _publish_launcher_artifact(
    target: Path, *, filename: str, payload: Mapping[str, object]
) -> str:
    """Publish one launcher receipt and reconcile a post-rename exception."""

    if target.exists():
        raise StartupCalibrationNoResumeError(
            f"repair-010 launcher artifact already exists: {target}"
        )

    def writer(staging: Path) -> None:
        v4._write_exact_json(staging / filename, payload)

    try:
        v4._publish_immutable_payload(target, writer)
    except BaseException:
        if not target.exists():
            raise
        try:
            _load_exact_calibration_artifact(target, filename=filename, payload=payload)
        except BaseException as validation_error:
            raise StartupCalibrationLauncherPersistenceError(
                "repair-010 launcher artifact target exists but its exact commit "
                "cannot be proven"
            ) from validation_error
    return _sha256(target / "SHA256SUMS")


def run_startup_calibration_launcher_process(
    *,
    command: Sequence[str],
    stdout_path: Path,
    stderr_path: Path,
    termination_grace_seconds: float,
    on_pid: Callable[[int], None],
    on_started: Callable[[int], None],
    on_failed: Callable[[int, int, str], None],
    creationflags: int = 0,
) -> int:
    """Spawn one background parent and close every post-spawn failure state."""

    stdout_path.parent.mkdir(parents=True, exist_ok=True)
    process: subprocess.Popen[bytes] | None = None
    try:
        with stdout_path.open("xb") as stdout, stderr_path.open("xb") as stderr:
            process = subprocess.Popen(
                list(command),
                cwd=Path(__file__).resolve().parents[1],
                stdout=stdout,
                stderr=stderr,
                env={**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
                creationflags=creationflags,
            )
            on_pid(process.pid)
            on_started(process.pid)
            return process.pid
    except BaseException as launch_error:
        if process is None:
            raise
        reason = (
            f"launcher_post_spawn_failure:{type(launch_error).__name__}:{launch_error}"
        )
        try:
            _stop_worker(process, termination_grace_seconds)
            return_code = process.poll()
            if return_code is None:
                raise RuntimeError("spawned calibration child is still alive")
            on_failed(process.pid, int(return_code), reason)
        except BaseException as persistence_error:
            raise StartupCalibrationLauncherPersistenceError(
                "repair-010 launcher could not prove child death and immutable "
                "launcher-failed publication; launcher root permanently blocks retry"
            ) from persistence_error
        raise StartupCalibrationLauncherFailedError(
            reason, worker_pid=process.pid, return_code=int(return_code)
        ) from launch_error


def _startup_calibration_launcher_command(
    *, config_path: Path, launcher_directory: Path
) -> tuple[str, ...]:
    return (
        sys.executable,
        "-u",
        "-B",
        "-m",
        _SUCCESSOR_MODULE,
        "--config",
        str(config_path),
        "--stage",
        "calibrate-startup",
        "--calibration-launcher-directory",
        str(launcher_directory),
    )


def _verify_startup_calibration_launcher_authorization(
    *,
    launcher_directory: Path,
    config_path: Path,
    config: Mapping[str, Any],
) -> None:
    frozen = Path(config["startup_calibration"]["launcher_directory"])
    if launcher_directory.resolve() != frozen.resolve():
        raise StartupCalibrationNoResumeError(
            "repair-010 calibration launcher directory drifted"
        )
    request_directory = launcher_directory / "request"
    pid_directory = launcher_directory / "pid"
    started_directory = launcher_directory / "started"
    failed_directory = launcher_directory / "failed"
    deadline = time.monotonic() + 30.0
    while not started_directory.is_dir() and not failed_directory.exists():
        if time.monotonic() >= deadline:
            raise StartupCalibrationNoResumeError(
                "repair-010 launcher started receipt was not published"
            )
        time.sleep(0.05)
    if failed_directory.exists():
        raise StartupCalibrationNoResumeError(
            "repair-010 launcher has immutable failed state"
        )
    v4._verify_output_manifest(request_directory)
    v4._verify_output_manifest(pid_directory)
    v4._verify_output_manifest(started_directory)
    request = v4._load_json(request_directory, "launcher_request.json")
    pid_receipt = v4._load_json(pid_directory, "launcher_pid.json")
    started = v4._load_json(started_directory, "launcher_started.json")
    if (
        request.get("schema")
        != "rts_gmlc_v4_repair_010_startup_calibration_launcher_request_v2"
        or request.get("config_sha256") != _sha256(config_path)
        or request.get("runner_sha256") != _sha256(Path(__file__))
        or request.get("calibration_contract_sha256")
        != canonical_sha256(config["startup_calibration"])
        or request.get("solver_callable_invocations_allowed") != 0
        or request.get("formal_execution_authorized") is not False
        or pid_receipt.get("schema")
        != "rts_gmlc_v4_repair_010_startup_calibration_launcher_pid_v2"
        or pid_receipt.get("request_manifest_sha256")
        != _sha256(request_directory / "SHA256SUMS")
        or pid_receipt.get("pid") != os.getpid()
        or started.get("schema")
        != "rts_gmlc_v4_repair_010_startup_calibration_launcher_started_v2"
        or started.get("request_manifest_sha256")
        != _sha256(request_directory / "SHA256SUMS")
        or started.get("pid_manifest_sha256") != _sha256(pid_directory / "SHA256SUMS")
        or started.get("pid") != os.getpid()
    ):
        raise StartupCalibrationNoResumeError(
            "repair-010 calibration launcher binding/PID drifted"
        )


def launch_startup_calibration(
    config_path: Path = DEFAULT_CONFIG_PATH,
) -> dict[str, Any]:
    """Launch the calibration parent in the background without running formal work."""

    config = _read_config(config_path)
    _assert_startup_calibration_only(config)
    contract = config["startup_calibration"]
    output_root = Path(contract["output_directory"])
    log_root = Path(contract["logging_directory"])
    launcher_root = Path(contract["launcher_directory"])
    if output_root.exists() or log_root.exists() or launcher_root.exists():
        raise StartupCalibrationNoResumeError(
            "repair-010 calibration/launcher state already exists; retry forbidden"
        )
    request_directory = launcher_root / "request"
    pid_directory = launcher_root / "pid"
    started_directory = launcher_root / "started"
    failed_directory = launcher_root / "failed"
    stdout_path = launcher_root / "launcher.stdout.log"
    stderr_path = launcher_root / "launcher.stderr.log"
    command = _startup_calibration_launcher_command(
        config_path=config_path, launcher_directory=launcher_root
    )
    request_payload = {
        "schema": "rts_gmlc_v4_repair_010_startup_calibration_launcher_request_v2",
        "requested_utc": datetime.now(timezone.utc).isoformat(),
        "config_path": str(config_path.resolve()),
        "config_sha256": _sha256(config_path),
        "runner_sha256": _sha256(Path(__file__)),
        "calibration_contract_sha256": canonical_sha256(contract),
        "command": list(command),
        "output_root": str(output_root.resolve()),
        "log_root": str(log_root.resolve()),
        "solver_callable_invocations_allowed": 0,
        "formal_execution_authorized": False,
        "retry_or_resume_allowed": False,
    }
    _publish_launcher_artifact(
        request_directory,
        filename="launcher_request.json",
        payload=request_payload,
    )
    request_manifest = _sha256(request_directory / "SHA256SUMS")

    def publish_pid(pid: int) -> None:
        _publish_launcher_artifact(
            pid_directory,
            filename="launcher_pid.json",
            payload={
                "schema": "rts_gmlc_v4_repair_010_startup_calibration_launcher_pid_v2",
                "request_manifest_sha256": request_manifest,
                "pid": pid,
            },
        )

    def publish_started(pid: int) -> None:
        _publish_launcher_artifact(
            started_directory,
            filename="launcher_started.json",
            payload={
                "schema": (
                    "rts_gmlc_v4_repair_010_startup_calibration_launcher_started_v2"
                ),
                "request_manifest_sha256": request_manifest,
                "pid_manifest_sha256": _sha256(pid_directory / "SHA256SUMS"),
                "pid": pid,
            },
        )

    def publish_failed(pid: int, return_code: int, reason: str) -> None:
        _publish_launcher_artifact(
            failed_directory,
            filename="launcher_failed.json",
            payload={
                "schema": (
                    "rts_gmlc_v4_repair_010_startup_calibration_launcher_failed_v2"
                ),
                "request_manifest_sha256": request_manifest,
                "pid_manifest_observed_sha256": (
                    _sha256(pid_directory / "SHA256SUMS")
                    if (pid_directory / "SHA256SUMS").is_file()
                    else None
                ),
                "pid": pid,
                "return_code": return_code,
                "reason": reason,
                "child_exit_confirmed": True,
                "retry_or_resume_allowed": False,
            },
        )

    creationflags = 0
    if os.name == "nt":
        creationflags = (
            subprocess.CREATE_NEW_PROCESS_GROUP
            | subprocess.CREATE_NO_WINDOW
            | subprocess.DETACHED_PROCESS
        )
    pid = run_startup_calibration_launcher_process(
        command=command,
        stdout_path=stdout_path,
        stderr_path=stderr_path,
        termination_grace_seconds=float(contract["termination_grace_seconds"]),
        on_pid=publish_pid,
        on_started=publish_started,
        on_failed=publish_failed,
        creationflags=creationflags,
    )
    return {
        "schema": "rts_gmlc_v4_repair_010_startup_calibration_launched_v2",
        "pid": pid,
        "request_manifest_sha256": request_manifest,
        "pid_manifest_sha256": _sha256(pid_directory / "SHA256SUMS"),
        "started_manifest_sha256": _sha256(started_directory / "SHA256SUMS"),
        "stdout_path": str(stdout_path.resolve()),
        "stderr_path": str(stderr_path.resolve()),
    }


def _build_context(config_path: Path) -> v4._FrontierContext:
    """Build the successor by reusing repair-009's frozen scientific model path."""

    successor = _read_config(config_path)
    predecessor_path = Path(successor["predecessor_ifocus4"]["config_path"])
    base = repair009._build_context(predecessor_path)
    return _build_context_from_predecessor(config_path, successor, base)


def _build_context_from_predecessor(
    config_path: Path,
    successor: Mapping[str, Any],
    base: v4._FrontierContext,
) -> v4._FrontierContext:
    effective = copy.deepcopy(base.config)
    effective["preregistration"] = dict(successor["preregistration"])
    effective["output"] = dict(successor["output"])
    effective["formal_solver"]["progress_logging"]["log_directory"] = successor[
        "logging"
    ]["directory"]
    runtime = effective["joint_ac"]["runtime_control"]
    joint = successor["joint_ac_successor"]
    runtime.update(
        {
            "log_directory": successor["logging"]["directory"],
            "max_wall_time_seconds_per_call": float(
                joint["solver_wall_limit_seconds_per_call"]
            ),
            "max_cpu_time_seconds_per_call": float(
                joint["ipopt_max_cpu_time_seconds_per_call"]
            ),
            "heartbeat_interval_seconds": float(
                joint["startup_heartbeat_interval_seconds"]
            ),
            "parent_watchdog_interval_seconds": float(
                joint["parent_watchdog_interval_seconds"]
            ),
            "termination_grace_seconds": float(joint["termination_grace_seconds"]),
        }
    )
    formal_successor = copy.deepcopy(base.input_contract["formal_successor"])
    formal_successor.update(successor["formal_successor"])
    contract = copy.deepcopy(base.input_contract)
    contract.update(
        {
            "schema": "rts_gmlc_v4_repair_010_formal_inputs_v1",
            "repair_009_parent_input_contract": base.input_contract,
            "repair_009_parent_input_contract_sha256": base.input_contract_sha256,
            "successor_config_sha256": _sha256(config_path),
            "predecessor_ifocus4": successor["predecessor_ifocus4"],
            "formal_successor": formal_successor,
            "frontier_import": successor["frontier_import"],
            "startup_calibration": successor["startup_calibration"],
            "joint_ac_successor": successor["joint_ac_successor"],
            "repair_010_implementation": {
                "runner_sha256": _sha256(Path(__file__)),
                "shared_adapter_authority_sha256": _sha256(SHARED_V4_ADAPTER_PATH),
                "repair_010_adapter_sha256": _sha256(REPAIR_010_ADAPTER_PATH),
                "phase_contract_sha256": _sha256(
                    Path("src/solvers/joint_ac_phase_contract.py")
                ),
            },
        }
    )
    return replace(
        base,
        config_path=config_path,
        config=effective,
        output_root=Path(successor["output"]["directory"]),
        input_contract=contract,
        input_contract_sha256=common_input_signature_sha256(contract),
    )


def _registration_payload(context: v4._FrontierContext) -> dict[str, Any]:
    preregistration = context.config["preregistration"]
    return {
        "schema": preregistration["schema"],
        "preregistration_id": preregistration["id"],
        "status": preregistration["status"],
        "externally_timestamped": False,
        "previous_ac_outcomes_observed": True,
        "candidate_frontier_outcomes_observed": True,
        "joint_ac_outcomes_observed": False,
        "warm_start_selection_frozen": True,
        "selected_candidate_method": context.config["formal_solver"]["algorithm"],
        "input_contract": context.input_contract,
        "input_contract_sha256": context.input_contract_sha256,
    }


def prepare_preregistration(
    config_path: Path = DEFAULT_CONFIG_PATH, *, output_directory: Path | None = None
) -> dict[str, Any]:
    config = _read_config(config_path)
    _assert_successor_ready(config)
    context = _build_context(config_path)
    output_root = output_directory or context.output_root
    target = output_root / "preregistration"
    expected = _registration_payload(context)
    if target.exists():
        _verify_manifest(target)
        observed = v4._load_json(target, "registration.json")
        if (
            v4._exact_json_text(observed) != v4._exact_json_text(expected)
            or (target / "config.yaml").read_bytes() != config_path.read_bytes()
        ):
            raise RuntimeError("repair-010 published preregistration drifted")
        return observed
    if output_root.exists() and any(output_root.iterdir()):
        raise RuntimeError("Cannot prepare repair-010 beside existing artifacts")

    def writer(staging: Path) -> None:
        (staging / "config.yaml").write_bytes(config_path.read_bytes())
        v4._write_exact_json(staging / "registration.json", expected)

    v4._publish_immutable_payload(target, writer)
    return v4._load_json(target, "registration.json")


def _require_preregistration(
    context: v4._FrontierContext, output_root: Path
) -> dict[str, Any]:
    target = output_root / "preregistration"
    _verify_manifest(target)
    observed = v4._load_json(target, "registration.json")
    if (
        v4._exact_json_text(observed)
        != v4._exact_json_text(_registration_payload(context))
        or (target / "config.yaml").read_bytes() != context.config_path.read_bytes()
        or common_input_signature_sha256(observed["input_contract"])
        != context.input_contract_sha256
    ):
        raise RuntimeError("repair-010 preregistration contract drifted")
    return observed


def _predecessor_authority_context(
    context: v4._FrontierContext,
) -> v4._FrontierContext:
    parent_contract = context.input_contract["repair_009_parent_input_contract"]
    parent_contract_sha256 = context.input_contract[
        "repair_009_parent_input_contract_sha256"
    ]
    authority_config = copy.deepcopy(context.config)
    authority_config["preregistration"]["id"] = context.input_contract[
        "frontier_import"
    ]["source_preregistration_id"]
    return replace(
        context,
        input_contract=parent_contract,
        input_contract_sha256=parent_contract_sha256,
        config=authority_config,
    )


def _frontier_import_record(
    context: v4._FrontierContext, audit: FrontierSourceAudit
) -> dict[str, object]:
    contract = context.input_contract["frontier_import"]
    return {
        "schema": contract["schema"],
        "mode": contract["mode"],
        "source_root": context.input_contract["predecessor_ifocus4"]["root"],
        "source_preregistration_id": contract["source_preregistration_id"],
        "source_preregistration_manifest_sha256": (
            audit.source_preregistration_manifest_sha256
        ),
        "source_frontier_manifest_sha256": audit.source_frontier_manifest_sha256,
        "source_preregistration_input_contract_sha256": (
            audit.source_preregistration_input_contract_sha256
        ),
        "source_frontier_input_contract_sha256": (
            audit.source_frontier_input_contract_sha256
        ),
        "source_candidate_ids": list(audit.candidate_ids),
        "source_budget_checkpoint_manifest_sha256s": dict(
            audit.budget_checkpoint_manifest_sha256s
        ),
        "source_nested_round_manifest_count": audit.nested_round_manifest_count,
        "source_outcomes_observed": True,
        "destination_preregistration_id": context.config["preregistration"]["id"],
        "destination_input_contract_sha256": context.input_contract_sha256,
        "scientific_values_unchanged": True,
        "direct_source_use_as_solver_input_allowed": False,
        "copied_payload_is_successor_local": True,
        "hard_links_used": False,
        "solver_call_count": 0,
        "authority_loader": contract["authority_loader"],
    }


def _validate_frontier_import_payload(
    context: v4._FrontierContext,
    import_root: Path,
    *,
    authority_loader: Callable[[Path], tuple[Sequence[object], str]] | None = None,
) -> tuple[list[v4._LoadedCandidate], str, FrontierSourceAudit]:
    v4._verify_output_manifest(import_root)
    if authority_loader is None:
        authority_context = _predecessor_authority_context(context)

        def authority_loader(root: Path) -> tuple[Sequence[object], str]:
            return repair009._load_candidate_frontier(authority_context, root)

    audit = audit_predecessor_frontier_source(
        source_root=import_root,
        predecessor_contract=context.input_contract["predecessor_ifocus4"],
        import_contract=context.input_contract["frontier_import"],
        authority_loader=authority_loader,
    )
    observed = v4._load_json(import_root, "import.json")
    expected = _frontier_import_record(context, audit)
    if v4._exact_json_text(observed) != v4._exact_json_text(
        v4._exact_json_payload(expected)
    ):
        raise RuntimeError("repair-010 successor-local frontier import drifted")
    candidates, frontier_manifest = authority_loader(import_root)
    return list(candidates), frontier_manifest, audit


def _publish_nested_immutable_payload(
    target: Path,
    writer: Callable[[Path], None],
    validator: Callable[[Path], None],
) -> None:
    """Atomically publish a tree whose child manifests are themselves evidence."""

    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists():
        raise FileExistsError(f"Immutable artifact already exists: {target}")
    staging = Path(
        tempfile.mkdtemp(dir=target.parent, prefix=f".{target.name}.processing-")
    )
    try:
        writer(staging)
        repair009._write_nested_manifest(staging)
        _verify_manifest(staging)
        validator(staging)
        if target.exists():
            raise FileExistsError(f"Immutable artifact already exists: {target}")
        staging.rename(target)
        _verify_manifest(target)
    finally:
        if staging.exists():
            shutil.rmtree(staging)


def publish_audited_frontier_import(
    *,
    context: v4._FrontierContext,
    output_root: Path,
    source_root: Path,
    predecessor_authority_context: v4._FrontierContext | None,
    authority_loader: Callable[[Path], tuple[Sequence[object], str]] | None = None,
) -> dict[str, object]:
    """Copy a fully validated predecessor frontier without running a solver."""

    _require_preregistration(context, output_root)
    contract = context.input_contract["frontier_import"]
    configured_source = Path(context.input_contract["predecessor_ifocus4"]["root"])
    if source_root.resolve() != configured_source.resolve():
        raise RuntimeError("repair-010 predecessor frontier source path drifted")

    if authority_loader is None:
        if predecessor_authority_context is None:
            raise ValueError("repair-010 predecessor authority context is required")

        def authority_loader(root: Path) -> tuple[Sequence[object], str]:
            return repair009._load_candidate_frontier(
                predecessor_authority_context, root
            )

    audit = audit_predecessor_frontier_source(
        source_root=source_root,
        predecessor_contract=context.input_contract["predecessor_ifocus4"],
        import_contract=contract,
        authority_loader=authority_loader,
    )
    target = output_root / str(contract["destination_relative_directory"])
    if target.exists():
        _validate_frontier_import_payload(
            context, target, authority_loader=authority_loader
        )
        return v4._load_json(target, "import.json")
    if any(
        (output_root / name).exists()
        for name in (
            "candidate_frontier",
            "candidate_checkpoints",
            "joint_call_registry",
            "joint_call_checkpoints",
            "joint_phase_registry",
            "joint_phase_spawn_registry",
            "joint_phase_completion_registry",
            "joint_phase_finalization_intent_registry",
            "joint_phase_terminal_incomplete_registry",
            "joint_phase_finalization_success_registry",
            "joint_ac",
        )
    ):
        raise RuntimeError("repair-010 frontier import target state drifted")

    expected_record = _frontier_import_record(context, audit)

    def writer(staging: Path) -> None:
        for name in ("preregistration", "candidate_frontier", "candidate_checkpoints"):
            shutil.copytree(
                source_root / name, staging / name, copy_function=shutil.copy2
            )
        v4._write_exact_json(staging / "import.json", expected_record)

    def validate(staging: Path) -> None:
        copied_candidates, copied_manifest, copied_audit = (
            _validate_frontier_import_payload(
                context, staging, authority_loader=authority_loader
            )
        )
        source_audit_after_copy = audit_predecessor_frontier_source(
            source_root=source_root,
            predecessor_contract=context.input_contract["predecessor_ifocus4"],
            import_contract=contract,
            authority_loader=authority_loader,
        )
        if (
            copied_audit != audit
            or source_audit_after_copy != audit
            or copied_manifest != audit.source_frontier_manifest_sha256
            or tuple(item.candidate_id for item in copied_candidates)
            != audit.candidate_ids
        ):
            raise RuntimeError("repair-010 frontier changed during audited copy")

    _publish_nested_immutable_payload(target, writer, validate)
    _validate_frontier_import_payload(
        context, target, authority_loader=authority_loader
    )
    return v4._load_json(target, "import.json")


def import_predecessor_frontier(
    config_path: Path = DEFAULT_CONFIG_PATH,
    *,
    output_directory: Path | None = None,
) -> dict[str, object]:
    config = _read_config(config_path)
    _assert_successor_ready(config)
    predecessor_context = repair009._build_context(
        Path(config["predecessor_ifocus4"]["config_path"])
    )
    context = _build_context_from_predecessor(config_path, config, predecessor_context)
    output_root = output_directory or context.output_root
    return publish_audited_frontier_import(
        context=context,
        output_root=output_root,
        source_root=Path(config["predecessor_ifocus4"]["root"]),
        predecessor_authority_context=predecessor_context,
    )


def _load_successor_frontier_import(
    context: v4._FrontierContext, output_root: Path
) -> tuple[list[v4._LoadedCandidate], str]:
    import_root = output_root / str(
        context.input_contract["frontier_import"]["destination_relative_directory"]
    )
    if not import_root.is_dir():
        raise RuntimeError("repair-010 successor-local frontier import is missing")
    candidates, frontier_manifest, _audit = _validate_frontier_import_payload(
        context, import_root
    )
    return candidates, frontier_manifest


def _software_identity() -> dict[str, object]:
    executable = Path(sys.executable)
    casadi_root = Path(ca.__file__).resolve().parent
    binary_names = (
        "_casadi.pyd",
        "libcasadi.dll",
        "libcasadi_nlpsol_ipopt.dll",
        "libipopt-3.dll",
        "libsipopt-3.dll",
    )
    binary_hashes = {
        name: _sha256(casadi_root / name)
        for name in binary_names
        if (casadi_root / name).is_file()
    }
    plugins = ca.CasadiMeta_plugins()
    if (
        "Nlpsol::ipopt" not in plugins
        or "libcasadi_nlpsol_ipopt.dll" not in binary_hashes
    ):
        raise RuntimeError("repair-010 CasADi IPOPT plugin identity is unavailable")
    return {
        "python_version": sys.version,
        "python_executable_sha256": _sha256(executable),
        "casadi_version": metadata.version("casadi"),
        "casadi_build_type": ca.CasadiMeta_build_type(),
        "casadi_compiler": ca.CasadiMeta_compiler(),
        "casadi_compiler_flags": ca.CasadiMeta_compiler_flags(),
        "casadi_git_describe": ca.CasadiMeta_git_describe(),
        "casadi_plugins": plugins.split(";"),
        "casadi_plugins_sha256": canonical_sha256(plugins.split(";")),
        "casadi_and_ipopt_binary_sha256": binary_hashes,
        "ipopt_plugin_identity": "CasADi Nlpsol::ipopt",
        "ipopt_identity_boundary": (
            "CasADi-bundled plugin and shared-library hashes are bound; no separate "
            "IPOPT executable/build manifest is exposed by this wheel"
        ),
        "numpy_version": metadata.version("numpy"),
        "shared_adapter_authority_sha256": _sha256(SHARED_V4_ADAPTER_PATH),
        "repair_010_adapter_sha256": _sha256(REPAIR_010_ADAPTER_PATH),
        "core_sha256": _sha256(Path("src/grid/rts_gmlc_ac_aware_commitment.py")),
        "phase_contract_sha256": _sha256(
            Path("src/solvers/joint_ac_phase_contract.py")
        ),
    }


def build_worker_binding(
    *,
    preregistration_id: str,
    input_contract_sha256: str,
    frontier_manifest_sha256: str,
    call_manifest_sha256: str,
    candidate_id: str,
    commitment_sha256: str,
    dispatch_sha256: str,
    initial_strategy: str,
    prepared_inputs_sha256: str,
    ipopt_options_sha256: str,
    software_identity: Mapping[str, object] | None = None,
) -> dict[str, object]:
    hashes = (
        input_contract_sha256,
        frontier_manifest_sha256,
        call_manifest_sha256,
        commitment_sha256,
        dispatch_sha256,
        prepared_inputs_sha256,
        ipopt_options_sha256,
    )
    if any(re.fullmatch(r"[0-9a-f]{64}", value) is None for value in hashes):
        raise ValueError("repair-010 worker binding hash drifted")
    return {
        "schema": "rts_gmlc_joint_ac_worker_binding_v1",
        "preregistration_id": preregistration_id,
        "input_contract_sha256": input_contract_sha256,
        "frontier_manifest_sha256": frontier_manifest_sha256,
        "call_manifest_sha256": call_manifest_sha256,
        "candidate_id": candidate_id,
        "commitment_sha256": commitment_sha256,
        "dispatch_sha256": dispatch_sha256,
        "initial_strategy": initial_strategy,
        "prepared_inputs_sha256": prepared_inputs_sha256,
        "ipopt_options_sha256": ipopt_options_sha256,
        "software_identity": dict(software_identity or _software_identity()),
    }


def register_phase_worker_call(
    registration_directory: Path,
    *,
    binding: Mapping[str, object],
    phase_journal: Path,
    worker_result: Path,
    native_solver_log: Path,
    worker_process_log: Path,
    parent_pid: int,
) -> str:
    if (
        isinstance(parent_pid, bool)
        or not isinstance(parent_pid, int)
        or parent_pid <= 0
    ):
        raise ValueError("repair-010 phase registration parent PID drifted")
    payload = {
        "schema": "rts_gmlc_joint_ac_phase_registration_v1",
        "binding": dict(binding),
        "binding_sha256": canonical_sha256(dict(binding)),
        "phase_journal": str(phase_journal.resolve()),
        "worker_result": str(worker_result.resolve()),
        "native_solver_log": str(native_solver_log.resolve()),
        "worker_process_log": str(worker_process_log.resolve()),
        "parent_pid": parent_pid,
        "retry_allowed": False,
    }
    if registration_directory.exists():
        raise RuntimeError("repair-010 phase call was already registered")

    def writer(staging: Path) -> None:
        v4._write_exact_json(staging / "phase_call.json", payload)

    v4._publish_immutable_payload(registration_directory, writer)
    observed = v4._load_json(registration_directory, "phase_call.json")
    if v4._exact_json_text(observed) != v4._exact_json_text(
        v4._exact_json_payload(payload)
    ):
        raise RuntimeError("repair-010 phase registration drifted")
    return _sha256(registration_directory / "SHA256SUMS")


def _load_phase_registration(registration_directory: Path) -> dict[str, Any]:
    v4._verify_output_manifest(registration_directory)
    observed = v4._load_json(registration_directory, "phase_call.json")
    binding = observed.get("binding")
    if (
        observed.get("schema") != "rts_gmlc_joint_ac_phase_registration_v1"
        or not isinstance(binding, dict)
        or observed.get("binding_sha256") != canonical_sha256(binding)
        or isinstance(observed.get("parent_pid"), bool)
        or not isinstance(observed.get("parent_pid"), int)
        or observed["parent_pid"] <= 0
        or observed.get("retry_allowed") is not False
    ):
        raise RuntimeError("repair-010 phase registration drifted")
    return observed


def register_phase_worker_spawn(
    spawn_directory: Path,
    *,
    phase_registration_directory: Path,
    binding: Mapping[str, object],
    worker_pid: int,
) -> str:
    """Persist the actual parent-spawned PID before phase polling begins."""

    if (
        isinstance(worker_pid, bool)
        or not isinstance(worker_pid, int)
        or worker_pid <= 0
    ):
        raise ValueError("repair-010 phase spawn worker PID drifted")
    registration = _load_phase_registration(phase_registration_directory)
    registration_manifest = _sha256(phase_registration_directory / "SHA256SUMS")
    if registration.get("binding") != dict(binding):
        raise PhaseContractError("repair-010 phase spawn binding drifted")
    payload = {
        "schema": "rts_gmlc_joint_ac_phase_spawn_v1",
        "binding": dict(binding),
        "binding_sha256": canonical_sha256(dict(binding)),
        "phase_registration_manifest_sha256": registration_manifest,
        "worker_pid": worker_pid,
    }

    def writer(staging: Path) -> None:
        v4._write_exact_json(staging / "phase_spawn.json", payload)

    v4._publish_immutable_payload(spawn_directory, writer)
    return _sha256(spawn_directory / "SHA256SUMS")


def load_verified_phase_worker_spawn(
    *,
    phase_registration_directory: Path,
    phase_spawn_directory: Path,
    expected_binding: Mapping[str, object],
) -> dict[str, Any]:
    registration = _load_phase_registration(phase_registration_directory)
    registration_manifest = _sha256(phase_registration_directory / "SHA256SUMS")
    if registration.get("binding") != dict(expected_binding):
        raise PhaseContractError("repair-010 recovery phase registration drifted")
    if not phase_spawn_directory.is_dir():
        raise PhaseContractError("repair-010 recovery phase spawn receipt is missing")
    v4._verify_output_manifest(phase_spawn_directory)
    observed = v4._load_json(phase_spawn_directory, "phase_spawn.json")
    worker_pid = observed.get("worker_pid")
    if (
        observed.get("schema") != "rts_gmlc_joint_ac_phase_spawn_v1"
        or observed.get("binding") != dict(expected_binding)
        or observed.get("binding_sha256") != canonical_sha256(dict(expected_binding))
        or observed.get("phase_registration_manifest_sha256") != registration_manifest
        or isinstance(worker_pid, bool)
        or not isinstance(worker_pid, int)
        or worker_pid <= 0
    ):
        raise PhaseContractError("repair-010 recovery phase spawn receipt drifted")
    return observed


def register_phase_completion(
    completion_directory: Path,
    *,
    binding: Mapping[str, object],
    phase_registration_manifest_sha256: str,
    phase_journal: Path,
    worker_pid: int,
    worker_result: Path,
    worker_result_manifest_sha256: str,
    native_solver_log: Path,
) -> str:
    if (
        isinstance(worker_pid, bool)
        or not isinstance(worker_pid, int)
        or worker_pid <= 0
    ):
        raise ValueError("repair-010 phase completion worker PID drifted")
    records = load_verified_phase_events(
        phase_journal,
        expected_binding=binding,
        expected_worker_pid=worker_pid,
    )
    if (
        tuple(
            record["event"] for record in records if record["event"] in REQUIRED_PHASES
        )
        != REQUIRED_PHASES
    ):
        raise PhaseContractError("repair-010 phase completion journal is incomplete")
    if (
        re.fullmatch(r"[0-9a-f]{64}", phase_registration_manifest_sha256) is None
        or re.fullmatch(r"[0-9a-f]{64}", worker_result_manifest_sha256) is None
        or not worker_result.is_dir()
        or _sha256(worker_result / "SHA256SUMS") != worker_result_manifest_sha256
        or not native_solver_log.is_file()
    ):
        raise PhaseContractError("repair-010 phase completion artifact drifted")
    payload = {
        "schema": "rts_gmlc_joint_ac_phase_completion_v1",
        "binding": dict(binding),
        "binding_sha256": canonical_sha256(dict(binding)),
        "phase_registration_manifest_sha256": (phase_registration_manifest_sha256),
        "phase_journal": str(phase_journal.resolve()),
        "phase_journal_sha256": _sha256(phase_journal),
        "worker_pid": worker_pid,
        "worker_result": str(worker_result.resolve()),
        "worker_result_manifest_sha256": worker_result_manifest_sha256,
        "native_solver_log": str(native_solver_log.resolve()),
        "native_solver_log_sha256": _sha256(native_solver_log),
        "solver_call_count": 1,
        "solver_finished_verified": True,
        "is_infeasibility_evidence": False,
        "retry_or_resume_used": False,
    }
    if completion_directory.exists():
        raise RuntimeError("repair-010 phase completion was already registered")

    def writer(staging: Path) -> None:
        v4._write_exact_json(staging / "phase_completion.json", payload)

    v4._publish_immutable_payload(completion_directory, writer)
    return _sha256(completion_directory / "SHA256SUMS")


def load_verified_phase_completion(
    *,
    phase_registration_directory: Path,
    phase_completion_directory: Path,
    expected_binding: Mapping[str, object],
    expected_phase_journal: Path,
    expected_worker_result: Path,
    expected_native_solver_log: Path,
) -> dict[str, Any]:
    registration = _load_phase_registration(phase_registration_directory)
    phase_registration_manifest = _sha256(phase_registration_directory / "SHA256SUMS")
    if (
        registration.get("binding") != dict(expected_binding)
        or registration.get("phase_journal") != str(expected_phase_journal.resolve())
        or registration.get("worker_result") != str(expected_worker_result.resolve())
        or registration.get("native_solver_log")
        != str(expected_native_solver_log.resolve())
    ):
        raise PhaseContractError("repair-010 recovery phase registration drifted")
    if not phase_completion_directory.is_dir():
        raise PhaseContractError(
            "repair-010 recovery phase completion is missing; retry/resume forbidden"
        )
    v4._verify_output_manifest(phase_completion_directory)
    completion = v4._load_json(phase_completion_directory, "phase_completion.json")
    worker_pid = completion.get("worker_pid")
    if (
        completion.get("schema") != "rts_gmlc_joint_ac_phase_completion_v1"
        or completion.get("binding") != dict(expected_binding)
        or completion.get("binding_sha256") != canonical_sha256(dict(expected_binding))
        or completion.get("phase_registration_manifest_sha256")
        != phase_registration_manifest
        or completion.get("phase_journal") != str(expected_phase_journal.resolve())
        or completion.get("worker_result") != str(expected_worker_result.resolve())
        or completion.get("native_solver_log")
        != str(expected_native_solver_log.resolve())
        or isinstance(worker_pid, bool)
        or not isinstance(worker_pid, int)
        or worker_pid <= 0
        or completion.get("solver_call_count") != 1
        or completion.get("solver_finished_verified") is not True
        or completion.get("is_infeasibility_evidence") is not False
        or completion.get("retry_or_resume_used") is not False
    ):
        raise PhaseContractError("repair-010 recovery phase completion drifted")
    if (
        not expected_phase_journal.is_file()
        or completion.get("phase_journal_sha256") != _sha256(expected_phase_journal)
        or not expected_worker_result.is_dir()
        or completion.get("worker_result_manifest_sha256")
        != _sha256(expected_worker_result / "SHA256SUMS")
        or not expected_native_solver_log.is_file()
        or completion.get("native_solver_log_sha256")
        != _sha256(expected_native_solver_log)
    ):
        raise PhaseContractError("repair-010 recovery artifact hash drifted")
    records = load_verified_phase_events(
        expected_phase_journal,
        expected_binding=expected_binding,
        expected_worker_pid=worker_pid,
    )
    required_events = tuple(
        record["event"] for record in records if record["event"] in REQUIRED_PHASES
    )
    if required_events != REQUIRED_PHASES:
        raise PhaseContractError("repair-010 recovery phase journal is incomplete")
    return completion


def register_phase_finalization_intent(
    intent_directory: Path,
    *,
    phase_registration_directory: Path,
    phase_spawn_directory: Path,
    binding: Mapping[str, object],
    phase_journal: Path,
) -> str:
    """Freeze trusted solver completion before any parent publication."""

    registration = _load_phase_registration(phase_registration_directory)
    spawn = load_verified_phase_worker_spawn(
        phase_registration_directory=phase_registration_directory,
        phase_spawn_directory=phase_spawn_directory,
        expected_binding=binding,
    )
    worker_pid = int(spawn["worker_pid"])
    records = load_verified_phase_events(
        phase_journal,
        expected_binding=binding,
        expected_worker_pid=worker_pid,
    )
    required = tuple(
        record["event"] for record in records if record["event"] in REQUIRED_PHASES
    )
    if (
        registration.get("binding") != dict(binding)
        or registration.get("phase_journal") != str(phase_journal.resolve())
        or required != REQUIRED_PHASES
    ):
        raise PhaseContractError(
            "repair-010 finalization intent phase evidence drifted"
        )
    payload = {
        "schema": "rts_gmlc_joint_ac_phase_finalization_intent_v1",
        "binding": dict(binding),
        "binding_sha256": canonical_sha256(dict(binding)),
        "phase_registration": str(phase_registration_directory.resolve()),
        "phase_registration_manifest_sha256": _sha256(
            phase_registration_directory / "SHA256SUMS"
        ),
        "phase_spawn": str(phase_spawn_directory.resolve()),
        "phase_spawn_manifest_sha256": _sha256(phase_spawn_directory / "SHA256SUMS"),
        "phase_journal": str(phase_journal.resolve()),
        "phase_journal_sha256": _sha256(phase_journal),
        "worker_pid": worker_pid,
        "solver_call_count": 1,
        "solver_started_verified": True,
        "solver_finished_verified": True,
        "success_seal_required": True,
        "retry_or_resume_allowed": False,
    }
    if intent_directory.exists():
        raise RuntimeError("repair-010 phase finalization intent already exists")

    def writer(staging: Path) -> None:
        v4._write_exact_json(staging / "finalization_intent.json", payload)

    v4._publish_immutable_payload(intent_directory, writer)
    return _sha256(intent_directory / "SHA256SUMS")


def load_verified_phase_finalization_intent(
    *,
    finalization_intent_directory: Path,
    expected_binding: Mapping[str, object],
    expected_phase_registration: Path,
    expected_phase_spawn: Path,
    expected_phase_journal: Path,
) -> dict[str, Any]:
    if not finalization_intent_directory.is_dir():
        raise PhaseContractError(
            "repair-010 finalization intent is missing; recovery forbidden"
        )
    try:
        v4._verify_output_manifest(finalization_intent_directory)
        intent = v4._load_json(
            finalization_intent_directory, "finalization_intent.json"
        )
        spawn = load_verified_phase_worker_spawn(
            phase_registration_directory=expected_phase_registration,
            phase_spawn_directory=expected_phase_spawn,
            expected_binding=expected_binding,
        )
        worker_pid = intent.get("worker_pid")
        if (
            intent.get("schema") != "rts_gmlc_joint_ac_phase_finalization_intent_v1"
            or intent.get("binding") != dict(expected_binding)
            or intent.get("binding_sha256") != canonical_sha256(dict(expected_binding))
            or intent.get("phase_registration")
            != str(expected_phase_registration.resolve())
            or intent.get("phase_registration_manifest_sha256")
            != _sha256(expected_phase_registration / "SHA256SUMS")
            or intent.get("phase_spawn") != str(expected_phase_spawn.resolve())
            or intent.get("phase_spawn_manifest_sha256")
            != _sha256(expected_phase_spawn / "SHA256SUMS")
            or intent.get("phase_journal") != str(expected_phase_journal.resolve())
            or intent.get("phase_journal_sha256") != _sha256(expected_phase_journal)
            or isinstance(worker_pid, bool)
            or not isinstance(worker_pid, int)
            or worker_pid != spawn.get("worker_pid")
            or intent.get("solver_call_count") != 1
            or intent.get("solver_started_verified") is not True
            or intent.get("solver_finished_verified") is not True
            or intent.get("success_seal_required") is not True
            or intent.get("retry_or_resume_allowed") is not False
        ):
            raise PhaseContractError("repair-010 finalization intent drifted")
        records = load_verified_phase_events(
            expected_phase_journal,
            expected_binding=expected_binding,
            expected_worker_pid=worker_pid,
        )
        required = tuple(
            record["event"] for record in records if record["event"] in REQUIRED_PHASES
        )
        if required != REQUIRED_PHASES:
            raise PhaseContractError(
                "repair-010 finalization intent journal is incomplete"
            )
        return intent
    except PhaseContractError:
        raise
    except Exception as error:
        raise PhaseContractError(
            f"repair-010 finalization intent validation failed: {error}"
        ) from error


def register_phase_terminal_incomplete(
    terminal_directory: Path,
    *,
    phase_finalization_intent_directory: Path,
    phase_completion_directory: Path,
    binding: Mapping[str, object],
    reason: str,
) -> str:
    """Atomically make a verified solver call permanently unacceptable."""

    if not reason:
        raise ValueError("repair-010 terminal-incomplete reason is empty")
    v4._verify_output_manifest(phase_finalization_intent_directory)
    raw_intent = v4._load_json(
        phase_finalization_intent_directory, "finalization_intent.json"
    )
    intent = load_verified_phase_finalization_intent(
        finalization_intent_directory=phase_finalization_intent_directory,
        expected_binding=binding,
        expected_phase_registration=Path(str(raw_intent.get("phase_registration"))),
        expected_phase_spawn=Path(str(raw_intent.get("phase_spawn"))),
        expected_phase_journal=Path(str(raw_intent.get("phase_journal"))),
    )
    if (
        intent.get("binding") != dict(binding)
        or intent.get("solver_started_verified") is not True
        or intent.get("solver_call_count") != 1
    ):
        raise PhaseContractError("repair-010 terminal-incomplete intent drifted")
    completion_manifest_path = phase_completion_directory / "SHA256SUMS"
    payload = {
        "schema": "rts_gmlc_joint_ac_phase_terminal_incomplete_v1",
        "binding": dict(binding),
        "binding_sha256": canonical_sha256(dict(binding)),
        "phase_finalization_intent": str(phase_finalization_intent_directory.resolve()),
        "phase_finalization_intent_manifest_sha256": _sha256(
            phase_finalization_intent_directory / "SHA256SUMS"
        ),
        "phase_registration_manifest_sha256": intent[
            "phase_registration_manifest_sha256"
        ],
        "phase_spawn_manifest_sha256": intent["phase_spawn_manifest_sha256"],
        "phase_journal_sha256": intent["phase_journal_sha256"],
        "worker_pid": intent["worker_pid"],
        "phase_completion": str(phase_completion_directory.resolve()),
        "completion_manifest_observed_sha256": (
            _sha256(completion_manifest_path)
            if completion_manifest_path.is_file()
            else None
        ),
        "reason": reason,
        "solver_call_count": 1,
        "is_infeasibility_evidence": False,
        "resume_allowed": False,
    }
    if terminal_directory.exists():
        raise RuntimeError("repair-010 terminal-incomplete receipt already exists")

    def writer(staging: Path) -> None:
        v4._write_exact_json(staging / "terminal_incomplete.json", payload)

    v4._publish_immutable_payload(terminal_directory, writer)
    return _sha256(terminal_directory / "SHA256SUMS")


def load_verified_phase_terminal_incomplete(
    *,
    terminal_directory: Path,
    finalization_intent_directory: Path,
    expected_binding: Mapping[str, object],
    expected_phase_registration: Path,
    expected_phase_spawn: Path,
    expected_phase_journal: Path,
    expected_phase_completion: Path,
) -> dict[str, Any]:
    try:
        v4._verify_output_manifest(terminal_directory)
        terminal = v4._load_json(terminal_directory, "terminal_incomplete.json")
        intent = load_verified_phase_finalization_intent(
            finalization_intent_directory=finalization_intent_directory,
            expected_binding=expected_binding,
            expected_phase_registration=expected_phase_registration,
            expected_phase_spawn=expected_phase_spawn,
            expected_phase_journal=expected_phase_journal,
        )
        observed_completion_manifest = terminal.get(
            "completion_manifest_observed_sha256"
        )
        phase_completion = expected_phase_completion
        if (
            terminal.get("schema") != "rts_gmlc_joint_ac_phase_terminal_incomplete_v1"
            or terminal.get("binding") != dict(expected_binding)
            or terminal.get("binding_sha256")
            != canonical_sha256(dict(expected_binding))
            or terminal.get("phase_finalization_intent")
            != str(finalization_intent_directory.resolve())
            or terminal.get("phase_finalization_intent_manifest_sha256")
            != _sha256(finalization_intent_directory / "SHA256SUMS")
            or terminal.get("phase_registration_manifest_sha256")
            != intent.get("phase_registration_manifest_sha256")
            or terminal.get("phase_spawn_manifest_sha256")
            != intent.get("phase_spawn_manifest_sha256")
            or terminal.get("phase_journal_sha256")
            != intent.get("phase_journal_sha256")
            or terminal.get("worker_pid") != intent.get("worker_pid")
            or terminal.get("phase_completion")
            != str(expected_phase_completion.resolve())
            or (
                observed_completion_manifest is not None
                and (
                    not (phase_completion / "SHA256SUMS").is_file()
                    or _sha256(phase_completion / "SHA256SUMS")
                    != observed_completion_manifest
                )
            )
            or not isinstance(terminal.get("reason"), str)
            or not terminal["reason"]
            or terminal.get("solver_call_count") != 1
            or terminal.get("is_infeasibility_evidence") is not False
            or terminal.get("resume_allowed") is not False
        ):
            raise PhaseContractError("repair-010 terminal-incomplete receipt drifted")
        return terminal
    except PhaseContractError:
        raise
    except Exception as error:
        raise PhaseContractError(
            f"repair-010 terminal-incomplete validation failed: {error}"
        ) from error


def register_phase_finalization_success(
    success_directory: Path,
    *,
    phase_finalization_intent_directory: Path,
    phase_completion_directory: Path,
    checkpoint_directory: Path,
    terminal_directory: Path,
    binding: Mapping[str, object],
) -> None:
    """Seal success only after completion and checkpoint publication."""

    if terminal_directory.exists():
        raise PhaseContractError(
            "repair-010 terminal-incomplete receipt forbids success sealing"
        )
    v4._verify_output_manifest(phase_finalization_intent_directory)
    v4._verify_output_manifest(phase_completion_directory)
    v4._verify_output_manifest(checkpoint_directory)
    raw_intent = v4._load_json(
        phase_finalization_intent_directory, "finalization_intent.json"
    )
    phase_registration = Path(str(raw_intent.get("phase_registration")))
    phase_journal = Path(str(raw_intent.get("phase_journal")))
    load_verified_phase_finalization_intent(
        finalization_intent_directory=phase_finalization_intent_directory,
        expected_binding=binding,
        expected_phase_registration=phase_registration,
        expected_phase_spawn=Path(str(raw_intent.get("phase_spawn"))),
        expected_phase_journal=phase_journal,
    )
    registration = _load_phase_registration(phase_registration)
    load_verified_phase_completion(
        phase_registration_directory=phase_registration,
        phase_completion_directory=phase_completion_directory,
        expected_binding=binding,
        expected_phase_journal=phase_journal,
        expected_worker_result=Path(str(registration.get("worker_result"))),
        expected_native_solver_log=Path(str(registration.get("native_solver_log"))),
    )
    payload = {
        "schema": "rts_gmlc_joint_ac_phase_finalization_success_v1",
        "binding": dict(binding),
        "binding_sha256": canonical_sha256(dict(binding)),
        "phase_finalization_intent_manifest_sha256": _sha256(
            phase_finalization_intent_directory / "SHA256SUMS"
        ),
        "phase_completion_manifest_sha256": _sha256(
            phase_completion_directory / "SHA256SUMS"
        ),
        "checkpoint_manifest_sha256": _sha256(checkpoint_directory / "SHA256SUMS"),
        "solver_call_count": 1,
        "successfully_finalized": True,
        "retry_or_resume_used": False,
    }
    if success_directory.exists():
        raise RuntimeError("repair-010 finalization success seal already exists")

    def writer(staging: Path) -> None:
        v4._write_exact_json(staging / "finalization_success.json", payload)

    try:
        v4._publish_immutable_payload(success_directory, writer)
    except BaseException as publish_error:
        try:
            committed_state = success_directory.stat()
        except FileNotFoundError:
            raise publish_error
        except BaseException as state_error:
            raise SuccessSealCommitIndeterminateError(
                "repair-010 success seal target state is unreadable after "
                "publication failure; terminal classification is forbidden"
            ) from state_error
        if not stat.S_ISDIR(committed_state.st_mode):
            raise SuccessSealCommitIndeterminateError(
                "repair-010 success seal target exists but is not an immutable "
                "directory; terminal classification is forbidden"
            ) from publish_error
        try:
            v4._verify_output_manifest(success_directory)
            observed = v4._load_json(success_directory, "finalization_success.json")
            if v4._exact_json_text(observed) != v4._exact_json_text(
                v4._exact_json_payload(payload)
            ):
                raise PhaseContractError(
                    "repair-010 committed success seal payload drifted"
                )
        except BaseException as validation_error:
            raise SuccessSealCommitIndeterminateError(
                "repair-010 success seal target exists but its exact committed "
                "payload cannot be proven; terminal classification is forbidden"
            ) from validation_error


def load_verified_phase_finalization_success(
    *, evidence: PhaseRecoveryEvidence
) -> dict[str, Any]:
    if not evidence.phase_finalization_success.is_dir():
        raise PhaseContractError(
            "repair-010 finalization success seal is missing; recovery forbidden"
        )
    try:
        intent = load_verified_phase_finalization_intent(
            finalization_intent_directory=evidence.phase_finalization_intent,
            expected_binding=evidence.expected_binding,
            expected_phase_registration=evidence.phase_registration,
            expected_phase_spawn=evidence.phase_spawn,
            expected_phase_journal=evidence.phase_journal,
        )
        completion = load_verified_phase_completion(
            phase_registration_directory=evidence.phase_registration,
            phase_completion_directory=evidence.phase_completion,
            expected_binding=evidence.expected_binding,
            expected_phase_journal=evidence.phase_journal,
            expected_worker_result=evidence.worker_result,
            expected_native_solver_log=evidence.native_solver_log,
        )
        v4._verify_output_manifest(evidence.phase_finalization_success)
        v4._verify_output_manifest(evidence.checkpoint)
        success = v4._load_json(
            evidence.phase_finalization_success, "finalization_success.json"
        )
        if (
            success.get("schema") != "rts_gmlc_joint_ac_phase_finalization_success_v1"
            or success.get("binding") != dict(evidence.expected_binding)
            or success.get("binding_sha256")
            != canonical_sha256(dict(evidence.expected_binding))
            or success.get("phase_finalization_intent_manifest_sha256")
            != _sha256(evidence.phase_finalization_intent / "SHA256SUMS")
            or success.get("phase_completion_manifest_sha256")
            != _sha256(evidence.phase_completion / "SHA256SUMS")
            or success.get("checkpoint_manifest_sha256")
            != _sha256(evidence.checkpoint / "SHA256SUMS")
            or success.get("solver_call_count") != 1
            or success.get("successfully_finalized") is not True
            or success.get("retry_or_resume_used") is not False
            or intent.get("worker_pid") != completion.get("worker_pid")
        ):
            raise PhaseContractError("repair-010 finalization success seal drifted")
        return success
    except PhaseContractError:
        raise
    except Exception as error:
        raise PhaseContractError(
            f"repair-010 finalization success validation failed: {error}"
        ) from error


def _stop_worker(process: subprocess.Popen[bytes], grace_seconds: float) -> None:
    if process.poll() is not None:
        return
    process.terminate()
    try:
        process.wait(timeout=grace_seconds)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait(timeout=grace_seconds)


def run_isolated_worker_process(
    *,
    command: Sequence[str],
    phase_journal: Path,
    expected_binding: Mapping[str, object],
    worker_process_log: Path,
    result_validator: Callable[[], object],
    startup_limit_seconds: float,
    solver_wall_limit_seconds: float,
    termination_grace_seconds: float,
    poll_interval_seconds: float = 0.05,
    on_spawn: Callable[[int], None] | None = None,
    on_incomplete: Callable[[HonestIncomplete], None] | None = None,
) -> IsolatedWorkerCompletion:
    """Run one fresh child and time solver wall only after a verified event."""

    if phase_journal.exists() or worker_process_log.exists():
        raise FileExistsError("repair-010 worker journal/log already exists")
    worker_process_log.parent.mkdir(parents=True, exist_ok=True)
    phase_journal.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    controller = PhaseTimingController(
        startup_started_monotonic=started,
        startup_limit_seconds=startup_limit_seconds,
        solver_wall_limit_seconds=solver_wall_limit_seconds,
    )
    last_solver_started = False
    with worker_process_log.open("xb") as output:
        process = subprocess.Popen(
            list(command),
            cwd=Path(__file__).resolve().parents[1],
            stdout=output,
            stderr=subprocess.STDOUT,
        )
        try:
            if on_spawn is not None:
                on_spawn(process.pid)
            while True:
                observed = time.monotonic()
                try:
                    state = controller.observe(
                        phase_journal,
                        expected_binding=expected_binding,
                        expected_worker_pid=process.pid,
                        observed_monotonic=observed,
                    )
                except PhaseContractError as error:
                    outcome = classify_phase_contract_failure(
                        solver_started_was_verified=last_solver_started,
                        reason=f"phase_contract_failure:{error}",
                    )
                    raise IsolatedWorkerIncompleteError(outcome) from error
                last_solver_started = state.solver_started_verified
                timeout = controller.timeout(observed_monotonic=observed)
                if timeout is not None:
                    raise IsolatedWorkerIncompleteError(timeout)
                return_code = process.poll()
                if return_code is not None:
                    if return_code != 0:
                        raise IsolatedWorkerIncompleteError(
                            classify_phase_contract_failure(
                                solver_started_was_verified=last_solver_started,
                                reason=f"worker_exit_code:{return_code}",
                            )
                        )
                    if not state.solver_finished_verified:
                        raise IsolatedWorkerIncompleteError(
                            classify_phase_contract_failure(
                                solver_started_was_verified=last_solver_started,
                                reason="worker_exit_before_verified_solver_finished",
                            )
                        )
                    try:
                        result = result_validator()
                    except BaseException as error:
                        raise IsolatedWorkerIncompleteError(
                            classify_phase_contract_failure(
                                solver_started_was_verified=True,
                                reason=f"worker_result_validation_failure:{error}",
                            )
                        ) from error
                    return IsolatedWorkerCompletion(
                        worker_pid=process.pid,
                        solver_call_count=1,
                        result=result,
                    )
                time.sleep(poll_interval_seconds)
        except IsolatedWorkerIncompleteError as error:
            _stop_worker(process, termination_grace_seconds)
            if on_incomplete is not None:
                try:
                    on_incomplete(error.outcome)
                except BaseException as callback_error:
                    error.add_note(
                        "Failed to persist repair-010 honest-incomplete evidence: "
                        + (str(callback_error) or repr(callback_error))
                    )
            raise
        except BaseException:
            _stop_worker(process, termination_grace_seconds)
            raise


def execute_phase_instrumented_worker(
    *,
    journal: DurablePhaseJournal,
    context_loader: Callable[[], object],
    prepared_cases_loader: Callable[[object], tuple[Sequence[object], object]],
    base_options: Mapping[str, object],
    runtime_options: Mapping[str, object],
    initial_strategy: str,
    heartbeat_interval_seconds: float = 30.0,
    worker_operation: (
        Callable[
            [
                object,
                Sequence[object],
                object,
                Callable[[str, Mapping[str, object]], None],
            ],
            object,
        ]
        | None
    ) = None,
    post_worker_start_validator: Callable[[], None] | None = None,
) -> object:
    journal.emit("worker_started", {"fresh_process_required": True})
    startup_heartbeat = PhaseHeartbeat(
        journal,
        event="startup_heartbeat",
        interval_seconds=heartbeat_interval_seconds,
    )
    solver_heartbeat = PhaseHeartbeat(
        journal,
        event="solver_heartbeat",
        interval_seconds=heartbeat_interval_seconds,
    )
    startup_heartbeat.start()

    def observer(event: str, payload: Mapping[str, object]) -> None:
        if event == "solver_started":
            startup_heartbeat.stop()
            journal.emit(event, payload)
            solver_heartbeat.start()
            return
        if event == "solver_finished":
            solver_heartbeat.stop()
        journal.emit(event, payload)

    try:
        if post_worker_start_validator is not None:
            post_worker_start_validator()
        journal.emit("context_load_started", {"mode": "fresh_rebuild"})
        context = context_loader()
        journal.emit("context_load_completed", {})
        prepared_cases, chronology = prepared_cases_loader(context)
        prepared_hash = v4_adapter.prepared_inputs_sha256(prepared_cases, chronology)
        if prepared_hash != journal.binding.get("prepared_inputs_sha256"):
            raise PhaseContractError("worker prepared input binding drifted")
        journal.emit(
            "prepared_cases_completed",
            {
                "case_count": len(prepared_cases),
                "prepared_inputs_sha256": prepared_hash,
            },
        )
        if worker_operation is not None:
            return worker_operation(context, prepared_cases, chronology, observer)
        return v4_adapter.solve_ac_aware_commitment_v4_worker(
            prepared_cases,
            chronology,
            base_options=base_options,
            runtime_options=runtime_options,
            initial_strategy=initial_strategy,
            phase_observer=observer,
        )
    finally:
        startup_heartbeat.stop()
        solver_heartbeat.stop()


def _joint_worker_command(
    *,
    python_executable: Path,
    config_path: Path,
    output_root: Path,
    candidate_id: str,
    initial_strategy: str,
    worker_result: Path,
    native_log: Path,
    phase_journal: Path,
    phase_registration_directory: Path,
    call_manifest_sha256: str,
    phase_registration_manifest_sha256: str,
) -> list[str]:
    return [
        str(python_executable),
        "-B",
        "-m",
        _SUCCESSOR_MODULE,
        "--config",
        str(config_path.resolve()),
        "--stage",
        "joint-call-worker",
        "--output-directory",
        str(output_root.resolve()),
        "--candidate-id",
        candidate_id,
        "--initial-strategy",
        initial_strategy,
        "--worker-result-directory",
        str(worker_result.resolve()),
        "--native-solver-log",
        str(native_log.resolve()),
        "--phase-journal",
        str(phase_journal.resolve()),
        "--phase-registration-directory",
        str(phase_registration_directory.resolve()),
        "--call-registration-manifest-sha256",
        call_manifest_sha256,
        "--phase-registration-manifest-sha256",
        phase_registration_manifest_sha256,
    ]


def _startup_calibration_worker_command(
    *,
    python_executable: Path,
    config_path: Path,
    registration_directory: Path,
) -> list[str]:
    return [
        str(python_executable),
        "-B",
        "-m",
        _SUCCESSOR_MODULE,
        "--config",
        str(config_path.resolve()),
        "--stage",
        "startup-calibration-worker",
        "--calibration-registration-directory",
        str(registration_directory.resolve()),
    ]


def _load_startup_calibration_worker_result(
    result_directory: Path,
    *,
    binding: Mapping[str, object],
    worker_pid: int,
    phase_journal: Path,
) -> dict[str, Any]:
    v4._verify_output_manifest(result_directory)
    result = v4._load_json(result_directory, "calibration_worker_result.json")
    events = load_verified_calibration_events(
        phase_journal,
        expected_binding=binding,
        expected_worker_pid=worker_pid,
    )
    stop_payload = next(
        (
            record["payload"]
            for record in events
            if record["event"] == "calibration_pre_solver_stop"
        ),
        None,
    )
    if (
        stop_payload is None
        or result.get("schema")
        != "rts_gmlc_v4_repair_010_startup_calibration_worker_result_v1"
        or result.get("binding") != dict(binding)
        or result.get("binding_sha256") != canonical_sha256(dict(binding))
        or result.get("worker_pid") != worker_pid
        or result.get("prepared_inputs_sha256")
        != stop_payload.get("prepared_inputs_sha256")
        or result.get("expression_fingerprint_sha256")
        != stop_payload.get("expression_fingerprint_sha256")
        or result.get("solver_input_fingerprint_sha256")
        != stop_payload.get("solver_input_fingerprint_sha256")
        or result.get("actual_nlpsol_constructed") is not True
        or result.get("complete_solver_arguments_verified") is not True
        or result.get("solver_callable_invocation_count") != 0
        or result.get("solver_call_count") != 0
        or result.get("is_infeasibility_evidence") is not False
        or result.get("resume_allowed") is not False
        or re.fullmatch(
            r"[0-9a-f]{64}", str(result.get("context_input_contract_sha256", ""))
        )
        is None
    ):
        raise PhaseContractError("repair-010 calibration worker result drifted")
    return result


def run_startup_calibration_worker(
    config_path: Path,
    *,
    registration_directory: Path,
) -> dict[str, object]:
    config = _read_config(config_path)
    _assert_startup_calibration_only(config)
    v4._verify_output_manifest(registration_directory)
    raw_registration = v4._load_json(
        registration_directory, "calibration_registration.json"
    )
    raw_binding = raw_registration.get("binding")
    if not isinstance(raw_binding, dict):
        raise PhaseContractError("repair-010 calibration binding is missing")
    native_log = Path(str(raw_registration.get("native_solver_log")))
    source_audit = audit_configured_predecessor_frontier_source(config)
    candidate_record = _calibration_candidate_record(config)
    binding = build_startup_calibration_binding(
        config_path=config_path,
        config=config,
        source_audit=source_audit,
        candidate_record=candidate_record,
        native_log=native_log,
    )
    if raw_binding != binding:
        raise PhaseContractError("repair-010 calibration binding drifted in worker")
    registration = load_verified_startup_calibration_registration(
        registration_directory, expected_binding=binding
    )
    parent_pid = int(registration["parent_pid"])
    if parent_pid != os.getppid():
        raise RuntimeError("repair-010 calibration parent identity drifted")
    phase_journal = Path(str(registration["phase_journal"]))
    result_directory = Path(str(registration["worker_result"]))
    native_log.parent.mkdir(parents=True, exist_ok=True)
    journal = DurablePhaseJournal(phase_journal, binding=binding)
    heartbeat = PhaseHeartbeat(
        journal,
        event="startup_heartbeat",
        interval_seconds=float(
            config["joint_ac_successor"]["startup_heartbeat_interval_seconds"]
        ),
    )
    heartbeat.start()
    try:
        journal.emit("worker_started", {"fresh_process_required": True})
        journal.emit("context_load_started", {"mode": "fresh_rebuild"})
        with v4.ParentProcessWatchdog(
            parent_pid,
            interval_seconds=float(
                config["joint_ac_successor"]["parent_watchdog_interval_seconds"]
            ),
        ):
            context = _build_context(config_path)
            journal.emit(
                "context_load_completed",
                {"context_input_contract_sha256": context.input_contract_sha256},
            )
            authority = _predecessor_authority_context(context)
            candidates, frontier_manifest = repair009._load_candidate_frontier(
                authority, Path(config["predecessor_ifocus4"]["root"])
            )
            matches = [
                candidate
                for candidate in candidates
                if candidate.candidate_id == binding["candidate_id"]
            ]
            if len(matches) != 1:
                raise RuntimeError("repair-010 calibration candidate load drifted")
            candidate = matches[0]
            if (
                frontier_manifest != binding["source_frontier_manifest_sha256"]
                or candidate.commitment_sha256 != binding["commitment_sha256"]
                or candidate.dispatch_sha256 != binding["dispatch_sha256"]
            ):
                raise RuntimeError("repair-010 calibration candidate binding drifted")
            prepared_cases = v4._prepared_joint_cases(context, candidate)
            chronology = v4._joint_chronology(context, candidate)
            prepared_hash = v4_adapter.prepared_inputs_sha256(
                prepared_cases, chronology
            )
            journal.emit(
                "prepared_cases_completed",
                {
                    "case_count": len(prepared_cases),
                    "prepared_inputs_sha256": prepared_hash,
                },
            )

            def observer(event: str, payload: Mapping[str, object]) -> None:
                if event == "calibration_pre_solver_stop":
                    heartbeat.stop()
                journal.emit(event, payload)

            fingerprint = v4_adapter.calibrate_ac_aware_commitment_v4_startup(
                prepared_cases,
                chronology,
                base_options=shared_ipopt._FROZEN_IPOPT_OPTIONS,
                runtime_options=_calibration_runtime_options(config, native_log),
                initial_strategy=str(binding["initial_strategy"]),
                phase_observer=observer,
            )
            events = load_verified_calibration_events(
                phase_journal,
                expected_binding=binding,
                expected_worker_pid=os.getpid(),
            )
            phases = tuple(
                record["event"]
                for record in events
                if record["event"] in CALIBRATION_REQUIRED_PHASES
            )
            if phases != CALIBRATION_REQUIRED_PHASES:
                raise PhaseContractError(
                    "repair-010 calibration did not reach the pre-solver stop"
                )
            payload = {
                "schema": (
                    "rts_gmlc_v4_repair_010_startup_calibration_worker_result_v1"
                ),
                "binding": dict(binding),
                "binding_sha256": canonical_sha256(dict(binding)),
                "worker_pid": os.getpid(),
                "context_input_contract_sha256": context.input_contract_sha256,
                "prepared_inputs_sha256": prepared_hash,
                "expression_fingerprint_sha256": fingerprint[
                    "expression_fingerprint_sha256"
                ],
                "solver_input_fingerprint_sha256": fingerprint[
                    "solver_input_fingerprint_sha256"
                ],
                "actual_nlpsol_constructed": True,
                "complete_solver_arguments_verified": True,
                "solver_callable_invocation_count": 0,
                "solver_call_count": 0,
                "is_infeasibility_evidence": False,
                "resume_allowed": False,
            }
            _publish_exact_artifact(
                result_directory, "calibration_worker_result.json", payload
            )
            return payload
    finally:
        heartbeat.stop()


def _runtime_options(
    context: v4._FrontierContext, native_log: Path
) -> dict[str, object]:
    runtime = context.config["joint_ac"]["runtime_control"]
    return {
        "ipopt.max_cpu_time": float(runtime["max_cpu_time_seconds_per_call"]),
        "ipopt.output_file": str(native_log.resolve()),
        "ipopt.file_print_level": int(runtime["native_file_print_level"]),
    }


def _phase_recovery_evidence(
    context: v4._FrontierContext,
    output_root: Path,
    candidate: v4._LoadedCandidate,
    initial_strategy: str,
    frontier_manifest: str,
    prepared_cases: tuple[Any, ...],
    chronology: Any,
) -> PhaseRecoveryEvidence:
    call_manifest = v4._validate_joint_call_registration(
        context,
        output_root,
        candidate,
        initial_strategy,
        frontier_manifest,
    )
    if call_manifest is None:
        raise PhaseContractError("repair-010 recovery call registration is missing")
    call_root = v4._joint_call_registration_path(
        output_root, candidate.candidate_id, initial_strategy
    )
    call_registration = v4._load_json(call_root, "call.json")
    worker_result, native_log, process_log = v4._registered_joint_worker_paths(
        context, call_registration
    )
    key = v4._joint_call_key(candidate.candidate_id, initial_strategy)
    log_root = process_log.parents[1]
    phase_journal = log_root / "phase_journal" / f"{key}.jsonl"
    phase_registration = output_root / "joint_phase_registry" / key
    phase_spawn = output_root / "joint_phase_spawn_registry" / key
    phase_completion = output_root / "joint_phase_completion_registry" / key
    phase_finalization_intent = (
        output_root / "joint_phase_finalization_intent_registry" / key
    )
    phase_terminal_incomplete = (
        output_root / "joint_phase_terminal_incomplete_registry" / key
    )
    phase_finalization_success = (
        output_root / "joint_phase_finalization_success_registry" / key
    )
    checkpoint = v4._joint_checkpoint_path(
        output_root, candidate.candidate_id, initial_strategy
    )
    runtime_options = _runtime_options(context, native_log)
    expected_binding = build_worker_binding(
        preregistration_id=context.config["preregistration"]["id"],
        input_contract_sha256=context.input_contract_sha256,
        frontier_manifest_sha256=frontier_manifest,
        call_manifest_sha256=call_manifest,
        candidate_id=candidate.candidate_id,
        commitment_sha256=candidate.commitment_sha256,
        dispatch_sha256=candidate.dispatch_sha256,
        initial_strategy=initial_strategy,
        prepared_inputs_sha256=v4_adapter.prepared_inputs_sha256(
            prepared_cases, chronology
        ),
        ipopt_options_sha256=v4_adapter.effective_ipopt_options_sha256(
            base_options=context.config["joint_ac"]["ipopt_options"],
            runtime_options=runtime_options,
        ),
    )
    return PhaseRecoveryEvidence(
        call_manifest_sha256=call_manifest,
        call_registration=call_registration,
        worker_result=worker_result,
        native_solver_log=native_log,
        phase_journal=phase_journal,
        phase_registration=phase_registration,
        phase_spawn=phase_spawn,
        phase_completion=phase_completion,
        phase_finalization_intent=phase_finalization_intent,
        phase_terminal_incomplete=phase_terminal_incomplete,
        phase_finalization_success=phase_finalization_success,
        checkpoint=checkpoint,
        expected_binding=expected_binding,
    )


def _load_completed_phase_evidence_unwrapped(
    context: v4._FrontierContext,
    output_root: Path,
    candidate: v4._LoadedCandidate,
    initial_strategy: str,
    frontier_manifest: str,
    prepared_cases: tuple[Any, ...],
    chronology: Any,
) -> dict[str, Any]:
    evidence = _phase_recovery_evidence(
        context,
        output_root,
        candidate,
        initial_strategy,
        frontier_manifest,
        prepared_cases,
        chronology,
    )
    spawn = load_verified_phase_worker_spawn(
        phase_registration_directory=evidence.phase_registration,
        phase_spawn_directory=evidence.phase_spawn,
        expected_binding=evidence.expected_binding,
    )
    completion = load_verified_phase_completion(
        phase_registration_directory=evidence.phase_registration,
        phase_completion_directory=evidence.phase_completion,
        expected_binding=evidence.expected_binding,
        expected_phase_journal=evidence.phase_journal,
        expected_worker_result=evidence.worker_result,
        expected_native_solver_log=evidence.native_solver_log,
    )
    registration = _load_phase_registration(evidence.phase_registration)
    if registration.get("parent_pid") != evidence.call_registration.get(
        "parent_pid"
    ) or completion.get("worker_pid") != spawn.get("worker_pid"):
        raise PhaseContractError("repair-010 recovery parent PID binding drifted")
    return completion


def _validate_completed_phase_evidence(
    context: v4._FrontierContext,
    output_root: Path,
    candidate: v4._LoadedCandidate,
    initial_strategy: str,
    frontier_manifest: str,
    prepared_cases: tuple[Any, ...],
    chronology: Any,
) -> dict[str, Any]:
    try:
        evidence = _phase_recovery_evidence(
            context,
            output_root,
            candidate,
            initial_strategy,
            frontier_manifest,
            prepared_cases,
            chronology,
        )
        _validate_phase_finalization_for_recovery(evidence)
        return _load_completed_phase_evidence_unwrapped(
            context,
            output_root,
            candidate,
            initial_strategy,
            frontier_manifest,
            prepared_cases,
            chronology,
        )
    except PhaseContractError:
        raise
    except Exception as error:
        raise PhaseContractError(
            f"repair-010 recovery phase evidence validation failed: {error}"
        ) from error


def _validate_phase_finalization_for_recovery(
    evidence: PhaseRecoveryEvidence,
) -> dict[str, Any]:
    """Reject terminal calls before inspecting any completion/result receipt."""

    if evidence.phase_terminal_incomplete.exists():
        terminal = load_verified_phase_terminal_incomplete(
            terminal_directory=evidence.phase_terminal_incomplete,
            finalization_intent_directory=evidence.phase_finalization_intent,
            expected_binding=evidence.expected_binding,
            expected_phase_registration=evidence.phase_registration,
            expected_phase_spawn=evidence.phase_spawn,
            expected_phase_journal=evidence.phase_journal,
            expected_phase_completion=evidence.phase_completion,
        )
        raise PhaseContractError(
            "repair-010 call is terminal honest incomplete; recovery forbidden: "
            f"{terminal['reason']}"
        )
    load_verified_phase_finalization_intent(
        finalization_intent_directory=evidence.phase_finalization_intent,
        expected_binding=evidence.expected_binding,
        expected_phase_registration=evidence.phase_registration,
        expected_phase_spawn=evidence.phase_spawn,
        expected_phase_journal=evidence.phase_journal,
    )
    return load_verified_phase_finalization_success(evidence=evidence)


def _classify_phase_journal_evidence(
    *,
    phase_registration: Path,
    phase_spawn: Path,
    phase_journal: Path,
    expected_binding: Mapping[str, object],
    reason: str,
) -> HonestIncomplete:
    solver_started_verified = False
    try:
        spawn = load_verified_phase_worker_spawn(
            phase_registration_directory=phase_registration,
            phase_spawn_directory=phase_spawn,
            expected_binding=expected_binding,
        )
        records = load_verified_phase_events(
            phase_journal,
            expected_binding=expected_binding,
            expected_worker_pid=int(spawn["worker_pid"]),
        )
        solver_started_verified = any(
            record.get("event") == "solver_started" for record in records
        )
    except Exception:
        solver_started_verified = False
    return classify_phase_contract_failure(
        solver_started_was_verified=solver_started_verified,
        reason=reason,
    )


def _classify_recovery_phase_failure(
    context: v4._FrontierContext,
    output_root: Path,
    candidate: v4._LoadedCandidate,
    initial_strategy: str,
    frontier_manifest: str,
    prepared_cases: tuple[Any, ...],
    chronology: Any,
    *,
    reason: str,
) -> HonestIncomplete:
    try:
        evidence = _phase_recovery_evidence(
            context,
            output_root,
            candidate,
            initial_strategy,
            frontier_manifest,
            prepared_cases,
            chronology,
        )
    except Exception:
        return classify_phase_contract_failure(
            solver_started_was_verified=False,
            reason=reason,
        )
    return _classify_phase_journal_evidence(
        phase_registration=evidence.phase_registration,
        phase_spawn=evidence.phase_spawn,
        phase_journal=evidence.phase_journal,
        expected_binding=evidence.expected_binding,
        reason=reason,
    )


def _load_phase_aware_checkpoint(
    context: v4._FrontierContext,
    output_root: Path,
    candidate: v4._LoadedCandidate,
    initial_strategy: str,
    frontier_manifest: str,
    prepared_cases: tuple[Any, ...],
    chronology: Any,
) -> tuple[v4._JointRows, str, str] | None:
    checkpoint = v4._joint_checkpoint_path(
        output_root, candidate.candidate_id, initial_strategy
    )
    if not checkpoint.exists():
        return None
    _validate_completed_phase_evidence(
        context,
        output_root,
        candidate,
        initial_strategy,
        frontier_manifest,
        prepared_cases,
        chronology,
    )
    return v4._load_joint_checkpoint(
        context,
        output_root,
        candidate,
        initial_strategy,
        frontier_manifest,
        prepared_cases,
        chronology,
    )


def _load_phase_aware_worker_result(
    context: v4._FrontierContext,
    output_root: Path,
    candidate: v4._LoadedCandidate,
    initial_strategy: str,
    frontier_manifest: str,
    prepared_cases: tuple[Any, ...],
    chronology: Any,
) -> tuple[v4._JointRows, Path, str, str]:
    _validate_completed_phase_evidence(
        context,
        output_root,
        candidate,
        initial_strategy,
        frontier_manifest,
        prepared_cases,
        chronology,
    )
    call_manifest = v4._validate_joint_call_registration(
        context, output_root, candidate, initial_strategy, frontier_manifest
    )
    if call_manifest is None:
        raise PhaseContractError("repair-010 recovery call registration is missing")
    call_registration = v4._load_json(
        v4._joint_call_registration_path(
            output_root, candidate.candidate_id, initial_strategy
        ),
        "call.json",
    )
    worker_result, native_log, _process_log = v4._registered_joint_worker_paths(
        context, call_registration
    )
    rows, worker_manifest = v4._load_joint_worker_result(
        context,
        worker_result,
        native_log,
        candidate,
        initial_strategy,
        frontier_manifest,
        call_manifest,
        prepared_cases,
        chronology,
    )
    return rows, native_log, worker_manifest, call_manifest


def _validate_all_completed_phase_evidence(
    context: v4._FrontierContext,
    output_root: Path,
    candidates: Sequence[v4._LoadedCandidate],
    frontier_manifest: str,
    prepared: Mapping[str, tuple[Any, ...]],
    chronology: Mapping[str, Any],
) -> None:
    for candidate in candidates:
        for strategy_value in context.config["joint_ac"]["initial_strategies"]:
            strategy = str(strategy_value)
            try:
                _validate_completed_phase_evidence(
                    context,
                    output_root,
                    candidate,
                    strategy,
                    frontier_manifest,
                    prepared[candidate.candidate_id],
                    chronology[candidate.candidate_id],
                )
            except PhaseContractError as error:
                raise IsolatedWorkerIncompleteError(
                    _classify_recovery_phase_failure(
                        context,
                        output_root,
                        candidate,
                        strategy,
                        frontier_manifest,
                        prepared[candidate.candidate_id],
                        chronology[candidate.candidate_id],
                        reason=f"recovery_phase_failure:{error}",
                    )
                ) from error


def _load_phase_aware_all_checkpoints(
    context: v4._FrontierContext,
    output_root: Path,
    candidates: Sequence[v4._LoadedCandidate],
    frontier_manifest: str,
    prepared: Mapping[str, tuple[Any, ...]],
    chronology: Mapping[str, Any],
) -> tuple[v4._JointRows, dict[str, str], dict[str, str]]:
    _validate_all_completed_phase_evidence(
        context,
        output_root,
        candidates,
        frontier_manifest,
        prepared,
        chronology,
    )
    return v4._load_all_joint_checkpoints(
        context,
        output_root,
        candidates,
        frontier_manifest,
        prepared,
        chronology,
    )


def _load_phase_aware_joint_results(
    context: v4._FrontierContext,
    target: Path,
    registration: Mapping[str, Any],
    candidates: Sequence[v4._LoadedCandidate],
    frontier_manifest: str,
    prepared: Mapping[str, tuple[Any, ...]],
    chronology: Mapping[str, Any],
) -> dict[str, Any]:
    _validate_all_completed_phase_evidence(
        context,
        target.parent,
        candidates,
        frontier_manifest,
        prepared,
        chronology,
    )
    return v4._load_joint_results(
        context,
        target,
        registration,
        candidates,
        frontier_manifest,
        prepared,
        chronology,
    )


def _raise_honest_incomplete(
    error: BaseException,
    *,
    outcome: HonestIncomplete,
    on_incomplete: Callable[[HonestIncomplete], None],
) -> None:
    notification_error: BaseException | None = None
    try:
        on_incomplete(outcome)
    except BaseException as callback_error:
        notification_error = callback_error
    incomplete = IsolatedWorkerIncompleteError(outcome)
    if notification_error is not None:
        incomplete.add_note(
            "Failed to persist repair-010 honest-incomplete evidence: "
            + (str(notification_error) or repr(notification_error))
        )
    raise incomplete from error


def _raise_verified_solver_incomplete(
    error: BaseException,
    *,
    reason: str,
    on_incomplete: Callable[[HonestIncomplete], None],
) -> None:
    _raise_honest_incomplete(
        error,
        outcome=classify_phase_contract_failure(
            solver_started_was_verified=True,
            reason=reason,
        ),
        on_incomplete=on_incomplete,
    )


def _persist_terminal_incomplete_or_raise(
    error: BaseException,
    *,
    outcome: HonestIncomplete,
    persist_terminal: Callable[[HonestIncomplete], None],
    on_incomplete: Callable[[HonestIncomplete], None],
) -> None:
    """Persist the immutable terminal state before reporting incompleteness."""

    try:
        persist_terminal(outcome)
    except BaseException as persistence_error:
        raise TerminalIncompletePersistenceError(outcome, persistence_error) from error
    _raise_honest_incomplete(
        error,
        outcome=outcome,
        on_incomplete=on_incomplete,
    )


def _seal_phase_finalization_or_raise(
    evidence: PhaseRecoveryEvidence,
    *,
    on_incomplete: Callable[[HonestIncomplete], None],
) -> None:
    """Resolve success-seal publication to one durable terminal truth."""

    try:
        register_phase_finalization_success(
            evidence.phase_finalization_success,
            phase_finalization_intent_directory=evidence.phase_finalization_intent,
            phase_completion_directory=evidence.phase_completion,
            checkpoint_directory=evidence.checkpoint,
            terminal_directory=evidence.phase_terminal_incomplete,
            binding=evidence.expected_binding,
        )
    except SuccessSealCommitIndeterminateError:
        raise
    except BaseException as error:
        outcome = classify_phase_contract_failure(
            solver_started_was_verified=True,
            reason=f"post_solver_success_seal_failure:{error}",
        )

        def persist_terminal(outcome: HonestIncomplete) -> None:
            register_phase_terminal_incomplete(
                evidence.phase_terminal_incomplete,
                phase_finalization_intent_directory=(
                    evidence.phase_finalization_intent
                ),
                phase_completion_directory=evidence.phase_completion,
                binding=evidence.expected_binding,
                reason=outcome.reason,
            )

        _persist_terminal_incomplete_or_raise(
            error,
            outcome=outcome,
            persist_terminal=persist_terminal,
            on_incomplete=on_incomplete,
        )


def _publish_verified_phase_completion(
    *,
    completion_directory: Path,
    binding: Mapping[str, object],
    phase_registration_manifest_sha256: str,
    phase_journal: Path,
    worker_pid: int,
    worker_result: Path,
    worker_result_manifest_sha256: str,
    native_solver_log: Path,
    post_completion_validator: Callable[[], object],
    persist_terminal: Callable[[HonestIncomplete], None],
    on_incomplete: Callable[[HonestIncomplete], None],
) -> str:
    """Publish/revalidate a receipt after solver start is already trusted."""

    try:
        manifest = register_phase_completion(
            completion_directory,
            binding=binding,
            phase_registration_manifest_sha256=(phase_registration_manifest_sha256),
            phase_journal=phase_journal,
            worker_pid=worker_pid,
            worker_result=worker_result,
            worker_result_manifest_sha256=worker_result_manifest_sha256,
            native_solver_log=native_solver_log,
        )
        post_completion_validator()
    except IsolatedWorkerIncompleteError:
        raise
    except BaseException as error:
        _persist_terminal_incomplete_or_raise(
            error,
            outcome=classify_phase_contract_failure(
                solver_started_was_verified=True,
                reason=f"post_solver_phase_completion_failure:{error}",
            ),
            persist_terminal=persist_terminal,
            on_incomplete=on_incomplete,
        )
    return manifest


def _run_joint_worker_process(
    context: v4._FrontierContext,
    output_root: Path,
    candidate: v4._LoadedCandidate,
    initial_strategy: str,
    frontier_manifest: str,
    prepared_cases: tuple[Any, ...],
    chronology: Any,
    log_root: Path,
    progress: JsonlProgressWriter,
    call_manifest: str,
) -> tuple[v4._JointRows, Path, str]:
    key = v4._joint_call_key(candidate.candidate_id, initial_strategy)
    worker_result, native_log, process_log = v4._joint_worker_paths(
        log_root, candidate.candidate_id, initial_strategy
    )
    phase_journal = log_root / "phase_journal" / f"{key}.jsonl"
    phase_registration = output_root / "joint_phase_registry" / key
    phase_spawn = output_root / "joint_phase_spawn_registry" / key
    phase_completion = output_root / "joint_phase_completion_registry" / key
    phase_finalization_intent = (
        output_root / "joint_phase_finalization_intent_registry" / key
    )
    phase_terminal_incomplete = (
        output_root / "joint_phase_terminal_incomplete_registry" / key
    )
    runtime_options = _runtime_options(context, native_log)
    binding = build_worker_binding(
        preregistration_id=context.config["preregistration"]["id"],
        input_contract_sha256=context.input_contract_sha256,
        frontier_manifest_sha256=frontier_manifest,
        call_manifest_sha256=call_manifest,
        candidate_id=candidate.candidate_id,
        commitment_sha256=candidate.commitment_sha256,
        dispatch_sha256=candidate.dispatch_sha256,
        initial_strategy=initial_strategy,
        prepared_inputs_sha256=v4_adapter.prepared_inputs_sha256(
            prepared_cases, chronology
        ),
        ipopt_options_sha256=v4_adapter.effective_ipopt_options_sha256(
            base_options=context.config["joint_ac"]["ipopt_options"],
            runtime_options=runtime_options,
        ),
    )
    phase_manifest = register_phase_worker_call(
        phase_registration,
        binding=binding,
        phase_journal=phase_journal,
        worker_result=worker_result,
        native_solver_log=native_log,
        worker_process_log=process_log,
        parent_pid=os.getpid(),
    )
    command = _joint_worker_command(
        python_executable=Path(sys.executable),
        config_path=context.config_path,
        output_root=output_root,
        candidate_id=candidate.candidate_id,
        initial_strategy=initial_strategy,
        worker_result=worker_result,
        native_log=native_log,
        phase_journal=phase_journal,
        phase_registration_directory=phase_registration,
        call_manifest_sha256=call_manifest,
        phase_registration_manifest_sha256=phase_manifest,
    )
    joint = _read_config(context.config_path)["joint_ac_successor"]

    def on_spawn(worker_pid: int) -> None:
        spawn_manifest = register_phase_worker_spawn(
            phase_spawn,
            phase_registration_directory=phase_registration,
            binding=binding,
            worker_pid=worker_pid,
        )
        progress.emit(
            "joint_call_started",
            stage="joint_ac",
            call_id=f"joint_ac.{key}",
            candidate_id=candidate.candidate_id,
            requested_candidate_id=candidate.requested_candidate_id,
            initial_strategy=initial_strategy,
            startup_limit_seconds=float(joint["startup_limit_seconds"]),
            solver_wall_limit_seconds=float(
                joint["solver_wall_limit_seconds_per_call"]
            ),
            native_log=str(native_log.resolve()),
            phase_journal=str(phase_journal.resolve()),
            worker_pid=worker_pid,
            call_registration_manifest_sha256=call_manifest,
            phase_registration_manifest_sha256=phase_manifest,
            phase_spawn_manifest_sha256=spawn_manifest,
        )

    def on_incomplete(outcome: HonestIncomplete) -> None:
        progress.emit(
            "joint_call_honest_incomplete",
            stage="joint_ac",
            candidate_id=candidate.candidate_id,
            requested_candidate_id=candidate.requested_candidate_id,
            initial_strategy=initial_strategy,
            reason=outcome.reason,
            solver_call_count=outcome.solver_call_count,
            is_infeasibility_evidence=outcome.is_infeasibility_evidence,
            resume_allowed=outcome.resume_allowed,
        )

    completion = run_isolated_worker_process(
        command=command,
        phase_journal=phase_journal,
        expected_binding=binding,
        worker_process_log=process_log,
        result_validator=lambda: v4._load_joint_worker_result(
            context,
            worker_result,
            native_log,
            candidate,
            initial_strategy,
            frontier_manifest,
            call_manifest,
            prepared_cases,
            chronology,
        ),
        startup_limit_seconds=float(joint["startup_limit_seconds"]),
        solver_wall_limit_seconds=float(joint["solver_wall_limit_seconds_per_call"]),
        termination_grace_seconds=float(joint["termination_grace_seconds"]),
        on_spawn=on_spawn,
        on_incomplete=on_incomplete,
    )
    intent_published = False
    try:
        rows, worker_manifest = completion.result
        intent_manifest = register_phase_finalization_intent(
            phase_finalization_intent,
            phase_registration_directory=phase_registration,
            phase_spawn_directory=phase_spawn,
            binding=binding,
            phase_journal=phase_journal,
        )
        intent_published = True
        progress.emit(
            "joint_call_phase_finalization_intent_registered",
            stage="joint_ac",
            candidate_id=candidate.candidate_id,
            requested_candidate_id=candidate.requested_candidate_id,
            initial_strategy=initial_strategy,
            worker_pid=completion.worker_pid,
            phase_finalization_intent_manifest_sha256=intent_manifest,
            solver_call_count=1,
            retry_or_resume_used=False,
        )

        def persist_terminal(outcome: HonestIncomplete) -> None:
            register_phase_terminal_incomplete(
                phase_terminal_incomplete,
                phase_finalization_intent_directory=phase_finalization_intent,
                phase_completion_directory=phase_completion,
                binding=binding,
                reason=outcome.reason,
            )

        completion_manifest = _publish_verified_phase_completion(
            completion_directory=phase_completion,
            binding=binding,
            phase_registration_manifest_sha256=phase_manifest,
            phase_journal=phase_journal,
            worker_pid=completion.worker_pid,
            worker_result=worker_result,
            worker_result_manifest_sha256=worker_manifest,
            native_solver_log=native_log,
            post_completion_validator=lambda: _load_completed_phase_evidence_unwrapped(
                context,
                output_root,
                candidate,
                initial_strategy,
                frontier_manifest,
                prepared_cases,
                chronology,
            ),
            persist_terminal=persist_terminal,
            on_incomplete=on_incomplete,
        )
        progress.emit(
            "joint_call_phase_completion_registered",
            stage="joint_ac",
            candidate_id=candidate.candidate_id,
            requested_candidate_id=candidate.requested_candidate_id,
            initial_strategy=initial_strategy,
            worker_pid=completion.worker_pid,
            phase_completion_manifest_sha256=completion_manifest,
            solver_call_count=1,
            is_infeasibility_evidence=False,
            retry_or_resume_used=False,
        )
        return rows, native_log, worker_manifest
    except IsolatedWorkerIncompleteError:
        raise
    except TerminalIncompletePersistenceError:
        raise
    except BaseException as error:
        outcome = classify_phase_contract_failure(
            solver_started_was_verified=True,
            reason=f"post_solver_parent_finalization_failure:{error}",
        )
        if not intent_published:
            try:
                on_incomplete(outcome)
            finally:
                raise TerminalIncompletePersistenceError(outcome, error) from error
        _persist_terminal_incomplete_or_raise(
            error,
            outcome=outcome,
            persist_terminal=persist_terminal,
            on_incomplete=on_incomplete,
        )


def _execute_repair010_joint_call_worker(
    context: v4._FrontierContext,
    candidate: v4._LoadedCandidate,
    initial_strategy: str,
    frontier_manifest: str,
    result_directory: Path,
    native_solver_log: Path,
    call_registration_manifest_sha256: str,
    prepared_cases: tuple[Any, ...],
    chronology: object,
    phase_observer: Callable[[str, Mapping[str, object]], None],
) -> dict[str, object]:
    """Execute the legacy worker publication contract via the repair-010 adapter."""

    runtime = context.config["joint_ac"]["runtime_control"]
    result = v4_adapter.solve_ac_aware_commitment_v4_worker(
        prepared_cases,
        chronology,
        initial_strategy=initial_strategy,
        base_options=context.config["joint_ac"]["ipopt_options"],
        runtime_options={
            "ipopt.max_cpu_time": float(runtime["max_cpu_time_seconds_per_call"]),
            "ipopt.output_file": str(native_solver_log.resolve()),
            "ipopt.file_print_level": int(runtime["native_file_print_level"]),
        },
        phase_observer=phase_observer,
    )
    result_tuple = v4._joint_result_rows(candidate, result)
    rows = v4._JointRows(
        runs=(result_tuple[0],),
        hours=tuple(result_tuple[1]),
        generators=tuple(result_tuple[2]),
        buses=tuple(result_tuple[3]),
        branches=tuple(result_tuple[4]),
        reserves=tuple(result_tuple[5]),
    )
    v4._validate_joint_result_rows(
        context,
        (candidate,),
        {candidate.candidate_id: prepared_cases},
        {candidate.candidate_id: chronology},
        rows.runs,
        rows.hours,
        rows.generators,
        rows.buses,
        rows.branches,
        rows.reserves,
        initial_strategies=(initial_strategy,),
    )
    if not native_solver_log.is_file() or native_solver_log.stat().st_size <= 0:
        raise RuntimeError("RTS-GMLC AC-aware worker native solver log is missing")
    metadata = v4._joint_worker_metadata(
        context,
        candidate,
        initial_strategy,
        frontier_manifest,
        call_registration_manifest_sha256,
        _sha256(native_solver_log),
    )

    def writer(staging: Path) -> None:
        v4._write_joint_rows(staging, rows)
        v4._write_exact_json(staging / "worker.json", metadata)

    def validate(staging: Path) -> None:
        observed = v4._load_json(staging, "worker.json")
        if v4._exact_json_text(observed) != v4._exact_json_text(
            v4._exact_json_payload(metadata)
        ):
            raise RuntimeError("RTS-GMLC AC-aware joint worker staging drifted")
        staged_rows = v4._load_joint_rows(staging)
        v4._validate_joint_result_rows(
            context,
            (candidate,),
            {candidate.candidate_id: prepared_cases},
            {candidate.candidate_id: chronology},
            staged_rows.runs,
            staged_rows.hours,
            staged_rows.generators,
            staged_rows.buses,
            staged_rows.branches,
            staged_rows.reserves,
            initial_strategies=(initial_strategy,),
        )

    v4._publish_immutable_payload(result_directory, writer, validator=validate)
    v4._load_joint_worker_result(
        context,
        result_directory,
        native_solver_log,
        candidate,
        initial_strategy,
        frontier_manifest,
        call_registration_manifest_sha256,
        prepared_cases,
        chronology,
    )
    return metadata


def run_joint_call_worker(
    config_path: Path,
    *,
    output_directory: Path,
    candidate_id: str,
    initial_strategy: str,
    result_directory: Path,
    native_solver_log: Path,
    phase_journal: Path,
    phase_registration_directory: Path,
    call_registration_manifest_sha256: str,
    phase_registration_manifest_sha256: str,
) -> dict[str, object]:
    config = _read_config(config_path)
    _assert_successor_ready(config)
    if (
        _sha256(phase_registration_directory / "SHA256SUMS")
        != phase_registration_manifest_sha256
    ):
        raise RuntimeError("repair-010 phase registration manifest drifted")
    registration = _load_phase_registration(phase_registration_directory)
    binding = registration["binding"]
    if (
        registration["phase_journal"] != str(phase_journal.resolve())
        or registration["worker_result"] != str(result_directory.resolve())
        or registration["native_solver_log"] != str(native_solver_log.resolve())
        or binding.get("call_manifest_sha256") != call_registration_manifest_sha256
        or binding.get("candidate_id") != candidate_id
        or binding.get("initial_strategy") != initial_strategy
    ):
        raise RuntimeError("repair-010 worker phase registration path drifted")
    output_root = output_directory.resolve()
    call_root = v4._joint_call_registration_path(
        output_root, candidate_id, initial_strategy
    )
    if _sha256(call_root / "SHA256SUMS") != call_registration_manifest_sha256:
        raise RuntimeError("repair-010 worker call registration drifted")
    call_registration = v4._load_json(call_root, "call.json")
    parent_pid = call_registration["parent_pid"]
    parent_attempt_id = call_registration["parent_attempt_id"]
    registered_log_root = (
        Path(config["logging"]["directory"]) / parent_attempt_id
    ).resolve()
    registered_result = (
        registered_log_root / call_registration["worker_result_relative_path"]
    ).resolve()
    registered_native = (
        registered_log_root / call_registration["native_solver_log_relative_path"]
    ).resolve()
    registered_process = (
        registered_log_root / call_registration["worker_process_log_relative_path"]
    ).resolve()
    if (
        parent_pid != os.getppid()
        or registration["parent_pid"] != parent_pid
        or registered_result != result_directory.resolve()
        or registered_native != native_solver_log.resolve()
        or registration["worker_result"] != str(registered_result)
        or registration["native_solver_log"] != str(registered_native)
        or registration["worker_process_log"] != str(registered_process)
    ):
        raise RuntimeError("repair-010 worker parent identity drifted")
    active_lease = json.loads(
        (output_root / "execution_lease" / "active" / "lease.json").read_text(
            encoding="utf-8"
        )
    )
    if (
        not isinstance(active_lease, dict)
        or active_lease.get("schema") != "execution_lease_v1"
        or active_lease.get("pid") != parent_pid
        or active_lease.get("stage") != "run_joint_ac"
        or active_lease.get("attempt_id") != parent_attempt_id
    ):
        raise RuntimeError("repair-010 worker execution lease drifted")
    journal = DurablePhaseJournal(phase_journal, binding=binding)
    runtime = config["joint_ac_successor"]
    with v4.ParentProcessWatchdog(
        int(parent_pid),
        interval_seconds=float(runtime["parent_watchdog_interval_seconds"]),
    ):
        context_holder: dict[str, object] = {}

        def load_context() -> v4._FrontierContext:
            context = _build_context(config_path)
            context_holder["context"] = context
            _require_preregistration(context, output_root)
            if (
                binding["preregistration_id"] != context.config["preregistration"]["id"]
                or binding["input_contract_sha256"] != context.input_contract_sha256
            ):
                raise RuntimeError("repair-010 worker input contract drifted")
            return context

        def load_prepared(
            context: v4._FrontierContext,
        ) -> tuple[Sequence[object], object]:
            candidates, frontier_manifest = _load_successor_frontier_import(
                context, output_root
            )
            matches = [item for item in candidates if item.candidate_id == candidate_id]
            if len(matches) != 1:
                raise RuntimeError("repair-010 worker candidate identity drifted")
            candidate = matches[0]
            if (
                frontier_manifest != binding["frontier_manifest_sha256"]
                or candidate.commitment_sha256 != binding["commitment_sha256"]
                or candidate.dispatch_sha256 != binding["dispatch_sha256"]
                or v4._validate_joint_call_registration(
                    context,
                    output_root,
                    candidate,
                    initial_strategy,
                    frontier_manifest,
                )
                != call_registration_manifest_sha256
            ):
                raise RuntimeError("repair-010 worker bound candidate drifted")
            context_holder["candidate"] = candidate
            context_holder["frontier_manifest"] = frontier_manifest
            return (
                v4._prepared_joint_cases(context, candidate),
                v4._joint_chronology(context, candidate),
            )

        def execute_and_publish(
            context: object,
            prepared_cases: Sequence[object],
            chronology: object,
            observer: Callable[[str, Mapping[str, object]], None],
        ) -> object:
            typed_context = context
            candidate = context_holder["candidate"]
            frontier_manifest = context_holder["frontier_manifest"]
            if (
                v4_adapter.prepared_inputs_sha256(prepared_cases, chronology)
                != binding["prepared_inputs_sha256"]
            ):
                raise RuntimeError("repair-010 prepared cases changed before solve")
            expected_runtime_options = {
                "ipopt.max_cpu_time": float(
                    typed_context.config["joint_ac"]["runtime_control"][
                        "max_cpu_time_seconds_per_call"
                    ]
                ),
                "ipopt.output_file": str(native_solver_log.resolve()),
                "ipopt.file_print_level": int(
                    typed_context.config["joint_ac"]["runtime_control"][
                        "native_file_print_level"
                    ]
                ),
            }
            if (
                v4_adapter.effective_ipopt_options_sha256(
                    base_options=typed_context.config["joint_ac"]["ipopt_options"],
                    runtime_options=expected_runtime_options,
                )
                != binding["ipopt_options_sha256"]
            ):
                raise RuntimeError("repair-010 observed solve input drifted")
            return _execute_repair010_joint_call_worker(
                typed_context,
                candidate,
                initial_strategy,
                frontier_manifest,
                result_directory,
                native_solver_log,
                call_registration_manifest_sha256,
                prepared_cases,
                chronology,
                observer,
            )

        def validate_software_identity() -> None:
            if binding.get("software_identity") != _software_identity():
                raise RuntimeError("repair-010 worker software identity drifted")

        result = execute_phase_instrumented_worker(
            journal=journal,
            context_loader=load_context,
            prepared_cases_loader=load_prepared,
            base_options={},
            runtime_options={},
            initial_strategy=initial_strategy,
            heartbeat_interval_seconds=float(
                runtime["startup_heartbeat_interval_seconds"]
            ),
            worker_operation=execute_and_publish,
            post_worker_start_validator=validate_software_identity,
        )
    return result


def _run_joint_ac_attempt(
    context: v4._FrontierContext,
    output_root: Path,
    registration: Mapping[str, Any],
    candidates: list[v4._LoadedCandidate],
    frontier_manifest: str,
    attempt_id: str,
    log_root: Path,
    progress: JsonlProgressWriter,
) -> dict[str, Any]:
    runtime = context.config["joint_ac"]["runtime_control"]
    progress.emit("joint_preparation_started", stage="joint_ac_preparation")
    with v4._CheckedProgressHeartbeat(
        progress,
        interval_seconds=float(runtime["heartbeat_interval_seconds"]),
        payload={"stage": "joint_ac_preparation"},
    ):
        prepared = {
            item.candidate_id: v4._prepared_joint_cases(context, item)
            for item in candidates
        }
        chronology = {
            item.candidate_id: v4._joint_chronology(context, item)
            for item in candidates
        }
    progress.emit("joint_preparation_completed", stage="joint_ac_preparation")
    target = output_root / "joint_ac"
    if target.exists():
        return _load_phase_aware_joint_results(
            context,
            target,
            registration,
            candidates,
            frontier_manifest,
            prepared,
            chronology,
        )
    parts = []
    completed = 0
    total = len(candidates) * len(context.config["joint_ac"]["initial_strategies"])
    for candidate in candidates:
        for strategy_value in context.config["joint_ac"]["initial_strategies"]:
            strategy = str(strategy_value)

            def report_incomplete(outcome: HonestIncomplete) -> None:
                progress.emit(
                    "joint_call_honest_incomplete",
                    stage="joint_ac",
                    candidate_id=candidate.candidate_id,
                    requested_candidate_id=candidate.requested_candidate_id,
                    initial_strategy=strategy,
                    reason=outcome.reason,
                    solver_call_count=outcome.solver_call_count,
                    is_infeasibility_evidence=outcome.is_infeasibility_evidence,
                    resume_allowed=outcome.resume_allowed,
                )

            try:
                loaded = _load_phase_aware_checkpoint(
                    context,
                    output_root,
                    candidate,
                    strategy,
                    frontier_manifest,
                    prepared[candidate.candidate_id],
                    chronology[candidate.candidate_id],
                )
            except PhaseContractError as error:
                _raise_honest_incomplete(
                    error,
                    outcome=_classify_recovery_phase_failure(
                        context,
                        output_root,
                        candidate,
                        strategy,
                        frontier_manifest,
                        prepared[candidate.candidate_id],
                        chronology[candidate.candidate_id],
                        reason=f"recovery_phase_failure:{error}",
                    ),
                    on_incomplete=report_incomplete,
                )
            if loaded is not None:
                rows, checkpoint_manifest, call_manifest = loaded
                parts.append(rows)
                completed += 1
                progress.emit(
                    "joint_checkpoint_loaded_with_phase_evidence",
                    stage="joint_ac",
                    candidate_id=candidate.candidate_id,
                    requested_candidate_id=candidate.requested_candidate_id,
                    initial_strategy=strategy,
                    completed_joint_call_count=completed,
                    expected_joint_call_count=total,
                    checkpoint_manifest_sha256=checkpoint_manifest,
                    call_registration_manifest_sha256=call_manifest,
                    retry_or_resume_incomplete_call_used=False,
                )
                continue
            existing_call_manifest = v4._validate_joint_call_registration(
                context, output_root, candidate, strategy, frontier_manifest
            )
            if existing_call_manifest is not None:
                try:
                    (
                        worker_rows,
                        registered_native,
                        worker_manifest,
                        observed_call_manifest,
                    ) = _load_phase_aware_worker_result(
                        context,
                        output_root,
                        candidate,
                        strategy,
                        frontier_manifest,
                        prepared[candidate.candidate_id],
                        chronology[candidate.candidate_id],
                    )
                except PhaseContractError as error:
                    _raise_honest_incomplete(
                        error,
                        outcome=_classify_recovery_phase_failure(
                            context,
                            output_root,
                            candidate,
                            strategy,
                            frontier_manifest,
                            prepared[candidate.candidate_id],
                            chronology[candidate.candidate_id],
                            reason=f"recovery_phase_failure:{error}",
                        ),
                        on_incomplete=report_incomplete,
                    )
                try:
                    if observed_call_manifest != existing_call_manifest:
                        raise RuntimeError("repair-010 recovered call manifest drifted")
                    rows, checkpoint_manifest, saved_call_manifest = (
                        v4._save_joint_checkpoint(
                            context,
                            output_root,
                            candidate,
                            strategy,
                            frontier_manifest,
                            existing_call_manifest,
                            prepared[candidate.candidate_id],
                            chronology[candidate.candidate_id],
                            worker_rows,
                            registered_native,
                            worker_manifest,
                        )
                    )
                    if saved_call_manifest != existing_call_manifest:
                        raise RuntimeError(
                            "repair-010 recovered checkpoint call drifted"
                        )
                except BaseException as error:
                    _raise_verified_solver_incomplete(
                        error,
                        reason=f"recovered_checkpoint_publication_failure:{error}",
                        on_incomplete=report_incomplete,
                    )
                parts.append(rows)
                completed += 1
                progress.emit(
                    "joint_worker_result_recovered_with_phase_evidence",
                    stage="joint_ac",
                    candidate_id=candidate.candidate_id,
                    requested_candidate_id=candidate.requested_candidate_id,
                    initial_strategy=strategy,
                    worker_result_manifest_sha256=worker_manifest,
                    checkpoint_manifest_sha256=checkpoint_manifest,
                    call_registration_manifest_sha256=existing_call_manifest,
                    completed_joint_call_count=completed,
                    expected_joint_call_count=total,
                    retry_or_resume_incomplete_call_used=False,
                )
                continue
            worker_result, native_log_path, process_log_path = v4._joint_worker_paths(
                log_root, candidate.candidate_id, strategy
            )
            call_manifest = v4._register_joint_call(
                context,
                output_root,
                candidate,
                strategy,
                frontier_manifest,
                parent_attempt_id=attempt_id,
                parent_pid=os.getpid(),
                worker_result_directory=worker_result,
                native_solver_log=native_log_path,
                worker_process_log=process_log_path,
            )
            verified_completion = False
            finalization_evidence: PhaseRecoveryEvidence | None = None
            try:
                worker_rows, native_log, worker_manifest = _run_joint_worker_process(
                    context,
                    output_root,
                    candidate,
                    strategy,
                    frontier_manifest,
                    prepared[candidate.candidate_id],
                    chronology[candidate.candidate_id],
                    log_root,
                    progress,
                    call_manifest,
                )
                verified_completion = True
                finalization_evidence = _phase_recovery_evidence(
                    context,
                    output_root,
                    candidate,
                    strategy,
                    frontier_manifest,
                    prepared[candidate.candidate_id],
                    chronology[candidate.candidate_id],
                )
                rows, checkpoint_manifest, observed_call_manifest = (
                    v4._save_joint_checkpoint(
                        context,
                        output_root,
                        candidate,
                        strategy,
                        frontier_manifest,
                        call_manifest,
                        prepared[candidate.candidate_id],
                        chronology[candidate.candidate_id],
                        worker_rows,
                        native_log,
                        worker_manifest,
                    )
                )
                if observed_call_manifest != call_manifest:
                    raise RuntimeError("repair-010 joint call manifest drifted")
                run_row = rows.runs[0]
                progress.emit(
                    "joint_call_completed",
                    stage="joint_ac",
                    candidate_id=candidate.candidate_id,
                    requested_candidate_id=candidate.requested_candidate_id,
                    initial_strategy=strategy,
                    solver_success=v4._parse_bool(
                        run_row["solver_success"], label="solver_success"
                    ),
                    feasibility_witnessed=v4._parse_bool(
                        run_row["feasibility_witnessed"],
                        label="feasibility_witnessed",
                    ),
                    return_status=str(run_row["return_status"]),
                    iterations=v4._exact_int(run_row["iterations"], label="iterations"),
                    native_log=str(native_log.resolve()),
                    native_log_sha256=_sha256(native_log),
                    worker_result_manifest_sha256=worker_manifest,
                    checkpoint_manifest_sha256=checkpoint_manifest,
                    call_registration_manifest_sha256=call_manifest,
                    completed_joint_call_count=completed + 1,
                    expected_joint_call_count=total,
                )
                _seal_phase_finalization_or_raise(
                    finalization_evidence,
                    on_incomplete=report_incomplete,
                )
            except IsolatedWorkerIncompleteError:
                raise
            except TerminalIncompletePersistenceError:
                raise
            except SuccessSealCommitIndeterminateError:
                raise
            except BaseException as error:
                if verified_completion:
                    outcome = classify_phase_contract_failure(
                        solver_started_was_verified=True,
                        reason=f"post_solver_checkpoint_failure:{error}",
                    )

                    def persist_terminal(outcome: HonestIncomplete) -> None:
                        if finalization_evidence is None:
                            raise PhaseContractError(
                                "repair-010 finalization evidence is unavailable"
                            )
                        register_phase_terminal_incomplete(
                            finalization_evidence.phase_terminal_incomplete,
                            phase_finalization_intent_directory=(
                                finalization_evidence.phase_finalization_intent
                            ),
                            phase_completion_directory=(
                                finalization_evidence.phase_completion
                            ),
                            binding=finalization_evidence.expected_binding,
                            reason=outcome.reason,
                        )

                    _persist_terminal_incomplete_or_raise(
                        error,
                        outcome=outcome,
                        persist_terminal=persist_terminal,
                        on_incomplete=report_incomplete,
                    )
                progress.emit(
                    "joint_call_failed",
                    stage="joint_ac",
                    candidate_id=candidate.candidate_id,
                    requested_candidate_id=candidate.requested_candidate_id,
                    initial_strategy=strategy,
                    error_type=type(error).__name__,
                    error_message=str(error) or repr(error),
                    completed_joint_call_count=completed,
                    expected_joint_call_count=total,
                )
                raise
            parts.append(rows)
            completed += 1
    merged = v4._merge_joint_rows(parts)
    checkpoint_rows, checkpoint_manifests, call_manifests = (
        _load_phase_aware_all_checkpoints(
            context,
            output_root,
            candidates,
            frontier_manifest,
            prepared,
            chronology,
        )
    )
    if merged != checkpoint_rows:
        raise RuntimeError("repair-010 resumed joint row order drifted")
    v4._validate_joint_result_rows(
        context,
        candidates,
        prepared,
        chronology,
        merged.runs,
        merged.hours,
        merged.generators,
        merged.buses,
        merged.branches,
        merged.reserves,
    )
    summary = v4._joint_summary(
        context,
        registration,
        candidates,
        frontier_manifest,
        merged.runs,
        checkpoint_manifests,
        call_manifests,
    )

    def writer(staging: Path) -> None:
        v4._write_joint_rows(staging, merged)
        v4._write_exact_json(staging / "summary.json", summary)

    v4._publish_immutable_payload(
        target,
        writer,
        validator=lambda staging: _load_phase_aware_joint_results(
            context,
            staging,
            registration,
            candidates,
            frontier_manifest,
            prepared,
            chronology,
        ),
    )
    result = _load_phase_aware_joint_results(
        context,
        target,
        registration,
        candidates,
        frontier_manifest,
        prepared,
        chronology,
    )
    manifest = _sha256(target / "SHA256SUMS")
    progress.emit(
        "joint_results_published",
        stage="joint_ac",
        joint_manifest_sha256=manifest,
        completed_joint_call_count=completed,
        expected_joint_call_count=total,
    )
    progress.emit(
        "attempt_completed",
        stage="joint_ac",
        joint_manifest_sha256=manifest,
        completed_joint_call_count=completed,
        expected_joint_call_count=total,
    )
    return result


def run_joint_ac(
    config_path: Path = DEFAULT_CONFIG_PATH,
    *,
    output_directory: Path | None = None,
    attempt_id: str | None = None,
) -> dict[str, Any]:
    config = _read_config(config_path)
    _assert_successor_ready(config)
    context = _build_context(config_path)
    output_root = output_directory or context.output_root
    registration = _require_preregistration(context, output_root)
    candidates, frontier_manifest = _load_successor_frontier_import(
        context, output_root
    )
    if not candidates:
        raise RuntimeError("repair-010 candidate frontier is empty")
    if attempt_id is None:
        attempt_id = (
            datetime.now(timezone.utc).strftime("joint_%Y%m%dT%H%M%S%fZ")
            + f"_pid{os.getpid()}"
        )
    if re.fullmatch(r"[A-Za-z0-9_.-]+", attempt_id) is None:
        raise ValueError("Invalid repair-010 joint attempt ID")
    log_root = Path(config["logging"]["directory"]) / attempt_id
    with ExecutionLease.acquire(
        output_root / "execution_lease",
        stage="run_joint_ac",
        attempt_id=attempt_id,
    ):
        target = output_root / "joint_ac"
        if target.exists():
            prepared = {
                item.candidate_id: v4._prepared_joint_cases(context, item)
                for item in candidates
            }
            chronology = {
                item.candidate_id: v4._joint_chronology(context, item)
                for item in candidates
            }
            return _load_phase_aware_joint_results(
                context,
                target,
                registration,
                candidates,
                frontier_manifest,
                prepared,
                chronology,
            )
        progress = JsonlProgressWriter(
            log_root / "progress.jsonl",
            run_id=attempt_id,
            preregistration_id=context.config["preregistration"]["id"],
            input_contract_sha256=context.input_contract_sha256,
        )
        started = datetime.now(timezone.utc)
        v4._write_exact_json(
            log_root / "attempt.json",
            {
                "schema": "rts_gmlc_v4_repair_010_joint_attempt_v1",
                "attempt_id": attempt_id,
                "pid": os.getpid(),
                "started_utc": started.isoformat(),
                "preregistration_id": context.config["preregistration"]["id"],
                "input_contract_sha256": context.input_contract_sha256,
                "candidate_frontier_manifest_sha256": frontier_manifest,
            },
        )
        progress.emit(
            "attempt_started",
            stage="joint_ac",
            started_utc=started.isoformat(),
            expected_joint_call_count=len(candidates)
            * len(context.config["joint_ac"]["initial_strategies"]),
            completed_joint_call_count=0,
        )
        try:
            return _run_joint_ac_attempt(
                context,
                output_root,
                registration,
                list(candidates),
                frontier_manifest,
                attempt_id,
                log_root,
                progress,
            )
        except BaseException as error:
            progress.emit(
                "attempt_failed",
                stage="joint_ac",
                error_type=type(error).__name__,
                error_message=str(error) or repr(error),
            )
            raise


def run_startup_calibration(
    config_path: Path = DEFAULT_CONFIG_PATH,
    *,
    launcher_directory: Path | None = None,
) -> dict[str, Any]:
    """Collect the single frozen fresh-child startup sample; never run IPOPT."""

    config = _read_config(config_path)
    _assert_startup_calibration_only(config)
    contract = config["startup_calibration"]
    output_root = Path(contract["output_directory"])
    log_root = Path(contract["logging_directory"])
    frozen_launcher = Path(contract["launcher_directory"])
    if launcher_directory is None:
        if frozen_launcher.exists():
            raise StartupCalibrationNoResumeError(
                "repair-010 direct calibration found existing launcher state"
            )
    else:
        _verify_startup_calibration_launcher_authorization(
            launcher_directory=launcher_directory,
            config_path=config_path,
            config=config,
        )
    if output_root.exists() or log_root.exists():
        raise FileExistsError(
            "repair-010 startup calibration already has evidence; retry/resume forbidden"
        )
    source_audit = audit_configured_predecessor_frontier_source(config)
    candidate_record = _calibration_candidate_record(config)
    contract_directory = output_root / "contract"
    registration_directory = output_root / "registration"
    spawn_directory = output_root / "spawn"
    worker_result = output_root / "worker_result"
    completion_directory = output_root / "completion"
    incomplete_directory = output_root / "incomplete"
    phase_journal = log_root / "phase_journal.jsonl"
    worker_process_log = log_root / "worker_process.log"
    native_solver_log = log_root / "native" / "calibration_ipopt.log"
    binding = build_startup_calibration_binding(
        config_path=config_path,
        config=config,
        source_audit=source_audit,
        candidate_record=candidate_record,
        native_log=native_solver_log,
    )
    contract_payload = {
        "schema": "rts_gmlc_v4_repair_010_startup_calibration_preregistered_v1",
        "calibration_contract": dict(contract),
        "calibration_contract_sha256": canonical_sha256(contract),
        "binding": binding,
        "binding_sha256": canonical_sha256(binding),
        "sample_outcomes_observed_before_freeze": False,
        "joint_ac_outcomes_read_or_used": False,
        "formal_execution_authorized": False,
    }
    calibration_id = str(contract["calibration_id"])
    with ExecutionLease.acquire(
        output_root / "execution_lease",
        stage="repair010_startup_calibration",
        attempt_id=calibration_id,
    ):
        _publish_exact_artifact(
            contract_directory, "calibration_contract.json", contract_payload
        )
        register_startup_calibration(
            registration_directory,
            binding=binding,
            contract_directory=contract_directory,
            phase_journal=phase_journal,
            worker_result=worker_result,
            native_solver_log=native_solver_log,
            worker_process_log=worker_process_log,
            parent_pid=os.getpid(),
        )

        def persist_incomplete(reason: str) -> None:
            register_startup_calibration_incomplete(
                incomplete_directory,
                completion_directory=completion_directory,
                binding=binding,
                registration_directory=registration_directory,
                spawn_directory=spawn_directory,
                phase_journal=phase_journal,
                reason=reason,
            )

        def validate_result() -> dict[str, Any]:
            spawn = load_verified_startup_calibration_spawn(
                spawn_directory,
                registration_directory=registration_directory,
                expected_binding=binding,
            )
            return _load_startup_calibration_worker_result(
                worker_result,
                binding=binding,
                worker_pid=int(spawn["worker_pid"]),
                phase_journal=phase_journal,
            )

        completion = run_startup_calibration_process(
            command=_startup_calibration_worker_command(
                python_executable=Path(sys.executable),
                config_path=config_path,
                registration_directory=registration_directory,
            ),
            registration_directory=registration_directory,
            spawn_directory=spawn_directory,
            phase_journal=phase_journal,
            expected_binding=binding,
            worker_process_log=worker_process_log,
            result_validator=validate_result,
            calibration_contract=contract,
            on_incomplete=persist_incomplete,
        )
        return finalize_startup_calibration(
            completion=completion,
            completion_directory=completion_directory,
            incomplete_directory=incomplete_directory,
            binding=binding,
            registration_directory=registration_directory,
            spawn_directory=spawn_directory,
            phase_journal=phase_journal,
            worker_result=worker_result,
            calibration_contract=contract,
            persist_incomplete=persist_incomplete,
        )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG_PATH)
    parser.add_argument(
        "--stage",
        choices=(
            "prepare",
            "import-predecessor-frontier",
            "run-joint-ac",
            "joint-call-worker",
            "launch-startup-calibration",
            "calibrate-startup",
            "startup-calibration-worker",
        ),
        required=True,
    )
    parser.add_argument("--output-directory", type=Path)
    parser.add_argument("--attempt-id")
    parser.add_argument("--candidate-id")
    parser.add_argument("--initial-strategy")
    parser.add_argument("--worker-result-directory", type=Path)
    parser.add_argument("--native-solver-log", type=Path)
    parser.add_argument("--phase-journal", type=Path)
    parser.add_argument("--phase-registration-directory", type=Path)
    parser.add_argument("--call-registration-manifest-sha256")
    parser.add_argument("--phase-registration-manifest-sha256")
    parser.add_argument("--calibration-registration-directory", type=Path)
    parser.add_argument("--calibration-launcher-directory", type=Path)
    args = parser.parse_args()
    worker_values = (
        args.candidate_id,
        args.initial_strategy,
        args.worker_result_directory,
        args.native_solver_log,
        args.phase_journal,
        args.phase_registration_directory,
        args.call_registration_manifest_sha256,
        args.phase_registration_manifest_sha256,
    )
    if args.stage == "joint-call-worker" and (
        args.output_directory is None or any(value is None for value in worker_values)
    ):
        parser.error("joint-call-worker requires all bound worker arguments")
    if args.stage != "joint-call-worker" and any(
        value is not None for value in worker_values
    ):
        parser.error("joint worker arguments are only valid for joint-call-worker")
    if (
        args.stage == "startup-calibration-worker"
        and args.calibration_registration_directory is None
    ):
        parser.error(
            "startup-calibration-worker requires "
            "--calibration-registration-directory"
        )
    if (
        args.stage != "startup-calibration-worker"
        and args.calibration_registration_directory is not None
    ):
        parser.error(
            "--calibration-registration-directory is only valid for "
            "startup-calibration-worker"
        )
    if args.stage in {"calibrate-startup", "startup-calibration-worker"} and (
        args.output_directory is not None
    ):
        parser.error("startup calibration uses only its frozen independent root")
    if args.stage == "launch-startup-calibration" and args.output_directory is not None:
        parser.error("startup calibration launcher uses only frozen independent roots")
    if (
        args.stage != "calibrate-startup"
        and args.calibration_launcher_directory is not None
    ):
        parser.error(
            "--calibration-launcher-directory is only valid for calibrate-startup"
        )
    if args.stage != "run-joint-ac" and args.attempt_id is not None:
        parser.error("--attempt-id is only valid for run-joint-ac")
    if args.stage == "prepare":
        result = prepare_preregistration(
            args.config, output_directory=args.output_directory
        )
    elif args.stage == "import-predecessor-frontier":
        result = import_predecessor_frontier(
            args.config, output_directory=args.output_directory
        )
    elif args.stage == "run-joint-ac":
        result = run_joint_ac(
            args.config,
            output_directory=args.output_directory,
            attempt_id=args.attempt_id,
        )
    elif args.stage == "launch-startup-calibration":
        result = launch_startup_calibration(args.config)
    elif args.stage == "calibrate-startup":
        result = run_startup_calibration(
            args.config, launcher_directory=args.calibration_launcher_directory
        )
    elif args.stage == "startup-calibration-worker":
        result = run_startup_calibration_worker(
            args.config,
            registration_directory=args.calibration_registration_directory,
        )
    else:
        result = run_joint_call_worker(
            args.config,
            output_directory=args.output_directory,
            candidate_id=args.candidate_id,
            initial_strategy=args.initial_strategy,
            result_directory=args.worker_result_directory,
            native_solver_log=args.native_solver_log,
            phase_journal=args.phase_journal,
            phase_registration_directory=args.phase_registration_directory,
            call_registration_manifest_sha256=(args.call_registration_manifest_sha256),
            phase_registration_manifest_sha256=(
                args.phase_registration_manifest_sha256
            ),
        )
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()


__all__ = [
    "DEFAULT_CONFIG_PATH",
    "IsolatedWorkerCompletion",
    "IsolatedWorkerIncompleteError",
    "SuccessorNotReadyError",
    "StartupCalibrationCompletion",
    "StartupCalibrationCompletionCommitIndeterminateError",
    "StartupCalibrationIncompleteError",
    "StartupCalibrationLauncherFailedError",
    "StartupCalibrationLauncherPersistenceError",
    "StartupCalibrationNoResumeError",
    "StartupCalibrationPersistenceError",
    "_assert_successor_ready",
    "_joint_worker_command",
    "_read_config",
    "build_worker_binding",
    "build_startup_calibration_binding",
    "derive_startup_limit_seconds",
    "execute_phase_instrumented_worker",
    "finalize_startup_calibration",
    "launch_startup_calibration",
    "load_verified_startup_calibration_completion",
    "prepare_preregistration",
    "register_phase_worker_call",
    "run_isolated_worker_process",
    "run_startup_calibration",
    "run_startup_calibration_process",
    "run_startup_calibration_launcher_process",
    "run_startup_calibration_worker",
    "run_joint_ac",
    "run_joint_call_worker",
]
