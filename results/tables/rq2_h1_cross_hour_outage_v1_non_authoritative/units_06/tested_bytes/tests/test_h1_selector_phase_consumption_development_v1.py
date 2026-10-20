"""Pure preview versus real phase persistence over fabricated selector records."""
from dataclasses import replace

import pytest

from experiments import h1_selector_phase_consumption_development_v1 as m
from tests.test_h1_phase_owner_development_v1 import setup,legacy_setup,holder,owner,saved


@pytest.mark.parametrize('actual',[True,False])
def test_preview_matches_exact_holder_and_database_events(setup,holder,monkeypatch,actual):
    s=setup;phase=m.phase
    with owner(s,holder,create=True) as store:
        records=saved(monkeypatch,s,phase._initial(s.manifest,s.currents[0]),0,actual=actual)
        before=store.heads;retained=holder.head
        plan=m._planned_bootstrap(s.manifest,s.binding,s.currents[0],
            owner_genesis=store.genesis,holder_genesis=holder.genesis,
            reference_records=records[0],actual_records=records[1])
        tickets,retentions,projection,state=plan.tickets,plan.retentions,plan.projection,plan.after
        assert store.heads==before and holder.head==retained and holder.inspect()==()
        calls=[]
        def retain(*args):calls.append(args);return args[2]
        holder.retain_head=retain
        result=store.advance(expected_heads=before,terminal_sha256=s.binding.genesis_terminal_sha256,
            reference_records=records[0],actual_records=records[1])
        assert holder.inspect()==tickets and tuple(calls)==retentions
        assert store.heads==tickets[-1].after_heads and holder.head==retentions[-1][2]
        with phase.closing(store._connect()) as db:rows=store._rows(db)
        assert rows==[ticket.event for ticket in tickets]
        assert tuple((holder.root/f'{i:06d}.json').read_bytes() for i in (1,2))==plan.holder_records
        observation=m._observe_bootstrap(plan,retained_count=2,holder_records=plan.holder_records,phase_rows=tuple(rows))
        assert observation['state']=='bootstrap_rows_present' and not observation['parent_phase_commit_verified']
        assert result.completed_hours==1
        assert phase.json.loads(tickets[-1].body)['projection']==phase.json.loads(projection)
        assert phase.json.loads(projection)['after']==phase.json.loads(state)
        statuses=[r['status'] for r in phase.json.loads(projection)['lanes']]
        assert statuses==['paired_committed' if actual else 'actual_unresolved']


def test_preview_preserves_complete_branch_capacity_and_lane_inventory(setup,monkeypatch):
    s=setup;state=m.phase._initial(s.manifest,s.currents[0])
    ref,act=saved(monkeypatch,s,state,0)
    options=dict(owner_genesis='a'*64,holder_genesis='b'*64,reference_records=ref,actual_records=act)
    with pytest.raises(ValueError,match='complete bootstrap branch'):
        m._planned_bootstrap(replace(s.manifest,max_events=2),s.binding,s.currents[0],**options)
    with pytest.raises(ValueError):
        m._planned_bootstrap(s.manifest,s.binding,s.currents[0],**(options|dict(actual_records={})))
    with pytest.raises(ValueError,match='current hour zero'):
        m._planned_bootstrap(s.manifest,s.binding,s.currents[1],**options)


