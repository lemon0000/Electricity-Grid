"""Draft computation reuse for a fully evaluated immutable repair digest operand.

Every caller still reads, pins and parses both scientific JSON inputs and builds
its exact rational rows. Only their repeated pure encoding/hash may be reused.
No source bytes, numerical audit, archive, identity function or discovery is cached.
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
        return value.__code__, repr(value.__defaults__), repr(value.__kwdefaults__)
    return None


@contextmanager
def reuse_pure_repair_digest():
    """One isolated entry scope, installed before any by-name digest consumer.

    Consumers imported here retain their guarded function definitions. Their
    owner cleanup must finish inside this scope; the interpreter exits after
    entry receipt/root checks. This is not a reusable application-wide context.
    """
    if not sys.flags.isolated:
        raise ValueError('isolated validation interpreter required')
    original = normal._digest
    if original.__module__ != normal.__name__ or original.__globals__ is not vars(normal):
        raise ValueError('original normal digest required')
    for name, module in tuple(sys.modules.items()):
        if (name.startswith(('experiments.', 'src.')) and module is not normal and module is not None
                and any(value is original for value in tuple(vars(module).values()))):
            raise ValueError('pure digest entry must precede imported-by-name consumers: ' + name)
    creator = os.getpid(), get_ident()
    label, maximum_keys, maximum_characters = LABEL, MAX_KEYS, MAX_OPERAND_CHARACTERS
    bindings = tuple((normal, name, getattr(normal, name)) for name in (
        '_encode', '_number', 'is_dataclass', 'fields', 'datetime', 'json', 'sha256', 'isfinite'))
    bindings += tuple((json, name, getattr(json, name)) for name in ('dumps', 'JSONEncoder'))
    bindings += tuple((json.JSONEncoder, name, getattr(json.JSONEncoder, name)) for name in (
        '__init__', 'encode', 'iterencode', 'default'))
    bindings += tuple((json.encoder, name, getattr(json.encoder, name)) for name in (
        'c_make_encoder', '_make_iterencode', 'encode_basestring_ascii', 'encode_basestring'))
    bindings += tuple((builtins, name, getattr(builtins, name)) for name in (
        'type', 'isinstance', 'str', 'tuple', 'list', 'dict', 'float', 'int', 'bool',
        'set', 'frozenset', 'sorted', 'repr', 'len', 'getattr', 'hasattr'))
    functions = tuple((value, _function_state(value)) for _, _, value in bindings
        if type(value) is FunctionType) + ((original, _function_state(original)),)
    builtin_resolution = tuple((name, vars(normal).get(name), name in vars(normal))
        for owner, name, _ in bindings if owner is builtins)
    normal_builtins = normal.__builtins__
    function_state = _function_state
    memo = MappingProxyType({})
    receipt = dict(schema=SCHEMA, pure_digest_cache=True, source_bytes_cached=False,
        numerical_audit_cached=False, identity_function_cached=False, cache_hits=0,
        computed_keys=0, fallback_calls=0, guard_checks=0, original_restored=False,
        remaining_keys=0, failure=None, formal_result=False, resource_admission=False,
        native_execution_authorized=False)
    active = True
    failure = None

    def check():
        nonlocal failure
        receipt['guard_checks'] += 1
        if (not active or normal._digest is not digest
                or any(getattr(owner, name) is not value for owner, name, value in bindings)
                or normal.__builtins__ is not normal_builtins
                or any((name in vars(normal), vars(normal).get(name)) != (present, value)
                    for name, value, present in builtin_resolution)
                or any(function_state(value) != state for value, state in functions)):
            failure = failure or 'pure repair digest dispatch changed'
            receipt['failure'] = failure
        if failure is not None:
            raise ValueError(failure)

    def digest(*items):
        nonlocal memo
        check()
        eligible = ((os.getpid(), get_ident()) == creator and len(items) == 2
            and type(items[0]) is str and items[0] == label and type(items[1]) is tuple
            and len(items[1]) == 93 and all(type(row) is tuple and len(row) == 3
                and all(type(part) is str for part in row) for row in items[1]))
        if eligible:
            eligible = sum(len(part) for row in items[1] for part in row) <= maximum_characters
        if not eligible:
            receipt['fallback_calls'] += 1
            return original(*items)
        result = memo.get(items)
        if result is None:
            result = original(*items)
            check()
            if len(memo) < maximum_keys:
                memo = MappingProxyType(dict(memo) | {items: result})
                receipt['computed_keys'] += 1
        else:
            receipt['cache_hits'] += 1
        check()
        return result

    normal._digest = digest
    body_error = None
    try:
        check()
        yield MappingProxyType(receipt)
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
            if normal._digest is digest:
                normal._digest = original
                receipt['original_restored'] = True
            for name, module in tuple(sys.modules.items()):
                if name.startswith(('experiments.', 'src.')) and module is not None:
                    for key, value in tuple(vars(module).items()):
                        if value is digest:
                            setattr(module, key, original)
            active = False
            memo = MappingProxyType({})
            receipt['remaining_keys'] = len(memo)
        if cleanup_error is not None:
            if body_error is None:
                raise cleanup_error
            try:
                body_error.add_note('pure digest cleanup: ' + repr(cleanup_error))
            except BaseException:
                pass
