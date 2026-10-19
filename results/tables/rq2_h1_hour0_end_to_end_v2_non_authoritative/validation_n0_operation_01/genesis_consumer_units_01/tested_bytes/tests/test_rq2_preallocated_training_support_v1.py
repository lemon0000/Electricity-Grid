from fractions import Fraction as Q
import pytest
from experiments.audit_rq2_preallocated_training_support_v1 import first_conflict
from src.rq2_joint_deliverability_boundary_v1.cfe_preallocation import allocate, necessary_conditions


@pytest.mark.parametrize('source,target,f,w', [('0.8','0.5','0.5','0.4'),
    ('0.8','0.5','0.8','0.4'), ('0.000001','1','0','1'), ('0.2','0.5','0','0.4')])
def test_optimized_search_matches_independent_allocation(source, target, f, w):
    a = allocate(w, source, target)
    factor = max(Q(0), 1-(1-Q(source))/Q(target))
    expected = 0 if necessary_conditions(a, f)['cfe_only_conflict'] else None
    assert first_conflict((factor,), (Q(w),), Q(f)) == expected


def test_unresolved_row_not_zero_and_later_witness_retained():
    assert first_conflict((Q(1), Q(1)), (None, Q('0.4')), Q('.5')) == 1
    assert first_conflict((Q(1),), (None,), Q('.5')) is None


def test_exact_equality_and_misaligned_horizons():
    assert first_conflict((Q('.5'),), (Q('.4'),), Q('.5')) is None
    with pytest.raises(ValueError): first_conflict((Q(1),), (), Q('.5'))


def test_activity_threshold_drift_is_not_silently_accepted(monkeypatch):
    from experiments import audit_rq2_preallocated_training_support_v1 as audit
    monkeypatch.setattr(audit.mapping, 'SERVICE_TOLERANCE', 1e-5)
    with pytest.raises(ValueError, match='threshold drift'):
        first_conflict((Q(1),), (Q(1),), Q('.5'))
    with pytest.raises(ValueError, match='threshold drift'): audit.audit()
