import ast
from dataclasses import asdict
import inspect

import pytest
from pyomo.environ import Var

from experiments import h1_origin_grid_step_development_v1 as m
from tests import test_h1_current_grid_step_development_v1 as prior

R=m.Lane('Rref',None)
A=m.Lane('A','joint_correct_shared')
G,B=prior.G,prior.B


def frame(**kwargs):
    previous=kwargs.pop('prior',None)
    if previous is not None:
        kwargs['prior']=prior.m._owned(prior.m.NormalFrame,**vars(previous))
    return m._owned(m.NormalFrame,**vars(prior.frame(**kwargs)))


def origin(f,active=None,*,chronology=True,lane=R):
    proto=m.events.DisclosureProtocol((B,G),
        'current_n1_outage_overlay_revealed_before_current_action',
        'complete_current_n1_outage_overlay__no_hidden_same_hour_replacement','mechanism_assumption')
    state=m.events.initialize_disclosure(proto,source_hour=0,active_component=active)
    return m.initialize_development_carry(f,state,lane=lane,chronology_origin=chronology)


def action(f,b,active=None,cap=None):
    if b.event_hour_offset==0 and f.info.relative_hour==0:
        assert cap is None
        return m.registry.FirstAction(0,b.disclosure)
    return m.registry.TransitionAction(f.info.relative_hour,m.events.disclose_current(b.disclosure,
        m.events.CurrentOutageReport(f.info.relative_hour+b.event_hour_offset,active,cap)))


def power(hour=0,mw=0):
    q=m.Q(str(mw));return m.RelativeDcPower(hour,str(q.numerator),str(q.denominator),'mechanism_assumption')


def run(f,b,*,generation=20.,mw=0,active=None,cap=None,lane=R):
    a=action(f,b,active,cap);p=power(f.info.relative_hour,mw)
    key=m.development_step_identity(f,a,b,p,lane=lane)
    model=m.build_development_model(f,a,b,p,lane=lane,expected_identity=key)
    values={v.name:0. for v in model.component_data_objects(Var)};values['generation[G1]']=generation
    return m.audit_development_assignment(f,a,b,p,values,lane=lane,expected_identity=key)


@pytest.mark.parametrize('active,demand,generation',[(None,20.,20.),(G,0.,0.),(B,20.,20.)])
def test_first_action_is_real_action_without_disclosure_transition(active,demand,generation,monkeypatch):
    f=frame(demand=demand,normal=20.);b=origin(f,active)
    def denied(*args,**kwargs):raise AssertionError('first action created a transition')
    monkeypatch.setattr(m.events,'disclose_current',denied)
    w=run(f,b,generation=generation)
    assert w.physical_assignment_valid,w.errors
    assert w.next_carry.completed_hours==1 and w.next_carry.disclosure==b.disclosure
    assert w.next_carry.previous_carry_identity==b.identity
    assert w.next_carry.previous_audit_identity==b.audit_identity


def test_first_action_and_ordinary_stay_have_equal_science_different_audit():
    f=frame();a=origin(f);b=origin(f,chronology=False);p=power()
    aa,ab=action(f,a),action(f,b)
    assert a.identity==b.identity and a.audit_identity!=b.audit_identity
    ka=m.development_step_identity(f,aa,a,p,lane=R);kb=m.development_step_identity(f,ab,b,p,lane=R)
    assert ka==kb
    assert m.audit_step_identity(f,aa,a,p,lane=R)!=m.audit_step_identity(f,ab,b,p,lane=R)
    ma=m.build_development_model(f,aa,a,p,lane=R,expected_identity=ka)
    mb=m.build_development_model(f,ab,b,p,lane=R,expected_identity=kb)
    assert prior.signature(ma)==prior.signature(mb)
    wa,wb=run(f,a),run(f,b)
    assert wa.next_carry.identity==wb.next_carry.identity
    assert wa.next_carry.audit_identity!=wb.next_carry.audit_identity
    assert wa.maximum_exact_violation==wb.maximum_exact_violation==0


@pytest.mark.parametrize('chronology',[True,False])
def test_three_action_clocks_and_source_mode_cannot_switch(chronology):
    f=frame();b=origin(f,chronology=chronology)
    for hour in range(3):
        w=run(f,b)
        assert w.physical_assignment_valid
        b=w.next_carry
        assert b.completed_hours==hour+1 and b.disclosure.source_hour==hour+b.event_hour_offset
        f=frame(prior=f)
    forged=m._owned(m.PhysicalCandidateCarry,**(vars(b)|{'event_hour_offset':1-b.event_hour_offset}))
    valid_action=action(f,b)
    with pytest.raises(ValueError,match='clock'):
        m.development_step_identity(f,valid_action,forged,power(f.info.relative_hour),lane=R)


def test_wrong_first_transition_and_repeated_first_action_rejected():
    f=frame();c=origin(f);o=origin(f,chronology=False)
    d=m.registry.TransitionAction(0,m.events.disclose_current(c.disclosure,m.events.CurrentOutageReport(1,None,None)))
    with pytest.raises(ValueError,match='genuine first'):
        m.development_step_identity(f,d,c,power(),lane=R)
    with pytest.raises(ValueError,match='requires a transition'):
        m.development_step_identity(f,m.registry.FirstAction(0,o.disclosure),o,power(),lane=R)
    w=run(f,c);g=frame(prior=f)
    with pytest.raises(ValueError,match='clock'):
        m.development_step_identity(g,m.registry.FirstAction(0,w.next_carry.disclosure),w.next_carry,power(1),lane=R)


