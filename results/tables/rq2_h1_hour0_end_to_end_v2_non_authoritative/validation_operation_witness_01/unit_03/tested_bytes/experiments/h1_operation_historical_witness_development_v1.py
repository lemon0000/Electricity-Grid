"""Single-arm, two-prepare diagnostic proof reuse; no live Handoff credential.

The unchanged predecessor context is observed before and after every old site.
This development prototype must not be installed under a predecessor module name.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass
from functools import wraps
from pathlib import Path
import json
import os
import sys
import threading
import types

from experiments import h1_historical_hour_witness_development_v1 as prior_witness
from experiments import h1_historical_n0_verifier_development_v1 as prior_verifier

legacy=prior_verifier.legacy
old,history,current=legacy.old,legacy.history,legacy.current
io,binding,bridge,base=legacy.io,legacy.binding,legacy.bridge,legacy.base
parent,hour,worker=prior_witness.parent,prior_witness.hour,prior_witness.worker
SCHEMA=legacy.SCHEMA
VERIFIER_SCHEMA='h1_operation_historical_witness_development_v1'
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


def verifier_identity():
    return io.digest(io.encode([VERIFIER_SCHEMA,io.digest(Path(__file__).read_bytes()),
        prior_verifier.verifier_identity()]))


@dataclass(frozen=True,init=False)
class DiagnosticVerifiedHistoricalEnvelope(prior_witness._PrivateResult):
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
        if (full,fresh) not in ((4,4),(0,8)):raise ValueError('honest diagnostic work counts required')
        if type(_operation) is not OperationHistoricalWitness:raise TypeError('owned diagnostic operation required')
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


class OperationHistoricalWitness(prior_witness._PrivateResult):
    """Diagnostic owner only; production must bind a real Handoff and its guards."""
    def __init__(self,root,*,arm_id,expected_binding_sha256,expected_terminal_sha256,
            completed_hours=1,reuse_numerical_proof=True):
        _runtime_check()
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
        if (self._failure is not None or self._state not in ('active','preparing')
                or (os.getpid(),threading.get_ident())!=self._owner
                or self._guard is not self._original_guard or not self._original_guard.locked()
                or self._declaration!=self._fixed_declaration
                or str(self._declaration[0])!=self._exact_root
                or self._nonce is not self._original_nonce or self._ended
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
        if self._state!='active' or self._attempts>=2:raise ValueError('two nonreentrant diagnostic prepares required')
        self._state='preparing';self._ticket=object();self._pending=[]
        self._prepare_context_start=self._contexts
        return self._ticket

    def _seed(self,ticket,prefix_index,scope):
        self._check(ticket)
        if (prefix_index!=len(self._pending) or prefix_index not in (0,1) or self._active_scope is not None
                or str(scope._root)!=self._exact_root):raise ValueError('diagnostic prefix order or root changed')
        self._active_scope=scope;self._site=0;self._site_ticket=None;self._context_edge=0
        if not self._declaration[-1] or self._proof is None:return None
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
            *[io.digest(repr(row[1]).encode('utf-8')) for row in self._pending]]))
        basis=(*science,identity,self._nonce)
        if self._science_basis is not None and basis!=self._science_basis:
            raise ValueError('first complete historical scientific proof differs')
        return basis

    def _execution(self,decision,audit,own,full,fresh):
        root,arm,binding_pin,terminal_pin,hours,reuse=self._fixed_declaration
        ordinal=self._attempts+1;basis=self._basis(decision,audit)
        expected_counts=(0,8) if reuse and ordinal==2 else (4,4)
        if (full,fresh)!=expected_counts:raise ValueError('diagnostic mode execution counts differ')
        active=io.digest(io.encode([own,self._exact_root,arm,binding_pin,terminal_pin,reuse]))
        if self._validation_identity is not None and active!=self._validation_identity:
            raise ValueError('active diagnostic validation identity changed')
        return io.encode(dict(schema=VERIFIER_SCHEMA,diagnostic_owner_only=True,
            compatibility_payload_scope='historical_scientific_projection_only',
            active_validation_identity=active,
            declared_arm_label=arm,arm_label_authenticated=False,controller_root_exact=self._exact_root,
            controller_binding_sha256=binding_pin,controller_terminal_sha256=terminal_pin,completed_hours=hours,
            session_nonce=str(id(self._nonce)),prepare=ordinal,mode='operation' if reuse else 'full_only',
            proof_basis_identity=basis[2],proof_role='produced' if ordinal==1 else ('consumed' if reuse else 'reconfirmed'),
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
            if (type(envelope) is not DiagnosticVerifiedHistoricalEnvelope or envelope.decision is not decision
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
        return full,fresh

    def prepare(self):
        try:
            ticket=self._start();root,arm,binding_pin,terminal_pin,hours,reuse=self._declaration
            own=verifier_identity()
            decision,audit=_projection(root,expected_binding_sha256=binding_pin,
                expected_terminal_sha256=terminal_pin,completed_hours=hours,
                _operation=self,_ticket=ticket)
            if verifier_identity()!=own:raise ValueError('operation verifier changed during preparation')
            full=sum(row[3] for row in self._pending);fresh=sum(row[4] for row in self._pending)
            execution=self._execution(decision,audit,own,full,fresh)
            envelope=DiagnosticVerifiedHistoricalEnvelope(decision,audit,own,full,fresh,execution,
                _token=_ENVELOPE_TOKEN,_operation=self,_ticket=ticket)
            if verifier_identity()!=own:raise ValueError('operation verifier changed before proof commit')
            full,fresh=self._finish(ticket,decision,audit,envelope=envelope)
            return envelope
        except BaseException as error:
            self._poison(error)
            raise

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
        return dict(schema=VERIFIER_SCHEMA,diagnostic_owner_only=True,production_handoff_integrated=False,
            declared_arm_label=self._fixed_declaration[1],arm_label_authenticated=False,
            controller_root_exact=self._exact_root,controller_binding_sha256=self._fixed_declaration[2],
            controller_terminal_sha256=self._fixed_declaration[3],
            mode='operation' if self._fixed_declaration[-1] else 'full_only',
            active_validation_identity=self._validation_identity,
            completed_prepares=self._attempts,prepares=deepcopy(self._rows),context_observations=self._contexts,
            first_failure=self._failure,closed=self._ended,proof_cleared=self._proof is None,
            complete=self._attempts==2 and self._failure is None,
            public_envelopes_complete=self._attempts==2 and self._failure is None
                and all(row['public_envelope_committed'] for row in self._rows),
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
    owner_type=OperationHistoricalWitness;scope_type=_OperationHourScope
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
            if kind=='self':
                first=args[0]
                owner=first if type(first) is owner_type else getattr(first,'_operation',None)
            elif kind=='scope':
                scope=kwargs.get('_scope',kwargs.get('scope'))
                if scope is None and args:scope=getattr(args[0],'_scope',None)
                owner=getattr(scope,'_operation',None)
            elif kind=='operation':owner=kwargs.get('_operation')
            try:
                check(full)
                if owner is not None and not enter:owner_check(owner)
                result=fn(*args,**kwargs)
                check(full)
                if owner is not None:owner_check(owner)
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
    for name in ('__init__','_inspect','promote'):
        setattr(scope_type,name,guard(getattr(scope_type,name),'operation' if name=='__init__' else 'self'))
    for cls,kind in ((RevalidatedChildInspection,'scope'),(DiagnosticVerifiedHistoricalEnvelope,'operation')):
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
    for cls in (owner_type,scope_type,RevalidatedChildInspection,DiagnosticVerifiedHistoricalEnvelope,
            ChildReference,prior_witness._HourScope):
        for name,value in vars(cls).items():
            if isinstance(value,(types.FunctionType,property,staticmethod,classmethod)):
                bindings.append((cls,name,value,state(value)))
    for target,name in ((hour,'inspect'),(prior_witness,'_dispatch_view'),(prior_witness,'_freeze')):
        value=getattr(target,name);bindings.append((target,name,value,state(value)))
    expected=tuple(bindings)
    with denial():baseline=dispatch(module)


_install_runtime_checks()
