"""Draft live hour-zero selector-to-phase handoff; no native execution entrypoint.

Consumes existing live parents only. A failure preserves the attempted root and
all child bytes; no retry, head selection, recovery or formal authority is issued.
"""
from base64 import b64encode
from dataclasses import asdict
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from threading import Lock,get_ident
from types import FunctionType,MappingProxyType,ModuleType

from experiments import h1_selector_parent_controller_development_v1 as parent
from experiments import h1_common_owner_genesis_development_v1 as common
from experiments import h1_selector_phase_consumption_development_v1 as preview

phase,bootstrap=common.phase,common.bootstrap
snapshot,sequence=parent.worker.snapshot,parent.worker.sequence
io=parent.io
SCHEMA='h1_selector_phase_handoff_development_v1'
FLAGS=MappingProxyType(dict(parent.FLAGS,live_handoff_detached_credential=False,
    full_192_hour_execution_verified=False,recovery_authorized=False,phase_episode_terminal=False))
_OWNERS={}


def _same(a,b):
    if phase.encode(a)!=phase.encode(b):raise ValueError('phase handoff correspondence differs')


def _phase_identity(owner):
    return (owner.file_identity,owner._lease_object.root_identity,owner._lease_object.file_identity)


def _transaction(self):
    p=self._plan
    planned=phase.encode(dict(tickets=[phase.tickets._ticket_payload(t) for t in p.tickets],
        holder_records=[b64encode(r).decode('ascii') for r in p.holder_records],retentions=p.retentions,
        projection=json.loads(p.projection),after=json.loads(p.after)))
    return (id(p),planned,phase.encode(self._events),self._packet,self._common_view,self._report,
        self._child_headers,self._original_binder,self._header)


def _dependencies():
    """Original project callables/module edges, including imported-by-name roots."""
    pending=[parent,common,phase,preview,snapshot,sequence,bootstrap,io];seen=set();records=[];modules=[]
    project=lambda name:name.startswith(('experiments.','src.'))
    while pending:
        module=pending.pop()
        if id(module) in seen:continue
        seen.add(id(module));modules.append(module)
        for name,value in tuple(vars(module).items()):
            if isinstance(value,ModuleType) and project(value.__name__):
                records.append((module,name,value));pending.append(value)
            elif callable(value):
                records.append((module,name,value));origin=getattr(value,'__module__','')
                if project(origin) and origin in sys.modules:pending.append(sys.modules[origin])
                if isinstance(value,type) and (project(origin) or module is parent):
                    for key,descriptor in tuple(vars(value).items()):
                        if callable(descriptor) or isinstance(descriptor,(property,staticmethod,classmethod)):
                            records.append((value,key,descriptor))
    return tuple(records),tuple(modules)


def _protocols(modules):
    def plain(v):
        if isinstance(v,(dict,MappingProxyType)):return {k:plain(x) for k,x in v.items()}
        if type(v) in (tuple,list):return [plain(x) for x in v]
        if type(v) in (set,frozenset):return sorted(plain(x) for x in v)
        return v
    return phase.encode([(m.__name__,{k:plain(v) for k,v in vars(m).items()
        if k.isupper() and not k.startswith('_') and not callable(v)
        and (any(word in k for word in ('SCHEMA','CAP','LIMIT','MAX')) or k in
            ('FLAGS','INPUTS','OUTPUTS','PHASES','FILES','INPUT_FILES','OUTPUT_FILES'))}) for m in modules])


def implementation_identity():
    _CHECK()
    return io.digest(phase.encode([SCHEMA,__name__,sha256(Path(__file__).read_bytes()).hexdigest(),
        parent.implementation_identity(),common.implementation_identity(),
        sha256(Path(preview.__file__).read_bytes()).hexdigest()]))


