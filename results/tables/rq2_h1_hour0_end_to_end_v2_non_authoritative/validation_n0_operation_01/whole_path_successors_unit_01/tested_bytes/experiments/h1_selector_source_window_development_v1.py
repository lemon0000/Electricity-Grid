"""Private synchronous source windows for the Parent3 lifecycle.

Source freshness is observed at entry/exit of fixed callback-free method bodies.
The engine clears its cached reference at every window exit and external boundary;
derived consumer values retain their original lifetime.
"""
from contextlib import contextmanager
from copy import deepcopy
import dis
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from threading import Lock, get_ident
from types import FunctionType, SimpleNamespace, MappingProxyType
from weakref import WeakKeyDictionary

from experiments import h1_selector_parent_validation_operation_development_v2 as kernel

SCHEMA='h1_selector_source_window_development_v1'
COUNTS=MappingProxyType(dict(construct_prepare=(4,4),construct_finish=(20,20),
    run_pre=(12,28),run_release=(12,28),run_quiet=(16,32),run_post=(28,76),validate=(16,48)))
_source_signature=kernel._source_signature
_source_types=kernel._source_types
_capture_source_guard=kernel._capture_source_guard
copy=deepcopy


def _encode(value):
    return json.dumps(value,sort_keys=True,separators=(',', ':'),ensure_ascii=True,allow_nan=False).encode('ascii')


def implementation_identity():
    return sha256(_encode([SCHEMA,sha256(Path(__file__).read_bytes()).hexdigest(),
        kernel.implementation_identity(),dict(COUNTS)])).hexdigest()


def state(value):
    return (value.__code__,repr(value.__defaults__),repr(value.__kwdefaults__)) if type(value) is FunctionType else None


def clone(function,**changes):
    namespace=dict(function.__globals__);namespace.update(changes)
    result=FunctionType(function.__code__,namespace,function.__name__,function.__defaults__,function.__closure__)
    result.__kwdefaults__=copy(function.__kwdefaults__)
    return result


