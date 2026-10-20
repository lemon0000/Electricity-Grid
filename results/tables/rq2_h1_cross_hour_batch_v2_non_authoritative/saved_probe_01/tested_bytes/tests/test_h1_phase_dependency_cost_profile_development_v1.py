"""Bounded detached phase-group profiling; no owner, source, Job or solver."""
import cProfile
from hashlib import sha256
import json
from pathlib import Path
import pstats
from time import perf_counter

import psutil

from experiments import h1_phase_dependency_verifier_development_v1 as verifier


def test_two_identical_detached_phase_groups_profile_read_and_projection_cost(tmp_path):
    process=psutil.Process()
    rows=[];outputs=[]
    for ordinal in range(2):
        profiler=cProfile.Profile()
        before=process.io_counters();start=perf_counter()
        with profiler:
            result=verifier.prepare_group('training_ub',0)
        elapsed=perf_counter()-start;after=process.io_counters()
        assert all(result[name] is False for name in verifier.FLAGS)
        assert result['fresh_at_return_only'] is True and result['detached_data'] is True
        raw=verifier.io.encode(result);outputs.append(raw)
        stats=pstats.Stats(profiler)
        functions=[]
        for (filename,line,name),(primitive,calls,total,cumulative,callers) in stats.stats.items():
            functions.append(dict(file=filename,line=line,function=name,primitive_calls=primitive,
                calls=calls,self_seconds=total,cumulative_seconds=cumulative))
        functions.sort(key=lambda row:row['cumulative_seconds'],reverse=True)
        focus=[row for row in functions if row['function'] in
            ('read_stable','_views','_project','_resolver','loads','digest','encode','identity')]
        rows.append(dict(observation=ordinal+1,elapsed_seconds=elapsed,
            output_sha256=sha256(raw).hexdigest(),observed_file_count=result['observed_file_count'],
            observed_total_bytes=result['observed_total_bytes'],
            io_read_operations=after.read_count-before.read_count,
            io_read_bytes=after.read_bytes-before.read_bytes,
            profile_total_calls=stats.total_calls,profile_primitive_calls=stats.prim_calls,
            focus=focus,top_cumulative=functions[:24]))
        print(json.dumps({key:value for key,value in rows[-1].items()
            if key not in ('focus','top_cumulative')}),flush=True)
    assert outputs[0]==outputs[1]
    (tmp_path/'phase_dependency_cost_profile.json').write_text(json.dumps(dict(
        status='BOUNDED_COST_OBSERVATION_NONAUTHORITATIVE',profiled_detached_groups=2,
        groups_byte_identical=True,observations=rows,
        scope='two canonical detached prepare_group calls under cProfile; includes profiler overhead; no owner/header or optimized-runtime claim',
        formal_result=False,resource_admission=False,native_execution_authorized=False),indent=2),encoding='utf-8')