@pytest.mark.parametrize('number',[1,2])
@pytest.mark.parametrize('point',['retention','holder_before','holder_after','db_before','db_after'])
def test_observation_preserves_each_write_failure_window(setup,holder,monkeypatch,number,point):
    s=setup;phase=m.phase;external=[]
    with owner(s,holder,create=True) as store:
        ref,act=saved(monkeypatch,s,phase._initial(s.manifest,s.currents[0]),0)
        plan=m._planned_bootstrap(s.manifest,s.binding,s.currents[0],owner_genesis=store.genesis,
            holder_genesis=holder.genesis,reference_records=ref,actual_records=act)
        def retain(*args):
            assert args==plan.retentions[len(external)]
            external.append(args)
            if len(external)==number and point=='retention':raise RuntimeError('injected retention')
            return args[2]
        holder.retain_head=retain
        original_new=phase.tickets._new
        def failing_new(path,raw):
            if path.name==f'{number:06d}.json' and point=='holder_before':raise RuntimeError('injected holder before')
            result=original_new(path,raw)
            if path.name==f'{number:06d}.json' and point=='holder_after':raise RuntimeError('injected holder after')
            return result
        monkeypatch.setattr(phase.tickets,'_new',failing_new)
        check=store._check;read_rows=store._rows
        def failing_check():
            check()
            if point=='db_before' and len(holder.inspect())==number:raise RuntimeError('injected db before')
        def failing_rows(db):
            rows=read_rows(db)
            if point=='db_after' and len(rows)==number:raise RuntimeError('injected db after')
            return rows
        monkeypatch.setattr(store,'_check',failing_check);monkeypatch.setattr(store,'_rows',failing_rows)
        with pytest.raises(RuntimeError,match='injected'):
            store.advance(expected_heads=store.heads,terminal_sha256=s.binding.genesis_terminal_sha256,
                reference_records=ref,actual_records=act)
        # Read known paths and read-only SQL evidence without retrying the poisoned owner.
        raw=tuple((holder.root/f'{i:06d}.json').read_bytes() for i in (1,2) if (holder.root/f'{i:06d}.json').exists())
        with phase.closing(store._connect()) as db:
            rows=tuple(db.execute('SELECT seq,predecessor,kind,body,head FROM events ORDER BY seq').fetchall())
        result=m._observe_bootstrap(plan,retained_count=len(external),holder_records=raw,phase_rows=rows)
        expected=('holder_retention_pending' if point in ('retention','holder_before') else
            'phase_commit_pending' if point in ('holder_after','db_before') else
            'outcome_pending' if number==1 else 'bootstrap_rows_present')
        assert result['state']==expected
        assert all(v is False for k,v in result.items() if k not in ('state','retained_count','holder_rows','phase_rows'))


def test_preview_rejects_unknown_suffix_order_and_forged_shapes(setup,holder,monkeypatch):
    s=setup;phase=m.phase
    with owner(s,holder,create=True) as store:
        ref,act=saved(monkeypatch,s,phase._initial(s.manifest,s.currents[0]),0)
        plan=m._planned_bootstrap(s.manifest,s.binding,s.currents[0],owner_genesis=store.genesis,
            holder_genesis=holder.genesis,reference_records=ref,actual_records=act)
        rows=tuple(t.event for t in plan.tickets)
        assert m._observe_bootstrap(plan,retained_count=0,holder_records=(),phase_rows=())['state']=='planned_only'
        for count,raw,db in ((0,plan.holder_records[:1],()),(2,plan.holder_records[:1],()),
                (1,plan.holder_records,rows),(2,plan.holder_records+(b'unknown',),rows),
                (2,plan.holder_records,rows+(rows[-1],)),(2,(b'changed',),())):
            with pytest.raises(ValueError):m._observe_bootstrap(plan,retained_count=count,holder_records=raw,phase_rows=db)
        with pytest.raises(ValueError):m._observe_bootstrap(plan,retained_count=True,holder_records=(),phase_rows=())
        with pytest.raises(ValueError):replace(plan,holder_records=(b'changed',plan.holder_records[1]))
        with pytest.raises(ValueError):replace(plan,after=b'{}')
        with pytest.raises(ValueError):
            m._observe_bootstrap(plan,retained_count=1,holder_records=plan.holder_records[:1],phase_rows=((True,*rows[0][1:]),))
        assert holder.inspect()==() and store.heads==(store.genesis,store.genesis)


