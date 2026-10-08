from fractions import Fraction as Q
import copy
import json

import pytest

from experiments import rq2_v2_cfe_exclusion_development_v1 as m


@pytest.mark.parametrize('source,f,approved,relaxed', [
    ('0.000001','0',False,False),       # q_raw == tau: inactive
    ('0.2','0.2',False,False),          # q_eff == f*w
    ('0.200002','0.2',True,False),      # q_eff == f*w + 2*tau
    ('0.200002000000000001','0.2',True,True),
    ('0','0',False,False),
])
def test_strict_boundaries_and_separate_contract(source,f,approved,relaxed):
    value = m.contradiction('1',source,'1',f)
    assert value['approved_contract_contradiction'] is approved
    assert value['local_relaxation_empty'] is relaxed
    assert value['absence_of_contradiction_is_feasibility'] is False
    q = Q(source) if Q(source) > Q('0.000001') else Q(0)
    assert Q(value['approved_contract_gap']) == q-Q(f)
    assert Q(value['contradiction_gap']) == q-Q(f)-Q('0.000002')


@pytest.mark.parametrize('args', [('.5','.2','.5',1.0), ('.5','.2','.5','1.01'),
    ('1.1','.2','.5','.2'), ('.5','1.1','.5','.2'), ('.5','.2','0','.2')])
def test_invalid_exact_domains(args):
    with pytest.raises(ValueError): m.contradiction(*args)


@pytest.fixture(scope='module')
def report():
    return m.audit()


def test_full_source_bound_catalog_and_independent_rational_oracle(report):
    assert len(report['cells']) == 1900
    assert len(report['arithmetic_groups']) == 300
    assert report['contradicted_cell_count'] == 1856
    assert sum(c['proof_sha256'] is None for c in report['cells']) == 44
    w, R, tau = Q(407772206073,500000000000), Q(118547425354783,5000000000000000), Q(1,1000000)
    for cell in report['cells']:
        a, f = Q(cell['alpha']), Q(cell['theta']['flexible_fraction'])
        raw = max(Q(0),w-R*w/a)
        q = raw if raw > tau else Q(0)
        group = report['arithmetic_groups'][cell['arithmetic_group_sha256']]
        assert Q(group['allocation']['raw_request']) == raw
        assert Q(group['allocation']['effective_request']) == q
        assert Q(group['contradiction_gap']) == q-f*w-2*tau
        assert group['approved_contract_contradiction'] == group['local_relaxation_empty'] == (q > f*w+2*tau)
        assert (cell['proof_sha256'] is not None) == (q > f*w+2*tau)
        assert cell['cell_sha256'] == m.io.digest(m.io.encode(dict(protocol_sha256=m.PINS[m.PROTOCOL],theta=cell['theta'],alpha=cell['alpha'])))
    assert len({c['cell_sha256'] for c in report['cells']}) == 1900
    # Non-f theta coordinates preserve distinct cell identities, sharing only arithmetic.
    assert len({c['arithmetic_group_sha256'] for c in report['cells'] if c['alpha_index'] == 10}) == 3
    witness = report['witness']
    assert witness['raw_source_hours'] == dict(power=354,workload=570)
    assert Q(witness['projected_workload']) == w
    assert 1-Q(witness['source_cfe']) == R
    assert len(witness['whole_enrollment_workload_projection']) == 168
    assert all(len(s['rows']) == 168 for s in witness['whole_enrollment_source_windows'].values())
    assert witness['normal_reference_reachability_proven'] is False


def test_factorized_overlay_preserves_roles_and_all_identities(report):
    coverage = report['coverage']
    affected = dict(training_lb=81537792,training_ub=8235316992,
        training_b6_actual=27179264,holdout=1856*14336*3)
    assert coverage['affected_identity_counts'] == affected
    assert coverage['direct_witness_planning_identity_counts'] == dict(training_lb=5568,training_ub=5568*101)
    for family, total in coverage['original_identity_counts'].items():
        assert total == affected[family]+coverage['remaining_identity_counts'][family]
    assert coverage['other_pair_planning_identity_counts']['training_lb'] == 81537792-5568
    assert coverage['other_pair_disposition'] == 'not_scheduled_due_to_parent_cell_proof'
    assert coverage['conditional_evaluation_disposition'] == 'prerequisite_false_no_training_UB; not_executed'
    assert coverage['omitted_identities'] == 0
    assert coverage['native_calls_avoided'] is None
    assert report['solver_calls'] == 0
    assert report['holdout_sources_evaluated'] is False
    assert all(report[key] is False for key in m.FLAGS)
    assert all(c['network_only_conclusion'] is None for c in report['cells'])
    assert all(set(c['planning_arm_disposition']) == set(m.ARMS) for c in report['cells'])


def test_fresh_report_reconstruction_and_reject_tampered_overlay(report,tmp_path):
    path = tmp_path/'report.json'
    raw = m.io.encode(report)
    m.io.write_new(path,raw)
    assert m.inspect(path,expected_sha256=m.io.digest(raw)) == report
    modified = copy.deepcopy(report)
    modified['cells'][0]['network_only_conclusion'] = 'excluded'
    bad = m.io.encode(modified)
    other = tmp_path/'tampered.json'
    m.io.write_new(other,bad)
    with pytest.raises(ValueError,match='reconstruction differs'):
        m.inspect(other,expected_sha256=m.io.digest(bad))
    with pytest.raises(ValueError,match='external exclusion pin'):
        m.inspect(other,expected_sha256=m.io.digest(raw))


@pytest.mark.parametrize('name', [m.PROTOCOL,m.COVERAGE,m.CATALOG,
    'src/rq2_joint_deliverability_boundary_v1/cfe_preallocation.py'])
def test_pinned_contract_source_catalog_and_implementation_drift(name,monkeypatch):
    original = m.io.read_stable
    def changed(path,cap):
        raw, stamp = original(path,cap)
        return (raw+b' ',stamp) if path == m.ROOT/name else (raw,stamp)
    monkeypatch.setattr(m.io,'read_stable',changed)
    with pytest.raises(ValueError,match='pinned proof input differs'): m.audit()


def test_threshold_and_named_hour_drift(monkeypatch):
    with monkeypatch.context() as patch:
        patch.setattr(m.mapping,'SERVICE_TOLERANCE',1e-5)
        with pytest.raises(ValueError,match='threshold drift'): m.audit()
    monkeypatch.setattr(m,'OFFSET',163)
    with pytest.raises(ValueError,match='witness identity differs'): m.audit()
