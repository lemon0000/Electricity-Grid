"""Persistent source-normal execute/audit supervision; no formal run authority."""
from copy import deepcopy
from dataclasses import asdict, dataclass
from hashlib import sha256
from math import isfinite
from pathlib import Path
import sys
import time

from . import normal_numerical_worker as worker, scale_episode_controller as supervision

base, process, local, declared = supervision.base, supervision.process, supervision.local, supervision.declared
SCHEMA = 'draft_source_bound_numerical_normal_pipeline_v1'


@dataclass(frozen=True)
class NormalPipelineBudget:
    execute: declared.DeclaredTaskProcessBudget
    audit: declared.DeclaredTaskProcessBudget
    controller_seconds: int
    execute_overhead_seconds: int
    max_record_bytes: int
    execute_scratch_bytes: int
    audit_scratch_bytes: int
    max_supervisor_peak_working_set_bytes: int
    max_tree_entries: int
    max_outer_scratch_entries: int


def admit(request, allocation):
    worker.source.request_identity(request)
    if type(allocation) is not NormalPipelineBudget:
        raise ValueError('typed source-normal pipeline allocation required')
    for name in ('controller_seconds','execute_overhead_seconds','max_record_bytes','execute_scratch_bytes',
                 'audit_scratch_bytes','max_supervisor_peak_working_set_bytes','max_tree_entries','max_outer_scratch_entries'):
        if type(getattr(allocation,name)) is not int or getattr(allocation,name)<=0:
            raise ValueError('positive explicit pipeline allocation required')
    if allocation.max_record_bytes>64*1024**2:
        raise ValueError('source record exceeds worker replay size limit')
    envelope=request.budget.envelope
    for budget in (allocation.execute,allocation.audit):
        if type(budget) is not declared.DeclaredTaskProcessBudget:
            raise ValueError('envelope-bound source worker process budget required')
        budget.__post_init__()
        if (budget.resource_contract_identity!=request.budget.resource_contract_identity or budget.envelope!=envelope):
            raise ValueError('normal worker budget differs from original resource plan')
    wall=sum(b.max_elapsed_seconds+b.max_quiescence_seconds for b in (allocation.execute,allocation.audit))+allocation.controller_seconds
    if (allocation.execute.max_elapsed_seconds<request.budget.max_observed_wall_seconds+allocation.execute_overhead_seconds
            or wall>envelope.max_wall_seconds
            or wall-request.budget.max_seconds_per_solve>envelope.non_solver_seconds):
        raise ValueError('normal pipeline wall/non-solver allocation shortfall')
    if (envelope.archive_bytes<11*base.LIMIT+2+allocation.max_record_bytes
            or envelope.scratch_bytes<allocation.execute_scratch_bytes+allocation.audit_scratch_bytes
            or allocation.max_tree_entries<17+allocation.max_outer_scratch_entries):
        raise ValueError('normal pipeline archive/scratch/entry allocation shortfall')


def controller_identity(root,request,*,allocation,environment):
    root=local._path(root)
    if not root.name.endswith('_non_authoritative'): raise ValueError('non_authoritative pipeline root required')
    admit(request,allocation)
    if type(environment) is not dict: raise ValueError('explicit worker environment required')
    process.process._environment_block(environment)
    host=supervision._host(root.parent,request,allocation)
    return worker.source.kernel._digest(SCHEMA,str(root),sha256(worker.transport.export_request(request)).hexdigest(),asdict(allocation),
        environment,process.resources.resource_identity(host),worker.implementation_identity(request),
        tuple((m.__name__,sha256(Path(m.__file__).read_bytes()).hexdigest()) for m in
              (supervision,declared,process,process.process,process.resources,base,local)),
        str(Path(sys.executable).resolve()),sha256(Path(sys.executable).read_bytes()).hexdigest(),
        sha256(Path(__file__).read_bytes()).hexdigest())


