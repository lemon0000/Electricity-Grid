"""Source-bound, saved-record H1 paired owner. DRAFT_NONAUTHORITATIVE.

No solver producer, formal resource admission or cross-owner reuse authority.
Every reopen replays the archived primitives from fresh historical N sources.
"""
from base64 import b64decode, b64encode
from contextlib import closing
from dataclasses import asdict, dataclass
from fractions import Fraction as Q
from hashlib import sha256
from functools import wraps
import json
import os
from pathlib import Path
import sqlite3
from threading import Lock

from experiments import h1_exact_source_current_development_v1 as source
from experiments import h1_exact_business_development_v1 as business
from experiments import h1_origin_selector_replay_development_v1 as selection
from src.rq2_joint_deliverability_boundary_v1 import episode_store as local

SCHEMA = 'h1_persistent_owner_saved_records_development_v1'
encode = business.encoding._encoded
RREF = selection.RREF
TABLES = (
    'CREATE TABLE header (id INTEGER PRIMARY KEY CHECK(id=1), body BLOB NOT NULL)',
    'CREATE TABLE events (seq INTEGER PRIMARY KEY, predecessor TEXT NOT NULL, kind TEXT NOT NULL, body BLOB NOT NULL, head TEXT NOT NULL)',
)


def digest(value):return sha256(encode(value)).hexdigest()


@dataclass(frozen=True)
class LaneConfig:
    lane_id: str
    policy: business.business.BidirectionalPolicy
    mechanism: business.Mechanism
    envelope: tuple

    @property
    def lane(self):return selection.physical.Lane('A',self.policy.arm_id)

    def __post_init__(self):
        if type(self.lane_id) is not str or not self.lane_id or len(self.lane_id)>128:
            raise ValueError('bounded explicit lane identity required')
        if type(self.policy) is not business.business.BidirectionalPolicy or type(self.mechanism) is not business.Mechanism:
            raise ValueError('typed fixed policy and mechanism required')
        self.policy.__post_init__();self.mechanism.__post_init__();self.lane.__post_init__()
        fields=('maximum_event_count','maximum_event_duration_hours','minimum_recovery_hours',
                'normalized_debt_limit','normalized_energy_budget','recovery_efficiency','time_step_hours')
        if (type(self.envelope) is not tuple or tuple(k for k,v in self.envelope)!=fields
                or dict(self.envelope)['time_step_hours']!=1):
            raise ValueError('complete sorted hourly envelope required')

    @property
    def scientific(self):
        policy=asdict(self.policy);policy.pop('capacity_declaration_id')
        return dict(lane_id=self.lane_id,lane=self.lane,policy=policy,mechanism=self.mechanism,envelope=self.envelope)


@dataclass(frozen=True)
class Manifest:
    lanes: tuple
    reference_selector: selection.reference.ReferenceSelectorSpec
    actual_selector: selection.actual.ActualDispatchSpec
    solver_specification: selection.native.capture.Rq2SolverSpec
    replay_limits: selection.ReplayLimits
    max_events: int
    max_event_bytes: int
    max_archive_bytes: int
    accounting_period_id: str

    def __post_init__(self):
        if type(self.lanes) is not tuple or not self.lanes or any(type(c) is not LaneConfig for c in self.lanes):
            raise ValueError('nonempty canonical lane roster required')
        ids=tuple(c.lane_id for c in self.lanes)
        if ids!=tuple(sorted(set(ids))):raise ValueError('unique sorted lane roster required')
        for c in self.lanes:c.__post_init__()
        for n in ('max_events','max_event_bytes','max_archive_bytes'):
            if type(getattr(self,n)) is not int or getattr(self,n)<=0:raise ValueError('explicit archive bounds required')
        if self.max_event_bytes>self.max_archive_bytes:raise ValueError('event bound exceeds archive bound')
        if type(self.accounting_period_id) is not str or not self.accounting_period_id:
            raise ValueError('explicit nonrolling accounting period label required')
        for lane,selector in [(RREF,self.reference_selector)]+[(c.lane,self.actual_selector) for c in self.lanes]:
            selection._configuration(lane,selector,self.solver_specification,self.replay_limits,0)

    @property
    def scientific(self):
        return dict(schema=SCHEMA,lanes=tuple(c.scientific for c in self.lanes),
            reference_selector=self.reference_selector,actual_selector=self.actual_selector,
            solver_specification=self.solver_specification,replay_limits=self.replay_limits,
            enrollment_hours=168,maximum_followup_hours=24,due_offset=24,period=business.PERIOD,
            retain_followup_births_and_debt=True,workload_projection='exact_decimal_half_even_then_str_float_identity_v1',
            decimal_places=12,normalized_unit_mw=250,cfe_rule=source.CFE_RULE,mode='saved_record_replay')


