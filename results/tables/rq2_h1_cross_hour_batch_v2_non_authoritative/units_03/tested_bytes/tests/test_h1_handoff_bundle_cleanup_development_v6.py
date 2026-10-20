"""Exact Handoff6 entry/consume bodies with explicit non-scientific seams."""
import ast
from pathlib import Path
from threading import Lock
from types import SimpleNamespace as NS

import pytest


class Guard:
    def __init__(self, fault=None):
        self.inner=Lock();self.fault=fault;self.releases=0
    def acquire(self,*args,**kw):return self.inner.acquire(*args,**kw)
    def locked(self):return self.inner.locked()
    def release(self):
        self.releases+=1
        fault,self.fault=self.fault,None
        if fault=='before':raise OSError('guard release before effect')
        self.inner.release()
        if fault=='after':raise OSError('guard release after effect')


def setup_case(*,mark_fault=None,release_fault=None,replace=False):
    path=Path(__file__).parents[1]/'experiments/h1_selector_phase_handoff_development_v6.py'
    tree=ast.parse(path.read_bytes(),filename=str(path))
    nodes={node.name:node for node in tree.body if isinstance(node,(ast.FunctionDef,ast.ClassDef))}
    primary=RuntimeError('original entry body failure')
    mark_error=RuntimeError('mark assignment after write')
    faults=[];parents=[];controls=[]
    class Parent:
        def __setattr__(self,name,value):
            before=(name=='_reference_held' and mark_fault is not None and len(parents)>mark_fault[0]+1
                and self is parents[mark_fault[0]+1] and getattr(self,name,None) is True
                and value is False and mark_fault[1]=='before' and not faults)
            if before:
                faults.append(True);raise OSError('mark cleanup before effect')
            object.__setattr__(self,name,value)
            if name=='_reference_held' and mark_fault is not None and len(parents)>mark_fault[0]+1 and self is parents[mark_fault[0]+1]:
                if value is True and mark_fault[1]=='assignment':raise mark_error
                if value is False and mark_fault[1]=='after' and not faults:
                    faults.append(True);raise OSError('mark cleanup after effect')
        def _enter(self):
            guard=self._guard
            if not guard.acquire(False):raise ValueError('guard already active')
            return guard
    class Receipt:pass
    for index in range(4):
        obj=Parent();obj._guard=Guard();obj._reference_held=False
        obj._reference_owner=None if index==0 else parents[0]
        obj._reference_completion=None if index==0 else parents[0]._issued
        obj._issued=Receipt();obj._issued.role='reference' if index==0 else 'actual'
        parents.append(obj);controls.append(obj._guard)
    # Acquisition order is Actual0, Actual1, Actual2, Rref.
    if release_fault is not None:
        index,phase=release_fault
        [*controls[1:],controls[0]][index].fault=phase
    status={};events=[]
    class Host:
        def _check(self):pass
        def _close_handles(self):events.append('close_handles')
    def abort_parent(host,error):status['parent']='aborted'
    def abort_validation(host,error):status['validation']='aborted'
    def body(bundle):
        if replace:
            for obj in parents:obj._guard=Guard()
        raise primary
    namespace=dict(_CHECK=lambda:None,parent=NS(Parent=Parent,ParentCompletion=Receipt),
        _PARENT_ATTACH=lambda *a:events.append('attach'),_PARENT_ABORT=abort_parent,
        _PARENT_VALIDATE_BUNDLE=body,Handoff=Host,common=NS(),
        _VALIDATION_ABORT=abort_validation)
    for name in ('_BEGIN','_END','_RECORD_HANDLE','_RECORD_VIEW','_SEAL','_RECORD_BUNDLE',
            '_RECORD_PREDECESSOR','_CLOSE_PREDECESSOR','_ABORT_PREDECESSOR',
            '_VALIDATION_ATTACH','_VALIDATION_FINISH','_VALIDATION_COMMIT',
            '_PARENT_FINISH','_PARENT_COMMIT'):
        namespace[name]=lambda *a:object()
    consume=next(node for node in nodes['Handoff'].body if isinstance(node,ast.FunctionDef) and node.name=='consume')
    exec(compile(ast.Module(body=[nodes['_release_bundle_resources'],nodes['_Bundle'],consume],
        type_ignores=[]),str(path),'exec'),namespace)
    bundle=namespace['_Bundle']((parents[0],parents[0]._issued),
        {str(i):(obj,obj._issued) for i,obj in enumerate(parents[1:])})
    host=Host();host._self=host;host._guard=Lock();host._state='new';host._bundle=bundle;host._genesis=NS()
    return NS(invoke=lambda:namespace['consume'](host),parents=parents,controls=controls,
        host=host,bundle=bundle,status=status,primary=primary,mark_error=mark_error,events=events)


def cleared(case):
    assert all(not guard.locked() for guard in case.controls)
    assert all(obj._reference_held is False for obj in case.parents)
    assert not case.host._guard.locked() and case.host._state=='failed'
    assert case.status==dict(parent='aborted',validation='aborted')
    assert not case.bundle.held and not case.bundle.marked and not case.bundle.releases


@pytest.mark.parametrize('index',range(3))
def test_mark_after_write_entry_fault_preserves_primary_and_cleans_all(index):
    case=setup_case(mark_fault=(index,'assignment'))
    with pytest.raises(RuntimeError) as caught:case.invoke()
    assert caught.value is case.mark_error
    assert 'attach' not in case.events
    cleared(case)


@pytest.mark.parametrize('index',range(3))
@pytest.mark.parametrize('phase',('before','after'))
def test_mark_clear_fault_does_not_interrupt_other_cleanup(index,phase):
    case=setup_case(mark_fault=(index,phase))
    with pytest.raises(RuntimeError) as caught:case.invoke()
    assert caught.value is case.primary and any('mark cleanup' in note for note in caught.value.__notes__)
    cleared(case)


@pytest.mark.parametrize('index',range(4))
@pytest.mark.parametrize('phase',('before','after'))
def test_guard_release_fault_does_not_interrupt_other_cleanup(index,phase):
    case=setup_case(release_fault=(index,phase))
    with pytest.raises(RuntimeError) as caught:case.invoke()
    assert caught.value is case.primary and any('guard release' in note for note in caught.value.__notes__)
    cleared(case)


def test_original_guards_are_released_after_owner_guard_replacement():
    case=setup_case(replace=True,release_fault=(1,'before'))
    with pytest.raises(RuntimeError) as caught:case.invoke()
    assert caught.value is case.primary
    cleared(case)
