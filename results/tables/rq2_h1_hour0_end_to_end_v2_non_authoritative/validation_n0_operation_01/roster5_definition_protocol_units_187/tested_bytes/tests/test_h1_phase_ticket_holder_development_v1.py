"""Real local ticket files; no source reads, solver or Job."""
import pytest
from experiments import h1_phase_ticket_holder_development_v1 as m
from experiments import h1_prepared_ticket_owner_development_v1 as legacy


def open_holder(tmp_path,**kw):
    return m.TicketHolder(tmp_path/'phase_tickets_non_authoritative',
        owner_root=tmp_path/'phase_owner_non_authoritative',max_tickets=8,
        max_ticket_bytes=100,max_total_ticket_bytes=300,**kw)


def append(h,kind,body=None):
    if body is None:body=m.encode({})
    previous=h.inspect()
    before=previous[-1].after_heads if previous else ('a'*64,'a'*64)
    ticket=m.old.AppendTicket('a'*64,len(previous)+1,before,kind,body)
    assert h.retain(ticket)==ticket.identity
    return ticket


def test_phase_kinds_preserve_outcome_head_and_reopen(tmp_path):
    retained=[]
    def retain(*args):retained.append(args);return args[2]
    with open_holder(tmp_path,create=True,retain_head=retain) as h:
        outcome='a'*64
        for kind in m.KINDS:
            t=append(h,kind)
            if kind=='outcome':outcome=t.event[-1]
            assert t.after_heads==(outcome,t.event[-1])
        head=h.head;expected=h.inspect()
    with open_holder(tmp_path,expected_head=head) as h:
        assert h.inspect()==expected
    assert len(retained)==5 and retained[-1][2]==head


@pytest.mark.parametrize('branches',[((1,)*9,),((100,100,100,1),),((1,),(100,100,100,1)),((True,),),((0,),),((101,),),(),([1],)])
def test_every_full_branch_must_fit_before_handoff(tmp_path,branches):
    calls=[]
    with open_holder(tmp_path,create=True,retain_head=lambda *a:calls.append(a)) as h:
        before=h.head
        with pytest.raises(ValueError):h.check_branches(expected_head=before,branches=branches)
        assert h.head==before and h.inspect()==() and calls==[]
        assert {p.name for p in h.root.iterdir()}=={'execution.lock','header.json'}


def test_branch_capacity_rechecks_used_bytes_and_stale_head(tmp_path):
    with open_holder(tmp_path,create=True,retain_head=lambda *a:a[2]) as h:
        head=h.head
        fit=h.check_branches(expected_head=head,branches=((100,100,100),(100,100)))
        assert fit['logical_fit'] and not fit['reservation_held'] and not fit['producer_admitted']
        append(h,'attempt')
        with pytest.raises(ValueError,match='stale'):h.check_branches(expected_head=head,branches=((1,),))
        with pytest.raises(ValueError,match='complete branch'):h.check_branches(expected_head=h.head,branches=((100,100,100),))
        used=len(m.encode({}))
        assert h.check_branches(expected_head=h.head,branches=((100,100,100-used),))['used_body_bytes']==used


def test_total_body_limit_blocks_write_and_reopen_configuration_drift(tmp_path):
    with open_holder(tmp_path,create=True,retain_head=lambda *a:a[2]) as h:
        body=m.encode('x'*97);assert len(body)==100
        for kind in ('attempt','intent','outcome'):append(h,kind,body)
        before=h.head
        with pytest.raises(ValueError,match='bounds'):append(h,'episode_terminal')
        assert h.head==before and len(h.inspect())==3
    with pytest.raises(ValueError,match='header differs'):
        m.TicketHolder(tmp_path/'phase_tickets_non_authoritative',owner_root=tmp_path/'phase_owner_non_authoritative',
            max_tickets=8,max_ticket_bytes=100,max_total_ticket_bytes=301,expected_head=before)


def test_live_total_limit_tampering_rejected(tmp_path):
    with open_holder(tmp_path,create=True) as h:
        h.max_total_ticket_bytes+=1
        with pytest.raises(ValueError,match='identity changed'):h.inspect()


def test_new_and_legacy_holder_headers_cannot_be_reinterpreted(tmp_path):
    with open_holder(tmp_path,create=True) as h:head=h.head
    with pytest.raises(ValueError,match='header differs'):
        legacy.TicketHolder(tmp_path/'phase_tickets_non_authoritative',owner_root=tmp_path/'phase_owner_non_authoritative',
            max_tickets=8,max_ticket_bytes=100,expected_head=head)
    root=tmp_path/'legacy_non_authoritative';owner=tmp_path/'old_owner_non_authoritative'
    with legacy.TicketHolder(root,owner_root=owner,max_tickets=8,max_ticket_bytes=100,create=True) as h:head=h.head
    with pytest.raises(ValueError,match='header differs'):
        m.TicketHolder(root,owner_root=owner,max_tickets=8,max_ticket_bytes=100,max_total_ticket_bytes=300,expected_head=head)
