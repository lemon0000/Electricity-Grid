from dataclasses import replace
from hashlib import sha256
import json

import pytest

from experiments import h1_attested_saved_hour_development_v1 as api
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver, saved, packet, spec
from tests.test_h1_native_export_guard_development_v1 import saved_origin
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_hour_replay_v3 as replay

LIMITS = replay.H1HourReplayLimits(232,891,1272)


@pytest.fixture
def synthetic_reports(saved):
    """Test-only copies; no native 5s capture or scientific witness is claimed."""
    pins = tuple(sha256(raw).hexdigest() for raw in saved[1])
    reports = []
    for raw in saved[1]:
        doc = json.loads(raw)
        assert doc['solver_options']['TimeLimit'] == 1.0
        doc['solver_options']['TimeLimit'] = 5.0
        reports.append(api.io.encode(doc))
    assert tuple(sha256(raw).hexdigest() for raw in saved[1]) == pins
    assert all(sha256(raw).hexdigest() != pin for raw,pin in zip(reports,pins))
    return reports


def make(tmp_path):
    return api.SavedHour(tmp_path/'hour', packet(), replace(spec(),time_limit_seconds=5.), LIMITS)


def fill(tmp_path, reports):
    hour = make(tmp_path)
    for raw in reports: hour.deliver(raw)
    return hour


def inspect(hour, terminal=None):
    return api.inspect(hour.root, hour.packet, hour.specification, hour.limits,
        expected_binding_sha256=hour.binding_sha256, expected_terminal_sha256=terminal)


def test_synthetic_complete_attested_hour_and_independent_reopen(tmp_path, synthetic_reports):
    hour = fill(tmp_path, synthetic_reports)
    projection, evidence = hour.finish()
    assert projection.canonical_locks == (20.,1.,20.)
    assert not projection.native_execution_authenticated
    assert not projection.exact_mathematical_certificate and not projection.published
    assert not projection.formal_result
    assert evidence['saved_hour_evidence_complete'] and evidence['saved_guard_receipts_recomputed']
    assert evidence['stages_recomputed'] == 3
    assert not evidence['resource_admission'] and not evidence['formal_execution_ready']
    assert inspect(hour, hour.terminal_sha256) == evidence
    assert not inspect(hour)['saved_hour_evidence_complete']
    bound = api.storage_bound(3)
    files = [p for p in hour.root.rglob('*') if p.is_file()]
    assert len(files) <= bound['files']
    assert sum(p.stat().st_size for p in files) <= bound['logical_bytes']


def test_real_original_rts_two_stage_prefix_attestation(tmp_path, saved_origin):
    hour = api.SavedHour(tmp_path/'real', saved_origin[1], replace(spec(),time_limit_seconds=5.), LIMITS)
    for index in range(2):
        raw = saved_origin[2][index][1]
        checked = hour.deliver(raw)
        assert checked['lock'].hex() == saved_origin[2][index][0]['lock_hex']
        assert (hour.stages.raw.root/f'{index:03d}'/'raw.bin').read_bytes() == raw
        assert (hour.attest/f'{index:03d}.commit.json').exists()
    assert not inspect(hour)['saved_hour_evidence_complete']
    with pytest.raises(ValueError, match='incomplete'): hour.finish()


@pytest.mark.parametrize('fault', ['guard_reject','guard_receipt','guard_receipt_after','audit','science','science_after',
    'mapping','mapping_after','outcome','commit_before','commit_after','post_commit_drift'])
