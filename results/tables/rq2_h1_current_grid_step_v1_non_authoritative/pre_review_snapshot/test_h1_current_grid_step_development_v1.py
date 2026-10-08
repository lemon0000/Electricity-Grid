from copy import copy, deepcopy
from dataclasses import replace
from fractions import Fraction
import ast
import inspect
import pickle

import pytest
from pyomo.environ import Constraint, Objective, Var, value
from pyomo.repn import generate_standard_repn

from experiments import h1_current_grid_step_development_v1 as m
from tests.test_rq2_normal_h1_source_v1 import packet
from tests.test_rq2_continuous_grid_normal_v1 import fixture
from tests import test_rq2_current_grid_step_v1 as legacy
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver

R = m.Lane('Rref', None)
A = m.Lane('A', 'joint_correct_shared')
G, B = legacy.G, legacy.B


def frame(*, prior=None, demand=20., normal=None, on=True, ramp=10.):
    data = fixture(1).data
    data = replace(data, generators=(replace(data.generators[0], ramp_mw_per_hour=ramp, ramp_mw_per_minute=ramp/60),))
    row = replace(data.hourly_points[0], demand_by_bus_mw={1:demand, 2:0.})
    h = 0 if prior is None else prior.info.relative_hour+1
    p = packet(data, row, relative_hour=h, before=None if prior is None else prior.normal_after)
    old = p.before.units[0]
    age = old[3]+1 if old[1] == on else 1
    after = m.information.source._owned(m.information.source.H1NormalBoundary,
        network_identity=p.network.identity, completed_hours=h+1,
        units=(('G1',on,demand if normal is None else normal,age),), evidence_role='numerical_lex_candidate')
    return m._frame(p,after)


def origin(f, active=None, lane=R):
    protocol = m.events.DisclosureProtocol((B,G),
        'current_n1_outage_overlay_revealed_before_current_action',
        'complete_current_n1_outage_overlay__no_hidden_same_hour_replacement','mechanism_assumption')
    disclosure = m.events.initialize_disclosure(protocol,source_hour=0,active_component=active)
    return m.initialize_development_carry(f,disclosure,lane=lane)


def power(h=0,mw=0):
    q=Fraction(str(mw))
    return m.RelativeDcPower(h,str(q.numerator),str(q.denominator),'mechanism_assumption')


def run(f,b,*,mw=0,generation=20.,active=None,cap=None,changes=None,lane=R):
    d=m.events.disclose_current(b.disclosure,m.events.CurrentOutageReport(f.info.relative_hour+1,active,cap))
    p=power(f.info.relative_hour,mw)
    key=m.development_step_identity(f,d,b,p,lane=lane)
    model=m.build_development_model(f,d,b,p,lane=lane,expected_identity=key)
    values={v.name:0. for v in model.component_data_objects(Var)}
    values['generation[G1]']=generation
    values.update(changes or {})
    return m.audit_development_assignment(f,d,b,p,values,lane=lane,expected_identity=key)


def signature(model):
    def linear(expr):
        rep=generate_standard_repn(expr)
        assert rep.is_linear()
        return (value(rep.constant),tuple(sorted((v.name,float(c)) for v,c in zip(rep.linear_vars,rep.linear_coefs))))
    return (
        tuple((v.name,str(v.domain),v.lb,v.ub,v.fixed,value(v) if v.fixed else None) for v in model.component_data_objects(Var)),
        tuple((c.name,None if c.lower is None else value(c.lower),linear(c.body),None if c.upper is None else value(c.upper)) for c in model.component_data_objects(Constraint)),
        tuple((o.name,o.sense,linear(o.expr)) for o in model.component_data_objects(Objective)))


