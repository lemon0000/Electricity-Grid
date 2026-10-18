from dataclasses import asdict, replace
from hashlib import sha256
import json
from pathlib import Path

import pytest
import yaml

from src.rq2_joint_deliverability_boundary_v1 import normal_task_inputs_stream as api
from tests.test_rq2_pair_normal_stream_v1 import supplied as bound_source
from tests.test_rq2_source_normal_v1 import supplied as source_supplied
from tests.test_rq2_source_pair_v1 import declaration


def encoded(value):
    return json.dumps(value, default=lambda x:x.isoformat() if hasattr(x,'isoformat') else list(x),
        allow_nan=False).encode()


@pytest.fixture
def supplied(bound_source,tmp_path):
    root,old,new,pair,window=bound_source
    config=tmp_path/'audit.yaml'; config.write_bytes(b'{}\n')
    config_pin=sha256(config.read_bytes()).hexdigest()
    d=replace(declaration(),config_sha256=config_pin)
    pair_path=tmp_path/'pair.yaml'; pair_path.write_text(yaml.safe_dump(asdict(d)),encoding='utf-8')
    pair_pin=sha256(pair_path.read_bytes()).hexdigest()
    binding=api.stream_binding.old_pair.bind_pair_normal(old,root,d,
        expected_assembly_identity=old.assembly_identity,expected_pair_identity=pair['pair_identity'],config_path=config)
    record=dict(status='DRAFT_NONAUTHORITATIVE',mode='verify',external_assembly_identity_verified=True,
        formal_result=False,solver_calls=0,declaration_role='explicit_mechanism_input_not_executable_checkpoint',
        normal_assembly_identity=old.assembly_identity,expected_assembly_identity=old.assembly_identity,
        normal_input_identity=old.normal_identity,pair_identity=pair['pair_identity'],pair_declaration_sha256=pair_pin,
        binding=binding,request=asdict(old.inputs.request),initial=asdict(old.inputs.initial),carry=asdict(old.inputs.carry),
        source_time_basis=old.inputs.source_time_basis,dependencies=[],extra_implementation_sha256={},
        model_builds=1,model_scale=dict(variables=10,constraints=12),normal_assignment_verified=False,
        normal_declaration_sha256='4'*64,original_dc_requested_mw=list(old.inputs.request.dc_requested_mw),runner_sha256='5'*64)
    normal=tmp_path/'normal.json'; normal.write_bytes(encoded(record))
    request=api.legacy.NormalTaskSourceRequest(str(normal),sha256(normal.read_bytes()).hexdigest(),
        str(pair_path),pair_pin,str(root),str(config),config_pin,old.assembly_identity,old.normal_identity,
        pair['pair_identity'],binding['binding_identity'],api.kernel.Rq2ModelScale(10,12),1024**2,65536,65536)
    return request,record


def run(request):
    return api.prepare_task_inputs(request,expected_request_identity=api.task_source_identity(request))


def test_full_tiny_preparation_matches_legacy_content(supplied):
    request,record=supplied
    old=api.legacy.prepare_task_inputs(request,expected_request_identity=api.legacy.task_source_identity(request))
    new=run(request)
    assert old.assembly.inputs==new.assembly.inputs
    assert old.binding_json==new.binding.legacy_content_json
    assert old.assembly.assembly_identity==new.assembly.legacy_content_assembly_identity
    assert new.request_identity!=old.request_identity
    assert new.binding.source_assembly_identity==new.assembly.assembly_identity
    assert new.solver_calls==0 and new.mechanism_initial_state
    assert not any((new.observed_power_mapping,new.normal_assignment_verified,new.formal_result))
    times=dict(new.timings)
    assert times['observed_total_seconds']==pytest.approx(sum(t for n,t in new.timings[:-1]))
    with pytest.raises(TypeError): replace(new,formal_result=True)


def test_prepare_never_calls_legacy_full_input_paths(supplied,monkeypatch):
    def forbidden(*a,**k): raise AssertionError('legacy input path or solver reached')
    for obj,name in ((api.kernel,'normal_input_identity'),(api.kernel.native,'create_solver'),
            (api.source_normal.legacy,'assemble_source_normal'),(api.source_normal.legacy,'normal_input_identity'),
            (api.stream_binding.old_pair,'bind_pair_normal'),(api.stream_binding.old_power,'bind_power_normal')):
        monkeypatch.setattr(obj,name,forbidden)
    assert run(supplied[0]).solver_calls==0


@pytest.mark.parametrize('field,value',[('formal_result',True),('solver_calls',False),('model_builds',0),
    ('mode','derive'),('external_assembly_identity_verified',1),('declaration_role','checkpoint'),
    ('normal_assembly_identity','0'*64),('normal_input_identity','0'*64),('pair_identity','0'*64),
    ('pair_declaration_sha256','0'*64),('normal_assignment_verified',True)])
def test_bad_declaration_rejected_before_source_load(supplied,monkeypatch,field,value):
    request,record=supplied; record[field]=value
    raw=encoded(record); Path(request.normal_record_path).write_bytes(raw)
    request=replace(request,expected_normal_record_sha256=sha256(raw).hexdigest())
    monkeypatch.setattr(api.source_normal,'assemble_source_normal',lambda *a,**k:pytest.fail('source load reached'))
    with pytest.raises(ValueError): run(request)


def test_new_request_pin_required(supplied):
    request,_=supplied
    with pytest.raises(ValueError,match='implementation/request drift'):
        api.prepare_task_inputs(request,expected_request_identity=api.legacy.task_source_identity(request))


def test_binding_legacy_content_is_checked(supplied,monkeypatch):
    original=api.stream_binding.bind_pair_normal
    def changed(*a,**k):
        result=original(*a,**k)
        content=json.loads(result.legacy_content_json); content['observed_power_mapping']=True
        return replace(result,legacy_content_json=json.dumps(content))
    monkeypatch.setattr(api.stream_binding,'bind_pair_normal',changed)
    with pytest.raises(ValueError,match='binding'): run(supplied[0])


@pytest.mark.parametrize('field',['normal_identity','source_assembly_identity','pair_identity',
    'legacy_content_binding_identity','implementation_identity','binding_identity'])
def test_binding_wrapper_identity_checked(supplied,monkeypatch,field):
    original=api.stream_binding.bind_pair_normal
    def changed(*a,**k): return replace(original(*a,**k),**{field:'0'*64})
    monkeypatch.setattr(api.stream_binding,'bind_pair_normal',changed)
    with pytest.raises(ValueError,match='binding identity'): run(supplied[0])


def test_post_read_detects_declaration_change(supplied,monkeypatch):
    original=api.stream_binding.bind_pair_normal
    def changed(*a,**k):
        result=original(*a,**k)
        Path(supplied[0].normal_record_path).write_bytes(b'{}')
        return result
    monkeypatch.setattr(api.stream_binding,'bind_pair_normal',changed)
    with pytest.raises(ValueError,match='size/hash'): run(supplied[0])
