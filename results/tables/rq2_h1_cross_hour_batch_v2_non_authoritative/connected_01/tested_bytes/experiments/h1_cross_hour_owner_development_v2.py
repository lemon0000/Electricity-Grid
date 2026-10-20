"""Atomic live phase continuation; DRAFT_NONAUTHORITATIVE.

The saved phase-owner v1 and its scientific transition are unchanged.  This
successor has its own header and roots.  It connects a still-live 192h normal
controller to the owner; reopening remains read-only for normal production.
Native execution requires separate authority.  Tests install explicit synthetic
source/catalog and fake-solver seams; none of these objects is a run authority.
"""
from contextlib import closing
from dataclasses import asdict, dataclass, replace
from fractions import Fraction as Q
from hashlib import sha256
import json
import os
from pathlib import Path
from threading import get_ident
import time

from experiments import h1_phase_owner_development_v1 as saved
from experiments import h1_phase_obligation_controller_development_v1 as normal
from experiments import h1_phase_exact_source_batch_development_v1 as batch_source

SCHEMA = 'h1_cross_hour_owner_development_v2'
SELECTOR_PURPOSE = 'phase_shared_reference_then_actual_development'
encode, digest = saved.encode, saved.digest
_PREPARE_MANY = batch_source.prepare_many
MAX_BATCH_OBSERVATIONS = 2048


def _check_source_entry():
    if batch_source.prepare_many is not _PREPARE_MANY:
        raise ValueError('original batch source entry required')
    batch_source._check_reader_entry()


def _validate_batch(result,binding,terminals,selected,source_identity):
    """Validate the successor data contract before scientific replay/effects."""
    encoded=batch_source.io.encode
    if (type(result) is not batch_source.CurrentBatch or type(result.currents) is not dict
            or set(result.currents)!=set(selected)):
        raise ValueError('exact batch current keyset/type required')
    if type(result.observations) is not tuple or len(result.observations)!=2:
        raise ValueError('two independent batch observations required')
    tokens=[]
    for metric in result.observations:
        if (type(metric) is not dict or metric.get('completed_hours')!=max(terminals)+1
                or metric.get('selected_hours')!=list(selected)
                or type(metric.get('parent_inspect_traversals')) is not int
                or metric['parent_inspect_traversals']!=2
                or type(metric.get('observation_token')) is not str or len(metric['observation_token'])!=32):
            raise ValueError('batch observation shape differs')
        tokens.append(metric['observation_token'])
    if tokens[0]==tokens[1]:raise ValueError('distinct batch observations required')
    prior=batch_source.prior
    false_flags=('policy_visible','shared_observed_clock','accepted_real_RTS_root_integration_verified',
        'detached_consumer_authenticated','persistent_lane_owner_implemented','common_publication_verified',
        'full_192_hour_execution_verified','resource_admission','formal_execution_ready','formal_result',
        'native_execution_authorized')
    verified=('current_source_correspondence_checked','registry_action_and_cap_lookup_checked',
        'exact_source_projection_checked')
    historical_true=('historical_parent_prefix_verified','historical_obligation_prefix_verified',
        'historical_job_clock_prefix_verified')
    historical_false=('suffix_chain_verified','current_latest_parent_verified','current_latest_obligation_verified',
        'live_release_authenticated','live_handoff_authenticated','writer_lock_authenticated',
        'persistent_lane_owner_implemented','detached_consumer_authenticated','common_prefix_publication_verified',
        'reference_or_actual_ready',*batch_source.historical.old.FLAGS)
    for hour,current in result.currents.items():
        if type(hour) is not int or type(current) is not prior.ExactSourceCurrent:
            raise ValueError('exact successor current type required')
        prepared=current.prepared_current
        if (type(prepared) is not prior.origin_join.PreparedCurrent
                or type(current.source_projection_audit_payload) is not bytes
                or len(current.source_projection_audit_payload)>prior.historical.binding.CAP
                or type(current.exogenous_scientific_payload) is not bytes
                or type(current.workload_exact) is not Q or type(current.source_cfe_at_alpha_one_exact) is not Q):
            raise ValueError('exact successor current fields required')
        audit=json.loads(current.source_projection_audit_payload)
        if (type(audit) is not dict or encoded(audit)!=current.source_projection_audit_payload
                or prepared.audit_payload!=current.source_projection_audit_payload
                or audit.get('schema')!=batch_source.SCHEMA or audit.get('replay_contract')!=batch_source.SCHEMA
                or audit.get('implementation_identity')!=source_identity
                or type(audit.get('completed_hours')) is not int or audit['completed_hours']!=hour+1
                or audit.get('controller_binding_sha256')!=binding.binding_sha256
                or audit.get('controller_terminal_sha256')!=terminals[hour]
                or audit.get('registry_identity')!=binding.registry_identity
                or any(audit.get(k) is not False for k in false_flags)
                or any(audit.get(k) is not True for k in verified)):
            raise ValueError('successor source audit identity/pins differ')
        proof=audit.get('historical_controller')
        if (type(proof) is not dict or proof.get('replay_contract')!=batch_source.historical.SCHEMA
                or type(proof.get('completed_hours')) is not int or proof['completed_hours']!=hour+1
                or any(proof.get(k) is not True for k in historical_true)
                or any(proof.get(k) is not False for k in historical_false)):
            raise ValueError('successor historical replay contract differs')
        normal_audit=audit.get('normal_audit_payload');registry_audit=audit.get('registry_audit_payload')
        if (type(normal_audit) is not dict or normal_audit.get('schema')!=prior.SCHEMA
                or normal_audit.get('historical_controller')!=proof
                or audit.get('normal_audit_identity')!=normal.io.digest(encoded(normal_audit))
                or type(registry_audit) is not dict or registry_audit.get('registry_identity')!=binding.registry_identity
                or audit.get('registry_audit_identity')!=normal.io.digest(encoded(registry_audit))
                or prepared.frame.info.relative_hour!=hour
                or audit.get('decision_identity')!=prepared.decision.decision_identity
                or normal_audit.get('decision_identity')!=prepared.decision.normal.decision_identity
                or audit.get('source_observation_identity')!=current.source_observation_identity
                or audit.get('exogenous_scientific_identity')!=current.exogenous_scientific_identity
                or audit.get('source_action_audit_identity')!=prior.physical._digest(prepared.source_action)
                or audit.get('source_cfe_at_alpha_one_exact')!=prior._ratio(current.source_cfe_at_alpha_one_exact)):
            raise ValueError('successor current projection correspondence differs')
        scientific=json.loads(current.exogenous_scientific_payload)
        if (encoded(scientific)!=current.exogenous_scientific_payload
                or scientific.get('schema')!=prior.SCHEMA or type(scientific.get('relative_hour')) is not int
                or scientific['relative_hour']!=hour or scientific.get('current_decision_identity')!=prepared.decision.decision_identity
                or scientific.get('workload_exact')!=prior._ratio(current.workload_exact)
                or scientific.get('source_cfe_at_alpha_one_exact')!=prior._ratio(current.source_cfe_at_alpha_one_exact)):
            raise ValueError('successor scientific quantity correspondence differs')


