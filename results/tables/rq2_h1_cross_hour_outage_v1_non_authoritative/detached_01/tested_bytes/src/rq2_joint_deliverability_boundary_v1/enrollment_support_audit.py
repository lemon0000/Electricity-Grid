"""Source coverage for a proposed finite enrollment, without choosing a contract.

Retain every enrollment start. Coverage is not dispatch, recovery feasibility,
service success, failure, or a lower bound on unknown outcome probability.
"""
from fractions import Fraction


def enumerate_enrollment_support(chains, *, enrollment_hours, followup_hours, stride_hours):
    for name, number, minimum in (('enrollment_hours', enrollment_hours, 1),
                                  ('followup_hours', followup_hours, 0), ('stride_hours', stride_hours, 1)):
        if type(number) is not int or number < minimum:
            raise ValueError('invalid explicit hour count: ' + name)
    windows = []
    for kind in ('power', 'workload'):
        seen = set()
        intervals = []
        for chain in chains[kind]:
            identity = chain['chain_id']
            if type(identity) is not str or not identity or identity in seen or chain['split'] not in ('training', 'holdout'):
                raise ValueError('duplicate chain or invalid split')
            seen.add(identity)
            seed = chain.get('outage_seed')
            if ((kind == 'power' and (type(seed) is not int or seed < 0))
                or (kind == 'workload' and seed is not None)):
                raise ValueError('power requires explicit seed; workload has no outage seed')
            first, last = chain['source_start'], chain['source_end']
            if type(first) is not int or type(last) is not int or not 0 <= first <= last:
                raise ValueError('invalid source clock')
            if type(chain['row_count']) is not int or chain['row_count'] != last-first+1:
                raise ValueError('source chain is not a complete interval')
            if any(split == chain['split'] and previous_seed == seed and first <= end and start <= last
                   for split, previous_seed, start, end in intervals):
                raise ValueError('overlapping chains within one marginal split/seed')
            intervals.append((chain['split'], seed, first, last))
            for start in range(first, last-enrollment_hours+2, stride_hours):
                enrollment_end = start+enrollment_hours-1
                needed_end = enrollment_end+followup_hours
                observed_end = min(needed_end, last)
                windows.append({'kind': kind, 'split': chain['split'], 'chain_id': identity,
                    'outage_seed': chain.get('outage_seed'), 'source_start': start,
                    'enrollment_end_inclusive': enrollment_end,
                    'needed_end_inclusive': needed_end, 'observed_end_inclusive': observed_end,
                    'available_followup_hours': observed_end-enrollment_end,
                    'missing_followup_hours': needed_end-observed_end,
                    'followup_source_complete': needed_end <= last})
    summaries = {}
    for split in ('training', 'holdout'):
        margins = {kind: [w for w in windows if w['kind'] == kind and w['split'] == split]
                   for kind in ('power', 'workload')}
        counts = {kind: len(rows) for kind, rows in margins.items()}
        full = {kind: sum(w['followup_source_complete'] for w in rows) for kind, rows in margins.items()}
        denominator = counts['power']*counts['workload']
        complete = full['power']*full['workload']
        summaries[split] = {'enrollment_windows': counts, 'followup_complete_windows': full,
            'all_enrollment_pairs_retained': denominator, 'both_followup_sources_complete': complete,
            'power_followup_only_missing': (counts['power']-full['power'])*full['workload'],
            'workload_followup_only_missing': full['power']*(counts['workload']-full['workload']),
            'both_followup_sources_missing': (counts['power']-full['power'])*(counts['workload']-full['workload']),
            'at_least_one_followup_source_missing': denominator-complete,
            'source_missing_fraction_under_uniform_product': str(Fraction(denominator-complete, denominator))
                if denominator else None}
    return {'status': 'DRAFT_NONAUTHORITATIVE', 'enrollment_hours': enrollment_hours,
        'followup_hours': followup_hours, 'stride_hours': stride_hours, 'windows': windows,
        'summary': summaries, 'scientific_parameters_registered': False,
        'coverage_is_service_outcome': False, 'missing_tail_is_automatic_unresolved_outcome': False,
        'joint_clock_observed': False, 'continuous_dispatch_verified': False, 'formal_result': False}
