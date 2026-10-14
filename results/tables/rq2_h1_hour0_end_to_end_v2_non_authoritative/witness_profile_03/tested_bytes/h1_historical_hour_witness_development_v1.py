"""Private read-only numerical witness, limited to one N0 prefix reader.

Every use revalidates the complete hour byte/identity view and dynamic context.
This is a versioned validation contract, not a live execution credential.
It does not isolate arbitrary Python reflection or unobservable file ABA.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import sys
import threading
import types

from experiments import h1_timed_job_parent_development_v1 as parent
from experiments import h1_job_clock_bridge_development_v1 as bridge
from experiments import h1_phase_dependency_verifier_development_v1 as bounded

worker, hour, io = parent.worker, parent.worker.hour, parent.io
SCHEMA = 'h1_historical_hour_witness_development_v1'
MAX_PROJECT_FILES = 2048
MAX_SOURCE_BYTES = 256 * 1024**2
MAX_BINDINGS = 100000


def _solver_guard_view():
    guard = hour.prior.guard
    endpoints = ((type(guard.SolverFactory), '__call__'), (guard.current, 'solve_current'),
        (guard.current.native, 'run_h1_chain'), (guard.current.native.capture, 'solve_once'),
        (guard.current.native.capture.provenance.adapter, 'create_solver'))
    functions = tuple(getattr(owner, name) for owner, name in endpoints)
    code = next(c for c in guard.solver_calls_forbidden.__wrapped__.__code__.co_consts
                if isinstance(c, types.CodeType) and c.co_name == 'denied')
    fn = functions[0]
    if (type(fn) is not types.FunctionType or any(f is not fn for f in functions)
            or fn.__code__ is not code or fn.__globals__ is not vars(guard)
            or len(fn.__closure__ or ()) != 1 or type(fn.__closure__[0].cell_contents) is not list
            or fn.__closure__[0].cell_contents):
        raise ValueError('exact active solver denial required')
    return fn, code


def _freeze(value):
    if type(value) in (str, int, bool, type(None)):
        return (type(value).__name__, value)
    if type(value) is float:
        return ('float', value.hex())
    if type(value) is bytes:
        return ('bytes', value)
    if type(value) in (tuple, list):
        return (type(value).__name__, tuple(_freeze(v) for v in value))
    if type(value) in (set, frozenset):
        return (type(value).__name__, tuple(sorted((_freeze(v) for v in value), key=repr)))
    if type(value) is dict:
        return ('dict', tuple(sorted(((_freeze(k), _freeze(v)) for k, v in value.items()), key=repr)))
    raise TypeError('nonliteral context')


def _dispatch_view():
    """Observe project module edges, direct callables/classes and literal constants.

    Imported vendor internals are checked by the original validate_vendor call.
    Python reflection that mutates arbitrary third-party object graphs is outside
    this contract, as is an unobserved change-and-restore between observations.
    """
    pending = [sys.modules[__name__], hour, parent, bridge]
    denied, denial_code = _solver_guard_view()
    seen = set(); rows = []; files = []; total = 0
    while pending:
        module = pending.pop()
        if id(module) in seen:
            continue
        seen.add(id(module))
        if len(seen) > MAX_PROJECT_FILES:
            raise ValueError('project source file bound exceeded')
        path = Path(module.__file__)
        raw, stamp = bounded.read_stable(path, 2 * 1024**2)
        total += len(raw)
        if total > MAX_SOURCE_BYTES:
            raise ValueError('project source byte bound exceeded')
        files.append((module.__name__, str(path), io.digest(raw), stamp))
        for name, value in sorted(vars(module).items()):
            if len(rows) >= MAX_BINDINGS:
                raise ValueError('project dispatch bound exceeded')
            if name.startswith('__'):
                continue
            key = (module.__name__, name)
            if isinstance(value, types.ModuleType):
                rows.append((key, 'module', id(value)))
                if value.__name__.startswith(('experiments.', 'src.')) and hasattr(value, '__file__'):
                    pending.append(value)
            elif isinstance(value, types.FunctionType):
                if value is denied:
                    rows.append((key, 'solver_denied', id(denial_code)))
                else:
                    rows.append((key, 'function', id(value), id(value.__code__),
                                 repr(value.__defaults__), repr(value.__kwdefaults__)))
                origin = sys.modules.get(value.__module__)
                if origin is not None and origin.__name__.startswith(('experiments.', 'src.')):
                    pending.append(origin)
            elif isinstance(value, type):
                methods = []
                if value.__module__.startswith(('experiments.', 'src.')):
                    pending.append(sys.modules[value.__module__])
                    for method, obj in sorted(vars(value).items()):
                        if isinstance(obj, property):
                            methods.append((method, 'property', id(obj), id(obj.fget), id(obj.fset)))
                        obj = obj.__func__ if isinstance(obj, (staticmethod, classmethod)) else obj
                        if isinstance(obj, types.FunctionType):
                            methods.append((method, id(obj), id(obj.__code__),
                                            repr(obj.__defaults__), repr(obj.__kwdefaults__)))
                rows.append((key, 'type', id(value), tuple(methods)))
            elif callable(value):
                rows.append((key, 'callable', id(value)))
            elif name.isupper() or name in ('_FILES',):
                try:
                    literal = _freeze(value)
                except TypeError:
                    literal = ('object', id(value))
                rows.append((key, 'constant', literal))
    return tuple(sorted(rows)), tuple(sorted(files))


def implementation_identity():
    return io.digest(io.encode([SCHEMA, io.digest(Path(__file__).read_bytes()),
                               hour.implementation_identity(), parent.implementation_identity(),
                               bridge.implementation_identity()]))


@dataclass(frozen=True)
class RevalidatedChildInspection:
    status: str
    head: str
    archive_identity: str
    stored_reports: int
    projection: parent.Projection


class _HourScope:
    """No caller result injection and no reuse beyond a single prefix Reader."""
    def __init__(self, root, leases):
        self._root = Path(root).absolute()
        self._original_root = self._root
        self._leases = tuple(leases)
        if len(self._leases) != 4:
            raise ValueError('four live prefix views required')
        self._lease_ids = tuple(id(v) for v in self._leases)
        self._owner = os.getpid(), threading.get_ident()
        self._nonce = self._original_nonce = object()
        self._closed = self._poisoned = self._promoted = False
        self._baseline = self._value = None
        self.full_calls = self.revalidation_calls = 0
        with hour.prior.guard.solver_calls_forbidden():
            self._dispatch = _dispatch_view()

    def _check(self):
        if (self._closed or self._poisoned or self._owner != (os.getpid(), threading.get_ident())
                or self._nonce is not self._original_nonce
                or self._root != self._original_root
                or tuple(id(v) for v in self._leases) != self._lease_ids):
            raise ValueError('numerical witness lifetime changed')
        for lease in self._leases:
            lease.check()

    def _context(self, root, packet, specification, limits, pins):
        self._check()
        dispatch = _dispatch_view()
        if dispatch != self._dispatch:
            raise ValueError('numerical witness dispatch or source changed')
        expected = self._root / 'job_000_non_authoritative/worker_non_authoritative/hour_non_authoritative'
        if Path(root).absolute() != expected or expected.resolve() != expected or packet.relative_hour != 0:
            raise ValueError('N0 witness root/hour differs')
        # This validates the full current input, dependency files and package versions.
        key = hour.request_key(packet, specification, limits)
        count = len(hour.prior.native.model_api.stage_order(packet.inputs))
        if not 1 <= count <= 232:
            raise ValueError('bounded complete stage inventory required')
        hour.stage.capture.timing.validate_vendor()
        hour.prior.generation_projection._frozen_thresholds()
        source = hour.prior.current.source
        packet_view = (source._digest(packet.network, packet.before, packet.inputs),
            packet.input_identity, packet.audit_identity, packet.relative_hour,
            packet.source_timestamp, packet.source_time_basis, packet.workload_projection_payload)
        result = (str(expected), key, packet_view, _freeze(asdict(specification)), _freeze(asdict(limits)),
                  _freeze(pins), hour.implementation_identity(), dispatch, hour._snapshot(expected, count, True))
        self._check()
        return result

    def inspect(self, root, packet, specification, limits, **pins):
        with hour.prior.guard.solver_calls_forbidden():
            return self._inspect(root, packet, specification, limits, **pins)

    def _inspect(self, root, packet, specification, limits, **pins):
        try:
            before = self._context(root, packet, specification, limits, pins)
            if self._baseline is not None and before != self._baseline:
                changed = [i for i, (left, right) in enumerate(zip(self._baseline, before)) if left != right]
                details = ''
                if 7 in changed:
                    left = {row[0]: row[1:] for row in self._baseline[7][0]}
                    right = {row[0]: row[1:] for row in before[7][0]}
                    details = repr([key for key in left.keys() | right.keys() if left.get(key) != right.get(key)][:8])
                raise ValueError('numerical witness input changed: '+repr(changed)+' '+details)
            if not self._promoted:
                if self.full_calls >= 2:
                    raise ValueError('unconfirmed numerical witness cannot be reused')
                result = hour.inspect(root, packet, specification, limits, **pins)
                self.full_calls += 1
                frozen = _freeze(result)
                if self._value is not None and frozen != self._value[0]:
                    raise ValueError('independent full numerical results differ')
                self._value = frozen, deepcopy(result)
            else:
                if self.full_calls != 2 or self.revalidation_calls >= 2:
                    raise ValueError('numerical witness use count exceeded')
                if _freeze(self._value[1]) != self._value[0]:
                    raise ValueError('retained numerical result changed')
                result = deepcopy(self._value[1])
                # Report exactly what happened at this boundary.
                result['full_hour_chain_recomputed'] = False
                self.revalidation_calls += 1
            after = self._context(root, packet, specification, limits, pins)
            if after != before:
                raise ValueError('numerical witness inputs changed during use')
            self._baseline = before
            return result
        except BaseException:
            self._poisoned = True
            self._value = self._baseline = None
            raise

    def promote(self, result):
        self._check()
        if (type(result) is not RevalidatedChildInspection or self.full_calls != 2
                or self._value is None or result.projection.payload != self._value[1]['projection_payload']):
            raise ValueError('complete accepted child required before witness promotion')
        self._promoted = True

    def close(self):
        self._closed = True
        self._nonce = None
        self._baseline = self._value = None

    def __copy__(self):
        raise TypeError('private numerical witness cannot be copied')

    def __deepcopy__(self, memo):
        raise TypeError('private numerical witness cannot be copied')

    def __reduce_ex__(self, protocol):
        raise TypeError('private numerical witness cannot be serialized')


class ChildReference(parent.ChildReference):
    def __init__(self, *args, scope, **kwargs):
        self._scope = scope
        super().__init__(*args, **kwargs)

    def inspect(self):
        if self.closed:
            raise ValueError('closed revalidated child reference')
        self._scope._check()
        topology = hour._directory(self.root, {'reference.json'})
        doc, view = parent.prior.read(self.root / 'reference.json', self.head)
        packet, specification, limits = self.context
        expected = parent.reference(self.root, self.job_root, self.parent, self.intent, self.lineage, doc['job_pins'])
        if not io.same(doc, expected):
            raise ValueError('child reference context differs')
        payload = inspect_job(self.job_root, *self.context, pins=doc['job_pins'],
            parent_declaration=self.parent, intent_head=self.intent, lineage=self.lineage, scope=self._scope)
        if (io.read_stable(self.root / 'reference.json', parent.prior.CAP) != view
                or hour._directory(self.root, {'reference.json'}) != topology):
            raise ValueError('child reference changed')
        projection = parent.Projection(io.digest(io.encode([parent.CHILD_SCHEMA, io.digest(payload)])), payload)
        self._scope._check()
        return RevalidatedChildInspection('accepted', self.head, self.head,
            len(hour.prior.native.model_api.stage_order(packet.inputs)), projection)


def inspect_worker(root, packet, specification, limits, *, expected_binding_sha, expected_terminal_sha, expected_implementation, scope):
    """Conditional complete-hour replay, not proof of live clock/Job membership."""
    for pin in (expected_binding_sha, expected_terminal_sha, expected_implementation):
        io.pin(pin)
    if worker.implementation_identity() != expected_implementation:
        raise ValueError('worker implementation differs')
    root = Path(root).absolute()
    identity = worker._root(root)
    binding, bv = worker._read(root / 'binding.json')
    terminal, tv = worker._read(root / 'terminal.json')
    if io.digest(bv[0]) != expected_binding_sha or io.digest(tv[0]) != expected_terminal_sha:
        raise ValueError('external worker pin differs')
    if set(binding) != {'schema', 'implementation', 'hour_request_sha256', 'controller_request_sha256', 'pid', 'creation_filetime', 'thread_id', 'clock', 'start_ns', *worker.FLAGS} or binding['schema'] != worker.SCHEMA or binding['implementation'] != expected_implementation or (binding['hour_request_sha256'] != hour.request_key(packet, specification, limits)) or (binding['clock'] != worker.clock_profile()) or any((binding[k] is not False for k in worker.FLAGS)):
        raise ValueError('worker binding differs')
    io.pin(binding['controller_request_sha256'])
    if worker._integer(binding['creation_filetime']) == 0:
        raise ValueError('process creation identity required')
    if set(terminal) != {'schema', 'binding_sha256', 'end_ns', 'hour_terminal_sha256', 'interval_vector_sha256', 'native_total_ns', 'worker_window_non_native_ns', *worker.FLAGS} or terminal['schema'] != worker.SCHEMA or terminal['binding_sha256'] != expected_binding_sha or any((terminal[k] is not False for k in worker.FLAGS)):
        raise ValueError('worker terminal differs')
    count = len(hour.prior.native.model_api.stage_order(packet.inputs))
    rows, views = worker._intervals(root / 'hour_non_authoritative', count)
    full_view = hour._snapshot(root / 'hour_non_authoritative', count, True)
    result = scope.inspect(root / 'hour_non_authoritative', packet, specification, limits, expected_terminal_sha=terminal['hour_terminal_sha256'], expected_implementation=hour.implementation_identity())
    values = worker.analyse_intervals(rows, count=count, pid=binding['pid'], thread_id=binding['thread_id'], start=binding['start_ns'], end=terminal['end_ns'])
    if io.digest(io.encode(rows)) != terminal['interval_vector_sha256'] or worker._integer(terminal['native_total_ns']) != values['native_total_ns'] or result['native_total_ns'] != values['native_total_ns'] or (worker._integer(terminal['worker_window_non_native_ns']) != values['worker_window_non_native_ns']):
        raise ValueError('worker native total/vector differs')
    views.update({root / 'binding.json': bv, root / 'terminal.json': tv})
    worker._unchanged(views)
    if hour._snapshot(root / 'hour_non_authoritative', count, True) != full_view or worker._root(root) != identity or worker.implementation_identity() != expected_implementation:
        raise ValueError('worker root/implementation changed')
    return dict(values, projection_payload=result['projection_payload'], interval_vector_sha256=terminal['interval_vector_sha256'], clock_source_authenticated=False, owned_run_return_observed=False, confirmation_tail_ns=None, **worker.FLAGS)


def inspect_job(root, packet, specification, limits, *, pins, parent_declaration, intent_head, lineage, scope):
    """Zero-solver conditional replay under external pins; no live receipt."""
    if type(pins) is not dict or set(pins) != set(parent.RECORDS):
        raise ValueError('complete Job pins required')
    root = parent.old.bounded.chunks.base.local._path(root)
    topology = worker.hour._directory(root, set(parent.RECORDS) | {'execution.lock', 'scratch_non_authoritative', 'worker_non_authoritative'})
    views, docs = ({}, {})
    lock_view = io.identity(root / 'execution.lock')
    if lock_view[2] != 1:
        raise ValueError('one-byte Job lock required')
    for name in parent.RECORDS:
        docs[name], view = parent.prior.read(root / name, pins[name])
        views[root / name] = (parent.prior.CAP, view)
    req, launch, child, release, consume, result, observed = (docs[n] for n in ('request.json', 'launch.json', 'child.json', 'release_intent.json', 'consumed.json', 'worker_result.json', 'observation.json'))
    expected_parent = io.digest(io.encode(parent_declaration))
    args = dict(expected_head=intent_head, expected_source_identity=lineage, expected_request_key=parent.replay.request_key(packet, specification, limits), expected_packet_audit=packet.audit_identity)
    anchor_path = Path(parent_declaration['root']) / 'parent_anchor_non_authoritative' / f'{2 * packet.relative_hour + 1:03d}.json'
    anchor_view = io.read_stable(anchor_path, parent.old.snapshot.anchor.MAX_RECORD_BYTES)
    anchor_pin = io.digest(anchor_view[0])
    views[anchor_path] = (parent.old.snapshot.anchor.MAX_RECORD_BYTES, anchor_view)
    if set(req) != parent.prior.REQUEST_FIELDS or req['schema'] != parent.ENTRY_SCHEMA or req['root'] != str(root) or (req['implementation'] != parent.implementation_identity()) or (req['route'] != 'owned_timed_hour_development') or (req['parent_identity'] != expected_parent) or (req['parent_declaration'] != parent_declaration) or (req['pending_arguments'] != args) or (req['anchor_record'] != anchor_pin) or any((req[k] is not False for k in parent.FLAGS)):
        raise ValueError('Job request differs from source parent')
    item = parent.old.snapshot.PendingWorkerInput(packet, specification, limits, io.encode(req['input_receipt']))
    item.validate(expected_receipt_sha256=req['input_receipt_sha256'])
    rec = req['input_receipt']
    if rec['parent_identity'] != expected_parent or rec['anchor_record_sha256'] != anchor_pin or rec['journal_head'] != intent_head or (rec['source_lineage_identity'] != lineage):
        raise ValueError('Job input receipt differs from parent intent')
    budget = parent.old.process.TaskProcessBudget(**req['budget'])
    if budget.max_elapsed_seconds > 300 or not io.same(asdict(budget), req['budget']):
        raise ValueError('short exact Job budget required')
    resources = parent.old.process.resources
    hv = launch['host']
    host = resources.HostResourceBudget(hv['additional_commit_bytes'], hv['commit_reserve_bytes'], tuple((resources.DirectoryDemand(**d) for d in hv['directories'])))
    if not io.same(asdict(host), hv):
        raise ValueError('exact host inventory required')
    scratch = root / 'scratch_non_authoritative'
    env = parent.environment(scratch)
    identity = parent.old.process.task_process_identity(launch['argv'], cwd=scratch, environment=env, budget=budget, host_budget=host, expected_host_identity=resources.resource_identity(host))
    expected_launch = dict(request_sha256=pins['request.json'], process_identity=identity, argv=launch['argv'], cwd=str(scratch), environment_sha256=io.digest(io.encode(env)), budget=asdict(budget), host=asdict(host))
    if not io.same(launch, expected_launch):
        raise ValueError('Job launch differs')
    parent.old._validate_initial(docs['initial_observation.json'], host)
    pid, creation = (child['pid'], child['creation_filetime'])
    parent.old._validate_observation(parent.observation(observed), identity, pid, creation, budget)
    if not io.same(child, dict(pid=pid, creation_filetime=creation, process_identity=identity, request_sha256=pins['request.json'], initial_observation_sha256=pins['initial_observation.json'])):
        raise ValueError('Job child identity differs')
    if not io.same(release, dict(request_sha256=pins['request.json'], launch_sha256=pins['launch.json'], child_sha256=pins['child.json'])):
        raise ValueError('Job release differs')
    if not io.same(consume, dict(schema=parent.ENTRY_SCHEMA, request_sha256=pins['request.json'], release_sha256=pins['release_intent.json'], child_sha256=pins['child.json'], pid=pid, creation_filetime=creation, **parent.FLAGS)):
        raise ValueError('Job consumption differs')
    expected_result = dict(schema=parent.ENTRY_SCHEMA, request_sha256=pins['request.json'], consume_sha256=pins['consumed.json'], input_receipt_sha256=item.receipt_sha256, pid=pid, creation_filetime=creation, worker_binding_sha256=result['worker_binding_sha256'], worker_terminal_sha256=result['worker_terminal_sha256'], worker_implementation=worker.implementation_identity(), projection_sha256=result['projection_sha256'], **parent.FLAGS)
    if not io.same(result, expected_result):
        raise ValueError('Job result differs')
    wr = root / 'worker_non_authoritative'
    count = len(worker.hour.prior.native.model_api.stage_order(packet.inputs))
    before = parent.prior.worker_view(wr, count)
    checked = inspect_worker(wr, packet, specification, limits, expected_binding_sha=result['worker_binding_sha256'], expected_terminal_sha=result['worker_terminal_sha256'], expected_implementation=result['worker_implementation'], scope=scope)
    binding, _ = worker._read(wr / 'binding.json')
    if binding['pid'] != pid or binding['creation_filetime'] != creation or binding['controller_request_sha256'] != pins['request.json'] or (io.digest(checked['projection_payload']) != result['projection_sha256']):
        raise ValueError('worker result/process/request binding differs')
    parent.prior.unchanged(views)
    if io.identity(root / 'execution.lock') != lock_view or parent.prior.worker_view(wr, count) != before or worker.hour._directory(root, set(parent.RECORDS) | {'execution.lock', 'scratch_non_authoritative', 'worker_non_authoritative'}) != topology:
        raise ValueError('Job evidence changed during inspection')
    return checked['projection_payload']


def inspect_bridge(root, index, packet, specification, limits, *, binding_pin, intent_pin, terminal_pin, scope):
    """Fresh full science plus conditional timing arithmetic; no live receipt."""
    root = Path(root).absolute()
    if type(index) is not int or not 0 <= index < 192:
        raise ValueError('hour index required')
    directory = root / f'{index:03d}'
    identity = worker.hour._directory(directory, {'intent.json', 'job.json', 'terminal.json'})
    binding, bv = bridge.base.entry.read(root / 'binding.json', binding_pin)
    intent, iv = bridge.base.entry.read(directory / 'intent.json', intent_pin)
    terminal, tv = bridge.base.entry.read(directory / 'terminal.json', terminal_pin)
    if set(binding) != {'schema', 'implementation', 'parent_identity', 'pid', 'creation_filetime', 'thread_id', 'clock', 'hours', *bridge.FLAGS} or binding['schema'] != bridge.SCHEMA or binding['implementation'] != bridge.implementation_identity() or (not io.same(binding['clock'], bridge.profile())) or (type(binding['hours']) is not int) or (not index < binding['hours'] <= 192) or any((binding[k] is not False for k in bridge.FLAGS)):
        raise ValueError('clock binding differs')
    for name in ('pid', 'creation_filetime', 'thread_id'):
        if worker._integer(binding[name]) == 0:
            raise ValueError('controller owner required')
    io.pin(binding['parent_identity'])
    if set(intent) != {'schema', 'binding_sha256', 'index', 'start_ns', 'expected_head', 'source_identity', 'previous_sha256'} or intent['schema'] != bridge.SCHEMA or intent['binding_sha256'] != binding_pin or (type(intent['index']) is not int) or (intent['index'] != index):
        raise ValueError('clock intent differs')
    for name in ('expected_head', 'source_identity', 'previous_sha256'):
        io.pin(intent[name])
    if set(terminal) != {'schema', 'intent_sha256', 'end_ns', 'job_start_ns', 'job_end_ns', 'job_pins', 'outcome_head', 'job_record_sha256', 'outcome_anchor_sha256', *bridge.FLAGS} or terminal['schema'] != bridge.SCHEMA or terminal['intent_sha256'] != intent_pin or any((terminal[k] is not False for k in bridge.FLAGS)):
        raise ValueError('clock terminal differs')
    io.pin(terminal['outcome_head'])
    previous_views = {}
    if index == 0:
        if intent['previous_sha256'] != binding_pin:
            raise ValueError('first timing predecessor differs')
    else:
        previous_path = root / f'{index - 1:03d}' / 'terminal.json'
        previous, pv = bridge.base.entry.read(previous_path, intent['previous_sha256'])
        previous_views[previous_path] = (bridge.CAP, pv)
        if previous['schema'] != bridge.SCHEMA or previous['outcome_head'] != intent['expected_head'] or worker._integer(previous['end_ns']) > worker._integer(intent['start_ns']):
            raise ValueError('timing predecessor/order differs')
    job_record, jv = bridge.base.entry.read(directory / 'job.json', terminal['job_record_sha256'])
    if not io.same(job_record, dict(schema=bridge.SCHEMA, intent_sha256=intent_pin, start_ns=terminal['job_start_ns'], end_ns=terminal['job_end_ns'], job_pins=terminal['job_pins'])):
        raise ValueError('job timing record differs')
    job = root.parent / f'job_{index:03d}_non_authoritative'
    count = len(worker.hour.prior.native.model_api.stage_order(packet.inputs))
    view = bridge.base.parent.job_view(job, count)
    pins = terminal['job_pins']
    req, _ = bridge.base.entry.read(job / 'request.json', pins['request.json'])
    if req['parent_identity'] != binding['parent_identity'] or req['pending_arguments']['expected_source_identity'] != intent['source_identity']:
        raise ValueError('timing source/parent differs')
    anchor_root = Path(req['parent_declaration']['root']) / 'parent_anchor_non_authoritative'
    intent_anchor, iav = bridge.base.entry.read(anchor_root / f'{2 * index + 1:03d}.json', req['anchor_record'])
    outcome_anchor, oav = bridge.base.entry.read(anchor_root / f'{2 * index + 2:03d}.json', terminal['outcome_anchor_sha256'])
    if intent_anchor['previous_registry_head'] != intent['expected_head'] or outcome_anchor['registry_head'] != terminal['outcome_head'] or outcome_anchor['previous_registry_head'] != req['pending_arguments']['expected_head']:
        raise ValueError('timing parent anchor transition differs')
    inspect_job(job, packet, specification, limits, pins=pins, parent_declaration=req['parent_declaration'], intent_head=req['pending_arguments']['expected_head'], lineage=intent['source_identity'], scope=scope)
    child, _ = bridge.base.entry.read(job / 'child.json', pins['child.json'])
    result, _ = bridge.base.entry.read(job / 'worker_result.json', pins['worker_result.json'])
    wr = job / 'worker_non_authoritative'
    wb, _ = bridge.base.entry.read(wr / 'binding.json', result['worker_binding_sha256'])
    wt, _ = bridge.base.entry.read(wr / 'terminal.json', result['worker_terminal_sha256'])
    if not io.same(wb['clock'], binding['clock']) or wb['pid'] != child['pid'] or wb['creation_filetime'] != child['creation_filetime'] or (wb['pid'] == binding['pid']):
        raise ValueError('same-clock independent worker identity required')
    values = bridge.analyse(transaction_start=intent['start_ns'], job_start=terminal['job_start_ns'], worker_start=wb['start_ns'], worker_end=wt['end_ns'], job_end=terminal['job_end_ns'], transaction_end=terminal['end_ns'], native_total=wt['native_total_ns'])
    bridge.base.entry.unchanged({root / 'binding.json': (bridge.CAP, bv), directory / 'intent.json': (bridge.CAP, iv), directory / 'terminal.json': (bridge.CAP, tv), directory / 'job.json': (bridge.CAP, jv), anchor_root / f'{2 * index + 1:03d}.json': (bridge.CAP, iav), anchor_root / f'{2 * index + 2:03d}.json': (bridge.CAP, oav)})
    bridge.base.entry.unchanged(previous_views)
    if bridge.base.parent.job_view(job, count) != view or worker.hour._directory(directory, {'intent.json', 'job.json', 'terminal.json'}) != identity:
        raise ValueError('clock evidence changed during inspection')
    return dict(values, live_clock_bridge_authenticated=False, parent_prefix_verified=False, confirmation_tail_ns=None, **bridge.FLAGS)


def after(self, packet, result, *, scope):
    if type(result) is not RevalidatedChildInspection or type(result.projection) is not parent.Projection:
        raise ValueError('timed child projection required')
    doc = json.loads(result.projection.payload)
    if doc['schema'] != worker.hour.SCHEMA or doc['request_sha256'] != worker.hour.request_key(packet, self._spec, self._limits) or doc['before_identity'] != parent.source._digest(packet.before) or (len(doc['value']['canonical_locks']) != self._stages) or any((doc[k] is not False for k in worker.hour.stage.capture.FLAGS)):
        raise ValueError('replayed timed projection differs')
    values = doc['value']
    after = parent.source._owned(parent.source.H1NormalBoundary, network_identity=values['network_identity'], completed_hours=values['completed_hours'], units=tuple(((uid, on, float.fromhex(power), age) for uid, on, power, age in values['units'])), evidence_role='numerical_lex_candidate')
    parent.source._boundary(self._network, after, packet.relative_hour + 1)
    return after


def outcome(self, hour, intent_head, result, *, scope):
    if type(result) is not RevalidatedChildInspection or result.status != 'accepted' or result.stored_reports != self._stages:
        raise ValueError('complete timed Job child required')
    return dict(schema=parent.bounded.SCHEMA, kind='accepted', hour=hour, intent_head=intent_head, child_protocol=parent.CHILD_SCHEMA, child_head=result.head, child_identity=result.archive_identity, stored_reports=result.stored_reports, projection_identity=result.projection.projection_identity)