@dataclass(frozen=True)
class SourceBinding:
    root: str
    binding_sha256: str
    registry_identity: str
    genesis_terminal_sha256: str

    def __post_init__(self):
        if type(self.root) is not str or str(Path(self.root).absolute())!=self.root:
            raise ValueError('absolute source controller root required')
        for pin in (self.binding_sha256,self.registry_identity,self.genesis_terminal_sha256):source.io.pin(pin)


def implementation_identity(manifest):
    return digest([SCHEMA,source.implementation_identity(),business.implementation_identity(),
        selection.implementation_identity(manifest.solver_specification,manifest.replay_limits),
        sha256(Path(local.__file__).read_bytes()).hexdigest(),sha256(Path(__file__).read_bytes()).hexdigest()])


def _fresh(binding,hour,terminal):
    source.io.pin(terminal)
    return source.prepare(binding.root,expected_binding_sha256=binding.binding_sha256,
        expected_terminal_sha256=terminal,completed_hours=hour+1,expected_registry_identity=binding.registry_identity)


def _anchor(current):
    """Recover the existing normalization recipe from one fresh source row."""
    audit=json.loads(current.source_projection_audit_payload)
    raw=audit['source_observation_audit_payload'];d=raw['declaration']
    config=audit['normal_audit_payload']['parent_declaration']['config_path']
    windows=source.source.windows;loaded={}
    for kind in ('power','workload'):
        window=windows.load_source_window(kind,d['split'],d[kind+'_raw_hour'],1,
            outage_seed=d['outage_seed'] if kind=='power' else None,
            config_path=config,expected_config_sha256=d['config_sha256'])
        if (window['window_identity']!=raw[kind+'_window_identity']
                or windows._hash(window['chain'])!=raw[kind+'_chain_identity']
                or window['rows']!=[raw[kind+'_source_row']]
                or window['package_manifest_sha256']!=raw[kind+'_package_manifest_sha256']):
            raise ValueError('fresh genesis source window correspondence changed')
        loaded[kind]=window
    p,w=loaded['power'],loaded['workload']
    normalization=dict(source_basis=w['chain']['trace_identity_basis'],
        source_package_manifest_sha256=w['package_manifest_sha256'],
        numerical_projection_rule='exact_decimal_half_even_then_str_float_identity_v1',
        decimal_places=12,normalized_unit_mw='250',power_rule='linear_workload_power_no_idle_offset_v1')
    return business.boundary.BoundaryAnchor(arm_id=business.arms.JOINT,track_id='shared',split=d['split'],
        power_source_hour=0,workload_source_hour=0,power_trajectory_id=p['chain']['chain_id'],
        workload_trace_id=w['chain']['chain_id'],workload_normalization_sha256=windows._hash(normalization),
        power_outage_seed=d['outage_seed'],power_provenance_sha256=p['package_manifest_sha256'],
        workload_provenance_sha256=w['package_manifest_sha256'])


@dataclass(frozen=True)
class _LaneState:
    business: business.BusinessCarry
    actual: selection.SelectionCandidate
    halted: bool = False
    reason: str | None = None


@dataclass(frozen=True)
class _State:
    hour: int
    reference: selection.SelectionCandidate
    lanes: tuple

    @property
    def scientific(self):
        return dict(hour=self.hour,reference=self.reference.identity,lanes=[dict(lane_id=k,
            business=v.business.identity,actual=v.actual.identity,halted=v.halted,reason=v.reason) for k,v in self.lanes])


