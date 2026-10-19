"""Three isolated N0 proof slots within one original guarded Handoff operation.

Cross-common reuse activates only after the complete first common returns.
No paired consumption, durable write, native call or formal authority is issued.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass
from functools import wraps
from pathlib import Path
from secrets import token_hex
import json
import os
import sys
import threading
import types
import weakref

from experiments import h1_historical_hour_witness_development_v1 as prior_witness
from experiments import h1_historical_n0_verifier_development_v1 as prior_verifier
from experiments import h1_common_validation_operation_development_v3 as operation_bridge

legacy=prior_verifier.legacy
old,history,current=legacy.old,legacy.history,legacy.current
io,binding,bridge,base=legacy.io,legacy.binding,legacy.bridge,legacy.base
parent,hour,worker=prior_witness.parent,prior_witness.hour,prior_witness.worker
SCHEMA=legacy.SCHEMA
VERIFIER_SCHEMA='h1_operation_historical_witness_development_v4'
implementation_identity=legacy.implementation_identity
_observe,_observe_sources,_observe_prefix=legacy._observe,legacy._observe_sources,legacy._observe_prefix
_obligation_inventory=legacy._obligation_inventory
_CONTEXT=prior_witness._HourScope._context
_dispatch_view=prior_witness._dispatch_view
_freeze=prior_witness._freeze
inspect_bridge,inspect_job=prior_witness.inspect_bridge,prior_witness.inspect_job
_CHILD_TOKEN=object()
_ENVELOPE_TOKEN=object()


def _copy_context(view):
    # The original context's first eight entries are recursively immutable
    # source/dispatch views. Only the two snapshot maps need an owned copy.
    if type(view) is not tuple or len(view)!=9:raise ValueError('complete predecessor context required')
    return (*view[:8],deepcopy(view[8]))


def _context_key(view):
    if type(view) is not tuple or len(view)!=9:raise ValueError('complete predecessor context required')
    return view[:8],_freeze(view[8])


def _identity_literal(value):
    """Canonical JSON representation of the literal predecessor context."""
    if type(value) is bytes:return ['bytes',value.hex()]
    if type(value) is tuple:return ['tuple',[_identity_literal(v) for v in value]]
    if type(value) in (str,int,bool,type(None)):return [type(value).__name__,value]
    raise TypeError('immutable literal proof identity required')


def verifier_identity():
    return io.digest(io.encode([VERIFIER_SCHEMA,io.digest(Path(__file__).read_bytes()),
        prior_verifier.verifier_identity()]))


@dataclass(frozen=True,init=False)
class VerifiedHistoricalEnvelope(prior_witness._PrivateResult):
    decision: current.H1CurrentInformation
    audit_payload: bytes
    verifier_identity: str
    full_numerical_hour_replays: int
    fresh_byte_context_revalidations: int
    execution_receipt: bytes
    envelope_identity: str

    def __init__(self,decision,audit,identity,full,fresh,execution,*,_token=None,_operation=None,_ticket=None):
        if _token is not _ENVELOPE_TOKEN:raise TypeError('owned diagnostic envelope required')
        if type(decision) is not current.H1CurrentInformation or type(audit) is not bytes:
            raise TypeError('exact historical science required')
        parsed=json.loads(audit)
        if (io.encode(parsed)!=audit or parsed['schema']!=SCHEMA
                or parsed['implementation']!=implementation_identity()
                or identity!=verifier_identity()
                or parsed['decision_identity']!=decision.decision_identity
                or any(parsed[key] is not False for key in ('policy_visible','common_prefix_publication_verified',
                    'detached_consumer_authenticated','reference_or_actual_ready','formal_execution_ready',
                    'formal_result','resource_admission','native_execution_authorized'))):
            raise ValueError('historical diagnostic scientific projection differs')
        if (full,fresh) not in ((4,4),(0,8)):raise ValueError('honest diagnostic work counts required')
        if type(_operation) is not ArmWitness:raise TypeError('owned diagnostic operation required')
        _operation._check(_ticket)
        expected=_operation._execution(decision,audit,identity,full,fresh)
        if execution!=expected:
            raise ValueError('diagnostic projection/execution binding differs')
        for key,value in (('decision',decision),('audit_payload',audit),('verifier_identity',io.pin(identity)),
                ('full_numerical_hour_replays',full),('fresh_byte_context_revalidations',fresh),
                ('execution_receipt',execution),('envelope_identity',io.digest(io.encode(
                    [VERIFIER_SCHEMA,identity,io.digest(audit),io.digest(execution)])))):
            object.__setattr__(self,key,value)
        _operation._check(_ticket)

    @property
    def audit_identity(self):return io.digest(self.audit_payload)


class ArmWitness(prior_witness._PrivateResult):
    """Private per-arm slot authenticated by its original grouped operation."""
    def __init__(self,root,*,arm_id,expected_binding_sha256,expected_terminal_sha256,
            completed_hours=1,reuse_numerical_proof=True,_session=None):
        _runtime_check()
        if type(_session) is not GroupWitnessSession:raise TypeError("original grouped witness session required")
        self._session=_session
        root=Path(root)
        if not root.is_absolute() or root!=root.resolve(strict=True):
            raise ValueError('canonical saved controller root required')
        if type(arm_id) is not str or not arm_id or len(arm_id)>64 or type(completed_hours) is not int or completed_hours!=1:
            raise ValueError('one explicit diagnostic N0 arm required')
        if type(reuse_numerical_proof) is not bool:raise TypeError('explicit diagnostic mode required')
        self._exact_root=str(root)
        if str(root.resolve(strict=True))!=self._exact_root:raise ValueError('exact canonical root spelling required')
        self._declaration=(root,arm_id,io.pin(expected_binding_sha256),io.pin(expected_terminal_sha256),
            completed_hours,reuse_numerical_proof)
        self._fixed_declaration=self._declaration
        self._owner=(os.getpid(),threading.get_ident())
        self._guard=self._original_guard=threading.Lock()
        self._state='new';self._attempts=0;self._ticket=None;self._proof=None;self._pending=[]
        self._rows=[];self._failure=None;self._contexts=0
        self._nonce=self._original_nonce=object();self._ended=False
        self._public_session=self._original_public_session=token_hex(32)
        self._active_scope=None;self._site=0;self._site_ticket=None;self._context_edge=0
        self._science_basis=None;self._prepare_context_start=0;self._validation_identity=None
        self._context_function=_CONTEXT;self._context_code=_CONTEXT.__code__

    def __enter__(self):
        if self._state!='new' or not self._guard.acquire(False):raise ValueError('single-use diagnostic operation required')
        self._state='active'
        try:self._check()
        except BaseException as error:
            self._poison(error);self.close();raise
        return self

    def _check(self,ticket=None):
        _runtime_check()
        self._session._check_arm(self)
        if (self._failure is not None or self._state not in ('active','preparing')
                or (os.getpid(),threading.get_ident())!=self._owner
                or self._guard is not self._original_guard or not self._original_guard.locked()
                or self._declaration!=self._fixed_declaration
                or str(self._declaration[0])!=self._exact_root
                or self._nonce is not self._original_nonce or self._ended
                or self._public_session!=self._original_public_session
                or _CONTEXT is not self._context_function or _CONTEXT.__code__ is not self._context_code
                or (ticket is not None and ticket is not self._ticket)):
            raise ValueError('diagnostic historical operation lifetime changed')

    def _poison(self,error):
        if self._failure is None:self._failure=repr(error)
        self._proof=None;self._pending.clear();self._state='failed'
        self._science_basis=None
        self._active_scope=self._site_ticket=None

    def _start(self):
        self._check()
        if self._state!='active' or self._attempts>=2*self._session._limit:raise ValueError('bounded nonreentrant arm prepares required')
        self._session._start_arm(self)
        self._state='preparing';self._ticket=object();self._pending=[]
        self._prepare_context_start=self._contexts
        return self._ticket

    def _seed(self,ticket,prefix_index,scope):
        self._check(ticket)
        if (prefix_index!=len(self._pending) or prefix_index not in (0,1) or self._active_scope is not None
                or str(scope._root)!=self._exact_root):raise ValueError('diagnostic prefix order or root changed')
        self._active_scope=scope;self._site=0;self._site_ticket=None;self._context_edge=0
        if not self._declaration[-1] or not self._session._reuse_active or self._proof is None:return None
        context,frozen,result,context_key,owner,index,declaration=self._proof[prefix_index]
        if (owner is not self._nonce or index!=prefix_index or declaration!=self._fixed_declaration
                or _freeze(result)!=frozen or _context_key(context)!=context_key):
            raise ValueError('retained numerical proof changed')
        return _copy_context(context),frozen,deepcopy(result)

    def _begin_site(self,scope):
        self._check(scope._ticket)
        if (self._active_scope is not scope or self._site_ticket is not None or not 0<=self._site<4
                or scope._promoted!=(self._site>=2)):
            raise ValueError('operation inspection site order changed')
        self._site_ticket=object();self._context_edge=0
        return self._site_ticket

    def _observed_context(self,scope,site_ticket,edge):
        self._check(scope._ticket)
        if (self._active_scope is not scope or self._site_ticket is not site_ticket
                or self._context_edge!=edge or edge not in (0,1)):
            raise ValueError('operation context observation order changed')
        self._contexts+=1;self._context_edge+=1

    def _end_site(self,scope,site_ticket):
        self._check(scope._ticket)
        if self._active_scope is not scope or self._site_ticket is not site_ticket or self._context_edge!=2:
            raise ValueError('operation inspection site incomplete')
        self._site+=1;self._site_ticket=None

    def _record_prefix(self,ticket,prefix_index,scope):
        self._check(ticket)
        if (prefix_index!=len(self._pending) or not scope._promoted or scope._value is None
                or scope._baseline is None or scope._operation is not self or scope._ticket is not ticket
                or self._active_scope is not scope or self._site!=4 or self._site_ticket is not None
                or scope._promotions!=(2,4)):
            raise ValueError('complete owned prefix required')
        expected=(0,4) if scope._borrowed else (2,2)
        if (scope.full_calls,scope.revalidation_calls)!=expected:raise ValueError('honest prefix work counts differ')
        context=_copy_context(scope._baseline);frozen,value=scope._value
        if _freeze(value)!=frozen:raise ValueError('prefix numerical proof changed')
        self._pending.append((context,frozen,deepcopy(value),*expected,_context_key(context)))
        self._active_scope=None

    def _basis(self,decision,audit):
        if len(self._pending)!=2 or self._contexts-self._prepare_context_start!=16:
            raise ValueError('two complete prefixes and sixteen context evaluations required')
        science=(decision.decision_bytes,audit)
        identity=io.digest(io.encode([VERIFIER_SCHEMA,self._exact_root,self._fixed_declaration[1:5],
            io.digest(science[0]),io.digest(science[1]),
            *[io.digest(io.encode(_identity_literal((index,row[5],row[1]))))
                for index,row in enumerate(self._pending)]]))
        basis=(*science,identity,self._nonce)
        if self._science_basis is not None and basis!=self._science_basis:
            raise ValueError('first complete historical scientific proof differs')
        return basis

    def _execution(self,decision,audit,own,full,fresh):
        root,arm,binding_pin,terminal_pin,hours,reuse=self._fixed_declaration
        ordinal=self._attempts+1;basis=self._basis(decision,audit)
        expected_counts=(0,8) if reuse and self._session._reuse_active else (4,4)
        if (full,fresh)!=expected_counts:raise ValueError('diagnostic mode execution counts differ')
        active=io.digest(io.encode([own,self._exact_root,arm,binding_pin,terminal_pin,reuse]))
        if self._validation_identity is not None and active!=self._validation_identity:
            raise ValueError('active diagnostic validation identity changed')
        return io.encode(dict(schema=VERIFIER_SCHEMA,diagnostic_owner_only=True,
            compatibility_payload_scope='historical_scientific_projection_only',
            active_validation_identity=active,
            declared_arm_label=arm,arm_label_authenticated=True,controller_root_exact=self._exact_root,
            controller_binding_sha256=binding_pin,controller_terminal_sha256=terminal_pin,completed_hours=hours,
            session_identity=self._session._public_session,prepare=ordinal,mode='operation' if reuse else 'full_only',
            proof_basis_identity=basis[2],proof_role='consumed' if expected_counts[0]==0 else 'staged_full',
            common_call=self._session._common_calls+1,
            full_numerical_hour_replays=full,reused_numerical_inspections_total=fresh,
            within_prefix_revalidations=4 if full else 0,cross_prepare_proof_reuses=0 if full else 8,
            context_evaluations=16,decision_sha256=io.digest(decision.decision_bytes),
            predecessor_audit_sha256=io.digest(audit),formal_result=False,resource_admission=False,
            native_execution_authorized=False,production_handoff_integrated=False))

    def _finish(self,ticket,decision,audit,*,envelope=None):
        self._check(ticket)
        if len(self._pending)!=2:raise ValueError('two complete prefixes required before proof commit')
        left,right=self._pending
        if left[:3]!=right[:3]:raise ValueError('independent prefix numerical proofs differ')
        full=sum(row[3] for row in self._pending);fresh=sum(row[4] for row in self._pending)
        if (full,fresh) not in ((4,4),(0,8)):raise ValueError('diagnostic prepare count differs')
        basis=self._basis(decision,audit)
        execution=None
        if envelope is not None:
            if (type(envelope) is not VerifiedHistoricalEnvelope or envelope.decision is not decision
                    or envelope.audit_payload!=audit or (envelope.full_numerical_hour_replays,
                        envelope.fresh_byte_context_revalidations)!=(full,fresh)):
                raise ValueError('complete diagnostic envelope required before proof commit')
            execution=json.loads(envelope.execution_receipt)
            if envelope.execution_receipt!=self._execution(decision,audit,envelope.verifier_identity,full,fresh):
                raise ValueError('diagnostic execution receipt changed before proof commit')
        if self._proof is None:
            if (full,fresh)!=(4,4):raise ValueError('four full checks required before proof commit')
            self._proof=tuple((_copy_context(row[0]),row[1],deepcopy(row[2]),row[5],self._nonce,index,self._fixed_declaration)
                for index,row in enumerate(self._pending))
        elif any((row[0],row[1],row[2],row[5])!=proof[:4] or proof[4] is not self._nonce
                or proof[5]!=index or proof[6]!=self._fixed_declaration
                for index,(row,proof) in enumerate(zip(self._pending,self._proof))):
            raise ValueError('committed numerical proof differs')
        self._science_basis=basis
        if execution is not None:self._validation_identity=execution['active_validation_identity']
        self._rows.append(dict(prepare=self._attempts+1,full_numerical_hour_replays=full,
            fresh_byte_context_revalidations=fresh,decision_sha256=io.digest(decision.decision_bytes),
            predecessor_audit_sha256=io.digest(audit),context_evaluations=16,proof_basis_identity=basis[2],
            active_validation_identity=self._validation_identity,
            envelope_identity=None if envelope is None else envelope.envelope_identity,
            execution_receipt_sha256=None if envelope is None else io.digest(envelope.execution_receipt),
            public_envelope_committed=envelope is not None,
            within_prefix_revalidations=4 if full else 0,cross_prepare_proof_reuses=0 if full else 8,
            prefixes=[dict(prefix=i,full=row[3],within_prefix_revalidations=row[4] if row[3] else 0,
                cross_prepare_proof_reuses=0 if row[3] else row[4],context_evaluations=8)
                for i,row in enumerate(self._pending)]))
        self._attempts+=1;self._ticket=None;self._pending=[];self._state='active'
        self._session._finish_arm(self,envelope)
        return full,fresh

    def prepare(self,*,expected_registry_identity):
        return operation_bridge._SOURCE_ENTRY(self._session._lease,self,expected_registry_identity)

    def close(self):
        if self._ended:return
        if (os.getpid(),threading.get_ident())!=self._owner:
            raise ValueError('diagnostic operation close must remain on owner thread')
        self._proof=self._science_basis=None;self._pending.clear();self._ticket=None
        self._active_scope=self._site_ticket=None;self._nonce=None
        self._state='closed';self._ended=True
        if self._original_guard.locked():self._original_guard.release()

    def __exit__(self,kind,value,tb):
        if value is not None:self._poison(value)
        self.close()

    def receipt(self):
        public_complete=self._attempts==2*self._session._limit and self._failure is None and all(
            row['public_envelope_committed'] for row in self._rows)
        closed=self._ended and self._state=='closed' and self._proof is None and not self._pending
        closed=closed and self._ticket is None and not self._original_guard.locked()
        return dict(schema=VERIFIER_SCHEMA,diagnostic_owner_only=True,production_handoff_integrated=False,
            declared_arm_label=self._fixed_declaration[1],arm_label_authenticated=True,
            controller_root_exact=self._exact_root,controller_binding_sha256=self._fixed_declaration[2],
            controller_terminal_sha256=self._fixed_declaration[3],
            mode='operation' if self._fixed_declaration[-1] else 'full_only',
            active_validation_identity=self._validation_identity,
            session_identity=self._session._public_session,
            completed_prepares=self._attempts,prepares=deepcopy(self._rows),context_observations=self._contexts,
            first_failure=self._failure,closed=self._ended,proof_cleared=self._proof is None,
            prepares_complete=self._attempts==2*self._session._limit and self._failure is None,
            complete=closed and public_complete,
            public_envelopes_complete=public_complete,
            helper_metadata_discovery_cache=False,formal_result=False,resource_admission=False,
            formal_execution_ready=False,native_execution_authorized=False)


class _OperationHourScope(prior_witness._HourScope):
    def __init__(self,root,leases,*,caller,_operation,_ticket,_prefix_index):
        self._operation,self._ticket,self._prefix_index=_operation,_ticket,_prefix_index
        super().__init__(root,leases,caller=caller)
        seed=_operation._seed(_ticket,_prefix_index,self)
        self._borrowed=seed is not None
        self._promotions=()
        if seed is not None:self._baseline,self._value=seed[0],(seed[1],seed[2])

    def _confirmed(self):
        self._operation._check(self._ticket)
        self._check()
        return self.full_calls==2 or (self._borrowed and self.full_calls==0 and self.revalidation_calls>=2)

    def _inspect(self,root,packet,specification,limits,**pins):
        try:
            site_ticket=self._operation._begin_site(self)
            before=_CONTEXT(self,root,packet,specification,limits,pins)
            self._operation._observed_context(self,site_ticket,0)
            if self._baseline is not None and before!=self._baseline:raise ValueError('operation numerical context changed')
            if not self._borrowed and not self._promoted:
                if self.full_calls>=2:raise ValueError('unconfirmed numerical witness cannot be reused')
                result=hour.inspect(root,packet,specification,limits,**pins);self.full_calls+=1
                frozen=_freeze(result)
                if self._value is not None and frozen!=self._value[0]:raise ValueError('independent full numerical results differ')
                self._value=frozen,deepcopy(result)
            else:
                limit=4 if self._borrowed else 2
                if ((not self._borrowed and self.full_calls!=2) or self.revalidation_calls>=limit
                        or (self._borrowed and not self._promoted and self.revalidation_calls>=2)):
                    raise ValueError('numerical witness use count exceeded')
                if _freeze(self._value[1])!=self._value[0]:raise ValueError('retained numerical result changed')
                result=deepcopy(self._value[1]);result['full_hour_chain_recomputed']=False
                self.revalidation_calls+=1
            after=_CONTEXT(self,root,packet,specification,limits,pins)
            self._operation._observed_context(self,site_ticket,1)
            if after!=before:raise ValueError('numerical witness inputs changed during use')
            self._baseline=before
            self._operation._end_site(self,site_ticket)
            return result
        except BaseException as error:
            self._poisoned=True;self._value=self._baseline=None;self._operation._poison(error)
            raise

    def promote(self,result):
        self._operation._check(self._ticket)
        self._check()
        if (type(result) is not RevalidatedChildInspection or not self._confirmed()
                or result._scope_nonce is not self._nonce or self._value is None
                or result.projection.payload!=self._value[1]['projection_payload']):
            raise ValueError('complete accepted operation child required')
        site=self._operation._site
        if (self._operation._active_scope is not self or self._operation._site_ticket is not None
                or (self._promotions,site) not in (((),2),((2,),4))):
            raise ValueError('operation promotion site order changed')
        self._promotions+=site,
        self._promoted=True


@dataclass(frozen=True,init=False)
class RevalidatedChildInspection(prior_witness._PrivateResult):
    status: str
    head: str
    archive_identity: str
    stored_reports: int
    projection: parent.Projection

    def __init__(self,status,head,archive_identity,stored_reports,projection,*,_token=None,_scope=None):
        if _token is not _CHILD_TOKEN or type(_scope) is not _OperationHourScope:
            raise TypeError('owned operation child construction required')
        _scope._check()
        if (status!='accepted' or io.pin(head)!=io.pin(archive_identity)
                or type(stored_reports) is not int or not 1<=stored_reports<=232
                or type(projection) is not parent.Projection or not _scope._confirmed()
                or projection.projection_identity!=io.digest(io.encode([parent.CHILD_SCHEMA,io.digest(projection.payload)]))
                or _scope._value is None or projection.payload!=_scope._value[1]['projection_payload']):
            raise ValueError('owned operation child fields differ')
        for name,value in (('status',status),('head',head),('archive_identity',archive_identity),
                ('stored_reports',stored_reports),('projection',projection),('_scope_nonce',_scope._nonce)):
            object.__setattr__(self,name,value)


# The adapter and minimal verifier bodies below are mechanically copied from
# the predecessor, retaining their source/registry/Job/clock/Parent observations.


witness=sys.modules[__name__]


class ChildReference(prior_witness.ChildReference):
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
            len(hour.prior.native.model_api.stage_order(packet.inputs)), projection,
            _token=_CHILD_TOKEN, _scope=self._scope)


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


def _close_prefix_resources(scope,reader,leases,body_error):
    errors=[]
    for resource in (scope,reader,*reversed(leases)):
        if resource is None:continue
        try:resource.close()
        except BaseException as error:errors.append(error)
    if errors:
        if body_error is not None:
            for error in errors:body_error.add_note('historical diagnostic cleanup: '+repr(error))
        else:
            for error in errors[1:]:errors[0].add_note('additional cleanup failure: '+repr(error))
            raise errors[0]


def _replay_prefix(root,*,expected_binding_sha256,expected_terminal_sha256,completed_hours,_observed=None,_operation,_ticket,_prefix_index):
    if type(completed_hours) is not int or completed_hours != 1: raise ValueError('N0 witness only')
    old.additional_content_bound(completed_hours)
    root=history.chunks.base.local._path(Path(root).absolute())
    own=implementation_identity();old_identity=old.implementation_identity()
    directory=root/'obligation_non_authoritative';clock=root/'clock_bridge_non_authoritative'
    observed={} if _observed is None else _observed
    leases=[];views=observed.setdefault('views',{});topology=observed.setdefault('topology',{})
    obligation_names=observed.setdefault('obligation_names',{});identities=observed.setdefault('identities',{})
    captured={};evidence={}
    def read(path,pin):
        before=history.chunks.base.local._file_identity(path)
        value,view=base.entry.read(path,pin,old.CAP)
        if history.chunks.base.local._file_identity(path)!=before:raise ValueError('historical evidence replaced')
        if path in views and views[path]!=(old.CAP,view):raise ValueError('retained evidence changed')
        views[path]=(old.CAP,view)
        evidence[str(path.relative_to(root))]=pin
        return value
    def inventory():
        for lease in leases:lease.check()
        _obligation_inventory(directory,completed_hours,obligation_names)
        for path,base_names,pattern,low in (
            (root,{'execution.lock','source_parent_non_authoritative','obligation_non_authoritative','clock_bridge_non_authoritative'},r'job_([0-9]{3})_non_authoritative',0),
            (clock,{'execution.lock','binding.json'},r'([0-9]{3})',0),
        ):
            found=history._inventory(path,base_names,pattern=pattern,low=low,high=191,directories=True,retained=topology)
            if not set(range(completed_hours))<=found:raise ValueError('historical Job/clock prefix missing')
    reader=None;scope=None
    try:
        for path in (root,directory,clock,root/'source_parent_non_authoritative'):
            lease=history.prior.ReadView(path);leases.append(lease)
            _observe(identities,'lease '+str(path),(lease.directory_identity,lease.lock_identity))
        scope=_OperationHourScope(root,leases,caller=sys.modules[__name__],_operation=_operation,_ticket=_ticket,_prefix_index=_prefix_index)
        inventory()
        header=read(directory/'binding.json',expected_binding_sha256)
        declaration=header['parent_declaration'];budget=base.old.process.TaskProcessBudget(**header['budget'])
        budget.__post_init__()
        _observe_sources(identities,declaration)
        resolver=binding.open_manifest()
        node=binding.precheck(resolver,declaration,family=header['family'],ordinal=header['ordinal'],relative_hour=0)
        if not io.same(header,dict(schema=old.SCHEMA,implementation=old_identity,parent_declaration=declaration,
                parent_identity=io.digest(io.encode(declaration)),manifest_sha256=resolver.identity,
                family=header['family'],ordinal=header['ordinal'],hours=192,budget=asdict(budget),
                clock_binding_sha256=io.pin(header['clock_binding_sha256']),**old.FLAGS)):
            raise ValueError('historical obligation header differs')
        if declaration['hours']!=192 or Path(declaration['root'])!=root/'source_parent_non_authoritative':
            raise ValueError('historical obligation parent path/horizon differs')
        enrollment=binding.prevalidate_enrollment(resolver,declaration,family=header['family'],ordinal=header['ordinal'],relative_hour=0)
        records={};next_pin=io.pin(expected_terminal_sha256)
        for hour in reversed(range(completed_hours)):
            terminal=read(directory/f'{hour:03d}.terminal.json',next_pin)
            link=read(directory/f'{hour:03d}.job.json',terminal['job_link_sha256'])
            joined=read(directory/f'{hour:03d}.binding.json',link['obligation_binding_sha256'])
            if (not io.same(link,dict(schema=old.SCHEMA,obligation_binding_sha256=link['obligation_binding_sha256'],job_pins=link['job_pins'],**old.FLAGS))
                    or not io.same(terminal,dict(schema=old.SCHEMA,previous_sha256=terminal['previous_sha256'],
                        job_link_sha256=terminal['job_link_sha256'],clock_terminal_sha256=terminal['clock_terminal_sha256'],
                        parent_head=terminal['parent_head'],parent_anchor_sha256=terminal['parent_anchor_sha256'],
                        relative_hour=hour,controller_live_join_checked=True,**old.FLAGS))):
                raise ValueError('historical obligation chain differs')
            records[hour]=terminal,link,joined;next_pin=terminal['previous_sha256']
        if next_pin!=expected_binding_sha256:raise ValueError('historical obligation genesis differs')

        class Reader(legacy.HistoricalTimedSnapshot):
            def _outcome(self,hour,intent_head,result):
                return witness.outcome(self,hour,intent_head,result,scope=scope)
            def _child(self,hour,packet,intent_head,lineage,*,expected_head,create=False):
                terminal,link,joined=records[hour]
                request=read(root/f'job_{hour:03d}_non_authoritative'/'request.json',link['job_pins']['request.json'])
                if not io.same(request['budget'],header['budget']):raise ValueError('historical episode budget differs')
                expected=old._historical_binding(packet,request,node,enrollment)
                if not io.same(joined,dict(schema=old.SCHEMA,implementation=old_identity,obligation=expected,
                        expected_worker_request_sha256=link['job_pins']['request.json'],**old.FLAGS)):
                    raise ValueError('historical obligation packet/request differs')
                ct=read(clock/f'{hour:03d}'/'terminal.json',terminal['clock_terminal_sha256'])
                if (ct['job_pins']!=link['job_pins'] or ct['outcome_head']!=terminal['parent_head']
                        or ct['outcome_anchor_sha256']!=terminal['parent_anchor_sha256']):
                    raise ValueError('historical obligation clock/outcome differs')
                witness.inspect_bridge(clock,hour,packet,self._spec,self._limits,scope=scope,binding_pin=header['clock_binding_sha256'],
                    intent_pin=ct['intent_sha256'],terminal_pin=terminal['clock_terminal_sha256'])
                if create is not False: raise ValueError('historical reference is read only')
                return witness.ChildReference(self._root/f'hour_{hour:03d}_non_authoritative',
                    self._root.parent/f'job_{hour:03d}_non_authoritative',packet,self._spec,self._limits,
                    parent_declaration=self._declaration,intent_head=intent_head,lineage=lineage,
                    expected_head=expected_head,scope=scope)

            def _after(self,packet,result):
                if type(result) is not witness.RevalidatedChildInspection or result.status!='accepted':
                    raise ValueError('accepted timed child required')
                count=len(binding.replay.native.model_api.stage_order(packet.inputs))
                if (result.stored_reports!=count or type(result.projection) is not current.parent.Projection
                        or result.projection.projection_identity!=io.digest(io.encode([current.parent.CHILD_SCHEMA,io.digest(result.projection.payload)]))):
                    raise ValueError('complete normal projection differs')
                after=witness.after(self,packet,result,scope=scope)
                scope.promote(result)
                if packet.relative_hour==completed_hours-1:captured.update(packet=packet,result=result,after=after,count=count)
                return after

        terminal=records[completed_hours-1][0]
        with history.replay.guard.solver_calls_forbidden():
            first_request=read(root/'job_000_non_authoritative'/'request.json',records[0][1]['job_pins']['request.json'])
            stages=first_request['input_receipt']['stage_slots']
            if type(stages) is not int or not 1<=stages<=232:raise ValueError('bounded stage count required')
            _observe_prefix(identities,root,completed_hours,stages)
            reader=Reader(declaration,completed_hours=completed_hours,expected_parent_identity=header['parent_identity'],
                expected_parent_head=terminal['parent_head'],expected_anchor_record=terminal['parent_anchor_sha256'])
            state=reader.inspect()
            if (state.completed_hours!=completed_hours or state.status!=('complete' if completed_hours==192 else 'ready')
                    or state.head!=terminal['parent_head'] or not captured):
                raise ValueError('historical accepted controller prefix differs')
            base.entry.unchanged(views);inventory()
            _observe_prefix(identities,root,completed_hours,stages)
            _observe_sources(identities,declaration)
            if implementation_identity()!=own:raise ValueError('historical controller implementation drift')
            result=dict(completed_hours=completed_hours,parent_head=state.head,
                evidence_identity=io.digest(io.encode(evidence)),historical_parent_prefix_verified=True,
                historical_obligation_prefix_verified=True,historical_job_clock_prefix_verified=True,
                suffix_chain_verified=False,current_latest_parent_verified=False,current_latest_obligation_verified=False,
                live_release_authenticated=False,live_handoff_authenticated=False,writer_lock_authenticated=False,
                persistent_lane_owner_implemented=False,detached_consumer_authenticated=False,
                common_prefix_publication_verified=False,reference_or_actual_ready=False,**old.FLAGS)
            _operation._record_prefix(_ticket,_prefix_index,scope)
            return result,captured,header
    finally:
        _close_prefix_resources(scope,reader,leases,sys.exc_info()[1])


def _projection(root,*,expected_binding_sha256,expected_terminal_sha256,completed_hours,_operation,_ticket):
    """Current-only information rebuilt twice from externally pinned N history."""
    own=implementation_identity()
    args=dict(expected_binding_sha256=expected_binding_sha256,expected_terminal_sha256=expected_terminal_sha256,
        completed_hours=completed_hours)
    observed={}
    first,captured,header=_replay_prefix(root,**args,_observed=observed,_operation=_operation,_ticket=_ticket,_prefix_index=0)
    packet,result,after=captured['packet'],captured['result'],captured['after']
    decision=current._decision(packet,after)
    projection=current.json.loads(result.projection.payload)
    audit=io.encode(dict(schema=SCHEMA,implementation=own,decision_identity=decision.decision_identity,
        parent_declaration=header['parent_declaration'],controller_header_sha256=expected_binding_sha256,
        controller_terminal_sha256=expected_terminal_sha256,normal_input_identity=packet.input_identity,
        packet_audit_identity=packet.audit_identity,source_timestamp=packet.source_timestamp,
        source_time_basis=packet.source_time_basis,child_head=result.head,child_archive_identity=result.archive_identity,
        projection_identity=result.projection.projection_identity,projection_payload_sha256=io.digest(result.projection.payload),
        normal_request_key=binding.replay.request_key(packet,history.prior.Rq2SolverSpec(**header['parent_declaration']['specification']),
            history.replay.H1HourReplayLimits(**header['parent_declaration']['limits'])),
        normal_before=asdict(packet.before),normal_after=asdict(after),canonical_locks=projection['value']['canonical_locks'],
        completed_stages=captured['count'],policy_visible=False,historical_controller=first,
        common_prefix_publication_verified=False,detached_consumer_authenticated=False,
        reference_or_actual_ready=False,formal_execution_ready=False,formal_result=False,resource_admission=False,
        native_execution_authorized=False))
    if len(audit)>binding.CAP:raise ValueError('historical information audit byte cap')
    second,fresh,fresh_header=_replay_prefix(root,**args,_observed=observed,_operation=_operation,_ticket=_ticket,_prefix_index=1)
    if (first!=second or header!=fresh_header or decision.decision_bytes!=current._decision(fresh['packet'],fresh['after']).decision_bytes
            or implementation_identity()!=own):
        raise ValueError('historical current prefix changed during preparation')
    return decision,audit


def _install_runtime_checks():
    """Fix dispatch at module definition, rather than first caller use.

    The small direct binding check brackets adapters. The complete original
    project dispatch/source view additionally brackets entry, preparation and
    proof publication. Neither replaces any original context evaluation.
    Change-and-restore between observations remains outside this contract.
    """
    namespace=globals();module=sys.modules[__name__]
    owner_type=ArmWitness;scope_type=_OperationHourScope
    owner_check=owner_type._check;poison=owner_type._poison
    dispatch=_dispatch_view;denial=hour.prior.guard.solver_calls_forbidden
    expected=();baseline=None

    def state(value):
        if type(value) is types.FunctionType:
            return id(value),id(value.__code__),repr(value.__defaults__),repr(value.__kwdefaults__)
        return id(value),

    def check(full=False):
        for target,name,value,identity in expected:
            live=target.get(name) if type(target) is dict else vars(target).get(name)
            if live is not value or state(live)!=identity:
                raise ValueError('definition-time historical dispatch changed: '+name)
        if full:
            with denial():observed=dispatch(module)
            if observed!=baseline:raise ValueError('definition-time historical project/source view changed')

    def guard(fn,kind,*,full=False,enter=False):
        @wraps(fn)
        def checked(*args,**kwargs):
            owner=None
            if kind in ('self','closed'):
                first=args[0]
                owner=first if type(first) is owner_type else getattr(first,'_operation',None)
            elif kind=='scope':
                scope=kwargs.get('_scope',kwargs.get('scope'))
                if scope is None and args:scope=getattr(args[0],'_scope',None)
                owner=getattr(scope,'_operation',None)
            elif kind=='operation':owner=kwargs.get('_operation')
            try:
                check(full)
                if owner is not None and not enter and kind!='closed':owner_check(owner)
                result=fn(*args,**kwargs)
                check(full)
                if owner is not None and kind!='closed':owner_check(owner)
                return result
            except BaseException as error:
                if type(owner) is owner_type and hasattr(owner,'_state'):poison(owner,error)
                raise
        return checked

    # Cleanup remains callable after dispatch failure and always releases locks.
    for name in ('__enter__','prepare','_finish'):
        setattr(owner_type,name,guard(getattr(owner_type,name),'self',full=True,enter=name=='__enter__'))
    for name in ('_start','_seed','_record_prefix','_basis','_execution'):
        setattr(owner_type,name,guard(getattr(owner_type,name),'self'))
    owner_type.receipt=guard(owner_type.receipt,'closed')
    for name in ('__init__','_inspect','promote'):
        setattr(scope_type,name,guard(getattr(scope_type,name),'operation' if name=='__init__' else 'self'))
    for cls,kind in ((RevalidatedChildInspection,'scope'),(VerifiedHistoricalEnvelope,'operation')):
        cls.__init__=guard(cls.__init__,kind)
    ChildReference.inspect=guard(ChildReference.inspect,'scope')
    for name in ('after','outcome','inspect_job','inspect_bridge'):
        namespace[name]=guard(namespace[name],'scope')
    for name in ('_replay_prefix','_projection'):
        namespace[name]=guard(namespace[name],'operation')
    namespace['_runtime_check']=check
    bindings=[]
    for name,value in tuple(namespace.items()):
        if isinstance(value,(types.FunctionType,types.ModuleType,type)) or name in (
                '_CHILD_TOKEN','_ENVELOPE_TOKEN','SCHEMA','VERIFIER_SCHEMA'):
            bindings.append((namespace,name,value,state(value)))
    for cls in (owner_type,scope_type,RevalidatedChildInspection,VerifiedHistoricalEnvelope,
            ChildReference,prior_witness._HourScope,GroupWitnessSession):
        for name,value in vars(cls).items():
            if isinstance(value,(types.FunctionType,property,staticmethod,classmethod)):
                bindings.append((cls,name,value,state(value)))
    for target,name in ((hour,'inspect'),(prior_witness,'_dispatch_view'),(prior_witness,'_freeze')):
        value=getattr(target,name);bindings.append((target,name,value,state(value)))
    expected=tuple(bindings)
    with denial():baseline=dispatch(module)


class GroupWitnessSession(prior_witness._PrivateResult):
    """Three separate proof slots, activated by one complete common result."""
    def __init__(self,lease):
        _runtime_check()
        roster,declarations,limit=operation_bridge._VERIFY_LEASE(lease)
        if limit!=22 or len(declarations)!=3 or len({d[0] for d in declarations})!=3:
            raise ValueError('exact twenty-two-common three-arm Handoff scope required')
        self._lease=lease;self._original_lease=lease
        self._roster=roster;self._declarations=declarations;self._limit=limit
        self._creator=(os.getpid(),threading.get_ident())
        self._nonce=self._original_nonce=object()
        self._public_session=self._original_public_session=token_hex(32)
        self._arms={};self._original_arms=();self._resource_caps=();self._rows=[]
        self._state='active';self._failure=None;self._poisoning=False;self._closed=False
        self._common_calls=0;self._reuse_active=False;self._common_ticket=None
        self._active_arm=None;self._current_rows=[];self._source_rows=[]
        operation_bridge._CLAIM_SESSION(lease,self)
        for arm,root,binding_pin,terminal_pin in declarations:
            child=ArmWitness(Path(root),arm_id=arm,
                expected_binding_sha256=binding_pin,expected_terminal_sha256=terminal_pin,
                completed_hours=1,reuse_numerical_proof=True,_session=self)
            self._arms[arm]=child
            self._original_arms+=((arm,child),)
            self._resource_caps+=((child,child._original_guard),)
        for _,owner in self._original_arms:owner.__enter__()
        self._check()

    def _check(self):
        _runtime_check()
        roster,declarations,limit=operation_bridge._VERIFY_LEASE(self._original_lease)
        if (self._closed or self._failure is not None or self._state not in ('active','preparing')
                or self._creator!=(os.getpid(),threading.get_ident())
                or self._lease is not self._original_lease or roster is not self._roster
                or declarations!=self._declarations or limit!=self._limit
                or tuple(self._arms.items())!=self._original_arms
                or tuple(owner for owner,_ in self._resource_caps)!=tuple(owner for _,owner in self._original_arms)
                or self._nonce is not self._original_nonce
                or self._public_session!=self._original_public_session
                or self._common_calls!=len(self._rows)
                or self._reuse_active is not (self._common_calls>0)):
            raise ValueError('original grouped historical witness lifetime changed')

    def _check_arm(self,owner):
        self._check()
        arm=owner._fixed_declaration[1]
        declaration=next((row for row in self._declarations if row[0]==arm),None)
        if (self._arms.get(arm) is not owner or declaration is None
                or owner._session is not self or owner._fixed_declaration[:5]!=(
                    Path(declaration[1]),arm,declaration[2],declaration[3],1)):
            raise ValueError('original authenticated arm/root/binding slot required')
        original_guard=next(guard for value,guard in self._resource_caps if value is owner)
        if owner._original_guard is not original_guard or owner._guard is not original_guard:
            raise ValueError('original per-arm operation guard changed')

    def _start_common(self):
        self._check();operation_bridge._BOOKEND(self._lease)
        if self._state!='active' or self._common_ticket is not None or self._common_calls>=self._limit:
            raise ValueError('twenty-two nonreentrant Handoff common calls required')
        self._state='preparing';self._common_ticket=object()
        self._current_rows=[];self._source_rows=[];self._active_arm=None
        return self._common_ticket

    def _arm(self,arm,ticket):
        self._check()
        if ticket is not self._common_ticket or self._state!='preparing' or arm not in self._arms:
            raise ValueError('original common call and authenticated arm required')
        return self._arms[arm]

    def _start_arm(self,owner):
        self._check_arm(owner)
        position=len(self._current_rows)
        expected=self._original_arms[position%3][1]
        if (self._state!='preparing' or self._common_ticket is None or self._active_arm is not None
                or position>=6 or owner is not expected
                or owner._attempts!=2*self._common_calls+position//3):
            raise ValueError('strict independent arm and round order required')
        self._active_arm=owner

    def _finish_arm(self,owner,envelope):
        self._check_arm(owner)
        if self._active_arm is not owner or type(envelope) is not VerifiedHistoricalEnvelope:
            raise ValueError('complete owned arm envelope required')
        execution=json.loads(envelope.execution_receipt)
        expected=(0,8) if self._reuse_active else (4,4)
        if (execution['session_identity']!=self._public_session
                or execution['common_call']!=self._common_calls+1
                or (execution['full_numerical_hour_replays'],execution['reused_numerical_inspections_total'])!=expected
                or execution['context_evaluations']!=16 or execution['arm_label_authenticated'] is not True):
            raise ValueError('actual grouped arm execution differs')
        self._current_rows.append(dict(arm=owner._fixed_declaration[1],
            envelope_identity=envelope.envelope_identity,execution=execution,
            execution_receipt_sha256=io.digest(envelope.execution_receipt)))
        self._active_arm=None

    def _execution(self,ticket,scientific_payload):
        self._check()
        if (ticket is not self._common_ticket or self._state!='preparing'
                or self._active_arm is not None or len(self._current_rows)!=6 or len(self._source_rows)!=6):
            raise ValueError('all six independent source preparations required')
        full=sum(r['execution']['full_numerical_hour_replays'] for r in self._current_rows)
        fresh=sum(r['execution']['within_prefix_revalidations'] for r in self._current_rows)
        cross=sum(r['execution']['cross_prepare_proof_reuses'] for r in self._current_rows)
        if (full,fresh,cross)!=((0,0,48) if self._reuse_active else (24,24,0)):
            raise ValueError('honest complete common work counts required')
        return io.encode(dict(schema=VERIFIER_SCHEMA,session_identity=self._public_session,
            common_call=self._common_calls+1,scientific_payload_sha256=io.digest(scientific_payload),
            full_numerical_hour_replays=full,within_prefix_revalidations=fresh,
            cross_common_numerical_proof_reuses=cross,context_evaluations=96,
            first_complete_common_proof_committed=self._reuse_active,
            arm_prepares=deepcopy(self._current_rows),source_preparations=deepcopy(self._source_rows),
            production_handoff_integrated=False,formal_result=False,resource_admission=False,
            native_execution_authorized=False))

    def _finish_common(self,ticket,result):
        self._check();operation_bridge._BOOKEND(self._lease)
        operation_bridge._COMMON_RESULT(self._lease,result,self)
        if result.execution_receipt!=self._execution(ticket,result.validation_report_payload):
            raise ValueError('final owned complete common result required before proof activation')
        # No caller callback occurs between complete validation and activation.
        self._rows.append(json.loads(result.execution_receipt));self._common_calls+=1
        self._reuse_active=True;self._common_ticket=None;self._current_rows=[];self._source_rows=[];self._state='active'
        self._check();operation_bridge._BOOKEND(self._lease)

    def _record_source(self,owner,bundle):
        self._check_arm(owner)
        operation_bridge._SOURCE_RESULT(self._lease,bundle)
        if (len(self._current_rows)!=len(self._source_rows)+1
                or self._current_rows[-1]['arm']!=owner._fixed_declaration[1]
                or self._current_rows[-1]['envelope_identity']!=bundle.historical.envelope_identity):
            raise ValueError('complete exact-source bundle in original arm order required')
        raw=bundle.verification_execution_payload;execution=json.loads(raw)
        if (io.encode(execution)!=raw or execution['historical_execution']!=self._current_rows[-1]['execution']
                or execution['exact_source_audit_sha256']!=io.digest(bundle.current.source_projection_audit_payload)
                or execution['prepared_current_audit_sha256']!=io.digest(bundle.current.prepared_current.audit_payload)):
            raise ValueError('exact-source execution and scientific audit binding differs')
        self._source_rows.append(dict(arm=owner._fixed_declaration[1],
            execution=execution,execution_receipt_sha256=io.digest(raw)))

    def receipt(self):
        _runtime_check()
        arms={arm:owner.receipt() for arm,owner in self._original_arms}
        return dict(schema=VERIFIER_SCHEMA,session_identity=self._original_public_session,
            common_calls=self._common_calls,common_executions=deepcopy(self._rows),
            arm_receipts=arms,closed=self._closed,first_failure=self._failure,
            complete=self._closed and self._failure is None and self._common_calls==self._limit
                and all(row['complete'] for row in arms.values()),
            production_handoff_integrated=False,formal_result=False,resource_admission=False,
            formal_execution_ready=False,native_execution_authorized=False)


def _bind_resource_methods():
    # Copy the original code into private callable closures. Replacing a class
    # method, shadowing it on an instance or changing the exposed __code__ cannot
    # replace the cleanup/poison code retained by the operation.
    copy_json, schema, describe = deepcopy, VERIFIER_SCHEMA, repr
    pid, thread, weak_reference = os.getpid, threading.get_ident, weakref.ref
    cleanup_globals = dict(globals(), deepcopy=copy_json, VERIFIER_SCHEMA=schema,
        os=types.SimpleNamespace(getpid=pid), threading=types.SimpleNamespace(get_ident=thread))
    def snapshot(fn, *, cleanup=False):
        return types.FunctionType(fn.__code__,cleanup_globals if cleanup else fn.__globals__,
            fn.__name__,fn.__defaults__,fn.__closure__)
    arm_poison=snapshot(ArmWitness._poison)
    arm_close=snapshot(ArmWitness.close,cleanup=True)
    arm_init=snapshot(ArmWitness.__init__)
    arm_check=snapshot(ArmWitness._check)
    arm_receipt=snapshot(ArmWitness.receipt,cleanup=True)
    session_init=snapshot(GroupWitnessSession.__init__)
    session_check=snapshot(GroupWitnessSession._check)
    owner_type,session_type=ArmWitness,GroupWitnessSession
    # Live resource authority is private closure state, never an instance alias.
    # Only completed JSON receipts remain after every release was attempted.
    sessions={};arm_sessions={};completed={}
    creator=lambda:(pid(),thread())

    def live(self):
        row=sessions.get(id(self))
        if row is None or row['owner'] is not self:
            raise ValueError('original live grouped resource record required')
        return row

    def aliases_match(self,row):
        fields=vars(self);resources=tuple(row['resources']);arms=fields.get('_arms')
        return (fields.get('_creator')==row['creator']
            and fields.get('_original_arms')==tuple((arm,owner) for arm,owner,_ in resources)
            and fields.get('_resource_caps')==tuple((owner,guard) for _,owner,guard in resources)
            and type(arms) is dict and tuple(arms.items())==tuple((arm,owner) for arm,owner,_ in resources))

    def initialize_arm(self,*args,**kwargs):
        session=kwargs.get('_session');row=live(session)
        if type(self) is not owner_type or row['creator']!=creator():
            raise ValueError('original creating-thread arm registration required')
        arm_init(self,*args,**kwargs)
        resource=(self._fixed_declaration[1],self,self._original_guard)
        row['resources'].append(resource)
        arm_sessions[id(self)]=(self,row)

    def initialize_group(self,lease):
        if type(self) is not session_type or id(self) in sessions or id(self) in completed:
            raise ValueError('new exact grouped resource owner required')
        row=dict(owner=self,creator=creator(),resources=[],poisoning=False,failure=None)
        sessions[id(self)]=row
        try:session_init(self,lease)
        except BaseException as error:
            poison_group(self,error)
            try:close_group(self)
            except BaseException as failure:error.add_note('group constructor cleanup: '+repr(failure))
            raise

    def check_group(self):
        row=live(self)
        if row['creator']!=creator() or not aliases_match(self,row):
            raise ValueError('original grouped resource aliases changed')
        session_check(self)

    def check_arm(self,ticket=None):
        registered=arm_sessions.get(id(self))
        if (registered is None or registered[0] is not self
                or self._session is not registered[1]['owner']):
            raise ValueError('original arm resource owner changed')
        arm_check(self,ticket)

    def poison_group(self,error):
        terminal=completed.get(id(self))
        if terminal is not None and terminal[0]() is self:
            receipt=terminal[1]
            if receipt['first_failure'] is None:receipt['first_failure']=describe(error)
            receipt['complete']=False
            for value in receipt['arm_receipts'].values():
                value['complete']=False
                if value.get('first_failure') is None:value['first_failure']=describe(error)
            return
        row=live(self)
        if row['poisoning']:return
        row['poisoning']=True
        try:
            if row['failure'] is None:row['failure']=describe(error)
            self._failure=row['failure']
            self._state='failed';self._reuse_active=False;self._common_ticket=None
            self._current_rows=[];self._source_rows=[];self._active_arm=None
            for _,owner,_ in tuple(row['resources']):
                try:arm_poison(owner,error)
                except BaseException as failure:error.add_note('arm poison failure: '+repr(failure))
        finally:row['poisoning']=False

    def close_group(self):
        terminal=completed.get(id(self))
        if terminal is not None and terminal[0]() is self:return
        row=live(self)
        errors=[]
        resources=tuple(row['resources'])
        arms={};receipt=None
        try:
            if row['creator']!=creator():
                errors.append(ValueError('group witness close must remain on creating thread'))
            try:
                if not aliases_match(self,row):
                    errors.append(ValueError('original grouped resource aliases changed during cleanup'))
            except BaseException as error:errors.append(error)
            for _,owner,guard in resources:
                try:
                    if (owner._original_guard is not guard or owner._guard is not guard or owner._session is not self):
                        raise ValueError('captured arm guard differs during cleanup')
                    arm_close(owner)
                except BaseException as error:
                    errors.append(error)
                    try:arm_poison(owner,error)
                    except BaseException as failure:errors.append(failure)
                finally:
                    # Proof destruction cannot depend on a reporting function,
                    # exposed method, module-global clock, or alias integrity.
                    vars(owner).update(_proof=None,_science_basis=None,_pending=[],_ticket=None,
                        _active_scope=None,_site_ticket=None,_nonce=None,_state='closed',_ended=True)
                    try:
                        if guard.locked():guard.release()
                    except BaseException as error:errors.append(error)
            if errors:
                try:poison_group(self,errors[0])
                except BaseException as error:errors.append(error)
            vars(self).update(_closed=True,_reuse_active=False,_common_ticket=None,
                _current_rows=[],_source_rows=[],_active_arm=None,_nonce=None,_state='closed')
            for arm,owner,guard in resources:
                try:arms[arm]=arm_receipt(owner)
                except BaseException as error:
                    errors.append(error)
                    arms[arm]=dict(complete=False,closed=True,proof_cleared=owner._proof is None,
                        first_failure=describe(error))
            if errors:
                try:poison_group(self,errors[0])
                except BaseException as error:errors.append(error)
            receipt=dict(schema=schema,session_identity=self._original_public_session,
                common_calls=self._common_calls,common_executions=copy_json(self._rows),
                arm_receipts=arms,closed=True,first_failure=row['failure'] or self._failure,
                complete=not errors and row['failure'] is None and self._failure is None
                    and self._common_calls==self._limit and len(arms)==3
                    and all(value['complete'] for value in arms.values()),
                production_handoff_integrated=False,formal_result=False,resource_admission=False,
                formal_execution_ready=False,native_execution_authorized=False)
        except BaseException as error:
            errors.append(error)
        finally:
            # Registry removal and proof destruction precede receipt publication.
            for _,owner,guard in resources:
                vars(owner).update(_proof=None,_science_basis=None,_pending=[],_ticket=None,
                    _active_scope=None,_site_ticket=None,_nonce=None,_state='closed',_ended=True)
                try:
                    if guard.locked():guard.release()
                except BaseException as error:errors.append(error)
                arm_sessions.pop(id(owner),None)
            sessions.pop(id(self),None)
            vars(self).update(_closed=True,_reuse_active=False,_common_ticket=None,
                _current_rows=[],_source_rows=[],_active_arm=None,_nonce=None,_state='closed',
                _lease=None,_original_lease=None,_roster=None,_arms={},_original_arms=(),_resource_caps=())
            if receipt is None or errors:
                receipt=dict(schema=schema,session_identity=self._original_public_session,
                    common_calls=self._common_calls,common_executions=[],arm_receipts=arms,
                    closed=True,complete=False,first_failure=describe(errors[0]) if errors else 'cleanup failed',
                    production_handoff_integrated=False,formal_result=False,resource_admission=False,
                    formal_execution_ready=False,native_execution_authorized=False)
            key=id(self)
            def expired(reference):
                terminal=completed.get(key)
                if terminal is not None and terminal[0] is reference:completed.pop(key,None)
            completed[key]=(weak_reference(self,expired),receipt)
        if errors:
            for error in errors[1:]:errors[0].add_note('additional arm cleanup failure: '+repr(error))
            raise errors[0]

    def poison_arm(self,error):
        try:arm_poison(self,error)
        finally:
            registered=arm_sessions.get(id(self))
            if registered is not None and registered[0] is self:
                poison_group(registered[1]['owner'],error)

    def receipt_group(self):
        _runtime_check()
        terminal=completed.get(id(self))
        if terminal is not None and terminal[0]() is self:return copy_json(terminal[1])
        row=live(self)
        arms={arm:arm_receipt(owner) for arm,owner,_ in row['resources']}
        return dict(schema=VERIFIER_SCHEMA,session_identity=self._original_public_session,
            common_calls=self._common_calls,common_executions=deepcopy(self._rows),
            arm_receipts=arms,closed=False,first_failure=row['failure'] or self._failure,
            complete=False,production_handoff_integrated=False,formal_result=False,
            resource_admission=False,formal_execution_ready=False,native_execution_authorized=False)

    ArmWitness.__init__=initialize_arm
    ArmWitness._check=check_arm
    ArmWitness._poison=poison_arm
    GroupWitnessSession.__init__=initialize_group
    GroupWitnessSession._check=check_group
    GroupWitnessSession._poison=poison_group
    GroupWitnessSession.close=close_group
    GroupWitnessSession.receipt=receipt_group


_bind_resource_methods()
_install_runtime_checks()