def test_initial_down_returns_at_action1_with_exact_cap():
    f=frame(demand=0.,normal=20.,ramp=4.);b=origin(f,G)
    w=run(f,b,generation=0.)
    assert w.physical_assignment_valid
    g=frame(prior=f,demand=20.,ramp=4.)
    assert not run(g,w.next_carry,generation=20.,cap=19.).physical_assignment_valid
    assert run(g,w.next_carry,generation=20.,cap=20.).physical_assignment_valid
    with pytest.raises(ValueError):run(g,w.next_carry,generation=20.)
    with pytest.raises(ValueError,match='nameplate'):run(g,w.next_carry,generation=20.,cap=101.)


def test_first_action_keeps_ramp_and_lane_local_generation():
    f=frame(ramp=10.);normal_before=asdict(f)
    r=run(f,origin(f,lane=R),generation=30.,mw=10,lane=R)
    a=run(f,origin(f,lane=A),generation=20.,lane=A)
    assert r.physical_assignment_valid and a.physical_assignment_valid
    g=frame(prior=f,demand=10.,normal=20.,ramp=10.)
    assert not run(g,r.next_carry,generation=10.,lane=R).physical_assignment_valid
    assert run(g,a.next_carry,generation=10.,lane=A).physical_assignment_valid
    with pytest.raises(ValueError,match='cross-lane'):run(g,r.next_carry,generation=10.,lane=A)
    assert asdict(f)==normal_before
    # Already-on synthetic N origin removes the allowed startup bonus.
    nb=m.information.source._owned(type(f.normal_before),**(vars(f.normal_before)|{'units':(('G1',True,20.,1),)}))
    info=m.information._owned(type(f.info),**(vars(f.info)|{'normal':m.information._owned(type(f.info.normal),
        **(vars(f.info.normal)|{'previous_commitment':(('G1',True),)}))}))
    fixed=m._owned(m.NormalFrame,**(vars(f)|{'normal_before':nb,'info':info}))
    assert not run(fixed,origin(fixed),generation=31.,mw=11.).physical_assignment_valid


def test_normalized_onset_and_past_event_history_remain_in_identity():
    f=frame();b=origin(f);first=run(f,b).next_carry;g=frame(prior=f,demand=0.,normal=20.)
    d=action(g,first,G)
    assert m._revealed_projection(d.step.after,0)['active']['observed_start_relative_hour']==1
    changed=m.events._owned(m.events.DisclosureState,protocol=d.step.after.protocol,origin_hour=0,
        source_hour=2,observed_event_count=1,active=m.events.RevealedOutage(1,G,2,2))
    assert m._revealed_projection(changed,0)!=m._revealed_projection(d.step.after,0)
    assert m._revealed_projection(changed,1)==m._revealed_projection(d.step.after,0)


def test_old_model_body_and_exact_residual_ast_are_unchanged():
    assert ast.dump(ast.parse(inspect.getsource(m._exact_residual)))==ast.dump(ast.parse(inspect.getsource(prior.m._exact_residual)))
    def body(fn):
        tree=ast.parse(inspect.getsource(fn)).body[0]
        for i,s in enumerate(tree.body):
            if isinstance(s,ast.Assign) and ast.unparse(s.targets[0])=='(n, c, plan)':
                return [ast.dump(x) for x in tree.body[i:]]
        raise AssertionError('missing mathematical body')
    assert body(m.build_development_model)==body(prior.m.build_development_model)


@pytest.mark.parametrize('incoming,current,cap,demand,gen,mw',[
    (None,None,None,20.,20.,0),(None,None,None,20.,30.,10),
    (G,None,20.,20.,20.,0),(G,None,19.,20.,20.,0),(None,G,None,0.,0.,0),
    (G,G,None,0.,0.,0),(B,B,None,20.,20.,0)])
def test_ordinary_transition_matches_old_model_and_residual(incoming,current,cap,demand,gen,mw):
    oldf=prior.frame(demand=demand,normal=20.);oldb=prior.origin(oldf,incoming)
    f=m._owned(m.NormalFrame,**vars(oldf));b=origin(f,incoming,chronology=False)
    d=action(f,b,current,cap);p=power(mw=mw);op=prior.power(mw=mw)
    oldkey=prior.m.development_step_identity(oldf,d.step,oldb,op,lane=prior.R)
    key=m.development_step_identity(f,d,b,p,lane=R)
    om=prior.m.build_development_model(oldf,d.step,oldb,op,lane=prior.R,expected_identity=oldkey)
    nm=m.build_development_model(f,d,b,p,lane=R,expected_identity=key)
    assert prior.signature(om)==prior.signature(nm)
    oldw=prior.run(oldf,oldb,generation=gen,mw=mw,active=current,cap=cap)
    neww=run(f,b,generation=gen,mw=mw,active=current,cap=cap)
    for field in ('physical_assignment_valid','maximum_exact_violation','maximum_constraint_violation','errors'):
        assert getattr(oldw,field)==getattr(neww,field)
    if oldw.next_carry:
        assert oldw.next_carry.generation_mw==neww.next_carry.generation_mw
