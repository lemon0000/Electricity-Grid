"""Differential digest, freshness and fail-stop checks in an isolated interpreter."""
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
from threading import Thread
from time import perf_counter

import pytest

from experiments import h1_pure_repair_digest_lease_development_v1 as entry


def operands(label=None):
    return entry.LABEL if label is None else label, tuple((str(i), '30', '1') for i in range(93))


def test_digest_parity_source_reads_and_alias_restoration(monkeypatch):
    from experiments import h1_origin_grid_step_development_v1 as physical
    registry = physical.registry
    original = physical._digest
    expected = physical.repair_mechanism_identity()
    pin = registry._pin
    reads = []
    def observe(path, expected):
        reads.append(str(path))
        return pin(path, expected)
    monkeypatch.setattr(registry, '_pin', observe)
    with entry.reuse_pure_repair_digest() as snapshot:
        for _ in range(5):
            assert physical.repair_mechanism_identity() == expected
        receipt = snapshot()
        assert receipt['computed_keys'] == 1 and receipt['cache_hits'] == 4
        assert receipt['calls'] == 5 and len(reads) == 10
        assert len(set(reads)) == 2
        with pytest.raises(TypeError):
            receipt['failure'] = None
    assert physical._digest is original
    assert snapshot()['restored_aliases'] == (physical.__name__ + '._digest',)
    assert snapshot()['remaining_keys'] == 0


@pytest.mark.parametrize('value', [(0.0,), (-0.0,), (True,), (1,), (['mutable'],), operands('other')])
def test_noneligible_arguments_keep_original_digest(monkeypatch, value):
    from experiments import h1_origin_grid_step_development_v1 as physical
    expected = physical._digest(*value)
    with entry.reuse_pure_repair_digest() as snapshot:
        assert physical._digest(*value) == expected
        assert physical._digest(*value) == expected
        assert snapshot()['fallback_calls'] == 2 and snapshot()['computed_keys'] == 0


def test_noneligible_failure_is_not_consumed_or_retried():
    from experiments import h1_origin_grid_step_development_v1 as physical
    with entry.reuse_pure_repair_digest() as snapshot:
        with pytest.raises(ValueError, match='unsupported'):
            physical._digest(object())
        assert snapshot()['failed_calls'] == 1


@pytest.mark.parametrize('point', ['encode', 'encoder', 'sha256', 'constant', 'defaults', 'keyword_inplace', 'code', 'shadow'])
def test_cached_result_cannot_hide_dependency_drift(monkeypatch, point):
    from experiments import h1_origin_grid_step_development_v1 as physical
    original = physical._digest
    with pytest.raises(ValueError, match='dispatch'):
        with entry.reuse_pure_repair_digest() as snapshot:
            physical._digest(*operands())
            with monkeypatch.context() as patch:
                if point == 'encode':
                    patch.setattr(entry.normal, '_encode', lambda value: value)
                elif point == 'encoder':
                    patch.setattr(json.JSONEncoder, 'item_separator', ';')
                elif point == 'sha256':
                    patch.setattr(entry.normal, 'sha256', lambda *args: None)
                elif point == 'constant':
                    patch.setattr(entry, 'MAX_KEYS', 100000)
                elif point == 'defaults':
                    patch.setattr(json.dumps, '__kwdefaults__', dict(json.dumps.__kwdefaults__, allow_nan=True))
                elif point == 'keyword_inplace':
                    patch.setitem(json.dumps.__kwdefaults__, 'allow_nan', True)
                elif point == 'code':
                    patch.setattr(entry.normal._encode, '__code__', (lambda value: value).__code__)
                else:
                    patch.setattr(entry.normal, 'str', lambda value: value, raising=False)
                with pytest.raises(ValueError, match='dispatch'):
                    physical._digest(*operands())
            # Restoring bytes/functions cannot reset the first failure.
            physical._digest(*operands())
    assert physical._digest is original


def test_foreign_thread_poison_is_retained():
    from experiments import h1_origin_grid_step_development_v1 as physical
    errors = []
    def foreign():
        try:
            physical._digest(*operands())
        except Exception as error:
            errors.append(error)
    with pytest.raises(ValueError, match='creating thread'):
        with entry.reuse_pure_repair_digest():
            thread = Thread(target=foreign)
            thread.start()
            thread.join(5)
            assert not thread.is_alive() and len(errors) == 1


def test_foreign_alias_is_preserved_and_body_first_error_retained(monkeypatch):
    from experiments import h1_origin_grid_step_development_v1 as physical
    original = physical._digest
    replacement = lambda *args: 'foreign'
    marker = RuntimeError('body first')
    try:
        with pytest.raises(RuntimeError) as caught:
            with entry.reuse_pure_repair_digest():
                monkeypatch.setattr(physical, '_digest', replacement)
                raise marker
        assert caught.value is marker and marker.__notes__
        assert physical._digest is replacement
    finally:
        monkeypatch.undo()
        physical._digest = original


def test_key_capacity_falls_back_without_changing_outputs():
    from experiments import h1_origin_grid_step_development_v1 as physical
    original = physical._digest
    values = [operands() for _ in range(10)]
    values = [(name, ((str(i), '29', '1'), *rows[1:])) for i, (name, rows) in enumerate(values)]
    expected = [original(*value) for value in values]
    with entry.reuse_pure_repair_digest() as snapshot:
        assert [physical._digest(*value) for value in values] == expected
        assert snapshot()['computed_keys'] == 8 and snapshot()['cache_hits'] == 0