def _file_pin(path,maximum):
    identity=local._file_identity(path)
    with path.open('rb') as stream: raw=stream.read(maximum+1)
    if len(raw)>maximum or local._file_identity(path)!=identity:
        raise ValueError('normal pipeline evidence size/identity mismatch')
    return identity,sha256(raw).hexdigest()


def _argv(root,mode,request_pin,request_identity,impl,environment_pin,allocation,pins):
    argv=[str(Path(sys.executable).resolve()),'-I','-B',str(Path(worker.__file__).resolve()),
        '--mode',mode,'--request-path',str(root/'request.json'),'--expected-request-sha256',request_pin,
        '--expected-request-identity',request_identity,'--max-request-bytes',str(worker.transport.LIMIT),
        '--root',str(root/'normal_non_authoritative'),'--receipt-path',str(root/(mode+'_receipt_non_authoritative.json')),
        '--expected-environment-identity',environment_pin,'--expected-implementation-identity',impl,
        '--max-record-bytes',str(allocation.max_record_bytes)]
    if pins is not None:
        argv+=['--expected-intent-sha256',pins['intent_sha256'],'--expected-record-sha256',pins['record_sha256'],
               '--expected-execution-environment-identity',pins['environment_identity']]
    return argv


def _audit_outcome(outcome,record):
    keys={'schema','record_consistent','accepted_record_reproduced','numerical','solver_calls_by_replay',
        'source_correspondence_rechecked','mechanism_initial_state','observed_power_mapping','registered_coupling',
        'native_execution_authenticated','resource_measurements_authenticated','executable_resume_available',
        'formal_result','security_certified','prepared_information'}
    if (type(outcome) is not dict or set(outcome)!=keys or outcome['schema']!=worker.source.SCHEMA
            or type(outcome['record_consistent']) is not bool or type(outcome['accepted_record_reproduced']) is not bool
            or type(outcome['solver_calls_by_replay']) is not int or outcome['solver_calls_by_replay']!=0
            or outcome['source_correspondence_rechecked'] is not True or outcome['mechanism_initial_state'] is not True
            or any(outcome[n] is not False for n in ('observed_power_mapping','registered_coupling','native_execution_authenticated',
                'resource_measurements_authenticated','executable_resume_available','formal_result','security_certified'))):
        raise ValueError('source audit receipt inventory or authority mismatch')
    if (base.worker.store._bytes(outcome['numerical']) != base.worker.store._bytes(record['projection'])
            or base.worker.store._bytes(outcome['prepared_information']) != base.worker.store._bytes(record['prepared_information'])
            or outcome['accepted_record_reproduced'] is not record['accepted']):
        raise ValueError('numerical audit projection mismatch')


def _verify_audit(outcome,record,raw,request,request_identity,record_pin,maximum):
    _audit_outcome(outcome,record)
    source=worker.source
    with source.solver_free():
        reproduced=source.audit_source(raw,request,expected_sha256=record_pin,
            expected_request_identity=request_identity,max_record_bytes=maximum)
    if base.worker.store._bytes(outcome)!=base.worker.store._bytes(reproduced):
        raise ValueError('audit receipt differs from independent parent replay')


def _completion(outcome,record,reserved_solver_seconds):
    complete=(outcome['numerical'] is not None and record['call_count_complete'] is True
        and type(record['solver_calls']) is int)
    status=('normal_invocation_unknown_not_replayed' if not complete else
        'replayed_accepted_normal' if outcome['accepted_record_reproduced'] else
        'replayed_unresolved_normal' if outcome['record_consistent'] else
        'unresolved_normal_record_not_reproduced')
    return dict(status=status,solver_calls=record['solver_calls'],
        call_count_complete=record['call_count_complete'],reserved_solver_seconds=reserved_solver_seconds)


