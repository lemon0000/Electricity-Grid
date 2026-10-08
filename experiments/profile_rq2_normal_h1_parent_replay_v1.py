"""Zero-solver profile of the retained synthetic two-hour parent audit."""
from pathlib import Path
import argparse
import cProfile
import hashlib
import json
import pstats
import sys
import tempfile
import time

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    output=args.output.resolve()
    if not output.parent.name.endswith('_non_authoritative') or output.exists():
        raise ValueError('new output in explicit non_authoritative directory required')
    import pytest
    from tests.test_rq2_normal_h1_source_binding_v1 import supplied
    from tests.test_rq2_normal_h1_source_episode_v1 import environment
    from tests.test_rq2_objective_provenance_run_v1 import spec
    from tests.test_rq2_normal_h1_short_solve_v1 import budget
    from src.rq2_joint_deliverability_boundary_v1 import normal_h1_anchored_source_episode as api
    from src.rq2_joint_deliverability_boundary_v1.normal_h1_resource_shape import solver_calls_forbidden

    sample=ROOT/'results/tables/rq2_normal_h1_anchored_source_episode_v1_non_authoritative'
    manifest=sample/'development_checks.json'
    pinned=json.loads(manifest.read_bytes())
    def verify():
        for name,digest in pinned['files'].items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=digest:
                raise ValueError('retained sample drift: '+name)
    verify()
    profiler=cProfile.Profile()
    mp=pytest.MonkeyPatch()
    start=time.perf_counter()
    try:
        with tempfile.TemporaryDirectory(prefix='h1_profile_') as scratch:
            env=environment.__wrapped__(supplied.__wrapped__(Path(scratch),mp),mp)
            _,_,origin,state=env
            expected=json.loads((sample/'tiny_native_checks.json').read_bytes())
            with solver_calls_forbidden():
                profiler.enable()
                owner=api.DevelopmentH1AnchoredSourceEpisode(sample/'parent_non_authoritative',
                    api.source.static_network(state['data']),spec(),budget(),api.old.H1EpisodeBudget(2,6,6.),
                    api.child.base.replay.H1HourReplayLimits(3,100,500),dc_bus=1,origin=origin,
                    upstream_root=sample/'upstream',config_path=sample/'source.yaml',
                    expected_anchor_record=expected['final_parent_anchor_sha256'])
                try:inspection=owner.inspect()
                finally:owner.close()
                profiler.disable()
            if inspection.completed_hours!=2 or inspection.status!='complete':
                raise ValueError('retained complete parent audit changed')
    finally:
        profiler.disable()
        mp.undo()
    elapsed=time.perf_counter()-start
    verify()
    stats=pstats.Stats(profiler)
    records=[]
    for (filename,line,name),(primitive,total,self_seconds,cumulative,callers) in stats.stats.items():
        records.append(dict(filename=filename,line=line,function=name,primitive_calls=primitive,
            total_calls=total,self_seconds=self_seconds,cumulative_seconds=cumulative))
    body=dict(schema='h1_parent_zero_solver_profile_v1',status='DRAFT_NONAUTHORITATIVE',
        source_role='retained_synthetic_fixture',profiled_operation='readonly constructor plus inspect and close',
        sample_manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),
        profile_runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        preserved_members=len(pinned['files']),drift_count=0,solver_calls=0,completed_hours=inspection.completed_hours,
        profiled_elapsed_seconds=elapsed,total_primitive_calls=stats.prim_calls,total_calls=stats.total_calls,
        functions=sorted(records,key=lambda row:row['cumulative_seconds'],reverse=True),
        formal_result=False,formal_execution_ready=False,hard_resources_admitted=False)
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as stream:json.dump(body,stream,indent=2);stream.write('\n')
    print(json.dumps({k:v for k,v in body.items() if k!='functions'}))
    print(json.dumps(body['functions'][:20],indent=2))


if __name__=='__main__':main()
