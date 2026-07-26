"""Fail-closed proxy certificates from bracketed level-set cost oracles."""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from collections.abc import Callable
from typing import Literal, Mapping

from src.grid.rts_gmlc_exact_cg import SharedSnapshot, structured_sha256

OracleStatus = Literal["audited_feasible", "certified_above_budget", "unresolved"]
_CHECKPOINT_SCHEMA = "rts_gmlc_proxy_level_set_round_v1"


def _finite(value: object, *, label: str) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    try:
        parsed = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be numeric") from error
    if not math.isfinite(parsed):
        raise ValueError(f"{label} must be finite")
    return parsed


def _snapshot_hash(
    values: tuple[tuple[str, tuple[object, ...], float], ...],
) -> str:
    return structured_sha256(
        [
            {
                "component": component,
                "index": list(index),
                "value_float_hex": float(number).hex(),
            }
            for component, index, number in values
        ]
    )


def _validate_snapshot(snapshot: SharedSnapshot) -> None:
    if not snapshot.values:
        raise ValueError("lower witness snapshot must contain full shared values")
    if _snapshot_hash(snapshot.values) != snapshot.sha256:
        raise ValueError("shared snapshot SHA256 does not match its values")
    _finite(snapshot.reactive_proxy, label="snapshot reactive proxy")
    _finite(snapshot.operating_cost_usd, label="snapshot operating cost")


@dataclass(frozen=True)
class ProxyBracket:
    lower_bound: float
    upper_bound: float
    lower_snapshot: SharedSnapshot

    def __post_init__(self) -> None:
        lower = _finite(self.lower_bound, label="proxy lower bound")
        upper = _finite(self.upper_bound, label="proxy upper bound")
        if lower > upper:
            raise ValueError("proxy bracket lower bound exceeds upper bound")
        _validate_snapshot(self.lower_snapshot)


@dataclass(frozen=True)
class LevelOracleEvidence:
    proxy_floor: float
    active_master_bound_valid: bool
    active_master_dual_lower_bound_usd: float | None
    incumbent_snapshot: SharedSnapshot | None
    all_inactive_states_screened: bool
    final_full_state_audit_passed: bool
    residual_audit_passed: bool
    recomputed_proxy: float | None
    audited_operating_cost_usd: float | None
    active_master_globally_infeasible: bool = False
    active_master_budget_cap_usd: float | None = None
    termination: str = "completed"

    def __post_init__(self) -> None:
        _finite(self.proxy_floor, label="proxy floor")
        if self.active_master_dual_lower_bound_usd is not None:
            _finite(
                self.active_master_dual_lower_bound_usd,
                label="active-master cost lower bound",
            )
        if self.incumbent_snapshot is not None:
            _validate_snapshot(self.incumbent_snapshot)
        if self.recomputed_proxy is not None:
            _finite(self.recomputed_proxy, label="recomputed proxy")
        if self.audited_operating_cost_usd is not None:
            _finite(self.audited_operating_cost_usd, label="audited operating cost")
        if self.active_master_budget_cap_usd is not None:
            _finite(
                self.active_master_budget_cap_usd,
                label="active-master decision budget cap",
            )
        if (
            self.active_master_globally_infeasible
            and self.active_master_budget_cap_usd is None
        ):
            raise ValueError(
                "global decision-MIP infeasibility requires its budget cap"
            )


@dataclass(frozen=True)
class OracleDisposition:
    status: OracleStatus
    reason: str
    bound_only: bool


@dataclass(frozen=True)
class BracketUpdate:
    bracket: ProxyBracket
    disposition: OracleDisposition


@dataclass(frozen=True)
class BracketRunResult:
    status: Literal["accepted", "unresolved", "round_limit", "numerical_limit"]
    bracket: ProxyBracket
    certificate: dict[str, object]
    round_checkpoints: tuple[dict[str, object], ...]
    failure_reason: str | None


