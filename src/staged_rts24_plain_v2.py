"""Unwired exact-type successor admitting exact str/int dictionary keys.

Equivalence assumes stationary inputs and unmodified standard-library/classes.
Unsupported input falls back at the root; no input or digest is memoized.
"""
from dataclasses import fields
from fractions import Fraction
from hashlib import sha256
import json

from src import staged_rts24_development_v1 as legacy
from src.staged_rts24_evidence_store_v1 import CLASSES

_legacy_plain=legacy.plain
# Static schema metadata, not a cache of an observation, input or digest.
_KNOWN_FIELDS=tuple((cls,tuple(f.name for f in fields(cls))) for cls in CLASSES.values())
MAX_FAST_DEPTH=64


class _Unsupported(Exception):
    pass


def _walk(value,depth,active):
    if depth>MAX_FAST_DEPTH:raise _Unsupported
    kind=type(value)
    if kind is Fraction:return str(value)
    if kind is str or kind is int or kind is float or kind is bool or kind is type(None):return value
    names=None
    if kind is not dict and kind is not list and kind is not tuple:
        # Identity comparisons avoid invoking an unknown metaclass's hash/eq.
        names=next((names for cls,names in _KNOWN_FIELDS if kind is cls),None)
        if names is None:raise _Unsupported
    identity=id(value)
    if identity in active:raise _Unsupported
    active.add(identity)
    try:
        if kind is dict:
            if any(type(k) is not str and type(k) is not int for k in value):raise _Unsupported
            return {str(k):_walk(v,depth+1,active) for k,v in value.items()}
        if names is not None:return {name:_walk(getattr(value,name),depth+1,active) for name in names}
        return [_walk(v,depth+1,active) for v in value]
    finally:active.remove(identity)


def plain(value):
    try:return _walk(value,0,set())
    except _Unsupported:return _legacy_plain(value)


def canonical_bytes(value):
    return json.dumps(plain(value),sort_keys=True,separators=(',',':'),allow_nan=False).encode('utf-8')


def digest(value):return sha256(canonical_bytes(value)).hexdigest()
