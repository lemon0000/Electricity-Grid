"""Persistence faults under an explicitly synthetic Parent/sequence identity.

The other handoff suite covers actual Parent alias/archive integration. This
suite has no live-Parent or Job evidence: only storage/state-machine ordering.
Scientific phase replay and the fabricated selector records remain real code.
"""
from dataclasses import asdict,dataclass
import json
from pathlib import Path
from threading import Lock
from types import ModuleType,SimpleNamespace

import pytest

from experiments import h1_selector_phase_handoff_development_v1 as canonical
from tests.test_h1_selector_parent_controller_development_v1 import context,case,setup,legacy_setup,no_solver,load
from tests.test_h1_persistent_owner_development_v1 import saved

pytestmark=pytest.mark.parametrize('context',['business_unresolved'],indirect=True)


@pytest.fixture
def fault_case(context,monkeypatch,tmp_path):
    c=context;real=canonical.parent;phase=canonical.phase
    current=c.s.currents[0]
    records,_=saved(monkeypatch,c.s,phase._initial(c.s.manifest,current),0,actual=False)
    raw=real.worker.snapshot.capture_reference(c.owner,c.config,max_archive_bytes=c.cap)
    @dataclass(frozen=True)
    class Completion:
        root: str
        role: str
        terminal_sha256: str
        scientific_root: str
        scientific_terminal_sha256: str
        scientific_request_sha256: str
        sequence_request_sha256: str
        max_archive_bytes: int
    class Parent:
        def __init__(self):
            self._guard=Lock();self._reference_owner=None;self._reference_completion=None;self._reference_held=False
            self.root=tmp_path/'synthetic_parent_non_authoritative'
            self.worker_root=self.root/'worker_non_authoritative';self._raw=raw
            self._issued=Completion(str(self.root),'reference','1'*64,
                str(self.worker_root/'science_sequence_non_authoritative'),'2'*64,'3'*64,'4'*64,c.cap)
            self._outcome=real.io.encode(dict(inspection=dict(data=dict(sequence_terminal_sha256='5'*64,
                record_sha256=[real.io.digest(r) for r in records],archive_view_sha256='6'*64))))
            self._declaration=real.io.encode(dict(request=dict(max_timing_archive_bytes=2**28)))
            self.closed=False
        def _enter(self):
            if self.closed or not self._guard.acquire(False):raise ValueError('synthetic parent unavailable')
        def _validate(self,receipt):
            if type(self) is not Parent or self.closed or not self._guard.locked() or receipt is not self._issued:
                raise ValueError('synthetic exact held parent required')
        def close(self):
            if not self._guard.acquire(False):raise ValueError('synthetic parent active')
            self.closed=True;self._guard.release()
    sequence=ModuleType('explicit_synthetic_handoff_sequence')
    sequence.inspect=lambda *a,**kw:dict(records=records,request_sha256='4'*64,scientific_terminal_sha256='2'*64,
        science=dict(request_sha256='3'*64))
    sequence._snapshot=lambda *a,**kw:('synthetic_archive_view',)
    sequence._snapshot_pin=lambda *a:'6'*64
    proxy=ModuleType('explicit_synthetic_handoff_parent')
    proxy.Parent=Parent;proxy.ParentCompletion=Completion;proxy.io=real.io;proxy.FLAGS=real.FLAGS
    proxy.worker=SimpleNamespace(snapshot=real.worker.snapshot,sequence=sequence,_read=real.worker._read)
    proxy._CHECK=lambda:None
    proxy.implementation_identity=lambda:real.io.digest(b'explicit_synthetic_handoff_parent_no_execution_evidence')
    proxy._completion_bytes=lambda receipt:real.io.encode(asdict(receipt))
    # Install explicit fault seams before the handoff captures implementation
    # identity. Their mutable selector is test input, not execution evidence.
    faults={}
    original_write=real.io.write_new
    def failing_write(path,raw):
        match=path.name==faults.get('file')
        if match and faults.get('point')=='write_before':raise RuntimeError('injected write before')
        result=original_write(path,b'{}' if match and faults.get('point')=='write_corrupt' else raw)
        if match and faults.get('point')=='write_after':raise RuntimeError('injected write after')
        return result
    monkeypatch.setattr(real.io,'write_new',failing_write)
    original_close=canonical.common.CommonOwnerGenesis._close_handles
    def failing_close(owner):
        if faults.get('point')=='close_before':raise RuntimeError('injected close before')
        result=original_close(owner)
        if faults.get('replace_phase'):
            if faults['replace_phase']=='directory':
                import shutil
                # Both paths are confined to this pytest case; preserve the old
                # directory as evidence, then place a new same-content directory.
                owner.owner_root.resolve().relative_to(tmp_path.resolve())
                old_root=tmp_path/'old_phase_directory';owner.owner_root.rename(old_root)
                shutil.copytree(old_root,owner.owner_root)
            else:
                target=owner.owner_root/('owner.sqlite' if faults['replace_phase']=='db' else 'execution.lock')
                replacement=tmp_path/'replacement.tmp';replacement.write_bytes(target.read_bytes());replacement.replace(target)
        if faults.get('point')=='close_after':raise RuntimeError('injected close after')
        return result
    monkeypatch.setattr(canonical.common.CommonOwnerGenesis,'_close_handles',failing_close)
    for cls,kind,old_child in ((phase.DevelopmentOwner,'phase',c.owner._original_phase),
                     (phase.tickets.TicketHolder,'holder',c.owner._original_holder),
                     (canonical.bootstrap._Journal,'journal',c.owner._original_journal)):
        original_child_close=cls.close
        def child_close(owner,_close=original_child_close,_kind=kind,_old=old_child):
            target=owner is _old and faults.get('close_child')==_kind
            if target and faults.get('point')=='child_before':raise RuntimeError('injected child close before')
            result=_close(owner)
            if target and faults.get('point')=='child_after':raise RuntimeError('injected child close after')
            return result
        monkeypatch.setattr(cls,'close',child_close)
    for cls,kind in ((phase.tickets.TicketHolder,'holder'),(phase.DevelopmentOwner,'phase')):
        original_init=cls.__init__
        def init(owner,*args,_init=original_init,_kind=kind,**kw):
            target=not kw.get('create',True) and faults.get('reopen')==_kind
            if target and faults.get('point')=='open_before':raise RuntimeError('injected reopen before')
            _init(owner,*args,**kw)
            # Return the created handle so the caller owns cleanup, then force
            # the immediate retained-header comparison to reject it.
            if target and faults.get('point')=='open_readback':owner.header=b'changed header'
        monkeypatch.setattr(cls,'__init__',init)
    original_new=phase.tickets._new
    def failing_new(path,raw):
        match=path.name==f"{faults.get('number',0):06d}.json"
        if match and faults.get('point')=='holder_before':raise RuntimeError('injected holder before')
        result=original_new(path,raw)
        if match and faults.get('point')=='holder_after':raise RuntimeError('injected holder after')
        return result
    monkeypatch.setattr(phase.tickets,'_new',failing_new)
    original_connect=phase._SavedOwner._connect
    class Connection:
        def __init__(self,db):self.db=db
        def __getattr__(self,name):return getattr(self.db,name)
        def commit(self):
            count=self.db.execute('SELECT count(*) FROM events').fetchone()[0]
            match=self.db.in_transaction and count==faults.get('number')
            if match and faults.get('point')=='db_before':raise RuntimeError('injected db before')
            result=self.db.commit()
            if match and faults.get('point')=='db_after':raise RuntimeError('injected db after')
            return result
    def connect(owner):return Connection(original_connect(owner))
    monkeypatch.setattr(phase._SavedOwner,'_connect',connect)
    module=load(canonical.__file__,'selector_phase_handoff_fault_test_alias',monkeypatch,
        dict(h1_selector_parent_controller_development_v1=proxy))
    ref=Parent();retained=[]
    def retain(root,before,after):retained.append((root,before,after));return after
    options=dict(retain_head=retain,max_packet_bytes=64*1024**2,max_record_bytes=1024**2,max_archive_bytes=128*1024**2)
    f=SimpleNamespace(c=c,m=module,ref=ref,receipt=ref._issued,retained=retained,options=options,records=records,faults=faults)
    try:yield f
    finally:ref.close()