def implementation_identity():
    return digest([sha256(Path(__file__).read_bytes()).hexdigest(),
        sha256(Path(batch_source.__file__).read_bytes()).hexdigest(),
        sha256(Path(batch_source.historical.__file__).read_bytes()).hexdigest()])


def _request(manifest,state,current):
    # The predecessor validates the scientific anchor. Its key is explicitly
    # nested under this successor's contract, never used as our outer identity.
    return digest([SCHEMA,'batch_source_replay_v1',saved._request(manifest,state,current)])


def _transition(manifest,state,current,records):
    after,raw=saved._transition(manifest,state,current,records)
    projection=json.loads(raw)
    projection['request_key']=_request(manifest,state,current)
    projection['request_contract']=SCHEMA
    return after,encode(projection)


@dataclass(frozen=True)
class _Capability:
    owner: object
    controller: object
    operation: object
    nonce: object
    creator: tuple
    hour: int
    heads: tuple
    attempt_head: str
    previous_terminal: str
    parent_head: str
    clock_previous: str
    clock_last: int


class PhaseController(normal.Controller):
    """One bootstrap, then only the exact attached owner's active attempt."""
    def __init__(self, *args, **kwargs):
        self._phase_owner = self._phase_scope = None
        self._phase_job_intent = None
        self._bootstrap_used = False
        self._phase_creator = (os.getpid(), get_ident())
        self._phase_code = implementation_identity()
        super().__init__(*args, **kwargs)
        try:
            self._phase_objects = self._objects()
        except BaseException:
            self.close()
            raise

    def _objects(self):
        p = self._parent
        return (p, self._lease, self._clock_lease, self._obligation_lease,
                p._root_lease, p._journal, p._journal._lease, p._anchor, p._anchor._lease, p._network,
                self._obligation_guard, self._clock_guard, self._guard, p._guard)

    def _phase_check(self):
        if (type(self) is not PhaseController or self._phase_creator != (os.getpid(), get_ident())
                or implementation_identity() != self._phase_code
                or any(a is not b for a, b in zip(self._objects(), self._phase_objects, strict=True))):
            raise ValueError('original phase controller objects/process/code required')
        self._check()

    def _scope_check(self):
        self._phase_check()
        scope = self._phase_scope
        if scope == 'bootstrap':
            if self._phase_owner is not None or not self._bootstrap_used or self._clock_index != 0:
                raise ValueError('one fresh bootstrap scope required')
        elif type(scope) is _Capability:
            scope.owner._capability_check(self, scope, after_normal=True)
            if (self._clock_index != scope.hour or self._clock_previous != scope.clock_previous
                    or self._clock_last != scope.clock_last
                    or self._obligation_previous != scope.previous_terminal
                    or self._parent._journal.head != (self._phase_job_intent or scope.parent_head)):
                raise ValueError('active normal predecessor/cursor changed')
        else:
            raise ValueError('owned phase capability required before producer effects')

    def _headroom(self):
        self._scope_check()
        return super()._headroom()

    def _job(self, index, item, pending, anchor):
        scope = self._phase_scope
        if type(scope) is _Capability:
            p = self._parent
            path = p._root/'parent_anchor_non_authoritative'/f'{2*index+1:03d}.json'
            record, _ = normal.base.entry.read(path, anchor)
            if (index != scope.hour or record['previous_registry_head'] != scope.parent_head
                    or p._journal.head != pending['expected_head']):
                raise ValueError('normal intent does not extend the capability parent')
            self._phase_job_intent = pending['expected_head']
        try:
            self._scope_check()
            return super()._job(index, item, pending, anchor)
        finally:
            self._phase_job_intent = None

    def _step_development(self, **kwargs):
        raise ValueError('use owner continuation; detached source identity is not authority')

    def bootstrap_development(self):
        self._phase_check()
        if self._bootstrap_used or self._phase_owner is not None or self._phase_scope is not None:
            raise ValueError('bootstrap already consumed or controller attached')
        self._bootstrap_used = True
        self._phase_scope = 'bootstrap'
        try:
            return self._produce()
        finally:
            self._phase_scope = None

    def _attach(self, owner):
        self._phase_check()
        if (type(owner) is not DevelopmentOwner or self._phase_owner is not None
                or self._phase_scope is not None or self._clock_index != 1
                or owner.binding.root != str(self._lease.root)
                or owner.binding.binding_sha256 != self.obligation_binding_pin
                or owner.binding.genesis_terminal_sha256 != self._obligation_previous):
            raise ValueError('fresh N0 and exact owner binding required')
        self._phase_owner = owner

    def _run_owned(self, owner, cap):
        # Validate before source reads, headroom, clock ticks or bridge calls.
        self._phase_check()
        if owner is not self._phase_owner or self._phase_scope is not None:
            raise ValueError('original idle owner/controller required')
        owner._capability_check(self, cap)
        self._phase_scope = cap
        try:
            return self._produce()
        finally:
            self._phase_scope = None

    def _produce(self):
        self._scope_check()
        p = self._parent
        state, _, _ = p._restore()
        hour = state.completed_hours
        if state.status != 'ready' or hour != self._clock_index:
            raise ValueError('ready normal parent and matching clock cursor required')
        predecessor = (state.head, self._clock_previous, self._obligation_previous)
        # No caller-provided source pin; derive the current declaration here.
        declaration = replace(p._origin, power_raw_hour=p._origin.power_raw_hour+hour,
                              workload_raw_hour=p._origin.workload_raw_hour+hour)
        source = normal.binding.source_binding
        receipt = source.load_pinned_current(declaration, p._upstream_root, config_path=p._config_path)
        self._scope_check()
        if (type(receipt) is not source.H1PinnedObservation or receipt.declaration != declaration
                or receipt.identity != source._identity(receipt)
                or receipt.network.identity != p._network.identity
                or type(receipt.audit_payload) is not bytes
                or (p._restore()[0].head, self._clock_previous, self._obligation_previous) != predecessor):
            raise ValueError('source/normal predecessor changed before release')
        return normal.Controller._step_development(self, expected_source_identity=receipt.identity,
                                                   expected_head=state.head)


