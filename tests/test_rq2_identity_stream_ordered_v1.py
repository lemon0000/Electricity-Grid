from dataclasses import dataclass, make_dataclass
from datetime import datetime, timezone
import json
import random
import tracemalloc

import pytest

from src.rq2_joint_deliverability_boundary_v1 import identity_stream_ordered as api


def test_numeric_key_order_and_current_values_match_full_pair_sort():
    keys = [-100, -10, -1, 0, 1, 10, 100, 10**40, '', 'a', 'ab', 'a\'',
        'a"', '\\', '\n', '\ud800', '\u7535', True, False]
    rng = random.Random(20260927)
    rows = []
    for _ in range(200):
        rng.shuffle(keys)
        rows.append({k: rng.choice([-0., 0., -1., 1., 5e-324, 1e100]) for k in keys})
    assert b''.join(api.encoded_chunks(rows)) == legacy_bytes(rows)


def test_bool_integer_cache_keys_are_distinct():
    rows = ({True: 1., False: 2.}, {1: 3., 0: 4.}, {True: -0., False: 5.})
    assert b''.join(api.encoded_chunks(rows)) == legacy_bytes(rows)


def test_order_cache_is_bounded_and_never_holds_values():
    orders = {}
    for i in range(100):
        api._local_encode({str(i): float(i)}, orders)
    assert len(orders) == 64
    before = dict(orders)
    large = {str(i): float(i) for i in range(513)}
    assert api._local_encode(large, orders) == api.legacy._encode(large)
    assert orders == before
    assert all(all(type(k) is str and type(prefix) is bytes for k, prefix in order)
        for order in orders.values())


def test_digest_rechecks_values_and_restarts_order_cache():
    value = {'x': 1., 'y': -0.}
    first = api.digest(value)
    value['x'] = 2.; value['z'] = 3.
    assert api.digest(value) == api.legacy._digest(value) != first


@pytest.mark.parametrize('module', ['baseline', 'legacy'])
def test_fallback_sources_bound(tmp_path, monkeypatch, module):
    before = api.implementation_identity()
    path = tmp_path/'changed.py'; path.write_text('# changed')
    monkeypatch.setattr(getattr(api, module), '__file__', str(path))
    assert api.implementation_identity() != before


@dataclass(frozen=True)
class Row:
    hour: int
    values: dict


def legacy_bytes(value):
    return json.dumps(api.legacy._encode(value), ensure_ascii=True, allow_nan=False).encode()


@pytest.mark.parametrize('value', [None, True, False, 0, -1, 10**40, 0., -0., 1.1,
    '\u7535\u7f51\n"\\', datetime(2020,1,1,tzinfo=timezone.utc), [], (), {}, set(), frozenset(),
    Row(1, {'a': 2., 10: -0., (1, 'x'): False}), {2, -1, 'x', (True, 3.)}])
def test_exact_legacy_byte_stream(value):
    assert b''.join(api.encoded_chunks(value)) == legacy_bytes(value)
    assert api.digest(value, (1,2)) == api.legacy._digest(value, (1,2))


def test_colliding_encoded_mapping_keys_keep_full_pair_repr_order():
    first = make_dataclass('Same', [('value', int)], frozen=True)
    second = make_dataclass('Same', [('value', int)], frozen=True)
    value = {first(1): 'z', second(1): 'a'}
    assert len(value) == 2
    assert b''.join(api.encoded_chunks(value)) == legacy_bytes(value)


def test_deterministic_nested_differential_cases():
    rng = random.Random(20260921)
    def build(depth):
        if not depth: return rng.choice([None, True, False, -0., 2.5, 'a\n', 3])
        kind = rng.randrange(4)
        if kind == 0: return tuple(build(depth-1) for _ in range(rng.randrange(5)))
        if kind == 1: return [build(depth-1) for _ in range(rng.randrange(5))]
        if kind == 2: return {str(k): build(depth-1) for k in range(rng.randrange(5))}
        return Row(rng.randrange(10), {'value': build(depth-1)})
    for _ in range(100):
        value = build(4)
        assert b''.join(api.encoded_chunks(value)) == legacy_bytes(value)
        assert api.digest(value) == api.legacy._digest(value)


@pytest.mark.parametrize('value', [float('nan'), float('inf'), float('-inf'), object()])
def test_unsupported_or_nonfinite_values_still_refused(value):
    with pytest.raises(ValueError): api.digest(value)
    with pytest.raises(ValueError): api.legacy._digest(value)


def test_normal_content_and_dependency_identity_preserved():
    from test_rq2_continuous_grid_normal_v1 import fixture
    inputs = fixture(2)
    assert api.normal_input_identity(inputs) == api.legacy.normal_input_identity(inputs)


