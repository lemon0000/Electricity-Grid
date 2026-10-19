"""Zero-owner bounded CPU attribution; profiler times are not a speed benchmark."""
import cProfile
import json
from pathlib import Path
import pstats
from time import perf_counter

from experiments import h1_group_execution_roster_development_v4 as roster
from tests.test_h1_selector_configuration_development_v1 import configuration


def test_runtime_seal_component_cost_with_no_public_owner_or_N0(tmp_path):
    bootstrap=roster.bootstrap;shared=bootstrap.phase_operation;binding=bootstrap.phase_manifest
    kernel=binding.observation;c=configuration();rows=[]
    def measure(name,function,count):
        profile=cProfile.Profile();start=perf_counter();profile.enable()
        for _ in range(count):function()
        profile.disable();elapsed=perf_counter()-start
        statistics=pstats.Stats(profile).stats
        top=sorted(statistics.items(),key=lambda item:item[1][3],reverse=True)[:14]
        row=dict(component=name,calls=count,profiled_seconds=elapsed,
            functions=[dict(file=key[0],line=key[1],function=key[2],primitive_calls=value[0],
                total_calls=value[1],self_seconds=value[2],cumulative_seconds=value[3]) for key,value in top])
        rows.append(row);profile.dump_stats(str(tmp_path/(name+'.prof')))
        print(json.dumps(dict(component=name,calls=count,profiled_seconds=elapsed)),flush=True)
    for name,function in (('Bootstrap5_runtime',bootstrap._PHASE_RUNTIME),('Roster4_runtime',roster._RUNTIME),
            ('shared_runtime',shared._RUNTIME),('binding3_runtime',binding._RUNTIME),
            ('kernel_runtime',kernel._RUNTIME),('configuration_binding',c.binding)):
        measure(name,function,32)
    window=kernel.PhaseDependencyValidationOperation(plan=(('training_ub',0),),diagnostic_only=True)
    with window:
        window.prepare_group('training_ub',0)
        measure('held_kernel_receipt',window.receipt,8)
    assert window.receipt()['lifecycle_complete']
    phase=shared.PhaseManifestValidationOperation(plan=(('training_ub',0),),configuration=c,
        archive=binding.ArchiveCapacityDeclaration(576,2**20,576*2**20,0),
        dynamic_roots=(tmp_path/'dynamic_non_authoritative',),maximum_projects=4,maximum_checks=32,diagnostic_only=True)
    with phase:measure('shared_active_check',phase.check,8)
    assert phase.receipt()['lifecycle_complete']
    cleanup=kernel._CLEANUP_DIAGNOSTICS()
    assert cleanup['active_operations']==cleanup['abandoned_pending_operations']==0
    (tmp_path/'public_phase_runtime_profile.json').write_text(json.dumps(dict(
        components=rows,kernel_window_receipt=window.receipt(),shared_window_receipt=phase.receipt(),
        public_owners=0,N0_Jobs=0,native_calls=0,profiler_enabled=True,
        matched_runtime_comparison=False,whole_workflow_estimate=False,
        formal_result=False,resource_admission=False),indent=2),encoding='utf-8')
