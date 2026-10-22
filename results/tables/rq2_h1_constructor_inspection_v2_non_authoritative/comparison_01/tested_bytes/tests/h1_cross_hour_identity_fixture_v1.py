"""Test-only memo of pure code/spec identities; never cache dynamic evidence.

This measures synthetic integration with a controlled immutable-code fixture,
not production overhead. All actual science/source/history functions execute.
Unobserved runtime dependency ABA is explicitly outside this fixture's claim.
"""
from contextlib import contextmanager
from functools import wraps
from hashlib import sha256
import json
from pathlib import Path

from experiments import h1_cross_hour_owner_development_v1 as cross
from src.solvers import rq2_gurobi_declared_normal as adapter


def _targets():
    saved = cross.saved
    source = saved.source
    return (
        (saved, 'implementation_identity'),
        (source, 'implementation_identity'),
        (source.historical, 'implementation_identity'),
        (source.historical.old, 'implementation_identity'),
        (source.origin_join, 'implementation_identity'),
        (source.normal, 'implementation_identity'),
        (saved.selection, 'implementation_identity'),
        (saved.selection.native, '_identity'),
        (saved.selection.physical, 'implementation_identity'),
        (saved.business, 'implementation_identity'),
        (saved.followup, 'implementation_identity'),
        (saved.followup, 'contract_identity'),
        (saved.tickets, 'implementation_identity'),
        (cross.normal.base.parent, 'implementation_identity'),
        (adapter, 'implementation_identity'),
    )


@contextmanager
def immutable_code_identities(receipt_path):
    entries, errors = [], []
    primary = None
    # Only these pure static functions are replaced. No metadata/version alias,
    # source load/prepare, historical replay, record, carry or input identity.
    def install(module, name):
        original = getattr(module, name)
        cache = {}
        entry = dict(module=module, name=name, original=original, cache=cache, calls=0)
        @wraps(original)
        def memo(*args, **kwargs):
            entry['calls'] += 1
            key = cross.encode([args, kwargs])
            if key not in cache:
                result = original(*args, **kwargs)
                cross.normal.io.pin(result)
                cache[key] = (args, kwargs.copy(), result)
            return cache[key][2]
        entry['wrapper'] = memo
        entries.append(entry)
        setattr(module, name, memo)
    try:
        installed = set()
        for module, name in _targets():
            if (module, name) in installed:
                continue
            install(module, name)
            installed.add((module, name))
        yield
    except BaseException as error:
        primary = error
        raise
    finally:
        # Restore every callable before any original-bookend evaluation, so
        # the comparison is not derived through another memoized dependency.
        for entry in reversed(entries):
            if getattr(entry['module'], entry['name'], None) is not entry['wrapper']:
                errors.append(dict(function=entry['module'].__name__+'.'+entry['name'],
                                   reason='identity callable changed inside fixture'))
            setattr(entry['module'], entry['name'], entry['original'])
        rows = []
        for entry in entries:
            checks = []
            for key, (args, kwargs, expected) in entry['cache'].items():
                try:
                    actual = entry['original'](*args, **kwargs)
                    if cross.encode([args, kwargs]) != key or actual != expected:
                        raise ValueError('static identity or canonical arguments drifted')
                    checks.append(dict(arguments_sha256=sha256(key).hexdigest(), before=expected, after=actual))
                except BaseException as error:
                    errors.append(dict(function=entry['module'].__name__+'.'+entry['name'],
                                       reason=type(error).__name__))
            rows.append(dict(function=entry['module'].__name__+'.'+entry['name'], calls=entry['calls'],
                original_computations=len(entry['cache']), bookends=checks,
                original_callable_restored=getattr(entry['module'], entry['name']) is entry['original']))
        receipt = dict(test_only_static_identity_memo=True, production_overhead_measured=False,
            dynamic_source_or_history_or_state_cached=False, unobserved_runtime_dependency_ABA_covered=False,
            original_functions_bookended_after_all_aliases_restored=True,
            functions=rows, errors=errors, formal_result=False)
        try:
            Path(receipt_path).write_text(json.dumps(receipt, indent=2)+'\n', encoding='utf-8')
        except BaseException as error:
            if primary is None:
                raise
            errors.append(dict(reason='receipt_write_failed', error_type=type(error).__name__))
        if errors:
            if primary is not None:
                try:
                    BaseException.add_note(primary, 'static identity fixture cleanup/bookend failed; receipt retained')
                except BaseException:
                    pass
            else:
                raise ValueError('static identity fixture cleanup/bookend failed')
