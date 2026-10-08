"""Draft byte-equivalent encoder reusing invocation-local numeric key order.

No input value, dependency or digest is cached. A bounded local cache stores
only numeric-mapping key order and JSON key prefixes; fallback keeps full
encoded-pair repr order.
Existing execution paths are unchanged; consumers must bind this source.
"""
from dataclasses import fields, is_dataclass
from hashlib import sha256
from math import isfinite
import json
from pathlib import Path

from . import continuous_grid_normal as legacy, identity_stream_fast as baseline


def implementation_identity():
    return sha256(repr((
        tuple((m.__name__, sha256(Path(m.__file__).read_bytes()).hexdigest())
            for m in (legacy, baseline)), sha256(Path(__file__).read_bytes()).hexdigest())).encode()).hexdigest()


def _quoted(value):
    return json.encoder.encode_basestring_ascii(value).encode('ascii')


def _layout(value, orders):
    """Return keys and their JSON prefixes; no current numeric values cached."""
    if type(value) is dict:
        keys = tuple(value)
        if any(type(k) not in (str, int, bool) or type(value[k]) is not float for k in keys):
            return None
        for number in value.values():
            if not isfinite(number):
                legacy._number(number, 'identity')
        signature = tuple((type(k), k) for k in keys)
        ordered = None if orders is None else orders.get(signature)
        if ordered is None:
            # Exact primitive repr is injective. For prefix integer reprs the
            # comma delimiter sorts before any following digit. Values cannot
            # break ties because these encoded keys are distinct.
            ordered = tuple((k, b'[' + json.dumps(k, ensure_ascii=True, allow_nan=False).encode('ascii')
                + b', ["float", "') for k in sorted(keys, key=lambda k: repr([k, None])))
            if orders is not None and len(orders) < 64 and len(keys) <= 512:
                orders[signature] = ordered
        return ordered
    return None


def _local_encode(value, orders=None):
    """Retain the legacy materialized representation for callers and fallback."""
    layout = _layout(value, orders)
    if layout is not None:
        return ['mapping', [[k, ['float', value[k].hex()]] for k, _prefix in layout]]
    return baseline._local_encode(value)


def encoded_chunks(value):
    """Emit legacy JSON bytes, preserving exact-type and finite-float rules."""
    yield from _encoded_chunks(value, {})


def _encoded_chunks(value, _orders):
    kind = type(value)
    if kind is str:
        yield _quoted(value)
    elif kind is float:
        legacy._number(value, 'identity')
        yield b'["float", "' + value.hex().encode('ascii') + b'"]'
    elif value is None:
        yield b'null'
    elif kind is bool:
        yield b'true' if value else b'false'
    elif kind is int:
        yield str(value).encode('ascii')
    elif kind is dict:
        layout = _layout(value, _orders)
        if layout is None:
            yield json.dumps(baseline._local_encode(value), ensure_ascii=True,
                             allow_nan=False).encode('ascii')
        else:
            yield b'["mapping", [' + b', '.join(prefix + value[key].hex().encode('ascii')
                + b'"]]' for key, prefix in layout) + b']]'
    elif is_dataclass(value):
        yield b'[' + _quoted(kind.__name__) + b', ['
        for index, field in enumerate(fields(value)):
            if index:
                yield b', '
            yield b'[' + _quoted(field.name) + b', '
            yield from _encoded_chunks(getattr(value, field.name), _orders)
            yield b']'
        yield b']]'
    elif isinstance(value, (tuple, list)):
        yield b'[' + _quoted(kind.__name__) + b', ['
        for index, item in enumerate(value):
            if index:
                yield b', '
            yield from _encoded_chunks(item, _orders)
        yield b']]'
    else:
        # Preserve datetime handling and full encoded-pair repr ordering.
        yield json.dumps(_local_encode(value, _orders), ensure_ascii=True,
                         allow_nan=False).encode('ascii')


def digest(*items):
    result = sha256()
    for chunk in encoded_chunks(items):
        result.update(chunk)
    return result.hexdigest()


def normal_input_identity(inputs):
    legacy._validate(inputs)
    return digest(legacy.CONTRACT, inputs, legacy._dependencies())