def _make_routes(row, parent, check, raw_source, raw_inspect):
    old_snapshot, old_worker = (parent.worker.snapshot, parent.worker)
    old_preparation, old_inspection = (parent.preparation, parent.inspection)
    old_phase = old_snapshot.phase
    source = old_phase.source
    functions = []
    proxies = []
    fixed_source = _capture_source_guard(source)
    direct = []

    def captured(obj, name):
        value = getattr(obj, name)
        direct.append((obj, name, value, state(value)))
        return value
    full_source = captured(source, 'prepare')

    def successor(function, **changes):
        result = clone(function, **changes)
        pending = [function.__code__]
        names = {'__builtins__'}
        while pending:
            code = pending.pop()
            names.update((instruction.argval for instruction in dis.get_instructions(code) if instruction.opname == 'LOAD_GLOBAL'))
            pending.extend((value for value in code.co_consts if type(value) is type(code)))
        functions.append((function, state(function), result, state(result), tuple(((name, result.__globals__[name]) for name in names if name in result.__globals__))))
        return result

    def proxy(**values):
        result = SimpleNamespace(**values)
        proxies.append((result, tuple(values.items())))
        return result

    def source_prepare(root, **arguments):
        owner = row['frames'][-1]['owner'] if row['frames'] else None
        check(row, owner)
        window = row['window']
        if window is None or not window['active'] or window['in_full_prepare']:
            raise ValueError('source request requires an active synchronous validation window')
        if str(root) != window['root'] or arguments != window['arguments']:
            raise ValueError('nested Parent source root, pins or registry differs')
        old = json.loads(owner._raw)['declaration']['source_binding']
        if old != row['source_binding']:
            raise ValueError('Parent source binding changed within validation window')
        if _source_signature(window['value']) != window['signature'] or _source_types(window['value']) != window['types']:
            raise ValueError('owned window source fields changed')
        result = window['value']
        if type(result) is not source.ExactSourceCurrent or _source_signature(result) != window['signature'] or _source_types(result) != window['types']:
            raise ValueError('complete original owned source required')
        row['frames'][-1]['completed_sources'] += 1
        row['source_requests'] += 1
        window['requests'] += 1
        check(row, owner)
        return result

    def materialize(root, arguments):
        check_routes()
        value = full_source(root, **arguments)
        check_routes()
        if type(value) is not source.ExactSourceCurrent:
            raise TypeError('original complete exact source kernel required')
        return value
    phase_source = proxy(io=source.io, prepare=source_prepare)
    fresh_source = successor(old_phase._fresh, source=phase_source)
    phase = proxy(_fresh=fresh_source, _initial=old_phase._initial, _request=old_phase._request, business=old_phase.business, RREF=old_phase.RREF)
    build = successor(old_snapshot._build, phase=phase)
    rebuild = successor(old_snapshot.rebuild, _build=build)
    snapshot = proxy(rebuild=rebuild, CAP=old_snapshot.CAP, encode=old_snapshot.encode, RebuiltInput=old_snapshot.RebuiltInput, implementation_identity=old_snapshot.implementation_identity)
    request = successor(old_worker.request_document, snapshot=snapshot)
    worker = proxy(request_document=request, CAP=old_worker.CAP, sequence=old_worker.sequence, runtime=old_worker.runtime, content_bound=old_worker.content_bound, implementation_identity=old_worker.implementation_identity)
    prepare = successor(old_preparation.prepare, worker=worker)
    bind = successor(old_preparation.bind, prepare=prepare)
    preparation = proxy(prepare=prepare, bind=bind)
    inspect_source = successor(old_inspection._source, snapshot=snapshot)
    inspect_body = successor(old_inspection._inspect, _source=inspect_source, snapshot=snapshot)
    inspect_entry = successor(old_inspection.inspect, _inspect=inspect_body)
    inspection = proxy(INPUT_FILES=old_inspection.INPUT_FILES, inspect=inspect_entry)
    parent_source = successor(raw_source, preparation=preparation)
    parent_inspect = successor(raw_inspect, inspection=inspection)

    def check_routes():
        if any((getattr(obj, name) is not value or state(value) != original for obj, name, value, original in direct)):
            raise ValueError('fixed Parent exact-source direct dispatch changed')
        fixed_source()
        for original, original_state, fn, fn_state, values in functions:
            if state(original) != original_state or state(fn) != fn_state or any((fn.__globals__.get(name) is not value for name, value in values)):
                raise ValueError('fixed Parent functional successor route changed')
        for obj, values in proxies:
            if len(vars(obj)) != len(values) or any((vars(obj).get(name) is not value for name, value in values)):
                raise ValueError('fixed Parent functional successor proxy changed')
    check_routes()
    route_declaration = dict(schema=SCHEMA, helper_identity=implementation_identity(), predecessor_snapshot_implementation=old_snapshot.implementation_identity(), predecessor_source_implementation=source.implementation_identity(), source_schedule='one_original_prepare_before_and_after_each_public_window', same_predecessor_per_nested_source_io_schedule=False, same_predecessor_failure_order=False, source_result_reuse_scope='single_synchronous_window_without_external_callback', cleared_state_scope='window_cache_entry_only', predecessor_derived_outputs_follow_original_consumer_lifetime=True, full_source_object_graph_destroyed=False, cross_window_source_reuse=False, complete_dynamic_input_closure_proved=False, unobserved_between_bookends_ABA_covered=False, predecessor_payload_scope='scientific_compatibility_projection_only', compatibility_counts_describe_actual_execution=False, route=[dict(function=original.__qualname__, file=original.__code__.co_filename) for original, _, _, _, _ in functions])
    check_routes()
    return dict(source=parent_source, inspect=parent_inspect, rebuild=rebuild, check=check_routes, materialize=materialize, prepare=prepare, bind=bind, declaration=route_declaration)


