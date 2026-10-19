"""Zero-owner identity cost and exact repeated identity values; no data windows."""
import cProfile
import json
from pathlib import Path
import pstats
from time import perf_counter

from experiments import h1_group_execution_roster_development_v4 as roster
from tests.test_h1_selector_configuration_development_v1 import configuration


def test_repeated_public_implementation_identity_cost_without_any_owner(tmp_path):
    bootstrap=roster.bootstrap;c=configuration();rows=[]
    for name,function in (('Bootstrap5_identity',bootstrap.implementation_identity),
            ('Roster4_identity',roster.implementation_identity),
            ('binding3_identity',lambda:bootstrap.phase_manifest.implementation_identity(c)),
            ('shared_identity',lambda:bootstrap.phase_operation.implementation_identity(c))):
        values=[];profile=cProfile.Profile();start=perf_counter();profile.enable()
        for _ in range(8):values.append(function())
        profile.disable();elapsed=perf_counter()-start
        assert len(set(values))==1 and type(values[0]) is str and len(values[0])==64
        stats=pstats.Stats(profile).stats;top=sorted(stats.items(),key=lambda item:item[1][3],reverse=True)[:32]
        row=dict(component=name,calls=8,identity=values[0],profiled_seconds=elapsed,
            functions=[dict(file=key[0],line=key[1],function=key[2],primitive_calls=value[0],total_calls=value[1],
                self_seconds=value[2],cumulative_seconds=value[3]) for key,value in top])
        rows.append(row);profile.dump_stats(str(tmp_path/(name+'.prof')))
        print(json.dumps(dict(component=name,calls=8,profiled_seconds=elapsed)),flush=True)
    assert bootstrap.phase_manifest.observation._CLEANUP_DIAGNOSTICS()['active_operations']==0
    (tmp_path/'public_implementation_identity_profile.json').write_text(json.dumps(dict(
        components=rows,public_owners=0,N0_Jobs=0,native_calls=0,data_windows=0,
        profiler_enabled=True,whole_workflow_estimate=False,formal_result=False,resource_admission=False),indent=2),encoding='utf-8')
