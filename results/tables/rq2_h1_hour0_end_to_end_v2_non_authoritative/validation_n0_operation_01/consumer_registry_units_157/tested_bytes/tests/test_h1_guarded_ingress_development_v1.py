import json

import pytest

from experiments import h1_guarded_ingress_development_v1 as api
from tests.test_h1_native_export_guard_development_v1 import saved_origin, stage_model
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver, saved, packet, spec


@pytest.mark.parametrize('bad', ['none','foreign','variables','constraints','terms','consumer','outcome'])
def test_guard_order_and_failure_raw_preservation(tmp_path, saved_origin, monkeypatch, bad):
    raw = saved_origin[2][0][1]
    doc = json.loads(raw)
    if bad == 'foreign': doc['assignment'][0][0] = 'foreign'
    if bad == 'variables': doc['variables'] = 892
    if bad == 'constraints': doc['constraints'] = 1273
    if bad == 'terms':
        doc['provenance']['ordered_native_objective_terms'].append(doc['provenance']['ordered_native_objective_terms'][0])
    raw = api.ingress.encode(doc)
    writer = api.SavedStages(tmp_path/'saved', 'a'*64, stages=1)
    called = []
    def consumer(fresh):
        assert (writer.raw.root/'000/raw_receipt.json').exists()
        assert (writer.raw.root/'000/raw.bin').read_bytes() == fresh == raw
        called.append(True)
        if bad == 'consumer': raise RuntimeError('scientific consumer')
        return 123
    write = api.ingress.write_metadata
    if bad == 'outcome':
        def fail(path, doc):
            if path.name == 'outcome.json': raise OSError('outcome failure')
            return write(path, doc)
        monkeypatch.setattr(api.ingress, 'write_metadata', fail)
    if bad == 'none':
        assert writer.deliver(0, raw, stage_model(saved_origin,0), consumer) == 123
        result = writer.finish()
        assert result['timing']['intervals_complete']
        assert not result['scientific_acceptance'] and not result['collector_integrated']
    else:
        with pytest.raises((ValueError, RuntimeError, OSError)):
            writer.deliver(0, raw, stage_model(saved_origin,0), consumer)
        assert (writer.raw.root/'000/raw.bin').read_bytes() == raw
        assert bool(called) == (bad in ('consumer','outcome'))
        assert not (writer.raw.root/'000/outcome.json').exists()
        with pytest.raises(ValueError, match='poisoned'): writer.finish()
        assert not api.timing.inspect(writer.timing.root,
            expected_binding_sha256=writer.timing.binding_sha256)['intervals_complete']
    bounds = api.storage_bound(1)
    files = [p for p in writer.root.rglob('*') if p.is_file()]
    assert len(files) <= bounds['files']
    assert sum(p.stat().st_size for p in files) <= bounds['logical_bytes']


def test_binding_drift_stops_before_consumer(tmp_path, saved_origin):
    writer = api.SavedStages(tmp_path/'saved', 'a'*64, stages=1)
    (writer.root/'adapter_binding.json').write_bytes(b'{}')
    with pytest.raises(ValueError, match='drift'):
        writer.deliver(0, saved_origin[2][0][1], stage_model(saved_origin,0),
                       lambda _: pytest.fail('must not consume'))


def test_transitive_timing_dependency_drift_stops_before_raw(tmp_path, saved_origin, monkeypatch):
    writer = api.SavedStages(tmp_path/'saved', 'a'*64, stages=1)
    dependency = tmp_path/'changed_timing.py'
    dependency.write_bytes(b'changed phase grammar')
    monkeypatch.setattr(api.timing.prior_timing, '__file__', str(dependency))
    with pytest.raises(ValueError, match='drift'):
        writer.deliver(0, saved_origin[2][0][1], stage_model(saved_origin,0),
                       lambda _: pytest.fail('must not consume'))
    assert not (writer.raw.root/'000').exists()


def test_real_scientific_two_stage_prefix(tmp_path, saved_origin):
    from src.rq2_joint_deliverability_boundary_v1 import normal_h1_full_job_v3 as job
    _, request = job.gates.verify_package(
        job.Path('configs/rq2_normal_h1_calibration_v3.OUTER.SHA256SUMS.json'),
        'e3acc7a6de1c1863ab64a8c1ae67ded9676e01c564a3d4ef2d0be29252f0edcf')
    # Same immutable scientific configuration as the saved capture.
    spec = job.Rq2SolverSpec(**request['work']['specification'])
    replay = job.collector.base.replay
    limits = replay.H1HourReplayLimits(**request['limits'])
    worker = api.SavedHour(tmp_path/'hour', saved_origin[1], spec, limits)
    for i in range(2):
        result = worker.deliver(saved_origin[2][i][1])
        assert result['lock'].hex() == saved_origin[2][i][0]['lock_hex']
    assert len(worker.locks) == 2
    assert not api.timing.inspect(worker.stages.timing.root,
        expected_binding_sha256=worker.stages.timing.binding_sha256)['intervals_complete']
    with pytest.raises(ValueError, match='incomplete scientific'): worker.finish()
    with pytest.raises(ValueError, match='poisoned'): worker.deliver(saved_origin[2][2][1])


