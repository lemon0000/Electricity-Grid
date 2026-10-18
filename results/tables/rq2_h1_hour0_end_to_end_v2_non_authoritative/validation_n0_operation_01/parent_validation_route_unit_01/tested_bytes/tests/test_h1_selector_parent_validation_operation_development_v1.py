"""Private route integration with real Parent method code and explicit fake science.

The host, transport readers and arithmetic proof are unit fixtures. This suite
does not replace a genuine Handoff/three-arm end-to-end acceptance run.
"""
import ast
from contextlib import nullcontext
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys
from threading import Lock
from types import FunctionType, ModuleType, SimpleNamespace as NS

import pytest

from experiments import h1_selector_parent_controller_development_v2 as predecessor
from experiments import h1_selector_parent_validation_operation_development_v1 as original


def encode(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def digest(value):return sha256(value).hexdigest()


def function(namespace, source, name):
    exec(compile(source,'explicit_parent_route_unit','exec'),namespace)
    return namespace[name]


@pytest.fixture
def case(tmp_path,monkeypatch):
    faults={};calls=[];proofs=[];fallback=[]
    fake_witness=ModuleType(original._WITNESS_NAME)
    fake_witness.__file__=str(Path(original.__file__).with_name(original._WITNESS_FILE))
    fake_witness.__spec__=fake_witness.__loader__=None
    monkeypatch.setitem(sys.modules,original._WITNESS_NAME,fake_witness)
    class Proof:
        def __init__(self,root,**kw):
            self.root,self.owner,self.lease=root,kw['_parent_owner'],kw['_parent_lease']
            self._parent_confirmed=False;self._attempts=0;self.full=self.reused=0
            self.closed=False;self.guard=Lock();self.failure=None
            def cleanup():
                self.closed=True
                if self.guard.locked():self.guard.release()
                if faults.get('cleanup') is self.owner:raise RuntimeError('proof cleanup fault')
            self._cleanup_original=cleanup;proofs.append(self)
        def __enter__(self):self.guard.acquire();return self
        def _start(self):return object()
        def _check(self,token):fresh._lease_check(self.lease,self.owner)
        def _finish(self,*args):
            self._attempts+=1
            self.full+=0 if self._parent_confirmed else 4
            self.reused+=8 if self._parent_confirmed else 4
        def activate(self):
            assert self._attempts==16 and fresh._parent_confirmed(self.lease,self.owner,self)
            self._parent_confirmed=True;calls.append(('activated',str(self.owner.root)))
        def _poison(self,error):self.failure=repr(error)
        def receipt(self):
            if faults.get('report') is self.owner:raise RuntimeError('proof report fault')
            return dict(complete=self.closed and self._parent_confirmed and self.failure is None,
                closed=self.closed,proof_cleared=self.closed,
                full_numerical_hour_replays=self.full,reused_numerical_inspections=self.reused,
                context_observations=self._attempts*16,parent_site_confirmed=self._parent_confirmed)
    fake_witness.ParentSourceWitness=Proof
    fake_witness._replay_prefix=lambda root,**kw:None
    # Predefinition unit seam, matching the bridge tests' fixed-route fixture.
    # Production source is never edited or dynamically redirected by this test.
    tree=ast.parse(Path(original.__file__).read_bytes())
    class UnitLoader(ast.NodeTransformer):
        def visit_FunctionDef(self,node):
            if node.name=='_capture_source_guard':
                node.body=ast.parse('return lambda: None').body
                return node
            if node.name=='load_witness':
                node.body=[ast.Return(value=ast.Name(id='_UNIT_WITNESS',ctx=ast.Load()))]
                return node
            return self.generic_visit(node)
    tree=ast.fix_missing_locations(UnitLoader().visit(tree))
    fresh=ModuleType(original.__name__);fresh.__file__=original.__file__
    fresh._UNIT_WITNESS=fake_witness
    monkeypatch.setitem(sys.modules,original.__name__,fresh)
    exec(compile(tree,original.__file__,'exec'),vars(fresh))
    class Current:
        def __init__(self):
            self.prepared_current=NS(decision=NS(decision_bytes=b'unit-science'))
            self.source_projection_audit_payload=b'unit-compatibility-projection'
    guard=NS(solver_calls_forbidden=nullcontext)
    io=NS(encode=encode,digest=digest,pin=lambda value:value)
    source=NS(io=io,ExactSourceCurrent=Current,implementation_identity=lambda:'a'*64,
        historical=NS(history=NS(replay=NS(guard=guard)),verifier_identity=lambda:'e'*64,
            witness=NS(_dispatch_view=lambda caller=None:('explicit-unit-dispatch',))))
    def core(root,**kw):
        kw['_check']()
        for _ in range(2):kw['_replay'](root)
        kw['_check']()
        return Current()
    source._prepare=core
    def full_source(*args,**kw):fallback.append('original_full_source');return Current()
    source.prepare=full_source
    phase=NS(source=source,_initial=lambda *a:None,_request=lambda *a:None,business=NS(),RREF='Rref')
    phase._fresh=predecessor.worker.snapshot.phase._fresh
    class Rebuilt:pass
    snapshot=NS(CAP=4096,encode=encode,RebuiltInput=Rebuilt,implementation_identity=lambda:'b'*64)
    snapshot._build=function(dict(phase=phase),
        'def _build(declaration):\n return phase._fresh(declaration,0,declaration.genesis_terminal_sha256)\n','_build')
    snapshot.rebuild=function(dict(_build=snapshot._build,json=json,NS=NS,Rebuilt=Rebuilt),
        'def rebuild(raw,*,expected_sha256):\n d=NS(**json.loads(raw)["declaration"]["source_binding"])\n _build(d)\n _build(d)\n return Rebuilt()\n','rebuild')
    worker=NS(CAP=4096,sequence=NS(),runtime=NS(),content_bound=lambda request:1,
        implementation_identity=lambda:'c'*64,snapshot=snapshot)
    worker.request_document=function(dict(snapshot=snapshot),
        'def request_document(root,raw,**kw):\n snapshot.rebuild(raw,expected_sha256="unused")\n return b"request"\n','request_document')
    declarations={};launches={};inspections={}
    prep=NS()
    prep.prepare=function(dict(worker=worker,declarations=declarations),
        'def prepare(root,raw,**kw):\n worker.request_document(root,raw)\n worker.request_document(root,raw)\n return declarations[str(root)]\n','prepare')
    prep.bind=function(dict(prepare=prep.prepare,json=json,launches=launches),
        'def bind(declaration,raw):\n prepare_fixed=prepare\n root=json.loads(declaration)["root"]\n prepare_fixed(root,raw)\n prepare_fixed(root,raw)\n return launches[root]\n','bind')
    inspection=NS(INPUT_FILES=frozenset(('input',)),OUTPUT_FILES=frozenset(('output',)))
    inspection._source=function(dict(snapshot=snapshot),
        'def _source(raw,root,request):\n return snapshot.rebuild(raw,expected_sha256="unused")\n','_source')
    inspection._inspect=function(dict(_source=inspection._source,inspections=inspections,deepcopy=deepcopy,faults=faults),
        'def _inspect(root,**kw):\n raw=inspections[str(root)][0]\n _source(raw,root,None)\n _source(raw,root,None)\n if faults.get("inspection")==str(root):raise RuntimeError("inspection tail fault")\n return deepcopy(inspections[str(root)][1])\n','_inspect')
    inspection.inspect=function(dict(_inspect=inspection._inspect),
        'def inspect(root,**kw):\n return _inspect(root,**kw)\n','inspect')
    parent=NS(preparation=prep,worker=worker,inspection=inspection,io=io,
        SCHEMA=predecessor.SCHEMA,FLAGS={})
    def same(a,b):
        if encode(a)!=encode(b):raise ValueError('unit retained bytes differ')
    parent._same=same
    parent._CHECK=lambda:None
    parent._completion_bytes=lambda value:encode(vars(value))
    class Receipt:pass
    class Parent:
        def _check(self):
            assert self._guard.locked()
        def _request_keys(self):return dict(scientific_request_sha256='f'*64,sequence_request_sha256='d'*64)
        def _reference_match(self,owner,issued):return {'reference_root':str(owner.root)}
    parent.Parent,parent.ParentCompletion=Parent,Receipt
    namespace=dict(preparation=prep,inspection=inspection,json=json,io=io,deepcopy=deepcopy,
        _same=same,SCHEMA=parent.SCHEMA,FLAGS={})
    for name in ('_source','_inspect','_retained','_validate','_reference'):
        old=getattr(predecessor.Parent,name)
        setattr(Parent,name,FunctionType(old.__code__,namespace,name,old.__defaults__,old.__closure__))
    raw=encode(dict(declaration=dict(source_binding=dict(root=str(tmp_path),binding_sha256='a'*64,
        genesis_terminal_sha256='b'*64,registry_identity='c'*64))))
    def make(name,reference=None):
        obj=Parent();obj.root=tmp_path/name;obj.worker_root=obj.root/'worker_non_authoritative'
        obj._guard=Lock();obj._guard.acquire();obj._reference_held=reference is not None
        obj._raw=raw;obj._options={};obj._own='a'*64;obj._state='complete';obj._binding=b'binding'
        obj._reference_owner=reference;obj._reference_completion=None if reference is None else reference._issued
        obj._reference_descriptor=None if reference is None else {'reference_root':str(reference.root)}
        obj._declaration=encode(dict(root=str(obj.root),environment={}))
        obj._launch=encode(dict(process_identity='c'*64))
        declarations[str(obj.root)]=obj._declaration;launches[str(obj.root)]=obj._launch
        prior=dict(data=dict(pins=dict(output='a'*64),output_pins_externally_supplied=False))
        outcome=dict(pid=1,creation_filetime=2,inspection=prior)
        obj._outcome=encode(outcome)
        expected=deepcopy(prior);expected['data']['output_pins_externally_supplied']=True
        inspections[str(obj.worker_root)]=(raw,expected)
        terminal=encode(dict(schema=parent.SCHEMA,implementation=obj._own,binding_sha256=digest(obj._binding),
            request_keys=obj._request_keys(),reference_execution=obj._reference_descriptor,lifecycle=outcome))
        obj._records={'terminal.json':(4096,terminal,()),'worker_non_authoritative/input':(4096,b'input',())}
        issued=Receipt();issued.terminal_sha256=digest(terminal)
        issued.scientific_request_sha256='f'*64;issued.sequence_request_sha256='d'*64
        obj._issued=issued;obj._issued_bytes=parent._completion_bytes(issued)
        return obj
    ref=make('reference_non_authoritative')
    actuals=[make('actual_'+str(i)+'_non_authoritative',ref) for i in range(3)]
    bundle=NS(reference=(ref,ref._issued),actuals=tuple((str(i),(owner,owner._issued)) for i,owner in enumerate(actuals)),
        held=[*(owner._guard for owner in actuals),ref._guard],marked=actuals[:])
    class Host:pass
    host=Host();host._guard=Lock();host._guard.acquire();host._bundle=bundle
    api=ModuleType(original._HOST);api.__file__=str(Path(predecessor.__file__).with_name('h1_selector_phase_handoff_development_v4.py'))
    api.Handoff=Host;api.parent=parent
    monkeypatch.setitem(sys.modules,original._HOST,api)
    token=object()
    def verify(value):
        if value is not host:raise ValueError('foreign unit host')
    def operation(value,issued):
        verify(value)
        if issued is not token or not host._guard.locked():raise ValueError('foreign unit token')
        return dict(bundle=bundle)
    def finalized(value):
        verify(value)
        if host._guard.locked() or any(g.locked() for g in bundle.held):
            raise ValueError('outer resources remain held')
    methods=fresh._bind_handoff(api,Host,verify,operation,finalized)
    attach,validate_bundle,rebuild,finish,abort,receipt,commit,validate_pair,declaration=methods
    attach(host,token)
    result=NS(module=fresh,host=host,bundle=bundle,parents=[ref,*actuals],actuals=actuals,ref=ref,
        validate_bundle=validate_bundle,rebuild=rebuild,finish=finish,abort=abort,receipt=receipt,
        commit=commit,validate_pair=validate_pair,declaration=declaration,source=source,witness=fake_witness,
        faults=faults,proofs=proofs,calls=calls,fallback=fallback)
    def release():
        for guard_ in bundle.held:
            if guard_.locked():guard_.release()
        if host._guard.locked():host._guard.release()
    result.release=release
    try:yield result
    finally:
        abort(host,RuntimeError('unit teardown'))
        release()


def complete(case):
    case.validate_bundle(case.bundle)
    for parent in case.parents:
        case.validate_pair(case.bundle,parent,parent._issued)
        case.rebuild(case.bundle,parent)
        case.validate_pair(case.bundle,parent,parent._issued)
    for _ in range(12):case.validate_bundle(case.bundle)


def test_complete_functional_route_counts_and_commit_after_outer_cleanup(case):
    complete(case)
    pending=case.finish(case.host)
    assert pending['validation_checks_complete'] and not pending['complete']
    assert pending['parent_validations']==150 and pending['source_prepares']==2408
    assert pending['full_numerical_hour_replays']==256 and pending['reused_numerical_inspections']==19008
    assert pending['fresh_context_observations']==38528
    assert not case.fallback
    assert all(proof.closed and not proof.guard.locked() for proof in case.proofs)
    with pytest.raises(ValueError,match='resources remain'):case.commit(case.host)
    assert not case.receipt(case.host)['complete']
    case.release()
    assert case.commit(case.host)['complete']
    with pytest.raises(ValueError,match='single pending'):case.commit(case.host)


def test_parent_tail_failure_never_activates_staged_numerical_proof(case):
    case.faults['inspection']=str(case.ref.worker_root)
    with pytest.raises(RuntimeError,match='inspection tail'):case.validate_bundle(case.bundle)
    assert len(case.proofs)==1 and not case.proofs[0]._parent_confirmed
    assert case.proofs[0].closed and not case.proofs[0].guard.locked()
    assert not case.receipt(case.host)['complete'] and not case.fallback
    assert all(guard.locked() for guard in case.bundle.held)


@pytest.mark.parametrize('fault',['receipt','snapshot','mark','unlock'])
def test_input_or_borrowed_guard_drift_poisoned_without_legacy_fallback(case,fault):
    case.validate_bundle(case.bundle)
    if fault=='receipt':case.ref._issued=NS(**vars(case.ref._issued))
    elif fault=='snapshot':case.ref._raw=bytes(bytearray(case.ref._raw))
    elif fault=='mark':case.actuals[0]._reference_held=False
    else:case.actuals[0]._guard.release()
    with pytest.raises((ValueError,TypeError)):case.validate_bundle(case.bundle)
    assert all(proof.closed and not proof.guard.locked() for proof in case.proofs)
    assert not case.receipt(case.host)['complete'] and not case.fallback


@pytest.mark.parametrize('fault',['cleanup','report'])
def test_all_private_proofs_closed_before_cleanup_or_report_failure_returns(case,fault):
    complete(case)
    case.faults[fault]=case.ref
    with pytest.raises((RuntimeError,ValueError)):case.finish(case.host)
    assert all(proof.closed and not proof.guard.locked() for proof in case.proofs)
    assert not case.receipt(case.host)['complete']
    assert all(guard.locked() for guard in case.bundle.held)


def test_failure_after_parent_pending_receipt_cannot_be_committed(case):
    complete(case);case.finish(case.host)
    case.abort(case.host,RuntimeError('outer cleanup failed'))
    case.release()
    aborted=case.receipt(case.host)
    assert aborted['status']=='aborted' and not aborted['validation_checks_complete']
    with pytest.raises(ValueError):case.commit(case.host)
    assert case.receipt(case.host)==aborted and not aborted['complete']


@pytest.mark.parametrize('slot', ['core','identity','verifier','dispatch','denial','replay'])
def test_rebound_direct_callable_is_rejected_before_it_can_execute(case,monkeypatch,slot):
    called=[]
    targets=dict(core=(case.source,'_prepare'),identity=(case.source,'implementation_identity'),
        verifier=(case.source.historical,'verifier_identity'),
        dispatch=(case.source.historical.witness,'_dispatch_view'),
        denial=(case.source.historical.history.replay.guard,'solver_calls_forbidden'),
        replay=(case.witness,'_replay_prefix'))
    obj,name=targets[slot]
    def replacement(*args,**kwargs):called.append(slot);raise AssertionError('replacement executed')
    monkeypatch.setattr(obj,name,replacement)
    with pytest.raises(ValueError,match='dispatch changed'):case.validate_bundle(case.bundle)
    assert called==[] and not case.receipt(case.host)['complete']


@pytest.mark.parametrize('name', ['_validate_pair','_declaration'])
def test_private_handoff_entry_does_not_execute_rebound_public_slot(case,monkeypatch,name):
    called=[]
    def replacement(*args,**kwargs):called.append(name);raise AssertionError('replacement executed')
    monkeypatch.setattr(case.module,name,replacement)
    with pytest.raises(ValueError,match='definition-time'):
        if name=='_validate_pair':case.validate_pair(case.bundle,case.ref,case.ref._issued)
        else:case.declaration(case.bundle)
    assert called==[]


def test_genuine_predecessor_dispatch_checklist_rejects_same_value_substitute(monkeypatch):
    source=predecessor.worker.snapshot.phase.source
    check=original._capture_source_guard(source)
    check()
    calls=[]
    def replacement():calls.append(True);return 'same-value-substitute'
    monkeypatch.setattr(source,'implementation_identity',replacement)
    with pytest.raises(ValueError,match='dispatch checklist'):check()
    assert calls==[]
