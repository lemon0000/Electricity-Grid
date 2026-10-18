from dataclasses import replace
from hashlib import sha256
from pathlib import Path
import json
import sys

import pytest
import yaml

from experiments import audit_rq2_scale_normal_h25_v1 as runner

CONFIG = runner.ROOT/'configs/rq2_scale_normal_h25_600s_development_v1.DRAFT.yaml'
PIN = 'a76b9a31843fbb98c2f1e4eb33c22e7aa7084b9609fd2607241bd962494b5066'


def test_concrete_declaration_is_one_normal_preserving_old_source():
    root, request, allocation, environment, pin = runner.read_declaration(CONFIG, PIN)
    plan = request.resource_plan
    report = runner.api.worker.source.budgets.check_single_normal_plan(plan)
    assert report['solver_calls'] == 1 and report['episode_tasks'] == 0
    assert report['reserved_total_wall_seconds'] == 1520
    assert request.budget.max_horizon == 25 and len(plan.normal.generator_uids) == 158
    assert request.specification.time_limit_seconds == 600
    assert not root.exists()
    assert sum(x.max_elapsed_seconds+x.max_quiescence_seconds for x in (allocation.execute, allocation.audit))+allocation.controller_seconds == 1386
    assert 1386-request.budget.max_seconds_per_solve == 786


def test_default_cli_only_inspects_without_creating_target(monkeypatch, capsys):
    def forbidden(*args, **kwargs): raise AssertionError('default CLI attempted execution')
    monkeypatch.setattr(runner.api, 'supervise_normal', forbidden)
    monkeypatch.setattr(sys, 'argv', ['inspect', '--declaration', str(CONFIG), '--expected-sha256', PIN,
        '--expected-script-sha256', sha256(Path(runner.__file__).read_bytes()).hexdigest()])
    runner.main()
    result = json.loads(capsys.readouterr().out)
    assert result['mode'] == 'read_only_diagnostic_inspection'
    assert result['execution_authorized'] is result['episode_execution_allowed'] is result['target_exists'] is False


@pytest.mark.parametrize('change', [
    {'formal_result':True}, {'episode_execution_allowed':True}, {'scope':'formal'},
    {'request_identity':'0'*64}, {'controller_identity':'0'*64},
    {'environment':{}}, {'request_sha256':'0'*64},
])
def test_modified_declaration_fails_before_execution(tmp_path, change):
    body = yaml.safe_load(CONFIG.read_text(encoding='utf-8'))
    body.update(change)
    raw = yaml.safe_dump(body).encode()
    path = tmp_path/'changed.yaml'
    path.write_bytes(raw)
    with pytest.raises(ValueError):
        runner.read_declaration(path, sha256(raw).hexdigest())


def test_existing_attempt_is_not_reused(monkeypatch, tmp_path):
    body = yaml.safe_load(CONFIG.read_text(encoding='utf-8'))
    target = tmp_path/'results/tables/rq2_scale_normal_h25_600s_attempt1_non_authoritative'
    target.mkdir(parents=True)
    body['task_root'] = str(target)
    raw = yaml.safe_dump(body).encode()
    declaration = tmp_path/'declaration.yaml'
    declaration.write_bytes(raw)
    monkeypatch.setattr(runner, 'ROOT', tmp_path)
    with pytest.raises(FileExistsError, match='one-shot'):
        runner.read_declaration(declaration, sha256(raw).hexdigest())


@pytest.mark.parametrize('change', [{'mip_relative_gap':1e-3}, {'time_limit_seconds':601.}, {'threads':2}])
def test_solver_contract_drift_rejected_before_identity(monkeypatch, change):
    read = runner.api.worker.transport.read_request
    def changed(*args, **kwargs):
        request = read(*args, **kwargs)
        return replace(request, specification=replace(request.specification, **change))
    monkeypatch.setattr(runner.api.worker.transport, 'read_request', changed)
    with pytest.raises(ValueError, match='preserve old H25'):
        runner.read_declaration(CONFIG, PIN)


@pytest.mark.parametrize('when', ['after_decode', 'during_execution'])
@pytest.mark.parametrize('which', ['runner', 'declaration', 'request', 'baseline'])
def test_outer_byte_drift_blocks_entry_or_success_publication(tmp_path, monkeypatch, capsys, when, which):
    # All mutation is confined to test-owned copies; no real candidate is edited.
    script = tmp_path/'runner.py'
    script.write_bytes(Path(runner.__file__).read_bytes())
    baseline = tmp_path/'baseline.yaml'
    baseline.write_bytes(runner.OLD_PATH.read_bytes())
    body = yaml.safe_load(CONFIG.read_text(encoding='utf-8'))
    packet = tmp_path/'request.json'
    packet.write_bytes(Path(body['request_path']).read_bytes())
    body['request_path'] = str(packet)
    declaration = tmp_path/'declaration.yaml'
    declaration.write_bytes(yaml.safe_dump(body).encode())
    declaration_pin = sha256(declaration.read_bytes()).hexdigest()
    script_pin = sha256(script.read_bytes()).hexdigest()
    monkeypatch.setattr(runner, '__file__', str(script))
    monkeypatch.setattr(runner, 'OLD_PATH', baseline)
    decoded = runner.read_declaration(declaration, declaration_pin)
    target = dict(runner=script, declaration=declaration, request=packet, baseline=baseline)[which]
    def mutate(): target.write_bytes(target.read_bytes()+b' ')
    def read(*args):
        if when == 'after_decode': mutate()
        return decoded
    called = []
    def execute(*args, **kwargs):
        called.append(True)
        mutate()
        return {'synthetic_test_only':True}
    monkeypatch.setattr(runner, 'read_declaration', read)
    monkeypatch.setattr(runner.api, 'supervise_normal', execute)
    monkeypatch.setattr(sys, 'argv', ['inspect', '--declaration', str(declaration),
        '--expected-sha256', declaration_pin, '--expected-script-sha256', script_pin, '--execute-development'])
    with pytest.raises(ValueError): runner.main()
    assert bool(called) is (when == 'during_execution')
    assert capsys.readouterr().out == ''
