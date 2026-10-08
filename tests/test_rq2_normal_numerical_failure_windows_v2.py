from copy import deepcopy
from dataclasses import replace
from hashlib import sha256

import pytest

from tests.test_rq2_normal_numerical_controller_v2 import (
    api, pipeline, subprocess_pipeline, supplied, legacy_request,
    declared_source, prepared_source, bound_source, source_supplied, run, audit)


def test_self_consistent_receipt_and_record_cannot_drop_plan(supplied):
    record = run(supplied)
    report = audit(supplied, record)
    record = deepcopy(record)
    report = deepcopy(report)
    record['prepared_information'] = report['prepared_information'] = None
    api._audit_outcome(report, record)
    raw = api.worker.source.replay._bytes(record)
    with pytest.raises(ValueError, match='independently replayed'):
        api._verify_audit(report, record, raw, supplied, api.worker.source.request_identity(supplied),
            sha256(raw).hexdigest(), 32*1024**2)


@pytest.mark.parametrize('changes', [dict(exit_code=False), dict(formal_result=True),
    dict(stop_markers=('invented_exit',))])
def test_forged_process_observation_never_reaches_audit_release(subprocess_pipeline, monkeypatch, changes):
    root, request, settings = subprocess_pipeline
    wait = api.declared._DeclaredTaskChild.wait
    release = api.declared._DeclaredTaskChild.release
    released = []
    def observed(child): return replace(wait(child), **changes)
    def released_once(child):
        released.append(child.pid)
        assert len(released) == 1
        return release(child)
    monkeypatch.setattr(api.declared._DeclaredTaskChild, 'wait', observed)
    monkeypatch.setattr(api.declared._DeclaredTaskChild, 'release', released_once)
    with pytest.raises(ValueError): api.supervise_normal(root, request, **settings)
    assert len(released) == 1 and not (root/'result.json').exists()


def test_persistent_unknown_return_preserves_full_reservation(subprocess_pipeline):
    root, request, settings = subprocess_pipeline
    # Only this fixture's synthetic bootstrap changes; no repository source changes.
    path = root.parent/'synthetic_worker.py'
    text = path.read_text(encoding='utf-8')
    assert text.count('worker.main()') == 1
    text = text.replace('worker.main()', '''def fail(*args, **kwargs):
    raise RuntimeError('injected lost native return')
worker.source.projection.capture.solve_once=fail
worker.main()''')
    path.write_text(text, encoding='utf-8')
    result = api.supervise_normal(root, request, **settings)
    assert result['status'] == 'normal_invocation_unknown_not_replayed'
    assert result['solver_calls'] is None and not result['call_count_complete']
    assert result['reserved_solver_seconds'] == request.budget.max_seconds_per_solve
    assert result['audit']['prepared_information'] is None
    assert not result['audit']['accepted_record_reproduced']
    assert result['audit']['solver_calls_by_replay'] == 0
    with pytest.raises((ValueError, FileExistsError)): api.supervise_normal(root, request, **settings)