class _Bundle:
    """Exact private adapter; locks remain held across the entire transaction."""
    __slots__=('actuals','held','marked','reference')
    def __init__(self,reference,actuals):
        if type(reference) is not tuple or len(reference)!=2 or type(actuals) is not dict:
            raise TypeError('exact reference pair and complete Actual dictionary required')
        self.reference=reference;self.actuals=tuple(sorted(actuals.items()));self.held=[];self.marked=[]
        pairs=(reference,*(p for _,p in self.actuals if p is not None))
        for pair in pairs:
            if (type(pair) is not tuple or len(pair)!=2 or type(pair[0]) is not parent.Parent
                    or type(pair[1]) is not parent.ParentCompletion):raise TypeError('exact live Parent pair required')
        if len({id(p[0]) for p in pairs})!=len(pairs):raise ValueError('distinct lane parent owners required')
        r,receipt=reference
        if receipt.role!='reference' or r._reference_owner is not None:raise ValueError('unique reference parent required')
        for lane,pair in self.actuals:
            if type(lane) is not str:raise TypeError('exact lane IDs required')
            if pair is not None:
                owner,issued=pair
                if (issued.role!='actual' or owner._reference_owner is not r or owner._reference_completion is not receipt
                        or owner._reference_held is not False):raise ValueError('exact Actual reference dependency required')

    def enter(self):
        _CHECK()
        if self.held:raise ValueError('bundle already active')
        try:
            for owner,_ in (*(p for _,p in self.actuals if p is not None),self.reference):
                guard=owner._guard
                parent.Parent._enter(owner);self.held.append(guard)
            for _,pair in self.actuals:
                if pair is not None:
                    pair[0]._reference_held=True;self.marked.append(pair[0])
            self.validate()
        except BaseException:self.leave();raise

    def validate(self):
        _CHECK()
        if len(self.held)!=1+sum(p is not None for _,p in self.actuals):raise ValueError('whole parent bundle guard required')
        parent.Parent._validate(*self.reference)
        for _,pair in self.actuals:
            if pair is not None:parent.Parent._validate(*pair)
        _CHECK()

    def records(self,pair):
        owner,receipt=pair
        parent.Parent._validate(owner,receipt)
        item=snapshot.rebuild(owner._raw,expected_sha256=io.digest(owner._raw))
        data=json.loads(owner._outcome)['inspection']['data']
        request=json.loads(owner._declaration)['request']
        science=owner.worker_root/'science_sequence_non_authoritative'
        timing=owner.worker_root/'timing_sequence_non_authoritative'
        result=sequence.inspect(science,timing,item.frame,item.disclosure,item.before,
            expected_terminal_sha256=data['sequence_terminal_sha256'],max_archive_bytes=item.max_archive_bytes,
            max_timing_archive_bytes=request['max_timing_archive_bytes'],run_configuration=item.run_configuration,**item.arguments)
        count=len(result['records'])
        view=sequence._snapshot(science,timing,count,item.arguments['limits'],True,True)
        _same([result['request_sha256'],result['scientific_terminal_sha256'],
            [io.digest(r) for r in result['records']],sequence._snapshot_pin(view,science,timing)],
            [receipt.sequence_request_sha256,receipt.scientific_terminal_sha256,data['record_sha256'],data['archive_view_sha256']])
        _same(receipt.scientific_request_sha256,result['science']['request_sha256'])
        if str(science)!=receipt.scientific_root:raise ValueError('science root differs')
        parent.Parent._validate(owner,receipt)
        return result['records']

    def leave(self):
        for owner in reversed(self.marked):owner._reference_held=False
        self.marked.clear()
        for guard in reversed(self.held):guard.release()
        self.held.clear()


