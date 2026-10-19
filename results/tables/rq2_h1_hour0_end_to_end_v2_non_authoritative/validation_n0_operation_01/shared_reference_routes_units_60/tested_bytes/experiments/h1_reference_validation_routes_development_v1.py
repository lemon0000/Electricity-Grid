"""Private clone factory for a four-Parent synchronous reference/source window."""
from copy import deepcopy as copy
from hashlib import sha256
import json
from pathlib import Path
from types import FunctionType, SimpleNamespace, MappingProxyType

from experiments import h1_selector_source_window_development_v2 as source_windows
from experiments import h1_selector_parent_validation_operation_development_v2 as literal
from experiments import h1_reference_validation_window_development_v1 as reference_windows

SCHEMA='h1_reference_validation_routes_development_v1'
state=source_windows.state
clone=source_windows.clone
_source_signature=literal._source_signature
_source_types=literal._source_types
_capture_source_guard=literal._capture_source_guard

def _encode(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True,allow_nan=False).encode('ascii')

def implementation_identity():
    _RUNTIME()
    return sha256(_encode([SCHEMA,sha256(Path(__file__).read_bytes()).hexdigest(),
        source_windows.implementation_identity(),reference_windows.implementation_identity()])).hexdigest()

def _make_routes(row, parent, check, raw_source, raw_inspect, *, family, enable_reference, scope_code, scope_globals,
                 capture_source_guard=None):
    _RUNTIME()
    if family not in ('parent_validation','post_negative'):
        raise ValueError('fixed shared reference validation family required')
    old_snapshot, old_worker = (parent.worker.snapshot, parent.worker)
    old_preparation, old_inspection = (parent.preparation, parent.inspection)
    old_phase = old_snapshot.phase
    source = old_phase.source
    functions = []
    proxies = []
    capture_source_guard=_capture_source_guard if capture_source_guard is None else capture_source_guard
    fixed_source = capture_source_guard(source)
    source_guard_records=reference_windows._function_rows((capture_source_guard,fixed_source))
    direct = []

    def captured(obj, name):
        value = getattr(obj, name)
        direct.append((obj, name, value, state(value)))
        return value
    full_source = captured(source, 'prepare')

    def successor(function, **changes):
        result = clone(function, **changes)
        functions.append((function, state(function), result, state(result),
            reference_windows._function_rows((function,result))))
        return result

    def proxy(**values):
        result = SimpleNamespace(**values)
        proxies.append((result, tuple(values.items())))
        return result

    def source_prepare(root, **arguments):
        owner = row['frames'][-1]['owner'] if row['frames'] else None
        check(row, owner, borrowed=True)
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
        check(row, owner, borrowed=True)
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
    reference=None
    rebuild_namespace=None
    if enable_reference:
        namespace=dict(old_snapshot._build.__globals__,phase=phase)
        rebuild_namespace=dict(old_snapshot.rebuild.__globals__)
        create=reference_windows._bind_parent_validation_window if family=='parent_validation' else reference_windows._bind_post_negative_window
        reference=create(row,parent,check,old_snapshot.sequence,
            caller_code=old_snapshot._build.__code__,caller_globals=namespace,
            rebuild_code=old_snapshot.rebuild.__code__,rebuild_globals=rebuild_namespace,
            scope_code=scope_code,scope_globals=scope_globals)
        namespace['sequence']=proxy(_root=old_snapshot.sequence._root,
            _configuration=old_snapshot.sequence._configuration,inspect=reference['inspect'])
        build=successor(old_snapshot._build,_namespace=namespace)
    else:build = successor(old_snapshot._build, phase=phase)
    reference_functions=() if reference is None else tuple(
        (name,reference[name],state(reference[name])) for name in ('inspect','finish','check'))
    rebuild = successor(old_snapshot.rebuild, _build=build,_namespace=rebuild_namespace)
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
        _RUNTIME()
        reference_windows._verify_functions(source_guard_records)
        if reference is not None:
            if any(reference[name] is not fn or state(fn)!=before for name,fn,before in reference_functions):
                raise ValueError('fixed reference-window private API changed')
            reference['check']()
        if any((getattr(obj, name) is not value or state(value) != original for obj, name, value, original in direct)):
            raise ValueError('fixed Parent exact-source direct dispatch changed')
        fixed_source()
        for original, original_state, fn, fn_state, values in functions:
            if state(original) != original_state or state(fn) != fn_state:
                raise ValueError('fixed Parent functional successor route changed')
            reference_windows._verify_functions(values)
        for obj, values in proxies:
            if len(vars(obj)) != len(values) or any((vars(obj).get(name) is not value for name, value in values)):
                raise ValueError('fixed Parent functional successor proxy changed')
    check_routes()
    route_declaration = dict(schema=SCHEMA, helper_identity=implementation_identity(), predecessor_snapshot_implementation=old_snapshot.implementation_identity(), predecessor_source_implementation=source.implementation_identity(), source_schedule='bookended_four_Parent_synchronous_validation_window', same_predecessor_per_nested_source_io_schedule=False, same_predecessor_failure_order=False, source_result_reuse_scope='single_synchronous_window_without_external_callback', full_dependency_check_scope='outer_dispatch_and_window_boundaries_after_solver_guard_restoration', borrowed_callback_check_scope='fixed_routes_creator_owner_frames_guards_binding_and_complete_source_fields', cleared_state_scope='window_cache_entry_only', predecessor_derived_outputs_follow_original_consumer_lifetime=True, full_source_object_graph_destroyed=False, cross_window_source_reuse=False, complete_dynamic_input_closure_proved=False, unobserved_between_bookends_ABA_covered=False, predecessor_payload_scope='scientific_compatibility_projection_only', compatibility_counts_describe_actual_execution=False, route=[dict(function=original.__qualname__, file=original.__code__.co_filename) for original, _, _, _, _ in functions])
    route_declaration.update(reference_window_supported=True,reference_window_active=reference is not None,
        reference_window_helper=reference_windows.implementation_identity(),
        reference_observation_schedule='entry_and_tail_original_across_three_Actuals_inside_held_four_Parent_window',
        reference_payload_fields=['request_sha256','replay'],reference_per_call_fresh_at_return=False,
        actual_output_inspection_cached=False,family=family)
    check_routes()
    return MappingProxyType(dict(source=parent_source, inspect=parent_inspect, rebuild=rebuild, check=check_routes,
        materialize=materialize, prepare=prepare, bind=bind, declaration=route_declaration,reference=reference))

def _install_runtime():
    namespace=globals()
    bindings=tuple((name,value,state(value)) for name,value in tuple(namespace.items()) if not name.startswith('__'))
    functions,used=reference_windows._function_rows(value for _,value,_ in bindings)
    used=tuple(row for row in used if not (row[0] is namespace and row[1]=='_RUNTIME'))
    source_runtime=source_windows._RUNTIME
    def check():
        if namespace.get('_RUNTIME') is not check or any(namespace.get(name) is not value or state(value)!=before for name,value,before in bindings):
            raise ValueError('shared validation clone factory changed')
        reference_windows._verify_functions((functions,used))
        source_runtime()
        reference_windows._RUNTIME()
    return check
_RUNTIME=_install_runtime()