def _initial(manifest,current):
    prepared=current.prepared_current
    if prepared.frame.info.relative_hour!=0:raise ValueError('source genesis must be first accepted N hour')
    anchor=_anchor(current)
    chronology=isinstance(prepared.source_action,selection.physical.registry.FirstAction)
    def initial(lane,selector):
        return selection.initialize_development_selection(prepared.frame,prepared.source_origin,lane=lane,
            selector=selector,specification=manifest.solver_specification,limits=manifest.replay_limits,
            chronology_origin=chronology)
    lanes=tuple((c.lane_id,_LaneState(business.initialize_development(c.policy,mechanism=c.mechanism,
        anchor=anchor,envelope=dict(c.envelope),accounting_period_id=manifest.accounting_period_id),
        initial(c.lane,manifest.actual_selector))) for c in manifest.lanes)
    return _State(0,initial(RREF,manifest.reference_selector),lanes)


def _request(manifest,state,current):
    if current.prepared_current.frame.info.relative_hour!=state.hour:
        raise ValueError('N and owner progress mismatch')
    anchor=_anchor(current)
    initial=state.lanes[0][1].business.cursor.initial.tracks[0][1].physical.anchor
    # Arm labels are adapted by the existing policy initializer; source labels are not.
    for key,value in asdict(anchor).items():
        if key not in ('arm_id','track_id') and getattr(initial,key)!=value:
            raise ValueError('owner source chain, normalization or provenance changed')
    return digest([SCHEMA,manifest.scientific,state.scientific,current.exogenous_scientific_identity])


def _replay_selection(manifest,current,before,lane,records,power=None):
    prepared=current.prepared_current
    return selection.replay_development_records(prepared.frame,prepared.source_action,before,records,
        lane=lane,selector=manifest.reference_selector if lane.role=='Rref' else manifest.actual_selector,
        specification=manifest.solver_specification,limits=manifest.replay_limits,power=power,
        expected_identity=selection.input_identity(prepared.frame,prepared.source_action,before,lane=lane,power=power),
        expected_policy_identity=before.policy_identity,expected_report_sha256=tuple(sha256(r).hexdigest() for r in records))


def _transition(manifest,state,current,records):
    """Only a complete common reference can produce one complete outer outcome."""
    reference=_replay_selection(manifest,current,state.reference,RREF,records['reference'])
    if reference.next_candidate is None:raise ValueError('reference unresolved: intent remains uncompleted')
    g=Q(*map(int,reference.candidate_request_exact))
    if not 0<=g<=current.workload_exact*250:raise ValueError('reference request outside exact baseline')
    lanes=[];outcomes=[]
    for config,(lane_id,before) in zip(manifest.lanes,state.lanes,strict=True):
        raw=records['actual'][lane_id];after=before;detail=None;power=None
        if before.halted:
            if raw:raise ValueError('halted lane has unused actual records')
            status='skipped_halted'
        else:
            try:
                item=business.current(relative_hour=state.hour,mechanism=config.mechanism,
                    workload=current.workload_exact,source_cfe_at_alpha_one=current.source_cfe_at_alpha_one_exact,
                    grid_request_mw=g)
            except ValueError as exc:
                if str(exc) not in (
                        'positive reference request below business resolution',
                        'raw component and combined activity mismatch',
                        'legacy binary threshold representation mismatch',
                        'exact interface unresolved: no lossless decimal built-in'):
                    raise
                detail=dict(input_unresolved_reason=str(exc))
                item=None
            if item is None:
                if raw:raise ValueError('unresolved business input has unused actual records')
                status='business_input_unresolved'
            else:
                candidate=business.prepare_development(before.business,item,expected_current_identity=item.identity)
                record=candidate.replay_cursor.records[-1]
                detail=dict(stage=record.stage,error=record.error,action=None if record.response is None else record.response.action,
                    grid_shortfall=None if record.response is None else record.response.grid_shortfall,
                    cfe_shortfall=None if record.response is None else record.response.cfe_shortfall)
                if candidate.next_candidate is None:
                    if raw:raise ValueError('unresolved business candidate has unused actual records')
                    status='business_unresolved'
                else:
                    power=candidate.actual_power_mw
                    prescribed=selection.physical.RelativeDcPower(state.hour,str(power.numerator),str(power.denominator),'mechanism_assumption')
                    actual=_replay_selection(manifest,current,before.actual,config.lane,raw,prescribed)
                    if actual.next_candidate is None:status='actual_unresolved'
                    else:
                        status='paired_committed'
                        after=_LaneState(candidate.next_candidate,actual.next_candidate)
            if status!='paired_committed':after=_LaneState(before.business,before.actual,True,status)
        lanes.append((lane_id,after));outcomes.append(dict(lane_id=lane_id,status=status,
            paired_committed=status=='paired_committed',business_candidate=detail,actual_power_mw=power,
            before_business=before.business.identity,after_business=after.business.identity,
            before_actual=before.actual.identity,after_actual=after.actual.identity,
            halted=after.halted,halt_reason=after.reason))
    after=_State(state.hour+1,reference.next_candidate,tuple(lanes))
    projection=encode(dict(request_key=_request(manifest,state,current),reference_request_mw=g,
        reference_after=after.reference.identity,lanes=outcomes,after=after.scientific))
    return after,projection


