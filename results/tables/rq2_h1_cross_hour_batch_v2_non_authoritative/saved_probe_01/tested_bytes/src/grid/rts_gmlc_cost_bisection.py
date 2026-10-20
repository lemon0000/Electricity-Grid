"""Fail-closed cost certificates from budget-capped decision MIPs."""

from __future__ import annotations

import hashlib
import json
import math
import shutil
import tempfile
from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Literal

from src.grid.rts_gmlc_exact_cg import SharedSnapshot, structured_sha256

OracleStatus = Literal["audited_feasible", "certified_infeasible_at_cap", "unresolved"]
_ROUND_SCHEMA = "rts_gmlc_cost_decision_round_v1"
_INFEASIBILITY_SCHEMA = "rts_gmlc_level_set_bound_only_early_separation_v1"
_INFEASIBILITY_SOURCE = "active_budget_capped_decision_mip_global_infeasibility"
_INFEASIBILITY_SCOPE = "no_budget_feasible_solution_at_or_above_this_proxy_floor"
_PROVEN_INFEASIBLE_TERMINATION = "TerminationCondition.provenInfeasible"


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
    if not snapshot.values or _snapshot_hash(snapshot.values) != snapshot.sha256:
        raise ValueError("cost bracket snapshot identity drifted")
    _finite(snapshot.reactive_proxy, label="snapshot reactive proxy")
    _finite(snapshot.operating_cost_usd, label="snapshot operating cost")


@dataclass(frozen=True)
class CostBracket:
    lower_bound_usd: float
    upper_bound_usd: float
    upper_snapshot: SharedSnapshot

    def __post_init__(self) -> None:
        lower = _finite(self.lower_bound_usd, label="cost lower bound")
        upper = _finite(self.upper_bound_usd, label="cost upper bound")
        if lower > upper:
            raise ValueError("cost bracket lower bound exceeds upper bound")
        _validate_snapshot(self.upper_snapshot)
        if float(self.upper_snapshot.operating_cost_usd) > upper:
            raise ValueError("cost bracket snapshot exceeds its upper bound")


@dataclass(frozen=True)
class CostOracleEvidence:
    cost_cap_usd: float
    active_master_globally_infeasible: bool
    incumbent_snapshot: SharedSnapshot | None
    all_inactive_states_screened: bool
    final_full_state_audit_passed: bool
    residual_audit_passed: bool
    audited_operating_cost_usd: float | None
    termination: str
    infeasibility_certificate_schema: str | None = None
    infeasibility_certificate_source: str | None = None
    infeasibility_claim_scope: str | None = None
    decision_budget_cap_usd: float | None = None
    cost_match_tolerance_usd: float = 0.0

    def __post_init__(self) -> None:
        _finite(self.cost_cap_usd, label="cost decision cap")
        if self.incumbent_snapshot is not None:
            _validate_snapshot(self.incumbent_snapshot)
        if self.audited_operating_cost_usd is not None:
            _finite(self.audited_operating_cost_usd, label="audited operating cost")
        if self.decision_budget_cap_usd is not None:
            _finite(self.decision_budget_cap_usd, label="decision budget cap")
        tolerance = _finite(
            self.cost_match_tolerance_usd, label="cost witness match tolerance"
        )
        if tolerance < 0.0:
            raise ValueError("cost witness match tolerance must be nonnegative")


@dataclass(frozen=True)
class CostOracleDisposition:
    status: OracleStatus
    reason: str


@dataclass(frozen=True)
class CostBracketUpdate:
    bracket: CostBracket
    disposition: CostOracleDisposition


@dataclass(frozen=True)
class CostBisectionResult:
    status: Literal["accepted", "unresolved", "round_limit", "numerical_limit"]
    bracket: CostBracket
    certificate: dict[str, object]
    round_checkpoints: tuple[dict[str, object], ...]
    failure_reason: str | None


