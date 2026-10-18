"""Borrowed Parent validation with operation-owned N0 arithmetic proofs.

Every source, registry, transport, clock, process and archive observation stays
on its predecessor route. Private functional successors replace only historical
hour arithmetic. Old audit identities name compatibility projections; the final
receipt records this implementation and the work that actually occurred.
"""
from copy import deepcopy
import dis
from hashlib import sha256
import importlib.util
import json
import os
from pathlib import Path
from threading import get_ident
import sys
from types import FunctionType, SimpleNamespace
import weakref

SCHEMA = 'h1_selector_parent_validation_operation_development_v1'
_HOST = 'experiments.h1_selector_phase_handoff_development_v4'
_WITNESS_NAME = 'experiments.h1_parent_source_n0_witness_development_v1'
_WITNESS_FILE = 'h1_parent_source_n0_witness_development_v1.py'
_WITNESS_SHA256 = '0a63d219ded8c0f550eebc797072fdf6db057a67395f64aed0bedefb14418272'


class _Lease:
    def __new__(cls, *args, **kwargs):
        raise TypeError('only the original Handoff can issue a Parent validation lease')

    def _no_copy(self, *args):
        raise TypeError('a Parent validation lease cannot be exported')
    __copy__ = __deepcopy__ = __reduce_ex__ = _no_copy


def implementation_identity():
    return sha256(_encode([SCHEMA, sha256(Path(__file__).read_bytes()).hexdigest(),
        _WITNESS_NAME, _WITNESS_SHA256])).hexdigest()


def _encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
        ensure_ascii=True, allow_nan=False).encode('ascii')


