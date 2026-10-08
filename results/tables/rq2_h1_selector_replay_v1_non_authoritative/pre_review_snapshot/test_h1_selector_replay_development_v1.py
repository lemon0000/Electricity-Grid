from dataclasses import replace
from fractions import Fraction as Q
from hashlib import sha256
import json

import pytest
from pyomo.environ import Var, value
from pyomo.opt import SolverResults, SolverStatus, SolutionStatus, TerminationCondition
from pyomo.opt.results.problem import ProblemSense

from experiments import h1_selector_replay_development_v1 as m
from tests.test_h1_current_grid_step_development_v1 import R, A, frame, origin, power, parity_objects, signature
from tests.test_rq2_normal_h1_source_v1 import packet
from tests.test_rq2_normal_h1_hour_archive_v1 import no_solver
from tests.test_rq2_continuous_grid_candidate_v1 import SPEC,BUDGET
from tests import test_rq2_current_grid_step_v1 as old_physics
from tests import test_rq2_reference_selector_v1 as old_ref
from tests import test_rq2_actual_dispatch_selector_v1 as old_actual

LIMITS=m.ReplayLimits(300,1000,2000,1024**2,16*1024**2)
REF=m.reference.ReferenceSelectorSpec('request_l1_normal_deviation_generation_uid_order',1e-7,1e-8,1e-9,'mechanism_assumption')
ACT=m.actual.ActualDispatchSpec('l1_normal_deviation_generation_uid_order',1e-7,1e-8,1e-9,'mechanism_assumption')


def inputs(lane=R):
    p=packet(raw_workload='0.1')
    after=m.physical.information.source._owned(type(p.before),network_identity=p.network.identity,completed_hours=1,
        units=(('G1',True,45.,1),),evidence_role='numerical_lex_candidate')
    f=m.physical._frame(p,after)
    selector=REF if lane==R else ACT
    initial=origin(f,lane=lane)
    b=m.initialize_development_selection(f,initial.disclosure,lane=lane,selector=selector,specification=SPEC,limits=LIMITS)
    d=m.physical.events.disclose_current(b.physical_carry.disclosure,m.physical.events.CurrentOutageReport(1,None,None))
    return f,d,b,dict(lane=lane,selector=selector,specification=SPEC,limits=LIMITS,power=None if lane==R else power(mw=5))


def install(monkeypatch,lane,fault=None,fail_index=1):
    """Fabricated solver-shaped records test consistency, never optimality."""
    calls=[]
    def create(spec):
        class Fake:
            def solve(self,model,**kwargs):
                i=len(calls);calls.append(i)
                vals={v.name:0. for v in model.component_data_objects(Var)}
                vals.update({'generation[G1]':30. if lane==R else 25.,'selector_deviation[G1]':15. if lane==R else 20.})
                if lane==R:vals['reference_power']=10.
                active=fault if i==fail_index else None
                if active=='strict_lock':
                    vals['generation[G1]']-=5e-7
                    vals['reference_power']-=5e-7
                    vals['selector_deviation[G1]']+=5e-7
                if active=='l1_slack':vals['selector_deviation[G1]']+=5e-7
                clone=model.clone()
                for name,x in vals.items():clone.find_component(name).set_value(x,skip_validation=True)
                objective=float(value(clone.objective))
                out=SolverResults();out.solver.status=SolverStatus.ok;out.solver.termination_condition=TerminationCondition.optimal
                out.problem.sense=ProblemSense.minimize;out.problem.number_of_objectives=1
                out.problem.lower_bound=out.problem.upper_bound=objective
                s=out.solution.add();s._cuid=False;s.status=SolutionStatus.optimal
                s.variable.update({k:{'Value':v} for k,v in vals.items()});s.objective['objective']={'Value':objective}
                if active=='timeout':out.solver.termination_condition=TerminationCondition.maxTimeLimit;s.status=SolutionStatus.feasible
                if active=='infeasible':out.solver.termination_condition=TerminationCondition.infeasible;out.solution.clear()
                if active=='gap':out.problem.lower_bound=objective-5e-7
                return out
        return Fake(),m.native.capture.solver_options(spec)
    monkeypatch.setattr(m.native.capture,'create_solver',create)
    return calls


