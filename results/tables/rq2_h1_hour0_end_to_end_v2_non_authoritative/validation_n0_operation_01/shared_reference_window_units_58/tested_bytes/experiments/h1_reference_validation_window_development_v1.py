"""Private reference replay across three Actuals in an existing held bundle.

This changes the observation schedule, never the numerical policy or limits.
Only the cloned snapshot build may borrow request_sha256/ReplayResult. Actual
output inspection remains fresh. No authority, native call, or persistent cache.
"""
from dataclasses import fields, is_dataclass
import dis
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from threading import get_ident
from types import CodeType, FunctionType, GeneratorType, MappingProxyType, ModuleType

from experiments import h1_selector_parent_validation_operation_development_v2 as literal
from experiments import h1_historical_hour_witness_development_v1 as witness


SCHEMA = 'h1_reference_validation_window_development_v1'
COUNTS = MappingProxyType(dict(bundle=48, records_bundle=102, post_negative_bundle=48))
SITE_COUNTS = MappingProxyType(dict(bundle=16, records_bundle=34, post_negative_bundle=16))
MAX_MODULES = 2048
MAX_BINDINGS = 100000
MAX_SIGNATURE_NODES = 100000


def _encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')


def _state(fn):
    if isinstance(fn, (staticmethod, classmethod)): return ('descriptor', _state(fn.__func__))
    if isinstance(fn, property): return ('property', id(fn), *(_state(v) for v in (fn.fget, fn.fset, fn.fdel)))
    return (id(fn.__code__), id(fn.__defaults__), repr(fn.__defaults__), id(fn.__kwdefaults__), repr(fn.__kwdefaults__),
            id(fn.__globals__),
            tuple(id(cell.cell_contents) for cell in fn.__closure__ or ())) if type(fn) is FunctionType else None


def implementation_identity():
    return sha256(_encode([SCHEMA, sha256(Path(__file__).read_bytes()).hexdigest(), dict(COUNTS),dict(SITE_COUNTS),
                          literal.implementation_identity()])).hexdigest()


def _function_rows(functions):
    """Fixed code, defaults, closures and used globals, including builtin shadows."""
    rows, globals_rows, seen, keys = [], [], set(), set()
    def names(code):
        result = {ins.argval for ins in dis.get_instructions(code) if ins.opname == 'LOAD_GLOBAL'}
        for value in code.co_consts:
            if type(value) is CodeType: result.update(names(value))
        return result
    def visit(fn):
        if isinstance(fn,(staticmethod,classmethod)):
            visit(fn.__func__);return
        if isinstance(fn,property):
            for accessor in (fn.fget,fn.fset,fn.fdel):visit(accessor)
            return
        if type(fn) is not FunctionType or id(fn) in seen: return
        seen.add(id(fn)); rows.append((fn, _state(fn), fn.__globals__))
        for cell in fn.__closure__ or (): visit(cell.cell_contents)
        visit(getattr(fn, '__wrapped__', None))
        for name in names(fn.__code__) | {'__builtins__'}:
            mappings = (fn.__globals__,) if name in fn.__globals__ else (fn.__globals__, fn.__builtins__)
            for namespace in mappings:
                key = id(namespace), name
                if key in keys: continue
                keys.add(key); value = namespace.get(name)
                globals_rows.append((namespace, name, name in namespace, value))
                if type(value) is FunctionType and value.__module__ == __name__: visit(value)
    for fn in functions: visit(fn)
    return tuple(rows), tuple(globals_rows)


def _verify_functions(records):
    rows, globals_rows = records
    if (any(_state(fn) != before or fn.__globals__ is not namespace for fn, before, namespace in rows) or
            any((name in namespace) != present or namespace.get(name) is not value
                for namespace, name, present, value in globals_rows)):
        raise ValueError('reference window callable or builtin/global binding changed')