class PhaseSelectorProducer:
    """Hour-indexed, fixed Rref -> business -> Actual producer, no callbacks."""
    def __init__(self, budget):
        if type(budget) is not saved.selection.native.capture.GridDevelopmentBudget:
            raise ValueError('exact bounded selector budget required')
        budget.__post_init__()
        if budget.purpose != SELECTOR_PURPOSE:
            raise ValueError('explicit phase selector purpose required')
        self.budget = budget
        self._budget_bytes = encode(budget)
        self._creator = (os.getpid(), get_ident())
        self._solve = saved.selection.native.capture._solve
        self._create_solver = saved.selection.native.capture.create_solver

    def _check(self):
        if (type(self) is not PhaseSelectorProducer or self._creator != (os.getpid(), get_ident())
                or 'produce' in vars(self) or type(self).produce is not _PHASE_PRODUCE
                or encode(self.budget) != self._budget_bytes
                or saved.selection.native.capture._solve is not self._solve
                or saved.selection.native.capture.create_solver is not self._create_solver):
            raise ValueError('selector producer callable/budget/creator changed')

    def produce(self, owner, cap, state, current):
        self._check()
        owner._selector_scope_check(cap, state, current)
        manifest = owner.manifest
        frame, action = current.prepared_current.frame, current.prepared_current.source_action
        selection = saved.selection
        roster = [(saved.RREF, manifest.reference_selector)]+[
            (config.lane, manifest.actual_selector) for config, (_, before) in
            zip(manifest.lanes, state.lanes, strict=True) if not before.halted and not before.completed]
        counts = [len(selection.stage_labels(frame, lane)) for lane, _ in roster]
        specification = manifest.solver_specification
        if (sum(counts) > self.budget.max_solver_calls or specification.time_limit_seconds is None
                or sum(counts)*specification.time_limit_seconds > self.budget.max_total_solver_seconds):
            raise ValueError('aggregate phase selector budget exceeded')
        for (lane, chosen), count in zip(roster, counts, strict=True):
            module = selection.reference if lane.role == 'Rref' else selection.actual
            module._admit(chosen, specification, replace(self.budget, purpose=module.PURPOSE), count)
        spent = 0

        def capture(before, lane, power=None):
            nonlocal spent
            began = time.perf_counter()
            owner._selector_scope_check(cap, state, current)
            chosen = manifest.reference_selector if lane.role == 'Rref' else manifest.actual_selector
            key = selection.input_identity(frame, action, before, lane=lane, power=power)
            frozen, records = (), []
            for i, label in enumerate(selection.stage_labels(frame, lane)):
                self._check()
                owner._selector_scope_check(cap, state, current)
                def builder():
                    return selection.build_development_stage(frame, action, before, lane=lane,
                        power=power, index=i, frozen=frozen, expected_identity=key)
                raw = self._solve(builder, manifest.solver_specification,
                    self.budget, f'{selection.SCHEMA}:{lane.role}:{i}:{label}')
                self._check()
                owner._selector_scope_check(cap, state, current)
                spent += raw.calls
                if (type(raw.calls) is not int or not 0 <= raw.calls <= 1
                        or spent > self.budget.max_solver_calls
                        or spent*specification.time_limit_seconds > self.budget.max_total_solver_seconds):
                    raise ValueError('observed selector call budget exceeded')
                records.append(selection.encode_development_record(frame, action, before, raw,
                    index=i, frozen=frozen, lane=lane, power=power, selector=chosen,
                    specification=manifest.solver_specification, limits=manifest.replay_limits))
                if not raw.optimal:
                    break
                frozen += (raw.objective,)
            owner.stage_timings.append((f'selector:{lane.role}:{lane.arm}', time.perf_counter()-began))
            return tuple(records)

        reference = capture(state.reference, saved.RREF)
        result = saved._replay_selection(manifest, current, state.reference, saved.RREF, reference)
        actual = {key: () for key, _ in state.lanes}
        if result.next_candidate is None:
            # Preserve the failed reference in the durable scientific intent;
            # the unchanged transition rejects it, with zero Actual captures.
            return reference, actual
        g = Q(*map(int, result.candidate_request_exact))
        for config, (key, before) in zip(manifest.lanes, state.lanes, strict=True):
            if before.halted or before.completed:
                continue
            try:
                item = saved.business.current(relative_hour=state.hour, mechanism=config.mechanism,
                    workload=current.workload_exact, source_cfe_at_alpha_one=current.source_cfe_at_alpha_one_exact,
                    grid_request_mw=g)
            except ValueError as exc:
                if str(exc) not in ('positive reference request below business resolution',
                        'raw component and combined activity mismatch',
                        'legacy binary threshold representation mismatch',
                        'exact interface unresolved: no lossless decimal built-in'):
                    raise
                continue
            candidate = saved.business.prepare_development(before.business, item,
                expected_current_identity=item.identity)
            if candidate.next_candidate is None:
                continue
            power = candidate.actual_power_mw
            prescribed = selection.physical.RelativeDcPower(state.hour, str(power.numerator),
                str(power.denominator), 'mechanism_assumption')
            actual[key] = capture(before.actual, config.lane, prescribed)
        owner._selector_scope_check(cap, state, current)
        return reference, actual


