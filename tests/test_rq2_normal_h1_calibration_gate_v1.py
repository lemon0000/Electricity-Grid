from copy import deepcopy
from hashlib import sha256
from pathlib import Path
from types import SimpleNamespace

import pytest

from src.rq2_joint_deliverability_boundary_v1 import normal_h1_calibration_gate as api
from src.rq2_joint_deliverability_boundary_v1 import normal_h1_full_job as job


@pytest.fixture
def package(tmp_path, monkeypatch):
    monkeypatch.setattr(api, 'ROOT', tmp_path)
    monkeypatch.setattr(api, 'required_code_members', lambda: ('module.py',))
    (tmp_path/'module.py').write_bytes(b'# pinned test-only module\n')
    order = (('operating_cost', None), *(('commitment', str(i)) for i in range(73)),
             *(('generation', str(i)) for i in range(158)))
    work = SimpleNamespace(hours=1, stage_order=order)
    monkeypatch.setattr(job, '_validate_request', lambda request: (work, None, None, None, None, None))
    def write(name, value):
        path = tmp_path/name
        path.write_bytes(api._bytes(value))
        return sha256(path.read_bytes()).hexdigest()
    request = dict(root=str(tmp_path/'run_non_authoritative'), source_declaration=dict(split='training'))
    request_pin = write('request.json', request)
    lease = dict(schema=api.SCHEMA, request_sha256=request_pin, root=request['root'], claim_path='claim.json', one_shot=True)
    lease_pin = write('lease.json', lease)
    evidence_pin = write('evidence.json', dict(status='PRE_SEAL_AUDIT', findings_closed=True, official_verdict=None))
    outer = dict(schema=api.SCHEMA, state='SEALED_READY_FOR_INDEPENDENT_REVIEW', request_path='request.json',
        request_sha256=request_pin, lease_path='lease.json', lease_sha256=lease_pin, claim_path='claim.json',
        preseal_evidence_path='evidence.json', preseal_evidence_sha256=evidence_pin,
        members={name: sha256((tmp_path/name).read_bytes()).hexdigest()
                 for name in ('module.py', 'request.json', 'lease.json', 'evidence.json')})
    inner = dict(schema=api.SCHEMA, files=dict(outer['members']), source_closure=['module.py'])
    inner_pin = write('inner.json', inner)
    outer.update(inner_path='inner.json', inner_sha256=inner_pin)
    outer['members']['inner.json'] = inner_pin
    outer_pin = write('outer.json', outer)
    review = dict(schema=api.SCHEMA, outer_sha256=outer_pin, verdict='PASS', reviewer='test-only-independent',
                  independent_read_only=True, fresh_official_context=True)
    authority = dict(schema=api.SCHEMA, outer_sha256=outer_pin, request_sha256=request_pin,
        action='single_hour_native_calibration_once', user_instruction='test-only authority fixture',
        root=request['root'], retry_authorized=False)
    gate = dict(outer_path=str(tmp_path/'outer.json'), outer_sha256=outer_pin,
        review_path=str(tmp_path/'review.json'), review_sha256=write('review.json', review),
        authority_path=str(tmp_path/'authority.json'), authority_sha256=write('authority.json', authority))
    return SimpleNamespace(root=tmp_path, work=work, request=request, outer=outer, gate=gate,
                           review=review, authority=authority, write=write)


def test_exact_gate_consumes_once_and_independent_worker_verifies(package):
    p = package
    assert api.verify_gate(p.gate)[1] == p.request
    assert not (p.root/'claim.json').exists()
    with pytest.raises(FileNotFoundError): api.verify_consumed(p.gate)
    assert api.consume(p.gate) == p.request
    assert api.verify_consumed(p.gate) == p.request
    with pytest.raises(FileExistsError): api.consume(p.gate)


@pytest.mark.parametrize('fault', ['code', 'source_omission', 'not_sealed', 'request', 'lease', 'evidence',
    'outer_pin', 'review_pin', 'authority_pin', 'review_not_pass', 'review_old_outer', 'review_not_fresh',
    'authority_no_instruction', 'authority_other_action', 'authority_root', 'authority_retry', 'short_inventory',
    'holdout', 'extra_gate', 'traversal'])
