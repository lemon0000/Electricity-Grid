"""Read-only worker input reconstruction under a separately held parent lease.

Every read is externally pinned. No locks are acquired/released, no files are
written, and no serialized owned carry is accepted as scientific evidence.
"""
from copy import deepcopy
from dataclasses import asdict, dataclass
from hashlib import sha256
from pathlib import Path
import stat

from experiments import h1_bounded_file_parent_development_v1 as bounded
from src.solvers.rq2_solver_adapter import Rq2SolverSpec

journal, anchor = bounded.journal, bounded.anchor
io, chunks = journal.io, bounded.chunks
source, binding, replay = bounded.source, bounded.binding, bounded.replay
SCHEMA = 'h1_parent_snapshot_development_v1'


def implementation_identity():
    return io.digest(io.encode([SCHEMA,bounded.implementation_identity(),
        sha256(Path(__file__).read_bytes()).hexdigest()]))


def _input_record(packet,specification,limits,*,parent_identity,anchor_pin,head,source_identity):
    return dict(schema=SCHEMA,parent_identity=parent_identity,parent_declaration_sha256=parent_identity,
        anchor_record_sha256=anchor_pin,journal_head=head,intent_head=head,
        relative_hour=packet.relative_hour,source_lineage_identity=source_identity,
        before_identity=source._digest(packet.before),request_key=replay.request_key(packet,specification,limits),
        packet_audit_identity=packet.audit_identity,stage_slots=len(replay.native.model_api.stage_order(packet.inputs)),
        snapshot_implementation=implementation_identity(),writer_lock_authenticated=False,
        quiescence_certified=False,native_execution_authorized=False,independent_job_integrated=False,
        resource_admission=False,formal_execution_ready=False,formal_result=False,
        external_live_handoff_required=True,solver_calls_by_reader=0)


@dataclass(frozen=True)
class PendingWorkerInput:
    packet: source.H1CurrentNormal
    specification: Rq2SolverSpec
    limits: replay.H1HourReplayLimits
    receipt: bytes

    def __post_init__(self):
        if (type(self.packet) is not source.H1CurrentNormal or type(self.specification) is not Rq2SolverSpec
                or type(self.limits) is not replay.H1HourReplayLimits
                or type(self.receipt) is not bytes or len(self.receipt)>io.META_CAP):
            raise ValueError('exact bounded typed worker input required')
        record=bounded.json.loads(self.receipt)
        for field in ('parent_identity','anchor_record_sha256','journal_head','source_lineage_identity'):
            io.pin(record[field])
        expected=_input_record(self.packet,self.specification,self.limits,
            parent_identity=record['parent_identity'],anchor_pin=record['anchor_record_sha256'],
            head=record['journal_head'],source_identity=record['source_lineage_identity'])
        if io.encode(expected)!=self.receipt:raise ValueError('worker input receipt differs from packet or authority boundary')

    @property
    def receipt_sha256(self):return io.digest(self.receipt)

    def validate(self,*,expected_receipt_sha256):
        if self.receipt_sha256!=io.pin(expected_receipt_sha256):raise ValueError('external worker input receipt pin differs')
        self.__post_init__()


class ReadView:
    """Identity observation only; not a writer lease or a quiescence certificate."""
    def __init__(self,root):
        self.root=chunks.base.local._path(Path(root))
        info=self.root.stat(follow_symlinks=False)
        if not stat.S_ISDIR(info.st_mode):raise ValueError('existing regular directory required')
        self.directory_identity=info.st_dev,info.st_ino
        self.lock_identity=io.identity(self.root/'execution.lock')
        if self.lock_identity[2]!=1:raise ValueError('existing writer lock file required')
        self.closed=False
        self.check()

    def check(self):
        if self.closed:raise ValueError('closed read view')
        path=chunks.base.local._path(self.root)
        info=path.stat(follow_symlinks=False)
        if (not stat.S_ISDIR(info.st_mode) or (info.st_dev,info.st_ino)!=self.directory_identity
                or io.identity(path/'execution.lock')!=self.lock_identity):
            raise ValueError('snapshot directory or lock identity changed')

    def close(self):self.closed=True


