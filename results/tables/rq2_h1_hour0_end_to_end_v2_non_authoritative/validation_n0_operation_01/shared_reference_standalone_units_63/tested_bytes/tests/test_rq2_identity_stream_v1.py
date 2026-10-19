from dataclasses import dataclass, make_dataclass
from datetime import datetime, timezone
import json
import random
import tracemalloc

import pytest

from src.rq2_joint_deliverability_boundary_v1 import identity_stream as api


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