def test_no_consumption_on_invalid_seal_review_or_authority(package, fault):
    p = package
    if fault == 'code': (p.root/'module.py').write_bytes(b'changed')
    elif fault == 'source_omission': p.outer['members'].pop('module.py')
    elif fault == 'not_sealed': p.outer['state'] = 'DRAFT_NONAUTHORITATIVE'
    elif fault == 'request': (p.root/'request.json').write_bytes(b'{}')
    elif fault == 'lease': (p.root/'lease.json').write_bytes(b'{}')
    elif fault == 'evidence': (p.root/'evidence.json').write_bytes(b'{}')
    elif fault.endswith('_pin'): p.gate[fault.replace('_pin', '_sha256')] = '0'*64
    elif fault == 'review_not_pass': p.review['verdict'] = 'PRE_SEAL_FINDINGS_CLOSED'
    elif fault == 'review_old_outer': p.review['outer_sha256'] = '0'*64
    elif fault == 'review_not_fresh': p.review['fresh_official_context'] = False
    elif fault == 'authority_no_instruction': p.authority['user_instruction'] = ' '
    elif fault == 'authority_other_action': p.authority['action'] = 'develop_only'
    elif fault == 'authority_root': p.authority['root'] += '_other'
    elif fault == 'authority_retry': p.authority['retry_authorized'] = True
    elif fault == 'short_inventory': p.work.stage_order = p.work.stage_order[:3]
    elif fault == 'holdout':
        p.request['source_declaration']['split'] = 'holdout'
        p.write('request.json', p.request)
    elif fault == 'extra_gate': p.gate['review_ready'] = True
    elif fault == 'traversal': p.outer['members']['../outside.py'] = '0'*64
    if fault in ('source_omission', 'not_sealed', 'traversal'):
        p.gate['outer_sha256'] = p.write('outer.json', p.outer)
    if fault.startswith('review_') and not fault.endswith('_pin'):
        p.gate['review_sha256'] = p.write('review.json', p.review)
    if fault.startswith('authority_') and not fault.endswith('_pin'):
        p.gate['authority_sha256'] = p.write('authority.json', p.authority)
    with pytest.raises(ValueError): api.consume(p.gate)
    assert not (p.root/'claim.json').exists()


def test_launch_failure_does_not_allow_retry_or_root_relocation(package, monkeypatch):
    p = package
    calls = []
    def fail(*a, **k):
        calls.append(1)
        raise RuntimeError('launch failed after durable consumption')
    monkeypatch.setattr(job, '_run_development_job', fail)
    with pytest.raises(ValueError): job.run_job(p.root/'other', p.request, gate=p.gate)
    assert not (p.root/'claim.json').exists()
    with pytest.raises(RuntimeError): job.run_job(p.request['root'], p.request, gate=p.gate)
    with pytest.raises(FileExistsError): job.run_job(p.request['root'], p.request, gate=p.gate)
    assert calls == [1]


def test_partial_claim_is_permanently_consumed(package):
    p = package
    (p.root/'claim.json').write_bytes(b'{')
    with pytest.raises(FileExistsError): api.consume(p.gate)
    with pytest.raises(ValueError): api.verify_consumed(p.gate)


def test_worker_requires_gate_before_development_seam(package, monkeypatch):
    p = package
    gate_path = p.root/'gate.json'
    pin = p.write('gate.json', p.gate)
    monkeypatch.setattr(job, '_execute_development_worker', lambda *a: pytest.fail('unconsumed gate reached worker'))
    with pytest.raises(FileNotFoundError):
        job._execute_calibration_worker(p.root/'request.json', p.outer['request_sha256'], gate_path, pin)


@pytest.mark.parametrize('fault', ['missing_member', 'short_closure', 'extra_field'])
def test_self_rehashed_inner_cannot_disagree_with_outer_or_closure(package, fault):
    import json
    p = package
    inner = json.loads((p.root/'inner.json').read_bytes())
    if fault == 'missing_member': inner['files'].pop('module.py')
    elif fault == 'short_closure': inner['source_closure'] = []
    else: inner['extra_field'] = True
    pin = p.write('inner.json', inner)
    p.outer['inner_sha256'] = p.outer['members']['inner.json'] = pin
    outer_pin = p.write('outer.json', p.outer)
    with pytest.raises(ValueError, match='inner manifest/closure'):
        api.verify_package(p.root/'outer.json', outer_pin)


def test_consistently_rehashed_holdout_reaches_training_inventory_gate(package):
    import json
    p = package
    p.request['source_declaration']['split'] = 'holdout'
    request_pin = p.write('request.json', p.request)
    lease = json.loads((p.root/'lease.json').read_bytes())
    lease['request_sha256'] = request_pin
    lease_pin = p.write('lease.json', lease)
    p.outer.update(request_sha256=request_pin, lease_sha256=lease_pin)
    p.outer['members'].update({'request.json': request_pin, 'lease.json': lease_pin})
    inner = dict(schema=api.SCHEMA, source_closure=['module.py'],
        files={name: pin for name, pin in p.outer['members'].items() if name != 'inner.json'})
    inner_pin = p.write('inner.json', inner)
    p.outer['inner_sha256'] = p.outer['members']['inner.json'] = inner_pin
    outer_pin = p.write('outer.json', p.outer)
    with pytest.raises(ValueError, match='1\\+73\\+158 training inventory'):
        api.verify_package(p.root/'outer.json', outer_pin)
