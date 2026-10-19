import ast
from dataclasses import replace
from hashlib import sha256
import inspect
import json

import pytest

from experiments import h1_origin_selector_replay_development_v1 as m
from tests import test_h1_selector_replay_development_v1 as old

R=m.physical.Lane('Rref',None)
A=m.physical.Lane('A','joint_correct_shared')
LIMITS=m.ReplayLimits(**vars(old.LIMITS))


def inputs(lane=R,chronology=True):
    oldf,oldd,oldb,oldargs=old.inputs(old.R if lane.role=='Rref' else old.A)
    f=m.physical._owned(m.physical.NormalFrame,**vars(oldf))
    selector=old.REF if lane.role=='Rref' else old.ACT
    b=m.initialize_development_selection(f,oldd.before,lane=lane,selector=selector,
        specification=old.SPEC,limits=LIMITS,chronology_origin=chronology)
    d=m.physical.registry.FirstAction(0,oldd.before) if chronology else m.physical.registry.TransitionAction(0,oldd)
    p=None if lane.role=='Rref' else m.physical.RelativeDcPower(**vars(oldargs['power']))
    return f,d,b,dict(lane=lane,selector=selector,specification=old.SPEC,limits=LIMITS,power=p)


def records(monkeypatch,lane=R,chronology=True,fault=None):
    f,d,b,args=inputs(lane,chronology)
    if fault in ('strict_lock','l1_slack'):
        args['specification']=replace(old.SPEC,feasibility_tolerance=1e-6)
        b=m.initialize_development_selection(f,b.physical_carry.disclosure,lane=lane,
            selector=args['selector'],specification=args['specification'],limits=LIMITS,chronology_origin=chronology)
    calls=old.install(monkeypatch,old.R if lane.role=='Rref' else old.A,fault)
    key=m.input_identity(f,d,b,lane=lane,power=args['power']);frozen=();saved=[]
    for i,label in enumerate(m.stage_labels(f,lane)):
        builder=lambda:m.build_development_stage(f,d,b,lane=lane,power=args['power'],index=i,frozen=frozen,expected_identity=key)
        raw=m.native.capture._solve(builder,args['specification'],old.BUDGET,f'{m.SCHEMA}:{lane.role}:{i}:{label}')
        saved.append(m.encode_development_record(f,d,b,raw,index=i,frozen=frozen,**args))
        if not raw.optimal or fault and i==1:break
        frozen+=(raw.objective,)
    return f,d,b,args,tuple(saved),calls


def replay(bundle,saved=None):
    f,d,b,args,original,_=bundle
    saved=original if saved is None else saved
    return m.replay_development_records(f,d,b,saved,**args,
        expected_identity=m.input_identity(f,d,b,lane=args['lane'],power=args['power']),
        expected_policy_identity=b.policy_identity,expected_report_sha256=tuple(sha256(r).hexdigest() for r in saved))


@pytest.mark.parametrize('lane',[R,A])
def test_first_action_complete_canonical_replay_without_solver(monkeypatch,lane):
    bundle=records(monkeypatch,lane)
    def denied(*args,**kwargs):raise AssertionError('replay entered solver')
    monkeypatch.setattr(m.native.capture,'_solve',denied)
    monkeypatch.setattr(m.native.capture,'create_solver',denied)
    out=replay(bundle)
    assert out.status=='replayed_numerical_candidate',out.errors
    assert out.verified_stages==(3 if lane==R else 2)
    assert out.canonical_lock_hex==tuple(float(x).hex() for x in ((15,15,30) if lane==R else (20,25)))
    assert out.next_candidate.physical_carry.completed_hours==1
    assert out.next_candidate.physical_carry.disclosure.source_hour==0
    assert out.next_candidate.previous_selection_identity==bundle[2].identity
    assert out.next_candidate.previous_audit_identity==bundle[2].audit_identity
    assert replay(bundle,bundle[4][:1]).next_candidate is None
    for key in ('native_execution_authenticated','source_input_binding_verified','normal_selection_authenticated',
                'detached_consumer_authenticated','common_publication_verified','reference_or_actual_ready','formal_result'):
        assert not getattr(out,key)


def test_same_science_different_source_clock_cannot_splice_saved_envelope(monkeypatch):
    first=records(monkeypatch)
    ordinary=records(monkeypatch,chronology=False)
    fa,da,ba,argsa,_,_=first;fb,db,bb,argsb,_,_=ordinary
    assert ba.identity==bb.identity and ba.audit_identity!=bb.audit_identity
    assert m.input_identity(fa,da,ba,lane=R)==m.input_identity(fb,db,bb,lane=R)
    a,b=replay(first),replay(ordinary)
    assert a.status==b.status=='replayed_numerical_candidate'
    assert a.next_candidate.identity==b.next_candidate.identity
    assert a.next_candidate.audit_identity!=b.next_candidate.audit_identity
    with pytest.raises(ValueError,match='forbidden suffix'):
        replay(ordinary,first[4])
    bad=replay(ordinary,first[4][:1])
    assert bad.status=='unresolved' and bad.next_candidate is None and bad.verified_stages==0


@pytest.mark.parametrize('field',['action_audit_identity','predecessor_audit_identity'])
def test_rehashed_audit_identity_substitution_rejected(monkeypatch,field):
    bundle=records(monkeypatch);saved=list(bundle[4]);body=json.loads(saved[1]);body[field]='0'*64
    saved[1]=m.native._encoded(body)
    out=replay(bundle,tuple(saved[:2]))
    assert out.status=='unresolved' and out.next_candidate is None and out.verified_stages==1


@pytest.mark.parametrize('fault',['timeout','gap','strict_lock','l1_slack'])
def test_failed_stage_retains_old_numeric_gates_and_forbids_suffix(monkeypatch,fault):
    bundle=records(monkeypatch,fault=fault);out=replay(bundle)
    assert out.status=='unresolved' and out.next_candidate is None and out.verified_stages==1
    assert out.infeasibility_certificate is None
    with pytest.raises(ValueError,match='forbidden suffix'):replay(bundle,bundle[4]+bundle[4][-1:])


def test_selector_mathematical_stages_and_exact_stage_audits_unchanged():
    for name in ('_base','build_development_stage','_reference_audit_stage','_actual_audit_stage'):
        assert ast.dump(ast.parse(inspect.getsource(getattr(m,name))))==ast.dump(ast.parse(inspect.getsource(getattr(old.m,name))))
    f,d,b,args=inputs()
    assert m.stage_labels(f,R)==('grid_request','l1_normal_deviation','generation:G1')
    assert m.stage_labels(f,A)==('l1_normal_deviation','generation:G1')
