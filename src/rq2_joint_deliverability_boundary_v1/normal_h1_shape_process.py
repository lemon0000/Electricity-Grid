"""Short Windows Job controller for zero-solver shape evidence only."""
from dataclasses import asdict
from hashlib import sha256
import json
import os
from pathlib import Path
import sys
from math import isfinite

from . import normal_h1_resource_shape as shape
from . import normal_task_process as process

SCHEMA='h1_zero_solver_shape_job_development_v1'
ROOT=Path(__file__).resolve().parents[2]
WORKER=ROOT/'experiments/probe_rq2_normal_h1_shape_v1.py'
MAX_RESULT_BYTES=1024*1024
RESULT_FIELDS=set(('schema implementation_identity normal_input_identity current_source_audit_identity network_identity '
    'runtime_versions stage_order stage_count measured_stage_shapes counterfactual_unadmitted_content_envelope sqlite_length_limit_bytes '
    'counterfactual_single_event_fits_observed_sqlite_length_limit causal_key accepted_normal_carry sharing unmeasured '
    'formal_resource_contract solver_calls shape_only formal_result formal_execution_ready numerical_certificate '
    'resource_contract_approved source_binding_identity source_binding_audit_sha256 source_declaration dc_bus '
    'source_load_and_assembly_seconds source_revalidation_seconds source_authenticated selection_registered request_sha256 '
    'worker_sha256 process_peak_working_set_bytes worker_elapsed_seconds peak_working_set_scope hard_rss_limit_enforced').split())


def _write(path, value):
    raw=json.dumps(value,sort_keys=True,separators=(',',':'),allow_nan=False).encode('ascii')
    with path.open('xb') as stream:
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    if path.read_bytes()!=raw:
        raise ValueError('shape controller record readback mismatch')
    return sha256(raw).hexdigest()


def _seconds(value):
    if type(value) not in (int,float) or not isfinite(value) or value<0:
        raise ValueError('finite nonnegative shape timing required')


