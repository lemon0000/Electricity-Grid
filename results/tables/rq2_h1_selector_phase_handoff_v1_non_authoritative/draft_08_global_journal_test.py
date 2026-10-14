"""Real retained pre-source claim journals; synthetic Parent/source/roster.

Only journal ancestry and operation-time head stability are exercised. This is
not a complete GroupRoster/common correspondence or accepted N0 execution test.
"""
from copy import deepcopy
from dataclasses import replace

import pytest

from tests.test_h1_selector_phase_handoff_faults_development_v1 import (
    fault_case,make,context,setup,legacy_setup,no_solver,load)
from tests.test_h1_common_owner_genesis_development_v1 import case as base_case,m
from tests.test_h1_bootstrap_integration_development_v1 import (
    example,setup as bootstrap_setup,retained)

pytestmark=pytest.mark.parametrize('context',['business_unresolved'],indirect=True)


@pytest.fixture
def case(setup,tmp_path,monkeypatch,example,no_solver):
    c=base_case.__wrapped__(setup,tmp_path,monkeypatch)
    b=bootstrap_setup.__wrapped__(tmp_path/'claims',example,monkeypatch)
    active=[]
    def claim(ordinal):
        kw={} if not active else dict(create_study=False,global_head=retained(active[-1],b)['global_head'])
        if active:active[-1].close()
        owner=b.open(declaration=replace(b.declaration,ordinal=ordinal),**kw)
        active.append(owner)
        with pytest.raises(ValueError,match='producer not implemented'):owner.bootstrap()
        journal=owner._global
        assert journal.rows() and journal.rows()[-1][1]['kind']=='claim'
        c.roster._owner._global=journal;c.global_=journal
        return journal.head
    claim(0)
    def prepare(roster):
        assert roster is c.roster and c.guard.locked()
        report=deepcopy(c.report);report['global_head']=c.global_.head
        return setup.manifest,setup.binding,report
    monkeypatch.setattr(m.common,'_prepare_locked',prepare)
    c.claim=claim
    try:yield c
    finally:
        for owner in reversed(active):owner.close()


@pytest.mark.parametrize('during_callback',[False,True])
def test_real_retained_journal_ancestor_and_operation_head(fault_case,during_callback):
    f=fault_case;c=f.c.case;captured=c.global_.head
    advanced=c.claim(1)
    assert captured!=advanced and captured in {head for head,_ in c.global_.rows()}
    calls=[]
    def retain(root,before,after):
        calls.append(after)
        if during_callback and len(calls)==1:c.claim(2)
        return after
    with make(f,retain_head=retain) as owner:
        if during_callback:
            with pytest.raises(ValueError):owner.consume()
            assert owner._state=='failed' and f.c.owner.poisoned and not f.c.owner.closed
            assert len(calls)==1
        else:
            assert owner.consume()['completed_hours']==1
            assert len(calls)==5
        assert not c.guard.locked() and not f.ref._guard.locked()