def classify_level_oracle(
    evidence: LevelOracleEvidence,
    *,
    effective_budget_usd: float,
    strict_separation_margin_usd: float,
) -> OracleDisposition:
    """Classify one floor without borrowing evidence from another floor."""

    budget = _finite(effective_budget_usd, label="effective budget")
    margin = _finite(strict_separation_margin_usd, label="separation margin")
    if margin < 0.0:
        raise ValueError("separation margin must be nonnegative")
    separation_threshold = budget + margin
    dual = evidence.active_master_dual_lower_bound_usd
    bound_separated = bool(
        evidence.active_master_bound_valid
        and dual is not None
        and float(dual) > separation_threshold
    )
    decision_cap = evidence.active_master_budget_cap_usd
    decision_separated = bool(
        evidence.active_master_globally_infeasible
        and decision_cap is not None
        and float(decision_cap) >= budget
    )
    separated = bound_separated or decision_separated

    snapshot = evidence.incumbent_snapshot
    recomputed_proxy = evidence.recomputed_proxy
    audited_cost = evidence.audited_operating_cost_usd
    feasible = bool(
        snapshot is not None
        and evidence.all_inactive_states_screened
        and evidence.final_full_state_audit_passed
        and evidence.residual_audit_passed
        and recomputed_proxy is not None
        and float(recomputed_proxy) >= float(evidence.proxy_floor)
        and audited_cost is not None
        and float(audited_cost) <= budget
    )
    if separated and feasible:
        raise RuntimeError(
            "level oracle returned inconsistent feasible and separating evidence"
        )
    if separated:
        return OracleDisposition(
            status="certified_above_budget",
            reason=(
                "active_budget_capped_decision_mip_globally_infeasible"
                if decision_separated
                else "active_master_cost_lower_bound_strictly_exceeds_budget"
            ),
            bound_only=snapshot is None,
        )
    if feasible:
        return OracleDisposition(
            status="audited_feasible",
            reason="full_state_audited_cost_feasible_witness",
            bound_only=False,
        )
    return OracleDisposition(
        status="unresolved",
        reason=(
            "strict_cost_separation_not_proven"
            if snapshot is None
            else "incumbent_not_fully_screened_and_audited"
        ),
        bound_only=snapshot is None,
    )


def apply_level_oracle(
    bracket: ProxyBracket,
    evidence: LevelOracleEvidence,
    *,
    effective_budget_usd: float,
    strict_separation_margin_usd: float,
    expected_proxy_floor: float | None = None,
) -> BracketUpdate:
    floor = float(evidence.proxy_floor)
    if expected_proxy_floor is not None and floor != float(expected_proxy_floor):
        raise ValueError("level-oracle evidence is floor-specific")
    if not bracket.lower_bound < floor < bracket.upper_bound:
        raise ValueError("level-oracle floor must be strictly inside the bracket")
    disposition = classify_level_oracle(
        evidence,
        effective_budget_usd=effective_budget_usd,
        strict_separation_margin_usd=strict_separation_margin_usd,
    )
    if disposition.status == "certified_above_budget":
        updated = ProxyBracket(
            bracket.lower_bound,
            floor,
            bracket.lower_snapshot,
        )
    elif disposition.status == "audited_feasible":
        assert evidence.incumbent_snapshot is not None
        assert evidence.recomputed_proxy is not None
        new_lower = max(bracket.lower_bound, float(evidence.recomputed_proxy))
        if new_lower > bracket.upper_bound:
            raise RuntimeError(
                "audited proxy witness lies above the certified upper bound"
            )
        updated = ProxyBracket(
            new_lower,
            bracket.upper_bound,
            evidence.incumbent_snapshot,
        )
    else:
        updated = bracket
    return BracketUpdate(updated, disposition)


def midpoint_floor(bracket: ProxyBracket) -> float | None:
    midpoint = bracket.lower_bound + (bracket.upper_bound - bracket.lower_bound) / 2.0
    if midpoint <= bracket.lower_bound:
        midpoint = math.nextafter(bracket.lower_bound, bracket.upper_bound)
    if midpoint >= bracket.upper_bound:
        return None
    return midpoint


