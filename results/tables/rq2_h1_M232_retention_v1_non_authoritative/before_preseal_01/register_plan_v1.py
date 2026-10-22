"""Register one bounded origin packet cost/footprint probe."""
import ast
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]


def pin(path):return sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_bytes())


def main():
    prior=HERE.parent/'rq2_h1_saved_reader_failure_v1_non_authoritative/final_verification.json'
    pins=dict(load(prior)['bindings'])
    assert len(pins)==2910 and all(pin(path)==value for path,value in pins.items())
    paths=[prior,*sorted(HERE.glob('*.py')),HERE/'design_and_budget.md',
        HERE.parent/'rq2_normal_h1_shape_v1_non_authoritative/request.json',
        REPO/'src/rq2_joint_deliverability_boundary_v1/normal_h1_source_binding.py',
        REPO/'src/rq2_joint_deliverability_boundary_v1/normal_h1_resource_shape.py',
        REPO/'experiments/h1_timed_job_parent_development_v1.py']
    pins.update({str(path):pin(path) for path in paths})
    for path in HERE.glob('*.py'):ast.parse(path.read_text(encoding='utf-8'))
    value=dict(status='DRAFT_NONAUTHORITATIVE',risk='R3',sole_writer='root',bindings=pins,
        scope='one real-source M232 origin packet footprint; not a source Reader or H192 simulation',
        repetitions=1,source_origin=dict(split='training',power_raw_hour=0,workload_raw_hour=0,outage_seed=20260822),
        input_loads=2,packet_assemblies=1,remember_calls=1,all_packet_validation_calls=1,
        additional_top_level_retained_size_calls=10,model_builds=0,Reader_invocations=0,
        new_normal_jobs=0,selector_calls=0,real_native_solver_calls=0,
        wall_limit_seconds=60,no_activity_limit_seconds=30,sampled_owned_RSS_limit_bytes=768*1024**2,
        output_logical_limit_bytes=64*1024**2,sample_seconds=2,heartbeat_seconds=30,
        maximum_audited_distinct_input_files=512,automatic_retry=False,
        limits_are_sampled_thresholds_with_cleanup_tail=True,
        conditional_equal_footprint_products_are_H192_bounds=False,
        source_successor_adopted=False,overall_performance_review_complete=False,
        resource_admission=False,formal_execution_ready=False,formal_result=False)
    with (HERE/'plan_v1.json').open('x',encoding='utf-8') as stream:json.dump(value,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(registered=True,source_pins=len(pins),repetitions=1,model_builds=0,Reader=0,solver=0)))


if __name__=='__main__':main()
