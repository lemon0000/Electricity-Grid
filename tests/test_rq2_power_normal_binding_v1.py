from copy import deepcopy
from dataclasses import replace
from datetime import timedelta
from types import SimpleNamespace

import pytest

from src.rq2_joint_deliverability_boundary_v1 import power_normal_binding as binding
from tests.test_rq2_continuous_grid_normal_v1 import fixture


def supplied():
    inputs = fixture(3)
    inputs = replace(inputs, carry=replace(inputs.carry, identity=replace(inputs.carry.identity,
        trajectory_id='power:training:outage_seed=1')))
    assembly = SimpleNamespace(inputs=inputs, raw_source_hours=(0,1,2),
        assembly_identity='a'*64, normal_identity='b'*64, source_manifest_sha256='1'*64)
    window = dict(kind='power', split='training', outage_seed=1,
        chain={'chain_id':'power:training:outage_seed=1'},
        continuous_power_source_hours=[1,2,3], window_identity='c'*64,
        package_manifest_sha256='d'*64, rows=[dict(source_hour=str(i),
            timestamp=t.isoformat(), system_load_mw='20') for i,t in enumerate(inputs.request.timestamps)])
    return assembly, window


def test_alignment():
    assert binding._alignment(*supplied()) == 0


@pytest.mark.parametrize('change', ['split','seed','trajectory','raw','continuous','clock','load','nan','infinity','kind'])
def test_alignment_rejects_disagreement(change):
    assembly, window = supplied()
    if change=='split': window['split']='holdout'
    elif change=='seed': window['outage_seed']=2
    elif change=='trajectory': window['chain']['chain_id']='foreign'
    elif change=='raw': window['rows'][0]['source_hour']='1'
    elif change=='continuous': window['continuous_power_source_hours']=[0,1,2]
    elif change=='clock': window['rows'][0]['timestamp']=(assembly.inputs.request.timestamps[0]+timedelta(hours=1)).isoformat()
    elif change=='load': window['rows'][0]['system_load_mw']='20.1'
    elif change=='nan': window['rows'][0]['system_load_mw']='NaN'
    elif change=='infinity': window['rows'][0]['system_load_mw']='Infinity'
    elif change=='kind': window['kind']='workload'
    with pytest.raises(ValueError): binding._alignment(assembly,window)


@pytest.fixture
def mocked(monkeypatch):
    assembly, window = supplied()
    monkeypatch.setattr(binding.source_normal,'validate_source_assembly',lambda *args: assembly)
    monkeypatch.setattr(binding.source_window,'load_source_window',lambda *args,**kw: deepcopy(window))
    monkeypatch.setattr(binding.source_window.audit,'_load_config',lambda *args:{'inputs':{'power':{}}})
    monkeypatch.setattr(binding.source_window.audit,'_verify_package',lambda *args:(None,{'grid_source_manifest_sha256':'1'*64}))
    monkeypatch.setattr(binding.source_window.audit,'_verify_hash',lambda *args:None)
    return assembly, window


def call(assembly, **changes):
    args=dict(expected_assembly_identity='a'*64, expected_window_identity='c'*64,expected_config_sha256='e'*64)
    args.update(changes)
    return binding.bind_power_normal(assembly,'unused',**args)


def test_rebuild_identity_and_evidence_flags(mocked):
    report=call(mocked[0])
    assert report['source_correspondence_verified']
    assert report['solver_calls']==0
    assert all(report[k] is False for k in ('initial_history_authenticated','initial_network_feasibility_verified',
        'normal_assignment_verified','outage_dispatch_verified','registered_coupling','business_power_mapping_verified','formal_result'))


@pytest.mark.parametrize('field',['expected_assembly_identity','expected_window_identity'])
def test_independent_identity_mismatch(mocked,field):
    with pytest.raises(ValueError,match='identity mismatch'): call(mocked[0],**{field:'0'*64})


def test_package_grid_origin_mismatch(mocked,monkeypatch):
    monkeypatch.setattr(binding.source_window.audit,'_verify_package',lambda *args:(None,{'grid_source_manifest_sha256':'2'*64}))
    with pytest.raises(ValueError,match='grid source manifest differ'): call(mocked[0])


def test_invalid_expected_digest_rejected_before_rebuild(mocked):
    class Equal:
        def __eq__(self,other): return True
    with pytest.raises(ValueError,match='SHA256'): call(mocked[0],expected_window_identity=Equal())


def test_declaration_conversion_preserves_contract_and_declares_new_identity():
    from dataclasses import asdict
    import json
    from experiments.audit_rq2_power_normal_binding_v1 import declared_inputs
    assembly, window = supplied()
    inputs=assembly.inputs
    record=json.loads(json.dumps(dict(request=asdict(inputs.request),initial=asdict(inputs.initial),
        carry=asdict(inputs.carry),source_manifest_sha256='1'*64),
        default=lambda x: sorted(x) if isinstance(x,frozenset) else x.isoformat()))
    before=deepcopy(record)
    request, initial, carry=declared_inputs(record,window)
    assert request==inputs.request and initial==inputs.initial and carry==inputs.carry
    assert record==before
    window['outage_seed']=2
    window['chain']['chain_id']='power:training:outage_seed=2'
    _, _, changed=declared_inputs(record,window)
    assert changed.identity.outage_seed==2 and changed.identity.trajectory_id==window['chain']['chain_id']
    assert changed.points==carry.points and changed.initial_history_role=='mechanism_assumption'


def test_runner_passes_external_assembly_pin(mocked, monkeypatch, tmp_path):
    import sys
    from hashlib import sha256
    from experiments import audit_rq2_power_normal_binding_v1 as runner
    assembly, window = mocked
    declaration=tmp_path/'declaration.json'
    declaration.write_text('{"source_time_basis":"naive_source_labelled_utc"}')
    output=tmp_path/'binding_non_authoritative.json'
    monkeypatch.setattr(runner,'declared_inputs',lambda *args:(None,None,None))
    monkeypatch.setattr(runner.source_normal,'assemble_source_normal',lambda *args,**kw:assembly)
    def reject(*args,**kw):
        assert kw['expected_assembly_identity']=='9'*64
        assert kw['expected_assembly_identity']!=assembly.assembly_identity
        raise ValueError('external pin rejected')
    monkeypatch.setattr(runner,'bind_power_normal',reject)
    monkeypatch.setattr(sys,'argv',['runner','--declaration',str(declaration),
        '--expected-declaration-sha256',sha256(declaration.read_bytes()).hexdigest(),
        '--source-root','unused','--split','training','--raw-start','0','--hours','3','--outage-seed','1',
        '--expected-window-identity','c'*64,'--expected-config-sha256','e'*64,
        '--expected-assembly-identity','9'*64,'--output',str(output)])
    with pytest.raises(ValueError,match='external pin rejected'): runner.main()
    assert not output.exists()
