"""Read-only pinned declaration gates; no Job or solver execution."""
from hashlib import sha256
from pathlib import Path

import pytest
import yaml

from experiments import audit_rq2_normal_task_stream_numeric_v1 as api


DECLARATION = Path('configs/rq2_normal_task_stream_numeric_h25_development_v1.DRAFT.yaml')
PIN = '6cc200dad82041d33ac83277d9067c32e63bc9d0d56428b949081a46b5243b0c'


def test_fixed_h25_declaration_decodes_without_prepare_or_process(monkeypatch):
    def forbidden(*a, **k): raise AssertionError('inspection must not prepare/spawn/solve')
    monkeypatch.setattr(api.controller.worker.inputs, 'prepare_task_inputs', forbidden)
    monkeypatch.setattr(api.controller.process, 'normal_task_child', forbidden)
    root, request, budget, _, pin = api.read_declaration(DECLARATION, PIN)
    assert request.source.expected_scale == api.controller.worker.kernel.Rq2ModelScale(22275, 28004)
    assert budget.max_total_elapsed_seconds == 600 and len(pin) == 64
    assert root.name == 'rq2_normal_task_stream_numeric_h25_attempt1_non_authoritative'


def test_successor_preserves_old_source_solver_and_resource_budgets():
    old = yaml.safe_load(Path('configs/rq2_normal_task_stream_fast_h25_development_v1.DRAFT.yaml').read_bytes())
    new = yaml.safe_load(DECLARATION.read_bytes())
    assert new['budget'] == old['budget']
    assert new['environment'] == old['environment']
    for field in ('source', 'specification', 'execution_budget', 'max_record_bytes', 'max_replay_bytes',
                  'expected_source_request_identity', 'expected_assembly_identity', 'expected_binding_identity',
                  'expected_source_implementation_identity', 'expected_binding_implementation_identity'):
        assert new['request'][field] == old['request'][field]
    for field in ('expected_normal_execution_identity', 'expected_source_execution_identity',
                  'expected_declared_execution_identity', 'expected_replay_identity'):
        assert new['request'][field] != old['request'][field]


@pytest.mark.parametrize('fault', ['hash', 'duplicate', 'authority', 'extra', 'controller_pin', 'solver_scope'])
def test_bad_declaration_refused(tmp_path, fault):
    body = yaml.safe_load(DECLARATION.read_bytes())
    if fault == 'authority': body['formal_result'] = True
    if fault == 'extra': body['resume'] = True
    if fault == 'controller_pin': body['expected_controller_identity'] = '0'*64
    if fault == 'solver_scope': body['request']['specification']['threads'] = 2
    raw = yaml.safe_dump(body).encode()
    if fault == 'duplicate': raw += b'formal_result: false\n'
    path = tmp_path/'declaration.yaml'
    path.write_bytes(raw)
    with pytest.raises((ValueError, TypeError)):
        api.read_declaration(path, '0'*64 if fault == 'hash' else sha256(raw).hexdigest())
