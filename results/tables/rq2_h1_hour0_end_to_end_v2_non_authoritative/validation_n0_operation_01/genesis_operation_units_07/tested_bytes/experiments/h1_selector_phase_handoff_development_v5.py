"""Draft hour-zero handoff with a sufficient negative-only missing-Actual probe.

Consumes existing live parents only. A failure preserves the attempted root and
all child bytes; no retry, head selection, recovery or formal authority is issued.
"""
from base64 import b64encode
from contextlib import nullcontext
from copy import deepcopy
from dataclasses import asdict
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from threading import Lock, get_ident
from types import FunctionType, MappingProxyType, ModuleType
from experiments import h1_selector_parent_controller_development_v3 as parent
from experiments import h1_common_owner_genesis_development_v2 as common
from experiments import h1_selector_phase_consumption_development_v2 as preview
from experiments import h1_common_validation_operation_development_v3 as validation
from experiments import h1_selector_parent_validation_operation_development_v3 as parent_validation
phase, bootstrap = (common.phase, common.bootstrap)
snapshot, sequence = (parent.worker.snapshot, parent.worker.sequence)
io = parent.io
SCHEMA = 'h1_selector_phase_handoff_development_v5'
FLAGS = MappingProxyType(dict(parent.FLAGS, live_handoff_detached_credential=False, full_192_hour_execution_verified=False, recovery_authorized=False, phase_episode_terminal=False))
_OWNERS = {}

def _same(a, b):
    if phase.encode(a) != phase.encode(b):
        raise ValueError('phase handoff correspondence differs')

def _phase_identity(owner):
    return (owner.file_identity, owner._lease_object.root_identity, owner._lease_object.file_identity)

def _common_resources(genesis):
    roster = genesis._original_roster
    aliases = [(genesis, '_operation', genesis._original_operation), (genesis, '_original_operation', genesis._original_operation), (genesis, '_roster', roster), (genesis, '_original_roster', roster)]
    if hasattr(roster, '_original_operation'):
        guards = (genesis._original_operation, roster._original_operation, roster._owner_guard)
        aliases.extend(((roster, k, getattr(roster, k)) for k in ('_operation', '_original_operation', '_owner_guard', '_owner', '_original_owner')))
        aliases.append((roster._owner, '_operation', roster._owner_guard))
    else:
        release = roster._leave
        guard = getattr(release, '__self__', None)
        if type(guard) is not type(genesis._original_operation) or getattr(release, '__name__', None) != 'release':
            raise ValueError('exact captured roster guard required')
        guards = (genesis._original_operation, guard)
    if len({id(g) for g in guards}) != len(guards):
        raise ValueError('distinct common guards required')
    return (guards, tuple(aliases))

def _transaction(self):
    p = self._plan
    planned = phase.encode(dict(tickets=[phase.tickets._ticket_payload(t) for t in p.tickets], holder_records=[b64encode(r).decode('ascii') for r in p.holder_records], retentions=p.retentions, projection=json.loads(p.projection), after=json.loads(p.after)))
    return (id(p), planned, phase.encode(self._events), self._packet, self._common_view, self._report, self._child_headers, self._original_binder, self._header)

def _dependencies():
    """Original project callables/module edges, including imported-by-name roots."""
    pending = [parent, common, phase, preview, snapshot, sequence, bootstrap, io, parent_validation]
    seen = set()
    records = []
    modules = []
    project = lambda name: name.startswith(('experiments.', 'src.'))
    while pending:
        module = pending.pop()
        if id(module) in seen:
            continue
        seen.add(id(module))
        modules.append(module)
        for name, value in tuple(vars(module).items()):
            if isinstance(value, ModuleType) and project(value.__name__):
                records.append((module, name, value))
                pending.append(value)
            elif callable(value):
                records.append((module, name, value))
                origin = getattr(value, '__module__', '')
                if project(origin) and origin in sys.modules:
                    pending.append(sys.modules[origin])
                if isinstance(value, type) and (project(origin) or module is parent):
                    for key, descriptor in tuple(vars(value).items()):
                        if callable(descriptor) or isinstance(descriptor, (property, staticmethod, classmethod)):
                            records.append((value, key, descriptor))
    return (tuple(records), tuple(modules))

def _protocols(modules):

    def plain(v):
        if isinstance(v, (dict, MappingProxyType)):
            return {k: plain(x) for k, x in v.items()}
        if type(v) in (tuple, list):
            return [plain(x) for x in v]
        if type(v) in (set, frozenset):
            return sorted((plain(x) for x in v))
        return v
    return phase.encode([(m.__name__, {k: plain(v) for k, v in vars(m).items() if k.isupper() and (not k.startswith('_')) and (not callable(v)) and (any((word in k for word in ('SCHEMA', 'CAP', 'LIMIT', 'MAX'))) or k in ('FLAGS', 'INPUTS', 'OUTPUTS', 'PHASES', 'FILES', 'INPUT_FILES', 'OUTPUT_FILES'))}) for m in modules])

def implementation_identity():
    _CHECK()
    return io.digest(phase.encode([SCHEMA, __name__, sha256(Path(__file__).read_bytes()).hexdigest(), parent.implementation_identity(), common.implementation_identity(), sha256(Path(preview.__file__).read_bytes()).hexdigest(), sha256(Path(validation.__file__).read_bytes()).hexdigest(), parent_validation.implementation_identity()]))

