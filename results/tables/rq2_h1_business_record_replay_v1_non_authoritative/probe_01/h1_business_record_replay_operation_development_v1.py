"""Call-local reuse of exact, previously replayed business records.

Only the record replay in the predecessor validator is specialized. Cursor,
observation, clock, implementation and every other predecessor check still run.
This detached synchronous operation is not an owner or execution credential.
"""
import ast
from dataclasses import fields, is_dataclass
from fractions import Fraction
from hashlib import sha256
from importlib import import_module
import inspect
import marshal
import os
from pathlib import Path
import sys
import struct
from threading import get_ident
from types import FunctionType

from experiments import h1_exact_business_development_v1 as business
from experiments import h1_validation_runtime_closure_development_v2 as runtime

SCHEMA = 'h1_business_record_replay_operation_development_v1'
MAX_RECORDS = 1024
MAX_SNAPSHOT_BYTES = 1024 ** 2
MAX_CACHE_BYTES = 64 * 1024 ** 2
MAX_NODES = 65536
_MODULE_NAMES = ('boundary', 'multiday', 'debt_cohorts', 'four_arm_replay',
    'causal_policy', 'actual_actions', 'aggregate_response', 'capacity_policy',
    'capacity_policy_bidirectional', 'cfe_preallocation', 'prefix_handoff')
_MODULES = (business,) + tuple(import_module('src.rq2_joint_deliverability_boundary_v1.' + name)
                              for name in _MODULE_NAMES)
_RECORD_TYPE = business.business.BidirectionalPolicyRecord
_ORIGINAL_VALIDATE = business._validate
_ORIGINAL_RECORD_VALIDATE = _RECORD_TYPE.__post_init__
_RUNTIME, _ARM = runtime.make_runtime(globals(), SCHEMA)


class _Uncacheable(TypeError):
    pass


def _snapshot(value):
    """Typed complete instance-field graph, including alias topology.

No __eq__, property or user serializer is used to establish a hit. Exact
registered dataclass types and built-in scalar/container types are admitted.
"""
    seen = {}
    nodes = 0
    def visit(item):
        nonlocal nodes
        nodes += 1
        if nodes > MAX_NODES:
            raise ValueError('record graph exceeds node cap')
        kind = type(item)
        if kind in (type(None), bool, int, str, bytes):
            return (kind.__name__, item)
        if kind is float:
            return ('float', struct.pack('>d', item))
        if kind is Fraction:
            return ('Fraction', object.__getattribute__(item, '_numerator'),
                    object.__getattribute__(item, '_denominator'))
        if kind not in (tuple, list, dict) and kind not in _DATA_TYPES:
            raise _Uncacheable('record graph has an unregistered exact type')
        identity = id(item)
        if identity in seen:
            if seen[identity][1]:
                raise ValueError('cyclic record graph')
            return ('reference', seen[identity][0])
        index = len(seen)
        seen[identity] = (index, True)
        if kind in (tuple, list):
            result = (kind.__name__, index, tuple(visit(v) for v in item))
        else:
            values = item if kind is dict else object.__getattribute__(item, '__dict__')
            if any(type(key) is not str for key in values):
                raise _Uncacheable('record graph fields require exact string keys')
            if kind is not dict and set(values) != set(_FIELD_NAMES[kind]):
                raise _Uncacheable('noncanonical instance layout requires original replay')
            result = ('dict' if kind is dict else ('dataclass', id(kind)), index,
                      tuple((key, visit(values[key])) for key in sorted(values)))
        seen[identity] = (index, False)
        return result
    raw = marshal.dumps(visit(value), 4)
    if len(raw) > MAX_SNAPSHOT_BYTES:
        raise ValueError('record snapshot exceeds byte cap')
    return raw


