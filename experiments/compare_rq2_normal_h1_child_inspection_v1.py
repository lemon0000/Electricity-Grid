"""Compare two API inspection strategies on the same retained raw evidence."""
from pathlib import Path
import argparse
import cProfile
import hashlib
import json
import pstats
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:sys.path.insert(0,str(ROOT))


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    output=args.output.resolve()
    if not output.parent.name.endswith('_non_authoritative') or output.exists():
        raise ValueError('new non_authoritative output required')
    from tests.test_rq2_normal_h1_source_v1 import packet
    from tests.test_rq2_objective_provenance_run_v1 import spec
    from tests.test_rq2_normal_h1_short_solve_v1 import budget
    from src.rq2_joint_deliverability_boundary_v1 import normal_h1_scoped_child_inspection as api
    from src.rq2_joint_deliverability_boundary_v1.normal_h1_resource_shape import solver_calls_forbidden
    root=ROOT/'results/tables/rq2_normal_h1_anchored_collector_v1_non_authoritative'
    manifest=root/'development_checks.json'
    pins=json.loads(manifest.read_bytes())['files']
    def verify():
        for name,pin in pins.items():
            if hashlib.sha256((ROOT/name).read_bytes()).hexdigest()!=pin:raise ValueError('retained artifact drift')
    verify()
    pin=json.loads((root/'tiny_native_checks.json').read_bytes())['anchor_record_sha256']
    metrics=[]
    results=[]
    with solver_calls_forbidden():
        for name,cls in [('legacy',api.legacy.DevelopmentH1AnchoredCollector),('scoped',api.DevelopmentH1ScopedChildInspection)]:
            profile=cProfile.Profile()
            start=time.perf_counter()
            profile.enable()
            owner=cls(root/'collector_non_authoritative',packet(),spec(),budget(),
                api.base.replay.H1HourReplayLimits(3,100,500),anchor_root=root/'anchor_non_authoritative',
                parent_intent_head='1'*64,source_lineage_identity='2'*64,expected_anchor_record=pin)
            try:value=owner.inspect()
            finally:owner.close()
            profile.disable()
            elapsed=time.perf_counter()-start
            results.append(value if name=='legacy' else value.inspection)
            stats=pstats.Stats(profile)
            audits=sum(v[0] for (f,line,fn),v in stats.stats.items() if Path(f).name=='normal_h1_hour_replay.py' and fn=='_audit_stage')
            metrics.append(dict(strategy=name,profiled_elapsed_seconds=elapsed,stage_audits=audits,
                primitive_calls=stats.prim_calls,total_calls=stats.total_calls))
    verify()
    if results[0]!=results[1]:raise ValueError('independent inspection results differ')
    if [x['stage_audits'] for x in metrics]!=[12,3]:raise ValueError('unexpected semantic replay count')
    report=dict(schema='h1_same_evidence_inspection_comparison_v1',status='DRAFT_NONAUTHORITATIVE',
        metrics=metrics,inspection_equal=True,solver_calls=0,preserved_members=len(pins),drift_count=0,
        inspector_identity=api.implementation_identity(),runner_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        sample_manifest_sha256=hashlib.sha256(manifest.read_bytes()).hexdigest(),formal_result=False,
        hard_resources_admitted=False,limitations=['One retained synthetic hour; instrumented local timing, not a multi-day resource bound.'])
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('x',encoding='utf-8') as stream:json.dump(report,stream,indent=2);stream.write('\n')
    print(json.dumps(report))


if __name__=='__main__':main()
