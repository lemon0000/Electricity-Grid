"""Strict input contracts for the full M6 chronological evidence gate."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timedelta
from math import isfinite
from pathlib import Path
from typing import Iterable


BUSINESS_CHRONOLOGY_SCHEMA = "m6_business_chronology_v1"
INCIDENT_CHRONOLOGY_SCHEMA = "m6_incident_chronology_v1"
RECOVERY_PARAMETERS_SCHEMA = "m6_recovery_parameters_v1"

_BUSINESS_FIELDS = (
    "timestamp",
    "period",
    "requested_demand_mw",
    "flexible_demand_mw",
    "recoverable_flexible_mw",
    "physical_maximum_demand_mw",
    "recovery_headroom_mw",
)
_INCIDENT_FIELDS = (
    "event_id",
    "start_timestamp",
    "end_timestamp",
    "kind",
    "element_id",
    "frequency_semantics",
    "frequency_value",
)
_SOURCE_KINDS = {
    "observed",
    "published_benchmark",
    "derived_benchmark",
    "synthetic_sensitivity",
}
_FREQUENCY_SEMANTICS = {
    "observed_occurrence",
    "sampled_from_published_rate",
    "scenario_weight",
    "deterministic_stress_no_frequency",
}


@dataclass(frozen=True)
class EvidenceSource:
    dataset_id: str
    source_kind: str
    citation: str
    version: str
    sha256: str


@dataclass(frozen=True)
class RecoveryParameters:
    maximum_recovery_power_mw: float
    recovery_efficiency: float
    source: EvidenceSource
    source_artifact_path: Path


@dataclass(frozen=True)
class BusinessChronologyPoint:
    timestamp: datetime
    period: str
    requested_demand_mw: float
    flexible_demand_mw: float
    recoverable_flexible_mw: float
    physical_maximum_demand_mw: float
    recovery_headroom_mw: float


@dataclass(frozen=True)
class BusinessChronology:
    schema: str
    time_step_hours: float
    points: tuple[BusinessChronologyPoint, ...]
    workload_source: EvidenceSource
    recovery: RecoveryParameters


@dataclass(frozen=True)
class GridIncident:
    event_id: str
    start_timestamp: datetime
    end_timestamp: datetime
    kind: str
    element_id: str
    frequency_semantics: str
    frequency_value: float


@dataclass(frozen=True)
class IncidentChronology:
    schema: str
    incidents: tuple[GridIncident, ...]
    source: EvidenceSource


def _finite_number(value: object, label: str, *, minimum: float = 0.0) -> float:
    if isinstance(value, bool):
        raise ValueError(f"{label} must be numeric")
    try:
        number = float(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be numeric") from error
    if not isfinite(number) or number < minimum:
        raise ValueError(f"{label} must be finite and at least {minimum}")
    return number


def _positive_number(value: object, label: str) -> float:
    number = _finite_number(value, label)
    if number <= 0.0:
        raise ValueError(f"{label} must be positive")
    return number


def _timestamp(value: str, label: str) -> datetime:
    try:
        timestamp = datetime.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise ValueError(f"{label} must be an ISO-8601 timestamp") from error
    if timestamp.utcoffset() is None:
        raise ValueError(f"{label} must include a UTC offset")
    return timestamp


def _validate_source_metadata(source: EvidenceSource) -> None:
    if not source.dataset_id or not source.citation or not source.version:
        raise ValueError("Evidence source id, citation, and version must be explicit")
    if source.source_kind not in _SOURCE_KINDS:
        raise ValueError(f"Unsupported evidence source kind: {source.source_kind}")
    if not isinstance(source.sha256, str) or len(source.sha256) != 64:
        raise ValueError("Evidence source SHA-256 must contain 64 hex characters")
    try:
        int(source.sha256, 16)
    except ValueError as error:
        raise ValueError("Evidence source SHA-256 must be hexadecimal") from error


def _validate_source(source: EvidenceSource, path: Path) -> None:
    _validate_source_metadata(source)
    actual = hashlib.sha256(path.read_bytes()).hexdigest()
    if actual != source.sha256.lower():
        raise ValueError(f"Evidence source SHA-256 does not match {path}")


def _read_exact_csv(
    path: Path,
    fields: tuple[str, ...],
    *,
    allow_empty: bool = False,
) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != list(fields):
            raise ValueError(
                f"{path} columns must exactly equal {list(fields)}; "
                f"received={reader.fieldnames}"
            )
        rows = list(reader)
    if any(None in row or any(value is None for value in row.values()) for row in rows):
        raise ValueError(f"{path} contains a row with missing or surplus cells")
    if not rows and not allow_empty:
        raise ValueError(f"{path} must contain at least one data row")
    return rows


def _validate_recovery(recovery: RecoveryParameters) -> None:
    _finite_number(
        recovery.maximum_recovery_power_mw,
        "maximum_recovery_power_mw",
    )
    efficiency = _positive_number(recovery.recovery_efficiency, "recovery_efficiency")
    if efficiency > 1.0:
        raise ValueError("recovery_efficiency cannot exceed 1")
    _validate_source(recovery.source, recovery.source_artifact_path)
    def reject_duplicates(pairs):
        payload = {}
        for key, value in pairs:
            if key in payload:
                raise ValueError(f"Duplicate recovery parameter key: {key}")
            payload[key] = value
        return payload

    def reject_constant(value):
        raise ValueError(f"Non-finite recovery parameter: {value}")

    try:
        payload = json.loads(
            recovery.source_artifact_path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_duplicates,
            parse_constant=reject_constant,
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as error:
        raise ValueError("Recovery parameter artifact must be valid UTF-8 JSON") from error
    expected_keys = {
        "schema",
        "maximum_recovery_power_mw",
        "recovery_efficiency",
    }
    if not isinstance(payload, dict) or set(payload) != expected_keys:
        raise ValueError("Recovery parameter artifact has an invalid schema")
    if payload["schema"] != RECOVERY_PARAMETERS_SCHEMA:
        raise ValueError("Recovery parameter artifact has an unknown schema version")
    artifact_power = _finite_number(
        payload["maximum_recovery_power_mw"],
        "artifact maximum_recovery_power_mw",
    )
    artifact_efficiency = _positive_number(
        payload["recovery_efficiency"],
        "artifact recovery_efficiency",
    )
    if (
        artifact_power != float(recovery.maximum_recovery_power_mw)
        or artifact_efficiency != float(recovery.recovery_efficiency)
    ):
        raise ValueError("Recovery parameters do not match the locked source artifact")


def load_business_chronology_csv(
    path: Path,
    *,
    time_step_hours: float,
    workload_source: EvidenceSource,
    recovery: RecoveryParameters,
) -> BusinessChronology:
    """Load a source-locked business chronology and fail closed on gaps."""

    time_step_hours = _positive_number(time_step_hours, "time_step_hours")
    _validate_source(workload_source, path)
    _validate_recovery(recovery)
    rows = _read_exact_csv(path, _BUSINESS_FIELDS)
    points = []
    for index, row in enumerate(rows):
        label = f"business row {index}"
        period = row["period"]
        if not period:
            raise ValueError(f"{label} period must be nonempty")
        point = BusinessChronologyPoint(
            timestamp=_timestamp(row["timestamp"], f"{label} timestamp"),
            period=period,
            requested_demand_mw=_finite_number(
                row["requested_demand_mw"], f"{label} requested_demand_mw"
            ),
            flexible_demand_mw=_finite_number(
                row["flexible_demand_mw"], f"{label} flexible_demand_mw"
            ),
            recoverable_flexible_mw=_finite_number(
                row["recoverable_flexible_mw"],
                f"{label} recoverable_flexible_mw",
            ),
            physical_maximum_demand_mw=_finite_number(
                row["physical_maximum_demand_mw"],
                f"{label} physical_maximum_demand_mw",
            ),
            recovery_headroom_mw=_finite_number(
                row["recovery_headroom_mw"], f"{label} recovery_headroom_mw"
            ),
        )
        if point.flexible_demand_mw > point.requested_demand_mw:
            raise ValueError(f"{label} flexible demand exceeds requested demand")
        if point.recoverable_flexible_mw > point.flexible_demand_mw:
            raise ValueError(f"{label} recoverable demand exceeds flexible demand")
        if point.requested_demand_mw > point.physical_maximum_demand_mw:
            raise ValueError(f"{label} requested demand exceeds physical maximum")
        if point.recovery_headroom_mw > (
            point.physical_maximum_demand_mw - point.requested_demand_mw
        ):
            raise ValueError(f"{label} recovery headroom exceeds physical headroom")
        points.append(point)

    timestamps = tuple(point.timestamp for point in points)
    if len(set(timestamps)) != len(timestamps):
        raise ValueError("Business chronology contains duplicate timestamps")
    expected_step = timedelta(hours=time_step_hours)
    if any(later - earlier != expected_step for earlier, later in zip(timestamps, timestamps[1:])):
        raise ValueError("Business chronology timestamps must be continuous")
    periods = tuple(point.period for point in points)
    for period in dict.fromkeys(periods):
        indices = [index for index, candidate in enumerate(periods) if candidate == period]
        if indices != list(range(indices[0], indices[-1] + 1)):
            raise ValueError("Each business period must form one contiguous block")

    return BusinessChronology(
        schema=BUSINESS_CHRONOLOGY_SCHEMA,
        time_step_hours=time_step_hours,
        points=tuple(points),
        workload_source=workload_source,
        recovery=recovery,
    )


def load_incident_chronology_csv(
    path: Path,
    *,
    source: EvidenceSource,
) -> IncidentChronology:
    """Load incidents without assigning probability to security-state rows."""

    _validate_source(source, path)
    rows = _read_exact_csv(path, _INCIDENT_FIELDS, allow_empty=True)
    incidents = []
    for index, row in enumerate(rows):
        label = f"incident row {index}"
        event_id = row["event_id"]
        element_id = row["element_id"]
        if not event_id or not element_id:
            raise ValueError(f"{label} event_id and element_id must be nonempty")
        kind = row["kind"]
        if kind not in {"branch", "generator"}:
            raise ValueError(f"{label} kind must be branch or generator")
        semantics = row["frequency_semantics"]
        if semantics not in _FREQUENCY_SEMANTICS:
            raise ValueError(
                f"{label} has unsupported frequency semantics; security-state "
                "enumeration cannot be used as event frequency"
            )
        allowed_source_kinds = {
            "observed_occurrence": {"observed"},
            "sampled_from_published_rate": {"derived_benchmark"},
            "scenario_weight": {
                "published_benchmark",
                "derived_benchmark",
                "synthetic_sensitivity",
            },
            "deterministic_stress_no_frequency": {"synthetic_sensitivity"},
        }[semantics]
        if source.source_kind not in allowed_source_kinds:
            raise ValueError(
                f"{label} frequency semantics are inconsistent with source_kind"
            )
        frequency = _finite_number(
            row["frequency_value"], f"{label} frequency_value"
        )
        if semantics == "observed_occurrence" and frequency != 1.0:
            raise ValueError("Observed occurrences must have frequency_value=1")
        if semantics == "sampled_from_published_rate" and frequency <= 0.0:
            raise ValueError("Published outage rates must be positive")
        if semantics == "scenario_weight" and not 0.0 < frequency <= 1.0:
            raise ValueError("Scenario weights must lie in (0, 1]")
        if semantics == "deterministic_stress_no_frequency" and frequency != 0.0:
            raise ValueError("Deterministic stress events must have frequency_value=0")
        start = _timestamp(row["start_timestamp"], f"{label} start_timestamp")
        end = _timestamp(row["end_timestamp"], f"{label} end_timestamp")
        if end <= start:
            raise ValueError(f"{label} end_timestamp must follow start_timestamp")
        incidents.append(
            GridIncident(
                event_id=event_id,
                start_timestamp=start,
                end_timestamp=end,
                kind=kind,
                element_id=element_id,
                frequency_semantics=semantics,
                frequency_value=frequency,
            )
        )
    event_ids = [incident.event_id for incident in incidents]
    if len(set(event_ids)) != len(event_ids):
        raise ValueError("Incident chronology contains duplicate event IDs")
    return IncidentChronology(
        schema=INCIDENT_CHRONOLOGY_SCHEMA,
        incidents=tuple(incidents),
        source=source,
    )


def validate_incidents_against_business_timeline(
    incidents: IncidentChronology,
    business: BusinessChronology,
    *,
    maximum_simultaneous_incidents: int = 1,
) -> None:
    """Require event boundaries and calls to be representable on the M6 clock."""

    if (
        isinstance(maximum_simultaneous_incidents, bool)
        or maximum_simultaneous_incidents != 1
    ):
        raise ValueError("The current M6 security scope supports only N-1 incidents")
    timestamps = tuple(point.timestamp for point in business.points)
    step = timedelta(hours=business.time_step_hours)
    boundaries = set(timestamps) | {timestamps[-1] + step}
    active_counts = [0] * len(timestamps)
    for incident in incidents.incidents:
        if incident.start_timestamp not in boundaries or incident.end_timestamp not in boundaries:
            raise ValueError(f"Incident {incident.event_id} is not aligned to the business clock")
        if incident.start_timestamp < timestamps[0] or incident.end_timestamp > timestamps[-1] + step:
            raise ValueError(f"Incident {incident.event_id} lies outside the business timeline")
        active_indices = [
            index
            for index, timestamp in enumerate(timestamps)
            if incident.start_timestamp <= timestamp < incident.end_timestamp
        ]
        if not active_indices:
            raise ValueError(f"Incident {incident.event_id} has no represented time step")
        for index in active_indices:
            active_counts[index] += 1
            if active_counts[index] > maximum_simultaneous_incidents:
                raise ValueError("Incident chronology contains overlapping N-1 events")


def incident_by_time_step(
    incidents: IncidentChronology,
    business: BusinessChronology,
) -> tuple[GridIncident | None, ...]:
    """Expand validated N-1 outages onto the shared business/grid clock."""

    validate_incidents_against_business_timeline(incidents, business)
    active_incidents = []
    for point in business.points:
        active_incidents.append(
            next(
                (
                    incident
                    for incident in incidents.incidents
                    if incident.start_timestamp
                    <= point.timestamp
                    < incident.end_timestamp
                ),
                None,
            )
        )
    return tuple(active_incidents)


def evidence_kinds(sources: Iterable[EvidenceSource]) -> tuple[str, ...]:
    """Return source kinds for machine-readable evidence-status gates."""

    kinds = tuple(source.source_kind for source in sources)
    unknown = set(kinds) - _SOURCE_KINDS
    if unknown:
        raise ValueError(f"Unsupported evidence source kinds: {sorted(unknown)}")
    return kinds
