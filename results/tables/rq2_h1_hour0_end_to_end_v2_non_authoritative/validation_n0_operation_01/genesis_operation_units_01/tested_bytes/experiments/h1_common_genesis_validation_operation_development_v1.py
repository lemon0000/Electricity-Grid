"""One-shot typed-compatible Genesis numerical observation successor.

Install before consumers in a dedicated interpreter. Disk Gen2 stays frozen;
new headers bind this adapter's active identity. Every common return still
rebuilds metadata and all independent N0 contexts. Only numerical proofs span
calls in one constructor or inspection. Exit the process after restoration.
"""
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from threading import get_ident
from types import FunctionType,ModuleType,SimpleNamespace
from weakref import WeakKeyDictionary

from experiments import h1_common_genesis_validation_routes_development_v1 as route_kernel

SCHEMA='h1_common_genesis_validation_operation_development_v1'
PLANS=(('create',15),('reopen',3),('inspect',2))
CONTRACT=dict(source_context_rebuilt_per_common=True,numerical_proof_scope='one_public_Genesis_method',
    report_reused=False,common_compatibility_payload_scope='predecessor_science_and_metadata_only',
    compatibility_counts_describe_actual_execution=False,per_site_failure_order_preserved=False,
    callback_between_bookends_ABA_covered=False,complete_dynamic_input_closure_proved=False,
    reopen_requires_same_active_adapter=True,post_scope_consumer_reuse_allowed=False,
    process_must_exit_after_receipt=True,formal_result=False,resource_admission=False,
    native_execution_authorized=False)


