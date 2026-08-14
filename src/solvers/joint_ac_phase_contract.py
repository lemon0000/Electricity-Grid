"""Durable, hash-bound phase contract for isolated joint-AC workers."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from threading import Event, Lock, Thread
from time import monotonic
from typing import Mapping, Sequence

REQUIRED_PHASES = (
    "worker_started",
    "context_load_started",
    "context_load_completed",
    "prepared_cases_completed",
    "nlp_build_started",
    "nlp_build_completed",
    "solver_started",
    "solver_finished",
)
CALIBRATION_REQUIRED_PHASES = (
    "worker_started",
    "context_load_started",
    "context_load_completed",
    "prepared_cases_completed",
    "nlp_build_started",
    "nlp_build_completed",
    "calibration_pre_solver_stop",
)
HEARTBEAT_EVENTS = frozenset({"startup_heartbeat", "solver_heartbeat"})
_HEX_SHA256 = re.compile(r"[0-9a-f]{64}")
_EXPRESSION_COMPONENT_FIELDS = (
    "schema",
    "variable_count",
    "constraint_count",
    "variable_order_sha256",
    "objective_expression_sha256",
    "constraint_order_and_expression_sha256",
    "ipopt_options_sha256",
    "prepared_inputs_sha256",
)
_SOLVER_INPUT_COMPONENT_FIELDS = (
    *_EXPRESSION_COMPONENT_FIELDS,
    "expression_fingerprint_sha256",
    "initial_point_sha256",
    "variable_lower_sha256",
    "variable_upper_sha256",
    "constraint_lower_sha256",
    "constraint_upper_sha256",
)


class PhaseContractError(RuntimeError):
    """The worker phase journal is missing, unordered, or hash-drifted."""


@dataclass(frozen=True)
class HonestIncomplete:
    reason: str
    solver_call_count: int
    is_infeasibility_evidence: bool = False
    resume_allowed: bool = False


@dataclass(frozen=True)
class PhaseTimingState:
    verified_phase_count: int
    solver_started_verified: bool
    solver_finished_verified: bool
    solver_deadline_monotonic: float | None


def canonical_sha256(value: object) -> str:
    encoded = json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _is_sha256(value: object) -> bool:
    return isinstance(value, str) and _HEX_SHA256.fullmatch(value) is not None


def expression_fingerprint_sha256(payload: Mapping[str, object]) -> str:
    components = {key: payload.get(key) for key in _EXPRESSION_COMPONENT_FIELDS}
    if (
        components["schema"] != "rts_gmlc_ac_aware_nlp_expression_fingerprint_v1"
        or any(
            isinstance(components[key], bool)
            or not isinstance(components[key], int)
            or components[key] < 0
            for key in ("variable_count", "constraint_count")
        )
        or any(
            not _is_sha256(components[key])
            for key in (
                "variable_order_sha256",
                "objective_expression_sha256",
                "constraint_order_and_expression_sha256",
                "ipopt_options_sha256",
                "prepared_inputs_sha256",
            )
        )
    ):
        raise PhaseContractError("joint-AC expression fingerprint is incomplete")
    return canonical_sha256(components)


def solver_input_fingerprint_sha256(payload: Mapping[str, object]) -> str:
    components = {key: payload.get(key) for key in _SOLVER_INPUT_COMPONENT_FIELDS}
    expected_expression = expression_fingerprint_sha256(components)
    if components["expression_fingerprint_sha256"] != expected_expression or any(
        not _is_sha256(components[key])
        for key in (
            "initial_point_sha256",
            "variable_lower_sha256",
            "variable_upper_sha256",
            "constraint_lower_sha256",
            "constraint_upper_sha256",
        )
    ):
        raise PhaseContractError("joint-AC solver input fingerprint is incomplete")
    return canonical_sha256(components)


class DurablePhaseJournal:
    """Append JSONL phase evidence using flush+fsync after every record."""

    def __init__(self, path: Path, *, binding: Mapping[str, object]) -> None:
        self.path = path
        self.binding = dict(binding)
        self.binding_sha256 = canonical_sha256(self.binding)
        self._started = monotonic()
        self._sequence = 0
        self._lock = Lock()

    def emit(self, event: str, payload: Mapping[str, object] | None = None) -> None:
        if (
            event not in REQUIRED_PHASES
            and event not in CALIBRATION_REQUIRED_PHASES
            and event not in HEARTBEAT_EVENTS
        ):
            raise ValueError(f"Unknown joint-AC phase event: {event}")
        with self._lock:
            self._sequence += 1
            record = {
                "schema": "rts_gmlc_joint_ac_phase_event_v1",
                "sequence": self._sequence,
                "event": event,
                "timestamp_utc": datetime.now(timezone.utc).isoformat(),
                "worker_monotonic_elapsed_seconds": monotonic() - self._started,
                "worker_pid": os.getpid(),
                "binding": self.binding,
                "binding_sha256": self.binding_sha256,
                "payload": dict(payload or {}),
            }
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8", newline="\n") as stream:
                stream.write(
                    json.dumps(
                        record,
                        sort_keys=True,
                        separators=(",", ":"),
                        ensure_ascii=True,
                        allow_nan=False,
                    )
                    + "\n"
                )
                stream.flush()
                os.fsync(stream.fileno())


class PhaseHeartbeat:
    """Emit durable worker heartbeats without changing required phase order."""

    def __init__(
        self,
        journal: DurablePhaseJournal,
        *,
        event: str,
        interval_seconds: float,
    ) -> None:
        if event not in HEARTBEAT_EVENTS or interval_seconds <= 0.0:
            raise ValueError("Invalid joint-AC heartbeat contract")
        self._journal = journal
        self._event = event
        self._interval_seconds = interval_seconds
        self._stop = Event()
        self._thread: Thread | None = None

    def start(self) -> None:
        if self._thread is not None:
            raise RuntimeError("joint-AC heartbeat already started")
        self._thread = Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=self._interval_seconds + 1.0)

    def _run(self) -> None:
        while not self._stop.wait(self._interval_seconds):
            self._journal.emit(self._event)


def load_verified_phase_events(
    path: Path,
    *,
    expected_binding: Mapping[str, object],
    expected_worker_pid: int,
) -> tuple[dict[str, object], ...]:
    return _load_verified_events(
        path,
        expected_binding=expected_binding,
        expected_worker_pid=expected_worker_pid,
        required_phases=REQUIRED_PHASES,
    )


def load_verified_calibration_events(
    path: Path,
    *,
    expected_binding: Mapping[str, object],
    expected_worker_pid: int,
) -> tuple[dict[str, object], ...]:
    return _load_verified_events(
        path,
        expected_binding=expected_binding,
        expected_worker_pid=expected_worker_pid,
        required_phases=CALIBRATION_REQUIRED_PHASES,
    )


def _load_verified_events(
    path: Path,
    *,
    expected_binding: Mapping[str, object],
    expected_worker_pid: int,
    required_phases: Sequence[str],
) -> tuple[dict[str, object], ...]:
    if (
        isinstance(expected_worker_pid, bool)
        or not isinstance(expected_worker_pid, int)
        or expected_worker_pid <= 0
    ):
        raise ValueError("expected_worker_pid must be a positive integer")
    if not path.is_file():
        return ()
    expected = dict(expected_binding)
    expected_hash = canonical_sha256(expected)
    records: list[dict[str, object]] = []
    required_index = 0
    previous_elapsed = -1.0
    for sequence, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), start=1
    ):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as error:
            raise PhaseContractError(
                "joint-AC phase journal has invalid JSON"
            ) from error
        timestamp = record.get("timestamp_utc") if isinstance(record, dict) else None
        elapsed = (
            record.get("worker_monotonic_elapsed_seconds")
            if isinstance(record, dict)
            else None
        )
        try:
            parsed_timestamp = datetime.fromisoformat(timestamp)
        except (TypeError, ValueError) as error:
            raise PhaseContractError(
                "joint-AC phase event timestamp drifted"
            ) from error
        if parsed_timestamp.tzinfo is None or parsed_timestamp.utcoffset() is None:
            raise PhaseContractError("joint-AC phase event timestamp drifted")
        if (
            not isinstance(record, dict)
            or record.get("schema") != "rts_gmlc_joint_ac_phase_event_v1"
            or record.get("sequence") != sequence
            or record.get("worker_pid") != expected_worker_pid
            or isinstance(elapsed, bool)
            or not isinstance(elapsed, (int, float))
            or not math.isfinite(float(elapsed))
            or float(elapsed) < 0.0
            or float(elapsed) < previous_elapsed
            or record.get("binding") != expected
            or record.get("binding_sha256") != expected_hash
            or canonical_sha256(record.get("binding")) != expected_hash
            or not isinstance(record.get("payload"), dict)
        ):
            raise PhaseContractError("joint-AC phase event identity/hash drifted")
        previous_elapsed = float(elapsed)
        event = record.get("event")
        if event in HEARTBEAT_EVENTS:
            if event == "startup_heartbeat" and required_index >= 7:
                raise PhaseContractError(
                    "startup heartbeat appeared after solver start"
                )
            if (
                required_phases == CALIBRATION_REQUIRED_PHASES
                and event == "solver_heartbeat"
            ):
                raise PhaseContractError(
                    "solver heartbeat appeared in pre-solver calibration"
                )
            if (
                required_phases == REQUIRED_PHASES
                and event == "solver_heartbeat"
                and not 7 <= required_index < 8
            ):
                raise PhaseContractError(
                    "solver heartbeat appeared outside solver phase"
                )
        elif (
            required_index >= len(required_phases)
            or event != required_phases[required_index]
        ):
            raise PhaseContractError("joint-AC required phase order drifted")
        else:
            required_index += 1
        records.append(record)
    _validate_fingerprint_chain(records, expected_binding=expected)
    return tuple(records)


def _phase_record(
    records: Sequence[Mapping[str, object]], event: str
) -> Mapping[str, object] | None:
    return next((record for record in records if record.get("event") == event), None)


def _validate_fingerprint_chain(
    records: Sequence[Mapping[str, object]],
    *,
    expected_binding: Mapping[str, object],
) -> None:
    build_started = _phase_record(records, "nlp_build_started")
    build_completed = _phase_record(records, "nlp_build_completed")
    solver_started = _phase_record(records, "solver_started")
    calibration_stop = _phase_record(records, "calibration_pre_solver_stop")
    solver_finished = _phase_record(records, "solver_finished")
    if solver_started is not None and calibration_stop is not None:
        raise PhaseContractError("joint-AC solver/calibration terminal phase drifted")
    if build_started is not None and build_completed is not None:
        started_payload = build_started["payload"]
        completed_payload = build_completed["payload"]
        if started_payload.get("prepared_inputs_sha256") != completed_payload.get(
            "prepared_inputs_sha256"
        ) or started_payload.get("ipopt_options_sha256") != completed_payload.get(
            "ipopt_options_sha256"
        ):
            raise PhaseContractError("joint-AC NLP build fingerprint drifted")
    for record in (build_started, build_completed):
        if record is not None:
            payload = record["payload"]
            calibration_binding = (
                expected_binding.get("schema")
                == "rts_gmlc_v4_repair_010_startup_calibration_binding_v1"
            )
            if (
                not calibration_binding
                and payload.get("prepared_inputs_sha256")
                != expected_binding.get("prepared_inputs_sha256")
            ) or payload.get("ipopt_options_sha256") != expected_binding.get(
                "ipopt_options_sha256"
            ):
                raise PhaseContractError("joint-AC bound input fingerprint drifted")
    if build_completed is not None:
        payload = build_completed["payload"]
        if payload.get(
            "expression_fingerprint_sha256"
        ) != expression_fingerprint_sha256(payload):
            raise PhaseContractError("joint-AC expression fingerprint drifted")
    solver_input_record = solver_started or calibration_stop
    if solver_input_record is not None:
        payload = solver_input_record["payload"]
        if payload.get(
            "solver_input_fingerprint_sha256"
        ) != solver_input_fingerprint_sha256(payload):
            raise PhaseContractError("joint-AC solver input fingerprint drifted")
        if build_completed is None or any(
            payload.get(key) != build_completed["payload"].get(key)
            for key in (
                "prepared_inputs_sha256",
                "ipopt_options_sha256",
                "expression_fingerprint_sha256",
            )
        ):
            raise PhaseContractError("joint-AC solver input build hash drifted")
    if solver_finished is not None:
        finished_payload = solver_finished["payload"]
        try:
            recomputed_finished = solver_input_fingerprint_sha256(finished_payload)
        except PhaseContractError as error:
            raise PhaseContractError("joint-AC solver_finished hash drifted") from error
        if (
            solver_started is None
            or finished_payload.get("solver_input_fingerprint_sha256")
            != recomputed_finished
            or finished_payload.get("solver_input_fingerprint_sha256")
            != solver_started["payload"].get("solver_input_fingerprint_sha256")
        ):
            raise PhaseContractError("joint-AC solver_finished hash drifted")


class PhaseTimingController:
    """Separate startup timing from solver wall timing in the parent process."""

    def __init__(
        self,
        *,
        startup_started_monotonic: float,
        startup_limit_seconds: float,
        solver_wall_limit_seconds: float,
    ) -> None:
        if startup_limit_seconds <= 0.0 or solver_wall_limit_seconds <= 0.0:
            raise ValueError("joint-AC phase limits must be positive")
        self.startup_deadline_monotonic = (
            startup_started_monotonic + startup_limit_seconds
        )
        self.solver_wall_limit_seconds = solver_wall_limit_seconds
        self.solver_deadline_monotonic: float | None = None

    def observe(
        self,
        path: Path,
        *,
        expected_binding: Mapping[str, object],
        expected_worker_pid: int,
        observed_monotonic: float,
    ) -> PhaseTimingState:
        records = load_verified_phase_events(
            path,
            expected_binding=expected_binding,
            expected_worker_pid=expected_worker_pid,
        )
        solver_started = _phase_record(records, "solver_started") is not None
        solver_finished = _phase_record(records, "solver_finished") is not None
        if solver_started and self.solver_deadline_monotonic is None:
            self.solver_deadline_monotonic = (
                observed_monotonic + self.solver_wall_limit_seconds
            )
        return PhaseTimingState(
            verified_phase_count=sum(
                record.get("event") in REQUIRED_PHASES for record in records
            ),
            solver_started_verified=solver_started,
            solver_finished_verified=solver_finished,
            solver_deadline_monotonic=self.solver_deadline_monotonic,
        )

    def timeout(self, *, observed_monotonic: float) -> HonestIncomplete | None:
        if self.solver_deadline_monotonic is None:
            if observed_monotonic >= self.startup_deadline_monotonic:
                return HonestIncomplete(
                    reason="startup_timeout_before_verified_solver_started",
                    solver_call_count=0,
                )
            return None
        if observed_monotonic >= self.solver_deadline_monotonic:
            return HonestIncomplete(
                reason="solver_wall_timeout_after_verified_solver_started",
                solver_call_count=1,
            )
        return None


def classify_phase_contract_failure(
    *, solver_started_was_verified: bool, reason: str
) -> HonestIncomplete:
    return HonestIncomplete(
        reason=reason,
        solver_call_count=1 if solver_started_was_verified else 0,
    )


__all__ = [
    "DurablePhaseJournal",
    "CALIBRATION_REQUIRED_PHASES",
    "HEARTBEAT_EVENTS",
    "HonestIncomplete",
    "PhaseContractError",
    "PhaseHeartbeat",
    "PhaseTimingController",
    "PhaseTimingState",
    "REQUIRED_PHASES",
    "canonical_sha256",
    "classify_phase_contract_failure",
    "expression_fingerprint_sha256",
    "load_verified_phase_events",
    "load_verified_calibration_events",
    "solver_input_fingerprint_sha256",
]
