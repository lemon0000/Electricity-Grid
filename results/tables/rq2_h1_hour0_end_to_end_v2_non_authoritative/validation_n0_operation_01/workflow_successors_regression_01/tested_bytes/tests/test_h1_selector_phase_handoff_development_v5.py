"""Genuine partial Parent3/Handoff5 persistence with explicit fake common source.

The common bridge, source rows, selector solver and Job transport are synthetic.
The real Handoff validates an issued Rref, records business-unresolved, retains,
closes, and reopens the saved phase. This is not three-arm N0 acceptance.
"""
import json
from pathlib import Path
from types import ModuleType

import pytest
import experiments

from tests.h1_hour0_synthetic_harness_v3 import harness,load
from tests.test_h1_selector_parent_controller_development_v3 import (
    context,case,setup,base_setup,legacy_setup,sequence_factory,no_solver)

pytestmark=pytest.mark.parametrize('context',['business_unresolved'],indirect=True)


def explicit_fake_common_bridge(common):
    bridge=ModuleType('explicit_fake_common_validation_for_partial_test')
    bridge.__file__=__file__
    def bind(api,kind,verify,operation,finalized):
        def attach(owner,token):
            verify(owner);operation(owner,token)
        def prepare(owner):
            verify(owner)
            return common.common._prepare_locked(owner._genesis._roster)
        def declaration(owner):
            return dict(explicit_fake_common_source=True,formal_result=False,resource_admission=False)
        def finish(owner):verify(owner)
        def abort(owner,error):pass
        def receipt(owner):
            return dict(explicit_fake_common_source=True,complete=False,formal_result=False)
        return attach,prepare,declaration,finish,abort,receipt,receipt
    bridge._bind_handoff=bind
    return bridge


def test_business_unresolved_partial_closes_and_replays_original_science(harness,monkeypatch):
    h=harness;p=h.module;c=h.context
    from experiments import h1_common_owner_genesis_development_v2 as common
    root=Path(p.__file__).parent
    helper=load(str(root/'h1_selector_parent_validation_operation_development_v3.py'),
        'experiments.h1_selector_parent_validation_operation_development_v3',monkeypatch)
    monkeypatch.setattr(experiments,'h1_selector_parent_validation_operation_development_v3',helper,raising=False)
    bridge=explicit_fake_common_bridge(common)
    consumer=load(str(root/'h1_selector_phase_handoff_development_v5.py'),
        'experiments.h1_selector_phase_handoff_development_v5',monkeypatch,{
            'h1_selector_parent_controller_development_v3':p,
            'h1_common_validation_operation_development_v3':bridge,
            'h1_selector_parent_validation_operation_development_v3':helper})
    monkeypatch.setattr(experiments,'h1_selector_phase_handoff_development_v5',consumer,raising=False)
    retained=[]
    def retain(path,before,after):
        assert reference._guard.locked() and c.case.guard.locked()
        retained.append((before,after));return after
    options=dict(retain_head=retain,max_packet_bytes=64*1024**2,
        max_record_bytes=1024**2,max_archive_bytes=128*1024**2)
    with p.Parent(h.root,h.raw,**h.options) as reference:
        issued=reference.run()
        with consumer.Handoff(c.owner,(reference,issued),{'joint':None},**options) as owner:
            result=owner.consume()
            assert result['completed_hours']==1 and len(retained)==5
            assert result['parent_validation_receipt'] is None
            assert result['validation_receipt']['explicit_fake_common_source']
            lane=json.loads(owner._plan.projection)['lanes'][0]
            assert lane['status'] in ('business_input_unresolved','business_unresolved')
            assert lane['before_business']==lane['after_business']
            assert lane['before_actual']==lane['after_actual']
            saved=dict(tickets=owner._plan.tickets,after=owner._plan.after,
                projection=owner._plan.projection,holder_head=owner._holder.head,phase_heads=owner._phase.heads)
            assert not reference._guard.locked() and c.owner.closed
            p._WINDOWS.assert_idle(reference)
    assert not c.case.guard.locked()
    phase=consumer.phase;manifest=c.owner._manifest
    def deny(*args):raise AssertionError('saved replay cannot retain events')
    with phase.tickets.TicketHolder(c.owner.holder_root,owner_root=c.owner.owner_root,
            max_tickets=manifest.max_events,max_ticket_bytes=manifest.max_event_bytes,
            max_total_ticket_bytes=manifest.max_archive_bytes,create=False,
            expected_head=saved['holder_head'],retain_head=deny) as holder:
        assert holder.inspect()==saved['tickets']
        with phase.DevelopmentOwner(c.owner.owner_root,manifest,c.owner._binding,holder=holder,
                create=False,expected_heads=saved['phase_heads']) as reopened:
            report=reopened.inspect(expected_heads=saved['phase_heads'])
            with phase.closing(reopened._connect()) as db:rows=reopened._rows(db)
            replay,state,_=reopened._restore(rows)
            assert replay==report and report.completed_hours==1
            assert phase.encode(state.scientific)==saved['after']
            assert phase.encode(json.loads(rows[-1][3])['projection'])==saved['projection']
            assert rows==[ticket.event for ticket in saved['tickets']]
