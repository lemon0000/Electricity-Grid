"""Byte-equivalent streaming of the existing normal identity encoding.

Dataclasses and sequences are traversed incrementally. Mapping/set subtrees
retain the legacy repr sorting and are materialized locally; this is not a
general hard memory bound. No existing execution path is changed here.
"""
from dataclasses import fields, is_dataclass
from hashlib import sha256
import json

from . import continuous_grid_normal as legacy


def _scalar_json(value):
    return json.dumps(value, ensure_ascii=True, allow_nan=False).encode('ascii')


def encoded_chunks(value):
    """Yield the exact bytes of json.dumps(legacy._encode(value)).

    Inputs must remain stable during traversal, as with the legacy encoder.
    A mapping/set fallback may be large when its values contain large subtrees.
    """
    if is_dataclass(value):
        yield b'['
        yield _scalar_json(type(value).__name__)
        yield b', ['
        for index, field in enumerate(fields(value)):
            if index: yield b', '
            yield b'['
            yield _scalar_json(field.name)
            yield b', '
            yield from encoded_chunks(getattr(value, field.name))
            yield b']'
        yield b']]'
    elif isinstance(value, (tuple, list)):
        yield b'['
        yield _scalar_json(type(value).__name__)
        yield b', ['
        for index, item in enumerate(value):
            if index: yield b', '
            yield from encoded_chunks(item)
        yield b']]'
    else:
        # Preserve full encoded-pair repr ordering, including tied encoded keys.
        yield _scalar_json(legacy._encode(value))


def digest(*items):
    result = sha256()
    for chunk in encoded_chunks(items): result.update(chunk)
    return result.hexdigest()


def normal_input_identity(inputs):
    """Same content/dependency payload as legacy; not an execution identity.

    A future caller must separately bind this implementation in its execution
    contract. Returning an old content hash does not authenticate this code.
    """
    legacy._validate(inputs)
    return digest(legacy.CONTRACT, inputs, legacy._dependencies())
