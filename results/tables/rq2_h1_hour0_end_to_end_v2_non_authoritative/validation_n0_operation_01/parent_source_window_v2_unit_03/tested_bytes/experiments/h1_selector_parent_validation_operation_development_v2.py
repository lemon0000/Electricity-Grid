"""Bookended source reconstruction within synchronous Parent validation windows.

The original source kernel runs at entry and exit of each public validation.
Nested source requests borrow the original owned value inside that window; Parent,
transport, archive, process, environment and reference observations stay real.
This is an explicitly different validation identity and observation schedule.
"""
from contextlib import contextmanager
from copy import deepcopy
from dataclasses import fields, is_dataclass
from fractions import Fraction
import dis
from hashlib import sha256
import json
import os
from pathlib import Path
from threading import get_ident
import sys
from types import FunctionType, SimpleNamespace
import weakref

SCHEMA = 'h1_selector_parent_validation_operation_development_v2'
_HOST = 'experiments.h1_selector_phase_handoff_development_v4'
EXPECTED_WINDOWS = dict(bundle=13, pair=8, records=4)
EXPECTED_SOURCE_REQUESTS = 2408


def implementation_identity():
    return sha256(_encode([SCHEMA, sha256(Path(__file__).read_bytes()).hexdigest(),
        EXPECTED_WINDOWS, EXPECTED_SOURCE_REQUESTS])).hexdigest()


def _encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=True, allow_nan=False).encode('ascii')


def _source_signature(value):
    def stable(item):
        kind=type(item)
        if kind in (str,int,bool,type(None)):return [kind.__name__,item]
        if kind is float:return ['float',item.hex()]
        if kind is bytes:return ['bytes',item.hex()]
        if isinstance(item,Fraction):return ['fraction',item.numerator,item.denominator]
        if is_dataclass(item):return ['dataclass',kind.__module__,kind.__qualname__,
            [[field.name,stable(getattr(item,field.name))] for field in fields(item)]]
        if kind in (tuple,list):return [kind.__name__,[stable(v) for v in item]]
        if kind is dict:return ['dict',sorted([[stable(k),stable(v)] for k,v in item.items()],key=repr)]
        if kind in (set,frozenset):return [kind.__name__,sorted([stable(v) for v in item],key=repr)]
        raise TypeError('complete literal source fields required: '+str(kind))
    return sha256(_encode(stable(value))).hexdigest()


def _source_types(value):
    """Keep actual class objects, including every nested dataclass/container."""
    rows=[]
    def visit(item):
        kind=type(item)
        if is_dataclass(item):
            names=tuple(field.name for field in fields(item))
            rows.append((kind,names))
            for name in names:visit(getattr(item,name))
        elif kind is dict:
            rows.append((kind,len(item)))
            for key,part in sorted(item.items(),key=lambda pair:repr(pair[0])):
                visit(key);visit(part)
        elif kind in (tuple,list,set,frozenset):
            rows.append((kind,len(item)))
            for part in (sorted(item,key=repr) if kind in (set,frozenset) else item):visit(part)
        else:rows.append((kind,None))
    visit(value)
    return tuple(rows)


