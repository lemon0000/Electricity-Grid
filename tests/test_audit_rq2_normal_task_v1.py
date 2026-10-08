"""Read-only pinned declaration gates; no Job or solver execution."""
from hashlib import sha256
from pathlib import Path

import pytest
import yaml

from experiments import audit_rq2_normal_task_v1 as api


DECLARATION = Path('configs/rq2_normal_task_h25_development_v1.DRAFT.yaml')
PIN = '9a49cccf52e23d91a43511322a5abaf569e6cd2dfbf8d6db67b7d43d3c228aa6'


def test_fixed_h25_declaration_decodes_without_prepare_or_process(monkeypatch):
    def forbidden(*a, **k): raise AssertionError('inspection must not prepare/spawn/solve')
    monkeypatch.setattr(api.controller.worker.inputs, 'prepare_task_inputs', forbidden)
    monkeypatch.setattr(api.controller.process, 'normal_task_child', forbidden)
    root, request, budget, _, pin = api.read_declaration(DECLARATION, PIN)
    assert request.source.expected_scale == api.controller.worker.kernel.Rq2ModelScale(22275, 28004)
    assert budget.max_total_elapsed_seconds == 600 and len(pin) == 64
    assert root.name == 'rq2_normal_task_h25_attempt1_non_authoritative'


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
