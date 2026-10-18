"""Concrete local holder; synthetic source only, real saved numerical replay."""
from contextlib import contextmanager
from dataclasses import replace
import json
import sqlite3
import pytest

from experiments import h1_prepared_ticket_owner_development_v1 as m
from tests.test_h1_persistent_owner_development_v1 import setup,saved,initial,advance


@pytest.fixture
def holder(setup,tmp_path):
    s=setup;heads=[]
    def retain(genesis,before,after,sequence):heads.append((genesis,before,after,sequence));return after
    with m.TicketHolder(tmp_path/'tickets_non_authoritative',owner_root=s.root,
            max_tickets=s.manifest.max_events,max_ticket_bytes=s.manifest.max_event_bytes,
            create=True,retain_head=retain) as h:
        h.test_retained_heads=heads
        yield h


def owner(s,h,**kw):return m.DevelopmentOwner(s.root,s.manifest,s.binding,holder=h,**kw)


@pytest.mark.parametrize('kind',['intent','outcome'])
@pytest.mark.parametrize('commit',['before','after'])
def test_prepared_ticket_recovery_is_automatic_but_before_never_retries(setup,holder,monkeypatch,kind,commit):
    s=setup;records=saved(monkeypatch,s,initial(s),0);tripped=[]
    with owner(s,holder,create=True) as o:
        check,rows=o._check,o._rows
        def fault_check():
            check();tickets=holder.inspect()
            if commit=='before' and tickets and tickets[-1].kind==kind and not tripped:
                tripped.append(True);raise RuntimeError('injected prepared before commit')
        def fault_rows(db):
            found=rows(db)
            if commit=='after' and found and found[-1][2]==kind and not tripped:
                tripped.append(True);raise RuntimeError('injected committed before return')
            return found
        monkeypatch.setattr(o,'_check',fault_check);monkeypatch.setattr(o,'_rows',fault_rows)
        with pytest.raises(RuntimeError,match='injected'):advance(o,records)
    ticket=holder.inspect()[-1];assert ticket.kind==kind
    # No caller-supplied recovery_ticket: omission cannot hide the holder tail.
    with owner(s,holder,expected_heads=ticket.before_heads) as o:
        report=o.inspect(expected_heads=o.heads)
        assert report.recovery_required==(commit=='before')
        assert not report.continuation_available if commit=='before' else True
        assert o.heads==(ticket.before_heads if commit=='before' else ticket.after_heads)
        if commit=='before':
            with sqlite3.connect(o.path) as db:before=db.execute('SELECT * FROM events').fetchall()
            with pytest.raises(ValueError,match='requires recovery'):advance(o,records)
            with pytest.raises(ValueError,match='requires recovery'):
                o.register_alternate_witness(expected_heads=o.heads,hour=0,terminal_sha256='3'*64,
                    reference_records=records[0],actual_records=records[1])
            with sqlite3.connect(o.path) as db:assert db.execute('SELECT * FROM events').fetchall()==before


def test_regular_pair_reopens_with_external_holder_head(setup,holder,monkeypatch):
    s=setup;records=saved(monkeypatch,s,initial(s),0)
    with owner(s,holder,create=True) as o:
        report=advance(o,records);heads=o.heads
        assert report.completed_hours==1 and not report.recovery_required and report.external_ticket_log_verified
        assert len(holder.inspect())==2 and holder.test_retained_heads[-1][2]==holder.head
    root,head=holder.root,holder.head;holder.close()
    with m.TicketHolder(root,owner_root=s.root,max_tickets=s.manifest.max_events,
            max_ticket_bytes=s.manifest.max_event_bytes,expected_head=head) as reopened:
        with owner(s,reopened,expected_heads=heads) as o:
            assert o.inspect(expected_heads=heads).completed_hours==1


@pytest.mark.parametrize('fault',['partial','handoff','unknown_kind'])
def test_holder_failure_precedes_owner_database_write(setup,holder,monkeypatch,fault):
    s=setup;records=saved(monkeypatch,s,initial(s),0)
    with owner(s,holder,create=True) as o:
        if fault=='handoff':holder.retain_head=lambda *a:'0'*64
        if fault=='partial':
            def partial(path,raw):path.write_bytes(raw[:5]);raise OSError('injected holder partial')
            monkeypatch.setattr(m,'_new',partial)
        with pytest.raises((ValueError,OSError)):
            if fault=='unknown_kind':o._append('bad',{},[])
            else:advance(o,records)
        with sqlite3.connect(o.path) as db:assert db.execute('SELECT count(*) FROM events').fetchone()[0]==0
        if fault!='unknown_kind':assert holder.poisoned