def _capture_source_guard(module):
    """Preserve the predecessor _guard_prepare dispatch checklist, without executing it."""
    historical=module.historical
    names=('historical','predecessor','origin_join','normal','source','registry','physical','io','json','asdict',
        'SCHEMA','PROJECTION_SCHEMA','CFE_RULE','_envelope','_project','_ratio','_prepare',
        'ExactSourceCurrent','CommonSourceBundle','_historical_projection','implementation_identity',
        '_guard_prepare','_build_entries','prepare','prepare_common_bundle')
    own=tuple((module,name,getattr(module,name)) for name in names)
    verifier_names=('_replay_prefix','verifier_identity','_observe_sources','legacy','witness',
        'old','history','current','io','binding','bridge','base','_observe',
        '_observe_prefix','_obligation_inventory','implementation_identity','VERIFIER_SCHEMA')
    verifier=tuple((historical,name,getattr(historical,name)) for name in verifier_names)
    dependencies=((module.source,('load_pinned_current','validate_pinned_current')),
        (module.registry,('prepare',)),(module.origin_join,('_join','implementation_identity')),
        (module.predecessor,('implementation_identity',)),
        (module.origin_join.predecessor,('_coordinates',)),(module.normal,('_owned','_decision')),
        (module.physical,('_digest',)),(module.io,('encode','digest','pin')),
        (module.source.h1.workload_projection,('project_workload_power',)),
        (historical.old,('additional_content_bound',)),
        (historical.binding.replay,('request_key',)),
        (historical.history.prior,('Rq2SolverSpec',)),
        (historical.history.replay,('H1HourReplayLimits',)),
        (historical.history.prior.Rq2SolverSpec,('__init__',)),
        (historical.history.replay.H1HourReplayLimits,('__init__','__post_init__')),
        (module.json,('loads',)),
        (historical.history.replay.guard,('solver_calls_forbidden',)),
        (historical.witness,('_dispatch_view',)),(historical.binding,('CAP',)))
    entries=own+verifier+tuple((obj,name,getattr(obj,name)) for obj,fields in dependencies for name in fields)
    codes=tuple((value,value.__code__,repr(value.__defaults__),repr(value.__kwdefaults__))
        for _,_,value in entries if type(value) is FunctionType)
    closures=tuple((value,value.__closure__,tuple(cell.cell_contents for cell in value.__closure__ or ()))
        for value in (module.prepare,module.prepare_common_bundle))
    def fixed():
        if (any(getattr(obj,name) is not value for obj,name,value in entries)
                or any(value.__code__ is not code or repr(value.__defaults__)!=defaults
                    or repr(value.__kwdefaults__)!=keywords for value,code,defaults,keywords in codes)
                or any(value.__closure__ is not cells or any(cell.cell_contents is not original
                    for cell,original in zip(cells or (),contents)) for value,cells,contents in closures)):
            raise ValueError('predecessor exact-source dispatch checklist changed')
    return fixed


