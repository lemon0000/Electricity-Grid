"""One synchronous, bookended source window for post-negative Parent checks.

A development successor of four public validate_completion calls. It preserves
Parent/transport/reference validation bodies and changes source observation times.
Only plain diagnostic JSON leaves the call; no completion or execution authority.
"""
from contextlib import contextmanager
from copy import deepcopy
import dis
from hashlib import sha256
import json
import os
from pathlib import Path
from threading import Lock, get_ident
from types import FunctionType, SimpleNamespace

from experiments import h1_selector_parent_controller_development_v4 as parent
from experiments import h1_selector_parent_validation_operation_development_v4 as kernel

from experiments import h1_reference_validation_routes_development_v1 as reference_routes

SCHEMA = 'h1_selector_post_negative_validation_development_v3'
EXPECTED_WINDOWS = dict(bundle=1)
_source_signature = kernel._source_signature
_source_types = kernel._source_types
_capture_source_guard = kernel._capture_source_guard


def _encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=True, allow_nan=False).encode('ascii')


def implementation_identity():
    return sha256(_encode([SCHEMA, sha256(Path(__file__).read_bytes()).hexdigest(),
        kernel.implementation_identity(), parent.implementation_identity(),
        EXPECTED_WINDOWS,reference_routes.implementation_identity()])).hexdigest()