def validate_result(report, request):
    if (type(report) is not dict or set(report)!=RESULT_FIELDS or report.get('schema')!=shape.SCHEMA
            or type(report.get('solver_calls')) is not int or report['solver_calls']!=0
            or report.get('source_binding_identity')!=request['expected_source_identity']
            or report.get('implementation_identity')!=request['shape_implementation_identity']
            or report.get('worker_sha256')!=request['worker_sha256']
            or report.get('source_declaration')!=request['declaration'] or report.get('dc_bus')!=request['dc_bus']
            or report.get('shape_only') is not True
            or any(report.get(name) is not False for name in ('formal_result','formal_execution_ready',
                'numerical_certificate','resource_contract_approved','source_authenticated','selection_registered'))):
        raise ValueError('zero-solver shape result binding/authority mismatch')
    for name in ('implementation_identity','normal_input_identity','current_source_audit_identity','network_identity',
            'source_binding_identity','source_binding_audit_sha256','request_sha256','worker_sha256'):
        shape.binding.windows._sha(report[name])
    if report['runtime_versions']!=shape.runtime_versions():
        raise ValueError('shape runtime version mismatch')
    for field in ('source_load_and_assembly_seconds','source_revalidation_seconds','worker_elapsed_seconds'):
        _seconds(report[field])
    expected_sharing=dict(reuse_eligible_iff_complete_causal_key_equal=True,labels_alone_establish_key_equality=False,
        observed_hit_count=None,observed_hit_rate=None,future_carry_keys_enumerated=False)
    expected_unmeasured=dict.fromkeys(('native_solve_seconds all_stage_build_seconds assignment_audit_seconds '
        'archive_encode_seconds archive_bytes replay_seconds complete_episode_wall_seconds '
        'complete_episode_peak_commit_bytes complete_episode_peak_rss_bytes').split())
    expected_contract=dict.fromkeys(('per_stage_time_limit_seconds task_wall_seconds threads process_commit_bytes '
        'job_commit_bytes archive_storage_bytes host_volume_binding').split())
    expected_contract['input_selection_registered']=False
    for field,expected in (('sharing',expected_sharing),('unmeasured',expected_unmeasured),('formal_resource_contract',expected_contract)):
        if shape.binding._bytes(report[field])!=shape.binding._bytes(expected):
            raise ValueError('shape sharing/resource schema mismatch')
    if report['network_identity']!=request['expected_network_identity']:
        raise ValueError('independent network pin mismatch')
    n=report['stage_count']
    order=report['stage_order']
    if (type(n) is not int or n<1 or n!=request['expected_stage_count'] or type(order) is not list or len(order)!=n
            or order[0]!=['operating_cost',None] or report['causal_key'] is not None or report['accepted_normal_carry'] is not None):
        raise ValueError('shape stage order/count or carry mismatch')
    groups={kind:[] for kind in ('commitment','generation')}
    for item in order[1:]:
        if type(item) is not list or len(item)!=2 or item[0] not in groups or type(item[1]) is not str or not item[1]:
            raise ValueError('shape objective label mismatch')
        groups[item[0]].append(item[1])
    if (any(items!=sorted(set(items)) for items in groups.values())
            or not set(groups['commitment'])<=set(groups['generation'])
            or order[1:]!=[['commitment',x] for x in groups['commitment']]+[['generation',x] for x in groups['generation']]):
        raise ValueError('shape objective labels not in canonical UID order')
    samples=report['measured_stage_shapes']
    indices=sorted({0,n-1})
    if type(samples) is not list or len(samples)!=len(indices):
        raise ValueError('shape endpoint sample count mismatch')
    for sample,index in zip(samples,indices):
        if (type(sample) is not dict or set(sample)!={'stage_index','objective','stage_model_identity','placeholder_locks','placeholder_lock_count',
                'lock_provenance_verified','shape_only','shape','model_construction_seconds','shape_count_seconds'}
                or type(sample['stage_index']) is not int or sample['stage_index']!=index
                or type(sample['placeholder_lock_count']) is not int or sample['placeholder_lock_count']!=index
                or sample['placeholder_locks'] is not (index>0) or sample['lock_provenance_verified'] is not False
                or sample['shape_only'] is not True or sample['objective']!=order[index]):
            raise ValueError('shape endpoint provenance mismatch')
        shape.binding.windows._sha(sample['stage_model_identity'])
        _seconds(sample['model_construction_seconds'])
        _seconds(sample['shape_count_seconds'])
        expected_stage=shape.model_api._digest(shape.model_api.CONTRACT,report['normal_input_identity'],
            tuple(tuple(x) for x in order),tuple((0.0).hex() for _ in range(index)),
            sha256(Path(shape.model_api.__file__).read_bytes()).hexdigest())
        if sample['stage_model_identity']!=expected_stage:
            raise ValueError('shape stage identity mismatch')
        counts=sample['shape']
        integer_fields=('active_var_data','fixed_var_data','active_constraint_data','ranged_constraint_data',
                        'linear_constraint_terms','lock_constraint_data','lock_linear_terms','objective_linear_terms')
        if (type(counts) is not dict or set(counts)!=set(integer_fields)|{'variable_classes','objective_sense','linear_term_scope','native_matrix_measured',
                'feasibility_checked','assignment_present','decision_present'}
                or any(type(counts[k]) is not int or counts[k]<0 for k in integer_fields)
                or any(counts[k] is not False for k in ('native_matrix_measured','feasibility_checked','assignment_present','decision_present'))
                or counts['linear_term_scope']!='standard_repn_after_fixed_substitution'
                or counts['ranged_constraint_data']>counts['active_constraint_data']
                or counts['lock_linear_terms']>counts['linear_constraint_terms']
                or counts['objective_sense']!='minimize' or counts['lock_constraint_data']!=index):
            raise ValueError('shape count/authority schema mismatch')
        classes=counts['variable_classes']
        if (type(classes) is not dict or set(classes)!={'binary','general_integer','continuous'} or any(type(v) is not int or v<0 for v in classes.values())
                or sum(classes.values())!=counts['active_var_data'] or counts['fixed_var_data']>counts['active_var_data']):
            raise ValueError('shape variable class partition mismatch')
    first,last=samples[0]['shape'],samples[-1]['shape']
    if (first['active_var_data']!=last['active_var_data']
            or last['active_constraint_data']-first['active_constraint_data']!=n-1):
        raise ValueError('shape endpoint lock increment mismatch')
    envelope=shape.unadmitted_content_envelope(n,192)
    if shape.binding._bytes(report['counterfactual_unadmitted_content_envelope'])!=shape.binding._bytes(envelope):
        raise ValueError('shape counterfactual envelope mismatch')
    connection=shape.sqlite3.connect(':memory:')
    try: local_limit=connection.getlimit(shape.sqlite3.SQLITE_LIMIT_LENGTH)
    finally: connection.close()
    limit=report['sqlite_length_limit_bytes']
    if (type(limit) is not int or limit<=0 or limit!=local_limit or report['counterfactual_single_event_fits_observed_sqlite_length_limit']
            is not (envelope['single_event_bytes']<=limit)):
        raise ValueError('shape SQLite limit relation mismatch')
    timings=[report['source_load_and_assembly_seconds'],report['source_revalidation_seconds']]
    timings.extend(s[k] for s in samples for k in ('model_construction_seconds','shape_count_seconds'))
    if sum(timings)>report['worker_elapsed_seconds']:
        raise ValueError('shape component timings exceed worker elapsed')
    if (report['hard_rss_limit_enforced'] is not False or type(report['process_peak_working_set_bytes']) is not int
            or report['process_peak_working_set_bytes']<=0 or report['peak_working_set_scope']!='process_lifetime_not_single_model'
            or any(v is not None for v in report['unmeasured'].values())
            or report['formal_resource_contract'].get('input_selection_registered') is not False
            or any(v is not None for k,v in report['formal_resource_contract'].items() if k!='input_selection_registered')):
        raise ValueError('shape measurements cannot imply full resource admission')


