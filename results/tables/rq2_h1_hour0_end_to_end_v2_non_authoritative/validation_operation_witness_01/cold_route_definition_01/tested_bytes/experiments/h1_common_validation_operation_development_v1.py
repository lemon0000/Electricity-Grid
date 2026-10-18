"""Read-only common-validation scope over an original registered Handoff.

This diagnostic borrows original guards, never consumes a handoff or creates
a journal. Only its own entry can issue a lease or acquire the operation token.
"""
import os
import sys
from hashlib import sha256
import importlib.util
import json
from pathlib import Path
from threading import get_ident
import types

from experiments import h1_selector_phase_handoff_development_v2 as handoff

SCHEMA = 'h1_common_validation_operation_development_v1'
_ROUTE_NAMES = ('experiments.h1_operation_historical_witness_development_v2',
    'experiments.h1_phase_exact_source_current_development_v3',
    'experiments.h1_group_n0_common_input_binding_development_v3')
_PINNED_ROUTES = (
    (_ROUTE_NAMES[0], 'h1_operation_historical_witness_development_v2.py',
        '499a7f7b7b0a1b004f7d59852e0773b4bfe32451f77dc4f046956389f3767a33'),
    (_ROUTE_NAMES[1], 'h1_phase_exact_source_current_development_v3.py',
        '0ac170f443977c51b94c336ebd30251745fc503a5d3d226a636affda76e19006'),
    (_ROUTE_NAMES[2], 'h1_group_n0_common_input_binding_development_v3.py',
        'f1c97a388199e9424e092142780b1e53b0c6f257cc44295faa0875727110ae6e'))


class _Lease:
    def __new__(cls, *args, **kwargs):
        raise TypeError('original common validation entry must issue the lease')

    def _no_copy(self, *args):
        raise TypeError('live common validation lease cannot be copied')
    __copy__ = __deepcopy__ = __reduce_ex__ = _no_copy


