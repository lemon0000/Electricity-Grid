from copy import deepcopy
from hashlib import sha256
from pathlib import Path

import pytest

from src.rq2_joint_deliverability_boundary_v1 import source_window as window


def supplied():
    rows = [dict(split='training', outage_seed='7', source_hour=str(h), block_id='a' if h < 24 else 'b',
                 cfe_call_fraction='0.125000', timestamp=f'raw-{h}') for h in range(48)]
    chains = [dict(split='training', outage_seed=7, source_start=0, source_end=47, block_ids=['a', 'b'])]
    return rows, chains


def test_cross_block_keeps_raw_values_and_copy():
    rows, chains = supplied()
    selected, chain = window._select(rows, chains, 'power', 'training', 23, 3, 7)
    assert [r['source_hour'] for r in selected] == ['23', '24', '25']
    assert selected[0]['cfe_call_fraction'] == '0.125000'
    rows[23]['cfe_call_fraction'] = '9'
    chains[0]['block_ids'].clear()
    assert selected[0]['cfe_call_fraction'] == '0.125000' and chain['block_ids'] == ['a', 'b']


@pytest.mark.parametrize('split,start,hours,seed', [
    ('holdout',0,2,7), ('training',0,2,8), ('training',47,2,7), ('training',-1,2,7),
    ('training',0,0,7), ('training',False,2,7), ('training',0,True,7), ('training',0,2,True)])
def test_invalid_selection(split, start, hours, seed):
    with pytest.raises(ValueError):
        window._select(*supplied(), 'power', split, start, hours, seed)


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'wrong_block'])
def test_missing_duplicate_and_foreign_block(change):
    rows, chains = supplied()
    if change == 'missing':
        rows.pop(24)
    elif change == 'duplicate':
        rows.append(deepcopy(rows[24]))
    else:
        rows[24]['block_id'] = 'foreign'
    with pytest.raises(ValueError):
        window._select(rows, chains, 'power', 'training', 23, 3, 7)


def test_workload_above_one_is_retained():
    rows = [dict(split='holdout', source_relative_hour='821', block_id='w', workload_fraction='1.25')]
    chains = [dict(split='holdout', source_start=821, source_end=821, block_ids=['w'])]
    selected, _ = window._select(rows, chains, 'workload', 'holdout', 821, 1, None)
    assert selected[0]['workload_fraction'] == '1.25'
    with pytest.raises(ValueError):
        window._select(rows, chains, 'workload', 'holdout', 821, 1, 7)


@pytest.fixture(scope='module')
def actual():
    config = window.audit.DEFAULT_CONFIG
    digest = sha256(config.read_bytes()).hexdigest()
    return {kind: window.load_source_window(kind, 'training', 0, 25,
        outage_seed=20260822 if kind == 'power' else None, expected_config_sha256=digest)
        for kind in ('power', 'workload')}


def test_actual_pinned_packages_cross_day(actual):
    power, workload = actual['power'], actual['workload']
    assert power['continuous_power_source_hours'] == list(range(1, 26))
    assert power['rows'][24]['timestamp'] == '2020-01-02T00:00:00+00:00'
    assert {r['outage_seed'] for r in power['rows']} == {'20260822'}
    assert [int(r['source_relative_hour']) for r in workload['rows']] == list(range(25))
    assert workload['continuous_power_source_hours'] is None
    assert workload['chain']['trace_identity_basis']['normalization_method'] == 'divide_by_training_segment_peak_occupancy'
    for result in actual.values():
        assert len(result['rows']) == 25
        assert not any(result[k] for k in ('formal_result','registered_coupling','shared_observed_clock',
            'continuous_dispatch_verified','workload_fraction_clipped','executable_episode_input'))
        copied = deepcopy(result)
        identity = copied.pop('window_identity')
        assert identity == window._hash(copied)


def test_config_pin_rejected_before_loading(monkeypatch):
    def fail(*args):
        raise AssertionError('must not load source')
    monkeypatch.setattr(window.audit, '_load_config', fail)
    with pytest.raises(ValueError, match='hash mismatch'):
        window.load_source_window('power', 'training', 0, 25, outage_seed=20260822,
            expected_config_sha256='0'*64)


@pytest.mark.parametrize('split,start', [('training',4343), ('holdout',4392)])
def test_actual_excluded_cross_split_source_hours_rejected(split, start):
    digest = sha256(window.audit.DEFAULT_CONFIG.read_bytes()).hexdigest()
    with pytest.raises(ValueError, match='one verified same-split'):
        window.load_source_window('power', split, start, 2, outage_seed=20260822,
            expected_config_sha256=digest)


def test_actual_holdout_keeps_training_normalization():
    digest = sha256(window.audit.DEFAULT_CONFIG.read_bytes()).hexdigest()
    result = window.load_source_window('workload', 'holdout', 821, 25, expected_config_sha256=digest)
    assert {r['split'] for r in result['rows']} == {'holdout'}
    assert result['chain']['source_start'] == 821
    assert result['chain']['trace_identity_basis']['normalization_method'] == 'divide_by_training_segment_peak_occupancy'
    assert result['chain']['trace_identity_basis']['training_peak_requested_gpu_occupancy']
