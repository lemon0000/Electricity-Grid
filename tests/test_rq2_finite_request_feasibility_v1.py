import pytest
from experiments.audit_rq2_finite_request_feasibility_v1 import necessary_conflict


def test_absolute_request_can_exceed_small_workload_for_any_capacity():
    result = necessary_conflict('0.5', '0.5', '0.6', '0.0001')
    assert result['effective_cfe_request'] == '1/5'
    assert result['request_exceeds_baseline'] and result['request_exceeds_available']


def test_flexibility_conflict_does_not_imply_baseline_conflict():
    result = necessary_conflict('1', '0.1', '0.2', '0.5')
    assert result['request_exceeds_available'] and not result['request_exceeds_baseline']


@pytest.mark.parametrize('amount', ['0', '0.000001'])
def test_effective_zero_boundary_is_not_positive_request(amount):
    result = necessary_conflict('1', '0', amount, '0')
    assert result['effective_cfe_request'] == '0' and not result['request_exceeds_baseline']


def test_exact_equality_is_not_a_conflict():
    result = necessary_conflict('1', '1', '0.4', '0.4')
    assert not result['request_exceeds_baseline'] and not result['request_exceeds_available']
