from hashlib import sha256
import os
from pathlib import Path
import sys

import pytest

from test_rq2_episode_zero_face_v1 import inputs
from src.rq2_joint_deliverability_boundary_v1 import scale_episode_zero_face_worker as worker


def test_fixed_cli_execute_then_independent_audit_in_outer_jobs(tmp_path):
    req, arms, hours, settings = inputs(tmp_path)
    packet = worker.transport.EpisodeInputs(req, arms, hours, settings['budget'], settings['resource_plan'])
    raw = worker.transport.export_inputs(packet)
    path = tmp_path/'inputs.json'
    path.write_bytes(raw)
    root = tmp_path/'episode_non_authoritative'
    environment = dict(settings['environment'], TEMP=str(tmp_path), TMP=str(tmp_path))
    environment_pin = sha256(worker.controller.worker.store._bytes(environment)).hexdigest()
    process = worker.controller.process
    mib = 1024**2
    budget = process.TaskProcessBudget(90., .05, 1536*mib, 2304*mib, 3.)
    host = process.resources.HostResourceBudget(2304*mib, 16*mib,
        (process.resources.DirectoryDemand('test', str(tmp_path), 128*mib, 8*mib),))
    def invoke(mode, pins=None):
        receipt = tmp_path/(mode+'_non_authoritative.json')
        argv = [sys.executable, '-I', '-B', str(Path(worker.__file__).resolve()), '--mode', mode,
            '--request-path', str(path), '--expected-request-sha256', sha256(raw).hexdigest(),
            '--max-request-bytes', str(len(raw)), '--episode-root', str(root), '--receipt-path', str(receipt),
            '--episode-environment-directory', str(tmp_path), '--expected-environment-sha256', environment_pin,
            '--expected-implementation-identity', worker.implementation_identity()]
        if pins is not None:
            argv += ['--header-sha256', pins['header_sha256']]
            for name in ('intent', 'result'):
                for pin in pins[name+'_sha256s']: argv += ['--'+name+'-sha256', pin]
        args = dict(cwd=tmp_path, environment=environment, budget=budget, host_budget=host,
            expected_host_identity=process.resources.resource_identity(host))
        with process.normal_task_child(argv, **args,
                expected_process_identity=process.task_process_identity(argv, **args)) as owned:
            owned.release()
            observed = owned.wait()
            assert observed.reason == 'child_exited' and observed.exit_code == 0, observed
            assert observed.whole_job_quiescent
        return worker.controller._read(receipt)
    executed = invoke('execute')
    assert executed['outcome']['completed_hours'] == 1
    pins = executed['outcome']
    archived_before = {str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest()
                       for p in root.rglob('*') if p.is_file()}
    audited = invoke('audit', pins)
    assert audited['outcome']['completed_hours'] == 1
    assert audited['outcome']['solver_calls_by_auditor'] == 0
    assert audited['outcome']['selected_phase_chains_replayed'] == 4
    assert audited['audit_pins']['header_sha256'] == pins['header_sha256']
    assert not audited['formal_result'] and not audited['whole_task_resources_verified']
    assert archived_before == {str(p.relative_to(root)): sha256(p.read_bytes()).hexdigest()
                               for p in root.rglob('*') if p.is_file()}


@pytest.mark.parametrize('fault', ['implementation', 'environment', 'request', 'resume', 'mode'])
def test_refusal_before_episode_creation(tmp_path, monkeypatch, fault):
    req, arms, hours, settings = inputs(tmp_path)
    raw = worker.transport.export_inputs(worker.transport.EpisodeInputs(
        req, arms, hours, settings['budget'], settings['resource_plan']))
    path = tmp_path/'inputs.json'
    path.write_bytes(raw)
    root = tmp_path/'episode_non_authoritative'
    args = dict(mode='execute', request_path=path, expected_request_sha256=sha256(raw).hexdigest(),
        max_request_bytes=len(raw), episode_root=root, receipt_path=tmp_path/'result_non_authoritative.json',
        episode_environment_directory=tmp_path,
        expected_environment_sha256=sha256(worker.controller.worker.store._bytes(worker.episode_environment(tmp_path))).hexdigest(),
        expected_implementation_identity=worker.implementation_identity())
    if fault == 'implementation': args['expected_implementation_identity'] = '0'*64
    elif fault == 'environment': args['expected_environment_sha256'] = '0'*64
    elif fault == 'request': args['expected_request_sha256'] = '0'*64
    elif fault == 'resume': args['header_sha256'] = '0'*64
    else: args['mode'] = 'resume'
    with pytest.raises(ValueError): worker.run_worker(**args)
    assert not root.exists() and not args['receipt_path'].exists()


@pytest.mark.parametrize('field', ['request_path', 'episode_environment_directory'])
@pytest.mark.parametrize('mode', ['execute', 'audit'])
def test_transport_and_scratch_cannot_enter_evidence_root(tmp_path, field, mode):
    root = tmp_path/'evidence'
    args = dict(mode=mode, request_path=tmp_path/'input.json', expected_request_sha256='0'*64,
        max_request_bytes=1, episode_root=root, receipt_path=tmp_path/'result_non_authoritative.json',
        episode_environment_directory=tmp_path, expected_environment_sha256='0'*64,
        expected_implementation_identity='0'*64, header_sha256='0'*64 if mode == 'audit' else None)
    args[field] = root/'inside'
    with pytest.raises(ValueError, match='outside evidence root'): worker.run_worker(**args)
    assert not root.exists()


@pytest.mark.parametrize('target', ['selector', 'process', 'native'])
def test_audit_execution_guard_blocks_and_restores_on_exception(tmp_path, monkeypatch, target):
    req, arms, hours, settings = inputs(tmp_path)
    raw = worker.transport.export_inputs(worker.transport.EpisodeInputs(
        req, arms, hours, settings['budget'], settings['resource_plan']))
    path = tmp_path/'inputs.json'
    path.write_bytes(raw)
    targets = dict(selector=(worker.controller, 'supervise_selector'),
        process=(worker.controller.process, 'normal_task_child'),
        native=(worker.episode.tx.scale.native, '_solve'))
    originals = {key: getattr(obj, name) for key, (obj, name) in targets.items()}
    def attempt(*args, **kwargs):
        obj, name = targets[target]
        return getattr(obj, name)()
    monkeypatch.setattr(worker.replay, 'audit_episode', attempt)
    receipt = tmp_path/'guard_non_authoritative.json'
    with pytest.raises(RuntimeError, match='offline worker execution forbidden'):
        worker.run_worker(mode='audit', request_path=path,
            expected_request_sha256=sha256(raw).hexdigest(), max_request_bytes=len(raw),
            episode_root=tmp_path/'absent_non_authoritative', receipt_path=receipt,
            episode_environment_directory=tmp_path,
            expected_environment_sha256=sha256(worker.controller.worker.store._bytes(
                worker.episode_environment(tmp_path))).hexdigest(),
            expected_implementation_identity=worker.implementation_identity(), header_sha256='0'*64)
    assert not receipt.exists()
    assert not (tmp_path/'absent_non_authoritative').exists()
    assert all(getattr(obj, name) is originals[key] for key, (obj, name) in targets.items())
