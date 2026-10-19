from copy import copy, deepcopy
from dataclasses import asdict, replace
from datetime import timedelta
import json
import pickle

import pytest

from experiments import h1_current_outage_information_development_v1 as m
from tests.test_rq2_normal_h1_source_binding_v1 import supplied
from tests.test_rq2_continuous_grid_normal_v1 import fixture


@pytest.fixture
def scenario(supplied, monkeypatch):
    """Real assembly + outage prepare; explicit synthetic source and N replay seam.

    This does not manufacture an authenticated accepted N execution witness.
    """
    root, config, initial, state = supplied
    state['data'] = fixture(4).data
    single = m.source.windows.load_source_window
    observations = {0: None, 1: ('event-1', 'generator', 'G1'),
                    2: ('event-1', 'generator', 'G1'), 3: None}
    def load(kind, split, raw_start, hours, **kwargs):
        value = single(kind, split, raw_start, 1, **kwargs)
        if kind == 'power':
            rows = []
            for h in range(raw_start, raw_start+hours):
                row = single(kind, split, h, 1, **kwargs)['rows'][0]
                eid, kind_, uid = observations[h] or ('', '', '')
                row.update(block_id='a', active_event_id=eid,
                           active_component_type=kind_, active_component_uid=uid)
                rows.append(row)
            value.update(rows=rows, hours=hours,
                         chain=dict(split=split, outage_seed=kwargs['outage_seed'],
                                    source_start=0, source_end=3, block_ids=['a']),
                         continuous_power_source_hours=list(range(raw_start+1, raw_start+hours+1)))
        value.pop('window_identity')
        value['window_identity'] = m.outage.source._hash(value)
        return value
    monkeypatch.setattr(m.source.windows, 'load_source_window', load)
    protocol = m.outage.events.DisclosureProtocol((m.outage.events.OutageComponent('generator', 'G1'),),
        'current_n1_outage_overlay_revealed_before_current_action',
        'complete_current_n1_outage_overlay__no_hidden_same_hour_replacement', 'mechanism_assumption')
    monkeypatch.setattr(m, '_source_protocol', lambda *a: protocol)
    normal_calls = []
    def build(hours=1, start=1, caps=None):
        origin = replace(initial, power_raw_hour=start)
        before = None
        for h in range(hours):
            current = replace(origin, power_raw_hour=start+h, workload_raw_hour=h)
            observation = m.source.load_pinned_current(current, root, config_path=config)
            packet = m.source.h1.assemble_current_normal(observation.network, observation.row,
                observation.raw_workload, relative_hour=h, dc_bus=1,
                source_time_basis=observation.source_time_basis, before=before)
            after = m.normal.source._owned(m.normal.source.H1NormalBoundary,
                network_identity=packet.network.identity, completed_hours=h+1,
                units=(('G1', True, 20., h+1),), evidence_role='numerical_lex_candidate')
            before = after
        decision = m.normal._decision(packet, after)
        audit = dict(parent_declaration=dict(origin=asdict(origin), config_path=str(config),
            upstream_root=str(root), dc_bus=1), decision_identity=decision.decision_identity,
            normal_before=asdict(packet.before), normal_after=asdict(after),
            normal_input_identity=packet.input_identity, source_timestamp=packet.source_timestamp,
            source_time_basis=packet.source_time_basis)
        envelope = m.normal._owned(m.normal.H1NormalAuditEnvelope, decision=decision,
                                   audit_payload=m.io.encode(audit))
        normal_calls.clear()
        def replay(root_, **kwargs):
            normal_calls.append(kwargs)
            assert kwargs['completed_hours'] == hours
            return envelope
        monkeypatch.setattr(m.normal, 'prepare', replay)
        w = load('power', initial.split, start-1, hours+1,
                 outage_seed=initial.outage_seed, expected_config_sha256=initial.config_sha256)
        args = dict(expected_binding_sha256='a'*64, expected_terminal_sha256='b'*64,
                    completed_hours=hours, protocol=protocol,
                    repair_limits=(None,)*hours if caps is None else caps,
                    expected_outage_window_identity=w['window_identity'])
        return envelope, args
    return root, state, observations, protocol, build, normal_calls


