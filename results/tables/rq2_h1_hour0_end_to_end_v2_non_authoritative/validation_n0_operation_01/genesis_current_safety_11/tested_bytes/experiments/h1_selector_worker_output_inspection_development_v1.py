"""Fresh conditional selector worker replay; never a live Job credential.

The owning parent must confirm exit0/whole-Job quiescence before invoking this
reader. Caller pins and identity declarations alone do not prove execution.
"""
from copy import deepcopy
from dataclasses import asdict,fields
import json
from pathlib import Path
import sys
from types import FunctionType,MappingProxyType

from experiments import h1_selector_released_worker_development_v1 as worker
from experiments import h1_selector_job_lifecycle_development_v1 as lifecycle

sequence,snapshot,io,process=worker.sequence,worker.snapshot,worker.io,worker.process
SCHEMA='h1_selector_worker_output_inspection_development_v1'
FILES=frozenset(('request.json','selector_snapshot.json','launch.json','initial_observation.json',
    'child.json','release_intent.json','consumed.json','worker_result.json','worker_timing_terminal.json'))
OUTPUT_FILES=frozenset(('consumed.json','worker_result.json','worker_timing_terminal.json'))
INPUT_FILES=FILES-OUTPUT_FILES
FLAGS=MappingProxyType(dict(worker.FLAGS,parent_selector_output_authenticated=False,
    whole_job_observation_authenticated=False,selector_parent_connected=False))
_FLAGS=FLAGS
_KEYS=frozenset(FLAGS)
_WORKER_SCOPE=io.encode([worker.CAP,snapshot.CAP,worker.PHASES,sorted(worker.INPUTS),sorted(worker.OUTPUTS),dict(worker.FLAGS)])


def implementation_identity():
    if (SCHEMA!='h1_selector_worker_output_inspection_development_v1' or FLAGS is not _FLAGS
            or frozenset(FLAGS)!=_KEYS or any(v is not False for v in FLAGS.values())
            or FILES!=frozenset(('request.json','selector_snapshot.json','launch.json','initial_observation.json',
                'child.json','release_intent.json','consumed.json','worker_result.json','worker_timing_terminal.json'))
            or OUTPUT_FILES!=frozenset(('consumed.json','worker_result.json','worker_timing_terminal.json'))
            or INPUT_FILES!=FILES-OUTPUT_FILES):
        raise ValueError('selector output inspection scope changed')
    return io.digest(io.encode([SCHEMA,io.digest(Path(__file__).read_bytes()),worker.implementation_identity(),
        lifecycle.implementation_identity()]))


def _verify():
    if (any(getattr(obj,name) is not original for obj,name,original in _FIXED)
            or io.encode([worker.CAP,snapshot.CAP,worker.PHASES,sorted(worker.INPUTS),sorted(worker.OUTPUTS),dict(worker.FLAGS)])!=_WORKER_SCOPE):
        raise ValueError('import-fixed selector output reader changed')


def _integer(value,positive=False):
    if type(value) is not int or value<(1 if positive else 0):raise ValueError('exact nonnegative integer required')
    return value


def _same(value,expected):
    if io.encode(value)!=io.encode(expected):raise ValueError('exact selector output fields or cross-pins differ')