def _build():
    records = {}
    bundles = {}
    completed = {}
    binding = None
    module = sys.modules[__name__]
    pid, thread = os.getpid, get_ident
    copy = deepcopy
    weak_reference = weakref.ref
    failure_bytes = _encode(dict(schema=SCHEMA, closed=True, complete=False,
        formal_result=False, resource_admission=False, native_execution_authorized=False))

    def state(value):
        return (value.__code__, repr(value.__defaults__), repr(value.__kwdefaults__)) if type(value) is FunctionType else None

    def require_binding():
        _RUNTIME()
        if binding is None:
            raise ValueError('original Handoff Parent validation anchor is not bound')
        api, kind, verify, operation, finalized, host_path, host_pin, fixed = binding
        if (sys.modules.get(_HOST) is not api or api.Handoff is not kind
                or api.__file__ != host_path or sha256(Path(host_path).read_bytes()).hexdigest() != host_pin
                or any(state(fn) != original for fn, original in fixed)):
            raise ValueError('original Parent validation host changed')
        return api, verify, operation, finalized

    def row_for_bundle(bundle):
        row = bundles.get(id(bundle))
        if row is None or row['bundle'] is not bundle:
            raise ValueError('original borrowed Parent bundle required')
        return row

    def admit_creator(row):
        # Admission must precede poisoning handlers. A foreign caller must not
        # discard the creating thread's only path to release private proofs.
        if (records.get(id(row['bundle'])) is not row or bundles.get(id(row['bundle'])) is not row
                or row['creator']!=(pid(),thread()) or row['closed']):
            raise ValueError('original Parent validation creating thread required')

    def admit_completed(host):
        saved=completed.get(id(host))
        if saved is None or saved[0]() is not host or saved[2]!=(pid(),thread()):
            raise ValueError('original Parent receipt creating thread required')
        return saved

    def admit_operation(row):
        admit_creator(row)
        if row['window'] is not None:
            error=ValueError('Parent validation window is nonreentrant')
            if row['failure'] is None:row['failure']=repr(error)
            raise error

    def check(row, owner=None):
        api, verify, operation, _ = require_binding()
        if (records.get(id(row['bundle'])) is not row
                or bundles.get(id(row['bundle'])) is not row
                or row['creator'] != (pid(), thread()) or row['closed'] or row['failure'] is not None):
            raise ValueError('Parent validation operation lifetime changed')
        verify(row['host'])
        saved = operation(row['host'], row['token'])
        bundle = row['bundle']
        if (saved['bundle'] is not bundle or bundle.reference is not row['reference']
                or bundle.actuals is not row['actuals']
                or len(bundle.held) != len(row['guards'])
                or any(a is not b for a, b in zip(bundle.held, row['guards']))
                or len(bundle.marked) != len(row['marks'])
                or any(a is not b for a, b in zip(bundle.marked, row['marks']))
                or any(not guard.locked() for guard in row['guards'])
                or any(mark._reference_held is not True for mark in row['marks'])):
            raise ValueError('original held Parent guards, marks or pairs changed')
        parent = api.parent
        parent._CHECK()
        for obj, receipt, raw, issued, guard in row['parents']:
            if (type(obj) is not parent.Parent or type(receipt) is not parent.ParentCompletion
                    or obj._raw is not raw or obj._issued is not receipt
                    or obj._issued_bytes != issued or parent._completion_bytes(receipt) != issued
                    or obj._guard is not guard or not guard.locked()):
                raise ValueError('exact original Parent, receipt, snapshot and guard required')
        if owner is not None:
            if not row['frames'] or row['frames'][-1]['owner'] is not owner:
                raise ValueError('original current Parent validation site required')
        if row['routes'] is not None:row['routes']['check']()
        return parent

    def clone(function, **changes):
        namespace = dict(function.__globals__)
        namespace.update(changes)
        result = FunctionType(function.__code__, namespace, function.__name__,
            function.__defaults__, function.__closure__)
        result.__kwdefaults__ = copy(function.__kwdefaults__)
        return result

    def routes(row, parent):
        old_snapshot, old_worker = parent.worker.snapshot, parent.worker
        old_preparation, old_inspection = parent.preparation, parent.inspection
        old_phase = old_snapshot.phase
        source = old_phase.source
        functions = []
        proxies = []
        fixed_source=_capture_source_guard(source)
        direct=[]

        def captured(obj,name):
            value=getattr(obj,name)
            direct.append((obj,name,value,state(value)))
            return value

        full_source=captured(source,'prepare')
        def successor(function, **changes):
            result = clone(function, **changes)
            pending=[function.__code__];names={'__builtins__'}
            while pending:
                code=pending.pop()
                names.update(instruction.argval for instruction in dis.get_instructions(code)
                    if instruction.opname=='LOAD_GLOBAL')
                pending.extend(value for value in code.co_consts if type(value) is type(code))
            functions.append((function, state(function), result, state(result),
                tuple((name,result.__globals__[name]) for name in names if name in result.__globals__)))
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
            if (_source_signature(window['value']) != window['signature']
                    or _source_types(window['value']) != window['types']):
                raise ValueError('owned window source fields changed')
            # ExactSourceCurrent forbids deepcopy. The fixed consumers read its
            # value; they receive no new ownership or execution capability.
            result = window['value']
            if (type(result) is not source.ExactSourceCurrent
                    or _source_signature(result) != window['signature']
                    or _source_types(result) != window['types']):
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
        phase = proxy(_fresh=fresh_source, _initial=old_phase._initial,
            _request=old_phase._request, business=old_phase.business, RREF=old_phase.RREF)
        build = successor(old_snapshot._build, phase=phase)
        rebuild = successor(old_snapshot.rebuild, _build=build)
        snapshot = proxy(rebuild=rebuild, CAP=old_snapshot.CAP, encode=old_snapshot.encode,
            RebuiltInput=old_snapshot.RebuiltInput, implementation_identity=old_snapshot.implementation_identity)
        request = successor(old_worker.request_document, snapshot=snapshot)
        worker = proxy(request_document=request, CAP=old_worker.CAP,
            sequence=old_worker.sequence, runtime=old_worker.runtime,
            content_bound=old_worker.content_bound, implementation_identity=old_worker.implementation_identity)
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
            if any(getattr(obj,name) is not value or state(value)!=original
                    for obj,name,value,original in direct):
                raise ValueError('fixed Parent exact-source direct dispatch changed')
            fixed_source()
            for original, original_state, fn, fn_state, values in functions:
                if (state(original) != original_state or state(fn) != fn_state
                        or any(fn.__globals__.get(name) is not value for name, value in values)):
                    raise ValueError('fixed Parent functional successor route changed')
            for obj, values in proxies:
                if len(vars(obj)) != len(values) or any(vars(obj).get(name) is not value for name, value in values):
                    raise ValueError('fixed Parent functional successor proxy changed')

        check_routes()
        route_declaration=dict(schema=SCHEMA, helper_identity=implementation_identity(),
                predecessor_snapshot_implementation=old_snapshot.implementation_identity(),
                predecessor_source_implementation=source.implementation_identity(),
                source_schedule='one_original_prepare_before_and_after_each_public_window',
                same_predecessor_per_nested_source_io_schedule=False,
                same_predecessor_failure_order=False,
                source_result_reuse_scope='single_synchronous_window_without_external_callback',
                cross_window_source_reuse=False,
                complete_dynamic_input_closure_proved=False,
                unobserved_between_bookends_ABA_covered=False,
                predecessor_payload_scope='scientific_compatibility_projection_only',
                compatibility_counts_describe_actual_execution=False,
                route=[dict(function=original.__qualname__, file=original.__code__.co_filename)
                    for original, _, _, _, _ in functions])
        check_routes()
        return dict(source=parent_source, inspect=parent_inspect, rebuild=rebuild, check=check_routes,
            materialize=materialize,
            declaration=route_declaration)

    def declaration(bundle):
        row=row_for_bundle(bundle)
        check(row)
        return dict(row['routes']['declaration'], parents=[dict(root=str(obj.root),
            issued_completion_sha256=sha256(issued).hexdigest(),
            snapshot_sha256=sha256(raw).hexdigest(),
            source_binding=json.loads(raw)['declaration']['source_binding'])
            for obj,_,raw,issued,_ in row['parents']])

    def terminal(row, value):
        host = row['host']
        creator=row['creator']
        key = id(host)
        def expired(reference):
            if completed.get(key, (None,))[0] is reference:completed.pop(key, None)
        try:
            completed[key] = weak_reference(host, expired), _encode(value), creator
        except BaseException:
            completed[key] = weak_reference(host, expired), failure_bytes, creator
            raise
        finally:
            records.pop(id(row['bundle']), None)
            bundles.pop(id(row['bundle']), None)
            row.clear()

    def close_row(row, error=None):
        # Only detached source values belong here. All borrowed guards and
        # every outer handle remain the Handoff's responsibility.
        active = row['window']
        if active is not None:
            active.clear()
            row['window'] = None
        complete = (error is None and row['bundle_calls'] == 13
            and row['validations'] == 150 and row['rebuilds'] == 4
            and row['source_requests'] == EXPECTED_SOURCE_REQUESTS
            and row['source_prepares'] == 50
            and row['window_counts'] == EXPECTED_WINDOWS
            and len(row['windows']) == 25)
        incomplete=error is None and not complete
        if incomplete:error=ValueError('complete Parent windows, source counts and cleanup required')
        value = dict(schema=SCHEMA, declaration=None if row['routes'] is None else row['routes']['declaration'],
            parent_validations=row['validations'], bundle_validations=row['bundle_calls'],
            standalone_record_rebuilds=row['rebuilds'], source_requests=row['source_requests'],
            source_prepares=row['source_prepares'], source_windows=row['windows'],
            source_window_counts=row['window_counts'],
            full_numerical_hour_replays=4 * row['source_prepares'],
            reused_numerical_inspections=0,
            within_prefix_numerical_revalidations=4 * row['source_prepares'],
            fresh_context_observations=16 * row['source_prepares'],
            borrowed_source_returns=row['source_requests'],
            source_window_cache_cleared=row['window'] is None, closed=True,
            validation_checks_complete=complete, status='pending' if complete else 'aborted',
            outer_cleanup_complete=False, complete=False,
            first_failure=row['failure'] or (None if error is None else repr(error)), cleanup_errors=[],
            formal_result=False, resource_admission=False, native_execution_authorized=False)
        terminal(row, value)
        if incomplete:raise error

    @contextmanager
    def source_window(row, kind):
        check(row)
        if row['window'] is not None or row['frames'] or kind not in EXPECTED_WINDOWS:
            raise ValueError('nonreentrant original Parent source window required')
        if row['window_counts'][kind] >= EXPECTED_WINDOWS[kind]:
            raise ValueError('Parent source window count exceeded')
        for owner,issued,_,_,_ in row['parents']:
            owner._check()
            if owner._state!='complete' or owner._issued is not issued:
                raise ValueError('original complete Parent admission required before source work')
        old = row['source_binding']
        arguments = dict(expected_binding_sha256=old['binding_sha256'],
            expected_terminal_sha256=old['genesis_terminal_sha256'], completed_hours=1,
            expected_registry_identity=old['registry_identity'])
        window = dict(root=old['root'], arguments=arguments, value=None, signature=None,types=None,
            active=False, in_full_prepare=True, requests=0)
        row['window'] = window
        try:
            before = row['routes']['materialize'](window['root'], arguments)
            row['source_prepares'] += 1
            signature = _source_signature(before)
            types=_source_types(before)
            window.update(value=before, signature=signature, types=types,active=True, in_full_prepare=False)
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
            # Reference pairs have16 requests; Actual pairs add2 recursive
            # reference validations and therefore48. Bundle always has160.
            if ((expected is not None and requests != expected)
                    or (kind == 'pair' and requests not in (16, 48))):
                raise ValueError('complete nested source request inventory required')
            row['windows'].append(dict(kind=kind, source_binding=copy(old),
                complete_source_signature_sha256=signature,
                nested_source_requests=requests, original_source_prepares=2,
                full_numerical_hour_replays=8, fresh_context_observations=32,
                fresh_at_return_only=True, closed=True, source_value_cleared=True))
            row['window_counts'][kind] += 1
        finally:
            window.clear()
            if row.get('window') is window:
                row['window'] = None

    def abort_row(row, error):
        if not row or row.get('closed'):return
        if row['failure'] is None:row['failure']=repr(error)
        close_row(row, error)

    def validate(row, owner, receipt):
        parent=check(row)
        if not any(owner is obj and receipt is issued for obj, issued, *_ in row['parents']):
            raise TypeError('original Parent and issued completion pair required')
        frame=dict(owner=owner,kind='validating',completed_sources=0)
        row['frames'].append(frame)
        try:
            owner._check()
            if (owner._state!='complete' or receipt is not owner._issued
                    or parent._completion_bytes(receipt)!=owner._issued_bytes):
                raise ValueError('exact original issued parent completion required')
            # Explicit successor of Parent._validate/_retained. Attribute calls
            # on the old Parent would bypass our private source route.
            owner._check();row['routes']['source'](owner)
            reference(row,owner)
            if owner._outcome is None:raise ValueError('completed owned outcome required')
            outcome=json.loads(owner._outcome);prior=outcome['inspection'];data=prior['data']
            fresh=row['routes']['inspect'](owner,
                dict(pid=outcome['pid'],creation_filetime=outcome['creation_filetime']),
                {name:data['pins'][name] for name in parent.inspection.OUTPUT_FILES})
            expected=copy(prior);expected['data']['output_pins_externally_supplied']=True
            parent._same(fresh,expected)
            raw=parent.io.encode(dict(schema=parent.SCHEMA,implementation=owner._own,
                binding_sha256=parent.io.digest(owner._binding),request_keys=owner._request_keys(),
                reference_execution=owner._reference_descriptor,lifecycle=outcome,**parent.FLAGS))
            if owner._records['terminal.json'][1]!=raw:raise ValueError('parent outcome terminal changed')
            reference(row,owner);owner._check()
            if any(getattr(receipt,key)!=value for key,value in owner._request_keys().items()):
                raise ValueError('completion request keys differ')
            if receipt.terminal_sha256!=parent.io.digest(owner._records['terminal.json'][1]):
                raise ValueError('completion terminal differs')
            check(row,owner)
            if frame['completed_sources']!=16:
                raise ValueError('all sixteen Parent source preparations must complete')
            row['validations']+=1
        finally:
            if row.get('frames') and row['frames'][-1] is frame:row['frames'].pop()

    def reference(row, owner):
        if owner._reference_owner is None:return
        if not owner._reference_held:raise ValueError('reference operation lease required')
        parent=check(row,owner)
        validate(row,owner._reference_owner,owner._reference_completion)
        parent._same(owner._reference_match(owner._reference_owner,owner._reference_completion),
            owner._reference_descriptor)

    def bind(api, owner_type, verify, operation, finalized):
        nonlocal binding
        if binding is not None or api.__name__!=_HOST or api.Handoff is not owner_type:
            raise ValueError('one original Handoff Parent anchor required')
        binding=(api,owner_type,verify,operation,finalized,api.__file__,
            sha256(Path(api.__file__).read_bytes()).hexdigest(),
            tuple((fn,state(fn)) for fn in (verify,operation,finalized)))
        return attach, validate_bundle, rebuild, finish, abort, receipt, commit, validate_pair, declaration

    def attach(host, token):
        api, verify, operation, _=require_binding()
        verify(host);saved=operation(host,token);bundle=saved['bundle']
        if id(bundle) in bundles:raise ValueError('Parent validation operation already active')
        pairs=(bundle.reference,*(pair for _,pair in bundle.actuals))
        if any(pair is None for pair in pairs):raise ValueError('complete three-Actual Parent bundle required')
        source_binding=json.loads(pairs[0][0]._raw)['declaration']['source_binding']
        if any(json.loads(obj._raw)['declaration']['source_binding']!=source_binding for obj,_ in pairs):
            raise ValueError('one canonical source binding for the complete Parent bundle required')
        row=dict(host=host,token=token,bundle=bundle,reference=bundle.reference,
            actuals=bundle.actuals,guards=tuple(bundle.held),marks=tuple(bundle.marked),
            parents=tuple((obj,issued,obj._raw,obj._issued_bytes,obj._guard) for obj,issued in pairs),
            creator=(pid(),thread()),closed=False,failure=None,frames=[],window=None,source_binding=copy(source_binding),
            routes=None,validations=0,bundle_calls=0,rebuilds=0,source_prepares=0,
            source_requests=0,windows=[],window_counts=dict(bundle=0,pair=0,records=0))
        records[id(bundle)]=row;bundles[id(bundle)]=row
        try:
            parent=check(row)
            row['routes']=routes(row,parent)
            check(row)
        except BaseException as error:
            try:abort_row(row,error)
            except BaseException as failure:error.add_note('Parent attach cleanup: '+repr(failure))
            raise

    def validate_bundle(bundle):
        row=row_for_bundle(bundle)
        admit_operation(row)
        try:
            check(row)
            with source_window(row, 'bundle'):
                validate(row,*bundle.reference)
                for _,pair in bundle.actuals:validate(row,*pair)
            row['bundle_calls']+=1
            if row['bundle_calls']>13:raise ValueError('Parent bundle validation count exceeded')
            check(row)
        except BaseException as error:
            try:abort_row(row,error)
            except BaseException as failure:error.add_note('Parent validation cleanup: '+repr(failure))
            raise

    def validate_pair(bundle,owner,issued):
        row=row_for_bundle(bundle)
        admit_operation(row)
        try:
            check(row)
            if not any(owner is obj and issued is receipt for obj,receipt,*_ in row['parents']):
                raise TypeError('original Parent pair required before source work')
            with source_window(row, 'pair'):validate(row,owner,issued)
        except BaseException as error:
            try:abort_row(row,error)
            except BaseException as failure:error.add_note('Parent pair cleanup: '+repr(failure))
            raise

    def rebuild(bundle, owner):
        row=row_for_bundle(bundle)
        admit_operation(row)
        try:
            parent=check(row)
            if not any(owner is value[0] for value in row['parents']):
                raise TypeError('original Parent record source required')
            with source_window(row, 'records'):
                frame=dict(owner=owner,kind='records',completed_sources=0)
                row['frames'].append(frame)
                try:
                    result=row['routes']['rebuild'](owner._raw,expected_sha256=parent.io.digest(owner._raw))
                    if frame['completed_sources']!=2:
                        raise ValueError('two complete records source requests required')
                    check(row,owner)
                finally:
                    if row.get('frames') and row['frames'][-1] is frame:row['frames'].pop()
            row['rebuilds']+=1
            return result
        except BaseException as error:
            try:abort_row(row,error)
            except BaseException as failure:error.add_note('Parent rebuild cleanup: '+repr(failure))
            raise

    def receipt(host):
        saved=admit_completed(host)
        return json.loads(saved[1])

    def finish(host):
        row=next((row for row in records.values() if row['host'] is host),None)
        if row is None:raise ValueError('original live Parent validation operation required')
        admit_operation(row)
        try:
            check(row);close_row(row)
            return receipt(host)
        except BaseException as error:
            try:abort_row(row,error)
            except BaseException as failure:error.add_note('Parent finish cleanup: '+repr(failure))
            raise

    def abort(host,error):
        row=next((row for row in records.values() if row['host'] is host),None)
        if row is not None:
            admit_creator(row)
            abort_row(row,error)
        else:
            saved=completed.get(id(host))
            if saved is not None and saved[0]() is host:
                admit_completed(host)
                value=json.loads(saved[1])
                if value.get('status')!='aborted':
                    value.update(complete=False,validation_checks_complete=False,status='aborted',outer_failure=repr(error))
                    completed[id(host)]=saved[0],_encode(value),saved[2]

    def commit(host):
        _,_,_,finalized=require_binding()
        admit_completed(host)
        value=receipt(host)
        if (value.get('status')!='pending' or not value.get('validation_checks_complete') or value.get('complete')
                or value.get('outer_cleanup_complete') or value.get('first_failure') is not None
                or value.get('outer_failure') is not None):
            raise ValueError('single pending Parent proof receipt required')
        finalized(host)
        value.update(outer_cleanup_complete=True,complete=True,status='committed')
        saved=completed[id(host)]
        completed[id(host)]=saved[0],_encode(value),saved[2]
        return receipt(host)

    return bind


_bind_handoff=_build()


def _install_runtime():
    namespace=globals()
    expected=tuple((name,value,value.__code__,repr(value.__defaults__),repr(value.__kwdefaults__))
        for name,value in tuple(namespace.items()) if type(value) is FunctionType)
    constants=(SCHEMA,_HOST,tuple(sorted(EXPECTED_WINDOWS.items())),EXPECTED_SOURCE_REQUESTS)
    def check():
        if ((SCHEMA,_HOST,tuple(sorted(EXPECTED_WINDOWS.items())),EXPECTED_SOURCE_REQUESTS)!=constants
                or any(namespace.get(name) is not fn or fn.__code__ is not code
                    or repr(fn.__defaults__)!=defaults or repr(fn.__kwdefaults__)!=keywords
                    for name,fn,code,defaults,keywords in expected)):
            raise ValueError('definition-time Parent validation operation changed')
    return check


_RUNTIME=_install_runtime()
