"""Run the exact Parent4 method bodies with explicit operation/transport seams."""
import ast
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from types import SimpleNamespace as NS

import pytest


class ObservedGuard:
    def __init__(self, failure=None):
        self.lock=Lock();self.failure=failure;self.releases=0

    def acquire(self, **keywords):return self.lock.acquire(**keywords)

    def locked(self):return self.lock.locked()

    def release(self):
        self.releases+=1
        failure,self.failure=self.failure,None
        if failure=='before':raise OSError('reference release before effect')
        self.lock.release()
        if failure=='after':raise OSError('reference release after effect')


@pytest.mark.parametrize('operation',('run','validate_completion'))
@pytest.mark.parametrize('replacement',('reference','actual','both'))
@pytest.mark.parametrize('release_fault',(None,'before','after'))
def test_real_parent_method_retains_primary_and_releases_both_original_guards(operation,replacement,release_fault):
    path=Path(__file__).parents[1]/'experiments/h1_selector_parent_controller_development_v4.py'
    tree=ast.parse(path.read_bytes(),filename=str(path))
    kind=next(node for node in tree.body if isinstance(node,ast.ClassDef) and node.name=='Parent')
    method=next(node for node in kind.body if isinstance(node,ast.FunctionDef) and node.name==operation)
    release=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='_release_operation_guards')
    failure=RuntimeError('original operation body failure')
    actual_guard=ObservedGuard();reference_guard=ObservedGuard(release_fault)
    reference=NS(_guard=reference_guard)
    reference._enter=lambda:reference._guard.acquire(blocking=False)
    owner=NS(_guard=actual_guard,_reference_owner=reference,_reference_held=False,
             _state='prepared',_issued=object(),_issued_bytes=b'issued')
    owner._enter=lambda:owner._guard.acquire(blocking=False)

    def body(*args):
        if replacement in ('actual','both'):owner._guard=ObservedGuard()
        if replacement in ('reference','both'):reference._guard=ObservedGuard()
        raise failure

    owner._source=owner._validate=body
    @contextmanager
    def window(*args):yield
    namespace=dict(_CHECK=lambda:None,Parent=NS(_check=lambda self:None),
                   _WINDOWS=NS(window=window))
    # Preserve the source AST, line numbers, exception/finally control flow and
    # nested callbacks. Only global dispatch and instance data are test seams.
    exec(compile(ast.Module(body=[release,method],type_ignores=[]),str(path),'exec'),namespace)
    with pytest.raises(RuntimeError) as caught:
        namespace[operation](owner,*(() if operation=='run' else (object(),)))
    assert caught.value is failure
    assert not actual_guard.locked() and not reference_guard.locked()
    assert not owner._reference_held
    assert actual_guard.releases==1
    assert reference_guard.releases==(2 if release_fault=='before' else 1)
    if release_fault:
        assert any('reference guard cleanup' in note for note in failure.__notes__)
    if operation=='run':assert owner._state=='failed' and owner._issued is None


def test_cleanup_failure_without_primary_still_releases_actual_and_invalidates_run():
    path=Path(__file__).parents[1]/'experiments/h1_selector_parent_controller_development_v4.py'
    tree=ast.parse(path.read_bytes(),filename=str(path))
    release=next(node for node in tree.body if isinstance(node,ast.FunctionDef) and node.name=='_release_operation_guards')
    namespace={};exec(compile(ast.Module(body=[release],type_ignores=[]),str(path),'exec'),namespace)
    actual=ObservedGuard();reference=ObservedGuard('after')
    actual.acquire();reference.acquire()
    owner=NS(_reference_held=True,_state='complete',_issued=object(),_issued_bytes=b'issued')
    with pytest.raises(OSError,match='after effect'):
        namespace['_release_operation_guards'](owner,actual,reference,None,invalidate=True)
    assert not actual.locked() and not reference.locked() and not owner._reference_held
    assert owner._state=='failed' and owner._issued is owner._issued_bytes is None