class Handoff:
    """Single attempt, one creating thread; no externally supplied record bytes."""
    __slots__=('_binding_view','_bundle','_caps','_child_headers','_children','_closed_genesis','_common_view',
        '_configuration','_events','_genesis','_guard','_header','_holder','_holder_callback','_in_external',
        '_journal','_journal_callback','_journal_count','_lease','_names','_original_binder','_own','_packet',
        '_packet_view','_phase','_pid','_plan','_report','_retain','_retained','_self','_state','_thread','root')
    def __init__(self,genesis,reference,actuals,*,retain_head,max_packet_bytes,max_record_bytes,max_archive_bytes):
        _CHECK()
        if type(genesis) is not common.CommonOwnerGenesis:raise TypeError('exact live common genesis required')
        if (not callable(retain_head) or any(type(n) is not int or n<=0 for n in
                (max_packet_bytes,max_record_bytes,max_archive_bytes)) or not 1024<=max_record_bytes<=1024**2):
            raise ValueError('explicit packet/journal bounds and external retention required')
        self._self=self;self._pid,self._thread=os.getpid(),get_ident();self._guard=Lock()
        self._genesis=genesis;self._bundle=_Bundle(reference,actuals);self._retain=retain_head
        self._caps=(max_packet_bytes,max_record_bytes,max_archive_bytes)
        self._state='new';self._lease=self._journal=self._holder=self._phase=None
        self._retained=0;self._plan=None;self._packet=None;self._packet_view=None
        self._report=None;self._common_view=None;self._header=None;self._events=None
        self._child_headers=None;self._original_binder=None;self._closed_genesis=False
        self._binding_view=None;self._names={'execution.lock'};self._children=None
        self._journal_count=0;self._in_external=False
        self._holder_callback=self._retain_holder;self._journal_callback=self._retain_journal
        self._own=implementation_identity()
        self.root=bootstrap.local._path(genesis._roster._owner.study_root/'selector_phase_handoffs_non_authoritative'/genesis.root.name)
        self._configuration=(genesis,reference,tuple(sorted(actuals.items())),retain_head,self._caps,self.root,self._own,
            self._holder_callback,self._journal_callback)
        _REGISTER(self)

    def _check(self):
        _CHECK()
        _VERIFY_OWNER(self)
        if (self._self is not self or _OWNERS.get(id(self)) is not self or (os.getpid(),get_ident())!=(self._pid,self._thread)
                or self._state not in ('new','running','complete') or self._own!=implementation_identity()
                or (self._genesis,self._bundle.reference,self._bundle.actuals,self._retain,self._caps,self.root,self._own,
                    self._holder_callback,self._journal_callback)!=self._configuration):
            raise ValueError('handoff live owner or declaration changed')
        if self._lease is not None:
            self._lease.check()
        if self._binding_view is not None:
            if parent.worker._read(self.root/'binding.json',self._caps[1])!=self._binding_view:
                raise ValueError('handoff binding changed')

    def _correspondence(self):
        self._check();g=self._genesis
        manifest,binding,report=common.common._prepare_locked(g._roster)
        _same([asdict(manifest),asdict(binding),report],
            [asdict(g._manifest),asdict(g._binding),json.loads(self._report)])
        if not self._closed_genesis:
            _same(snapshot._owner_view(g),json.loads(self._common_view))
        else:
            if not g.closed:raise ValueError('predecessor genesis must remain closed')
            for path,view in self._original_binder:
                if parent.worker._read(path,g.max_record_bytes)!=view:raise ValueError('predecessor binder changed')
            if {p.name for p in g.root.iterdir()}!={p.name for p,_ in self._original_binder}|{'execution.lock'}:
                raise ValueError('predecessor binder namespace changed')
        if self._packet_view is not None:
            if parent.worker._read(self.root/'takeover_packet.json',self._caps[0])!=self._packet_view:
                raise ValueError('retained takeover packet changed')
        if self._children is not None:
            h,p=self._children
            if self._holder is not h or self._phase is not p or h.retain_head!=self._holder_callback:
                raise ValueError('handoff child ownership changed')
            h._check();phase._SavedOwner._check(p)
            if phase.encode(h.binding)!=self._child_headers[2] or p.holder is not h or p.retain_prepared!=h.retain:
                raise ValueError('handoff child binding changed')
            if _phase_identity(p)!=self._child_headers[3]:raise ValueError('original phase file identities changed')
        self._check()

    def _prepare(self):
        g=self._genesis;bundle=self._bundle
        view=snapshot._owner_view(g)
        manifest,binding,report=common.common._prepare_locked(g._roster)
        self._common_view=phase.encode(view);self._report=phase.encode(report)
        ids=tuple(c.lane_id for c in manifest.lanes)
        if tuple(k for k,_ in bundle.actuals)!=ids:raise ValueError('complete exact Actual disposition roster required')
        for lane,pair in ((None,bundle.reference),*bundle.actuals):
            if pair is None:continue
            doc=json.loads(pair[0]._raw)['declaration']
            captured=dict(doc['provenance']);current_view=dict(view)
            captured_global=captured.pop('global_head');current_view.pop('global_head')
            global_=g._roster._owner._global
            if captured_global not in {global_.genesis,*(head for head,_ in global_.rows())}:
                raise ValueError('Parent captured global head is not a retained ancestor')
            _same([captured,doc['manifest'],doc['source_binding'],doc['lane_id']],
                [current_view,asdict(manifest),asdict(binding),lane])
        current=phase._fresh(binding,0,binding.genesis_terminal_sha256)
        reference=bundle.records(bundle.reference)
        base=preview._planned_bootstrap(manifest,binding,current,owner_genesis=g._phase.genesis,
            holder_genesis=g._holder.genesis,reference_records=reference,actual_records={k:() for k in ids})
        disposition={r['lane_id']:r['status'] for r in json.loads(base.projection)['lanes']}
        actual={};typed=[]
        for lane,pair in bundle.actuals:
            unresolved=disposition[lane] in ('business_input_unresolved','business_unresolved')
            if pair is None:
                if not unresolved:raise ValueError('Actual execution missing or failed: keep pending')
                actual[lane]=();typed.append(dict(lane_id=lane,kind='business_unresolved_before_actual'))
            else:
                if unresolved:raise ValueError('unused Actual execution for unresolved business')
                actual[lane]=bundle.records(pair);typed.append(dict(lane_id=lane,kind='paired_actual'))
        plan=preview._planned_bootstrap(manifest,binding,current,owner_genesis=g._phase.genesis,
            holder_genesis=g._holder.genesis,reference_records=reference,actual_records=actual)
        if any(r['status'] not in ('paired_committed','business_input_unresolved','business_unresolved')
                for r in json.loads(plan.projection)['lanes']):raise ValueError('authenticated complete disposition required')
        self._plan=plan
        parents=[dict(lane_id=lane,completion=json.loads(parent._completion_bytes(pair[1])),snapshot_sha256=io.digest(pair[0]._raw))
            for lane,pair in ((None,bundle.reference),*bundle.actuals) if pair is not None]
        phase_identity=_phase_identity(g._phase)
        packet=phase.encode(dict(schema=SCHEMA,implementation=self._own,common=view,group_audit=report,
            phase_file_identity=phase_identity,
            dispositions=typed,parents=parents,tickets=[phase.tickets._ticket_payload(t) for t in plan.tickets],
            holder_records=[b64encode(raw).decode('ascii') for raw in plan.holder_records],retentions=plan.retentions,
            projection=json.loads(plan.projection),after=json.loads(plan.after),**FLAGS))
        declaration=dict(schema=SCHEMA,implementation=self._own,packet_sha256=io.digest(packet),packet_bytes=len(packet),
            packet_cap=self._caps[0],total_archive_cap=self._caps[2],common=view,**FLAGS)
        journal_root=self.root/'journal_non_authoritative'
        header=bootstrap._journal_header(journal_root,declaration,5,self._caps[1],bootstrap.implementation_identity())
        binding_worst=phase.encode(dict(declaration=declaration,journal_root=str(journal_root),
            root=str(self.root),root_identity=(10**40-1,)*2,file_identity=(10**40-1,)*2,
            packet_stamp=(10**40-1,)*5,**FLAGS))
        events=(dict(kind='takeover_intent',packet_sha256=io.digest(packet),packet_bytes=len(packet),
                packet_stamp=(10**40-1,)*5,binding_sha256='0'*64,expected_phase_heads=plan.tickets[-1].after_heads,**FLAGS),
            dict(kind='handoff_opened',holder_header_sha256=io.digest(g._holder.header),owner_header_sha256=io.digest(g._phase.header),**FLAGS),
            *(dict(kind=f'holder_head_prepared_{i}',retention=r,**FLAGS) for i,r in enumerate(plan.retentions,1)),
            dict(kind='bootstrap_consumed_terminal',holder_head=plan.retentions[-1][2],phase_heads=plan.tickets[-1].after_heads,
                projection_sha256=io.digest(plan.projection),completed_hours=1,**FLAGS))
        head=io.digest(header);sizes=[]
        for i,event in enumerate(events,1):
            raw=phase.encode(dict(sequence=i,previous=head,body=event));sizes.append(len(raw));head=io.digest(raw)
        if (len(packet)>self._caps[0] or max(len(header),len(binding_worst),*sizes)>self._caps[1]
                or len(packet)+len(binding_worst)+len(header)+sum(sizes)>self._caps[2]):raise ValueError('complete handoff archive branch exceeds declared bounds')
        self._packet,self._header,self._events=packet,header,events
        self._child_headers=(g._holder.header,g._phase.header,phase.encode(g._holder.binding),phase_identity)
        self._original_binder=tuple((p,parent.worker._read(p,g.max_record_bytes)) for p in sorted(g.root.iterdir()) if p.name!='execution.lock')
        self._correspondence()
        return declaration,reference,actual

    def _retain_journal(self,root,before,after):
        check,verify=_CHECK,_VERIFY_OWNER
        enter_external,leave_external,advance=_ENTER_EXTERNAL,_LEAVE_EXTERNAL,_ADVANCE_COUNT
        check();verify(self)
        if self._in_external or not self._guard.locked():raise ValueError('owned nonreentrant journal handoff required')
        count=self._journal_count+1
        def prefix():
            self._correspondence();self._bundle.validate()
            if root!=self.root/'journal_non_authoritative' or count!=self._journal_count+1 or not 1<=count<=5:
                raise ValueError('journal callback stage differs')
            if {p.name for p in root.iterdir()}!={'execution.lock','header.json',*(f'{i:020d}.json' for i in range(1,count+1))}:
                raise ValueError('journal callback namespace differs')
            views=[parent.worker._read(root/'header.json',self._caps[1])]
            if views[0][0]!=self._header:raise ValueError('journal header changed at retention')
            head=io.digest(self._header)
            for i in range(1,count+1):
                observed=parent.worker._read(root/f'{i:020d}.json',self._caps[1]);views.append(observed)
                raw=phase.encode(dict(sequence=i,previous=head,body=self._events[i-1]))
                if observed[0]!=raw:raise ValueError('journal retained prefix differs')
                if i==count and head!=before:raise ValueError('journal predecessor differs')
                head=io.digest(raw)
            if head!=after or self._journal.head!=before:raise ValueError('journal prospective head differs')
            return tuple(views)
        views=prefix();external_token=enter_external(self)
        try:returned=self._retain(root,before,after)
        finally:leave_external(self,external_token)
        check();verify(self)
        if prefix()!=views:raise ValueError('journal replaced during external retention')
        if returned!=after:raise ValueError('exact external journal head acknowledgement required')
        advance(self,'_journal_count',count,external_token)
        return returned

    def _retain_holder(self,genesis,before,after,count):
        self._correspondence()
        if (self._in_external or self._children is None or not self._phase._operation.locked() or not self._holder._guard.locked()
                or type(count) is not int or count!=self._retained+1 or count not in (1,2)
                or (genesis,before,after,count)!=self._plan.retentions[count-1]):raise ValueError('unplanned holder retention callback')
        self._journal.append(self._events[count+1],expected_head=self._journal.head)
        self._correspondence();_ADVANCE_COUNT(self,'_retained',count)
        return after

    def _readback(self):
        self._correspondence();p=self._plan
        if self._retained!=2 or self._holder.inspect()!=p.tickets or self._holder.head!=p.retentions[-1][2]:
            raise ValueError('paired holder readback differs')
        with phase.closing(self._phase._connect()) as db:rows=self._phase._rows(db)
        if rows!=[t.event for t in p.tickets] or self._phase.heads!=p.tickets[-1].after_heads:
            raise ValueError('paired database readback differs')
        result=self._phase.inspect(expected_heads=self._phase.heads)
        if result.completed_hours!=1 or result.pending_intent or result.pending_attempt or result.recovery_required or result.conflicted_keys:
            raise ValueError('complete paired bootstrap required')
        if self._holder.header!=self._child_headers[0] or self._phase.header!=self._child_headers[1]:
            raise ValueError('child headers changed')
        self._bundle.validate();self._correspondence()

    def consume(self):
        _CHECK()
        if type(self) is not Handoff or self._self is not self:raise TypeError('exact original handoff required')
        guard=self._guard
        if not guard.acquire(False):raise ValueError('handoff operation active')
        bundle=self._bundle;g=self._genesis;common_held=False;parents_held=False;attempted=False;token=None
        parent_guards=();parent_marks=()
        cleanup,common_leave=Handoff._close_handles,common.CommonOwnerGenesis._leave
        begin,end,record_handle,record_view,seal,record_bundle=_BEGIN,_END,_RECORD_HANDLE,_RECORD_VIEW,_SEAL,_RECORD_BUNDLE
        record_predecessor,close_predecessor=_RECORD_PREDECESSOR,_CLOSE_PREDECESSOR
        try:
            self._check()
            if self._state!='new':raise ValueError('handoff is single-attempt')
            token=begin(self);self._state='running';attempted=True
            bundle.enter();parents_held=True
            parent_guards,parent_marks=tuple(bundle.held),tuple(bundle.marked)
            record_bundle(self,token)
            common.CommonOwnerGenesis._enter(g);common_held=True
            record_predecessor(self,token)
            declaration,reference,actual=self._prepare()
            self.root.parent.mkdir(exist_ok=True)
            self._lease=bootstrap.local._Lease(self.root,True)
            record_handle(self,token,'_lease',self._lease)
            io.write_new(self.root/'takeover_packet.json',self._packet)
            self._names.add('takeover_packet.json')
            self._packet_view=parent.worker._read(self.root/'takeover_packet.json',self._caps[0])
            if self._packet_view[0]!=self._packet:raise ValueError('packet readback differs')
            record_view(self,token,'takeover_packet.json',self._packet_view)
            stamp=self._packet_view[1]
            identities=(*self._lease.root_identity,*self._lease.file_identity)
            if len(stamp)!=5 or len(identities)!=4 or any(type(n) is not int or not 0<=n<10**40 for n in (*stamp,*identities)):
                raise ValueError('bounded outer identity and packet stamp required')
            binding=phase.encode(dict(declaration=declaration,journal_root=str(self.root/'journal_non_authoritative'),
                root=str(self.root),root_identity=self._lease.root_identity,file_identity=self._lease.file_identity,packet_stamp=stamp,**FLAGS))
            if len(binding)>self._caps[1]:raise ValueError('binding cap exceeded')
            io.write_new(self.root/'binding.json',binding);self._names.add('binding.json')
            self._binding_view=parent.worker._read(self.root/'binding.json',self._caps[1])
            if self._binding_view[0]!=binding:raise ValueError('binding readback differs')
            record_view(self,token,'binding.json',self._binding_view)
            self._events=(dict(self._events[0],packet_stamp=stamp,binding_sha256=io.digest(binding)),*self._events[1:])
            seal(self,token)
            self._journal=bootstrap._Journal(self.root/'journal_non_authoritative',declaration,max_events=5,
                max_record_bytes=self._caps[1],create=True,expected_head=None,retain_head=self._journal_callback)
            record_handle(self,token,'_journal',self._journal)
            self._names.add('journal_non_authoritative')
            if self._journal._header!=self._header:raise ValueError('journal header differs from preflight')
            self._journal.append(self._events[0],expected_head=self._journal.head)
            self._correspondence()
            # Keep common operation and roster locked throughout the handoff gap.
            close_predecessor(self,token)
            m=g._manifest
            self._holder=phase.tickets.TicketHolder(g.holder_root,owner_root=g.owner_root,max_tickets=m.max_events,
                max_ticket_bytes=m.max_event_bytes,max_total_ticket_bytes=m.max_archive_bytes,create=False,
                expected_head=json.loads(self._common_view)['holder_receipt']['head'],retain_head=self._holder_callback)
            record_handle(self,token,'_holder',self._holder)
            if (self._holder.header!=self._child_headers[0] or phase.encode(self._holder.binding)!=self._child_headers[2]
                    or self._holder.inspect()!=()):raise ValueError('reopened holder differs from retained genesis')
            self._phase=phase.DevelopmentOwner(g.owner_root,m,g._binding,holder=self._holder,create=False,
                expected_heads=tuple(json.loads(self._common_view)['owner_receipt']['heads']))
            record_handle(self,token,'_phase',self._phase)
            if self._phase.header!=self._child_headers[1]:raise ValueError('reopened phase header differs')
            if _phase_identity(self._phase)!=self._child_headers[3]:raise ValueError('original phase file identities changed')
            self._children=(self._holder,self._phase)
            self._correspondence()
            self._journal.append(self._events[1],expected_head=self._journal.head)
            self._phase.advance(expected_heads=self._phase.heads,terminal_sha256=g._binding.genesis_terminal_sha256,
                reference_records=reference,actual_records=actual)
            self._readback()
            self._journal.append(self._events[-1],expected_head=self._journal.head)
            self._readback()
            _same([v for _,v in self._journal.rows()],self._events)
            self._state='complete'
            return dict(schema=SCHEMA,root=str(self.root),journal_head=self._journal.head,
                holder_head=self._holder.head,phase_heads=self._phase.heads,completed_hours=1,
                fresh_at_return_only=True,**FLAGS)
        except BaseException:
            if attempted:
                self._state='failed'
                cleanup(self)
            raise
        finally:
            try:
                if common_held:common_leave(g)
            finally:
                try:
                    if parents_held:
                        for owner in reversed(parent_marks):owner._reference_held=False
                        for held_guard in reversed(parent_guards):held_guard.release()
                        bundle.held=[];bundle.marked=[]
                finally:
                    try:
                        if token is not None:end(self,token)
                    finally:guard.release()

    def _close_handles(self):
        try:
            if self._phase is not None:phase.DevelopmentOwner.close(self._phase)
        finally:
            try:
                if self._holder is not None:phase.tickets.TicketHolder.close(self._holder)
            finally:
                try:
                    if self._journal is not None:bootstrap._Journal.close(self._journal)
                finally:
                    if self._lease is not None:bootstrap.local._Lease.close(self._lease)

    def close(self):return _CLEANUP(self)

    def __enter__(self):self._check();return self
    def __exit__(self,*args):self.close()
    def _no_copy(self,*args):raise TypeError('live handoff cannot be copied')
    __copy__=__deepcopy__=__reduce_ex__=_no_copy


