"""Borrowed validation scope for one twenty-two-common draft Handoff.

The original Handoff alone owns BEGIN/END and every outer resource. This
neutral bridge never imports Handoff, acquires an outer lock or releases one.
"""
from copy import deepcopy
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
import sys
from threading import get_ident
import types
import weakref

SCHEMA = 'h1_common_validation_operation_development_v2'
_HANDOFF_NAME = 'experiments.h1_selector_phase_handoff_development_v4'
_ROUTE_NAMES = ('experiments.h1_operation_historical_witness_development_v3',
    'experiments.h1_phase_exact_source_current_development_v4',
    'experiments.h1_group_n0_common_input_binding_development_v4')
_PINNED_ROUTES = (
    ('experiments.h1_operation_historical_witness_development_v3', 'h1_operation_historical_witness_development_v3.py', '3220ab84c8bbfaa34f2b36cc1c05ead3b3614079b118ac78c08af5916f535d56'),
    ('experiments.h1_phase_exact_source_current_development_v4', 'h1_phase_exact_source_current_development_v4.py', 'b455b42afd587359a5e33af566afe411d962e3efb3143619e8a83bd74f7a8a3a'),
    ('experiments.h1_group_n0_common_input_binding_development_v4', 'h1_group_n0_common_input_binding_development_v4.py', '5b810a7c49e01efa7a32fe526e1690cea1f3b73408897556bc821dbe29ec23b8'),
)


class _Lease:
    def __new__(cls, *args, **kwargs):
        raise TypeError('original Handoff anchor must issue the validation lease')

    def _no_copy(self, *args):
        raise TypeError('live validation lease cannot be copied')
    __copy__ = __deepcopy__ = __reduce_ex__ = _no_copy


