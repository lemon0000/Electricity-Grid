"""Draft byte-equivalent identity encoder with direct primitive emission.

No input, field layout, dependency or digest is cached. Mapping/set ordering
still uses the legacy encoded-pair repr order and local materialization.
Existing execution paths are unchanged; consumers must bind this source.
"""
from dataclasses import fields, is_dataclass
from datetime import datetime
from hashlib import sha256
import json

from . import continuous_grid_normal as legacy


def _quoted(value):
    return json.encoder.encode_basestring_ascii(value).encode('ascii')


def _local_encode(value):
    """Legacy representation for a locally materialized mapping/set subtree."""
    kind = type(value)
    if kind is float:
        legacy._number(value, 'identity')
        return ['float', value.hex()]
    if value is None or kind in (str, int, bool):
        return value
    if is_dataclass(value):
        return [kind.__name__, [[f.name, _local_encode(getattr(value, f.name))]
                               for f in fields(value)]]
    if isinstance(value, datetime):
        return ['datetime', value.isoformat()]
    if isinstance(value, dict):
        return ['mapping', sorted([[_local_encode(k), _local_encode(v)]
                                   for k, v in value.items()], key=repr)]
    if isinstance(value, (tuple, list)):
        return [kind.__name__, [_local_encode(v) for v in value]]
    if isinstance(value, (set, frozenset)):
        return ['set', sorted([_local_encode(v) for v in value], key=repr)]
    raise ValueError(f'unsupported input identity type: {kind.__name__}')


def encoded_chunks(value):
    """Emit legacy JSON bytes, preserving exact-type and finite-float rules."""
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
    elif is_dataclass(value):
        yield b'[' + _quoted(kind.__name__) + b', ['
        for index, field in enumerate(fields(value)):
            if index:
                yield b', '
            yield b'[' + _quoted(field.name) + b', '
            yield from encoded_chunks(getattr(value, field.name))
            yield b']'
        yield b']]'
    elif isinstance(value, (tuple, list)):
        yield b'[' + _quoted(kind.__name__) + b', ['
        for index, item in enumerate(value):
            if index:
                yield b', '
            yield from encoded_chunks(item)
        yield b']]'
    else:
        # Preserve datetime handling and full encoded-pair repr ordering.
        yield json.dumps(_local_encode(value), ensure_ascii=True,
                         allow_nan=False).encode('ascii')


def digest(*items):
    result = sha256()
    for chunk in encoded_chunks(items):
        result.update(chunk)
    return result.hexdigest()


def normal_input_identity(inputs):
    legacy._validate(inputs)
    return digest(legacy.CONTRACT, inputs, legacy._dependencies())
