"""Real unchanged source core with explicit historical/owner unit seams.

This tests source/registry/scientific composition and failure chronology. The
mock witness supplies no numerical proof, live Handoff or integration evidence.
"""
import json
from pathlib import Path
import sys
from types import ModuleType,SimpleNamespace

import pytest

import experiments
from experiments import h1_phase_exact_source_current_development_v2 as core
from tests.test_h1_phase_exact_source_current_development_v2 import inputs,scenario,supplied
from tests.test_h1_common_source_bundle_v2 import complete


@pytest.fixture
def build(complete,monkeypatch):
    root,args,prefix_calls,*_=complete
    def create(fault=None):
        counts=dict(registry=0,source=0,validate=0,final=0,finished=0,recorded=0,poisoned=0)
        holder={};original_owned=core.normal._owned
        def owned(cls,**values):
            if cls.__name__=='CommonSourceBundle' and cls.__module__=='experiments._operation_source_unit_v3':
                if fault=='result_constructor':raise RuntimeError('result constructor')
                result=original_owned(cls,**values)
                if fault=='result_return':holder['module'].SCHEMA='changed-after-result'
                return result
            return original_owned(cls,**values)
        monkeypatch.setattr(core.normal,'_owned',owned)
        for owner,name,key in ((core.registry,'prepare','registry'),
                (core.source,'load_pinned_current','source'),
                (core.source,'validate_pinned_current','validate'),
                (core.historical,'_observe_sources','final')):
            original_call=getattr(owner,name)
            def call(*a,_fn=original_call,_key=key,**kw):
                counts[_key]+=1
                if fault=='second_registry' and _key=='registry' and counts[_key]==2:
                    raise RuntimeError('second registry')
                if fault=='final_source' and _key=='final':raise RuntimeError('final source')
                return _fn(*a,**kw)
            monkeypatch.setattr(owner,name,call)
        fake=ModuleType('experiments.h1_operation_historical_witness_development_v2')
        fake.__file__=str(Path(core.__file__).with_name('h1_operation_historical_witness_development_v2.py'))
        fake.prior_witness=core.historical.witness
        fake.verifier_identity=lambda:'d'*64
        fake._ENVELOPE_TOKEN=object()
        old_replay=core.historical._replay_prefix
        def replay(root,*,_operation,_ticket,_prefix_index,**arguments):
            result=old_replay(root,**arguments)
            _operation._pending.append((None,None,None,2,2))
            return result
        fake._replay_prefix=replay
        class Envelope:
            def __init__(self,decision,audit,identity,full,fresh,execution,**kw):
                self.decision=decision;self.audit_payload=audit;self.execution_receipt=execution
                self.envelope_identity=core.io.digest(core.io.encode([identity,core.io.digest(audit),core.io.digest(execution)]))
        fake.VerifiedHistoricalEnvelope=Envelope
        class Arm:
            def __init__(self):
                self._fixed_declaration=(root,'unit-arm',args['expected_binding_sha256'],
                    args['expected_terminal_sha256'],1,True)
                self._ticket=None;self._pending=[];self.failure=None
                self._session=SimpleNamespace(_record_source=lambda *a:counts.__setitem__('recorded',counts['recorded']+1))
            def _check(self):
                if self.failure:raise ValueError('poisoned unit arm')
            def _start(self):self._ticket=object();self._pending=[];return self._ticket
            def _execution(self,*a):return core.io.encode(dict(explicit_unit_witness=True))
            def _finish(self,*a,**kw):
                counts['finished']+=1;self._ticket=None
                if fault=='post_commit_return':holder['module']._scientific_audit=lambda *a:b'{}'
            def _poison(self,error):self.failure=repr(error);self._pending=[];counts['poisoned']+=1
        fake.ArmWitness=Arm
        monkeypatch.setitem(sys.modules,fake.__name__,fake)
        monkeypatch.setattr(experiments,'h1_operation_historical_witness_development_v2',fake,raising=False)
        path=Path(core.__file__).with_name('h1_phase_exact_source_current_development_v3.py')
        name='experiments._operation_source_unit_v3'
        module=ModuleType(name);module.__file__=str(path);module.__package__='experiments'
        monkeypatch.setitem(sys.modules,name,module)
        exec(compile(path.read_bytes(),str(path),'exec'),vars(module))
        holder['module']=module
        return module,Arm(),counts
    return create


def test_source_core_two_registry_load_validate_final_observe_and_new_objects(build,inputs):
    module,arm,counts=build()
    result=module.prepare_common_bundle(arm,expected_registry_identity=inputs[1]['expected_registry_identity'])
    assert type(result) is module.CommonSourceBundle and type(result.current) is module.ExactSourceCurrent
    assert counts==dict(registry=2,source=2,validate=1,final=1,finished=1,recorded=1,poisoned=0)
    current=result.current;raw=current.source_projection_audit_payload
    assert current.prepared_current.audit_payload==raw
    audit=json.loads(raw);compat=audit['predecessor_compatibility']['payload']
    assert all(key not in audit for key in module._EXECUTION_FIELDS)
    assert audit['normal_audit_payload']==compat['normal_audit_payload']
    assert audit['source_observation_audit_payload']==compat['source_observation_audit_payload']
    assert audit['registry_audit_payload']==compat['registry_audit_payload']
    assert audit['workload_projection']==compat['workload_projection']
    assert len(inputs[2])==2
    execution=json.loads(result.verification_execution_payload)
    assert (execution['full_numerical_hour_replays'],execution['within_prefix_revalidations'],execution['cross_common_numerical_proof_reuses'])==(4,4,0)
    assert execution['prepared_current_audit_sha256']==execution['exact_source_audit_sha256']==module.io.digest(raw)
    assert execution['production_handoff_integrated'] is False


@pytest.mark.parametrize('fault',['second_registry','final_source','result_constructor','result_return','post_commit_return'])
def test_source_failure_window_preserves_error_and_poisons_pending_proof(build,inputs,fault):
    module,arm,counts=build(fault)
    with pytest.raises((RuntimeError,ValueError)) as caught:
        module.prepare_common_bundle(arm,expected_registry_identity=inputs[1]['expected_registry_identity'])
    assert counts['poisoned']==1 and arm.failure and not arm._pending
    if fault in ('second_registry','final_source','result_constructor'):
        assert fault.replace('_',' ') in str(caught.value) and counts['finished']==0
    elif fault=='result_return':assert counts['finished']==0
    else:assert counts['finished']==1