def _dependencies(sequence):
    """The project dispatch closure; the five genuine denial endpoints are special.

    Mutable runtime registries are not scientific constants. Actual inputs,
    saved bytes and class graphs are checked separately, with honest bookends.
    """
    guard = witness.hour.prior.guard
    targets = ((type(guard.SolverFactory), '__call__'), (guard.current, 'solve_current'),
        (guard.current.native, 'run_h1_chain'), (guard.current.native.capture, 'solve_once'),
        (guard.current.native.capture.provenance.adapter, 'create_solver'))
    denial_keys = {(id(obj), name) for obj, name in targets}
    endpoints = tuple((obj, name, getattr(obj, name), _state(getattr(obj, name))) for obj, name in targets)
    if type(sequence) is not ModuleType:
        # Unit fixtures use an explicitly synthetic sequence, never admitted as
        # canonical by a real Parent or the configured acceptance target.
        direct = tuple((obj, name, getattr(obj, name), _state(getattr(obj, name))) for obj, names in (
            (sequence, ('inspect', '_snapshot', '_configuration', 'selection', 'FLAGS', 'SCHEMA', 'io')),
            (sequence.selection, ('stage_labels', 'ReplayResult')),
            (sequence.io, ('encode',))) for name in names)
        records = _function_rows(value for _, _, value, _ in direct)
        def synthetic_check():
            _RUNTIME()
            if any(getattr(obj, name) is not value or _state(value) != before for obj, name, value, before in direct):
                raise ValueError('synthetic reference sequence binding changed')
            _verify_functions(records)
            if any(getattr(obj, name) is not value or _state(value) != before for obj, name, value, before in endpoints):
                witness._solver_guard_view()
        return synthetic_check
    pending, seen, bindings, functions, constants, modules = [sequence, witness, literal], set(), [], [], [], []
    while pending:
        module = pending.pop()
        if id(module) in seen: continue
        seen.add(id(module))
        if len(seen) > MAX_MODULES: raise ValueError('reference dependency module bound exceeded')
        if type(module) is not ModuleType: continue  # Explicit synthetic namespace tests.
        modules.append((module, module.__name__, module.__file__, module.__spec__, module.__loader__))
        for name, value in tuple(vars(module).items()):
            if len(bindings) > MAX_BINDINGS: raise ValueError('reference dependency binding bound exceeded')
            if name.startswith('__'): continue
            if type(value) is ModuleType and value.__name__.startswith(('experiments.', 'src.')):
                bindings.append((module, name, value, None)); pending.append(value)
            elif callable(value):
                if (id(module), name) not in denial_keys:
                    bindings.append((module, name, value, _state(value)))
                    if type(value) is FunctionType: functions.append(value)
                origin = sys.modules.get(getattr(value, '__module__', ''))
                if type(origin) is ModuleType and origin.__name__.startswith(('experiments.', 'src.')):
                    pending.append(origin)
                if isinstance(value, type) and value.__module__.startswith(('experiments.', 'src.')):
                    for field, member in tuple(vars(value).items()):
                        if (callable(member) or isinstance(member, (property, staticmethod, classmethod))) and (id(value), field) not in denial_keys:
                            bindings.append((value, field, member, _state(member)))
                            functions.append(member)
            elif name.isupper() and type(value) in (str, int, float, bool, tuple, frozenset, MappingProxyType, type(None)):
                constants.append((module, name, value, repr(value)))
    function_rows, global_rows = _function_rows(functions)
    denial_globals = {(id(vars(obj)), name) for obj, name in targets if type(obj) is ModuleType}
    function_records = function_rows, tuple(row for row in global_rows if (id(row[0]), row[1]) not in denial_globals)
    bindings, constants, modules = tuple(bindings), tuple(constants), tuple(modules)
    def check():
        _RUNTIME()
        if (any(sys.modules.get(name) is not module or module.__name__ != name or module.__file__ != path or
                module.__spec__ is not spec or module.__loader__ is not loader for module, name, path, spec, loader in modules) or
                any(vars(obj).get(name) is not value or _state(value) != before for obj, name, value, before in bindings) or
                any(getattr(obj, name) is not value or repr(value) != encoded for obj, name, value, encoded in constants)):
            raise ValueError('reference saved-replay dependency closure changed')
        _verify_functions(function_records)
        if any(getattr(obj, name) is not value or _state(value) != before for obj, name, value, before in endpoints):
            witness._solver_guard_view()
    return check