def test_stage_failure_windows_retain_raw_and_do_not_advance(tmp_path, synthetic_reports, monkeypatch, fault):
    hour = make(tmp_path)
    raw = synthetic_reports[0]
    if fault == 'guard_reject':
        doc = json.loads(raw);doc['variables'] = 892;raw = api.io.encode(doc)
    calls = []
    original_audit = replay._audit_stage
    def audit(*args):
        calls.append(True)
        assert (hour.attest/'000.guard.json').exists()
        if fault == 'audit': raise ValueError('injected audit')
        return original_audit(*args)
    monkeypatch.setattr(replay, '_audit_stage', audit)
    original = api.io.write_metadata
    def write(path, doc):
        bad = ((fault == 'guard_receipt' and path.name == '000.guard.json')
            or (fault == 'science' and path.name == '000.science.json')
            or (fault == 'outcome' and path.name == 'outcome.json')
            or (fault == 'commit_before' and path.name == '000.commit.json'))
        if bad:
            path.write_bytes(b'{')
            raise OSError('injected partial write')
        pin = original(path,doc)
        if ((fault == 'guard_receipt_after' and path.name == '000.guard.json')
                or (fault == 'science_after' and path.name == '000.science.json')):
            raise OSError('lost receipt confirmation')
        if path.name == '000.commit.json':
            if fault == 'commit_after': raise OSError('lost commit confirmation')
            if fault == 'post_commit_drift': monkeypatch.setattr(replay,'implementation_identity',lambda: 'f'*64)
        return pin
    monkeypatch.setattr(api.io,'write_metadata',write)
    if fault in ('mapping','mapping_after'):
        original_bytes = api.io.write_new
        def mapping_write(path, raw):
            if path.name == '000.mapping.json':
                if fault == 'mapping_after': original_bytes(path,raw)
                else: path.write_bytes(b'{')
                raise OSError('mapping write/confirmation failed')
            return original_bytes(path,raw)
        monkeypatch.setattr(api.io,'write_new',mapping_write)
    with pytest.raises((ValueError,OSError)): hour.deliver(raw)
    assert hour.locks == () and hour.poisoned
    assert (hour.stages.raw.root/'000/raw.bin').read_bytes() == raw
    assert bool(calls) == (fault not in ('guard_reject','guard_receipt','guard_receipt_after'))
    if fault in ('guard_reject','guard_receipt','guard_receipt_after','audit','science','science_after','mapping','mapping_after'):
        assert not (hour.stages.raw.root/'000/outcome.json').exists()
    with pytest.raises(ValueError,match='poisoned'): hour.deliver(raw)
    with pytest.raises(ValueError,match='poisoned'): hour.finish()


@pytest.mark.parametrize('fault', ['fresh_replay','raw_terminal','timing_terminal',
                                 'hour_terminal_before','hour_terminal_after','projection','final_reader'])
def test_finish_failure_windows_never_release_projection(tmp_path, synthetic_reports, monkeypatch, fault):
    hour = fill(tmp_path, synthetic_reports)
    if fault == 'fresh_replay':
        (hour.stages.raw.root/'001/raw.bin').write_bytes(b'{}')
    write = api.io.write_metadata
    def metadata(path, doc):
        if ((fault == 'raw_terminal' and path.name == 'terminal.json')
                or (fault == 'timing_terminal' and doc.get('kind') == 'terminal')
                or (fault == 'hour_terminal_before' and path.name == 'attestation_terminal.json')):
            raise OSError('terminal write failed')
        pin = write(path,doc)
        if fault == 'hour_terminal_after' and path.name == 'attestation_terminal.json':
            raise OSError('terminal confirmation failed')
        return pin
    monkeypatch.setattr(api.io,'write_metadata',metadata)
    if fault == 'projection':
        original = api.io.write_new
        def payload(path, raw):
            if path.name == 'projection.bin': raise OSError('payload failed')
            return original(path,raw)
        monkeypatch.setattr(api.io,'write_new',payload)
    if fault == 'final_reader':
        monkeypatch.setattr(api,'inspect',lambda *a,**k: dict(saved_hour_evidence_complete=False, errors=['injected']))
    with pytest.raises((ValueError,OSError)): hour.finish()
    assert hour.terminal_sha256 is None and hour.poisoned
    with pytest.raises(ValueError,match='poisoned'): hour.deliver(synthetic_reports[0])
    with pytest.raises(ValueError,match='poisoned'): hour.finish()


