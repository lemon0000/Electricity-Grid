"""Owned cleanup and borrowed restoration under callback attribute replacement."""
from threading import Lock
from types import SimpleNamespace

import pytest

from tests.test_h1_selector_phase_handoff_faults_development_v1 import (
    fault_case,make,rows,context,case,setup,legacy_setup,no_solver,load)

pytestmark=pytest.mark.parametrize('context',['business_unresolved'],indirect=True)


@pytest.mark.parametrize('kind,attack',[(k,a) for k in ('phase','holder','journal')
                                     for a in ('lease','aliases','stream','closed')]+[('outer','stream')])
def test_owned_nested_resource_mutation_closes_only_originals(fault_case,kind,attack):
    f=fault_case;calls=[];saved=[];foreign=[]
    def retain(root,before,after):
        calls.append(after)
        if len(calls)==3:
            handles=(owner._phase,owner._holder,owner._journal,owner._lease)
            leases=(handles[0]._lease_object,handles[1]._lease_object,handles[2]._original_lease,handles[3])
            saved.extend((lease,lease.stream) for lease in leases)
            target=dict(zip(('phase','holder','journal','outer'),handles))[kind]
            lease=leases[('phase','holder','journal','outer').index(kind)]
            if attack=='stream':lease.stream=None
            elif attack=='closed':target.closed=True
            else:
                fake=SimpleNamespace(close=lambda:foreign.append('closed'),stream=None)
                if kind=='journal':target._original_lease=fake
                else:target._lease_object=fake
                if attack=='aliases':setattr(target,'_lease' if kind=='journal' else 'lease',fake)
        return after
    with make(f,retain_head=retain) as owner:
        with pytest.raises((ValueError,RuntimeError)):owner.consume()
        assert len(calls)==3 and not foreign
        assert all(stream.closed and lease.stream is None for lease,stream in saved)
        assert rows(f.c.owner.owner_root/'owner.sqlite')==[]
        assert not f.ref._guard.locked() and not f.c.case.guard.locked()


@pytest.mark.parametrize('kind',['holder','phase'])
def test_changed_nested_guard_releases_the_actually_acquired_guard(fault_case,kind):
    f=fault_case;calls=[];original=[];foreign=Lock()
    def retain(root,before,after):
        calls.append(after)
        if len(calls)==3:
            target=owner._holder if kind=='holder' else owner._phase
            name='_guard' if kind=='holder' else '_operation'
            original.append(getattr(target,name));assert original[0].locked()
            setattr(target,name,foreign)
        return after
    with make(f,retain_head=retain) as owner:
        with pytest.raises((ValueError,RuntimeError)):owner.consume()
        assert len(calls)==3 and not original[0].locked() and not foreign.locked()
        assert owner._holder._lease_object.stream is None and owner._phase._lease_object.stream is None


@pytest.mark.parametrize('attack',['phase_lease','holder_lease','journal_lease','phase_guard','holder_guard',
                                 'common_guard','roster','phase_closed','common_closed','stream'])
def test_pre_takeover_borrowed_fields_restore_and_revalidate(fault_case,attack):
    f=fault_case;g=f.c.owner;before_view=g.inspect();calls=[];foreign=[]
    original=(g._phase._lease_object,g._holder._lease_object,g._journal._original_lease)
    streams=tuple(lease.stream for lease in original)
    def retain(root,before,after):
        calls.append(after)
        fake=SimpleNamespace(close=lambda:foreign.append('close'),_leave=lambda:foreign.append('leave'))
        if attack=='phase_lease':g._phase._lease_object=fake
        elif attack=='holder_lease':g._holder._lease_object=fake
        elif attack=='journal_lease':g._journal._original_lease=fake
        elif attack=='phase_guard':g._phase._operation=Lock()
        elif attack=='holder_guard':g._holder._guard=Lock()
        elif attack=='common_guard':g._original_operation=Lock()
        elif attack=='roster':g._original_roster=fake
        elif attack=='phase_closed':g._phase.closed=True
        elif attack=='common_closed':g.closed=True
        else:g._holder._lease_object.stream=None
        return after
    with make(f,retain_head=retain) as owner:
        with pytest.raises((ValueError,RuntimeError)):owner.consume()
        assert len(calls)==1 and not foreign
        assert not g.closed and not g.poisoned and g.inspect()==before_view
        assert tuple(lease.stream for lease in original)==streams and all(not s.closed for s in streams)
        assert not g._original_operation.locked() and not f.c.case.guard.locked()