def _build():
    records = {}
    owners = {}
    completed = {}
    binding = None
    loaded_routes = None
    lease_type = _Lease
    module = sys.modules[__name__]
    creator = lambda: (os.getpid(), get_ident())
    source_root = Path(__file__).resolve(strict=True).parent
    sources = tuple(sorted(((__name__, str(Path(__file__).resolve(strict=True)),
        sha256(Path(__file__).read_bytes()).hexdigest()), *(
        (name, str((source_root / filename).resolve(strict=True)), pin)
        for name, filename, pin in _PINNED_ROUTES))))
    manifest_pin = sha256(json.dumps(sources, ensure_ascii=True,
        separators=(',', ':')).encode('ascii')).hexdigest()
    compile_source, execute_source = compile, exec
    make_spec, new_module = importlib.util.spec_from_file_location, importlib.util.module_from_spec
    weak_reference = weakref.ref
    closed_failure = b'{"closed":true,"complete":false,"formal_result":false,"native_execution_authorized":false,"resource_admission":false,"schema":"h1_common_validation_operation_development_v2"}'

    def canonical(value):
        return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True,
            allow_nan=False).encode('ascii')

    def terminal(h, value, row=None):
        key = id(h)
        def expired(reference):
            saved = completed.get(key)
            if saved is not None and saved[0] is reference:
                completed.pop(key, None)
        try:
            raw = canonical(value)
            completed[key] = weak_reference(h, expired), raw
        except BaseException:
            completed[key] = weak_reference(h, expired), closed_failure
            raise
        finally:
            if row is not None:
                records.pop(id(row['lease']), None)
                owners.pop(key, None)
                row.clear()

    def state(value):
        fn = value.__func__ if isinstance(value, (staticmethod, classmethod)) else value
        return (fn.__code__, repr(fn.__defaults__), repr(fn.__kwdefaults__)) if type(fn) is types.FunctionType else None

    def snapshot(fn):
        return types.FunctionType(fn.__code__, fn.__globals__, fn.__name__, fn.__defaults__, fn.__closure__)

    def bindings():
        _RUNTIME()
        if binding is None:
            raise ValueError('original Handoff anchor is not bound')
        api, owner_type, verify, operation, fixed, host = binding
        if (sys.modules.get(_HANDOFF_NAME) is not api or api.Handoff is not owner_type
                or api._VERIFY_OWNER is not verify
                or api.__spec__ is not host[2] or api.__loader__ is not host[3]
                or api.__file__ != host[0] or sha256(Path(host[0]).read_bytes()).hexdigest() != host[1]
                or any(state(fn) != original for fn, original in fixed)):
            raise ValueError('original Handoff validation anchor changed')

    def check_routes(routes):
        package = sys.modules['experiments']
        for name, path, pin in routes['sources']:
            target = routes['modules'][name]
            if (sys.modules.get(name) is not target or vars(package).get(name.rsplit('.', 1)[1]) is not target
                    or target.__name__ != name or target.__file__ != path
                    or sha256(Path(path).read_bytes()).hexdigest() != pin):
                raise ValueError('fixed Handoff validation import route changed')
        if (any(target.__spec__ is not spec or target.__loader__ is not loader
                for target, spec, loader in routes['specs'])
                or any(vars(owner).get(name) is not value or state(value) != original
                    for owner, name, value, original in routes['observations'])):
            raise ValueError('fixed Handoff validation entry/code route changed')

    def load_routes():
        nonlocal loaded_routes
        if loaded_routes is not None:
            check_routes(loaded_routes)
            return loaded_routes
        package = sys.modules['experiments']
        if any(name in sys.modules or hasattr(package, name.rsplit('.', 1)[1]) for name in _ROUTE_NAMES):
            raise ValueError('Handoff witness/source/common routes must not be preloaded')
        raw = {}
        for name, path, pin in sources:
            value = Path(path).read_bytes()
            if sha256(value).hexdigest() != pin:
                raise ValueError('declared Handoff validation source bytes changed')
            raw[name] = path, value
        modules = {__name__: module}
        created = []
        try:
            for name in _ROUTE_NAMES:
                path, value = raw[name]
                spec = make_spec(name, path)
                target = new_module(spec)
                created.append((name, target))
                sys.modules[name] = target
                setattr(package, name.rsplit('.', 1)[1], target)
                execute_source(compile_source(value, path, 'exec'), vars(target))
                modules[name] = target
            w, s, c = (modules[name] for name in _ROUTE_NAMES)
            if w.operation_bridge is not module or s.witness is not w or c.witness is not w or c.source is not s:
                raise ValueError('compiled Handoff validation route edges differ')
            observations = []
            for owner, name in ((w, 'GroupWitnessSession'), (w, 'ArmWitness'),
                    (s, 'prepare_common_bundle'), (s, 'CommonSourceBundle'),
                    (c, 'prepare'), (c, 'PreparedCommonInput')):
                value = vars(owner)[name]
                observations.append((owner, name, value, state(value)))
                if isinstance(value, type):
                    for field, descriptor in vars(value).items():
                        if callable(descriptor) or isinstance(descriptor, (property, staticmethod, classmethod)):
                            observations.append((value, field, descriptor, state(descriptor)))
            routes = dict(modules=modules, sources=sources, observations=tuple(observations),
                specs=tuple((target, target.__spec__, target.__loader__) for target in modules.values()),
                source_entry=s.prepare_common_bundle, source_type=s.CommonSourceBundle,
                common_entry=c.prepare, common_type=c.PreparedCommonInput, session_type=w.GroupWitnessSession)
            check_routes(routes)
            loaded_routes = routes
            return routes
        except BaseException as error:
            for name, target in reversed(created):
                field = name.rsplit('.', 1)[1]
                try:
                    if vars(package).get(field) is target:
                        delattr(package, field)
                except BaseException as failure:
                    error.add_note('Handoff package route rollback: ' + repr(failure))
                try:
                    if sys.modules.get(name) is target:
                        del sys.modules[name]
                except BaseException as failure:
                    error.add_note('Handoff module route rollback: ' + repr(failure))
            raise

    def owner_row(owner):
        row = owners.get(id(owner))
        if row is None or row['handoff'] is not owner:
            raise ValueError('original Handoff validation attachment required')
        return row

    def verify_lease(lease):
        bindings()
        row = records.get(id(lease))
        if type(lease) is not lease_type or row is None or row['lease'] is not lease or row['closed']:
            raise ValueError('original active Handoff validation lease required')
        api, owner_type, verify, operation, _, _ = binding
        h = row['handoff']
        record = operation(h, row['token'])
        verify(h)
        if (type(h) is not owner_type or creator() != row['creator'] or h._state != 'running'
                or record is not row['operation'] or record['external_active']
                or record['bundle_state'] is not row['bundle_state']
                or record['predecessor'] is not row['predecessor']
                or record['common_guards'] is not row['common_guards']
                or any(not guard.locked() for guard in row['common_guards'])
                or any(not guard.locked() for guard in row['parent_guards'])
                or any(not owner._reference_held for owner in row['parent_marks'])):
            raise ValueError('borrowed Handoff operation or resources changed')
        return row['roster'], row['declarations'], 22

    def bookend(lease):
        verify_lease(lease)
        check_routes(records[id(lease)]['routes'])

    def claim(lease, session):
        verify_lease(lease)
        row = records[id(lease)]
        if row['session'] is not None or type(session) is not row['routes']['session_type']:
            raise ValueError('one original historical session per Handoff required')
        row['session'] = session
        row['session_close'] = snapshot(type(session).close)
        row['session_receipt'] = snapshot(type(session).receipt)
        row['session_poison'] = snapshot(type(session)._poison)

    def source_result(lease, result):
        bookend(lease)
        if type(result) is not records[id(lease)]['routes']['source_type']:
            raise TypeError('exact pinned Handoff source result required')

    def common_result(lease, result, session):
        bookend(lease)
        row = records[id(lease)]
        if (row['session'] is not session or type(result) is not row['routes']['common_type']
                or result._session_nonce is not session._nonce):
            raise ValueError('exact pinned common result from original Handoff session required')

    def source_entry(lease, arm, registry_identity):
        bookend(lease)
        result = records[id(lease)]['routes']['source_entry'](arm,
            expected_registry_identity=registry_identity)
        source_result(lease, result)
        return result

    def poison(row, error):
        if row['session'] is not None:
            try:
                row['session_poison'](row['session'], error)
            except BaseException as failure:
                error.add_note('Handoff validation poison: ' + repr(failure))

    def attach(h, token):
        bindings()
        api, owner_type, verify, operation, _, host = binding
        previous = completed.get(id(h))
        if type(h) is not owner_type or id(h) in owners or previous is not None and previous[0]() is h:
            raise ValueError('new exact single-attempt Handoff validation attachment required')
        record = operation(h, token)
        verify(h)
        if (h._state != 'running' or record['external_active'] or record['predecessor'] is None
                or record['bundle_state'] is None or not record['common_guards']):
            raise ValueError('original complete guarded Handoff acquisition required')
        roster = record['predecessor'][4]
        lease = object.__new__(lease_type)
        row = dict(lease=lease, handoff=h, creator=creator(), token=token, operation=record,
            roster=roster, declarations=(), predecessor=record['predecessor'],
            bundle_state=record['bundle_state'], common_guards=record['common_guards'],
            parent_guards=record['bundle_state'][2], parent_marks=record['bundle_state'][3],
            closed=False, session=None, session_close=None, session_receipt=None,
            session_poison=None, routes=None, declaration=None, validation_payload=None,
            predecessor_payload=None)
        owners[id(h)] = row
        records[id(lease)] = row
        try:
            attached, _, _ = roster._replay()
            if len(roster._direct) != 3 or set(attached) != set(roster._direct):
                raise ValueError('three independently authenticated N0 siblings required')
            declarations = []
            for arm in sorted(roster._direct):
                local = attached[arm]['reference']['local_terminal']['body']
                declarations.append((arm, local['controller_root'],
                    local['controller_binding_sha256'], local['controller_terminal_sha256']))
            row['declarations'] = tuple(declarations)
            row['routes'] = load_routes()
            row['routes']['session_type'](lease)
            bookend(lease)
            w, s, c = (row['routes']['modules'][name] for name in _ROUTE_NAMES)
            row['declaration'] = dict(schema=SCHEMA, expected_common_calls=22,
                session_identity=row['session']._public_session,
                authenticated_N0_slots=[dict(arm=arm, controller_root=root,
                    controller_binding_sha256=binding_pin, controller_terminal_sha256=terminal_pin)
                    for arm, root, binding_pin, terminal_pin in row['declarations']],
                handoff_implementation_identity=api.implementation_identity(),
                handoff_source=dict(module=api.__name__, path=host[0], sha256=host[1]),
                validation_route_manifest_sha256=manifest_pin,
                validation_route_sources=[dict(module=n, path=p, sha256=pin) for n, p, pin in sources],
                historical_verifier_identity=w.verifier_identity(),
                exact_source_validation_identity=s.implementation_identity(),
                common_validation_identity=c.implementation_identity(),
                predecessor_work_counts_scope='compatibility_projection_only',
                formal_result=False, resource_admission=False, native_execution_authorized=False)
            bookend(lease)
        except BaseException as error:
            abort(h, error)
            raise

    def declaration(h):
        row = owner_row(h)
        bookend(row['lease'])
        return deepcopy(row['declaration'])

    def prepare(h):
        row = owner_row(h)
        try:
            bookend(row['lease'])
            before = row['session']._common_calls
            result = row['routes']['common_entry'](row['session'])
            common_result(row['lease'], result, row['session'])
            if row['session']._common_calls != before + 1:
                raise ValueError('one complete Handoff common return required')
            if row['validation_payload'] is None:
                row['validation_payload'] = result.validation_report_payload
                row['predecessor_payload'] = result.predecessor_report_payload
            elif (result.validation_report_payload != row['validation_payload']
                    or result.predecessor_report_payload != row['predecessor_payload']):
                raise ValueError('guarded common validation or predecessor science changed')
            return result.manifest, result.source_binding, json.loads(result.predecessor_report_payload)
        except BaseException as error:
            poison(row, error)
            raise

    def finish(h):
        row = owner_row(h)
        try:
            bookend(row['lease'])
            if row['session']._common_calls != 22:
                raise ValueError('all twenty-two original common observations required')
            row['session_close'](row['session'])
            row['closed'] = True
            full = row['session_receipt'](row['session'])
            if full.get('complete') is not True:
                raise ValueError('complete closed Handoff validation receipt required')
            executions = full['common_executions']
            counts = {key: sum(value[key] for value in executions) for key in (
                'full_numerical_hour_replays', 'within_prefix_revalidations',
                'cross_common_numerical_proof_reuses', 'context_evaluations')}
            if (len(executions) != 22 or tuple(value['common_call'] for value in executions) != tuple(range(1, 23))
                    or tuple(counts.values()) != (24, 24, 1008, 2112)):
                raise ValueError('honest twenty-two-common validation totals required')
            raw = canonical(full)
            receipt = dict(row['declaration'], common_calls=22, **counts,
                execution_receipt_encoding='json_sorted_ascii_without_newline_v1',
                validation_report_encoding='predecessor_group_encoder_with_newline',
                execution_receipt_sha256=sha256(raw).hexdigest(),
                operation_execution_receipt=full,
                validation_report=json.loads(row['validation_payload']),
                validation_report_sha256=sha256(row['validation_payload']).hexdigest(),
                predecessor_report_sha256=sha256(row['predecessor_payload']).hexdigest(),
                common_receipt_sha256s=[sha256(canonical(value)).hexdigest() for value in executions],
                closed=True, complete=True, first_failure=None,
                all_arm_proofs_cleared=all(value['proof_cleared'] for value in full['arm_receipts'].values()))
            if not receipt['all_arm_proofs_cleared']:
                raise ValueError('all operation-local historical proofs must be cleared')
            if any(value['scientific_payload_sha256'] != receipt['validation_report_sha256'] for value in executions):
                raise ValueError('every execution must bind the same complete validation report')
            check_routes(row['routes'])
            terminal(h, receipt, row)
            return deepcopy(receipt)
        except BaseException as error:
            abort(h, error)
            raise

    def abort(h, error):
        # Cleanup uses captured originals and does not call the possibly broken
        # public dispatch. No outer guard, mark, token or handle is released here.
        row = owners.get(id(h))
        if row is None or row['handoff'] is not h:
            previous = completed.get(id(h))
            if previous is not None and previous[0]() is h:
                try:
                    terminal(h, dict(schema=SCHEMA, closed=True, complete=False,
                        first_failure=repr(error), formal_result=False, resource_admission=False,
                        native_execution_authorized=False))
                except BaseException as failure:
                    error.add_note('Handoff terminal failure record: ' + repr(failure))
            return
        poison(row, error)
        if row['session'] is not None:
            try:
                row['session_close'](row['session'])
            except BaseException as failure:
                error.add_note('Handoff validation close: ' + repr(failure))
        try:
            terminal(h, dict(schema=SCHEMA, closed=True, complete=False,
                first_failure=repr(error), formal_result=False, resource_admission=False,
                native_execution_authorized=False), row)
        except BaseException as failure:
            error.add_note('Handoff terminal failure record: ' + repr(failure))

    def receipt(h):
        saved = completed.get(id(h))
        if saved is None or saved[0]() is not h:
            raise ValueError('validation operation has not reached a terminal state')
        return json.loads(saved[1])

    def bind_handoff(api, owner_type, verify, operation):
        nonlocal binding
        _RUNTIME()
        if (binding is not None or api.__name__ != _HANDOFF_NAME
                or sys.modules.get(_HANDOFF_NAME) is not api or api.Handoff is not owner_type
                or Path(api.__file__).resolve(strict=True) != source_root / (_HANDOFF_NAME.rsplit('.', 1)[1] + '.py')
                or verify.__qualname__ != '_anchor.<locals>.verify'
                or operation.__qualname__ != '_anchor.<locals>.operation'):
            raise ValueError('single original definition-time Handoff anchor required')
        host = (api.__file__, sha256(Path(api.__file__).read_bytes()).hexdigest(), api.__spec__, api.__loader__)
        binding = api, owner_type, verify, operation, tuple((fn, state(fn)) for fn in (verify, operation)), host
        return attach, prepare, declaration, finish, abort, receipt

    return bind_handoff, verify_lease, claim, bookend, source_entry, source_result, common_result


(_bind_handoff, _VERIFY_LEASE, _CLAIM_SESSION, _BOOKEND,
    _SOURCE_ENTRY, _SOURCE_RESULT, _COMMON_RESULT) = _build()


def _install_runtime():
    module = sys.modules[__name__]
    expected = []
    for owner in (module, _Lease):
        for name, value in tuple(vars(owner).items()):
            if ((owner is module and (not name.startswith('__') or name in
                    ('__name__', '__file__', '__package__', '__spec__', '__loader__')) and name != '_RUNTIME')
                    or isinstance(value, (types.FunctionType, types.ModuleType, type, staticmethod, classmethod, property))):
                state = (value.__code__, repr(value.__defaults__), repr(value.__kwdefaults__)) if type(value) is types.FunctionType else None
                expected.append((owner, name, value, state))

    def check():
        if (module._RUNTIME is not check or any(vars(owner).get(name) is not value
                or state is not None and (value.__code__, repr(value.__defaults__), repr(value.__kwdefaults__)) != state
                for owner, name, value, state in expected)):
            raise ValueError('definition-time borrowed Handoff validation bridge changed')
    return check


_RUNTIME = _install_runtime()
