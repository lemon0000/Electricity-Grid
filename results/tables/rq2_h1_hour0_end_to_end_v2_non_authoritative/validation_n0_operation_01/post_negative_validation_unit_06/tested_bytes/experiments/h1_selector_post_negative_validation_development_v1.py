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

from experiments import h1_selector_parent_controller_development_v2 as parent
from experiments import h1_selector_parent_validation_operation_development_v2 as kernel

SCHEMA = 'h1_selector_post_negative_validation_development_v1'
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
        EXPECTED_WINDOWS])).hexdigest()


def _build():
    active = None
    registry_lock = Lock()
    copy = deepcopy
    pid, thread = os.getpid, get_ident

    def check(row, owner=None):
        _RUNTIME()
        if (active is not row or row['creator'] != (pid(), thread())
                or row['failure'] is not None):
            raise ValueError('original post-negative operation lifetime required')
        parent._CHECK()
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

    def routes(row, parent):
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
        parent_source = successor(parent.Parent._source, preparation=preparation)
        parent_inspect = successor(parent.Parent._inspect, inspection=inspection)

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
        route_declaration = dict(schema=SCHEMA, helper_identity=implementation_identity(), predecessor_snapshot_implementation=old_snapshot.implementation_identity(), predecessor_source_implementation=source.implementation_identity(), source_schedule='one_original_prepare_before_and_after_each_public_window', same_predecessor_per_nested_source_io_schedule=False, same_predecessor_failure_order=False, same_public_parent_guard_schedule=False, between_top_level_parent_validations_ABA_covered=False, source_result_reuse_scope='single_synchronous_window_without_external_callback', cleared_state_scope='window_cache_entry_only', predecessor_derived_outputs_follow_original_consumer_lifetime=True, full_source_object_graph_destroyed=False, cross_window_source_reuse=False, complete_dynamic_input_closure_proved=False, unobserved_between_bookends_ABA_covered=False, predecessor_payload_scope='scientific_compatibility_projection_only', compatibility_counts_describe_actual_execution=False, route=[dict(function=original.__qualname__, file=original.__code__.co_filename) for original, _, _, _, _ in functions])
        check_routes()
        return dict(source=parent_source, inspect=parent_inspect, rebuild=rebuild, check=check_routes, materialize=materialize, declaration=route_declaration)

    @contextmanager
    def source_window(row, kind, owner=None):
        check(row)
        if row['window'] is not None or row['frames'] or kind not in EXPECTED_WINDOWS:
            raise ValueError('nonreentrant original Parent source window required')
        if row['window_counts'][kind] >= EXPECTED_WINDOWS[kind]:
            raise ValueError('Parent source window count exceeded')
        for admitted_owner, issued, _, _, _ in row['parents']:
            admitted_owner._check()
            if admitted_owner._state != 'complete' or admitted_owner._issued is not issued:
                raise ValueError('original complete Parent admission required before source work')
        old = row['source_binding']
        arguments = dict(expected_binding_sha256=old['binding_sha256'], expected_terminal_sha256=old['genesis_terminal_sha256'], completed_hours=1, expected_registry_identity=old['registry_identity'])
        window = dict(root=old['root'], arguments=arguments, value=None, signature=None, types=None, active=False, in_full_prepare=True, requests=0)
        entry = None
        row['window'] = window
        try:
            before = row['routes']['materialize'](window['root'], arguments)
            row['source_prepares'] += 1
            signature = _source_signature(before)
            types = _source_types(before)
            window.update(value=before, signature=signature, types=types, active=True, in_full_prepare=False)
            check(row)
            yield
            check(row)
            if _source_signature(before) != signature or _source_types(before) != types:
                raise ValueError('retained source fields changed before window tail')
            window['in_full_prepare'] = True
            after = row['routes']['materialize'](window['root'], arguments)
            row['source_prepares'] += 1
            if _source_signature(after) != signature or _source_types(after) != types:
                raise ValueError('source fields changed during synchronous Parent validation')
            check(row)
            requests = window['requests']
            expected = dict(bundle=160, pair=None, records=2)[kind]
            if expected is not None and requests != expected or (kind == 'pair' and requests not in (16, 48)):
                raise ValueError('complete nested source request inventory required')
            entry = dict(kind=kind, source_binding=copy(old), parent_root=None if owner is None else str(owner.root), complete_source_signature_sha256=signature, nested_source_requests=requests, original_source_prepares=2, full_numerical_hour_replays=8, fresh_context_observations=32, fresh_at_return_only=True, closed=True, window_cache_entry_cleared=False)
            row['windows'].append(entry)
            row['window_counts'][kind] += 1
        finally:
            window.clear()
            if row.get('window') is window:
                row['window'] = None
            if entry is not None:
                entry['window_cache_entry_cleared'] = True

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
                    or len(row['windows'])!=1 or not row['windows'][0]['window_cache_entry_cleared']):
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
