"""Draft selector-to-phase consumption; planning alone grants no write authority.

The ticket planner reproduces the existing phase wire contract before a future
controller starts a handoff. Live parent binding and durable consumption are
still required; a constructible plan is never a completion or admission proof.
"""
from hashlib import sha256
from dataclasses import dataclass
import json

from experiments import h1_phase_owner_development_v1 as phase


@dataclass(frozen=True)
class _BootstrapPlan:
    """Constructible numerical preview, never a live or persisted credential."""
    tickets: tuple
    holder_records: tuple
    retentions: tuple
    projection: bytes
    after: bytes

    def __post_init__(self):
        if (type(self.tickets) is not tuple or len(self.tickets)!=2
                or any(type(t) is not phase.AppendTicket for t in self.tickets)
                or type(self.holder_records) is not tuple or len(self.holder_records)!=2
                or any(type(raw) is not bytes for raw in self.holder_records)
                or type(self.retentions) is not tuple or len(self.retentions)!=2
                or type(self.projection) is not bytes or type(self.after) is not bytes):
            raise ValueError('complete immutable bootstrap preview required')
        first,second=self.tickets
        if (first.sequence!=1 or second.sequence!=2 or first.kind!='intent' or second.kind!='outcome'
                or first.before_heads!=(first.store_identity,first.store_identity)
                or second.store_identity!=first.store_identity or second.before_heads!=first.after_heads):
            raise ValueError('bootstrap ticket chain differs')
        genesis=self.retentions[0][0];phase.tickets._pin(genesis);previous=genesis
        for t,raw,retention in zip(self.tickets,self.holder_records,self.retentions,strict=True):
            if raw!=phase.encode(dict(sequence=t.sequence,previous=previous,ticket=phase.tickets._ticket_payload(t))):
                raise ValueError('planned holder bytes differ')
            after=sha256(raw).hexdigest()
            if type(retention) is not tuple or retention!=(genesis,previous,after,t.sequence):
                raise ValueError('planned holder retention differs')
            previous=after
        intent,outcome=json.loads(first.body),json.loads(second.body)
        if (phase.encode(intent)!=first.body or phase.encode(outcome)!=second.body
                or phase.encode(json.loads(self.projection))!=self.projection
                or phase.encode(json.loads(self.after))!=self.after
                or intent['hour']!=0 or intent['alternate'] is not False
                or intent['before_heads']!=list(first.before_heads)
                or outcome!=dict(intent_head=first.event[-1],key=intent['key'],
                    projection=json.loads(self.projection),projection_sha256=sha256(self.projection).hexdigest())
                or json.loads(self.projection)['after']!=json.loads(self.after)):
            raise ValueError('planned projection correspondence differs')


def _planned_bootstrap(manifest,binding,current,*,owner_genesis,holder_genesis,
                       reference_records,actual_records):
    """Pure exact two-event preview, including the retained holder hash chain.

    Unresolved numerical branches remain visible in the projection. This helper
    does not authenticate the reason an Actual record prefix is absent/partial;
    a live consumer must reject it unless it owns the corresponding evidence.
    """
    if type(manifest) is not phase.Manifest or type(binding) is not phase.SourceBinding:
        raise TypeError('exact phase declaration required')
    manifest.__post_init__();binding.__post_init__()
    phase.tickets._pin(owner_genesis);phase.tickets._pin(holder_genesis)
    if type(current.prepared_current.frame.info.relative_hour) is not int or current.prepared_current.frame.info.relative_hour!=0:
        raise ValueError('bootstrap preview requires current hour zero')
    state=phase._initial(manifest,current)
    if state.hour!=0:raise ValueError('bootstrap preview requires hour zero')
    # Preserve the existing whole-branch reservation including a future terminal.
    if manifest.max_events<3 or 3*manifest.max_event_bytes>manifest.max_archive_bytes:
        raise ValueError('complete bootstrap branch exceeds declared owner bounds')
    packed=phase._pack_records(manifest,reference_records,actual_records)
    key=phase._request(manifest,state,current)
    intent=dict(hour=0,terminal=binding.genesis_terminal_sha256,key=key,
        source_audit=json.loads(current.source_projection_audit_payload),records=packed,
        alternate=False,before_heads=(owner_genesis,owner_genesis))
    first=phase.AppendTicket(owner_genesis,1,(owner_genesis,owner_genesis),'intent',phase.encode(intent))
    after,projection=phase._transition(manifest,state,current,phase._unpack_records(manifest,packed))
    outcome=dict(intent_head=first.event[-1],key=key,projection=json.loads(projection),
        projection_sha256=sha256(projection).hexdigest())
    second=phase.AppendTicket(owner_genesis,2,first.after_heads,'outcome',phase.encode(outcome))
    previous=holder_genesis;retentions=[];holder_records=[]
    for ticket in (first,second):
        if len(ticket.body)>manifest.max_event_bytes:raise ValueError('planned phase body exceeds cap')
        raw=phase.encode(dict(sequence=ticket.sequence,previous=previous,ticket=phase.tickets._ticket_payload(ticket)))
        if len(raw)>2*manifest.max_event_bytes+4096:raise ValueError('planned holder record exceeds cap')
        following=sha256(raw).hexdigest()
        holder_records.append(raw)
        retentions.append((holder_genesis,previous,following,ticket.sequence))
        previous=following
    return _BootstrapPlan((first,second),tuple(holder_records),tuple(retentions),projection,phase.encode(after.scientific))


def _observe_bootstrap(plan,*,retained_count,holder_records,phase_rows):
    """Classify supplied exact prefixes; no disk read, authentication or recovery.

    A future controller must obtain retained_count from its external journal,
    and stable holder/DB bytes under the owned leases. Merely knowing planned
    future hashes must never increase retained_count. The return grants no
    permission to fill a missing ticket, repeat a phase write, or issue a receipt.
    """
    if type(plan) is not _BootstrapPlan:raise TypeError('exact bootstrap preview required')
    plan.__post_init__()
    if type(retained_count) is not int or not 0<=retained_count<=2:
        raise ValueError('exact external retention count required')
    if type(holder_records) is not tuple or type(phase_rows) is not tuple:
        raise TypeError('immutable observed prefixes required')
    h,d=len(holder_records),len(phase_rows)
    if (any(type(raw) is not bytes for raw in holder_records)
            or any(type(row) is not tuple or len(row)!=5
                or tuple(type(v) for v in row)!=(int,str,str,bytes,str) for row in phase_rows)
            or holder_records!=plan.holder_records[:h] or h>2
            or phase_rows!=tuple(t.event for t in plan.tickets[:d]) or d>2):
        raise ValueError('observed bootstrap bytes or suffix differ')
    stages={
        (0,0,0):'planned_only',
        (1,0,0):'holder_retention_pending',
        (1,1,0):'phase_commit_pending',
        (1,1,1):'outcome_pending',
        (2,1,1):'holder_retention_pending',
        (2,2,1):'phase_commit_pending',
        (2,2,2):'bootstrap_rows_present',
    }
    state=stages.get((retained_count,h,d))
    if state is None:raise ValueError('bootstrap observation violates write order')
    return dict(state=state,retained_count=retained_count,holder_rows=h,phase_rows=d,
        live_parent_authenticated=False,source_correspondence_verified=False,
        controller_terminal_verified=False,recovery_authorized=False,
        parent_phase_commit_verified=False,full_192_hour_execution_verified=False,
        resource_admission=False,formal_execution_ready=False,formal_result=False)