@pytest.fixture
def synthetic_hour(tmp_path, saved):
    """Test-only metadata adaptation, NOT a native 5-second capture/witness.

    Keep original pinned archive and bytes unchanged. Only the declared option
    differs; numerical assignment/algebra remain the tiny retained test case.
    All actual guard and scientific audit functions run unmodified.
    """
    from dataclasses import replace
    from hashlib import sha256
    from src.rq2_joint_deliverability_boundary_v1 import normal_h1_hour_replay_v3 as replay
    original = tuple(saved[1])
    source_pins = tuple(sha256(raw).hexdigest() for raw in original)
    synthetic = []
    for raw in original:
        doc = json.loads(raw)
        assert doc['solver_options']['TimeLimit'] == 1.0
        doc['solver_options']['TimeLimit'] = 5.0
        synthetic.append(api.ingress.encode(doc))
    assert all(sha256(raw).hexdigest() != pin for raw, pin in zip(synthetic, source_pins))
    worker = api.SavedHour(tmp_path/'synthetic_hour', packet(),
        replace(spec(), time_limit_seconds=5.0), replay.H1HourReplayLimits(232,891,1272))
    for raw in synthetic: worker.deliver(raw)
    assert tuple(sha256(raw).hexdigest() for raw in saved[1]) == source_pins
    return worker


def test_synthetic_complete_hour_real_guard_and_scientific_replay(synthetic_hour):
    worker = synthetic_hour
    projection, evidence = worker.finish()
    assert projection.canonical_locks == (20.,1.,20.)
    assert not projection.native_execution_authenticated and not projection.formal_result
    assert not projection.exact_mathematical_certificate and not projection.published
    assert evidence['raw']['callback_sequence_complete']
    assert not evidence['guard_execution_durably_attested']
    assert evidence['timing']['intervals_complete']
    fresh = api.timing.inspect(worker.stages.timing.root,
        expected_binding_sha256=evidence['timing']['binding_sha256'],
        expected_terminal_sha256=evidence['timing']['terminal_sha256'])
    assert fresh == evidence['timing']
    assert not fresh['component_budget_verified']


@pytest.mark.parametrize('fault', ['fresh_replay','raw_terminal','timing_terminal'])
def test_complete_hour_finish_failures_stop_without_projection(synthetic_hour, monkeypatch, fault):
    worker = synthetic_hour
    if fault == 'fresh_replay':
        (worker.stages.raw.root/'001/raw.bin').write_bytes(b'{}')
    else:
        original = api.ingress.write_metadata
        def fail(path, doc):
            if ((fault == 'raw_terminal' and path.name == 'terminal.json')
                    or (fault == 'timing_terminal' and doc.get('kind') == 'terminal')):
                raise OSError('terminal fault')
            return original(path, doc)
        monkeypatch.setattr(api.ingress, 'write_metadata', fail)
    with pytest.raises((ValueError, OSError)): worker.finish()
    assert worker.poisoned
    with pytest.raises(ValueError, match='poisoned'): worker.finish()
    with pytest.raises(ValueError, match='poisoned'): worker.deliver(b'{}')


def test_scientific_identity_drift_after_audit_retains_raw_without_lock(tmp_path, saved_origin, monkeypatch):
    from src.rq2_joint_deliverability_boundary_v1 import normal_h1_full_job_v3 as job
    from src.rq2_joint_deliverability_boundary_v1 import normal_h1_hour_replay_v3 as replay
    from dataclasses import replace
    worker = api.SavedHour(tmp_path/'drift', saved_origin[1],
        replace(spec(),time_limit_seconds=5.0), replay.H1HourReplayLimits(232,891,1211))
    audit = replay._audit_stage
    def drift(*args):
        result = audit(*args)
        monkeypatch.setattr(replay, 'implementation_identity', lambda: 'f'*64)
        return result
    monkeypatch.setattr(replay, '_audit_stage', drift)
    raw = saved_origin[2][0][1]
    with pytest.raises(ValueError, match='drift after audit'): worker.deliver(raw)
    assert worker.locks == ()
    assert (worker.stages.raw.root/'000/raw.bin').read_bytes() == raw
    assert (worker.stages.raw.root/'000/outcome.json').exists()
    with pytest.raises(ValueError, match='poisoned'): worker.deliver(raw)
