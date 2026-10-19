"""Private route integration with real Parent method code and explicit fake science.

The host, transport readers and full source kernel are explicit unit fixtures. This suite
does not replace a genuine Handoff/three-arm end-to-end acceptance run.
"""
import ast
from contextlib import nullcontext
from dataclasses import dataclass, field
from copy import deepcopy
from hashlib import sha256
import json
from pathlib import Path
import sys
from threading import Lock,Thread,get_ident
from types import FunctionType, ModuleType, SimpleNamespace as NS

import pytest

from experiments import h1_selector_parent_controller_development_v2 as predecessor
from experiments import h1_selector_parent_validation_operation_development_v4 as original


def encode(value):return json.dumps(value,sort_keys=True,separators=(',',':')).encode()
def digest(value):return sha256(value).hexdigest()


def function(namespace, source, name):
    exec(compile(source,'explicit_parent_route_unit','exec'),namespace)
    return namespace[name]


@pytest.fixture
def case(tmp_path,monkeypatch):
    yield from make_case(tmp_path,monkeypatch)


def make_case(tmp_path,monkeypatch,*,exact_source=None,source_binding=None,before_attach=None):
    """Fake Parent transport, optionally retaining the actual source and its guards."""
    faults={};calls=[];fallback=[]
    tree=ast.parse(Path(original.__file__).read_bytes())
    class UnitLoader(ast.NodeTransformer):
        def visit_FunctionDef(self,node):
            if node.name=='_capture_source_guard' and exact_source is None:
                node.body=ast.parse('return lambda: None').body
                return node
            return self.generic_visit(node)
    tree=ast.fix_missing_locations(UnitLoader().visit(tree))
    fresh=ModuleType(original.__name__);fresh.__file__=original.__file__
    monkeypatch.setitem(sys.modules,original.__name__,fresh)
    exec(compile(tree,original.__file__,'exec'),vars(fresh))
    @dataclass(frozen=True)
    class Current:
        value: list = field(default_factory=lambda: [b'unit-science'])
        def __deepcopy__(self, memo):raise TypeError('owned source cannot be copied')
    guard=NS(solver_calls_forbidden=nullcontext)
    io=NS(encode=encode,digest=digest,pin=lambda value:value)
    source=NS(io=io,ExactSourceCurrent=Current,implementation_identity=lambda:'a'*64,
        historical=NS(history=NS(replay=NS(guard=guard)),verifier_identity=lambda:'e'*64,
            witness=NS(_dispatch_view=lambda caller=None:('explicit-unit-dispatch',))))
    values=[]
    def full_source(root,**kw):
        calls.append(('full_source',str(root)))
        action=faults.get('full_source')
        if action is not None:action(len(values)+1)
        value=Current()
        if faults.get('tail_difference') and values:value.value.append(b'tail-change')
        if faults.get('source_value'):value=faults['source_value'](value,len(values)+1)
        values.append(value)
        return value
    if exact_source is None:source.prepare=full_source
    else:source=exact_source
    phase=NS(source=source,_initial=lambda *a:None,_request=lambda *a:None,business=NS(),RREF='Rref')
    phase._fresh=predecessor.worker.snapshot.phase._fresh
    class Rebuilt:pass
    snapshot=NS(phase=phase,CAP=4096,encode=encode,RebuiltInput=Rebuilt,implementation_identity=lambda:'b'*64)
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
        'def _inspect(root,**kw):\n raw=inspections[str(root)][0]\n _source(raw,root,None)\n _source(raw,root,None)\n if faults.get("hook"):faults["hook"]()\n if faults.get("inspection")==str(root):raise RuntimeError("inspection tail fault")\n return deepcopy(inspections[str(root)][1])\n','_inspect')
    inspection.inspect=function(dict(_inspect=inspection._inspect),
        'def inspect(root,**kw):\n return _inspect(root,**kw)\n','inspect')
    parent=NS(preparation=prep,worker=worker,inspection=inspection,io=io,
        SCHEMA='h1_selector_parent_controller_development_v4',FLAGS={})
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
    raw=encode(dict(declaration=dict(source_binding=source_binding if source_binding is not None else
        dict(root=str(tmp_path),binding_sha256='a'*64,genesis_terminal_sha256='b'*64,registry_identity='c'*64))))
    def make(name,reference=None):
        obj=Parent();obj.root=tmp_path/name;obj.worker_root=obj.root/'worker_non_authoritative'
        obj._guard=Lock();obj._guard.acquire();obj._reference_held=reference is not None
        d=json.loads(raw);d['declaration'].update(role='reference' if reference is None else 'actual',
            lane_id=None if reference is None else name,reference=None)
        obj._raw=encode(d);obj._pid,obj._thread=__import__('os').getpid(),get_ident();obj._options={};obj._own='a'*64;obj._state='complete';obj._binding=b'binding'
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
    api=ModuleType(original._HOST);api.__file__=str(Path(predecessor.__file__).with_name('h1_selector_phase_handoff_development_v6.py'))
    api.Handoff=Host;api.parent=parent
    monkeypatch.setitem(sys.modules,original._HOST,api)
    parent._WINDOWS=NS(raw_source=Parent._source,raw_inspect=Parent._inspect)
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
    attach,validate_bundle,rebuild,finish,abort,receipt,commit,validate_pair,declaration,records_bundle=methods
    result=NS(module=fresh,host=host,token=token,attach=attach,bundle=bundle,parents=[ref,*actuals],actuals=actuals,ref=ref,
        validate_bundle=validate_bundle,rebuild=rebuild,finish=finish,abort=abort,receipt=receipt,
        commit=commit,validate_pair=validate_pair,declaration=declaration,records_bundle=records_bundle,source=source,values=values,
        faults=faults,calls=calls,fallback=fallback)
    def release():
        for guard_ in [*(owner._guard for owner in (ref,*actuals)),*bundle.held]:
            if guard_.locked():guard_.release()
        if host._guard.locked():host._guard.release()
    result.release=release
    result.parent=parent
    from tests.h1_reference_window_test_helpers_v1 import seed_reference
    seed_reference(result,tmp_path)
    try:
        if before_attach is not None:before_attach(host,bundle)
        attach(host,token)
        yield result
    finally:
        abort(host,RuntimeError('unit teardown'))
        release()