def parity_objects(info,before):
    """Private algebra-only bridge; old synthetic origin is not an H1 origin."""
    inf=m.information
    view=inf._owned(inf.H1CurrentInformation,contract=inf.SCHEMA,relative_hour=0,network=info.network,
        current=inf._owned(inf.H1CurrentConditions,**{k:getattr(info.current,k) for k in inf.H1CurrentConditions.__dataclass_fields__}),
        normal=inf._owned(inf.H1CurrentNormalView,**{k:getattr(info.normal,k) for k in inf.H1CurrentNormalView.__dataclass_fields__}))
    def nb(hour,com,gen):
        return inf.source._owned(inf.source.H1NormalBoundary,network_identity='a'*64,completed_hours=hour,
            units=tuple((k,on,dict(gen)[k],1) for k,on in com),evidence_role='numerical_lex_candidate')
    f=m._owned(m.NormalFrame,info=view,normal_before=nb(0,view.normal.previous_commitment,before.generation_mw),
        normal_after=nb(1,view.normal.commitment,view.normal.generation_mw))
    b=m._owned(m.PhysicalCandidateCarry,protocol=m.CONTRACT,lane=R,network_identity=m._digest(view.network),
        origin_identity='b'*64,completed_hours=0,normal_boundary_identity=m._digest(f.normal_before),decision_identity=None,
        generation_mw=before.generation_mw,base_availability=before.base_availability,
        effective_availability=before.effective_availability,planned_commitment=before.planned_commitment,
        disclosure=before.disclosure,previous_carry_identity=None,step_input_identity=None)
    return f,b


@pytest.mark.parametrize('ramp,demand,mw,generation,incoming,active,cap,changes',[
    (10.,10.,20.,30.,None,None,None,{}),
    (10.,10.,21.,31.,None,None,None,{}),
    (60.,10.,0.,10.,G,None,10.,{}),
    (60.,10.,0.,10.,G,None,9.,{}),
    (4.,0.,0.,0.,None,G,None,{}),
    (4.,0.,0.,0.,G,G,None,{}),
    (60.,20.,0.,20.,None,B,None,{}),
    (60.,20.,0.,20.,None,None,None,{'angle_degrees[1]':1.}),
    (60.,20.,0.,20.,None,None,None,{'branch_flow[AC1]':101.}),
    (60.,20.,'17.800000000000002',37.799999,None,None,None,{}),
])
def test_complete_algebra_and_audit_equivalence(ramp,demand,mw,generation,incoming,active,cap,changes):
    info=legacy.view(legacy.prepared(ramp),legacy.current(demand=demand))
    before=legacy.origin(info,active=incoming,generation=0. if incoming else 20.)
    f,b=parity_objects(info,before)
    d=m.events.disclose_current(before.disclosure,m.events.CurrentOutageReport(1,active,cap))
    po=legacy.power(mw=mw);pn=power(mw=mw)
    ko=m.old.current_step_identity(info,d,before,po)
    kn=m.development_step_identity(f,d,b,pn,lane=R)
    om=m.old.build_current_grid_model(info,d,before,po,expected_identity=ko)
    nm=m.build_development_model(f,d,b,pn,lane=R,expected_identity=kn)
    assert signature(om)==signature(nm)
    vals={v.name:0. for v in nm.component_data_objects(Var)}
    vals['generation[G1]']=generation;vals.update(changes)
    a=m.old.audit_current_grid_assignment(info,d,before,po,vals,expected_identity=ko)
    z=m.audit_development_assignment(f,d,b,pn,vals,lane=R,expected_identity=kn)
    for k in ('assignment','maximum_fixed_violation','maximum_bound_violation','maximum_constraint_violation',
              'maximum_exact_violation','errors','physical_assignment_valid'):
        assert getattr(a,k)==getattr(z,k)
    if a.next_carry is not None:
        for k in ('generation_mw','base_availability','effective_availability','planned_commitment','disclosure'):
            assert getattr(a.next_carry,k)==getattr(z.next_carry,k)


def test_exact_residual_ast_is_mechanically_unchanged():
    assert ast.dump(ast.parse(inspect.getsource(m._exact_residual)))==ast.dump(ast.parse(inspect.getsource(m.old._exact_residual)))


def test_approved_origin_and_three_hour_own_generation_chain():
    f=frame();b=origin(f)
    assert b.completed_hours==0 and b.generation_mw==(('G1',0.),)
    a=run(f,b,mw=10,generation=30.)
    assert a.physical_assignment_valid
    g=frame(prior=f)
    z=run(g,a.next_carry,mw=10,generation=30.)
    assert z.physical_assignment_valid
    assert z.next_carry.decision_identity!=a.next_carry.decision_identity
    assert z.next_carry.previous_carry_identity==a.next_carry.identity
    h=frame(prior=g,demand=10.)
    bad=run(h,z.next_carry,generation=10.)
    assert not bad.physical_assignment_valid and bad.maximum_exact_violation==10.
    assert bad.next_carry is None and z.next_carry.completed_hours==2
    for k in ('detached_consumer_authenticated','normal_selection_authenticated','common_publication_verified',
              'reference_or_actual_ready','formal_result','security_certified'):
        assert not getattr(a,k)


