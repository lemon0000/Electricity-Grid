"""Synthetic Parent guards and roster rejection; no execution authentication."""
from dataclasses import replace
import json

import pytest

from tests.test_h1_selector_phase_handoff_faults_development_v1 import (
    fault_case,context,case,setup,legacy_setup,no_solver,load)

pytestmark=pytest.mark.parametrize('context',['business_unresolved'],indirect=True)


def actual(f,lane):
    owner=type(f.ref)()
    owner._issued=replace(owner._issued,role='actual')
    owner._reference_owner=f.ref;owner._reference_completion=f.receipt
    doc=json.loads(owner._raw);doc['declaration']['lane_id']=lane
    owner._raw=f.m.phase.encode(doc)
    return owner,owner._issued


def test_multiple_actual_guards_are_held_and_released_as_one_bundle(fault_case):
    f=fault_case;a=actual(f,'a');z=actual(f,'z')
    bundle=f.m._Bundle((f.ref,f.receipt),{'z':z,'a':a})
    bundle.enter()
    try:
        assert bundle.held==[a[0]._guard,z[0]._guard,f.ref._guard]
        assert all(g.locked() for g in bundle.held)
        assert a[0]._reference_held and z[0]._reference_held
        bundle.validate()
    finally:bundle.leave()
    assert not any(o._guard.locked() for o in (a[0],z[0],f.ref))
    assert not a[0]._reference_held and not z[0]._reference_held
    a[0].close();z[0].close()


@pytest.mark.parametrize('roster',[{}, {'joint':None,'extra':None}])
def test_missing_or_extra_roster_keys_reject_before_writes(fault_case,roster):
    f=fault_case;before=f.c.owner.inspect()
    with f.m.Handoff(f.c.owner,(f.ref,f.receipt),roster,**f.options) as owner:
        with pytest.raises(ValueError,match='complete exact Actual disposition roster'):owner.consume()
        assert not owner.root.exists() and not f.retained
    assert f.c.owner.inspect()==before


def test_actual_for_business_unresolved_lane_rejects_before_writes(fault_case):
    f=fault_case;pair=actual(f,'joint')
    with f.m.Handoff(f.c.owner,(f.ref,f.receipt),{'joint':pair},**f.options) as owner:
        with pytest.raises(ValueError,match='unused Actual execution'):owner.consume()
        assert not owner.root.exists() and not f.retained and not f.c.owner.closed
        assert not pair[0]._reference_held and not pair[0]._guard.locked()
    pair[0].close()