def records(monkeypatch,lane=R,fault=None):
    f,d,b,args=inputs(lane);calls=install(monkeypatch,lane,fault)
    key=m.input_identity(f,d,b,lane=lane,power=args['power']);frozen=();saved=[]
    for i,label in enumerate(m.stage_labels(f,lane)):
        builder=lambda:m.build_development_stage(f,d,b,lane=lane,power=args['power'],index=i,frozen=frozen,expected_identity=key)
        raw=m.native.capture._solve(builder,SPEC,BUDGET,f'{m.SCHEMA}:{lane.role}:{i}:{label}')
        saved.append(m.encode_development_record(f,d,b,raw,index=i,frozen=frozen,**args))
        if not raw.optimal or fault and i==1:break
        frozen+=(raw.objective,)
    def denied(*a,**k):raise AssertionError('replay entered a solver')
    monkeypatch.setattr(m.native.capture,'_solve',denied);monkeypatch.setattr(m.native.capture,'create_solver',denied)
    return f,d,b,args,tuple(saved),calls


def replay(bundle,saved=None,**changes):
    f,d,b,args,raw,_=bundle
    saved=raw if saved is None else saved
    kw=dict(args,expected_identity=m.input_identity(f,d,b,lane=args['lane'],power=args['power']),
        expected_policy_identity=b.policy_identity,expected_report_sha256=tuple(sha256(x).hexdigest() for x in saved))
    kw.update(changes)
    return m.replay_development_records(f,d,b,saved,**kw)


@pytest.mark.parametrize('lane',[R,A])
def test_complete_saved_chain_without_solver(monkeypatch,lane):
    bundle=records(monkeypatch,lane);out=replay(bundle)
    assert out.status=='replayed_numerical_candidate',out.errors
    assert out.verified_stages==len(bundle[-1])==(3 if lane==R else 2)
    assert out.canonical_lock_hex==tuple(float(x).hex() for x in ((15,15,30) if lane==R else (20,25)))
    assert out.candidate_request_exact==(('15','1') if lane==R else None)
    assert out.next_candidate.physical_carry.completed_hours==1
    assert out.next_candidate.previous_selection_identity==bundle[2].identity
    assert out.solver_calls_by_replay==0
    for field in ('native_execution_authenticated','source_input_binding_verified','normal_selection_authenticated',
                  'detached_consumer_authenticated','common_publication_verified','reference_or_actual_ready','formal_result','security_certified'):
        assert not getattr(out,field)


@pytest.mark.parametrize('field',['index','label','purpose','input_identity','policy_identity','implementation_identity',
    'lane','power','specification','limits','model_structure_identity','frozen','frozen_hex','canonical_objective_hex','raw_objective'])
def test_rehashed_stage_context_and_objective_tampering(monkeypatch,field):
    bundle=records(monkeypatch);saved=list(bundle[4]);body=json.loads(saved[1])
    if field=='raw_objective':body['raw']['objective']+=1.
    elif field in ('index',):body[field]=0
    elif field in ('frozen','frozen_hex'):body[field]=[]
    elif field in ('lane','power','specification','limits'):body[field]={}
    else:body[field]='changed'
    saved[1]=m.native._encoded(body)
    out=replay(bundle,tuple(saved))
    assert out.status=='unresolved' and out.next_candidate is None and out.verified_stages==1


def test_topology_and_external_pins(monkeypatch):
    bundle=records(monkeypatch);rows=bundle[4]
    assert replay(bundle,rows[:1]).next_candidate is None
    assert replay(bundle,()).status=='unresolved'
    assert replay(bundle,tuple(reversed(rows))).verified_stages==0
    with pytest.raises(ValueError):replay(bundle,rows+rows[:1])
    with pytest.raises(ValueError):replay(bundle,expected_report_sha256=('0'*64,)*3)
    with pytest.raises(ValueError):replay(bundle,expected_policy_identity='1'*64)
    with pytest.raises(ValueError):replay(bundle,expected_identity='1'*64)