def make(f,**options):
    return f.m.Handoff(f.c.owner,(f.ref,f.receipt),{'joint':None},**(f.options|options))


def rows(path):
    import sqlite3
    with sqlite3.connect(path.as_uri()+'?mode=ro',uri=True) as db:
        return db.execute('SELECT kind FROM events ORDER BY seq').fetchall()


@pytest.mark.parametrize('number',[1,2])
@pytest.mark.parametrize('point',['holder_before','holder_after','db_before','db_after'])
def test_durable_write_windows_keep_exact_prefix_and_release_leases(fault_case,number,point):
    f=fault_case;f.faults.update(number=number,point=point)
    with make(f) as owner:
        with pytest.raises(RuntimeError,match='injected'):owner.consume()
        assert owner._state=='failed' and f.c.owner.closed
        committed=number if point=='db_after' else number-1
        assert rows(f.c.owner.owner_root/'owner.sqlite')==[('intent',),('outcome',)][:committed]
        files=sorted(f.c.owner.holder_root.glob('[0-9]*.json'))
        assert len(files)==(number-1 if point=='holder_before' else number)
        assert len(f.retained)==number+2
        assert not f.ref._guard.locked() and not f.c.case.guard.locked()
        for lease in (owner._lease,owner._journal._original_lease,
                      owner._holder._lease_object,owner._phase._lease_object):
            assert lease.stream is None
        retained={p:p.read_bytes() for root in (owner.root,f.c.owner.holder_root,f.c.owner.owner_root)
                  for p in root.rglob('*') if p.is_file()}
        with pytest.raises(ValueError):owner.consume()
        assert all(p.read_bytes()==raw for p,raw in retained.items())


