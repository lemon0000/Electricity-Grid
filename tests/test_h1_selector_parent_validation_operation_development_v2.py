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
from experiments import h1_selector_parent_validation_operation_development_v2 as original


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
    raw=encode(dict(declaration=dict(source_binding=source_binding if source_binding is not None else
        dict(root=str(tmp_path),binding_sha256='a'*64,genesis_terminal_sha256='b'*64,registry_identity='c'*64))))
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
    result=NS(module=fresh,host=host,token=token,attach=attach,bundle=bundle,parents=[ref,*actuals],actuals=actuals,ref=ref,
        validate_bundle=validate_bundle,rebuild=rebuild,finish=finish,abort=abort,receipt=receipt,
        commit=commit,validate_pair=validate_pair,declaration=declaration,source=source,values=values,
        faults=faults,calls=calls,fallback=fallback)
    def release():
        for guard_ in [*(owner._guard for owner in (ref,*actuals)),*bundle.held]:
            if guard_.locked():guard_.release()
        if host._guard.locked():host._guard.release()
    result.release=release
    try:
        if before_attach is not None:before_attach(host,bundle)
        attach(host,token)
        yield result
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


def test_complete_windows_keep_parent_recursion_and_record_rebuilds(case):
    complete(case)
    pending=case.finish(case.host)
    assert pending['validation_checks_complete'] and pending['status']=='pending'
    assert not pending['complete'] and not pending['outer_cleanup_complete']
    assert pending['parent_validations']==150 and pending['source_requests']==2408
    assert pending['source_prepares']==len(case.values)==50
    assert pending['source_window_counts']==dict(bundle=13,pair=8,records=4)
    assert [(site['root'],site['pair_windows'],site['record_windows']) for site in pending['parent_sites']]==[
        (str(owner.root),2,1) for owner in case.parents]
    assert len(pending['source_windows'])==25
    assert pending['full_numerical_hour_replays']==200
    assert pending['within_prefix_numerical_revalidations']==200
    assert pending['reused_numerical_inspections']==0
    assert pending['fresh_context_observations']==800
    assert pending['borrowed_source_returns']==2408
    assert pending['source_window_cache_cleared'] and not case.fallback
    assert sorted(v['nested_source_requests'] for v in pending['source_windows'])==[2]*4+[16]*2+[48]*6+[160]*13
    assert all(v['parent_root'] is None for v in pending['source_windows'] if v['kind']=='bundle')
    for owner in case.parents:
        assert sorted(v['kind'] for v in pending['source_windows'] if v['parent_root']==str(owner.root))==[
            'pair','pair','records']
    assert all(v['closed'] and v['window_cache_entry_cleared'] for v in pending['source_windows'])
    declaration=pending['declaration']
    assert declaration['source_schedule']=='one_original_prepare_before_and_after_each_public_window'
    assert declaration['cleared_state_scope']=='window_cache_entry_only'
    assert declaration['predecessor_derived_outputs_follow_original_consumer_lifetime']
    assert declaration['full_source_object_graph_destroyed'] is False
    assert all(declaration[key] is False for key in (
        'same_predecessor_per_nested_source_io_schedule','same_predecessor_failure_order',
        'cross_window_source_reuse','complete_dynamic_input_closure_proved',
        'unobserved_between_bookends_ABA_covered'))
    with pytest.raises(ValueError,match='resources remain'):case.commit(case.host)
    case.release()
    assert case.commit(case.host)['status']=='committed'
    with pytest.raises(ValueError,match='single pending'):case.commit(case.host)


@pytest.mark.parametrize('kind',['entry','tail','tail_fields','body','owned_fields'])
def test_failure_discards_scope_and_never_publishes_pending_or_commit(case,kind):
    if kind in ('entry','tail'):
        def fail(call):
            if call==(1 if kind=='entry' else 2):raise OSError('source IO '+kind)
        case.faults['full_source']=fail
    elif kind=='tail_fields':case.faults['tail_difference']=True
    elif kind=='body':case.faults['inspection']=str(case.ref.worker_root)
    else:case.faults['hook']=lambda:case.values[0].value.append(b'mutation')
    with pytest.raises((ValueError,RuntimeError,OSError)):case.validate_bundle(case.bundle)
    terminal=case.receipt(case.host)
    assert terminal['status']=='aborted' and not terminal['complete']
    assert not terminal['validation_checks_complete'] and terminal['source_window_cache_cleared']
    assert terminal['source_window_counts']==dict(bundle=0,pair=0,records=0)
    if kind=='body':assert len(case.values)==1
    with pytest.raises(ValueError):case.validate_bundle(case.bundle)
    case.release()
    with pytest.raises(ValueError):case.commit(case.host)