def _pack_records(manifest,reference,actual):
    if type(reference) is not tuple or type(actual) is not dict or set(actual)!={c.lane_id for c in manifest.lanes}:
        raise ValueError('complete canonical reference/actual record roster required')
    def pack(items):
        if type(items) is not tuple or len(items)>manifest.replay_limits.max_stages:
            raise ValueError('bounded tuple of immutable saved records required')
        if any(type(r) is not bytes or not 0<len(r)<=manifest.replay_limits.max_record_bytes for r in items):
            raise ValueError('bounded nonempty saved record bytes required')
        if sum(map(len,items))>manifest.replay_limits.max_total_bytes:raise ValueError('selector archive exceeds limit')
        return [b64encode(r).decode('ascii') for r in items]
    return dict(reference=pack(reference),actual={k:pack(actual[k]) for k in sorted(actual)})


def _unpack_records(manifest,body):
    def unpack(items):return tuple(b64decode(r,validate=True) for r in items)
    records=dict(reference=unpack(body['reference']),actual={k:unpack(v) for k,v in body['actual'].items()})
    if _pack_records(manifest,**records)!=body:raise ValueError('noncanonical saved record encoding')
    return records


@dataclass(frozen=True)
class Inspection:
    outcome_head: str
    registry_head: str
    completed_hours: int
    pending_intent: bool
    conflicted_keys: tuple
    continuation_available: bool
    lane_status: tuple
    orphaned_after_conflicted_ancestor: bool
    formal_result: bool = False
    resource_admission: bool = False
    formal_execution_ready: bool = False
    native_execution_authenticated: bool = False
    full_192_hour_execution_verified: bool = False


@dataclass(frozen=True)
class AppendTicket:
    """A precommit handoff to an independent holder, not a database credential."""
    store_identity: str
    sequence: int
    before_heads: tuple
    kind: str
    body: bytes

    @property
    def event(self):
        pred=self.before_heads[1]
        return (self.sequence,pred,self.kind,self.body,
                digest([self.sequence,pred,self.kind,sha256(self.body).hexdigest()]))

    @property
    def after_heads(self):
        head=self.event[-1]
        return (head if self.kind=='outcome' else self.before_heads[0],head)

    @property
    def identity(self):
        return digest([self.store_identity,self.sequence,self.before_heads,self.kind,sha256(self.body).hexdigest()])


def _serial(method):
    @wraps(method)
    def guarded(self,*args,**kwargs):
        if not self._operation.acquire(blocking=False):raise ValueError('owner operation already in progress')
        try:return method(self,*args,**kwargs)
        finally:self._operation.release()
    return guarded


