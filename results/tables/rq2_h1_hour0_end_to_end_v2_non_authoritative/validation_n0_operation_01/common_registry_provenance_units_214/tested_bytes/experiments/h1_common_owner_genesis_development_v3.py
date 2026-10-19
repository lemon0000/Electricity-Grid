"""Durable empty common-owner genesis; no selector or continuation entrypoint."""
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
from threading import Lock, get_ident

from experiments import h1_group_n0_common_input_binding_development_v11 as common

bootstrap,phase=common.bootstrap,common.phase
encode=bootstrap.encode
SCHEMA='h1_common_owner_genesis_development_v3'
HOLDER_BINDING_CAP=4096
FLAGS=dict(common.FLAGS,continuation_ready=False,live_controller_attached=False)


@dataclass(frozen=True)
class HolderGenesisReceipt:
    root: str
    header_sha256: str
    binding_sha256: str
    genesis: str
    head: str

    def __post_init__(self):
        if type(self.root) is not str or str(bootstrap.local._path(self.root))!=self.root:
            raise ValueError('absolute canonical holder receipt root required')
        for pin in (self.header_sha256,self.binding_sha256,self.genesis,self.head):bootstrap.storage._pin(pin)
        if self.head!=self.genesis or self.header_sha256!=self.genesis:
            raise ValueError('empty holder genesis receipt required')


@dataclass(frozen=True)
class OwnerGenesisReceipt:
    root: str
    header_sha256: str
    genesis: str
    heads: tuple

    def __post_init__(self):
        if type(self.root) is not str or str(bootstrap.local._path(self.root))!=self.root:
            raise ValueError('absolute canonical owner receipt root required')
        bootstrap.storage._pin(self.header_sha256);bootstrap.storage._pin(self.genesis)
        if type(self.heads) is not tuple or self.heads!=(self.genesis,self.genesis):
            raise ValueError('empty owner genesis heads required')


def _receipt_identity(value):return sha256(encode(asdict(value))).hexdigest()


def implementation_identity():
    return bootstrap.digest([SCHEMA,sha256(Path(__file__).read_bytes()).hexdigest(),
                             common.implementation_identity()])


def _stable(report):
    value=dict(report);value.pop('global_head')
    return encode(value)


class _BinderJournal(bootstrap._Journal):
    def __init__(self,wrapper,*args,**kw):
        self._wrapper=self._original_wrapper=wrapper
        super().__init__(*args,**kw)

    def check(self):
        super().check()
        if self._wrapper is not self._original_wrapper:raise ValueError('binder wrapper changed')
        wrapper=self._wrapper
        wrapper._check_live()
        if (self._declaration!=wrapper._declaration
                or encode(json.loads(self._header)['declaration'])!=wrapper._declaration
                or self.genesis!=wrapper._binder_genesis
                or (self.root,self.max_events,self.cap)!=(wrapper.root,3,wrapper.max_record_bytes)
                or self._retain is not wrapper._binder_retainer
                or self._original_retain is not wrapper._binder_retainer):
            raise ValueError('binder journal detached from wrapper declaration')