def classify_cost_oracle(evidence: CostOracleEvidence) -> CostOracleDisposition:
    cap = float(evidence.cost_cap_usd)
    snapshot = evidence.incumbent_snapshot
    audited_cost = evidence.audited_operating_cost_usd
    tolerance = float(evidence.cost_match_tolerance_usd)
    feasible = bool(
        snapshot is not None
        and evidence.all_inactive_states_screened
        and evidence.final_full_state_audit_passed
        and evidence.residual_audit_passed
        and audited_cost is not None
        and float(audited_cost) <= cap
        and float(snapshot.operating_cost_usd) <= cap
        and abs(float(snapshot.operating_cost_usd) - float(audited_cost)) <= tolerance
    )
    if evidence.active_master_globally_infeasible and (
        snapshot is not None or audited_cost is not None
    ):
        raise RuntimeError("cost oracle returned inconsistent evidence")
    infeasible = bool(
        evidence.active_master_globally_infeasible
        and evidence.termination == _PROVEN_INFEASIBLE_TERMINATION
        and evidence.infeasibility_certificate_schema == _INFEASIBILITY_SCHEMA
        and evidence.infeasibility_certificate_source == _INFEASIBILITY_SOURCE
        and evidence.infeasibility_claim_scope == _INFEASIBILITY_SCOPE
        and evidence.decision_budget_cap_usd is not None
        and float(evidence.decision_budget_cap_usd) == cap
    )
    if infeasible:
        return CostOracleDisposition(
            "certified_infeasible_at_cap",
            "active_budget_capped_decision_mip_globally_infeasible",
        )
    if feasible:
        return CostOracleDisposition(
            "audited_feasible",
            "full_state_audited_cost_feasible_witness",
        )
    return CostOracleDisposition("unresolved", "cost_decision_oracle_unresolved")


def apply_cost_oracle(
    bracket: CostBracket,
    evidence: CostOracleEvidence,
    *,
    expected_cost_cap_usd: float | None = None,
) -> CostBracketUpdate:
    cap = float(evidence.cost_cap_usd)
    if expected_cost_cap_usd is not None and cap != float(expected_cost_cap_usd):
        raise ValueError("cost-oracle evidence is cap-specific")
    if not bracket.lower_bound_usd < cap < bracket.upper_bound_usd:
        raise ValueError("cost-oracle cap must be strictly inside the bracket")
    disposition = classify_cost_oracle(evidence)
    if disposition.status == "certified_infeasible_at_cap":
        updated = CostBracket(cap, bracket.upper_bound_usd, bracket.upper_snapshot)
    elif disposition.status == "audited_feasible":
        assert evidence.incumbent_snapshot is not None
        assert evidence.audited_operating_cost_usd is not None
        upper = min(
            bracket.upper_bound_usd,
            max(
                float(evidence.audited_operating_cost_usd),
                float(evidence.incumbent_snapshot.operating_cost_usd),
            ),
        )
        if upper < bracket.lower_bound_usd:
            raise RuntimeError(
                "audited cost witness lies below the certified lower bound"
            )
        updated = CostBracket(
            bracket.lower_bound_usd,
            upper,
            evidence.incumbent_snapshot,
        )
    else:
        updated = bracket
    return CostBracketUpdate(updated, disposition)


def midpoint_cap(bracket: CostBracket) -> float | None:
    midpoint = (
        bracket.lower_bound_usd
        + (bracket.upper_bound_usd - bracket.lower_bound_usd) / 2.0
    )
    if midpoint <= bracket.lower_bound_usd:
        midpoint = math.nextafter(bracket.lower_bound_usd, bracket.upper_bound_usd)
    if midpoint >= bracket.upper_bound_usd:
        return None
    return midpoint


def acceptance_certificate(
    bracket: CostBracket,
    *,
    target_relative_gap: float,
    maximum_relative_gap: float,
) -> dict[str, object]:
    target = _finite(target_relative_gap, label="target relative gap")
    maximum = _finite(maximum_relative_gap, label="maximum relative gap")
    if target < 0.0 or maximum < target:
        raise ValueError("cost gap thresholds drifted")
    absolute_gap = bracket.upper_bound_usd - bracket.lower_bound_usd
    guarded_upper = math.nextafter(bracket.upper_bound_usd, math.inf)
    guarded_lower = math.nextafter(bracket.lower_bound_usd, -math.inf)
    guarded_gap = guarded_upper - guarded_lower
    denominator = max(abs(bracket.upper_bound_usd), 1.0e-12)
    guarded_denominator = math.nextafter(denominator, 0.0)
    relative = absolute_gap / denominator
    guarded_relative = guarded_gap / guarded_denominator
    return {
        "schema": "rts_gmlc_cost_decision_bisection_certificate_v1",
        "valid": True,
        "lower_bound": bracket.lower_bound_usd,
        "upper_bound": bracket.upper_bound_usd,
        "absolute_gap": absolute_gap,
        "relative_gap_to_feasible_incumbent": relative,
        "guarded_absolute_gap": guarded_gap,
        "guarded_relative_gap_to_feasible_incumbent": guarded_relative,
        "target_relative_gap_to_feasible_incumbent": target,
        "target_attained": guarded_relative <= target,
        "maximum_accepted_relative_gap_to_feasible_incumbent": maximum,
        "maximum_acceptance_passed": guarded_relative <= maximum,
        "boundary_guard": "outward_one_ulp_on_each_interval_endpoint",
    }