def _payload_signature(value):
    """A frozen outer dataclass is insufficient; check the complete literal graph."""
    nodes = [0]
    def check(item):
        nodes[0] += 1
        if nodes[0] > MAX_SIGNATURE_NODES: raise ValueError('reference replay graph bound exceeded')
        kind = type(item)
        if kind in (str, int, float, bool, bytes, type(None)): return
        if kind is tuple:
            for part in item: check(part)
            return
        if is_dataclass(item) and getattr(kind, '__dataclass_params__', None).frozen:
            for field in fields(item): check(getattr(item, field.name))
            return
        raise TypeError('exact frozen reference replay literal graph required: '+str(kind))
    check(value)
    return literal._source_signature(value), literal._source_types(value)


def _bind_parent_validation_window(row,parent,check_owner,sequence,**callers):
    kind=row['window']['kind']
    if kind not in ('bundle','records_bundle'):
        raise ValueError('fixed Parent-validation reference window kind required')
    return _bind(row,parent,check_owner,sequence,kind=kind,**callers)


def _bind_post_negative_window(row,parent,check_owner,sequence,**callers):
    if row['window']['kind']!='bundle':
        raise ValueError('fixed post-negative reference window kind required')
    return _bind(row,parent,check_owner,sequence,kind='post_negative_bundle',**callers)