@pytest.mark.parametrize('target', ['guard','mapping','science','commit','raw','projection','extra','timing',
    'attestation_binding.json','attestation_terminal.json','adapter_binding.json','raw_terminal'])
def test_fresh_reader_rejects_tampered_views(tmp_path, synthetic_reports, target):
    hour = fill(tmp_path, synthetic_reports)
    hour.finish()
    if target in ('guard','mapping','science','commit'):
        (hour.attest/f'000.{target}.json').write_bytes(b'{}')
    elif target == 'raw': (hour.stages.raw.root/'000/raw.bin').write_bytes(b'{}')
    elif target == 'projection': (hour.root/'projection.bin').write_bytes(b'{}')
    elif target == 'timing': (hour.stages.timing.root/'00005.json').write_bytes(b'{}')
    elif target.endswith('.json'): (hour.root/target).write_bytes(b'{}')
    elif target == 'raw_terminal': (hour.stages.raw.root/'terminal.json').write_bytes(b'{}')
    else: (hour.attest/'unexpected').write_bytes(b'')
    result = inspect(hour,hour.terminal_sha256)
    assert not result['saved_hour_evidence_complete']
    assert not result['saved_guard_receipts_recomputed']


def test_binding_failure_preserves_root_without_retry(tmp_path, monkeypatch):
    original = api.io.write_metadata
    def fail(path, doc):
        if path.name == 'attestation_binding.json':
            path.write_bytes(b'{')
            raise OSError('binding failure')
        return original(path,doc)
    monkeypatch.setattr(api.io,'write_metadata',fail)
    with pytest.raises(OSError): make(tmp_path)
    with pytest.raises(FileExistsError): make(tmp_path)


def test_rejection_mapping_receipt_is_retained_before_failure(tmp_path, synthetic_reports, monkeypatch):
    hour = make(tmp_path)
    original = replay._audit_stage
    expected = []
    def reject(*args):
        # A fault-injection receipt, not a numerical infeasibility witness.
        mapping = dict(original(*args)['generation_mapping'],candidate_accepted=False)
        expected.append(mapping)
        error = replay.H1ReportAuditRejected('injected rejected mapping')
        error.generation_mapping = mapping
        raise error
    monkeypatch.setattr(replay,'_audit_stage',reject)
    with pytest.raises(replay.H1ReportAuditRejected): hour.deliver(synthetic_reports[0])
    assert (hour.attest/'000.mapping.json').read_bytes() == api.io.encode(expected[0])
    assert not (hour.attest/'000.science.json').exists()
    assert not (hour.stages.raw.root/'000/outcome.json').exists()
    assert hour.locks == () and hour.poisoned


def test_mapping_cap_failure_stops_before_outcome(tmp_path, synthetic_reports, monkeypatch):
    hour = make(tmp_path)
    monkeypatch.setattr(api,'MAPPING_CAP',1)
    with pytest.raises(ValueError,match='mapping byte cap'): hour.deliver(synthetic_reports[0])
    assert hour.locks == () and hour.poisoned
    assert not (hour.stages.raw.root/'000/outcome.json').exists()


def test_existing_real_stage25_negative_mapping_exact_persistence(tmp_path, saved_origin):
    """Storage-only check of an already reviewed v3 receipt; no new prefix audit."""
    metadata, raw = saved_origin[2][25]
    assert sha256(raw).hexdigest() == '0bbffb4cb0ceb39354854ad7bbde60cdda62ecbf94ce74577091455021701588'
    mapping = metadata['generation_mapping']
    encoded = api.io.encode(mapping)
    assert len(encoded) == 1838 < api.MAPPING_CAP
    assert sha256(encoded).hexdigest() == '2f508ce4d138317d049cc08ec7e6e705b16890237f139929d7dab925e30bad13'
    assert mapping['normalization_applied'] and mapping['candidate_accepted']
    assert mapping['changes'] == [['generation[normal,0,201_CT_2]',
        '-0x1.7bd24a3baa1f4p-39','0x0.0p+0','0x1.7bd24a3baa1f4p-39']]
    assert dict(json.loads(raw)['assignment'])[mapping['changes'][0][0]] == mapping['changes'][0][1]
    hour = api.SavedHour(tmp_path/'receipt_only', saved_origin[1],
        replace(spec(),time_limit_seconds=5.), LIMITS)
    hour._mapping(25,mapping)
    assert api.io.read_stable(hour.attest/'025.mapping.json',api.MAPPING_CAP)[0] == encoded
    assert api.io.encode(metadata['generation_mapping']) == encoded
    assert hour.locks == () and not (hour.attest/'025.commit.json').exists()


