import pytest

from src.rq2_joint_deliverability_boundary_v1.enrollment_support_audit import enumerate_enrollment_support as audit


def chains():
    return {kind: [dict(chain_id=kind+':training', split='training', source_start=start,
                       source_end=start+9, row_count=10, outage_seed=47 if kind == 'power' else None)]
            for kind, start in [('power', 0), ('workload', 100)]}


def test_all_enrollment_starts_retained_and_distinct_source_clocks():
    result = audit(chains(), enrollment_hours=6, followup_hours=3, stride_hours=2)
    assert len(result['windows']) == 6
    assert [r['source_start'] for r in result['windows']] == [0, 2, 4, 100, 102, 104]
    assert [r['missing_followup_hours'] for r in result['windows']] == [0, 1, 3, 0, 1, 3]
    summary = result['summary']['training']
    assert summary['all_enrollment_pairs_retained'] == 9
    assert summary['both_followup_sources_complete'] == 1
    assert summary['power_followup_only_missing'] == summary['workload_followup_only_missing'] == 2
    assert summary['both_followup_sources_missing'] == 4
    assert summary['source_missing_fraction_under_uniform_product'] == '8/9'
    assert not result['coverage_is_service_outcome']


def test_endpoint_zero_followup_and_empty_support():
    result = audit(chains(), enrollment_hours=10, followup_hours=0, stride_hours=24)
    assert len(result['windows']) == 2
    assert result['summary']['training']['both_followup_sources_complete'] == 1
    assert result['summary']['holdout']['source_missing_fraction_under_uniform_product'] is None
    assert not audit(chains(), enrollment_hours=11, followup_hours=24, stride_hours=24)['windows']


def test_followup_never_borrows_from_next_split_or_chain():
    data = chains()
    data['power'].append(dict(chain_id='later', split='holdout', source_start=10, source_end=19, row_count=10, outage_seed=47))
    result = audit(data, enrollment_hours=10, followup_hours=3, stride_hours=1)
    assert all(r['missing_followup_hours'] == 3 for r in result['windows'])
    assert result['summary']['training']['all_enrollment_pairs_retained'] == 1
    assert result['summary']['holdout']['all_enrollment_pairs_retained'] == 0


@pytest.mark.parametrize('bad', [dict(enrollment_hours=0), dict(enrollment_hours=True),
    dict(followup_hours=-1), dict(stride_hours=0), dict(stride_hours=1.5)])
def test_invalid_counts_refused(bad):
    with pytest.raises(ValueError):
        audit(chains(), **dict(dict(enrollment_hours=6, followup_hours=3, stride_hours=2), **bad))


@pytest.mark.parametrize('fault', ['duplicate', 'clock', 'gap', 'split', 'missing_seed', 'bool_seed', 'overlap'])
def test_invalid_chain_refused(fault):
    data = chains()
    if fault == 'duplicate': data['power'].append(dict(data['power'][0]))
    if fault == 'clock': data['power'][0]['source_start'] = True
    if fault == 'gap': data['power'][0]['row_count'] = 9
    if fault == 'split': data['power'][0]['split'] = 'other'
    if fault == 'missing_seed': data['power'][0].pop('outage_seed')
    if fault == 'bool_seed': data['power'][0]['outage_seed'] = True
    if fault == 'overlap': data['power'].append(dict(data['power'][0], chain_id='other'))
    with pytest.raises(ValueError):
        audit(data, enrollment_hours=6, followup_hours=3, stride_hours=2)


def test_current_frozen_sources_rebuilt_with_all_enrollment_starts():
    from experiments.audit_rq2_enrollment_support_v1 import run
    report = run(168, 24, 24)
    for split, total, complete in [('training', 14644, 14040), ('holdout', 14336, 13743)]:
        power = [w for w in report['windows'] if w['kind'] == 'power' and w['split'] == split]
        workload = [w for w in report['windows'] if w['kind'] == 'workload' and w['split'] == split]
        # Independent enumeration of pairs, not the implementation's product formula.
        pairs = [(p, w) for p in power for w in workload]
        assert len(pairs) == total
        assert sum(p['missing_followup_hours'] == w['missing_followup_hours'] == 0 for p, w in pairs) == complete
        assert all(w['enrollment_end_inclusive']-w['source_start']+1 == 168 for w in power+workload)
        assert report['summary'][split]['all_enrollment_pairs_retained'] == total
    assert len(report['raw_above_one_source_hours']['holdout']) == 6
    assert report['summary']['holdout']['raw_above_one_workload_windows'] == {
        'enrollment': 10, 'observed_followup_only': 1, 'either': 11}
    assert not report['registered_joint_coupling'] and report['solver_calls'] == 0