def _build():
    # The token and lease registry are closure state. Neither caller tokens nor
    # caller-supplied validation callbacks are accepted by any issuing entry.
    records = {};operations={}
    lease_type = _Lease
    api = handoff
    owner_type = api.Handoff
    begin, end = api._BEGIN, api._END
    owner_check, original_check = api._VERIFY_OWNER, api._CHECK
    record_bundle, record_predecessor = api._RECORD_BUNDLE, api._RECORD_PREDECESSOR
    resources, bundle_enter = api._common_resources, api._Bundle.enter
    common_enter = api.common.CommonOwnerGenesis._enter
    fixed = ((api, '_BEGIN', begin), (api, '_END', end),
        (api, '_VERIFY_OWNER', owner_check), (api, '_CHECK', original_check),
        (api, '_RECORD_BUNDLE', record_bundle), (api, '_RECORD_PREDECESSOR', record_predecessor),
        (api, '_common_resources', resources), (api._Bundle, 'enter', bundle_enter),
        (api.common.CommonOwnerGenesis, '_enter', common_enter))
    codes = tuple((fn, fn.__code__, repr(fn.__defaults__), repr(fn.__kwdefaults__))
        for _, _, fn in fixed)
    bridge_module=sys.modules[__name__]
    bridge_source=(str(Path(__file__).resolve()),sha256(Path(__file__).read_bytes()).hexdigest())
    route_names=_ROUTE_NAMES
    source_root=Path(bridge_source[0]).parent
    sources=tuple(sorted(((__name__,*bridge_source),*(
        (name,str((source_root/filename).resolve(strict=True)),pin) for name,filename,pin in _PINNED_ROUTES))))
    manifest_payload=json.dumps(sources,ensure_ascii=True,separators=(',',':')).encode('ascii')
    manifest_pin=sha256(manifest_payload).hexdigest()
    compile_source,execute_source=compile,exec
    make_spec,new_module=importlib.util.spec_from_file_location,importlib.util.module_from_spec

    def snapshot(fn):
        return types.FunctionType(fn.__code__,fn.__globals__,fn.__name__,fn.__defaults__,fn.__closure__)

    def route_state(value):
        fn=value.__func__ if isinstance(value,(staticmethod,classmethod)) else value
        return (fn.__code__,repr(fn.__defaults__),repr(fn.__kwdefaults__)) if type(fn) is types.FunctionType else None

    def load_routes(sources):
        package=sys.modules['experiments']
        if any(name in sys.modules or hasattr(package,name.rsplit('.',1)[1]) for name in route_names):
            raise ValueError('witness/source/common routes must not be preloaded')
        raw={}
        for name,path,pin in sources:
            value=Path(path).read_bytes()
            if sha256(value).hexdigest()!=pin:raise ValueError('declared route source bytes changed')
            raw[name]=(path,value)
        modules={__name__:bridge_module}
        created=[]
        try:
            for name in route_names:
                path,value=raw[name]
                spec=make_spec(name,path)
                module=new_module(spec);created.append((name,module))
                sys.modules[name]=module;setattr(package,name.rsplit('.',1)[1],module)
                execute_source(compile_source(value,path,'exec'),vars(module))
                modules[name]=module
            w,s,c=(modules[name] for name in route_names)
            if w.operation_bridge is not bridge_module or s.witness is not w or c.witness is not w or c.source is not s:
                raise ValueError('compiled common route module edges differ')
            entries=((w,'GroupWitnessSession'),(w,'ArmWitness'),
                (s,'prepare_common_bundle'),(s,'CommonSourceBundle'),(c,'prepare'),(c,'PreparedCommonInput'))
            observations=[]
            for owner,name in entries:
                value=vars(owner)[name];observations.append((owner,name,value,route_state(value)))
                if isinstance(value,type):
                    for field,descriptor in vars(value).items():
                        if callable(descriptor) or isinstance(descriptor,(property,staticmethod,classmethod)):
                            observations.append((value,field,descriptor,route_state(descriptor)))
            routes=dict(modules=modules,sources=sources,observations=tuple(observations),
                specs=tuple((m,m.__spec__,m.__loader__) for m in modules.values()),
                source_entry=s.prepare_common_bundle,source_type=s.CommonSourceBundle,
                common_entry=c.prepare,common_type=c.PreparedCommonInput,session_type=w.GroupWitnessSession)
            check_routes(routes)
            # Successful routes remain until this isolated interpreter exits.
            return routes
        except BaseException as error:
            for name,module in reversed(created):
                field=name.rsplit('.',1)[1]
                try:
                    if vars(package).get(field) is module:delattr(package,field)
                except BaseException as failure:error.add_note('package route rollback: '+repr(failure))
                try:
                    if sys.modules.get(name) is module:del sys.modules[name]
                except BaseException as failure:error.add_note('module route rollback: '+repr(failure))
            raise

    def check_routes(routes):
        package=sys.modules['experiments']
        for name,path,pin in routes['sources']:
            module=routes['modules'][name]
            if (sys.modules.get(name) is not module or vars(package).get(name.rsplit('.',1)[1]) is not module
                    or module.__name__!=name or module.__file__!=path or sha256(Path(path).read_bytes()).hexdigest()!=pin):
                raise ValueError('fixed common validation import route changed')
        if (any(m.__spec__ is not spec or m.__loader__ is not loader for m,spec,loader in routes['specs'])
                or any(vars(owner).get(name) is not value or route_state(value)!=state
                    for owner,name,value,state in routes['observations'])):
            raise ValueError('fixed common validation entry/code route changed')

    def bindings():
        _RUNTIME()
        if (any(getattr(obj, name) is not fn for obj, name, fn in fixed)
                or any(fn.__code__ is not code or repr(fn.__defaults__) != defaults
                    or repr(fn.__kwdefaults__) != keywords for fn, code, defaults, keywords in codes)):
            raise ValueError('original common validation entry dispatch changed')
        original_check()

    def verify(lease):
        if type(lease) is not lease_type:
            raise TypeError('original common validation lease required')
        row = records.get(id(lease))
        if row is None or row['lease'] is not lease or row['closed']:
            raise ValueError('common validation lease is absent or closed')
        h = row['handoff']
        if ((os.getpid(), get_ident()) != row['creator'] or h._state != 'running'
                or h._guard is not row['guard'] or not row['guard'].locked()
                or h._genesis is not row['genesis'] or h._bundle is not row['bundle']
                or any(not guard.locked() for guard in row['common_guards'])
                or any(getattr(obj, name) is not value for obj, name, value in row['aliases'])):
            raise ValueError('original common validation operation lifetime changed')
        owner_check(h)
        return row['roster'], row['declarations'], row['max_common_calls']

    def claim(lease, session):
        verify(lease)
        row = records[id(lease)]
        if row['session'] is not None:
            raise ValueError('one historical witness session per live operation required')
        session_type=row['routes']['session_type']
        if type(session) is not session_type:
            raise TypeError('exact grouped historical witness session required')
        row['session'] = session
        row['session_close'] = snapshot(session_type.close)
        row['session_receipt'] = snapshot(session_type.receipt)
        row['session_poison'] = snapshot(session_type._poison)

    def bookend(lease):
        bindings()
        verify(lease)
        check_routes(records[id(lease)]['routes'])

    def source_result(lease,result):
        bookend(lease)
        if type(result) is not records[id(lease)]['routes']['source_type']:
            raise TypeError('exact pinned common source result required')

    def common_result(lease,result,session):
        bookend(lease);row=records[id(lease)]
        if (row['session'] is not session or type(result) is not row['routes']['common_type']
                or result._session_nonce is not session._nonce):
            raise ValueError('exact pinned common result from original session required')

    def source_entry(lease,arm,registry_identity):
        bookend(lease);routes=records[id(lease)]['routes']
        result=routes['source_entry'](arm,expected_registry_identity=registry_identity)
        source_result(lease,result)
        return result

    class GuardedCommonOperation:
        def __init__(self, owner, *, max_common_calls=2):
            bindings()
            if type(owner) is not owner_type or type(max_common_calls) is not int or max_common_calls != 2:
                raise ValueError('original Handoff and explicit two-common diagnostic required')
            owner._check()
            if owner._state != 'new':
                raise ValueError('new single-attempt Handoff required')
            self._owner = owner
            self._original_owner = owner
            self._creator = os.getpid(), get_ident()
            self._limit = max_common_calls
            self._route_sources=sources
            self._lease = self._session = None
            self._entered = self._closed = False
            operations[id(self)]=dict(owner=self,handoff=owner,creator=self._creator,
                sources=self._route_sources,stage='new',active=None)

        def __enter__(self):
            bindings()
            record=operations.get(id(self))
            if record is None or record['owner'] is not self:
                raise ValueError('original common validation entry required')
            h=record['handoff']
            if (record['stage']!='new' or self._entered or self._closed
                    or record['creator'] != (os.getpid(), get_ident())
                    or self._owner is not h or h is not self._original_owner or self._limit != 2
                    or self._route_sources is not record['sources']):
                raise ValueError('single-use creating-thread common validation entry required')
            guard = h._guard
            if not guard.acquire(False):
                raise ValueError('Handoff operation already active')
            self._entered = True
            record['stage']='running'
            bundle = h._bundle
            token = None
            parent_guards = parent_marks = common_guards = ()
            try:
                h._check()
                if h._state != 'new':
                    raise ValueError('new single-attempt Handoff required')
                token = begin(h)
                h._state = 'running'
                bundle_enter(h._bundle)
                parent_guards, parent_marks = tuple(h._bundle.held), tuple(h._bundle.marked)
                record_bundle(h, token)
                proposed_guards, aliases = resources(h._genesis)
                common_enter(h._genesis)
                common_guards = proposed_guards
                record_predecessor(h, token, common_guards, aliases)
                roster = h._genesis._original_roster
                attached, _, _ = roster._replay()
                if len(roster._direct) != 3 or set(attached) != set(roster._direct):
                    raise ValueError('three independently authenticated N0 siblings required')
                declarations = []
                for arm in sorted(roster._direct):
                    local = attached[arm]['reference']['local_terminal']['body']
                    declarations.append((arm, local['controller_root'],
                        local['controller_binding_sha256'], local['controller_terminal_sha256']))
                routes=load_routes(record['sources'])
                lease = object.__new__(lease_type)
                row = dict(lease=lease, handoff=h, creator=self._creator, token=token, guard=guard,
                    genesis=h._genesis, bundle=h._bundle, roster=roster, aliases=aliases,
                    common_guards=common_guards, parent_guards=parent_guards, parent_marks=parent_marks,
                    declarations=tuple(declarations), max_common_calls=self._limit,
                    closed=False, session=None, session_close=None,session_receipt=None,session_poison=None,routes=routes)
                records[id(lease)] = row
                record['active']=row
                self._lease = lease
                self._session = routes['session_type'](lease)
                bookend(lease)
                return self
            except BaseException as error:
                cleanup(self, h, bundle, token, guard, common_guards, parent_guards, parent_marks, error)
                raise

        def prepare_common(self):
            try:
                record=operations[id(self)];row=record['active']
                if (row is None or self._lease is not row['lease'] or self._session is not row['session']
                        or self._owner is not row['handoff']):
                    raise ValueError('original validation operation aliases changed')
                bookend(row['lease'])
                before=row['session']._common_calls
                result=row['routes']['common_entry'](row['session'])
                common_result(row['lease'],result,row['session'])
                if row['session']._common_calls!=before+1:
                    raise ValueError('one complete original common call required')
                return result
            except BaseException as error:
                record=operations.get(id(self));row=None if record is None else record['active']
                if row is not None and row['session'] is not None:
                    try:row['session_poison'](row['session'],error)
                    except BaseException as failure:error.add_note('common validation poison: '+repr(failure))
                raise

        def receipt(self):
            record=operations.get(id(self));row=None if record is None else record['active']
            if row is None or row['session'] is None:
                return dict(schema=SCHEMA, closed=self._closed, complete=False)
            receipt=row['session_receipt'](row['session'])
            return dict(receipt,validation_route_manifest_sha256=manifest_pin,
                validation_route_sources=[dict(module=n,path=p,sha256=h) for n,p,h in sources])

        def _release(self, owner, bundle, token, guard, common_guards, parent_guards, parent_marks, body_error):
            errors = []
            def attempt(function,*arguments):
                try:function(*arguments)
                except BaseException as error:errors.append(error)
            record=operations[id(self)];row=record['active']
            if row is not None:
                if row['session'] is not None:
                    attempt(row['session_close'],row['session'])
                row['closed'] = True
            for held in reversed(common_guards):
                attempt(held.release)
            for marked_parent in reversed(parent_marks):
                attempt(setattr,marked_parent,'_reference_held',False)
            for held in reversed(parent_guards):
                attempt(held.release)
            attempt(setattr,bundle,'held',[])
            attempt(setattr,bundle,'marked',[])
            if token is not None:
                attempt(end,owner,token)
            attempt(setattr,owner,'_state','failed')  # No consume credential.
            attempt(guard.release)
            attempt(setattr,self,'_closed',True)
            record['stage']='closed'
            if row is not None and row['session'] is not None and (body_error is not None or errors):
                attempt(row['session_poison'],row['session'],body_error or errors[0])
            if errors:
                if body_error is not None:
                    for error in errors:
                        body_error.add_note('common validation cleanup: ' + repr(error))
                else:
                    for error in errors[1:]:
                        errors[0].add_note('additional cleanup failure: ' + repr(error))
                    raise errors[0]

        def __exit__(self, kind, value, traceback):
            record=operations.get(id(self));row=None if record is None else record['active']
            if row is None:
                raise ValueError('original common validation cleanup record required')
            cleanup(self, row['handoff'], row['bundle'], row['token'], row['guard'], row['common_guards'],
                row['parent_guards'], row['parent_marks'], value)
            if value is None:
                try:
                    receipt=row['session_receipt'](row['session'])
                    if receipt.get('complete') is not True:
                        raise ValueError('two complete common calls and closed public arm envelopes required')
                except BaseException as error:
                    try:row['session_poison'](row['session'],error)
                    except BaseException as failure:error.add_note('common validation poison: '+repr(failure))
                    raise

        def _no_copy(self, *args):
            raise TypeError('live common validation operation cannot be copied')
        __copy__ = __deepcopy__ = __reduce_ex__ = _no_copy

    cleanup=GuardedCommonOperation._release
    return GuardedCommonOperation, verify, claim, bookend,source_entry,source_result,common_result


(GuardedCommonOperation,_VERIFY_LEASE,_CLAIM_SESSION,_BOOKEND,
    _SOURCE_ENTRY,_SOURCE_RESULT,_COMMON_RESULT) = _build()


def _install_runtime():
    module=sys.modules[__name__];expected=[]
    for owner in (module,GuardedCommonOperation,_Lease):
        for name,value in tuple(vars(owner).items()):
            if ((owner is module and (not name.startswith('__') or name in
                    ('__name__','__file__','__package__','__spec__','__loader__')) and name!='_RUNTIME')
                    or isinstance(value,(types.FunctionType,types.ModuleType,type,staticmethod,classmethod,property))):
                state=(value.__code__,repr(value.__defaults__),repr(value.__kwdefaults__)) if type(value) is types.FunctionType else None
                expected.append((owner,name,value,state))
    def check():
        if (module._RUNTIME is not check or any(vars(owner).get(name) is not value
                or state is not None and (value.__code__,repr(value.__defaults__),repr(value.__kwdefaults__))!=state
                for owner,name,value,state in expected)):
            raise ValueError('definition-time common validation bridge dispatch changed')
    return check


_RUNTIME=_install_runtime()