@pytest.mark.parametrize('fault',['root','binding','terminal','registry','raw_object','issued','mark','unlock'])
def test_exact_parent_source_keys_and_original_objects_admitted_before_source(case,fault):
    parent=case.actuals[0]
    if fault in ('root','binding','terminal','registry'):
        doc=json.loads(parent._raw)
        key=dict(root='root',binding='binding_sha256',terminal='genesis_terminal_sha256',registry='registry_identity')[fault]
        doc['declaration']['source_binding'][key]='different'
        parent._raw=encode(doc)
    elif fault=='raw_object':parent._raw=bytes(bytearray(parent._raw))
    elif fault=='issued':parent._issued=NS(**vars(parent._issued))
    elif fault=='mark':parent._reference_held=False
    else:parent._guard.release()
    with pytest.raises((ValueError,TypeError)):case.validate_bundle(case.bundle)
    assert not case.values
    assert case.receipt(case.host)['status']=='aborted'


def test_foreign_pair_rejected_before_original_source_io(case):
    with pytest.raises(TypeError,match='before source'):case.validate_pair(case.bundle,object(),case.ref._issued)
    assert not case.values and case.receipt(case.host)['status']=='aborted'


@pytest.mark.parametrize('fault',['substituted_guard','duplicate_guard','missing_mark','duplicate_mark'])
def test_attach_rejects_unrelated_guard_or_mark_inventory_before_source(tmp_path,monkeypatch,fault):
    captured=[]
    def before_attach(host,bundle):
        captured.extend([host,bundle])
        if fault=='substituted_guard':
            guard=Lock();guard.acquire();bundle.held[0]=guard
        elif fault=='duplicate_guard':bundle.held[0]=bundle.held[1]
        elif fault=='missing_mark':bundle.marked.pop()
        else:bundle.marked[0]=bundle.marked[1]
    generator=make_case(tmp_path,monkeypatch,before_attach=before_attach)
    with pytest.raises(ValueError,match='guard and mark inventory'):next(generator)
    host,bundle=captured
    assert not host._guard.locked() and all(not guard.locked() for guard in bundle.held)


@pytest.mark.parametrize('fault',['foreign_owner','route'])
def test_rebuild_admission_failure_aborts_before_original_source_io(case,monkeypatch,fault):
    if fault=='route':monkeypatch.setattr(case.source,'prepare',lambda *a,**k:pytest.fail('foreign source invoked'))
    with pytest.raises((TypeError,ValueError)):
        case.rebuild(case.bundle,object() if fault=='foreign_owner' else case.ref)
    terminal=case.receipt(case.host)
    assert not case.values and terminal['status']=='aborted' and terminal['source_window_cache_cleared']
    with pytest.raises(ValueError):case.validate_bundle(case.bundle)
    case.release()
    with pytest.raises(ValueError):case.commit(case.host)


def test_closed_receipt_rejects_foreign_thread_without_changing_creator_state(case):
    complete(case);case.finish(case.host)
    before=case.receipt(case.host);errors=[]
    def foreign():
        for action in (lambda:case.receipt(case.host),lambda:case.abort(case.host,RuntimeError('foreign')),
                lambda:case.commit(case.host)):
            try:action()
            except ValueError as error:errors.append(str(error))
    worker=Thread(target=foreign);worker.start();worker.join(5)
    assert not worker.is_alive() and len(errors)==3 and case.receipt(case.host)==before
    case.release()
    assert case.commit(case.host)['status']=='committed'


@pytest.mark.parametrize('fault',['route','host','incomplete'])
def test_finish_failure_clears_operation_and_preserves_failed_receipt(case,monkeypatch,fault):
    if fault=='route':monkeypatch.setattr(case.source,'prepare',lambda *a,**k:pytest.fail('foreign source invoked'))
    elif fault=='host':monkeypatch.setattr(sys.modules[original._HOST],'Handoff',object)
    with pytest.raises(ValueError):case.finish(case.host)
    terminal=case.receipt(case.host)
    assert terminal['status']=='aborted' and terminal['first_failure'] is not None
    assert terminal['source_window_cache_cleared'] and not case.values
    case.abort(case.host,RuntimeError('later cleanup'))
    assert case.receipt(case.host)==terminal
    with pytest.raises(ValueError):case.validate_bundle(case.bundle)
    case.release()
    with pytest.raises(ValueError):case.commit(case.host)


def test_entry_body_and_tail_route_drift_rejected(case,monkeypatch):
    original=case.source.prepare
    def drift():monkeypatch.setattr(case.source,'prepare',lambda *a,**k:pytest.fail('foreign dispatch invoked'))
    case.faults['hook']=drift
    with pytest.raises(ValueError,match='dispatch'):case.validate_bundle(case.bundle)
    assert len(case.values)==1
    monkeypatch.setattr(case.source,'prepare',original)
    assert case.receipt(case.host)['status']=='aborted'