@pytest.mark.parametrize('filename',['takeover_packet.json','binding.json'])
@pytest.mark.parametrize('point',['write_before','write_after'])
def test_outer_file_failure_preserves_live_predecessor(fault_case,filename,point):
    f=fault_case;f.faults.update(file=filename,point=point)
    before=f.c.owner.inspect()
    with make(f) as owner:
        with pytest.raises(RuntimeError,match='injected write'):owner.consume()
        assert not f.retained and not f.c.owner.closed
        assert (owner.root/filename).exists() is (point=='write_after')
        assert owner._lease.stream is None
    assert f.c.owner.inspect()==before


@pytest.mark.parametrize('point',['close_before','close_after'])
def test_predecessor_close_failure_releases_original_leases(fault_case,point):
    f=fault_case;f.faults['point']=point
    old=f.c.owner
    leases=(old._original_phase._lease_object,old._original_holder._lease_object,old._original_journal._original_lease)
    with make(f) as owner:
        with pytest.raises(RuntimeError,match='injected close'):owner.consume()
        assert old.closed and old.poisoned and len(f.retained)==1
        assert all(lease.stream is None for lease in leases)
        assert owner._lease.stream is None and owner._journal._original_lease.stream is None
        assert rows(old.owner_root/'owner.sqlite')==[]
        assert not f.ref._guard.locked() and not f.c.case.guard.locked()


@pytest.mark.parametrize('kind',['holder','phase'])
@pytest.mark.parametrize('point',['open_before','open_readback'])
def test_reopen_failure_keeps_empty_prefix_and_releases_owned_handles(fault_case,kind,point):
    f=fault_case;f.faults.update(reopen=kind,point=point)
    with make(f) as owner:
        with pytest.raises((RuntimeError,ValueError)):owner.consume()
        assert f.c.owner.closed and len(f.retained)==1
        assert rows(f.c.owner.owner_root/'owner.sqlite')==[]
        assert list(f.c.owner.holder_root.glob('[0-9]*.json'))==[]
        for child in (owner._holder,owner._phase):
            if child is not None:assert child._lease_object.stream is None
        assert owner._lease.stream is None and owner._journal._original_lease.stream is None
        assert not f.ref._guard.locked() and not f.c.case.guard.locked()