def acceptance_certificate(
    bracket: ProxyBracket,
    *,
    target_relative_gap: float,
    maximum_absolute_gap: float,
    maximum_relative_gap: float,
) -> dict[str, object]:
    target = _finite(target_relative_gap, label="target relative gap")
    maximum_absolute = _finite(maximum_absolute_gap, label="maximum absolute gap")
    maximum_relative = _finite(maximum_relative_gap, label="maximum relative gap")
    if min(target, maximum_absolute, maximum_relative) < 0.0:
        raise ValueError("gap thresholds must be nonnegative")
    absolute_gap = bracket.upper_bound - bracket.lower_bound
    guarded_upper = math.nextafter(bracket.upper_bound, math.inf)
    guarded_lower = math.nextafter(bracket.lower_bound, -math.inf)
    guarded_gap = guarded_upper - guarded_lower
    denominator = max(abs(bracket.lower_bound), 1.0e-12)
    guarded_denominator = math.nextafter(denominator, 0.0)
    guarded_relative = guarded_gap / guarded_denominator
    relative_gap = absolute_gap / denominator
    absolute_passed = guarded_gap <= maximum_absolute
    relative_passed = guarded_relative <= maximum_relative
    target_attained = guarded_relative <= target
    return {
        "schema": "rts_gmlc_proxy_level_set_certificate_v1",
        "valid": True,
        "lower_bound": bracket.lower_bound,
        "upper_bound": bracket.upper_bound,
        "absolute_gap": absolute_gap,
        "relative_gap_to_feasible_incumbent": relative_gap,
        "guarded_absolute_gap": guarded_gap,
        "guarded_relative_gap_to_feasible_incumbent": guarded_relative,
        "target_relative_gap_to_feasible_incumbent": target,
        "target_attained": target_attained,
        "maximum_accepted_absolute_gap": maximum_absolute,
        "maximum_accepted_relative_gap_to_feasible_incumbent": maximum_relative,
        "absolute_acceptance_passed": absolute_passed,
        "relative_acceptance_passed": relative_passed,
        "maximum_acceptance_passed": absolute_passed and relative_passed,
        "boundary_guard": "outward_one_ulp_on_each_interval_endpoint",
    }


def _snapshot_payload(snapshot: SharedSnapshot) -> dict[str, object]:
    return {
        "values": [
            {
                "component": component,
                "index": list(index),
                "value": number,
            }
            for component, index, number in snapshot.values
        ],
        "sha256": snapshot.sha256,
        "reactive_proxy": snapshot.reactive_proxy,
        "operating_cost_usd": snapshot.operating_cost_usd,
    }


def _snapshot_from_payload(payload: Mapping[str, object]) -> SharedSnapshot:
    raw_values = payload.get("values")
    if not isinstance(raw_values, list):
        raise RuntimeError("checkpoint snapshot values are missing")
    values = []
    for item in raw_values:
        if not isinstance(item, Mapping):
            raise RuntimeError("checkpoint snapshot value drifted")
        index = item.get("index")
        if not isinstance(index, list):
            raise RuntimeError("checkpoint snapshot index drifted")
        values.append(
            (
                str(item.get("component")),
                tuple(index),
                _finite(item.get("value"), label="checkpoint snapshot value"),
            )
        )
    snapshot = SharedSnapshot(
        values=tuple(values),
        sha256=str(payload.get("sha256")),
        reactive_proxy=_finite(
            payload.get("reactive_proxy"), label="checkpoint snapshot proxy"
        ),
        operating_cost_usd=_finite(
            payload.get("operating_cost_usd"), label="checkpoint snapshot cost"
        ),
    )
    try:
        _validate_snapshot(snapshot)
    except ValueError as error:
        raise RuntimeError(str(error)) from error
    return snapshot


def _bracket_payload(bracket: ProxyBracket) -> dict[str, object]:
    return {
        "lower_bound": bracket.lower_bound,
        "upper_bound": bracket.upper_bound,
        "lower_snapshot": _snapshot_payload(bracket.lower_snapshot),
    }


