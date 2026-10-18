"""Draft pure computation reuse after every original fresh repair-input read.

Only the physical module's digest alias is replaced, before selector consumers
load. Both JSON pin/read/parse operations and all rational conversions execute
on every call. No source bytes, numerical audit or identity function is cached.
"""
from contextlib import contextmanager
import builtins
import json
import os
import sys
from threading import get_ident
from types import FunctionType, MappingProxyType

from src.rq2_joint_deliverability_boundary_v1 import continuous_grid_normal as normal

SCHEMA = 'h1_pure_repair_digest_lease_development_v1'
LABEL = 'approved_Rref_actual_repair_cap_min_Pmax_60ramp'
MAX_KEYS = 8
MAX_OPERAND_CHARACTERS = 32768


def _function_state(value):
    if type(value) is FunctionType:
        return (value.__code__, id(value.__defaults__),
            tuple(id(x) for x in value.__defaults__ or ()), id(value.__kwdefaults__),
            tuple((key, id(part)) for key, part in sorted((value.__kwdefaults__ or {}).items())))
    return None


@contextmanager
def reuse_pure_repair_digest():
    """One isolated creating-thread entry; all owner cleanup stays inside it."""
    if not sys.flags.isolated:
        raise ValueError('isolated validation interpreter required')
    forbidden = ('h1_selector_parent_controller_development_', 'h1_origin_selector_replay_development_')
    if any(name.startswith('experiments.' + prefix) for name in sys.modules for prefix in forbidden):
        raise ValueError('pure repair entry must precede selector consumers')
    from experiments import h1_origin_grid_step_development_v1 as physical
    original = physical._digest
    if original is not normal._digest or original.__globals__ is not vars(normal):
        raise ValueError('original physical digest alias required')
    pid_of, thread_of, snapshot_function = os.getpid, get_ident, _function_state
    state_code = snapshot_function.__code__
    creator = pid_of(), thread_of()
    label, maximum_keys, maximum_characters = LABEL, MAX_KEYS, MAX_OPERAND_CHARACTERS
    namespace = globals()
    own_names = ('SCHEMA', 'LABEL', 'MAX_KEYS', 'MAX_OPERAND_CHARACTERS', '_function_state', 'get_ident')
    own_bindings = tuple((name, namespace[name]) for name in own_names)
    bindings = tuple((normal, name, getattr(normal, name)) for name in (
        '_digest', '_encode', '_number', 'is_dataclass', 'fields', 'datetime', 'json', 'sha256', 'isfinite'))
    bindings += tuple((json, name, getattr(json, name)) for name in ('dumps', 'JSONEncoder'))
    bindings += tuple((json.JSONEncoder, name, getattr(json.JSONEncoder, name)) for name in (
        '__init__', 'encode', 'iterencode', 'default', 'item_separator', 'key_separator'))
    bindings += tuple((json.encoder, name, getattr(json.encoder, name)) for name in (
        'c_make_encoder', '_make_iterencode', 'encode_basestring_ascii', 'encode_basestring'))
    builtin_names = ('type', 'isinstance', 'str', 'tuple', 'list', 'dict', 'float', 'int', 'bool',
        'set', 'frozenset', 'sorted', 'repr', 'len', 'getattr', 'hasattr', 'all', 'sum', 'id')
    bindings += tuple((builtins, name, getattr(builtins, name)) for name in builtin_names)
    bindings += ((os, 'getpid', pid_of),)
    functions = tuple((value, snapshot_function(value)) for _, _, value in bindings
        if type(value) is FunctionType)
    builtin_resolution = tuple((name, vars(normal).get(name), name in vars(normal)) for name in builtin_names)
    normal_builtins = normal.__builtins__
    memo = MappingProxyType({})
    record = dict(schema=SCHEMA, creator_pid=creator[0], creator_thread=creator[1],
        pure_digest_cache=True, source_bytes_cached=False, numerical_audit_cached=False,
        identity_function_cached=False, maximum_keys=maximum_keys,
        maximum_characters_per_operand=maximum_characters, cache_hits=0, computed_keys=0,
        calls=0, fallback_calls=0, failed_calls=0, guard_checks=0,
        restored_aliases=(), remaining_keys=0, failure=None,
        formal_result=False, resource_admission=False, native_execution_authorized=False)
    active = True
    failure = None

    def poison(message):
        nonlocal failure
        failure = failure or message
        record['failure'] = failure
        raise ValueError(failure)

    def check_creator():
        if (pid_of(), thread_of()) != creator:
            poison('pure repair digest creating thread required')

    def check():
        check_creator()
        record['guard_checks'] += 1
        if failure is not None:
            raise ValueError(failure)
        if (not active or physical._digest is not digest
                or snapshot_function.__code__ is not state_code
                or any(namespace.get(name) is not value for name, value in own_bindings)
                or any(getattr(owner, name) is not value for owner, name, value in bindings)
                or normal.__builtins__ is not normal_builtins
                or any((name in vars(normal)) != present or present and vars(normal).get(name) is not value
                    for name, value, present in builtin_resolution)
                or any(snapshot_function(value) != state for value, state in functions)):
            poison('pure repair digest dispatch changed')

    def digest(*items):
        nonlocal memo
        check()
        record['calls'] += 1
        try:
            eligible = (len(items) == 2 and type(items[0]) is str and items[0] == label
                and type(items[1]) is tuple and len(items[1]) == 93
                and all(type(row) is tuple and len(row) == 3
                    and all(type(part) is str for part in row) for row in items[1]))
            if eligible:
                eligible = sum(len(part) for row in items[1] for part in row) <= maximum_characters
            if not eligible:
                record['fallback_calls'] += 1
                return original(*items)
            result = memo.get(items)
            if result is None:
                result = original(*items)
                check()
                if type(result) is not str or len(result) != 64 or any(c not in '0123456789abcdef' for c in result):
                    poison('pure repair digest result differs')
                if len(memo) < maximum_keys:
                    memo = MappingProxyType(dict(memo) | {items: result})
                    record['computed_keys'] += 1
            else:
                record['cache_hits'] += 1
            check()
            return result
        except BaseException:
            record['failed_calls'] += 1
            raise

    def receipt():
        check_creator()
        if active:
            check()
        return MappingProxyType(dict(record))

    physical._digest = digest
    body_error = None
    try:
        check()
        yield receipt
    except BaseException as error:
        body_error = error
        raise
    finally:
        cleanup_error = None
        try:
            check()
        except BaseException as error:
            cleanup_error = error
        finally:
            if physical._digest is digest:
                physical._digest = original
                record['restored_aliases'] = (physical.__name__ + '._digest',)
            active = False
            memo = MappingProxyType({})
            record['remaining_keys'] = 0
        if cleanup_error is not None:
            if body_error is None:
                raise cleanup_error
            try:
                body_error.add_note('pure digest cleanup: ' + repr(cleanup_error))
            except BaseException:
                pass
