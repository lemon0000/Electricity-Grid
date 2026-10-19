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
from experiments import h1_reference_validation_routes_development_v1 as reference_routes
from experiments import h1_validation_runtime_closure_development_v1 as runtime_closure

SCHEMA = 'h1_selector_parent_validation_operation_development_v4'
_HOST = 'experiments.h1_selector_phase_handoff_development_v6'
EXPECTED_WINDOWS = dict(bundle=13, records_bundle=1)
EXPECTED_SOURCE_REQUESTS = 2408

def implementation_identity():
    return sha256(_encode([SCHEMA, sha256(Path(__file__).read_bytes()).hexdigest(), EXPECTED_WINDOWS, EXPECTED_SOURCE_REQUESTS,reference_routes.implementation_identity()])).hexdigest()

def _encode(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode('ascii')

def _source_signature(value):

    def stable(item):
        kind = type(item)
        if kind in (str, int, bool, type(None)):
            return [kind.__name__, item]
        if kind is float:
            return ['float', item.hex()]
        if kind is bytes:
            return ['bytes', item.hex()]
        if isinstance(item, Fraction):
            return ['fraction', item.numerator, item.denominator]
        if is_dataclass(item):
            return ['dataclass', kind.__module__, kind.__qualname__, [[field.name, stable(getattr(item, field.name))] for field in fields(item)]]
        if kind in (tuple, list):
            return [kind.__name__, [stable(v) for v in item]]
        if kind is dict:
            return ['dict', sorted([[stable(k), stable(v)] for k, v in item.items()], key=repr)]
        if kind in (set, frozenset):
            return [kind.__name__, sorted([stable(v) for v in item], key=repr)]
        raise TypeError('complete literal source fields required: ' + str(kind))
    return sha256(_encode(stable(value))).hexdigest()

def _source_types(value):
    """Keep actual class objects, including every nested dataclass/container."""
    rows = []

    def visit(item):
        kind = type(item)
        if is_dataclass(item):
            names = tuple((field.name for field in fields(item)))
            rows.append((kind, names))
            for name in names:
                visit(getattr(item, name))
        elif kind is dict:
            rows.append((kind, len(item)))
            for key, part in sorted(item.items(), key=lambda pair: repr(pair[0])):
                visit(key)
                visit(part)
        elif kind in (tuple, list, set, frozenset):
            rows.append((kind, len(item)))
            for part in sorted(item, key=repr) if kind in (set, frozenset) else item:
                visit(part)
        else:
            rows.append((kind, None))
    visit(value)
    return tuple(rows)

def _capture_source_guard(module):
    """Preserve the predecessor _guard_prepare dispatch checklist, without executing it."""
    historical = module.historical
    names = ('historical', 'predecessor', 'origin_join', 'normal', 'source', 'registry', 'physical', 'io', 'json', 'asdict', 'SCHEMA', 'PROJECTION_SCHEMA', 'CFE_RULE', '_envelope', '_project', '_ratio', '_prepare', 'ExactSourceCurrent', 'CommonSourceBundle', '_historical_projection', 'implementation_identity', '_guard_prepare', '_build_entries', 'prepare', 'prepare_common_bundle')
    own = tuple(((module, name, getattr(module, name)) for name in names))
    verifier_names = ('_replay_prefix', 'verifier_identity', '_observe_sources', 'legacy', 'witness', 'old', 'history', 'current', 'io', 'binding', 'bridge', 'base', '_observe', '_observe_prefix', '_obligation_inventory', 'implementation_identity', 'VERIFIER_SCHEMA')
    verifier = tuple(((historical, name, getattr(historical, name)) for name in verifier_names))
    dependencies = ((module.source, ('load_pinned_current', 'validate_pinned_current')), (module.registry, ('prepare',)), (module.origin_join, ('_join', 'implementation_identity')), (module.predecessor, ('implementation_identity',)), (module.origin_join.predecessor, ('_coordinates',)), (module.normal, ('_owned', '_decision')), (module.physical, ('_digest',)), (module.io, ('encode', 'digest', 'pin')), (module.source.h1.workload_projection, ('project_workload_power',)), (historical.old, ('additional_content_bound',)), (historical.binding.replay, ('request_key',)), (historical.history.prior, ('Rq2SolverSpec',)), (historical.history.replay, ('H1HourReplayLimits',)), (historical.history.prior.Rq2SolverSpec, ('__init__',)), (historical.history.replay.H1HourReplayLimits, ('__init__', '__post_init__')), (module.json, ('loads',)), (historical.history.replay.guard, ('solver_calls_forbidden',)), (historical.witness, ('_dispatch_view',)), (historical.binding, ('CAP',)))
    entries = own + verifier + tuple(((obj, name, getattr(obj, name)) for obj, fields in dependencies for name in fields))
    codes = tuple(((value, value.__code__, repr(value.__defaults__), repr(value.__kwdefaults__)) for _, _, value in entries if type(value) is FunctionType))
    closures = tuple(((value, value.__closure__, tuple((cell.cell_contents for cell in value.__closure__ or ()))) for value in (module.prepare, module.prepare_common_bundle)))

    def fixed():
        if any((getattr(obj, name) is not value for obj, name, value in entries)) or any((value.__code__ is not code or repr(value.__defaults__) != defaults or repr(value.__kwdefaults__) != keywords for value, code, defaults, keywords in codes)) or any((value.__closure__ is not cells or any((cell.cell_contents is not original for cell, original in zip(cells or (), contents))) for value, cells, contents in closures)):
            raise ValueError('predecessor exact-source dispatch checklist changed')
    return fixed

def _build(runtime):
    records = {}
    bundles = {}
    completed = {}
    binding = None
    module = sys.modules[__name__]
    pid, thread = (os.getpid, get_ident)
    copy = deepcopy
    weak_reference = weakref.ref
    failure_bytes = _encode(dict(schema=SCHEMA, closed=True, complete=False, formal_result=False, resource_admission=False, native_execution_authorized=False))

    def state(value):
        return (value.__code__, repr(value.__defaults__), repr(value.__kwdefaults__)) if type(value) is FunctionType else None

    def require_binding():
        runtime()
        if binding is None:
            raise ValueError('original Handoff Parent validation anchor is not bound')
        api, kind, verify, operation, finalized, host_path, host_pin, fixed = binding
        if sys.modules.get(_HOST) is not api or api.Handoff is not kind or api.__file__ != host_path or (sha256(Path(host_path).read_bytes()).hexdigest() != host_pin) or any((state(fn) != original for fn, original in fixed)):
            raise ValueError('original Parent validation host changed')
        return (api, verify, operation, finalized)

    def row_for_bundle(bundle):
        row = bundles.get(id(bundle))
        if row is None or row['bundle'] is not bundle:
            raise ValueError('original borrowed Parent bundle required')
        return row

    def admit_creator(row):
        if records.get(id(row['bundle'])) is not row or bundles.get(id(row['bundle'])) is not row or row['creator'] != (pid(), thread()) or row['closed']:
            raise ValueError('original Parent validation creating thread required')

    def admit_completed(host):
        saved = completed.get(id(host))
        if saved is None or saved[0]() is not host or saved[2] != (pid(), thread()):
            raise ValueError('original Parent receipt creating thread required')
        return saved

    def admit_operation(row):
        admit_creator(row)
        if row['window'] is not None:
            error = ValueError('Parent validation window is nonreentrant')
            if row['failure'] is None:
                row['failure'] = repr(error)
            raise error

    def check(row, owner=None, *, borrowed=False):
        api, verify, operation, _ = require_binding()
        if records.get(id(row['bundle'])) is not row or bundles.get(id(row['bundle'])) is not row or row['creator'] != (pid(), thread()) or row['closed'] or (row['failure'] is not None):
            raise ValueError('Parent validation operation lifetime changed')
        verify(row['host'])
        saved = operation(row['host'], row['token'])
        bundle = row['bundle']
        if saved['bundle'] is not bundle or bundle.reference is not row['reference'] or bundle.actuals is not row['actuals'] or (len(bundle.held) != len(row['guards'])) or any((a is not b for a, b in zip(bundle.held, row['guards']))) or (len(bundle.marked) != len(row['marks'])) or any((a is not b for a, b in zip(bundle.marked, row['marks']))):
            raise ValueError('original held Parent guards, marks or pairs changed')
        parent = api.parent
        # Nested source dispatch can be inside the original solver-denial
        # context; its temporary bindings are verified after outer dispatch.
        if not borrowed:parent._CHECK()
        for obj, receipt, raw, issued, guard in row['parents']:
            if type(obj) is not parent.Parent or type(receipt) is not parent.ParentCompletion or obj._raw is not raw or (obj._issued is not receipt) or (obj._issued_bytes != issued) or (parent._completion_bytes(receipt) != issued) or (obj._guard is not guard) or (not guard.locked()):
                raise ValueError('exact original Parent, receipt, snapshot and guard required')
        guards = tuple((part[4] for part in row['parents'][1:])) + (row['parents'][0][4],)
        marks = tuple((part[0] for part in row['parents'][1:]))
        if len(row['guards']) != len(guards) or any((a is not b for a, b in zip(row['guards'], guards))) or len(row['marks']) != len(marks) or any((a is not b for a, b in zip(row['marks'], marks))) or any((mark._reference_held is not True for mark in marks)):
            raise ValueError('exact original Parent guard and mark inventory required')
        if owner is not None:
            if not row['frames'] or row['frames'][-1]['owner'] is not owner:
                raise ValueError('original current Parent validation site required')
        if row['routes'] is not None:
            row['routes']['check']()
        return parent

    def clone(function, **changes):
        namespace = dict(function.__globals__)
        namespace.update(changes)
        result = FunctionType(function.__code__, namespace, function.__name__, function.__defaults__, function.__closure__)
        result.__kwdefaults__ = copy(function.__kwdefaults__)
        return result

    def routes(row,parent):
        return reference_routes._make_routes(row,parent,check,parent._WINDOWS.raw_source,parent._WINDOWS.raw_inspect,
            family='parent_validation',enable_reference=row['window'] is not None,
            consumer_schema=SCHEMA,consumer_identity=implementation_identity(),
            capture_source_guard=_capture_source_guard,
            scope_code=source_window.__wrapped__.__code__,scope_globals=source_window.__wrapped__.__globals__)

    def declaration(bundle):
        runtime()
        row = row_for_bundle(bundle)
        check(row)
        return dict(row['routes']['declaration'], parents=[dict(root=str(obj.root), issued_completion_sha256=sha256(issued).hexdigest(), snapshot_sha256=sha256(raw).hexdigest(), source_binding=json.loads(raw)['declaration']['source_binding']) for obj, _, raw, issued, _ in row['parents']])

    def terminal(row, value):
        host = row['host']
        creator = row['creator']
        key = id(host)

        def expired(reference):
            if completed.get(key, (None,))[0] is reference:
                completed.pop(key, None)
        try:
            completed[key] = (weak_reference(host, expired), _encode(value), creator)
        except BaseException:
            completed[key] = (weak_reference(host, expired), failure_bytes, creator)
            raise
        finally:
            records.pop(id(row['bundle']), None)
            bundles.pop(id(row['bundle']), None)
            row.clear()

    def close_row(row, error=None):
        active = row['window']
        if active is not None:
            active.clear()
            row['window'] = None
        complete = error is None and row['bundle_calls'] == 13 and (row['validations'] == 150) and (row['rebuilds'] == 4) and (row['source_requests'] == EXPECTED_SOURCE_REQUESTS) and (row['source_prepares'] == 28) and (row['window_counts'] == EXPECTED_WINDOWS) and (len(row['windows']) == 14) and (row['records_bundle_calls'] == 1) and (row['record_edge'] == 12) and all((row['pair_sites'][id(owner)] == 2 and row['record_sites'][id(owner)] == 1 for owner, *_ in row['parents']))
        reference_receipts=[item['reference_window'] for item in row['windows']]
        complete=complete and all(item['cache_cleared'] and item['original_reference_inspects']==2
                                  for item in reference_receipts)
        complete=complete and sum(item['logical_reference_inspects'] for item in reference_receipts)==726
        complete=complete and sum(item['original_reference_inspects'] for item in reference_receipts)==28
        incomplete = error is None and (not complete)
        if incomplete:
            error = ValueError('complete Parent windows, source counts and cleanup required')
        value = dict(schema=SCHEMA, declaration=None if row['routes'] is None else row['routes']['declaration'], parent_validations=row['validations'], bundle_validations=row['bundle_calls'], records_bundle_rebuilds=row['rebuilds'], source_requests=row['source_requests'], source_prepares=row['source_prepares'], source_windows=row['windows'], source_window_counts=row['window_counts'], parent_sites=[dict(root=str(owner.root), issued_completion_sha256=sha256(issued).hexdigest(), pair_validation_sites=row['pair_sites'][id(owner)], record_rebuild_sites=row['record_sites'][id(owner)]) for owner, _, _, issued, _ in row['parents']], full_numerical_hour_replays=4 * row['source_prepares'], reused_numerical_inspections=0, within_prefix_numerical_revalidations=4 * row['source_prepares'], fresh_context_observations=16 * row['source_prepares'], borrowed_source_returns=row['source_requests'], source_window_cache_cleared=row['window'] is None, closed=True, validation_checks_complete=complete, status='pending' if complete else 'aborted', outer_cleanup_complete=False, complete=False, first_failure=row['failure'] or (None if error is None else repr(error)), cleanup_errors=[], formal_result=False, resource_admission=False, native_execution_authorized=False)
        value.update(reference_logical_inspects=sum(item['logical_reference_inspects'] for item in reference_receipts),
                     reference_original_inspects=sum(item['original_reference_inspects'] for item in reference_receipts),
                     reference_borrowed_results=sum(item['borrowed_reference_results'] for item in reference_receipts))
        terminal(row, value)
        if incomplete:
            raise error

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

    def abort_row(row, error):
        if not row or row.get('closed'):
            return
        if row['failure'] is None:
            row['failure'] = repr(error)
        close_row(row, error)

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

    def bind(api, owner_type, verify, operation, finalized):
        nonlocal binding
        runtime()
        if binding is not None or api.__name__ != _HOST or api.Handoff is not owner_type:
            raise ValueError('one original Handoff Parent anchor required')
        binding = (api, owner_type, verify, operation, finalized, api.__file__, sha256(Path(api.__file__).read_bytes()).hexdigest(), tuple(((fn, state(fn)) for fn in (verify, operation, finalized))))
        runtime()
        return (attach, validate_bundle, rebuild, finish, abort, receipt, commit, validate_pair, declaration, records_bundle)

    def attach(host, token):
        api, verify, operation, _ = require_binding()
        previous = completed.get(id(host))
        if previous is not None and previous[0]() is host:
            raise ValueError('Parent validation operation already finalized for this Handoff')
        verify(host)
        saved = operation(host, token)
        bundle = saved['bundle']
        if id(bundle) in bundles:
            raise ValueError('Parent validation operation already active')
        pairs = (bundle.reference, *(pair for _, pair in bundle.actuals))
        if any((pair is None for pair in pairs)):
            raise ValueError('complete three-Actual Parent bundle required')
        source_binding = json.loads(pairs[0][0]._raw)['declaration']['source_binding']
        if any((json.loads(obj._raw)['declaration']['source_binding'] != source_binding for obj, _ in pairs)):
            raise ValueError('one canonical source binding for the complete Parent bundle required')
        row = dict(host=host, token=token, bundle=bundle, reference=bundle.reference, actuals=bundle.actuals, guards=tuple(bundle.held), marks=tuple(bundle.marked), parents=tuple(((obj, issued, obj._raw, obj._issued_bytes, obj._guard) for obj, issued in pairs)), creator=(pid(), thread()), closed=False, failure=None, frames=[], window=None, source_binding=copy(source_binding), routes=None, validations=0, bundle_calls=0, rebuilds=0, source_prepares=0, source_requests=0, windows=[], window_counts=dict(bundle=0, records_bundle=0), records_bundle_calls=0, record_edge=0, pair_sites={id(obj): 0 for obj, _ in pairs}, record_sites={id(obj): 0 for obj, _ in pairs})
        records[id(bundle)] = row
        bundles[id(bundle)] = row
        try:
            parent = check(row)
            row['routes'] = routes(row, parent)
            check(row)
        except BaseException as error:
            try:
                abort_row(row, error)
            except BaseException as failure:
                error.add_note('Parent attach cleanup: ' + repr(failure))
            raise

    def validate_bundle(bundle):
        runtime()
        row = row_for_bundle(bundle)
        admit_operation(row)
        try:
            check(row)
            with source_window(row, 'bundle'):
                validate(row, *bundle.reference)
                for _, pair in bundle.actuals:
                    validate(row, *pair)
            row['bundle_calls'] += 1
            if row['bundle_calls'] > 13:
                raise ValueError('Parent bundle validation count exceeded')
            check(row)
        except BaseException as error:
            try:
                abort_row(row, error)
            except BaseException as failure:
                error.add_note('Parent validation cleanup: ' + repr(failure))
            raise

    def require_record_edge(row, owner, kind):
        check(row)
        window = row['window']
        if window is None or window['kind'] != 'records_bundle':
            raise ValueError('original complete records window required')
        order = tuple(((part, obj) for obj, *_ in row['parents'] for part in ('pair', 'rebuild', 'pair')))
        if row['record_edge'] >= len(order) or order[row['record_edge']] != (kind, owner):
            raise ValueError('original canonical Parent records edge required')

    @contextmanager
    def records_bundle(bundle):
        runtime()
        row = row_for_bundle(bundle)
        admit_operation(row)
        try:
            if row['records_bundle_calls'] or row['record_edge']:
                raise ValueError('single records bundle required')
            with source_window(row, 'records_bundle'):
                yield
                check(row)
                if row['record_edge'] != 12 or row['rebuilds'] != 4 or any((row['pair_sites'][id(obj)] != 2 or row['record_sites'][id(obj)] != 1 for obj, *_ in row['parents'])):
                    raise ValueError('all twelve canonical records edges required')
            row['records_bundle_calls'] += 1
        except BaseException as error:
            try:
                abort_row(row, error)
            except BaseException as failure:
                error.add_note('Parent records cleanup: ' + repr(failure))
            raise

    def validate_pair(bundle, owner, issued):
        runtime()
        row = row_for_bundle(bundle)
        admit_creator(row)
        try:
            require_record_edge(row, owner, 'pair')
            if not any((owner is obj and issued is receipt for obj, receipt, *_ in row['parents'])):
                raise TypeError('original Parent pair required before source work')
            validate(row, owner, issued)
            row['pair_sites'][id(owner)] += 1
            row['record_edge'] += 1
        except BaseException as error:
            try:
                abort_row(row, error)
            except BaseException as failure:
                error.add_note('Parent pair cleanup: ' + repr(failure))
            raise

    def rebuild(bundle, owner):
        runtime()
        row = row_for_bundle(bundle)
        admit_creator(row)
        try:
            parent = check(row)
            require_record_edge(row, owner, 'rebuild')
            frame = dict(owner=owner, kind='records', completed_sources=0)
            row['frames'].append(frame)
            try:
                result = row['routes']['rebuild'](owner._raw, expected_sha256=parent.io.digest(owner._raw))
                if frame['completed_sources'] != 2:
                    raise ValueError('two complete records source requests required')
                check(row, owner)
            finally:
                if row.get('frames') and row['frames'][-1] is frame:
                    row['frames'].pop()
            row['rebuilds'] += 1
            row['record_sites'][id(owner)] += 1
            row['record_edge'] += 1
            return result
        except BaseException as error:
            try:
                abort_row(row, error)
            except BaseException as failure:
                error.add_note('Parent rebuild cleanup: ' + repr(failure))
            raise

    def receipt(host):
        saved = admit_completed(host)
        return json.loads(saved[1])

    def finish(host):
        runtime()
        row = next((row for row in records.values() if row['host'] is host), None)
        if row is None:
            raise ValueError('original live Parent validation operation required')
        admit_operation(row)
        try:
            check(row)
            close_row(row)
            return receipt(host)
        except BaseException as error:
            try:
                abort_row(row, error)
            except BaseException as failure:
                error.add_note('Parent finish cleanup: ' + repr(failure))
            raise

    def abort(host, error):
        row = next((row for row in records.values() if row['host'] is host), None)
        if row is not None:
            admit_creator(row)
            abort_row(row, error)
        else:
            saved = completed.get(id(host))
            if saved is not None and saved[0]() is host:
                admit_completed(host)
                value = json.loads(saved[1])
                if value.get('status') != 'aborted':
                    value.update(complete=False, validation_checks_complete=False, status='aborted', outer_failure=repr(error))
                    completed[id(host)] = (saved[0], _encode(value), saved[2])

    def commit(host):
        runtime()
        _, _, _, finalized = require_binding()
        admit_completed(host)
        value = receipt(host)
        if value.get('status') != 'pending' or not value.get('validation_checks_complete') or value.get('complete') or value.get('outer_cleanup_complete') or (value.get('first_failure') is not None) or (value.get('outer_failure') is not None):
            raise ValueError('single pending Parent proof receipt required')
        finalized(host)
        value.update(outer_cleanup_complete=True, complete=True, status='committed')
        saved = completed[id(host)]
        completed[id(host)] = (saved[0], _encode(value), saved[2])
        return receipt(host)
    return bind

def _initialize_runtime():
    namespace = globals()
    runtime, arm = runtime_closure.make_runtime(namespace, 'Parent validation operation')
    namespace['_RUNTIME'] = runtime
    bind = _build(runtime)
    namespace['_bind_handoff'] = bind
    arm(transitions=((runtime_closure._cell(bind, 'binding'), 'binding', bind),),
        ignored=('_initialize_runtime',))


_initialize_runtime()
del _initialize_runtime
