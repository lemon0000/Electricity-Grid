"""Apply the frozen exact-current contract tests to the phase successor.

The original assertions/fixtures are reused by rebinding only their module API
for each test. Historical N is still an explicit seam in these contract tests;
the separate phase-history suite tests actual synthetic Job record replay.
"""
import pytest
from experiments import h1_phase_exact_source_current_development_v1 as phase
from tests import test_h1_exact_source_current_development_v1 as cases
from tests.test_h1_exact_source_current_development_v1 import (scenario,supplied,
    test_fresh_exact_projection_and_owned_boundary,
    test_reuses_frozen_projection_instead_of_reinterpreting_float,
    test_unresolved_raw_source_is_not_clipped_or_dropped,
    test_current_registry_origin_and_progress_are_preserved,
    test_incomplete_controller_proof_rejected,
    test_registry_drift_between_reads_rejected,
    test_projection_must_match_packet_and_baseline,
    test_equivalent_raw_decimal_only_changes_audit,
    test_changed_cfe_input_changes_exogenous_key_even_when_N_is_same,
    test_equivalent_raw_CFE_only_changes_audit,
    test_audit_record_cap_is_enforced,
    test_invalid_current_CFE_source_does_not_become_an_input,
    test_final_N_replay_drift_is_rejected,
    test_implementation_rechecked_after_final_source_observation,
)


@pytest.fixture(autouse=True)
def phase_api(monkeypatch):
    monkeypatch.setattr(cases,'m',phase)


def test_phase_progress_bound_precedes_replay(monkeypatch,tmp_path):
    calls=[]
    def reached(root,**kw):
        calls.append(kw['completed_hours'])
        raise RuntimeError('test reached phase replay')
    monkeypatch.setattr(phase.historical,'_replay_prefix',reached)
    args=dict(expected_binding_sha256='1'*64,expected_terminal_sha256='2'*64,expected_registry_identity='3'*64)
    with pytest.raises(RuntimeError,match='reached phase replay'):phase.prepare(tmp_path,completed_hours=192,**args)
    with pytest.raises(ValueError):phase.prepare(tmp_path,completed_hours=193,**args)
    assert calls==[192]