def _bracket_from_payload(payload: Mapping[str, object]) -> ProxyBracket:
    snapshot = payload.get("lower_snapshot")
    if not isinstance(snapshot, Mapping):
        raise RuntimeError("checkpoint lower witness is missing")
    return ProxyBracket(
        _finite(payload.get("lower_bound"), label="checkpoint lower bound"),
        _finite(payload.get("upper_bound"), label="checkpoint upper bound"),
        _snapshot_from_payload(snapshot),
    )


def build_round_checkpoint(
    *,
    candidate_id: str,
    candidate_ordinal: int,
    round_ordinal: int,
    input_contract_sha256: str,
    predecessor_manifest_sha256: str,
    bracket_before: ProxyBracket,
    evidence: LevelOracleEvidence,
    update: BracketUpdate,
) -> dict[str, object]:
    if candidate_ordinal < 1 or round_ordinal < 1:
        raise ValueError("candidate and round ordinals must be positive")
    if not candidate_id or not candidate_id.replace("_", "").isalnum():
        raise ValueError("invalid candidate ID")
    if len(input_contract_sha256) != 64 or len(predecessor_manifest_sha256) != 64:
        raise ValueError("checkpoint contracts require SHA256 identities")
    if (
        evidence.proxy_floor <= bracket_before.lower_bound
        or evidence.proxy_floor >= bracket_before.upper_bound
    ):
        raise ValueError("checkpoint floor is outside bracket_before")
    return {
        "schema": _CHECKPOINT_SCHEMA,
        "candidate_id": candidate_id,
        "candidate_ordinal": candidate_ordinal,
        "round_ordinal": round_ordinal,
        "input_contract_sha256": input_contract_sha256,
        "predecessor_manifest_sha256": predecessor_manifest_sha256,
        "bracket_before": _bracket_payload(bracket_before),
        "proxy_floor": evidence.proxy_floor,
        "oracle_evidence": {
            **asdict(evidence),
            "incumbent_snapshot": (
                _snapshot_payload(evidence.incumbent_snapshot)
                if evidence.incumbent_snapshot is not None
                else None
            ),
        },
        "disposition": asdict(update.disposition),
        "bracket_after": _bracket_payload(update.bracket),
    }


def _json_bytes(payload: object) -> bytes:
    return (
        json.dumps(
            payload, allow_nan=False, ensure_ascii=True, indent=2, sort_keys=True
        )
        + "\n"
    ).encode("utf-8")


def _round_path(root: Path, payload: Mapping[str, object]) -> Path:
    return (
        root
        / f"{int(payload['candidate_ordinal']):02d}_{payload['candidate_id']}"
        / "level_set_rounds"
        / f"{int(payload['round_ordinal']):02d}"
    )


def publish_round_checkpoint(root: Path, payload: Mapping[str, object]) -> Path:
    target = _round_path(root, payload)
    encoded = _json_bytes(payload)
    digest = hashlib.sha256(encoded).hexdigest()
    manifest = f"{digest}  round.json\n".encode("ascii")
    if target.exists():
        if (target / "round.json").read_bytes() != encoded or (
            target / "SHA256SUMS"
        ).read_bytes() != manifest:
            raise RuntimeError("existing level-set round checkpoint drifted")
        return target
    target.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(
        tempfile.mkdtemp(dir=target.parent, prefix=f".{target.name}.processing-")
    )
    try:
        (staging / "round.json").write_bytes(encoded)
        (staging / "SHA256SUMS").write_bytes(manifest)
        staging.rename(target)
    finally:
        if staging.exists():
            shutil.rmtree(staging)
    return target