def complete(case):
    case.validate_bundle(case.bundle)
    with case.records_bundle(case.bundle):
        for parent in case.parents:
            case.validate_pair(case.bundle,parent,parent._issued)
            case.rebuild(case.bundle,parent)
            case.validate_pair(case.bundle,parent,parent._issued)
    for _ in range(12):case.validate_bundle(case.bundle)


@pytest.mark.parametrize('fault',('runtime','all','any','code','closure'))
def test_definition_seal_rejects_before_first_source_or_reference_read(case,monkeypatch,fault):
    if fault=='runtime':monkeypatch.setattr(case.module,'_RUNTIME',lambda:None)
    elif fault in ('all','any'):monkeypatch.setattr(case.module,fault,lambda *a:False,raising=False)
    elif fault=='code':
        function=case.module._source_signature
        monkeypatch.setattr(function,'__code__',(lambda value:None).__code__)
    else:
        function=case.validate_bundle
        cells=dict(zip(function.__code__.co_freevars,function.__closure__))
        # Replace the registry object, rather than its permitted live contents.
        cell=cells['row_for_bundle']
        original=cell.cell_contents
        monkeypatch.setattr(cell,'cell_contents',lambda bundle:None)
        assert original is not cell.cell_contents
    with pytest.raises(ValueError,match='definition-time'):case.validate_bundle(case.bundle)
    assert not case.values and case.reference_counts['original']==0
    assert case.receipt(case.host)['status']=='aborted'
    case.release()
    assert all(not obj._guard.locked() for obj in case.parents)


def test_complete_four_parent_records_share_one_window(case):
    complete(case);pending=case.finish(case.host)
    assert pending['validation_checks_complete'] and pending['status']=='pending'
    assert (pending['parent_validations'],pending['source_requests'],pending['source_prepares'])==(150,2408,28)
    assert pending['source_window_counts']==dict(bundle=13,records_bundle=1)
    assert len(case.values)==28 and len(pending['source_windows'])==14
    assert sorted(w['nested_source_requests'] for w in pending['source_windows'])==[160]*13+[328]
    assert all(w['window_cache_entry_cleared'] for w in pending['source_windows'])
    references=[w['reference_window'] for w in pending['source_windows']]
    assert sum(w['logical_reference_inspects'] for w in references)==726
    assert sum(w['original_reference_inspects'] for w in references)==28
    assert case.reference_counts['original']==28
    assert all(w['cache_cleared'] for w in references)
    assert sorted(w['logical_reference_inspects'] for w in references)==[48]*13+[102]
    assert pending['parent_sites']==[dict(root=str(obj.root),issued_completion_sha256=digest(obj._issued_bytes),
        pair_validation_sites=2,record_rebuild_sites=1) for obj in case.parents]
    case.release();receipt=case.commit(case.host)
    assert receipt['complete'] and receipt['outer_cleanup_complete']
    assert not receipt['formal_result'] and not receipt['resource_admission']