def test_reader_detects_change_after_scientific_recomputation(tmp_path, synthetic_reports, monkeypatch):
    hour = fill(tmp_path, synthetic_reports)
    hour.finish()
    original = api.io.read_stable
    touched = []
    def change(path, cap):
        result = original(path, cap)
        if path.name == 'projection.bin' and not touched:
            touched.append(True)
            (hour.attest/'000.guard.json').write_bytes(b'{}')
        return result
    monkeypatch.setattr(api.io,'read_stable',change)
    result = inspect(hour,hour.terminal_sha256)
    assert result['stages_recomputed'] == 3
    assert not result['saved_hour_evidence_complete']
    assert any('view changed' in error for error in result['errors'])


@pytest.mark.parametrize('wrong', ['binding_pin','terminal_pin','packet','clock','spec','limits'])
def test_reader_requires_exact_external_inputs(tmp_path, synthetic_reports, wrong):
    hour = fill(tmp_path, synthetic_reports)
    hour.finish()
    p,specification,limits = hour.packet,hour.specification,hour.limits
    binding,terminal = hour.binding_sha256,hour.terminal_sha256
    if wrong == 'binding_pin': binding = 'f'*64
    if wrong == 'terminal_pin': terminal = 'f'*64
    if wrong == 'packet': p = packet(raw_workload='1')
    if wrong == 'clock':
        from datetime import timedelta
        from tests.test_rq2_continuous_grid_normal_v1 import fixture
        data = fixture(1).data
        p = packet(data,replace(data.hourly_points[0],timestamp=data.hourly_points[0].timestamp+timedelta(hours=1)))
        assert replay.request_key(p,specification,limits) == hour.key
        assert p.audit_identity != hour.packet.audit_identity
    if wrong == 'spec': specification = replace(specification,time_limit_seconds=4.)
    if wrong == 'limits': limits = replace(limits,max_constraints=1271)
    result = api.inspect(hour.root,p,specification,limits,
        expected_binding_sha256=binding,expected_terminal_sha256=terminal)
    assert not result['saved_hour_evidence_complete']


def test_reader_detects_packet_clock_drift_during_replay(tmp_path, synthetic_reports, monkeypatch):
    from datetime import timedelta
    from tests.test_rq2_continuous_grid_normal_v1 import fixture
    hour = fill(tmp_path, synthetic_reports)
    hour.finish()
    data = fixture(1).data
    changed = packet(data,replace(data.hourly_points[0],
        timestamp=data.hourly_points[0].timestamp+timedelta(hours=1)))
    original = replay.replay_stream
    def drift(*args,**kwargs):
        projection = original(*args,**kwargs)
        object.__setattr__(hour.packet,'source_timestamp',changed.source_timestamp)
        object.__setattr__(hour.packet,'audit_identity',changed.audit_identity)
        return projection
    monkeypatch.setattr(replay,'replay_stream',drift)
    result = inspect(hour,hour.terminal_sha256)
    assert not result['saved_hour_evidence_complete']
    assert any('input changed' in error for error in result['errors'])


@pytest.mark.parametrize('stages',[1,232])
def test_incremental_storage_accounting(stages):
    before,after = api.prior.storage_bound(stages),api.storage_bound(stages)
    assert after['logical_bytes']-before['logical_bytes'] == (3*stages+2)*2048+262144+stages*262144
    assert after['files']-before['files'] == 4*stages+3
    assert after['directories']-before['directories'] == 1
    assert not after['resource_admission']
