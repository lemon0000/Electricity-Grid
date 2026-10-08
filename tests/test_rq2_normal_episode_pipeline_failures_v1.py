"""Fault windows for the additional persisted normal binding."""
import json
from pathlib import Path
from contextlib import contextmanager

import pytest

from tests.test_rq2_normal_episode_pipeline_v1 import (
    pipeline, packet, bound, supplied, legacy_request, declared_source, prepared_source,
    bound_source, original_bound_source, base_bound_source, source_supplied, original_source_supplied, api)


def test_member_drift_after_launch_prevents_release(pipeline, monkeypatch):
    root, packet, kwargs = pipeline
    write = api.base._write
    released = []
    child_factory = api.process.normal_task_child

    @contextmanager
    def child(*args, **kw):
        with child_factory(*args, **kw) as value:
            release = value.release
            def observed_release():
                released.append(True)
                return release()
            value.release = observed_release
            yield value

    def drift(path, value):
        result = write(path, value)
        if path.name == 'execute_launch.json':
            member = Path(packet.normal_request.source.upstream_root)/'synthetic_source.bin'
            member.write_bytes(b'drift after durable launch, before release')
        return result

    monkeypatch.setattr(api.process, 'normal_task_child', child)
    monkeypatch.setattr(api.base, '_write', drift)
    with pytest.raises(ValueError, match='manifest-listed source file changed'):
        api.supervise_episode(root, packet, **kwargs)
    assert not released
    assert (root/'execute_launch.json').is_file()
    assert not (root/'execute_receipt_non_authoritative.json').exists()
    assert not (root/'result.json').exists()


@pytest.mark.parametrize('mode', ['execute', 'audit'])
def test_reencoded_binding_receipt_refused(pipeline, monkeypatch, mode):
    root, packet, kwargs = pipeline
    pin = api.worker.episode._file_pin
    changed = []

    def forge(path):
        if Path(path) == root/(mode+'_receipt_non_authoritative.json') and not changed:
            body = json.loads(Path(path).read_bytes())
            body['normal_binding']['business_pair_correspondence_verified'] = False
            Path(path).write_bytes(api.base.worker.store._bytes(body))
            changed.append(True)
        return pin(path)

    monkeypatch.setattr(api.worker.episode, '_file_pin', forge)
    with pytest.raises(ValueError, match='pipeline worker receipt binding mismatch'):
        api.supervise_episode(root, packet, **kwargs)
    assert changed
    assert not (root/'result.json').exists()
    with pytest.raises((ValueError, FileExistsError)):
        api.supervise_episode(root, packet, **kwargs)
