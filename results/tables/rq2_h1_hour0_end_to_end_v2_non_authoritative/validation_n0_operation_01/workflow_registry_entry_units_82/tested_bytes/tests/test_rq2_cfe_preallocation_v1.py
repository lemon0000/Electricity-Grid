from dataclasses import replace
from fractions import Fraction as Q

import pytest

from src.rq2_joint_deliverability_boundary_v1 import cfe_preallocation as api


@pytest.mark.parametrize('w,source,alpha,q,s', [
    ('0.4', '0.8', '0.5', '0.24', '0'),
    ('0.4', '0.2', '0.5', '0', '0.24'),
    ('0', '0.8', '0.5', '0', '0'),
    ('1', '1', '0.5', '1', '0'),
    ('0.4', '0', '0.5', '0', '0.4'),
    ('0.4', '0.5', '0.5', '0', '0'),
    ('1', '0', '1', '0', '0')])
def test_exact_preaction_power_balance(w, source, alpha, q, s):
    a = api.allocate(w, source, alpha)
    assert a.raw_request == Q(q) and a.compatible_surplus == Q(s)
    assert a.allowance == (1-Q(source))*Q(w)
    assert a.raw_request <= a.workload and a.raw_request*a.compatible_surplus == 0
    if a.raw_request:
        assert a.target*(a.workload-a.raw_request) == a.allowance
    else:
        assert a.target*(a.workload+a.compatible_surplus) == a.allowance


@pytest.mark.parametrize('q', ['0.000000999999', '0.000001', '0.000001000001'])
def test_existing_effective_threshold_is_applied_after_raw_mapping(q):
    a = api.allocate('1', q, '1')
    assert a.raw_request == Q(q)
    assert a.effective_request == (Q(q) if Q(q) > Q('0.000001') else 0)


def test_four_arms_preserve_shared_capacity_and_b6_separate_accounts():
    a = api.allocate('0.4', '0.8', '0.5')  # q_C=.24; available=.28
    result = api.necessary_conditions(a, '0.7', grid_request='0.1')
    assert not result['network_only_conflict'] and not result['cfe_only_conflict']
    assert result['joint_additive_conflict'] and result['b6_shared_execution_necessary_conflict']
    assert not result['b6_planning_track_conflict']
    assert not result['absence_of_conflict_is_service_success']
    assert api.necessary_conditions(a, '0.5')['cfe_only_conflict']
    assert a.raw_request == Q('0.24')  # No truncation to f*w.


def test_allowance_does_not_depend_on_arm_capacity_or_actions():
    a = api.allocate('0.4', '0.8', '0.5')
    identity = a.identity
    for f, grid in [('0.1', '0'), ('0.9', '0.2')]:
        api.necessary_conditions(a, f, grid_request=grid)
        assert a.identity == identity
    with pytest.raises(ValueError, match='same pre-action allowance'):
        replace(a, compatible_surplus=Q('0.1'))


@pytest.mark.parametrize('w,source,alpha', [('1.01','0.5','0.5'), ('-1','0.5','0.5'),
    ('1','1.01','0.5'), ('1','-0.1','0.5'), ('1','0.5','0'), ('1','0.5','1.1'),
    (0.4,'0.5','0.5'), (True,'0.5','0.5')])
def test_invalid_or_implicit_numeric_input_rejected(w, source, alpha):
    with pytest.raises(ValueError): api.allocate(w, source, alpha)


def test_repeating_rational_has_no_float_or_recovery_quantization():
    a = api.allocate('1/7', '1/3', '1/2')
    assert a.compatible_surplus == Q(1, 21)
    assert a.record()['compatible_surplus'] == '1/21'


def test_low_renewable_hour_still_conflicts_at_current_fraction():
    a = api.allocate('0.8', '0.9762905149290434', '0.5')
    assert a.raw_request/a.workload == Q('0.9525810298580868')
    assert api.necessary_conditions(a, '0.5')['cfe_only_conflict']


def test_old_or_forged_allocation_type_rejected():
    with pytest.raises(ValueError): api.necessary_conditions(object(), '0.5')


def test_subthreshold_components_cannot_silently_become_shared_positive_request():
    a = api.allocate('1', '0.0000006', '1')
    r = api.necessary_conditions(a, '1', grid_request='0.0000006')
    assert r['separate_shared_activity_mismatch']
    assert a.effective_request == 0