def _build():
    active = None
    registry_lock = Lock()
    copy = deepcopy
    pid, thread = os.getpid, get_ident

    def check(row, owner=None, *, borrowed=False):
        _RUNTIME()
        if (active is not row or row['creator'] != (pid(), thread())
                or row['failure'] is not None):
            raise ValueError('original post-negative operation lifetime required')
        if not borrowed:parent._CHECK()
        for index, (obj, receipt, raw, issued, guard) in enumerate(row['parents']):
            if (type(obj) is not parent.Parent or type(receipt) is not parent.ParentCompletion
                    or obj._raw is not raw or obj._issued is not receipt
                    or obj._issued_bytes != issued or parent._completion_bytes(receipt) != issued
                    or obj._guard is not guard or not guard.locked()
                    or (obj._pid, obj._thread) != row['creator']
                    or obj._state != 'complete'):
                raise ValueError('exact original complete Parent, receipt, raw and guard required')
            declaration=json.loads(raw)['declaration']
            role='reference' if index==0 else 'actual'
            lane=None if index==0 else row['lanes'][index-1]
            if (receipt.role != role or declaration['role'] != role
                    or declaration['lane_id'] != lane
                    or declaration['source_binding'] != row['source_binding']
                    or obj._reference_held is not (index != 0)
                    or obj._reference_owner is not (None if index==0 else row['parents'][0][0])
                    or obj._reference_completion is not (None if index==0 else row['parents'][0][1])):
                raise ValueError('original Parent role, lane, source binding or reference changed')
        guards=tuple(part[4] for part in row['parents'][1:])+(row['parents'][0][4],)
        marks=tuple(part[0] for part in row['parents'][1:])
        if (len(row['guards'])!=4 or any(a is not b for a,b in zip(row['guards'],guards))
                or len(row['marks'])!=3 or any(a is not b for a,b in zip(row['marks'],marks))):
            raise ValueError('exact post-negative guard and mark inventory required')
        if owner is not None and (not row['frames'] or row['frames'][-1]['owner'] is not owner):
            raise ValueError('original current Parent validation site required')
        if row['routes'] is not None:row['routes']['check']()
        return parent

    def state(value):
        return (value.__code__, repr(value.__defaults__), repr(value.__kwdefaults__)) if type(value) is FunctionType else None

    def clone(function, **changes):
        namespace = dict(function.__globals__)
        namespace.update(changes)
        result = FunctionType(function.__code__, namespace, function.__name__, function.__defaults__, function.__closure__)
        result.__kwdefaults__ = copy(function.__kwdefaults__)
        return result

    def routes(row,parent):
        return reference_routes._make_routes(row,parent,check,parent._WINDOWS.raw_source,parent._WINDOWS.raw_inspect,
            family='post_negative',enable_reference=row['window'] is not None,
            capture_source_guard=_capture_source_guard,
            scope_code=source_window.__wrapped__.__code__,scope_globals=source_window.__wrapped__.__globals__)

    @contextmanager
    def source_window(row,kind,owner=None):
        parent=check(row)
        if row['window'] is not None or row['frames'] or kind not in EXPECTED_WINDOWS:
            raise ValueError('nonreentrant original Parent source window required')
        if row['window_counts'][kind]>=EXPECTED_WINDOWS[kind]:
            raise ValueError('Parent source window count exceeded')
        for admitted,issued,_,_,_ in row['parents']:
            admitted._check()
            if admitted._state!='complete' or admitted._issued is not issued:
                raise ValueError('original complete Parent admission required before source work')
        old=row['source_binding']
        arguments=dict(expected_binding_sha256=old['binding_sha256'],expected_terminal_sha256=old['genesis_terminal_sha256'],
            completed_hours=1,expected_registry_identity=old['registry_identity'])
        window=dict(kind=kind,root=old['root'],arguments=arguments,value=None,signature=None,types=None,
            active=False,in_full_prepare=True,requests=0)
        prior_routes=row['routes'];reference=None;entry=None;primary=None;cleanup_failure=None
        row['window']=window
        try:
            row['routes']=routes(row,parent)
            reference=row['routes']['reference']
            if reference is None:raise ValueError('shared reference window must be active')
            before=row['routes']['materialize'](window['root'],arguments)
            row['source_prepares']+=1
            signature=_source_signature(before);types=_source_types(before)
            window.update(value=before,signature=signature,types=types,active=True,in_full_prepare=False)
            check(row)
            yield
            check(row)
            if row['frames'] or _source_signature(before)!=signature or _source_types(before)!=types:
                raise ValueError('retained source fields or frames changed before window tail')
            window['in_full_prepare']=True
            after=row['routes']['materialize'](window['root'],arguments)
            row['source_prepares']+=1
            if _source_signature(after)!=signature or _source_types(after)!=types:
                raise ValueError('source fields changed during synchronous Parent validation')
            check(row)
            requests=window['requests']
            if requests!=dict(bundle=160,records_bundle=328)[kind]:
                raise ValueError('complete nested source request inventory required')
            reference_receipt=reference['finish']()
            check(row)
            route=copy(row['routes']['declaration'])
            entry=dict(kind=kind,source_binding=copy(old),parent_root=None if owner is None else str(owner.root),
                complete_source_signature_sha256=signature,nested_source_requests=requests,original_source_prepares=2,
                full_numerical_hour_replays=8,fresh_context_observations=32,fresh_at_return_only=True,
                closed=True,window_cache_entry_cleared=False,reference_window=reference_receipt,
                reference_route=route,reference_route_sha256=sha256(_encode(route)).hexdigest())
        except BaseException as error:
            primary=error
            if row and row['failure'] is None:row['failure']=repr(error)
            raise
        finally:
            if reference is not None:
                try:
                    reference['close']()
                    if reference['generator'].gi_frame is not None:
                        raise ValueError('shared reference cache clearance incomplete')
                except BaseException as error:
                    cleanup_failure=error
            window.clear()
            if row.get('window') is window:
                row['window']=None;row['routes']=prior_routes
            if entry is not None and primary is None and cleanup_failure is None:
                entry['window_cache_entry_cleared']=True
                entry['reference_window']['cache_cleared']=True
                row['windows'].append(entry);row['window_counts'][kind]+=1
            if cleanup_failure is not None:
                if row and row['failure'] is None:row['failure']=repr(cleanup_failure)
                if primary is not None:primary.add_note('shared reference cleanup: '+repr(cleanup_failure))
                else:raise cleanup_failure

    def validate(row, owner, receipt):
        parent = check(row)
        if not any((owner is obj and receipt is issued for obj, issued, *_ in row['parents'])):
            raise TypeError('original Parent and issued completion pair required')
        frame = dict(owner=owner, kind='validating', completed_sources=0)
        row['frames'].append(frame)
        try:
            owner._check()
            if owner._state != 'complete' or receipt is not owner._issued or parent._completion_bytes(receipt) != owner._issued_bytes:
                raise ValueError('exact original issued parent completion required')
            owner._check()
            row['routes']['source'](owner)
            reference(row, owner)
            if owner._outcome is None:
                raise ValueError('completed owned outcome required')
            outcome = json.loads(owner._outcome)
            prior = outcome['inspection']
            data = prior['data']
            fresh = row['routes']['inspect'](owner, dict(pid=outcome['pid'], creation_filetime=outcome['creation_filetime']), {name: data['pins'][name] for name in parent.inspection.OUTPUT_FILES})
            expected = copy(prior)
            expected['data']['output_pins_externally_supplied'] = True
            parent._same(fresh, expected)
            raw = parent.io.encode(dict(schema=parent.SCHEMA, implementation=owner._own, binding_sha256=parent.io.digest(owner._binding), request_keys=owner._request_keys(), reference_execution=owner._reference_descriptor, lifecycle=outcome, **parent.FLAGS))
            if owner._records['terminal.json'][1] != raw:
                raise ValueError('parent outcome terminal changed')
            reference(row, owner)
            owner._check()
            if any((getattr(receipt, key) != value for key, value in owner._request_keys().items())):
                raise ValueError('completion request keys differ')
            if receipt.terminal_sha256 != parent.io.digest(owner._records['terminal.json'][1]):
                raise ValueError('completion terminal differs')
            check(row, owner)
            if frame['completed_sources'] != 16:
                raise ValueError('all sixteen Parent source preparations must complete')
            row['validations'] += 1
            row['parent_counts'][id(owner)] += 1
        finally:
            if row.get('frames') and row['frames'][-1] is frame:
                row['frames'].pop()

    def reference(row, owner):
        if owner._reference_owner is None:
            return
        if not owner._reference_held:
            raise ValueError('reference operation lease required')
        parent = check(row, owner)
        validate(row, owner._reference_owner, owner._reference_completion)
        parent._same(owner._reference_match(owner._reference_owner, owner._reference_completion), owner._reference_descriptor)

    def validate_completed_bundle(reference, actuals):
        nonlocal active
        _RUNTIME()
        creator=(pid(),thread())
        def claim(row=None):
            nonlocal active
            with registry_lock:
                if active is not None:
                    error=ValueError('post-negative validation is nonreentrant')
                    if active['creator']==creator and active['failure'] is None:
                        active['failure']=repr(error)
                    raise error
                if row is not None:active=row
        claim()
        if (type(reference) is not tuple or len(reference)!=2
                or type(actuals) is not dict or len(actuals)!=3
                or any(type(lane) is not str for lane in actuals)
                or any(type(pair) is not tuple or len(pair)!=2 for pair in actuals.values())):
            raise TypeError('one reference and exactly three lane-keyed Actual pairs required')
        lanes=tuple(sorted(actuals))
        pairs=(reference,*(actuals[lane] for lane in lanes))
        if any(type(obj) is not parent.Parent or type(issued) is not parent.ParentCompletion
                for obj,issued in pairs):
            raise TypeError('exact same-module Parent and completion pairs required')
        if len({id(obj) for obj,_ in pairs})!=4 or len({id(obj._guard) for obj,_ in pairs})!=4:
            raise ValueError('four distinct original Parent owners and guards required')
        binding=json.loads(reference[0]._raw)['declaration']['source_binding']
        for index,(obj,issued) in enumerate(pairs):
            declaration=json.loads(obj._raw)['declaration']
            role='reference' if index==0 else 'actual'
            if (obj._issued is not issued or obj._state!='complete'
                    or (obj._pid,obj._thread)!=creator or obj._reference_held is not False
                    or issued.role!=role or declaration['role']!=role
                    or declaration['lane_id']!=(None if index==0 else lanes[index-1])
                    or declaration['source_binding']!=binding
                    or obj._reference_owner is not (None if index==0 else reference[0])
                    or obj._reference_completion is not (None if index==0 else reference[1])
                    or parent._completion_bytes(issued)!=obj._issued_bytes):
                raise ValueError('complete original role, lane, reference and binding admission required')
        row=dict(creator=creator, parents=tuple((obj,issued,obj._raw,obj._issued_bytes,obj._guard)
                for obj,issued in pairs), lanes=lanes, source_binding=copy(binding),
            guards=[],marks=[],frames=[],window=None,windows=[],window_counts=dict(bundle=0),
            routes=None,failure=None,validations=0,source_prepares=0,source_requests=0,
            parent_counts={id(obj):0 for obj,_ in pairs})
        first=None; cleanup_errors=[]; result=None
        # Capture releases before any caller-controlled work. Never release a
        # replacement guard, nor a guard whose nonblocking acquisition failed.
        acquisitions=[(obj,obj._guard,obj._guard.release,obj._guard.locked)
            for obj,_ in (*pairs[1:],pairs[0])]
        owned=[]
        identity=None
        try:
            claim(row)
            parent._CHECK()
            for obj,guard,release,locked in acquisitions:
                parent.Parent._enter(obj)
                owned.append((guard,release,locked))
                row['guards'].append(guard)
            for obj,_ in pairs[1:]:
                row['marks'].append(obj)
                obj._reference_held=True
            check(row)
            identity=implementation_identity()
            row['routes']=routes(row,parent)
            with source_window(row,'bundle'):
                for obj,issued in pairs:validate(row,obj,issued)
            check(row)
            if (row['validations']!=10 or row['source_prepares']!=2 or row['source_requests']!=160
                    or row['parent_counts'][id(pairs[0][0])]!=7
                    or any(row['parent_counts'][id(obj)]!=1 for obj,_ in pairs[1:])
                    or row['window'] is not None or row['frames']
                    or len(row['windows'])!=1 or not row['windows'][0]['window_cache_entry_cleared']
                    or not row['windows'][0]['reference_window']['cache_cleared']
                    or row['windows'][0]['reference_window']['logical_reference_inspects']!=48
                    or row['windows'][0]['reference_window']['original_reference_inspects']!=2):
                raise ValueError('complete post-negative source and retained-body inventory required')
            if implementation_identity()!=identity:raise ValueError('post-negative identity bookends differ')
            result=dict(schema=SCHEMA,implementation=identity,declaration=row['routes']['declaration'],
                top_level_validations=4,parent_validations=10,source_prepares=2,
                borrowed_source_returns=160,full_numerical_hour_replays=8,
                within_prefix_numerical_revalidations=8,fresh_context_observations=32,
                source_windows=copy(row['windows']),source_window_cache_cleared=True,
                parent_sites=[dict(root=str(obj.root),role=issued.role,lane_id=None if index==0 else lanes[index-1],
                    retained_bodies=row['parent_counts'][id(obj)],snapshot_sha256=sha256(raw).hexdigest(),
                    issued_completion_sha256=sha256(encoded).hexdigest(),source_binding=copy(binding))
                    for index,(obj,issued,raw,encoded,_) in enumerate(row['parents'])],
                formal_result=False,resource_admission=False,native_execution_authorized=False)
        except BaseException as error:
            first=error
        finally:
            if row['window'] is not None:row['window'].clear();row['window']=None
            row['frames'].clear()
            for obj in reversed(row['marks']):
                try:
                    obj._reference_held=False
                    if obj._reference_held is not False:raise ValueError('Parent reference mark cleanup incomplete')
                except BaseException as error:
                    cleanup_errors.append(repr(error))
                    if first is None:first=error
            for guard,release,locked in reversed(owned):
                try:
                    release()
                    if locked():raise ValueError('Parent guard cleanup incomplete')
                except BaseException as error:
                    cleanup_errors.append(repr(error))
                    if first is None:first=error
            if row['failure'] is not None and first is None:
                first=ValueError('post-negative operation was poisoned by reentry')
            with registry_lock:
                if active is row:active=None
            row.clear()
        if first is not None:
            if cleanup_errors:first.add_note('post-negative cleanup errors: '+repr(cleanup_errors))
            raise first
        _RUNTIME()
        if implementation_identity()!=identity:raise ValueError('post-negative identity changed during cleanup')
        # Round-trip removes all borrowed objects. This is diagnostic JSON,
        # never a ParentCompletion or a transferable execution capability.
        result.update(closed=True,complete=True,outer_cleanup_complete=True,
            operation_registry_cleared=True,all_owned_guards_released=True,all_reference_marks_cleared=True)
        return json.loads(_encode(result))

    return validate_completed_bundle