@pytest.mark.parametrize('edge',['pair','rebuild'])
def test_records_edge_cannot_be_called_outside_bundle_window(case,edge):
    with pytest.raises(ValueError,match='records window'):
        if edge=='pair':case.validate_pair(case.bundle,case.ref,case.ref._issued)
        else:case.rebuild(case.bundle,case.ref)
    assert not case.values
    assert case.receipt(case.host)['status']=='aborted'


@pytest.mark.parametrize('fault',['wrong_owner','wrong_edge','caught_reentry','incomplete'])
def test_noncanonical_or_incomplete_records_bundle_aborts(case,fault):
    with pytest.raises(ValueError):
        with case.records_bundle(case.bundle):
            if fault=='wrong_owner':case.validate_pair(case.bundle,case.actuals[0],case.actuals[0]._issued)
            elif fault=='wrong_edge':case.rebuild(case.bundle,case.ref)
            elif fault=='caught_reentry':
                with pytest.raises(ValueError):
                    with case.records_bundle(case.bundle):pass
            elif fault=='incomplete':case.validate_pair(case.bundle,case.ref,case.ref._issued)
    assert case.receipt(case.host)['status']=='aborted'
    assert case.receipt(case.host)['source_window_cache_cleared']


@pytest.mark.parametrize('at',[1,2])
def test_records_entry_and_tail_fault_never_publish_success(case,at):
    failure=RuntimeError('records bookend failure')
    def fail(number):
        if number==at:raise failure
    case.faults['full_source']=fail
    with pytest.raises(RuntimeError) as caught:
        with case.records_bundle(case.bundle):
            for parent in case.parents:
                case.validate_pair(case.bundle,parent,parent._issued)
                case.rebuild(case.bundle,parent)
                case.validate_pair(case.bundle,parent,parent._issued)
    assert caught.value is failure
    assert case.receipt(case.host)['status']=='aborted'


def test_records_preserve_rebuilt_scientific_value_type(case):
    results=[]
    with case.records_bundle(case.bundle):
        for parent in case.parents:
            case.validate_pair(case.bundle,parent,parent._issued)
            results.append(case.rebuild(case.bundle,parent))
            case.validate_pair(case.bundle,parent,parent._issued)
    assert all(type(item) is sys.modules[case.module._HOST].parent.worker.snapshot.RebuiltInput
        for item in results)
    assert len(case.values)==2


def test_real_handoff6_has_weakref_and_closes_records_window_before_writes():
    import weakref
    from experiments import h1_selector_phase_handoff_development_v6 as h
    from experiments import h1_selector_parent_controller_development_v4 as parent
    assert h.parent is parent and h.parent_validation is original
    owner=object.__new__(h.Handoff)
    assert weakref.ref(owner)() is owner
    tree=ast.parse(Path(h.__file__).read_bytes())
    owner=next(n for n in tree.body if isinstance(n,ast.ClassDef) and n.name=='Handoff')
    prepare=next(n for n in owner.body if isinstance(n,ast.FunctionDef) and n.name=='_prepare')
    windows=[n for n in prepare.body if isinstance(n,ast.With)]
    assert len(windows)==1
    choice=windows[0].items[0].context_expr
    assert isinstance(choice,ast.IfExp) and ast.unparse(choice.body)=='_PARENT_RECORDS_BUNDLE(bundle)'
    assert ast.unparse(choice.orelse)=='nullcontext()'
    assert not any(isinstance(n,ast.Call) and isinstance(n.func,ast.Attribute) and
        (n.func.attr in ('mkdir','write_new') or
         (n.func.attr=='append' and ast.unparse(n.func.value) in ('self._journal','self._holder')))
        for n in ast.walk(windows[0]))
