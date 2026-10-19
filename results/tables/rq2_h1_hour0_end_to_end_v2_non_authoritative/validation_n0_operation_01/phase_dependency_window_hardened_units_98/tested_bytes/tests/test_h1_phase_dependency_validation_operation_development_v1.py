"""Real immutable phase-data window versus the canonical detached verifier."""
import json
from hashlib import sha256
from time import perf_counter

import pytest

from experiments import h1_phase_dependency_validation_operation_development_v1 as m


def test_immutable_phase_window_matches_canonical_science_and_closes(tmp_path):
    before=m.predecessor.io.encode(m.predecessor.prepare_group('training_ub',0))
    count=6;timings=[];start=perf_counter()
    operation=m.PhaseDependencyValidationOperation(plan=(('training_ub',0),)*count,diagnostic_only=True)
    with operation:
        entry=perf_counter()-start
        for ordinal in range(count):
            tick=perf_counter();raw=operation.prepare_group('training_ub',0)
            timings.append(perf_counter()-tick)
            report=json.loads(raw)
            assert report['schema']==m.SCHEMA and report['consumer_bound'] is False
            assert report['diagnostic_only'] is True and report['detached_data'] is True
            assert report['execution']['prepare']==ordinal+1
            assert report['canonical_physical_verifier_invoked'] is False
            assert report['fresh_at_return_only'] is False
            assert report['per_call_physical_freshness'] is False
            assert report['canonical_equivalence_verified'] is False
            assert 'canonical_predecessor_payload' not in report
            assert report['execution']['legacy_shape_reference_sha256']==sha256(before).hexdigest()
            assert report['scientific_projection']['predecessor_group']==json.loads(before)['predecessor_group']
            assert report['scientific_projection']['dependency_sha256']==json.loads(before)['dependency_sha256']
        assert not operation.receipt()['lifecycle_complete']
    total=perf_counter()-start;receipt=operation.receipt()
    assert receipt['lifecycle_complete'] and receipt['closed'] and receipt['all_handles_closed']
    assert receipt['canonical_equivalence_verified'] is False
    assert receipt['immutable_bytes_cleared'] and receipt['original_guard_released']
    assert receipt['first_failure'] is None and receipt['cleanup_errors']==[]
    after=m.predecessor.io.encode(m.predecessor.prepare_group('training_ub',0))
    assert after==before
    with pytest.raises(ValueError,match='lifetime'):
        operation.prepare_group('training_ub',0)
    assert not operation.receipt()['lifecycle_complete']
    # Preserve the successful close observation separately from the intentional
    # post-close misuse, which correctly leaves a sticky failure.
    (tmp_path/'phase_window_observation.json').write_text(json.dumps(dict(
        entry_seconds=entry,prepare_seconds=timings,total_window_seconds=total,
        successful_closed_receipt=receipt,post_close_use_rejected=True,
        canonical_before_after_equal=True,formal_result=False,resource_admission=False),indent=2),encoding='utf-8')


@pytest.mark.parametrize('plan,diagnostic',[((),True),((('training_ub',0),)*17,True),
    ((('training_ub',True),),True),((('training_ub',0),),False),((('training_ub',0),),1)])
def test_only_bounded_explicit_diagnostic_data_plan_is_accepted(plan,diagnostic):
    with pytest.raises(ValueError):
        m.PhaseDependencyValidationOperation(plan=plan,diagnostic_only=diagnostic)
