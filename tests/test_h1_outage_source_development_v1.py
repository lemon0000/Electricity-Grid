from copy import deepcopy
from datetime import datetime, timedelta, timezone
from hashlib import sha256

import pytest

from experiments import h1_outage_source_development_v1 as m


def protocol():
    return m.events.DisclosureProtocol(
        tuple(sorted((m.events.OutageComponent('generator', '123_CT_1'),
                      m.events.OutageComponent('branch', 'b')), key=lambda c: (c.kind, c.uid))),
        'current_n1_outage_overlay_revealed_before_current_action',
        'complete_current_n1_outage_overlay__no_hidden_same_hour_replacement', 'mechanism_assumption')


def window(observations):
    rows = []
    for h, obs in enumerate(observations):
        eid, kind, uid = obs if obs else ('', '', '')
        rows.append(dict(split='training', outage_seed='7', source_hour=str(h), block_id='a',
                         timestamp=(datetime(2020, 1, 1, tzinfo=timezone.utc)+timedelta(hours=h)).isoformat(),
                         active_event_id=eid, active_component_type=kind, active_component_uid=uid))
    value = dict(kind='power', split='training', raw_start=0, hours=len(rows), outage_seed=7,
                 rows=rows, chain=dict(split='training', outage_seed=7, source_start=0,
                                      source_end=len(rows)-1, block_ids=['a']),
                 config_sha256='a'*64, package_manifest_sha256='b'*64)
    value['window_identity'] = m.source._hash(value)
    return value


G = ('e', 'generator', '123_CT_1')
B = ('f', 'branch', 'b')


def rebuild(w, caps=None, **changes):
    args = dict(split='training', raw_start=1, hours=len(w['rows'])-1, seed=7,
                protocol=protocol(), repair_limits=caps or (None,)*(len(w['rows'])-1))
    args.update(changes)
    return m._rebuild(w, **args)


def test_trip_continue_repair_and_unknown_incoming():
    p = rebuild(window([None, G, G, None]), (None, None, 12.5))
    assert p.origin.active is None
    assert p.steps[0].started.observed_start_hour == 1
    assert p.steps[1].started is None and p.steps[1].ended is None
    assert p.steps[2].ended.component.uid == '123_CT_1'
    assert p.steps[2].repaired_generator_return_limit_mw == 12.5
    incoming = rebuild(window([G, G]))
    assert incoming.origin.active.observed_start_hour is None
    assert incoming.steps[0].after.active.observed_start_hour is None
    assert not p.formal_result and not p.detached_consumer_authenticated
    assert not p.normal_source_correspondence_verified


@pytest.mark.parametrize('obs,caps', [([G, None], (None,)), ([None, G], (2,)),
    ([B, None], (2,)), ([G, G], (2,)), ([G, None], (True,)), ([G, None], (float('nan'),))])
def test_repair_cap_exact_applicability(obs, caps):
    with pytest.raises(ValueError):
        rebuild(window(obs), caps)


@pytest.mark.parametrize('obs,caps', [([G, ('f', 'generator', '123_CT_1')], (None,)),
    ([G, ('e', 'branch', 'b')], (2,)), ([G, None, G], (2, None)),
    ([None, ('e', '', '123_CT_1')], (None,)),
    ([None, ('e', 'generator', 'unknown')], (None,))])
def test_bad_observations(obs, caps):
    with pytest.raises(ValueError):
        rebuild(window(obs), caps)


@pytest.mark.parametrize('field,value', [('raw_start', 0), ('raw_start', True), ('hours', 193),
    ('hours', False), ('split', 'test'), ('seed', True)])
def test_parameter_rejection(field, value):
    with pytest.raises(ValueError):
        rebuild(window([None, G]), **{field: value})


@pytest.mark.parametrize('change', ['split', 'seed', 'hour', 'block', 'clock', 'naive', 'chain', 'missing'])
def test_continuity_and_left_boundary(change):
    w = window([None, G])
    if change == 'split': w['rows'][0]['split'] = 'holdout'
    elif change == 'seed': w['rows'][0]['outage_seed'] = '8'
    elif change == 'hour': w['rows'][0]['source_hour'] = '1'
    elif change == 'block': w['rows'][0]['block_id'] = 'other'
    elif change == 'clock': w['rows'][0]['timestamp'] = w['rows'][1]['timestamp']
    elif change == 'naive': w['rows'][0]['timestamp'] = '2020-01-01T00:00:00'
    elif change == 'chain': w['chain']['source_start'] = 1
    else: w['rows'].pop(0)
    with pytest.raises(ValueError):
        rebuild(w, hours=1, repair_limits=(None,))


def test_audit_identity_excluded_and_current_sensitive():
    w = window([None, G, G])
    p = rebuild(w)
    other = deepcopy(w)
    for row in other['rows']:
        row['timestamp'] = (datetime.fromisoformat(row['timestamp'])+timedelta(days=90)).isoformat()
        if row['active_event_id']: row['active_event_id'] = 'renamed'
    assert rebuild(other).decision_identity == p.decision_identity
    assert rebuild(window([None, B, B])).decision_identity != p.decision_identity
    assert rebuild(window([G, None]), (1,)).decision_identity != rebuild(window([G, None]), (2,)).decision_identity


def prepare(w):
    return m.prepare(split='training', raw_start=1, hours=len(w['rows'])-1, outage_seed=7,
                     protocol=protocol(), repair_limits=(None,)*(len(w['rows'])-1),
                     expected_window_identity=w['window_identity'], expected_config_sha256='a'*64)


@pytest.mark.parametrize('drift', ['none', 'row', 'identity', 'implementation'])
def test_prepare_rechecks_before_return(monkeypatch, drift):
    w = window([None, G])
    calls = []
    def load(*args, **kwargs):
        calls.append((args, kwargs))
        v = deepcopy(w)
        if len(calls) == 2:
            if drift == 'row': v['rows'][1]['active_event_id'] = 'changed'
            if drift == 'identity': v['window_identity'] = 'c'*64
        return v
    monkeypatch.setattr(m.source, 'load_source_window', load)
    identities = iter(['a', 'b' if drift == 'implementation' else 'a'])
    monkeypatch.setattr(m, 'implementation_identity', lambda: next(identities))
    if drift == 'none':
        assert prepare(w).audit['implementation_identity'] == 'a'
        assert calls[0][0] == ('power', 'training', 0, 2)
    else:
        with pytest.raises(ValueError): prepare(w)
    assert len(calls) == 2


def test_real_pinned_source_trip_continuation_repair():
    config_sha = '0cca33dbfbd934881be3c4e375c76eb668c2ec41ff9bbc7392c2eb3947de18a5'
    assert sha256(m.source.audit.DEFAULT_CONFIG.read_bytes()).hexdigest() == config_sha
    w = m.source.load_source_window('power', 'training', 0, 13, outage_seed=20260822,
                                    expected_config_sha256=config_sha)
    p = m.prepare(split='training', raw_start=1, hours=12, outage_seed=20260822,
                  protocol=protocol(), repair_limits=(None,)*11+(10,),
                  expected_window_identity=w['window_identity'], expected_config_sha256=config_sha)
    assert p.origin.active is None
    assert p.steps[0].started.component.uid == '123_CT_1'
    assert p.steps[10].after.active is not None
    assert p.steps[11].after.active is None
    assert p.audit['source_role'].startswith('synthetic_')
