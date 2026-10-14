"""Synthetic selector adapters for the complete N0/common integration test.

The only numeric oracle here is a tiny zero-workload, neutral-outage case:
P_ref=P_actual=0 and G1 supplies the fixed 20 MW demand. No native optimum or
canonical selector Job is claimed. Snapshot and persistence paths stay real.
"""
from contextlib import ExitStack
import json
from types import SimpleNamespace

import pytest

from experiments import h1_selector_phase_handoff_development_v1 as handoff
from tests.test_h1_selector_parent_controller_development_v1 import harness,load
from tests.test_h1_timed_selector_sequence_development_v1 import factory,producer


def consume_zero_workload(common_owner,configuration,patch,root):
    original_install=producer.install
    def install(mp,path,lane,fault=None):
        assert fault is None
        instances=original_install(mp,path,lane,fault)
        direct=producer.m.capture.GurobiDirect;presolve=direct._presolve
        def analytic(self,model,**kwargs):
            presolve(self,model,**kwargs)
            values={v.VarName:(20. if v.VarName=='generation[G1]' else 0.)
                    for v in self.native.variables}
            assert 'generation[G1]' in values and 'selector_deviation[G1]' in values
            if lane.role=='Rref':assert 'reference_power' in values
            for v in self.native.variables:v.X=values[v.VarName]
            objective=self.native.objective.constant+sum(c*v.X for v,c in self.native.objective.terms)
            self.native.ObjVal=self.native.ObjBound=self.native.ObjBoundC=objective
            self.result.problem.lower_bound=self.result.problem.upper_bound=objective
            for name,value in values.items():self.result.solution[0].variable[name]['Value']=value
        mp.setattr(direct,'_presolve',analytic)
        return instances
    patch.setattr(producer,'install',install)
    build=factory.__wrapped__(root,patch,None)
    context=SimpleNamespace(owner=common_owner,config=configuration,cap=2**30)
    h=harness.__wrapped__(context,build,patch,root)
    consumer=load(handoff.__file__,'complete_group_handoff_test_alias',patch,
        {'h1_selector_parent_controller_development_v1':h.module})
    retained=[]
    def retain(path,before,after):
        assert common_owner._original_operation.locked()
        assert common_owner._roster._original_operation.locked()
        assert common_owner._roster._owner._original_operation.locked()
        retained.append((before,after))
        return after
    options=dict(retain_head=retain,max_packet_bytes=64*1024**2,
        max_record_bytes=1024**2,max_archive_bytes=128*1024**2)
    with ExitStack() as stack:
        reference=stack.enter_context(h.module.Parent(h.root,h.raw,**h.options))
        ref=reference.run()
        lane_ids=tuple(c.lane_id for c in common_owner._manifest.lanes)
        with consumer.Handoff(common_owner,(reference,ref),dict.fromkeys(lane_ids),**options) as absent:
            with pytest.raises(ValueError,match='Actual execution missing or failed'):absent.consume()
            assert not absent.root.exists() and not retained
        actuals={}
        for lane in lane_ids:
            raw=h.module.worker.snapshot.capture_actual(common_owner,configuration,max_archive_bytes=context.cap,
                lane_id=lane,reference_root=ref.scientific_root,reference_terminal_sha256=ref.scientific_terminal_sha256,
                reference_request_sha256=ref.scientific_request_sha256,reference_max_archive_bytes=ref.max_archive_bytes)
            actual=stack.enter_context(h.module.Parent(root/('actual_'+lane),raw,**h.options,
                reference_owner=reference,reference_completion=ref))
            actuals[lane]=(actual,actual.run())
        assert len({id(v[0]) for v in actuals.values()})==len(lane_ids)==3
        with consumer.Handoff(common_owner,(reference,ref),actuals,**options) as owner:
            result=owner.consume()
            assert result['completed_hours']==1 and len(retained)==5
            assert all(result[k] is False for k in consumer.FLAGS)
            projection=json.loads(owner._plan.projection)
            assert {v['lane_id'] for v in projection['lanes']}==set(lane_ids)
            assert all(v['status']=='paired_committed' for v in projection['lanes'])
            assert owner._holder.inspect()==owner._plan.tickets
            assert owner._phase.heads==owner._plan.tickets[-1].after_heads
            packet=json.loads(owner._packet)
            assert packet['group_audit']==json.loads(common_owner._initial_report)
            return dict(root=str(owner.root),result=result,retained_heads=retained,
                synthetic_selector_parents=1+len(actuals),canonical_selector_jobs=0,
                real_native_calls=0,formal_result=False)