validate_completed_bundle=_build()


def _install_runtime():
    namespace=globals()
    names=('parent','kernel','SCHEMA','EXPECTED_WINDOWS','FunctionType','SimpleNamespace','deepcopy',
        'dis','sha256','json','os','Path','Lock','get_ident','contextmanager')
    entries=[(namespace,name,namespace[name]) for name in names]
    entries.extend((namespace,name,value) for name,value in tuple(namespace.items()) if type(value) is FunctionType)
    direct=[(parent,name,getattr(parent,name)) for name in
        ('Parent','ParentCompletion','_CHECK','_completion_bytes','_same','io','inspection','preparation','worker',
         'implementation_identity')]
    direct.extend((parent.Parent,name,getattr(parent.Parent,name)) for name in
        ('_enter','_check','_source','_inspect','_reference','_validate','_retained'))
    direct.extend((kernel,name,getattr(kernel,name)) for name in
        ('_RUNTIME','_source_signature','_source_types','_capture_source_guard','implementation_identity',
         'fields','is_dataclass','Fraction','json','sha256','FunctionType'))
    direct.extend((obj,name,getattr(obj,name)) for obj,attrs in
        ((json,('loads','dumps')),(os,('getpid',)),(dis,('get_instructions',))) for name in attrs)
    functions=[(value,value.__code__,repr(value.__defaults__),repr(value.__kwdefaults__))
        for value in [*(v for _,_,v in entries),*(v for _,_,v in direct)] if type(value) is FunctionType]
    windows=tuple(sorted(EXPECTED_WINDOWS.items()))
    def check():
        if (tuple(sorted(EXPECTED_WINDOWS.items()))!=windows
                or any(mapping.get(name) is not value for mapping,name,value in entries)
                or any(getattr(obj,name) is not value for obj,name,value in direct)
                or any(value.__code__ is not code or repr(value.__defaults__)!=defaults
                    or repr(value.__kwdefaults__)!=keywords for value,code,defaults,keywords in functions)):
            raise ValueError('definition-time post-negative validation route changed')
        kernel._RUNTIME()
    return check


_RUNTIME=_install_runtime()
