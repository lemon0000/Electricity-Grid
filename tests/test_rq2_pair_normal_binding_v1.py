from dataclasses import replace
from types import SimpleNamespace
from copy import deepcopy

import pytest

from src.rq2_joint_deliverability_boundary_v1 import pair_normal_binding as binding
from tests.test_rq2_continuous_grid_normal_v1 import fixture
from tests.test_rq2_source_pair_v1 import declaration


@pytest.fixture
def supplied(monkeypatch):
    inputs=fixture(3)
    inputs=replace(inputs,request=replace(inputs.request,dc_requested_mw=(10.,20.,30.),
        dc_physical_maximum_mw=(250.,)*3,dc_connected_capacity_mw=(250.,)*3))
    assembly=SimpleNamespace(inputs=inputs)
    pair={'pair_identity':'a'*64,'status':'staged','mapping':{'normalized_unit_mw':'250'},
        'hours':[{'power_source_hour':i+1,'workload_source_hour':i+1,'workload_occupancy':x}
                 for i,x in enumerate((.04,.08,.12))],
        'rows':[{'workload_projection':{'dc_baseline_mw':x}} for x in (10.,20.,30.)]}
    monkeypatch.setattr(binding.source_pair,'prepare_source_pair',lambda *args,**kw:deepcopy(pair))
    power={'normal_assembly_identity':'b'*64,'normal_input_identity':'c'*64}
    monkeypatch.setattr(binding.power_normal_binding,'bind_power_normal',lambda *args,**kw:deepcopy(power))
    return assembly,pair


def call(assembly,**changes):
    args=dict(expected_assembly_identity='b'*64,expected_pair_identity='a'*64)
    args.update(changes)
    return binding.bind_pair_normal(assembly,'unused',declaration(),**args)


def test_dynamic_baseline_and_no_model_certification(supplied):
    report=call(supplied[0])
    assert report['dc_baseline_mw']==[10.,20.,30.]
    assert report['dynamic_baseline_correspondence_verified']
    assert all(report[k] is False for k in ('normal_assignment_verified','initial_network_feasibility_verified',
        'registered_coupling','observed_power_mapping','formal_result'))
    assert report['solver_calls']==0


@pytest.mark.parametrize('baseline',[(250.,)*3,(10.,20.,30.000001),(10.,20.)])
def test_wrong_or_old_constant_baseline_rejected(supplied,baseline):
    assembly,_=supplied
    assembly.inputs=replace(assembly.inputs,request=replace(assembly.inputs.request,
        dc_requested_mw=baseline)) if len(baseline)==3 else SimpleNamespace(
            request=SimpleNamespace(dc_requested_mw=baseline),source_hours=(1,2,3))
    with pytest.raises(ValueError,match='baseline'): call(assembly)


def test_unresolved_pair_rejected_before_network_source(supplied,monkeypatch):
    assembly,pair=supplied
    pair['status']='unresolved';pair['hours']=None
    def forbidden(*args,**kw): raise AssertionError('must not bind incomplete pair')
    monkeypatch.setattr(binding.power_normal_binding,'bind_power_normal',forbidden)
    with pytest.raises(ValueError,match='unresolved hours'): call(assembly)


def test_external_pair_pin(supplied):
    with pytest.raises(ValueError,match='pair identity'): call(supplied[0],expected_pair_identity='d'*64)


def test_power_hour_shift(supplied):
    supplied[1]['hours'][0]['power_source_hour']=2
    with pytest.raises(ValueError,match='baseline'): call(supplied[0])


def test_occupancy_power_identity_not_just_float_baseline(supplied):
    supplied[1]['hours'][0]['workload_occupancy']=.05
    with pytest.raises(ValueError,match='exact paired'): call(supplied[0])


def test_snapshot_isolated_from_caller_mutation_during_source_check(supplied,monkeypatch):
    assembly,_=supplied
    def source_check(snapshot,*args,**kw):
        assembly.inputs.request.initial_generation_mw['G1']=99.
        assert snapshot.inputs.request.initial_generation_mw['G1']==20.
        return {'normal_assembly_identity':'b'*64,'normal_input_identity':'c'*64}
    monkeypatch.setattr(binding.power_normal_binding,'bind_power_normal',source_check)
    assert call(assembly)['dc_baseline_mw']==[10.,20.,30.]


@pytest.mark.parametrize('mode,pin',[('verify',None),('derive','a'*64)])
def test_runner_separates_derivation_from_external_pin_verification(monkeypatch,tmp_path,mode,pin):
    import sys
    from experiments import audit_rq2_pair_normal_build_v1 as runner
    args=['runner','--mode',mode,'--normal-declaration',str(tmp_path/'absent.json'),
        '--expected-normal-declaration-sha256','a'*64,'--pair-declaration',str(tmp_path/'absent.yaml'),
        '--expected-pair-declaration-sha256','b'*64,'--expected-pair-identity','c'*64,
        '--source-root','unused','--output',str(tmp_path/'example_non_authoritative.json')]
    if pin is not None:args+=['--expected-assembly-identity',pin]
    monkeypatch.setattr(sys,'argv',args)
    with pytest.raises(SystemExit) as error:runner.main()
    assert error.value.code==2
    assert not (tmp_path/'example_non_authoritative.json').exists()
