"""Frozen live-closure, accounting, and sealed-integration contract for v3."""

from __future__ import annotations

import hashlib
import importlib
import json
from collections.abc import Callable, Mapping
from pathlib import Path
from typing import Any

from experiments import rq2_public_grid_execution_dependency_closure_v2 as predecessor

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "configs/rq2_public_grid_two_block_pilot_execution_controller_successor_v3.json"
INNER = ROOT / (
    "configs/rq2_public_grid_two_block_pilot_execution_controller_successor_v3"
    ".SHA256SUMS.json"
)
OUTER = ROOT / (
    "configs/rq2_public_grid_two_block_pilot_execution_controller_successor_v3"
    ".OUTER.SHA256SUMS.json"
)
REVIEW = ROOT / "configs/rq2_public_grid_two_block_pilot_execution_controller_review_pass_v3.json"
STAGES = (
    "bootstrap_pre_controller_import",
    "worker_pre_loader",
    "worker_post_solve_pre_validator",
    "worker_post_validator_pre_write",
    "worker_post_write_pre_ack",
    "controller_post_child_pre_accept",
    "controller_post_block2_pre_publish",
    "controller_post_publish",
)


class RuntimeContractRejected(RuntimeError):
    """A frozen v3 runtime contract did not verify exactly."""


class LiveClosureDrift(RuntimeContractRejected):
    """A required stage detected dependency closure drift."""


def canonical_bytes(value: object) -> bytes:
    return predecessor.canonical_bytes(value)


def canonical_sha256(value: object) -> str:
    return predecessor.canonical_sha256(value)


def _load_config() -> dict[str, Any]:
    try:
        value = json.loads(predecessor.read_stable_bytes(CONFIG))
    except (json.JSONDecodeError, predecessor.ClosureRejected) as exc:
        raise RuntimeContractRejected("v3 config is unavailable") from exc
    if not isinstance(value, dict) or value.get("status") != (
        "execution_controller_successor_v3_review_closed"
    ):
        raise RuntimeContractRejected("v3 config identity drifted")
    return value


