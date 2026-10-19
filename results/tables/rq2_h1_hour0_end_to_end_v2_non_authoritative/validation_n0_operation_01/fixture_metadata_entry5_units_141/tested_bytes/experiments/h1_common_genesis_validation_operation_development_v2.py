"""One-shot typed-compatible Genesis numerical observation successor.

Install before consumers in a dedicated interpreter. Disk Gen2 stays frozen;
new headers bind this adapter's active identity. Every common return still
rebuilds metadata and all independent N0 contexts. Only numerical proofs span
calls in one constructor or inspection. Exit the process after restoration.
"""
from contextlib import contextmanager
from copy import deepcopy
from hashlib import sha256
from functools import partial
import json
import os
from pathlib import Path
import sys
from threading import get_ident
from types import FunctionType,ModuleType,SimpleNamespace,MappingProxyType,MethodType,MemberDescriptorType,CodeType

from experiments import h1_common_genesis_validation_routes_development_v2 as route_kernel

SCHEMA='h1_common_genesis_validation_operation_development_v2'
PLANS=(('create',15),('reopen',3),('inspect',2),('capture',2))
CONSUMERS=('h1_selector_input_snapshot_development_v2','h1_selector_phase_handoff_development_v6')
EXTERNAL_FINALIZER='_development_genesis_external_finalize_v2'
CONTRACT=dict(source_context_rebuilt_per_common=True,numerical_proof_scope='one_public_Genesis_method',
    report_reused=False,reconcile_supported=False,common_compatibility_payload_scope='predecessor_science_and_metadata_only',
    compatibility_counts_describe_actual_execution=False,per_site_failure_order_preserved=False,
    callback_between_bookends_ABA_covered=False,complete_dynamic_input_closure_proved=False,
    reopen_requires_same_active_adapter=True,post_scope_consumer_reuse_allowed=False,
    process_must_exit_after_receipt=True,formal_result=False,resource_admission=False,
    native_execution_authorized=False,complete_workflow_observed=False)