def _snapshot_payload(snapshot: SharedSnapshot) -> dict[str, object]:
    return {
        "values": [
            {"component": component, "index": list(index), "value": number}
            for component, index, number in snapshot.values
        ],
        "sha256": snapshot.sha256,
        "reactive_proxy": snapshot.reactive_proxy,
        "operating_cost_usd": snapshot.operating_cost_usd,
    }


def _snapshot_from_payload(payload: Mapping[str, object]) -> SharedSnapshot:
    raw = payload.get("values")
    if not isinstance(raw, list):
        raise RuntimeError("cost checkpoint snapshot values are missing")
    values = []
    for item in raw:
        if not isinstance(item, Mapping) or not isinstance(item.get("index"), list):
            raise RuntimeError("cost checkpoint snapshot value drifted")
        values.append(
            (
                str(item.get("component")),
                tuple(item["index"]),
                _finite(item.get("value"), label="cost checkpoint snapshot value"),
            )
        )
    snapshot = SharedSnapshot(
        tuple(values),
        str(payload.get("sha256")),
        _finite(payload.get("reactive_proxy"), label="cost checkpoint proxy"),
        _finite(payload.get("operating_cost_usd"), label="cost checkpoint cost"),
    )
    _validate_snapshot(snapshot)
    return snapshot


def _bracket_payload(bracket: CostBracket) -> dict[str, object]:
    return {
        "lower_bound_usd": bracket.lower_bound_usd,
        "upper_bound_usd": bracket.upper_bound_usd,
        "upper_snapshot": _snapshot_payload(bracket.upper_snapshot),
    }


def _bracket_from_payload(payload: Mapping[str, object]) -> CostBracket:
    snapshot = payload.get("upper_snapshot")
    if not isinstance(snapshot, Mapping):
        raise RuntimeError("cost checkpoint upper witness is missing")
    return CostBracket(
        _finite(payload.get("lower_bound_usd"), label="cost checkpoint lower bound"),
        _finite(payload.get("upper_bound_usd"), label="cost checkpoint upper bound"),
        _snapshot_from_payload(snapshot),
    )


def _evidence_from_payload(payload: Mapping[str, object]) -> CostOracleEvidence:
    snapshot_payload = payload.get("incumbent_snapshot")
    if snapshot_payload is not None and not isinstance(snapshot_payload, Mapping):
        raise RuntimeError("cost checkpoint oracle snapshot drifted")
    return CostOracleEvidence(
        cost_cap_usd=_finite(
            payload.get("cost_cap_usd"), label="cost checkpoint oracle cap"
        ),
        active_master_globally_infeasible=bool(
            payload.get("active_master_globally_infeasible")
        ),
        incumbent_snapshot=(
            _snapshot_from_payload(snapshot_payload)
            if isinstance(snapshot_payload, Mapping)
            else None
        ),
        all_inactive_states_screened=bool(payload.get("all_inactive_states_screened")),
        final_full_state_audit_passed=bool(
            payload.get("final_full_state_audit_passed")
        ),
        residual_audit_passed=bool(payload.get("residual_audit_passed")),
        audited_operating_cost_usd=(
            _finite(
                payload.get("audited_operating_cost_usd"),
                label="cost checkpoint audited operating cost",
            )
            if payload.get("audited_operating_cost_usd") is not None
            else None
        ),
        termination=str(payload.get("termination")),
        infeasibility_certificate_schema=(
            str(payload.get("infeasibility_certificate_schema"))
            if payload.get("infeasibility_certificate_schema") is not None
            else None
        ),
        infeasibility_certificate_source=(
            str(payload.get("infeasibility_certificate_source"))
            if payload.get("infeasibility_certificate_source") is not None
            else None
        ),
        infeasibility_claim_scope=(
            str(payload.get("infeasibility_claim_scope"))
            if payload.get("infeasibility_claim_scope") is not None
            else None
        ),
        decision_budget_cap_usd=(
            _finite(
                payload.get("decision_budget_cap_usd"),
                label="cost checkpoint decision budget cap",
            )
            if payload.get("decision_budget_cap_usd") is not None
            else None
        ),
        cost_match_tolerance_usd=_finite(
            payload.get("cost_match_tolerance_usd", 0.0),
            label="cost checkpoint witness match tolerance",
        ),
    )