class _Bundle:
    """Exact private adapter; locks remain held across the entire transaction."""
    __slots__ = ('actuals', 'held', 'marked', 'reference')

    def __init__(self, reference, actuals):
        if type(reference) is not tuple or len(reference) != 2 or type(actuals) is not dict:
            raise TypeError('exact reference pair and complete Actual dictionary required')
        self.reference = reference
        self.actuals = tuple(sorted(actuals.items()))
        self.held = []
        self.marked = []
        pairs = (reference, *(p for _, p in self.actuals if p is not None))
        for pair in pairs:
            if type(pair) is not tuple or len(pair) != 2 or type(pair[0]) is not parent.Parent or (type(pair[1]) is not parent.ParentCompletion):
                raise TypeError('exact live Parent pair required')
        if len({id(p[0]) for p in pairs}) != len(pairs):
            raise ValueError('distinct lane parent owners required')
        r, receipt = reference
        if receipt.role != 'reference' or r._reference_owner is not None:
            raise ValueError('unique reference parent required')
        for lane, pair in self.actuals:
            if type(lane) is not str:
                raise TypeError('exact lane IDs required')
            if pair is not None:
                owner, issued = pair
                if issued.role != 'actual' or owner._reference_owner is not r or owner._reference_completion is not receipt or (owner._reference_held is not False):
                    raise ValueError('exact Actual reference dependency required')

    def enter(self, host, token):
        _CHECK()
        if self.held:
            raise ValueError('bundle already active')
        try:
            for owner, _ in (*(p for _, p in self.actuals if p is not None), self.reference):
                guard = owner._guard
                parent.Parent._enter(owner)
                self.held.append(guard)
            for _, pair in self.actuals:
                if pair is not None:
                    pair[0]._reference_held = True
                    self.marked.append(pair[0])
            if all((pair is not None for _, pair in self.actuals)):
                _PARENT_ATTACH(host, token)
            self.validate()
        except BaseException as error:
            try:
                _PARENT_ABORT(host, error)
            except BaseException as failure:
                error.add_note('Parent validation abort: ' + repr(failure))
            try:
                self.leave()
            except BaseException as failure:
                error.add_note('Parent bundle release: ' + repr(failure))
            raise

    def validate(self):
        _CHECK()
        if len(self.held) != 1 + sum((p is not None for _, p in self.actuals)):
            raise ValueError('whole parent bundle guard required')
        if all((pair is not None for _, pair in self.actuals)):
            _PARENT_VALIDATE_BUNDLE(self)
        else:
            _PARTIAL_VALIDATE(self,*self.reference)
            for _, pair in self.actuals:
                if pair is not None:
                    _PARTIAL_VALIDATE(self,*pair)
        _CHECK()

    def records(self, pair):
        owner, receipt = pair
        optimized = all((pair is not None for _, pair in self.actuals))
        if optimized:
            _PARENT_VALIDATE_PAIR(self, owner, receipt)
            item = _PARENT_REBUILD(self, owner)
        else:
            _PARTIAL_VALIDATE(self,owner,receipt)
            item = snapshot.rebuild(owner._raw, expected_sha256=io.digest(owner._raw))
        data = json.loads(owner._outcome)['inspection']['data']
        request = json.loads(owner._declaration)['request']
        science = owner.worker_root / 'science_sequence_non_authoritative'
        timing = owner.worker_root / 'timing_sequence_non_authoritative'
        result = sequence.inspect(science, timing, item.frame, item.disclosure, item.before, expected_terminal_sha256=data['sequence_terminal_sha256'], max_archive_bytes=item.max_archive_bytes, max_timing_archive_bytes=request['max_timing_archive_bytes'], run_configuration=item.run_configuration, **item.arguments)
        count = len(result['records'])
        view = sequence._snapshot(science, timing, count, item.arguments['limits'], True, True)
        _same([result['request_sha256'], result['scientific_terminal_sha256'], [io.digest(r) for r in result['records']], sequence._snapshot_pin(view, science, timing)], [receipt.sequence_request_sha256, receipt.scientific_terminal_sha256, data['record_sha256'], data['archive_view_sha256']])
        _same(receipt.scientific_request_sha256, result['science']['request_sha256'])
        if str(science) != receipt.scientific_root:
            raise ValueError('science root differs')
        if optimized:
            _PARENT_VALIDATE_PAIR(self, owner, receipt)
        else:
            _PARTIAL_VALIDATE(self,owner,receipt)
        return result['records']

    def leave(self):
        for owner in reversed(self.marked):
            owner._reference_held = False
        self.marked.clear()
        for guard in reversed(self.held):
            guard.release()
        self.held.clear()

def _negative_missing_actual(self):
    """Sufficient rejection only; never accepts or creates a credential.

    This v3 observation precedes the v2 bundle/common observations. Compound
    faults can therefore have a different first error and lock trajectory.
    Structurally unsupported evidence and legitimate business-unresolved lanes
    retain the complete original path. Observation errors fail this attempt;
    no hint is retained across calls or callbacks.
    """
    bundle = self._bundle
    missing = tuple((lane for lane, pair in bundle.actuals if pair is None))
    if not missing:
        return None
    guard = None
    held = False
    reject = None
    try:
        _CHECK()
        owner, receipt = bundle.reference
        if type(owner) is not parent.Parent or type(receipt) is not parent.ParentCompletion:
            return None
        if any((not hasattr(owner, name) for name in ('_check', '_state', '_issued', '_issued_bytes', '_records'))):
            return None
        parent.Parent._check(owner)
        guard = owner._guard
        if not guard.acquire(False):
            return None
        held = True

        def shallow():
            parent.Parent._check(owner)
            if owner._guard is not guard or not guard.locked() or owner._state != 'complete' or (owner._reference_owner is not None) or (receipt.role != 'reference') or (owner._issued is not receipt) or (parent._completion_bytes(receipt) != owner._issued_bytes) or (receipt.terminal_sha256 != io.digest(owner._records['terminal.json'][1])):
                raise ValueError('original complete reference required for negative hint')
        shallow()
        item = snapshot.rebuild(owner._raw, expected_sha256=io.digest(owner._raw))
        data = json.loads(owner._outcome)['inspection']['data']
        request = json.loads(owner._declaration)['request']
        science = owner.worker_root / 'science_sequence_non_authoritative'
        timing = owner.worker_root / 'timing_sequence_non_authoritative'
        result = sequence.inspect(science, timing, item.frame, item.disclosure, item.before, expected_terminal_sha256=data['sequence_terminal_sha256'], max_archive_bytes=item.max_archive_bytes, max_timing_archive_bytes=request['max_timing_archive_bytes'], run_configuration=item.run_configuration, **item.arguments)
        count = len(result['records'])
        view = sequence._snapshot(science, timing, count, item.arguments['limits'], True, True)
        _same([result['request_sha256'], result['scientific_terminal_sha256'], [io.digest(r) for r in result['records']], sequence._snapshot_pin(view, science, timing)], [receipt.sequence_request_sha256, receipt.scientific_terminal_sha256, data['record_sha256'], data['archive_view_sha256']])
        _same(receipt.scientific_request_sha256, result['science']['request_sha256'])
        if str(science) != receipt.scientific_root:
            raise ValueError('negative hint science root differs')
        d = json.loads(owner._raw)['declaration']
        if d['role'] != 'reference' or d['lane_id'] is not None:
            return None
        manifest, binding, _ = snapshot._declarations(d['manifest'], d['source_binding'], d['run_configuration'])
        ids = tuple((c.lane_id for c in manifest.lanes))
        if tuple((k for k, _ in bundle.actuals)) != ids:
            return None
        g = self._genesis
        _same([asdict(manifest), asdict(binding)], [asdict(g._manifest), asdict(g._binding)])
        current = phase._fresh(binding, 0, binding.genesis_terminal_sha256)
        base = preview._planned_bootstrap(manifest, binding, current, owner_genesis=g._phase.genesis, holder_genesis=g._holder.genesis, reference_records=result['records'], actual_records={k: () for k in ids})
        dispositions = {row['lane_id']: row['status'] for row in json.loads(base.projection)['lanes']}
        if tuple(sorted(dispositions)) != ids:
            return None
        reject = next((lane for lane in missing if dispositions[lane] not in ('business_input_unresolved', 'business_unresolved')), None)
        shallow()
        _CHECK()
    finally:
        if held:
            guard.release()
    return reject