def _bind(row, parent, check_owner, sequence, *, kind, caller_code, caller_globals,
          rebuild_code, rebuild_globals, scope_code, scope_globals):
    """A private per-window generator owns the record; no mutable control dict.

    Its API does not accept cached results, signatures, callbacks or controls.
    The independent bound close always clears even if a Python API is changed.
    """
    _RUNTIME()
    creator = row['creator']
    if kind not in COUNTS or len(row['parents']) != 4:
        raise ValueError('already-held four-Parent validation window required')
    parent_check=parent._CHECK
    parent_check()
    if parent.SCHEMA!='h1_selector_parent_controller_development_v4':
        raise ValueError('fixed Parent4 validation family required')
    anchors=tuple((obj,issued,raw,issued_bytes,guard) for obj,issued,raw,issued_bytes,guard in row['parents'])
    reference,completion,reference_raw,reference_issued,reference_guard=anchors[0]
    actuals=tuple(anchor[0] for anchor in anchors[1:])
    if len({id(obj) for obj in (reference,*actuals)})!=4 or len({id(anchor[4]) for anchor in anchors})!=4:
        raise ValueError('four distinct original owners and guards required')
    expected=(completion.scientific_root,completion.scientific_terminal_sha256,
              completion.scientific_request_sha256,completion.max_archive_bytes)
    reference_declaration=json.loads(reference_raw)['declaration']
    source_binding=reference_declaration['source_binding']
    if reference_declaration['role']!='reference' or reference_declaration['reference'] is not None:
        raise ValueError('original Rref declaration required')
    for obj,issued,raw,issued_bytes,guard in anchors[1:]:
        declaration=json.loads(raw)['declaration'];ref=declaration['reference']
        if (declaration['role']!='actual' or declaration['source_binding']!=source_binding or
                (ref['root'],ref['terminal_sha256'],ref['request_sha256'],ref['max_archive_bytes'])!=expected):
            raise ValueError('all Actual declarations must share the original reference key')
    def check_anchors():
        if parent._CHECK is not parent_check:
            raise ValueError('fixed Parent4 checker changed')
        for index,(obj,issued,raw,issued_bytes,guard) in enumerate(anchors):
            if (type(obj) is not parent.Parent or type(issued) is not parent.ParentCompletion or
                    obj._raw is not raw or obj._issued is not issued or obj._issued_bytes!=issued_bytes or
                    parent._completion_bytes(issued)!=issued_bytes or obj._guard is not guard or not guard.locked() or
                    (obj._pid,obj._thread)!=creator or obj._state!='complete' or
                    obj._reference_held is not bool(index) or
                    obj._reference_owner is not (reference if index else None) or
                    obj._reference_completion is not (completion if index else None)):
                raise ValueError('original held four-Parent reference anchors changed')
    check_anchors()
    canonical = type(sequence) is ModuleType
    if canonical:
        path = Path(__file__).with_name('h1_owned_selector_sequence_development_v1.py')
        if (sequence.__name__ != 'experiments.h1_owned_selector_sequence_development_v1' or sequence.__file__ != str(path) or
                sys.modules.get(sequence.__name__) is not sequence or sequence.inspect.__globals__ is not vars(sequence)):
            raise ValueError('canonical reference sequence provenance required')
        body, = [v for v in compile(path.read_bytes(), str(path), 'exec').co_consts
                 if type(v) is CodeType and v.co_name == 'inspect']
        if sequence.inspect.__code__ != body: raise ValueError('source-authored reference inspect required')
    dependencies = _dependencies(sequence)
    # All authority-bearing controls are immutable and captured before any IO.
    control = MappingProxyType(dict(original=sequence.inspect, snapshot=sequence._snapshot,
        configuration=sequence._configuration, labels=sequence.selection.stage_labels,
        replay_type=sequence.selection.ReplayResult, encode=sequence.io.encode,
        check_owner=check_owner,check_anchors=check_anchors,actuals=actuals,
        dependencies=dependencies, expected=expected,
        caller_code=caller_code, caller_globals=caller_globals, rebuild_code=rebuild_code,rebuild_globals=rebuild_globals,
        scope_code=scope_code, scope_globals=scope_globals,protocol_globals=globals()))
    own = implementation_identity()
    audit_data={}
    audit=MappingProxyType(audit_data)

    def admit(*, borrowed, owner=None):
        _RUNTIME()
        if creator != (os.getpid(), get_ident()) or row['failure'] is not None:
            raise ValueError('reference window original creator and lifetime required')
        if borrowed and not any(owner is obj for obj in control['actuals']):
            raise ValueError('only an original Actual site can borrow the shared reference')
        control['check_anchors']()
        control['check_owner'](row, owner if borrowed else None, borrowed=borrowed)
        control['dependencies']()

    def context(args, keywords):
        if (len(args) != 4 or set(keywords) != {'expected_terminal_sha256', 'max_archive_bytes', 'run_configuration',
                'lane', 'selector', 'specification', 'limits', 'power'} or
                str(args[0]) != expected[0] or keywords['expected_terminal_sha256'] != expected[1] or
                keywords['max_archive_bytes'] != expected[3] or keywords['lane'].role != 'Rref' or keywords['power'] is not None):
            raise ValueError('one exact declared reference request required')
        value = (str(args[0]), *args[1:], dict(keywords))
        return literal._source_signature(value), literal._source_types(value)

    def complete(args, keywords):
        root, frame, disclosure, before = args
        count = len(control['labels'](frame, keywords['lane']))
        view = control['snapshot'](root, count, keywords['limits'], True)
        result = control['original'](*args, **keywords)
        if (type(result) is not dict or set(result) != {'schema', 'records', 'replay', 'terminal_sha256',
                'request_sha256', 'fresh_at_return', 'owned_run_return_observed', *sequence.FLAGS} or
                result['schema'] != sequence.SCHEMA or result['terminal_sha256'] != expected[1] or
                result['request_sha256'] != expected[2] or result['fresh_at_return'] is not True or
                result['owned_run_return_observed'] is not False or type(result['records']) is not tuple or
                any(type(raw) is not bytes for raw in result['records']) or type(result['replay']) is not control['replay_type'] or
                any(result[name] is not False for name in sequence.FLAGS)):
            raise ValueError('complete canonical reference replay result required')
        signature = _payload_signature((result['records'], result['replay']))
        if control['snapshot'](root, count, keywords['limits'], True) != view:
            raise ValueError('reference namespace/files changed around full inspection')
        configuration = control['configuration'](frame, disclosure, before,
            {name: keywords[name] for name in ('lane', 'selector', 'specification', 'limits', 'power')},
            keywords['max_archive_bytes'], keywords['run_configuration'])
        return result, signature, view, sha256(control['encode'](configuration)).hexdigest()

    def machine():
        cached = saved_context = saved_key = saved_signature = saved_view = saved_configuration = None
        logical = original = borrowed = 0
        site_counts=(0,0,0)
        request = yield None
        try:
            while True:
                action, value = request
                sender=sys._getframe(1)
                try:
                    code=audit['inspect_code'] if action=='borrow' else audit['finish_code'] if action=='finish' else None
                    if (creator!=(os.getpid(),get_ident()) or sender.f_code is not code or
                            sender.f_globals is not control['protocol_globals']):
                        raise ValueError('original private reference protocol caller required')
                finally:del sender
                if action == 'borrow':
                    args, keywords,owner = value
                    index=next((index for index,obj in enumerate(actuals) if owner is obj),None)
                    if index is None:raise ValueError('original Actual site required')
                    key = context(args, keywords)
                    if cached is None:
                        result, signature, view, configuration = complete(args, keywords)
                        if context(args, keywords) != key:
                            raise ValueError('reference context changed during entry inspection')
                        cached = (result['request_sha256'], result['replay'], result['records'])
                        saved_context = (tuple(args), MappingProxyType(dict(keywords)))
                        saved_key, saved_signature, saved_view, saved_configuration = key, signature, view, configuration
                        original += 1
                    else:
                        if key != saved_key: raise ValueError('second reference key in one window refused')
                        if _payload_signature((cached[2], cached[1])) != saved_signature:
                            raise ValueError('cached reference typed graph changed')
                        borrowed += 1
                    logical += 1
                    site_counts=tuple(count+int(site==index) for site,count in enumerate(site_counts))
                    if any(count>SITE_COUNTS[kind] for count in site_counts):
                        raise ValueError('shared reference owner site count exceeded')
                    reply = {'request_sha256': cached[0], 'replay': cached[1]}
                elif action == 'finish':
                    if (cached is None or logical!=COUNTS[kind] or
                            site_counts!=(SITE_COUNTS[kind],)*3):
                        raise ValueError('complete shared reference per-owner request counts required')
                    if context(*saved_context) != saved_key or _payload_signature((cached[2], cached[1])) != saved_signature:
                        raise ValueError('retained reference context or payload changed')
                    result, signature, view, configuration = complete(*saved_context)
                    original += 1
                    if (context(*saved_context) != saved_key or _payload_signature((cached[2], cached[1])) != saved_signature or
                            signature != saved_signature or view != saved_view or configuration != saved_configuration):
                        raise ValueError('reference saved view or fresh numerical replay changed at tail')
                    reply = dict(schema=SCHEMA, implementation=own, kind=kind,
                        canonical_reference_sequence=canonical, logical_reference_inspects=logical,
                        original_reference_inspects=original, entry_original_fresh=1, exit_original_fresh=1,
                        borrowed_reference_results=borrowed, complete_saved_view_sha256=sha256(_encode(saved_view)).hexdigest(),
                        request_sha256=cached[0], replay_signature_sha256=saved_signature[0],
                        configuration_sha256=saved_configuration, per_call_fresh_at_return=False,
                        bookend_only_freshness=True, configuration_bookend_only=True,
                        scientific_payload_compatible=True, legacy_observation_or_report_equal=False,
                        actual_output_inspection_cached=False, cache_cleared=False,
                        cross_window_reuse=False, unobserved_between_bookends_ABA_covered=False,
                        cross_actual_reference_payload_reuse=True,
                        same_per_parent_reference_observation_schedule=False,
                        between_owner_calls_ABA_covered=False,
                        parent_sites=[dict(root=str(obj.root),logical_reference_inspects=count)
                                      for obj,count in zip(actuals,site_counts)],
                        complete_dynamic_input_closure_proved=False, formal_result=False,
                        resource_admission=False, native_execution_authorized=False)
                    yield reply
                    raise ValueError('finished reference window cannot be reused')
                else: raise ValueError('private reference window command required')
                request = yield reply
        finally:
            primary=sys.exc_info()[1]
            try:
                if cached is not None and _payload_signature((cached[2], cached[1])) != saved_signature:
                    raise ValueError('cached reference graph changed before clearance')
            except BaseException as cleanup:
                if primary is not None and not isinstance(primary,GeneratorExit):
                    primary.add_note('reference graph cleanup: '+repr(cleanup))
                else:raise
            finally:
                cached = saved_context = saved_key = saved_signature = saved_view = saved_configuration = None
                site_counts=None

    def check():
        _RUNTIME()
        _verify_functions(audit['records'])
        if (creator != (os.getpid(), get_ident()) or type(engine) is not GeneratorType or
                engine.gi_code is not engine_code or engine.gi_frame is None or engine.gi_yieldfrom is not None):
            raise ValueError('original active reference window required')

    def inspect(*args, **keywords):
        frame = sys._getframe(1)
        try:
            check()
            if (frame.f_code is not control['caller_code'] or frame.f_globals is not control['caller_globals'] or
                    frame.f_back is None or frame.f_back.f_code is not control['rebuild_code'] or
                    frame.f_back.f_globals is not control['rebuild_globals'] or
                    not row['frames'] or not any(row['frames'][-1]['owner'] is obj for obj in actuals)):
                raise ValueError('exact private snapshot build caller required')
            owner=row['frames'][-1]['owner']
            admit(borrowed=True,owner=owner)
            return engine.send(('borrow', (args, keywords,owner)))
        except BaseException as error:
            if creator == (os.getpid(), get_ident()) and row['failure'] is None: row['failure'] = repr(error)
            raise
        finally: del frame

    def finish():
        frame = sys._getframe(1)
        try:
            check()
            if frame.f_code is not control['scope_code'] or frame.f_globals is not control['scope_globals']:
                raise ValueError('original source-window tail caller required')
            admit(borrowed=False)
            return engine.send(('finish', None))
        except BaseException as error:
            if creator == (os.getpid(), get_ident()) and row['failure'] is None: row['failure'] = repr(error)
            raise
        finally: del frame
    engine = machine(); next(engine)
    engine_code = engine.gi_code
    audit_data.update(inspect_code=inspect.__code__,finish_code=finish.__code__)
    audit_data['records']=_function_rows((admit, context, complete, machine, check, inspect, finish, dependencies,
                 check_anchors,check_owner,parent_check,parent._completion_bytes,
                 literal._source_signature, literal._source_types, witness._solver_guard_view,
                 control['original'], control['snapshot'], control['configuration'], control['labels']))
    return MappingProxyType(dict(inspect=inspect, finish=finish, check=check, close=engine.close,
                                 generator=engine, control=control))


def _install_runtime():
    namespace = globals()
    rows = tuple((name, value, _state(value)) for name, value in namespace.items() if not name.startswith('__'))
    constants = tuple(COUNTS.items())
    site_constants=tuple(SITE_COUNTS.items())
    literal_runtime, literal_state = literal._RUNTIME, _state(literal._RUNTIME)
    functions,used_globals=_function_rows(value for _,value,_ in rows)
    used_globals=tuple(row for row in used_globals if not (row[0] is namespace and row[1]=='_RUNTIME'))
    def check():
        if (namespace.get('_RUNTIME') is not check or tuple(COUNTS.items()) != constants or
                tuple(SITE_COUNTS.items())!=site_constants or
                literal._RUNTIME is not literal_runtime or _state(literal_runtime) != literal_state or
                any(namespace.get(name) is not value or _state(value) != before for name, value, before in rows)):
            raise ValueError('reference sequence window helper changed')
        _verify_functions((functions,used_globals))
        literal_runtime()
    return check


_RUNTIME = _install_runtime()