def build_round_checkpoint(
    *,
    candidate_id: str,
    candidate_ordinal: int,
    round_ordinal: int,
    input_contract_sha256: str,
    predecessor_manifest_sha256: str,
    bracket_before: CostBracket,
    evidence: CostOracleEvidence,
    update: CostBracketUpdate,
) -> dict[str, object]:
    if candidate_ordinal < 1 or round_ordinal < 1:
        raise ValueError("candidate and round ordinals must be positive")
    if len(input_contract_sha256) != 64 or len(predecessor_manifest_sha256) != 64:
        raise ValueError("cost round contracts require SHA256 identities")
    if not candidate_id or not candidate_id.replace("_", "").isalnum():
        raise ValueError("invalid candidate ID")
    recomputed = apply_cost_oracle(
        bracket_before,
        evidence,
        expected_cost_cap_usd=evidence.cost_cap_usd,
    )
    if update != recomputed:
        raise RuntimeError("cost round update does not match its oracle evidence")
    return {
        "schema": _ROUND_SCHEMA,
        "candidate_id": candidate_id,
        "candidate_ordinal": candidate_ordinal,
        "round_ordinal": round_ordinal,
        "input_contract_sha256": input_contract_sha256,
        "predecessor_manifest_sha256": predecessor_manifest_sha256,
        "bracket_before": _bracket_payload(bracket_before),
        "cost_cap_usd": evidence.cost_cap_usd,
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


def publish_round_checkpoint(root: Path, payload: Mapping[str, object]) -> Path:
    target = (
        root
        / f"{int(payload['candidate_ordinal']):02d}_{payload['candidate_id']}"
        / "cost_decision_rounds"
        / f"{int(payload['round_ordinal']):02d}"
    )
    encoded = _json_bytes(payload)
    manifest = f"{hashlib.sha256(encoded).hexdigest()}  round.json\n".encode("ascii")
    if target.exists():
        if (target / "round.json").read_bytes() != encoded or (
            target / "SHA256SUMS"
        ).read_bytes() != manifest:
            raise RuntimeError("existing cost round checkpoint drifted")
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


def load_contiguous_round_checkpoints(
    root: Path,
    *,
    candidate_id: str,
    candidate_ordinal: int,
    input_contract_sha256: str,
    predecessor_manifest_sha256: str,
) -> tuple[dict[str, object], ...]:
    rounds_root = (
        root / f"{candidate_ordinal:02d}_{candidate_id}" / "cost_decision_rounds"
    )
    if not rounds_root.exists():
        return ()
    directories = sorted(path for path in rounds_root.iterdir() if path.is_dir())
    if [path.name for path in directories] != [
        f"{ordinal:02d}" for ordinal in range(1, len(directories) + 1)
    ]:
        raise RuntimeError("cost round checkpoints are not contiguous")
    loaded = []
    previous_after: CostBracket | None = None
    for ordinal, directory in enumerate(directories, 1):
        document = directory / "round.json"
        manifest = directory / "SHA256SUMS"
        if not document.is_file() or not manifest.is_file():
            raise RuntimeError("cost round checkpoint manifest is missing")
        if manifest.read_text(encoding="ascii") != (
            f"{hashlib.sha256(document.read_bytes()).hexdigest()}  round.json\n"
        ):
            raise RuntimeError("cost round checkpoint manifest drifted")
        payload = json.loads(document.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise RuntimeError("cost round checkpoint is not an object")
        if (
            payload.get("schema") != _ROUND_SCHEMA
            or payload.get("candidate_id") != candidate_id
            or payload.get("candidate_ordinal") != candidate_ordinal
            or payload.get("round_ordinal") != ordinal
            or payload.get("input_contract_sha256") != input_contract_sha256
            or payload.get("predecessor_manifest_sha256") != predecessor_manifest_sha256
        ):
            raise RuntimeError("cost round checkpoint identity drifted")
        before_payload = payload.get("bracket_before")
        after_payload = payload.get("bracket_after")
        evidence_payload = payload.get("oracle_evidence")
        disposition_payload = payload.get("disposition")
        if (
            not isinstance(before_payload, Mapping)
            or not isinstance(after_payload, Mapping)
            or not isinstance(evidence_payload, Mapping)
            or not isinstance(disposition_payload, Mapping)
        ):
            raise RuntimeError("cost round checkpoint payload drifted")
        before = _bracket_from_payload(before_payload)
        after = _bracket_from_payload(after_payload)
        if previous_after is not None and before != previous_after:
            raise RuntimeError("cost round checkpoint chain drifted")
        cap = _finite(payload.get("cost_cap_usd"), label="cost checkpoint cap")
        expected_cap = midpoint_cap(before)
        if expected_cap is None or cap != expected_cap:
            raise RuntimeError("cost round checkpoint cap drifted")
        evidence = _evidence_from_payload(evidence_payload)
        if float(evidence.cost_cap_usd) != cap:
            raise RuntimeError("cost round checkpoint evidence cap drifted")
        recomputed = apply_cost_oracle(
            before,
            evidence,
            expected_cost_cap_usd=cap,
        )
        if disposition_payload != asdict(recomputed.disposition):
            raise RuntimeError("cost round checkpoint disposition drifted")
        if after != recomputed.bracket:
            raise RuntimeError("cost round checkpoint recomputed update drifted")
        previous_after = after
        loaded.append(payload)
    return tuple(loaded)


def run_bracketed_cost_bisection(
    initial_bracket: CostBracket,
    *,
    oracle: Callable[[float, int], CostOracleEvidence],
    target_relative_gap: float,
    maximum_relative_gap: float,
    maximum_rounds: int,
    candidate_id: str = "synthetic",
    candidate_ordinal: int = 1,
    input_contract_sha256: str = "0" * 64,
    predecessor_manifest_sha256: str = "0" * 64,
    checkpoint_root: Path | None = None,
) -> CostBisectionResult:
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
            if _bracket_from_payload(resumed[0]["bracket_before"]) != initial_bracket:
                raise RuntimeError("resumed cost initial bracket drifted")
            bracket = _bracket_from_payload(resumed[-1]["bracket_after"])
            records.extend(resumed)
            disposition = resumed[-1].get("disposition")
            if (
                isinstance(disposition, Mapping)
                and disposition.get("status") == "unresolved"
            ):
                return CostBisectionResult(
                    "unresolved",
                    bracket,
                    acceptance_certificate(
                        bracket,
                        target_relative_gap=target_relative_gap,
                        maximum_relative_gap=maximum_relative_gap,
                    ),
                    tuple(records),
                    str(disposition.get("reason")),
                )
    for round_ordinal in range(len(records) + 1, maximum_rounds + 1):
        certificate = acceptance_certificate(
            bracket,
            target_relative_gap=target_relative_gap,
            maximum_relative_gap=maximum_relative_gap,
        )
        if certificate["maximum_acceptance_passed"]:
            return CostBisectionResult(
                "accepted", bracket, certificate, tuple(records), None
            )
        cap = midpoint_cap(bracket)
        if cap is None:
            return CostBisectionResult(
                "numerical_limit",
                bracket,
                certificate,
                tuple(records),
                "no_representable_cost_cap_inside_bracket",
            )
        evidence = oracle(cap, round_ordinal)
        update = apply_cost_oracle(bracket, evidence, expected_cost_cap_usd=cap)
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
            return CostBisectionResult(
                "unresolved",
                bracket,
                acceptance_certificate(
                    bracket,
                    target_relative_gap=target_relative_gap,
                    maximum_relative_gap=maximum_relative_gap,
                ),
                tuple(records),
                update.disposition.reason,
            )
    certificate = acceptance_certificate(
        bracket,
        target_relative_gap=target_relative_gap,
        maximum_relative_gap=maximum_relative_gap,
    )
    status = "accepted" if certificate["maximum_acceptance_passed"] else "round_limit"
    return CostBisectionResult(
        status,
        bracket,
        certificate,
        tuple(records),
        None if status == "accepted" else "maximum_cost_bisection_rounds_exhausted",
    )


__all__ = [
    "CostBisectionResult",
    "CostBracket",
    "CostBracketUpdate",
    "CostOracleDisposition",
    "CostOracleEvidence",
    "acceptance_certificate",
    "apply_cost_oracle",
    "build_round_checkpoint",
    "classify_cost_oracle",
    "load_contiguous_round_checkpoints",
    "midpoint_cap",
    "publish_round_checkpoint",
    "run_bracketed_cost_bisection",
]
