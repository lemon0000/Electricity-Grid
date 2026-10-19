import csv
import hashlib
import json
from dataclasses import replace
from datetime import datetime, timedelta, timezone

import pytest

from src.evaluation import (
    BUSINESS_CHRONOLOGY_SCHEMA,
    INCIDENT_CHRONOLOGY_SCHEMA,
    ChronologicalFlexibilityEnvelope,
    EvidenceSource,
    RecoveryParameters,
    incident_by_time_step,
    load_business_chronology_csv,
    load_incident_chronology_csv,
    validate_incidents_against_business_timeline,
)
from src.grid import (
    ChronologicalDispatchResult,
    build_chronological_dispatch_request,
    dispatch_result_to_flexibility_trace,
    validate_chronological_dispatch,
)


BUSINESS_FIELDS = (
    "timestamp",
    "period",
    "requested_demand_mw",
    "flexible_demand_mw",
    "recoverable_flexible_mw",
    "physical_maximum_demand_mw",
    "recovery_headroom_mw",
)
INCIDENT_FIELDS = (
    "event_id",
    "start_timestamp",
    "end_timestamp",
    "kind",
    "element_id",
    "frequency_semantics",
    "frequency_value",
)


def _write_csv(path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def _source(path, *, kind="observed"):
    return EvidenceSource(
        dataset_id=path.stem,
        source_kind=kind,
        citation="doi:10.0000/example",
        version="v1",
        sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
    )


def _recovery(tmp_path):
    artifact = tmp_path / "recovery-source.txt"
    artifact.write_text(
        json.dumps(
            {
                "schema": "m6_recovery_parameters_v1",
                "maximum_recovery_power_mw": 20.0,
                "recovery_efficiency": 0.9,
            }
        ),
        encoding="utf-8",
    )
    return RecoveryParameters(
        maximum_recovery_power_mw=20.0,
        recovery_efficiency=0.9,
        source=EvidenceSource(
            dataset_id="recovery_parameters",
            source_kind="published_benchmark",
            citation="doi:10.0000/recovery",
            version="v1",
            sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
        ),
        source_artifact_path=artifact,
    )


def _business_rows():
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    return [
        {
            "timestamp": (start + timedelta(hours=index)).isoformat(),
            "period": "q1",
            "requested_demand_mw": 100,
            "flexible_demand_mw": 40,
            "recoverable_flexible_mw": 30,
            "physical_maximum_demand_mw": 120,
            "recovery_headroom_mw": 20,
        }
        for index in range(3)
    ]


def _load_business(tmp_path, rows=None):
    path = tmp_path / "business.csv"
    _write_csv(path, BUSINESS_FIELDS, rows or _business_rows())
    return load_business_chronology_csv(
        path,
        time_step_hours=1.0,
        workload_source=_source(path),
        recovery=_recovery(tmp_path),
    )


def _incident_rows():
    start = datetime(2020, 1, 1, tzinfo=timezone.utc)
    return [
        {
            "event_id": "event-1",
            "start_timestamp": (start + timedelta(hours=1)).isoformat(),
            "end_timestamp": (start + timedelta(hours=2)).isoformat(),
            "kind": "branch",
            "element_id": "A1",
            "frequency_semantics": "observed_occurrence",
            "frequency_value": 1,
        }
    ]


def _load_incidents(tmp_path, rows=None):
    path = tmp_path / "incidents.csv"
    _write_csv(path, INCIDENT_FIELDS, rows or _incident_rows())
    return load_incident_chronology_csv(path, source=_source(path))


def test_valid_source_locked_chronologies_share_one_clock(tmp_path):
    business = _load_business(tmp_path)
    incidents = _load_incidents(tmp_path)

    validate_incidents_against_business_timeline(incidents, business)
    active = incident_by_time_step(incidents, business)

    assert business.schema == BUSINESS_CHRONOLOGY_SCHEMA
    assert incidents.schema == INCIDENT_CHRONOLOGY_SCHEMA
    assert [event.event_id if event else None for event in active] == [
        None,
        "event-1",
        None,
    ]


def test_business_loader_rejects_schema_drift_and_source_drift(tmp_path):
    path = tmp_path / "business.csv"
    _write_csv(path, BUSINESS_FIELDS[:-1], _business_rows())
    source = _source(path)
    with pytest.raises(ValueError, match="columns must exactly equal"):
        load_business_chronology_csv(
            path,
            time_step_hours=1.0,
            workload_source=source,
            recovery=_recovery(tmp_path),
        )

    _write_csv(path, BUSINESS_FIELDS, _business_rows())
    with pytest.raises(ValueError, match="SHA-256 does not match"):
        load_business_chronology_csv(
            path,
            time_step_hours=1.0,
            workload_source=source,
            recovery=_recovery(tmp_path),
        )


def test_business_loader_rejects_surplus_row_cells(tmp_path):
    path = tmp_path / "business.csv"
    row = _business_rows()[0]
    path.write_text(
        ",".join(BUSINESS_FIELDS)
        + "\n"
        + ",".join(str(row[field]) for field in BUSINESS_FIELDS)
        + ",unexpected\n",
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="missing or surplus cells"):
        load_business_chronology_csv(
            path,
            time_step_hours=1.0,
            workload_source=_source(path),
            recovery=_recovery(tmp_path),
        )

def test_recovery_values_must_match_the_hashed_parameter_artifact(tmp_path):
    path = tmp_path / "business.csv"
    _write_csv(path, BUSINESS_FIELDS, _business_rows())
    recovery = replace(_recovery(tmp_path), recovery_efficiency=0.8)

    with pytest.raises(ValueError, match="do not match"):
        load_business_chronology_csv(
            path,
            time_step_hours=1.0,
            workload_source=_source(path),
            recovery=recovery,
        )


def test_recovery_artifact_rejects_duplicate_json_keys(tmp_path):
    path = tmp_path / "business.csv"
    _write_csv(path, BUSINESS_FIELDS, _business_rows())
    recovery = _recovery(tmp_path)
    artifact = recovery.source_artifact_path
    artifact.write_text(
        '{"schema":"m6_recovery_parameters_v1",'
        '"maximum_recovery_power_mw":20.0,'
        '"recovery_efficiency":0.9,"recovery_efficiency":0.8}',
        encoding="utf-8",
    )
    source = replace(
        recovery.source,
        sha256=hashlib.sha256(artifact.read_bytes()).hexdigest(),
    )

    with pytest.raises(ValueError, match="valid UTF-8 JSON"):
        load_business_chronology_csv(
            path,
            time_step_hours=1.0,
            workload_source=_source(path),
            recovery=replace(recovery, source=source),
        )


@pytest.mark.parametrize(
    ("field", "value", "message"),
    (
        ("requested_demand_mw", "NaN", "finite"),
        ("flexible_demand_mw", 101, "flexible demand exceeds"),
        ("recoverable_flexible_mw", 41, "recoverable demand exceeds"),
        ("physical_maximum_demand_mw", 99, "requested demand exceeds"),
        ("recovery_headroom_mw", 21, "recovery headroom exceeds"),
    ),
)
def test_business_physical_inequalities_fail_closed(tmp_path, field, value, message):
    rows = _business_rows()
    rows[1][field] = value
    path = tmp_path / "business.csv"
    _write_csv(path, BUSINESS_FIELDS, rows)

    with pytest.raises(ValueError, match=message):
        load_business_chronology_csv(
            path,
            time_step_hours=1.0,
            workload_source=_source(path),
            recovery=_recovery(tmp_path),
        )


@pytest.mark.parametrize("duplicate", (True, False))
def test_business_clock_rejects_duplicates_and_gaps(tmp_path, duplicate):
    rows = _business_rows()
    rows[1]["timestamp"] = (
        rows[0]["timestamp"] if duplicate else "2020-01-01T03:00:00+00:00"
    )
    path = tmp_path / "business.csv"
    _write_csv(path, BUSINESS_FIELDS, rows)

    with pytest.raises(ValueError, match="duplicate|continuous"):
        load_business_chronology_csv(
            path,
            time_step_hours=1.0,
            workload_source=_source(path),
            recovery=_recovery(tmp_path),
        )


def test_naive_business_timestamps_are_rejected(tmp_path):
    rows = _business_rows()
    rows[0]["timestamp"] = "2020-01-01T00:00:00"
    path = tmp_path / "business.csv"
    _write_csv(path, BUSINESS_FIELDS, rows)

    with pytest.raises(ValueError, match="UTC offset"):
        load_business_chronology_csv(
            path,
            time_step_hours=1.0,
            workload_source=_source(path),
            recovery=_recovery(tmp_path),
        )


def test_security_state_enumeration_cannot_be_event_frequency(tmp_path):
    rows = _incident_rows()
    rows[0]["frequency_semantics"] = "security_state_enumeration"
    path = tmp_path / "incidents.csv"
    _write_csv(path, INCIDENT_FIELDS, rows)

    with pytest.raises(ValueError, match="cannot be used as event frequency"):
        load_incident_chronology_csv(path, source=_source(path))


def test_zero_observed_incidents_do_not_require_an_artificial_event(tmp_path):
    path = tmp_path / "incidents.csv"
    _write_csv(path, INCIDENT_FIELDS, [])

    incidents = load_incident_chronology_csv(path, source=_source(path))

    assert incidents.incidents == ()


def test_frequency_semantics_cannot_upgrade_synthetic_events_to_observed(tmp_path):
    rows = _incident_rows()
    rows[0]["frequency_semantics"] = "deterministic_stress_no_frequency"
    rows[0]["frequency_value"] = 0
    path = tmp_path / "incidents.csv"
    _write_csv(path, INCIDENT_FIELDS, rows)

    with pytest.raises(ValueError, match="inconsistent with source_kind"):
        load_incident_chronology_csv(path, source=_source(path, kind="observed"))


def test_incident_ids_boundaries_and_n_minus_one_scope_are_strict(tmp_path):
    business = _load_business(tmp_path)
    rows = _incident_rows()
    second = dict(rows[0])
    second["event_id"] = "event-2"
    second["kind"] = "generator"
    second["element_id"] = "G1"
    incidents = _load_incidents(tmp_path, rows + [second])

    with pytest.raises(ValueError, match="overlapping N-1"):
        validate_incidents_against_business_timeline(incidents, business)

    rows[0]["start_timestamp"] = "2020-01-01T01:30:00+00:00"
    incidents = _load_incidents(tmp_path, rows)
    with pytest.raises(ValueError, match="not aligned"):
        validate_incidents_against_business_timeline(incidents, business)


def test_sourced_business_and_incidents_close_the_dispatch_audit_loop(tmp_path):
    business = _load_business(tmp_path)
    incidents = _load_incidents(tmp_path)
    envelope = ChronologicalFlexibilityEnvelope(
        time_step_hours=1.0,
        maximum_event_duration_hours=1.0,
        minimum_recovery_hours=0.0,
        maximum_events_by_period={"q1": 1},
        maximum_curtailment_energy_mwh_by_period={"q1": 10.0},
        maximum_recovery_debt_mwh=10.0,
        maximum_recovery_power_mw=20.0,
        minimum_event_power_mw=1.0,
        response_time_hours=1.0,
        curtailment_ramp_mw_per_hour=20.0,
        recovery_efficiency=0.9,
        terminal_debt_limit_mwh_by_period={"q1": 0.0},
        parameter_status="published_benchmark_interface_test",
    )
    request = build_chronological_dispatch_request(
        business,
        incidents,
        system_demand_by_bus_mw=({1: 90.0, 8: 0.0},) * 3,
        generator_availability=({"G1": True},) * 3,
        dc_bus=8,
        contract_call_limit_mw=(15.0, 15.0, 15.0),
        connected_capacity_mw=(120.0, 120.0, 120.0),
        flexibility_envelope=envelope,
        flexibility_boundary_state_status="clean_boundary_with_zero_carry_in",
        completed_periods=frozenset({"q1"}),
        initial_commitment={"G1": True},
        initial_generation_mw={"G1": 190.0},
        initial_time_in_state_hours={"G1": 12.0},
    )
    recovery = 10.0 / 0.9
    result = ChronologicalDispatchResult(
        feasible=True,
        timestamps=tuple(point.timestamp for point in business.points),
        grid_call_mw=(0.0, 10.0, 0.0),
        recovery_power_mw=(0.0, 0.0, recovery),
        dc_power_mw=(100.0, 90.0, 100.0 + recovery),
        generation_mw=(
            {"G1": 190.0},
            {"G1": 180.0},
            {"G1": 190.0 + recovery},
        ),
        commitment=({"G1": True},) * 3,
        load_shed_mw=(0.0, 0.0, 0.0),
        network_losses_mw=(0.0, 0.0, 0.0),
        commitment_feasible_by_step=(True, True, True),
        ramp_feasible_by_step=(True, True, True),
        reserve_feasible_by_step=(True, True, True),
        normal_secure_by_step=(True, True, True),
        contingency_secure_by_step=(True, True, True),
        security_state_count_by_step=(2, 2, 2),
        checked_security_state_ids_by_step=(
            ("normal", "event-1"),
            ("normal", "event-1"),
            ("normal", "event-1"),
        ),
        termination_condition="optimal",
        dispatch_scope="sourced_business_integration_test",
        security_scope="normal_plus_named_incident_integration_test",
    )

    validate_chronological_dispatch(request, result)
    trace = dispatch_result_to_flexibility_trace(request, result)

    assert request.dc_call_limit_mw == pytest.approx((15.0, 15.0, 15.0))
    assert trace.prescribed_recovery_power_mw == pytest.approx(
        result.recovery_power_mw
    )

    debt_invalid = replace(
        result,
        recovery_power_mw=(0.0, 0.0, 0.0),
        dc_power_mw=(100.0, 90.0, 100.0),
        generation_mw=({"G1": 190.0}, {"G1": 180.0}, {"G1": 190.0}),
    )
    with pytest.raises(ValueError, match="business envelope"):
        validate_chronological_dispatch(request, debt_invalid)