class JournalSnapshot(journal.Journal):
    def __init__(self,root,budget,*,binding_identity,expected_head):
        if type(budget) is not chunks.ChunkContentBudget:raise ValueError('exact content budget required')
        budget.__post_init__();journal.storage_bound(budget.max_events)
        if budget.max_event_bytes>2*journal.CONTENT_CAP:raise ValueError('bounded event size required')
        io.pin(binding_identity);io.pin(expected_head)
        self._guard=chunks._Exclusive()
        self._closed=self._poisoned=self._writable=False
        self._budget=budget;self._retained={}
        self._lease=ReadView(root);self.root=self._lease.root
        try:
            self._header=dict(schema=journal.SCHEMA,root=str(self.root),budget=asdict(budget),
                binding=binding_identity,implementation=journal.implementation_identity())
            self.identity=io.digest(io.encode(self._header));self._head=expected_head
            self._scan()
        except BaseException:
            self.close()
            raise

    def append(self,*args,**kwargs):raise ValueError('snapshot is read only')


class AnchorSnapshot(anchor.DevelopmentH1FullAttemptAnchor):
    def __init__(self,root,binding_identity,*,max_records,expected_record_sha256):
        io.pin(binding_identity);io.pin(expected_record_sha256)
        if type(max_records) is not int or not 1<=max_records<=anchor.MAX_RECORDS:
            raise ValueError('bounded anchor records required')
        self._guard=chunks._Exclusive()
        self._closed=self._poisoned=self._writable=False
        self._retained={};self._expected_count=None
        self._lease=ReadView(root)
        self._header=dict(schema=anchor.SCHEMA,root=str(self._lease.root),binding=binding_identity,
            max_records=max_records,implementation=anchor.implementation_identity())
        self.identity=io.digest(chunks.base._bytes(self._header));self._max_records=max_records
        try:
            self._scan(bootstrap=True)
            count=0 if self._latest is None else self._latest.sequence+1
            for name in ['header.json',*[f'{i:03d}.json' for i in range(count)]]:
                path=self._lease.root/name
                identity=anchor.files.local._file_identity(path)
                self._retained[name]=(identity,io.digest(chunks.base._bytes(anchor._read(path,identity))))
            self._expected_count=count
            self._scan()
            if self._latest is None or self._latest.record_sha256!=expected_record_sha256:
                raise ValueError('external snapshot anchor pin differs')
        except BaseException:
            self.close()
            raise

    def advance(self,*args,**kwargs):raise ValueError('snapshot is read only')


