"""Fresh analytic Rref through original-source aliases; zero native calls.

The alias lifecycle and identity seams are the existing hour-0 synthetic seams.
No archived completion is reconstructed, and no Actual or paired commit runs.
"""
from contextlib import contextmanager
from fractions import Fraction
import json
from pathlib import Path
from types import SimpleNamespace

from tests import h1_group_selector_integration_helpers_v2 as fixture


@contextmanager
def live_reference(common_owner,configuration,patch,root,trace):
    sequence=fixture.sequence;producer=fixture.producer
    modules=(sequence.selection.physical,sequence.selection,sequence.legacy.stage,
        sequence.legacy.bridge,sequence.legacy.configuration_api,sequence.timed.capture.legacy,
        sequence.legacy,sequence.timed,sequence.timed.capture)
    originals={module:module.implementation_identity for module in modules}
    def identity(module,fn):
        return fn(configuration.specification,configuration.limits) if module is sequence.selection else fn()
    pins={module:identity(module,fn) for module,fn in originals.items()}
    try:
        with patch.context() as scoped:
            fixture.no_solver.__wrapped__(scoped)
            original_install=producer.install
            def install(mp,path,lane,fault=None):
                assert fault is None
                instances=original_install(mp,path,lane,fault)
                direct=producer.m.capture.GurobiDirect;presolve=direct._presolve
                def analytic(self,model,**kwargs):
                    presolve(self,model,**kwargs)
                    values={v.VarName:(20. if v.VarName=='generation[G1]' else 0.) for v in self.native.variables}
                    assert 'generation[G1]' in values and 'selector_deviation[G1]' in values
                    if lane.role=='Rref':assert 'reference_power' in values
                    for variable in self.native.variables:variable.X=values[variable.VarName]
                    objective=self.native.objective.constant+sum(c*v.X for v,c in self.native.objective.terms)
                    self.native.ObjVal=self.native.ObjBound=self.native.ObjBoundC=objective
                    self.result.problem.lower_bound=self.result.problem.upper_bound=objective
                    for name,value in values.items():self.result.solution[0].variable[name]['Value']=value
                mp.setattr(direct,'_presolve',analytic)
                return instances
            scoped.setattr(producer,'install',install)
            build=fixture.factory.__wrapped__(root,scoped,None)
            context=SimpleNamespace(owner=common_owner,config=configuration,cap=2**30)
            h=fixture.harness.__wrapped__(context,build,scoped,root)
            trace('slice_reference_snapshot_and_harness')
            consumer=fixture.load(fixture.handoff.__file__,'guarded_common_slice_handoff_test_alias',scoped,
                {'h1_selector_parent_controller_development_v2':h.module})
            with h.module.Parent(h.root,h.raw,**h.options) as reference:
                completion=reference.run()
                trace('slice_live_Rref_parent_complete')
                snapshot=h.module.worker.snapshot
                item=snapshot.rebuild(h.raw,expected_sha256=snapshot.io.digest(h.raw))
                assert item.frame.info.current.dc_baseline_mw==0
                assert sum(v for _,v in item.frame.info.current.demand_by_bus_mw)==20
                assert item.disclosure.current_state.active is None
                terminal=json.loads((Path(completion.scientific_root)/'terminal.json').read_bytes())
                assert terminal['canonical_lock_hex']==[float(v).hex() for v in fixture.ZERO_WORKLOAD_REFERENCE_LOCKS]
                assert Fraction(*map(int,terminal['candidate_request_exact']))==0
                trace('slice_Rref_zero_workload_oracle')
                yield consumer,(reference,completion),scoped
    finally:
        for module,fn in originals.items():
            assert module.implementation_identity is fn and identity(module,fn)==pins[module]
