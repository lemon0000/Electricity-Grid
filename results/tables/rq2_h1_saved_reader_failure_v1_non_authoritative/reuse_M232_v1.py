"""Reconcile existing M232 files and metadata without replaying or solving."""
from hashlib import sha256
import json
from pathlib import Path

HERE=Path(__file__).resolve().parent
REPO=HERE.parents[2]


def load(path):return json.loads(Path(path).read_bytes())
def pin(path):return sha256(Path(path).read_bytes()).hexdigest()


def main():
    root=HERE.parent
    gap_path=root/'rq2_h1_resource_readiness_v1_non_authoritative/resource_gap_audit_v2_final.json'
    gap=load(gap_path)
    evidence={str(REPO/name):value for name,value in gap['evidence_sha256'].items()}
    assert all(pin(path)==value for path,value in evidence.items())
    old=root/'rq2_normal_h1_full_job_v3_non_authoritative'
    inventory_path=old/'calibration_v3.postrun_inventory.json'
    review_path=old/'calibration_v3.postrun_review.json'
    inventory,review=load(inventory_path),load(review_path)
    source_root=Path(inventory['root'])
    expected={str(source_root/name):item['sha256'] for name,item in inventory['members'].items()}
    before={str(path):pin(path) for path in source_root.rglob('*') if path.is_file()}
    assert before==expected and len(before)==251
    assert sum(Path(name).stat().st_size for name in before)==inventory['bytes']==20938085
    assert review['native_reports']==232 and review['formal_result'] is False
    shape_path=root/'rq2_normal_h1_shape_v1_non_authoritative/scratch_non_authoritative/shape_result.json'
    checks_path=shape_path.parent.parent/'shape_job_checks.json'
    shape,checks=load(shape_path),load(checks_path)
    assert pin(shape_path)==checks['result_sha256']
    assert shape['stage_count']==232 and shape['shape_only'] is True and shape['solver_calls']==0
    producer_path=root/'rq2_h1_producer_ingress_v1_non_authoritative/producer_shape_audit_v2_final.json'
    producer=load(producer_path)
    assert producer['source_pin_equal'] is True and producer['solver_calls']==0
    after={str(path):pin(path) for path in source_root.rglob('*') if path.is_file()}
    assert before==after
    named=[Path(__file__),gap_path,inventory_path,review_path,shape_path,checks_path,producer_path]
    evidence.update({str(path):pin(path) for path in named});evidence.update(before)
    value=dict(status='DRAFT_NONAUTHORITATIVE',scope='existing one-hour M232 metadata and251-file SHA reuse; no new Reader or SQLite replay',
        bindings=evidence,calibration_owned_files=251,calibration_logical_bytes=20938085,
        existing_calibration=dict(native_reports=232,job_wall_seconds=review['job_elapsed_seconds'],
            job_peak_total_commit_bytes=review['job_peak_total_commit_bytes'],
            measured_non_solver_seconds=None,native_execution_authenticated=review['native_execution_authenticated'],
            optimality_certified=review['optimality_certified'],official_verdict=review['official_verdict'],
            whole_task_resources_verified=review['whole_task_resources_verified'],formal_result=review['formal_result'],
            scope='historical one training origin/hour; historical native use not new execution authority'),
        existing_zero_solver_shape=dict(stage_count=232,source_authenticated=shape['source_authenticated'],
            worker_seconds=shape['worker_elapsed_seconds'],
            source_load_assembly_seconds=shape['source_load_and_assembly_seconds'],
            source_revalidation_seconds=shape['source_revalidation_seconds'],
            stage_shapes=shape['measured_stage_shapes'],unmeasured=shape['unmeasured']),
        existing_producer_shape=dict(scope=producer['scope'],
            constraints=producer['static_inventory']['constraints'],
            native_export_coverage=producer['native_export_coverage'],
            producer_coverage_proven=producer['producer_coverage_proven'],
            counterexample=producer['counterexample']),
        source_v3_M232_saved_reader_not_executed=True,
        H192_packet_retention_verified=False,H192_parent_namespace_or_future_carry_proved=False,
        all_stage_native_time_or_assembly_time_bound_established=False,
        shape_build_times_are_232_stage_total=False,
        next_use='Use pinned M232 artifacts/shape for a bounded source-applicability and retention plan, not a new native calibration or a missing predecessor substitute.',
        saved_Reader_invocations=0,new_normal_jobs=0,real_native_solver_calls=0,
        source_successor_adopted=False,resource_admission=False,formal_execution_ready=False,formal_result=False)
    with (HERE/'saved_M232_evidence_reuse_v1.json').open('x',encoding='utf-8') as stream:
        json.dump(value,stream,indent=2);stream.write('\n')
    print(json.dumps(dict(files=251,logical_bytes=20938085,bindings=len(evidence),
        historical_reports=232,new_Reader=0,new_native=0)))


if __name__=='__main__':main()