class Handoff:
    """Single attempt, one creating thread; no externally supplied record bytes."""
    __slots__ = ('_binding_view', '_bundle', '_caps', '_child_headers', '_children', '_closed_genesis', '_common_view', '_configuration', '_events', '_genesis', '_guard', '_header', '_holder', '_holder_callback', '_in_external', '_journal', '_journal_callback', '_journal_count', '_lease', '_names', '_original_binder', '_own', '_packet', '_packet_view', '_phase', '_pid', '_plan', '_report', '_retain', '_retained', '_self', '_state', '_thread', 'root', '__weakref__')

    def __init__(self, genesis, reference, actuals, *, retain_head, max_packet_bytes, max_record_bytes, max_archive_bytes):
        _CHECK()
        if type(genesis) is not common.CommonOwnerGenesis:
            raise TypeError('exact live common genesis required')
        if not callable(retain_head) or any((type(n) is not int or n <= 0 for n in (max_packet_bytes, max_record_bytes, max_archive_bytes))) or (not 1024 <= max_record_bytes <= 1024 ** 2):
            raise ValueError('explicit packet/journal bounds and external retention required')
        self._self = self
        self._pid, self._thread = (os.getpid(), get_ident())
        self._guard = Lock()
        self._genesis = genesis
        self._bundle = _Bundle(reference, actuals)
        self._retain = retain_head
        self._caps = (max_packet_bytes, max_record_bytes, max_archive_bytes)
        self._state = 'new'
        self._lease = self._journal = self._holder = self._phase = None
        self._retained = 0
        self._plan = None
        self._packet = None
        self._packet_view = None
        self._report = None
        self._common_view = None
        self._header = None
        self._events = None
        self._child_headers = None
        self._original_binder = None
        self._closed_genesis = False
        self._binding_view = None
        self._names = {'execution.lock'}
        self._children = None
        self._journal_count = 0
        self._in_external = False
        self._holder_callback = self._retain_holder
        self._journal_callback = self._retain_journal
        self._own = implementation_identity()
        self.root = bootstrap.local._path(genesis._roster._owner.study_root / 'selector_phase_handoffs_non_authoritative' / genesis.root.name)
        self._configuration = (genesis, reference, tuple(sorted(actuals.items())), retain_head, self._caps, self.root, self._own, self._holder_callback, self._journal_callback)
        _REGISTER(self)

    def _check(self):
        _CHECK()
        _VERIFY_OWNER(self)
        if self._self is not self or _OWNERS.get(id(self)) is not self or (os.getpid(), get_ident()) != (self._pid, self._thread) or (self._state not in ('new', 'running', 'complete')) or (self._own != implementation_identity()) or ((self._genesis, self._bundle.reference, self._bundle.actuals, self._retain, self._caps, self.root, self._own, self._holder_callback, self._journal_callback) != self._configuration):
            raise ValueError('handoff live owner or declaration changed')
        if self._lease is not None:
            self._lease.check()
        if self._binding_view is not None:
            if parent.worker._read(self.root / 'binding.json', self._caps[1]) != self._binding_view:
                raise ValueError('handoff binding changed')

    def _correspondence(self):
        self._check()
        g = self._genesis
        manifest, binding, report = _VALIDATION_PREPARE(self)
        _same([asdict(manifest), asdict(binding), report], [asdict(g._manifest), asdict(g._binding), json.loads(self._report)])
        if not self._closed_genesis:
            _same(snapshot._owner_view(g), json.loads(self._common_view))
        else:
            if not g.closed:
                raise ValueError('predecessor genesis must remain closed')
            for path, view in self._original_binder:
                if parent.worker._read(path, g.max_record_bytes) != view:
                    raise ValueError('predecessor binder changed')
            if {p.name for p in g.root.iterdir()} != {p.name for p, _ in self._original_binder} | {'execution.lock'}:
                raise ValueError('predecessor binder namespace changed')
        if self._packet_view is not None:
            if parent.worker._read(self.root / 'takeover_packet.json', self._caps[0]) != self._packet_view:
                raise ValueError('retained takeover packet changed')
        if self._children is not None:
            h, p = self._children
            if self._holder is not h or self._phase is not p or h.retain_head != self._holder_callback:
                raise ValueError('handoff child ownership changed')
            h._check()
            phase._SavedOwner._check(p)
            if phase.encode(h.binding) != self._child_headers[2] or p.holder is not h or p.retain_prepared != h.retain:
                raise ValueError('handoff child binding changed')
            if _phase_identity(p) != self._child_headers[3]:
                raise ValueError('original phase file identities changed')
        self._check()

    def _prepare(self):
        g = self._genesis
        bundle = self._bundle
        view = snapshot._owner_view(g)
        manifest, binding, report = _VALIDATION_PREPARE(self)
        self._common_view = phase.encode(view)
        self._report = phase.encode(report)
        ids = tuple((c.lane_id for c in manifest.lanes))
        if tuple((k for k, _ in bundle.actuals)) != ids:
            raise ValueError('complete exact Actual disposition roster required')
        for lane, pair in ((None, bundle.reference), *bundle.actuals):
            if pair is None:
                continue
            doc = json.loads(pair[0]._raw)['declaration']
            captured = dict(doc['provenance'])
            current_view = dict(view)
            captured_global = captured.pop('global_head')
            current_view.pop('global_head')
            global_ = g._roster._owner._global
            if captured_global not in {global_.genesis, *(head for head, _ in global_.rows())}:
                raise ValueError('Parent captured global head is not a retained ancestor')
            _same([captured, doc['manifest'], doc['source_binding'], doc['lane_id']], [current_view, asdict(manifest), asdict(binding), lane])
        current = phase._fresh(binding, 0, binding.genesis_terminal_sha256)
        with (_PARENT_RECORDS_BUNDLE(bundle) if all(pair is not None for _,pair in bundle.actuals) else nullcontext()):
            reference = bundle.records(bundle.reference)
            base = preview._planned_bootstrap(manifest, binding, current, owner_genesis=g._phase.genesis, holder_genesis=g._holder.genesis, reference_records=reference, actual_records={k: () for k in ids})
            disposition = {r['lane_id']: r['status'] for r in json.loads(base.projection)['lanes']}
            actual = {}
            typed = []
            for lane, pair in bundle.actuals:
                unresolved = disposition[lane] in ('business_input_unresolved', 'business_unresolved')
                if pair is None:
                    if not unresolved:
                        raise ValueError('Actual execution missing or failed: keep pending')
                    actual[lane] = ()
                    typed.append(dict(lane_id=lane, kind='business_unresolved_before_actual'))
                else:
                    if unresolved:
                        raise ValueError('unused Actual execution for unresolved business')
                    actual[lane] = bundle.records(pair)
                    typed.append(dict(lane_id=lane, kind='paired_actual'))
            plan = preview._planned_bootstrap(manifest, binding, current, owner_genesis=g._phase.genesis, holder_genesis=g._holder.genesis, reference_records=reference, actual_records=actual)
            if any((r['status'] not in ('paired_committed', 'business_input_unresolved', 'business_unresolved') for r in json.loads(plan.projection)['lanes'])):
                raise ValueError('authenticated complete disposition required')
        self._plan = plan
        parents = [dict(lane_id=lane, completion=json.loads(parent._completion_bytes(pair[1])), snapshot_sha256=io.digest(pair[0]._raw)) for lane, pair in ((None, bundle.reference), *bundle.actuals) if pair is not None]
        phase_identity = _phase_identity(g._phase)
        validation_declaration = _VALIDATION_DECLARATION(self)
        parent_validation_declaration = _PARENT_DECLARATION(bundle) if all((pair is not None for _, pair in bundle.actuals)) else None
        packet = phase.encode(dict(schema=SCHEMA, implementation=self._own, common=view, group_audit=report, validation_declaration=validation_declaration, parent_validation_declaration=parent_validation_declaration, phase_file_identity=phase_identity, dispositions=typed, parents=parents, tickets=[phase.tickets._ticket_payload(t) for t in plan.tickets], holder_records=[b64encode(raw).decode('ascii') for raw in plan.holder_records], retentions=plan.retentions, projection=json.loads(plan.projection), after=json.loads(plan.after), **FLAGS))
        declaration = dict(schema=SCHEMA, implementation=self._own, packet_sha256=io.digest(packet), packet_bytes=len(packet), packet_cap=self._caps[0], total_archive_cap=self._caps[2], common=view, validation_declaration=validation_declaration, parent_validation_declaration=parent_validation_declaration, **FLAGS)
        journal_root = self.root / 'journal_non_authoritative'
        header = bootstrap._journal_header(journal_root, declaration, 5, self._caps[1], bootstrap.implementation_identity())
        binding_worst = phase.encode(dict(declaration=declaration, journal_root=str(journal_root), root=str(self.root), root_identity=(10 ** 40 - 1,) * 2, file_identity=(10 ** 40 - 1,) * 2, packet_stamp=(10 ** 40 - 1,) * 5, **FLAGS))
        events = (dict(kind='takeover_intent', packet_sha256=io.digest(packet), packet_bytes=len(packet), packet_stamp=(10 ** 40 - 1,) * 5, binding_sha256='0' * 64, expected_phase_heads=plan.tickets[-1].after_heads, **FLAGS), dict(kind='handoff_opened', holder_header_sha256=io.digest(g._holder.header), owner_header_sha256=io.digest(g._phase.header), **FLAGS), *(dict(kind=f'holder_head_prepared_{i}', retention=r, **FLAGS) for i, r in enumerate(plan.retentions, 1)), dict(kind='bootstrap_consumed_terminal', holder_head=plan.retentions[-1][2], phase_heads=plan.tickets[-1].after_heads, projection_sha256=io.digest(plan.projection), completed_hours=1, **FLAGS))
        head = io.digest(header)
        sizes = []
        for i, event in enumerate(events, 1):
            raw = phase.encode(dict(sequence=i, previous=head, body=event))
            sizes.append(len(raw))
            head = io.digest(raw)
        if len(packet) > self._caps[0] or max(len(header), len(binding_worst), *sizes) > self._caps[1] or len(packet) + len(binding_worst) + len(header) + sum(sizes) > self._caps[2]:
            raise ValueError('complete handoff archive branch exceeds declared bounds')
        self._packet, self._header, self._events = (packet, header, events)
        self._child_headers = (g._holder.header, g._phase.header, phase.encode(g._holder.binding), phase_identity)
        self._original_binder = tuple(((p, parent.worker._read(p, g.max_record_bytes)) for p in sorted(g.root.iterdir()) if p.name != 'execution.lock'))
        self._correspondence()
        return (declaration, reference, actual)

    def _retain_journal(self, root, before, after):
        check, verify = (_CHECK, _VERIFY_OWNER)
        enter_external, leave_external, advance = (_ENTER_EXTERNAL, _LEAVE_EXTERNAL, _ADVANCE_COUNT)
        check()
        verify(self)
        if self._in_external or not self._guard.locked():
            raise ValueError('owned nonreentrant journal handoff required')
        count = self._journal_count + 1

        def prefix():
            self._correspondence()
            self._bundle.validate()
            if root != self.root / 'journal_non_authoritative' or count != self._journal_count + 1 or (not 1 <= count <= 5):
                raise ValueError('journal callback stage differs')
            if {p.name for p in root.iterdir()} != {'execution.lock', 'header.json', *(f'{i:020d}.json' for i in range(1, count + 1))}:
                raise ValueError('journal callback namespace differs')
            views = [parent.worker._read(root / 'header.json', self._caps[1])]
            if views[0][0] != self._header:
                raise ValueError('journal header changed at retention')
            head = io.digest(self._header)
            for i in range(1, count + 1):
                observed = parent.worker._read(root / f'{i:020d}.json', self._caps[1])
                views.append(observed)
                raw = phase.encode(dict(sequence=i, previous=head, body=self._events[i - 1]))
                if observed[0] != raw:
                    raise ValueError('journal retained prefix differs')
                if i == count and head != before:
                    raise ValueError('journal predecessor differs')
                head = io.digest(raw)
            if head != after or self._journal.head != before:
                raise ValueError('journal prospective head differs')
            return tuple(views)
        views = prefix()
        external_token = enter_external(self)
        try:
            returned = self._retain(root, before, after)
        finally:
            leave_external(self, external_token)
        check()
        verify(self)
        if prefix() != views:
            raise ValueError('journal replaced during external retention')
        if returned != after:
            raise ValueError('exact external journal head acknowledgement required')
        advance(self, '_journal_count', count, external_token)
        return returned

    def _retain_holder(self, genesis, before, after, count):
        self._correspondence()
        if self._in_external or self._children is None or (not self._phase._operation.locked()) or (not self._holder._guard.locked()) or (type(count) is not int) or (count != self._retained + 1) or (count not in (1, 2)) or ((genesis, before, after, count) != self._plan.retentions[count - 1]):
            raise ValueError('unplanned holder retention callback')
        self._journal.append(self._events[count + 1], expected_head=self._journal.head)
        self._correspondence()
        _ADVANCE_COUNT(self, '_retained', count)
        return after

    def _readback(self):
        self._correspondence()
        p = self._plan
        if self._retained != 2 or self._holder.inspect() != p.tickets or self._holder.head != p.retentions[-1][2]:
            raise ValueError('paired holder readback differs')
        with phase.closing(self._phase._connect()) as db:
            rows = self._phase._rows(db)
        if rows != [t.event for t in p.tickets] or self._phase.heads != p.tickets[-1].after_heads:
            raise ValueError('paired database readback differs')
        result = self._phase.inspect(expected_heads=self._phase.heads)
        if result.completed_hours != 1 or result.pending_intent or result.pending_attempt or result.recovery_required or result.conflicted_keys:
            raise ValueError('complete paired bootstrap required')
        if self._holder.header != self._child_headers[0] or self._phase.header != self._child_headers[1]:
            raise ValueError('child headers changed')
        self._bundle.validate()
        self._correspondence()

    def consume(self):
        _CHECK()
        if type(self) is not Handoff or self._self is not self:
            raise TypeError('exact original handoff required')
        guard = self._guard
        if not guard.acquire(False):
            raise ValueError('handoff operation active')
        bundle = self._bundle
        g = self._genesis
        common_held = False
        parents_held = False
        attempted = False
        token = None
        body_error = None
        parent_guards = ()
        parent_marks = ()
        common_guards = ()
        genesis_finalize = getattr(common, '_development_genesis_external_finalize_v1', None)
        cleanup = Handoff._close_handles
        begin, end, record_handle, record_view, seal, record_bundle = (_BEGIN, _END, _RECORD_HANDLE, _RECORD_VIEW, _SEAL, _RECORD_BUNDLE)
        record_predecessor, close_predecessor = (_RECORD_PREDECESSOR, _CLOSE_PREDECESSOR)
        abort_predecessor = _ABORT_PREDECESSOR
        validation_attach, validation_finish, validation_abort, validation_commit = (_VALIDATION_ATTACH, _VALIDATION_FINISH, _VALIDATION_ABORT, _VALIDATION_COMMIT)
        parent_finish, parent_abort, parent_commit = (_PARENT_FINISH, _PARENT_ABORT, _PARENT_COMMIT)
        parent_optimized = all((pair is not None for _, pair in bundle.actuals))
        result = None
        try:
            self._check()
            if self._state != 'new':
                raise ValueError('handoff is single-attempt')
            token = begin(self)
            self._state = 'running'
            attempted = True
            if any((pair is None for _, pair in bundle.actuals)):
                missing = _negative_missing_actual(self)
                if missing is not None:
                    raise ValueError('Actual execution missing or failed: keep pending')
            bundle.enter(self, token)
            parents_held = True
            parent_guards, parent_marks = (tuple(bundle.held), tuple(bundle.marked))
            record_bundle(self, token)
            common_guards, common_aliases = _common_resources(g)
            common.CommonOwnerGenesis._enter(g)
            common_held = True
            record_predecessor(self, token, common_guards, common_aliases)
            validation_attach(self, token)
            declaration, reference, actual = self._prepare()
            self.root.parent.mkdir(exist_ok=True)
            self._lease = bootstrap.local._Lease(self.root, True)
            record_handle(self, token, '_lease', self._lease)
            io.write_new(self.root / 'takeover_packet.json', self._packet)
            self._names.add('takeover_packet.json')
            self._packet_view = parent.worker._read(self.root / 'takeover_packet.json', self._caps[0])
            if self._packet_view[0] != self._packet:
                raise ValueError('packet readback differs')
            record_view(self, token, 'takeover_packet.json', self._packet_view)
            stamp = self._packet_view[1]
            identities = (*self._lease.root_identity, *self._lease.file_identity)
            if len(stamp) != 5 or len(identities) != 4 or any((type(n) is not int or not 0 <= n < 10 ** 40 for n in (*stamp, *identities))):
                raise ValueError('bounded outer identity and packet stamp required')
            binding = phase.encode(dict(declaration=declaration, journal_root=str(self.root / 'journal_non_authoritative'), root=str(self.root), root_identity=self._lease.root_identity, file_identity=self._lease.file_identity, packet_stamp=stamp, **FLAGS))
            if len(binding) > self._caps[1]:
                raise ValueError('binding cap exceeded')
            io.write_new(self.root / 'binding.json', binding)
            self._names.add('binding.json')
            self._binding_view = parent.worker._read(self.root / 'binding.json', self._caps[1])
            if self._binding_view[0] != binding:
                raise ValueError('binding readback differs')
            record_view(self, token, 'binding.json', self._binding_view)
            self._events = (dict(self._events[0], packet_stamp=stamp, binding_sha256=io.digest(binding)), *self._events[1:])
            seal(self, token)
            self._journal = bootstrap._Journal(self.root / 'journal_non_authoritative', declaration, max_events=5, max_record_bytes=self._caps[1], create=True, expected_head=None, retain_head=self._journal_callback)
            record_handle(self, token, '_journal', self._journal)
            self._names.add('journal_non_authoritative')
            if self._journal._header != self._header:
                raise ValueError('journal header differs from preflight')
            self._journal.append(self._events[0], expected_head=self._journal.head)
            self._correspondence()
            close_predecessor(self, token)
            m = g._manifest
            self._holder = phase.tickets.TicketHolder(g.holder_root, owner_root=g.owner_root, max_tickets=m.max_events, max_ticket_bytes=m.max_event_bytes, max_total_ticket_bytes=m.max_archive_bytes, create=False, expected_head=json.loads(self._common_view)['holder_receipt']['head'], retain_head=self._holder_callback)
            record_handle(self, token, '_holder', self._holder)
            if self._holder.header != self._child_headers[0] or phase.encode(self._holder.binding) != self._child_headers[2] or self._holder.inspect() != ():
                raise ValueError('reopened holder differs from retained genesis')
            self._phase = phase.DevelopmentOwner(g.owner_root, m, g._binding, holder=self._holder, create=False, expected_heads=tuple(json.loads(self._common_view)['owner_receipt']['heads']))
            record_handle(self, token, '_phase', self._phase)
            if self._phase.header != self._child_headers[1]:
                raise ValueError('reopened phase header differs')
            if _phase_identity(self._phase) != self._child_headers[3]:
                raise ValueError('original phase file identities changed')
            self._children = (self._holder, self._phase)
            self._correspondence()
            self._journal.append(self._events[1], expected_head=self._journal.head)
            self._phase.advance(expected_heads=self._phase.heads, terminal_sha256=g._binding.genesis_terminal_sha256, reference_records=reference, actual_records=actual)
            self._readback()
            self._journal.append(self._events[-1], expected_head=self._journal.head)
            self._readback()
            _same([v for _, v in self._journal.rows()], self._events)
            validation_receipt = validation_finish(self)
            result = dict(schema=SCHEMA, root=str(self.root), journal_head=self._journal.head, holder_head=self._holder.head, phase_heads=self._phase.heads, completed_hours=1, validation_receipt=validation_receipt, fresh_at_return_only=True, **FLAGS)
        except BaseException as error:
            body_error = error
            if attempted:
                try:
                    parent_abort(self, error)
                except BaseException as failure:
                    error.add_note('Parent proof abort: ' + repr(failure))
                try:
                    validation_abort(self, error)
                except BaseException as failure:
                    error.add_note('handoff validation abort: ' + repr(failure))
                try:
                    self._state = 'failed'
                except BaseException as failure:
                    error.add_note('handoff failure state: ' + repr(failure))
                try:
                    abort_predecessor(self, token)
                except BaseException as failure:
                    error.add_note('handoff predecessor abort: ' + repr(failure))
                try:
                    cleanup(self)
                except BaseException as failure:
                    error.add_note('handoff handle cleanup: ' + repr(failure))
            raise
        finally:
            errors = []

            def attempt(function, *arguments):
                try:
                    function(*arguments)
                except BaseException as failure:
                    errors.append(failure)
            if parents_held and parent_optimized:
                if body_error is None:
                    attempt(parent_finish, self)
                else:
                    attempt(parent_abort, self, body_error)
            if common_held:
                for held_guard in reversed(common_guards):
                    attempt(held_guard.release)
            if parents_held:
                for owner in reversed(parent_marks):
                    attempt(setattr, owner, '_reference_held', False)
                for held_guard in reversed(parent_guards):
                    attempt(held_guard.release)
                attempt(setattr, bundle, 'held', [])
                attempt(setattr, bundle, 'marked', [])
            if token is not None:
                attempt(end, self, token)
            attempt(guard.release)
            if common_held and genesis_finalize is not None:
                attempt(genesis_finalize, 'released', g, self, common_guards, body_error, tuple(errors))
            if errors:
                primary = body_error or errors[0]
                if attempted:
                    attempt(parent_abort, self, primary)
                    attempt(validation_abort, self, primary)
                    attempt(setattr, self, '_state', 'failed')
                    attempt(cleanup, self)
                for failure in errors:
                    if failure is not primary:
                        primary.add_note('handoff outer cleanup: ' + repr(failure))
                if body_error is None:
                    raise primary
        try:
            result['validation_receipt'] = validation_commit(self)
            result['parent_validation_receipt'] = parent_commit(self) if parent_optimized else None
            self._state = 'complete'
            if common_held and genesis_finalize is not None:
                genesis_finalize('committed', g, self, common_guards, None, ())
            return result
        except BaseException as error:
            if common_held and genesis_finalize is not None:
                try:
                    genesis_finalize('failed', g, self, common_guards, error, ())
                except BaseException as failure:
                    error.add_note('Genesis commit finalization: ' + repr(failure))
            try:
                parent_abort(self, error)
            except BaseException as failure:
                error.add_note('Parent proof commit abort: ' + repr(failure))
            try:
                validation_abort(self, error)
            except BaseException as failure:
                error.add_note('handoff validation commit abort: ' + repr(failure))
            try:
                self._state = 'failed'
            finally:
                try:
                    cleanup(self)
                except BaseException as failure:
                    error.add_note('handoff commit cleanup: ' + repr(failure))
            raise

    def _close_handles(self):
        try:
            if self._phase is not None:
                phase.DevelopmentOwner.close(self._phase)
        finally:
            try:
                if self._holder is not None:
                    phase.tickets.TicketHolder.close(self._holder)
            finally:
                try:
                    if self._journal is not None:
                        bootstrap._Journal.close(self._journal)
                finally:
                    if self._lease is not None:
                        bootstrap.local._Lease.close(self._lease)

    def close(self):
        return _CLEANUP(self)

    def validation_receipt(self):
        return _VALIDATION_RECEIPT(self)

    def __enter__(self):
        self._check()
        return self

    def __exit__(self, *args):
        self.close()

    def _no_copy(self, *args):
        raise TypeError('live handoff cannot be copied')
    __copy__ = __deepcopy__ = __reduce_ex__ = _no_copy