def test_sequence_of_small_mappings_reduces_encoding_allocation_peak():
    # Representative structure only; does not claim measured RTS resource use.
    rows = tuple(Row(hour, {str(k): float(k) for k in range(48)}) for hour in range(256))
    def peak(function):
        tracemalloc.start()
        try:
            result = function(rows)
            return result, tracemalloc.get_traced_memory()[1]
        finally: tracemalloc.stop()
    expected, old_peak = peak(api.legacy._digest)
    observed, new_peak = peak(api.digest)
    assert observed == expected
    assert new_peak < old_peak/4


@pytest.mark.parametrize('value', ['\ud800', '\udfff', '\U0001f600', '\x00\b\f\r\t',
    5e-324, -5e-324, 1.7976931348623157e308, -1.7976931348623157e308])
def test_unicode_and_float_boundary_bytes(value):
    for tree in (value, [value], {'key': value}, Row(1, {'key': value})):
        assert b''.join(api.encoded_chunks(tree)) == legacy_bytes(tree)
        assert api._local_encode(tree) == api.legacy._encode(tree)


def test_float_bit_patterns_differential():
    import math
    import struct
    rng = random.Random(20260927)
    for _ in range(500):
        value = struct.unpack('!d', rng.getrandbits(64).to_bytes(8, 'big'))[0]
        if math.isfinite(value):
            assert b''.join(api.encoded_chunks(value)) == legacy_bytes(value)
        else:
            with pytest.raises(ValueError):
                api.digest(value)


def test_container_subclasses_and_dataclass_precedence():
    class Sequence(list):
        pass
    class Mapping(dict):
        pass
    @dataclass
    class TaggedSequence(list):
        tag: str = 'field'
    value = [Sequence([2.5]), Mapping(a=-0.), TaggedSequence()]
    assert b''.join(api.encoded_chunks(value)) == legacy_bytes(value)
    assert api._local_encode(value) == api.legacy._encode(value)


@pytest.mark.parametrize('base', [str, int, float])
def test_unsupported_primitive_subclasses_remain_rejected(base):
    class Unsupported(base):
        pass
    value = Unsupported('1')
    for tree in (value, [value], {'key': value}):
        with pytest.raises(ValueError):
            api.digest(tree)
        with pytest.raises(ValueError):
            api.legacy._digest(tree)


def test_mutable_contents_and_field_layout_are_not_cached():
    @dataclass
    class Mutable:
        first: object
        second: object
    value = Mutable({'nested': [1.]}, 2)
    before = api.digest(value)
    value.first['nested'][0] = -0.
    assert api.digest(value) == api.legacy._digest(value) != before
    before = api.digest(value)
    # Dataclass metadata is mutable even when an instance is reused.
    field = Mutable.__dataclass_fields__.pop('second')
    Mutable.__dataclass_fields__ = {'second': field, **Mutable.__dataclass_fields__}
    assert api.digest(value) == api.legacy._digest(value) != before


def test_normal_validation_and_dependencies_recomputed(monkeypatch):
    from test_rq2_continuous_grid_normal_v1 import fixture
    inputs = fixture(2)
    validation = api.legacy._validate
    calls = []
    def validate(value):
        calls.append(value)
        return validation(value)
    monkeypatch.setattr(api.legacy, '_validate', validate)
    monkeypatch.setattr(api.legacy, '_dependencies', lambda: ('first',))
    before = api.normal_input_identity(inputs)
    monkeypatch.setattr(api.legacy, '_dependencies', lambda: ('second',))
    after = api.normal_input_identity(inputs)
    assert before != after
    assert len(calls) == 2 and all(value is inputs for value in calls)
    assert after == api.legacy.normal_input_identity(inputs)


@pytest.mark.parametrize('value', [
    {'10': -0., '2': 1., 'a\n': 5e-324},
    {10: 2., 2: -0., -1: 1., True: 3.},
    {'x': 1., 'y': [2.]}, {'x': 1., (1, 2): 3.},
    {'nested': {'b': 2., 'a': 1.}},
])
def test_specialized_numeric_mapping_and_fallback(value):
    assert api._local_encode(value) == api.legacy._encode(value)
    assert b''.join(api.encoded_chunks(value)) == legacy_bytes(value)
    assert api.digest(value) == api.baseline.digest(value)


def test_numeric_path_does_not_delegate_or_cache(monkeypatch):
    def forbidden(value):
        raise AssertionError('numeric mapping should use the specialized path')
    monkeypatch.setattr(api.baseline, '_local_encode', forbidden)
    value = {'bus': 1.}
    first = api.digest(value)
    value['bus'] = -0.
    assert first != api.digest(value) == api.legacy._digest(value)


@pytest.mark.parametrize('bad', [float('nan'), float('inf'), float('-inf')])
def test_numeric_mapping_nonfinite_refused(bad):
    with pytest.raises(ValueError):
        api.digest({'first': 1., 'bad': bad})


def test_numeric_mapping_subclass_uses_legacy_semantics():
    class Mapping(dict):
        pass
    @dataclass
    class TaggedMapping(dict):
        field: str = 'metadata'
    for value in [Mapping(a=1.), TaggedMapping()]:
        assert b''.join(api.encoded_chunks(value)) == legacy_bytes(value)
