"""Diagnostic of the old saved-record owner, NOT a passing acceptance gate.

It documents continuation still offered after an externally prepared before-state.
No producer is called; the phase-owner successor must add a recovery-required gate.
"""
import json
import pytest
from tests.test_h1_persistent_owner_development_v1 import (
    setup,m,saved,initial,open_owner,advance,
)


@pytest.mark.parametrize('supply_ticket',[True,False])
def test_observe_prepared_before_continuation_gap(setup,monkeypatch,supply_ticket):
    s=setup;records=saved(monkeypatch,s,initial(s),0)
    with open_owner(s,create=True) as owner:
        check=owner._check
        def fail_before_commit():
            check()
            if s.tickets:raise RuntimeError('probe after external preparation before commit')
        monkeypatch.setattr(owner,'_check',fail_before_commit)
        with pytest.raises(RuntimeError,match='probe'):advance(owner,records)
        ticket=s.tickets[-1]
    arguments=dict(expected_heads=ticket.before_heads)
    if supply_ticket:arguments['recovery_ticket']=ticket
    with m.DevelopmentOwner(s.root,s.manifest,s.binding,**arguments) as owner:
        report=owner.inspect(expected_heads=owner.heads)
        assert owner.heads==ticket.before_heads and report.completed_hours==0
        assert not report.pending_intent and report.continuation_available
        print(json.dumps(dict(diagnostic_only=True,supply_ticket=supply_ticket,
            prepared_ticket_kind=ticket.kind,pending_intent=report.pending_intent,
            continuation_available=report.continuation_available,producer_called=False,
            successor_recovery_gate_required=True,formal_result=False)))