def _validate_round_payload(
    payload: Mapping[str, object],
    *,
    candidate_id: str,
    candidate_ordinal: int,
    round_ordinal: int,
    input_contract_sha256: str,
    predecessor_manifest_sha256: str,
    previous_after: ProxyBracket | None,
) -> ProxyBracket:
    if (
        payload.get("schema") != _CHECKPOINT_SCHEMA
        or payload.get("candidate_id") != candidate_id
        or payload.get("candidate_ordinal") != candidate_ordinal
        or payload.get("round_ordinal") != round_ordinal
        or payload.get("input_contract_sha256") != input_contract_sha256
        or payload.get("predecessor_manifest_sha256") != predecessor_manifest_sha256
    ):
        raise RuntimeError("level-set round checkpoint identity drifted")
    before_payload = payload.get("bracket_before")
    after_payload = payload.get("bracket_after")
    if not isinstance(before_payload, Mapping) or not isinstance(
        after_payload, Mapping
    ):
        raise RuntimeError("level-set round checkpoint bracket drifted")
    before = _bracket_from_payload(before_payload)
    after = _bracket_from_payload(after_payload)
    if previous_after is not None and before != previous_after:
        raise RuntimeError("level-set round checkpoint chain drifted")
    floor = _finite(payload.get("proxy_floor"), label="checkpoint proxy floor")
    if not before.lower_bound < floor < before.upper_bound:
        raise RuntimeError("level-set round checkpoint floor drifted")
    if after.lower_bound < before.lower_bound or after.upper_bound > before.upper_bound:
        raise RuntimeError("level-set round checkpoint widened its bracket")
    return after


