"""Phase FSM draft: synthetic source seam, actual business/selector replay."""
from dataclasses import replace
import pytest
from experiments import h1_phase_owner_development_v1 as m
from tests.test_h1_persistent_owner_development_v1 import setup as legacy_setup,saved


@pytest.fixture
def setup(legacy_setup,monkeypatch):
    # Explicit synthetic seam for the new adapter; numerical replay is real.
    # The phase source suite separately checks its actual historical reader.
    monkeypatch.setattr(m.source,'prepare',m.legacy.source.prepare)
    monkeypatch.setattr(m.source,'implementation_identity',lambda:'a'*64)
    return legacy_setup


@pytest.fixture
def holder(setup,tmp_path):
    s=setup
    with m.tickets.TicketHolder(tmp_path/'phase_tickets_non_authoritative',owner_root=s.root,
            max_tickets=s.manifest.max_events,max_ticket_bytes=s.manifest.max_event_bytes,
            max_total_ticket_bytes=s.manifest.max_archive_bytes,create=True,retain_head=lambda *a:a[2]) as h:
        yield h


def owner(s,h,**kw):return m.DevelopmentOwner(s.root,s.manifest,s.binding,holder=h,**kw)


def bootstrap(s,h,monkeypatch,*,actual=True):
    o=owner(s,h,create=True)
    records=saved(monkeypatch,s,m._initial(s.manifest,s.currents[0]),0,actual=actual)
    o.advance(expected_heads=o.heads,terminal_sha256=s.binding.genesis_terminal_sha256,
        reference_records=records[0],actual_records=records[1])
    return o


def test_attempt_precedes_next_source_and_saved_pair_commits(setup,holder,monkeypatch):
    s=setup;calls=[];fresh=m._fresh
    def observed(binding,hour,terminal):calls.append(hour);return fresh(binding,hour,terminal)
    monkeypatch.setattr(m,'_fresh',observed)
    with bootstrap(s,holder,monkeypatch) as o:
        before=o.heads;calls.clear()
        report=o.prepare_next(expected_heads=before)
        assert report.pending_attempt and not report.continuation_available and not report.live_controller_attached
        assert set(calls)=={0} and o.heads[0]==before[0] and o.heads[1]!=before[1]
        with m.closing(o._connect()) as db:rows=o._rows(db)
        _,state,_=o._restore(rows);records=saved(monkeypatch,s,state,1)
        report=o.complete_saved(expected_heads=o.heads,terminal_sha256='3'*64,
            reference_records=records[0],actual_records=records[1])
        assert report.completed_hours==2 and not report.pending_attempt and report.continuation_available
        assert [t.kind for t in holder.inspect()]==['intent','outcome','attempt','intent','outcome']
        heads=o.heads
    with owner(s,holder,expected_heads=heads) as o:assert o.inspect(expected_heads=heads).completed_hours==2


def test_source_failure_retains_attempt_and_reopen_blocks_retry(setup,holder,monkeypatch):
    s=setup;fresh=m._fresh
    with bootstrap(s,holder,monkeypatch) as o:
        o.prepare_next(expected_heads=o.heads);heads=o.heads
        def failure(binding,hour,terminal):
            if hour==1:raise ValueError('injected missing needed source')
            return fresh(binding,hour,terminal)
        monkeypatch.setattr(m,'_fresh',failure)
        with pytest.raises(ValueError,match='injected'):
            o.complete_saved(expected_heads=heads,terminal_sha256='3'*64,reference_records=(),actual_records={'joint':()})
        assert o.poisoned and o.heads==heads
    with owner(s,holder,expected_heads=heads) as o:
        assert o.inspect(expected_heads=heads).pending_attempt
        with pytest.raises(ValueError,match='no automatic retry'):o.prepare_next(expected_heads=heads)
        with pytest.raises(ValueError,match='later hours require attempt'):
            o.advance(expected_heads=heads,terminal_sha256='3'*64,reference_records=(),actual_records={'joint':()})


def test_halted_lane_terminal_has_no_next_source_and_no_suffix(setup,holder,monkeypatch):
    s=setup;fresh=m._fresh;calls=[]
    def observed(binding,hour,terminal):calls.append(hour);return fresh(binding,hour,terminal)
    monkeypatch.setattr(m,'_fresh',observed)
    with bootstrap(s,holder,monkeypatch,actual=False) as o:
        old=o.heads;calls.clear();report=o.prepare_next(expected_heads=old)
        assert report.episode_terminal and report.lane_status==( ('joint','halted_unresolved'), )
        assert set(calls)=={0} and o.heads[0]==old[0]
        with pytest.raises(ValueError,match='terminal'):o.prepare_next(expected_heads=o.heads)
        with pytest.raises(ValueError,match='terminal'):
            o.register_alternate_witness(expected_heads=o.heads,hour=0,terminal_sha256='3'*64,
                reference_records=(),actual_records={'joint':()})


def test_full_branch_capacity_failure_has_no_attempt_or_next_source(setup,tmp_path,monkeypatch):
    s=setup;s.manifest=replace(s.manifest,max_events=4)
    with m.tickets.TicketHolder(tmp_path/'limited_tickets_non_authoritative',owner_root=s.root,
            max_tickets=4,max_ticket_bytes=s.manifest.max_event_bytes,max_total_ticket_bytes=s.manifest.max_archive_bytes,
            create=True,retain_head=lambda *a:a[2]) as h:
        with bootstrap(s,h,monkeypatch) as o:
            heads=o.heads;before=h.inspect()
            with pytest.raises(ValueError,match='complete branch'):o.prepare_next(expected_heads=heads)
            assert o.heads==heads and h.inspect()==before