_PHASE_PRODUCE = PhaseSelectorProducer.produce


class DevelopmentOwner(saved.DevelopmentOwner):
    """One owner guard from need/attempt through normal and paired outcome."""
    def __init__(self, *args, controller=None, **kwargs):
        _check_source_entry()
        self._live_controller = controller
        self._phase_nonce = self._phase_capability = None
        self._phase_state = self._phase_current = None
        self._post_normal = self._phase_rows = None
        self._post_observations = None
        self._cross_code = implementation_identity()
        self.stage_timings = []
        self.batch_observations = []
        super().__init__(*args, **kwargs)
        if controller is not None:
            try:
                if type(controller) is not PhaseController:
                    raise ValueError('exact phase controller required')
                controller._attach(self)
            except BaseException:
                self.close()
                raise

    def _header_bytes(self):
        return encode(dict(schema=SCHEMA, storage=json.loads(super()._header_bytes()),
            cross_hour_implementation=self._cross_code, producer_contract='single_live_owner_operation',
            source_replay_contract=batch_source.SCHEMA,
            writer_rehydration_implemented=False, formal_result=False))

    def _check(self):
        _check_source_entry()
        super()._check()
        if implementation_identity() != self._cross_code:
            raise ValueError('cross-hour implementation changed')

    def _attempt_body(self, state, rows):
        return dict(super()._attempt_body(state, rows), live_controller_attached=True,
                    producer_contract=SCHEMA)

    def _terminals(self,rows,hour=None,terminal=None):
        terminals={0:self.binding.genesis_terminal_sha256}
        for row in rows:
            if row[2]=='intent':
                body=json.loads(row[3])
                h,pin=body['hour'],body['terminal']
                if type(h) is not int or not 0<=h<192:
                    raise ValueError('bounded exact phase intent required')
                normal.io.pin(pin)
                if h in terminals and terminals[h]!=pin:
                    raise ValueError('intent terminal conflicts with the pinned prefix')
                terminals[h]=pin
        if hour is not None:
            normal.io.pin(terminal)
            if hour in terminals and terminals[hour]!=terminal:
                raise ValueError('current terminal conflicts with the pinned prefix')
            terminals[hour]=terminal
        if set(terminals)!=set(range(max(terminals)+1)):
            raise ValueError('every pinned N predecessor terminal is required')
        return terminals

    def _currents(self,rows,*,hour=None,terminal=None):
        _check_source_entry()
        if len(self.batch_observations)+2>MAX_BATCH_OBSERVATIONS:
            raise ValueError('bounded batch diagnostic observations exhausted')
        began=time.perf_counter()
        terminals=self._terminals(rows,hour,terminal)
        selected=tuple(sorted(terminals)) if hour is None else (hour,)
        source_identity=batch_source.implementation_identity()
        result=_PREPARE_MANY(self.binding.root,
            expected_binding_sha256=self.binding.binding_sha256,
            expected_registry_identity=self.binding.registry_identity,
            expected_terminals=terminals,selected_hours=selected)
        try:
            _check_source_entry()
            if batch_source.implementation_identity()!=source_identity:
                raise ValueError('batch source implementation changed')
            _validate_batch(result,self.binding,terminals,selected,source_identity)
            self.batch_observations.extend(dict(row) for row in result.observations)
            self.stage_timings.append((f'batch_source:{max(terminals)+1}:{len(result.currents)}',time.perf_counter()-began))
            return result.currents
        except BaseException:
            if type(result) is batch_source.CurrentBatch and type(result.currents) is dict:result.currents.clear()
            raise

    def _independent_current(self,rows,hour,terminal):
        return self._currents(rows,hour=hour,terminal=terminal)[hour]

    def _restore(self,rows):
        currents=self._currents(rows)
        try:
            return self._reduce_saved(rows,currents)
        finally:
            currents.clear()

    def _reduce_saved(self,rows,currents):
        initial=currents[0]
        state=saved._initial(self.manifest,initial);states=[state];claims={};conflicts=set();keys=[]
        pending=attempt=None;terminal=False
        for seq,pred,kind,raw,head in rows:
            body=json.loads(raw);prefix=rows[:seq-1]
            if terminal:raise ValueError('suffix after episode terminal')
            if kind=='attempt':
                if pending or attempt or conflicts:raise ValueError('attempt after pending/conflict')
                self._fits(prefix,self._branches())
                if raw!=encode(self._attempt_body(state,prefix)):raise ValueError('attempt differs from replayed need/state')
                attempt=body;continue
            if kind=='episode_terminal':
                if pending or attempt or conflicts:raise ValueError('terminal after pending/conflict')
                if raw!=encode(self._terminal_body(state,prefix)):raise ValueError('episode terminal differs from replay')
                terminal=True;continue
            if kind=='intent':
                if pending is not None or conflicts:raise ValueError('intent after pending/conflict')
                if set(body)!={'hour','terminal','key','source_audit','records','alternate','before_heads'}:
                    raise ValueError('intent schema differs')
                if body['before_heads']!=list(self._heads(prefix)):raise ValueError('intent before heads differ')
                hour=body['hour'];alternate=body['alternate']
                if type(hour) is not int or not 0<=hour<192 or type(alternate) is not bool:
                    raise ValueError('bounded exact phase intent required')
                if alternate:
                    if attempt is not None or not 0<=hour<state.hour:raise ValueError('invalid alternate progress')
                else:
                    if hour!=state.hour or not saved._assessment(state).needs_next_hour:raise ValueError('intent progress differs')
                    if hour==0:
                        if attempt is not None or body['terminal']!=self.binding.genesis_terminal_sha256:
                            raise ValueError('bootstrap must consume fixed N0 terminal')
                        self._fits(prefix,self._branches(True))
                    elif attempt is None:raise ValueError('normal intent lacks pre-source attempt')
                before=states[hour];current=currents[hour]
                if (body['source_audit']!=json.loads(current.source_projection_audit_payload)
                        or body['key']!=_request(self.manifest,before,current)):
                    raise ValueError('intent source or scientific request changed')
                if alternate and body['key']!=keys[hour]:raise ValueError('alternate request differs')
                saved._unpack_records(self.manifest,body['records']);pending=(body,before,current,head)
            elif kind in ('outcome','witness'):
                if pending is None:raise ValueError('outcome without intent')
                intent,before,current,intent_head=pending
                if kind!=('witness' if intent['alternate'] else 'outcome'):raise ValueError('intent/result kind mismatch')
                after,projection=_transition(self.manifest,before,current,saved._unpack_records(self.manifest,intent['records']))
                expected=dict(intent_head=intent_head,key=intent['key'],projection=json.loads(projection),
                    projection_sha256=sha256(projection).hexdigest())
                if body!=expected:raise ValueError('phase outcome does not reproduce saved evidence')
                key=intent['key'];claim=body['projection_sha256']
                if key in claims and claims[key]!=claim:conflicts.add(key)
                else:claims.setdefault(key,claim)
                if kind=='outcome':state=after;states.append(state);keys.append(key);attempt=None
                pending=None
            else:raise ValueError('unknown phase event kind')
        affected=bool(set(keys)&conflicts);assessment=saved._assessment(state)
        continuation=not(pending or attempt or affected or terminal) and assessment.needs_next_hour
        report=saved.PhaseInspection(*self._heads(rows),state.hour,pending is not None,tuple(sorted(conflicts)),
            continuation,tuple((v.lane_id,v.owner_disposition) for v in assessment.lanes),affected,
            pending_attempt=attempt is not None,episode_terminal=terminal)
        return report,state,states

    def _stable_replay(self, expected_heads):
        """One full replay, bookended by exact DB/holder and lease checks."""
        self._check()
        with closing(self._connect()) as db:
            rows = self._rows(db)
        if type(expected_heads) is not tuple or expected_heads != self._heads(rows):
            raise ValueError('both retained owner heads must match')
        tail = self._pending(rows)
        report, state, _ = self._restore(rows)
        if tail is not None:
            self._restore(rows+[tail.event])
        with closing(self._connect()) as db:
            if self._rows(db) != rows or self._pending(rows) != tail:
                raise ValueError('owner/holder changed during replay')
        self._check()
        report = replace(report, continuation_available=report.continuation_available and tail is None,
            recovery_required=tail is not None, prepared_ticket_identity=None if tail is None else tail.identity)
        self.last_candidate_state = state
        return rows, report, state

    def _inspect(self, *, expected_heads):
        return self._stable_replay(expected_heads)[1]

    def _ready_replay(self, expected_heads):
        rows, report, state = self._stable_replay(expected_heads)
        if report.recovery_required or report.pending_intent or report.conflicted_keys or report.episode_terminal:
            raise ValueError('recovery/pending/conflict/terminal blocks mutation')
        return rows, report, state

    def _normal_token(self):
        c = self._live_controller
        c._phase_check()
        c._clock_check()
        if any(value is not None for value in (c._clock_pending, c._active_request,
                                               c._phase_job_intent, c._phase_scope)):
            raise ValueError('idle post-normal controller required')
        return (c._clock_index, c._clock_previous, c._obligation_previous, c._parent._journal.head,
                c._parent._anchor.inspect().record_sha256, c._clock_last,
                encode(asdict(c.last_observation)), encode(asdict(c.last_obligation_observation)))

    def _post_check(self, cap, rows):
        self._check()
        if (cap is not self._phase_capability or cap.owner is not self
                or cap.controller is not self._live_controller or cap.operation is not self._operation
                or not self._operation.locked() or cap.nonce is not self._phase_nonce
                or cap.creator != (os.getpid(), get_ident()) or self._normal_token() != self._post_normal):
            raise ValueError('post-normal capability/cursor changed')
        if (self._live_controller.last_observation is not self._post_observations[0]
                or self._live_controller.last_obligation_observation is not self._post_observations[1]):
            raise ValueError('original normal observation objects required')
        with closing(self._connect()) as db:
            if self._rows(db) != rows or self.heads != self._heads(rows):
                raise ValueError('owner prefix changed after normal')
        attempt = next((r for r in reversed(rows) if r[2] == 'attempt'), None)
        if attempt is None or attempt[4] != cap.attempt_head:
            raise ValueError('post-normal attempt changed')

    def _capability_check(self, controller, cap, *, after_normal=False):
        self._check()
        if (type(cap) is not _Capability or cap is not self._phase_capability
                or cap.owner is not self or cap.controller is not controller
                or controller is not self._live_controller or controller._phase_owner is not self
                or cap.operation is not self._operation or not self._operation.locked()
                or cap.nonce is not self._phase_nonce or cap.creator != (os.getpid(), get_ident())
                or self.heads != cap.heads):
            raise ValueError('original owner operation and one-shot capability required')
        with closing(self._connect()) as db:
            rows = self._rows(db)
        if (not rows or rows[-1][2] != 'attempt' or rows[-1][4] != cap.attempt_head
                or json.loads(rows[-1][3])['hour'] != cap.hour):
            raise ValueError('exact durable pre-source attempt required')
        if not after_normal and (controller._clock_index != cap.hour
                or controller._obligation_previous != cap.previous_terminal
                or controller._clock_previous != cap.clock_previous
                or controller._clock_last != cap.clock_last
                or controller._parent._journal.head != cap.parent_head):
            raise ValueError('normal/clock/terminal predecessor differs')

    def _selector_scope_check(self, cap, state, current):
        if cap is None:  # N0 is already terminal; the owner still holds one guard.
            self._check()
            if not self._operation.locked() or state.hour != 0 or self._phase_capability is not None:
                raise ValueError('bootstrap selector scope required')
        else:
            self._post_check(cap, self._phase_rows)
            if self._live_controller._clock_index != state.hour+1:
                raise ValueError('normal terminal must precede selector')
        if (state is not self._phase_state or current is not self._phase_current
                or current.prepared_current.frame.info.relative_hour != state.hour):
            raise ValueError('exact current and replayed carry required')

    def _paired_locked(self, rows, state, terminal, producer, cap):
        began = time.perf_counter()
        current = self._independent_current(rows, state.hour, terminal)
        self.stage_timings.append(('fresh_current', time.perf_counter()-began))
        self._phase_state, self._phase_current = state, current
        reference, actual = _PHASE_PRODUCE(producer, self, cap, state, current)
        packed = saved._pack_records(self.manifest, reference, actual)
        key = _request(self.manifest, state, current)
        began = time.perf_counter()
        rows = self._append('intent', dict(hour=state.hour, terminal=terminal, key=key,
            source_audit=json.loads(current.source_projection_audit_payload), records=packed,
            alternate=False, before_heads=self._heads(rows)), rows)
        self._phase_rows = rows
        self.stage_timings.append(('intent_and_ticket', time.perf_counter()-began))
        began = time.perf_counter()
        after, projection = _transition(self.manifest, state, current,
                                              saved._unpack_records(self.manifest, packed))
        self.stage_timings.append(('scientific_transition_replay', time.perf_counter()-began))
        # This remains a separate dynamic observation, never a memoized baseline.
        began = time.perf_counter()
        fresh = self._independent_current(rows, state.hour, terminal)
        self.stage_timings.append(('fresh_before_paired', time.perf_counter()-began))
        if (fresh.source_projection_audit_payload != current.source_projection_audit_payload
                or fresh.exogenous_scientific_payload != current.exogenous_scientific_payload):
            raise ValueError('source changed before paired publication')
        if cap is not None:
            self._post_check(cap, rows)
        began = time.perf_counter()
        rows = self._append('outcome', dict(intent_head=rows[-1][4], key=key,
            projection=json.loads(projection), projection_sha256=sha256(projection).hexdigest()), rows)
        self.stage_timings.append(('outcome_and_ticket', time.perf_counter()-began))
        return after, rows

    @saved._serial
    def run_next_development(self, *, expected_heads, selector_producer=None):
        began = time.perf_counter()
        rows, report, state = self._ready_replay(expected_heads)
        self.stage_timings.append(('ready_replay', time.perf_counter()-began))
        if report.pending_attempt:
            raise ValueError('attempt pending; no automatic retry')
        if not saved._assessment(state).needs_next_hour:
            try:
                self._append('episode_terminal', self._terminal_body(state, rows), rows)
                return self._inspect(expected_heads=self.heads)
            except BaseException:
                self.poisoned = True
                raise
        if type(selector_producer) is not PhaseSelectorProducer:
            raise ValueError('exact phase selector producer required')
        PhaseSelectorProducer._check(selector_producer)
        controller = self._live_controller
        if type(controller) is not PhaseController or controller._phase_owner is not self:
            raise ValueError('read-only reopen cannot produce a normal hour')
        controller._phase_check()
        self._reserve_check(rows, bootstrap=state.hour == 0)
        try:
            if state.hour == 0:
                terminal = self.binding.genesis_terminal_sha256
            else:
                rows = self._append('attempt', self._attempt_body(state, rows), rows)
                self._phase_nonce = object()
                previous = json.loads(rows[-1][3])['previous_normal_terminal']
                cap = _Capability(self, controller, self._operation, self._phase_nonce,
                    (os.getpid(), get_ident()), state.hour, self.heads, rows[-1][4], previous,
                    controller._parent._journal.head, controller._clock_previous, controller._clock_last)
                self._phase_capability = cap
                began = time.perf_counter()
                result = controller._run_owned(self, cap)
                self.stage_timings.append(('normal', time.perf_counter()-began))
                observation = controller.last_obligation_observation
                if (result.completed_hours != state.hour+1 or observation is None
                        or observation.relative_hour != state.hour or observation.outcome_head != result.head):
                    raise ValueError('normal terminal does not match owner attempt')
                terminal = observation.terminal_sha256
                token = self._normal_token()
                if (token[0] != state.hour+1 or token[1] != controller.last_observation.terminal_sha256
                        or token[2] != terminal or token[3] != result.head):
                    raise ValueError('normal post-state does not match terminal')
                self._post_normal = token
                self._post_observations = (controller.last_observation, controller.last_obligation_observation)
                self._phase_rows = rows
            began = time.perf_counter()
            self._paired_locked(rows, state, terminal, selector_producer, self._phase_capability)
            self.stage_timings.append(('source_selectors_paired', time.perf_counter()-began))
            self._phase_capability = self._phase_nonce = None
            began = time.perf_counter()
            report = self._inspect(expected_heads=self.heads)
            self.stage_timings.append(('final_full_replay', time.perf_counter()-began))
            return report
        except BaseException:
            self.poisoned = True
            raise
        finally:
            self._phase_capability = self._phase_nonce = None
            self._phase_state = self._phase_current = None
            self._post_normal = self._phase_rows = None
            self._post_observations = None

    def prepare_next(self, **kwargs):
        raise ValueError('use atomic live continuation')

    def complete_saved(self, **kwargs):
        raise ValueError('use atomic live continuation')

    def advance(self, **kwargs):
        raise ValueError('use atomic live continuation')