class DevelopmentOwner:
    """Single local lease; append-only SQLite records; no persisted executable carry."""
    def __init__(self,root,manifest,binding,*,create=False,expected_heads=None,
                 retain_prepared=None,recovery_ticket=None):
        if type(manifest) is not Manifest or type(binding) is not SourceBinding:raise ValueError('typed owner configuration required')
        manifest.__post_init__();binding.__post_init__()
        self.manifest,self.binding=manifest,binding
        self._operation=Lock()
        if retain_prepared is not None and not callable(retain_prepared):raise ValueError('external ticket holder must be callable')
        self.retain_prepared=retain_prepared
        self.closed,self.poisoned=False,False
        self.implementation=implementation_identity(manifest)
        self.lease=local._Lease(root,create)
        self.root=self.lease.root;self.path=self.root/'owner.sqlite'
        self.header=self._header_bytes()
        self.genesis=digest(['owner_genesis',sha256(self.header).hexdigest()])
        try:
            if create:
                if expected_heads is not None or recovery_ticket is not None:raise ValueError('create cannot claim existing retained heads')
                with self.path.open('xb') as f:f.flush();os.fsync(f.fileno())
            self.file_identity=local._file_identity(self.path)
            if create:
                with closing(self._connect()) as db:
                    for sql in TABLES:db.execute(sql)
                    db.execute('INSERT INTO header VALUES(1,?)',(self.header,))
                    db.commit()
            elif expected_heads is None:raise ValueError('reopen requires both independently retained heads')
            self.heads=(self.genesis,self.genesis) if create else expected_heads
            if recovery_ticket is not None:
                ticket=recovery_ticket
                if (type(ticket) is not AppendTicket or ticket.store_identity!=self.genesis
                        or ticket.before_heads!=expected_heads or type(ticket.sequence) is not int
                        or ticket.sequence<=0 or ticket.kind not in ('intent','outcome','witness')
                        or type(ticket.body) is not bytes or len(ticket.body)>manifest.max_event_bytes
                        or encode(json.loads(ticket.body))!=ticket.body):
                    raise ValueError('independently retained recovery ticket differs')
                with closing(self._connect()) as db:rows=self._rows(db)
                if self._heads(rows)==ticket.after_heads:
                    if (len(rows)!=ticket.sequence or rows[-1]!=ticket.event
                            or self._heads(rows[:-1])!=expected_heads):
                        raise ValueError('recovery event is not the exact retained next append')
                    self.heads=ticket.after_heads
                elif self._heads(rows)!=expected_heads or len(rows)+1!=ticket.sequence:
                    raise ValueError('database is neither retained before nor exact retained after')
                else:
                    # Validate the proposed next event against the retained prefix,
                    # but never append it during recovery.
                    self._restore(rows+[ticket.event])
            self.inspect(expected_heads=self.heads)
        except BaseException:
            self.close();raise

    def _header_bytes(self):
        return encode(dict(schema=SCHEMA,root=os.path.normcase(str(self.root)),manifest=self.manifest,
            binding=self.binding,implementation_identity=self.implementation,sqlite_version=sqlite3.sqlite_version,
            tables=TABLES,status='DRAFT_NONAUTHORITATIVE',formal_result=False,raw_ingress_owned=False))

    def _check(self):
        if self.closed or self.poisoned:raise ValueError('closed or poisoned owner')
        if self._header_bytes()!=self.header:raise ValueError('live owner configuration changed')
        if self.genesis!=digest(['owner_genesis',sha256(self.header).hexdigest()]):raise ValueError('owner genesis changed')
        self.lease.check()
        if local._file_identity(self.path)!=self.file_identity:raise ValueError('owner database identity changed')
        if implementation_identity(self.manifest)!=self.implementation:raise ValueError('owner implementation changed')
        allowed={'execution.lock','owner.sqlite','owner.sqlite-journal'}
        if any(p.name not in allowed for p in self.root.iterdir()):raise ValueError('unexpected owner namespace entry')
        for path in self.root.iterdir():local._file_identity(path)

    def _connect(self):
        db=sqlite3.connect(self.path.as_uri()+'?mode=rw',uri=True,timeout=0)
        if db.execute('PRAGMA journal_mode=DELETE').fetchone()!=('delete',):
            db.close();raise ValueError('DELETE journal mode required')
        db.execute('PRAGMA synchronous=FULL')
        return db

    def _rows(self,db):
        self._check()
        if db.execute('PRAGMA integrity_check').fetchall()!=[('ok',)]:raise ValueError('owner database integrity')
        schema=db.execute("SELECT sql FROM sqlite_master WHERE name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
        if sorted(sql for (sql,) in schema)!=sorted(TABLES):raise ValueError('owner schema changed')
        if db.execute('SELECT id,body FROM header').fetchall()!=[(1,self.header)]:raise ValueError('owner header changed')
        count,total,largest=db.execute('SELECT count(*),coalesce(sum(length(body)),0),coalesce(max(length(body)),0) FROM events').fetchone()
        m=self.manifest
        if count>m.max_events or total>m.max_archive_bytes or largest>m.max_event_bytes:
            raise ValueError('owner bounded archive exceeded')
        rows=db.execute('SELECT seq,predecessor,kind,body,head FROM events ORDER BY seq').fetchall()
        previous=self.genesis
        for i,(seq,pred,kind,body,head) in enumerate(rows,1):
            if seq!=i or pred!=previous or kind not in ('intent','outcome','witness') or type(body) is not bytes:
                raise ValueError('owner event chain discontinuity')
            if encode(json.loads(body))!=body or digest([seq,pred,kind,sha256(body).hexdigest()])!=head:
                raise ValueError('owner event canonical bytes or head differs')
            previous=head
        return rows

    def _heads(self,rows):
        return (next((r[4] for r in reversed(rows) if r[2]=='outcome'),self.genesis),rows[-1][4] if rows else self.genesis)

    def _append(self,kind,body,expected_rows):
        raw=encode(body);m=self.manifest
        if (len(raw)>m.max_event_bytes or len(expected_rows)+1>m.max_events
                or sum(len(r[3]) for r in expected_rows)+len(raw)>m.max_archive_bytes):
            raise ValueError('owner archive reservation exceeded')
        self._check()
        if self.retain_prepared is None:raise ValueError('independent precommit ticket retention required')
        ticket=AppendTicket(self.genesis,len(expected_rows)+1,self._heads(expected_rows),kind,raw)
        # The caller must persist this ticket independently before acknowledging.
        # Callback acknowledgement is a trust boundary, not a crash-durability proof.
        if self.retain_prepared(ticket)!=ticket.identity:raise ValueError('external holder did not acknowledge the exact ticket')
        self._check()
        if ticket!=AppendTicket(self.genesis,len(expected_rows)+1,self._heads(expected_rows),kind,raw):
            raise ValueError('precommit ticket changed during external handoff')
        with closing(self._connect()) as observed:
            if self._rows(observed)!=expected_rows:raise ValueError('owner changed during external ticket handoff')
        db=self._connect()
        try:
            db.execute('BEGIN IMMEDIATE')
            if self._rows(db)!=expected_rows:raise ValueError('owner changed before atomic append')
            db.execute('INSERT INTO events VALUES(?,?,?,?,?)',ticket.event)
            self._check();db.commit()
            rows=self._rows(db)
            if rows!=expected_rows+[ticket.event]:raise ValueError('committed append readback differs')
            self.heads=self._heads(rows)
            return rows
        except BaseException:
            self.poisoned=True;raise
        finally:db.close()

    def _restore(self,rows):
        genesis=_fresh(self.binding,0,self.binding.genesis_terminal_sha256)
        state=_initial(self.manifest,genesis);states=[state];claims={};conflicts=set();keys=[];pending=None
        for seq,pred,kind,raw,head in rows:
            body=json.loads(raw)
            if kind=='intent':
                if pending is not None:raise ValueError('suffix after bare intent')
                if set(body)!={'hour','terminal','key','source_audit','records','alternate','before_heads'}:
                    raise ValueError('intent schema differs')
                if body['before_heads']!=list(self._heads(rows[:seq-1])):raise ValueError('intent before heads differ')
                hour=body['hour']
                if type(hour) is not int or not 0<=hour<168:raise ValueError('source producer enrollment bound')
                if type(body['alternate']) is not bool:raise ValueError('typed witness mode required')
                if conflicts:raise ValueError('suffix after conflicted ancestor')
                if (not body['alternate'] and (hour!=state.hour or all(v.halted for _,v in state.lanes))
                        or body['alternate'] and not 0<=hour<state.hour):raise ValueError('intent progress invalid')
                before=states[hour];current=_fresh(self.binding,hour,body['terminal'])
                if (body['source_audit']!=json.loads(current.source_projection_audit_payload)
                        or body['key']!=_request(self.manifest,before,current)):
                    raise ValueError('intent source or scientific request changed')
                if body['alternate'] and body['key']!=keys[hour]:raise ValueError('alternate is not the same request key')
                _unpack_records(self.manifest,body['records'])
                pending=(body,before,current,head)
            else:
                if pending is None:raise ValueError('outcome without complete intent')
                intent,before,current,intent_head=pending
                if kind!=('witness' if intent['alternate'] else 'outcome'):raise ValueError('intent/result kind mismatch')
                after,projection=_transition(self.manifest,before,current,_unpack_records(self.manifest,intent['records']))
                expected=dict(intent_head=intent_head,key=intent['key'],projection=json.loads(projection),projection_sha256=sha256(projection).hexdigest())
                if body!=expected:raise ValueError('outer outcome does not reproduce saved evidence')
                key=intent['key'];p=body['projection_sha256']
                if key in claims and claims[key]!=p:conflicts.add(key)
                else:claims.setdefault(key,p)
                if kind=='outcome':state=after;states.append(state);keys.append(key)
                pending=None
        # A late alternate may conflict with an ancestor; preserve all existing outcomes.
        affected=bool(set(keys)&conflicts)
        continuation=(not pending and not affected and state.hour<168 and any(not v.halted for _,v in state.lanes))
        heads=self._heads(rows)
        report=Inspection(*heads,state.hour,pending is not None,tuple(sorted(conflicts)),continuation,
            tuple((k,'halted' if v.halted else 'active') for k,v in state.lanes),affected)
        return report,state,states

    @_serial
    def inspect(self,*,expected_heads):
        return self._inspect(expected_heads=expected_heads)

    def _inspect(self,*,expected_heads):
        self._check()
        with closing(self._connect()) as db:rows=self._rows(db)
        if type(expected_heads) is not tuple or expected_heads!=self._heads(rows):raise ValueError('both retained owner heads must match')
        report,_,_=self._restore(rows)
        with closing(self._connect()) as db:
            if self._rows(db)!=rows:raise ValueError('owner changed during replay')
        self._check()
        return report

    @_serial
    def advance(self,*,expected_heads,terminal_sha256,reference_records,actual_records):
        return self._apply(expected_heads,terminal_sha256,reference_records,actual_records,None)

    @_serial
    def register_alternate_witness(self,*,expected_heads,hour,terminal_sha256,reference_records,actual_records):
        return self._apply(expected_heads,terminal_sha256,reference_records,actual_records,hour)

    def _apply(self,expected_heads,terminal,reference,actual,alternate):
        self._check()
        with closing(self._connect()) as db:rows=self._rows(db)
        if type(expected_heads) is not tuple or expected_heads!=self._heads(rows):raise ValueError('both retained owner heads must match')
        report,state,states=self._restore(rows)
        if report.pending_intent or report.conflicted_keys:raise ValueError('pending intent or sticky conflict forbids continuation')
        if alternate is None:
            if not report.continuation_available:raise ValueError('owner has no admitted next action')
            hour=state.hour
        else:
            if type(alternate) is not int or not 0<=alternate<state.hour:raise ValueError('existing outcome hour required')
            hour=alternate;state=states[hour]
        current=_fresh(self.binding,hour,terminal)
        packed=_pack_records(self.manifest,reference,actual)
        key=_request(self.manifest,state,current)
        if alternate is not None:
            original=next(json.loads(r[3])['key'] for r in rows if r[2]=='intent'
                and json.loads(r[3])['hour']==hour and not json.loads(r[3])['alternate'])
            if original!=key:raise ValueError('alternate is not the same request key')
        intent=dict(hour=hour,terminal=terminal,key=key,
            source_audit=json.loads(current.source_projection_audit_payload),records=packed,
            alternate=alternate is not None,before_heads=expected_heads)
        rows=self._append('intent',intent,rows)
        try:
            after,projection=_transition(self.manifest,state,current,_unpack_records(self.manifest,packed))
            repeated=_fresh(self.binding,hour,terminal)
            if (current.source_projection_audit_payload!=repeated.source_projection_audit_payload
                    or current.exogenous_scientific_payload!=repeated.exogenous_scientific_payload):
                raise ValueError('source changed before paired publication')
            self._check()
            outcome=dict(intent_head=rows[-1][4],key=intent['key'],projection=json.loads(projection),
                         projection_sha256=sha256(projection).hexdigest())
            self._append('outcome' if alternate is None else 'witness',outcome,rows)
            return self._inspect(expected_heads=self.heads)
        except BaseException:
            self.poisoned=True;raise

    def __copy__(self):raise TypeError('owner cannot be copied')
    def __deepcopy__(self,memo):raise TypeError('owner cannot be copied')
    def __reduce_ex__(self,protocol):raise TypeError('owner cannot be serialized')

    @_serial
    def close(self):
        if not self.closed:self.closed=True;self.lease.close()

    def __enter__(self):return self
    def __exit__(self,*args):self.close()
