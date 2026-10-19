from copy import deepcopy
from dataclasses import replace
import json

import pytest

from src.rq2_joint_deliverability_boundary_v1 import pair_normal_stream as api
from tests.test_rq2_source_normal_v1 import supplied as source_supplied
from tests.test_rq2_source_pair_v1 import declaration


@pytest.fixture
def supplied(source_supplied, monkeypatch):
    root, inputs = source_supplied
    inputs = replace(inputs, request=replace(inputs.request, dc_requested_mw=(10.,20.,30.),
        dc_physical_maximum_mw=(250.,)*3, dc_connected_capacity_mw=(250.,)*3))
    args = (root, (0,1,2), inputs.request, inputs.initial, inputs.carry)
    old = api.source.legacy.assemble_source_normal(*args, source_time_basis=inputs.source_time_basis)
    new = api.source.assemble_source_normal(*args, source_time_basis=inputs.source_time_basis,
        expected_implementation_identity=api.source.implementation_identity())
    identity = inputs.carry.identity
    window = dict(kind='power', split=identity.split, outage_seed=identity.outage_seed,
        chain={'chain_id':identity.trajectory_id}, continuous_power_source_hours=[1,2,3],
        window_identity=declaration().power_window_identity, package_manifest_sha256='d'*64,
        rows=[dict(source_hour=str(i), timestamp=t.isoformat(), system_load_mw='20')
            for i,t in enumerate(inputs.request.timestamps)])
    pair = dict(pair_identity='e'*64, status='staged', mapping={'normalized_unit_mw':'250'},
        hours=[dict(power_source_hour=i+1,workload_source_hour=i+1,workload_occupancy=x)
            for i,x in enumerate((.04,.08,.12))],
        rows=[{'workload_projection':{'dc_baseline_mw':x}} for x in (10.,20.,30.)])
    monkeypatch.setattr(api.source_pair,'prepare_source_pair',lambda *a,**k:deepcopy(pair))
    monkeypatch.setattr(api.source_window,'load_source_window',lambda *a,**k:deepcopy(window))
    monkeypatch.setattr(api.source_window.audit,'_load_config',lambda *a:{'inputs':{'power':{}}})
    monkeypatch.setattr(api.source_window.audit,'_verify_package',lambda *a:(None,
        {'grid_source_manifest_sha256':new.source_manifest_sha256}))
    monkeypatch.setattr(api.source_window.audit,'_verify_hash',lambda *a:None)
    return root, old, new, pair, window


def call(supplied, **changes):
    root, _, new, pair, _ = supplied
    args = dict(expected_assembly_identity=new.assembly_identity,
        expected_pair_identity=pair['pair_identity'], expected_source_implementation_identity=api.source.implementation_identity(),
        expected_implementation_identity=api.implementation_identity())
    args.update(changes)
    return api.bind_pair_normal(new, root, declaration(), **args)


def test_legacy_reference_equal_but_new_binding_separate(supplied):
    root, old, new, pair, _ = supplied
    legacy = api.old_pair.bind_pair_normal(old, root, declaration(),
        expected_assembly_identity=old.assembly_identity,expected_pair_identity=pair['pair_identity'])
    result = call(supplied)
    assert json.loads(result.legacy_content_json) == legacy
    assert result.legacy_content_binding_identity == legacy['binding_identity']
    assert result.binding_identity != legacy['binding_identity']
    assert result.source_assembly_identity == new.assembly_identity
    assert result.normal_identity == old.normal_identity
    assert legacy['solver_calls'] == 0 and legacy['formal_result'] is False


@pytest.mark.parametrize('pin', ['expected_assembly_identity','expected_pair_identity',
    'expected_source_implementation_identity','expected_implementation_identity'])
def test_external_pin_mismatch(supplied,pin):
    with pytest.raises(ValueError): call(supplied, **{pin:'0'*64})


def test_no_legacy_input_hash_or_binding_path(supplied,monkeypatch):
    def forbidden(*a,**k): raise AssertionError('legacy full-input path reached')
    monkeypatch.setattr(api.old_pair,'bind_pair_normal',forbidden)
    monkeypatch.setattr(api.old_power,'bind_power_normal',forbidden)
    monkeypatch.setattr(api.source.legacy,'validate_source_assembly',forbidden)
    monkeypatch.setattr(api.source.legacy,'normal_input_identity',forbidden)
    monkeypatch.setattr(api.source.stream.legacy,'normal_input_identity',forbidden)
    assert call(supplied).binding_identity


@pytest.mark.parametrize('fault',['unresolved','baseline','occupancy','power_hour','window_id',
    'split','seed','trajectory','raw','continuous','clock','load','nan','manifest'])
def test_correspondence_rejects_faults(supplied,monkeypatch,fault):
    _,_,_,pair,window=supplied
    if fault=='unresolved': pair.update(status='unresolved',hours=None)
    elif fault=='baseline': pair['rows'][0]['workload_projection']['dc_baseline_mw']=11.
    elif fault=='occupancy': pair['hours'][0]['workload_occupancy']=.05
    elif fault=='power_hour': pair['hours'][0]['power_source_hour']=2
    elif fault=='window_id': window['window_identity']='0'*64
    elif fault=='split': window['split']='holdout'
    elif fault=='seed': window['outage_seed']+=1
    elif fault=='trajectory': window['chain']['chain_id']='foreign'
    elif fault=='raw': window['rows'][0]['source_hour']='1'
    elif fault=='continuous': window['continuous_power_source_hours']=[0,1,2]
    elif fault=='clock': window['rows'][0]['timestamp']=window['rows'][1]['timestamp']
    elif fault=='load': window['rows'][0]['system_load_mw']='21'
    elif fault=='nan': window['rows'][0]['system_load_mw']='NaN'
    elif fault=='manifest': monkeypatch.setattr(api.source_window.audit,'_verify_package',
        lambda *a:(None,{'grid_source_manifest_sha256':'0'*64}))
    if fault=='unresolved':
        monkeypatch.setattr(api.source,'validate_source_assembly',lambda *a,**k:
            pytest.fail('unresolved pair reached source load'))
    with pytest.raises(ValueError): call(supplied)


def test_owned_rebuild_survives_caller_mutation(supplied,monkeypatch):
    original = api._legacy_power_content
    def mutate(rebuilt, **kwargs):
        supplied[2].inputs.request.initial_generation_mw['G1']=99.
        assert rebuilt.inputs.request.initial_generation_mw['G1']==20.
        return original(rebuilt,**kwargs)
    monkeypatch.setattr(api,'_legacy_power_content',mutate)
    assert json.loads(call(supplied).legacy_content_json)['dc_baseline_mw']==[10.,20.,30.]


def test_legacy_type_rejected(supplied):
    root,old,_,pair,window=supplied
    with pytest.raises(ValueError,match='typed streaming'):
        call((root,old,old,pair,window))


def test_implementation_change_during_check(supplied,monkeypatch):
    original = api._legacy_power_content
    def changed(*args,**kwargs):
        result=original(*args,**kwargs)
        monkeypatch.setattr(api,'implementation_identity',lambda:'0'*64)
        return result
    monkeypatch.setattr(api,'_legacy_power_content',changed)
    with pytest.raises(ValueError,match='implementation drift'): call(supplied)