def test_wrong_thread_cannot_poison_or_close_creators_window(case):
    errors=[]
    def foreign():
        for action in (lambda:case.validate_bundle(case.bundle),
                lambda:case.validate_pair(case.bundle,case.ref,case.ref._issued),
                lambda:case.rebuild(case.bundle,case.ref),
                lambda:case.abort(case.host,RuntimeError('foreign'))):
            try:action()
            except ValueError as error:errors.append(str(error))
    worker=Thread(target=foreign);worker.start();worker.join(5)
    assert not worker.is_alive() and len(errors)==4 and not case.values
    case.validate_bundle(case.bundle)
    assert len(case.values)==2


def test_caught_reentrant_attempt_poisoned_without_recursive_source_work(case):
    caught=[]
    def reenter():
        try:case.validate_pair(case.bundle,case.ref,case.ref._issued)
        except ValueError as error:caught.append(str(error))
    case.faults['hook']=reenter
    with pytest.raises(ValueError):case.validate_bundle(case.bundle)
    assert caught==['Parent validation window is nonreentrant'] and len(case.values)==1
    terminal=case.receipt(case.host)
    assert terminal['status']=='aborted' and 'nonreentrant' in terminal['first_failure']


def test_completed_abort_preserves_first_failure_and_forbids_commit(case):
    complete(case);case.finish(case.host)
    case.abort(case.host,RuntimeError('outer cleanup'))
    first=case.receipt(case.host)
    case.abort(case.host,ValueError('secondary'))
    assert case.receipt(case.host)==first
    case.release()
    with pytest.raises(ValueError):case.commit(case.host)


@pytest.mark.parametrize('state',['pending','aborted'])
def test_finalized_host_cannot_reattach_or_replace_its_receipt(case,state):
    if state=='pending':complete(case);case.finish(case.host)
    else:case.abort(case.host,RuntimeError('original abort'))
    before=case.receipt(case.host);calls=list(case.calls)
    with pytest.raises(ValueError,match='already finalized'):case.attach(case.host,case.token)
    assert case.receipt(case.host)==before and case.calls==calls
    if state=='pending':
        case.release()
        assert case.commit(case.host)['status']=='committed'


@pytest.mark.parametrize('kind',['pair','records'])
def test_duplicate_parent_site_cannot_replace_an_omitted_owner(case,kind):
    action=(lambda:case.validate_pair(case.bundle,case.actuals[0],case.actuals[0]._issued)) if kind=='pair' else (
        lambda:case.rebuild(case.bundle,case.actuals[0]))
    for _ in range(2 if kind=='pair' else 1):action()
    calls=list(case.calls)
    with pytest.raises(ValueError,match='count exceeded for original owner'):action()
    assert case.calls==calls
    terminal=case.receipt(case.host)
    assert terminal['status']=='aborted' and terminal['source_window_cache_cleared']
    case.release()
    with pytest.raises(ValueError):case.commit(case.host)


def test_signature_and_type_vector_bind_all_nested_class_objects():
    @dataclass
    class Nested:
        value:int
    @dataclass
    class Outer:
        nested:object
    original_value=Outer(Nested(3))
    same_name=type('Nested',(),dict(__annotations__={'value':int}))
    same_name.__module__=Nested.__module__;same_name.__qualname__=Nested.__qualname__
    replacement=dataclass(same_name)
    replaced=Outer(replacement(3))
    assert original._source_signature(original_value)==original._source_signature(replaced)
    assert original._source_types(original_value)!=original._source_types(replaced)


def test_window_tail_rejects_same_name_nested_class_despite_equal_field_signature(case):
    @dataclass
    class Nested:
        value:int
    same_name=type('Nested',(),dict(__annotations__={'value':int}))
    same_name.__module__=Nested.__module__;same_name.__qualname__=Nested.__qualname__
    replacement=dataclass(same_name)
    def source_value(value,call):
        value.value[:]=[(Nested if call==1 else replacement)(3)]
        return value
    case.faults['source_value']=source_value
    with pytest.raises(ValueError,match='source fields changed'):case.validate_bundle(case.bundle)
    before,after=case.values
    assert case.module._source_signature(before)==case.module._source_signature(after)
    assert case.module._source_types(before)!=case.module._source_types(after)
    terminal=case.receipt(case.host)
    assert terminal['status']=='aborted' and terminal['source_window_cache_cleared']
    case.release()
    with pytest.raises(ValueError):case.commit(case.host)