def _hash_bytes(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _verified_json(relative: str, expected: str, label: str) -> dict[str, Any]:
    try:
        raw = predecessor.read_stable_bytes(ROOT / relative)
        value = json.loads(raw)
    except (json.JSONDecodeError, predecessor.ClosureRejected) as exc:
        raise RuntimeContractRejected(f"{label} is unavailable") from exc
    if _hash_bytes(raw) != expected or not isinstance(value, dict):
        raise RuntimeContractRejected(f"{label} hash/schema drifted")
    return value


def verify_full_live_closure(
    root: Path,
    config: Mapping[str, Any],
    *,
    trace: Callable[[str, str], None] | None = None,
) -> tuple[str, ...]:
    """Double-read every predecessor and transitive dependency at one stage."""
    if root != ROOT or dict(config) != _load_config():
        raise RuntimeContractRejected("v3 live-closure authority drifted")
    authority = config["recursive_dependency_authority"]
    pred = config["predecessor"]
    observed: dict[str, str] = {}

    def record(relative: str, digest: str) -> None:
        previous = observed.setdefault(relative, digest)
        if previous != digest:
            raise RuntimeContractRejected(f"duplicate closure binding drifted: {relative}")
        if trace is not None:
            trace(relative, digest)

    outer_relative = OUTER.relative_to(root).as_posix()
    inner_relative = INNER.relative_to(root).as_posix()
    outer_raw = predecessor.read_stable_bytes(OUTER)
    outer_digest = _hash_bytes(outer_raw)
    try:
        own_outer = json.loads(outer_raw)
    except json.JSONDecodeError as exc:
        raise RuntimeContractRejected("v3 outer JSON malformed") from exc
    inner_raw = predecessor.read_stable_bytes(INNER)
    inner_digest = _hash_bytes(inner_raw)
    if own_outer != {
        "schema": "rq2_public_grid_two_block_pilot_execution_controller_successor_outer_v3",
        "files": {inner_relative: inner_digest},
    }:
        raise RuntimeContractRejected("v3 outer binding drifted")
    record(outer_relative, outer_digest)
    record(inner_relative, inner_digest)
    try:
        own_inner = json.loads(inner_raw)
    except json.JSONDecodeError as exc:
        raise RuntimeContractRejected("v3 inner JSON malformed") from exc
    own_files = own_inner.get("files") if isinstance(own_inner, dict) else None
    if (
        not isinstance(own_inner, dict)
        or own_inner.get("schema")
        != "rq2_public_grid_two_block_pilot_execution_controller_successor_bundle_v3"
        or not isinstance(own_files, dict)
        or len(own_files) != 7
    ):
        raise RuntimeContractRejected("v3 inner schema drifted")
    identity = config["successor_identity"]
    expected_identity = {
        identity[f"{label}_path"]: identity[f"{label}_sha256"]
        for label in ("contract", "bootstrap", "controller", "worker")
    }
    if any(own_files.get(relative) != digest for relative, digest in expected_identity.items()):
        raise RuntimeContractRejected("v3 successor identity/inner binding drifted")
    for relative, expected in own_files.items():
        if not isinstance(relative, str) or not isinstance(expected, str):
            raise RuntimeContractRejected("v3 inner member binding malformed")
        raw = predecessor.read_stable_bytes(root / relative)
        digest = _hash_bytes(raw)
        if digest != expected:
            raise RuntimeContractRejected(f"v3 member drifted: {relative}")
        record(relative, digest)
    if REVIEW.exists():
        review_raw = predecessor.read_stable_bytes(REVIEW)
        try:
            review = json.loads(review_raw)
        except json.JSONDecodeError as exc:
            raise RuntimeContractRejected("v3 review receipt JSON malformed") from exc
        validate_review_receipt_object(
            review, outer_relative=outer_relative, outer_sha256=outer_digest
        )
        record(REVIEW.relative_to(root).as_posix(), _hash_bytes(review_raw))

    outer = _verified_json(pred["outer_path"], pred["outer_sha256"], "v2 outer")
    if (
        outer.get("schema") != authority["predecessor_outer_schema"]
        or outer.get("files") != {pred["inner_path"]: pred["inner_sha256"]}
    ):
        raise RuntimeContractRejected("v2 outer object drifted")
    record(pred["outer_path"], pred["outer_sha256"])
    inner = _verified_json(pred["inner_path"], pred["inner_sha256"], "v2 inner")
    if (
        inner.get("schema") != authority["predecessor_inner_schema"]
        or inner.get("files") != authority["predecessor_exact_members"]
    ):
        raise RuntimeContractRejected("v2 inner object drifted")
    record(pred["inner_path"], pred["inner_sha256"])
    for relative, expected in authority["predecessor_exact_members"].items():
        raw = predecessor.read_stable_bytes(root / relative)
        digest = _hash_bytes(raw)
        if digest != expected:
            raise RuntimeContractRejected(f"v2 member drifted: {relative}")
        record(relative, digest)

    v2_config_relative = authority["predecessor_config_path"]
    v2_config = _verified_json(
        v2_config_relative,
        authority["predecessor_exact_members"][v2_config_relative],
        "v2 config",
    )
    try:
        predecessor.verify_dependency_closure(
            root, v2_config, trace=lambda relative, digest: record(relative, digest)
        )
    except predecessor.ClosureRejected as exc:
        raise RuntimeContractRejected("recursive predecessor closure rejected") from exc

    integration = config["sealed_actual_integration"]
    for label in ("candidate_v4", "recovery", "publication_v7"):
        relative = integration[f"{label}_path"]
        expected = integration[f"{label}_sha256"]
        raw = predecessor.read_stable_bytes(root / relative)
        digest = _hash_bytes(raw)
        if digest != expected:
            raise RuntimeContractRejected(f"sealed {label} implementation drifted")
        record(relative, digest)
    return tuple(sorted(observed))


def full_inventory_paths(root: Path, config: Mapping[str, Any]) -> tuple[str, ...]:
    return verify_full_live_closure(root, config)


class StageAwareClosureVerifier:
    """Re-run the exact full closure at every scientific/publication boundary."""

    def __init__(self, fault_stage: str | None = None) -> None:
        if fault_stage is not None and fault_stage not in STAGES:
            raise RuntimeContractRejected("unregistered live-closure stage")
        self._fault_stage = fault_stage
        self._fault_consumed = False
        self.audit: dict[str, object] = {
            "full_verifications": 0,
            "last_inventory_count": 0,
            "stages": [],
        }

    @classmethod
    def production(cls) -> StageAwareClosureVerifier:
        return cls()

    def verify(self, stage: str) -> tuple[str, ...]:
        if stage not in STAGES:
            raise RuntimeContractRejected(f"unregistered live-closure stage: {stage}")
        if self._fault_stage == stage and self._fault_consumed:
            raise LiveClosureDrift(f"replayed injected closure drift at {stage}")
        inventory = verify_full_live_closure(ROOT, _load_config())
        self.audit["full_verifications"] = int(self.audit["full_verifications"]) + 1
        self.audit["last_inventory_count"] = len(inventory)
        stages = self.audit["stages"]
        assert isinstance(stages, list)
        stages.append(stage)
        if self._fault_stage == stage:
            self._fault_consumed = True
            raise LiveClosureDrift(f"injected live closure drift at {stage}")
        return inventory


def register_test_stage_fault(stage: str) -> StageAwareClosureVerifier:
    """Registered deterministic fault seam; it never mutates a sealed file."""
    return StageAwareClosureVerifier(stage)


def _pair(value: Mapping[str, Any], label: str) -> tuple[str, str]:
    termination = value.get("termination_condition")
    status = value.get("solver_status")
    if not isinstance(termination, str) or not isinstance(status, str):
        raise RuntimeContractRejected(f"{label} termination/status pair missing")
    return termination, status


def solver_call_accounting(payload: Mapping[str, Any]) -> dict[str, int]:
    """Count only frozen, actually invoked termination/status pairs."""
    config = _load_config()["solver_call_accounting_authority"]
    baseline = payload.get("baseline_audit")
    outcomes = payload.get("outcomes")
    if not isinstance(baseline, Mapping) or not isinstance(outcomes, list) or len(outcomes) != 24:
        raise RuntimeContractRejected("solver accounting inventory malformed")
    no_event = config["baseline_not_applicable_object"]
    if dict(baseline) == no_event:
        baseline_calls = 0
    elif list(_pair(baseline, "baseline")) in config["baseline_solver_invoked_pairs"]:
        baseline_calls = 1
    else:
        raise RuntimeContractRejected("baseline termination/status pair is unregistered")

    primary_calls = 0
    confirmation_calls = 0
    for index, outcome in enumerate(outcomes):
        if not isinstance(outcome, Mapping):
            raise RuntimeContractRejected(f"hour {index} outcome malformed")
        primary = outcome.get("primary")
        certificate = outcome.get("primary_certificate")
        if not isinstance(primary, Mapping) or not isinstance(certificate, Mapping) or not certificate:
            raise RuntimeContractRejected(f"hour {index} primary evidence incomplete")
        pair = list(_pair(primary, f"hour {index} primary"))
        active = primary.get("event_id") is not None
        if active:
            if pair not in config["primary_solver_invoked_pairs"]:
                raise RuntimeContractRejected(f"hour {index} active primary pair unregistered")
            primary_calls += 1
        elif pair != config["primary_not_applicable_pair"]:
            raise RuntimeContractRejected(f"hour {index} inactive primary pair drifted")

        state = outcome.get("state")
        zero = outcome.get("zero_dc_confirmation")
        zero_certificate = outcome.get("zero_dc_confirmation_certificate")
        if state == "finite_grid_need":
            if zero is not None or zero_certificate is not None:
                raise RuntimeContractRejected(f"hour {index} finite state has zero confirmation")
        elif state == "exogenous_grid_infeasibility":
            if not active or not isinstance(zero, Mapping) or not isinstance(zero_certificate, Mapping) or not zero_certificate:
                raise RuntimeContractRejected(f"hour {index} E0 confirmation incomplete")
            if list(_pair(zero, f"hour {index} zero confirmation")) not in config[
                "zero_confirmation_solver_invoked_pairs"
            ]:
                raise RuntimeContractRejected(f"hour {index} zero confirmation pair unregistered")
            confirmation_calls += 1
        else:
            raise RuntimeContractRejected(f"hour {index} state unregistered")
    return {
        "baseline_solver_calls": baseline_calls,
        "primary_solver_calls": primary_calls,
        "zero_dc_confirmation_solver_calls": confirmation_calls,
        "solver_calls": baseline_calls + primary_calls + confirmation_calls,
    }


class SealedActualIntegration:
    """Fixed adapters around the hash-bound v4 scientific and v7 publication APIs."""

    def __init__(self, verifier: StageAwareClosureVerifier) -> None:
        verify_full_live_closure(ROOT, _load_config())
        self.verifier = verifier
        authority = _load_config()["sealed_actual_integration"]
        self.v4 = importlib.import_module(authority["candidate_v4_module"])
        self.recovery = importlib.import_module(authority["recovery_module"])
        self.v7 = importlib.import_module(authority["publication_v7_module"])
        self.verify_function_identities()

    def verify_function_identities(self) -> dict[str, object]:
        authority = _load_config()["sealed_actual_integration"]
        for name in authority["candidate_v4_functions"]:
            value = getattr(self.v4, name, None)
            if not callable(value) or getattr(value, "__module__", None) != authority["candidate_v4_module"]:
                raise RuntimeContractRejected(f"sealed candidate-v4 function drifted: {name}")
        for name in authority["candidate_v4_types"]:
            value = getattr(self.v4, name, None)
            if not isinstance(value, type) or value.__module__ != authority["candidate_v4_module"]:
                raise RuntimeContractRejected(f"sealed candidate-v4 type drifted: {name}")
        for name in authority["recovery_functions"]:
            value = getattr(self.recovery, name, None)
            if not callable(value) or getattr(value, "__module__", None) != authority["recovery_module"]:
                raise RuntimeContractRejected(f"sealed recovery function drifted: {name}")
        for name in authority["publication_v7_functions"]:
            value = getattr(self.v7, name, None)
            if not callable(value) or getattr(value, "__module__", None) != authority["publication_v7_module"]:
                raise RuntimeContractRejected(f"sealed publication-v7 function drifted: {name}")
        return {"verified": True}

    def validate_scientific_payload(
        self, payload: Mapping[str, Any], block_id: str
    ) -> dict[str, Any]:
        context = self.v4._stage_context()
        if block_id not in context["blocks"]:
            raise RuntimeContractRejected("scientific block is unregistered")
        scientific_keys = {
            "block_id",
            "split",
            "baseline_audit",
            "all_hours_resolved",
            "exogenous_grid_infeasibility_hour_count",
            "outcomes",
            "rows",
        }
        if set(payload) == scientific_keys:
            scientific = dict(payload)
            validation_context = context
        elif set(payload) == scientific_keys | {
            "schema",
            "stage_base_provenance_sha256",
        }:
            accounting_authority = _load_config()["solver_call_accounting_authority"]
            formal_path = ROOT / _load_config()["formal_protection"][
                "activated_config_path"
            ]
            formal_context = self.recovery._stage_context(formal_path)
            if (
                payload.get("schema") != "rts_gmlc_public_grid_need_block_checkpoint_v4"
                or payload.get("stage_base_provenance_sha256")
                != accounting_authority[
                    "real_gurobi_0008_stage_base_provenance_sha256"
                ]
                or block_id != "holdout_s20260822_0008"
            ):
                raise RuntimeContractRejected("formal checkpoint wrapper authority drifted")
            scientific = {key: payload[key] for key in scientific_keys}
            validation_context = formal_context
        else:
            raise RuntimeContractRejected("scientific payload wrapper schema drifted")
        validated = self.recovery._validate_scientific_payload(
            scientific,
            block_id=block_id,
            expected_block=validation_context["blocks"][block_id],
            config=validation_context["config"],
        )
        solver_call_accounting(validated)
        return validated

    def publication_config(self) -> dict[str, Any]:
        return self.v7._publication_config()

    def build_controller_receipt(self, config: Mapping[str, Any], ledger: Any) -> dict[str, object]:
        return self.v4._build_controller_receipt(config, ledger)

    def publish(
        self,
        staging: Path,
        target: Path,
        success: Path,
        terminal: Path,
        *,
        config: Mapping[str, Any],
        controller: Mapping[str, Any],
        ledger: Any,
        post_commit_test_hook: Callable[..., None] | None = None,
    ) -> dict[str, object]:
        return self.v7._publish_result(
            staging,
            target,
            success,
            terminal,
            config=config,
            controller=controller,
            ledger=ledger,
            post_commit_test_hook=post_commit_test_hook,
        )

    def load_verified_success(
        self,
        *,
        target: Path,
        success: Path,
        terminal: Path,
        config: Mapping[str, Any],
        controller: Mapping[str, Any],
        ledger: Any,
    ) -> dict[str, Any]:
        return self.v7.load_verified_success_commit(
            target=target,
            success_directory=success,
            terminal_directory=terminal,
            config=config,
            controller=controller,
            ledger=ledger,
        )


def load_sealed_actual_integration(
    verifier: StageAwareClosureVerifier,
) -> SealedActualIntegration:
    return SealedActualIntegration(verifier)


def validate_review_receipt_object(
    receipt: object, *, outer_relative: str, outer_sha256: str
) -> dict[str, Any]:
    """Validate the fixed, externally produced v3 execution-review receipt."""
    config = _load_config()
    authority = config["fixed_execution_review"]
    if not isinstance(receipt, dict) or set(receipt) != set(authority["exact_keyset"]):
        raise RuntimeContractRejected("v3 execution-review receipt schema drifted")
    predecessor_binding = {
        "outer_path": config["predecessor"]["outer_path"],
        "outer_sha256": config["predecessor"]["outer_sha256"],
        "inner_path": config["predecessor"]["inner_path"],
        "inner_sha256": config["predecessor"]["inner_sha256"],
        "escalate_path": config["predecessor"]["escalate_path"],
        "escalate_sha256": config["predecessor"]["escalate_sha256"],
    }
    if (
        receipt.get("schema") != authority["schema"]
        or receipt.get("version") != 3
        or receipt.get("reviewer_role") != "independent_sol_reviewer"
        or receipt.get("verdict") != "PASS"
        or receipt.get("reviewed_outer")
        != {"path": outer_relative, "sha256": outer_sha256}
        or receipt.get("bound_predecessor") != predecessor_binding
        or receipt.get("bound_recursive_dependency_authority")
        != config["recursive_dependency_authority"]
        or receipt.get("effect") != authority["exact_effect"]
        or not isinstance(receipt.get("reviewed_on"), str)
        or not isinstance(receipt.get("findings"), list)
    ):
        raise RuntimeContractRejected("v3 execution-review receipt binding drifted")
    return dict(receipt)