def test_trip_continuation_repair_and_shutdown():
    f=frame(ramp=4.);b=origin(f)
    w=run(f,b,generation=20.)
    g=frame(prior=f,demand=0.,normal=20.,ramp=4.)
    trip=run(g,w.next_carry,generation=0.,active=G)
    assert trip.physical_assignment_valid
    h=frame(prior=g,demand=0.,normal=20.,ramp=4.)
    stay=run(h,trip.next_carry,generation=0.,active=G)
    assert stay.physical_assignment_valid
    j=frame(prior=h,demand=20.,ramp=4.)
    assert not run(j,stay.next_carry,generation=20.,cap=19.).physical_assignment_valid
    assert run(j,stay.next_carry,generation=20.,cap=20.).physical_assignment_valid
    with pytest.raises(ValueError):run(j,stay.next_carry,generation=20.)
    off=frame(prior=f,demand=0.,on=False,ramp=4.)
    assert run(off,w.next_carry,generation=0.).physical_assignment_valid


@pytest.mark.parametrize('field,change',[('generation',21.),('age',2),('network','c'*64)])
def test_normal_boundary_splice_rejected_even_same_commitment(field,change):
    f=frame();b=run(f,origin(f)).next_carry;g=frame(prior=f)
    nb=g.normal_before
    units=list(nb.units);u=list(units[0]);u[2 if field=='generation' else 3]=change
    if field!='network':units[0]=tuple(u)
    altered=m.information.source._owned(type(nb),network_identity=change if field=='network' else nb.network_identity,
        completed_hours=nb.completed_hours,units=tuple(units),evidence_role=nb.evidence_role)
    broken=m._owned(m.NormalFrame,info=g.info,normal_before=altered,normal_after=g.normal_after)
    with pytest.raises(ValueError,match='normal boundary'):run(broken,b)


def test_cross_lane_and_clock_rejected():
    f=frame();b=origin(f)
    with pytest.raises(ValueError,match='cross-lane'):run(f,b,lane=A)
    a=origin(f,lane=A)
    with pytest.raises(ValueError,match='cross-lane'):run(f,a,lane=m.Lane('A','network_only_shared'))
    assert run(f,a,lane=A).physical_assignment_valid
    with pytest.raises(ValueError):origin(frame(prior=f))
    with pytest.raises(ValueError):m.initialize_development_carry(f,None,lane=R)
    with pytest.raises(ValueError):m.Lane('Rref','hidden_pair')
    with pytest.raises(ValueError):m.events.disclose_current(b.disclosure,m.events.CurrentOutageReport(0,None,None))
    with pytest.raises(ValueError):m.RelativeDcPower(-1,'0','1','mechanism_assumption')


def test_detached_objects_and_old_interface():
    f=frame();b=origin(f)
    for x in (f,b,run(f,b)):
        for clone in (copy,deepcopy,pickle.dumps):
            with pytest.raises(TypeError):clone(x)
    with pytest.raises(TypeError):replace(b,completed_hours=1)
    with pytest.raises(ValueError):m.old._information(f.info)


@pytest.mark.parametrize('change',['missing','extra','nan','identity','tolerance'])
def test_invalid_assignment_or_mid_audit_drift_never_returns_carry(change,monkeypatch):
    f=frame();b=origin(f);d=m.events.disclose_current(b.disclosure,m.events.CurrentOutageReport(1,None,None));p=power()
    key=m.development_step_identity(f,d,b,p,lane=R)
    model=m.build_development_model(f,d,b,p,lane=R,expected_identity=key)
    vals={v.name:0. for v in model.component_data_objects(Var)};vals['generation[G1]']=20.
    if change=='missing':del vals['dc_flow[DC1]']
    elif change=='extra':vals['unknown']=0.
    elif change=='nan':vals['generation[G1]']=float('nan')
    elif change=='identity':key='0'*64
    else:
        original=m._exact_residual
        def mutate(*args):
            out=original(*args);monkeypatch.setattr(m,'TOLERANCE',1e-5);return out
        monkeypatch.setattr(m,'_exact_residual',mutate)
    with pytest.raises(ValueError):m.audit_development_assignment(f,d,b,p,vals,lane=R,expected_identity=key)
