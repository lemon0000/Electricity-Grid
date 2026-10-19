import os
import pytest

from test_rq2_scale_selector_worker_v1 import request, actual_request, LIMIT
from src.rq2_joint_deliverability_boundary_v1 import scale_selector_controller as controller


def setup(tmp_path, factory=request):
    root = tmp_path/'task_non_authoritative'
    mib = 1024**2
    resources = controller.process.resources
    settings = dict(budget=controller.process.TaskProcessBudget(30., .1, 768*mib, 768*mib, 3.),
        host_budget=resources.HostResourceBudget(800*mib, 16*mib, (
            resources.DirectoryDemand('archive', str(root), 32*mib, 8*mib),
            resources.DirectoryDemand('scratch', str(root/'scratch'), 16*mib, 8*mib))),
        environment=dict(os.environ, OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1'),
        max_record_bytes=LIMIT)
    req = factory()
    pin = controller.controller_identity(root, req, **settings)
    return root, req, dict(settings, expected_controller_identity=pin)


@pytest.mark.parametrize('factory,calls', [(request, 3), (actual_request, 2)])
def test_real_controller_records_launch_and_quiet_result(tmp_path, factory, calls):
    root, req, settings = setup(tmp_path, factory)
    result = controller.supervise_selector(root, req, **settings)
    assert result['status'] == 'returned_unverified'
    assert result['inspection']['reported_solver_calls'] == calls
    assert result['observation']['whole_job_quiescent']
    launch = controller._read(root/'launch.json')
    assert launch['pid'] == result['observation']['pid']
    assert launch['creation_filetime'] == result['observation']['creation_filetime']
    assert not result['formal_result'] and not result['whole_task_resources_verified']
    with pytest.raises((ValueError, FileExistsError)):
        controller.supervise_selector(root, req, **settings)


def test_bad_controller_pin_creates_nothing(tmp_path):
    root, req, settings = setup(tmp_path)
    settings['expected_controller_identity'] = 'a'*64
    with pytest.raises(ValueError, match='drift'):
        controller.supervise_selector(root, req, **settings)
    assert not root.exists()


@pytest.mark.parametrize('name', ['intent.json', 'launch.json'])
def test_durable_record_failure_prevents_release(tmp_path, monkeypatch, name):
    root, req, settings = setup(tmp_path)
    original = controller._write
    def failed(path, body):
        if path.name == name:
            raise OSError('injected durable record failure')
        return original(path, body)
    monkeypatch.setattr(controller, '_write', failed)
    with pytest.raises(OSError, match='injected'):
        controller.supervise_selector(root, req, **settings)
    assert not (root/'selector_non_authoritative').exists()
    assert not (root/'result.json').exists()


@pytest.mark.parametrize('fault', ['result', 'extra', 'missing'])
def test_receipt_result_mismatch_cannot_publish_completion(tmp_path, monkeypatch, fault):
    root, req, settings = setup(tmp_path)
    original = controller._read
    def wrong(path, identity=None):
        body = original(path, identity)
        if path.name == 'receipt_non_authoritative.json':
            if fault == 'result': body['result_identity'] = 'a'*64
            elif fault == 'extra': body['unexpected'] = True
            else: del body['reported_status']
        return body
    monkeypatch.setattr(controller, '_read', wrong)
    with pytest.raises(ValueError, match='archived request/result|exact worker receipt'):
        controller.supervise_selector(root, req, **settings)
    assert controller._read(root/'observation.json')['whole_job_quiescent']
    assert not (root/'result.json').exists()


def test_changed_intent_before_release_is_rejected(tmp_path, monkeypatch):
    root, req, settings = setup(tmp_path)
    original = controller._write
    def tampered(path, body):
        answer = original(path, body)
        if path.name == 'launch.json':
            target = root/'intent.json'
            intent = controller._read(target)
            intent['planned_solver_calls'] += 1
            target.write_bytes(controller.worker.store._bytes(intent))
        return answer
    monkeypatch.setattr(controller, '_write', tampered)
    with pytest.raises(ValueError, match='retained record drift'):
        controller.supervise_selector(root, req, **settings)
    assert not (root/'selector_non_authoritative').exists()


def test_earliest_lease_failure_is_preserved(tmp_path, monkeypatch):
    root, req, settings = setup(tmp_path)
    registry = set(controller.local._REGISTRY)
    def failed(*args):
        raise OSError('early lease failure')
    monkeypatch.setattr(controller.local._Lease, '__init__', failed)
    with pytest.raises(OSError, match='early lease failure'):
        controller.supervise_selector(root, req, **settings)
    assert not root.exists()
    assert set(controller.local._REGISTRY) == registry


def test_result_readback_is_last_validation(tmp_path, monkeypatch):
    root, req, settings = setup(tmp_path)
    original = controller._write
    def final_write(path, body):
        answer = original(path, body)
        if path.name == 'result.json':
            def forbidden(*args, **kwargs):
                raise AssertionError('validation after terminal result')
            monkeypatch.setattr(controller, 'controller_identity', forbidden)
        return answer
    monkeypatch.setattr(controller, '_write', final_write)
    assert controller.supervise_selector(root, req, **settings)['status'] == 'returned_unverified'