def test_business_unresolved_handoff_closes_both_carries_without_episode_terminal(fault_case):
    f=fault_case
    with make(f) as owner:
        result=owner.consume()
        projection=json.loads(owner._plan.projection)
        assert projection['lanes'][0]['status'] in ('business_input_unresolved','business_unresolved')
        assert projection['lanes'][0]['before_business']==projection['lanes'][0]['after_business']
        assert projection['lanes'][0]['before_actual']==projection['lanes'][0]['after_actual']
        assert result['phase_episode_terminal'] is False and result['full_192_hour_execution_verified'] is False
        assert rows(owner._phase.path)==[('intent',),('outcome',)]


@pytest.mark.parametrize('stage',[1,2,3,4,5])
def test_external_retention_failure_never_retries_or_fills_missing_bytes(fault_case,stage):
    f=fault_case;calls=[]
    def fail(root,before,after):
        calls.append(after)
        if len(calls)==stage:raise RuntimeError('injected external retention failure')
        return after
    with make(f,retain_head=fail) as owner:
        with pytest.raises(RuntimeError,match='injected external'):owner.consume()
        assert owner._state=='failed' and len(calls)==stage
        assert f.c.owner.closed is (stage>=2)
        expected_rows=[] if stage<=3 else [('intent',)] if stage==4 else [('intent',),('outcome',)]
        assert rows(f.c.owner.owner_root/'owner.sqlite')==expected_rows
        holder_files=sorted(f.c.owner.holder_root.glob('[0-9]*.json'))
        assert len(holder_files)==(0 if stage<=3 else 1 if stage==4 else 2)
        assert not f.ref._guard.locked() and not f.c.case.guard.locked()
        saved_bytes={p:p.read_bytes() for p in owner.root.rglob('*') if p.is_file()}
        with pytest.raises(ValueError):owner.consume()
        assert all(p.read_bytes()==raw for p,raw in saved_bytes.items())
        assert (owner.root/'execution.lock').read_bytes()==b'0'


@pytest.mark.parametrize('bound',['packet','archive','record'])
def test_preclose_capacity_rejection_preserves_common_genesis(fault_case,bound):
    f=fault_case;change={'packet':dict(max_packet_bytes=1),'archive':dict(max_archive_bytes=1),
        'record':dict(max_record_bytes=1024)}[bound]
    before=f.c.owner.inspect()
    with make(f,**change) as owner:
        with pytest.raises(ValueError,match='complete handoff archive branch'):owner.consume()
        assert not owner.root.exists() and not f.retained
    assert f.c.owner.inspect()==before


@pytest.mark.parametrize('attack',['future_event','packet','namespace','helper','checker','phase_handle','root_lease'])
def test_callback_mutations_fail_closed_and_release_original_handles(fault_case,monkeypatch,attack):
    f=fault_case;called=[];original=[]
    def retained(root,before,after):
        called.append(after)
        if len(called)==1:
            original.extend((owner._lease,owner._journal))
            if attack=='future_event':owner._events=(owner._events[0],dict(owner._events[1],kind='forged_future'),*owner._events[2:])
            elif attack=='packet':
                path=owner.root/'takeover_packet.json';raw=path.read_bytes()
                replacement=owner.root/'same_bytes.tmp';replacement.write_bytes(raw);replacement.replace(path)
            elif attack=='namespace':
                (owner.root/'unknown.json').write_bytes(b'{}');owner._names.add('unknown.json')
            elif attack=='helper':monkeypatch.setattr(f.m.preview,'_planned_bootstrap',lambda *a,**k:owner._plan)
            elif attack=='checker':
                monkeypatch.setattr(f.m,'_CHECK',lambda:None)
                monkeypatch.setattr(f.m.Handoff,'_correspondence',lambda self:None)
                monkeypatch.setattr(f.m._Bundle,'validate',lambda self:None)
            elif attack=='phase_handle':owner._phase=SimpleNamespace(close=lambda:pytest.fail('foreign handle closed'))
            elif attack=='root_lease':owner._lease=SimpleNamespace(close=lambda:pytest.fail('foreign lease closed'))
        return after
    with make(f,retain_head=retained) as owner:
        with pytest.raises(ValueError):owner.consume()
        assert len(called)==1 and not f.c.owner.closed
        assert not f.ref._guard.locked() and not f.c.case.guard.locked()
        assert (owner.root/'execution.lock').read_bytes()==b'0'
        assert (owner.root/'journal_non_authoritative'/'execution.lock').read_bytes()==b'0'