def _source(raw,root,request):
    item=snapshot.rebuild(raw,expected_sha256=request['snapshot']['sha256'])
    _verify()
    if type(item) is not snapshot.RebuiltInput:raise ValueError('exact rebuilt selector input required')
    role={'Rref':'reference','A':'actual'}.get(item.arguments['lane'].role)
    if role is None:raise ValueError('selector lane role required')
    configuration=sequence._configuration((item.frame,item.disclosure,item.before),item.arguments,
        item.max_archive_bytes,request['max_timing_archive_bytes'],item.run_configuration)
    binding=item.run_configuration.binding()
    expected=dict(schema=worker.SCHEMA,root=str(root),implementation=worker.implementation_identity(),
        snapshot=dict(name='selector_snapshot.json',size=len(raw),sha256=io.digest(raw),
            implementation=snapshot.implementation_identity()),route='source_rebuilt_timed_selector',
        role=role,lane=asdict(item.arguments['lane']),run_configuration=binding,
        run_configuration_sha256=io.digest(io.encode(binding)),max_archive_bytes=item.max_archive_bytes,
        max_timing_archive_bytes=request['max_timing_archive_bytes'],
        budget=asdict(getattr(item.run_configuration,role+'_job_budget')),
        non_solver_seconds=getattr(item.run_configuration,role+'_non_solver_seconds'),
        sequence_request_sha256=io.digest(io.encode(configuration)),sequence_configuration=configuration,**worker.FLAGS)
    _same(request,expected)
    return item