class Snapshot(bounded.SavedSourceParent):
    def __init__(self,root,network,specification,limits,*,origin,upstream_root,config_path,
                 dc_bus,hours,expected_anchor_record,expected_parent_identity):
        io.pin(expected_anchor_record);io.pin(expected_parent_identity)
        if type(hours) is not int or not 1<=hours<=192:raise ValueError('bounded exact hours required')
        if type(origin) is not binding.H1SourceDeclaration:raise ValueError('exact origin required')
        origin.__post_init__();source._network(network)
        replay.native.capture.provenance.adapter.validate_spec(specification)
        if type(limits) is not replay.H1HourReplayLimits:raise ValueError('exact replay limits required')
        limits.__post_init__()
        if type(dc_bus) is not int or dc_bus not in {b.uid for b in network.data.buses}:
            raise ValueError('declared static DC bus required')
        self._network,self._spec,self._limits,self._origin=deepcopy((network,specification,limits,origin))
        self._hours,self._dc_bus=hours,dc_bus
        self._upstream_root=Path(upstream_root).resolve(strict=True)
        self._config_path=Path(config_path).resolve(strict=True)
        self._root=Path(root).resolve()
        self._stages=1+len(network.data.generators)+sum(g.dispatch_mode=='committable' for g in network.data.generators)
        if self._stages>limits.max_stages:raise ValueError('complete stage inventory exceeds replay limits')
        self._guard=chunks._Exclusive()
        self._closed=self._poisoned=self._writable=False
        self._journal=self._anchor=self._root_lease=None
        self._declaration=self._declare()
        self.identity=io.digest(chunks.base._bytes(self._declaration))
        if self.identity!=expected_parent_identity:raise ValueError('external parent declaration differs')
        self.snapshot_implementation=implementation_identity()
        self.anchor_pin=expected_anchor_record
        budget=chunks.ChunkContentBudget(2*hours,2*chunks.METADATA_BYTES,4*hours*chunks.METADATA_BYTES)
        try:
            self._root_lease=ReadView(self._root)
            self._anchor=AnchorSnapshot(self._root/'parent_anchor_non_authoritative',self.identity,
                max_records=2*hours+1,expected_record_sha256=expected_anchor_record)
            receipt=self._anchor.inspect()
            self._journal=JournalSnapshot(self._root/'parent_events_non_authoritative',budget,
                binding_identity=self.identity,expected_head=receipt.registry_head)
            self.inspect()
        except BaseException:
            self.close()
            raise

    def _check(self):
        if implementation_identity()!=self.snapshot_implementation:
            raise ValueError('snapshot reader implementation drift')
        super()._check()
        if self._anchor.inspect().record_sha256!=self.anchor_pin:
            raise ValueError('snapshot anchor changed')

    def _append(self,*args,**kwargs):raise ValueError('snapshot is read only')

    def _child(self,*args,**kwargs):
        if kwargs.get('create',False) is not False:raise ValueError('snapshot cannot create child')
        return super()._child(*args,**kwargs)

    def _pending_view(self,state):
        receipt=self._anchor.inspect()
        if (state.status!='pending_unknown' or state.attempted_hours!=state.completed_hours+1
                or receipt.sequence!=2*state.completed_hours+1 or receipt.registry_head!=state.head):
            raise ValueError('exact pending source attempt required')
        names={'execution.lock','parent_events_non_authoritative','parent_anchor_non_authoritative',
               *(f'hour_{i:03d}_non_authoritative' for i in range(state.completed_hours))}
        if bounded.prior.hour_api._names(self._root,len(names))!=names:
            raise ValueError('pending child already exists or parent topology differs')
        view=[]
        for name in sorted(names):
            info=(self._root/name).stat(follow_symlinks=False)
            regular=stat.S_ISREG(info.st_mode) if name=='execution.lock' else stat.S_ISDIR(info.st_mode)
            if not regular:raise ValueError('regular parent snapshot topology required')
            view.append((name,info.st_dev,info.st_ino))
        return tuple(view)

    def pending_input(self,*,expected_head,expected_source_identity,expected_request_key,expected_packet_audit):
        with self._guard,replay.guard.solver_calls_forbidden():
            try:
                for pin in (expected_head,expected_source_identity,expected_request_key,expected_packet_audit):io.pin(pin)
                state,before,previous=self._restore()
                physical=self._journal.inspect()
                if state.status!='pending_unknown' or state.head!=expected_head or physical.events!=2*state.completed_hours+1:
                    raise ValueError('exact current pending parent intent required')
                view=self._pending_view(state)
                receipt=self._load(state.completed_hours,expected_source_identity)
                packet=self._packet(receipt,state.completed_hours,before,previous)
                raw=self._journal.event_metadata(physical.events,expected_head=expected_head)
                if (raw!=chunks.base._bytes(self._intent(state.completed_hours,receipt,packet))
                        or b''.join(self._journal.iter_event(physical.events,expected_head=expected_head))!=receipt.audit_payload
                        or self._journal.event_head(physical.events,expected_head=expected_head)!=expected_head
                        or replay.request_key(packet,self._spec,self._limits)!=expected_request_key
                        or packet.audit_identity!=expected_packet_audit):
                    raise ValueError('worker input differs from pinned pending intent')
                if self._restore()[0]!=state:raise ValueError('parent snapshot changed during packet reconstruction')
                if self._pending_view(state)!=view:raise ValueError('pending parent topology changed')
                result=PendingWorkerInput(packet,self._spec,self._limits,io.encode(_input_record(
                    packet,self._spec,self._limits,parent_identity=self.identity,anchor_pin=self.anchor_pin,
                    head=expected_head,source_identity=expected_source_identity)))
                self._check()
                if self._pending_view(state)!=view:raise ValueError('parent changed before worker input return')
                return result
            except BaseException:
                self._poisoned=True
                raise


def open_snapshot(declaration,*,expected_parent_identity,expected_anchor_record):
    """Rebuild from plain declaration and pinned source, never owned carry JSON."""
    if type(declaration) is not dict:raise ValueError('exact parent declaration required')
    declaration=deepcopy(declaration)
    if io.digest(chunks.base._bytes(declaration))!=io.pin(expected_parent_identity):
        raise ValueError('parent declaration hash differs')
    origin=binding.H1SourceDeclaration(**declaration['origin'])
    receipt=binding.load_pinned_current(origin,declaration['upstream_root'],config_path=declaration['config_path'])
    owner=Snapshot(declaration['root'],receipt.network,Rq2SolverSpec(**declaration['specification']),
        replay.H1HourReplayLimits(**declaration['limits']),origin=origin,
        upstream_root=declaration['upstream_root'],config_path=declaration['config_path'],
        dc_bus=declaration['dc_bus'],hours=declaration['hours'],
        expected_anchor_record=expected_anchor_record,expected_parent_identity=expected_parent_identity)
    if not io.same(owner._declaration,declaration):
        owner.close()
        raise ValueError('snapshot declaration differs from independently rebuilt configuration')
    return owner