def supervise_normal(root,request,*,allocation,environment,expected_controller_identity):
    started=time.monotonic()
    request,allocation,environment=deepcopy((request,allocation,environment))
    root=local._path(root)
    evidence=root/'normal_non_authoritative'
    retained={}
    evidence_pins=None
    evidence_lease=None
    lease=object.__new__(local._Lease)
    worker_elapsed,active_started=0.,None
    def identity_check():
        if controller_identity(root,request,allocation=allocation,environment=environment)!=expected_controller_identity:
            raise ValueError('source normal pipeline identity drift')
    identity_check()
    def snapshot(held):
        if {p.name for p in evidence.iterdir()}!={'execution.lock','intent.json','normal_record.json'}:
            raise ValueError('normal worker evidence inventory mismatch')
        return dict({name:_file_pin(evidence/name,maximum) for name,maximum in
                (('intent.json',base.LIMIT),('normal_record.json',allocation.max_record_bytes))},
                root_identity=held.root_identity,lock_identity=held.file_identity)
    def check():
        lease.check()
        identity_check()
        for path,(identity,pin) in retained.items():
            if _file_pin(path,base.LIMIT)!=(identity,pin): raise ValueError('pipeline retained bytes changed')
        sample=supervision._measure(root,request,allocation,started)
        if evidence_pins is not None:
            held=evidence_lease or local._Lease(evidence,False)
            try:
                held.check()
                if snapshot(held)!=evidence_pins: raise ValueError('source evidence changed between phases')
            finally:
                if held is not evidence_lease: held.close()
        now=time.monotonic()
        elapsed=now-started-worker_elapsed-(0. if active_started is None else now-active_started)
        if elapsed>allocation.controller_seconds: raise TimeoutError('normal controller allowance exceeded')
        sample['controller_elapsed_seconds']=elapsed
        return sample
    def write(name,body):
        supervision._measure(root,request,allocation,started,len(base.worker.store._bytes(body)))
        retained[root/name]=base._write(root/name,body)
    try:
        host=supervision._host(root.parent,request,allocation)
        if not process.resources.observe_headroom(host,expected_request_identity=process.resources.resource_identity(host)).observed_headroom_sufficient:
            raise ValueError('normal pipeline initial headroom insufficient')
        local._Lease.__init__(lease,root,True)
        for name in ('execute_scratch','audit_scratch'): (root/name).mkdir()
        packet=worker.transport.export_request(request)
        supervision._measure(root,request,allocation,started,len(packet))
        retained[root/'request.json']=worker._write_record(root/'request.json',packet,worker.transport.LIMIT)
        request_pin=sha256(packet).hexdigest()
        request_id=worker.source.request_identity(request)
        impl=worker.implementation_identity(request)
        phases,pins,record=[],None,None
        for mode,budget in (('execute',allocation.execute),('audit',allocation.audit)):
            sample=check()
            remaining=(allocation.execute,allocation.audit) if mode=='execute' else (allocation.audit,)
            needed=sum(b.max_elapsed_seconds+b.max_quiescence_seconds for b in remaining)
            needed+=max(0.,allocation.controller_seconds-sample['controller_elapsed_seconds'])
            if request.budget.envelope.max_wall_seconds-(time.monotonic()-started)<needed:
                raise TimeoutError('normal pipeline remaining wall insufficient')
            scratch=root/(mode+'_scratch')
            env=dict(environment,TEMP=str(scratch),TMP=str(scratch))
            env_pin=sha256(base.worker.store._bytes(env)).hexdigest()
            argv=_argv(root,mode,request_pin,request_id,impl,env_pin,allocation,pins)
            host=supervision._host(root,request,allocation,scratch,sample)
            options=dict(cwd=scratch,environment=env,budget=budget,host_budget=host,
                expected_host_identity=process.resources.resource_identity(host))
            process_pin=declared.task_process_identity(argv,**options)
            write(mode+'_intent.json',dict(schema=SCHEMA,mode=mode,controller_identity=expected_controller_identity,
                request_sha256=request_pin,process_identity=process_pin,worker_identity=impl,audit_pins=pins,
                allocation=asdict(allocation),host_budget=asdict(host),formal_result=False))
            check()
            with declared.declared_task_child(argv,expected_process_identity=process_pin,**options) as child:
                active_started=child._started
                write(mode+'_launch.json',dict(process_identity=process_pin,pid=child.pid,creation_filetime=child.creation_filetime))
                check()
                child.release()
                observed=child.wait()
                if (type(observed) is not process.TaskProcessObservation or observed.process_identity!=process_pin
                        or observed.pid!=child.pid or observed.creation_filetime!=child.creation_filetime
                        or observed.whole_job_quiescent is not True):
                    raise ValueError('normal worker identity or quiescence unverified')
                if type(observed.elapsed_seconds) not in (int,float) or not isfinite(observed.elapsed_seconds) or observed.elapsed_seconds<0:
                    raise ValueError('normal worker lifecycle time invalid')
                worker_elapsed+=observed.elapsed_seconds
                active_started=None
            write(mode+'_observation.json',asdict(observed))
            check()
            supervision._successful_observation(observed,budget,host)
            evidence_lease=local._Lease(evidence,False)
            try:
                check()
                current=snapshot(evidence_lease)
                receipt=root/(mode+'_receipt_non_authoritative.json')
                receipt_pin=_file_pin(receipt,base.LIMIT)
                body=base._read(receipt,receipt_pin[0])
                required={'schema','mode','request_identity','request_sha256','environment_identity','implementation_identity',
                    'root','intent_sha256','record_sha256','outcome','formal_result','whole_task_resources_verified','executable_resume_available'}
                expected=dict(schema=worker.SCHEMA,mode=mode,request_identity=request_id,request_sha256=request_pin,
                    environment_identity=env_pin,implementation_identity=impl,root=str(evidence),
                    intent_sha256=current['intent.json'][1],record_sha256=current['normal_record.json'][1],
                    formal_result=False,whole_task_resources_verified=False,executable_resume_available=False)
                if (set(body)!=required or any(base.worker.store._bytes(body[n])!=base.worker.store._bytes(v) for n,v in expected.items())
                        or sha256(base.worker.store._bytes(body)).hexdigest()!=receipt_pin[1]):
                    raise ValueError('normal worker receipt binding mismatch')
                retained[receipt]=receipt_pin
                outcome=body['outcome']
                if mode=='execute':
                    evidence_pins=current
                    raw=worker.source.prepare._read_pinned(evidence/'normal_record.json',current['normal_record.json'][1],allocation.max_record_bytes)
                    record=worker.source.prepare._json(raw)
                    summary={k:record[k] for k in ('accepted','status','solver_calls','call_count_complete','source_correspondence_verified')}
                    if base.worker.store._bytes(summary)!=base.worker.store._bytes(outcome):
                        raise ValueError('execution receipt differs from archived source result')
                    pins=dict(intent_sha256=current['intent.json'][1],record_sha256=current['normal_record.json'][1],environment_identity=env_pin)
                else:
                    _verify_audit(outcome,record,raw,request,request_id,pins['record_sha256'],allocation.max_record_bytes)
                evidence_lease.check()
            finally:
                if mode=='execute':
                    evidence_lease.close()
                    evidence_lease=None
            phases.append(dict(mode=mode,process_identity=process_pin,receipt_sha256=receipt_pin[1],observation=asdict(observed)))
            check()
        sample=check()
        result=dict(schema=SCHEMA,controller_identity=expected_controller_identity,
            **_completion(outcome,record,request.budget.max_seconds_per_solve),
            phases=phases,source_pins=pins,audit=outcome,resource_sample=sample,formal_result=False,
            whole_task_resources_verified=False,executable_resume_available=False)
        write('result.json',result)
        return result
    finally:
        try:
            if evidence_lease is not None: evidence_lease.close()
        finally:
            if getattr(lease,'stream',None) is not None: lease.close()
