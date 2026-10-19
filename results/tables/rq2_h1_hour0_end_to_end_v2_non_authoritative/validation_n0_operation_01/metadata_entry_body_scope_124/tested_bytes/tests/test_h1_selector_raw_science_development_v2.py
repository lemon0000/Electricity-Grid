"""Explicit v2 wiring against unchanged v1 and saved-record numerical oracles."""
import json
import sys

import pytest

from experiments import h1_selector_raw_science_development_v2 as m
from tests import test_h1_selector_raw_science_development_v1 as producer
from tests.test_h1_origin_selector_incremental_replay_development_v1 import static_identity_bookends, pins
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver


@pytest.fixture(scope='module')
def captures(tmp_path_factory):
    base = tmp_path_factory.mktemp('selector_raw_v2_non_authoritative')
    samples = []
    for lane in (producer.fixtures.R, producer.fixtures.A):
        f, d, b, args = producer.inputs(lane)
        records = ()
        for index in range(len(m.selector.stage_labels(f, lane))):
            outputs = []
            for label, bridge in (('legacy', producer.m), ('incremental', m)):
                path = base / (lane.role + str(index) + '_' + label)
                with pytest.MonkeyPatch.context() as patch:
                    instances = producer.install(patch, path, lane)
                    out = bridge._run_stage(path, f, d, b, records,
                        expected_key=bridge.request_key(f, d, b, records, **args), **args)
                assert instances[0].apply_calls == instances[0].post_calls == instances[0].close_calls == 1
                outputs.append(out)
            assert outputs[0]['selector_record'] == outputs[1]['selector_record']
            assert outputs[0]['lock_hex'] == outputs[1]['lock_hex']
            assert outputs[0]['selector_chain_complete'] == outputs[1]['selector_chain_complete']
            samples.append((path, f, d, b, args, records, outputs[1]))
            records += (outputs[1]['selector_record'],)
    return samples


def audit(sample):
    path, f, d, b, args, records, _ = sample
    terminal = json.loads((path / 'terminal.json').read_bytes())
    observations = json.loads((path / 'observations.json').read_bytes())['observations']
    return m._audit_stage((path / 'capture/native_raw/000/raw.bin').read_bytes(),
        (path / 'postsolve.json').read_bytes(), f, d, b, records, **args,
        expected_key=terminal['request_key'], expected_binding=terminal['binding_sha256'],
        expected_export=terminal['export_sha256'], observations=observations)


def test_explicit_raw_bridge_all_prefixes_records_and_final_carry(captures, no_solver):
    assert m.__file__.endswith('h1_selector_raw_science_development_v2.py')
    for sample in captures:
        _, f, d, b, args, prefix, original = sample
        result = audit(sample)
        assert result == {k: v for k, v in original.items() if k != 'bridge_terminal_sha256'}
        combined = prefix + (result['selector_record'],)
        replay = m.selector.replay_development_records(f, d, b, combined, **args,
            expected_identity=m.selector.input_identity(f, d, b, lane=args['lane'], power=args['power']),
            expected_policy_identity=b.policy_identity, expected_report_sha256=pins(combined))
        assert replay.verified_stages == len(combined)
        assert replay.errors in ((), ('incomplete_stage_chain',))
        assert result['lock_hex'] == replay.canonical_lock_hex[-1]
        assert result['selector_chain_complete'] == (replay.next_candidate is not None)
        assert not any(result[field] for field in m.FLAGS)


def test_raw_audit_numerically_replays_each_old_stage_once_and_new_stage_once(captures, no_solver):
    previous = sys.getprofile()
    code = m.selector.native._replay.__code__
    for sample in captures:
        calls = []
        def profile(frame, event, arg):
            if event == 'call' and frame.f_code is code:
                calls.append(frame.f_locals['purpose'])
        try:
            sys.setprofile(profile)
            audit(sample)
        finally:
            sys.setprofile(previous)
        assert len(calls) == len(sample[5]) + 1
        assert len(set(calls)) == len(calls)


@pytest.mark.parametrize('fault', ['frame', 'before', 'selector', 'specification', 'limits', 'helper', 'bridge', 'threshold'])
def test_raw_return_bookend_rejects_drift_after_append(captures, monkeypatch, no_solver, fault):
    sample = captures[1]
    _, f, _, b, args, _, _ = sample
    original = m.incremental.append_verified_stage
    resets = []

    def append(*a, **kwargs):
        result = original(*a, **kwargs)
        if fault in ('frame', 'before', 'selector', 'specification', 'limits'):
            target, field, value = {
                'frame': (f, 'normal_network_identity', '0' * 64),
                'before': (b, 'previous_audit_identity', '0' * 64),
                'selector': (args['selector'], 'relative_gap', 1e-3),
                'specification': (args['specification'], 'threads', 2),
                'limits': (args['limits'], 'max_variables', args['limits'].max_variables + 1),
            }[fault]
            resets.append((target, field, getattr(target, field)))
            object.__setattr__(target, field, value)
        elif fault == 'helper':
            monkeypatch.setattr(m.incremental, 'revalidate_prefix', lambda *a, **k: (15.,))
        elif fault == 'bridge':
            monkeypatch.setattr(m, '_derived_record', lambda *a, **k: None)
        else:
            monkeypatch.setattr(m.selector.physical, 'TOLERANCE', 1e-3)
        return result

    monkeypatch.setattr(m.incremental, 'append_verified_stage', append)
    try:
        with pytest.raises((ValueError, TypeError)):
            audit(sample)
    finally:
        for target, field, value in resets:
            object.__setattr__(target, field, value)


@pytest.mark.parametrize('entry', ['request', 'run'])
@pytest.mark.parametrize('fault', ['frame', 'selector_helper', 'threshold'])
def test_prefix_return_drift_stops_before_allocation(tmp_path, monkeypatch, no_solver, entry, fault):
    f, d, b, args = producer.inputs(producer.fixtures.R)
    key = m.request_key(f, d, b, (), **args)
    original = m.incremental.verify_prefix
    resets = []
    def verify(*a, **kw):
        token = original(*a, **kw)
        if fault == 'frame':
            resets.append((f, 'normal_network_identity', f.normal_network_identity))
            object.__setattr__(f, 'normal_network_identity', '0' * 64)
        elif fault == 'selector_helper':
            monkeypatch.setattr(m.selector, '_context', lambda *a, **k: {})
        else:
            monkeypatch.setattr(m.selector.physical, 'TOLERANCE', 1e-3)
        return token
    monkeypatch.setattr(m.incremental, 'verify_prefix', verify)
    root = tmp_path / 'must_not_allocate'
    try:
        with pytest.raises((ValueError, TypeError, KeyError)):
            if entry == 'request':
                m.request_key(f, d, b, (), **args)
            else:
                m._run_stage(root, f, d, b, (), expected_key=key, **args)
    finally:
        for target, field, value in resets:
            object.__setattr__(target, field, value)
    assert not root.exists()
