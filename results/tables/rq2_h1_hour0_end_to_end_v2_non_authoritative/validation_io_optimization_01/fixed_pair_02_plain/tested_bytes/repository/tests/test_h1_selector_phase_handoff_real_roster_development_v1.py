"""Real GroupRoster three-lock lifetime; synthetic phase/source/Parent.

The real roster is metadata-only. Its scientific correspondence is replaced by
an explicit fixture, so this is not complete group/N0 execution evidence.
"""
from copy import deepcopy
from threading import Lock

import pytest

from tests.test_h1_selector_phase_handoff_faults_development_v1 import (
    fault_case,make,context,setup,legacy_setup,no_solver,load)
from tests.test_h1_common_owner_genesis_development_v1 import case as base_case,m
from tests.test_h1_bootstrap_integration_development_v1 import example,setup as bootstrap_setup
from tests.test_h1_group_execution_roster_development_v1 import (
    cached_declarations,declaration,roster)

pytestmark=pytest.mark.parametrize('context',['business_unresolved'],indirect=True)


@pytest.fixture
def case(setup,tmp_path,monkeypatch,example,no_solver,cached_declarations):
    c=base_case.__wrapped__(setup,tmp_path,monkeypatch)
    (tmp_path/'roster_metadata').mkdir()
    b=bootstrap_setup.__wrapped__(tmp_path/'roster_metadata',example,monkeypatch)
    parent=b.open(declaration=declaration(b.declaration));group=None
    try:
        group=roster(parent,b)
        c.roster=group;c.global_=parent._global;c.study=parent.study_root
        c.episode=c.study/'synthetic_phase_episode_non_authoritative';c.episode.mkdir()
        c.report['arm_audits']['joint']['reference']['episode_root']=str(c.episode)
        c.guard=group._original_operation;c.bootstrap_guard=parent._original_operation
        def prepare(r):
            assert r is group
            group._check()
            report=deepcopy(c.report);report['global_head']=parent._global.head
            return setup.manifest,setup.binding,report
        monkeypatch.setattr(m.common,'_prepare_locked',prepare)
        yield c
    finally:
        if group is not None:group.close()
        parent.close()


@pytest.mark.parametrize('replace_guard',[False,True])
def test_real_three_original_guards_held_and_released(fault_case,replace_guard):
    f=fault_case;c=f.c.case;g=f.c.owner
    originals=(g._original_operation,c.guard,c.bootstrap_guard)
    assert len({id(v) for v in originals})==3
    calls=[];foreign=Lock();foreign.acquire()
    before=c.roster.inspect()
    def retain(root,previous,after):
        calls.append(after)
        assert all(guard.locked() for guard in originals)
        if replace_guard and len(calls)==1:c.roster._owner_guard=foreign
        return after
    try:
        with make(f,retain_head=retain) as owner:
            if replace_guard:
                with pytest.raises(ValueError):owner.consume()
                assert len(calls)==1 and owner._state=='failed'
                assert not g.closed and not g.poisoned
            else:
                assert owner.consume()['completed_hours']==1
                assert len(calls)==5
            assert all(not guard.locked() for guard in originals)
            assert foreign.locked() and not f.ref._guard.locked()
            assert c.roster.inspect()==before
    finally:foreign.release()