def test_current_only_and_progress_bound(scenario):
    root, _, _, _, build, calls = scenario
    _, args = build(hours=2)
    result = m.prepare(root, **args)
    assert len(calls) == 2
    assert result.decision.normal.relative_hour == 1
    assert result.decision.outage.before.source_hour == 1
    assert result.decision.outage.after.source_hour == 2
    assert result.decision.outage.started is None
    decision = json.loads(result.decision.decision_bytes)
    assert set(decision) == {'normal', 'outage'}
    for hidden in (b'event-1', b'timestamp', b'raw_start', b'outage_seed', b'window_identity', b'steps', b'rows'):
        assert hidden not in result.decision.decision_bytes
    audit = json.loads(result.audit_payload)
    assert audit['current_source_correspondence_checked']
    assert not any(audit[k] for k in ('formal_result', 'formal_execution_ready',
        'repair_cap_source_registered', 'persistent_lane_owner_implemented',
        'full_192_hour_coverage_verified', 'detached_consumer_authenticated',
        'common_publication_verified', 'resource_admission', 'native_execution_authorized'))
    assert audit['outage_protocol_inventory_source_checked']
    for clone in (copy, deepcopy, pickle.dumps):
        with pytest.raises(TypeError): clone(result)


def test_future_and_audit_labels_cannot_change_current_decision(scenario):
    root, state, observations, _, build, _ = scenario
    _, args = build()
    first = m.prepare(root, **args)
    observations[2] = ('future-other', 'branch', 'not-in-current-inventory')
    observations[3] = ('another-future', 'generator', 'not-in-current-inventory')
    assert m.prepare(root, **args).decision.decision_identity == first.decision.decision_identity
    observations[1] = ('renamed-audit-id', 'generator', 'G1')
    state['data'] = replace(state['data'], hourly_points=tuple(
        replace(row, timestamp=row.timestamp+timedelta(days=10)) for row in state['data'].hourly_points))
    _, other_args = build()
    other = m.prepare(root, **other_args)
    assert other.decision.decision_bytes == first.decision.decision_bytes
    assert other.audit_payload != first.audit_payload


@pytest.mark.parametrize('hours', [0, 169, 192, True, 1.0])
def test_unsupported_progress_rejected_before_replay(scenario, hours):
    root, _, _, _, build, calls = scenario
    _, args = build()
    with pytest.raises(ValueError, match='progress'):
        m.prepare(root, **dict(args, completed_hours=hours))
    assert not calls


def test_future_prefix_pin_and_extra_cap_slots_rejected(scenario):
    root, _, _, _, build, _ = scenario
    _, later = build(hours=2)
    _, now = build()
    with pytest.raises(ValueError, match='window changed'):
        m.prepare(root, **dict(now, expected_outage_window_identity=later['expected_outage_window_identity']))
    with pytest.raises(ValueError, match='slot'):
        m.prepare(root, **dict(now, repair_limits=(None, None)))


@pytest.mark.parametrize('change', ['row', 'input', 'clock', 'progress', 'foreign_inventory'])
def test_correspondence_rejects_mismatched_inputs(scenario, monkeypatch, change):
    root, _, _, protocol, build, _ = scenario
    envelope, args = build()
    if change == 'row':
        original = m.outage.prepare
        def wrong(**kwargs):
            p = original(**kwargs)
            p.audit['rows'][-1]['system_load_mw'] = '999'
            return p
        monkeypatch.setattr(m.outage, 'prepare', wrong)
    elif change == 'foreign_inventory':
        args['protocol'] = replace(protocol, components=(m.outage.events.OutageComponent('generator','G1'),
                                                         m.outage.events.OutageComponent('generator','Z')))
    else:
        audit = json.loads(envelope.audit_payload)
        if change == 'input': audit['normal_input_identity'] = 'f'*64
        elif change == 'clock': audit['source_timestamp'] = 'invalid'
        else: audit['normal_after']['completed_hours'] = 2
        wrong = m.normal._owned(m.normal.H1NormalAuditEnvelope, decision=envelope.decision,
                                audit_payload=m.io.encode(audit))
        monkeypatch.setattr(m.normal, 'prepare', lambda *a, **kw: wrong)
    with pytest.raises(ValueError): m.prepare(root, **args)


def test_explicit_repair_cap_nameplate_and_source_boundary(scenario):
    root, _, observations, _, build, _ = scenario
    observations[0] = ('incoming', 'generator', 'G1')
    observations[1] = None
    _, args = build(caps=(10.,))
    result = m.prepare(root, **args)
    assert result.decision.outage.ended.observed_start_hour is None
    assert result.decision.outage.repaired_generator_return_limit_mw == 10.
    with pytest.raises(ValueError, match='nameplate'):
        m.prepare(root, **dict(args, repair_limits=(101.,)))
    # No public path accepts a detached Prefix or caller-chosen raw source hour.
    with pytest.raises(TypeError): m.prepare(root, **dict(args, prefix=object()))
    with pytest.raises(TypeError): m.prepare(root, **dict(args, raw_start=0))