def test_same_before_ticket_never_reprepared(setup,holder,monkeypatch):
    s=setup;records=saved(monkeypatch,s,initial(s),0)
    with owner(s,holder,create=True) as o:advance(o,records)
    ticket=holder.inspect()[0]
    with pytest.raises(ValueError,match='already prepared'):holder.retain(ticket)
    with pytest.raises(ValueError):holder.retain(replace(ticket,body=m.encode({'other':True})))


@pytest.mark.parametrize('fault',['gap','inode','hardlink','extra','head'])
def test_holder_tampering_rejected(setup,holder,monkeypatch,tmp_path,fault):
    s=setup;records=saved(monkeypatch,s,initial(s),0)
    with owner(s,holder,create=True) as o:
        advance(o,records);p=holder.root/'000001.json'
        if fault=='gap':p.rename(tmp_path/'held_ticket')
        elif fault=='inode':raw=p.read_bytes();p.rename(tmp_path/'held_ticket');p.write_bytes(raw)
        elif fault=='hardlink':(tmp_path/'alias').hardlink_to(p)
        elif fault=='extra':(holder.root/'temporary.json').write_bytes(b'{}')
        else:holder.head='0'*64
        with pytest.raises(ValueError):o.inspect(expected_heads=o.heads)


def test_rollback_is_rejected_by_external_holder_head(setup,holder,monkeypatch,tmp_path):
    s=setup;records=saved(monkeypatch,s,initial(s),0)
    with owner(s,holder,create=True) as o:advance(o,records)
    root,head=holder.root,holder.head;holder.close()
    (root/'000002.json').rename(tmp_path/'retained_last_ticket')
    with pytest.raises(ValueError,match='head differs'):
        m.TicketHolder(root,owner_root=s.root,max_tickets=s.manifest.max_events,
            max_ticket_bytes=s.manifest.max_event_bytes,expected_head=head)


def test_owner_without_committed_ticket_rejected(setup,holder,monkeypatch):
    s=setup;records=saved(monkeypatch,s,initial(s),0)
    with owner(s,holder,create=True) as o:
        advance(o,records)
        with sqlite3.connect(o.path) as db:db.execute('DELETE FROM events');db.commit()
        with pytest.raises(ValueError,match='prefix lengths'):o.inspect(expected_heads=o.heads)


def test_wrong_holder_and_bounds_rejected(setup,holder,tmp_path):
    s=setup
    with pytest.raises(ValueError,match='live concrete'):owner(s,object(),create=True)
    with pytest.raises(ValueError,match='another owner'):
        m.DevelopmentOwner(tmp_path/'other_non_authoritative',s.manifest,s.binding,holder=holder,create=True)
    with m.TicketHolder(tmp_path/'small_non_authoritative',owner_root=s.root,max_tickets=1,
            max_ticket_bytes=1,create=True) as small:
        with pytest.raises(ValueError,match='bounds'):owner(s,small,create=True)


@pytest.mark.parametrize('field',['root','owner_root','max_tickets','max_ticket_bytes','cap','header_identity'])
def test_live_holder_configuration_cannot_diverge_from_binding(setup,holder,monkeypatch,tmp_path,field):
    s=setup
    with owner(s,holder,create=True) as o:
        original=getattr(holder,field)
        value=(tmp_path/'changed_non_authoritative' if field in ('root','owner_root')
            else (0,0) if field=='header_identity' else original+1)
        with monkeypatch.context() as patch:
            patch.setattr(holder,field,value)
            with pytest.raises(ValueError,match='identity changed'):o.inspect(expected_heads=o.heads)
        assert o.inspect(expected_heads=o.heads).continuation_available


def test_holder_cannot_continue_across_lease_gap(setup,holder):
    s=setup
    with owner(s,holder,create=True) as o:
        original=holder.lease;original.close()
        replacement=m.local._Lease(holder.root,False)
        try:
            holder.lease=replacement
            with pytest.raises(ValueError,match='lease instance changed'):o.inspect(expected_heads=o.heads)
        finally:
            replacement.close();holder.lease=original


def test_old_holder_repeated_close_preserves_new_holder_registry(setup,holder):
    s=setup;root,head=holder.root,holder.head;holder.close()
    with m.TicketHolder(root,owner_root=s.root,max_tickets=s.manifest.max_events,
            max_ticket_bytes=s.manifest.max_event_bytes,expected_head=head) as reopened:
        assert reopened.lease.key in m.local._REGISTRY
        holder.close()
        assert reopened.lease.key in m.local._REGISTRY
        reopened.lease.check();assert reopened.inspect()==()


def test_cross_thread_close_is_rejected_without_releasing_holder(holder):
    from threading import Thread
    errors=[]
    def close():
        try:holder.close()
        except ValueError as error:errors.append(str(error))
    thread=Thread(target=close);thread.start();thread.join(timeout=5)
    assert not thread.is_alive() and errors==['ticket holder close owner differs']
    assert not holder.closed and holder.lease.key in m.local._REGISTRY
    holder.lease.check();assert holder.inspect()==()