@pytest.mark.parametrize('fault',['timeout','infeasible','gap','strict_lock','l1_slack'])
def test_failed_stage_never_returns_prefix_candidate(monkeypatch,fault):
    bundle=records(monkeypatch,fault=fault);out=replay(bundle)
    assert len(bundle[-1])==2
    assert out.status=='unresolved' and out.next_candidate is None and out.candidate_request_exact is None
    assert out.verified_stages==1
    assert out.infeasibility_certificate is None


def test_wrong_actual_lane_power_and_policy(monkeypatch):
    bundle=records(monkeypatch,A)
    with pytest.raises(ValueError):replay(bundle,lane=m.physical.Lane('A','network_only_shared'))
    with pytest.raises(ValueError):replay(bundle,power=power(mw=6))
    with pytest.raises(ValueError):replay(bundle,selector=REF)
    with pytest.raises(ValueError):replay(bundle,limits=replace(LIMITS,max_stages=1))


def test_reference_request_uses_decimal_rational_difference():
    f,d,b,args=inputs()
    v={'generation[G1]':20.1,'angle_degrees[1]':0.,'angle_degrees[2]':0.,'branch_flow[AC1]':0.,'dc_flow[DC1]':0.,'reference_power':.1}
    w=m._reference_assignment(f,d,b,v)
    assert w.physical_assignment_valid
    assert w.candidate_grid_request_exact==('249','10')


@pytest.mark.parametrize('lane',[R,A])
def test_all_stage_linear_algebra_matches_old_selector(lane):
    info=old_physics.view(old_physics.prepared(),old_physics.current(demand=20.))
    prev=old_physics.origin(info);f,c=parity_objects(info,prev)
    selector=REF if lane==R else ACT
    if lane!=R:
        c=m.physical._owned(type(c),**{k:(lane if k=='lane' else getattr(c,k)) for k in c.__dataclass_fields__})
    b=m._owned(m.SelectionCandidate,physical_carry=c,policy_identity=m.policy_identity(lane,selector,SPEC,LIMITS),
        previous_selection_identity=None,selection_identity=None)
    d=m.physical.events.disclose_current(prev.disclosure,m.physical.events.CurrentOutageReport(1,None,None))
    p=None if lane==R else power(mw=5)
    if lane==R:
        old=m.old_reference.initialize_reference_origin(info,prev.disclosure,
            reference_protocol=m.old_reference.ReferenceProtocol('common_baseline_no_cfe_no_recovery_assumed_prior_reference_fulfilment',
                'all_current_hours_mechanism','mechanism_assumption'),grid_protocol=prev.protocol,
            generation_mw=prev.generation_mw,base_availability=prev.base_availability)
    else:old=old_actual.wrap(info,prev)
    for i,label in enumerate(m.stage_labels(f,lane)):
        frozen=(0.,)*i
        new=m.build_development_stage(f,d,b,lane=lane,power=p,index=i,frozen=frozen,
            expected_identity=m.input_identity(f,d,b,lane=lane,power=p))
        legacy=(m.reference._stage_model(info,d,old,m.old_reference.reference_input_identity(info,d,old),i,frozen) if lane==R
            else m.actual._stage_model(info,d,old,old_physics.power(mw=5),i,frozen))
        assert signature(new)==signature(legacy)


def test_mid_replay_identity_drift_raises(monkeypatch):
    bundle=records(monkeypatch);original=m._reference_assignment
    def changed(*a,**kw):
        out=original(*a,**kw);monkeypatch.setattr(m,'SCHEMA','changed');return out
    monkeypatch.setattr(m,'_reference_assignment',changed)
    with pytest.raises(ValueError,match='drift'):replay(bundle)


def test_stage_index_lock_shape_and_sha_types():
    f,d,b,args=inputs();key=m.input_identity(f,d,b,lane=R)
    for index,frozen in ((True,()),(-1,()),(3,()),(1,()),(1,(float('nan'),)),(1,(-1.,))):
        with pytest.raises(ValueError):m.build_development_stage(f,d,b,lane=R,index=index,frozen=frozen,expected_identity=key)
    with pytest.raises(ValueError):m.build_development_stage(f,d,b,lane=R,index=0,frozen=(),expected_identity=True)
