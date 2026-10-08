from dataclasses import asdict, replace
from copy import deepcopy

import pytest

from test_rq2_source_pair_v1 import declaration as old_declaration, supplied
from src.rq2_joint_deliverability_boundary_v1 import source_pair_preallocated as api


def declaration():
    return api.PreallocatedPairDeclaration(**asdict(old_declaration()))


def test_binds_exact_request_and_surplus_to_one_current_allowance(supplied):
    r = api.prepare_source_pair(declaration())
    assert r['status'] == 'staged_preallocated' and len(r['hours']) == 3
    for h in r['hours']:
        assert h['allocation']['allowance'] == '1/25'
        assert h['allocation']['raw_request'] == '4/25'
        assert h['allocation']['compatible_surplus'] == '0'
    supplied['power']['rows'][1]['cfe_call_fraction'] = '0.2'
    changed = api.prepare_source_pair(replace(declaration(), hourly_cfe_target='0.5'))
    assert changed['hours'][1]['allocation']['compatible_surplus'] == '3/25'
    assert changed['pair_identity'] != r['pair_identity']
    assert not r['executable_episode_input'] and not r['formal_result']


def test_future_source_change_preserves_current_allowance_identity(supplied):
    before = api.prepare_source_pair(declaration())
    supplied['power']['rows'][2]['cfe_call_fraction'] = '0.1'
    after = api.prepare_source_pair(declaration())
    assert before['hours'][0]['allocation_identity'] == after['hours'][0]['allocation_identity']
    assert before['hours'][0]['allocation'] == after['hours'][0]['allocation']
    assert before['pair_identity'] != after['pair_identity']


@pytest.mark.parametrize('raw', ['1.01', '0.00000000000001'])
def test_unresolved_source_retained_and_whole_packet_not_staged(supplied, raw):
    supplied['workload']['rows'][1]['workload_fraction'] = raw
    r = api.prepare_source_pair(declaration())
    assert r['status'] == 'unresolved' and r['hours'] is None
    assert len(r['rows']) == 3 and r['rows'][1]['allocation'] is None
    assert r['rows'][1]['workload_source_row']['workload_fraction'] == raw


def test_new_and_old_declarations_cannot_cross_interfaces(supplied):
    with pytest.raises(ValueError): api.prepare_source_pair(old_declaration())
    with pytest.raises(ValueError): api.old.prepare_source_pair(declaration())


@pytest.mark.parametrize('fault', ['pin', 'count', 'clock'])
def test_source_correspondence_failures_rejected(supplied, fault):
    if fault == 'pin': supplied['power']['window_identity'] = 'f'*64
    if fault == 'count': supplied['power']['rows'].pop()
    if fault == 'clock': supplied['power']['rows'][1]['source_hour'] = '9'
    with pytest.raises(ValueError): api.prepare_source_pair(declaration())