def _anchor():
    namespace=vars(sys.modules[__name__]);parent_check=parent._CHECK
    owner_type,registry,pid,thread=Handoff,_OWNERS,os.getpid,get_ident
    owned={};transaction=_transaction
    handle_names=('_phase','_holder','_journal','_lease')
    closers=(phase.DevelopmentOwner.close,phase.tickets.TicketHolder.close,bootstrap._Journal.close,bootstrap.local._Lease.close)
    old_close=common.CommonOwnerGenesis._close_handles;lease_close=bootstrap.local._Lease.close
    def register(self):
        if type(self) is not owner_type or id(self) in owned:raise ValueError('new exact handoff owner required')
        owned[id(self)]=dict(owner=self,configuration=self._configuration,bundle=self._bundle,guard=self._guard,
            creator=(self._pid,self._thread),bundle_state=None,predecessor=None,predecessor_leases=None,
            external_active=False,external_token=None,counts={'_journal_count':0,'_retained':0},
            handles={name:None for name in handle_names},views={},transaction=None,token=None,released=set())
        registry[id(self)]=self
    def lookup(self):
        record=owned.get(id(self))
        if (type(self) is not owner_type or record is None or record['owner'] is not self or registry.get(id(self)) is not self
                or self._self is not self or self._configuration is not record['configuration']
                or self._bundle is not record['bundle'] or self._guard is not record['guard']
                or (pid(),thread())!=record['creator'] or (self._pid,self._thread)!=record['creator']):
            raise ValueError('original registered handoff identity required')
        return record
    def verify(self):
        record=lookup(self)
        if self._in_external is not record['external_active'] or any(getattr(self,k)!=v for k,v in record['counts'].items()):
            raise ValueError('original callback state or counters changed')
        if any(getattr(self,k) is not v for k,v in record['handles'].items()):raise ValueError('original handoff handles changed')
        if (self._packet_view!=record['views'].get('takeover_packet.json')
                or self._binding_view!=record['views'].get('binding.json')):raise ValueError('retained outer views changed')
        if self._lease is not None:
            names={'execution.lock',*record['views']}
            if self._journal is not None:names.add('journal_non_authoritative')
            if {p.name for p in self.root.iterdir()}!=names:raise ValueError('fixed handoff outer namespace differs')
        if record['transaction'] is not None and transaction(self)!=record['transaction']:
            raise ValueError('immutable handoff transaction changed')
        if record['bundle_state'] is not None and (self._bundle.reference,self._bundle.actuals,
                tuple(self._bundle.held),tuple(self._bundle.marked))!=record['bundle_state']:
            raise ValueError('original held parent bundle changed')
        if record['predecessor'] is not None:
            g,p,h,j,r,guard=record['predecessor']
            if (self._genesis is not g or g._phase is not p or g._original_phase is not p
                    or g._holder is not h or g._original_holder is not h or g._journal is not j or g._original_journal is not j
                    or g._roster is not r or g._original_roster is not r or g._original_operation is not guard):
                raise ValueError('original common genesis handles changed')
    def begin(self):
        record=lookup(self)
        if record['token'] is not None or not record['guard'].locked():raise ValueError('exclusive handoff operation required')
        token=record['token']=object();return token
    def enter_external(self):
        record=lookup(self);verify(self)
        if record['token'] is None or record['external_active'] or not record['guard'].locked():
            raise ValueError('owned nonreentrant external retention required')
        if record['external_token'] is not None:raise ValueError('previous external retention not advanced')
        token=object();record['external_token']=token
        record['external_active']=True;self._in_external=True
        return token
    def leave_external(self,token):
        record=lookup(self)
        if token is None or token is not record['external_token'] or not record['external_active']:
            raise ValueError('original external retention token required')
        record['external_active']=False;self._in_external=False
    def advance_count(self,name,count,token=None):
        record=lookup(self);verify(self)
        if (record['token'] is None or record['external_active'] or name not in record['counts']
                or type(count) is not int or count!=record['counts'][name]+1):
            raise ValueError('original sequential retention count required')
        if name=='_journal_count':
            if token is None or token is not record['external_token']:raise ValueError('original external retention token required')
            record['external_token']=None
        elif token is not None or record['external_token'] is not None:
            raise ValueError('external retention must precede holder retention')
        record['counts'][name]=count;setattr(self,name,count)
    def operation(self,token):
        record=lookup(self)
        if token is None or record['token'] is not token or not record['guard'].locked():raise ValueError('original handoff operation token required')
        return record
    def end(self,token):
        record=operation(self,token);record['token']=None;record['bundle_state']=None
    def record_bundle(self,token):
        record=operation(self,token);b=record['bundle']
        if record['bundle_state'] is not None:raise ValueError('parent bundle already retained')
        record['bundle_state']=(b.reference,b.actuals,tuple(b.held),tuple(b.marked))
    def record_predecessor(self,token):
        record=operation(self,token);g=self._genesis
        if record['predecessor'] is not None:raise ValueError('predecessor already retained')
        record['predecessor']=(g,g._original_phase,g._original_holder,g._original_journal,g._original_roster,g._original_operation)
        record['predecessor_leases']=(g._original_phase._lease_object,g._original_holder._lease_object,g._original_journal._original_lease)
    def close_predecessor(self,token):
        record=operation(self,token);g,p,h,j,_,_=record['predecessor'];first=None
        try:old_close(g)
        except BaseException as exc:first=exc;g.poisoned=True
        finally:
            g.closed=True;self._closed_genesis=True
            # A child close can fail before releasing its lease. Close only the
            # captured predecessor leases that still own a stream, never a new
            # lease reopened by another handle or a replaced public attribute.
            for handle,lease in zip((p,h,j),record['predecessor_leases'],strict=True):
                if lease.stream is not None:
                    try:lease_close(lease)
                    except BaseException as exc:
                        if first is None:first=exc
                    finally:handle.closed=True
        if first is not None:raise first
    def record_handle(self,token,name,handle):
        record=operation(self,token)
        if name not in handle_names or record['handles'][name] is not None or getattr(self,name) is not handle:
            raise ValueError('create-once original handle registration required')
        record['handles'][name]=handle
    def record_view(self,token,name,view):
        record=operation(self,token)
        if name not in ('takeover_packet.json','binding.json') or name in record['views']:
            raise ValueError('create-once original file retention required')
        record['views'][name]=view
    def seal(self,token):
        record=operation(self,token)
        if record['transaction'] is not None:raise ValueError('transaction already fixed')
        record['transaction']=transaction(self)
    def close_handles(self):
        # Use only closure-owned originals, even when public fields were replaced.
        record=owned.get(id(self))
        if record is None or record['owner'] is not self:raise ValueError('registered cleanup owner required')
        first=None
        for name,close in zip(handle_names,closers,strict=True):
            handle=record['handles'][name]
            if handle is None or name in record['released']:continue
            record['released'].add(name)
            try:
                close(handle)
            except BaseException as exc:
                if first is None:first=exc
        if first is not None:raise first
    def cleanup(self):
        if type(self) is not owner_type:raise TypeError('exact handoff owner required')
        record=owned.get(id(self))
        if record is None:
            if self._state=='closed':return
            raise ValueError('registered handoff owner required')
        if record['owner'] is not self:raise ValueError('registered handoff owner required')
        if (pid(),thread())!=record['creator']:raise ValueError('handoff creating thread required')
        guard=record['guard']
        if not guard.acquire(False):raise ValueError('cannot close active handoff')
        try:
            if self._state=='closed':return
            if registry.get(id(self)) is not self:raise ValueError('registered handoff owner required')
            try:close_handles(self)
            finally:self._state='closed';registry.pop(id(self),None);owned.pop(id(self),None)
        finally:guard.release()
    def leave(self,*args):return cleanup(self)
    namespace['_CLEANUP']=cleanup
    namespace.update(_REGISTER=register,_VERIFY_OWNER=verify,_BEGIN=begin,_END=end,
        _ENTER_EXTERNAL=enter_external,_LEAVE_EXTERNAL=leave_external,_ADVANCE_COUNT=advance_count,
        _RECORD_HANDLE=record_handle,_RECORD_VIEW=record_view,_SEAL=seal,_RECORD_BUNDLE=record_bundle,
        _RECORD_PREDECESSOR=record_predecessor,_CLOSE_PREDECESSOR=close_predecessor)
    owner_type.close,owner_type.__exit__,owner_type._close_handles=cleanup,leave,close_handles
    def guarded(function):
        def entry(*args,**kwargs):
            if not args or type(args[0]) is not owner_type:raise TypeError('exact original handoff required')
            check()
            if function.__name__!='__init__':verify(args[0])
            return function(*args,**kwargs)
        return entry
    for name in ('__init__','consume','_check','__enter__'):
        setattr(owner_type,name,guarded(vars(owner_type)[name]))
    functions=tuple((obj,name,value) for obj in (sys.modules[__name__],_Bundle,Handoff,common.CommonOwnerGenesis,
            bootstrap._Journal,phase.DevelopmentOwner,phase._SavedOwner,phase.tickets.TicketHolder)
        for name,value in tuple(vars(obj).items()) if isinstance(value,(FunctionType,staticmethod,classmethod,property)))
    dependencies,modules=_dependencies();protocols=_protocols(modules);protocol_read=_protocols
    retained=tuple((name,value) for name,value in namespace.items() if name!='_CHECK')
    def check():
        if (namespace.get('_CHECK') is not check or any(namespace.get(k) is not v for k,v in retained)
                or any(vars(o).get(k) is not v for o,k,v in (*functions,*dependencies))):
            raise ValueError('handoff original scope changed')
        if protocol_read(modules)!=protocols:raise ValueError('handoff dependency protocol changed')
        parent_check()
    return check


_CHECK=_anchor()