def _inspect(root,*,pins,environment,expected_process_identity,expected_pid,expected_creation_filetime,expected_output_pins):
    """Read-only full conditional replay. Call only after owned Job success.

    Six preexisting parent pins are required. Fresh mode discovers three output
    pins by bounded stable reads; retained mode additionally requires those pins.
    """
    _verify();own=implementation_identity()
    root=sequence.legacy._root(root)
    if type(pins) is not dict or set(pins)!=INPUT_FILES:raise ValueError('exact six parent transport pins required')
    pins,environment=deepcopy((pins,environment))
    retained_mode=expected_output_pins is not None
    if retained_mode:
        if type(expected_output_pins) is not dict or set(expected_output_pins)!=OUTPUT_FILES:
            raise ValueError('exact three retained output pins required')
        pins.update(deepcopy(expected_output_pins))
    for pin in pins.values():io.pin(pin)
    io.pin(expected_process_identity)
    _integer(expected_pid,True);_integer(expected_creation_filetime,True)
    worker.runtime._environment(environment)
    directories=worker._roots(root,worker.INPUTS|worker.OUTPUTS)
    retained={}
    for name in sorted(FILES):
        cap=snapshot.CAP if name=='selector_snapshot.json' else worker.CAP
        raw,stamp=worker._read(root/name,cap)
        digest=io.digest(raw)
        if name in pins and digest!=pins[name]:raise ValueError('external selector transport pin differs')
        pins[name]=digest
        retained[name]=(cap,raw,stamp)
    arguments=io.encode([str(root),pins,environment,expected_process_identity,expected_pid,expected_creation_filetime])
    raw=retained['selector_snapshot.json'][1]
    if snapshot.encode(json.loads(raw))!=raw:raise ValueError('canonical selector snapshot required')
    docs={name:worker._doc(value[1]) for name,value in retained.items() if name!='selector_snapshot.json'}
    request=docs['request.json'];launch=docs['launch.json'];child=docs['child.json']
    release=docs['release_intent.json'];result=docs['worker_result.json'];terminal=docs['worker_timing_terminal.json']
    def check():
        _verify()
        if (implementation_identity()!=own or worker._roots(root,worker.INPUTS|worker.OUTPUTS)!=directories
                or io.encode([str(root),pins,environment,expected_process_identity,expected_pid,expected_creation_filetime])!=arguments
                or any(worker._read(root/name,cap)!=(data,stamp) for name,(cap,data,stamp) in retained.items())):
            raise ValueError('selector output retained view changed')
    check()
    with sequence.legacy.bridge.science.prior.guard.solver_calls_forbidden():
        item=_source(raw,root,request);check()
        budget=process.TaskProcessBudget(**request['budget'])
        host_value=worker._object(launch['host'],('additional_commit_bytes','commit_reserve_bytes','directories'))
        if type(host_value['directories']) is not list:raise ValueError('exact host directory vector required')
        resources=process.resources
        host=resources.HostResourceBudget(host_value['additional_commit_bytes'],host_value['commit_reserve_bytes'],
            tuple(resources.DirectoryDemand(**worker._object(d,(f.name for f in fields(resources.DirectoryDemand))))
                for d in host_value['directories']))
        _same(host_value,asdict(host))
        if not any(d.directory==str(root) and d.additional_bytes>=worker.content_bound(request) for d in host.directories):
            raise ValueError('host declaration misses complete selector content bound')
        worker._validate_initial(docs['initial_observation.json'],host)
        identity=process.task_process_identity(launch['argv'],cwd=root/'scratch_non_authoritative',environment=environment,
            budget=budget,host_budget=host,expected_host_identity=resources.resource_identity(host))
        if identity!=expected_process_identity:raise ValueError('selector launch process identity differs')
        _same(launch,dict(request_sha256=pins['request.json'],process_identity=identity,argv=launch['argv'],
            cwd=str(root/'scratch_non_authoritative'),environment_sha256=io.digest(io.encode(environment)),
            budget=asdict(budget),host=asdict(host)))
        _same(child,dict(pid=expected_pid,creation_filetime=expected_creation_filetime,process_identity=identity,
            request_sha256=pins['request.json'],initial_observation_sha256=pins['initial_observation.json']))
        _same(release,dict(request_sha256=pins['request.json'],launch_sha256=pins['launch.json'],child_sha256=pins['child.json']))
        _same(docs['consumed.json'],dict(schema=worker.SCHEMA,request_sha256=pins['request.json'],
            release_sha256=pins['release_intent.json'],child_sha256=pins['child.json'],pid=expected_pid,
            creation_filetime=expected_creation_filetime,**worker.FLAGS))
        science=root/'science_sequence_non_authoritative';timing=root/'timing_sequence_non_authoritative'
        count=len(sequence.selection.stage_labels(item.frame,item.arguments['lane']))
        view=sequence._snapshot(science,timing,count,item.arguments['limits'],True,True)
        view_pin=sequence._snapshot_pin(view,science,timing)
        check()
        fresh=sequence.inspect(science,timing,item.frame,item.disclosure,item.before,
            expected_terminal_sha256=result['sequence_terminal_sha256'],max_archive_bytes=item.max_archive_bytes,
            max_timing_archive_bytes=request['max_timing_archive_bytes'],run_configuration=item.run_configuration,**item.arguments)
        check()
        thread=_integer(result['thread_id'],True)
        profile=sequence.timed.capture.clock_profile()
        _same(result,dict(schema=worker.SCHEMA,implementation=worker.implementation_identity(),
            request_sha256=pins['request.json'],snapshot_sha256=pins['selector_snapshot.json'],
            consumed_sha256=pins['consumed.json'],pid=expected_pid,creation_filetime=expected_creation_filetime,
            thread_id=thread,scientific_root=str(science),timing_root=str(timing),
            sequence_request_sha256=request['sequence_request_sha256'],
            scientific_terminal_sha256=fresh['scientific_terminal_sha256'],sequence_terminal_sha256=fresh['terminal_sha256'],
            archive_view_sha256=view_pin,record_sha256=tuple(io.digest(r) for r in fresh['records']),
            native_interval_ns=fresh['native_interval_ns'],clock=profile,**worker.FLAGS))
        if fresh['request_sha256']!=request['sequence_request_sha256']:raise ValueError('selector sequence request differs')
        phases=terminal['phases']
        if type(phases) is not list or len(phases)!=len(worker.PHASES):raise ValueError('complete eight worker phases required')
        for label,phase in zip(worker.PHASES,phases,strict=True):
            worker._object(phase,('name','start_ns','end_ns'))
            _integer(phase['start_ns']);_integer(phase['end_ns'])
            if phase['name']!=label or phase['end_ns']<phase['start_ns']:raise ValueError('worker phase order differs')
        if any(a['end_ns']!=b['start_ns'] for a,b in zip(phases,phases[1:])):
            raise ValueError('worker phases are not contiguous')
        _same(terminal,dict(schema=worker.SCHEMA,implementation=worker.implementation_identity(),
            request_sha256=pins['request.json'],consumed_sha256=pins['consumed.json'],result_sha256=pins['worker_result.json'],
            pid=expected_pid,creation_filetime=expected_creation_filetime,thread_id=thread,clock=profile,phases=phases,
            entry_to_result_readback_ns=phases[-1]['end_ns']-phases[0]['start_ns'],
            window_scope='execute_entry_to_result_readback_excludes_timing_terminal_and_exit',**worker.FLAGS))
        run_phase=phases[3];vector=fresh['stage_vector']
        if (any(v['pid']!=expected_pid or v['thread_id']!=thread
                or not run_phase['start_ns']<=v['stage_start_ns']<=v['native_start_ns']<=v['native_end_ns']<=v['stage_end_ns']<=run_phase['end_ns']
                for v in vector) or fresh['native_interval_ns']!=sum(v['native_interval_ns'] for v in vector)):
            raise ValueError('native stages outside worker run phase or owner')
        after=_source(raw,root,request);check()
        if (sequence._snapshot(science,timing,count,after.arguments['limits'],True,True)!=view
                or sequence._snapshot_pin(view,science,timing)!=view_pin):
            raise ValueError('selector archive view changed during parent inspection')
        check()
    transport_pin=io.digest(io.encode([directories,[(name,cap,io.digest(data),stamp)
        for name,(cap,data,stamp) in sorted(retained.items())]]))
    data=dict(schema=SCHEMA,implementation=own,role=request['role'],pins=pins,process_identity=identity,
        pid=expected_pid,creation_filetime=expected_creation_filetime,thread_id=thread,
        sequence_request_sha256=fresh['request_sha256'],scientific_terminal_sha256=fresh['scientific_terminal_sha256'],
        sequence_terminal_sha256=fresh['terminal_sha256'],archive_view_sha256=view_pin,transport_view_sha256=transport_pin,
        record_sha256=result['record_sha256'],native_interval_ns=fresh['native_interval_ns'],phases=deepcopy(phases),
        fresh_at_return=True,output_pins_externally_supplied=retained_mode,**FLAGS)
    checked=lifecycle._inspection(dict(schema=lifecycle.INSPECTION_SCHEMA,data=data));check()
    return checked