class CommonOwnerGenesis:
    """Create or inspect fixed genesis; explicit reconcile writes metadata only."""
    def __init__(self,roster,*,create,retain_binder_head,retain_holder_receipt,
                 retain_owner_receipt,max_record_bytes,expected_head=None,
                 holder_receipt=None,owner_receipt=None,reconcile=False):
        if type(roster) is not common.roster_api.GroupRoster:
            raise ValueError('exact live group roster required')
        if (type(create) is not bool or type(reconcile) is not bool or create and reconcile
                or type(max_record_bytes) is not int or not 1024<=max_record_bytes<=1024**2
                or not all(callable(x) for x in (retain_binder_head,retain_holder_receipt,retain_owner_receipt))):
            raise ValueError('exact binder declaration and retention callbacks required')
        if create and any(x is not None for x in (expected_head,holder_receipt,owner_receipt)):
            raise ValueError('create cannot adopt retained genesis metadata')
        if not create:bootstrap.storage._pin(expected_head)
        for receipt,kind in ((holder_receipt,HolderGenesisReceipt),(owner_receipt,OwnerGenesisReceipt)):
            if receipt is not None:
                if type(receipt) is not kind:raise ValueError('exact typed external genesis receipt required')
                receipt.__post_init__()
        if owner_receipt is not None and holder_receipt is None:
            raise ValueError('owner receipt requires independently retained holder receipt')
        self._self=self;self._roster=self._original_roster=roster
        self._pid,self._thread=os.getpid(),get_ident()
        self._operation=self._original_operation=Lock()
        self.closed=self.poisoned=False
        self._journal=self._original_journal=None
        self._holder=self._original_holder=None;self._phase=self._original_phase=None
        self._retainers=(retain_binder_head,retain_holder_receipt,retain_owner_receipt)
        self._original_retainers=self._retainers
        self._ticket_retainer=self._deny_ticket
        self._binder_retainer=self._original_binder_retainer=self._retain_binder
        self.max_record_bytes=max_record_bytes
        self._enter()
        try:
            self._implementation=implementation_identity()
            manifest,binding,report=common._prepare_locked(roster)
            self._manifest,self._binding=manifest,binding
            self._manifest_bytes=encode(asdict(manifest));self._binding_bytes=encode(asdict(binding))
            self._phase_implementation=phase.implementation_identity(manifest)
            if manifest.max_events>999999:raise ValueError('holder event bound exceeds namespace')
            group=report['phase_manifest_candidate']['audit']['group']
            self.root=bootstrap.local._path(roster._owner.study_root/'common_owners_non_authoritative'/
                                          (group['group_identity']+'_non_authoritative'))
            episode=Path(report['arm_audits'][report['canonical_arm']]['reference']['episode_root'])
            self.holder_root=bootstrap.local._path(episode/'holder_non_authoritative')
            self.owner_root=bootstrap.local._path(episode/'owner_non_authoritative')
            if create:
                if self.holder_root.exists() or self.owner_root.exists():
                    raise ValueError('new genesis requires absent fixed child roots')
                initial=report
            else:
                raw,_=bootstrap.storage._read(self.root/'header.json',max_record_bytes)
                initial=json.loads(raw)['declaration']['initial_report']
                if _stable(initial)!=_stable(report):raise ValueError('retained common correspondence changed')
            self._initial_report=encode(initial)
            self._stable_report=_stable(initial)
            declaration=dict(schema=SCHEMA,initial_report=initial,manifest=asdict(manifest),source_binding=asdict(binding),
                holder_root=str(self.holder_root),owner_root=str(self.owner_root),implementation=self._implementation,
                phase_implementation=self._phase_implementation,max_record_bytes=max_record_bytes,
                holder_binding_cap=HOLDER_BINDING_CAP,max_events=3,**FLAGS)
            self._declaration=encode(declaration)
            header=bootstrap._journal_header(self.root,declaration,3,max_record_bytes,bootstrap.implementation_identity())
            self._binder_genesis=sha256(header).hexdigest()
            self._configuration=(self.root,self.holder_root,self.owner_root,max_record_bytes,self._declaration,
                                 self._initial_report,self._stable_report,self._manifest_bytes,self._binding_bytes)
            self._preflight(header)
            self._correspondence()
            if create:
                self.root.parent.mkdir(exist_ok=True)
                bootstrap.local._path(self.root)
            self._journal=_BinderJournal(self,self.root,declaration,max_events=3,max_record_bytes=max_record_bytes,
                create=create,expected_head=expected_head,retain_head=self._binder_retainer)
            self._original_journal=self._journal
            if create:self._initialize()
            else:
                rows=self._journal.rows()
                if not rows and (holder_receipt is not None or owner_receipt is not None
                                 or self.holder_root.exists() or self.owner_root.exists()):
                    raise ValueError('child genesis has no retained initialization intent')
                if len(rows)>=2 and holder_receipt is None:raise ValueError('external holder receipt required')
                if len(rows)>=3 and owner_receipt is None:raise ValueError('external owner receipt required')
                if holder_receipt is not None:self._open_holder(holder_receipt)
                if owner_receipt is not None:self._open_owner(owner_receipt)
                self._replay()
                if reconcile:self._reconcile()
            self._replay();self._correspondence()
        except BaseException:
            self.poisoned=True
            self._close_handles();self.closed=True
            raise
        finally:self._leave()

    def _enter(self):
        if (self._self is not self or self.closed or self.poisoned
                or (os.getpid(),get_ident())!=(self._pid,self._thread)
                or self._operation is not self._original_operation or self._roster is not self._original_roster):
            raise ValueError('common genesis live owner changed')
        if not self._original_operation.acquire(False):raise ValueError('common genesis operation active')
        try:self._original_roster._enter()
        except BaseException:self._original_operation.release();raise

    def _leave(self):
        try:self._original_roster._leave()
        finally:self._original_operation.release()

    def _check_live(self):
        self._roster._check()
        if (self._self is not self or self.closed or self.poisoned
                or (os.getpid(),get_ident())!=(self._pid,self._thread)
                or self._roster is not self._original_roster or self._operation is not self._original_operation
                or not self._original_operation.locked() or self._retainers is not self._original_retainers
                or self._binder_retainer is not self._original_binder_retainer
                or self._journal is not self._original_journal or self._holder is not self._original_holder
                or self._phase is not self._original_phase or implementation_identity()!=self._implementation
                or phase.implementation_identity(self._manifest)!=self._phase_implementation
                or encode(asdict(self._manifest))!=self._manifest_bytes or encode(asdict(self._binding))!=self._binding_bytes
                or (self.root,self.holder_root,self.owner_root,self.max_record_bytes,self._declaration,
                    self._initial_report,self._stable_report,self._manifest_bytes,self._binding_bytes)!=self._configuration):
            raise ValueError('common genesis live configuration changed')

    def _correspondence(self):
        self._check_live()
        manifest,binding,report=common._prepare_locked(self._roster)
        global_=self._roster._owner._global
        initial=json.loads(self._initial_report)['global_head']
        if (encode(asdict(manifest))!=self._manifest_bytes or encode(asdict(binding))!=self._binding_bytes
                or _stable(report)!=self._stable_report or report['global_head']!=global_.head
                or initial not in {global_.genesis,*(h for h,body in global_.rows())}):
            raise ValueError('common correspondence or global ancestor changed')
        self._check_live()
        return report['global_head']

    def _intent(self):return dict(kind='initialize_intent',binder_genesis=self._binder_genesis,**FLAGS)

    def _holder_event(self,receipt,binding):
        return dict(kind='holder_bound',receipt=asdict(receipt),receipt_identity=_receipt_identity(receipt),
                    holder_binding=binding,**FLAGS)

    def _owner_event(self,holder,owner):
        return dict(kind='initialized_terminal',holder_receipt_identity=_receipt_identity(holder),
                    receipt=asdict(owner),receipt_identity=_receipt_identity(owner),**FLAGS)

    def _preflight(self,header):
        h=HolderGenesisReceipt(str(self.holder_root),*(['0'*64]*4))
        o=OwnerGenesisReceipt(str(self.owner_root),'0'*64,'0'*64,('0'*64,'0'*64))
        bodies=(self._intent(),self._holder_event(h,'x'*HOLDER_BINDING_CAP),self._owner_event(h,o))
        if len(header)>self.max_record_bytes or any(len(encode(dict(sequence=i,previous='0'*64,body=b)))>
                self.max_record_bytes for i,b in enumerate(bodies,1)):
            raise ValueError('complete genesis journal branch exceeds byte cap')

    def _holder_receipt(self):
        holder=self._holder
        if holder is None:raise ValueError('retained holder genesis unavailable')
        if (holder is not self._original_holder or holder.retain_head is not self._ticket_retainer
                or holder.root!=self.holder_root or holder.owner_root!=self.owner_root
                or holder.inspect()!=() or holder.head!=holder.genesis):
            raise ValueError('exact empty holder genesis required')
        raw=encode(holder.binding)
        if len(raw)>HOLDER_BINDING_CAP:raise ValueError('holder binding exceeds logical byte bound')
        return HolderGenesisReceipt(str(holder.root),sha256(holder.header).hexdigest(),
                                    sha256(raw).hexdigest(),holder.genesis,holder.head)

    def _owner_receipt(self):
        owner=self._phase
        if owner is None:raise ValueError('retained owner genesis unavailable')
        self._holder_receipt()
        if owner is not self._original_phase or owner.root!=self.owner_root:
            raise ValueError('exact common owner required')
        heads=(owner.genesis,owner.genesis)
        view=owner.inspect(expected_heads=heads)
        if (owner.heads!=heads or view.completed_hours!=0 or view.pending_intent or view.pending_attempt
                or view.recovery_required or view.conflicted_keys
                or encode(asdict(owner.manifest))!=self._manifest_bytes
                or encode(asdict(owner.binding))!=self._binding_bytes or owner.holder is not self._holder):
            raise ValueError('exact empty common owner genesis required')
        return OwnerGenesisReceipt(str(owner.root),sha256(owner.header).hexdigest(),owner.genesis,heads)

    def _holder_open(self,create,head=None):
        m=self._manifest
        self._holder=phase.tickets.TicketHolder(self.holder_root,owner_root=self.owner_root,
            max_tickets=m.max_events,max_ticket_bytes=m.max_event_bytes,max_total_ticket_bytes=m.max_archive_bytes,
            create=create,expected_head=head,retain_head=self._ticket_retainer)
        self._original_holder=self._holder

    def _open_holder(self,receipt):
        if receipt.root!=str(self.holder_root):raise ValueError('holder receipt root differs')
        self._holder_open(False,receipt.head)
        if self._holder_receipt()!=receipt:raise ValueError('external holder receipt differs')

    def _owner_open(self,create,heads=None):
        self._phase=phase.DevelopmentOwner(self.owner_root,self._manifest,self._binding,
                                         holder=self._holder,create=create,expected_heads=heads)
        self._original_phase=self._phase

    def _open_owner(self,receipt):
        if receipt.root!=str(self.owner_root):raise ValueError('owner receipt root differs')
        self._owner_open(False,receipt.heads)
        if self._owner_receipt()!=receipt:raise ValueError('external owner receipt differs')

    def _retain_child(self,receipt,index,fresh):
        before=encode(asdict(receipt));global_head=self._correspondence()
        returned=self._retainers[index](receipt)
        if (type(returned) is not type(receipt) or encode(asdict(returned))!=before
                or encode(asdict(receipt))!=before or encode(asdict(fresh()))!=before
                or self._correspondence()!=global_head):
            raise ValueError('external child receipt retention changed')

    def _retain_binder(self,root,before,after):
        global_head=self._correspondence()
        if self._holder is not None:self._holder_receipt()
        if self._phase is not None:self._owner_receipt()
        value=self._retainers[0](root,before,after)
        if self._holder is not None:self._holder_receipt()
        if self._phase is not None:self._owner_receipt()
        if self._correspondence()!=global_head:raise ValueError('global head changed during retention')
        return value

    def _replay(self):
        self._check_live();rows=self._journal.rows()
        expected=[self._intent()]
        if len(rows)>=2:expected.append(self._holder_event(self._holder_receipt(),self._holder.binding))
        if len(rows)>=3:expected.append(self._owner_event(self._holder_receipt(),self._owner_receipt()))
        if len(rows)>3 or any(encode(body)!=encode(want) for (_,body),want in zip(rows,expected)):
            raise ValueError('common genesis journal state differs')
        return len(rows)

    def _initialize(self):
        if self._replay()!=0 or self.holder_root.exists() or self.owner_root.exists():
            raise ValueError('fresh absent child roots required; no automatic retry')
        self._journal.reserve(3)
        self._journal.append(self._intent(),expected_head=self._journal.head)
        self._correspondence();self._holder_open(True)
        h=self._holder_receipt();self._retain_child(h,1,self._holder_receipt)
        self._journal.append(self._holder_event(h,self._holder.binding),expected_head=self._journal.head)
        self._correspondence();self._owner_open(True)
        o=self._owner_receipt();self._retain_child(o,2,self._owner_receipt)
        self._journal.append(self._owner_event(h,o),expected_head=self._journal.head)

    def _reconcile(self):
        stage=self._replay()
        if stage not in (1,2):raise ValueError('pending genesis metadata required')
        self._correspondence()
        if stage==1:
            h=self._holder_receipt()
            self._journal.append(self._holder_event(h,self._holder.binding),expected_head=self._journal.head)
        if self._phase is not None:
            self._journal.append(self._owner_event(self._holder_receipt(),self._owner_receipt()),expected_head=self._journal.head)
        self._correspondence()

    def inspect(self):
        self._enter()
        try:
            before=self._correspondence();stage=self._replay()
            if self._holder is not None:self._holder_receipt()
            if self._phase is not None:self._owner_receipt()
            if self._correspondence()!=before or self._replay()!=stage:
                raise ValueError('common genesis changed during inspection')
            return dict(schema=SCHEMA,root=str(self.root),head=self._journal.head,stage=stage,
                state=('new','initialize_pending','holder_bound','initialized_genesis')[stage],
                persistent_empty_genesis_bound=stage==3,global_head=before,
                fresh_at_return_only=True,**FLAGS)
        except BaseException:self.poisoned=True;raise
        finally:self._leave()

    def _deny_ticket(self,*args):raise ValueError('genesis wrapper has no phase mutation capability')

    def _close_handles(self):
        try:
            if self._original_phase is not None:self._original_phase.close()
        finally:
            try:
                if self._original_holder is not None:self._original_holder.close()
            finally:
                if self._original_journal is not None:self._original_journal.close()

    def close(self):
        if (os.getpid(),get_ident())!=(self._pid,self._thread):raise ValueError('common genesis close owner differs')
        if self.closed:return
        if not self._original_operation.acquire(False):raise ValueError('common genesis operation active')
        try:self._close_handles();self.closed=True
        finally:self._original_operation.release()

    def __enter__(self):return self
    def __exit__(self,*args):self.close()
    def _no_copy(self,*args):raise TypeError('live common genesis wrapper cannot be copied')
    __copy__=__deepcopy__=__reduce_ex__=_no_copy