def _specialize(callback):
    tree = ast.parse(inspect.getsource(_ORIGINAL_VALIDATE))
    matches = [node for node in ast.walk(tree) if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute) and node.func.attr == '__post_init__'
        and isinstance(node.func.value, ast.Name) and node.func.value.id == 'record']
    if len(matches) != 1 or matches[0].args or matches[0].keywords:
        raise ValueError('predecessor record-replay seam differs')
    call = matches[0]
    call.func = ast.copy_location(ast.Name(id='_scoped_record_validate', ctx=ast.Load()), call.func)
    call.args = [ast.copy_location(ast.Name(id='record', ctx=ast.Load()), call)]
    ast.fix_missing_locations(tree)
    namespace = dict(_ORIGINAL_VALIDATE.__globals__, _scoped_record_validate=callback)
    exec(compile(tree, '<' + SCHEMA + '>', 'exec'), namespace)
    return namespace['_validate']


def _file_pins():
    paths = {Path(module.__file__) for module in _MODULES}
    paths.update(business.encoding.ROOT / name for name in business.encoding.IMPLEMENTATION)
    paths.update((Path(__file__), Path(runtime.__file__)))
    paths.add(Path(sys.modules[business._owned.__module__].__file__))
    return tuple((str(path), sha256(path.read_bytes()).hexdigest()) for path in sorted(paths))


class RecordReplayOperation:
    def __init__(self, *, max_records=MAX_RECORDS, max_cache_bytes=MAX_CACHE_BYTES):
        _RUNTIME()
        if (type(max_records) is not int or not 1 <= max_records <= MAX_RECORDS
                or type(max_cache_bytes) is not int or not 1 <= max_cache_bytes <= MAX_CACHE_BYTES):
            raise ValueError('bounded record-cache resource limits required')
        self._creator = (os.getpid(), get_ident())
        self._active, self._busy, self._poisoned = True, False, False
        self._cache = {}
        self._cache_bytes = 0
        self._max_records, self._max_cache_bytes = max_records, max_cache_bytes
        self._counts = dict(validator_calls=0, records_observed=0, original_record_replays=0,
                            record_reuses=0, peak_cache_bytes=0)
        self._files = _file_pins()
        self._validator = _specialize(self._record)
        self._validator_code, self._validator_globals = self._validator.__code__, self._validator.__globals__
        _RUNTIME()

    def _check(self):
        _RUNTIME()
        if (os.getpid(), get_ident()) != self._creator:
            raise ValueError('record operation creator differs')
        if not self._active or self._poisoned:
            raise ValueError('record operation is closed or poisoned')
        if (self._validator.__code__ is not self._validator_code
                or self._validator.__globals__ is not self._validator_globals):
            raise ValueError('private specialized validator changed')

    def _record(self, record):
        caller = sys._getframe(1)
        if (not self._busy or caller.f_code is not self._validator_code
                or caller.f_globals is not self._validator_globals):
            raise ValueError('private validator record call required')
        del caller
        _RUNTIME()
        self._counts['records_observed'] += 1
        try:
            raw = _snapshot(record)
        except _Uncacheable:
            # Keep the predecessor lookup, exception ordering and acceptance
            # domain for noncanonical objects; such records are never cached.
            record.__post_init__()
            self._counts['original_record_replays'] += 1
            _RUNTIME()
            return
        key = id(record)
        previous = self._cache.get(key)
        if previous is not None and previous[0] is record and previous[1] == raw:
            if _snapshot(record) != raw:
                raise ValueError('record changed during reuse observation')
            _RUNTIME()
            self._counts['record_reuses'] += 1
            return
        record.__post_init__()
        if _snapshot(record) != raw:
            raise ValueError('record changed during deterministic replay')
        _RUNTIME()
        previous_size = len(previous[1]) if previous is not None else 0
        if ((previous is None and len(self._cache) >= self._max_records)
                or self._cache_bytes - previous_size + len(raw) > self._max_cache_bytes):
            raise ValueError('record-cache resource cap exceeded')
        self._cache[key] = (record, raw)
        self._cache_bytes += len(raw) - previous_size
        self._counts['original_record_replays'] += 1
        self._counts['peak_cache_bytes'] = max(self._counts['peak_cache_bytes'], self._cache_bytes)

    def validate(self, carry):
        if (os.getpid(), get_ident()) != self._creator:
            raise ValueError('record operation creator differs')
        if self._busy:
            raise ValueError('record operation is nonreentrant')
        self._busy = True
        try:
            self._check()
            self._counts['validator_calls'] += 1
            result = self._validator(carry)
            self._check()
            return result
        except BaseException:
            self._poisoned = True
            self._cache.clear()
            self._cache_bytes = 0
            raise
        finally:
            self._busy = False

    def close(self):
        if (os.getpid(), get_ident()) != self._creator:
            raise ValueError('record operation creator differs')
        if not self._active:
            return
        if self._busy:
            raise ValueError('record operation is nonreentrant')
        try:
            _RUNTIME()
            if _file_pins() != self._files:
                raise ValueError('record operation dependency bytes changed')
        finally:
            self._active = False
            self._cache.clear()
            self._cache_bytes = 0

    @property
    def observation(self):
        return dict(self._counts, schema=SCHEMA, active=self._active, poisoned=self._poisoned,
            cache_cleared=not self._cache, cross_operation_reuse=False,
            dynamic_source_cached=False, complete_dynamic_closure_proved=False,
            unobserved_ABA_covered=False, formal_result=False)

    def __enter__(self):
        self._check()
        return self

    def __exit__(self, *args):
        self.close()

    def __copy__(self):
        raise TypeError('record operation cannot be copied')

    def __deepcopy__(self, memo):
        raise TypeError('record operation cannot be copied')

    def __reduce_ex__(self, protocol):
        raise TypeError('record operation cannot be serialized')