@pytest.mark.parametrize('commit',['before','after'])
@pytest.mark.parametrize('kind',['attempt','episode_terminal'])
def test_phase_ticket_exact_recovery_never_retries(setup,holder,monkeypatch,commit,kind):
    s=setup;tripped=[]
    with bootstrap(s,holder,monkeypatch,actual=kind=='attempt') as o:
        check,rows=o._check,o._rows
        def fault_check():
            check();retained=holder.inspect()
            if commit=='before' and retained[-1].kind==kind and not tripped:
                tripped.append(True);raise RuntimeError('injected attempt before')
        def fault_rows(db):
            result=rows(db)
            if commit=='after' and result[-1][2]==kind and not tripped:
                tripped.append(True);raise RuntimeError('injected attempt after')
            return result
        monkeypatch.setattr(o,'_check',fault_check);monkeypatch.setattr(o,'_rows',fault_rows)
        with pytest.raises(RuntimeError,match='injected'):o.prepare_next(expected_heads=o.heads)
    tail=holder.inspect()[-1]
    with owner(s,holder,expected_heads=tail.before_heads) as o:
        report=o.inspect(expected_heads=o.heads)
        assert report.recovery_required==(commit=='before')
        assert report.pending_attempt==(commit=='after' and kind=='attempt')
        assert report.episode_terminal==(commit=='after' and kind=='episode_terminal')
        assert not report.continuation_available
        with pytest.raises(ValueError):o.prepare_next(expected_heads=o.heads)


@pytest.mark.parametrize('create',[1,0,'yes'])
def test_create_requires_exact_bool_before_owner_creation(setup,holder,create):
    with pytest.raises(ValueError,match='exact bool'):owner(setup,holder,create=create)
    assert not setup.root.exists() and holder.inspect()==()


@pytest.mark.parametrize('drift',['binding','database'])
def test_prepared_tail_replay_rechecks_live_and_database_state(setup,holder,monkeypatch,drift):
    s=setup
    with bootstrap(s,holder,monkeypatch) as o:
        with m.closing(o._connect()) as db:rows=o._rows(db)
        _,state,_=o._restore(rows)
        ticket=m.AppendTicket(o.genesis,len(rows)+1,o.heads,'attempt',m.encode(o._attempt_body(state,rows)))
        holder.retain(ticket)
        original=o._restore
        def changing_tail(current):
            result=original(current)
            if len(current)==len(rows)+1:
                if drift=='binding':o._holder_binding=m.encode({})
                else:
                    with m.closing(o._connect()) as db:
                        db.execute('UPDATE header SET body=?',(b'changed',));db.commit()
            return result
        monkeypatch.setattr(o,'_restore',changing_tail)
        with pytest.raises(ValueError,match='configuration changed|header changed'):
            o.inspect(expected_heads=o.heads)


@pytest.mark.parametrize('hour',[168,191,192])
def test_phase_attempt_boundary_from_explicit_progress_seam(setup,holder,monkeypatch,hour):
    # Check the pure attempt declaration at the phase edge, not an accepted
    # 192-hour prefix. Never persist this artificially advanced state.
    s=setup
    with bootstrap(s,holder,monkeypatch) as o:
        rows,report,state=o._ready_rows(o.heads);heads=o.heads;retained=holder.inspect()
        advanced=replace(state,hour=hour)
        assessment=m.followup.RosterAssessment('0'*64,hour,(),True,hour)
        monkeypatch.setattr(m,'_assessment',lambda _:assessment)
        if hour==192:
            with pytest.raises(ValueError,match='positive next-hour need'):
                o._attempt_body(advanced,rows)
        else:
            body=o._attempt_body(advanced,rows)
            assert body['hour']==hour and body['phase']=='followup'
            assert body['previous_normal_terminal']==s.binding.genesis_terminal_sha256
            assert not body['live_controller_attached']
        assert o.heads==heads and holder.inspect()==retained


@pytest.mark.parametrize('active,max_events',[(True,7),(False,5)])
def test_witness_reserves_continuation_or_stopped_branch(setup,tmp_path,monkeypatch,active,max_events):
    s=setup;s.manifest=replace(s.manifest,max_events=max_events)
    with m.tickets.TicketHolder(tmp_path/'witness_tickets_non_authoritative',owner_root=s.root,
            max_tickets=max_events,max_ticket_bytes=s.manifest.max_event_bytes,max_total_ticket_bytes=s.manifest.max_archive_bytes,
            create=True,retain_head=lambda *a:a[2]) as h:
        with bootstrap(s,h,monkeypatch,actual=active) as o:
            heads=o.heads;before=h.inspect()
            records=saved(monkeypatch,s,m._initial(s.manifest,s.currents[0]),0,actual=active,flow_loop=True)
            def witness():
                return o.register_alternate_witness(expected_heads=heads,hour=0,terminal_sha256='3'*64,
                    reference_records=records[0],actual_records=records[1])
            if active:
                with pytest.raises(ValueError,match='complete branch'):witness()
                assert o.heads==heads and h.inspect()==before
            else:
                result=witness();assert not result.conflicted_keys
                assert o.prepare_next(expected_heads=o.heads).episode_terminal
                assert len(h.inspect())==5