def _anchor():
    namespace = vars(sys.modules[__name__])
    parent_check = parent._CHECK
    owner_type, registry, pid, thread = (Handoff, _OWNERS, os.getpid, get_ident)
    owned = {}
    transaction = _transaction
    handle_names = ('_phase', '_holder', '_journal', '_lease')
    old_close = common.CommonOwnerGenesis._close_handles
    lease_check = bootstrap.local._Lease.check
    common_view = snapshot._owner_view
    encode = phase.encode
    local = bootstrap.local
    lease_registry, lease_registry_guard = (local._REGISTRY, local._REGISTRY_LOCK)
    lease_fields = ('root', 'key', 'pid', 'stream', 'locked', 'root_identity', 'file_identity')

    def capsule(handle, kind):
        aliases = {'_phase': ('lease', '_lease_object'), '_holder': ('lease', '_lease_object'), '_journal': ('_lease', '_original_lease'), '_lease': ()}[kind]
        lease = handle if kind == '_lease' else getattr(handle, aliases[-1])
        if type(lease) is not local._Lease:
            raise TypeError('exact original child lease required')
        guards = {'_phase': ('_operation',), '_holder': ('_guard',), '_journal': (), '_lease': ()}[kind]
        return dict(handle=handle, lease=lease, fields=tuple(((k, getattr(lease, k)) for k in lease_fields)), aliases=tuple(((k, lease) for k in aliases)), guards=tuple(((k, getattr(handle, k)) for k in guards)), states=tuple(((k, getattr(handle, k)) for k in ('closed', 'poisoned') if kind != '_lease')), release_guards=(), released=False)

    def capsule_changed(cap):
        h, l = (cap['handle'], cap['lease'])
        if any((getattr(h, k) is not v for k, v in (*cap['aliases'], *cap['guards']))):
            return True
        if cap['released']:
            return False
        if any((getattr(h, k) is not v for k, v in cap['states'])):
            return True
        for k, v in cap['fields']:
            changed = getattr(l, k) is not v if k == 'stream' else getattr(l, k) != v
            if changed:
                return True
        stream = dict(cap['fields'])['stream']
        return stream.closed or local._REGISTRY is not lease_registry or local._REGISTRY_LOCK is not lease_registry_guard or (dict(cap['fields'])['key'] not in lease_registry)

    def restore_capsule(cap, *, states):
        h, l = (cap['handle'], cap['lease'])
        for k, v in (*cap['aliases'], *cap['guards']):
            setattr(h, k, v)
        for k, v in cap['fields']:
            setattr(l, k, v)
        if states:
            for k, v in cap['states']:
                setattr(h, k, v)

    def release_capsule(cap):
        if cap['released']:
            return
        cap['released'] = True
        h, l = (cap['handle'], cap['lease'])
        saved = dict(cap['fields'])
        stream = saved['stream']
        restore_capsule(cap, states=False)
        try:
            if not stream.closed:
                try:
                    stream.close()
                finally:
                    with lease_registry_guard:
                        lease_registry.discard(saved['key'])
        finally:
            l.stream = None
            l.locked = False
            if cap['states']:
                h.closed = True
            for guard in cap['release_guards']:
                if guard.locked():
                    guard.release()

    def register(self):
        if type(self) is not owner_type or id(self) in owned:
            raise ValueError('new exact handoff owner required')
        owned[id(self)] = dict(owner=self, configuration=self._configuration, bundle=self._bundle, guard=self._guard, creator=(self._pid, self._thread), bundle_state=None, predecessor=None, predecessor_leases=None, external_active=False, external_token=None, external_ever=False, counts={'_journal_count': 0, '_retained': 0}, handles={name: None for name in handle_names}, capsules={}, predecessor_capsules=(), common_aliases=(), common_guards=(), validation_guards=(), predecessor_closed=False, predecessor_states=(), views={}, transaction=None, token=None, released=set())
        owned[id(self)].update(partial_failure=None,partial_active=False,partial_reference=self._bundle.reference,
            partial_actuals=self._bundle.actuals,partial_parents=tuple(
                (p,issued,p._raw,p._issued_bytes,p._guard) for p,issued in
                (self._bundle.reference,*(pair for _,pair in self._bundle.actuals if pair is not None))))
        registry[id(self)] = self

    def lookup(self):
        record = owned.get(id(self))
        if type(self) is not owner_type or record is None or record['owner'] is not self or (registry.get(id(self)) is not self) or (self._self is not self) or (self._configuration is not record['configuration']) or (self._bundle is not record['bundle']) or (self._guard is not record['guard']) or ((pid(), thread()) != record['creator']) or ((self._pid, self._thread) != record['creator']):
            raise ValueError('original registered handoff identity required')
        return record

    def verify(self):
        record = lookup(self)
        if self._in_external is not record['external_active'] or any((getattr(self, k) != v for k, v in record['counts'].items())):
            raise ValueError('original callback state or counters changed')
        if any((getattr(self, k) is not v for k, v in record['handles'].items())):
            raise ValueError('original handoff handles changed')
        if any((capsule_changed(cap) for cap in (*record['capsules'].values(), *record['predecessor_capsules']))):
            raise ValueError('original nested resources changed')
        if any((getattr(o, k) is not v for o, k, v in record['common_aliases'])) or any((not g.locked() for g in record['common_guards'])):
            raise ValueError('original acquired common guards changed')
        if self._packet_view != record['views'].get('takeover_packet.json') or self._binding_view != record['views'].get('binding.json'):
            raise ValueError('retained outer views changed')
        if self._lease is not None:
            names = {'execution.lock', *record['views']}
            if self._journal is not None:
                names.add('journal_non_authoritative')
            if {p.name for p in self.root.iterdir()} != names:
                raise ValueError('fixed handoff outer namespace differs')
        if record['transaction'] is not None and transaction(self) != record['transaction']:
            raise ValueError('immutable handoff transaction changed')
        if record['bundle_state'] is not None and (self._bundle.reference, self._bundle.actuals, tuple(self._bundle.held), tuple(self._bundle.marked)) != record['bundle_state']:
            raise ValueError('original held parent bundle changed')
        if record['predecessor'] is not None:
            g, p, h, j, r, guard = record['predecessor']
            if self._genesis is not g or g._phase is not p or g._original_phase is not p or (g._holder is not h) or (g._original_holder is not h) or (g._journal is not j) or (g._original_journal is not j) or (g._roster is not r) or (g._original_roster is not r) or (g._original_operation is not guard):
                raise ValueError('original common genesis handles changed')
            if not record['predecessor_closed'] and any((getattr(g, k) is not v for k, v in record['predecessor_states'])):
                raise ValueError('borrowed common state changed')

    def begin(self):
        record = lookup(self)
        if record['token'] is not None or not record['guard'].locked():
            raise ValueError('exclusive handoff operation required')
        token = record['token'] = object()
        return token

    def enter_external(self):
        record = lookup(self)
        verify(self)
        if record['token'] is None or record['external_active'] or (not record['guard'].locked()):
            raise ValueError('owned nonreentrant external retention required')
        if record['external_token'] is not None:
            raise ValueError('previous external retention not advanced')
        token = object()
        record['external_token'] = token
        record['external_active'] = True
        record['external_ever'] = True
        self._in_external = True
        for cap in record['capsules'].values():
            cap['release_guards'] = tuple((guard for _, guard in cap['guards'] if guard.locked()))
        return token

    def leave_external(self, token):
        record = lookup(self)
        if token is None or token is not record['external_token'] or (not record['external_active']):
            raise ValueError('original external retention token required')
        record['external_active'] = False
        self._in_external = False

    def advance_count(self, name, count, token=None):
        record = lookup(self)
        verify(self)
        if record['token'] is None or record['external_active'] or name not in record['counts'] or (type(count) is not int) or (count != record['counts'][name] + 1):
            raise ValueError('original sequential retention count required')
        if name == '_journal_count':
            if token is None or token is not record['external_token']:
                raise ValueError('original external retention token required')
            record['external_token'] = None
        elif token is not None or record['external_token'] is not None:
            raise ValueError('external retention must precede holder retention')
        record['counts'][name] = count
        setattr(self, name, count)

    def operation(self, token):
        record = lookup(self)
        if token is None or record['token'] is not token or (not record['guard'].locked()):
            raise ValueError('original handoff operation token required')
        return record

    raw_source,raw_inspect=parent._WINDOWS.raw_source,parent._WINDOWS.raw_inspect
    partial_raw_states=tuple((fn,fn.__code__,repr(fn.__defaults__),repr(fn.__kwdefaults__))
        for fn in (raw_source,raw_inspect))
    partial_callers=(_Bundle.validate.__code__,_Bundle.records.__code__)

    def partial_validate(bundle,owner,issued):
        """Original uncached validation schedule for a genuine partial roster.

        The new Parent's private raw methods do not open lifecycle windows.
        This adapter retains the predecessor per-site source preparations and
        supports the existing business-unresolved disposition.
        """
        _CHECK()
        if sys._getframe(1).f_code not in partial_callers:
            raise ValueError('original partial bundle call site required')
        matches=[row for row in owned.values() if row['bundle'] is bundle]
        if len(matches)!=1:raise ValueError('original registered partial bundle required')
        record=matches[0];host=record['owner']
        def admit():
            verify(host);operation(host,record['token']);parent_check()
            if (parent._WINDOWS.raw_source is not raw_source or parent._WINDOWS.raw_inspect is not raw_inspect
                    or any(fn.__code__ is not code or repr(fn.__defaults__)!=defaults
                        or repr(fn.__kwdefaults__)!=keywords for fn,code,defaults,keywords in partial_raw_states)):
                raise ValueError('original uncached partial Parent routes required')
            if (record['partial_failure'] is not None or host._state!='running'
                    or record['external_active'] or bundle.reference is not record['partial_reference']
                    or bundle.actuals is not record['partial_actuals']
                    or all(pair is not None for _,pair in bundle.actuals)):
                raise ValueError('original active partial Handoff required')
            expected=tuple(pair[0] for _,pair in bundle.actuals if pair is not None)
            guards=tuple(p._guard for p in expected)+(bundle.reference[0]._guard,)
            if (len(bundle.held)!=len(guards) or any(a is not b for a,b in zip(bundle.held,guards))
                    or len(bundle.marked)!=len(expected) or any(a is not b for a,b in zip(bundle.marked,expected))):
                raise ValueError('original partial Parent guards and marks required')
            binding=json.loads(record['partial_parents'][0][2])['declaration']['source_binding']
            for index,(p,completion,raw,completion_raw,guard) in enumerate(record['partial_parents']):
                if (type(p) is not parent.Parent or type(completion) is not parent.ParentCompletion
                        or (p._pid,p._thread)!=record['creator'] or p._raw is not raw
                        or p._issued is not completion or p._issued_bytes!=completion_raw
                        or parent._completion_bytes(completion)!=completion_raw
                        or p._guard is not guard or not guard.locked() or p._state!='complete'
                        or p._reference_held is not (index!=0)
                        or json.loads(raw)['declaration']['source_binding']!=binding
                        or (index and (p._reference_owner is not bundle.reference[0]
                            or p._reference_completion is not bundle.reference[1]))):
                    raise ValueError('exact original partial Parent and completion required')
        def validate(p,completion):
            admit()
            if not any(p is obj and completion is receipt for obj,receipt,*_ in record['partial_parents']):
                raise ValueError('original partial Parent pair required')
            p._check()
            raw_source(p)
            def reference():
                if p._reference_owner is None:return
                if not p._reference_held:raise ValueError('reference operation lease required')
                validate(p._reference_owner,p._reference_completion)
                parent._same(p._reference_match(p._reference_owner,p._reference_completion),p._reference_descriptor)
            reference()
            if p._outcome is None:raise ValueError('completed owned outcome required')
            outcome=json.loads(p._outcome);prior=outcome['inspection'];data=prior['data']
            fresh=raw_inspect(p,dict(pid=outcome['pid'],creation_filetime=outcome['creation_filetime']),
                {name:data['pins'][name] for name in parent.inspection.OUTPUT_FILES})
            expected=deepcopy(prior);expected['data']['output_pins_externally_supplied']=True
            parent._same(fresh,expected)
            terminal=parent.io.encode(dict(schema=parent.SCHEMA,implementation=p._own,
                binding_sha256=parent.io.digest(p._binding),request_keys=p._request_keys(),
                reference_execution=p._reference_descriptor,lifecycle=outcome,**parent.FLAGS))
            if p._records['terminal.json'][1]!=terminal:raise ValueError('parent outcome terminal changed')
            reference();p._check()
            if any(getattr(completion,key)!=value for key,value in p._request_keys().items()):
                raise ValueError('completion request keys differ')
            if completion.terminal_sha256!=parent.io.digest(p._records['terminal.json'][1]):
                raise ValueError('completion terminal differs')
            admit()
        entered=False
        try:
            verify(host)
            if record['partial_active']:
                raise ValueError('partial Parent validation is nonreentrant')
            record['partial_active']=True;entered=True
            validate(owner,issued)
        except BaseException as error:
            if record['creator']==(pid(),thread()) and record['partial_failure'] is None:
                record['partial_failure']=repr(error)
            raise
        finally:
            if entered:record['partial_active']=False

    def end(self, token):
        record = operation(self, token)
        record['token'] = None
        record['bundle_state'] = None
        record['common_guards'] = ()

    def record_bundle(self, token):
        record = operation(self, token)
        b = record['bundle']
        if record['bundle_state'] is not None:
            raise ValueError('parent bundle already retained')
        record['bundle_state'] = (b.reference, b.actuals, tuple(b.held), tuple(b.marked))

    def record_predecessor(self, token, guards, aliases):
        record = operation(self, token)
        g = self._genesis
        if record['predecessor'] is not None:
            raise ValueError('predecessor already retained')
        if any((not guard.locked() for guard in guards)):
            raise ValueError('all captured common guards must be held')
        record['common_guards'], record['common_aliases'] = (guards, aliases)
        record['validation_guards'] = guards
        record['predecessor'] = (g, g._original_phase, g._original_holder, g._original_journal, g._original_roster, g._original_operation)
        record['predecessor_states'] = tuple(((k, getattr(g, k)) for k in ('closed', 'poisoned')))
        record['predecessor_leases'] = (g._original_phase._lease_object, g._original_holder._lease_object, g._original_journal._original_lease)
        record['predecessor_capsules'] = tuple((capsule(h, k) for h, k in ((g._original_phase, '_phase'), (g._original_holder, '_holder'), (g._original_journal, '_journal'))))

    def abort_predecessor(self, token):
        record = owned.get(id(self))
        if record is None or record['owner'] is not self:
            raise ValueError('original handoff cleanup owner required')
        if token is None or token is not record['token'] or (not record['guard'].locked()):
            raise ValueError('original handoff operation token required')
        if not record['external_ever'] or record['predecessor_closed'] or record['predecessor'] is None:
            return
        g, p, h, j, r, guard = record['predecessor']
        caps = record['predecessor_capsules']
        try:
            g._phase = g._original_phase = p
            g._holder = g._original_holder = h
            g._journal = g._original_journal = j
            for obj, key, value in record['common_aliases']:
                setattr(obj, key, value)
            if any((dict(cap['fields'])['stream'].closed for cap in caps)):
                raise ValueError('external capability destruction')
            for cap in caps:
                restore_capsule(cap, states=True)
            for key, value in record['predecessor_states']:
                setattr(g, key, value)
            check()
            for cap in caps:
                if capsule_changed(cap):
                    raise ValueError('borrowed resource integrity loss')
                lease_check(cap['lease'])
            if record['transaction'] is None or encode(common_view(g)) != record['transaction'][4]:
                raise ValueError('borrowed durable owner correspondence changed')
        except BaseException:
            g.poisoned = True
            raise ValueError('external borrowed capability integrity loss; no automatic recovery')

    def close_predecessor(self, token):
        record = operation(self, token)
        g, p, h, j, _, _ = record['predecessor']
        first = None
        verify(self)
        try:
            old_close(g)
        except BaseException as exc:
            first = exc
            g.poisoned = True
        finally:
            g.closed = True
            self._closed_genesis = True
            record['predecessor_closed'] = True
            for cap in record['predecessor_capsules']:
                try:
                    release_capsule(cap)
                except BaseException as exc:
                    if first is None:
                        first = exc
        if first is not None:
            raise first

    def record_handle(self, token, name, handle):
        record = operation(self, token)
        if name not in handle_names or record['handles'][name] is not None or getattr(self, name) is not handle:
            raise ValueError('create-once original handle registration required')
        record['handles'][name] = handle
        record['capsules'][name] = capsule(handle, name)

    def record_view(self, token, name, view):
        record = operation(self, token)
        if name not in ('takeover_packet.json', 'binding.json') or name in record['views']:
            raise ValueError('create-once original file retention required')
        record['views'][name] = view

    def seal(self, token):
        record = operation(self, token)
        if record['transaction'] is not None:
            raise ValueError('transaction already fixed')
        record['transaction'] = transaction(self)

    def close_handles(self):
        record = owned.get(id(self))
        if record is None or record['owner'] is not self:
            raise ValueError('registered cleanup owner required')
        first = None
        for name in handle_names:
            handle = record['handles'][name]
            if handle is None or name in record['released']:
                continue
            record['released'].add(name)
            try:
                release_capsule(record['capsules'][name])
            except BaseException as exc:
                if first is None:
                    first = exc
        if first is not None:
            raise first

    def cleanup(self):
        if type(self) is not owner_type:
            raise TypeError('exact handoff owner required')
        record = owned.get(id(self))
        if record is None:
            if self._state == 'closed':
                return
            raise ValueError('registered handoff owner required')
        if record['owner'] is not self:
            raise ValueError('registered handoff owner required')
        if (pid(), thread()) != record['creator']:
            raise ValueError('handoff creating thread required')
        guard = record['guard']
        if not guard.acquire(False):
            raise ValueError('cannot close active handoff')
        try:
            if self._state == 'closed':
                return
            if registry.get(id(self)) is not self:
                raise ValueError('registered handoff owner required')
            try:
                close_handles(self)
            finally:
                self._state = 'closed'
                registry.pop(id(self), None)
                owned.pop(id(self), None)
        finally:
            guard.release()

    def leave(self, *args):
        return cleanup(self)

    def validation_finalized(self):
        check()
        record = lookup(self)
        verify(self)
        b = record['bundle']
        parents = tuple((pair[0] for pair in (b.reference, *(pair for _, pair in b.actuals)) if pair is not None))
        if record['token'] is not None or record['guard'].locked() or record['common_guards'] or b.held or b.marked or any((guard.locked() for guard in record['validation_guards'])) or any((owner._guard.locked() or owner._reference_held for owner in parents)):
            raise ValueError('all original outer resources must be released before validation commit')
    namespace['_CLEANUP'] = cleanup
    namespace['_PARTIAL_VALIDATE']=partial_validate
    namespace.update(_REGISTER=register, _VERIFY_OWNER=verify, _BEGIN=begin, _END=end, _ENTER_EXTERNAL=enter_external, _LEAVE_EXTERNAL=leave_external, _ADVANCE_COUNT=advance_count, _RECORD_HANDLE=record_handle, _RECORD_VIEW=record_view, _SEAL=seal, _RECORD_BUNDLE=record_bundle, _RECORD_PREDECESSOR=record_predecessor, _CLOSE_PREDECESSOR=close_predecessor, _ABORT_PREDECESSOR=abort_predecessor)
    namespace['_VALIDATION_ATTACH'], namespace['_VALIDATION_PREPARE'], namespace['_VALIDATION_DECLARATION'], namespace['_VALIDATION_FINISH'], namespace['_VALIDATION_ABORT'], namespace['_VALIDATION_RECEIPT'], namespace['_VALIDATION_COMMIT'] = validation._bind_handoff(sys.modules[__name__], owner_type, verify, operation, validation_finalized)
    namespace['_PARENT_ATTACH'], namespace['_PARENT_VALIDATE_BUNDLE'], namespace['_PARENT_REBUILD'], namespace['_PARENT_FINISH'], namespace['_PARENT_ABORT'], namespace['_PARENT_RECEIPT'], namespace['_PARENT_COMMIT'], namespace['_PARENT_VALIDATE_PAIR'], namespace['_PARENT_DECLARATION'], namespace['_PARENT_RECORDS_BUNDLE'] = parent_validation._bind_handoff(sys.modules[__name__], owner_type, verify, operation, validation_finalized)
    owner_type.close, owner_type.__exit__, owner_type._close_handles = (cleanup, leave, close_handles)

    def guarded(function):

        def entry(*args, **kwargs):
            if not args or type(args[0]) is not owner_type:
                raise TypeError('exact original handoff required')
            check()
            if function.__name__ != '__init__':
                verify(args[0])
            return function(*args, **kwargs)
        return entry
    for name in ('__init__', 'consume', '_check', '__enter__'):
        setattr(owner_type, name, guarded(vars(owner_type)[name]))
    functions = tuple(((obj, name, value) for obj in (sys.modules[__name__], _Bundle, Handoff, common.CommonOwnerGenesis, bootstrap._Journal, phase.DevelopmentOwner, phase._SavedOwner, phase.tickets.TicketHolder) for name, value in tuple(vars(obj).items()) if isinstance(value, (FunctionType, staticmethod, classmethod, property))))
    dependencies, modules = _dependencies()
    protocols = _protocols(modules)
    protocol_read = _protocols
    retained = tuple(((name, value) for name, value in namespace.items() if name != '_CHECK'))

    def check():
        if namespace.get('_CHECK') is not check or any((namespace.get(k) is not v for k, v in retained)) or any((vars(o).get(k) is not v for o, k, v in (*functions, *dependencies))):
            raise ValueError('handoff original scope changed')
        if protocol_read(modules) != protocols:
            raise ValueError('handoff dependency protocol changed')
        parent_check()
    return check
_CHECK = _anchor()