def _build():
    records = {}
    bundles = {}
    completed = {}
    binding = None
    witness_module = None
    module = sys.modules[__name__]
    lease_type = _Lease
    pid, thread = os.getpid, get_ident
    copy = deepcopy
    weak_reference = weakref.ref
    witness_path = str(Path(__file__).resolve().with_name(_WITNESS_FILE))
    witness_pin = _WITNESS_SHA256
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

    def load_witness():
        nonlocal witness_module
        package = sys.modules['experiments']
        leaf = _WITNESS_NAME.rsplit('.', 1)[1]
        if sha256(Path(witness_path).read_bytes()).hexdigest() != witness_pin:
            raise ValueError('fixed Parent arithmetic witness source changed')
        if witness_module is not None:
            if (sys.modules.get(_WITNESS_NAME) is not witness_module
                    or vars(package).get(leaf) is not witness_module):
                raise ValueError('fixed Parent arithmetic witness route changed')
            return witness_module
        if _WITNESS_NAME in sys.modules or leaf in vars(package):
            raise ValueError('Parent arithmetic witness must not be preloaded')
        raw = Path(witness_path).read_bytes()
        spec = importlib.util.spec_from_file_location(_WITNESS_NAME, witness_path)
        target = importlib.util.module_from_spec(spec)
        try:
            sys.modules[_WITNESS_NAME] = target
            setattr(package, leaf, target)
            exec(compile(raw, witness_path, 'exec'), vars(target))
        except BaseException:
            if sys.modules.get(_WITNESS_NAME) is target:sys.modules.pop(_WITNESS_NAME)
            if vars(package).get(leaf) is target:delattr(package, leaf)
            raise
        witness_module = target
        return target

    def row_for_bundle(bundle):
        row = bundles.get(id(bundle))
        if row is None or row['bundle'] is not bundle:
            raise ValueError('original borrowed Parent bundle required')
        return row

    def check(row, owner=None):
        api, verify, operation, _ = require_binding()
        if (records.get(id(row['lease'])) is not row
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

    def lease_check(lease, owner):
        row = records.get(id(lease))
        if type(lease) is not lease_type or row is None or row['lease'] is not lease:
            raise TypeError('original Parent validation lease required')
        # Inner arithmetic guards borrow the already checked live scope. Full
        # host/Parent/functional-route checks bracket every Parent validation
        # and source preparation; do not recursively repeat them at each of the
        # original sixteen numerical context observations.
        if (row['creator']!=(pid(),thread()) or row['closed'] or row['failure'] is not None
                or not row['frames'] or row['frames'][-1]['owner'] is not owner
                or bundles.get(id(row['bundle'])) is not row or binding is None):
            raise ValueError('Parent numerical lease lifetime or current site changed')
        saved=binding[3](row['host'],row['token'])
        if (saved['bundle'] is not row['bundle'] or row['bundle'].reference is not row['reference']
                or row['bundle'].actuals is not row['actuals']
                or any(not guard.locked() for guard in row['guards'])
                or any(mark._reference_held is not True for mark in row['marks'])):
            raise ValueError('Parent numerical lease guards or original bundle changed')
        found=next((value for value in row['parents'] if value[0] is owner),None)
        if (found is None or owner._raw is not found[2] or owner._issued is not found[1]
                or owner._issued_bytes!=found[3] or owner._guard is not found[4]):
            raise ValueError('original Parent numerical lease owner changed')

    def parent_confirmed(lease, owner, witness):
        lease_check(lease, owner)
        row = records[id(lease)]
        frame = row['frames'][-1]
        return (frame['kind'] == 'validated' and frame['completed_sources'] == 16
            and row['witnesses'].get(id(owner), (None,))[0] is witness)

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
        witness = load_witness()
        witness_definition=(witness.__spec__,witness.__loader__,witness.__file__)
        functions = []
        proxies = []

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
            frame = row['frames'][-1]
            old = json.loads(owner._raw)['declaration']['source_binding']
            expected = dict(expected_binding_sha256=old['binding_sha256'],
                expected_terminal_sha256=old['genesis_terminal_sha256'], completed_hours=1,
                expected_registry_identity=old['registry_identity'])
            if str(root) != old['root'] or arguments != expected:
                raise ValueError('Parent source root, pins or registry declaration differs')
            key = id(owner)
            if key not in row['witnesses']:
                proof = witness.ParentSourceWitness(Path(root), arm_id='Parent:'+str(len(row['witnesses'])),
                    expected_binding_sha256=old['binding_sha256'],
                    expected_terminal_sha256=old['genesis_terminal_sha256'],
                    _parent_lease=row['lease'], _parent_owner=owner)
                row['witnesses'][key] = proof, proof._cleanup_original
                proof.__enter__()
            proof = row['witnesses'][key][0]
            ticket = proof._start()
            own = source.implementation_identity()
            prefix = [0]
            with source.historical.history.replay.guard.solver_calls_forbidden():
                baseline = source.historical.witness._dispatch_view(module)
                verifier = source.historical.verifier_identity()

                def fresh():
                    lease_check(row['lease'], owner)
                    row['routes']['check']()
                    proof._check(ticket)
                    if (source.implementation_identity() != own
                            or source.historical.verifier_identity() != verifier
                            or source.historical.witness._dispatch_view(module) != baseline):
                        raise ValueError('Parent source successor dispatch or input context changed')
                    return verifier

                def replay(root_, **pins):
                    if prefix[0] not in (0, 1) or root_ != root:
                        raise ValueError('two ordered Parent historical prefixes required')
                    index = prefix[0]
                    result = witness._replay_prefix(root_, **pins,
                        _operation=proof, _ticket=ticket, _prefix_index=index)
                    prefix[0] += 1
                    return result

                fresh()
                result = source._prepare(root, **arguments, _check=fresh, _replay=replay)
                fresh()
                if type(result) is not source.ExactSourceCurrent or prefix[0] != 2:
                    raise ValueError('complete predecessor exact source projection required')
                proof._finish(ticket, result.prepared_current.decision,
                    result.source_projection_audit_payload)
                frame['completed_sources'] += 1
                row['source_prepares'] += 1
                check(row, owner)
                return result

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
            if sha256(Path(witness_path).read_bytes()).hexdigest() != witness_pin:
                raise ValueError('Parent arithmetic witness source bytes changed')
            if sys.modules.get(_WITNESS_NAME) is not witness:
                raise ValueError('Parent arithmetic witness module changed')
            if (witness.__spec__ is not witness_definition[0] or witness.__loader__ is not witness_definition[1]
                    or witness.__file__!=witness_definition[2]):
                raise ValueError('Parent arithmetic witness origin or loader changed')
            for original, original_state, fn, fn_state, values in functions:
                if (state(original) != original_state or state(fn) != fn_state
                        or any(fn.__globals__.get(name) is not value for name, value in values)):
                    raise ValueError('fixed Parent functional successor route changed')
            for obj, values in proxies:
                if len(vars(obj)) != len(values) or any(vars(obj).get(name) is not value for name, value in values):
                    raise ValueError('fixed Parent functional successor proxy changed')

        return dict(source=parent_source, inspect=parent_inspect, rebuild=rebuild, check=check_routes,
            declaration=dict(schema=SCHEMA, helper_identity=implementation_identity(),
                arithmetic_witness_source_sha256=witness_pin,
                predecessor_snapshot_implementation=old_snapshot.implementation_identity(),
                predecessor_source_implementation=source.implementation_identity(),
                predecessor_payload_scope='scientific_compatibility_projection_only',
                compatibility_counts_describe_actual_execution=False,
                route=[dict(function=original.__qualname__, file=original.__code__.co_filename)
                    for original, _, _, _, _ in functions]))

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
        key = id(host)
        def expired(reference):
            if completed.get(key, (None,))[0] is reference:completed.pop(key, None)
        try:
            completed[key] = weak_reference(host, expired), _encode(value)
        except BaseException:
            completed[key] = weak_reference(host, expired), failure_bytes
            raise
        finally:
            records.pop(id(row['lease']), None)
            bundles.pop(id(row['bundle']), None)
            row.clear()

    def close_row(row, error=None):
        receipts = []
        failures = []
        # Release all private proof guards even when a report or live dependency
        # is broken. Borrowed Parent/Handoff guards remain the host's property.
        witnesses = tuple(row['witnesses'].values())
        for proof, cleanup in witnesses:
            try:
                if error is not None:proof._poison(error)
            except BaseException as failure:failures.append(failure)
            finally:
                try:cleanup()
                except BaseException as failure:failures.append(failure)
        try:
            for proof, _ in witnesses:
                try:receipts.append(proof.receipt())
                except BaseException as failure:failures.append(failure)
            complete=(error is None and not failures and row['bundle_calls'] == 13
                and row['validations'] == 150 and row['rebuilds'] == 4
                and row['source_prepares'] == 2408 and len(receipts) == 4
                and all(value['complete'] for value in receipts))
            value=dict(schema=SCHEMA, declaration=row['routes']['declaration'],
                parent_validations=row['validations'], bundle_validations=row['bundle_calls'],
                standalone_record_rebuilds=row['rebuilds'], source_prepares=row['source_prepares'],
                full_numerical_hour_replays=sum(v['full_numerical_hour_replays'] for v in receipts),
                reused_numerical_inspections=sum(v['reused_numerical_inspections'] for v in receipts),
                fresh_context_observations=sum(v['context_observations'] for v in receipts),
                parents=receipts, closed=True, validation_checks_complete=complete,
                outer_cleanup_complete=False, complete=False,
                first_failure=None if error is None else repr(error),
                cleanup_errors=[repr(failure) for failure in failures],
                formal_result=False, resource_admission=False, native_execution_authorized=False)
            if error is None and not complete:
                failures.append(ValueError('complete Parent operation counts and proof cleanup required'))
            terminal(row, value)
        except BaseException:
            if row:terminal(row, dict(schema=SCHEMA, closed=True, complete=False,
                formal_result=False, resource_admission=False, native_execution_authorized=False))
            raise
        if failures:
            primary=error or failures[0]
            for failure in failures:
                if failure is not primary:primary.add_note('Parent proof cleanup: '+repr(failure))
            if error is None:raise primary

    def abort_row(row, error):
        if row.get('closed'):return
        row['failure']=repr(error)
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
            proof=row['witnesses'][id(owner)][0]
            if not proof._parent_confirmed:
                frame['kind']='validated'
                proof.activate()
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
        return attach, validate_bundle, rebuild, finish, abort, receipt, commit

    def attach(host, token):
        api, verify, operation, _=require_binding()
        verify(host);saved=operation(host,token);bundle=saved['bundle']
        if id(bundle) in bundles:raise ValueError('Parent validation operation already active')
        pairs=(bundle.reference,*(pair for _,pair in bundle.actuals))
        if any(pair is None for pair in pairs):raise ValueError('complete three-Actual Parent bundle required')
        lease=object.__new__(lease_type)
        row=dict(lease=lease,host=host,token=token,bundle=bundle,reference=bundle.reference,
            actuals=bundle.actuals,guards=tuple(bundle.held),marks=tuple(bundle.marked),
            parents=tuple((obj,issued,obj._raw,obj._issued_bytes,obj._guard) for obj,issued in pairs),
            creator=(pid(),thread()),closed=False,failure=None,frames=[],witnesses={},
            routes=None,validations=0,bundle_calls=0,rebuilds=0,source_prepares=0)
        records[id(lease)]=row;bundles[id(bundle)]=row
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
        try:
            check(row)
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
        try:validate(row,owner,issued)
        except BaseException as error:
            try:abort_row(row,error)
            except BaseException as failure:error.add_note('Parent pair cleanup: '+repr(failure))
            raise

    def rebuild(bundle, owner):
        row=row_for_bundle(bundle);parent=check(row)
        if not any(owner is value[0] for value in row['parents']):
            raise TypeError('original Parent record source required')
        frame=dict(owner=owner,kind='records',completed_sources=0)
        row['frames'].append(frame)
        try:
            if not row['witnesses'][id(owner)][0]._parent_confirmed:
                raise ValueError('complete Parent validation required before records reconstruction')
            result=row['routes']['rebuild'](owner._raw,expected_sha256=parent.io.digest(owner._raw))
            if frame['completed_sources']!=2:raise ValueError('two complete records source reconstructions required')
            row['rebuilds']+=1
            check(row,owner)
            return result
        except BaseException as error:
            try:abort_row(row,error)
            except BaseException as failure:error.add_note('Parent rebuild cleanup: '+repr(failure))
            raise
        finally:
            if row.get('frames') and row['frames'][-1] is frame:row['frames'].pop()

    def receipt(host):
        saved=completed.get(id(host))
        if saved is None or saved[0]() is not host:
            raise ValueError('closed original Parent validation receipt required')
        return json.loads(saved[1])

    def finish(host):
        row=next((row for row in records.values() if row['host'] is host),None)
        if row is None:raise ValueError('original live Parent validation operation required')
        check(row);close_row(row)
        return receipt(host)

    def abort(host,error):
        row=next((row for row in records.values() if row['host'] is host),None)
        if row is not None:
            abort_row(row,error)
        else:
            saved=completed.get(id(host))
            if saved is not None and saved[0]() is host:
                value=json.loads(saved[1])
                value.update(complete=False,outer_failure=repr(error))
                completed[id(host)]=saved[0],_encode(value)

    def commit(host):
        _,_,_,finalized=require_binding()
        value=receipt(host)
        if (not value.get('validation_checks_complete') or value.get('complete')
                or value.get('outer_cleanup_complete')):
            raise ValueError('single pending Parent proof receipt required')
        finalized(host)
        value.update(outer_cleanup_complete=True,complete=True)
        saved=completed[id(host)]
        completed[id(host)]=saved[0],_encode(value)
        return receipt(host)

    return bind,lease_check,parent_confirmed,validate_pair,declaration


_bind_handoff,_lease_check,_parent_confirmed,_validate_pair,_declaration=_build()


def _install_runtime():
    namespace=globals()
    expected=tuple((name,value,value.__code__,repr(value.__defaults__),repr(value.__kwdefaults__))
        for name,value in tuple(namespace.items()) if type(value) is FunctionType)
    constants=(SCHEMA,_HOST,_WITNESS_NAME,_WITNESS_FILE,_WITNESS_SHA256,_Lease)
    def check():
        if ((SCHEMA,_HOST,_WITNESS_NAME,_WITNESS_FILE,_WITNESS_SHA256,_Lease)!=constants
                or any(namespace.get(name) is not fn or fn.__code__ is not code
                    or repr(fn.__defaults__)!=defaults or repr(fn.__kwdefaults__)!=keywords
                    for name,fn,code,defaults,keywords in expected)):
            raise ValueError('definition-time Parent validation operation changed')
    return check


_RUNTIME=_install_runtime()