def _bind_parent(parent,raw_source,raw_inspect,callers):
    """Bound before Parent3 freezes its namespace; arm its captured checker once."""
    actives={};inventories=WeakKeyDictionary();registry_lock=Lock();checker=None;api=None
    fixed_callers=dict(callers)
    original_kind=parent.Parent
    own_identity=implementation_identity()
    own_state=tuple((fn,state(fn)) for fn in (raw_source,raw_inspect,
        *(value for value in vars(original_kind).values() if type(value) is FunctionType)))
    api_members=None

    def fixed():
        _RUNTIME()
        if (checker is None or parent.Parent is not original_kind or parent._CHECK is not checker
                or parent._WINDOWS is not api
                or any(state(fn)!=before for fn,before in own_state)
                or any(getattr(api,name) is not value or state(value)!=before
                    for name,value,before in api_members)):
            raise ValueError('fixed original Parent source-window anchor required')
        checker()

    def check(row,owner=None):
        fixed()
        if actives.get(row['creator']) is not row or row['creator']!=(os.getpid(),get_ident()) or row['failure'] is not None:
            raise ValueError('original lifecycle source-window lifetime required')
        for index,entry in enumerate(row['parents']):
            obj,raw,guard,locked,base,issued,issued_bytes=entry
            if (type(obj) is not original_kind or obj._raw is not raw or obj._guard is not guard
                    or guard.locked() is not locked
                    or (obj._pid,obj._thread)!=(os.getpid(),get_ident())
                    or (obj.root,obj.worker_root,obj._nonce,obj._own,_encode(obj._options))!=base
                    or json.loads(raw)['declaration']['source_binding']!=row['source_binding']):
                raise ValueError('original Parent source, guard, creator or declaration changed')
            if index:
                if (obj._state!='complete' or obj._issued is not issued or obj._issued_bytes!=issued_bytes
                        or parent._completion_bytes(issued)!=issued_bytes
                        or row['owner']._reference_owner is not obj
                        or row['owner']._reference_completion is not issued
                        or row['owner']._reference_held is not True):
                    raise ValueError('original held reference completion changed')
            elif row['kind'].startswith('construct_'):
                states=('constructing',) if row['kind']=='construct_prepare' else ('constructing','prepared')
                if obj._state not in states or obj._issued is not None:
                    raise ValueError('original partial construction state required')
            elif row['kind']=='run_post':
                if obj._state not in ('running','complete'):
                    raise ValueError('original post-Job publication state required')
                if obj._issued is not None and (obj._state!='complete'
                        or type(obj._issued) is not parent.ParentCompletion
                        or parent._completion_bytes(obj._issued)!=obj._issued_bytes):
                    raise ValueError('original post-Job completion required')
            else:
                expected='complete' if row['kind']=='validate' else 'running'
                if obj._state!=expected or obj._issued is not issued or obj._issued_bytes!=issued_bytes:
                    raise ValueError('original running or completed Parent state required')
        if row['owner']._source_windows is not row['prior_receipts']:
            raise ValueError('Parent diagnostic inventory changed inside window')
        if owner is not None:
            if not row['frames'] or row['frames'][-1]['owner'] is not owner:
                raise ValueError('original current lifecycle source site required')
        if row['routes'] is not None:row['routes']['check']()
        return parent

    def dispatch(kind,owner,*arguments,**keywords):
        creator=(os.getpid(),get_ident())
        if (owner._pid,owner._thread)!=creator:
            raise ValueError('original lifecycle source-window creator required')
        row=actives.get(creator)
        if row is None:raise ValueError('Parent core requires its original source window')
        if not any(owner is entry[0] for entry in row['parents']):
            error=ValueError('original lifecycle Parent site required')
            if row['failure'] is None:row['failure']=repr(error)
            raise error
        frame=dict(owner=owner,completed_sources=0)
        row['frames'].append(frame)
        try:
            check(row,owner)
            result=row['routes'][kind](owner,*arguments,**keywords) if kind in ('source','inspect') else row['routes'][kind](*arguments,**keywords)
            check(row,owner)
            return result
        except BaseException as error:
            if row['creator']==(os.getpid(),get_ident()) and row['failure'] is None:row['failure']=repr(error)
            raise
        finally:
            if row['frames'] and row['frames'][-1] is frame:row['frames'].pop()

    @contextmanager
    def scoped(owner,kind):
        row=None;registered=False;error=None;window=None;receipt=None
        creator=(os.getpid(),get_ident())
        try:
            fixed()
            if type(owner) is not original_kind or (owner._pid,owner._thread)!=creator:
                raise TypeError('original Parent creator required for source window')
            constructing=kind.startswith('construct_')
            role=json.loads(owner._raw)['declaration']['role']
            if role not in ('reference','actual'):raise ValueError('exact lifecycle source role required')
            binding=json.loads(owner._raw)['declaration']['source_binding']
            ref=None if constructing else owner._reference_owner
            parents=[owner] if ref is None else [owner,ref]
            if ref is not None and (type(ref) is not original_kind or ref is owner
                    or ref._reference_owner is not None or ref._issued is not owner._reference_completion
                    or parent._completion_bytes(ref._issued)!=ref._issued_bytes):
                raise ValueError('exact live original Rref pair required')
            for obj in parents:
                if ((obj._pid,obj._thread)!=creator or type(obj._raw) is not bytes
                        or obj._guard.locked() is not (not constructing)
                        or json.loads(obj._raw)['declaration']['source_binding']!=binding):
                    raise ValueError('original lifecycle locks and complete source binding required')
            with registry_lock:
                saved=inventories.get(owner,())
            if owner._source_windows is not saved:
                raise ValueError('original prior lifecycle receipt inventory required')
            row=dict(owner=owner,kind=kind,creator=creator,source_binding=copy(binding),
                parents=tuple((obj,obj._raw,obj._guard,obj._guard.locked(),
                    (obj.root,obj.worker_root,obj._nonce,obj._own,_encode(obj._options)),obj._issued,obj._issued_bytes)
                    for obj in parents),frames=[],failure=None,routes=None,window=None,
                source_requests=0,prior_receipts=owner._source_windows)
            with registry_lock:
                active=actives.get(creator)
                if active is not None:
                    failure=ValueError('Parent lifecycle source window is nonreentrant')
                    if active['creator']==creator and active['failure'] is None:active['failure']=repr(failure)
                    raise failure
                actives[creator]=row;registered=True
            check(row)
            row['routes']=_make_routes(row,parent,check,raw_source,raw_inspect)
            arguments=dict(expected_binding_sha256=binding['binding_sha256'],
                expected_terminal_sha256=binding['genesis_terminal_sha256'],completed_hours=1,
                expected_registry_identity=binding['registry_identity'])
            window=dict(root=binding['root'],arguments=arguments,value=None,signature=None,types=None,
                active=False,in_full_prepare=True,requests=0)
            row['window']=window
            before=row['routes']['materialize'](window['root'],arguments)
            signature=_source_signature(before);types=_source_types(before)
            window.update(value=before,signature=signature,types=types,active=True,in_full_prepare=False)
            check(row)
            yield
            check(row)
            if row['frames'] or _source_signature(before)!=signature or _source_types(before)!=types:
                raise ValueError('lifecycle retained source or frame inventory changed')
            window['in_full_prepare']=True
            after=row['routes']['materialize'](window['root'],arguments)
            check(row)
            if _source_signature(after)!=signature or _source_types(after)!=types:
                raise ValueError('source changed during lifecycle window')
            expected=COUNTS[kind][role=='actual']
            if row['source_requests']!=expected or window['requests']!=expected:
                raise ValueError('complete original lifecycle source request inventory required')
            route=copy(row['routes']['declaration'])
            receipt=dict(schema=SCHEMA,kind=kind,role=role,root=str(owner.root),
                implementation=own_identity,parent_implementation=owner._own,
                source_route_declaration=route,source_route_sha256=sha256(_encode(route)).hexdigest(),
                logical_source_requests=expected,original_source_prepares=2,
                complete_source_signature_sha256=signature,source_binding=copy(binding),
                full_numerical_hour_replays=8,within_prefix_numerical_revalidations=8,fresh_context_observations=32,
                source_schedule='one_original_source_prepare_at_each_synchronous_window_bookend',
                per_site_source_io_schedule_preserved=False,predecessor_failure_order_preserved=False,
                source_reuse_across_job_or_callback_boundary=False,cross_window_source_reuse=False,
                complete_dynamic_input_closure_proved=False,unobserved_between_bookends_ABA_covered=False,
                cleared_state_scope='window_cache_entry_only',full_source_object_graph_destroyed=False,
                complete=True,source_window_cache_cleared=False,formal_result=False,resource_admission=False,
                native_execution_authorized=False)
        except BaseException as failure:
            error=failure
            if registered and row['failure'] is None:row['failure']=repr(failure)
            raise
        finally:
            if window is not None:window.clear()
            if row is not None:row['window']=None;row['frames'].clear()
            if registered:
                with registry_lock:
                    if actives.get(creator) is row:actives.pop(creator)
                if receipt is not None:
                    receipt['source_window_cache_cleared']=True
                    try:
                        saved=(*row['prior_receipts'],_encode(receipt))
                        with registry_lock:inventories[owner]=saved
                        owner._source_windows=saved
                    except BaseException as cleanup:
                        if error is not None:error.add_note('source receipt cleanup: '+repr(cleanup))
                        else:raise
            if row is not None:row.clear()

    def window(owner,kind):
        fixed()
        creator=(os.getpid(),get_ident())
        with registry_lock:
            active=actives.get(creator)
            if active is not None:
                error=ValueError('Parent lifecycle source window is nonreentrant')
                if active['creator']==creator and active['failure'] is None:active['failure']=repr(error)
                raise error
        frame=sys._getframe(1)
        code=fixed_callers.get(kind)
        if code is None or frame.f_code is not code or frame.f_locals.get('self') is not owner:
            raise ValueError('original fixed Parent lifecycle call site required')
        return scoped(owner,kind)

    def source(owner):return dispatch('source',owner)
    def inspect(owner,*args,**kwargs):return dispatch('inspect',owner,*args,**kwargs)
    def prepare(owner,*args,**kwargs):return dispatch('prepare',owner,*args,**kwargs)
    def bind(owner,*args,**kwargs):return dispatch('bind',owner,*args,**kwargs)
    def receipts(owner):
        fixed();owner._check()
        with registry_lock:saved=inventories.get(owner,())
        if owner._source_windows is not saved or type(saved) is not tuple or any(type(item) is not bytes for item in saved):
            raise ValueError('original lifecycle diagnostic byte inventory required')
        return [json.loads(item) for item in owner._source_windows]
    def assert_idle(owner):
        fixed()
        creator=(os.getpid(),get_ident())
        if type(owner) is not original_kind or (owner._pid,owner._thread)!=creator:
            raise ValueError('original lifecycle boundary creator required')
        if actives.get(creator) is not None:raise ValueError('source cache must be empty at Job or callback boundary')
    def arm(value):
        nonlocal checker
        if checker is not None:raise ValueError('one original Parent checker binding required')
        checker=value
    api=SimpleNamespace(window=window,source=source,inspect=inspect,prepare=prepare,bind=bind,
        receipts=receipts,assert_idle=assert_idle,arm=arm,raw_source=raw_source,raw_inspect=raw_inspect)
    api_members=tuple((name,value,state(value)) for name,value in vars(api).items())
    return api


def _install_runtime():
    namespace=globals()
    bindings=tuple((name,value,state(value)) for name,value in tuple(namespace.items())
        if not name.startswith('__'))
    constants=tuple(COUNTS.items())
    def check():
        if (tuple(COUNTS.items())!=constants or any(namespace.get(name) is not value or state(value)!=before
                for name,value,before in bindings)):
            raise ValueError('definition-time lifecycle source-window implementation changed')
        kernel._RUNTIME()
    return check


_RUNTIME=_install_runtime()
