from dataclasses import replace
from pathlib import Path

import pytest
from pyomo.environ import Constraint, Objective, Var, value
from pyomo.repn import generate_standard_repn

from src.rq2_joint_deliverability_boundary_v1 import continuous_grid_normal_stream_fast as api
from tests.test_rq2_continuous_grid_normal_v1 import fixture, assignment_for, model_for


def build(inputs, **changes):
    args=dict(expected_identity=api.normal_input_identity(inputs),
        expected_implementation_identity=api.implementation_identity())
    args.update(changes)
    return api.build_continuous_normal_model(inputs, **args)


def audit(inputs, assignment):
    return api.audit_normal_assignment(inputs,assignment,expected_identity=api.normal_input_identity(inputs),
        expected_implementation_identity=api.implementation_identity())


def signature(model):
    def expression(expr):
        rep=generate_standard_repn(expr,compute_values=True)
        assert rep.nonlinear_expr is None and not rep.quadratic_vars
        return rep.constant,tuple(sorted((v.name,c) for v,c in zip(rep.linear_vars,rep.linear_coefs)))
    return (tuple((v.name,str(v.domain),value(v.lb),value(v.ub),v.fixed) for v in model.component_data_objects(Var)),
        tuple((c.name,c.active,value(c.lower),expression(c.body),value(c.upper))
            for c in model.component_data_objects(Constraint,active=None)),
        tuple((o.name,o.active,int(o.sense),expression(o.expr)) for o in model.component_data_objects(Objective,active=None)))


@pytest.mark.parametrize('horizon',[1,25,49])
@pytest.mark.parametrize('committed,minimum,age',[(True,3.,1),(False,3.,0),(True,2.2,2),(False,2.2,3)])
def test_full_model_matrix_matches_legacy(horizon,committed,minimum,age):
    inputs=fixture(horizon,committed=committed,minimum=minimum,age=age)
    old,new=model_for(inputs),build(inputs)
    assert signature(new)==signature(old)


@pytest.mark.parametrize('fault',['none','power','flow','integrality','reserve','missing'])
def test_witness_matches_legacy(fault):
    inputs=fixture(25); assignment=assignment_for(inputs)
    if fault=='power': assignment['generation[normal,1,G1]']=21.
    elif fault=='flow': assignment['branch_flow[normal,1,AC1]']=101.
    elif fault=='integrality': assignment['commitment[1,G1]']=.5
    elif fault=='reserve': assignment['reserve_up[1,G1]']=81.
    elif fault=='missing': assignment.pop(next(iter(assignment)))
    if fault=='missing':
        with pytest.raises(ValueError): audit(inputs,assignment)
    else:
        old=api.legacy.audit_normal_assignment(inputs,assignment,expected_identity=api.legacy.normal_input_identity(inputs))
        assert audit(inputs,assignment)==old


def test_no_legacy_full_tree_input_call(monkeypatch):
    inputs=fixture(2); assignment=assignment_for(inputs)
    def forbidden(*a,**k): raise AssertionError('legacy model/input path reached')
    for name in ('normal_input_identity','build_continuous_normal_model','audit_normal_assignment','_digest'):
        monkeypatch.setattr(api.legacy,name,forbidden)
    assert audit(inputs,assignment).errors==()


@pytest.mark.parametrize('field',['expected_identity','expected_implementation_identity'])
def test_external_pin_rejected_before_build(monkeypatch,field):
    inputs=fixture(2)
    monkeypatch.setattr(api.scuc,'_build_model',lambda *a:pytest.fail('model built before external pin check'))
    with pytest.raises(ValueError): build(inputs,**{field:'0'*64})


def test_build_implementation_change_rejected(monkeypatch):
    inputs=fixture(2); original=api.scuc._build_model
    def changed(*a):
        model=original(*a)
        monkeypatch.setattr(api,'implementation_identity',lambda:'0'*64)
        return model
    monkeypatch.setattr(api.scuc,'_build_model',changed)
    with pytest.raises(ValueError,match='implementation drift'): build(inputs)


def test_old_input_pin_detects_mutation():
    inputs=fixture(2); pin=api.normal_input_identity(inputs)
    inputs.initial.generation_mw['G1']=21.
    with pytest.raises(ValueError): build(inputs,expected_identity=pin)


def test_prior_stream_implementation_cannot_authorize_fast_model():
    from src.rq2_joint_deliverability_boundary_v1 import continuous_grid_normal_stream as prior
    with pytest.raises(ValueError, match='implementation drift'):
        build(fixture(2), expected_implementation_identity=prior.implementation_identity())