def _arm_runtime():
    attributes = []
    classes = set()
    metadata = []
    module_names = []
    for module in _MODULES:
        module_names.append((module, tuple(vars(module))))
        for name, value in vars(module).items():
            if name.startswith('__') and name != '__file__':
                continue
            attributes.append((module, name, value))
            if isinstance(value, type) and value.__module__ == module.__name__:
                classes.add(value)
    classes.update((RecordReplayOperation, Fraction, business._Detached,
                    sys.modules[business._owned.__module__]._Owned))
    for kind in classes:
        attributes.extend((kind, name, value) for name, value in vars(kind).items())
        attributes.extend(((kind, '__bases__', kind.__bases__), (kind, '__mro__', kind.__mro__)))
        if is_dataclass(kind):
            metadata.append((kind, tuple((field.name, field.type, field.default, field.default_factory)
                                         for field in fields(kind))))
    class_names = [(kind, tuple(vars(kind))) for kind in classes]
    attributes.extend(((marshal, 'dumps', marshal.dumps), (os, 'getpid', os.getpid),
                       (struct, 'pack', struct.pack)))
    def metadata_unchanged():
        if (any(tuple(vars(module)) != before for module, before in module_names)
                or any(tuple(vars(kind)) != before for kind, before in class_names)):
            raise ValueError('record module or class dictionary inventory changed')
        for kind, before in metadata:
            if tuple((field.name, field.type, field.default, field.default_factory)
                     for field in fields(kind)) != before:
                raise ValueError('record dataclass field metadata changed')
    data_types = frozenset(kind for kind in classes if is_dataclass(kind))
    return data_types, {kind: tuple(field.name for field in fields(kind)) for kind in data_types}, attributes, metadata_unchanged


_DATA_TYPES, _FIELD_NAMES, _ATTRIBUTES, _METADATA_CHECK = _arm_runtime()
_ARM(attributes=tuple(_ATTRIBUTES), checks=(_METADATA_CHECK,), ignored=('_ARM', '_ATTRIBUTES'))
del _ARM, _ATTRIBUTES