def _encode(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')


def _state(fn):
    return (fn.__code__,repr(fn.__defaults__),repr(fn.__kwdefaults__),
        tuple(id(c.cell_contents) for c in fn.__closure__ or ())) if type(fn) is FunctionType else None


def _clone(fn,**changes):
    namespace=dict(fn.__globals__);namespace.update(changes)
    result=FunctionType(fn.__code__,namespace,fn.__name__,fn.__defaults__,fn.__closure__)
    result.__kwdefaults__=deepcopy(fn.__kwdefaults__)
    return result


def implementation_identity():
    return sha256(_encode([SCHEMA,sha256(Path(__file__).read_bytes()).hexdigest(),
        route_kernel.implementation_identity(),PLANS,CONTRACT])).hexdigest()


def _reject_consumers(host,caller):
    """Refuse preloaded project consumers, including descriptor-container pins."""
    root=Path(__file__).resolve().parents[1]
    targets=(host,host.CommonOwnerGenesis,host.implementation_identity,
        host.CommonOwnerGenesis.__init__,host.CommonOwnerGenesis._enter,
        host.CommonOwnerGenesis._leave,host.CommonOwnerGenesis._correspondence,host.CommonOwnerGenesis.inspect)
    def contains(value,seen,depth=0):
        if any(value is item for item in targets):return True
        if id(value) in seen or depth>16:return False
        seen.add(id(value))
        if type(value) in (tuple,list,set,frozenset):return any(contains(v,seen,depth+1) for v in value)
        if type(value) is dict:return any(contains(v,seen,depth+1) for v in value.values())
        return False
    for module in tuple(sys.modules.values()):
        if not isinstance(module,ModuleType) or module is host:continue
        path=getattr(module,'__file__',None)
        if not isinstance(path,str):continue
        try:Path(path).resolve().relative_to(root)
        except ValueError:continue
        for name,value in tuple(vars(module).items()):
            if module is caller and value is host:continue
            if (module is sys.modules.get('experiments') and name==host.__name__.rsplit('.',1)[-1]
                    and value is host):continue
            if contains(value,set()):
                raise ValueError('Genesis adapter must precede every project consumer: '+module.__name__)


def _build():
    records={};binding=None;used=False

    def verify(lease):
        _RUNTIME()
        row=records.get(id(lease))
        if row is None or row['lease'] is not lease:raise ValueError('original active Genesis lease required')
        b=row['binding'];b['check']();owner=row['owner'];roster=row['roster']
        if (row['creator']!=(os.getpid(),get_ident()) or row['failure'] is not None
                or row['closed'] or type(owner) is not b['kind'] or owner._self is not owner
                or owner._operation is not row['guards'][0] or owner._original_operation is not row['guards'][0]
                or owner._roster is not roster or owner._original_roster is not roster
                or roster._operation is not row['guards'][1] or roster._original_operation is not row['guards'][1]
                or roster._owner_guard is not row['guards'][2] or roster._owner._operation is not row['guards'][2]
                or roster._owner is not row['bootstrap_owner'] or roster._original_owner is not row['bootstrap_owner']
                or any(not guard.locked() for guard in row['guards'])):
            raise ValueError('original guarded Genesis observation lifetime changed')
        roster._check()
        return roster,row['declarations'],row['limit']

    def bookend(lease):
        verify(lease);records[id(lease)]['binding']['routes']['check']()

    def claim(lease,session):
        bookend(lease);row=records[id(lease)]
        if row['session'] is not None or type(session) is not row['binding']['routes']['session_type']:
            raise ValueError('one original session per Genesis method required')
        row['session']=session
        row['close']=_clone(type(session).close);row['receipt']=_clone(type(session).receipt)
        row['poison']=_clone(type(session)._poison)

    def source_result(lease,result):
        bookend(lease)
        if type(result) is not records[id(lease)]['binding']['routes']['source_type']:
            raise TypeError('original local Genesis exact-source result required')

    def common_result(lease,result,session):
        bookend(lease);row=records[id(lease)]
        if (row['session'] is not session or type(result) is not row['binding']['routes']['common_type']
                or result._session_nonce is not session._nonce):
            raise ValueError('original local Genesis common result required')

    def source_entry(lease,arm,identity):
        bookend(lease)
        value=records[id(lease)]['binding']['routes']['source_entry'](arm,expected_registry_identity=identity)
        source_result(lease,value);return value

    def poison(row,error):
        if row['failure'] is None:row['failure']=repr(error)
        if row['session'] is not None:
            try:row['poison'](row['session'],error)
            except BaseException as failure:error.add_note('Genesis numerical poison: '+repr(failure))

    def operation(host):
        nonlocal binding,used
        _RUNTIME()
        if used:raise ValueError('Genesis adapter requires a fresh dedicated process')
        if (type(host) is not ModuleType or Path(host.__file__).name!='h1_common_owner_genesis_development_v2.py'
                or host.SCHEMA!='h1_common_owner_genesis_development_v2'):
            raise TypeError('original Gen2 module required')
        caller=sys.modules.get(sys._getframe(1).f_globals.get('__name__'))
        _reject_consumers(host,caller)
        used=True;creator=(os.getpid(),get_ident());kind=host.CommonOwnerGenesis
        names=('__init__','_enter','_leave','_correspondence','inspect')
        original={name:vars(kind)[name] for name in names};original_identity=host.implementation_identity
        original_state={name:_state(fn) for name,fn in original.items()}
        host_pin=sha256(Path(host.__file__).read_bytes()).hexdigest();own=implementation_identity()
        histories=WeakKeyDictionary();actives={};routes=None;installed=[];terminal=None;phase='new'
        clones={};patches={};close_handles=kind._close_handles;original_close=kind.close
        original_common=host.common._prepare_locked

        def identity():
            if phase!='active':raise ValueError('active one-shot Genesis adapter required')
            check()
            return sha256(_encode([own,host_pin,original_identity(),routes['manifest'],CONTRACT])).hexdigest()

        def check():
            _RUNTIME()
            if (creator!=(os.getpid(),get_ident()) or phase!='active'
                    or host.CommonOwnerGenesis is not kind or host.implementation_identity is not identity
                    or sha256(Path(host.__file__).read_bytes()).hexdigest()!=host_pin
                    or implementation_identity()!=own or host.common._prepare_locked is not original_common
                    or any(_state(original[name])!=original_state[name] for name in names)
                    or any(vars(kind).get(name) is not value or _state(value)!=patch_states[name]
                        for name,value in patches.items())):
                raise ValueError('fixed Genesis adapter host/dispatch changed')

        def begin(owner,plan):
            check()
            if owner in actives:raise ValueError('Genesis observation is nonreentrant')
            roster=owner._original_roster;guards=(owner._original_operation,roster._original_operation,roster._owner_guard)
            if len({id(g) for g in guards})!=3 or any(not g.locked() for g in guards):
                raise ValueError('three original Genesis/roster/bootstrap guards required')
            roster._check();attached,_,_=roster._replay()
            if len(roster._direct)!=3 or set(attached)!=set(roster._direct):
                raise ValueError('three independent N0 slots required for Genesis observation')
            declarations=[]
            for arm in sorted(roster._direct):
                local=attached[arm]['reference']['local_terminal']['body']
                declarations.append((arm,local['controller_root'],local['controller_binding_sha256'],local['controller_terminal_sha256']))
            lease=object();row=dict(binding=binding,lease=lease,owner=owner,roster=roster,
                bootstrap_owner=roster._owner,guards=guards,creator=creator,declarations=tuple(declarations),
                plan=plan,limit=dict(PLANS)[plan],closed=False,failure=None,session=None,close=None,
                receipt=None,poison=None,validation=None,compatibility=None,calls=0,preparing=False,
                active_implementation=identity())
            records[id(lease)]=row;actives[owner]=row
            try:routes['session_type'](lease);bookend(lease)
            except BaseException as error:
                poison(row,error);finish(owner,error);raise

        def finish(owner,body_error=None):
            row=actives.get(owner)
            if row is None:return
            error=body_error;full=None
            try:
                if body_error is not None:poison(row,body_error)
                else:bookend(row['lease'])
                if row['session'] is not None:
                    row['close'](row['session']);full=row['receipt'](row['session'])
                if body_error is None:
                    if (row['failure'] is not None or row['calls']!=row['limit'] or not full
                            or full.get('complete') is not True):raise ValueError('complete fixed Genesis common call plan required')
                    executions=full['common_executions'];limit=row['limit']
                    totals=tuple(sum(r[k] for r in executions) for k in
                        ('full_numerical_hour_replays','within_prefix_revalidations',
                         'cross_common_numerical_proof_reuses','context_evaluations'))
                    if totals!=(24,24,48*(limit-1),96*limit):raise ValueError('Genesis common execution totals differ')
                    if not all(r['proof_cleared'] for r in full['arm_receipts'].values()):
                        raise ValueError('all Genesis numerical proofs must be cleared')
            except BaseException as failure:
                poison(row,failure)
                if error is None:error=failure
                else:error.add_note('Genesis observation cleanup: '+repr(failure))
                if row['session'] is not None:
                    try:row['close'](row['session']);full=row['receipt'](row['session'])
                    except BaseException as cleanup:error.add_note('Genesis proof cleanup: '+repr(cleanup))
            finally:
                row['closed']=True
                report=dict(schema=SCHEMA,active_implementation=row['active_implementation'],
                    plan=row['plan'],expected_common_calls=row['limit'],common_calls=row['calls'],
                    operation_execution_receipt=full,first_failure=row['failure'],closed=True,
                    complete=error is None,**CONTRACT)
                histories[owner]=histories.get(owner,())+(_encode(report),)
                records.pop(id(row['lease']),None);actives.pop(owner,None)
                for key in ('session','close','receipt','poison','validation','compatibility','binding','lease','owner','roster','guards'):
                    row[key]=None
            if error is not None and body_error is None:raise error

        def prepare(roster):
            row=next((r for r in actives.values() if r['roster'] is roster),None)
            if row is None:return original_common(roster)
            if creator!=(os.getpid(),get_ident()):raise ValueError('Genesis common creator required')
            try:
                caller=sys._getframe(1)
                if (caller.f_globals is not clones['__init__'].__globals__
                        and caller.f_globals is not clones['_correspondence'].__globals__):
                    raise ValueError('original Genesis common call site required')
                if row['preparing']:raise ValueError('Genesis common preparation is nonreentrant')
                row['preparing']=True;bookend(row['lease'])
                value=routes['common_entry'](row['session']);common_result(row['lease'],value,row['session'])
                if row['validation'] is None:
                    row['validation']=value.validation_report_payload;row['compatibility']=value.predecessor_report_payload
                elif (value.validation_report_payload!=row['validation'] or value.predecessor_report_payload!=row['compatibility']):
                    raise ValueError('fresh Genesis common metadata or source correspondence changed')
                row['calls']+=1;bookend(row['lease'])
                return value.manifest,value.source_binding,json.loads(value.predecessor_report_payload)
            except BaseException as error:poison(row,error);raise
            finally:row['preparing']=False

        def enter(owner):
            check();frame=sys._getframe(1);row=actives.get(owner)
            try:original['_enter'](owner)
            except BaseException as error:
                if row is not None and creator==(os.getpid(),get_ident()):poison(row,error)
                raise
            try:
                if frame.f_globals is clones['__init__'].__globals__:
                    if not frame.f_locals['reconcile']:begin(owner,'create' if frame.f_locals['create'] else 'reopen')
                elif frame.f_globals is clones['inspect'].__globals__:begin(owner,'inspect')
            except BaseException:
                original['_leave'](owner);raise

        def leave(owner):
            error=sys.exc_info()[1]
            try:finish(owner,error)
            except BaseException:
                owner.poisoned=True
                try:close_handles(owner)
                finally:owner.closed=True
                raise
            finally:original['_leave'](owner)

        correspondence_callers=tuple(getattr(kind,name).__code__ for name in
            ('__init__','_retain_child','_retain_binder','_initialize','_reconcile','inspect'))
        def correspondence(owner):
            row=actives.get(owner)
            if row is not None:
                frame=sys._getframe(1)
                if frame.f_code not in correspondence_callers or frame.f_locals.get('self') is not owner:
                    error=ValueError('original Genesis correspondence call site required')
                    if creator==(os.getpid(),get_ident()):poison(row,error)
                    raise error
            return clones['_correspondence'](owner)

        proxy=SimpleNamespace(**vars(host.common));proxy._prepare_locked=prepare
        for name in ('__init__','_correspondence','inspect'):
            clones[name]=_clone(original[name],common=proxy,implementation_identity=identity)
        patches.update(clones);patches.update(_enter=enter,_leave=leave,_correspondence=correspondence)
        patch_states={name:_state(fn) for name,fn in patches.items()}

        @contextmanager
        def scope():
            nonlocal binding,routes,phase,terminal
            error=None;cleanup=[]
            try:
                routes=route_kernel.load(sys.modules[__name__])
                for name,value in patches.items():
                    if vars(kind).get(name) is not original[name]:raise ValueError('Genesis installation CAS failed')
                    setattr(kind,name,value);installed.append((kind,name,value,original[name]))
                if host.implementation_identity is not original_identity:raise ValueError('Genesis identity installation CAS failed')
                host.implementation_identity=identity;installed.append((host,'implementation_identity',identity,original_identity))
                phase='active';binding=dict(check=check,kind=kind,routes=routes)
                check();yield
                check()
                if actives:raise ValueError('Genesis method still active at adapter exit')
                if any(not owner.closed for owner in histories):raise ValueError('all Genesis owners must close before adapter exit')
            except BaseException as failure:error=failure;raise
            finally:
                for owner in tuple(actives):
                    try:finish(owner,error or ValueError('unclosed Genesis method'))
                    except BaseException as failure:cleanup.append(failure)
                for owner in tuple(histories):
                    if not owner.closed:
                        try:original_close(owner)
                        except BaseException as failure:cleanup.append(failure)
                restored=[]
                for obj,name,value,before in reversed(installed):
                    if vars(obj).get(name) is value:setattr(obj,name,before);restored.append(name)
                    else:cleanup.append(ValueError('foreign Genesis alias preserved: '+name))
                terminal=_encode(dict(schema=SCHEMA,implementation=own,closed=True,
                    first_failure=None if error is None else repr(error),cleanup_errors=[repr(e) for e in cleanup],
                    restored_aliases=restored,all_aliases_restored=len(restored)==len(installed),
                    all_private_sessions_cleared=not actives and not records,
                    method_receipts=[json.loads(raw) for rows in histories.values() for raw in rows],**CONTRACT))
                histories.clear();binding=None;phase='closed'
                if cleanup:
                    if error is not None:
                        for failure in cleanup:error.add_note('Genesis adapter cleanup: '+repr(failure))
                    else:raise BaseExceptionGroup('Genesis adapter cleanup failed',cleanup)
        def receipt():
            _RUNTIME()
            if creator!=(os.getpid(),get_ident()) or phase!='closed' or terminal is None:
                raise ValueError('closed Genesis adapter creator receipt required')
            return json.loads(terminal)
        return scope(),receipt

    return operation,verify,claim,bookend,source_entry,source_result,common_result


(operation,_VERIFY_LEASE,_CLAIM_SESSION,_BOOKEND,_SOURCE_ENTRY,_SOURCE_RESULT,_COMMON_RESULT)=_build()


def _install_runtime():
    namespace=globals();fixed=tuple((n,v,_state(v)) for n,v in namespace.items() if not n.startswith('__'))
    contract=_encode([PLANS,CONTRACT])
    def check():
        if (namespace.get('_RUNTIME') is not check or _encode([PLANS,CONTRACT])!=contract
                or any(namespace.get(n) is not v or _state(v)!=state for n,v,state in fixed)):
            raise ValueError('definition-time Genesis observation adapter changed')
    return check


_RUNTIME=_install_runtime()