@pytest.mark.parametrize('kind', ['normal', 'outage', 'implementation', 'current_source'])
def test_drift_before_return_rejected(scenario, monkeypatch, kind):
    root, _, _, _, build, _ = scenario
    _, args = build()
    if kind == 'current_source':
        def fail(*args, **kwargs):
            raise ValueError('current source changed during validation')
        monkeypatch.setattr(m.source, 'validate_pinned_current', fail)
    elif kind == 'implementation':
        identity = iter(['a'*64, 'b'*64])
        monkeypatch.setattr(m, 'implementation_identity', lambda: next(identity))
    elif kind == 'normal':
        original = m.normal.prepare
        count = []
        def changed(*a, **kw):
            value = original(*a, **kw); count.append(1)
            if len(count) == 2:
                return m.normal._owned(m.normal.H1NormalAuditEnvelope, decision=value.decision,
                                       audit_payload=value.audit_payload+b' ')
            return value
        monkeypatch.setattr(m.normal, 'prepare', changed)
    else:
        original = m.outage.prepare
        count = []
        def changed(**kw):
            value = original(**kw); count.append(1)
            if len(count) == 2: value.audit['window_identity'] = 'f'*64
            return value
        monkeypatch.setattr(m.outage, 'prepare', changed)
    with pytest.raises(ValueError, match='changed during'):
        m.prepare(root, **args)


def test_missing_origin_stays_unresolved(scenario, monkeypatch):
    root, _, _, _, build, _ = scenario
    envelope, args = build()
    audit = json.loads(envelope.audit_payload)
    audit['parent_declaration']['origin']['power_raw_hour'] = 0
    zero = m.normal._owned(m.normal.H1NormalAuditEnvelope, decision=envelope.decision,
                           audit_payload=m.io.encode(audit))
    monkeypatch.setattr(m.normal, 'prepare', lambda *a, **kw: zero)
    with pytest.raises(ValueError, match='prior boundary row required'):
        m.prepare(root, **args)


@pytest.mark.parametrize('pin', [True, 1, 'A'*64, 'a'*63])
def test_invalid_external_pin_rejected_before_replay(scenario, pin):
    root, _, _, _, build, calls = scenario
    _, args = build()
    with pytest.raises(ValueError, match='SHA256'):
        m.prepare(root, **dict(args, expected_terminal_sha256=pin))
    assert not calls


def test_current_legal_outage_change_is_decision_sensitive(scenario, monkeypatch):
    root, _, observations, protocol, build, _ = scenario
    protocol = replace(protocol, components=(m.outage.events.OutageComponent('branch', 'AC1'),)+protocol.components)
    monkeypatch.setattr(m, '_source_protocol', lambda *a: protocol)
    _, args = build()
    args['protocol'] = protocol
    down = m.prepare(root, **args)
    observations[1] = None
    _, args = build()
    args['protocol'] = protocol
    available = m.prepare(root, **args)
    assert down.decision.decision_identity != available.decision.decision_identity
    observations[1] = ('branch-event', 'branch', 'AC1')
    _, args = build()
    args['protocol'] = protocol
    branch = m.prepare(root, **args)
    assert branch.decision.normal.decision_bytes == down.decision.normal.decision_bytes
    assert branch.decision.outage.report.active_component.uid == 'AC1'
    assert branch.decision.decision_identity not in (down.decision.decision_identity, available.decision.decision_identity)


def test_real_source_inventory_rejects_islanding_extra_and_partial():
    config = m.generator.yaml.safe_load(m.generator.CONFIG.read_bytes())
    root = m.generator.ROOT/config['source']['grid_root']
    expected = m._source_protocol(root, m.outage.source.audit.DEFAULT_CONFIG,
        '0cca33dbfbd934881be3c4e375c76eb668c2ec41ff9bbc7392c2eb3947de18a5')
    assert len(expected.components) == 211
    assert sum(c.kind == 'generator' for c in expected.components) == 93
    assert sum(c.kind == 'branch' for c in expected.components) == 118
    # B11/C11 are real AC branches but intentionally ineligible for this source.
    data = m.source.rts.load_rts_gmlc_chronological_data(root)
    assert {'B11', 'C11'} <= {b.uid for b in data.branches}
    for uid in ('B11', 'C11'):
        extra = m.outage.events.OutageComponent('branch', uid)
        bad = replace(expected, components=tuple(sorted(expected.components+(extra,), key=lambda c: (c.kind,c.uid))))
        with pytest.raises(ValueError, match='complete frozen source'): m._check_protocol(bad, expected)
    with pytest.raises(ValueError, match='complete frozen source'):
        m._check_protocol(replace(expected, components=expected.components[:-1]), expected)
    m._check_protocol(expected, expected)