def _encode(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode('ascii')


def _state(fn):
    if isinstance(fn,(staticmethod,classmethod)):return ('descriptor',_state(fn.__func__))
    if isinstance(fn,property):return ('property',id(fn),*(_state(v) for v in (fn.fget,fn.fset,fn.fdel)))
    return (fn.__code__,repr(fn.__defaults__),repr(fn.__kwdefaults__),
        tuple(id(c.cell_contents) for c in fn.__closure__ or ())) if type(fn) is FunctionType else None


def _clone(fn,**changes):
    namespace=dict(fn.__globals__);namespace.update(changes)
    result=FunctionType(fn.__code__,namespace,fn.__name__,fn.__defaults__,fn.__closure__)
    result.__kwdefaults__=deepcopy(fn.__kwdefaults__)
    return result


def _blueprint(path):
    pending=[compile(path.read_bytes(),str(path),'exec')];result={}
    while pending:
        code=pending.pop();result[code.co_qualname]=code
        pending.extend(value for value in code.co_consts if type(value) is CodeType)
    return result


def _source_functions(module,path):
    """Check source-authored code before recording mutable runtime states."""
    blueprint=_blueprint(path)
    def check(value,name):
        if isinstance(value,(staticmethod,classmethod)):value=value.__func__
        if isinstance(value,property):
            for fn in (value.fget,value.fset,value.fdel):
                if fn is not None:check(fn,fn.__qualname__)
            return
        expected=blueprint.get(name)
        if type(value) is FunctionType:
            expected=expected or blueprint.get(value.__qualname__)
            # Dataclass-generated methods have no authored code in this file.
            if expected is not None and (value.__code__!=expected or value.__globals__ is not vars(module)):
                raise ValueError('original Genesis sequence source function required: '+name)
        elif expected is not None:raise ValueError('original Genesis sequence source function required: '+name)
    for name,code in blueprint.items():
        if '<locals>' in name or not code.co_flags&2:continue
        fields=name.split('.')
        if len(fields)==1:value=vars(module).get(name)
        elif len(fields)==2:
            kind=vars(module).get(fields[0])
            if not isinstance(kind,type) or kind.__module__!=module.__name__:
                raise ValueError('original Genesis sequence source class required: '+fields[0])
            value=vars(kind).get(fields[1])
        else:raise ValueError('unsupported Genesis sequence source nesting')
        check(value,name)
    for name,value in tuple(vars(module).items()):
        if type(value) is FunctionType:check(value,name)
        elif isinstance(value,type) and value.__module__==module.__name__:
            for field,descriptor in vars(value).items():
                if callable(descriptor) or isinstance(descriptor,(property,staticmethod,classmethod)):
                    check(descriptor,value.__name__+'.'+field)


def implementation_identity():
    return sha256(_encode([SCHEMA,sha256(Path(__file__).read_bytes()).hexdigest(),
        route_kernel.implementation_identity(),PLANS,CONTRACT,
        [(name,sha256((Path(__file__).parent/(name+'.py')).read_bytes()).hexdigest())
            for name in CONSUMERS]])).hexdigest()


def _reject_consumers(host,caller):
    """Refuse preloaded project consumers, including descriptor-container pins."""
    root=Path(__file__).resolve().parents[1]
    targets=(host,host.CommonOwnerGenesis,host.implementation_identity,
        host.CommonOwnerGenesis.__init__,host.CommonOwnerGenesis._enter,
        host.CommonOwnerGenesis._leave,host.CommonOwnerGenesis._correspondence,host.CommonOwnerGenesis.inspect)
    visited=set()
    def project_class(value):
        origin=sys.modules.get(value.__module__);path=getattr(origin,'__file__',None)
        if not isinstance(path,str):return False
        try:Path(path).resolve().relative_to(root);return True
        except ValueError:return False
    def contains(value,seen,depth=0):
        if any(value is item for item in targets):return True
        if id(value) in seen:return False
        if depth>32 or len(seen)>500000:raise ValueError('consumer capture inventory exceeds audit bound')
        seen.add(id(value))
        if type(value) in (tuple,list,set,frozenset):return any(contains(v,seen,depth+1) for v in value)
        if type(value) in (dict,MappingProxyType):
            return any(contains(v,seen,depth+1) for pair in value.items() for v in pair)
        if type(value) is FunctionType:
            return any(contains(v,seen,depth+1) for v in (
                value.__defaults__,value.__kwdefaults__,*(c.cell_contents for c in value.__closure__ or ()),
                value.__annotations__,value.__dict__,
                *(value.__globals__[n] for n in value.__code__.co_names if n in value.__globals__)))
        if type(value) is MethodType:return contains(value.__func__,seen,depth+1) or contains(value.__self__,seen,depth+1)
        if isinstance(value,partial):return any(contains(v,seen,depth+1) for v in (value.func,value.args,value.keywords))
        if type(value) is SimpleNamespace:return contains(vars(value),seen,depth+1)
        if isinstance(value,type) and project_class(value):return any(contains(v,seen,depth+1) for v in vars(value).values())
        if isinstance(value,(staticmethod,classmethod)):return contains(value.__func__,seen,depth+1)
        if isinstance(value,property):return any(contains(v,seen,depth+1) for v in (value.fget,value.fset,value.fdel))
        if type(value) is host.CommonOwnerGenesis:return True
        if project_class(type(value)):
            try:fields=object.__getattribute__(value,'__dict__')
            except AttributeError:fields={}
            if contains(fields,seen,depth+1):return True
            for base in type(value).__mro__:
                for descriptor in vars(base).values():
                    if type(descriptor) is not MemberDescriptorType:continue
                    try:field=descriptor.__get__(value,type(value))
                    except AttributeError:continue
                    if contains(field,seen,depth+1):return True
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
            if contains(value,visited):
                raise ValueError('Genesis adapter must precede every project consumer: '+module.__name__)


def _build():
    records={};binding_box=[None];usage=[False]

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
        b['retain_resources'](owner)
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
        _RUNTIME()
        if usage[0]:raise ValueError('Genesis adapter requires a fresh dedicated process')
        if (type(host) is not ModuleType or Path(host.__file__).name!='h1_common_owner_genesis_development_v2.py'
                or host.SCHEMA!='h1_common_owner_genesis_development_v2'):
            raise TypeError('original Gen2 module required')
        caller=sys.modules.get(sys._getframe(1).f_globals.get('__name__'))
        _reject_consumers(host,caller)
        usage[0]=True;creator=(os.getpid(),get_ident());kind=host.CommonOwnerGenesis
        names=('__init__','_enter','_leave','_correspondence','inspect')
        original={name:vars(kind)[name] for name in names};original_identity=host.implementation_identity
        original_state={name:_state(fn) for name,fn in original.items()}
        original_identity_state=_state(original_identity);identity_state=None
        host_pin=sha256(Path(host.__file__).read_bytes()).hexdigest();own=implementation_identity()
        histories={};actives={};external={};external_history=[];external_finalized={};consumers={}
        routes=None;installed=[];terminal=None;phase='new'
        absent=object();finalizer_state=None
        clones={};patches={};close_handles=kind._close_handles
        owner_resources={};owner_guards={};resource_capsules={}
        lease_kind=host.bootstrap.local._Lease
        lease_registry=host.bootstrap.local._REGISTRY;lease_registry_guard=host.bootstrap.local._REGISTRY_LOCK
        resource_closers=tuple((name,_clone(fn)) for name,fn in (
            ('_original_phase',host.phase.DevelopmentOwner.close),
            ('_original_holder',host.phase.tickets.TicketHolder.close),
            ('_original_journal',host.bootstrap._Journal.close)))
        from experiments import h1_owned_selector_sequence_development_v1 as expected_sequence
        sequence_path=Path(__file__).parent/'h1_owned_selector_sequence_development_v1.py'
        sequence_pin=sha256(sequence_path.read_bytes()).hexdigest()
        sequence_spec=expected_sequence.__spec__;sequence_loader=expected_sequence.__loader__
        sequence_name='experiments.h1_owned_selector_sequence_development_v1'
        if (sequence_spec is None or sequence_spec.name!=sequence_name
                or sequence_spec.origin!=str(sequence_path) or sequence_spec.loader is not sequence_loader
                or expected_sequence.__file__!=str(sequence_path)
                or sys.modules.get(sequence_name) is not expected_sequence
                or getattr(sys.modules.get('experiments'),sequence_name.rsplit('.',1)[-1],None) is not expected_sequence):
            raise ValueError('canonical Genesis sequence provenance required')
        _source_functions(expected_sequence,sequence_path)
        original_common=host.common._prepare_locked
        overrides={(id(kind),name) for name in names}|{(id(host),'implementation_identity')}
        pending=[host,expected_sequence];seen=set();dependency_rows=[];protocols=[]
        while pending:
            module=pending.pop()
            if id(module) in seen:continue
            seen.add(id(module))
            for name,value in tuple(vars(module).items()):
                if isinstance(value,ModuleType) and value.__name__.startswith(('experiments.','src.')):
                    dependency_rows.append((module,name,value,None));pending.append(value)
                elif callable(value):
                    dependency_rows.append((module,name,value,_state(value)))
                    origin=sys.modules.get(getattr(value,'__module__',''))
                    if origin is not None and origin.__name__.startswith(('experiments.','src.')):pending.append(origin)
                    if isinstance(value,type) and (value.__module__==host.__name__
                            or value.__module__.startswith(('experiments.','src.'))):
                        dependency_rows.extend((value,n,v,_state(v))
                            for n,v in vars(value).items() if callable(v) or isinstance(v,(property,staticmethod,classmethod)))
                # The canonical lease registry changes when a journal opens.
                # Its original class checks remain in the callable inventory.
                runtime_registry=module is host.bootstrap.local and name=='_REGISTRY'
                if name.isupper() and not runtime_registry and type(value) in (str,int,float,bool,tuple,list,dict,set,frozenset,MappingProxyType,type(None)):
                    protocols.append((module,name,repr(value)))
        dependencies=tuple((obj,name,value,state) for obj,name,value,state in dependency_rows
            if (id(obj),name) not in overrides)
        # These five entries are temporarily replaced only by the genuine
        # nested solver denial; all other imported functions remain fixed.
        witness=sys.modules.get('experiments.h1_historical_hour_witness_development_v1')
        guard=witness.hour.prior.guard
        denial_targets=((type(guard.SolverFactory),'__call__'),(guard.current,'solve_current'),
            (guard.current.native,'run_h1_chain'),(guard.current.native.capture,'solve_once'),
            (guard.current.native.capture.provenance.adapter,'create_solver'))
        denial_keys={(id(obj),name) for obj,name in denial_targets}
        denial_original=tuple((obj,name,getattr(obj,name),_state(getattr(obj,name))) for obj,name in denial_targets)
        denial_check=witness._solver_guard_view
        consumer_sources={name:(Path(__file__).parent/(name+'.py')) for name in CONSUMERS}
        consumer_pins={name:sha256(path.read_bytes()).hexdigest() for name,path in consumer_sources.items()}
        def consumer(frame,index,symbol):
            name=CONSUMERS[index];qualified='experiments.'+name
            module=sys.modules.get(qualified);package=sys.modules.get('experiments')
            if (not isinstance(module,ModuleType) or frame.f_globals is not vars(module)
                    or getattr(package,name,None) is not module or module.common is not host):return None
            path=consumer_sources[name];spec=module.__spec__
            if (module.__file__!=str(path) or spec is None or spec.name!=qualified
                    or spec.origin!=str(path) or module.__loader__ is not spec.loader
                    or sha256(path.read_bytes()).hexdigest()!=consumer_pins[name]):
                raise ValueError('fixed Genesis consumer provenance changed')
            if index==0:
                sequence_name='h1_owned_selector_sequence_development_v1'
                sequence=expected_sequence
                sequence_path=Path(__file__).parent/(sequence_name+'.py')
                if (sys.modules.get('experiments.'+sequence_name) is not sequence
                        or getattr(package,sequence_name,None) is not sequence
                        or sequence.__file__!=str(sequence_path) or sequence.__spec__ is None
                        or sequence.__spec__.origin!=str(sequence_path)
                        or module.sequence is not sequence or module.phase is not host.phase
                        or module.selection is not sequence.selection or module.io is not sequence.io
                        or module.encode is not host.phase.encode):
                    raise ValueError('canonical Genesis Snapshot aliases required')
            wrapped=fn=getattr(module,symbol) if index==0 else getattr(module.Handoff,symbol)
            if index==1 and type(fn) is FunctionType:
                # Handoff's own scope guard wraps the original consume body.
                # The acquisition occurs in that body, below the wrapper.
                bodies=[cell.cell_contents for cell in fn.__closure__ or ()
                    if type(cell.cell_contents) is FunctionType and cell.cell_contents.__name__==symbol
                    and cell.cell_contents.__globals__ is vars(module)]
                if len(bodies)!=1:raise ValueError('original guarded Handoff consumer required')
                fn=bodies[0]
            own_fn=module.implementation_identity
            if type(fn) is not FunctionType or fn.__globals__ is not vars(module):
                raise ValueError('fixed Genesis consumer function required')
            key=(index,symbol)
            if key not in consumers:
                blueprint=_blueprint(path)
                if (fn.__code__!=blueprint.get(fn.__qualname__) or type(own_fn) is not FunctionType
                        or own_fn.__globals__ is not vars(module)
                        or own_fn.__code__!=blueprint.get(own_fn.__qualname__)):
                    raise ValueError('original Genesis consumer code required')
                if index==1:
                    cells=dict(zip(wrapped.__code__.co_freevars,
                        (cell.cell_contents for cell in wrapped.__closure__ or ())))
                    verifier=cells.get('verify')
                    if (wrapped.__globals__ is not vars(module)
                            or wrapped.__code__!=blueprint.get('_anchor.<locals>.guarded.<locals>.entry')
                            or wrapped.__defaults__ is not None or wrapped.__kwdefaults__ is not None
                            or set(cells)!={'check','function','owner_type','verify'}
                            or cells['check'] is not module._CHECK or cells['function'] is not fn
                            or cells['owner_type'] is not module.Handoff
                            or verifier is not module._VERIFY_OWNER or type(verifier) is not FunctionType
                            or verifier.__globals__ is not vars(module)
                            or verifier.__code__!=blueprint.get('_anchor.<locals>.verify')
                            or verifier.__defaults__ is not None or verifier.__kwdefaults__ is not None):
                        raise ValueError('original Genesis guarded consumer wrapper required')
                observations=[]
                for field,value in tuple(vars(module).items()):
                    expected=blueprint.get(field)
                    if type(value) is FunctionType:
                        if expected is not None or value.__module__==qualified:
                            expected=expected or blueprint.get(value.__qualname__)
                            if value.__code__!=expected or value.__globals__ is not vars(module):
                                raise ValueError('original Genesis consumer function graph required: '+field)
                        observations.append((module,field,value,_state(value)))
                    elif isinstance(value,type) and value.__module__==qualified:
                        for attr,descriptor in vars(value).items():
                            if callable(descriptor) or isinstance(descriptor,(property,staticmethod,classmethod)):
                                observations.append((value,attr,descriptor,_state(descriptor)))
                    elif isinstance(value,ModuleType):observations.append((module,field,value,None))
                consumers[key]=(module,spec,module.__loader__,fn,_state(fn),own_fn,_state(own_fn),own_fn(),tuple(observations))
            m,s,loader,entry,state,identity_fn,identity_state,implementation,observations=consumers[key]
            if (module is not m or spec is not s or module.__loader__ is not loader or fn is not entry
                    or _state(fn)!=state or own_fn is not identity_fn or _state(own_fn)!=identity_state
                    or any(vars(obj).get(field) is not value or _state(value)!=before
                        for obj,field,value,before in observations)
                    or own_fn()!=implementation):raise ValueError('fixed active Genesis consumer changed')
            return module,fn
        def retain_resources(owner):
            saved=owner_resources.setdefault(owner,{})
            for name,_ in resource_closers:
                value=getattr(owner,name)
                if name in saved and saved[name] is not value:
                    raise ValueError('original Genesis owned resource changed')
                if value is not None:
                    saved[name]=value
                    lease=getattr(value,'_original_lease' if name=='_original_journal' else '_lease_object')
                    capsules=resource_capsules.setdefault(owner,{})
                    if name in capsules:
                        if (capsules[name]['lease'] is not lease or capsules[name]['key']!=lease.key
                                or capsules[name]['stream'] is not lease.stream):
                            raise ValueError('original Genesis resource lease changed')
                    else:
                        if type(lease) is not lease_kind or lease.stream is None:
                            raise ValueError('original Genesis resource stream required')
                        close=lease.stream.close
                        if type(close) is MethodType:close=partial(_clone(close.__func__),lease.stream)
                        capsules[name]=dict(resource=value,lease=lease,stream=lease.stream,
                            close=close,key=lease.key)
                    if (host.bootstrap.local._REGISTRY is not lease_registry
                            or host.bootstrap.local._REGISTRY_LOCK is not lease_registry_guard):
                        raise ValueError('original Genesis lease registry changed')
            original_guard=owner_guards.setdefault(owner,owner._original_operation)
            if original_guard is not owner._original_operation:raise ValueError('original Genesis close guard changed')
        def captured_close(owner):
            errors=[]
            for name,close in resource_closers:
                resource=owner_resources.get(owner,{}).get(name)
                if resource is not None:
                    try:close(resource)
                    except BaseException as error:errors.append(error)
            for capsule in resource_capsules.get(owner,{}).values():
                lease,stream=capsule['lease'],capsule['stream']
                # A predecessor may set closed=True and discard lease.stream
                # even when stream.close raises. Keep the actual owned handle.
                if not stream.closed:
                    try:
                        capsule['close']()
                        if not stream.closed:raise ValueError('original Genesis stream did not close')
                        # A set key cannot identify its current owner. A fresh
                        # Handoff lease may already have acquired the same key.
                        # Only the typed closer owns normal registry cleanup.
                    except BaseException as error:errors.append(error)
                if stream.closed:
                    if lease.stream is stream or lease.stream is None:
                        lease.stream=None;lease.locked=False;capsule['resource'].closed=True
                    else:errors.append(ValueError('foreign Genesis lease stream preserved'))
            if errors:
                for error in errors[1:]:errors[0].add_note('additional Genesis child cleanup: '+repr(error))
                raise errors[0]

        def identity():
            if phase!='active':raise ValueError('active one-shot Genesis adapter required')
            check()
            return sha256(_encode([own,host_pin,original_identity(),routes['manifest'],CONTRACT])).hexdigest()

        def check():
            _RUNTIME()
            if (creator!=(os.getpid(),get_ident()) or phase!='active'
                    or host.CommonOwnerGenesis is not kind or host.implementation_identity is not identity
                    or getattr(host,EXTERNAL_FINALIZER,None) is not finalize_external
                    or _state(finalize_external)!=finalizer_state
                    or sha256(Path(host.__file__).read_bytes()).hexdigest()!=host_pin
                    or implementation_identity()!=own or host.common._prepare_locked is not original_common
                    or expected_sequence.__spec__ is not sequence_spec or expected_sequence.__loader__ is not sequence_loader
                    or sequence_spec.loader is not sequence_loader
                    or sequence_spec.name!='experiments.h1_owned_selector_sequence_development_v1'
                    or sequence_spec.origin!=str(sequence_path)
                    or sys.modules.get(sequence_spec.name) is not expected_sequence
                    or getattr(sys.modules.get('experiments'),sequence_spec.name.rsplit('.',1)[-1],None) is not expected_sequence
                    or expected_sequence.__file__!=str(sequence_path) or sha256(sequence_path.read_bytes()).hexdigest()!=sequence_pin
                    or _state(original_identity)!=original_identity_state or _state(identity)!=identity_state
                    or any(_state(original[name])!=original_state[name] for name in names)
                    or any(vars(kind).get(name) is not value or _state(value)!=patch_states[name]
                        for name,value in patches.items())
                    or any(vars(obj).get(name) is not value or _state(value)!=state
                        for obj,name,value,state in dependencies if (id(obj),name) not in denial_keys)
                    or any(repr(getattr(obj,name))!=value for obj,name,value in protocols)):
                drift=[getattr(obj,'__name__',type(obj).__name__)+'.'+name
                    for obj,name,value,state in dependencies if (id(obj),name) not in denial_keys
                    and (vars(obj).get(name) is not value or _state(value)!=state)]
                drift.extend(getattr(obj,'__name__',type(obj).__name__)+'.'+name
                    for obj,name,value in protocols if repr(getattr(obj,name))!=value)
                raise ValueError('fixed Genesis adapter host/dispatch changed: '+repr(drift))
            if any(getattr(obj,name) is not value or _state(value)!=state for obj,name,value,state in denial_original):
                denial_check()

        def resources_closed(owner):
            capsules=resource_capsules.get(owner,{})
            return (host.bootstrap.local._REGISTRY is lease_registry
                and host.bootstrap.local._REGISTRY_LOCK is lease_registry_guard
                and len(capsules)==len(owner_resources.get(owner,{}))
                and all(getattr(value,'closed',False) for value in owner_resources.get(owner,{}).values())
                and all(cap['stream'].closed and cap['lease'].stream is None and not cap['lease'].locked
                    and cap['lease'].key==cap['key']
                    for cap in capsules.values()))

        def external_failure(row,error):
            if row['failure'] is None:row['failure']=error

        def complete_external(owner,row,error):
            if error is not None:external_failure(row,error)
            error=row['failure']
            row['released']=not any(guard.locked() for guard in row['guards'])
            if not row['released'] or not owner.closed or not resources_closed(owner):
                external_failure(row,ValueError('original Genesis external cleanup incomplete'))
                return False
            report=dict(consumer=CONSUMERS[1],guards_released=True,
                handoff_committed=error is None,first_failure=None if error is None else repr(error),
                original_resources_closed=True,original_streams_closed=True,complete=error is None,
                formal_result=False)
            external_finalized[owner]=(row['handoff'],len(external_history))
            external_history.append(_encode(report));external.pop(owner,None)
            return True

        def finalize_external(stage,owner,handoff,guards,body_error,cleanup_errors):
            if creator!=(os.getpid(),get_ident()):raise ValueError('Genesis external creator required')
            check();frame=sys._getframe(1)
            if frame.f_code.co_name=='attempt':frame=frame.f_back
            bound=consumer(frame,1,'consume')
            if (bound is None or frame.f_code is not bound[1].__code__
                    or frame.f_locals.get('self') is not handoff or frame.f_locals.get('g') is not owner):
                raise ValueError('original Handoff Genesis finalization required')
            row=external.get(owner)
            if row is None:
                prior=external_finalized.get(owner)
                if (stage=='failed' and prior is not None and prior[0] is handoff
                        and json.loads(external_history[prior[1]])['first_failure'] is not None):return
                raise ValueError('original pending Genesis external acquisition required')
            error=body_error if body_error is not None else (cleanup_errors[0] if cleanup_errors else None)
            if error is not None:external_failure(row,error)
            try:
                if (row['handoff'] is not handoff
                        or tuple(guards)!=row['guards']):
                    raise ValueError('original Handoff Genesis finalization required')
                if any(g.locked() for g in row['guards']):raise ValueError('Genesis external guards still held')
                if stage=='released':
                    row['released']=True
                    if error is not None:complete_external(owner,row,error)
                    return
                if stage=='failed':
                    if error is None:raise ValueError('Genesis external failure cause required')
                    complete_external(owner,row,error);return
                if (stage!='committed' or not row['released'] or handoff._state!='complete'
                        or not owner.closed or error is not None
                        or not resources_closed(owner) or row['failure'] is not None):
                    raise ValueError('completed Handoff and closed Genesis resources required')
                complete_external(owner,row,None)
            except BaseException as failure:
                complete_external(owner,row,error if error is not None else failure)
                if error is not None:error.add_note('Genesis external finalization: '+repr(failure))
                raise

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
            lease=object();row=dict(binding=binding_box[0],lease=lease,owner=owner,roster=roster,
                bootstrap_owner=roster._owner,guards=guards,creator=creator,declarations=tuple(declarations),
                plan=plan,limit=dict(PLANS)[plan],closed=False,failure=None,session=None,close=None,
                receipt=None,poison=None,validation=None,compatibility=None,calls=0,preparing=False,
                active_implementation=identity())
            records[id(lease)]=row;actives[owner]=row
            try:retain_resources(owner);routes['session_type'](lease);bookend(lease)
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
                    validation_checks_complete=error is None,outer_guard_release_complete=False,
                    complete=False,**CONTRACT)
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
                if (not any(caller.f_globals is clones[name].__globals__ and caller.f_code is clones[name].__code__
                            for name in ('__init__','_correspondence'))
                        or caller.f_locals.get('self') is not row['owner']):
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
            internal=next((name for name in ('__init__','inspect')
                if frame.f_globals is clones[name].__globals__ and frame.f_code is clones[name].__code__
                and frame.f_locals.get('self') is owner),None)
            snapshot_bound=consumer(frame,0,'_capture') if internal is None else None
            handoff_bound=consumer(frame,1,'consume') if internal is None else None
            snapshot_call=(snapshot_bound is not None and frame.f_code is snapshot_bound[1].__code__
                and frame.f_locals.get('owner') is owner)
            handoff_call=(handoff_bound is not None and frame.f_code is handoff_bound[1].__code__
                and frame.f_locals.get('g') is owner)
            if internal=='__init__' and frame.f_locals['reconcile']:
                owner.closed=owner.poisoned=True
                raise ValueError('Genesis observation adapter does not support reconcile')
            if internal is None and not snapshot_call and not handoff_call:
                error=ValueError('original fixed Genesis method or consumer acquisition required')
                if row is not None and creator==(os.getpid(),get_ident()):poison(row,error)
                raise error
            if internal!='__init__':
                active_identity=identity()
                if (owner._implementation!=active_identity
                        or json.loads(owner._declaration)['implementation']!=active_identity
                        or json.loads(owner._original_journal._header)['declaration']['implementation']!=active_identity):
                    raise ValueError('Genesis owner must bind the active observation identity')
            try:original['_enter'](owner)
            except BaseException as error:
                if row is not None and creator==(os.getpid(),get_ident()):poison(row,error)
                raise
            acquired_guards=(owner._original_operation,owner._original_roster._original_operation,
                owner._original_roster._owner_guard)
            try:
                if internal=='__init__':begin(owner,'create' if frame.f_locals['create'] else 'reopen')
                elif internal=='inspect':begin(owner,'inspect')
                elif snapshot_call:begin(owner,'capture')
                else:
                    retain_resources(owner)
                    external[owner]=dict(handoff=frame.f_locals['self'],released=False,failure=None,
                        guards=(owner._original_operation,owner._original_roster._original_operation,
                            owner._original_roster._owner_guard))
            except BaseException as error:
                owner.poisoned=True
                try:finish(owner,error)
                except BaseException as failure:error.add_note('Genesis begin proof cleanup: '+repr(failure))
                try:captured_close(owner)
                except BaseException as failure:error.add_note('Genesis begin resource cleanup: '+repr(failure))
                owner.closed=True
                try:original['_leave'](owner)
                except BaseException as failure:error.add_note('Genesis begin guard release: '+repr(failure))
                for held in reversed(acquired_guards):
                    if held.locked():
                        try:held.release()
                        except BaseException as failure:error.add_note('Genesis begin original guard cleanup: '+repr(failure))
                raise

        def leave(owner):
            error=sys.exc_info()[1];failure=None;release_error=None
            row=actives.get(owner)
            guards=row['guards'] if row is not None else ()
            if row is None:
                raise ValueError('original active Genesis method release required')
            try:finish(owner,error)
            except BaseException as caught:failure=caught
            try:original['_leave'](owner)
            except BaseException as caught:release_error=caught
            finally:external.pop(owner,None)
            if failure is not None or release_error is not None:
                owner.poisoned=True
                for caught in (release_error,):
                    if caught is not None:
                        if failure is None:failure=caught
                        else:failure.add_note('Genesis guard release: '+repr(caught))
                try:captured_close(owner)
                except BaseException as cleanup:failure.add_note('Genesis captured handle cleanup: '+repr(cleanup))
                finally:owner.closed=True
                for held in reversed(guards):
                    if held.locked():
                        try:held.release()
                        except BaseException as cleanup:failure.add_note('Genesis original guard cleanup: '+repr(cleanup))
            if owner in histories:
                report=json.loads(histories[owner][-1])
                report['outer_guard_release_complete']=release_error is None and not any(g.locked() for g in guards)
                report['owned_guards_unlocked_after_cleanup']=not any(g.locked() for g in guards)
                if failure is not None and report['first_failure'] is None:report['first_failure']=repr(failure)
                report['complete']=report['validation_checks_complete'] and report['outer_guard_release_complete'] and failure is None
                histories[owner]=histories[owner][:-1]+(_encode(report),)
            if failure is not None:
                if error is not None:error.add_note('Genesis method cleanup: '+repr(failure))
                else:raise failure

        correspondence_callers=tuple(getattr(kind,name).__code__ for name in
            ('__init__','_retain_child','_retain_binder','_initialize','_reconcile','inspect'))
        def correspondence(owner):
            row=actives.get(owner)
            if row is not None:
                frame=sys._getframe(1)
                if frame.f_code not in correspondence_callers or frame.f_locals.get('self') is not owner:
                    # Snapshot capture has two exact owner-view observations.
                    capture_bound=consumer(frame,0,'_owner_view') if row['plan']=='capture' else None
                    capture_view=(capture_bound is not None and frame.f_locals.get('owner') is owner
                        and frame.f_code is capture_bound[1].__code__)
                    if capture_view:return clones['_correspondence'](owner)
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
            nonlocal routes,phase,terminal,identity_state,finalizer_state
            error=None;cleanup=[]
            try:
                routes=route_kernel.load(sys.modules[__name__])
                for name,value in patches.items():
                    if vars(kind).get(name) is not original[name]:raise ValueError('Genesis installation CAS failed')
                    setattr(kind,name,value);installed.append((kind,name,value,original[name],_state(value),original_state[name]))
                if host.implementation_identity is not original_identity:raise ValueError('Genesis identity installation CAS failed')
                host.implementation_identity=identity
                identity_install_index=len(installed)
                installed.append((host,'implementation_identity',identity,original_identity,_state(identity),original_identity_state))
                previous_hook=vars(host).get(EXTERNAL_FINALIZER,absent)
                if previous_hook is not absent:raise ValueError('fresh Genesis external hook required')
                setattr(host,EXTERNAL_FINALIZER,finalize_external)
                phase='active';identity_state=_state(identity);finalizer_state=_state(finalize_external)
                installed[identity_install_index]=(host,'implementation_identity',identity,original_identity,identity_state,original_identity_state)
                installed.append((host,EXTERNAL_FINALIZER,finalize_external,absent,finalizer_state,None))
                binding_box[0]=dict(check=check,kind=kind,routes=routes,retain_resources=retain_resources)
                check();yield
                check()
                if actives or any(row['failure'] is None for row in external.values()):
                    raise ValueError('Genesis method or external acquisition still active at adapter exit')
                if any(not owner.closed and owner not in external for owner in histories):
                    raise ValueError('all Genesis owners must close before adapter exit')
            except BaseException as failure:error=failure;raise
            finally:
                for owner,row in tuple(external.items()):
                    failure=row['failure']
                    if failure is None:failure=error if error is not None else ValueError('unfinished Genesis external acquisition')
                    try:captured_close(owner)
                    except BaseException as caught:cleanup.append(caught)
                    owner.poisoned=True
                    if resources_closed(owner):owner.closed=True
                    for held in reversed(row['guards']):
                        if held.locked():
                            try:held.release()
                            except BaseException as caught:cleanup.append(caught)
                    row['released']=not any(g.locked() for g in row['guards'])
                    if not complete_external(owner,row,failure):
                        cleanup.append(ValueError('original Genesis external cleanup remains incomplete'))
                for owner in tuple(actives):
                    guards=actives[owner]['guards']
                    try:finish(owner,error if error is not None else ValueError('unclosed Genesis method'))
                    except BaseException as failure:cleanup.append(failure)
                    try:captured_close(owner);owner.closed=owner.poisoned=True
                    except BaseException as failure:cleanup.append(failure)
                    for held in reversed(guards):
                        if held.locked():
                            try:held.release()
                            except BaseException as failure:cleanup.append(failure)
                for owner in tuple(histories):
                    if not owner.closed or not resources_closed(owner):
                        held=owner_guards[owner]
                        if not held.acquire(False):cleanup.append(ValueError('Genesis close guard still active'));continue
                        try:captured_close(owner);owner.closed=True
                        except BaseException as failure:cleanup.append(failure)
                        finally:held.release()
                restored=[]
                for obj,name,value,before,current_state,before_state in reversed(installed):
                    if (vars(obj).get(name) is value and _state(value)==current_state and _state(before)==before_state):
                        if before is absent:delattr(obj,name)
                        else:setattr(obj,name,before)
                        restored.append(name)
                    else:cleanup.append(ValueError('foreign Genesis alias preserved: '+name))
                route_cleanup=None
                if routes is not None:
                    try:
                        route_cleanup=routes['unload']()
                        cleanup.extend(ValueError(value) for value in route_cleanup['errors'])
                    except BaseException as caught:cleanup.append(caught)
                methods=[json.loads(raw) for rows in histories.values() for raw in rows]
                terminal=_encode(dict(schema=SCHEMA,implementation=own,closed=True,
                    first_failure=None if error is None else repr(error),cleanup_errors=[repr(e) for e in cleanup],
                    restored_aliases=restored,all_host_aliases_restored=len(restored)==len(installed),
                    route_cleanup=route_cleanup,
                    all_aliases_restored=len(restored)==len(installed) and
                        (route_cleanup is None or route_cleanup['all_route_aliases_removed']),
                    all_private_sessions_cleared=not actives and not records and not external
                        and all(resources_closed(owner) for owner in owner_resources)
                        and all(not guard.locked() for guard in owner_guards.values()),
                    observed_method_window_count=len(methods),
                    all_observed_method_windows_successful=bool(methods) and all(row['complete'] for row in methods),
                    observed_external_window_count=len(external_history),
                    external_receipts=[json.loads(raw) for raw in external_history],
                    all_observed_external_windows_successful=bool(external_history) and
                        all(json.loads(raw)['complete'] for raw in external_history),
                    method_receipts=methods,**CONTRACT))
                histories.clear();owner_resources.clear();owner_guards.clear();resource_capsules.clear()
                external_finalized.clear();consumers.clear();binding_box[0]=None;phase='closed'
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
    kernel_fixed=tuple((name,getattr(route_kernel,name,None),_state(getattr(route_kernel,name,None)))
        for name in ('load','implementation_identity','ROUTES','_RUNTIME','__spec__','__loader__','__file__'))
    kernel_routes=repr(getattr(route_kernel,'ROUTES',None))
    def check():
        if (namespace.get('_RUNTIME') is not check or _encode([PLANS,CONTRACT])!=contract
                or any(namespace.get(n) is not v or _state(v)!=state for n,v,state in fixed)):
            raise ValueError('definition-time Genesis observation adapter changed')
        if (repr(getattr(route_kernel,'ROUTES',None))!=kernel_routes
                or any(getattr(route_kernel,n,None) is not v or _state(v)!=state for n,v,state in kernel_fixed)):
            raise ValueError('definition-time Genesis route kernel changed')
    return check


_RUNTIME=_install_runtime()