def run_shape_job(root, declaration, upstream_root, *, config_path, expected_source_identity, dc_bus, expected_network_identity, expected_stage_count,
                  task_budget, commit_reserve_bytes, disk_demand_bytes, disk_reserve_bytes):
    """One launch, no retry; result reads occur only after entire Job is quiet."""
    if type(task_budget) is not process.TaskProcessBudget:
        raise ValueError('explicit shape Job budget required')
    task_budget.__post_init__()
    if task_budget.max_elapsed_seconds>60 or task_budget.max_job_commit_bytes>2*1024**3:
        raise ValueError('zero-solver shape probe exceeds short process ceiling')
    if type(declaration) is not shape.binding.H1SourceDeclaration:
        raise ValueError('exact source declaration required')
    declaration.__post_init__()
    shape.binding.windows._sha(expected_source_identity)
    shape.binding.windows._sha(expected_network_identity)
    if type(expected_stage_count) is not int or expected_stage_count<1:
        raise ValueError('independent positive stage count required')
    upstream=Path(upstream_root).resolve(strict=True)
    config=Path(config_path).resolve(strict=True)
    lease=process.resources.local._Lease(root,True)
    try:
        scratch=lease.root/'scratch_non_authoritative'
        scratch.mkdir()
        output=scratch/'shape_result.json'
        request=dict(schema='h1_zero_solver_shape_probe_request_v1',declaration=asdict(declaration),
            upstream_root=str(upstream),config_path=str(config),expected_source_identity=expected_source_identity,
            dc_bus=dc_bus,expected_network_identity=expected_network_identity,expected_stage_count=expected_stage_count,output_file=str(output),shape_implementation_identity=shape.implementation_identity(),
            worker_sha256=sha256(WORKER.read_bytes()).hexdigest())
        request_path=lease.root/'request.json'
        request_pin=_write(request_path,request)
        host=process.resources.HostResourceBudget(task_budget.max_job_commit_bytes,commit_reserve_bytes,
            (process.resources.DirectoryDemand('shape_scratch',str(scratch),disk_demand_bytes,disk_reserve_bytes),))
        environment=dict(os.environ,TEMP=str(scratch),TMP=str(scratch),OMP_NUM_THREADS='1',
            OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1',PYTHONDONTWRITEBYTECODE='1')
        argv=[sys.executable,'-I','-B',str(WORKER),str(request_path),request_pin]
        args=dict(cwd=scratch,environment=environment,budget=task_budget,host_budget=host,
            expected_host_identity=process.resources.resource_identity(host))
        identity=process.task_process_identity(argv,**args)
        controller_pin=sha256(Path(__file__).read_bytes()).hexdigest()
        _write(lease.root/'intent.json',dict(schema=SCHEMA,request_sha256=request_pin,
            process_identity=identity,controller_sha256=controller_pin,task_budget=asdict(task_budget),host_budget=asdict(host),
            solver_calls_allowed=0,formal_result=False,formal_run_authority=False))
        with process.normal_task_child(argv,**args,expected_process_identity=identity) as child:
            _write(lease.root/'child_identity.json',dict(pid=child.pid,creation_filetime=child.creation_filetime,
                process_identity=identity,release_called=False,initial_headroom=asdict(child.initial_observation)))
            lease.check()
            child.release()
            observation=child.wait()
        _write(lease.root/'process_observation.json',asdict(observation))
        if (observation.reason!='child_exited' or observation.exit_code!=0 or not observation.whole_job_quiescent
                or not observation.job_commit_limits_configured or observation.observation_error_type is not None
                or observation.last_resource_errors):
            raise ValueError('shape Job did not complete cleanly; retained unresolved attempt')
        if (not 0<observation.job_peak_process_commit_bytes<=task_budget.max_process_commit_bytes
                or not 0<observation.job_peak_total_commit_bytes<=task_budget.max_job_commit_bytes):
            raise ValueError('shape Job peak commit inconsistent with enforced cap')
        if output.stat().st_size>MAX_RESULT_BYTES:
            raise ValueError('shape child output exceeds bounded receipt size')
        raw=output.read_bytes()
        report=shape.episode.replay._decode(raw,MAX_RESULT_BYTES)
        validate_result(report,request)
        if report['worker_elapsed_seconds']>task_budget.max_elapsed_seconds:
            raise ValueError('worker elapsed exceeds Job budget')
        if report.get('request_sha256')!=request_pin:
            raise ValueError('shape child request pin mismatch')
        if (shape.implementation_identity()!=request['shape_implementation_identity']
                or sha256(WORKER.read_bytes()).hexdigest()!=request['worker_sha256']
                or sha256(Path(__file__).read_bytes()).hexdigest()!=controller_pin):
            raise ValueError('shape Job producer/controller drift')
        lease.check()
        record=dict(schema=SCHEMA,request_sha256=request_pin,process_identity=identity,result_sha256=sha256(raw).hexdigest(),
            current_one_blob_worst_case_persistence_blocked=not report['counterfactual_single_event_fits_observed_sqlite_length_limit'],
            result_bytes=len(raw),job_observation=asdict(observation),solver_calls=0,formal_result=False,
            formal_execution_ready=False,whole_task_resources_verified=False,shape_receipt_checked=True)
        _write(lease.root/'shape_job_checks.json',record)
        return record
    finally:
        lease.close()