def load_contiguous_round_checkpoints(
    root: Path,
    *,
    candidate_id: str,
    candidate_ordinal: int,
    input_contract_sha256: str,
    predecessor_manifest_sha256: str,
) -> tuple[dict[str, object], ...]:
    rounds_root = root / f"{candidate_ordinal:02d}_{candidate_id}" / "level_set_rounds"
    if not rounds_root.exists():
        return ()
    directories = sorted(path for path in rounds_root.iterdir() if path.is_dir())
    ordinals = []
    for path in directories:
        try:
            ordinals.append(int(path.name))
        except ValueError as error:
            raise RuntimeError("level-set round directory identity drifted") from error
    if ordinals != list(range(1, len(ordinals) + 1)):
        raise RuntimeError("level-set round checkpoints are not contiguous")
    loaded = []
    previous_after = None
    for ordinal, directory in zip(ordinals, directories, strict=True):
        document = directory / "round.json"
        manifest = directory / "SHA256SUMS"
        if not document.is_file() or not manifest.is_file():
            raise RuntimeError("level-set round checkpoint manifest is missing")
        expected_manifest = (
            f"{hashlib.sha256(document.read_bytes()).hexdigest()}  round.json\n"
        )
        if manifest.read_text(encoding="ascii") != expected_manifest:
            raise RuntimeError("level-set round checkpoint manifest drifted")
        payload = json.loads(document.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise RuntimeError("level-set round checkpoint is not an object")
        previous_after = _validate_round_payload(
            payload,
            candidate_id=candidate_id,
            candidate_ordinal=candidate_ordinal,
            round_ordinal=ordinal,
            input_contract_sha256=input_contract_sha256,
            predecessor_manifest_sha256=predecessor_manifest_sha256,
            previous_after=previous_after,
        )
        loaded.append(payload)
    return tuple(loaded)


def run_bracketed_level_set(
    initial_bracket: ProxyBracket,
    *,
    oracle: Callable[[float, int], LevelOracleEvidence],
    effective_budget_usd: float,
    strict_separation_margin_usd: float,
    target_relative_gap: float,
    maximum_absolute_gap: float,
    maximum_relative_gap: float,
    maximum_rounds: int,
    candidate_id: str,
    candidate_ordinal: int,
    input_contract_sha256: str,
    predecessor_manifest_sha256: str,
    checkpoint_root: Path | None = None,
) -> BracketRunResult:
    """Bisect a proxy bracket; an unresolved floor stops without changing bounds."""

    if maximum_rounds < 1:
        raise ValueError("maximum_rounds must be positive")
    bracket = initial_bracket
    records: list[dict[str, object]] = []
    if checkpoint_root is not None:
        resumed = load_contiguous_round_checkpoints(
            checkpoint_root,
            candidate_id=candidate_id,
            candidate_ordinal=candidate_ordinal,
            input_contract_sha256=input_contract_sha256,
            predecessor_manifest_sha256=predecessor_manifest_sha256,
        )
        if resumed:
            first_before = resumed[0].get("bracket_before")
            last_after = resumed[-1].get("bracket_after")
            if not isinstance(first_before, Mapping) or not isinstance(
                last_after, Mapping
            ):
                raise RuntimeError("resumed level-set checkpoint bracket is missing")
            if _bracket_from_payload(first_before) != initial_bracket:
                raise RuntimeError("resumed level-set initial bracket drifted")
            bracket = _bracket_from_payload(last_after)
            records.extend(resumed)
            disposition = resumed[-1].get("disposition")
            if (
                isinstance(disposition, Mapping)
                and disposition.get("status") == "unresolved"
            ):
                certificate = acceptance_certificate(
                    bracket,
                    target_relative_gap=target_relative_gap,
                    maximum_absolute_gap=maximum_absolute_gap,
                    maximum_relative_gap=maximum_relative_gap,
                )
                return BracketRunResult(
                    "unresolved",
                    bracket,
                    certificate,
                    tuple(records),
                    str(disposition.get("reason")),
                )
    for round_ordinal in range(len(records) + 1, maximum_rounds + 1):
        certificate = acceptance_certificate(
            bracket,
            target_relative_gap=target_relative_gap,
            maximum_absolute_gap=maximum_absolute_gap,
            maximum_relative_gap=maximum_relative_gap,
        )
        if certificate["maximum_acceptance_passed"]:
            return BracketRunResult(
                "accepted", bracket, certificate, tuple(records), None
            )
        floor = midpoint_floor(bracket)
        if floor is None:
            return BracketRunResult(
                "numerical_limit",
                bracket,
                certificate,
                tuple(records),
                "no_representable_proxy_floor_inside_bracket",
            )
        evidence = oracle(floor, round_ordinal)
        update = apply_level_oracle(
            bracket,
            evidence,
            effective_budget_usd=effective_budget_usd,
            strict_separation_margin_usd=strict_separation_margin_usd,
            expected_proxy_floor=floor,
        )
        checkpoint = build_round_checkpoint(
            candidate_id=candidate_id,
            candidate_ordinal=candidate_ordinal,
            round_ordinal=round_ordinal,
            input_contract_sha256=input_contract_sha256,
            predecessor_manifest_sha256=predecessor_manifest_sha256,
            bracket_before=bracket,
            evidence=evidence,
            update=update,
        )
        if checkpoint_root is not None:
            publish_round_checkpoint(checkpoint_root, checkpoint)
        records.append(checkpoint)
        bracket = update.bracket
        if update.disposition.status == "unresolved":
            certificate = acceptance_certificate(
                bracket,
                target_relative_gap=target_relative_gap,
                maximum_absolute_gap=maximum_absolute_gap,
                maximum_relative_gap=maximum_relative_gap,
            )
            return BracketRunResult(
                "unresolved",
                bracket,
                certificate,
                tuple(records),
                update.disposition.reason,
            )
    certificate = acceptance_certificate(
        bracket,
        target_relative_gap=target_relative_gap,
        maximum_absolute_gap=maximum_absolute_gap,
        maximum_relative_gap=maximum_relative_gap,
    )
    status = "accepted" if certificate["maximum_acceptance_passed"] else "round_limit"
    return BracketRunResult(
        status,
        bracket,
        certificate,
        tuple(records),
        None if status == "accepted" else "maximum_level_set_rounds_exhausted",
    )


__all__ = [
    "BracketUpdate",
    "BracketRunResult",
    "LevelOracleEvidence",
    "OracleDisposition",
    "ProxyBracket",
    "acceptance_certificate",
    "apply_level_oracle",
    "build_round_checkpoint",
    "classify_level_oracle",
    "load_contiguous_round_checkpoints",
    "midpoint_floor",
    "publish_round_checkpoint",
    "run_bracketed_level_set",
]
