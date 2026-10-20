"""Draft byte-equivalent encoder specializing numeric mapping subtrees.

No input, field layout, dependency or digest is cached. Mapping/set ordering
still uses the legacy encoded-pair repr order and local materialization.
Existing execution paths are unchanged; consumers must bind this source.
"""
from dataclasses import fields, is_dataclass
from hashlib import sha256
from math import isfinite
import json

from . import continuous_grid_normal as legacy, identity_stream_fast as baseline


def _quoted(value):
    return json.encoder.encode_basestring_ascii(value).encode('ascii')


def _local_encode(value):
    """Specialize exact primitive-key/float mappings; retain full pair sorting."""
    if type(value) is dict:
        pairs = []
        for key, number in value.items():
            if type(key) not in (str, int, bool) or type(number) is not float:
                return baseline._local_encode(value)
            if not isfinite(number):
                legacy._number(number, 'identity')
            pairs.append([key, ['float', number.hex()]])
        return ['mapping', sorted(pairs, key=repr)]
    return baseline._local_encode(value)


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