@pytest.mark.parametrize('incomplete',[None,'alpha','omega'])
def test_multiple_lanes_have_independent_records_and_outcomes(setup,holder,monkeypatch,incomplete):
    s=setup;phase=m.phase
    s.manifest=replace(s.manifest,lanes=tuple(replace(s.manifest.lanes[0],lane_id=k) for k in ('alpha','omega')))
    with owner(s,holder,create=True) as store:
        ref,act=saved(monkeypatch,s,phase._initial(s.manifest,s.currents[0]),0)
        if incomplete is not None:act[incomplete]=act[incomplete][:-1]
        options=dict(owner_genesis=store.genesis,holder_genesis=holder.genesis,reference_records=ref,actual_records=act)
        plan=m._planned_bootstrap(s.manifest,s.binding,s.currents[0],**options)
        for invalid in ({'alpha':act['alpha']},act|{'unknown':()}):
            with pytest.raises(ValueError,match='complete canonical'):
                m._planned_bootstrap(s.manifest,s.binding,s.currents[0],**(options|dict(actual_records=invalid)))
        store.advance(expected_heads=store.heads,terminal_sha256=s.binding.genesis_terminal_sha256,
            reference_records=ref,actual_records=act)
        assert holder.inspect()==plan.tickets
        outcomes=phase.json.loads(plan.projection)['lanes']
        assert [(r['lane_id'],r['status']) for r in outcomes]==[
            (k,'actual_unresolved' if k==incomplete else 'paired_committed') for k in ('alpha','omega')]
        for row in outcomes:
            if row['lane_id']==incomplete:
                assert row['after_business']==row['before_business'] and row['after_actual']==row['before_actual']
                assert row['halted'] is True
            else:assert row['halted'] is False


def test_exact_whole_branch_and_actual_body_capacity(setup,monkeypatch):
    s=setup;phase=m.phase
    ref,act=saved(monkeypatch,s,phase._initial(s.manifest,s.currents[0]),0)
    options=dict(owner_genesis='a'*64,holder_genesis='b'*64,reference_records=ref,actual_records=act)
    plan=m._planned_bootstrap(s.manifest,s.binding,s.currents[0],**options)
    cap=max(len(t.body) for t in plan.tickets)
    exact=replace(s.manifest,max_events=3,max_event_bytes=cap,max_archive_bytes=3*cap)
    assert m._planned_bootstrap(exact,s.binding,s.currents[0],**options)==plan
    with pytest.raises(ValueError,match='complete bootstrap branch'):
        m._planned_bootstrap(replace(exact,max_archive_bytes=3*cap-1),s.binding,s.currents[0],**options)
    assert len(plan.tickets[0].body)==cap
    with pytest.raises(ValueError,match='planned phase body exceeds cap'):
        m._planned_bootstrap(replace(exact,max_event_bytes=cap-1),s.binding,s.currents[0],**options)
    # For bootstrap seq=1/2, fixed-width SHA fields and fixed kind labels,
    # independent base64 length arithmetic proves holder cap is conservative.
    # An exactly full holder cap cannot be reached by a legal bounded body.
    from base64 import b64encode
    for ticket,raw in zip(plan.tickets,plan.holder_records,strict=True):
        overhead=len(raw)-len(b64encode(ticket.body))
        assert overhead<4096
        assert len(raw)==overhead+4*((len(ticket.body)+2)//3)
        assert overhead+4*((cap+2)//3)<2*cap+4096
    original=phase._transition
    def enlarged(*a,**kw):
        after,projection=original(*a,**kw)
        # Explicit serialization-cap seam only, not a scientific candidate.
        return after,phase.encode(phase.json.loads(projection)|dict(cap_test_padding='x'*(2*cap)))
    monkeypatch.setattr(phase,'_transition',enlarged)
    with pytest.raises(ValueError,match='planned phase body exceeds cap'):
        m._planned_bootstrap(exact,s.binding,s.currents[0],**options)
