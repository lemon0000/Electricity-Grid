"""One target-length detached business cost diagnostic, no owner or solver."""
from dataclasses import replace
from fractions import Fraction as Q
from hashlib import sha256
import json
from pathlib import Path
import sys
import time

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO))
sys.path.insert(1, str(REPO / 'tests'))
import pytest
import yaml

from experiments import h1_exact_business_development_v1 as business
from tests import test_h1_exact_business_development_v1 as fixture
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver


def test_target_history_cost(tmp_path, monkeypatch):
    # The imported autouse fixture denies all established normal/native solver
    # entries. Deny the source/producer entries explicitly as well.
    from experiments import h1_phase_owner_development_v1 as phase
    from experiments import h1_phase_obligation_controller_development_v1 as normal
    def denied(*args, **kwargs):
        raise AssertionError('business component diagnostic attempted a source or Job')
    monkeypatch.setattr(phase, '_fresh', denied)
    monkeypatch.setattr(phase.source.source.windows, 'load_source_window', denied)
    monkeypatch.setattr(normal.Controller, '_step_development', denied)
    protocol_path = REPO / 'configs/rq2_finite_mechanism_protocol_candidate_v2.DRAFT.yaml'
    assert sha256(protocol_path.read_bytes()).hexdigest() == '95eb158f0a8e6784d2af401e67164965543c98f42ff02b756c214982601e5430'
    protocol = yaml.safe_load(protocol_path.read_bytes())
    parameters = protocol['business_anchor']
    assert protocol['window']['enrollment_hours'] == 168
    assert protocol['window']['maximum_followup_hours'] == 24
    started = time.perf_counter()
    seed = fixture.origin()
    spec = replace(seed.cursor.spec,
        committed_capacity=.5,
        minimum_event_power=float(parameters['minimum_event_power']),
        curtailment_ramp_per_hour=float(parameters['curtailment_up_ramp_per_hour']),
        response_time_hours=float(parameters['response_time_hours']),
        maximum_recovery_power=float(parameters['maximum_recovery_power']),
        recovery_decimal_places=parameters['recovery_decimal_places'])
    anchor = seed.cursor.initial.tracks[0][1].physical.anchor
    envelope = dict(seed.cursor.initial.tracks[0][1].physical.envelope,
        time_step_hours=float(parameters['time_step_hours']),
        recovery_efficiency=float(parameters['recovery_efficiency']),
        maximum_event_duration_hours=float(parameters['maximum_event_duration_hours']),
        maximum_event_count=parameters['episode_event_cap'],
        normalized_energy_budget=float(parameters['episode_call_energy_cap']),
        normalized_debt_limit=float(parameters['normalized_debt_cap']),
        minimum_recovery_hours=float(parameters['minimum_rest_hours']))
    mechanism = business.Mechanism(Q(1,2), Q(parameters['flexible_fraction']),
                                   Q(parameters['recovery_headroom_coefficient']))
    carry = business.initialize_development(spec, mechanism=mechanism, anchor=anchor,
        envelope=envelope, accounting_period_id=business.PERIOD)
    carries = {0: carry}
    for hour in range(1, 193):
        current = fixture.hour(carry, hour-1,
            g=Q(17,1000) if hour == 168 else Q(0),
            source=Q(0) if hour == 192 else Q(1,2))
        candidate = fixture.advance(carry, current)
        assert candidate.next_candidate is not None, (hour, candidate.status)
        carry = candidate.next_candidate
        if hour in (168,192):
            carries[hour] = carry
        if hour % 8 == 0:
            progress = dict(business_hours=hour, stage='detached_business_build',
                elapsed_seconds=time.perf_counter()-started, scientific_chain_progress=False)
            (tmp_path / 'progress.json').write_text(json.dumps(progress), encoding='utf-8')
            print(json.dumps(progress), flush=True)
    build_seconds = time.perf_counter()-started
    rows = []
    for hour in (168,192):
        selected = carries[hour]
        began = time.perf_counter()
        scientific = selected.scientific_payload
        science_seconds = time.perf_counter()-began
        before = sha256(scientific).hexdigest()
        began = time.perf_counter()
        assert business._validate(selected) is None
        validate_seconds = time.perf_counter()-began
        assert sha256(selected.scientific_payload).hexdigest() == before
        began = time.perf_counter()
        audit = business.encoding._encoded(selected)
        audit_seconds = time.perf_counter()-began
        assert len(scientific)+len(audit) < 16*1024**2
        (tmp_path / f'h{hour}_scientific.json').write_bytes(scientific)
        (tmp_path / f'h{hour}_full_carry_audit.json').write_bytes(audit)
        ledger = selected.cursor.execution.tracks[0][1].ledger
        rows.append(dict(hours=hour, original_validator_seconds=validate_seconds,
            scientific_encoding_seconds=science_seconds, full_carry_encoding_seconds=audit_seconds,
            scientific_bytes=len(scientific), scientific_sha256=before,
            full_carry_bytes=len(audit), full_carry_sha256=sha256(audit).hexdigest(),
            history_length=len(selected.history), records=len(selected.cursor.records),
            debt=str(ledger.debt), scientific_payload_unchanged=True))
    ledger = carry.cursor.execution.tracks[0][1].ledger
    action = carry.cursor.records[-1].response.action
    assert carries[168].cursor.execution.tracks[0][1].ledger.debt == Q(17,1000)
    assert action.recovery == Q(1,50) and ledger.debt == 0
    assert ledger.cohorts[0].due_hour == 192 and ledger.cohorts[0].missed_at_deadline == 0
    assert ledger.cohorts[0].incurred == Q(17,1000)
    fact = dict(status='DRAFT_NONAUTHORITATIVE', scope='target_length_original_business_validator_and_encoding_observation',
        frozen_v2_anchor_parameters=parameters, benchmark_alpha='1/2', benchmark_D='1/2',
        build_business_hours=192, build_seconds=build_seconds,
        build_prepare_calls_by_fixed_code=192, build_validate_history_length_sum_by_fixed_code=sum(range(192)),
        internal_record_or_callback_calls_instrumented=False, rows=rows,
        primary_birth_hour=168, due_hour=192, final_recovery=str(action.recovery),
        final_debt=str(ledger.debt), deadline_snapshot=str(ledger.cohorts[0].missed_at_deadline),
        repetitions_per_target=1, runtime_record_cache=False,
        component_wall_or_storage_upper_bound_established=False,
        complete_owner_event_size_measured=False, complete_owner_chain_measured=False,
        source_prefix_authenticated=False, paired_owner_authenticated=False, phase_events_written=0,
        overall_performance_review_complete=False, resource_admission=False,
        full_192_hour_execution_verified=False, new_normal_jobs=0, real_native_calls=0, formal_result=False)
    (tmp_path / 'fact.json').write_text(json.dumps(fact, indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(rows=rows, build_seconds=build_seconds)), flush=True)
