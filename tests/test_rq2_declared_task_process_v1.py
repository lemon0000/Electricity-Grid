from dataclasses import replace
import os
import sys

import pytest

from src.rq2_joint_deliverability_boundary_v1 import declared_task_process as api

pytestmark = pytest.mark.skipif(os.name != 'nt', reason='Windows Job lifecycle')
MIB = 1024**2


def budget():
    envelope = api.contract.TaskEnvelope('episode', 8000, 60, 256*MIB, 32*MIB, 16*MIB, 1, 10000, 10000)
    return api.DeclaredTaskProcessBudget('a'*64, envelope, 7200., .02, 128*MIB, 256*MIB, 2.)


def arguments(tmp_path, code='pass', b=None):
    b = budget() if b is None else b
    host = api.legacy.resources.HostResourceBudget(256*MIB, 16*MIB,
        (api.legacy.resources.DirectoryDemand('scratch', str(tmp_path), MIB, 8*MIB),))
    argv = [sys.executable, '-I', '-B', '-c', code]
    kwargs = dict(cwd=tmp_path, environment=dict(os.environ, TEMP=str(tmp_path), TMP=str(tmp_path)), budget=b,
        host_budget=host, expected_host_identity=api.legacy.resources.resource_identity(host))
    return argv, dict(kwargs, expected_process_identity=api.task_process_identity(argv, **kwargs))


def test_full_budget_survives_legacy_ceiling_without_long_wait(tmp_path):
    argv, kwargs = arguments(tmp_path)
    with api.declared_task_child(argv, **kwargs) as owner:
        assert type(owner._budget) is api.DeclaredTaskProcessBudget
        assert owner._budget.max_elapsed_seconds == 7200.
        owner._started -= 3601.  # Inject age; the child only executes pass.
        owner.release()
        report = owner.wait()
        assert report.reason == 'child_exited' and report.exit_code == 0
        assert report.elapsed_seconds >= 3601 and report.whole_job_quiescent
        assert not report.whole_task_resources_verified and not report.formal_result


def test_full_declared_deadline_stops_short_owned_child(tmp_path):
    argv, kwargs = arguments(tmp_path, 'import time; time.sleep(20)')
    with api.declared_task_child(argv, **kwargs) as owner:
        owner.release()
        owner._started -= 7201.
        report = owner.wait()
        assert report.reason == 'task_deadline_stop' and report.whole_job_quiescent


@pytest.mark.parametrize('field,value', [('max_elapsed_seconds', 7999.), ('max_elapsed_seconds', float('nan')),
    ('max_elapsed_seconds', True), ('max_job_commit_bytes', 257*MIB), ('sample_interval_seconds', 2.),
    ('max_quiescence_seconds', 6.), ('resource_contract_identity', 'bad')])
def test_declared_budget_still_enforces_envelope_and_native_limits(field, value):
    with pytest.raises(ValueError): replace(budget(), **{field: value})


def test_legacy_ceiling_and_exact_type_gate_unchanged(tmp_path):
    with pytest.raises(ValueError, match='development ceiling'):
        api.legacy.TaskProcessBudget(3601., .02, 128*MIB, 256*MIB, 2.)
    argv, kwargs = arguments(tmp_path)
    kwargs.pop('expected_process_identity')
    with pytest.raises(ValueError, match='typed task process'):
        api.legacy.task_process_identity(argv, **kwargs)


def test_full_job_commit_is_not_shrunk_by_validation_projection(tmp_path):
    argv, kwargs = arguments(tmp_path)
    kwargs.pop('expected_process_identity')
    kwargs['host_budget'] = replace(kwargs['host_budget'], additional_commit_bytes=255*MIB)
    kwargs['expected_host_identity'] = api.legacy.resources.resource_identity(kwargs['host_budget'])
    with pytest.raises(ValueError, match='cover task Job'): api.task_process_identity(argv, **kwargs)


@pytest.mark.parametrize('field,value', [('max_elapsed_seconds', 7100.), ('resource_contract_identity', 'b'*64)])
def test_full_identity_changes_even_when_validation_projection_is_same(tmp_path, field, value):
    argv, kwargs = arguments(tmp_path)
    pin = kwargs.pop('expected_process_identity')
    kwargs['budget'] = replace(kwargs['budget'], **{field: value})
    assert api.task_process_identity(argv, **kwargs) != pin


def test_initialization_interrupt_releases_inherited_owner(tmp_path, monkeypatch):
    import _winapi
    argv, kwargs = arguments(tmp_path, 'import time; time.sleep(20)')
    initialize = api._DeclaredTaskChild._initialize
    captured = {}
    def interrupted(owner, *args, **settings):
        initialize(owner, *args, **settings)
        captured['owner'] = owner
        captured['handle'] = _winapi.DuplicateHandle(_winapi.GetCurrentProcess(), owner._child._process,
            _winapi.GetCurrentProcess(), 0, False, _winapi.DUPLICATE_SAME_ACCESS)
        raise KeyboardInterrupt('injected initialization interruption')
    monkeypatch.setattr(api._DeclaredTaskChild, '_initialize', interrupted)
    try:
        with pytest.raises(KeyboardInterrupt):
            with api.declared_task_child(argv, **kwargs): pass
        assert captured['owner']._child is None
        assert _winapi.WaitForSingleObject(captured['handle'], 1000) == 0
    finally:
        if 'handle' in captured: _winapi.CloseHandle(captured['handle'])