def inspect(root,*,pins,environment,expected_process_identity,expected_pid,expected_creation_filetime,expected_output_pins=None):
    """Fresh mode reads outputs first; retained mode verifies explicit output pins.

    This function does not verify a live Job and must only be called by the
    controller's on_quiescent callback or as explicitly conditional saved replay.
    """
    _verify()
    with sequence.legacy.bridge.science.prior.guard.solver_calls_forbidden():
        return _inspect(root,pins=pins,environment=environment,expected_process_identity=expected_process_identity,
            expected_pid=expected_pid,expected_creation_filetime=expected_creation_filetime,expected_output_pins=expected_output_pins)


def _bindings():
    module=sys.modules[__name__]
    result=[(module,name,value) for name,value in tuple(vars(module).items()) if isinstance(value,FunctionType)
        and value.__module__==__name__]
    for obj,names in ((worker,('_read','_doc','_roots','_object','content_bound','_validate_initial','implementation_identity')),
        (snapshot,('rebuild','implementation_identity','encode')),
        (sequence,('inspect','_snapshot','_snapshot_pin','_configuration','implementation_identity')),
        (process,('task_process_identity',)),(process.resources,('resource_identity',)),
        (worker.runtime,('_environment',)),(sequence.timed.capture,('clock_profile',)),
        (lifecycle,('_inspection','_scope','implementation_identity')),
        (io,('encode','digest','pin','read_stable'))):
        result.extend((obj,name,getattr(obj,name)) for name in names)
    return tuple(result)


_FIXED=_bindings()
