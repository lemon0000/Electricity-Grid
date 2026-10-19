"""Real immutable phase-data window versus the canonical detached verifier."""
import json
from pathlib import Path
from time import perf_counter

import pytest

from experiments import h1_phase_dependency_validation_operation_development_v1 as m


def test_immutable_phase_window_matches_canonical_science_and_closes(tmp_path):
    before=m.predecessor.io.encode(m.predecessor.prepare_group('training_ub',0))
    count=6;timings=[];start=perf_counter()
    operation=m.PhaseDependencyValidationOperation(maximum_prepares=count,diagnostic_only=True)
    with operation:
        entry=perf_counter()-start
        for ordinal in range(count):
            tick=perf_counter();raw=operation.prepare_group('training_ub',0)
            timings.append(perf_counter()-tick)
            report=json.loads(raw)
            assert report['schema']==m.SCHEMA and report['consumer_bound'] is False
            assert report['diagnostic_only'] is True and report['detached_data'] is True
            assert report['execution']['prepare']==ordinal+1
            assert report['execution']['canonical_physical_verifier_invoked'] is False
            assert m.predecessor.io.encode(report['canonical_predecessor_payload'])==before
        assert not operation.receipt()['complete']
    total=perf_counter()-start;receipt=operation.receipt()
    assert receipt['complete'] and receipt['closed'] and receipt['all_handles_closed']
    assert receipt['immutable_bytes_cleared'] and receipt['original_guard_released']
    assert receipt['first_failure'] is None and receipt['cleanup_errors']==[]
    after=m.predecessor.io.encode(m.predecessor.prepare_group('training_ub',0))
    assert after==before
    with pytest.raises(ValueError,match='lifetime'):
        operation.prepare_group('training_ub',0)
    assert not operation.receipt()['complete']
    # Preserve the successful close observation separately from the intentional
    # post-close misuse, which correctly leaves a sticky failure.
    (tmp_path/'phase_window_observation.json').write_text(json.dumps(dict(
        entry_seconds=entry,prepare_seconds=timings,total_window_seconds=total,
        successful_closed_receipt=receipt,post_close_use_rejected=True,
        canonical_before_after_equal=True,formal_result=False,resource_admission=False),indent=2),encoding='utf-8')


@pytest.mark.parametrize('maximum,diagnostic',[(0,True),(17,True),(True,True),(1,False),(1,1)])
def test_only_bounded_explicit_diagnostic_data_plan_is_accepted(maximum,diagnostic):
    with pytest.raises(ValueError):
        m.PhaseDependencyValidationOperation(maximum_prepares=maximum,diagnostic_only=diagnostic)
